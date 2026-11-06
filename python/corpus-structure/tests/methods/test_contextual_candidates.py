"""Independent source/role and selected-edge projection controls for actual occurrence linking."""

from dataclasses import replace

import pytest

from corpus_structure.methods.contextual_candidates import (
    ContextualCandidateConfig,
    relationship_contributions,
    retained_occurrences,
)
from corpus_structure.semantic.contextual_links import (
    RelationshipConstraint,
    RelationshipWitness,
    select_relationships,
)
from corpus_structure.semantic.contextual_retrieval import (
    ChannelHit,
    freeze_inventory,
    fuse_candidates,
    target_representation,
)
from corpus_structure.semantic.contributions import contribution_identity, occurrence_identity
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.record_contracts import anchor_identity


PIN = dict(source="source", native_product_task_id=1, product_key="native", product_digest="a" * 64, projection_digest="b" * 64, recipe_digest="c" * 64, source_view_id=1)

def located(role="term", start=0, end=4):
    anchor = dict(pin=PIN, space="native", pointer="#/texts/1", precision="exact",
                  start=start, end=end, source_piece="Mean is average."[start:end])
    anchor["anchor_id"] = anchor_identity(anchor)
    row = dict(kind="occurrence", semantic_type="source_rule." + role, operation_key="producer-op",
               item_key=role, pin=PIN, anchors=(anchor,), occurrence_id=occurrence_identity((anchor,)))
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
    assert {source_python(row["value"])["producer_semantic_type"] for row in rows} == {"source_rule.term", "source_rule.expression"}
    assert coordinates[0]["text"] == "Mean is average."


def test_actual_occurrence_cannot_invent_source_extent():
    row = located()
    row["anchors"][0]["source_piece"] = "wrong"
    with pytest.raises(ValueError, match="slice"):
        retained_occurrences({"contributions": (row,)}, {"#/texts/1": {"text": "Mean is average."}}, PIN, "new-op")


def test_supplied_mention_and_registry_production_bridge_removed():
    with pytest.raises(ValueError):
        ContextualCandidateConfig.model_validate(dict(cases=(), registry_targets=(), scope="s"))


def test_projection_preserves_all_selected_kinds_without_first_alternative():
    from corpus_structure.methods.contextual_embeddings import EncodedVector

    target = target_representation("concept", "component-source", "Mean", "average", scope="chapter")
    inventory = freeze_inventory((target,), source_selection="component-inventory", scope="chapter")
    candidates = fuse_candidates(occurrence_id="occ", query=EncodedVector("v", "occ", "source", "p", "digest", (1., 0.)), inventory=inventory,
                                 channels={"dense": (ChannelHit("concept", 1.),)})
    original = RelationshipWitness("d", "occ", "concept", "denotes", "source", "chapter", None, ("raw",), "producer_group")
    decision = select_relationships(candidates=candidates, inventory=inventory, source_binding="source", scope="chapter", effective_version=None,
                                    constraints=(RelationshipConstraint("sense", ("denotes",), "usage", "sense", "one"),
                                                 RelationshipConstraint("comparison", ("compared-with",), "subject", "comparator", "many")),
                                    witnesses=(original, replace(original, witness_id="c", relation="compared-with")))
    source = located()
    rows = relationship_contributions(decision, source, inventory, "edge-op")
    assert {source_python(row["value"])["relation"] for row in rows} == {"denotes", "compared-with"}
    assert len({source_python(row["value"])["edge_id"] for row in rows}) == 2
    assert all(row["members"] == (source["contribution_id"],) for row in rows)
    assert len(decision.selected_edges) == 2
