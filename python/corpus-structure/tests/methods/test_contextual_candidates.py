"""Independent source/role criteria for the actual current occurrence projection."""

from typing import Any
import pytest
from corpus_structure.methods.contextual_candidates import retained_occurrences
from corpus_structure.semantic.contributions import contribution_identity, occurrence_identity
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.record_contracts import anchor_identity

from methods.contextual_query_support import source

PIN = source("Mean is average.").pin.values()


def located(role="term", start=0, end=4) -> dict[str, Any]:
    anchor = dict(
        pin=PIN,
        space="native",
        pointer="#/texts/1",
        precision="exact",
        start=start,
        end=end,
        source_piece="Mean is average."[start:end],
    )
    anchor["anchor_id"] = anchor_identity(anchor)
    row = dict(
        kind="occurrence",
        semantic_type="source_rule." + role,
        operation_key="producer-op",
        item_key=role,
        pin=PIN,
        anchors=(anchor,),
        occurrence_id=occurrence_identity((anchor,)),
    )
    row["contribution_id"] = contribution_identity(row)
    return row


def test_actual_roles_preserved_with_one_physical_query_context():
    a, b = located(), located("expression")
    rows, contexts, coordinates = retained_occurrences(
        {"contributions": (a, b)}, {"#/texts/1": {"text": "Mean is average."}}, PIN, "new-op"
    )
    assert len(rows) == 2 and len(contexts) == 1
    assert rows[0]["contribution_id"] != rows[1]["contribution_id"]
    assert rows[0]["occurrence_id"] == rows[1]["occurrence_id"]
    assert {source_python(row["value"])["producer_semantic_type"] for row in rows} == {
        "source_rule.term",
        "source_rule.expression",
    }
    assert coordinates[0]["text"] == "Mean is average."


def test_actual_occurrence_cannot_invent_source_extent():
    row = located()
    row["anchors"][0]["source_piece"] = "wrong"
    with pytest.raises(ValueError, match="slice"):
        retained_occurrences(
            {"contributions": (row,)}, {"#/texts/1": {"text": "Mean is average."}}, PIN, "new-op"
        )


def test_coarse_native_occurrence_is_retained_without_an_encoder_span():
    row = located()
    anchor = row["anchors"][0]
    anchor.pop("start")
    anchor.pop("end")
    anchor.pop("source_piece")
    anchor["precision"] = "item"
    anchor["anchor_id"] = anchor_identity(anchor)
    row["occurrence_id"] = occurrence_identity((anchor,))
    row["contribution_id"] = contribution_identity(row)
    (actual,), contexts, _ = retained_occurrences(
        {"contributions": (row,)}, {"#/texts/1": {"text": "Mean is average."}}, PIN, "new-op"
    )
    assert actual["anchors"] == (anchor,)
    assert contexts == {}
