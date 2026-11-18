"""Independent finite-set and captured-source expectations for DDO physical derivation."""

from pathlib import Path

import pytest
import yaml
from linkml_runtime.utils.schemaview import SchemaView
from sqlalchemy import ARRAY, Column
from sqlalchemy.sql.type_api import TypeEngine

from corpus_structure.schema.model import ModelError
from corpus_structure.schema.physical import (
    compile_physical,
    physical_source_closure,
    physical_sources_id,
)
from corpus_structure.schema.relational import compile_metadata, render_typed_column_class
from corpus_structure.semantic import _data_operation_fates
from corpus_structure.semantic.data_operation_protocol import protocol_value_sets
from corpus_structure.semantic.metadata import PHYSICAL_MODEL
from corpus_structure.semantic.typed_generation import generated_fates

HISTORY = (
    "known-absent",
    "unknown",
    "unavailable",
    "invalid",
    "closed",
    "awaiting-discovery",
    "awaiting-inputs",
    "awaiting-population",
    "not-applicable",
    "failed",
    "cancelled",
    "partial",
    "attached",
    "fulfilled",
)


def captured():
    return physical_source_closure(
        PHYSICAL_MODEL.name, lambda name: PHYSICAL_MODEL.with_name(name).read_bytes()
    )


def test_captured_protocol_owns_distinct_fate_and_selector_sets():
    sources = captured()
    values = protocol_value_sets(sources["data-operation-native.yaml"])
    assert values["RecordableFate"] == HISTORY[:-2]
    assert values["HistoricalFate"] == HISTORY
    assert values["VisibleFate"] == (*HISTORY[:7], "awaiting-external", *HISTORY[7:], "waiting")
    assert values["RevocationSelectorKind"] == (
        "derivation",
        "recipe",
        "runtime",
        "product",
        "original-source",
        "original-admission",
    )
    md = compile_physical(sources)
    fate = md.tables["ops.demand_use"].c.fate
    assert fate.info["enum"] == HISTORY
    assert all(
        "'waiting'" not in str(item.sqltext)
        for item in fate.table.constraints
        if hasattr(item, "sqltext")
    )
    assert Path(_data_operation_fates.__file__).read_text() == generated_fates()


def test_protocol_only_edit_changes_physical_identity_and_constraint():
    sources = captured()
    before = compile_physical(sources).tables["ops.demand_use"]
    protocol = yaml.safe_load(sources["data-operation-native.yaml"])
    protocol["definitions"]["historical_fate"]["enum"].remove("partial")
    changed = sources | {"data-operation-native.yaml": yaml.safe_dump(protocol).encode()}
    after = compile_physical(changed).tables["ops.demand_use"]
    assert physical_sources_id(sources) != physical_sources_id(changed)
    assert tuple(after.c.fate.info["enum"]) == tuple(
        value for value in HISTORY if value != "partial"
    )
    before_checks = {str(c.name) for c in before.constraints if hasattr(c, "sqltext")}
    after_checks = {str(c.name) for c in after.constraints if hasattr(c, "sqltext")}
    assert before_checks != after_checks


def test_missing_protocol_cannot_be_recovered_from_installed_model():
    sources = captured()
    del sources["data-operation-native.yaml"]
    with pytest.raises(ModelError, match="missing physical"):
        compile_physical(sources)
    with pytest.raises(ModelError, match="require compile_physical"):
        compile_metadata(SchemaView(str(PHYSICAL_MODEL)), target="semantic")


@pytest.mark.parametrize("sql_type", [TypeEngine(), ARRAY(TypeEngine())])
def test_unknown_typed_column_cannot_degrade_to_object(sql_type):
    with pytest.raises(ModelError, match="unsupported typed column"):
        render_typed_column_class("Unknown", (Column("value", sql_type),))


@pytest.mark.parametrize(
    "status",
    [
        "not-applicable",
        "awaiting-inputs",
        "awaiting-population",
        "unknown",
        "invalid",
        "unavailable",
    ],
)
def test_missing_binding_states_have_explicit_recordable_fates(status):
    from corpus_structure.semantic.data_operation_bindings import recordable_binding_fate

    assert recordable_binding_fate(status) == status


def test_ready_binding_cannot_be_recorded_as_missing_work():
    from corpus_structure.semantic.data_operation_bindings import recordable_binding_fate

    with pytest.raises(ValueError, match="native request attachment"):
        recordable_binding_fate("ready")


def test_task_guard_uses_captured_protocol_states_and_transitions():
    from corpus_structure.semantic.data_operation_protocol import data_task_lifecycle
    from corpus_structure.semantic.target_installation import target_task_guard_sql

    sources = captured()
    content = sources["data-operation-native.yaml"]
    policy = data_task_lifecycle(content)
    assert policy == {
        "initial": "pending",
        "running": "running",
        "terminal": ["done", "empty", "failed", "cancelled"],
        "receipt_required": ["done", "empty", "failed"],
        "new_attempt": [["pending", "running"], ["running", "running"]],
        "same_attempt": [
            ["running", "pending"],
            ["running", "done"],
            ["running", "empty"],
            ["running", "failed"],
            ["running", "cancelled"],
        ],
    }
    rendered = target_task_guard_sql(content)
    assert "__DDO_TASK_" not in rendered
    assert "NEW.attempt<>OLD.attempt+1" in rendered
    assert "NEW.claimed_by IS DISTINCT FROM OLD.claimed_by" in rendered
    assert "('running','failed')" in rendered
    changed = yaml.safe_load(content)
    changed["definitions"]["data_task_state"]["x-ddo-lifecycle"]["same_attempt"].remove(
        ["running", "pending"]
    )
    modified = target_task_guard_sql(yaml.safe_dump(changed).encode())
    assert "('running','pending')" not in modified
    assert "('running','failed')" in modified


def test_task_protocol_rejects_unclassified_state():
    from corpus_structure.semantic.data_operation_protocol import data_task_lifecycle

    protocol = yaml.safe_load(captured()["data-operation-native.yaml"])
    protocol["definitions"]["data_task_state"]["enum"].append("forgotten")
    with pytest.raises(ValueError, match="unclassified state"):
        data_task_lifecycle(yaml.safe_dump(protocol).encode())


def test_member_context_requires_explicit_subject_definition():
    from corpus_structure.semantic.data_operation_wire import schema_closure, validate_wire_schema

    definitions = yaml.safe_load(captured()["data-operation-native.yaml"])["definitions"]
    schema = schema_closure(definitions["member_context"], definitions)
    context = {
        "subject": "same-address",
        "subject_definition": "original-source-view",
        "original_source": "document",
        "analyzed_scope": {"page": 2},
    }
    assert validate_wire_schema(schema, context) == context
    for invalid in (
        {key: value for key, value in context.items() if key != "subject_definition"},
        {**context, "subject_definition": ""},
    ):
        with pytest.raises(ValueError, match="schema"):
            validate_wire_schema(schema, invalid)
