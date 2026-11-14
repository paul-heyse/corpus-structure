"""Population association retains JSON context types within one frozen demand."""

import pytest

from corpus_structure.semantic.data_operation_demands import _population_context_matches


@pytest.mark.parametrize("scope, expected", [(1, True), (1.0, True), (True, False), ("1", False)])
@pytest.mark.parametrize("origin", ["selection", "producer", "source-set"])
def test_population_context_distinguishes_boolean_and_number_with_numeric_value_equality(
    scope,
    expected,
    origin,
):
    obligation = {
        "obligation_id": "obligation:one",
        "operation_id": "operation:aggregate",
        "subject": "subject:one",
        "original_source": "source:one",
        "analyzed_scope": {"page": 1},
    }
    context = {**obligation, "analyzed_scope": {"page": scope}}
    source_sets = {}
    if origin == "selection":
        row = {"evidence": {"selection": context}, "members": []}
    elif origin == "producer":
        row = {"evidence": {"producer_context": context}, "members": []}
    else:
        # A remote source is admitted only through the frozen member association.
        row = {
            "evidence": {
                "producer_context": {**context, "original_source": "source:remote"},
                "product_id": "product:remote",
            },
            "members": [{**context, "member_id": "member:one"}],
        }
        source_sets = {
            "selected": [
                {
                    **obligation,
                    "project_id": "project:one",
                    "product": "product:remote",
                    "member": "member:one",
                    "original_source": "source:remote",
                }
            ]
        }
        row["members"][0]["original_source"] = "source:remote"
    assert (
        _population_context_matches(
            row,
            obligation,
            source_set="selected",
            source_sets=source_sets,
            project="project:one",
        )
        is expected
    )


def test_two_populations_in_one_demand_keep_their_distinct_boolean_and_numeric_roots():
    common = {"subject": "same", "original_source": "same"}
    rows = [
        {"evidence": {"producer_context": {**common, "analyzed_scope": {"page": value}}}}
        for value in (True, 1)
    ]
    for index, value in enumerate((True, 1)):
        obligation = {**common, "analyzed_scope": {"page": value}}
        assert [
            position
            for position, row in enumerate(rows)
            if _population_context_matches(
                row,
                obligation,
                source_set=None,
                source_sets={},
                project="project:one",
            )
        ] == [index]


def test_original_source_role_retains_complete_sibling_context_with_exact_frozen_parent():
    from copy import deepcopy

    obligation = dict(obligation_id="obligation:child", operation_id="op:consumer",
        subject="source:child", original_source="original:book", analyzed_scope={"region": 1})
    parent = dict(name="context-universe", complete=True, evidence=dict(product_id="product:views",
        derivation_id="derivation:views", admission_use_id="use:views", member_role="result",
        producer_context=dict(operation_id="op:chosen-discovery", subject="document:book",
            original_source="original:book", analyzed_scope={"scope": "whole-document"})),
        members=[dict(member_id="child", subject="source:child", original_source="original:book", analyzed_scope={"region": 1}),
            dict(member_id="sibling", subject="source:sibling", original_source="original:book", analyzed_scope={"region": 2})])
    relation = dict(producer="op:chosen-discovery", output_role="result", target="op:consumer", population="context-universe")
    arguments = dict(source_set=None, source_sets={}, project="same-native-demand-project",
        original_source_role=True, discovery=(relation,))
    before = deepcopy(parent)
    assert _population_context_matches(parent, obligation, **arguments)
    assert parent == before and len(parent["members"]) == 2
    assert not _population_context_matches(parent, obligation, **{**arguments, "original_source_role": False})
    assert not _population_context_matches(parent, obligation, **{**arguments, "discovery": ()})
    for change in ("open", "wrong-original", "different-child-scope", "wrong-output", "wrong-producer", "wrong-population", "missing-native-use"):
        changed = deepcopy(parent)
        if change == "open":
            changed["complete"] = False
        elif change == "wrong-original":
            changed["evidence"]["producer_context"]["original_source"] = "another-original"
        elif change == "different-child-scope":
            changed["members"][0]["analyzed_scope"] = {"region": True}
        elif change == "wrong-output":
            changed["evidence"]["member_role"] = "another-output"
        elif change == "wrong-producer":
            changed["evidence"]["producer_context"]["operation_id"] = "unfrozen-discovery"
        elif change == "wrong-population":
            changed["name"] = "another-population"
        else:
            changed["evidence"].pop("admission_use_id")
        assert not _population_context_matches(changed, obligation, **arguments), change
