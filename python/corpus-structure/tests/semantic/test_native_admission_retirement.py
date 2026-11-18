"""Current normalized ACL replacements cannot inherit a removed reader grant."""

from dataclasses import replace

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.metadata import metadata
from corpus_structure.semantic.native_admission import _admission_descriptor, native_admission_sql
from corpus_structure.semantic.native_objects import (
    admit_native,
    definition_from_sql,
    prepare_native_authoring,
)
from corpus_structure.semantic.native_products import admission_kernel
from corpus_structure.semantic.target_installation import (
    capture_target_installation,
    target_admission_descriptor,
)


def test_managed_acl_replacement_removes_reader_in_native_and_descriptor(infrastructure_rollback):
    connection = infrastructure_rollback
    connection.exec_driver_sql("CREATE SCHEMA native_acl_control")
    connection.exec_driver_sql(
        "GRANT USAGE,CREATE ON SCHEMA native_acl_control TO corpus_sem_publisher"
    )
    definition = definition_from_sql(
        connection,
        "CREATE OR REPLACE FUNCTION native_acl_control.selected() RETURNS integer "
        "LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$ SELECT 7 $$",
        source="current ACL replacement control",
        owner="corpus_sem_publisher",
        grants=(("corpus_sem_reader", "EXECUTE", False),),
    )
    before = prepare_native_authoring(connection, (definition,), owned_authoring=True)
    operations = Operations(MigrationContext.configure(connection))
    operations.invoke(NativeTransitionOp(None, before.desired[0]))
    admit_native(connection, before.desired)
    after = prepare_native_authoring(
        connection,
        (
            replace(
                definition,
                grants=(
                    ("corpus_sem_evaluator", "EXECUTE", False),
                    ("corpus_sem_fitter", "EXECUTE", False),
                ),
            ),
        ),
        predecessor=before.desired,
        owned_authoring=True,
    )
    captured = capture_target_installation(metadata)
    admission = native_admission_sql(
        admission_kernel() + "\n" + definition.sql,
        captured.authoring_inputs,
        base_descriptor=target_admission_descriptor(captured, ()),
        target_metadata=metadata,
        native_objects=after.desired,
    )
    selected = next(
        entry
        for entry in _admission_descriptor(admission)["functions"]
        if entry["signature"] == definition.identity.qualified
    )
    assert selected["execute_roles"] == ["corpus_sem_evaluator", "corpus_sem_fitter"]
    assert ["corpus_sem_reader", "EXECUTE", False] not in selected["catalog_acl"]
    operations.invoke(NativeTransitionOp(before.desired[0], after.desired[0]))
    admit_native(connection, after.desired)
    assert (
        connection.scalar(
            text(
                "SELECT has_function_privilege('corpus_sem_reader',"
                "'native_acl_control.selected()','EXECUTE')"
            )
        )
        is False
    )
    assert connection.scalar(text("SELECT native_acl_control.selected()")) == 7
