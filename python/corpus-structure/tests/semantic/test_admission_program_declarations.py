"""Private admission producers own typed programs and their family responsibilities."""

import pytest
from sqlalchemy import Column, MetaData, Table, insert, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.schema.integrity import role_name
from corpus_structure.semantic.artifact_admission_native import (
    artifact_admission_native_programs,
    artifact_admission_native_sql,
)
from corpus_structure.semantic.definition_admission_native import (
    definition_admission_native_programs,
    definition_admission_native_sql,
)
from corpus_structure.semantic.execution_evidence_leaf import (
    execution_evidence_leaf_native_programs,
    execution_evidence_leaf_native_sql,
)
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_inventory import update_function_inventory
from corpus_structure.semantic.native_objects import INTERNAL_PROGRAM, execute_native_sql
from corpus_structure.semantic.native_program import NativeRoutine
from corpus_structure.semantic.native_program_registry import ProgramValidity


@pytest.mark.parametrize("family", ("artifact", "definition"))
def test_admission_programs_own_exact_family_roles_and_private_capture(family, monkeypatch):
    produce = {
        "artifact": artifact_admission_native_programs,
        "definition": definition_admission_native_programs,
    }[family]
    capture = {
        "artifact": artifact_admission_native_sql,
        "definition": definition_admission_native_sql,
    }[family]
    declarations = produce()
    roles = {
        declaration.identity.name: declaration.validity
        for declaration in declarations
        if declaration.validity
    }
    assert roles == {
        f"ddo_require_{family}_completion": (ProgramValidity(family, "completion_guard"),),
        f"ddo_{family}_dependencies_valid": (ProgramValidity(family, "validator"),),
    }
    inventory = {}
    update_function_inventory(inventory, capture())
    for declaration in declarations:
        assert declaration.source == "data-operations:forward"
        assert declaration.owner == role_name("publisher")
        assert declaration.access == INTERNAL_PROGRAM
        signature = (
            "ops."
            + declaration.identity.name
            + "("
            + ",".join(declaration.identity.arguments)
            + ")"
        )
        observed = inventory.pop(signature)
        assert observed["execute_roles"] == []
        assert observed["owner"] == declaration.owner
    assert inventory == {}

    def refuse_render(self):
        raise AssertionError("producer rendered its structured program")

    monkeypatch.setattr(NativeRoutine, "render", refuse_render)
    assert len(produce()) == {"artifact": 3, "definition": 5}[family]
    leaves = execution_evidence_leaf_native_programs(get_metadata())
    assert len(leaves) == 1
    assert leaves[0].validity == ()
    assert leaves[0].identity.name == "ddo_cpu_execution_leaf"
    assert leaves[0].access == INTERNAL_PROGRAM


@pytest.mark.parametrize("family", ("artifact", "definition"))
def test_typed_admission_producer_and_validator_controls(infrastructure_rollback, family):
    connection = infrastructure_rollback
    model = get_metadata()
    for schema in ("ops", "sem", "data"):
        connection.exec_driver_sql("CREATE SCHEMA " + schema)
    controls = MetaData()
    for name in (
        "sem.data_operation_definition",
        "ops.data_request",
        "ops.data_derivation",
        "ops.data_completion_intent",
    ):
        owner = model.tables[name]
        Table(
            owner.name,
            controls,
            *(Column(column.name, column.type) for column in owner.c),
            schema=owner.schema,
        )
    controls.create_all(connection)
    produce = {
        "artifact": artifact_admission_native_programs,
        "definition": definition_admission_native_programs,
    }[family]
    for declaration in produce():
        # Other definition helpers use additional row types. This control installs
        # the actual producer, completion guard and validator exercised below.
        if declaration.identity.name in {
            f"ddo_require_{family}_producer",
            f"ddo_require_{family}_completion",
            f"ddo_{family}_dependencies_valid",
        }:
            execute_native_sql(connection, declaration.routine.render())
    revision = "implementation-slice:" + "a" * 64
    connection.execute(
        insert(controls.tables["sem.data_operation_definition"]),
        dict(
            release_id="release",
            operation_id="operation",
            profile="derivation",
            recipe="recipe",
            implementation_revision=revision,
            validity_families=[family],
            support_contract={
                "capabilities": {
                    "prepared_factory": {
                        "entrypoint": "renamed.factory",
                        "source_digest": "a" * 64,
                    },
                    "forms": ["scalar"],
                    "preparation": "resource",
                    "cpu_receipts": 1,
                },
                "effects": [],
            },
        ),
    )
    connection.execute(
        insert(controls.tables["ops.data_request"]),
        dict(id="request", release_id="release", operation_id="operation", recipe="recipe"),
    )
    import json

    valid = dict(implementation_revision=revision, execution_evidence={"cpu_receipts": [{}]})
    statement = text(
        f"SELECT ops.ddo_require_{family}_producer(r,CAST(:completion AS jsonb)) "
        "FROM ops.data_request r WHERE id='request'"
    )
    connection.execute(statement, dict(completion=json.dumps(valid)))
    for invalid in (
        {**valid, "implementation_revision": "changed"},
        {**valid, "execution_evidence": {"cpu_receipts": []}},
    ):
        with pytest.raises(DBAPIError) as refused, connection.begin_nested():
            connection.execute(statement, dict(completion=json.dumps(invalid)))
        assert getattr(refused.value.orig, "sqlstate", None) == "23514"
    assert (
        connection.execute(
            text(f"SELECT ops.ddo_{family}_dependencies_valid('absent')")
        ).scalar_one()
        is False
    )


def test_execution_leaf_capture_keeps_private_abi():
    declarations = execution_evidence_leaf_native_programs(get_metadata())
    assert declarations[0].identity.arguments == ("text", "text", "text", "bigint", "text")
    inventory = {}
    update_function_inventory(inventory, execution_evidence_leaf_native_sql(get_metadata()))
    observed = inventory["ops.ddo_cpu_execution_leaf(text,text,text,bigint,text)"]
    assert observed["owner"] == role_name("publisher")
    assert observed["execute_roles"] == []
    assert observed["security"] is True
    assert observed["volatility"] == "s"
