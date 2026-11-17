"""Explicit closed S40 maintenance composes with N1 and precedes retired stores."""

from types import SimpleNamespace

import pytest
from alembic.operations import ops
from pydantic import ValidationError
from sqlalchemy import Column, Text

from corpus_structure.schema.data_steps import DataStepRequest, order_data_steps, prepare_data_steps
from corpus_structure.semantic.alembic_privileges import OwnedOperationsOp
from corpus_structure.semantic.native_objects import NativeAuthoringError


def flatten(operations):
    for operation in operations:
        if isinstance(operation, OwnedOperationsOp):
            yield from flatten(operation.ops)
        else:
            yield operation


def operations():
    return ops.UpgradeOps([
        OwnedOperationsOp("corpus_sem_publisher", [
            ops.DropTableOp("pdf_artifact_part", schema="ops"),
            ops.CreateTableOp("pdf_shared_stream", [Column("project_id", Text())], schema="ops"),
            ops.DropTableOp("pdf_stage_artifact_part", schema="ops"),
        ]),
    ])


def test_shared_stream_backfill_and_authenticated_n1_are_explicit_composable_owners():
    selected = prepare_data_steps((DataStepRequest(name="ddo_n1_relower"),
                                   DataStepRequest(name="pdf_s40_shared_streams")))
    assert [step.name for step in selected] == ["ddo_n1_relower", "pdf_s40_shared_streams"]
    assert selected[1].owner == "corpus_sem_publisher"
    assert "LOCK TABLE ops.pdf_artifact_part" in selected[1].statements[0]
    assert "pdf_identity_fold_finish" in selected[1].statements[0]
    assert "TO_REGCLASS" not in selected[1].statements[0].upper()
    with pytest.raises(ValidationError):
        DataStepRequest.model_validate({"name": "pdf_s40_shared_streams", "parameters": {"sql": "DELETE FROM sem.release"}})


def test_shared_stream_data_guard_finishes_before_both_retired_tables_drop():
    upgrade = operations()
    step = prepare_data_steps((DataStepRequest(name="pdf_s40_shared_streams"),))
    order_data_steps(upgrade, step, SimpleNamespace(desired=()))
    ordered = list(flatten(upgrade.ops))
    assert [type(operation) for operation in ordered] == [
        ops.CreateTableOp, ops.ExecuteSQLOp, ops.DropTableOp, ops.DropTableOp,
    ]
    assert [operation.table_name for operation in ordered[2:]] == ["pdf_artifact_part", "pdf_stage_artifact_part"]


def test_retired_table_names_never_auto_select_maintenance_and_changed_sql_refuses():
    upgrade = operations()
    before = tuple(flatten(upgrade.ops))
    order_data_steps(upgrade, (), SimpleNamespace(desired=()))
    assert tuple(flatten(upgrade.ops)) == before
    (step,) = prepare_data_steps((DataStepRequest(name="pdf_s40_shared_streams"),))
    changed = step.model_copy(update={"statements": ("DELETE FROM sem.release",)})
    with pytest.raises(NativeAuthoringError, match="closed builder custody"):
        order_data_steps(upgrade, (changed,), SimpleNamespace(desired=()))
