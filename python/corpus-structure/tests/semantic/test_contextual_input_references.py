"""Exact contextual graph edges through independent producing input occurrences."""

from copy import deepcopy
from types import SimpleNamespace
from typing import Any, cast

import pytest

from corpus_structure.semantic._data_operation_wire import WireOutputMember
from corpus_structure.semantic.contextual_input_references import (
    expand_selected_contextual_inputs,
    pack_contextual_input_support,
    project_contextual_input_support,
)
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.detached_reference_resolution import (
    require_detached_output_references,
)


def graph() -> dict[str, Any]:
    first = dict(product_id="formal:first", member_id="shared")
    second = dict(product_id="formal:second", member_id="shared")
    symbolic = dict(product_id="construction", member_id="term")
    choice = dict(product_id="formal:second", member_id="alternative")
    return dict(
        dependencies=[
            dict(product_id=key) for key in ("formal:first", "formal:second", "construction")
        ],
        roots=[symbolic],
        environment=dict(
            context_products=[dict(product_id="formal:first")],
            hypotheses=[first],
            proposals=[second],
            choices=[choice],
            attribution=[symbolic],
            bindings=[dict(variable=first, binder=symbolic)],
        ),
        members=[
            dict(
                member_id="out",
                body=dict(
                    record_type="term",
                    local_id="out",
                    external_premises=[first, second],
                    required_external_choices=[choice],
                ),
            ),
            dict(
                member_id="role",
                body=dict(
                    record_type="role",
                    local_id="role",
                    basis=dict(external_premises=[symbolic]),
                ),
            ),
            dict(member_id="manifest", body=dict(record_type="manifest", dependencies=[])),
        ],
    )


def roles():
    return {
        "formal": tuple(
            SimpleNamespace(semantic_id=key) for key in ("formal:first", "formal:second")
        ),
        "constructions": (SimpleNamespace(semantic_id="construction"),),
        "supporting": (),
    }


def parents():
    return tuple(
        (role, str(position), product.semantic_id)
        for role, products in roles().items()
        for position, product in enumerate(products)
    )


def test_contextual_role_edges_preserve_overlap_choices_and_environment_without_product_rosters():
    original = graph()
    saved = deepcopy(original)
    stored = pack_contextual_input_support(original, roles())
    assert original == saved
    assert "dependencies" not in stored
    assert "dependencies" not in stored["members"][-1]["body"]
    assert stored["members"][0]["body"]["external_premises"] == []
    assert stored["roots"] == []
    assert stored["environment"]["bindings"] == []
    premises = [slot for slot in stored["formal_member_support"] if slot["use"] == "premise"]
    assert [slot["target"] for slot in premises] == [
        dict(variant="member", role="formal", occurrence=str(position), member_id="shared")
        for position in (0, 1)
    ]
    expanded = project_contextual_input_support(stored, parents())
    assert expanded["roots"] == saved["roots"]
    assert expanded["environment"] == saved["environment"]
    assert expanded["members"][:-1] == saved["members"][:-1]


@pytest.mark.parametrize(
    "failure", ["missing_parent", "wrong_role", "duplicate_slot", "missing_owner", "gap"]
)
def test_contextual_role_edges_refuse_incomplete_or_substituted_addresses(failure):
    stored = pack_contextual_input_support(graph(), roles())
    selected_parents = parents()
    slot = next(slot for slot in stored["formal_member_support"] if slot["use"] == "premise")
    if failure == "missing_parent":
        selected_parents = selected_parents[1:]
    elif failure == "wrong_role":
        slot["target"]["role"] = "constructions"
    elif failure == "duplicate_slot":
        stored["formal_member_support"].append(deepcopy(slot))
    elif failure == "missing_owner":
        slot["owner"] = "absent"
    else:
        slot["position"] = 5
    with pytest.raises(ValueError):
        project_contextual_input_support(stored, selected_parents)


def test_contextual_graph_cannot_cite_an_unselected_report_with_the_same_local_member():
    value = graph()
    value["members"][0]["body"]["external_premises"][0]["product_id"] = "unselected"
    with pytest.raises(ValueError, match="outside its producing inputs"):
        pack_contextual_input_support(value, roles())


