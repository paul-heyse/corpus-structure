"""Native projection of frozen row filters; aggregate binding remains authoritative."""

from __future__ import annotations

import json
from typing import Any

import pglast
import pytest
from native_refusals import native_refusal
from pglast import ast
from sqlalchemy import text

from corpus_structure.semantic.prepared_sql import prepare_sql
from semantic.data_operation_binding_support import (
    binding_native_connection as binding_native_connection,
)
from semantic.data_operation_binding_support import (
    binding_source_recipe,
    context,
    evaluate,
    field,
    literal,
)


@pytest.fixture
def selection_connection(binding_native_connection):
    prepared = prepare_sql(binding_source_recipe().codecs.decode(), source="population-filter")
    for index, raw in enumerate(prepared.statements):
        if (
            isinstance(raw.stmt, ast.CreateFunctionStmt)
            and raw.stmt.funcname is not None
            and raw.stmt.funcname[-1].sval
            in {
                "ddo_population_filter",
                "ddo_population_producer_context",
                "ddo_population_scope",
                "ddo_population_evidence_scope",
            }
        ):
            helper = prepared.excerpt(index)
            if raw.stmt.funcname[-1].sval == "ddo_population_filter":
                pglast.parse_plpgsql(helper)
            binding_native_connection.exec_driver_sql(
                helper, execution_options={"no_parameters": True}
            )
    return binding_native_connection


def project(connection, node, *, role="items", choices=None):
    return connection.scalar(
        text(
            "SELECT ops.ddo_population_filter(CAST(:node AS jsonb),:role,CAST(:choices AS jsonb))"
        ),
        {"node": json.dumps(node), "role": role, "choices": json.dumps(choices or {})},
    )


def within(role="items"):
    return {"operator": "range", "operands": [field(role), literal(10), literal(20)]}


@pytest.mark.db
def test_population_filter_keeps_row_qualification_and_defers_cardinality(selection_connection):
    connection = selection_connection
    node = {
        "operator": "forall",
        "roles": ["items"],
        "population": "selected-items",
        "children": [
            within(),
            {"operator": "cardinality", "roles": ["items"], "maximum": 1},
            {"operator": "covers", "operands": [field(), literal(15)]},
        ],
    }
    predicate = project(connection, node)
    assert evaluate(connection, predicate, context(15)) is True
    assert evaluate(connection, predicate, context(5)) is False
    assert evaluate(connection, predicate, context(12, 15)) is True
    # Exact-one is still enforced by the original binding, independently of selection.
    facts = context(12, 15)
    facts["populations"]["selected-items"] = facts["populations"]["retained"]
    assert evaluate(connection, node, facts) is False


@pytest.mark.db
def test_population_filter_keeps_constraints_outside_forall_and_cross_role_children(
    selection_connection,
):
    connection = selection_connection
    node: dict[str, Any] = {
        "operator": "all",
        "children": [
            {"operator": "forall", "roles": ["items"], "population": "selected-items"},
            {"operator": "equal", "operands": [field(), field("right")], "children": [within()]},
        ],
    }
    predicate = project(connection, node)
    assert evaluate(connection, predicate, context(15)) is True
    assert evaluate(connection, predicate, context(25)) is False
    # Cross-role relationship remains present in the original immutable expression.
    assert node["children"][1]["operands"][1]["field"]["role"] == "right"


@pytest.mark.db
def test_population_filter_uses_only_frozen_active_choice(selection_connection):
    node = {
        "operator": "choice",
        "choice_parameter": "which",
        "children": [within(), within("right")],
    }
    predicate = project(selection_connection, node, choices={"which": "items"})
    assert evaluate(selection_connection, predicate, context(15)) is True
    assert evaluate(selection_connection, predicate, context(5)) is False
    with (
        native_refusal("P0001", message="population filter branch is not uniquely frozen"),
        selection_connection.begin_nested(),
    ):
        project(selection_connection, node, choices={"which": "unknown"})
    assert project(selection_connection, node, choices={"which": "items"}) == predicate


