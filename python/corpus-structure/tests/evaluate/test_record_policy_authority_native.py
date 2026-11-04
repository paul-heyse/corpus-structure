"""Protected finite feature-fit authority over independently authored native cells.

These controls establish evaluator custody, not model quality or origin independence.
"""

from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from importlib.resources import files
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml
from semantic import test_private_records as source_fixture
from semantic.conftest import semantic_db_engine as semantic_db_engine
from semantic.conftest import semantic_evaluator_engine as semantic_evaluator_engine
from semantic.conftest import semantic_writer_engine as semantic_writer_engine
from semantic.test_private_records import private_source as private_source
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.method import UnitRef, UnitResult
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.evaluate.record_policy import fit_record_policy
from corpus_structure.evaluate.record_references import (
    PROTOCOL,
    reference_evaluate,
    reference_inputs,
)
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import complete_unit_result, seal_cut
from corpus_structure.semantic.record_assertions import source_reading_inputs
from corpus_structure.semantic.record_contracts import (
    anchor_identity,
    evidence_set_identity,
    interpretation_identity,
    record_identity,
)
from corpus_structure.semantic.record_policy import (
    FEATURES,
    FeatureInstance,
    RecordAcceptanceInstance,
    RecordAlgorithm,
)
from corpus_structure.semantic.types import SourceArtifact, SourceBundle

from . import test_record_references_native as references

ALGORITHM = RecordAlgorithm(features=(FEATURES[0],), minimum_origin_groups=1)


def _second_reference(case, first):
    """The independent source fixture has two cells, both explicitly spelling 12."""
    row = deepcopy(first)
    for anchor in row["anchors"]:
        anchor["pointer"] = case.table + "/data/table_cells/1"
        anchor["anchor_id"] = anchor_identity(anchor)
    for evidence, anchor in zip(row["evidence_sets"], row["anchors"], strict=True):
        evidence["anchors"] = (anchor["anchor_id"],)
        evidence["set_id"] = evidence_set_identity(evidence)
    for field, evidence in zip(row["fields"], row["evidence_sets"], strict=True):
        field["evidence_sets"] = (evidence["set_id"],)
        if field["role"] == "location":
            field["value"]["pointer"] = case.table + "/data/table_cells/1"
    row["occurrence_anchors"] = (row["anchors"][1]["anchor_id"],)
    row["record_id"] = record_identity(case.prepared.release_id, row)
    row["interpretation_id"] = interpretation_identity(row)
    return row


def _pass(conn, unit, rows, frame, kind, parents=()):
    payload = dict(
        protocol=PROTOCOL,
        release_id=frame.release_id,
        unit_ref=frame.unit,
        guideline=frame.guideline_version,
        reference_policy_version=frame.reference_policy_version,
        prediction_policy_version=frame.prediction_policy_version,
        reason="Two explicit source cells both spell 12; complete location and literal support.",
        adjudication_passes=parents,
        records=rows,
    )
    return conn.scalar(
        text("SELECT eval.record_source_record_reference_pass(:u,:k,:a,:b,CAST(:f AS jsonb))"),
        dict(
            u=unit["id"],
            k=kind,
            a="controlled-independent-" + kind,
            b=canonical_bytes(payload),
            f=canonical_bytes(unit["context"][0]).decode(),
        ),
    )


def _four_candidates(case, source="private-unit"):
    records = []
    for cell in (0, 1):
        correct = source_fixture.candidate(case, cell)
        if source != "private-unit":
            pin = dict(correct["pin"], source=source)
            correct["pin"] = pin
            for anchor in correct["anchors"]:
                anchor["pin"] = pin
                anchor["anchor_id"] = anchor_identity(anchor)
            for field, evidence, anchor in zip(
                correct["fields"], correct["evidence_sets"], correct["anchors"], strict=True
            ):
                evidence["anchors"] = (anchor["anchor_id"],)
                evidence["set_id"] = evidence_set_identity(evidence)
                field["evidence_sets"] = (evidence["set_id"],)
            correct["occurrence_anchors"] = (correct["anchors"][1]["anchor_id"],)
            correct["record_id"] = record_identity(case.prepared.release_id, correct)
        correct["policy_version"] = ALGORITHM.version
        correct["computation_dependencies"] = ("native-group:cell-" + str(cell),)
        correct["interpretation_id"] = interpretation_identity(correct)
        wrong = deepcopy(correct)
        value = next(field for field in wrong["fields"] if field["role"] == "value")
        value.update(
            state="unresolved", reason="producer could not resolve the explicit cell value"
        )
        value.pop("value")
        value.pop("original")
        wrong["interpretation_id"] = interpretation_identity(wrong)
        records.extend((correct, wrong))
    return tuple(records)


