"""Protected finite feature-fit authority over independently authored native cells.

These controls establish evaluator custody, not model quality or origin independence.
"""

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

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
from corpus_structure.semantic.record_contracts import (
    anchor_identity,
    evidence_set_identity,
    interpretation_identity,
    record_identity,
)
from corpus_structure.semantic.record_policy import FEATURES, FeatureInstance, RecordAlgorithm
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
        return reference_inputs(original_inputs(complete))

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
    records = []
    for cell in (0, 1):
        correct = source_fixture.candidate(case, cell)
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
