"""Native run bindings, terminal fences and immutable consolidation cuts."""

from types import SimpleNamespace

import pytest
from sqlalchemy import insert, select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import (
    OperationBinding,
    OperationConflict,
    claim_tasks,
    complete_task,
    create_run,
    create_task,
    cut_observations,
    record_method,
    seal_cut,
)


def setup(engine, *, observations=False, archive=False):
    bundle = SourceBundle(
        "m",
        (
            SourceArtifact(
                "m",
                b"""id: https://example/m
name: m
prefixes: {ex: 'https://example/'}
default_prefix: ex
types:
 string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}
 integer: {base: int, uri: 'http://www.w3.org/2001/XMLSchema#integer'}
 boolean: {base: bool, uri: 'http://www.w3.org/2001/XMLSchema#boolean'}
classes:
 Report:
  attributes:
   text: {required: true}
""",
            ),
        ),
    )
    if observations:
        from pathlib import Path

        from corpus_structure.semantic.observations import observation_inputs

        core = SourceArtifact(
            "core",
            (
                Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
            ).read_bytes(),
        )
        root = bundle.sources[0]
        bundle = SourceBundle(
            "m",
            (
                core,
                SourceArtifact(
                    root.name,
                    root.content.split(b"types:", 1)[0].replace(
                        b"default_prefix: ex", b"default_prefix: ex\nimports: [core]"
                    )
                    + b"classes:"
                    + root.content.split(b"classes:", 1)[1],
                ),
            ),
        )
        bundle = observation_inputs(bundle)
    from corpus_structure.semantic.types import ResolvedDependencies
    dependencies = ResolvedDependencies()
    if observations:
        from corpus_structure.semantic.metrics import observation_dependencies
        from corpus_structure.semantic.metrics import METRIC_INPUT
        import yaml
        packaged = observation_dependencies(dependencies)
        declared = yaml.safe_load(next(a.content for a in packaged.artifacts if a.name == METRIC_INPUT))
        declared["metrics"].append(dict(id="count", value_type="SourceNumberOrNull", subject_kind="run", detail_schema="SourceObject", description="Test method count"))
        dependencies = observation_dependencies(dependencies, yaml.safe_dump(declared).encode())
    p = prepare_release(bundle, dependencies)
    with engine.begin() as c:
        if archive or observations:
            from corpus_structure.semantic.releases import persist_release
            from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies

            persist_release(c, bundle, dependencies, PreparationProfile(), p)
        else:
            c.execute(
                insert(table("sem.release")).values(
                    release_id=p.release_id,
                    content_digest="test",
                    profile="test",
                    prepared_bytes=b"{}",
                    manifest_bytes=b"{}",
                )
            )
        c.execute(insert(table("data.project")).values(project_id="p"))
        c.execute(
            insert(table("data.realization")).values(
                realization_id="z", release_id=p.release_id, project_id="p"
            )
        )
    return p


def test_native_terminal_fence_replay_and_sealed_cut(semantic_db_engine, semantic_writer_engine):
    p = setup(semantic_db_engine)
    e = semantic_writer_engine
    binding = OperationBinding(p.release_id, "z", 0, b"{}")
    with e.begin() as c:
        run = create_run(
            c, project_id="p", binding=binding, kind="full", options={}, code_commit="test"
        )
        config = record_method(
            c,
            SimpleNamespace(
                name="read",
                version="1",
                family="ingest",
                tier="deterministic",
                confidence_source=None,
            ),
            "default",
            {},
            "config:one",
        )
        task = create_task(
            c, run_id=run, config_id=config, stage="ingest", unit_type="run", input_hash="same"
        )
        claim = claim_tasks(c, run_id=run, config_id=config, holder="worker")[0]
    observations = [
        {
            "payload_definition": "Report",
            "item_key": "a",
            "payload": {"text": "same"},
            "kind": "reading",
        },
        {
            "payload_definition": "Report",
            "item_key": "b",
            "payload": {"text": "same"},
            "kind": "reading",
        },
    ]
    with e.begin() as c:
        ids = complete_task(
            c,
            task_id=task,
            attempt=claim.attempt,
            holder="worker",
            prepared=p,
            observations=observations,
        )
    with e.begin() as c:
        assert (
            complete_task(
                c,
                task_id=task,
                attempt=claim.attempt,
                holder="worker",
                prepared=p,
                observations=observations,
            )
            .receipt == ids.receipt
        )
        pending = create_task(
            c, run_id=run, config_id=config, stage="ingest", unit_type="run", input_hash="late"
        )
        later = claim_tasks(c, run_id=run, config_id=config, holder="late")[0]
        c.execute(
            table("ops.task")
            .update()
            .where(table("ops.task").c.id == pending)
            .values(status="cancelled")
        )
        cut = seal_cut(c, run, "final", final=True)
        assert seal_cut(c, run, "final", final=True) == cut
        rows = cut_observations(c, cut)
        assert [r["payload"] for r in rows] == [{"text": "same"}, {"text": "same"}]
        assert len({r["observation_key"] for r in rows}) == 2
    with pytest.raises(OperationConflict), e.begin() as c:
        complete_task(
            c,
            task_id=pending,
            attempt=later.attempt,
            holder="late",
            prepared=p,
            observations=observations,
        )
    with pytest.raises(DBAPIError), e.begin() as c:
        c.execute(table("kb.observation").insert().values(task_id=task))