@pytest.mark.parametrize("current", ["complete", "rank_changed", "substituted", "split_authority"])
def test_selected_contextual_graph_requires_one_complete_exact_use(current):
    stored = pack_contextual_input_support(graph(), roles())
    pins = [
        dict(role=role, product_id=product, position=int(position), multiplicity=1)
        for role, position, product in parents()
    ]
    selected = deepcopy(pins)
    if current == "rank_changed":
        selected[0]["position"], selected[1]["position"] = 1, 0
    elif current == "substituted":
        selected[1]["product_id"] = "other-report"
    selections = [selected] if current != "split_authority" else [[pins[0]], pins[1:]]
    uses = {
        str(position): dict(
            id=str(position),
            fate="fulfilled",
            derivation_id="episode",
            selection={"inputs": values},
        )
        for position, values in enumerate(selections)
    }
    targets = [
        dict(
            output_role="result",
            input_role=role,
            input_kind="inventory",
            variant=variant,
            occurrence_position=True,
            path=f"/{role}_{variant}_support/*/target",
        )
        for role in roles()
        for variant in ("member", "product")
    ]
    products = {pin["product_id"]: dict(project_id="project", kind_contract="kind") for pin in pins}
    tables = {
        "ops.demand_use": uses,
        "ops.data_derivation": {"episode": dict(release_id="release", request_id="request")},
        "ops.data_request": {"request": dict(operation_id="contextual")},
        "sem.data_operation_definition": {
            ("release", "contextual"): dict(
                support_contract={"reference_targets": targets},
                input_roles=[
                    dict(name=role, kind="inventory", accepted_kind_contracts=["kind"])
                    for role in roles()
                ],
            )
        },
        "kb.data_product": {
            key: {**header, "canonical_body": semantic_value({})}
            for key, header in products.items()
        },
        "kb.data_product_member": {
            (product, member): dict(body=semantic_value(dict(local_id=member)))
            for product, members in {
                "formal:first": ("shared",),
                "formal:second": ("shared", "alternative"),
                "construction": ("term",),
            }.items()
            for member in members
        },
        "kb.data_product_partition": {},
        "sem.data_kind_contract": {"kind": {}},
    }

    tables["kb.data_product_member"]["formal:second", "alternative"] = dict(
        body=semantic_value(
            dict(record_type="choice_member", local_id="alternative", group_id="group", root="term")
        )
    )
    tables["kb.data_product_member"]["formal:second", "group"] = dict(
        body=semantic_value(
            dict(
                record_type="choice",
                local_id="group",
                members=[dict(local_id="alternative", root="term")],
            )
        )
    )

    def rows_for(relation, **fields):
        if relation == "ops.data_derivation_output":
            return (dict(derivation_id="episode", role="result"),)
        if relation == "ops.data_derivation_input":
            return [pin for pin in pins if "role" not in fields or pin["role"] == fields["role"]]
        assert relation == "ops.demand_use"
        return tuple(uses.values())

    index = SimpleNamespace(mapping=lambda relation, _: tables[relation], rows_for=rows_for)
    cut = SimpleNamespace(record={"project_id": "project"})
    if current in {"substituted", "split_authority"}:
        with pytest.raises((ValueError, PermissionError)):
            expand_selected_contextual_inputs(stored, index, cut, "report")
    else:
        expanded = expand_selected_contextual_inputs(stored, index, cut, "report")
        assert expanded["members"][0]["body"]["external_premises"] == [
            dict(product_id=product, member_id="shared")
            for product in ("formal:first", "formal:second")
        ]


@pytest.mark.parametrize("change", [None, "ordinary_member", "inconsistent_group"])
def test_detached_contextual_choice_requires_its_actual_admitted_group(change):
    reference = dict(variant="member", role="formal", occurrence="0", member_id="alternative")
    member = dict(
        record_type="choice_member", local_id="alternative", group_id="group", root="term"
    )
    group: dict[str, Any] = dict(
        record_type="choice", local_id="group", members=[dict(local_id="alternative", root="term")]
    )
    if change == "ordinary_member":
        member["record_type"] = "annotation"
    elif change == "inconsistent_group":
        group["members"][0]["root"] = "other"
    tables = {
        "kb.data_product": {"parent": dict(project_id="project", kind_contract="kind")},
        "kb.data_product_member": {
            ("parent", "alternative"): dict(body=semantic_value(member)),
            ("parent", "group"): dict(body=semantic_value(group)),
        },
        "kb.data_product_partition": {},
        "sem.data_kind_contract": {"kind": {}},
    }
    target = dict(
        output_role="result",
        input_role="formal",
        input_kind="inventory",
        variant="member",
        occurrence_position=True,
        path="/formal_member_support/*/target",
    )

    def check():
        require_detached_output_references(
            row_map=lambda name, *fields: tables[name],
            rows_for=lambda *_args, **_fields: [
                dict(role="formal", product_id="parent", position=0, multiplicity=1)
            ],
            derivation_id="episode",
            project_id="project",
            targets=[target],
            input_roles=[dict(name="formal", kind="inventory", accepted_kind_contracts=["kind"])],
            outputs=[
                cast(
                    WireOutputMember,
                    dict(
                        role="result",
                        product=dict(
                            body=semantic_value(
                                {
                                    "formal_member_support": [
                                        dict(
                                            owner="term", use="choice", position=0, target=reference
                                        )
                                    ],
                                }
                            )
                        ),
                    ),
                )
            ],
        )

    if change is None:
        check()
    else:
        with pytest.raises(ValueError, match="alternative"):
            check()