@pytest.fixture
def policy_source(monkeypatch, request):
    original_inputs = source_fixture.observation_inputs

    def inputs(bundle):
        # Alignment owns a five-family contract. Reuse its actual other four families,
        # preserving the deliberately small two-cell table fixture as the fifth.
        document = yaml.safe_load(
            (Path(__file__).resolve().parents[4] / "domains/statistics/semantic.yaml").read_bytes()
        )
        document["classes"].pop("TableRecordFields")
        document["imports"] = ["core"]
        document["name"] = "statistics_policy_fixture"
        module = SourceArtifact("statistics_policy_fixture", yaml.safe_dump(document).encode())
        root = SourceArtifact(
            "policy-fixture-root",
            canonical_bytes(
                dict(
                    id="https://example/policy-fixture-root",
                    name="policy_fixture_root",
                    imports=[bundle.root, module.name],
                )
            ),
        )
        complete = SourceBundle(root.name, (*bundle.sources, module, root))
        return reference_inputs(source_reading_inputs(original_inputs(complete)))

    monkeypatch.setattr(source_fixture, "observation_inputs", inputs)
    original_namespace = source_fixture.SimpleNamespace

    def namespace(**values):
        if values.get("name") == "private.records":
            values.update(
                name="extract.m1_candidates", version="3", family="extract", tier="encoder"
            )
        return original_namespace(**values)

    monkeypatch.setattr(source_fixture, "SimpleNamespace", namespace)
    case = request.getfixturevalue("private_source")
    records = _four_candidates(case)
    with case.writer.begin() as conn:
        complete_unit_result(
            conn,
            task_id=case.task,
            attempt=case.held.attempt,
            holder="records",
            prepared=case.prepared,
            method=case.method,
            configuration_hash="private-config",
            source="private-unit",
            result=UnitResult(
                ref=UnitRef(TaskUnitType.SOURCE_VIEW, case.view, "private-unit"),
                outcome=ObservationOutcome.PRODUCED,
                records=tuple(records),
            ),
            records=tuple(records),
        )
        case.cut = seal_cut(conn, case.run, "policy-feature-frame", final=True)
    consolidate_cut(case.writer, case.cut, "policy-feature-result")
    original_expected = references.expected_reading

    def expected(case_, logical):
        row, frame = original_expected(case_, logical)
        other = _second_reference(case_, row)
        scope = tuple(
            {
                k: v
                for k, v in anchor.items()
                if k in {"pin", "space", "pointer", "precision", "start", "end"}
            }
            for anchor in other["anchors"]
        )
        return row, replace(
            frame,
            prediction_policy_version=ALGORITHM.version,
            anchor_scopes=frame.anchor_scopes + scope,
        )

    monkeypatch.setattr(references, "expected_reading", expected)
    original_origin = references.assign_origin

    def origin(conn, **values):
        if "heldout.pdf" in values["source_uris"]:
            values["origin_group"] = "controlled-heldout-original"
        return original_origin(conn, **values)

    monkeypatch.setattr(references, "assign_origin", origin)
    original_reference_set = references.create_reference_set

    def reference_set(conn, **values):
        values["label"] += ":" + values["partition"]
        return original_reference_set(conn, **values)

    monkeypatch.setattr(references, "create_reference_set", reference_set)
    return case


