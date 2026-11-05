"""Actual native custody/authorization controls; no semantic-quality claim.

Fixture actor labels test native independence mechanics. They do not represent
independently authored judgments about the statistical sources.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.evaluate.review_assessments import iter_assessment_review_rows, record_review_exposure
from corpus_structure.evaluate.structural_assessment import (
    StructuralAuthoredReference, StructuralEvaluationFrame, StructuralReferenceCase,
    create_structural_reference_set, record_structural_reference_pass,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.regeneration import prepare_packs
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import StructuralInput
from corpus_structure.semantic.structural_sources import StructuralPassageSelection, prepare_structural_sources
from corpus_structure.settings import Settings


def refusal(conn, action):
    try:
        with conn.begin_nested():
            action()
    except DBAPIError as error:
        code = getattr(error.orig, "sqlstate", None)
        assert code in {"23514", "42501"}, (code, str(error))
        return code
    raise AssertionError("expected native refusal")


def main():
    settings = Settings()
    bundle, dependencies, profile, prepared = prepare_packs((Path("domains/statistics"),))
    print(json.dumps({"prepared_release_id": prepared.release_id}), flush=True)
    report = {"semantic_quality": "not_assessed", "release_id": prepared.release_id, "checks": {}}
    with open_runtime_engine(settings, "pce-native-assessment-install", purpose="admit") as engine:
        with engine.begin() as conn:
            persist_release(conn, bundle, dependencies, profile, prepared)
    with open_runtime_engine(settings, "pce-native-assessment-project", purpose="maintenance") as engine:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO data.project(project_id,generation) VALUES ('pce-statistics-structural',0) ON CONFLICT DO NOTHING"))
    selections = (
        StructuralPassageSelection(run_id=45, source_view_id=46, passage_id="control-grinstead", start=0, end=96, scope="native custody control"),
        StructuralPassageSelection(run_id=15, source_view_id=25, passage_id="control-forbes", start=0, end=96, scope="native custody control"),
        StructuralPassageSelection(run_id=13, source_view_id=32, passage_id="control-nist", start=0, end=96, scope="native custody control"),
    )
    with open_runtime_engine(settings, "pce-native-assessment-source", purpose="read") as engine:
        sources = prepare_structural_sources(engine, selections)
    frame = StructuralEvaluationFrame(
        inputs=StructuralInput(question="native custody exercise", scope="native control", inventory_id="control-three-source-1", policy_id="control-no-semantic-authority-1", sources=sources.sources, passages=sources.passages, dependencies=tuple(s.identity for s in sources.sources), coverage_limits=("native controls only; not statistical semantic assessment",)),
        operation="definition_applicability", direction="source_first", rubric_version="native-control-1",
        rubric_text="Controlled custody exercise. Actor labels are test fixture identities, not independent semantic authors.",
    )
    reference = StructuralAuthoredReference(frame_digest=frame.identity, cases=(StructuralReferenceCase(
        case_id="controlled-unassessed", facet="source_support", path=("definition",), expected=None,
        source_passages=tuple(p.passage_id for p in sources.passages), judgment="unassessed",
        explanation="This exercises native custody and makes no semantic-quality claim.",
    ),))
    authored = canonical_bytes(reference.model_dump(mode="json"))
    with open_runtime_engine(settings, "pce-native-assessment-evaluator", purpose="evaluate") as engine:
        with engine.begin() as conn:
            set_id = create_structural_reference_set(conn, project_id="pce-statistics-structural", release_id=prepared.release_id, frame=frame)
            a = record_structural_reference_pass(conn, set_id=set_id, pass_kind="A", actor="native-control-A", authored=authored)
            report["checks"]["same_actor_B"] = refusal(conn, lambda: record_structural_reference_pass(conn, set_id=set_id, pass_kind="B", actor="native-control-A", authored=authored))
            b = record_structural_reference_pass(conn, set_id=set_id, pass_kind="B", actor="native-control-B", authored=authored)
            report["checks"]["wrong_C_parents"] = refusal(conn, lambda: record_structural_reference_pass(conn, set_id=set_id, pass_kind="C", actor="native-control-C", authored=authored, parents=(b,a)))
            c = record_structural_reference_pass(conn, set_id=set_id, pass_kind="C", actor="native-control-C", authored=authored, parents=(a,b))
            receipt = record_review_exposure(conn, project_id="pce-statistics-structural", set_id=set_id, purpose="native controls", recipient_class="local evaluator", group=True)
            try:
                report["checks"]["uncommitted_exposure"] = refusal(conn, lambda: list(iter_assessment_review_rows(conn, project_id="pce-statistics-structural", set_id=set_id, exposure_receipt_id=receipt, group=True)))
            except AssertionError:
                report["checks"]["uncommitted_exposure"] = "failed: labels delivered before commit"
        with engine.begin() as conn:
            rows = list(iter_assessment_review_rows(conn, project_id="pce-statistics-structural", set_id=set_id, exposure_receipt_id=receipt, group=True))
            assert [r["value"]["pass_kind"] for r in rows if r["kind"] == "pass"] == ["A","B","C"]
            report["checks"]["committed_full_group_history"] = "passed"
            report.update(group_set_id=set_id, group_pass_ids=[a,b,c], exposure_receipt_id=receipt, group_history_rows=len(rows))
            dev = conn.execute(text("SELECT id,project_id FROM eval.reference_set WHERE id=18 AND sampling->>'partition'='feature_fit' AND sampling->>'operation_protocol'='source-operation-reference-1'")).mappings().one()
            dev_receipt = record_review_exposure(conn, project_id=dev["project_id"], set_id=dev["id"], purpose="native history controls", recipient_class="local evaluator", authorization_basis="Operator accepted PCE09: selected already-exposed PCE00-08 feature_fit cohort18; retained published development evidence.")
        with engine.begin() as conn:
            rows = list(iter_assessment_review_rows(conn, project_id=dev["project_id"], set_id=dev["id"], exposure_receipt_id=dev_receipt))
            kinds = {r["kind"] for r in rows}
            assert {"set","set_definition","unit","pass","frame","item"} <= kinds
            report["checks"]["original_operation_history"] = "passed"
            report.update(operation_set_id=dev["id"], operation_history_rows=len(rows), operation_receipt_id=dev_receipt)
            sealed = conn.execute(text("SELECT id,project_id FROM eval.reference_set WHERE sampling->>'partition' IN ('final_event_calibration','final_assessment') AND sampling->>'operation_protocol'='source-operation-reference-1' ORDER BY id DESC LIMIT 1")).mappings().first()
            if sealed:
                rows = list(iter_assessment_review_rows(conn, project_id=sealed["project_id"], set_id=sealed["id"]))
                assert all(r["kind"] in {"set", "unit_inventory"} for r in rows)
                report["checks"]["sealed_inventory_only"] = "passed"
            else:
                report["checks"]["sealed_inventory_only"] = "not_run: no selected sealed operation set"
    with open_runtime_engine(settings, "pce-native-assessment-producer", purpose="write") as engine:
        with engine.begin() as conn:
            report["checks"]["producer_history_denial"] = refusal(conn, lambda: list(iter_assessment_review_rows(conn, project_id="pce-statistics-structural", set_id=set_id, exposure_receipt_id=receipt, group=True)))
    report["defaults_activated"] = False
    report["outcome"] = "failed" if any(str(v).startswith("failed") for v in report["checks"].values()) else "passed"
    with Path(__file__).with_name("raw").joinpath(sys.argv[1] if len(sys.argv)>1 else "native-assessment-controls-001.json").open("x") as out:
        out.write(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