def test_binding_revision_and_wrong_attempt(semantic_db_engine, semantic_writer_engine):
    p = setup(semantic_db_engine)
    e = semantic_writer_engine
    with pytest.raises(OperationConflict), e.begin() as c:
        create_run(
            c,
            project_id="p",
            binding=OperationBinding(p.release_id, "z", 1, b"{}"),
            kind="full",
            options={},
            code_commit="test",
        )
    with e.begin() as c:
        run = create_run(
            c,
            project_id="p",
            binding=OperationBinding(p.release_id, "z", 0, b"{}"),
            kind="full",
            options={},
            code_commit="test",
        )
        config = record_method(
            c,
            SimpleNamespace(
                name="read",
                version="1",
                family="ingest",
                tier="deterministic",
                confidence_source=None,
            ),
            "default",
            {},
            "config:one",
        )
        task = create_task(
            c, run_id=run, config_id=config, stage="ingest", unit_type="run", input_hash="same"
        )
        claim_tasks(c, run_id=run, config_id=config, holder="worker")
    with pytest.raises(OperationConflict), e.begin() as c:
        complete_task(
            c,
            task_id=task,
            attempt=2,
            holder="worker",
            prepared=p,
            observations=[],
            outcome="empty",
        )
    with e.connect() as c:
        assert not c.execute(select(table("kb.observation"))).first()


