"""Independent controls for native carried binding-fact verification."""

from hashlib import sha256

import pytest
from sqlalchemy import Column, MetaData, Table, insert, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_compiler_native import _binding_facts_proof
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.native_objects import execute_native_sql


@pytest.mark.parametrize("changed", (None, "parameters", "role", "expression", "types"))
def test_full_proof_compares_admitted_facts_to_authenticated_sources(
    infrastructure_rollback, changed
):
    connection = infrastructure_rollback
    connection.exec_driver_sql("CREATE SCHEMA sem")
    model = get_metadata()
    controls = MetaData()
    for name in ("sem.artifact", "sem.data_operation_definition", "sem.data_operation_release"):
        relation = model.tables[name]
        Table(relation.name, controls, *(Column(c.name, c.type) for c in relation.c), schema="sem")
    controls.create_all(connection)
    expression = {"operator": "scan", "roles": ["input"]}
    role = {"name": "input", "direction": "input", "kind": "primitive:string", "support": None}
    lowered_role = {
        **role,
        "kind_contract": "kind:string",
        "identity_requirements": [],
        "accepted_kind_contracts": ["kind:string"],
    }
    parameter_definitions = {"x": {"value_type": "primitive:string"}}
    kinds = [
        {
            "semantic_id": "primitive:string",
            "name": "string",
            "category": "primitive",
            "facts": {"json": {"primitive": "string"}},
        }
    ]
    document = {
        "kinds": kinds,
        "operations": [
            {
                "semantic_id": "operation",
                "binding": "binding",
                "roles": [role],
                "parameters": {"json": parameter_definitions},
            }
        ],
        "bindings": [{"semantic_id": "binding", "expression": expression}],
        "identities": [
            {"owner": "operation", "domain": "definition", "key": "definition"},
            {"owner": "operation", "domain": "eligibility", "key": "eligibility"},
            {"owner": "primitive:string", "domain": "kind", "key": "kind:string"},
        ],
    }
    projection = {
        "operations": [
            {
                "operation_id": "operation",
                "binding": expression,
                "input_roles": [lowered_role],
                "output_roles": [],
                "definition": "definition",
                "eligibility": "eligibility",
            }
        ]
    }
    for name, value in (
        ("data_operations.json", document),
        ("data_operation_native_definitions.json", projection),
    ):
        content = canonical_bytes(value)
        connection.execute(
            insert(controls.tables["sem.artifact"]),
            {
                "release_id": "release",
                "artifact_name": name,
                "content": content,
                "content_digest": sha256(content).hexdigest(),
            },
        )
    connection.execute(
        insert(controls.tables["sem.data_operation_release"]),
        {"release_id": "release", "binding_types": [] if changed == "types" else kinds},
    )
    connection.execute(
        insert(controls.tables["sem.data_operation_definition"]),
        {
            "release_id": "release",
            "operation_id": "operation",
            "parameter_definitions": {} if changed == "parameters" else parameter_definitions,
            "binding_expression": {} if changed == "expression" else expression,
            "input_roles": [] if changed == "role" else [lowered_role],
            "output_roles": [],
            "definition_identity": "definition",
            "eligibility_identity": "eligibility",
        },
    )
    execute_native_sql(connection, _binding_facts_proof(model).render())
    if changed is None:
        connection.execute(text("SELECT sem.require_execution_binding_facts('release')"))
    else:
        with pytest.raises(DBAPIError, match=r"admitted .* differ"), connection.begin_nested():
            connection.execute(text("SELECT sem.require_execution_binding_facts('release')"))
