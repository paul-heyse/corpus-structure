"""Native run bindings, terminal fences and immutable consolidation cuts."""

from types import SimpleNamespace
from typing import Any

import psycopg
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


def setup(engine, *, observations=False, archive=False, composed=False, evaluation=False):
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
        import yaml

        from corpus_structure.semantic.metrics import METRIC_INPUT, observation_dependencies

        packaged = observation_dependencies(dependencies)
        declared = yaml.safe_load(
            next(a.content for a in packaged.artifacts if a.name == METRIC_INPUT)
        )
        declared["metrics"].append(
            dict(
                id="count",
                value_type="SourceNumberOrNull",
                subject_kind="run",
                detail_schema="SourceObject",
                description="Test method count",
            )
        )
        dependencies = observation_dependencies(dependencies, yaml.safe_dump(declared).encode())
    from corpus_structure.semantic.releases import persist_release
    from corpus_structure.semantic.types import PreparationProfile

    profile = PreparationProfile()
    if evaluation:
        from corpus_structure.semantic.analytical_profile import analytical_inputs
        from corpus_structure.semantic.domain_operations import domain_rule_inputs
        from corpus_structure.semantic.proposals import proposal_inputs

        dependencies = domain_rule_inputs(dependencies, b"rules: []\n")
        bundle = proposal_inputs(bundle, dependencies)
        bundle, dependencies = analytical_inputs(bundle, dependencies)
    if composed or evaluation:
        from corpus_structure.semantic.composed import composed_dependencies

        dependencies = composed_dependencies(dependencies)
        profile = PreparationProfile(version="semantic-2")
    p = prepare_release(bundle, dependencies, profile)
    with engine.begin() as c:
        persist_release(c, bundle, dependencies, profile, p)
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
            ).receipt
            == ids.receipt
        )
        pending = create_task(
            c, run_id=run, config_id=config, stage="ingest", unit_type="run", input_hash="late"
        )
        later = claim_tasks(c, run_id=run, config_id=config, holder="late")[0]
        failed = complete_task(
            c,
            task_id=pending,
            attempt=later.attempt,
            holder="late",
            prepared=p,
            observations=[],
            outcome="failed",
            error={"reason": "independent task failure"},
        )
        assert failed.receipt.protocol == "failed"
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
            mime="text/html",
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
    with e.connect() as c:
        assert read_original(c, doc) == b"<p>source</p>"


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

    class SourceConfig(BaseModel):
        pass

    p = setup(semantic_db_engine, observations=True, evaluation=True)
    e = semantic_writer_engine
    method = SimpleNamespace(
        name="read",
        version="1",
        family="ingest",
        tier="deterministic",
        confidence_source=None,
        unit_type=TaskUnitType.RUN,
        Config=SourceConfig,
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
            MeasurementDraft(
                metric="count",
                scope_type=MeasurementScope.RUN,
                value=3.5,
                detail={"flag": False, "text": "δ", "items": [1, None, 0.5]},
            ),
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
            ).receipt
            == ids.receipt
        )
        measured_rows = (
            c.execute(
                select(table("ops.measurement")).order_by(
                    table("ops.measurement").c.source_position
                )
            )
            .mappings()
            .all()
        )
        assert [row["source_position"] for row in measured_rows] == [0, 1, 2, 3]
        assert [row["value"] for row in measured_rows] == [2, 2, 3.5, None]
        assert measured_rows[2]["detail"] == {"flag": False, "text": "δ", "items": [1, None, 0.5]}
        for changes in (
            {},
            {"source_position": 0},
            {"metric": "undeclared"},
            {"run_id": run + 10000},
            {"detail": []},
        ):
            with pytest.raises(DBAPIError), c.begin_nested():
                forged: dict[str, Any] = dict(
                    run_id=run, task_id=task, metric="count", scope_type="run", value=2, detail={}
                )
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

    from corpus_structure.semantic.domain_operations import consolidate_cut
    from corpus_structure.semantic.query import read_session

    with e.connect().execution_options(isolation_level="SERIALIZABLE") as c, c.begin():
        cut = seal_cut(c, run, "measurement-final", final=True)
    consolidate_cut(e, cut, "measurement-output")
    with read_session(semantic_reader_engine, "measurement-output") as session:
        measurements = [m.model_dump(mode="python") for m in session.measurements("count")]
    assert len(measurements) == 4
    assert [m["source_position"] for m in measurements] == [0, 1, 2, 3]
    assert [source_python(m["value"]) for m in measurements] == [2, 2, 3.5, None]
    assert source_python(measurements[2]["detail"]) == {
        "flag": False,
        "text": "δ",
        "items": [1, None, 0.5],
    }
    measurement = measurements[0]
    assert measurement["metric"]["id"] == "count"
    assert measurement["subject"]["kind"] == "run"
    assert measurement["producer"]["run_id"] == run
    assert measurement["producer"]["task_id"] == task
    assert measurement["producer"]["method"] == "read"
    assert measurement["producer"]["operation_version"] == "1"
    assert source_python(measurement["value"]) == 2
    for statement in (
        "INSERT INTO "
        "ops.measurement(run_id,task_id,metric,scope_type,value,detail,source_position) "
        "VALUES(:run,:task,'count','run',2,'{}'::jsonb,4)",
        "UPDATE ops.measurement SET value=999 WHERE task_id=:task",
        "DELETE FROM ops.measurement WHERE task_id=:task",
    ):
        with pytest.raises(DBAPIError), e.begin() as c:
            c.execute(text(statement), {"run": run, "task": task})
    with read_session(semantic_reader_engine, "measurement-output") as session:
        assert [m.model_dump()["source_position"] for m in session.measurements("count")] == [
            0,
            1,
            2,
            3,
        ]
    import json

    malformed_values = (
        {"kind": "float", "hexadecimal": "NaN"},
        {
            "kind": "object",
            "fields": [
                {"name": "x", "position": 0, "value": {"kind": "null"}},
                {"name": "x", "position": 1, "value": {"kind": "integer", "integer": 2}},
            ],
        },
        {"kind": "object", "fields": [{"name": "x", "position": 4, "value": {"kind": "null"}}]},
    )
    with semantic_db_engine.connect() as c:
        for malformed in malformed_values:
            with pytest.raises(DBAPIError), c.begin_nested():
                c.execute(
                    text("SELECT ops.decode_source_value(CAST(:value AS jsonb))"),
                    {"value": json.dumps(malformed)},
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


def test_cli_initializes_pdf_source_project_without_active_pointer_changes(
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
    from pdf_acceptance_support import write_controlled_pdf

    write_controlled_pdf(corpus / "toy/input.pdf", ("Source",))
    registry = MethodRegistry(
        METHODS,
        MethodsFile(
            configs={
                "ingest.pdf": {"default": {"originals": ["toy/input.pdf"]}},
                "ingest.pdf_integrated": {"default": {"originals": ["toy/input.pdf"]}},
                "segment.sentences": {"default": {}},
                "profile.segments": {"default": {}},
            }
        ),
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
        assert source["source_uri"] == "toy/input.pdf" and source["mime"] == "application/pdf"
        assert source["meta"] == {
            "input_format": "pdf",
            "source_inventory": "configured-pdf-originals",
        }


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
                from corpus_structure.semantic.releases import persist_release
                from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies

                from .test_releases import source_bundle

                bundle = source_bundle(b"# independent other release\n")
                other = prepare_release(bundle, ResolvedDependencies())
                persist_release(c, bundle, ResolvedDependencies(), PreparationProfile(), other)
                release, z = other.release_id, "other-z"
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
    mutation = dict(status="reused", reused_task_id=target if difference == "self" else origin)
    with pytest.raises(DBAPIError) as denied, e.begin() as c:
        c.execute(
            update(table("ops.task")).where(table("ops.task").c.id == target).values(**mutation)
        )
    assert isinstance(denied.value.orig, psycopg.Error)
    assert denied.value.orig.sqlstate == "42501"
    # The independently invalid bound origin must also fail after reaching the native guard.
    with (
        pytest.raises(DBAPIError, match="reuse origin has another bound source context") as guarded,
        semantic_db_engine.begin() as c,
    ):
        c.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        c.execute(
            update(table("ops.task")).where(table("ops.task").c.id == target).values(**mutation)
        )
    assert isinstance(guarded.value.orig, psycopg.Error)
    assert guarded.value.orig.sqlstate == "P0001"
    with e.connect() as c:
        assert tuple(
            c.execute(
                select(table("ops.task").c.status, table("ops.task").c.reused_task_id).where(
                    table("ops.task").c.id == target
                )
            ).one()
        ) == ("pending", None)


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
    with pytest.raises(DBAPIError) as denied, e.begin() as c:
        c.execute(
            update(table("ops.task"))
            .where(table("ops.task").c.id == task)
            .values(status="running", attempt=2)
        )
    assert isinstance(denied.value.orig, psycopg.Error)
    assert denied.value.orig.sqlstate == "42501"
    with e.connect() as c:
        assert tuple(
            c.execute(
                select(table("ops.task").c.status, table("ops.task").c.attempt).where(
                    table("ops.task").c.id == task
                )
            ).one()
        ) == ("empty", 1)
    # Independently reach the lifecycle guard with an actor that can issue the invalid DML.
    with (
        pytest.raises(DBAPIError, match="terminal source task is immutable") as guarded,
        semantic_db_engine.begin() as c,
    ):
        c.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        c.execute(
            update(table("ops.task"))
            .where(table("ops.task").c.id == task)
            .values(status="running", attempt=2)
        )
    assert isinstance(guarded.value.orig, psycopg.Error)
    assert guarded.value.orig.sqlstate == "P0001"
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
    with pytest.raises(DBAPIError) as denied, e.begin() as c:
        c.execute(
            update(table("ops.run"))
            .where(table("ops.run").c.id == run)
            .values(sealed=False, status="running")
        )
    assert isinstance(denied.value.orig, psycopg.Error)
    assert denied.value.orig.sqlstate == "42501"
    with (
        pytest.raises(DBAPIError, match="sealed run cannot reopen") as guarded,
        semantic_db_engine.begin() as c,
    ):
        c.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        c.execute(
            update(table("ops.run"))
            .where(table("ops.run").c.id == run)
            .values(sealed=False, status="running")
        )
    assert isinstance(guarded.value.orig, psycopg.Error)
    assert guarded.value.orig.sqlstate == "P0001"
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
            ).receipt
            == one.receipt
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
    # Time expiry is fixture setup, not a write capability granted to the worker.
    with semantic_db_engine.begin() as c:
        c.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        c.execute(
            t.update()
            .where(t.c.id == task)
            .values(lease_until=text("clock_timestamp()-interval '1 second'"))
        )
    with e.begin() as c:
        second = claim_tasks(c, run_id=run, config_id=cfg, holder="second")[0]
        assert second.attempt == first.attempt + 1 and second.invocation_key == first.invocation_key
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