def test_source_rendition_fidelity_and_original_change(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    from corpus_structure.core.evidence import RenditionContent, Segment
    from corpus_structure.core.vocab import SegmentKind
    from corpus_structure.semantic.operations import (
        read_original,
        read_rendition,
        register_document,
        store_rendition,
    )

    p = setup(semantic_db_engine)
    e = semantic_writer_engine
    original = tmp_path / "source.html"
    original.write_bytes(b"<p>source</p>")
    content = RenditionContent(
        canonical_text="é🙂\n",
        document=Segment(
            kind=SegmentKind.DOCUMENT,
            start=0,
            end=3,
            children=(Segment(kind=SegmentKind.PARAGRAPH, start=0, end=2),),
        ),
    )
    with e.begin() as c:
        run = create_run(
            c,
            project_id="p",
            binding=OperationBinding(p.release_id, "z", 0, b"{}"),
            kind="full",
            options={},
            code_commit="test",
        )
        cfg = record_method(
            c,
            SimpleNamespace(
                name="read",
                version="1",
                family="ingest",
                tier="deterministic",
                confidence_source=None,
            ),
            "default",
            {},
            "config",
        )
        task = create_task(
            c, run_id=run, config_id=cfg, stage="ingest", unit_type="run", input_hash="same"
        )
        doc = register_document(
            c,
            project_id="p",
            source_uri="file:source",
            original_path=str(original),
            original=original.read_bytes(),
        )
        ren = store_rendition(
            c,
            run_id=run,
            document_id=doc,
            content=content,
            task_id=task,
            config_id=cfg,
            parse_detail={"diagnostic": "kept"},
        )
        assert read_rendition(c, ren) == content
        assert read_original(c, doc) == original.read_bytes()
        assert (
            store_rendition(
                c,
                run_id=run,
                document_id=doc,
                content=content,
                task_id=task,
                config_id=cfg,
                parse_detail={"diagnostic": "kept"},
            )
            == ren
        )
    original.write_bytes(b"changed")
    with e.connect() as c, pytest.raises(OperationConflict):
        read_original(c, doc)


def test_recognizer_terminal_source_boundary_and_coverage(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine
):
    from pydantic import BaseModel

    from corpus_structure.core.method import (
        CoverageDraft,
        MeasurementDraft,
        ObservationDraft,
        UnitRef,
        UnitResult,
    )
    from corpus_structure.core.vocab import (
        MeasurementScope,
        ObservationKind,
        ObservationOutcome,
        TaskUnitType,
    )
    from corpus_structure.semantic.observations import source_python
    from corpus_structure.semantic.operations import complete_unit_result

    class Payload(BaseModel):
        text: str

    p = setup(semantic_db_engine, observations=True)
    e = semantic_writer_engine
    method = SimpleNamespace(
        name="read", version="1", family="ingest", tier="deterministic", confidence_source=None
    )
    with e.begin() as c:
        run = create_run(
            c,
            project_id="p",
            binding=OperationBinding(p.release_id, "z", 0, b"{}"),
            kind="full",
            options={},
            code_commit="test",
        )
        cfg = record_method(c, method, "default", {}, "config")
        task = create_task(
            c,
            run_id=run,
            config_id=cfg,
            stage="ingest",
            unit_type="run",
            unit_key="unit:1",
            input_hash="same",
        )
        claimed = claim_tasks(c, run_id=run, config_id=cfg, holder="worker")[0]
    draft = ObservationDraft(
        kind=ObservationKind.AUTHOR_MARKUP,
        payload=Payload(text="exact"),
        payload_class=Payload,
        payload_version="1",
    )
    result = UnitResult(
        ref=UnitRef(TaskUnitType.RUN, unit_key="unit:1"),
        outcome=ObservationOutcome.PRODUCED,
        observations=(draft, draft),
        coverage=(
            CoverageDraft(
                family="parse", scope="unit:1", outcome="partial", reason="unsupported tail"
            ),
        ),
        measurements=(
            MeasurementDraft(metric="count", scope_type=MeasurementScope.RUN, value=2),
            MeasurementDraft(metric="count", scope_type=MeasurementScope.RUN, value=2),
            MeasurementDraft(metric="count", scope_type=MeasurementScope.RUN, value=3.5,
                detail={"flag": False, "text": "δ", "items": [1, None, 0.5]}),
            MeasurementDraft(metric="count", scope_type=MeasurementScope.RUN, value=None),
        ),
    )
    with e.begin() as c:
        ids = complete_unit_result(
            c,
            task_id=task,
            attempt=claimed.attempt,
            holder="worker",
            prepared=p,
            result=result,
            method=method,
            configuration_hash="config",
            source="file:source",
        )
        assert len(ids.receipt.observation_ids) == 2
        assert ids.transaction == "applied"
        envelope = c.execute(select(table("ops.task_result").c.body)).scalar_one()
        assert envelope["coverage"] == [
            {
                "family": "parse",
                "scope": "unit:1",
                "outcome": "partial",
                "reason": "unsupported tail",
            }
        ]
        rows = c.execute(select(table("kb.observation"))).mappings().all()
        assert [source_python(r["payload"]["payload"]) for r in rows] == [
            {"text": "exact"},
            {"text": "exact"},
        ]
        assert len({r["observation_key"] for r in rows}) == 2
        assert (
            complete_unit_result(
                c,
                task_id=task,
                attempt=claimed.attempt,
                holder="worker",
                prepared=p,
                result=result,
                method=method,
                configuration_hash="config",
                source="file:source",
            )
            .receipt == ids.receipt
        )
        measured_rows = c.execute(select(table("ops.measurement")).order_by(table("ops.measurement").c.source_position)).mappings().all()
        assert [row["source_position"] for row in measured_rows] == [0, 1, 2, 3]
        assert [row["value"] for row in measured_rows] == [2, 2, 3.5, None]
        assert measured_rows[2]["detail"] == {"flag": False, "text": "δ", "items": [1, None, 0.5]}
        for changes in ({}, {"source_position": 0}, {"metric": "undeclared"}, {"run_id": run + 10000}, {"detail": []}):
            with pytest.raises(DBAPIError), c.begin_nested():
                forged = dict(run_id=run, task_id=task, metric="count", scope_type="run", value=2, detail={})
                forged.update(changes)
                c.execute(insert(table("ops.measurement")).values(**forged))
    from dataclasses import replace

    changed = replace(
        result,
        measurements=(MeasurementDraft(metric="count", scope_type=MeasurementScope.RUN, value=3),),
    )
    with pytest.raises(OperationConflict), e.begin() as c:
        complete_unit_result(
            c,
            task_id=task,
            attempt=claimed.attempt,
            holder="worker",
            prepared=p,
            result=changed,
            method=method,
            configuration_hash="config",
            source="file:source",
        )


    from corpus_structure.semantic.arrow_publication import SnapshotDerivedPublication, publish_arrow_on_connection
    from corpus_structure.semantic.publication import PublicationBatch
    from corpus_structure.semantic.query import SnapshotBinding, read_session
    with e.connect().execution_options(isolation_level="SERIALIZABLE") as c, c.begin():
        cut = seal_cut(c, run, "measurement-final", final=True)
        c.execute(text("SELECT data.begin_evaluation(:cut,:output)"), {"cut": cut, "output": "measurement-output"})
        batch = PublicationBatch(p.release_id, "measurement-output", "measurement-result")
        publish_arrow_on_connection(c, SnapshotDerivedPublication.from_rows(batch,
            source=SnapshotBinding(p.release_id, "z", 0, "cut:" + str(cut)),
            operation_id="consolidate_cut", projection_id="candidate"))
        c.execute(text("SELECT data.finish_evaluation(:cut,:output,:batch)"),
                  {"cut": cut, "output": "measurement-output", "batch": batch.batch_id})
    with read_session(semantic_reader_engine, "measurement-output") as session:
        measurements = [m.model_dump(mode="python") for m in session.measurements("count")]
    assert len(measurements) == 4
    assert [m["source_position"] for m in measurements] == [0, 1, 2, 3]
    assert [source_python(m["value"]) for m in measurements] == [2, 2, 3.5, None]
    assert source_python(measurements[2]["detail"]) == {"flag": False, "text": "δ", "items": [1, None, 0.5]}
    measurement = measurements[0]
    assert measurement["metric"]["id"] == "count"
    assert measurement["subject"]["kind"] == "run"
    assert measurement["producer"]["run_id"] == run
    assert measurement["producer"]["task_id"] == task
    assert measurement["producer"]["method"] == "read"
    assert measurement["producer"]["operation_version"] == "1"
    assert source_python(measurement["value"]) == 2
    for statement in (
        "INSERT INTO ops.measurement(run_id,task_id,metric,scope_type,value,detail,source_position) VALUES(:run,:task,'count','run',2,'{}'::jsonb,4)",
        "UPDATE ops.measurement SET value=999 WHERE task_id=:task",
        "DELETE FROM ops.measurement WHERE task_id=:task",
    ):
        with pytest.raises(DBAPIError), e.begin() as c:
            c.execute(text(statement), {"run": run, "task": task})
    with read_session(semantic_reader_engine, "measurement-output") as session:
        assert [m.source_position for m in session.measurements("count")] == [0, 1, 2, 3]
    import json
    malformed_values = (
        {"kind": "float", "hexadecimal": "NaN"},
        {"kind": "object", "fields": [
            {"name": "x", "position": 0, "value": {"kind": "null"}},
            {"name": "x", "position": 1, "value": {"kind": "integer", "integer": 2}},
        ]},
        {"kind": "object", "fields": [{"name": "x", "position": 4, "value": {"kind": "null"}}]},
    )
    with semantic_db_engine.connect() as c:
        for malformed in malformed_values:
            with pytest.raises(DBAPIError), c.begin_nested():
                c.execute(text("SELECT ops.decode_source_value(CAST(:value AS jsonb))"), {"value": json.dumps(malformed)})


@pytest.mark.parametrize(
    "body", ["A paragraph with two sentences. Another sentence.", r"Let \(x\) be a variable."]
)
def test_current_ingest_and_profile_graph_on_semantic_storage(
    semantic_db_engine, semantic_writer_engine, tmp_path, body
):
    from corpus_structure.core.method import MethodSettings
    from corpus_structure.ingest.methods import METHODS
    from corpus_structure.methods.math.methods import METHODS as MATH_METHODS
    from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
    from corpus_structure.orchestrate.semantic import run_source_methods
    from corpus_structure.semantic.operations import register_document

    p = setup(semantic_db_engine, observations=True)
    e = semantic_writer_engine
    raw = tmp_path / "input.html"
    raw.write_text("<html><body><h1>Source</h1><p>" + body + "</p></body></html>")
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "test.yaml").write_text(
        "version: '1'\nroot: toy\napplies_to: 'toy/*.html'\n"
        "language: english\ntitle: h1\nsections: [h1]\n"
    )
    registry = MethodRegistry(
        (*METHODS, *MATH_METHODS),
        MethodsFile(
            sections={
                "math": {"macros": {}, "constants": []},
                "binders": {
                    "sentence_initial": ["let"],
                    "clause": [],
                    "reopen": [],
                    "section_wide": [],
                },
            },
            configs={
                "ingest.html": {"default": {"source_profile": "test"}},
                "segment.sentences": {"default": {}},
                "profile.segments": {"default": {}},
            },
        ),
        sources=sources,
    )
    with e.begin() as c:
        register_document(
            c,
            project_id="p",
            source_uri="toy/input.html",
            original_path=str(raw),
            original=raw.read_bytes(),
        )
    from corpus_structure.orchestrate.phase0 import PHASE0

    graph = PHASE0
    report = run_source_methods(
        e,
        project_id="p",
        prepared=p,
        binding=OperationBinding(p.release_id, "z", 0, b"{}"),
        registry=registry,
        graph=graph,
        method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
    )
    assert report.status == "source_ready" and report.cut_id is not None
    with e.connect() as c:
        assert (
            c.execute(select(table("kb.rendition").c.canonical_text)).scalar_one()
            == "Source\n\n" + body
        )
        assert c.execute(select(table("ops.measurement").c.metric)).first()
        assert len(c.execute(select(table("ops.cut_task"))).all()) == 5
        if "\\(" in body:
            kinds = set(c.execute(select(table("kb.observation").c.kind)).scalars())
            assert {"mention", "value"} <= kinds
            assert "scope" in kinds
            assert c.execute(select(table("kb.observation_input").c.role)).first()
    replay = run_source_methods(
        e,
        project_id="p",
        prepared=p,
        binding=OperationBinding(p.release_id, "z", 0, b"{}"),
        registry=registry,
        graph=graph,
        method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
    )
    assert replay.cut_id is not None
    with e.connect() as c:
        statuses = (
            c.execute(
                select(table("ops.task").c.status).where(
                    table("ops.task").c.run_id == replay.run_id
                )
            )
            .scalars()
            .all()
        )
        assert statuses == ["reused"] * 5
        assert [r["observation_key"] for r in cut_observations(c, report.cut_id)] == [
            r["observation_key"] for r in cut_observations(c, replay.cut_id)
        ]
    fresh_run = run_source_methods(
        e,
        project_id="p",
        prepared=p,
        binding=OperationBinding(p.release_id, "z", 0, b"{}"),
        registry=registry,
        graph=graph,
        method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
        fresh=("ingest.html", "profile.segments"),
    )
    with e.connect() as c:
        t = table("ops.task")
        m = table("ops.method")
        cfg = table("ops.method_config")
        states = dict(
            c.execute(
                select(m.c.name, t.c.status)
                .join_from(t, cfg, t.c.method_config_id == cfg.c.id)
                .join(m, cfg.c.method_id == m.c.id)
                .where(t.c.run_id == fresh_run.run_id)
            ).all()
        )
        assert states["ingest.html"] == "empty" and states["profile.segments"] == "empty"
        assert (
            states["extract.math"] == "reused"
            and states["normalize.formula"] == "reused"
            and states["resolve.symbol_scope"] == "reused"
        )
        assert len(c.execute(select(table("ops.rendition_build"))).all()) == 2
        assert len(c.execute(select(table("kb.rendition"))).all()) == 1
        assert (
            len(
                c.execute(
                    select(table("ops.measurement")).where(
                        table("ops.measurement").c.run_id == fresh_run.run_id
                    )
                ).all()
            )
            > 0
        )
    fresh_all = run_source_methods(
        e,
        project_id="p",
        prepared=p,
        binding=OperationBinding(p.release_id, "z", 0, b"{}"),
        registry=registry,
        graph=graph,
        method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
        fresh=(
            "ingest.html",
            "profile.segments",
            "extract.math",
            "normalize.formula",
            "resolve.symbol_scope",
        ),
    )
    assert fresh_all.cut_id is not None
    with e.connect() as c:
        assert (
            "reused"
            not in c.execute(
                select(table("ops.task").c.status).where(
                    table("ops.task").c.run_id == fresh_all.run_id
                )
            )
            .scalars()
            .all()
        )
        assert {r["observation_key"] for r in cut_observations(c, report.cut_id)}.isdisjoint(
            r["observation_key"] for r in cut_observations(c, fresh_all.cut_id)
        )
    changed_policy = run_source_methods(
        e,
        project_id="p",
        prepared=p,
        binding=OperationBinding(p.release_id, "z", 0, b"{}"),
        registry=registry,
        graph=graph,
        method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
        policy_source="version: 'changed'\nchains: {}\n",
    )
    with e.connect() as c:
        states = (
            c.execute(
                select(table("ops.task").c.status).where(
                    table("ops.task").c.run_id == changed_policy.run_id
                )
            )
            .scalars()
            .all()
        )
        assert len(states) == 5 and "reused" not in states
    raw.write_text("changed after registered input")
    with pytest.raises(OperationConflict, match="original content changed"):
        run_source_methods(
            e,
            project_id="p",
            prepared=p,
            binding=OperationBinding(p.release_id, "z", 0, b"{}"),
            registry=registry,
            graph=graph,
            method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
        )


