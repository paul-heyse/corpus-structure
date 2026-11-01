"""Cancellation dispatch and borrower return have one synchronized lifetime."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import MagicMock

import psycopg
import pytest
from sqlalchemy import Connection

from corpus_structure.core.db.lifetime import BorrowerCancellation, DatabaseOperationCancelled


def connection_for(driver):
    connection = MagicMock(spec=Connection)
    connection.connection.driver_connection = driver
    return connection


def driver():
    value = MagicMock(spec=psycopg.Connection)
    value.info.transaction_status = psycopg.pq.TransactionStatus.IDLE
    return value


def test_cancel_before_checkout_refuses_without_dispatch():
    cancel = BorrowerCancellation()
    cancel.request_cancel()
    native = driver()
    with pytest.raises(DatabaseOperationCancelled), cancel.borrow(connection_for(native)):
        pytest.fail("must not start work")
    native.cancel_safe.assert_not_called()


def test_late_cancel_after_deregistration_does_not_touch_reused_session():
    cancel = BorrowerCancellation()
    native = driver()
    with cancel.borrow(connection_for(native)):
        pass
    cancel.request_cancel()
    native.cancel_safe.assert_not_called()


def test_return_waits_for_cancel_dispatch_before_reuse():
    cancel = BorrowerCancellation(timeout=0.1)
    native = driver()
    entered, dispatched, release_dispatch, owner_exited = Event(), Event(), Event(), Event()

    def dispatch(*, timeout):
        assert timeout == 0.1
        dispatched.set()
        assert release_dispatch.wait(3)

    native.cancel_safe.side_effect = dispatch

    def owner():
        with cancel.borrow(connection_for(native)):
            entered.set()
            assert dispatched.wait(3)
        owner_exited.set()

    with ThreadPoolExecutor(max_workers=2) as threads:
        executing = threads.submit(owner)
        assert entered.wait(3)
        requesting = threads.submit(cancel.request_cancel)
        assert dispatched.wait(3)
        assert not owner_exited.wait(0.05)
        release_dispatch.set()
        requesting.result(timeout=3)
        executing.result(timeout=3)
    assert owner_exited.is_set()
    native.cancel_safe.assert_called_once()


def test_secondary_cancellation_failure_is_retained_and_deregistration_still_runs():
    cancel = BorrowerCancellation()
    native = driver()
    failure = RuntimeError("cancel request unavailable")
    native.cancel_safe.side_effect = failure
    with cancel.borrow(connection_for(native)):
        cancel.request_cancel()
    assert cancel.cleanup_failures == [failure]
    cancel.request_cancel()
    native.cancel_safe.assert_called_once()


@pytest.mark.parametrize(
    "status", [psycopg.pq.TransactionStatus.UNKNOWN, psycopg.pq.TransactionStatus.ACTIVE]
)
def test_unsettled_physical_session_is_invalidated(status):
    native = driver()
    native.info.transaction_status = status
    connection = connection_for(native)
    with BorrowerCancellation().borrow(connection):
        pass
    connection.invalidate.assert_called_once()


def test_nested_readers_keep_the_outer_borrower_registered():
    cancel = BorrowerCancellation()
    native = driver()
    connection = connection_for(native)
    with cancel.borrow(connection):
        with cancel.borrow(connection):
            pass
        cancel.request_cancel()
    native.cancel_safe.assert_called_once()
    cancel.request_cancel()
    native.cancel_safe.assert_called_once()