def test_feature_fit_is_protected_complete_frame_and_preserves_exact_parameters(
    policy_source, semantic_evaluator_engine
):
    case = policy_source
    with semantic_evaluator_engine.begin() as conn:
        created, unit, row, frame = references.create_case(conn, case, "feature_fit")
        refs = [row, _second_reference(case, row)]
        a = _pass(conn, unit, refs, frame, "A")
        b = _pass(conn, unit, refs, frame, "B")
        _pass(conn, unit, refs, frame, "C", (a, b))
        outcome = fit_record_policy(
            conn,
            project_id="private-records",
            run_id=case.run,
            set_id=created["set_id"],
            family="table",
            subset="controlled-cells",
            assumptions="One fixed controlled source; correlated alternatives are not independent.",
            algorithm=ALGORITHM,
        )
        assert outcome.report is not None, outcome.diagnostics
        product = outcome.report.result["policy_fit"]
        assert product["kind"] == "feature_fit"
        assert len(product["event_members"]) == 4
        assert sorted(member["correct"] for member in product["event_members"]) == [
            False,
            False,
            True,
            True,
        ]
        feature = FeatureInstance.model_validate_json(product["feature_canonical_json"])
        assert feature.digest == product["feature_instance_digest"]
        assert feature.parameters.coefficients[0] > 0
        assert feature.fit.negative_count == feature.fit.positive_count == 2
        assert feature.fit.declared_origin_group_count == 1
        assert feature.fit.standing == "fitted"
        stored = (
            conn.execute(
                select(table("eval.reference_evaluation")).where(
                    table("eval.reference_evaluation").c.id == outcome.report.id
                )
            )
            .mappings()
            .one()
        )
        assert stored["result"]["policy_fit"] == product
        assert stored["reference_snapshot"] == outcome.report.reference_snapshot
        assert product["feature_canonical_json"].encode() == canonical_bytes(
            product["feature_instance"]
        )
        with pytest.raises(DBAPIError) as partition_refusal, conn.begin_nested():
            conn.execute(
                text(
                    "SELECT eval.record_policy_prediction_frame("
                    ":p,:r,:s,'table','final_event_calibration')"
                ),
                dict(p="private-records", r=case.run, s=created["set_id"]),
            )
        assert getattr(partition_refusal.value.orig, "sqlstate", None) == "23514"
        changed = deepcopy(product)
        changed["event_members"][0]["correct"] = not changed["event_members"][0]["correct"]
        with pytest.raises(DBAPIError) as label_refusal, conn.begin_nested():
            reference_evaluate(
                conn,
                project_id="private-records",
                run_id=case.run,
                set_id=created["set_id"],
                policy_fit=changed,
            )
        assert getattr(label_refusal.value.orig, "sqlstate", None) == "23514"


