"""Actual evaluator pass custody; controlled source, never model-quality evidence."""

import json
from dataclasses import asdict

import pytest
from evaluate.test_record_references_native import expected_reading
from evaluate.test_record_references_native import reference_source as reference_source
from semantic.conftest import semantic_db_engine as semantic_db_engine
from semantic.conftest import semantic_evaluator_engine as semantic_evaluator_engine
from semantic.conftest import semantic_writer_engine as semantic_writer_engine
from semantic.test_private_records import private_source as private_source
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
    review_export,
)
from corpus_structure.evaluate.record_references import assign_origin, source_binding
from corpus_structure.evaluate.semantic import split_documents
from corpus_structure.evaluate.split import SplitConfig
from corpus_structure.semantic.metadata import table


def freeze(conn, case, partition="development"):
    uri = conn.scalar(select(table("kb.document").c.source_uri).where(
        table("kb.document").c.id == case.view_row["document_id"]))
    assign_origin(conn, project_id="private-records", origin_group="operation-fixture-origin",
                  partition=partition, source_uris=(uri,), provenance={"source": "independent two-cell control"})
    split_documents(conn, "private-records", SplitConfig(forced_dev={uri: "controlled source"}),
                    release_id=case.prepared.release_id)
    logical = source_binding(conn, source_run_id=case.run, source_view_id=case.view, source_cut_id=case.cut)
    reading, old_frame = expected_reading(case, logical)
    frame = OperationEvaluationFrame(unit=old_frame.unit, release_id=old_frame.release_id,
        guideline_version="operation-guideline-1", rubric_version="cell-value-1", context_policy="native-source-only-1",
        operation_question="recover_returned_local_contributions", operation_version="retained-native-contributions-1",
        domain="scientific-source", direction="source_first", pin=old_frame.pin,
        anchor_ids=tuple(anchor["anchor_id"] for anchor in reading["anchors"]), anchor_scopes=old_frame.anchor_scopes)
    created = create_reference_set(conn, project_id="private-records", source_run_id=case.run,
        source_cut_id=case.cut, label="operation-source-only", legacy_split="dev",
        guideline=frame.guideline_version, guideline_text="Transcribe only independently selected source cell.",
        partition=partition, frames={frame.unit: frame}, sampling=dict(seed=1,
            strata={frame.unit: "body_cell"}, inclusion_probabilities={frame.unit: 1},
            provenance={"selection": "source-only controlled cell"}, cohort="native-controls"))
    units = table("eval.reference_unit")
    unit = conn.scalar(select(units.c.id).where(units.c.set_id == created["set_id"]))
    expected = OperationCase(case_id="cell-value", facet="value", anchor_ids=(frame.anchor_ids[0],),
        inspected_scope="controlled/table/cell-0", source_state="stated", judgment="supported",
        alternatives=({"value": {"kind": "text", "text": "12"}},),
        explanation="The source cell independently spells 12.", assessor_provenance={"assistance": "none"})
    payload = dict(protocol=PROTOCOL, release_id=frame.release_id, unit_ref=frame.unit,
        guideline=frame.guideline_version, rubric_version=frame.rubric_version, context_policy=frame.context_policy,
        operation_question=frame.operation_question, operation_version=frame.operation_version, domain=frame.domain,
        direction=frame.direction, reason="Controlled independent source-only pass", cases=[asdict(expected)],
        adjudication_passes=[])
    return created, unit, frame, payload


def test_native_source_only_passes_and_protected_inventory(reference_source, semantic_evaluator_engine):
    source = reference_source
    with semantic_evaluator_engine.begin() as conn:
        created, unit, frame, payload = freeze(conn, source)
        packet = author_packet(conn, unit)
        assert packet["native_contexts"]
        assert "contributions" not in packet and "authors" not in packet
        assert "contribution_ids" not in packet["source_frame"]["evaluation_frame"]
        a = record_pass(conn, unit_id=unit, pass_kind="A", actor="independent-A",
                        authored=json.dumps(payload).encode(), frame=frame)
        with pytest.raises(DBAPIError, match="independent"), conn.begin_nested():
            record_pass(conn, unit_id=unit, pass_kind="B", actor="independent-A",
                        authored=json.dumps(payload).encode(), frame=frame)
        b = record_pass(conn, unit_id=unit, pass_kind="B", actor="independent-B",
                        authored=json.dumps(payload).encode(), frame=frame)
        c_packet = adjudication_packet(conn, unit)
        assert c_packet["adjudication_passes"] == [a, b]
        payload["adjudication_passes"] = [a, b]
        record_pass(conn, unit_id=unit, pass_kind="C", actor="independent-C",
                    authored=json.dumps(payload).encode(), frame=frame)
        exported = review_export(conn, project_id="private-records", set_id=created["set_id"])
        assert exported["judgments_exposed"] and len(exported["judgments"]) == 1
    with source.writer.begin() as conn, pytest.raises(DBAPIError):
        conn.execute(text("SELECT authored FROM eval.reference_pass LIMIT 1"))


def test_heldout_review_export_retains_sealed_inventory_only(reference_source, semantic_evaluator_engine):
    source = reference_source
    with semantic_evaluator_engine.begin() as conn:
        created, unit, frame, payload = freeze(conn, source, "feature_fit")
        ids = []
        for kind in ("A", "B", "C"):
            payload["adjudication_passes"] = ids if kind == "C" else []
            identity = record_pass(conn, unit_id=unit, pass_kind=kind, actor=f"independent-{kind}",
                                   authored=json.dumps(payload).encode(), frame=frame)
            if kind != "C":
                ids.append(identity)
        exported = review_export(conn, project_id="private-records", set_id=created["set_id"])
        assert exported["inventory"][0]["adjudicated"]
        assert exported["judgments"] == [] and not exported["judgments_exposed"]
