"""Explicit closed S40 maintenance composes with N1 and precedes retired stores."""

from functools import partial

import pytest
from alembic.operations import ops
from pydantic import ValidationError
from sqlalchemy import BigInteger, Column, LargeBinary, Text

from corpus_structure.schema import data_steps
from corpus_structure.schema.data_step_programs import RETIRED_PARTS, predecessor_parts
from corpus_structure.schema.data_steps import DataStepRequest
from corpus_structure.semantic.alembic_privileges import OwnedOperationsOp
from corpus_structure.semantic.metadata import metadata
from corpus_structure.semantic.native_objects import NativeAuthoring, NativeAuthoringError

PREDECESSOR = "semantic_ddo_pe_n2"
PREDECESSOR_PARTS = ("ops.pdf_artifact_part", "ops.pdf_stage_artifact_part")
prepare_data_steps = partial(
    data_steps.prepare_data_steps, target=metadata, predecessor=PREDECESSOR
)
order_data_steps = partial(data_steps.order_data_steps, target=metadata, predecessor=PREDECESSOR)


def flatten(operations):
    for operation in operations:
        if isinstance(operation, OwnedOperationsOp):
            yield from flatten(operation.ops)
        else:
            yield operation


def operations():
    return ops.UpgradeOps(
        [
            OwnedOperationsOp(
                "corpus_sem_publisher",
                [
                    ops.DropTableOp("pdf_artifact_part", schema="ops"),
                    ops.CreateTableOp(
                        "pdf_shared_stream", [Column("project_id", Text())], schema="ops"
                    ),
                    ops.DropTableOp("pdf_stage_artifact_part", schema="ops"),
                ],
            ),
        ]
    )


def test_shared_stream_backfill_and_authenticated_n1_are_explicit_composable_owners():
    selected = prepare_data_steps(
        (DataStepRequest(name="ddo_n1_relower"), DataStepRequest(name="pdf_s40_shared_streams"))
    )
    assert [step.name for step in selected] == ["ddo_n1_relower", "pdf_s40_shared_streams"]
    assert selected[1].owner == "corpus_sem_publisher"
    assert "TO_REGCLASS" not in selected[1].statements[0].upper()
    assert "IN EXECUTE" not in selected[1].statements[0].upper()
    assert selected[1].retired_relations == RETIRED_PARTS == PREDECESSOR_PARTS
    assert set(PREDECESSOR_PARTS) <= set(selected[1].prerequisite_relations)
    with pytest.raises(ValidationError):
        DataStepRequest.model_validate(
            {"name": "pdf_s40_shared_streams", "parameters": {"sql": "DELETE FROM sem.release"}}
        )


def test_shared_stream_step_holds_both_predecessor_locks_before_transaction_end(commit_db_engine):
    from sqlalchemy import text
    from sqlalchemy.schema import CreateTable

    from corpus_structure.semantic.native_objects import execute_native_sql

    relations, _ = predecessor_parts(PREDECESSOR)
    with commit_db_engine.begin() as connection:
        for relation in relations.values():
            connection.execute(CreateTable(relation, include_foreign_key_constraints=[]))
    (step,) = prepare_data_steps((DataStepRequest(name="pdf_s40_shared_streams"),))
    locks = text(
        "SELECT namespace.nspname||'.'||relation.relname FROM pg_locks held "
        "JOIN pg_class relation ON relation.oid=held.relation "
        "JOIN pg_namespace namespace ON namespace.oid=relation.relnamespace "
        "WHERE held.pid=pg_backend_pid() AND held.granted "
        "AND held.mode='AccessExclusiveLock' AND namespace.nspname='ops' "
        "AND relation.relname IN ('pdf_artifact_part','pdf_stage_artifact_part')"
    )
    with commit_db_engine.connect() as connection:
        transaction = connection.begin()
        try:
            assert set(connection.scalars(locks)) == set()
            for statement in step.statements:
                execute_native_sql(connection, statement)
            assert set(connection.scalars(locks)) == set(PREDECESSOR_PARTS)
        finally:
            transaction.rollback()


def test_shared_stream_data_guard_finishes_before_both_retired_tables_drop():
    upgrade = operations()
    step = prepare_data_steps((DataStepRequest(name="pdf_s40_shared_streams"),))
    order_data_steps(upgrade, step, NativeAuthoring(()))
    ordered = list(flatten(upgrade.ops))
    assert [type(operation) for operation in ordered] == [
        ops.CreateTableOp,
        ops.ExecuteSQLOp,
        ops.DropTableOp,
        ops.DropTableOp,
    ]
    assert [operation.table_name for operation in ordered[2:]] == [
        "pdf_artifact_part",
        "pdf_stage_artifact_part",
    ]


def test_retired_table_names_never_auto_select_maintenance_and_changed_sql_refuses():
    upgrade = operations()
    before = tuple(flatten(upgrade.ops))
    order_data_steps(upgrade, (), NativeAuthoring(()))
    assert tuple(flatten(upgrade.ops)) == before
    (step,) = prepare_data_steps((DataStepRequest(name="pdf_s40_shared_streams"),))
    changed = step.model_copy(update={"statements": ("DELETE FROM sem.release",)})
    with pytest.raises(NativeAuthoringError, match="closed builder custody"):
        order_data_steps(upgrade, (changed,), NativeAuthoring(()))


def test_retired_shapes_come_from_the_fixed_predecessor_inventory():
    relations, captured = predecessor_parts(PREDECESSOR)
    assert b'"physical_id"' in captured
    assert tuple(relations) == PREDECESSOR_PARTS
    for relation in relations.values():
        assert set(relation.c.keys()) == {
            "product_id",
            "revision_id",
            "stream_id",
            "ordinal",
            "byte_offset",
            "byte_length",
            "body",
            "sha256_digest",
        }
        assert isinstance(relation.c.body.type, LargeBinary)
        assert isinstance(relation.c.byte_length.type, BigInteger)
        assert isinstance(relation.c.product_id.type, Text)
        assert all(not column.nullable for column in relation.c)
        assert {column.name for column in relation.primary_key} == {
            "product_id",
            "revision_id",
            "stream_id",
            "ordinal",
        }


def test_s40_refuses_a_transition_that_would_keep_a_retired_store():
    step = prepare_data_steps((DataStepRequest(name="pdf_s40_shared_streams"),))
    upgrade = ops.UpgradeOps([ops.DropTableOp("pdf_artifact_part", schema="ops")])
    with pytest.raises(NativeAuthoringError, match="declared physical retirement"):
        order_data_steps(upgrade, step, NativeAuthoring(()))