def _heldout_source(case, directory):
    """Publish a second synthetic original through the existing native stage lifecycle."""
    from docling_core.types.doc import DoclingDocument, GroupLabel, TableCell, TableData
    from semantic.native_record_fixtures import publish_native_record_fixture

    from corpus_structure.core.method import SourceViewDraft
    from corpus_structure.ingest.pdf import PdfConversion, publication_payload
    from corpus_structure.ingest.pdf_hierarchy import snapshot
    from corpus_structure.semantic.operations import (
        OperationBinding,
        claim_tasks,
        complete_task,
        create_run,
        create_task,
        register_document,
    )
    from corpus_structure.semantic.pdf_contracts import prepare_pdf_product, store_pdf_original
    from corpus_structure.semantic.product_reference import ProductReference
    from corpus_structure.semantic.source_views import store_source_view

    original = b"%PDF-1.7\nheld-out synthetic source: two cells independently specified as 12"
    recipe = b'{"recipe":"controlled-heldout-native-1"}'
    document = DoclingDocument(name="Held-out controlled cells")
    section = document.add_group(label=GroupLabel.SECTION, name="Held-out measurements")
    native_table = document.add_table(
        parent=section,
        data=TableData(
            num_rows=1,
            num_cols=2,
            table_cells=[
                TableCell(
                    text="12",
                    start_row_offset_idx=0,
                    end_row_offset_idx=1,
                    start_col_offset_idx=index,
                    end_col_offset_idx=index + 1,
                )
                for index in (0, 1)
            ],
        ),
    )
    schema = (
        files("corpus_structure")
        .joinpath("model/semantic/docling-validation.schema.json")
        .read_bytes()
    )
    payload = publication_payload(
        PdfConversion(
            sha256(original).hexdigest(), recipe, snapshot(document), "success", (), (), (), None
        ),
        product_key="native",
        schema_digest=sha256(schema).hexdigest(),
        section_refs=frozenset((section.self_ref,)),
    )
    product = prepare_pdf_product(payload, original, schema, recipe)
    with case.writer.begin() as conn:
        run = create_run(
            conn,
            project_id="private-records",
            binding=OperationBinding(case.prepared.release_id, "private-input", 0, b"{}"),
            kind="full",
            options={},
            code_commit="controlled-heldout-source",
        )
        config = conn.scalar(
            select(table("ops.task").c.method_config_id).where(
                table("ops.task").c.id == case.source_task
            )
        )
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "heldout.pdf"
        path.write_bytes(original)
        doc_id = register_document(
            conn,
            project_id="private-records",
            source_uri="heldout.pdf",
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
            unit_id=doc_id,
            unit_key="heldout.pdf",
            input_hash=sha256(original).hexdigest(),
        )
        claim = claim_tasks(conn, run_id=run, config_id=config, holder="heldout-source")[0]
        store_pdf_original(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder="heldout-source",
            original=original,
            recipe_bytes=recipe,
        )
    published = publish_native_record_fixture(
        case.writer,
        directory / "native",
        task_id=task,
        attempt=claim.attempt,
        holder="heldout-source",
        product=product,
        document=document,
    )
    reference = ProductReference(task, "native", published.logical_digest)
    with case.writer.begin() as conn:
        draft = SourceViewDraft(
            "heldout-view",
            doc_id,
            reference,
            section.self_ref,
            "direct",
            "12\n12",
            (
                dict(
                    kind="native_text",
                    item_ref=native_table.self_ref,
                    source_field="cell_text",
                    cell_index=0,
                    start=0,
                    end=2,
                ),
                dict(kind="synthetic_separator", start=2, end=3),
                dict(
                    kind="native_text",
                    item_ref=native_table.self_ref,
                    source_field="cell_text",
                    cell_index=1,
                    start=3,
                    end=5,
                ),
            ),
            (section.self_ref, native_table.self_ref),
            (),
            dict(payload["health"], formula_outcomes=[]),
            b'{"view":"heldout-cells"}',
        )
        view = store_source_view(
            conn,
            run_id=run,
            task_id=task,
            attempt=claim.attempt,
            holder="heldout-source",
            draft=draft,
            position=0,
        )
        complete_task(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder="heldout-source",
            prepared=case.prepared,
            observations=[],
            outcome="empty",
        )
        row = dict(
            conn.execute(
                select(table("kb.source_view")).where(table("kb.source_view").c.id == view)
            )
            .mappings()
            .one()
        )
    return SimpleNamespace(
        prepared=case.prepared,
        writer=case.writer,
        run=run,
        view=view,
        source_task=task,
        view_row=row,
        table=native_table.self_ref,
        method=case.method,
        source="heldout-view",
        cut=None,
    )


