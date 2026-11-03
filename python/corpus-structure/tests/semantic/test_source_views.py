"""Real native section custody, with independent source text and invalid selections."""

from dataclasses import asdict, replace
from hashlib import sha256
from importlib.resources import files
from types import SimpleNamespace

import pytest
from pydantic import create_model
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.method import SourceViewDraft
from corpus_structure.semantic.operation_results import MethodConfigId, RunId
from corpus_structure.semantic.operations import (
    BoundReader,
    OperationBinding,
    OperationConflict,
    claim_tasks,
    create_run,
    create_task,
    record_method,
    register_document,
)
from corpus_structure.semantic.pdf_contracts import (
    prepare_pdf_product,
    store_pdf_original,
)
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.source_views import (
    load_source_view,
    selected_source_views,
    store_native_source_frame,
    store_source_view,
)

from .native_record_fixtures import publish_native_record_fixture
from .operation_scenario_support import prepare_operation_scenario


def test_native_source_view_is_real_unit_with_exact_context(
    semantic_db_engine, semantic_writer_engine, tmp_path, monkeypatch
):
    from docling_core.types.doc import (
        BoundingBox,
        DocItemLabel,
        DoclingDocument,
        GroupLabel,
        PageItem,
        ProvenanceItem,
        Size,
        TableCell,
        TableData,
    )

    from corpus_structure.ingest.pdf import PdfConversion, publication_payload
    from corpus_structure.ingest.pdf_hierarchy import snapshot
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.proposals import native_source_frame

    prepared = prepare_operation_scenario(semantic_db_engine, observations=True, composed=True)
    original = b"%PDF-1.7\nindependent source view fixture"
    recipe = b'{"recipe":"native-scope-fixture"}'
    schema = (
        files("corpus_structure")
        .joinpath("model/semantic/docling-validation.schema.json")
        .read_bytes()
    )
    doc = DoclingDocument(name="Independent view")
    section = doc.add_group(label=GroupLabel.SECTION, name="Independent")
    paragraph = doc.add_text(
        label=DocItemLabel.TEXT,
        text="Independent source.",
        orig="Independent source.",
        parent=section,
    )
    formula = doc.add_formula(text="f(x)=x", orig="f(x)=x", parent=section)
    child = doc.add_group(label=GroupLabel.SECTION, name="Child", parent=section)
    child_formula = doc.add_formula(text="f(2)", orig="f(2)", parent=child)
    doc.pages[1] = PageItem(page_no=1, size=Size(width=200, height=300))
    box = BoundingBox(l=10, t=20, r=150, b=50, coord_origin="TOPLEFT")
    table = doc.add_table(
        data=TableData(
            num_rows=1,
            num_cols=1,
            table_cells=[
                TableCell(
                    text="Probability",
                    bbox=box,
                    start_row_offset_idx=0,
                    end_row_offset_idx=1,
                    start_col_offset_idx=0,
                    end_col_offset_idx=1,
                    column_header=True,
                )
            ],
        ),
        parent=child,
        prov=ProvenanceItem(page_no=1, bbox=box, charspan=(0, 0)),
    )
    from corpus_structure.ingest.pdf_health import FormulaOutcome

    conversion = PdfConversion(
        sha256(original).hexdigest(),
        recipe,
        snapshot(doc),
        "success",
        (),
        (
            FormulaOutcome(formula.self_ref, "succeeded"),
            FormulaOutcome(child_formula.self_ref, "succeeded"),
        ),
        (),
        None,
    )
    payload = publication_payload(
        conversion,
        product_key="native",
        schema_digest=sha256(schema).hexdigest(),
        section_refs=frozenset({section.self_ref, child.self_ref}),
    )
    coverage = [
        {
            "section_pointer": pointer,
            "membership": membership,
            "universe": universe,
            "outcome": "complete",
            "policy": policy,
        }
        for pointer, membership in ((section.self_ref, "descendants"), (child.self_ref, "direct"))
        for universe, policy in (
            ("display", "detected-native-display-v1"),
            ("inline", "native-font-token-vector-v2"),
            ("cell", "all-nonempty-selected-cells-v1"),
        )
    ]
    payload["recognition_coverage"] = coverage
    payload["cell_reports"] = [
        dict(
            table_pointer=table.self_ref,
            cell_index=0,
            page_no=1,
            classification="prose",
            basis="native-word-text",
            outcome="not_requested",
        )
    ]
    payload["runtime_report"] = {
        "packages": [{"name": "fixture", "version": "1"}],
        "bindings": [{"name": "fixture.provider", "value": "CPU"}],
        "effective_options": "{}",
        "confidence": "{}",
    }
    from corpus_structure.semantic.source_views import source_view_health

    product = prepare_pdf_product(payload, original, schema, recipe)
    with semantic_writer_engine.begin() as conn:
        run = create_run(
            conn,
            project_id="p",
            binding=OperationBinding(prepared.release_id, "z", 0, b"{}"),
            kind="full",
            options={},
            code_commit="source-view-test",
        )
        config = record_method(
            conn,
            SimpleNamespace(
                name="pdf.view-fixture",
                version="1",
                family="ingest",
                tier="deterministic",
                confidence_source=None,
                unit_type="document",
                Config=create_model("ViewFixture"),
            ),
            "default",
            {},
            "view-fixture",
        )
        path = tmp_path / "source.pdf"
        path.write_bytes(original)
        document = register_document(
            conn,
            project_id="p",
            source_uri="file:source-view-fixture",
            original_path=str(path),
            original=original,
            mime="application/pdf",
        )
        task = create_task(
            conn,
            run_id=run,
            config_id=config,
            stage="ingest",
            unit_type="document",
            unit_id=document,
            unit_key="view-source",
            input_hash=sha256(original).hexdigest(),
        )
        claim = claim_tasks(
            conn, run_id=RunId(run), config_id=MethodConfigId(config), holder="view-fixture"
        )[0]
        store_pdf_original(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder="view-fixture",
            original=original,
            recipe_bytes=recipe,
        )
    published = publish_native_record_fixture(
        semantic_writer_engine,
        tmp_path / "native-records",
        task_id=task,
        attempt=claim.attempt,
        holder="view-fixture",
        product=product,
        document=doc,
    )
    native_reference = ProductReference(task, "native", published.logical_digest)
    with semantic_writer_engine.begin() as conn:
        reader = BoundReader(conn, run, prepared)
        reader.bind_source_tasks({document: task})
        # No selected view or future-output input config exists yet. The current
        # task's immutable publication is the legitimate source for selection.
        assert selected_source_views(conn, run) == ()
        current = reader.native_document(native_reference, include_candidate_pages=False)
        assert current.original == original
        assert current.values()["document"]["name"] == doc.name
        drafts = reader.native_section_drafts(
            native_reference,
            document_id=document,
            selections=(),
            membership="descendants",
            scope=None,
            consumer_release=prepared.release_id,
        )
        assert drafts and all(item.native_product == native_reference for item in drafts)
        # A real, different document cannot be substituted for the producing unit.
        other_original = b"%PDF-1.7\nother actual document"
        other_path = tmp_path / "other.pdf"
        other_path.write_bytes(other_original)
        other = register_document(
            conn,
            project_id="p",
            source_uri="file:other-document",
            original_path=str(other_path),
            original=other_original,
            mime="application/pdf",
        )
        reader.bind_source_tasks({other: task})
        with pytest.raises(OperationConflict, match="exact claimed"):
            reader.native_document(native_reference)
        another_run = create_run(
            conn,
            project_id="p",
            binding=OperationBinding(prepared.release_id, "z", 0, b"{}"),
            kind="slice",
            options={},
            code_commit="other-source-custody",
        )
        another = create_task(
            conn,
            run_id=another_run,
            config_id=config,
            stage="ingest",
            unit_type="document",
            unit_id=document,
            unit_key="different-current-task",
            input_hash="different-task",
            fresh=True,
        )
        claim_tasks(
            conn, run_id=RunId(another_run), config_id=MethodConfigId(config), holder="other-owner"
        )
        reader = BoundReader(conn, another_run, prepared)
        reader.bind_source_tasks({document: another})
        with pytest.raises(OperationConflict, match="exact claimed"):
            reader.native_document(native_reference)
    with semantic_writer_engine.begin() as conn:
        draft = SourceViewDraft(
            "view-independent",
            document,
            native_reference,
            section.self_ref,
            "direct",
            "Independent source.\nf(x)=x",
            (
                {
                    "item_ref": paragraph.self_ref,
                    "start": 0,
                    "end": 19,
                    "kind": "native_text",
                    "source_field": "text",
                },
                {"start": 19, "end": 20, "kind": "synthetic_separator"},
                {
                    "item_ref": formula.self_ref,
                    "start": 20,
                    "end": 26,
                    "kind": "native_text",
                    "source_field": "text",
                },
            ),
            (section.self_ref, paragraph.self_ref, formula.self_ref),
            (),
            source_view_health(
                payload["health"],
                section.self_ref,
                "direct",
                tuple(
                    n.model_dump(mode="json", by_alias=True) for n in (section, paragraph, formula)
                ),
                (),
                recognition_coverage=coverage,
            ),
            b'{"recipe":"section-view-fixture"}',
        )
        identity = store_source_view(
            conn,
            run_id=run,
            task_id=task,
            attempt=claim.attempt,
            holder="view-fixture",
            draft=draft,
            position=0,
        )
        child_draft = SourceViewDraft(
            "view-child",
            document,
            native_reference,
            child.self_ref,
            "direct",
            "f(2)\nProbability",
            (
                {
                    "item_ref": child_formula.self_ref,
                    "start": 0,
                    "end": 4,
                    "kind": "native_text",
                    "source_field": "text",
                },
                {"start": 4, "end": 5, "kind": "synthetic_separator"},
                {
                    "item_ref": table.self_ref,
                    "start": 5,
                    "end": 16,
                    "kind": "native_text",
                    "source_field": "cell_text",
                    "cell_index": 0,
                },
            ),
            (child.self_ref, child_formula.self_ref, table.self_ref),
            (section.self_ref,),
            source_view_health(
                payload["health"],
                child.self_ref,
                "direct",
                tuple(
                    n.model_dump(mode="json", by_alias=True) for n in (child, child_formula, table)
                ),
                (section.self_ref,),
                recognition_coverage=coverage,
            ),
            b'{"recipe":"section-view-fixture"}',
        )
        child_identity = store_source_view(
            conn,
            run_id=run,
            task_id=task,
            attempt=claim.attempt,
            holder="view-fixture",
            draft=child_draft,
            position=1,
        )
        from corpus_structure.semantic.pdf_record_reader import published_record_reader

        record_reader = published_record_reader(conn, native_reference, projection_context=prepared)
        assert record_reader is not None
        assert list(record_reader.native_metadata("recognition_coverage")) == coverage
        reports = list(record_reader.native_metadata("cell_reports"))
        assert len(reports) == 1
        assert (reports[0]["classification"], reports[0]["outcome"]) == ("prose", "not_requested")
        assert list(record_reader.native_metadata("runtime_report")) == [payload["runtime_report"]]
        from copy import deepcopy

        bad = deepcopy(payload)
        bad["product_key"] = "bad-cell"
        bad["cell_reports"][0].update(
            classification="unknown", basis="unresolved-native-evidence", outcome="unknown"
        )
        from corpus_structure.semantic.pdf_contracts import validate_pdf_report_metadata

        with pytest.raises(ValueError, match="unresolved recognition/classification"):
            malformed = prepare_pdf_product(bad, original, schema, recipe)
            validate_pdf_report_metadata(malformed.values())
        assert selected_source_views(conn, run)[0].id == identity
        loaded = load_source_view(conn, identity)
        assert loaded.text == "Independent source.\nf(x)=x"
        assert (
            loaded.health["inline_coverage"] == "complete"
            and loaded.health["cell_coverage"] == "complete"
        )
        assert [i["self_ref"] for i in loaded.items] == [
            section.self_ref,
            paragraph.self_ref,
            formula.self_ref,
        ]
        with pytest.raises((ValueError, DBAPIError)), conn.begin_nested():
            store_source_view(
                conn,
                run_id=run,
                task_id=task,
                attempt=claim.attempt,
                holder="view-fixture",
                draft=replace(draft, key="wrong-membership", items=(paragraph.self_ref,)),
                position=1,
            )
        frame = native_source_frame(loaded, [("s1", 0, 19)])
        packet_hash = "a" * 64
        agent_config = record_method(
            conn,
            SimpleNamespace(
                name="native.packet-fixture",
                version="1",
                family="agent",
                tier="agent",
                confidence_source=None,
                unit_type="source_view",
                Config=create_model("NativePacketFixture"),
            ),
            "default",
            {},
            "native-packet-fixture",
        )
        agent_task = create_task(
            conn,
            run_id=run,
            config_id=agent_config,
            stage="agent",
            unit_type="source_view",
            unit_id=identity,
            unit_key=draft.key,
            input_hash="packet-input",
            packet_hash=packet_hash,
            agent=True,
        )
        missing = asdict(frame)
        missing["sentences"] = tuple(
            row for row in missing["sentences"] if not row["id"].startswith("native_evidence:")
        )
        with pytest.raises(DBAPIError, match="alias inventory is incomplete"), conn.begin_nested():
            store_native_source_frame(
                conn, task_id=agent_task, packet_hash=packet_hash, frame=missing
            )
        mismatched = asdict(frame)
        next(row for row in mismatched["sentences"] if row["id"] == "native_evidence:0")["end"] = 1
        with pytest.raises(DBAPIError, match="exact retained piece"), conn.begin_nested():
            store_native_source_frame(
                conn, task_id=agent_task, packet_hash=packet_hash, frame=mismatched
            )
        store_native_source_frame(
            conn, task_id=agent_task, packet_hash=packet_hash, frame=asdict(frame)
        )
        assert (
            conn.execute(
                text("SELECT count(*) FROM ops.native_source_frame_sentence WHERE task_id=:task"),
                {"task": agent_task},
            ).scalar_one()
            == 3
        )
        invalid = asdict(frame)
        invalid["native_context"] = canonical_bytes(dict(loaded.context(), items=[])).decode()
        with pytest.raises(DBAPIError), conn.begin_nested():
            store_native_source_frame(
                conn, task_id=agent_task, packet_hash=packet_hash, frame=invalid
            )
        assert conn.scalar(text("SELECT to_regclass('ops.rendition_build')")) is None
        from corpus_structure.semantic.proposals import native_frame_source
        from corpus_structure.semantic.source_views import load_native_source_frames

        child_loaded = load_source_view(conn, child_identity)
        child_frame = replace(
            native_source_frame(child_loaded, [("s1", 0, 4)]),
            context_sources=(native_frame_source(frame),),
        )
        child_agent = create_task(
            conn,
            run_id=run,
            config_id=agent_config,
            stage="agent",
            unit_type="source_view",
            unit_id=child_identity,
            unit_key=child_draft.key,
            input_hash="child-packet",
            packet_hash=packet_hash,
            agent=True,
        )
        store_native_source_frame(
            conn, task_id=child_agent, packet_hash=packet_hash, frame=asdict(child_frame)
        )
        handle = f"native_context:{identity}:native_evidence:2"
        saved = conn.execute(
            text(
                "SELECT source_view_id,start_offset,end_offset FROM "
                "ops.native_source_frame_sentence WHERE task_id=:task AND "
                "sentence_id=:handle"
            ),
            dict(task=child_agent, handle=handle),
        ).one()
        assert tuple(saved) == (
            identity,
            20,
            26,
        )  # Parent offsets exceed the entire child projection.
        assert (
            load_native_source_frames(conn, [agent_task, child_agent])[child_agent] == child_frame
        )
        wrong = asdict(frame)
        wrong["context_sources"] = (
            asdict(native_frame_source(native_source_frame(child_loaded, [("s1", 0, 4)]))),
        )
        with pytest.raises(DBAPIError, match="direct ancestor"), conn.begin_nested():
            store_native_source_frame(
                conn, task_id=agent_task, packet_hash=packet_hash, frame=wrong
            )

    with semantic_db_engine.begin() as conn:
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        assert (
            conn.execute(
                text("SELECT ops.native_source_statement_source_key(:task,:handle)"),
                dict(task=child_agent, handle=handle),
            ).scalar_one()
            == draft.key
        )

    # An archived native product is adopted only by an exact declared, claimed input.
    with semantic_writer_engine.begin() as conn:
        adopted = create_run(
            conn,
            project_id="p",
            binding=OperationBinding(prepared.release_id, "z", 0, b"{}"),
            kind="slice",
            options={
                "scope": {
                    "kind": "native_sections",
                    "sections": ["Independent"],
                    "include_descendants": True,
                }
            },
            code_commit="native-adoption-fixture",
        )
        adoption_model = create_model("AdoptionFixture", native_product=(ProductReference, ...))
        adoption = SimpleNamespace(
            name="pdf.adoption-fixture",
            version="1",
            family="ingest",
            tier="deterministic",
            confidence_source=None,
            unit_type="document",
            Config=adoption_model,
        )
        params = {"native_product": loaded.ref.native_product.values()}
        config_id = record_method(
            conn, adoption, "input", params, "adoption-fixture", prepared=prepared
        )
        adoption_task = create_task(
            conn,
            run_id=adopted,
            config_id=config_id,
            stage="ingest",
            unit_type="document",
            unit_id=document,
            unit_key="adopted-original",
            input_hash="adopted-source",
        )
        claim_tasks(
            conn, run_id=RunId(adopted), config_id=MethodConfigId(config_id), holder="adopter"
        )
        reader = BoundReader(conn, adopted, prepared)
        with pytest.raises(OperationConflict):
            reader.native_document(loaded.ref.native_product)
        reader.bind_source_tasks({document: adoption_task})
        archived = reader.native_document(loaded.ref.native_product)
        assert loaded.ref.native_product == native_reference
        assert archived.original == original
        assert (
            DoclingDocument.model_validate(archived.values()["document"]).export_to_dict()
            == product.values()["document"]
        )

    from corpus_structure.semantic.native_requests import request_source_view

    lexical = request_source_view(
        semantic_writer_engine,
        source_run_id=run,
        source_view_id=identity,
        demand="lexical",
        pointer=formula.self_ref,
        code_commit="request-fixture",
    )
    assert lexical.status == "source_ready"
    assert lexical.result is not None
    assert lexical.result["items"][0]["recognized_latex"] == "f(x)=x"
    assert lexical.result["items"][0]["lexical"]
    from corpus_structure.methods.math import native

    def forbidden(*args, **kwargs):
        raise AssertionError("reused native request must not execute its kernel")

    with monkeypatch.context() as patch:
        patch.setattr(native, "native_request_analysis", forbidden)
        repeated = request_source_view(
            semantic_writer_engine,
            source_run_id=run,
            source_view_id=identity,
            demand="lexical",
            pointer=formula.self_ref,
            code_commit="request-fixture",
        )
    assert repeated.status == "source_ready" and repeated.result == lexical.result
    # Parent roles are retained source products. Strong requests hydrate these exact
    # records, while weak requests must never invoke parent context preparation.
    from corpus_structure.core.method import CoverageDraft, ObservationDraft, UnitRef, UnitResult
    from corpus_structure.core.vocab import ObservationKind, ObservationOutcome, TaskUnitType
    from corpus_structure.semantic.operations import OperationDescriptor, complete_unit_result

    parent_method = OperationDescriptor(
        "resolve.symbol_scope",
        "4",
        "resolve",
        "deterministic",
        TaskUnitType.SOURCE_VIEW,
        create_model("ParentContextFixture"),
    )
    with semantic_writer_engine.begin() as conn:
        parent_config = record_method(
            conn, parent_method, "context", {}, "context-fixture", prepared=prepared
        )
        parent_task = create_task(
            conn,
            run_id=run,
            config_id=parent_config,
            stage="scope",
            unit_type="source_view",
            unit_id=identity,
            unit_key=loaded.ref.key,
            input_hash="parent-context-fixture",
        )
        parent_claim = claim_tasks(
            conn,
            run_id=RunId(run),
            config_id=MethodConfigId(parent_config),
            holder="context-fixture",
        )[0]
        parent_payload = native.NativeContextPayload(
            source_view_id=identity,
            native_product=loaded.ref.native_product.values(),
            projection_digest=loaded.ref.projection_digest,
            declarations=(
                native.NativeContextDeclaration(
                    symbol="f",
                    role="function",
                    rule_id="function-definition-1",
                    source_pointer=formula.self_ref,
                    recognized_start=0,
                    recognized_end=1,
                    scope_pointer=section.self_ref,
                    quote="f(x)=x",
                    projection_start=20,
                    projection_end=26,
                ),
            ),
            issues=(),
        )
        parent_result = UnitResult(
            ref=UnitRef(TaskUnitType.SOURCE_VIEW, identity, loaded.ref.key),
            outcome=ObservationOutcome.PRODUCED,
            observations=(
                ObservationDraft(
                    kind=ObservationKind.RECORD,
                    payload=parent_payload,
                    payload_class=native.NativeContextPayload,
                    payload_version="1",
                    source_view_id=identity,
                ),
            ),
            coverage=(
                CoverageDraft(
                    family="resolve.symbol_scope",
                    scope=loaded.ref.key,
                    outcome="complete",
                    required_capability="context_declarations",
                ),
            ),
        )
        complete_unit_result(
            conn,
            task_id=parent_task,
            attempt=parent_claim.attempt,
            holder="context-fixture",
            prepared=prepared,
            result=parent_result,
            method=parent_method,
            configuration_hash="context-fixture",
            source=loaded.ref.key,
        )
    with monkeypatch.context() as patch:
        patch.setattr(native, "native_ancestor_declarations", forbidden)
        patch.setattr(native, "stored_native_ancestor_declarations", forbidden)
        child_weak = request_source_view(
            semantic_writer_engine,
            source_run_id=run,
            source_view_id=child_identity,
            demand="lexical",
            pointer=child_formula.self_ref,
            code_commit="request-fixture",
        )
        assert child_weak.status == "source_ready"
    with monkeypatch.context() as patch:
        patch.setattr(native, "native_ancestor_declarations", forbidden)
        child_strong = request_source_view(
            semantic_writer_engine,
            source_run_id=run,
            source_view_id=child_identity,
            demand="interpretation",
            pointer=child_formula.self_ref,
            code_commit="request-fixture",
        )
    assert child_strong.result is not None
    declarations = child_strong.result["items"][0]["context"]["declarations"]
    assert any(
        d["symbol"] == "f"
        and d["role"] == "function"
        and "preparation_observation" in d["evidence"]
        for d in declarations
    )
    with semantic_writer_engine.connect() as conn:
        params = conn.execute(
            text(
                "SELECT c.params FROM ops.task t JOIN ops.method_config c ON "
                "c.id=t.method_config_id WHERE t.id=:task"
            ),
            {"task": child_strong.task_id},
        ).scalar_one()
        import json

        basis = json.loads(params["ancestor_context"])
        assert basis["observations"][0]["source_view_id"] == identity
        assert basis["observations"][0]["payload_hash"]
    calls = []

    def timed_out(*args, **kwargs):
        calls.append(1)
        return native.NativeAnalysisPayload(
            source_view_id=identity,
            native_product=loaded.ref.native_product.values(),
            projection_digest=loaded.ref.projection_digest,
            recipe_digest=loaded.ref.recipe_digest,
            demand="syntax",
            items=(
                {
                    "pointer": formula.self_ref,
                    "failure": {"category": "timeout"},
                    "stages": {"syntax": {"work": "failed", "diagnostic": "budget exhausted"}},
                },
            ),
        )

    with monkeypatch.context() as patch:
        patch.setattr(native, "native_request_analysis", timed_out)
        for _ in range(2):
            failed = request_source_view(
                semantic_writer_engine,
                source_run_id=run,
                source_view_id=identity,
                demand="syntax",
                pointer=formula.self_ref,
                seconds=0.01,
                code_commit="request-fixture",
            )
            assert failed.result is not None
            assert (
                failed.status == "failed"
                and failed.cut_id is None
                and failed.result["items"][0]["failure"]["category"] == "timeout"
            )
            with semantic_writer_engine.connect() as conn:
                assert (
                    conn.execute(
                        text("SELECT status FROM ops.task WHERE id=:task"), {"task": failed.task_id}
                    ).scalar_one()
                    == "failed"
                )
    assert len(calls) == 2


