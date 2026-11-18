"""Module-owned substitute schema for CPU basis programs and invalid-state controls."""

import pytest
from pglast import ast
from sqlalchemy.schema import CreateTable

from corpus_structure.semantic.data_operation_cpu_basis import cpu_input_basis_native_sql
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.prepared_sql import prepare_sql
from native_test_support import database_name, rollback_connection


@pytest.fixture(scope="module")
def cpu_basis_engine(native_server):

    from corpus_structure.semantic.data_operation_binding_native import binding_native_sql
    from corpus_structure.semantic.data_operation_storage import native_protocol_sources, native_sql
    from corpus_structure.semantic.target_installation import foundation_programs

    foundation = foundation_programs()
    closure = foundation.closure
    with native_server.database(database_name("bare").name, native_server.template) as engine:
        with engine.begin() as connection:
            for schema in ("ops", "sem", "data", "kb"):
                connection.exec_driver_sql(f"CREATE SCHEMA IF NOT EXISTS {schema}")
            for name in (
                "ops.data_request",
                "sem.data_operation_definition",
                "kb.data_product",
                "kb.data_product_member",
                "ops.data_derivation_output",
                "ops.original_source_admission",
            ):
                connection.execute(CreateTable(table(name), include_foreign_key_constraints=[]))
            for source, names in (
                (foundation.identity, {"canonical_json", "decimal_canonical"}),
                (closure, {"require_float_lexical"}),
                (
                    native_sql(native_protocol_sources()),
                    {
                        "ddo_normalize",
                        "ddo_json_meaning",
                        "ddo_field",
                        "ddo_operation_subject",
                        "ddo_digest",
                        "ddo_cpu_reply_value",
                    },
                ),
                (binding_native_sql(), {"ddo_input_support_selection", "ddo_input_support_refs"}),
                (cpu_input_basis_native_sql(), {"ddo_cpu_input_basis", "ddo_cpu_reply_output"}),
            ):
                parsed = prepare_sql(source, source="cpu-actual-input-basis-control")
                for index, statement in enumerate(parsed.statements):
                    node = statement.stmt
                    if (
                        isinstance(node, ast.CreateFunctionStmt)
                        and node.funcname
                        and node.funcname[-1].sval in names
                    ):
                        connection.exec_driver_sql(
                            parsed.excerpt(index), execution_options={"no_parameters": True}
                        )
        yield engine


@pytest.fixture
def cpu_basis_connection(cpu_basis_engine):
    with rollback_connection(cpu_basis_engine) as connection:
        yield connection