def test_reuse_requires_complete_bound_meaning(semantic_db_engine, semantic_writer_engine):
    p = setup(semantic_db_engine)
    e = semantic_writer_engine
    method = SimpleNamespace(
        name="read", version="1", family="ingest", tier="deterministic", confidence_source=None
    )

    def start(c, dependencies):
        run = create_run(
            c,
            project_id="p",
            binding=OperationBinding(p.release_id, "z", 0, dependencies),
            kind="full",
            options={},
            code_commit="test",
        )
        cfg = record_method(c, method, "default", {}, "config")
        return run, cfg

    with e.begin() as c:
        first, cfg = start(c, b"{}")
        task = create_task(
            c, run_id=first, config_id=cfg, stage="ingest", unit_type="run", input_hash="same"
        )
        claim_tasks(c, run_id=first, config_id=cfg, holder="worker")
        complete_task(
            c,
            task_id=task,
            attempt=1,
            holder="worker",
            prepared=p,
            observations=[],
            outcome="empty",
        )
    with e.begin() as c:
        second, cfg = start(c, b"{}")
        same = create_task(
            c, run_id=second, config_id=cfg, stage="ingest", unit_type="run", input_hash="same"
        )
        changed, cfg = start(c, b'{"policy":"changed"}')
        different = create_task(
            c, run_id=changed, config_id=cfg, stage="ingest", unit_type="run", input_hash="same"
        )
        t = table("ops.task")
        assert c.execute(select(t.c.status, t.c.reused_task_id).where(t.c.id == same)).one() == (
            "reused",
            task,
        )
        assert c.execute(
            select(t.c.status, t.c.reused_task_id).where(t.c.id == different)
        ).one() == ("pending", None)


