"""Independent graph-position expectations for construction's formal input support."""

from copy import deepcopy
from types import SimpleNamespace

import pytest

from corpus_structure.semantic.construction_formal_references import (
    project_construction_formal_support,
)
from corpus_structure.semantic.construction_products import _stage_construction_support
from corpus_structure.semantic.data_product_reference import SemanticReference


def test_formal_premises_keep_mixed_annotation_positions_and_packed_choice_addresses():
    left = {"product_id": "formal:left", "member_id": "annotation:shared"}
    right = {"product_id": "formal:right", "member_id": "annotation:shared"}
    choice = {"product_id": "formal:right", "member_id": "choice:alternative"}
    token = SemanticReference.item("sentences", "rows", "block", ("token", 0)).values()
    term = {
        "local_id": "term",
        "record_type": "term",
        "external_premises": [token, left, right],
        "required_external_choices": [choice],
        "basis": {"external_premises": [right, token], "required_external_choices": [choice]},
    }
    alternative = {"local_id": "alternative", "external_premises": [right, left]}
    group = {"local_id": "group", "record_type": "choice", "members": [alternative]}
    facts = {
        name: []
        for name in ("occurrences", "annotations", "memberships", "roles", "terms", "choices")
    }
    facts.update(terms=[term], choices=[group])
    annotations, formal = _stage_construction_support(
        facts,
        (SimpleNamespace(semantic_id="formal:left"), SimpleNamespace(semantic_id="formal:right")),
    )
    assert term["external_premises"] == []
    assert alternative["external_premises"] == []
    assert [
        row["position"]
        for row in formal
        if row["owner"] == "term" and row["use"] == "external_premise"
    ] == [1, 2]
    assert [row["target"]["occurrence"] for row in formal if row["owner"] == "alternative"] == [
        "1",
        "0",
    ]
    stored = {
        "formal_support": formal,
        "annotation_support": annotations,
        "members": [
            {"member_id": "term", "body": term},
            {"member_id": "group", "body": group},
            {
                "member_id": "alternative",
                "body": {**alternative, "record_type": "choice_member", "group_id": "group"},
            },
            {"member_id": "$manifest", "body": {"record_type": "manifest"}},
        ],
    }
    original = deepcopy(stored)
    expanded = project_construction_formal_support(
        stored, (("0", "formal:left"), ("1", "formal:right"))
    )
    assert stored == original
    actual = {row["member_id"]: row["body"] for row in expanded["members"]}
    assert actual["term"]["external_premises"] == [left, right]
    assert actual["term"]["required_external_choices"] == [choice]
    assert actual["term"]["basis"] == {
        "external_premises": [right],
        "required_external_choices": [choice],
    }
    assert actual["group"]["members"][0]["external_premises"] == [right, left]
    assert actual["alternative"] == {
        **actual["group"]["members"][0],
        "record_type": "choice_member",
        "group_id": "group",
    }


@pytest.mark.parametrize(
    "mutation", ["missing-parent", "duplicate-slot", "absent-owner", "overlap", "outside-position"]
)
def test_formal_support_refuses_unresolved_or_inconsistent_graph_slots(mutation):
    target = SemanticReference.member("formal", "annotation", occurrence="7").values()
    item = dict(owner="node", use="external_premise", position=0, target=target)
    value = {
        "formal_support": [item],
        "annotation_support": [],
        "members": [
            {
                "member_id": "node",
                "body": {"local_id": "node", "record_type": "annotation", "external_premises": []},
            }
        ],
    }
    parents = (("7", "formal:original"),)
    if mutation == "missing-parent":
        parents = ()
    elif mutation == "duplicate-slot":
        value["formal_support"].append(dict(item))
    elif mutation == "absent-owner":
        item["owner"] = "absent"
    elif mutation == "outside-position":
        item["position"] = 4
    else:
        value["annotation_support"] = [dict(owner="node", use="external_premise", position=0)]
    with pytest.raises(ValueError):
        project_construction_formal_support(value, parents)
