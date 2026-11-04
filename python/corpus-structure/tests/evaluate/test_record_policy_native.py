"""Native full-reading label controls; these do not establish fitted model quality."""

from copy import deepcopy

from semantic.conftest import semantic_db_engine as semantic_db_engine
from semantic.conftest import semantic_writer_engine as semantic_writer_engine
from semantic.test_private_records import candidate
from semantic.test_private_records import private_source as private_source
from sqlalchemy import text

from corpus_structure.semantic.identity import canonical_bytes


def test_native_whole_reading_labels_keep_meaning_and_source_occurrence(
    private_source, semantic_db_engine
):
    record = candidate(private_source)
    different = deepcopy(record)
    different["fields"][0]["value"]["lexical"] = "13"
    different["fields"][0]["original"] = "13"
    different_occurrence = candidate(private_source, cell=1)
    explanatory = deepcopy(record)
    explanatory["fields"][0]["reason"] = "independently inspected"
    evidence = deepcopy(record)
    evidence["fields"][0]["evidence_sets"] = ["another-set"]
    with semantic_db_engine.connect() as conn:

        def correct(prediction):
            return conn.execute(
                text(
                    "SELECT eval.record_policy_full_correct("
                    ":release,CAST(:candidate AS jsonb),CAST(:refs AS jsonb))"
                ),
                dict(
                    release=private_source.prepared.release_id,
                    candidate=canonical_bytes(prediction).decode(),
                    refs=canonical_bytes([record]).decode(),
                ),
            ).scalar_one()

        assert correct(record) is True
        assert correct(explanatory) is True
        assert correct(different) is False
        assert correct(different_occurrence) is False
        assert correct(evidence) is False


def test_native_comparison_projection_preserves_original_ids_and_exact_coordinates(
    private_source, semantic_db_engine
):
    """Comparison mechanics only; the protected caller authenticates these pin pairs."""
    from corpus_structure.evaluate.record_alignment import comparison_record
    from corpus_structure.semantic.record_contracts import (
        anchor_identity,
        evidence_set_identity,
        interpretation_identity,
        record_identity,
    )

    reference = candidate(private_source)
    prediction = deepcopy(reference)
    original_bytes = canonical_bytes(reference)
    pin = dict(reference["pin"], source="actual-successor-alias", source_view_id=927)
    prediction["pin"] = pin
    anchors = {}
    for anchor in prediction["anchors"]:
        old = anchor["anchor_id"]
        anchor["pin"] = pin
        anchor["anchor_id"] = anchor_identity(anchor)
        anchors[old] = anchor["anchor_id"]
    for field, evidence in zip(prediction["fields"], prediction["evidence_sets"], strict=True):
        evidence["anchors"] = [anchors[value] for value in evidence["anchors"]]
        evidence["set_id"] = evidence_set_identity(evidence)
        field["evidence_sets"] = [evidence["set_id"]]
    prediction["occurrence_anchors"] = [
        anchors[value] for value in prediction["occurrence_anchors"]
    ]
    prediction["record_id"] = record_identity("release:" + "9" * 64, prediction)
    prediction["interpretation_id"] = interpretation_identity(prediction)
    views = [
        {"reference_pin": reference["pin"], "prediction_pin": pin, "physical_digest": "d" * 64}
    ]
    assert reference["record_id"] != prediction["record_id"]
    with semantic_db_engine.connect() as conn:
        args = dict(
            release=private_source.prepared.release_id,
            candidate=canonical_bytes(prediction).decode(),
            refs=canonical_bytes([reference]).decode(),
            views=canonical_bytes(views).decode(),
        )
        statement = text(
            "SELECT eval.record_policy_full_correct(:release,CAST(:candidate AS jsonb),"
            "CAST(:refs AS jsonb),CAST(:views AS jsonb))"
        )
        assert conn.scalar(statement, args) is True
        normalized = conn.scalar(
            text(
                "SELECT eval.record_reference_comparison_record(CAST(:candidate AS jsonb),"
                "CAST(:views AS jsonb),'prediction')"
            ),
            args,
        )
        assert normalized == __import__("json").loads(
            canonical_bytes(comparison_record(prediction, views, "prediction"))
        )
        wrong = deepcopy(prediction)
        wrong["fields"][0]["value"]["lexical"] = "13"
        wrong["fields"][0]["original"] = "13"
        assert (
            conn.scalar(statement, dict(args, candidate=canonical_bytes(wrong).decode())) is False
        )
        other_occurrence = deepcopy(prediction)
        other_occurrence["occurrence_anchors"] = [other_occurrence["anchors"][0]["anchor_id"]]
        assert (
            conn.scalar(statement, dict(args, candidate=canonical_bytes(other_occurrence).decode()))
            is False
        )
    assert canonical_bytes(reference) == original_bytes
