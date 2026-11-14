"""Native full-reading label controls; these do not establish fitted model quality."""

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

import pytest
from semantic.native_record_fixtures import RecordSourceRecipe, candidate
from semantic.native_record_fixtures import private_record_release as private_record_release
from sqlalchemy import text

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.types import PreparedRelease


@dataclass(frozen=True)
class PolicyCandidateSource:
    prepared: PreparedRelease
    view_row: Mapping[str, Any]
    table: str


@pytest.fixture
def policy_record_source(private_record_release):
    # eval.record_policy_full_correct consumes the release artifact and supplied
    # candidate/reference values. Source custody is qualified by other native tests.
    return PolicyCandidateSource(
        private_record_release.prepared,
        MappingProxyType(
            dict(
                native_task_id=11,
                native_product_key="native",
                native_content_digest="a" * 64,
                projection_digest="b" * 64,
                recipe_digest="c" * 64,
                id=17,
            )
        ),
        "#/tables/0",
    )


@pytest.mark.parametrize(
    "private_record_release", [RecordSourceRecipe()], indirect=True, ids=("record-base",)
)
def test_native_whole_reading_labels_keep_meaning_and_source_occurrence(
    policy_record_source, commit_db_engine
):
    record = candidate(policy_record_source)
    different = deepcopy(record)
    different["fields"][0]["value"]["lexical"] = "13"
    different["fields"][0]["original"] = "13"
    different_occurrence = candidate(policy_record_source, cell=1)
    explanatory = deepcopy(record)
    explanatory["fields"][0]["reason"] = "independently inspected"
    evidence = deepcopy(record)
    evidence["fields"][0]["evidence_sets"] = ["another-set"]
    with commit_db_engine.connect() as conn:

        def correct(prediction):
            return conn.execute(
                text(
                    "SELECT eval.record_policy_full_correct("
                    ":release,CAST(:candidate AS jsonb),CAST(:refs AS jsonb))"
                ),
                dict(
                    release=policy_record_source.prepared.release_id,
                    candidate=canonical_bytes(prediction).decode(),
                    refs=canonical_bytes([record]).decode(),
                ),
            ).scalar_one()

        assert correct(record) is True
        assert correct(explanatory) is True
        assert correct(different) is False
        assert correct(different_occurrence) is False
        assert correct(evidence) is False


@pytest.mark.parametrize(
    "private_record_release", [RecordSourceRecipe()], indirect=True, ids=("record-base",)
)
def test_native_comparison_projection_preserves_original_ids_and_exact_coordinates(
    policy_record_source, commit_db_engine
):
    """Comparison mechanics only; the protected caller authenticates these pin pairs."""
    from corpus_structure.evaluate.record_alignment import comparison_record
    from corpus_structure.semantic.record_contracts import (
        anchor_identity,
        evidence_set_identity,
        interpretation_identity,
        record_identity,
    )

    reference = candidate(policy_record_source)
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
    with commit_db_engine.connect() as conn:
        args = dict(
            release=policy_record_source.prepared.release_id,
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
