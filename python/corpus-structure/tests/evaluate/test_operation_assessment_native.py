"""Actual evaluator pass custody; controlled source, never model-quality evidence."""

import json
from copy import deepcopy
from dataclasses import asdict
from typing import Any

import pytest
from semantic.conftest import semantic_db_engine as semantic_db_engine
from semantic.conftest import semantic_evaluator_engine as semantic_evaluator_engine
from semantic.conftest import semantic_writer_engine as semantic_writer_engine
from semantic.native_record_fixtures import private_source as private_source
from semantic.reference_scenarios import expected_reading
from semantic.reference_scenarios import private_source_options as private_source_options
from semantic.reference_scenarios import reference_source as reference_source
from semantic.test_method_dimensions_native import current_guarded_database
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.evaluate.operation_assessment import (
    PROTOCOL,
    OperationCase,
    OperationEvaluationFrame,
    adjudication_packet,
    author_packet,
    create_reference_set,
    record_pass,
    reference_evaluate,
    review_export,
)
from corpus_structure.evaluate.record_references import assign_origin, source_binding
from corpus_structure.evaluate.semantic import split_documents
from corpus_structure.evaluate.split import SplitConfig
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import seal_cut


def freeze(conn, case, partition="development", label="operation-source-only"):
    uri = conn.scalar(
        select(table("kb.document").c.source_uri).where(
            table("kb.document").c.id == case.view_row["document_id"]
        )
    )
    origins = table("eval.reference_origin_source")
    if (
        conn.scalar(
            select(origins.c.origin_group).where(
                origins.c.project_id == "private-records", origins.c.source_uri == uri
            )
        )
        is None
    ):
        assign_origin(
            conn,
            project_id="private-records",
            origin_group="operation-fixture-origin",
            partition=partition,
            source_uris=(uri,),
            provenance={"source": "independent two-cell control"},
        )
    splits = table("eval.document_split")
    if (
        conn.scalar(
            select(splits.c.id).where(
                splits.c.project_id == "private-records", splits.c.source_uri == uri
            )
        )
        is None
    ):
        split_documents(
            conn,
            "private-records",
            SplitConfig(forced_dev={uri: "controlled source"}),
            release_id=case.prepared.release_id,
        )
    logical = source_binding(
        conn, source_run_id=case.run, source_view_id=case.view, source_cut_id=case.cut
    )
    reading, old_frame = expected_reading(case, logical)
    frame = OperationEvaluationFrame(
        unit=old_frame.unit,
        release_id=old_frame.release_id,
        guideline_version="operation-guideline-1",
        rubric_version="cell-value-1",
        context_policy="native-source-only-1",
        operation_question="recover_returned_local_contributions",
        operation_version="retained-native-contributions-1",
        domain="scientific-source",
        direction="source_first",
        pin=old_frame.pin,
        anchor_ids=tuple(anchor["anchor_id"] for anchor in reading["anchors"]),
        anchor_scopes=old_frame.anchor_scopes,
    )
    created = create_reference_set(
        conn,
        project_id="private-records",
        source_run_id=case.run,
        source_cut_id=case.cut,
        label=label,
        legacy_split="dev",
        guideline=frame.guideline_version,
        guideline_text="Transcribe only independently selected source cell.",
        partition=partition,
        frames={frame.unit: frame},
        sampling=dict(
            seed=1,
            strata={frame.unit: "body_cell"},
            inclusion_probabilities={frame.unit: 1},
            provenance={"selection": "source-only controlled cell"},
            cohort="native-controls",
        ),
    )
    units = table("eval.reference_unit")
    unit = conn.scalar(select(units.c.id).where(units.c.set_id == created["set_id"]))
    expected = OperationCase(
        case_id="cell-value",
        facet="value",
        anchor_ids=(frame.anchor_ids[0],),
        inspected_scope="controlled/table/cell-0",
        source_state="stated",
        judgment="supported",
        alternatives=({"value": {"kind": "text", "text": "12"}},),
        explanation="The source cell independently spells 12.",
        assessor_provenance={"assistance": "none"},
    )
    payload = dict(
        protocol=PROTOCOL,
        release_id=frame.release_id,
        unit_ref=frame.unit,
        guideline=frame.guideline_version,
        rubric_version=frame.rubric_version,
        context_policy=frame.context_policy,
        operation_question=frame.operation_question,
        operation_version=frame.operation_version,
        domain=frame.domain,
        direction=frame.direction,
        reason="Controlled independent source-only pass",
        cases=[asdict(expected)],
        adjudication_passes=[],
    )
    return created, unit, frame, payload


