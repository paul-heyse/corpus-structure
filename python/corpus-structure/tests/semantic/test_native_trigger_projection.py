"""Independent trigger policy expectations over a captured physical projection."""

from dataclasses import FrozenInstanceError, replace

import pytest
from pglast import ast
from sqlalchemy import Column, ForeignKey, Integer, MetaData, Table

from corpus_structure.schema.integrity import IntegrityPolicy, RolePolicy
from corpus_structure.semantic.native_objects import NativeAuthoringError, NativeIdentity
from corpus_structure.semantic.target_installation import (
    capture_trigger_inputs,
    target_trigger_programs,
)


@pytest.fixture
def physical_target(monkeypatch):
    from corpus_structure.semantic import native_protocol_authoring

    role = RolePolicy("trigger_publisher", "publisher", False, (), True)
    metadata = MetaData(
        info={
            "physical_sources": {},
            "integrity_policy": IntegrityPolicy({"publisher": role}, {}),
        }
    )
    Table("task", metadata, Column("id", Integer, primary_key=True), schema="ops")
    Table("unrelated", metadata)
    intrinsic = Table("intrinsic", metadata, schema="ops")
    Table(
        "pending_parent",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("self_id", ForeignKey("ops.pending_parent.id")),
        schema="ops",
        info={"immutability": "pending-content"},
    )
    Table(
        "pending_child",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("parent_id", ForeignKey("ops.pending_parent.id")),
        schema="ops",
        info={"immutability": "pending-content"},
    )
    Table(
        "archive",
        metadata,
        schema="ops",
        info={"immutability": "deployment", "frontier_guard": "guarded", "archive_role": "input"},
    )
    Table("physical_contract", metadata, schema="sem")
    monkeypatch.setattr(
        native_protocol_authoring,
        "data_operation_immutable_relations",
        lambda target, sources: (intrinsic,),
    )
    return metadata


def observed(inputs):
    result = []
    for declaration in target_trigger_programs(inputs):
        body = declaration.body
        assert isinstance(body, ast.CreateTrigStmt)
        assert body.relation is not None and body.funcname is not None
        result.append(
            (
                body.relation.schemaname,
                body.relation.relname,
                body.trigname,
                tuple(part.sval for part in body.funcname),
                body.events,
                body.row,
                declaration.owner,
            )
        )
    return result


def test_captured_trigger_policy_has_independent_expected_inventory(physical_target):
    inputs = capture_trigger_inputs(physical_target)
    assert observed(inputs) == [
        (
            "ops",
            "task",
            "zz_execution_task",
            ("ops", "guard_execution_task"),
            20,
            True,
            "trigger_publisher",
        ),
        (
            "ops",
            "archive",
            "semantic_immutable",
            ("sem", "refuse_immutable_mutation"),
            56,
            False,
            "trigger_publisher",
        ),
        (
            "ops",
            "archive",
            "ddo_read_frontier_guard",
            ("ops", "ddo_refuse_post_acquisition_graph_write"),
            60,
            False,
            "trigger_publisher",
        ),
        (
            "ops",
            "archive",
            "finalized_release",
            ("sem", "guard_finalized_insert"),
            4,
            True,
            "trigger_publisher",
        ),
        (
            "ops",
            "intrinsic",
            "semantic_immutable",
            ("sem", "refuse_immutable_mutation"),
            56,
            False,
            "trigger_publisher",
        ),
        (
            "ops",
            "pending_child",
            "pdf_shared_content_mutation",
            ("ops", "pdf_shared_stream_mutation_guard"),
            28,
            True,
            "trigger_publisher",
        ),
        (
            "ops",
            "pending_child",
            "pdf_shared_content_truncate",
            ("ops", "pdf_shared_stream_mutation_guard"),
            32,
            False,
            "trigger_publisher",
        ),
        (
            "ops",
            "pending_parent",
            "pdf_shared_content_mutation",
            ("ops", "pdf_shared_stream_mutation_guard"),
            24,
            True,
            "trigger_publisher",
        ),
        (
            "ops",
            "pending_parent",
            "pdf_shared_content_truncate",
            ("ops", "pdf_shared_stream_mutation_guard"),
            32,
            False,
            "trigger_publisher",
        ),
        (
            "sem",
            "physical_contract",
            "semantic_immutable",
            ("sem", "refuse_immutable_mutation"),
            56,
            False,
            "trigger_publisher",
        ),
    ]
    assert all(isinstance(row.relation, NativeIdentity) for row in inputs.relations)
    assert all(row.relation.name != "unrelated" for row in inputs.relations)
    assert all(
        isinstance(item.body, ast.CreateTrigStmt) for item in target_trigger_programs(inputs)
    )


def test_trigger_rendering_uses_only_the_immutable_acquired_values(physical_target):
    inputs = capture_trigger_inputs(physical_target)
    before = observed(inputs)
    physical_target.tables["ops.archive"].info.clear()
    physical_target.remove(physical_target.tables["ops.pending_child"])
    physical_target.info.clear()
    assert observed(inputs) == before
    with pytest.raises(FrozenInstanceError):
        field = "publisher"
        setattr(inputs, field, "another_owner")


def test_trigger_identity_must_name_a_physical_table():
    from corpus_structure.semantic.native_objects import native_before_trigger

    with pytest.raises(NativeAuthoringError, match="physical table identity"):
        native_before_trigger(
            NativeIdentity("view", "ops", "task"),
            "invalid_parent",
            ("ops", "guard_execution_task"),
            events=("update",),
        )


def test_quoted_relation_names_become_plain_values_and_keep_sql_quoting(physical_target):
    from pglast.stream import RawStream
    from sqlalchemy.sql.elements import quoted_name

    Table(
        quoted_name("Quoted Relation", True),
        physical_target,
        schema=quoted_name("Odd Schema", True),
        info={"immutability": "immutable"},
    )
    inputs = capture_trigger_inputs(physical_target)
    row = next(item for item in inputs.relations if item.relation.name == "Quoted Relation")
    assert type(row.relation.schema) is str
    assert type(row.relation.name) is str
    assert any(
        'ON "Odd Schema"."Quoted Relation"' in RawStream()(item.body)
        for item in target_trigger_programs(inputs)
    )


def test_changed_trigger_projection_moves_the_program_input_key(physical_target):
    from corpus_structure.semantic.code_identity import CodeIdentity
    from corpus_structure.semantic.native_program_store import input_key
    from corpus_structure.semantic.target_installation import NativeGeneratorInputs

    # This is a controlled key-consumer fixture. Production eligibility still
    # requires the complete authenticated generator workload.
    inputs = NativeGeneratorInputs(
        physical_sources=(),
        linkml_types=b"types",
        logical_sources=(),
        model_sources=(),
        pdf_actions=None,
        pdf_sources=(),
        extra_sources=(),
        resource_sources=(),
        module_sources=(),
        analysis_runtime=(),
        native_library_runtime=(),
        code_identity=CodeIdentity((), (), (), (), b"controlled identity"),
        trigger_inputs=capture_trigger_inputs(physical_target),
    )
    before = input_key(inputs)
    changed = replace(inputs.trigger_inputs, publisher="other_publisher")
    assert input_key(replace(inputs, trigger_inputs=changed)) != before
    assert input_key(inputs) == before
