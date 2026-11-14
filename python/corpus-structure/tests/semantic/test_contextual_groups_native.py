"""Native selector replay for local semantic groups; custody is tested by native workflows."""

from copy import deepcopy
from dataclasses import asdict, replace

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.identity import canonical_bytes
from semantic.contextual_enrichment_support import (
    candidates,
    definition_inventory,
    select_definition_origins,
    semantic_definition_meaning,
    witness,
)


def replay(conn, decision, candidate_list, inventory):
    # Production report serialization omits optional null-valued fields.
    conn.execute(
        text(
            "SELECT ops.validate_contextual_selection("
            "jsonb_strip_nulls(CAST(:decision AS jsonb)),"
            "jsonb_strip_nulls(CAST(:candidates AS jsonb)),"
            "jsonb_strip_nulls(CAST(:inventory AS jsonb)))"
        ),
        {
            name: canonical_bytes(asdict(value)).decode()
            for name, value in (
                ("decision", decision),
                ("candidates", candidate_list),
                ("inventory", inventory),
            )
        },
    )


def test_native_same_meaning_corroboration_preserves_one_edge_and_all_proofs(commit_db_engine):
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
        replay(conn, decision, candidates(inventory), inventory)
        unsupported = select_definition_origins(
            inventory, (rule, replace(model, support_state="unsupported"))
        )
        replay(conn, unsupported, candidates(inventory), inventory)
        assert unsupported.selected_edges[0].member_target_ids == ("a",)
        assert len(unsupported.witnesses) == 2
        # A private proof cannot be erased while claiming the full selected edge.
        corrupt = replace(decision, selected_edges=(replace(edge, member_target_ids=("a",)),))
        with pytest.raises(DBAPIError, match="selected edges or alternatives"), conn.begin_nested():
            replay(conn, corrupt, candidates(inventory), inventory)


def test_native_distinct_source_meanings_remain_competing_senses(commit_db_engine):
    first = semantic_definition_meaning()
    second = deepcopy(first)
    second["content"]["text"] = "another"
    inventory = definition_inventory({"a": first, "b": second})
    decision = select_definition_origins(inventory, (witness("a", "a"), witness("b", "b")))
    assert decision.outcome == "ambiguous" and not decision.selected_edges
    assert len(decision.alternative_groups[0].edges) == 2
    with commit_db_engine.begin() as conn:
        replay(conn, decision, candidates(inventory), inventory)
