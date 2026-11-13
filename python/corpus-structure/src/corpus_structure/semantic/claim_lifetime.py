"""Maintain existing native leases across long operation-owned inference."""

from __future__ import annotations

import sys
from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from threading import Event, RLock, Thread
from typing import Literal, Protocol

from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.db.lifetime import BorrowerCancellation
from corpus_structure.core.db.store import (
    DatabaseCause,
    DatabaseFailure,
    DatabaseOperationFailure,
    DatabasePhase,
    EffectKnowledge,
    classify_error,
    record_operation_failure,
)
from corpus_structure.settings import DatabaseSettings

from .operations import OperationConflict, renew_claim


class OwnedClaim(Protocol):
    """Physical fence shared by legacy tasks and native request generations."""

    @property
    def task_id(self) -> int: ...
    @property
    def attempt(self) -> int: ...
    @property
    def holder(self) -> str: ...
    @property
    def release_id(self) -> str: ...
    @property
    def deadline(self) -> datetime: ...


class ClaimSettlementUncertain(OperationConflict):
    """Exact completion intent remains available to the caller for receipt recovery."""

    def __init__(self, claim, holder, completion, *, retire=True):
        self.claim = claim
        self.holder = holder
        self.completion = completion
        self.retire = retire
        super().__init__(
            f"completion uncertain for task {claim.task_id}, attempt {claim.attempt}, "
            f"holder {holder}; replay the retained exact completion intent"
        )


class ClaimFenceLost(OperationConflict):
    """One native request lost its publication fence; independent claims remain useful."""

    def __init__(
        self,
        claim: OwnedClaim,
        reason: Literal[
            "fence",
            "cancelled",
            "revoked",
            "support-unavailable",
        ],
    ):
        self.claim, self.reason = claim, reason
        super().__init__(
            f"claim fence lost for task {claim.task_id}, attempt {claim.attempt}: {reason}"
        )


