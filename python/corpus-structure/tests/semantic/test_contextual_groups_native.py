"""Native member schemas and selected-edge consumers for controlled local groups."""

from copy import deepcopy
from dataclasses import asdict, replace
from pathlib import Path

import pytest
from sqlalchemy import text

from corpus_structure.methods.contextual_embeddings import identity
from corpus_structure.semantic.contextual_operations import (
    contextual_inputs,
    contextual_relationship_binding,
    contextual_relationship_decision,
    witnessed_relationship_members,
)
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.types import SourceArtifact, SourceBundle
from semantic.contextual_enrichment_support import (
    candidates,
    definition_inventory,
    select_definition_origins,
    semantic_definition_meaning,
    witness,
)


@pytest.fixture(scope="module")
def relationship_schema():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    prepared = prepare_release(
        contextual_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    )
    return prepared.json_schema("DdoContextualSelectedRelationship")


def native_member_matches(conn, schema, edge):
    # Generic native nominal admission owns this same schema check. Source and
    # producing-use custody are exercised by the actual contextual workflows.
    return conn.scalar(
        text(
            "SELECT public.json_matches_schema(CAST(:schema AS json), CAST(:member AS json))"
        ),
        {
            "schema": canonical_bytes(schema).decode(),
            "member": canonical_bytes(edge).decode(),
        },
    )


def replay(conn, schema, decision, candidate_list, inventory):
    product = witnessed_relationship_members(
        {
            "version": "declared-contextual-retrieval-1",
            "source_pin": {"source": decision.source_binding},
            "anchors": [],
            "inventory": source_value(asdict(inventory)),
            "candidate_list": source_value(asdict(candidate_list)),
            "relationship_decision": source_value(asdict(decision)),
            "witness_input": {"variant": "product", "role": "witnesses"},
        },
        kind_contract="controlled-selected-relationship",
        context=SubjectContext("book", "occ", "source", b"{}", subject_definition="source-view"),
    )
    assert contextual_relationship_decision(product) == decision
    for edge in (
        *decision.selected_edges,
        *(edge for group in decision.alternative_groups for edge in group.edges),
    ):
        body = {**asdict(edge), "witnesses": source_value(asdict(edge)["witnesses"])}
        assert native_member_matches(conn, schema, body) is True
    for edge in decision.selected_edges:
        binding = contextual_relationship_binding(
            product, decision_id=decision.decision_id, edge_id=edge.edge_id
        )
        assert binding.edge == edge
    return product


def test_native_same_meaning_corroboration_preserves_one_edge_and_all_proofs(
    commit_db_engine, relationship_schema
):
    meaning = semantic_definition_meaning()
    inventory = definition_inventory({"a": meaning, "b": deepcopy(meaning)})
    rule = witness("rule", "a")
    model = replace(witness("model", "b"), basis="model_reading")
    decision = select_definition_origins(inventory, (rule, model))
    single = select_definition_origins(inventory, (rule,))
    (edge,) = decision.selected_edges
    assert decision.outcome == "selected" and not decision.alternative_groups
    assert edge.member_target_ids == ("a", "b")
    assert {proof.witness_id for proof in edge.witnesses} == {"rule", "model"}
    assert edge.edge_id == single.selected_edges[0].edge_id
    with commit_db_engine.begin() as conn:
        product = replay(conn, relationship_schema, decision, candidates(inventory), inventory)
        assert len(product["members"]) == 1
        unsupported = select_definition_origins(
            inventory, (rule, replace(model, support_state="unsupported"))
        )
        replay(conn, relationship_schema, unsupported, candidates(inventory), inventory)
        assert unsupported.selected_edges[0].member_target_ids == ("a",)
        assert len(unsupported.witnesses) == 2
        # A private proof cannot be erased while claiming the full selected edge.
        corrupt = replace(decision, selected_edges=(replace(edge, member_target_ids=("a",)),))
        meaning = {key: value for key, value in asdict(corrupt).items() if key != "decision_id"}
        corrupt = replace(corrupt, decision_id=identity("scoped-relationship", meaning))
        with pytest.raises(ValueError, match="substitutes its actual semantic target carriers"):
            replay(conn, relationship_schema, corrupt, candidates(inventory), inventory)
        malformed = {**product["members"][0]["body"], "relation": "invented"}
        assert native_member_matches(conn, relationship_schema, malformed) is False


def test_native_distinct_source_meanings_remain_competing_senses(
    commit_db_engine, relationship_schema
):
    first = semantic_definition_meaning()
    second = deepcopy(first)
    second["content"]["text"] = "another"
    inventory = definition_inventory({"a": first, "b": second})
    decision = select_definition_origins(inventory, (witness("a", "a"), witness("b", "b")))
    assert decision.outcome == "ambiguous" and not decision.selected_edges
    assert len(decision.alternative_groups[0].edges) == 2
    with commit_db_engine.begin() as conn:
        product = replay(conn, relationship_schema, decision, candidates(inventory), inventory)
        assert product["members"] == []
