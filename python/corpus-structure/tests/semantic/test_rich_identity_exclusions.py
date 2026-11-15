"""Actual typed declaration/resolution correspondence and independent refusal controls."""

from decimal import Decimal
from typing import Literal

import pytest
from evaluate.declared_record_policy_support import source
from pydantic import TypeAdapter

from corpus_structure.semantic.rich_identity_exclusions import (
    rich_identity_exclusion_id,
    rich_located_evidence,
    validate_rich_identity_exclusion,
)
from corpus_structure.semantic.rich_knowledge_contracts import (
    DdoRichContextPin,
    DdoRichExclusionDeclaration,
    DdoRichIdentityExclusion,
)
from semantic.test_rich_queries import Graph
from semantic.test_rich_queries import query_source as query_source


def constraint(
    graph,
    *,
    left="A",
    right="B",
    outcome: Literal["located", "unlocated", "unresolved-endpoint"] = "located",
    located=True,
):
    selected_source = source(1).model_copy(update={"project_id": graph.context.project_id})
    pin = DdoRichContextPin(
        project_id=selected_source.project_id,
        subject=selected_source.subject,
        subject_definition=selected_source.subject_definition,
        original_source=selected_source.original_source,
        analyzed_scope_meaning=selected_source.analyzed_scope_meaning,
    )
    evidence = rich_located_evidence(
        graph.prepared,
        dict(
            sentence="sentence:1",
            quote="A differs from B",
            role="primary",
            placement="exact",
            matches=1 if located else 0,
            picked=False,
            outcome="located" if located else "unlocated",
            **dict(locator="#/texts/1", start=0, end=16) if located else {},
        ),
    )
    declaration = DdoRichExclusionDeclaration(
        local_id="separate",
        unit_ref="unit:actual",
        source=selected_source,
        context=pin,
        left={"kind": "local", "target": "local:A"},
        right={"kind": "known", "target": "B"},
        reason="source distinguishes them",
        evidence=(evidence,),
    )
    refs = (graph.origin.model_copy(update={"member_id": "identity_exclusion:separate"}),)
    fields = dict(
        declaration=declaration,
        left_entity_id=left,
        right_entity_id=right,
        outcome=outcome,
        reason="actual-source-resolution",
        source_members=refs,
    )
    return DdoRichIdentityExclusion(
        member_type="identity-exclusion",
        exclusion_id=rich_identity_exclusion_id(graph.context, **fields),
        **fields,
    )


def test_constraint_projects_exact_source_declaration_without_relabelling_evidence_or_resolution(
    query_source,
):
    graph = Graph(query_source, {"A": "DistributionFamily", "B": "DistributionFamily"})
    value = constraint(graph)
    validate_rich_identity_exclusion(graph.prepared, graph.context, value)
    assert value.declaration.left.target == "local:A" and value.left_entity_id == "A"
    assert value.declaration.right.target == value.right_entity_id == "B"
    assert value.source_members[0].member_id == "identity_exclusion:separate"
    assert value.declaration.evidence[0].quote == "A differs from B"
    graph.bodies[value.exclusion_id] = value
    assert graph.index().state.members[value.exclusion_id] == value
    # Actual CPU/Pydantic JSON defaults roundtrip does not change this meaning.
    adapter = TypeAdapter(DdoRichIdentityExclusion)
    returned = adapter.validate_json(adapter.dump_json(value), strict=True)
    validate_rich_identity_exclusion(graph.prepared, graph.context, returned)
    assert returned == value


def test_unlocated_and_unresolved_are_explicit_non_constraints(query_source):
    graph = Graph(query_source, {"A": "DistributionFamily", "B": "DistributionFamily"})
    unlocated = constraint(graph, located=False, outcome="unlocated")
    unresolved = constraint(graph, right=None, outcome="unresolved-endpoint")
    for value in (unlocated, unresolved):
        validate_rich_identity_exclusion(graph.prepared, graph.context, value)
    assert unlocated.outcome != "located" and unresolved.right_entity_id is None


@pytest.mark.parametrize(
    "defect",
    [
        "wrong-id",
        "false-located",
        "same-entity",
        "known-remapped",
        "source-context",
        "local-address",
        "missing-bounds",
        "unknown-evidence-role",
        "missing-entity",
    ],
)
def test_constraint_refuses_forged_correspondence_and_actual_local_links(query_source, defect):
    graph = Graph(query_source, {"A": "DistributionFamily", "B": "DistributionFamily"})
    value = constraint(graph)
    if defect == "wrong-id":
        value = value.model_copy(update={"exclusion_id": "invented"})
    elif defect == "false-located":
        value = constraint(graph, located=False, outcome="located")
    elif defect == "same-entity":
        value = constraint(graph, left="B")
    elif defect == "known-remapped":
        value = constraint(graph, right="A")
    elif defect == "source-context":
        value = value.model_copy(
            update={
                "declaration": value.declaration.model_copy(
                    update={
                        "context": value.declaration.context.model_copy(
                            update={"original_source": "other-original"}
                        )
                    }
                )
            }
        )
    elif defect == "local-address":
        value = value.model_copy(
            update={
                "source_members": (
                    value.source_members[0].model_copy(
                        update={"member_id": "identity_exclusion:other"}
                    ),
                )
            }
        )
    elif defect in {"missing-bounds", "unknown-evidence-role"}:
        evidence = value.declaration.evidence[0].model_copy(
            update={"start": None} if defect == "missing-bounds" else {"role": "never-declared"}
        )
        value = value.model_copy(
            update={"declaration": value.declaration.model_copy(update={"evidence": (evidence,)})}
        )
    else:
        value = constraint(graph, left="not-in-actual-graph")
    if defect != "wrong-id":
        value = value.model_copy(
            update={
                "exclusion_id": rich_identity_exclusion_id(
                    graph.context,
                    declaration=value.declaration,
                    left_entity_id=value.left_entity_id,
                    right_entity_id=value.right_entity_id,
                    outcome=value.outcome,
                    reason=value.reason,
                    source_members=value.source_members,
                )
            }
        )
    with pytest.raises(ValueError):
        graph.bodies[value.exclusion_id] = value
        graph.index()


def test_optional_evidence_projection_keeps_unknown_absent_and_explicit_empty_distinct(
    query_source,
):
    prepared = query_source[0]
    raw = dict(
        sentence="s",
        quote="unplaced",
        role="primary",
        placement="exact",
        matches=0,
        picked=False,
        outcome="unlocated",
    )
    absent = rich_located_evidence(prepared, raw)
    empty = rich_located_evidence(prepared, {**raw, "timeouts": (), "fuzzy_counts": ()})
    assert absent.timeouts is None and empty.timeouts == ()
    assert absent.fuzzy_counts is None and empty.fuzzy_counts == ()
    with pytest.raises(ValueError):
        rich_located_evidence(prepared, {**raw, "start": None})
    score = Decimal("0.123456789123456789123456789")
    scored = rich_located_evidence(prepared, {**raw, "alignment_score": score})
    assert scored.alignment_score == score
