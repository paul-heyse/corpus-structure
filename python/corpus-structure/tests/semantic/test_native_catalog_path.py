"""Native catalog facts use the guard's search path, independently of authoring defaults."""

from sqlalchemy import text

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
