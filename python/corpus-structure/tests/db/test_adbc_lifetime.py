"""Native ADBC cancellation targets the currently borrowed dedicated session."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from time import monotonic, sleep
from typing import Any, cast
from uuid import uuid4

import pytest
from sqlalchemy import text

from corpus_structure.core.db.adbc_lifetime import (
    ADBCBorrowerCancellation,
    open_adbc_connection,
    owned_adbc_child,
    owned_adbc_read,
)


@pytest.mark.parametrize("resolver", ["builtin", "server"])
@pytest.mark.parametrize("configured", [False, True])
def test_factory_selects_explicit_driver_and_resolver(monkeypatch, resolver, configured):
    from corpus_structure.core.db import adbc_lifetime

    observed = []
    connection = object()

    def connect(*args, **kwargs):
        observed.append((args, kwargs))
        return connection

    monkeypatch.setattr(adbc_lifetime.adbc, "connect", connect)
    monkeypatch.setattr(adbc_lifetime.adbc_manager, "connect", connect)
    driver = Path("/configured/postgresql.so") if configured else None
    assert (
        open_adbc_connection(
            "postgresql://reader@/selected", driver_path=driver, resolver_mode=resolver
        )
        is connection
    )
    options = {"adbc.postgresql.type_resolver_mode": resolver}
    assert observed == [
        (
            (),
            {
                "driver": str(driver),
                "entrypoint": "AdbcDriverPostgresqlInit",
                "db_kwargs": {"uri": "postgresql://reader@/selected", **options},
            },
        )
        if configured
        else (("postgresql://reader@/selected",), {"db_kwargs": options})
    ]


def test_factory_refuses_unsupported_resolver_before_acquisition(monkeypatch):
    from corpus_structure.core.db import adbc_lifetime

    def forbidden(*args, **kwargs):
        pytest.fail("invalid resolver must not acquire a native session")

    monkeypatch.setattr(adbc_lifetime.adbc, "connect", forbidden)
    monkeypatch.setattr(adbc_lifetime.adbc_manager, "connect", forbidden)
    with pytest.raises(ValueError, match="unsupported ADBC PostgreSQL resolver"):
        open_adbc_connection("unused", driver_path=None, resolver_mode=cast(Any, "auto"))


@pytest.mark.parametrize("configured", [False, True])
def test_factory_preserves_acquisition_exception(monkeypatch, configured):
    from corpus_structure.core.db import adbc_lifetime

    failure = RuntimeError("native acquisition failed")

    def refused(*args, **kwargs):
        raise failure

    monkeypatch.setattr(adbc_lifetime.adbc, "connect", refused)
    monkeypatch.setattr(adbc_lifetime.adbc_manager, "connect", refused)
    with pytest.raises(RuntimeError) as caught:
        open_adbc_connection(
            "unused",
            driver_path="/configured/postgresql.so" if configured else None,
            resolver_mode="builtin",
        )
    assert caught.value is failure


@pytest.mark.parametrize("configured", [False, True])
@pytest.mark.parametrize("resolver", ["builtin", "server"])
def test_actual_factory_driver_resolver_parity(db_engine, configured, resolver):
    import adbc_driver_postgresql

    uri = db_engine.url.set(drivername="postgresql").render_as_string(hide_password=False)
    driver = adbc_driver_postgresql._driver_path() if configured else None
    with db_engine.connect() as control:
        expected_principal = control.scalar(text("SELECT current_user"))
    with (
        owned_adbc_read(
            open_adbc_connection(uri, driver_path=driver, resolver_mode=resolver)
        ) as conn,
        conn.cursor() as cursor,
    ):
        cursor.adbc_statement.set_options(**{"adbc.postgresql.use_copy": "false"})
        cursor.execute("SELECT 73::bigint AS value, current_user::text AS principal")
        assert cursor.fetchone() == (73, expected_principal)


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
                owned_adbc_read(
                    open_adbc_connection(uri, driver_path=None, resolver_mode="builtin"), handle
                ) as connection,
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
    with (
        owned_adbc_read(
            open_adbc_connection(uri, driver_path=None, resolver_mode="builtin")
        ) as next_connection,
        next_connection.cursor() as cursor,
    ):
        cursor.execute("SELECT 73::bigint AS value")
        with cursor.fetch_record_batch() as reader:
            assert reader.read_all()["value"].to_pylist() == [73]
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


def test_operation_request_reaches_both_backends_even_if_dispatch_is_interrupted(monkeypatch):
    import pytest

    from corpus_structure.core.db.cancellation import OperationCancellation
    from corpus_structure.core.db.lifetime import DatabaseOperationCancelled

    owner = OperationCancellation()
    calls = []

    def interrupted():
        calls.append("postgresql")
        raise KeyboardInterrupt("dispatch interrupted")

    monkeypatch.setattr(owner.postgresql, "request_cancel", interrupted)
    monkeypatch.setattr(owner.adbc, "request_cancel", lambda: calls.append("adbc"))
    with pytest.raises(BaseExceptionGroup) as caught:
        owner.request_cancel()
    assert calls == ["postgresql", "adbc"]
    assert isinstance(caught.value.exceptions[0], KeyboardInterrupt)
    with pytest.raises(DatabaseOperationCancelled):
        owner.check_active()


def test_operation_request_before_publication_refuses_atomic_effect():
    import pytest

    from corpus_structure.core.db.cancellation import OperationCancellation
    from corpus_structure.core.db.lifetime import DatabaseOperationCancelled

    owner = OperationCancellation()
    owner.request_cancel()
    with pytest.raises(DatabaseOperationCancelled), owner.publication():
        pytest.fail("a canceled operation cannot publish")


def test_capture_registers_actual_binding_queries_before_bulk_acquisition(db_engine, monkeypatch):
    from corpus_structure.core.db.cancellation import OperationCancellation
    from corpus_structure.semantic import analytics, query

    owner = OperationCancellation(timeout=2)
    entered = Event()
    failures = []
    backend = []

    def bind(conn, *args):
        backend.append(conn.scalar(text("SELECT pg_backend_pid()")))
        entered.set()
        conn.execute(text("SELECT pg_sleep(20)"))
        raise AssertionError("capture must cancel before binding can return")

    monkeypatch.setattr(query, "bind_realization", bind)
    monkeypatch.setattr(
        analytics,
        "open_adbc_connection",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("metadata cancellation must not acquire bulk transport")
        ),
    )

    def capture():
        try:
            analytics.capture_packet(db_engine, "unbound", "unused", cancellation=owner)
        except Exception as error:
            failures.append(error)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(capture)
        assert entered.wait(timeout=10)
        deadline = monotonic() + 10
        while True:
            with db_engine.connect() as control:
                active = control.scalar(
                    text(
                        "SELECT count(*) FROM pg_stat_activity WHERE pid=:pid "
                        "AND state='active' AND wait_event='PgSleep'"
                    ),
                    {"pid": backend[0]},
                )
            if active:
                break
            assert monotonic() < deadline, "binding query did not become active"
            sleep(0.02)
        owner.request_cancel()
        future.result(timeout=10)
    assert len(failures) == 1
    assert "cancel" in str(failures[0]).lower()
    assert owner.cleanup_failures == []
    owner.request_cancel()
    with db_engine.connect() as conn:
        assert conn.scalar(text("SELECT 73")) == 73


@pytest.mark.parametrize("primary", [RuntimeError("body"), KeyboardInterrupt("body")])
def test_child_retirement_preserves_body_and_all_nested_cleanup(primary):
    calls = []
    failures = {name: RuntimeError(name) for name in ("reader", "cursor", "rollback", "connection")}

    class Child:
        def __init__(self, name):
            self.name = name

        def close(self):
            calls.append(self.name)
            raise failures[self.name]

    class Connection(Child):
        def rollback(self):
            calls.append("rollback")
            raise failures["rollback"]

    token = ADBCBorrowerCancellation()
    with (
        pytest.raises(type(primary)) as caught,
        owned_adbc_read(cast(Any, Connection("connection")), token),
        owned_adbc_child(Child("cursor")),
        owned_adbc_child(Child("reader")),
    ):
        raise primary
    assert caught.value is primary
    assert calls == ["reader", "cursor", "rollback", "connection"]
    assert primary.__dict__["adbc_cleanup_failures"] == tuple(failures[name] for name in calls)
    assert token._connection is None


def test_child_cleanup_only_raises_first_failure_and_retains_subsequent_failures():
    first, second = RuntimeError("reader"), SystemExit("cursor")

    class Child:
        def __init__(self, error):
            self.error = error

        def close(self):
            raise self.error

    with (
        pytest.raises(RuntimeError) as caught,
        owned_adbc_child(Child(second)),
        owned_adbc_child(Child(first)),
    ):
        pass
    assert caught.value is first
    assert first.__dict__["adbc_cleanup_failures"] == (second,)
