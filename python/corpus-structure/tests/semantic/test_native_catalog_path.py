"""Native catalog facts use the guard's search path, independently of authoring defaults."""

from hashlib import sha256

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.native_objects import (
    admit_native,
    definition_from_sql,
    execute_native_sql,
    native_owner,
    prepare_native_authoring,
)


def test_extension_type_signature_result_and_defaults_are_guard_path_canonical(
    infrastructure_rollback,
):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    from corpus_structure.semantic.alembic_native import NativeTransitionOp

    connection = infrastructure_rollback
    connection.exec_driver_sql("CREATE SCHEMA catalog_path_control")
    connection.exec_driver_sql(
        "GRANT USAGE,CREATE ON SCHEMA catalog_path_control TO corpus_sem_publisher"
    )
    connection.exec_driver_sql("SET LOCAL search_path=pg_catalog,public")
    definition = definition_from_sql(
        connection,
        "CREATE OR REPLACE FUNCTION catalog_path_control.vector_identity(p vector DEFAULT '[1,2]'::vector) "
        "RETURNS vector LANGUAGE sql IMMUTABLE AS $$ SELECT p $$",
        source="actual extension type/default control",
        owner="corpus_sem_publisher",
    )
    assert definition.identity.arguments == ("public.vector",)
    authoring = prepare_native_authoring(connection, (definition,), owned_authoring=True)
    (item,) = authoring.desired
    assert item.catalog["result_type"] == item.catalog["result"] == "public.vector"
    assert item.catalog["arguments"] == "p public.vector DEFAULT '[1,2]'::public.vector"
    assert item.catalog["defaults"] == "'[1,2]'::public.vector"
    from corpus_structure.semantic.metadata import metadata
    from corpus_structure.semantic.native_admission import native_admission_sql
    from corpus_structure.semantic.native_products import (
        admission_kernel,
        literal_json_descriptor,
    )
    from corpus_structure.semantic.target_installation import (
        capture_target_installation,
        target_admission_descriptor,
    )

    captured = capture_target_installation(metadata)
    admission = native_admission_sql(
        admission_kernel() + "\n" + definition.sql,
        captured.authoring_inputs,
        base_descriptor=target_admission_descriptor(captured, ()),
        target_metadata=metadata,
        native_objects=authoring.desired,
    )
    descriptor = literal_json_descriptor(admission, "data.execution_contract_descriptor")
    entries = [
        entry
        for entry in descriptor["functions"]
        if entry["signature"].startswith("catalog_path_control.")
    ]
    assert len(entries) == 1
    assert entries[0]["signature"] == "catalog_path_control.vector_identity(public.vector)"
    assert entries[0]["result"] == "public.vector"
    assert entries[0]["argument_defaults"] == "'[1,2]'::public.vector"
    Operations(MigrationContext.configure(connection)).invoke(NativeTransitionOp(None, item))
    for path in ("pg_catalog,public", "pg_catalog,pg_temp"):
        connection.execute(text("SELECT set_config('search_path',:path,true)"), {"path": path})
        admit_native(connection, authoring.desired)
        assert connection.scalar(text("SELECT current_setting('search_path')")) == path
    with native_owner(connection, "corpus_sem_publisher"):
        execute_native_sql(
            connection, "DROP FUNCTION catalog_path_control.vector_identity(public.vector)"
        )


def test_catalog_fingerprints_keep_signature_order_missing_functions_and_exact_body(
    infrastructure_rollback,
):
    from corpus_structure.semantic.native_catalog import function_body_fingerprints

    connection = infrastructure_rollback
    connection.exec_driver_sql("CREATE SCHEMA body_fingerprint_control")
    first, second = " SELECT 1 ", " SELECT 'two'::text "
    connection.exec_driver_sql(
        "CREATE FUNCTION body_fingerprint_control.first() RETURNS integer LANGUAGE sql "
        "AS $$" + first + "$$"
    )
    connection.exec_driver_sql(
        "CREATE FUNCTION body_fingerprint_control.second() RETURNS text LANGUAGE sql "
        "AS $$" + second + "$$"
    )
    signatures = tuple(
        "body_fingerprint_control." + name + "()"
        for name in ("second", "missing", "first", "second")
    )
    assert connection.scalars(function_body_fingerprints(signatures)).all() == [
        sha256(second.encode()).hexdigest(),
        None,
        sha256(first.encode()).hexdigest(),
        sha256(second.encode()).hexdigest(),
    ]


def test_frozen_catalog_probe_initializes_guard_variables_and_excludes_release_effects(
    infrastructure_rollback,
):
    from corpus_structure.semantic.native_admission import frozen_catalog_verification
    from corpus_structure.semantic.native_sql_body import catalog_path

    connection = infrastructure_rollback
    connection.exec_driver_sql("CREATE SCHEMA sem; CREATE SCHEMA data")
    descriptor = (
        "CREATE OR REPLACE FUNCTION data.execution_contract_descriptor() "
        'RETURNS jsonb LANGUAGE sql AS $$ SELECT \'{"token":"current"}\'::jsonb $$'
    )
    connection.exec_driver_sql(descriptor)
    body = """BEGIN
 RAISE EXCEPTION 'release precondition must remain outside catalog replay';
 -- native catalog checks begin
 spec := expected;
 IF spec->>'token' <> 'current' OR owner_name IS DISTINCT FROM current_user THEN
   RAISE EXCEPTION 'controlled frozen catalog refusal' USING ERRCODE='23514';
 END IF;
 -- native catalog checks complete
 RAISE EXCEPTION 'release publication must remain outside catalog replay';
END"""
    verification = frozen_catalog_verification(body)
    with catalog_path(connection):
        execute_native_sql(connection, verification)
        with connection.begin_nested() as changed:
            connection.exec_driver_sql(descriptor.replace('"current"', '"changed"'))
            with (
                pytest.raises(DBAPIError, match="controlled frozen catalog refusal") as refused,
                connection.begin_nested(),
            ):
                execute_native_sql(connection, verification)
            assert getattr(refused.value.orig, "sqlstate", None) == "23514"
            changed.rollback()
        execute_native_sql(connection, verification)
