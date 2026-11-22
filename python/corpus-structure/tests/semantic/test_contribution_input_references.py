"""Evidence belongs to its producing report, independently of reusable domain members."""

from types import SimpleNamespace
from typing import Any, cast

import pytest

from corpus_structure.semantic._data_operation_wire import WireOutputMember
from corpus_structure.semantic.contribution_input_references import (
    check_contribution_input_support,
    pack_contribution_input_support,
    project_contribution_input_support,
    require_selected_contribution_input_support,
    split_contribution_evidence,
)
from corpus_structure.semantic.contributions import contribution_identity
from corpus_structure.semantic.data_operation_values import decode_semantic_value, semantic_value
from corpus_structure.semantic.detached_reference_resolution import (
    require_detached_output_references,
)
from corpus_structure.semantic.observations import source_python, source_value
from corpus_structure.semantic.reference_resolution import (
    ProducingReferenceBindings,
    ProducingReferenceInput,
)


def contribution(
    product="construction:original", *, dependencies=(), text="literal"
) -> dict[str, Any]:
    row = dict(
        semantic_type="structural.located_participant",
        computation_dependencies=dependencies,
        value=source_value(
            dict(
                text=text,
                nullable=None,
                absent_is_not_null=False,
                primary_node=dict(product_id=product, member_id="node:shared"),
            )
        ),
    )
    row["contribution_id"] = contribution_identity(row)
    return row


def roles(product="construction:original", *, position=7):
    return (
        SimpleNamespace(
            role="constructions",
            members=(
                SimpleNamespace(
                    product=product,
                    member=None,
                    multiplicity=1,
                    reference_position=position,
                ),
            ),
        ),
        SimpleNamespace(role="formal", members=()),
    )


def report(rows, support):
    return dict(
        members=[
            dict(
                member_id="contribution:" + row["contribution_id"],
                body={**row, "candidate_type": "contribution"},
            )
            for row in rows
        ],
        **support,
    )


def test_domain_identity_excludes_only_structural_evidence_and_keeps_null_and_source_meaning():
    first, second = contribution(), contribution("construction:another")
    assert first["contribution_id"] == second["contribution_id"]
    clean, evidence = split_contribution_evidence(first)
    assert evidence == [
        ("value/primary_node", 0, dict(product_id="construction:original", member_id="node:shared"))
    ]
    assert source_python(clean["value"]) == dict(
        text="literal", nullable=None, absent_is_not_null=False
    )
    assert contribution(text="changed")["contribution_id"] != first["contribution_id"]
    assert (
        contribution(dependencies=("actual:domain-premise",))["contribution_id"]
        != first["contribution_id"]
    )
    authored = dict(semantic_type="authored.external_target", value=first["value"])
    assert split_contribution_evidence(authored) == (authored, [])


def test_fresh_contribution_evidence_names_original_input_position_and_keeps_body_once():
    original = contribution()
    rows, support = pack_contribution_input_support((original,), roles())
    identifier = "contribution:" + original["contribution_id"]
    assert support["construction_support"] == [
        dict(
            member_id=identifier,
            field="value/primary_node",
            position=0,
            target=dict(
                variant="member", role="constructions", occurrence="7", member_id="node:shared"
            ),
        )
    ]
    assert support["formal_support"] == support["inherited_support"] == []
    assert "primary_node" not in source_python(rows[0]["value"])
    check_contribution_input_support(report(rows, support))


def test_equal_domain_members_retain_distinct_independent_producer_evidence():
    first, second = contribution(), contribution("construction:second")
    selected_roles = (
        SimpleNamespace(
            role="constructions",
            members=(
                roles()[0].members[0],
                SimpleNamespace(
                    product="construction:second", member=None, multiplicity=1, reference_position=8
                ),
            ),
        ),
    )
    rows, support = pack_contribution_input_support((first, second), selected_roles)
    assert len(rows) == 1
    assert [slot["target"]["occurrence"] for slot in support["construction_support"]] == ["7", "8"]
    assert {slot["position"] for slot in support["construction_support"]} == {0}
    check_contribution_input_support(report(rows, support))
    collected = (
        (
            first["contribution_id"],
            "value/primary_node",
            0,
            dict(product_id="construction:second", member_id="node:shared"),
        ),
    )
    rows_from_cache, captured = pack_contribution_input_support(
        (first,), selected_roles, primary_evidence=collected
    )
    assert rows_from_cache == rows and captured == support


def test_inherited_predicate_member_keeps_original_owner_when_current_ledger_changes():
    original = contribution()
    rows, support = pack_contribution_input_support(
        (original,), roles(position=19), inherited=(original,)
    )
    identifier = "contribution:" + original["contribution_id"]
    assert support["construction_support"] == support["formal_support"] == []
    assert support["inherited_support"] == [
        dict(
            member_id=identifier,
            target=dict(variant="member", role="predicates", member_id=identifier),
        )
    ]
    check_contribution_input_support(report(rows, support))


def test_derived_member_uses_actual_inherited_domain_dependency_without_relabelling_its_evidence():
    original = contribution("construction:not-current")
    derived = contribution(
        "construction:not-current", dependencies=(original["contribution_id"],), text="derived"
    )
    rows, support = pack_contribution_input_support(
        (original, derived), roles(), inherited=(original,)
    )
    assert len(support["inherited_support"]) == 1
    assert support["construction_support"] == []
    assert rows[1]["computation_dependencies"] == (original["contribution_id"],)
    with pytest.raises(ValueError, match="actual producing inputs"):
        pack_contribution_input_support(
            (original, contribution("construction:not-current", text="unrelated")),
            roles(),
            inherited=(original,),
        )


