"""Protected automated hold fencing and cancellation keep the durable first result."""

from types import SimpleNamespace

import pytest
from pydantic import create_model
from sqlalchemy import insert, select, text, update
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import (
    OperationBinding,
    OperationConflict,
    claim_tasks,
    create_run,
    create_task,
    end_source_run,
    hold_agent_result,
    record_method,
)


def test_native_hold_fences_cancellation_and_refuses_forged_error_seed(
    semantic_db_engine, semantic_writer_engine
):
    from .operation_scenario_support import prepare_operation_scenario

    prepared = prepare_operation_scenario(semantic_db_engine)
    engine = semantic_writer_engine
    t = table("ops.task")
    with engine.begin() as conn:
        run = create_run(
            conn,
            project_id="p",
            binding=OperationBinding(prepared.release_id, "z", 0, b"{}"),
            kind="full",
            options={},
            code_commit="test",
        )
        cfg = record_method(
            conn,
            SimpleNamespace(
                name="agent",
                version="1",
                family="agent",
                tier="agent",
                confidence_source=None,
                unit_type="run",
                Config=create_model("AgentHoldConfig"),
            ),
            "default",
            {},
            "agent-cfg",
            prepared=prepared,
        )
        task = create_task(
            conn,
            run_id=run,
            config_id=cfg,
            stage="propose",
            unit_type="run",
            input_hash="input",
            packet_hash="packet",
            agent=True,
        )
        claim = claim_tasks(conn, run_id=run, config_id=cfg, holder="agent:first", agent=True)[0]
    with engine.begin() as conn:
        assert (
            hold_agent_result(
                conn,
                task_id=task,
                attempt=claim.attempt,
                holder="agent:first",
                packet_hash="packet",
                clean=False,
                result={"issues": ["uncertain"]},
            ).disposition
            == "held"
        )
        with pytest.raises(DBAPIError) as blocked, engine.begin() as cancellation:
            cancellation.execute(text("SET LOCAL lock_timeout='100ms'"))
            end_source_run(cancellation, run)
        assert getattr(blocked.value.orig, "sqlstate", None) == "55P03"
    with pytest.raises(DBAPIError), engine.begin() as conn:
        conn.execute(update(t).where(t.c.id == task).values(error=None))
    with pytest.raises(DBAPIError, match="protected submission"), engine.begin() as conn:
        conn.execute(
            insert(t).values(
                run_id=run,
                release_id=prepared.release_id,
                method_config_id=cfg,
                stage="propose",
                unit_type="run",
                input_hash="forged",
                packet_hash="packet",
                attempt=0,
                status="awaiting_agent",
                cost={},
                priority=0,
                created_at=text("clock_timestamp()"),
                error={"semantic_proposal_first_result": {}},
            )
        )
    with engine.begin() as conn:
        assert end_source_run(conn, run) == 1
        assert conn.execute(select(t.c.error).where(t.c.id == task)).scalar_one()[
            "semantic_proposal_first_result"
        ]["result"]["issues"] == ["uncertain"]
    with pytest.raises(OperationConflict), engine.begin() as conn:
        hold_agent_result(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder="agent:first",
            packet_hash="packet",
            clean=False,
            result={},
        )