def test_native_source_only_passes_and_protected_inventory(
    reference_source, semantic_evaluator_engine
):
    source = reference_source
    with semantic_evaluator_engine.begin() as conn:
        created, unit, frame, payload = freeze(conn, source)
        packet = author_packet(conn, unit)
        assert packet["native_contexts"]
        assert "contributions" not in packet and "authors" not in packet
        assert "contribution_ids" not in packet["source_frame"]["evaluation_frame"]
        a = record_pass(
            conn,
            unit_id=unit,
            pass_kind="A",
            actor="independent-A",
            authored=json.dumps(payload).encode(),
            frame=frame,
        )
        with pytest.raises(DBAPIError, match="independent"), conn.begin_nested():
            record_pass(
                conn,
                unit_id=unit,
                pass_kind="B",
                actor="independent-A",
                authored=json.dumps(payload).encode(),
                frame=frame,
            )
        b = record_pass(
            conn,
            unit_id=unit,
            pass_kind="B",
            actor="independent-B",
            authored=json.dumps(payload).encode(),
            frame=frame,
        )
        c_packet = adjudication_packet(conn, unit)
        assert c_packet["adjudication_passes"] == [a, b]
        payload["adjudication_passes"] = [a, b]
        record_pass(
            conn,
            unit_id=unit,
            pass_kind="C",
            actor="independent-C",
            authored=json.dumps(payload).encode(),
            frame=frame,
        )
        exported = review_export(conn, project_id="private-records", set_id=created["set_id"])
        assert exported["judgments_exposed"] and len(exported["judgments"]) == 1
    with source.writer.begin() as conn:
        final = seal_cut(conn, source.run, "operation-grade-final", final=True)
    consolidate_cut(source.writer, final, "operation-grade-output")
    with semantic_evaluator_engine.begin() as conn:
        graded = reference_evaluate(
            conn, project_id="private-records", run_id=source.run, set_id=created["set_id"]
        )
        assert graded.result["protocol"] == "source-operation-evaluation-1"
        assert graded.result["quality_claim"] == "not_established"
        assert graded.result["population_claim"] == "declared_cases_only"
        assert graded.result["units"][0]["cases"][0]["case_id"] == "cell-value"
        assert graded.result["units"][0]["cases"][0]["judgment"] == "unsupported"
        assert "comparisons" not in graded.result["units"][0]
        stored = conn.scalar(
            select(table("eval.reference_evaluation").c.result).where(
                table("eval.reference_evaluation").c.id == graded.id
            )
        )
        assert stored == graded.result
        statement = text(
            "SELECT eval.record_operation_reference_evaluation("
            "'private-records',:r,:s,CAST(:n AS jsonb),CAST(:v AS jsonb))"
        )

        def record(result, set_id=created["set_id"]):
            return conn.scalar(
                statement,
                dict(
                    r=source.run,
                    s=set_id,
                    n=canonical_bytes(graded.reference_snapshot).decode(),
                    v=canonical_bytes(result).decode(),
                ),
            )

        for protocol in ("source-record-evaluation-1", "scientific-evaluation-1", "unknown"):
            invalid = dict(graded.result, protocol=protocol)
            with pytest.raises(DBAPIError, match="trusted set protocol"), conn.begin_nested():
                record(invalid)
        invalid = deepcopy(graded.result)
        invalid["units"][0]["cases"] = []
        with pytest.raises(DBAPIError, match="misses selected source cases"), conn.begin_nested():
            record(invalid)
        # Report-supplied protocol cannot choose operation validation for another trusted set.
        for index, sampling in enumerate(
            (
                {},
                {"record_protocol": "source-record-reference-1"},
                {"operation_protocol": "source-operation-reference-999"},
            )
        ):
            foreign = conn.scalar(
                text(
                    "SELECT eval.create_reference_set('private-records',"
                    ":release,:run,:label,'dev','independent',"
                    "CAST(:sampling AS jsonb))"
                ),
                dict(
                    release=source.prepared.release_id,
                    run=source.run,
                    label=f"foreign protocol control {index}",
                    sampling=canonical_bytes(sampling).decode(),
                ),
            )
            invalid = dict(graded.result, set_id=foreign)
            with pytest.raises(DBAPIError, match="trusted set protocol"), conn.begin_nested():
                record(invalid, foreign)
        assert (
            conn.scalar(
                select(table("eval.reference_evaluation").c.id).where(
                    table("eval.reference_evaluation").c.set_id == created["set_id"]
                )
            )
            == graded.id
        )
    with source.writer.begin() as conn, pytest.raises(DBAPIError):
        conn.execute(text("SELECT authored FROM eval.reference_pass LIMIT 1"))