def test_cli_initializes_indexed_source_project_without_active_pointer_changes(
    semantic_db_engine, semantic_writer_engine, tmp_path, monkeypatch
):
    from contextlib import contextmanager

    from typer.testing import CliRunner

    from corpus_structure.cli import orchestrate as cli
    from corpus_structure.cli.app import app
    from corpus_structure.ingest.methods import METHODS
    from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile

    p = setup(semantic_db_engine, observations=True, archive=True)
    e = semantic_writer_engine
    corpus = tmp_path / "corpus"
    (corpus / "toy").mkdir(parents=True)
    (corpus / "toy" / "input.html").write_text("<p>Source</p>")
    (corpus / "index.tsv").write_text("path\tfirst_pass\ninput.html\tyes\n")
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "test.yaml").write_text(
        "version: '1'\nroot: toy\nindex: {file: index.tsv, page: path}\napplies_to: 'toy/*.html'\n"
    )
    registry = MethodRegistry(
        METHODS,
        MethodsFile(
            configs={
                "ingest.html": {"default": {"source_profile": "test"}},
                "segment.sentences": {"default": {}},
                "profile.segments": {"default": {}},
            }
        ),
        sources=sources,
    )

    @contextmanager
    def engine(_):
        yield e

    monkeypatch.setattr(cli, "ENGINE", engine)
    monkeypatch.setattr(
        cli, "PHASE0", lambda: {"registry_for": lambda _: registry, "domains": tmp_path}
    )
    result = CliRunner().invoke(
        app,
        [
            "project",
            "init",
            "--domain",
            "test",
            "--corpus",
            str(corpus),
            "--name",
            "new-project",
            "--semantic-release",
            p.release_id,
            "--realization",
            "new-source",
            "--json",
        ],
    )
    assert result.exit_code == 0, (result.output, result.exception)
    import json

    report = json.loads(result.stdout)
    assert report["documents"] == 1 and report["project"] == "new-project"
    with e.connect() as c:
        project = (
            c.execute(
                select(table("data.project")).where(
                    table("data.project").c.project_id == "new-project"
                )
            )
            .mappings()
            .one()
        )
        assert project["active_release_id"] is None and project["generation"] == 0
        source = (
            c.execute(
                select(table("kb.document")).where(
                    table("kb.document").c.project_id == "new-project"
                )
            )
            .mappings()
            .one()
        )
        assert source["source_uri"] == "toy/input.html" and source["meta"]["page"] == "input.html"


