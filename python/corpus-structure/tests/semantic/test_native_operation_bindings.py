"""Actual native call ABI and the bound attempt-fence diagnostic, after deployment."""

import json
from types import SimpleNamespace

import psycopg
import pytest
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.contracts import bound_execution_model
from corpus_structure.semantic.invariant_failures import classify_invariant_failure
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operation_results import MethodConfigId, RunId
from corpus_structure.semantic.operations import (
    OperationBinding,
    claim_tasks,
    create_run,
    create_task,
    record_method,
)
from semantic.operation_scenario_support import prepare_operation_scenario


class Config(BaseModel):
    pass


def test_native_claim_abi_result_and_observable_trigger_fence(
    commit_db_engine,
    commit_writer_engine,
):
    prepared = prepare_operation_scenario(commit_db_engine, composed=True)
    model = bound_execution_model(prepared)
    call = model.operation("claim").call
    assert call is not None
    expected = [
        ("p_run", "bigint"),
        ("p_config", "bigint"),
        ("p_holder", "text"),
        ("p_limit", "bigint"),
        ("p_agent", "boolean"),
    ]
    assert [f.native_parameter for f in call.parameters] == [name for name, _ in expected]
    with commit_db_engine.connect() as conn:
        actual = conn.execute(
            text("""SELECT p.proargnames[a.ordinality],
format_type(a.typ,NULL) FROM pg_proc p
CROSS JOIN LATERAL unnest(p.proargtypes) WITH ORDINALITY a(typ,ordinality)
WHERE p.oid='ops.claim_tasks(bigint,bigint,text,bigint,boolean)'::regprocedure
ORDER BY a.ordinality""")
        ).all()
        assert [tuple(row) for row in actual] == expected
        assert (
            conn.scalar(
                text("""SELECT pg_get_function_result(
'ops.claim_tasks(bigint,bigint,text,bigint,boolean)'::regprocedure)""")
            )
            == "SETOF ops.task"
        )
        names = set(
            conn.scalars(
                text("""SELECT attname FROM pg_attribute
WHERE attrelid='ops.task'::regclass AND attnum>0 AND NOT attisdropped""")
            )
        )
        assert all(f.source.removeprefix("physical:ops.task.") in names for f in call.result_fields)
    with commit_writer_engine.begin() as conn:
        run = create_run(
            conn,
            project_id="p",
            binding=OperationBinding(prepared.release_id, "z", 0, b"{}"),
            kind="full",
            options={},
            code_commit="native-binding-control",
        )
        config = record_method(
            conn,
            SimpleNamespace(
                name="native-binding",
                version="1",
                family="ingest",
                tier="deterministic",
                confidence_source=None,
                unit_type="run",
                Config=Config,
            ),
            "default",
            {},
            "native-binding-config",
            prepared=prepared,
        )
        task = create_task(
            conn,
            run_id=run,
            config_id=config,
            stage="ingest",
            unit_type="run",
            input_hash="native-binding-input",
        )
        claimed = claim_tasks(
            conn,
            run_id=RunId(run),
            config_id=MethodConfigId(config),
            holder="worker",
            prepared=prepared,
        )[0]
    assert (
        claimed.task_id,
        claimed.run_id,
        claimed.release_id,
        claimed.method_config_id,
        claimed.attempt,
        claimed.holder,
    ) == (task, run, prepared.release_id, config, 1, "worker")
    assert claimed.deadline is not None and claimed.held_progress is None
    with pytest.raises(DBAPIError) as guarded, commit_db_engine.begin() as conn:
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        conn.execute(
            table("ops.task")
            .update()
            .where(table("ops.task").c.id == task)
            .values(attempt=claimed.attempt + 2)
        )
    assert isinstance(guarded.value.orig, psycopg.Error)
    assert guarded.value.orig.sqlstate == "23514"
    detail = guarded.value.orig.diag.message_detail
    assert detail is not None
    assert json.loads(detail) == {
        "protocol": "corpus-invariant-1",
        "guard": "execution_task",
        "version": "2",
        "invariant": "attempt_fence",
    }
    failure = classify_invariant_failure(model, "claim", guarded.value)
    assert failure is not None
    assert (failure.code, failure.invariant, failure.operation) == (
        "execution.attempt_fence",
        "attempt_fence",
        "claim",
    )
    with commit_db_engine.connect() as conn:
        assert tuple(
            conn.execute(
                select(table("ops.task").c.attempt, table("ops.task").c.claimed_by).where(
                    table("ops.task").c.id == task
                )
            ).one()
        ) == (1, "worker")
