"""Maintain existing native leases across long operation-owned inference."""

from __future__ import annotations

import sys
from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from threading import Event, Thread

from sqlalchemy import Engine, text

from corpus_structure.core.db.lifetime import BorrowerCancellation
from corpus_structure.core.db.store import (
    DatabaseCause,
    DatabaseOperationFailure,
    DatabasePhase,
    EffectKnowledge,
    classify_error,
    record_operation_failure,
)
from corpus_structure.settings import DatabaseSettings

from .operation_results import ClaimedTask
from .operations import renew_claim


@contextmanager
def maintained_claims(
    engine: Engine,
    claims: Sequence[ClaimedTask],
    holder: str,
    *,
    interval: float = 30,
    database: DatabaseSettings | None = None,
) -> Generator[Callable[[], None]]:
    """Renew on an owned, cancellable checkout with finite server query deadlines.

    Stop cancels the live renewal and joins its owner. Server deadlines and modern libpq
    cancellation timeout are useful bounds, not a hard total shutdown guarantee.
    """
    if interval <= 0:
        raise ValueError("claim renewal interval must be positive")
    database = database or getattr(engine, "_corpus_database_settings", None) or DatabaseSettings()
    cancellation = BorrowerCancellation(timeout=database.cancel_request_timeout_seconds)
    stop = Event()
    failed = Event()
    failures: list[Exception] = []

    def check_active() -> None:
        if failed.is_set():
            raise failures[0]

    def renew() -> None:
        while not stop.wait(interval):
            phase = DatabasePhase.ACQUIRING
            effects = EffectKnowledge.NONE
            claim = claims[0] if len(claims) == 1 else None
            try:
                with engine.connect() as conn, cancellation.borrow(conn):
                    try:
                        with conn.begin():
                            phase = DatabasePhase.EXECUTING
                            effects = EffectKnowledge.UNCERTAIN
                            statement_ms = max(
                                1, int(database.renewal_statement_timeout_seconds * 1000)
                            )
                            lock_ms = max(1, int(database.renewal_lock_timeout_seconds * 1000))
                            conn.execute(
                                text("SELECT set_config('statement_timeout', :value, true)"),
                                {"value": f"{statement_ms}ms"},
                            )
                            conn.execute(
                                text("SELECT set_config('lock_timeout', :value, true)"),
                                {"value": f"{lock_ms}ms"},
                            )
                            for claim in claims:
                                cancellation.check_active()
                                renew_claim(
                                    conn,
                                    task_id=claim.task_id,
                                    attempt=claim.attempt,
                                    holder=holder,
                                )
                            cancellation.check_active()
                            phase = DatabasePhase.COMMITTING
                        effects = EffectKnowledge.COMMITTED
                    except Exception:
                        if phase != DatabasePhase.COMMITTING and not conn.invalidated:
                            effects = EffectKnowledge.ROLLED_BACK
                        raise
            except Exception as error:
                failure = classify_error(
                    error,
                    phase=phase,
                    effects=effects,
                    cancellation_requested=cancellation.requested,
                )
                if (
                    stop.is_set()
                    and cancellation.requested
                    and failure.cause == DatabaseCause.CANCELLED
                ):
                    return
                record_operation_failure(
                    error,
                    DatabaseOperationFailure(
                        failure,
                        operation_id=(f"claim:{claim.task_id}:{claim.attempt}" if claim else None),
                        remediation="stop_claimed_work",
                        release_id=claim.release_id if claim else None,
                    ),
                )
                failures.append(error)
                failed.set()
                return

    thread = Thread(target=renew, name="corpus-claim-renewal", daemon=True)
    thread.start()
    try:
        yield check_active
        check_active()
    finally:
        primary = sys.exception()
        stop.set()
        cancellation.request_cancel()
        thread.join()
        if primary is not None:
            for cleanup in cancellation.cleanup_failures:
                primary.add_note("renewal cancellation request failed: " + repr(cleanup))
        elif cancellation.cleanup_failures:
            raise ExceptionGroup(
                "renewal cancellation request failed", cancellation.cleanup_failures
            )
        if primary is None:
            check_active()
