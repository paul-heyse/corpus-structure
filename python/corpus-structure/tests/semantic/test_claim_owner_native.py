"""Actual native renewal/terminal fences under one attempt lifetime owner."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from threading import Event
from types import SimpleNamespace

import psycopg
import pytest
from pydantic import BaseModel
from sqlalchemy import text

from corpus_structure.semantic import claim_lifetime
from corpus_structure.semantic.operations import (
    OperationBinding, OperationConflict, claim_tasks, complete_task, create_run,
    create_task, record_method,
)

from .operation_scenario_support import prepare_operation_scenario


class Config(BaseModel):
    pass


def claims(admin, writer, count=1):
    prepared = prepare_operation_scenario(admin)
    with writer.begin() as conn:
        run = create_run(conn, project_id="p", binding=OperationBinding(prepared.release_id, "z", 0, b"{}"),
                         kind="full", options={}, code_commit="test")
        method = SimpleNamespace(name="owned", version="1", family="profile", tier="deterministic",
                                 confidence_source=None, unit_type="run", Config=Config)
        config = record_method(conn, method, "default", {}, "owned-config")
        for n in range(count):
            create_task(conn, run_id=run, config_id=config, stage="ingest", unit_type="run", input_hash=f"owned-{n}", unit_key=f"{n}")
        tasks = claim_tasks(conn, run_id=run, config_id=config, holder="owner", limit=count)
    return prepared, tasks


def completion(prepared, claim):
    return lambda conn: complete_task(conn, task_id=claim.task_id, attempt=claim.attempt,
                                     holder=claim.holder, prepared=prepared, observations=(), outcome="empty")


def test_renewal_is_serialized_through_terminal_commit_and_retirement(
    semantic_db_engine, semantic_writer_engine, monkeypatch
):
    prepared, (claim,) = claims(semantic_db_engine, semantic_writer_engine)
    entered, release, completed = Event(), Event(), Event()
    renewals = []
    actual = claim_lifetime.renew_claim

    def delayed(conn, **values):
        renewals.append(values)
        entered.set()
        assert release.wait(5)
        assert not completed.is_set()
        actual(conn, **values)

    monkeypatch.setattr(claim_lifetime, "renew_claim", delayed)
    with claim_lifetime.maintained_claims(semantic_writer_engine, [claim], "owner", interval=0.01) as owner:
        assert entered.wait(5)
        with ThreadPoolExecutor(1) as pool:
            pending = pool.submit(owner.settle, claim, completion(prepared, claim))
            assert not pending.done()
            release.set()
            result = pending.result(5)
        completed.set()
        assert result.transaction == "applied" and result.receipt.attempt == claim.attempt
        assert not owner.active
    assert len(renewals) == 1
    with semantic_writer_engine.begin() as conn, pytest.raises(OperationConflict):
        actual(conn, task_id=claim.task_id, attempt=claim.attempt, holder="owner")


def test_lost_commit_response_replays_exact_completion_before_retirement(
    semantic_db_engine, semantic_writer_engine
):
    prepared, (claim,) = claims(semantic_db_engine, semantic_writer_engine)
    lost = []

    class ResponseLost:
        @contextmanager
        def connect(self):
            with semantic_writer_engine.connect() as conn:
                class Connection:
                    @contextmanager
                    def begin(self):
                        with conn.begin():
                            yield
                        if not lost:
                            lost.append(True)
                            raise psycopg.OperationalError("commit response lost")

                    def __getattr__(self, name):
                        return getattr(conn, name)
                yield Connection()

    owner = claim_lifetime.ClaimOwner(ResponseLost(), [claim], "owner",
                                     claim_lifetime.DatabaseSettings(), lambda: None)
    result = owner.settle(claim, completion(prepared, claim))
    assert result.transaction == "replay" and result.receipt.attempt == claim.attempt
    assert not owner.active
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text("SELECT status FROM ops.task WHERE id=:id"), {"id": claim.task_id}) == "empty"
        assert conn.scalar(text("SELECT count(*) FROM kb.observation WHERE task_id=:id"), {"id": claim.task_id}) == 0


def test_later_failure_preserves_earlier_durable_completion(semantic_db_engine, semantic_writer_engine):
    prepared, owned = claims(semantic_db_engine, semantic_writer_engine, 2)
    first, second = owned
    with pytest.raises(OperationConflict, match="later task failed"):
        with claim_lifetime.maintained_claims(semantic_writer_engine, owned, "owner") as owner:
            owner.settle(first, completion(prepared, first))
            def fail(conn):
                raise OperationConflict("later task failed")
            owner.settle(second, fail)
    with semantic_db_engine.connect() as conn:
        assert conn.scalar(text("SELECT status FROM ops.task WHERE id=:id"), {"id": first.task_id}) == "empty"
        assert conn.scalar(text("SELECT status FROM ops.task WHERE id=:id"), {"id": second.task_id}) == "running"