def _resolved_cut(case, feature, *, binding=None, forged_score=False):
    """Use the real resolver over a sealed parent, then protected normal publication."""
    from corpus_structure.methods.m1_readings import M1ReadingConfig, M1Readings
    from corpus_structure.semantic.operations import (
        BoundReader,
        OperationBinding,
        claim_tasks,
        create_run,
        create_task,
        record_method,
    )
    from corpus_structure.semantic.proposals import native_source_frame
    from corpus_structure.semantic.source_contexts import NativeSourcePin

    if binding is not None:
        original_run = case.run
        with case.writer.begin() as conn:
            case.run = create_run(
                conn,
                project_id="private-records",
                binding=OperationBinding(
                    case.prepared.release_id,
                    "private-input",
                    0,
                    canonical_bytes(dict(record_acceptance=[binding])),
                ),
                kind="full",
                options={},
                code_commit="controlled-final-policy-consumer",
            )
            conn.execute(
                text("SELECT ops.select_source_view(:r,:s,:v)"),
                dict(r=case.run, s=original_run, v=case.view),
            )
    records = _four_candidates(case, case.source)
    with case.writer.begin() as conn:
        raw_config = record_method(
            conn, case.method, "default", {}, "private-config", prepared=case.prepared
        )
        raw_task = create_task(
            conn,
            run_id=case.run,
            config_id=raw_config,
            stage="extract",
            unit_type="source_view",
            unit_id=case.view,
            unit_key=case.source,
            input_hash="controlled-raw:" + str(case.run),
            fresh=True,
        )
        raw_claim = claim_tasks(
            conn, run_id=case.run, config_id=raw_config, holder="controlled-raw"
        )[0]
        reader = BoundReader(conn, case.run, case.prepared)
        view = reader.source_view(case.view)
        detail = dict(
            source_pin=NativeSourcePin.from_source(native_source_frame(view, ())).values(),
            reports=[],
        )
        complete_unit_result(
            conn,
            task_id=raw_task,
            attempt=raw_claim.attempt,
            holder="controlled-raw",
            prepared=case.prepared,
            method=case.method,
            configuration_hash="private-config",
            source=case.source,
            result=UnitResult(
                ref=UnitRef(TaskUnitType.SOURCE_VIEW, case.view, case.source),
                outcome=ObservationOutcome.PRODUCED,
                records=records,
                parse_detail=detail,
            ),
            records=records,
        )
        resolver = M1Readings()
        cfg = M1ReadingConfig(subset="controlled-cells", feature_instances=(feature,))
        parameters = cfg.model_dump(mode="json")
        config_hash = "controlled-resolver:" + feature.digest
        resolver_config = record_method(
            conn, resolver, "default", parameters, config_hash, prepared=case.prepared
        )
        ref = UnitRef(TaskUnitType.SOURCE_VIEW, case.view, case.source)
        unit = SimpleNamespace(ref=ref, run=SimpleNamespace(reader=reader))
        digest = resolver.input_digest(unit, cfg)
        task = create_task(
            conn,
            run_id=case.run,
            config_id=resolver_config,
            stage="assemble",
            unit_type="source_view",
            unit_id=case.view,
            unit_key=case.source,
            input_hash=sha256(digest.bytes).hexdigest(),
            fresh=True,
        )
        conn.execute(text("SELECT ops.add_source_task_dependency(:c,:p)"), dict(c=task, p=raw_task))
        claim = claim_tasks(
            conn, run_id=case.run, config_id=resolver_config, holder="controlled-resolver"
        )[0]
        result = resolver.run(
            (unit,), cfg, SimpleNamespace(reader=reader, check_active=lambda: None)
        )[0]
        if forged_score:
            forged_detail: dict[str, Any] = deepcopy(dict(result.parse_detail or {}))
            forged_detail["record_policy_events"][0]["final_event_score"] += 1.0
            result = replace(result, parse_detail=forged_detail)
        complete_unit_result(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder="controlled-resolver",
            prepared=case.prepared,
            method=resolver,
            configuration_hash=config_hash,
            source=case.source,
            result=result,
            records=result.records,
        )
        case.cut = seal_cut(conn, case.run, "controlled-resolved-cut", final=True)
    return consolidate_cut(case.writer, case.cut, "controlled-result:" + str(case.run))


def _adjudicated_case(conn, case, partition):
    created, unit, row, frame = references.create_case(conn, case, partition)
    records = [row, _second_reference(case, row)]
    a = _pass(conn, unit, records, frame, "A")
    b = _pass(conn, unit, records, frame, "B")
    _pass(conn, unit, records, frame, "C", (a, b))
    return created


