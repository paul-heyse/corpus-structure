"""Independent semantic admission expectations, distinct from grade labels."""

from copy import deepcopy
from typing import Any

import pytest
from sqlalchemy import text

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.local_semantic_admission import CONTEXT_POLICY, RUBRIC
from corpus_structure.semantic.observations import source_value


def evidence() -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]
]:
    # Expected semantic content is fixed independently of computational lineage.
    statement = dict(
        target_id="statistics:poisson",
        target_source_binding="descriptor:poisson",
        relation="denotes",
        scope="selected-source-context",
        effective_version=None,
    )
    value = source_value(statement)
    contribution = dict(
        standing="retained_private",
        kind="proposal",
        semantic_type="contextual.denotation",
        contribution_id="proposal:one",
        occurrence_id="physical:one",
        value=value,
        pin={"source_view_id": 23, "projection_digest": "source-projection"},
        anchors=[
            dict(
                anchor_id="anchor:one",
                space="native",
                precision="exact",
                start=0,
                end=7,
                source_piece="Poisson",
            )
        ],
    )
    question = "contextual denotation selection for supplied occurrence"
    operation = dict(question=question, operation_version="1", outcome="succeeded")
    frame = dict(
        direction="source_first",
        operation_question=question,
        operation_version="1",
        rubric_version=RUBRIC,
        context_policy=CONTEXT_POLICY,
        pin=contribution["pin"],
        anchor_ids=["anchor:one"],
    )
    case = dict(
        case_id="denotation-one",
        facet="denotation",
        judgment="supported",
        source_state="stated",
        expectation_mode="structure",
        contribution_kind="proposal",
        anchor_ids=["anchor:one"],
        alternatives=[dict(semantic_type="contextual.denotation", value=value)],
    )
    result = dict(
        case_id="denotation-one",
        facet="denotation",
        judgment="supported",
        source_state="stated",
        expectation_mode="structure",
        capture_outcome="captured_structure",
        error_category=None,
        contribution_id="proposal:one",
    )
    return contribution, operation, frame, case, result


def native_match(engine, values):
    with engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT data.local_semantic_case_matches(CAST(:c AS jsonb),CAST(:o AS jsonb),"
                "CAST(:f AS jsonb),CAST(:a AS jsonb),CAST(:g AS jsonb))"
            ),
            {
                name: canonical_bytes(value).decode()
                for name, value in zip("cofag", values, strict=True)
            },
        ).scalar_one()


def test_exact_independent_denotation_can_qualify(semantic_db_engine):
    assert native_match(semantic_db_engine, evidence())


@pytest.mark.parametrize(
    "position,key,value",
    [
        (0, "semantic_type", "entity.canonical_identity"),
        (1, "outcome", "failed"),
        (1, "operation_version", "2"),
        (2, "direction", "output_first"),
        (2, "rubric_version", "other-rubric"),
        (2, "context_policy", "other-context"),
        (2, "operation_question", "different question"),
        (2, "pin", {"source_view_id": 99}),
        (3, "judgment", "ambiguous"),
        (3, "judgment", "unassessed"),
        (3, "source_state", "unstated"),
        (3, "expectation_mode", "absence_detection"),
        (3, "facet", "scientific_truth"),
        (3, "anchor_ids", ["other-anchor"]),
        (4, "contribution_id", "foreign-proposal"),
        (4, "capture_outcome", "not_captured"),
        (4, "judgment", "unsupported"),
    ],
)
def test_supported_label_cannot_bypass_applicability(semantic_db_engine, position, key, value):
    values = deepcopy(evidence())
    values[position][key] = value
    assert not native_match(semantic_db_engine, values)


def test_partial_or_wrong_full_semantic_statement_is_not_admitted(semantic_db_engine):
    for expected in (
        {"semantic_type": "contextual.denotation"},
        {"value": source_value({"target_id": "statistics:poisson"})},
        {
            "semantic_type": "contextual.denotation",
            "value": source_value(
                {
                    "target_id": "statistics:binomial",
                    "target_source_binding": "descriptor:binomial",
                    "relation": "denotes",
                    "scope": "selected-source-context",
                    "effective_version": None,
                }
            ),
        },
    ):
        values = deepcopy(evidence())
        values[3]["alternatives"] = [expected]
        assert not native_match(semantic_db_engine, values)