def test_heldout_review_export_retains_sealed_inventory_only(
    reference_source, semantic_evaluator_engine
):
    source = reference_source
    with semantic_evaluator_engine.begin() as conn:
        created, unit, frame, payload = freeze(conn, source, "feature_fit")
        ids = []
        for kind in ("A", "B", "C"):
            payload["adjudication_passes"] = ids if kind == "C" else []
            identity = record_pass(
                conn,
                unit_id=unit,
                pass_kind=kind,
                actor=f"independent-{kind}",
                authored=json.dumps(payload).encode(),
                frame=frame,
            )
            if kind != "C":
                ids.append(identity)
        exported = review_export(conn, project_id="private-records", set_id=created["set_id"])
        assert exported["inventory"][0]["adjudicated"]
        assert exported["judgments"] == [] and not exported["judgments_exposed"]


def test_native_conditional_proposal_endpoint_cases_preserve_kind_and_source_scope(
    reference_source, semantic_db_engine, semantic_evaluator_engine
):
    current_guarded_database(semantic_db_engine)
    source = reference_source
    with semantic_evaluator_engine.begin() as conn:
        _, unit, frame, payload = freeze(conn, source)
        expected: dict[str, Any] = payload["cases"][0]
        expected.update(
            facet="conditional_role",
            contribution_kind="proposal",
            anchor_endpoint_role="mention",
            candidate_selector={"semantic_type": "attribute.role"},
            alternatives=[
                {
                    "semantic_type": "attribute.role",
                    "value": {"kind": "text", "text": "defined_term"},
                    "endpoint_semantics": [
                        {
                            "role": "mention",
                            "anchor_ids": [frame.anchor_ids[0]],
                            "fields": {"source_pieces": ["12"]},
                        }
                    ],
                }
            ],
        )
        identity = record_pass(
            conn,
            unit_id=unit,
            pass_kind="A",
            actor="independent-conditional-A",
            authored=canonical_bytes(payload),
            frame=frame,
        )
        units = table("eval.reference_unit")
        frozen = conn.scalar(select(units.c.context).where(units.c.id == unit))[0]
        statement = text(
            "SELECT eval.record_operation_reference_pass("
            ":u,'B',:actor,:authored,CAST(:frame AS jsonb))"
        )
        # Bypass Python construction: the actual native boundary must reject
        # unsupported kinds and source anchors outside the independent frame.
        invalid_values: list[dict[str, Any]] = [
            dict(contribution_kind=kind) for kind in ("occurrence", "composite", "diagnostic")
        ]
        invalid_values.extend((dict(anchor_endpoint_role=""), dict(anchor_endpoint_role=True)))
        invalid_values.append(dict(anchor_ids=["not-in-frozen-source"]))
        for index, changed in enumerate(invalid_values):
            invalid = deepcopy(payload)
            invalid["cases"][0].update(changed)
            with (
                pytest.raises(DBAPIError, match="independent source/facet authority"),
                conn.begin_nested(),
            ):
                conn.scalar(
                    statement,
                    dict(
                        u=unit,
                        actor=f"invalid-conditional-{index}",
                        authored=canonical_bytes(invalid),
                        frame=canonical_bytes(frozen).decode(),
                    ),
                )
        items = table("eval.reference_item")
        stored = conn.scalar(select(items.c.payload).where(items.c.pass_id == identity))
        assert stored["contribution_kind"] == "proposal"
        assert stored["anchor_endpoint_role"] == "mention"
        assert stored["alternatives"][0]["endpoint_semantics"][0]["anchor_ids"] == [
            frame.anchor_ids[0]
        ]


@pytest.mark.parametrize("partition", ["final_event_calibration", "final_assessment"])
def test_sealed_access_control_fixture_history_has_no_labels(
    reference_source, semantic_evaluator_engine, partition
):
    """Controlled fixture labels test access only; no valid heldout quality follows."""
    from corpus_structure.evaluate.review_assessments import iter_assessment_review_rows

    source = reference_source
    with semantic_evaluator_engine.begin() as conn:
        created, unit, frame, payload = freeze(
            conn, source, partition, label="sealed-access-control-fixture-not-research-evidence"
        )
        ids = []
        for kind in ("A", "B", "C"):
            payload["adjudication_passes"] = ids if kind == "C" else []
            identity = record_pass(
                conn,
                unit_id=unit,
                pass_kind=kind,
                actor=f"sealed-access-control-fixture-{kind}",
                authored=json.dumps(payload).encode(),
                frame=frame,
            )
            if kind != "C":
                ids.append(identity)
        rows = list(
            iter_assessment_review_rows(
                conn, project_id="private-records", set_id=created["set_id"]
            )
        )
        assert {row["kind"] for row in rows} == {"set", "unit_inventory"}
        assert (
            next(row for row in rows if row["kind"] == "set")["value"]["judgments_exposed"] is False
        )
        assert all("authored_base64" not in row["value"] for row in rows)
    with source.writer.begin() as conn:
        with pytest.raises(DBAPIError) as refused, conn.begin_nested():
            list(
                iter_assessment_review_rows(
                    conn, project_id="private-records", set_id=created["set_id"]
                )
            )
        assert getattr(refused.value.orig, "sqlstate", None) == "42501"
