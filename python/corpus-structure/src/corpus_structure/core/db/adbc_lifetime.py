"""Explicit ADBC acquisition and cancellation scoped to one owned physical session."""

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Literal

import adbc_driver_manager.dbapi as adbc_manager
import adbc_driver_postgresql.dbapi as adbc
from adbc_driver_manager.dbapi import Connection

from .lifetime import DatabaseOperationCancelled


def open_adbc_connection(
    uri: str,
    *,
    driver_path: str | Path | None,
    resolver_mode: Literal["builtin", "server"],
) -> Connection:
    """Acquire an explicit driver/resolver; callers own purpose, transaction and lifetime.

    The URI is already derived for the operation's purpose. Acquiring a connection
    does not register cancellation or import a snapshot; compose the returned session
    with ``owned_adbc_read`` before using it.
    """
    if resolver_mode not in ("builtin", "server"):
        raise ValueError(f"unsupported ADBC PostgreSQL resolver mode: {resolver_mode!r}")
    options = {"adbc.postgresql.type_resolver_mode": resolver_mode}
    if driver_path is None:
        return adbc.connect(uri, db_kwargs=options)
    return adbc_manager.connect(
        driver=str(driver_path),
        entrypoint="AdbcDriverPostgresqlInit",
        db_kwargs={"uri": uri, **options},
    )


class ADBCBorrowerCancellation:
    """Retire native cancellation before the session can acquire another borrower.

    Cursor/reader closure and rollback stay with the execution owner. Hold ``borrow``
    until those settle; native dispatch and deregistration synchronize on one lock.
    """

    def __init__(self):
        self._lock = RLock()
        self._connection: Connection | None = None
        self._requested = False
        self.cleanup_failures: list[Exception] = []

    @property
    def requested(self) -> bool:
        with self._lock:
            return self._requested

    def check_active(self) -> None:
        if self.requested:
            raise DatabaseOperationCancelled("ADBC operation cancellation requested")

    def request_cancel(self) -> None:
        with self._lock:
            self._requested = True
            if self._connection is not None:
                try:
                    self._connection.adbc_cancel()
                except Exception as error:
                    self.cleanup_failures.append(error)

    @contextmanager
    def borrow(self, connection: Connection) -> Generator[None]:
        with self._lock:
            self.check_active()
            if self._connection is not None:
                raise RuntimeError("ADBC cancellation handle already owns a borrower")
            self._connection = connection
        try:
            yield
        finally:
            with self._lock:
                self._connection = None


@contextmanager
def owned_adbc_read(
    connection: Connection, cancellation: ADBCBorrowerCancellation | None = None
) -> Generator[Connection]:
    """Own registration, rollback and close while retaining the failure reaching this owner.

    Child cursor/reader contexts settle inside this scope. Their own exit failures
    may replace an earlier body failure before it reaches this connection owner.
    """
    from contextlib import nullcontext

    settled = False

    def settle():
        nonlocal settled
        failures = []
        with cancellation._lock if cancellation is not None else nullcontext():
            for cleanup in (connection.rollback, connection.close):
                try:
                    cleanup()
                except BaseException as failure:
                    failures.append(failure)
            if cancellation is not None and cancellation._connection is connection:
                # Retirement and physical close are atomic with cancellation dispatch.
                cancellation._connection = None
        settled = True
        return failures

    def retain_cleanup(error, failures):
        if failures:
            error.__dict__["adbc_cleanup_failures"] = tuple(failures)
            for failure in failures:
                error.add_note(f"ADBC read cleanup also failed: {failure!r}")

    try:
        with cancellation.borrow(connection) if cancellation is not None else nullcontext():
            try:
                yield connection
            except BaseException as error:
                retain_cleanup(error, settle())
                raise
            else:
                failures = settle()
                if len(failures) == 1:
                    raise failures[0]
                if failures:
                    raise BaseExceptionGroup("ADBC read cleanup failed", failures)
    except BaseException as error:
        if not settled:
            # A fresh connection is already owned even when registration refuses entry.
            retain_cleanup(error, settle())
        raise