@pytest.mark.parametrize(
    "difference",
    [
        "dependencies",
        "project",
        "release",
        "revision",
        "configuration",
        "input",
        "unit",
        "packet",
        "self",
    ],
)
def test_native_role_cannot_forge_reuse_binding(
    semantic_db_engine, semantic_writer_engine, difference
):
    from sqlalchemy import update

    p = setup(semantic_db_engine)
    e = semantic_writer_engine
    method = SimpleNamespace(
        name="read", version="1", family="ingest", tier="deterministic", confidence_source=None
    )
    with e.begin() as c:
        origin_run = create_run(
            c,
            project_id="p",
            binding=OperationBinding(p.release_id, "z", 0, b"{}"),
            kind="full",
            options={},
            code_commit="test",
        )
        cfg = record_method(c, method, "default", {}, "config")
        origin = create_task(
            c, run_id=origin_run, config_id=cfg, stage="ingest", unit_type="run", input_hash="same"
        )
        claim_tasks(c, run_id=origin_run, config_id=cfg, holder="worker")
        complete_task(
            c,
            task_id=origin,
            attempt=1,
            holder="worker",
            prepared=p,
            observations=[],
            outcome="empty",
        )
    project, release, z, rev, deps = "p", p.release_id, "z", 0, b"{}"
    if difference == "dependencies":
        deps = b'{"policy":"changed"}'
    if difference in {"project", "release", "revision"}:
        with semantic_db_engine.begin() as c:
            if difference == "project":
                project, z = "other", "other-z"
                c.execute(insert(table("data.project")).values(project_id=project))
                c.execute(
                    insert(table("data.realization")).values(
                        realization_id=z, release_id=release, project_id=project
                    )
                )
            elif difference == "release":
                release, z = "release:other", "other-z"
                c.execute(
                    insert(table("sem.release")).values(
                        release_id=release,
                        content_digest="other",
                        profile="test",
                        prepared_bytes=b"{}",
                        manifest_bytes=b"{}",
                    )
                )
                c.execute(
                    insert(table("data.realization")).values(
                        realization_id=z, release_id=release, project_id=project
                    )
                )
            else:
                rev = 1
                c.execute(
                    update(table("data.realization"))
                    .where(table("data.realization").c.realization_id == z)
                    .values(data_revision=rev)
                )
    with e.begin() as c:
        run = create_run(
            c,
            project_id=project,
            binding=OperationBinding(release, z, rev, deps),
            kind="full",
            options={},
            code_commit="test",
        )
        if difference == "configuration":
            cfg = record_method(c, method, "other", {"other": True}, "other")
        target = create_task(
            c,
            run_id=run,
            config_id=cfg,
            stage="ingest",
            unit_type="run",
            input_hash="different" if difference in {"input", "self"} else "same",
            unit_key="different" if difference == "unit" else None,
            packet_hash="different" if difference == "packet" else None,
        )
    with pytest.raises(DBAPIError), e.begin() as c:
        c.execute(
            update(table("ops.task"))
            .where(table("ops.task").c.id == target)
            .values(status="reused", reused_task_id=target if difference == "self" else origin)
        )


