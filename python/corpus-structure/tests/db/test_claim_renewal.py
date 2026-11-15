"""Renewal owns one idle-capable checkout and retries only observed rollback."""

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from threading import Event, get_ident
from time import monotonic, sleep
from types import SimpleNamespace
from unittest.mock import MagicMock

import psycopg
import pytest
from sqlalchemy import Connection
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.db.store import DatabasePhase, EffectKnowledge, classify_error
from corpus_structure.semantic.claim_lifetime import (
    _retryable_renewal_failure,
    maintained_claims,
)


def fixture_connection():
    conn = MagicMock(spec=Connection)
    driver = MagicMock(spec=psycopg.Connection)
    driver.info.transaction_status = psycopg.pq.TransactionStatus.IDLE
    conn.connection.driver_connection = driver
    conn.invalidated = False
    conn.scalar.return_value = 1
    return conn


def fake_engine(conn):
    acquired = []
    released = Event()

    @contextmanager
    def connect():
        acquired.append(get_ident())
        try:
            yield conn
        finally:
            released.set()

    return SimpleNamespace(connect=connect), acquired, released


def claim():
    return SimpleNamespace(
        task_id=1, attempt=1, holder="owner", release_id="release:test",
        deadline=datetime.now(UTC) + timedelta(minutes=5),
    )


def await_failure(owner):
    deadline = monotonic() + 3
    while monotonic() < deadline:
        try:
            owner()
        except Exception as error:
            return error
        sleep(0.001)
    pytest.fail("renewal did not report failure")


def test_reservation_is_acquired_on_renewal_thread_before_owner_yield_and_released_after_exit():
    conn = fixture_connection()
    engine, acquired, released = fake_engine(conn)
    with maintained_claims(engine, [], "owner", interval=60):
        assert len(acquired) == 1
        assert acquired[0] != get_ident()
        conn.begin.assert_not_called()
        assert not released.is_set()
    assert released.is_set()


@pytest.mark.parametrize("kind", [psycopg.errors.LockNotAvailable, psycopg.errors.QueryCanceled])
def test_single_retry_uses_sqlstate_after_successful_rollback_regardless_of_message(kind):
    conn = fixture_connection()
    engine, acquired, released = fake_engine(conn)
    completed = Event()
    calls = []

    def renew(connection, owned):
        calls.append(owned.task_id)
        if len(calls) == 1:
            raise DBAPIError("renew", {}, kind("arbitrary localized cause"))
        # Retire after the successful retry so further clock ticks do no work.
        owner.active.clear()
        completed.set()

    with maintained_claims(engine, [claim()], "owner", interval=0.001, renew=renew) as owner:
        assert completed.wait(3)
    assert calls == [1, 1]
    assert len(acquired) == 1 and released.is_set()
    conn.begin.return_value.rollback.assert_called_once()
    assert conn.begin.return_value.commit.call_count == 1


@pytest.mark.parametrize("failure_kind", ["rollback", "commit", "lease", "invalidated"])
def test_uncertain_or_uncovered_renewal_never_retries(failure_kind):
    conn = fixture_connection()
    engine, _, _ = fake_engine(conn)
    original = DBAPIError("renew", {}, psycopg.errors.QueryCanceled("native cause"))
    calls = []
    if failure_kind == "rollback":
        conn.begin.return_value.rollback.side_effect = RuntimeError("rollback failed")
    elif failure_kind == "commit":
        conn.begin.return_value.commit.side_effect = original
    elif failure_kind == "lease":
        conn.scalar.return_value = 0
    elif failure_kind == "invalidated":
        conn.invalidated = True

    def renew(connection, owned):
        calls.append(owned.task_id)
        if failure_kind != "commit":
            raise original

    with pytest.raises(Exception):
        with maintained_claims(engine, [claim()], "owner", interval=0.001, renew=renew) as owner:
            error = await_failure(owner)
            if failure_kind == "rollback":
                assert error is original
                assert str(error.__cause__) == "rollback failed"
                assert error.__dict__["database_cleanup_unresolved"] is True
    assert calls == [1]


def test_client_requested_cancellation_is_never_retryable():
    error = DBAPIError("renew", {}, psycopg.errors.QueryCanceled("native cause"))
    failure = classify_error(
        error, phase=DatabasePhase.EXECUTING,
        effects=EffectKnowledge.ROLLED_BACK, cancellation_requested=True,
    )
    assert not _retryable_renewal_failure(error, failure)


def test_second_native_failure_keeps_both_actual_causes_and_does_not_retry_again():
    conn = fixture_connection()
    engine, _, _ = fake_engine(conn)
    errors = [
        DBAPIError("renew", {}, psycopg.errors.LockNotAvailable("first cause")),
        DBAPIError("renew", {}, psycopg.errors.QueryCanceled("second cause")),
    ]
    calls = []

    def renew(connection, owned):
        index = len(calls)
        calls.append(index)
        raise errors[index]

    with pytest.raises(DBAPIError) as caught:
        with maintained_claims(engine, [claim()], "owner", interval=0.001, renew=renew) as owner:
            assert await_failure(owner) is errors[1]
    assert caught.value is errors[1]
    assert caught.value.__cause__ is errors[0]
    assert calls == [0, 1]


def test_failed_initial_reservation_never_yields_foreground_owner():
    error = RuntimeError("checkout unavailable")
    engine = SimpleNamespace(connect=MockFailingConnect(error))
    with pytest.raises(RuntimeError, match="checkout unavailable"):
        with maintained_claims(engine, [], "owner"):
            pytest.fail("foreground owner cannot run without reserved capacity")


class MockFailingConnect:
    def __init__(self, error):
        self.error = error

    def __call__(self):
        raise self.error