def test_heldout_calibration_binding_and_native_whole_reading_admission(
    policy_source, semantic_evaluator_engine, tmp_path, semantic_db_engine
):
    training = policy_source
    with semantic_evaluator_engine.begin() as conn:
        created = _adjudicated_case(conn, training, "feature_fit")
        fitted = fit_record_policy(
            conn,
            project_id="private-records",
            run_id=training.run,
            set_id=created["set_id"],
            family="table",
            subset="controlled-cells",
            algorithm=ALGORITHM,
            assumptions="Controlled fixed synthetic training origin; no quality generalization.",
        )
        assert fitted.report is not None, fitted.diagnostics
        feature = FeatureInstance.model_validate_json(
            fitted.report.result["policy_fit"]["feature_canonical_json"]
        )
        feature_evaluation = fitted.report.id
    heldout = _heldout_source(training, tmp_path / "heldout")
    _resolved_cut(heldout, feature)
    with semantic_evaluator_engine.begin() as conn:
        calibration_set = _adjudicated_case(conn, heldout, "final_event_calibration")
        calibrated = fit_record_policy(
            conn,
            project_id="private-records",
            run_id=heldout.run,
            set_id=calibration_set["set_id"],
            family="table",
            subset="controlled-cells",
            feature_evaluation_id=feature_evaluation,
            threshold=0.5,
            assumptions=(
                "Second synthetic original, disjoint bytes and declared origin; machinery only."
            ),
        )
        assert calibrated.report is not None, calibrated.diagnostics
        product = calibrated.report.result["policy_fit"]
        assert len(product["event_members"]) == 4
        assert sorted(m["correct"] for m in product["event_members"]) == [False, False, True, True]
        instance = RecordAcceptanceInstance.model_validate_json(product["instance_canonical_json"])
        assert instance.feature.digest == feature.digest
        evaluation = table("eval.reference_evaluation")
        evaluation_digest = conn.scalar(
            select(evaluation.c.content_digest).where(evaluation.c.id == calibrated.report.id)
        )
        binding = dict(
            instance=product["acceptance_instance"],
            instance_digest=product["instance_digest"],
            instance_canonical_json=product["instance_canonical_json"],
            evaluation_id=calibrated.report.id,
            evaluation_digest=evaluation_digest,
        )
    with semantic_db_engine.connect() as conn:
        conn.execute(
            text("SELECT sem.require_record_policy_binding(:r,CAST(:b AS jsonb),true)"),
            dict(r=training.prepared.release_id, b=canonical_bytes(binding).decode()),
        )
        bad = deepcopy(binding)
        bad["evaluation_digest"] = "0" * 64
        with pytest.raises(DBAPIError) as refusal, conn.begin_nested():
            conn.execute(
                text("SELECT sem.require_record_policy_binding(:r,CAST(:b AS jsonb),true)"),
                dict(r=training.prepared.release_id, b=canonical_bytes(bad).decode()),
            )
        assert getattr(refusal.value.orig, "sqlstate", None) == "23514"
        altered = deepcopy(binding)
        altered["instance"]["threshold"] = 0.1
        encoded = canonical_bytes(altered["instance"])
        altered["instance_canonical_json"] = encoded.decode()
        altered["instance_digest"] = sha256(encoded).hexdigest()
        with pytest.raises(DBAPIError) as parameter_refusal, conn.begin_nested():
            conn.execute(
                text("SELECT sem.require_record_policy_binding(:r,CAST(:b AS jsonb),true)"),
                dict(r=training.prepared.release_id, b=canonical_bytes(altered).decode()),
            )
        assert getattr(parameter_refusal.value.orig, "sqlstate", None) == "23514"
    result = _resolved_cut(heldout, feature, binding=binding)
    with heldout.writer.connect() as conn:
        admission = table("data.record_admission")
        rows = (
            conn.execute(
                select(admission).where(admission.c.realization_id == result.realization_id)
            )
            .mappings()
            .all()
        )
        accepted = [row for row in rows if row["decision"] == "accepted"]
        assert len(accepted) == 2
        assert all(row["evaluation_id"] == calibrated.report.id for row in accepted)
        facts = {
            row.fact_id
            for row in conn.execute(
                select(table("data.record_assertion")).where(
                    table("data.record_assertion").c.realization_id == result.realization_id,
                    table("data.record_assertion").c.interpretation_id.in_(
                        [row["interpretation_id"] for row in accepted]
                    ),
                )
            )
        }
        selections = set(
            conn.scalars(
                select(table("data.selection").c.fact_id).where(
                    table("data.selection").c.realization_id == result.realization_id
                )
            )
        )
        assert len(facts) == 4 and selections == facts
    forged = _resolved_cut(heldout, feature, binding=binding, forged_score=True)
    with heldout.writer.connect() as conn:
        decisions = list(
            conn.scalars(
                select(table("data.record_admission").c.decision).where(
                    table("data.record_admission").c.realization_id == forged.realization_id
                )
            )
        )
        # Only the other correctly scored complete reading can be accepted.
        assert decisions.count("accepted") == 1
