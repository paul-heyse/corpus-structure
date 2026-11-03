"""One operation request spanning its PostgreSQL and ADBC borrowers."""

from collections.abc import Generator
from contextlib import contextmanager
from threading import RLock

from .adbc_lifetime import ADBCBorrowerCancellation
from .lifetime import BorrowerCancellation, DatabaseOperationCancelled


class OperationCancellation:
    """Compose native handles without transferring their settlement responsibilities.

    Requests are sticky across the metadata-to-bulk handoff. Each backend keeps its own
    synchronized registration and retirement; neither handle can cancel a later borrower.
    The execution thread still owns rollback, reader closure and snapshot settlement.
    """

    def __init__(self, *, timeout: float = 5.0):
        self.postgresql = BorrowerCancellation(timeout=timeout)
        self.adbc = ADBCBorrowerCancellation()
        self._lock = RLock()
        self._requested = False

    @property
    def requested(self) -> bool:
        with self._lock:
            return self._requested or self.postgresql.requested or self.adbc.requested

    @property
    def cleanup_failures(self) -> list[Exception]:
        return [*self.postgresql.cleanup_failures, *self.adbc.cleanup_failures]

    def check_active(self) -> None:
        if self.requested:
            raise DatabaseOperationCancelled("database operation cancellation requested")

    def request_cancel(self) -> None:
        with self._lock:
            self._requested = True
        # Never hold the publication lock during native dispatch or settlement. Always
        # attempt both backends even when an interruption occurs during the first one.
        failures: list[BaseException] = []
        for handle in (self.postgresql, self.adbc):
            try:
                handle.request_cancel()
            except BaseException as error:
                failures.append(error)
        if failures:
            raise BaseExceptionGroup("operation cancellation dispatch failed", failures)

    @contextmanager
    def publication(self) -> Generator[None]:
        """Linearize cancellation against the final atomic destination publication.

        A request preceding this boundary refuses publication. A racing request waits
        for the atomic effect and cannot turn an already published result into failure.
        """
        with self._lock:
            self.check_active()
            yield