def test_native_cut_cannot_be_reopened_or_grow_from_empty_task(
    semantic_db_engine, semantic_writer_engine
):
    from sqlalchemy import update

    p = setup(semantic_db_engine)
    e = semantic_writer_engine
    with e.begin() as c:
        run = create_run(
            c,
            project_id="p",
            binding=OperationBinding(p.release_id, "z", 0, b"{}"),
            kind="full",
            options={},
            code_commit="test",
        )
        cfg = record_method(
            c,
            SimpleNamespace(
                name="read",
                version="1",
                family="ingest",
                tier="deterministic",
                confidence_source=None,
            ),
            "default",
            {},
            "config",
        )
        task = create_task(
            c, run_id=run, config_id=cfg, stage="ingest", unit_type="run", input_hash="same"
        )
        claim_tasks(c, run_id=run, config_id=cfg, holder="worker")
        complete_task(
            c,
            task_id=task,
            attempt=1,
            holder="worker",
            prepared=p,
            observations=[],
            outcome="empty",
        )
        cut = seal_cut(c, run, "preview")
    with pytest.raises(DBAPIError, match="terminal source task is immutable"), e.begin() as c:
        c.execute(
            update(table("ops.task"))
            .where(table("ops.task").c.id == task)
            .values(status="running", attempt=2)
        )
    with pytest.raises(OperationConflict), e.begin() as c:
        complete_task(
            c,
            task_id=task,
            attempt=2,
            holder="worker",
            prepared=p,
            observations=[
                {
                    "payload_definition": "Report",
                    "item_key": "fake",
                    "payload": {"text": "invented"},
                    "kind": "reading",
                }
            ],
        )
    with e.begin() as c:
        assert cut_observations(c, cut) == []
        final = seal_cut(c, run, "final", final=True)
    with pytest.raises(DBAPIError), e.begin() as c:
        c.execute(
            update(table("ops.run"))
            .where(table("ops.run").c.id == run)
            .values(sealed=False, status="running")
        )
    with e.connect() as c:
        assert cut_observations(c, final) == []
        assert c.execute(
            select(table("ops.run").c.sealed).where(table("ops.run").c.id == run)
        ).scalar_one()