@pytest.mark.db
def test_population_filter_optional_parameter_absence_preserves_native_semantics(
    selection_connection,
):
    node = {
        "operator": "optional",
        "children": [
            {
                "operator": "membership",
                "operands": [
                    field(),
                    {"kind": "parameter", "name": "allowed", "value_type": "integer"},
                ],
            }
        ],
    }
    predicate = project(selection_connection, node)
    facts = context(15)
    assert evaluate(selection_connection, predicate, facts) is False
    facts["parameters"] = {}
    facts["parameterdefs"] = {"allowed": {"required": False}}
    assert evaluate(selection_connection, predicate, facts) is True


@pytest.mark.db
@pytest.mark.parametrize(
    ("node", "reason"),
    [
        (
            {"operator": "unreviewed", "roles": ["items"]},
            "unrepresentable selected-population filter operator",
        ),
        (
            {"operator": "absent", "roles": ["items"], "population": "selected-items"},
            "absence cannot define a positive selected population",
        ),
        (
            {
                "operator": "membership",
                "operands": [field(), {"kind": "population", "name": "selected-items"}],
            },
            "selected population filter requires explicit non-circular membership operands",
        ),
        (
            {
                "operator": "optional",
                "children": [
                    within(),
                    {"operator": "cardinality", "roles": ["items"], "maximum": 1},
                ],
            },
            "optional population filter is not a closed row-local predicate",
        ),
    ],
)
def test_population_filter_refuses_unrepresentable_role_qualification(
    selection_connection, node, reason
):
    predicate = project(selection_connection, within())
    assert evaluate(selection_connection, predicate, context(15)) is True
    with native_refusal("P0001", message=reason), selection_connection.begin_nested():
        project(selection_connection, node)
    assert project(selection_connection, within()) == predicate


@pytest.mark.db
def test_population_scope_uses_selected_context_without_relabelling_source_episode(
    selection_connection,
):
    selected_context = {
        "operation_id": "urn:consumer",
        "subject": "comparison:one",
        "subject_definition": "comparison",
        "original_source": "source:analysis",
        "analyzed_scope": {"pair": 1},
    }
    population = {
        "evidence": {"selection": selected_context, "derivation_id": "absent:episode"},
    }
    actual = selection_connection.scalar(
        text(
            "SELECT ops.ddo_population_scope("
            "jsonb_populate_record(NULL::ops.data_population,CAST(:population AS jsonb)))"
        ),
        {"population": json.dumps(population)},
    )
    assert actual == selected_context
    # Original producing context cannot be inferred from consumer labels or a
    # forged evidence field when its authenticated episode is not present.
    producer = selection_connection.scalar(
        text(
            "SELECT ops.ddo_population_producer_context("
            "jsonb_populate_record(NULL::ops.data_population,CAST(:population AS jsonb)))"
        ),
        {"population": json.dumps(population)},
    )
    assert producer is None


@pytest.mark.db
def test_population_filter_defers_optional_global_coverage_with_original_missing_semantics(
    selection_connection,
):
    aggregate = {
        "operator": "optional",
        "children": [
            {
                "operator": "covers",
                "operands": [
                    field(),
                    {
                        "kind": "parameter",
                        "name": "required",
                        "value_type": "integer",
                    },
                ],
            }
        ],
    }
    node = {"operator": "all", "children": [within(), aggregate]}
    predicate = project(selection_connection, node)
    facts = context(15)
    facts["parameterdefs"] = {"required": {"required": False}}
    assert evaluate(selection_connection, predicate, facts) is True
    assert evaluate(selection_connection, node, facts) is True
    facts["parameters"]["required"] = [15, 20]
    assert evaluate(selection_connection, predicate, facts) is True
    assert evaluate(selection_connection, node, facts) is False
