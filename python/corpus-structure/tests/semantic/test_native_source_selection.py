"""Actual semantic CLI source selection, automated routing and protected lifecycle controls."""

from types import SimpleNamespace

import psycopg
import pytest
from pydantic import create_model
from sqlalchemy import select, update
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import (
    OperationBinding,
    claim_tasks,
    complete_task,
    create_run,
    create_task,
    record_method,
    register_document,
    seal_cut,
)

from .operation_scenario_support import prepare_operation_scenario


def test_native_declared_corpus_and_final_open_task_guard(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    p = prepare_operation_scenario(semantic_db_engine)
    e = semantic_writer_engine
    source = tmp_path / "source"
    source.write_text("source")
    with e.begin() as conn:
        doc = register_document(
            conn,
            project_id="p",
            source_uri="source",
            original_path=str(source),
            original=source.read_bytes(),
            mime="text/html",
        )
        run = create_run(
            conn,
            project_id="p",
            binding=OperationBinding(p.release_id, "z", 0, b"{}"),
            kind="full",
            options={"corpus": {"documents": []}},
            code_commit="test",
        )
        config = record_method(
            conn,
            SimpleNamespace(
                name="read",
                version="1",
                family="ingest",
                tier="deterministic",
                confidence_source=None,
                unit_type="run",
                Config=create_model("ScopeControlConfig"),
            ),
            "default",
            {},
            "cfg",
        )
    with pytest.raises(DBAPIError, match="immutable declared corpus"), e.begin() as conn:
        create_task(
            conn,
            run_id=run,
            config_id=config,
            stage="ingest",
            unit_type="document",
            unit_id=doc,
            input_hash="input",
        )
    with e.begin() as conn:
        task = create_task(
            conn,
            run_id=run,
            config_id=config,
            stage="read",
            unit_type="run",
            input_hash="input",
            trigger={"rule_key": "declared"},
        )
    with pytest.raises(DBAPIError, match="all automated tasks"), e.begin() as conn:
        seal_cut(conn, run, "final", final=True)
    with (
        pytest.raises(DBAPIError) as denied,
        e.begin() as conn,
    ):
        conn.execute(
            update(table("ops.task"))
            .where(table("ops.task").c.id == task)
            .values(trigger={"rule_key": "changed"})
        )
    assert isinstance(denied.value.orig, psycopg.Error)
    assert denied.value.orig.sqlstate == "42501"
    with e.connect() as conn:
        assert conn.scalar(
            select(table("ops.task").c.trigger).where(table("ops.task").c.id == task)
        ) == {"rule_key": "declared"}
    with (
        pytest.raises(DBAPIError, match="routing provenance") as guarded,
        semantic_db_engine.begin() as conn,
    ):
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        conn.execute(
            update(table("ops.task"))
            .where(table("ops.task").c.id == task)
            .values(trigger={"rule_key": "changed"})
        )
    assert isinstance(guarded.value.orig, psycopg.Error)
    assert guarded.value.orig.sqlstate == "P0001"
    with e.begin() as conn:
        claim = claim_tasks(conn, run_id=run, config_id=config, holder="worker")[0]
        completed = complete_task(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder="worker",
            prepared=p,
            observations=[],
            outcome="empty",
        )
        assert completed.receipt.protocol == "empty"
        seal_cut(conn, run, "final", final=True)