class ClaimOwner:
    def __init__(self, engine, claims, holder, database, check_active):
        self.engine, self.holder, self.database = engine, holder, database
        self._check_active = check_active
        self.lock = RLock()
        self.active = {(claim.task_id, claim.attempt, holder): claim for claim in claims}
        if len(self.active) != len(claims) or any(claim.holder != holder for claim in claims):
            raise ValueError("claim owner requires unique exact task/attempt/holder bindings")
        self.uncertain = {}
        self.lost: dict[tuple[int, int, str], ClaimFenceLost] = {}

    def __call__(self):
        self._check_active()

    def add_claim(self, claim: OwnedClaim) -> None:
        with self.lock:
            self()
            key = (claim.task_id, claim.attempt, self.holder)
            if claim.holder != self.holder or key in self.active or key in self.lost:
                raise OperationConflict("claim is already owned or belongs to another holder")
            self.active[key] = claim

    def check_claim(self, claim: OwnedClaim) -> None:
        """Check one producer without stopping useful independent siblings."""
        self()
        key = (claim.task_id, claim.attempt, self.holder)
        if key in self.lost:
            raise self.lost[key]
        if key not in self.active or claim.holder != self.holder:
            raise OperationConflict("task is no longer active in this owner")
        if key in self.uncertain:
            raise self.uncertain[key]

    def check_settled(self) -> None:
        """Unresolved claim failures and completion custody remain visible at owner exit."""
        failures: list[Exception] = []
        try:
            self()
        except Exception as error:
            failures.append(error)
        failures.extend((*self.lost.values(), *self.uncertain.values()))
        if len(failures) == 1:
            raise failures[0]
        if failures:
            raise ExceptionGroup("claim ownership failures", failures)

    def note_uncertainties(self, error: BaseException) -> None:
        for uncertainty in (*self.lost.values(), *self.uncertain.values()):
            if uncertainty is not error:
                note = str(uncertainty)
                if note not in getattr(error, "__notes__", ()):
                    error.add_note(note)

    def settle(self, claim: OwnedClaim, completion: Callable[[Connection], object]):
        return self._transact(claim, completion, retire=True)

    def retain(self, claim: OwnedClaim, completion: Callable[[Connection], object]):
        """Commit exact private intent while retaining the publication fence."""
        return self._transact(claim, completion, retire=False)

    def _transact(
        self, claim: OwnedClaim, completion: Callable[[Connection], object], *, retire: bool
    ):
        """Serialize renewal and finite exact completion/replay, retaining per-task durability."""
        key = (claim.task_id, claim.attempt, self.holder)
        with self.lock:
            self()
            if key in self.lost:
                raise self.lost[key]
            if key not in self.active:
                raise OperationConflict("task is no longer active in this owner")
            prior = self.uncertain.get(key)
            if prior is not None and (completion is not prior.completion or retire != prior.retire):
                raise prior
            for replay in range(2):
                phase = DatabasePhase.ACQUIRING
                try:
                    with self.engine.connect() as conn, conn.begin():
                        phase = DatabasePhase.EXECUTING
                        _deadlines(
                            conn,
                            self.database,
                            statement_timeout_seconds=self.database.completion_statement_timeout_seconds,
                        )
                        result = completion(conn)
                        phase = DatabasePhase.COMMITTING
                    # Never retire until commit succeeds or an exact replay commits.
                    if retire:
                        del self.active[key]
                    self.uncertain.pop(key, None)
                    return result
                except Exception as error:
                    failure = classify_error(error, phase=phase)
                    prior_uncertainty = self.uncertain.get(key)
                    if prior_uncertainty is not None:
                        error.add_note(str(prior_uncertainty))
                    if phase != DatabasePhase.COMMITTING or failure.cause not in {
                        DatabaseCause.CONNECTION_UNUSABLE,
                        DatabaseCause.IO,
                        DatabaseCause.UNKNOWN_OPERATIONAL,
                    }:
                        if prior_uncertainty is not None and not isinstance(
                            error, OperationConflict
                        ):
                            raise prior_uncertainty from error
                        raise
                    uncertainty = ClaimSettlementUncertain(
                        claim, self.holder, completion, retire=retire
                    )
                    self.uncertain[key] = uncertainty
                    if replay:
                        self.uncertain[key] = uncertainty
                        record_operation_failure(
                            error,
                            DatabaseOperationFailure(
                                failure,
                                operation_id=f"claim:{claim.task_id}:{claim.attempt}",
                                remediation="replay_exact_completion",
                                release_id=claim.release_id,
                            ),
                        )
                        raise uncertainty from error
            raise AssertionError("unreachable settlement state")


def _deadlines(conn, database, *, statement_timeout_seconds: float):
    for setting, seconds in (
        ("statement_timeout", statement_timeout_seconds),
        ("lock_timeout", database.renewal_lock_timeout_seconds),
    ):
        conn.execute(
            text("SELECT set_config(:setting, :value, true)"),
            {"setting": setting, "value": f"{max(1, int(seconds * 1000))}ms"},
        )


def _retryable_renewal_timeout(error: Exception, failure: DatabaseFailure) -> bool:
    if (
        not isinstance(error, DBAPIError)
        or failure.phase != DatabasePhase.EXECUTING
        or failure.effects != EffectKnowledge.ROLLED_BACK
        or failure.invalidated
        or failure.cancellation_requested
    ):
        return False
    message = getattr(getattr(error.orig, "diag", None), "message_primary", None)
    return (failure.sqlstate, message) in {
        ("55P03", "canceling statement due to lock timeout"),
        ("57014", "canceling statement due to statement timeout"),
    }


def _leases_cover_retry(
    conn: Connection, claims: Sequence[OwnedClaim], attempt_budget: timedelta
) -> bool:
    return conn.scalar(
        text(
            "SELECT count(*) FROM ops.task AS task "
            "JOIN unnest(CAST(:tasks AS bigint[]), CAST(:attempts AS bigint[])) "
            "AS active(id, attempt) USING (id, attempt) "
            "WHERE task.status = 'running' AND task.claimed_by = :holder "
            "AND task.lease_until > clock_timestamp() + :budget"
        ),
        {
            "tasks": [claim.task_id for claim in claims],
            "attempts": [claim.attempt for claim in claims],
            "holder": claims[0].holder,
            "budget": attempt_budget,
        },
    ) == len(claims)


