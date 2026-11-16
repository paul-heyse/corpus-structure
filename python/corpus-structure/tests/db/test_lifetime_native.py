"""Real pool pressure, cancellation, rollback and renewal settlement on owned clones."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from types import SimpleNamespace
from threading import Event
from time import monotonic, sleep

import psycopg
import pytest
from db_store_support import settings_for
from psycopg_pool import PoolTimeout
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.db.lifetime import BorrowerCancellation
from corpus_structure.core.db.store import (
    DatabaseCause,
    DatabasePhase,
    EffectKnowledge,
    open_store,
    operation_failure,
)
from corpus_structure.semantic import claim_lifetime
from corpus_structure.settings import DatabaseSettings


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


@pytest.mark.usefixtures("observed_store_checkouts")
def test_actual_pool_pressure_timeout_closed_and_non_destructive_diagnostics(
    infrastructure_engine,
):
    settings = settings_for(infrastructure_engine)
    with open_store(
        settings, "pg-lifecycle-pressure", min_size=0, max_size=1, timeout=0.15, max_waiting=1
    ) as store:
        borrowed = store.pool.getconn()
        try:
            with ThreadPoolExecutor(max_workers=1) as threads:
                waiting = threads.submit(store.pool.getconn)
                wait_until(lambda: store.pool.get_stats().get("requests_waiting") == 1)
                with pytest.raises(DBAPIError) as pressure, store.engine.connect():
                    pytest.fail("overload must not acquire a database connection")
                failure = operation_failure(pressure.value).failure
                assert failure.cause is DatabaseCause.ADMISSION_PRESSURE
                # Raw pool acquisition supplies the native cause. It has no semantic
                # operation context from which to infer effects or replay policy.
                assert failure.phase is DatabasePhase.UNKNOWN
                assert failure.effects is EffectKnowledge.UNCERTAIN
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
    with pytest.raises(DBAPIError) as closed, store.engine.connect():
        pytest.fail("closed pool must not acquire a database connection")
    assert operation_failure(closed.value).failure.cause is DatabaseCause.INVENTORY_CLOSED
    assert operation_failure(closed.value).failure.phase is DatabasePhase.UNKNOWN


@pytest.mark.parametrize("copy", [False, True])
def test_actual_cancel_settles_query_or_copy_before_connection_reuse(infrastructure_engine, copy):
    with open_store(
        settings_for(infrastructure_engine), "pg-lifecycle-cancel", max_size=1
    ) as store:
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
            wait_until(lambda: active_query(infrastructure_engine, session[0], "pg_sleep"))
            cancellation.request_cancel()
            executing.result(timeout=5)
        assert not cancellation.cleanup_failures
        with store.engine.begin() as conn:
            assert conn.scalar(text("SELECT 73")) == 73
            assert conn.scalar(text("SELECT pg_backend_pid()")) == session[0]
        cancellation.request_cancel()  # deregistered token cannot touch next borrow
        with store.engine.begin() as conn:
            assert conn.scalar(text("SELECT 91")) == 91


def test_mid_write_native_failure_has_independent_zero_row_rollback(infrastructure_commit_engine):
    with infrastructure_commit_engine.begin() as conn:
        conn.execute(text("CREATE TABLE public.pg_runtime_effect (value int)"))

    with pytest.raises(DBAPIError), infrastructure_commit_engine.begin() as conn:
        conn.execute(text("INSERT INTO public.pg_runtime_effect VALUES (1)"))
        conn.execute(text("SELECT 1/0"))
        pytest.fail("division by zero did not fail")
    with infrastructure_commit_engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM public.pg_runtime_effect")) == 0


def test_renewal_exit_cancels_active_query_and_joins_owner(infrastructure_engine):
    started = Event()
    pid = []

    def slow_renew(conn, owned):
        pid.append(conn.scalar(text("SELECT pg_backend_pid()")))
        started.set()
        conn.execute(text("SELECT pg_sleep(20)"))

    # This is a physical renewal/cancellation control; the callback deliberately owns
    # only a sleeping SQL statement. Current native task custody is tested separately.
    claim = SimpleNamespace(
        task_id=1, attempt=1, release_id="r", holder="owner", deadline=datetime.now(UTC)
    )
    with open_store(settings_for(infrastructure_engine), "pg-renewal-stop", max_size=1) as store:
        with claim_lifetime.maintained_claims(
            store.engine, [claim], "owner", interval=0.01, renew=slow_renew
        ):
            assert started.wait(3)
            wait_until(lambda: active_query(infrastructure_engine, pid[0], "pg_sleep"))
            stop_started = monotonic()
        assert monotonic() - stop_started < 5
        with store.engine.begin() as conn:
            assert conn.scalar(text("SELECT 19")) == 19


@pytest.mark.usefixtures("observed_store_checkouts")
def test_renewal_native_statement_deadline_reaches_authority_check(
    infrastructure_engine,
):
    def slow_renew(conn, owned):
        conn.execute(text("SELECT pg_sleep(20)"))

    claim = SimpleNamespace(
        task_id=1, attempt=1, release_id="r", holder="owner", deadline=datetime.now(UTC)
    )
    deadline = DatabaseSettings(
        renewal_statement_timeout_seconds=0.1, renewal_lock_timeout_seconds=0.05
    )
    with open_store(settings_for(infrastructure_engine), "pg-renewal-timeout", max_size=1) as store:
        with (
            pytest.raises(DBAPIError) as caught,
            claim_lifetime.maintained_claims(
                store.engine, [claim], "owner", interval=0.01, database=deadline, renew=slow_renew
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


@pytest.mark.usefixtures("observed_store_checkouts")
def test_cli_runtime_failure_reports_its_actual_live_pool_without_sql(infrastructure_engine):
    import json

    import typer
    from typer.testing import CliRunner

    from corpus_structure.cli.failures import failure_boundary
    from corpus_structure.semantic.runtime import open_runtime_engine

    settings = settings_for(infrastructure_engine)
    settings = settings.model_copy(
        update={
            "database": settings.database.model_copy(
                update={"maintenance_url": settings.database.url}
            )
        }
    )
    app = typer.Typer()

    @app.command()
    def inspect_failure():
        with (
            failure_boundary(True),
            open_runtime_engine(
                settings, "diagnostic-invocation", purpose="maintenance"
            ) as engine,
            engine.begin() as conn,
        ):
            conn.execute(text("SELECT 1/0"))

    result = CliRunner().invoke(app, [])
    assert result.exit_code == 1
    assert result.stdout, (result.output, result.exception)
    error = json.loads(result.stdout)["error"]
    assert error["failure"]["sqlstate"] == "22012"
    assert error["failure"]["effects"] == "uncertain"
    assert error["database"]["application_name"] == "diagnostic-invocation"
    assert error["database"]["lifecycle"] == "open"
    assert error["database"]["pool_stats"]["pool_size"] >= 1
    assert error["database"]["usage_scope"] == "pool_connection_scopes_only"
    assert "SELECT" not in result.stdout


@pytest.mark.usefixtures("observed_store_checkouts")
def test_reserved_renewal_runs_while_all_port_capacity_is_borrowed(infrastructure_engine):
    from datetime import timedelta

    renewed = Event()
    observed = []
    claim = SimpleNamespace(
        task_id=1,
        attempt=1,
        holder="owner",
        release_id="release:test",
        deadline=datetime.now(UTC) + timedelta(minutes=5),
    )

    def renew(conn, owned):
        observed.append(conn.scalar(text("SELECT pg_backend_pid()")))
        renewed.set()

    with open_store(
        settings_for(infrastructure_engine), "pg-renewal-reserved", min_size=1, max_size=2
    ) as store:
        with (
            claim_lifetime.maintained_claims(
                store.engine, [claim], "owner", interval=0.01, renew=renew
            ),
            store.engine.begin() as foreground,
        ):
            foreground_pid = foreground.scalar(text("SELECT pg_backend_pid()"))
            renewed.clear()
            assert renewed.wait(3)
            assert observed[-1] != foreground_pid
        with store.engine.begin() as conn:
            assert conn.scalar(text("SELECT 19")) == 19
