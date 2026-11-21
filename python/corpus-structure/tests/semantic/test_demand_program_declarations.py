"""Demand producers retain explicit determinant inputs and native ABI custody."""

import json

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.schema.integrity import role_name
from corpus_structure.semantic.data_operation_subjects import subject_scope_values
from corpus_structure.semantic.data_validity_native import data_validity_programs
from corpus_structure.semantic.demand_authority_native import demand_authority_programs
from corpus_structure.semantic.demand_registration_native import demand_intent_programs
from corpus_structure.semantic.demand_result_native import demand_result_programs
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import (
    INTERNAL_PROGRAM,
    NativeProgramAccess,
    execute_native_sql,
)
from corpus_structure.semantic.native_program import NativeRoutine


def declarations():
    model = get_metadata()
    return (
        *demand_authority_programs(model, subject_scopes=subject_scope_values()),
        *demand_intent_programs(
            model, protocol=model.info["physical_sources"]["data-operation-native.yaml"]
        ),
        *demand_result_programs(model),
        *data_validity_programs(model),
    )


def test_demand_producers_hold_structured_private_programs_until_authoring(monkeypatch):
    def refuse_render(self):
        raise AssertionError("demand producer eagerly rendered a native routine")

    monkeypatch.setattr(NativeRoutine, "render", refuse_render)
    programs = declarations()
    assert len({item.identity for item in programs}) == len(programs)
    assert {item.identity.name for item in programs} >= {
        "register_data_demand",
        "cancel_data_demand",
        "record_data_fate",
        "close_data_population",
        "read_demand_result",
        "revoke_data_support",
        "ddo_valid_closure",
        "ddo_node_valid",
    }
    for declaration in programs:
        assert declaration.source == "data-operations:forward"
        assert declaration.owner == role_name("publisher")
        # The wire authoring owner renames these implementation declarations and
        # owns the separate public purpose wrappers.
        if declaration.identity.name == "acquire_data_read_context":
            assert declaration.access == NativeProgramAccess(purposes=("read", "write", "evaluate"))
        else:
            assert declaration.access == INTERNAL_PROGRAM


def test_validity_and_authority_default_arguments_keep_their_full_native_identity():
    programs = {item.identity.name: item for item in declarations()}
    closure = programs["ddo_valid_closure"]
    assert closure.identity.arguments == ("text[]", "text[]", "ops.data_demand_read", "text[]")
    assert tuple(item.default is not None for item in closure.routine.parameters) == (
        False,
        False,
        True,
        True,
    )
    assert closure.routine.returns.setof is True
    assert tuple(name for name, _ in closure.routine.table_columns) == ("kind", "id", "valid")
    node = programs["ddo_node_valid"]
    assert node.identity.arguments == ("text", "text", "ops.data_demand_read")
    assert node.routine.parameters[-1].default is not None
    discovery = programs["ddo_discovery_role_population"]
    assert discovery.routine.parameters[-1].default is not None
    assert discovery.identity.arguments[-1] == "ops.data_demand_read"


def test_selected_typed_demand_programs_enforce_closed_semantic_controls(infrastructure_rollback):
    connection = infrastructure_rollback
    connection.exec_driver_sql("CREATE SCHEMA ops")
    programs = {item.identity.name: item for item in declarations()}
    for name in (
        "ddo_replicate_required",
        "ddo_support_reference_node",
        "ddo_result_bytes_refusal",
    ):
        execute_native_sql(connection, programs[name].routine.render())
    for value, expected in (
        ("deterministic-single-result", False),
        ("retained-observation-single-result", False),
        ("explicit-replicates", True),
    ):
        assert (
            connection.scalar(text("SELECT ops.ddo_replicate_required(:value)"), {"value": value})
            is expected
        )
    for value in (None, "", "independent-fresh"):
        with pytest.raises(DBAPIError) as refused, connection.begin_nested():
            connection.execute(text("SELECT ops.ddo_replicate_required(:value)"), {"value": value})
        assert getattr(refused.value.orig, "sqlstate", None) == "23514"
    for reference, expected in (
        (
            {"kind": "original-source", "admission_id": "admission"},
            {"kind": "original", "id": "admission"},
        ),
        (
            {"admission_use_id": "current", "derivation_id": "historical"},
            {"kind": "use", "id": "current"},
        ),
        ({"derivation_id": "historical"}, {"kind": "episode", "id": "historical"}),
    ):
        assert (
            connection.scalar(
                text("SELECT ops.ddo_support_reference_node(CAST(:value AS jsonb))"),
                {"value": json.dumps(reference)},
            )
            == expected
        )
    with pytest.raises(DBAPIError, match="exceeds max_bytes"), connection.begin_nested():
        connection.execute(text("SELECT ops.ddo_result_bytes_refusal()"))


def test_context_acquisition_authenticates_read_without_constructing_frontier(monkeypatch):
    from corpus_structure.semantic.demand_result_native import _read_demand_result

    def refuse_frontier(*args, **kwargs):
        raise AssertionError("compact context acquisition constructed a result page")

    monkeypatch.setattr("corpus_structure.semantic.demand_result_native.read_page", refuse_frontier)
    routine = _read_demand_result(get_metadata(), context_only=True)
    sql = routine.render()
    assert routine.name == "acquire_data_read_context"
    assert "ddo_require_read_current" in sql
    assert "trust snapshot changed; reacquire demand read" in sql
    assert "read scope differs from its pinned acquisition" in sql
    assert "jsonb_build_object('demand_id'" in sql
    assert "ops.ddo_authorize" in sql