@contextmanager
def maintained_claims(
    engine: Engine,
    claims: Sequence[OwnedClaim],
    holder: str,
    *,
    interval: float = 30,
    database: DatabaseSettings | None = None,
    renew: Callable[[Connection, OwnedClaim], None] | None = None,
) -> Generator[ClaimOwner]:
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

    owner = ClaimOwner(engine, claims, holder, database, check_active)
    renew_owned_claim = renew

    def renew_loop() -> None:
        renewed = False
        retry_of: Exception | None = None
        while not stop.wait(interval if retry_of is None else 0):
            active: tuple[OwnedClaim, ...] = ()
            phase = DatabasePhase.ACQUIRING
            effects = EffectKnowledge.NONE
            claim = claims[0] if len(claims) == 1 else None
            try:
                with owner.lock:
                    active = tuple(
                        claim for key, claim in owner.active.items() if key not in owner.uncertain
                    )
                if not active:
                    retry_of = None
                    continue
                with engine.connect() as conn, cancellation.borrow(conn):
                    if retry_of is not None:
                        with owner.lock, conn.begin():
                            phase = DatabasePhase.EXECUTING
                            _deadlines(
                                conn,
                                database,
                                statement_timeout_seconds=database.renewal_statement_timeout_seconds,
                            )
                            if not _leases_cover_retry(
                                conn,
                                active,
                                timedelta(
                                    seconds=database.renewal_statement_timeout_seconds * len(active)
                                ),
                            ):
                                raise retry_of
                    for claim in active:
                        key = (claim.task_id, claim.attempt, holder)
                        with owner.lock:
                            if key not in owner.active or key in owner.uncertain:
                                continue
                            phase = DatabasePhase.ACQUIRING
                            effects = EffectKnowledge.NONE
                            try:
                                with conn.begin():
                                    phase = DatabasePhase.EXECUTING
                                    effects = EffectKnowledge.UNCERTAIN
                                    _deadlines(
                                        conn,
                                        database,
                                        statement_timeout_seconds=database.renewal_statement_timeout_seconds,
                                    )
                                    cancellation.check_active()
                                    if renew_owned_claim is not None:
                                        renew_owned_claim(conn, claim)
                                    else:
                                        from ._operation_calls import TaskAttempt, TaskId

                                        renew_claim(
                                            conn,
                                            task_id=TaskId(claim.task_id),
                                            attempt=TaskAttempt(claim.attempt),
                                            holder=holder,
                                        )
                                    cancellation.check_active()
                                    phase = DatabasePhase.COMMITTING
                                effects = EffectKnowledge.COMMITTED
                                renewed = True
                            except ClaimFenceLost as loss:
                                # A typed native refusal concerns only this exact
                                # producer. Prior sibling renewal commits survive.
                                if loss.claim != claim:
                                    raise OperationConflict(
                                        "renewal loss belongs to another claim"
                                    ) from loss
                                owner.lost[key] = loss
                                del owner.active[key]
                                effects = EffectKnowledge.ROLLED_BACK
                            except Exception:
                                if phase != DatabasePhase.COMMITTING and not conn.invalidated:
                                    effects = EffectKnowledge.ROLLED_BACK
                                raise
                    retry_of = None
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
                if (
                    retry_of is None
                    and _retryable_renewal_timeout(error, failure)
                    and (renewed or all(c.deadline > datetime.now(UTC) for c in active))
                ):
                    # Release the checkout and serialization lock before the retry.
                    retry_of = error
                    continue
                if retry_of is not None and retry_of is not error:
                    prior_state = classify_error(retry_of).sqlstate
                    error.add_note(f"renewal retry followed SQLSTATE {prior_state}")
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

    thread = Thread(target=renew_loop, name="corpus-claim-renewal", daemon=True)
    thread.start()
    try:
        yield owner
        owner.check_settled()
    finally:
        primary = sys.exception()
        if primary is not None:
            owner.note_uncertainties(primary)
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
            owner.check_settled()
