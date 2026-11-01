"""Native ADBC cancellation targets the currently borrowed dedicated session."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic, sleep
from typing import Any, cast
from uuid import uuid4

import adbc_driver_postgresql.dbapi as adbc
from sqlalchemy import text

from corpus_structure.core.db.adbc_lifetime import ADBCBorrowerCancellation, owned_adbc_read


def test_actual_adbc_cancel_settles_slow_query_then_retired_handle_cannot_cancel_next(db_engine):
    name = "ci-adbc-cancel-" + uuid4().hex
    uri = (
        db_engine.url.set(drivername="postgresql")
        .update_query_dict({"application_name": name})
        .render_as_string(hide_password=False)
    )
    handle = ADBCBorrowerCancellation()
    entered = Event()
    failures = []

    def query():
        try:
            with (
                owned_adbc_read(adbc.connect(uri), handle) as connection,
                connection.cursor() as cursor,
            ):
                cursor.adbc_statement.set_options(**{"adbc.postgresql.use_copy": "false"})
                entered.set()
                cursor.execute("SELECT pg_sleep(20)")
                cursor.fetchall()
        except Exception as error:
            failures.append(error)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(query)
        assert entered.wait(timeout=10)
        stop = monotonic() + 10
        while True:
            with db_engine.connect() as control:
                active = control.scalar(
                    text(
                        "SELECT count(*) FROM pg_stat_activity WHERE application_name=:name "
                        "AND state='active' AND wait_event='PgSleep'"
                    ),
                    {"name": name},
                )
            if active:
                break
            assert monotonic() < stop, "native slow ADBC query never became active"
            sleep(0.02)
        handle.request_cancel()
        future.result(timeout=10)
    assert failures
    assert "cancel" in str(failures[0]).lower()
    assert handle.cleanup_failures == []
    handle.request_cancel()
    with adbc.connect(uri) as next_connection, next_connection.cursor() as cursor:
        cursor.execute("SELECT 73::bigint AS value")
        with cursor.fetch_record_batch() as reader:
            assert reader.read_all()["value"].to_pylist() == [73]
        next_connection.rollback()
    with db_engine.connect() as control:
        assert (
            control.scalar(
                text("SELECT count(*) FROM pg_stat_activity WHERE application_name=:name"),
                {"name": name},
            )
            == 0
        )


def test_cleanup_failures_retain_primary_and_attempt_rollback_and_close():
    import pytest

    from corpus_structure.core.db.lifetime import DatabaseOperationCancelled

    calls = []
    rollback = RuntimeError("rollback failed")
    close = RuntimeError("close failed")

    class BrokenRead:
        def rollback(self):
            calls.append("rollback")
            raise rollback

        def close(self):
            calls.append("close")
            raise close

    primary = DatabaseOperationCancelled("capture canceled")
    with (
        pytest.raises(DatabaseOperationCancelled) as caught,
        owned_adbc_read(cast(Any, BrokenRead())),
    ):
        raise primary
    assert caught.value is primary
    assert calls == ["rollback", "close"]
    assert caught.value.__dict__["adbc_cleanup_failures"] == (rollback, close)
    assert len(caught.value.__notes__) == 2


def test_requested_before_registration_still_settles_the_already_owned_connection():
    import pytest

    from corpus_structure.core.db.lifetime import DatabaseOperationCancelled

    calls = []

    class UnregisteredRead:
        def rollback(self):
            calls.append("rollback")

        def close(self):
            calls.append("close")

    token = ADBCBorrowerCancellation()
    token.request_cancel()
    with (
        pytest.raises(DatabaseOperationCancelled),
        owned_adbc_read(cast(Any, UnregisteredRead()), token),
    ):
        pytest.fail("a pre-canceled borrower must not execute")
    assert calls == ["rollback", "close"]
    assert token._connection is None


def test_failed_second_registration_preserves_the_original_cancel_target():
    import pytest

    calls = []

    class Read:
        def __init__(self, name):
            self.name = name

        def rollback(self):
            calls.append((self.name, "rollback"))

        def close(self):
            calls.append((self.name, "close"))

        def adbc_cancel(self):
            calls.append((self.name, "cancel"))

    token = ADBCBorrowerCancellation()
    first, rejected = Read("first"), Read("rejected")
    with token.borrow(cast(Any, first)):
        with (
            pytest.raises(RuntimeError, match="already owns"),
            owned_adbc_read(cast(Any, rejected), token),
        ):
            pytest.fail("a second borrower must not enter")
        token.request_cancel()
    assert calls == [("rejected", "rollback"), ("rejected", "close"), ("first", "cancel")]
