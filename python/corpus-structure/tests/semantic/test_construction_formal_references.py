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


@pytest.mark.parametrize("location", ["term", "basis", "packed-choice"])
@pytest.mark.parametrize("field", ["external_premises", "required_external_choices"])
def test_dependency_checker_rejects_unstaged_computed_formal_pins(location, field):
    from corpus_structure.semantic.construction_products import (
        verify_interpreted_dependency_members,
    )

    reference = {"product_id": "formal:original", "member_id": "formal:node"}
    node: dict[str, object] = {"local_id": "node", "record_type": "term"}
    if location == "basis":
        node["basis"] = {field: [reference]}
    elif location == "packed-choice":
        node.update(record_type="choice", members=[{"local_id": "alternative", field: [reference]}])
    else:
        node[field] = [reference]
    product = {
        "formal_support": [],
        "members": [{"member_id": "node", "body": node}],
    }
    dependencies = (
        (
            "formal:original",
            {
                "members": [
                    {
                        "member_id": "formal:node",
                        "body": {"record_type": "choice_member", "local_id": "formal:node"},
                    }
                ]
            },
        ),
    )
    with pytest.raises(ValueError, match="retains a computed formal input pin"):
        verify_interpreted_dependency_members(product, {}, dependencies, include_annotations=False)
    product["members"] = []
    verify_interpreted_dependency_members(product, {}, dependencies, include_annotations=False)


@pytest.mark.parametrize(
    "authority",
    ["complete", "rank_changed", "missing_uncited", "missing_annotations", "split", "conflicting"],
)
def test_selected_construction_requires_one_complete_original_role_closure(authority):
    from corpus_structure.semantic.construction_formal_references import (
        expand_selected_construction_formal_support,
    )

    # Neither formal input is cited by a graph member. Both still determined
    # which complete domain the producer examined; the annotation role is exact.
    value = dict(formal_support=[], annotation_support=[], members=[])
    original = [
        dict(role="formal", product_id="first", position=0, multiplicity=1),
        dict(role="formal", product_id="second", position=1, multiplicity=1),
        dict(role="sentences", product_id="annotations", position=0, multiplicity=1),
    ]
    current = deepcopy(original)
    if authority == "rank_changed":
        current[0]["position"], current[1]["position"] = 1, 0
    elif authority == "missing_uncited":
        current.pop(1)
    elif authority == "missing_annotations":
        current.pop()
    selections = [current] if authority != "split" else [[current[0]], current[1:]]
    inputs = {"episode": original}
    if authority == "conflicting":
        alternate = deepcopy(original)
        alternate[1]["product_id"] = "another"
        inputs["other-origin"] = alternate
    uses = {
        "use-" + str(position): dict(
            id="use-" + str(position),
            fate="fulfilled",
            derivation_id="episode",
            selection={"inputs": selected},
        )
        for position, selected in enumerate(selections)
    }
    if authority == "conflicting":
        uses["other-use"] = dict(
            id="other-use",
            fate="fulfilled",
            derivation_id="other-origin",
            selection={"inputs": inputs["other-origin"]},
        )
    targets = [
        dict(
            output_role="result",
            input_role="formal",
            input_kind="formal-kind",
            variant="member",
            occurrence_position=True,
            path="/formal_support/*/target",
        ),
        dict(
            output_role="result",
            input_role="sentences",
            input_kind="annotation-kind",
            variant="partition-item",
            collection="rows",
            path="/annotation_support/*/target",
        ),
    ]
    tables = {
        "ops.demand_use": uses,
        "ops.data_derivation": {
            episode: dict(release_id="release", request_id="request") for episode in inputs
        },
        "ops.data_request": {"request": dict(operation_id="construction")},
        "sem.data_operation_definition": {
            ("release", "construction"): dict(
                support_contract={"reference_targets": targets},
                input_roles=[
                    dict(name=role, kind=kind, accepted_kind_contracts=[kind])
                    for role, kind in (("formal", "formal-kind"), ("sentences", "annotation-kind"))
                ],
            )
        },
        # Headers suffice for full-role authorization; no body can be read here.
        "kb.data_product": {
            product: dict(project_id="project", kind_contract=kind)
            for product, kind in (
                ("first", "formal-kind"),
                ("second", "formal-kind"),
                ("another", "formal-kind"),
                ("annotations", "annotation-kind"),
            )
        },
        "kb.data_product_member": {},
        "kb.data_product_partition": {},
        "sem.data_kind_contract": {"formal-kind": {}, "annotation-kind": {}},
    }

    def rows_for(relation, **fields):
        if relation == "ops.data_derivation_output":
            return tuple(dict(derivation_id=episode, role="result") for episode in inputs)
        if relation == "ops.data_derivation_input":
            return tuple(
                item for item in inputs[fields["derivation_id"]] if item["role"] == fields["role"]
            )
        assert relation == "ops.demand_use"
        return tuple(
            use for use in uses.values() if use["derivation_id"] == fields["derivation_id"]
        )

    index = SimpleNamespace(mapping=lambda relation, _: tables[relation], rows_for=rows_for)
    cut = SimpleNamespace(record={"project_id": "project"})
    if authority not in {"complete", "rank_changed"}:
        with pytest.raises(ValueError):
            expand_selected_construction_formal_support(value, index, cut, "product")
    else:
        expanded, parents = expand_selected_construction_formal_support(
            value, index, cut, "product", with_parents=True
        )
        assert expanded == value
        assert set(parents) == {
            ("formal", "0", "first"),
            ("formal", "1", "second"),
            ("sentences", None, "annotations"),
        }