@pytest.mark.parametrize("seconds", [float("inf"), float("-inf"), float("nan"), 0, -1])
def test_native_request_budget_is_finite_and_positive(seconds):
    from corpus_structure.semantic.native_requests import NativeRequestLimits

    with pytest.raises(ValueError):
        NativeRequestLimits(seconds=seconds)


def test_source_view_health_is_relative_to_its_named_native_universe():
    from corpus_structure.semantic.source_views import source_view_health

    group = {"self_ref": "#/groups/0", "label": "section"}
    formula = {"self_ref": "#/texts/0", "label": "formula", "parent": {"$ref": "#/groups/0"}}
    health = {
        "conversion": "success",
        "display_coverage": "partial",
        "inline_coverage": "complete",
        "cell_coverage": "complete",
        "inline_scope": ["#/groups/0"],
        "cell_scope": ["#/groups/0"],
        "inline_membership": "direct",
        "cell_membership": "direct",
        "formula_outcomes": [
            {"pointer": "#/texts/0", "outcome": "succeeded"},
            {"pointer": "#/texts/1", "outcome": "failed"},
        ],
    }
    local = source_view_health(health, "#/groups/0", "direct", (group, formula), ())
    assert (
        local["display_coverage"] == "complete"
        and local["inline_coverage"] == "complete"
        and local["cell_coverage"] == "complete"
    )
    assert local["formula_outcomes"] == [{"pointer": "#/texts/0", "outcome": "succeeded"}]
    child = {"self_ref": "#/groups/1", "label": "section"}
    outside = source_view_health(health, "#/groups/1", "direct", (child,), ("#/groups/0",))
    assert outside["inline_coverage"] == "unknown" and outside["cell_coverage"] == "unknown"
    strong = source_view_health(
        dict(health, inline_membership="descendants", cell_membership="descendants"),
        "#/groups/1",
        "direct",
        (child,),
        ("#/groups/0",),
    )
    assert strong["inline_coverage"] == "complete" and strong["cell_coverage"] == "complete"
    unqualified = source_view_health(
        dict(health, inline_scope=[], cell_scope=[]), "#/groups/0", "direct", (group, formula), ()
    )
    assert unqualified["inline_coverage"] == "unknown" and unqualified["cell_coverage"] == "unknown"
