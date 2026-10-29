"""Native compact alternative sets and independent explanation expectations."""

import json
from dataclasses import replace
from decimal import Decimal
from hashlib import sha256

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.arrow_publication import ArrowPublicationBatch, publish_arrow
from corpus_structure.semantic.identity import alternative_group_key
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.publication import (
    AlternativeGroupRow,
    AlternativeMemberRow,
    AssessmentRow,
    publish_batch,
)
from corpus_structure.semantic.query import read_session

from .test_query import Z, candidate, seed


def grouped(prepared):
    batch = candidate(prepared)
    members = sorted([batch.fact[0].fact_id, batch.fact[1].fact_id])
    # Independent canonical reference encoding; do not use the production identity helper.
    group_id = (
        "alternative:"
        + sha256(
            json.dumps(
                [prepared.release_id, Z, members], ensure_ascii=False, separators=(",", ":")
            ).encode()
        ).hexdigest()
    )
    reason = json.dumps(
        {
            "sources": [
                {
                    "observation_key": "source:first",
                    "local_id": "local-group",
                    "faithful": True,
                    "reason": "First raw reason",
                },
                {
                    "observation_key": "source:second",
                    "local_id": "local-group",
                    "faithful": False,
                    "reason": "Second raw reason",
                },
            ],
            "generated": [
                {"kind": "scientific_value_difference", "key": "global-subject/property"}
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return replace(
        batch,
        alternative_group=(
            AlternativeGroupRow(group_id, reason, "consolidate.alternatives", "semantic-5"),
        ),
        alternative_member=tuple(AlternativeMemberRow(group_id, member) for member in members),
        assessment=(
            AssessmentRow(
                "assessment:occurrence",
                "science",
                "semantic-5",
                "rejected",
                occurrence_id=batch.occurrence[0].occurrence_id,
                confidence=Decimal("0.25"),
                reason="Explicit operation reason",
                uncertainty="Insufficient source agreement",
            ),
            AssessmentRow(
                "assessment:fact",
                "selection",
                "semantic-5",
                "accepted",
                fact_id=batch.fact[0].fact_id,
            ),
            AssessmentRow(
                "assessment:unrelated",
                "selection",
                "semantic-5",
                "accepted",
                fact_id=batch.fact[2].fact_id,
            ),
        ),
    )


def test_native_group_and_assessments_explain_all_source_occurrences(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine
):
    prepared = seed(semantic_db_engine)
    batch = grouped(prepared)
    assert publish_batch(semantic_writer_engine, batch).data_revision == 1
    assert publish_batch(semantic_writer_engine, batch).data_revision == 1
    with read_session(semantic_reader_engine, Z) as session:
        explanation = session.explain(batch.fact[0].fact_id)
        assert len(explanation.alternatives) == 1
        group = explanation.alternatives[0]
        assert group.group_id == batch.alternative_group[0].group_id
        assert group.member_fact_ids == tuple(
            sorted([batch.fact[0].fact_id, batch.fact[1].fact_id])
        )
        assert (
            group.operation_id == "consolidate.alternatives"
            and group.operation_version == "semantic-5"
        )
        assert json.loads(group.reason)["sources"][1]["reason"] == "Second raw reason"
        assert len(explanation.supports) == 2
        assert {assessment.assessment_id for assessment in explanation.assessments} == {
            "assessment:fact",
            "assessment:occurrence",
        }
        occurrence = next(a for a in explanation.assessments if a.occurrence_id is not None)
        assert occurrence.confidence == Decimal("0.25") and occurrence.outcome == "rejected"
        assert occurrence.reason == "Explicit operation reason"
        assert occurrence.uncertainty == "Insufficient source agreement"
        assert session.explain(batch.fact[1].fact_id).alternatives == explanation.alternatives
        assert session.explain(batch.fact[2].fact_id).alternatives == ()
    with semantic_writer_engine.connect() as conn:
        assert len(conn.execute(select(table("data.alternative_group"))).all()) == 1
        assert len(conn.execute(select(table("data.alternative_member"))).all()) == 2
        assert len(conn.execute(select(table("data.occurrence"))).all()) == 2


@pytest.mark.parametrize(
    "damage, message",
    [
        ("single", "alternative group requires at least two distinct facts"),
        ("omitted", "alternative group requires at least two distinct facts"),
        ("id", "invalid canonical alternative group identity"),
        ("reason", "alternative reason must be a canonical JSON object"),
        ("missing_fact", "foreign key constraint"),
        ("missing_group", "foreign key constraint"),
    ],
)
def test_native_refuses_invalid_group_structure(
    semantic_db_engine, semantic_writer_engine, damage, message
):
    batch = grouped(seed(semantic_db_engine))
    if damage == "single":
        batch = replace(batch, alternative_member=batch.alternative_member[:1])
    elif damage == "omitted":
        batch = replace(batch, alternative_member=())
    elif damage == "id":
        batch = replace(
            batch,
            alternative_group=(replace(batch.alternative_group[0], group_id="invented"),),
            alternative_member=tuple(
                replace(member, group_id="invented") for member in batch.alternative_member
            ),
        )
    elif damage == "reason":
        batch = replace(
            batch,
            alternative_group=(replace(batch.alternative_group[0], reason='{"not": "canonical"}'),),
        )
    elif damage == "missing_fact":
        batch = replace(
            batch,
            alternative_member=(
                replace(batch.alternative_member[0], fact_id="outside"),
                *batch.alternative_member[1:],
            ),
        )
    else:
        batch = replace(batch, alternative_group=())
    with pytest.raises(DBAPIError, match=message):
        publish_batch(semantic_writer_engine, batch)
    with semantic_writer_engine.connect() as conn:
        assert conn.execute(select(table("data.alternative_group"))).all() == []
        assert conn.execute(select(table("data.fact"))).all() == []


def test_arrow_group_transport_and_duplicate_fact_collapse(
    semantic_db_engine, semantic_writer_engine
):
    prepared = seed(semantic_db_engine)
    batch = grouped(prepared)
    members = tuple(member.fact_id for member in batch.alternative_member)
    assert (
        alternative_group_key(prepared.release_id, Z, (*members, members[0]))
        == batch.alternative_group[0].group_id
    )
    with pytest.raises(ValueError, match="at least two distinct facts"):
        alternative_group_key(prepared.release_id, Z, (members[0], members[0]))
    arrow = ArrowPublicationBatch.from_rows(batch)
    assert arrow.content == batch.content
    assert len(arrow.relations["alternative_member"]) == 2
    assert publish_arrow(semantic_writer_engine, arrow).data_revision == 1