def test_working_projection_uses_original_predicate_bindings_not_current_ledger(monkeypatch):
    from corpus_structure.semantic import reference_resolution

    original = contribution()
    rows, support = pack_contribution_input_support((original,), roles())
    bindings = ProducingReferenceBindings(
        "original:episode",
        (
            ProducingReferenceInput(
                "constructions",
                "construction:original",
                "kind:construction",
                None,
                occurrence="7",
                occurrence_position=True,
            ),
        ),
    )
    monkeypatch.setattr(
        reference_resolution, "selected_producing_reference_bindings", lambda member: bindings
    )
    (working,) = project_contribution_input_support(report(rows, support), SimpleNamespace())
    assert source_python(working["value"])["primary_node"] == dict(
        product_id="construction:original", member_id="node:shared"
    )
    assert working["contribution_id"] == original["contribution_id"]


def test_choice_order_survives_support_split_across_formal_and_construction_roles(monkeypatch):
    from corpus_structure.semantic import reference_resolution

    original = contribution()
    meaning = source_python(original["value"])
    meaning["primary_choices"] = [
        dict(product_id="formal:original", member_id="alternative:first"),
        dict(product_id="construction:original", member_id="alternative:second"),
    ]
    original["value"] = source_value(meaning)
    original["contribution_id"] = contribution_identity(original)
    selected_roles = (
        *roles()[:1],
        SimpleNamespace(
            role="formal",
            members=(
                SimpleNamespace(
                    product="formal:original",
                    member=None,
                    multiplicity=1,
                    reference_position=3,
                ),
            ),
        ),
    )
    rows, support = pack_contribution_input_support((original,), selected_roles)
    bindings = ProducingReferenceBindings(
        "original:episode",
        tuple(
            ProducingReferenceInput(
                role, product, "kind", None, occurrence=position, occurrence_position=True
            )
            for role, product, position in (
                ("formal", "formal:original", "3"),
                ("constructions", "construction:original", "7"),
            )
        ),
    )
    monkeypatch.setattr(
        reference_resolution, "selected_producing_reference_bindings", lambda member: bindings
    )
    (working,) = project_contribution_input_support(report(rows, support), SimpleNamespace())
    assert source_python(working["value"])["primary_choices"] == meaning["primary_choices"]


@pytest.mark.parametrize("change", ["owner", "duplicate", "gap", "unpacked"])
def test_report_support_refuses_orphans_duplicate_slots_gaps_and_old_persisted_evidence(change):
    original = contribution()
    rows, support = pack_contribution_input_support((original,), roles())
    body = report(rows, support)
    slot = body["construction_support"][0]
    if change == "owner":
        slot["member_id"] = "contribution:other"
    elif change == "duplicate":
        body["construction_support"].append(dict(slot))
    elif change == "gap":
        slot["position"] = 1
    else:
        body["members"][0]["body"] = {**original, "candidate_type": "contribution"}
    with pytest.raises(ValueError):
        check_contribution_input_support(body)


@pytest.mark.parametrize(
    "mode,change",
    [
        ("live", None),
        ("live", "body"),
        ("live", "current_parent"),
        ("detached", None),
        ("detached", "body"),
    ],
)
def test_inherited_reference_requires_exact_parent_and_original_member_body(mode, change):
    original = contribution()
    clean, support = pack_contribution_input_support((original,), roles(), inherited=(original,))
    body = decode_semantic_value(semantic_value(report(clean, support)))
    identifier = body["members"][0]["member_id"]
    parent_body = dict(body["members"][0]["body"])
    if change == "body":
        parent_body["value"] = source_value(dict(text="substituted original meaning"))
    target = dict(
        output_role="result",
        path="/inherited_support/*/target",
        input_role="predicates",
        input_kind="inventory",
        variant="member",
    )
    pins = [dict(role="predicates", product_id="original:predicate", position=0, multiplicity=1)]
    current = [dict(pin) for pin in pins]
    if change == "current_parent":
        current[0]["product_id"] = "same-content:other-predicate"
    tables = {
        "ops.demand_use": {
            "use": dict(
                id="use", derivation_id="episode", fate="fulfilled", selection={"inputs": current}
            )
        },
        "ops.data_derivation": {"episode": dict(release_id="release")},
        "sem.data_operation_definition": {
            ("release", "scoped"): dict(
                support_contract={"reference_targets": [target]},
                input_roles=[
                    dict(name="predicates", kind="inventory", accepted_kind_contracts=["kind"])
                ],
            )
        },
        "kb.data_product": {
            "original:predicate": dict(
                project_id="project", kind_contract="kind", canonical_body=semantic_value({})
            )
        },
        "kb.data_product_member": {
            ("original:predicate", identifier): dict(body=semantic_value(parent_body))
        },
        "kb.data_product_partition": {},
        "sem.data_kind_contract": {"kind": {}},
    }

    def check():
        if mode == "live":
            scope = SimpleNamespace(
                index=SimpleNamespace(
                    mapping=lambda name, _: tables[name], rows_for=lambda name, **fields: pins
                ),
                cut=SimpleNamespace(record={"project_id": "project"}),
            )
            selected = SimpleNamespace(
                body=body,
                use_id="use",
                derivation_id="episode",
                operation_id="scoped",
                output={"role": "result"},
            )
            require_selected_contribution_input_support(scope, selected)
        else:
            require_detached_output_references(
                row_map=lambda name, *fields: tables[name],
                rows_for=lambda name, **fields: pins,
                derivation_id="episode",
                project_id="project",
                targets=[target],
                input_roles=[
                    dict(name="predicates", kind="inventory", accepted_kind_contracts=["kind"])
                ],
                outputs=[
                    cast(
                        WireOutputMember,
                        dict(role="result", product=dict(body=semantic_value(body))),
                    )
                ],
            )

    if change is None:
        check()
    else:
        with pytest.raises(ValueError):
            check()