def test_logical_invocation_distinguishes_fresh_reports_but_not_retries(
    semantic_db_engine, semantic_writer_engine
):
    p = setup(semantic_db_engine)
    e = semantic_writer_engine
    method = SimpleNamespace(
        name="read", version="1", family="ingest", tier="deterministic", confidence_source=None
    )
    with e.begin() as c:
        run = create_run(
            c,
            project_id="p",
            binding=OperationBinding(p.release_id, "z", 0, b"{}"),
            kind="full",
            options={},
            code_commit="test",
        )
        cfg = record_method(c, method, "default", {}, "config")
        first = create_task(
            c, run_id=run, config_id=cfg, stage="ingest", unit_type="run", input_hash="same"
        )
        claim_tasks(c, run_id=run, config_id=cfg, holder="worker")
        rows = [
            {
                "payload_definition": "Report",
                "item_key": "1",
                "payload": {"text": "same"},
                "kind": "reading",
            }
        ]
        one = complete_task(
            c, task_id=first, attempt=1, holder="worker", prepared=p, observations=rows
        )
        assert (
            complete_task(
                c, task_id=first, attempt=1, holder="worker", prepared=p, observations=rows
            )
            .receipt == one.receipt
        )
        fresh = create_task(
            c,
            run_id=run,
            config_id=cfg,
            stage="ingest",
            unit_type="run",
            input_hash="same",
            fresh=True,
        )
        claim_tasks(c, run_id=run, config_id=cfg, holder="worker")
        two = complete_task(
            c, task_id=fresh, attempt=1, holder="worker", prepared=p, observations=rows
        )
        assert one != two
        keys = c.execute(select(table("kb.observation").c.observation_key)).scalars().all()
        assert len(set(keys)) == 2
        invocations = c.execute(select(table("ops.task").c.invocation_key)).scalars().all()
        assert len(set(invocations)) == 2


def test_native_cancel_drains_claims_and_blocks_late_completion(
    semantic_db_engine, semantic_writer_engine
):
    from corpus_structure.semantic.operations import end_source_run

    p = setup(semantic_db_engine)
    e = semantic_writer_engine
    with e.begin() as c:
        run = create_run(
            c,
            project_id="p",
            binding=OperationBinding(p.release_id, "z", 0, b"{}"),
            kind="full",
            options={},
            code_commit="test",
        )
        cfg = record_method(
            c,
            SimpleNamespace(
                name="read",
                version="1",
                family="ingest",
                tier="deterministic",
                confidence_source=None,
            ),
            "default",
            {},
            "config",
        )
        task = create_task(
            c, run_id=run, config_id=cfg, stage="ingest", unit_type="run", input_hash="same"
        )
        claim_tasks(c, run_id=run, config_id=cfg, holder="worker")
        assert end_source_run(c, run) == 1
        assert end_source_run(c, run) == 0
    with pytest.raises(OperationConflict), e.begin() as c:
        complete_task(
            c,
            task_id=task,
            attempt=1,
            holder="worker",
            prepared=p,
            observations=[],
            outcome="empty",
        )
    with e.connect() as c:
        assert c.execute(select(table("ops.task").c.status)).scalar_one() == "cancelled"
        assert not c.execute(select(table("kb.observation"))).first()


def test_lease_reclaim_keeps_invocation_and_refuses_stale_attempt(
    semantic_db_engine, semantic_writer_engine
):
    p = setup(semantic_db_engine)
    e = semantic_writer_engine
    t = table("ops.task")
    with e.begin() as c:
        run = create_run(
            c,
            project_id="p",
            binding=OperationBinding(p.release_id, "z", 0, b"{}"),
            kind="full",
            options={},
            code_commit="test",
        )
        cfg = record_method(
            c,
            SimpleNamespace(
                name="read",
                version="1",
                family="ingest",
                tier="deterministic",
                confidence_source=None,
            ),
            "default",
            {},
            "cfg",
        )
        task = create_task(
            c, run_id=run, config_id=cfg, stage="read", unit_type="run", input_hash="input"
        )
        first = claim_tasks(c, run_id=run, config_id=cfg, holder="first")[0]
        c.execute(
            t.update()
            .where(t.c.id == task)
            .values(lease_until=text("clock_timestamp()-interval '1 second'"))
        )
        second = claim_tasks(c, run_id=run, config_id=cfg, holder="second")[0]
        assert (
            second.attempt == first.attempt + 1
            and second.invocation_key == first.invocation_key
        )
    with pytest.raises(OperationConflict), e.begin() as c:
        complete_task(
            c,
            task_id=task,
            attempt=first.attempt,
            holder="first",
            prepared=p,
            observations=[],
            outcome="empty",
        )
    with e.begin() as c:
        complete_task(
            c,
            task_id=task,
            attempt=second.attempt,
            holder="second",
            prepared=p,
            observations=[],
            outcome="empty",
        )
