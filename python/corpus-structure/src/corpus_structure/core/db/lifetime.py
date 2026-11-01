"""Cancellation belongs to one live borrower, never to the next user of its session."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager
from threading import RLock, get_ident

import psycopg
from sqlalchemy import Connection


class DatabaseOperationCancelled(Exception):
    """The operation owner requested cancellation; no automatic retry is permitted."""


class BorrowerCancellation:
    """Synchronize native cancellation dispatch with checkout registration and release.

    The executing thread still owns cursor/COPY closure and transaction settlement. Keep
    this borrow scope outside its transaction scope so deregistration follows settlement.
    Nested readers may register the same borrower on its executing thread; only the
    outer registration releases the cancellation handle. A different borrower is refused.
    cancel_safe's timeout bounds modern libpq's request, not the operation's shutdown.
    """

    def __init__(self, *, timeout: float = 5.0):
        if timeout <= 0:
            raise ValueError("cancellation request timeout must be positive")
        self.timeout = timeout
        self._lock = RLock()
        self._driver: psycopg.Connection | None = None
        self._requested = False
        self._depth = 0
        self._thread: int | None = None
        self.cleanup_failures: list[Exception] = []

    @property
    def requested(self) -> bool:
        with self._lock:
            return self._requested

    def check_active(self) -> None:
        if self.requested:
            raise DatabaseOperationCancelled("database operation cancellation requested")

    def request_cancel(self) -> None:
        # Hold the lock through dispatch: unregister cannot return this checkout while
        # a cancellation intended for it is waiting to be sent.
        with self._lock:
            self._requested = True
            if self._driver is not None:
                try:
                    self._driver.cancel_safe(timeout=self.timeout)
                except Exception as error:
                    self.cleanup_failures.append(error)

    @contextmanager
    def borrow(self, connection: Connection) -> Generator[None]:
        with self._lock:
            self.check_active()
            driver = connection.connection.driver_connection
            if self._driver is not None and (
                self._driver is not driver or self._thread != get_ident()
            ):
                raise RuntimeError("cancellation handle already owns another borrower")
            if not isinstance(driver, psycopg.Connection):
                raise TypeError("Psycopg cancellation requires a Psycopg borrower")
            self._driver = driver
            self._thread = get_ident()
            self._depth += 1
        try:
            yield
        finally:
            with self._lock:
                self._depth -= 1
                if self._depth == 0:
                    self._driver = None
                    self._thread = None
                if self._depth == 0 and driver.info.transaction_status in (
                    psycopg.pq.TransactionStatus.ACTIVE,
                    psycopg.pq.TransactionStatus.UNKNOWN,
                ):
                    try:
                        connection.invalidate()
                    except Exception as error:
                        self.cleanup_failures.append(error)
