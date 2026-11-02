"""Real pool pressure, cancellation, rollback and renewal settlement on owned clones."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Event
from time import monotonic, sleep

import psycopg
import pytest
from psycopg_pool import PoolTimeout
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.db.lifetime import BorrowerCancellation
from corpus_structure.core.db.store import (
    DatabaseCause,
    EffectKnowledge,
    open_store,
    operation_failure,
)
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.semantic import claim_lifetime, publication
from corpus_structure.semantic.operation_results import (
    ClaimedTask,
    MethodConfigId,
    ReleaseId,
    RunId,
    TaskAttempt,
    TaskId,
)
from corpus_structure.semantic.publication import PublicationBatch
from corpus_structure.settings import DatabaseSettings

from .test_store import settings_for


def wait_until(predicate, *, timeout=5):
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        if predicate():
            return
        sleep(0.005)
    pytest.fail("native operation did not reach the expected state")


def active_query(engine, pid, fragment):
    with engine.connect() as conn:
        return (
            conn.scalar(
                text(
                    "SELECT count(*) FROM pg_stat_activity WHERE pid=:pid "
                    "AND state='active' AND query LIKE :query"
                ),
                {"pid": pid, "query": f"%{fragment}%"},
            )
            == 1
        )


def test_actual_pool_pressure_timeout_closed_and_non_destructive_diagnostics(
    db_engine, monkeypatch
):
    settings = settings_for(db_engine)
    with open_store(
        settings, "pg-lifecycle-pressure", min_size=0, max_size=1, timeout=0.15, max_waiting=1
    ) as store:
        borrowed = store.pool.getconn()
        try:
            with ThreadPoolExecutor(max_workers=1) as threads:
                waiting = threads.submit(store.pool.getconn)
                wait_until(lambda: store.pool.get_stats().get("requests_waiting") == 1)
                monkeypatch.setattr(
                    publication,
                    "lookup_receipt",
                    lambda *args: pytest.fail("acquisition must not resolve receipts"),
                )
                with pytest.raises(DBAPIError) as pressure:
                    publication._publish(
                        store.engine,
                        PublicationBatch("r", "z", "b"),
                        lambda *args: pytest.fail("overload must not execute"),
                        attempts=3,
                    )
                failure = operation_failure(pressure.value).failure
                assert failure.cause is DatabaseCause.ADMISSION_PRESSURE
                assert failure.effects is EffectKnowledge.NONE
                with pytest.raises(PoolTimeout):
                    waiting.result(timeout=3)
        finally:
            store.pool.putconn(borrowed)
        first = store.diagnostic()
        second = store.diagnostic()
        assert first.lifecycle == "open"
        assert first.pool_stats is not None and second.pool_stats is not None
        assert first.pool_stats["requests_errors"] >= 2
        assert second.pool_stats["requests_errors"] == first.pool_stats["requests_errors"]
        assert first.usage_scope == "pool_connection_scopes_only"
    assert store.diagnostic().lifecycle == "closed"
    with pytest.raises(DBAPIError) as closed:
        publication._publish(
            store.engine,
            PublicationBatch("r", "z", "b"),
            lambda *args: pytest.fail("closed pool must not execute"),
            attempts=3,
        )
    assert operation_failure(closed.value).failure.cause is DatabaseCause.INVENTORY_CLOSED
    assert operation_failure(closed.value).failure.effects is EffectKnowledge.NONE


@pytest.mark.parametrize("copy", [False, True])
def test_actual_cancel_settles_query_or_copy_before_connection_reuse(db_engine, copy):
    with open_store(settings_for(db_engine), "pg-lifecycle-cancel", max_size=1) as store:
        cancellation = BorrowerCancellation(timeout=2)
        started = Event()
        session = []

        def operation():
            with store.engine.connect() as conn, cancellation.borrow(conn):
                session.append(conn.scalar(text("SELECT pg_backend_pid()")))
                conn.rollback()
                try:
                    with conn.begin():
                        if copy:
                            driver = conn.connection.driver_connection
                            assert isinstance(driver, psycopg.Connection)
                            started.set()
                            with (
                                driver.cursor() as cursor,
                                cursor.copy("COPY (SELECT pg_sleep(20)) TO STDOUT") as rows,
                            ):
                                started.set()
                                list(rows)
                        else:
                            started.set()
                            conn.execute(text("SELECT pg_sleep(20)"))
                except (DBAPIError, psycopg.errors.QueryCanceled) as error:
                    native = error.orig if isinstance(error, DBAPIError) else error
                    assert isinstance(native, psycopg.Error)
                    assert native.sqlstate == "57014"
                    driver = conn.connection.driver_connection
                    assert isinstance(driver, psycopg.Connection)
                    assert driver.info.transaction_status == psycopg.pq.TransactionStatus.IDLE
                    return
                pytest.fail("native query unexpectedly completed")

        with ThreadPoolExecutor(max_workers=1) as threads:
            executing = threads.submit(operation)
            assert started.wait(3)
            wait_until(lambda: active_query(db_engine, session[0], "pg_sleep"))
            cancellation.request_cancel()
            executing.result(timeout=5)
        assert not cancellation.cleanup_failures
        with store.engine.begin() as conn:
            assert conn.scalar(text("SELECT 73")) == 73
            assert conn.scalar(text("SELECT pg_backend_pid()")) == session[0]
        cancellation.request_cancel()  # deregistered token cannot touch next borrow
        with store.engine.begin() as conn:
            assert conn.scalar(text("SELECT 91")) == 91


def test_mid_write_native_failure_has_independent_zero_row_rollback(db_engine, monkeypatch):
    with db_engine.begin() as conn:
        conn.execute(text("CREATE TABLE public.pg_runtime_effect (value int)"))

    def execute(conn, batch):
        conn.execute(text("INSERT INTO public.pg_runtime_effect VALUES (1)"))
        conn.execute(text("SELECT 1/0"))
        pytest.fail("division by zero did not fail")

    monkeypatch.setattr(
        publication, "lookup_receipt", lambda *args: pytest.fail("commit never attempted")
    )
    with pytest.raises(DBAPIError) as caught:
        publication._publish(db_engine, PublicationBatch("r", "z", "batch"), execute, attempts=3)
    assert operation_failure(caught.value).failure.effects is EffectKnowledge.ROLLED_BACK
    with db_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM public.pg_runtime_effect")) == 0


def test_renewal_exit_cancels_active_query_and_joins_owner(db_engine, monkeypatch):
    started = Event()
    pid = []

    def slow_renew(conn, **kwargs):
        pid.append(conn.scalar(text("SELECT pg_backend_pid()")))
        started.set()
        conn.execute(text("SELECT pg_sleep(20)"))

    monkeypatch.setattr(claim_lifetime, "renew_claim", slow_renew)
    claim = ClaimedTask(
        task_id=TaskId(1),
        run_id=RunId(1),
        release_id=ReleaseId("r"),
        method_config_id=MethodConfigId(1),
        unit_type=TaskUnitType.SOURCE_VIEW,
        unit_id=1,
        unit_key=None,
        packet_hash=None,
        attempt=TaskAttempt(1),
        holder="owner",
        deadline=datetime.now(UTC),
        invocation_key="renewal",
        held_progress=None,
    )
    with open_store(settings_for(db_engine), "pg-renewal-stop", max_size=1) as store:
        with claim_lifetime.maintained_claims(store.engine, [claim], "owner", interval=0.01):
            assert started.wait(3)
            wait_until(lambda: active_query(db_engine, pid[0], "pg_sleep"))
            stop_started = monotonic()
        assert monotonic() - stop_started < 5
        with store.engine.begin() as conn:
            assert conn.scalar(text("SELECT 19")) == 19


def test_renewal_native_statement_deadline_reaches_authority_check(db_engine, monkeypatch):
    def slow_renew(conn, **kwargs):
        conn.execute(text("SELECT pg_sleep(20)"))

    monkeypatch.setattr(claim_lifetime, "renew_claim", slow_renew)
    claim = ClaimedTask(
        task_id=TaskId(1),
        run_id=RunId(1),
        release_id=ReleaseId("r"),
        method_config_id=MethodConfigId(1),
        unit_type=TaskUnitType.SOURCE_VIEW,
        unit_id=1,
        unit_key=None,
        packet_hash=None,
        attempt=TaskAttempt(1),
        holder="owner",
        deadline=datetime.now(UTC),
        invocation_key="renewal",
        held_progress=None,
    )
    deadline = DatabaseSettings(
        renewal_statement_timeout_seconds=0.1, renewal_lock_timeout_seconds=0.05
    )
    with open_store(settings_for(db_engine), "pg-renewal-timeout", max_size=1) as store:
        with (
            pytest.raises(DBAPIError) as caught,
            claim_lifetime.maintained_claims(
                store.engine, [claim], "owner", interval=0.01, database=deadline
            ) as check,
        ):
            wait_until(lambda: _check_failed(check))
        failure = operation_failure(caught.value).failure
        assert failure.cause is DatabaseCause.CANCELLED
        assert not failure.cancellation_requested
        assert failure.effects is EffectKnowledge.ROLLED_BACK


def _check_failed(check):
    check()
    return False


def test_cli_runtime_failure_reports_its_actual_live_pool_without_sql(db_engine):
    import json

    import typer
    from typer.testing import CliRunner

    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.runtime import open_runtime_engine

    app = typer.Typer()

    @app.command()
    def inspect_failure():
        with (
            failure_boundary(True),
            open_runtime_engine(
                settings_for(db_engine), "diagnostic-invocation", purpose="maintenance"
            ) as engine,
            engine.begin() as conn,
        ):
            conn.execute(text("SELECT 1/0"))

    result = CliRunner().invoke(app, [])
    assert result.exit_code == 1
    error = json.loads(result.stdout)["error"]
    assert error["failure"]["sqlstate"] == "22012"
    assert error["failure"]["effects"] == "uncertain"
    assert error["database"]["application_name"] == "diagnostic-invocation"
    assert error["database"]["lifecycle"] == "open"
    assert error["database"]["pool_stats"]["pool_size"] >= 1
    assert error["database"]["usage_scope"] == "pool_connection_scopes_only"
    assert "SELECT" not in result.stdout
