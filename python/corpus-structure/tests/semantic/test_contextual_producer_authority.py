"""Native role permission distinguishes retained input authority from executable edges."""

import pytest
from sqlalchemy import bindparam, func, select
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.semantic.contextual_admission_native import _contextual_producer_allowed


@pytest.mark.parametrize(
    "selected_role,source,source_set,direction,required,potential,producer,expected",
    (
        ("query", "frozen-source-set", "contextual-query", "input", (), (), "retained-query", True),
        (
            "inventory",
            "frozen-source-set",
            "contextual-inventory",
            "input",
            (),
            (),
            "retained-inventory",
            True,
        ),
        (
            "other",
            "frozen-source-set",
            "contextual-query",
            "input",
            (),
            (),
            "retained-query",
            False,
        ),
        ("query", "frozen-source-set", None, "input", (), (), "retained-query", False),
        ("query", "frozen-source-set", "", "input", (), (), "retained-query", False),
        ("query", "same-original", "contextual-query", "input", (), (), "retained-query", False),
        (
            "query",
            "frozen-source-set",
            "contextual-query",
            "output",
            (),
            (),
            "retained-query",
            False,
        ),
        (
            "vectors",
            "selected-inventory-and-query",
            None,
            "input",
            ("vectors",),
            (),
            "vectors",
            True,
        ),
        (
            "vectors",
            "selected-inventory-and-query",
            None,
            "input",
            (),
            ("vectors",),
            "vectors",
            True,
        ),
        (
            "vectors",
            "selected-inventory-and-query",
            None,
            "input",
            ("vectors",),
            (),
            "undeclared-vectors",
            False,
        ),
    ),
    ids=(
        "selected-query",
        "selected-inventory",
        "other-role",
        "missing-set",
        "empty-set",
        "other-source",
        "output-role",
        "required-local",
        "potential-local",
        "undeclared-local",
    ),
)
def test_native_contextual_producer_permission_follows_the_admitted_input_role(
    infrastructure_rollback,
    selected_role,
    source,
    source_set,
    direction,
    required,
    potential,
    producer,
    expected,
):
    roles = [
        dict(
            name="query" if selected_role == "other" else selected_role,
            direction=direction,
            support=dict(source=source, source_set=source_set),
        )
    ]
    contract = select(
        bindparam("roles", roles, type_=JSONB).label("roles"),
        bindparam("dependencies", dict(required=required, potential=potential), type_=JSONB).label(
            "dependencies"
        ),
    ).cte("admitted_contract")
    actual = infrastructure_rollback.scalar(
        select(
            _contextual_producer_allowed(
                contract.c.roles, contract.c.dependencies, selected_role, producer
            )
        )
    )
    assert actual is expected


@pytest.mark.parametrize(
    "corruption", (None, "name", "product", "member", "episode", "use", "output")
)
def test_native_frozen_role_binding_checks_the_exact_selected_proof(native_rollback, corruption):
    """Controlled proof values assess the binding predicate, not publication standing."""
    from copy import deepcopy

    from corpus_structure.semantic.data_operation_source_sets import (
        FrozenSourceSet,
        source_sets_record,
    )
    from semantic.test_data_operation_source_sets import selected_entry

    sets = source_sets_record(
        (FrozenSourceSet.from_selected("contextual-query", (selected_entry(),)),)
    )
    scope = sets["contextual-query"]
    proof = scope["acquisition"]["reads"][0]["proofs"][0]
    row = deepcopy(scope["entries"][0])
    row["support_references"] = [deepcopy(proof["support"])]
    row["support_evidence"] = dict(producer_output=deepcopy(proof["output"]))
    role = dict(support=dict(source="frozen-source-set", source_set="contextual-query"))
    if corruption == "name":
        role["support"]["source_set"] = "another-named-set"
    elif corruption in {"product", "member"}:
        row[corruption] = "foreign-selected-value"
    elif corruption in {"episode", "use"}:
        row["support_references"][0][
            "derivation_id" if corruption == "episode" else "admission_use_id"
        ] = "foreign-producing-support"
    elif corruption == "output":
        row["support_evidence"]["producer_output"]["position"] += 1
    actual = native_rollback.connection.scalar(
        select(
            func.ops.ddo_binding_source(
                bindparam("role", role, type_=JSONB),
                bindparam("row", row, type_=JSONB),
                "source:one",
                bindparam("sets", sets, type_=JSONB),
            )
        )
    )
    assert actual is (corruption is None)
