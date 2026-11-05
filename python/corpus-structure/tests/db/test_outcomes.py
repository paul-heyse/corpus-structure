"""Independent physical-cause and operation-context controls without a server."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import psycopg
import pytest
from psycopg_pool import PoolClosed, PoolTimeout, TooManyRequests
from pydantic import ValidationError
from sqlalchemy import Engine, create_engine
from sqlalchemy.exc import OperationalError

from corpus_structure.core.db.store import (
    DatabaseCause,
    DatabaseOperationFailure,
    DatabasePhase,
    EffectKnowledge,
    classify_error,
    diagnostic_fields,
    operation_failure,
    record_operation_failure,
)
from corpus_structure.semantic import publication
from corpus_structure.semantic.publication import PublicationBatch, PublicationReceipt
from corpus_structure.settings import DatabaseSettings


@pytest.mark.parametrize(
    "error,expected",
    [
        (PoolClosed(), DatabaseCause.INVENTORY_CLOSED),
        (TooManyRequests(), DatabaseCause.ADMISSION_PRESSURE),
        (PoolTimeout(), DatabaseCause.ACQUISITION_DEADLINE),
        (psycopg.errors.SerializationFailure(), DatabaseCause.SERIALIZATION),
        (psycopg.errors.DeadlockDetected(), DatabaseCause.DEADLOCK),
        (psycopg.errors.QueryCanceled(), DatabaseCause.CANCELLED),
        (psycopg.errors.CheckViolation(), DatabaseCause.CONSTRAINT),
        (psycopg.OperationalError("no code"), DatabaseCause.UNKNOWN_OPERATIONAL),
        (RuntimeError("defect"), DatabaseCause.UNKNOWN),
    ],
)
def test_native_causes_do_not_select_effects_or_recovery(error, expected):
    failure = classify_error(error)
    assert failure.cause is expected
    assert failure.phase is DatabasePhase.UNKNOWN
    assert failure.effects is EffectKnowledge.UNCERTAIN


def test_sqlalchemy_invalidation_survives_single_native_unwrap():
    error = OperationalError(None, None, psycopg.OperationalError(), connection_invalidated=True)
    failure = classify_error(
        error, phase=DatabasePhase.COMMITTING, effects=EffectKnowledge.UNCERTAIN
    )
    assert failure.cause is DatabaseCause.CONNECTION_UNUSABLE
    assert failure.invalidated and failure.effects is EffectKnowledge.UNCERTAIN


def test_context_keeps_native_exception_and_safe_fields():
    error = psycopg.errors.QueryCanceled("secret SQL")
    record_operation_failure(
        error,
        DatabaseOperationFailure(
            classify_error(
                error,
                phase=DatabasePhase.EXECUTING,
                effects=EffectKnowledge.ROLLED_BACK,
                cancellation_requested=True,
            ),
            "batch",
            "stop_claimed_work",
            "release",
            "realization",
        ),
    )
    assert operation_failure(error).failure.cancellation_requested
    assert operation_failure(error).operation_id == "batch"
    assert diagnostic_fields(SimpleNamespace(sqlstate="57014", message_hint="retry later")) == {
        "sqlstate": "57014",
        "message_hint": "retry later",
    }
    assert diagnostic_fields(SimpleNamespace()) == {}


@pytest.mark.parametrize(
    "settings",
    [
        {"pool_min_size": 3, "pool_max_size": 2},
        {"pool_max_waiting": 0},
        {"checkout_timeout_seconds": 0},
        {"cancel_request_timeout_seconds": 0},
        {"completion_statement_timeout_seconds": 0},
        {"completion_statement_timeout_seconds": float("inf")},
        {"completion_statement_timeout_seconds": float("nan")},
        {"renewal_statement_timeout_seconds": 1, "renewal_lock_timeout_seconds": 2},
    ],
)
def test_invalid_pool_and_renewal_limits_refuse(settings):
    with pytest.raises(ValidationError):
        DatabaseSettings(**settings)


def test_completion_and_renewal_budgets_have_separate_defaults():
    settings = DatabaseSettings()
    assert settings.completion_statement_timeout_seconds == 120
    assert settings.renewal_statement_timeout_seconds == 10
    assert settings.renewal_lock_timeout_seconds == 5


def test_precheckout_failure_never_looks_up_a_receipt(monkeypatch):
    engine = MagicMock(spec=Engine)
    engine.connect.side_effect = PoolClosed()

    def unexpected(*args):
        pytest.fail("pre-checkout failure must not inspect receipts or execute")

    monkeypatch.setattr(publication, "lookup_receipt", unexpected)
    with pytest.raises(PoolClosed) as caught:
        publication._publish(engine, PublicationBatch("r", "z", "b"), unexpected, attempts=3)
    context = operation_failure(caught.value)
    assert context.failure.phase is DatabasePhase.ACQUIRING
    assert context.failure.effects is EffectKnowledge.NONE


def test_unclassified_execution_failure_rolls_back_without_hidden_replay(monkeypatch):
    engine = create_engine("sqlite://")
    seen = []

    def execute(connection, batch):
        seen.append(batch)
        raise psycopg.OperationalError("unknown operational")

    monkeypatch.setattr(
        publication, "lookup_receipt", lambda *args: pytest.fail("no commit attempt")
    )
    try:
        with pytest.raises(psycopg.OperationalError) as caught:
            publication._publish(engine, PublicationBatch("r", "z", "b"), execute, attempts=3)
        failure = operation_failure(caught.value).failure
        assert failure.cause is DatabaseCause.UNKNOWN_OPERATIONAL
        assert failure.phase is DatabasePhase.EXECUTING
        assert failure.effects is EffectKnowledge.ROLLED_BACK
        assert len(seen) == 1
    finally:
        engine.dispose()


def test_commit_exception_resolves_but_unknown_defect_never_replays(monkeypatch):
    engine = create_engine("sqlite://")
    attempts = []

    def publish(conn, batch):
        attempts.append(batch)
        return PublicationReceipt("b", 1, "digest")

    def broken_commit(driver):
        raise RuntimeError("unclassified commit failure")

    monkeypatch.setattr(engine.dialect, "do_commit", broken_commit)
    monkeypatch.setattr(publication, "lookup_receipt", lambda *args: None)
    try:
        with pytest.raises(RuntimeError) as caught:
            publication._publish(engine, PublicationBatch("r", "z", "b"), publish, attempts=3)
        assert operation_failure(caught.value).failure.effects is EffectKnowledge.UNCERTAIN
        assert operation_failure(caught.value).remediation == "resolve_original_identity"
        assert len(attempts) == 1
    finally:
        engine.dispose()


def test_failed_receipt_resolution_retains_original_identity_and_uncertainty(monkeypatch):
    engine = create_engine("sqlite://")
    original = psycopg.OperationalError("acknowledgement missing")
    resolution = PoolTimeout("resolution cannot acquire")

    def publish(conn, batch):
        return PublicationReceipt("b", 1, "digest")

    def commit(driver):
        raise original

    def lookup(*args):
        raise resolution

    monkeypatch.setattr(engine.dialect, "do_commit", commit)
    monkeypatch.setattr(publication, "lookup_receipt", lookup)
    try:
        with pytest.raises(psycopg.OperationalError) as caught:
            publication._publish(engine, PublicationBatch("r", "z", "b"), publish, attempts=3)
        assert caught.value.__cause__ is resolution
        context = operation_failure(caught.value)
        assert context.operation_id == "b" and context.release_id == "r"
        assert context.realization_id == "z"
        assert context.failure.phase is DatabasePhase.RESOLVING
        assert context.failure.effects is EffectKnowledge.UNCERTAIN
        assert context.failure.cause is DatabaseCause.ACQUISITION_DEADLINE
        assert context.remediation == "resolve_original_identity"
    finally:
        engine.dispose()


def test_failed_rollback_preserves_primary_and_uncertain_effects(monkeypatch):
    engine = create_engine("sqlite://")
    primary = RuntimeError("encoder defect")
    rollback = engine.dialect.do_rollback
    calls = []

    def execute(conn, batch):
        raise primary

    def fail_rollback(driver):
        calls.append(1)
        if len(calls) == 2:  # initial connection setup also calls rollback
            raise RuntimeError("rollback unavailable")
        rollback(driver)

    monkeypatch.setattr(engine.dialect, "do_rollback", fail_rollback)
    try:
        with pytest.raises(RuntimeError) as caught:
            publication._publish(engine, PublicationBatch("r", "z", "b"), execute, attempts=3)
        assert caught.value is primary
        assert operation_failure(caught.value).failure.effects is EffectKnowledge.UNCERTAIN
        assert any("rollback failed" in note for note in caught.value.__notes__)
    finally:
        engine.dispose()


def test_receipt_identity_conflict_is_never_relabelled_as_connectivity(monkeypatch):
    engine = create_engine("sqlite://")

    def publish(conn, batch):
        return PublicationReceipt("b", 1, "digest")

    def commit(driver):
        raise psycopg.OperationalError("acknowledgement missing")

    def lookup(*args):
        raise publication.PublicationConflict("different exact contents")

    monkeypatch.setattr(engine.dialect, "do_commit", commit)
    monkeypatch.setattr(publication, "lookup_receipt", lookup)
    try:
        with pytest.raises(publication.PublicationConflict, match="different exact contents"):
            publication._publish(engine, PublicationBatch("r", "z", "b"), publish, attempts=3)
    finally:
        engine.dispose()


def test_adbc_native_fields_do_not_invent_transport_or_sqlstate():
    import adbc_driver_manager as adbc

    error = adbc.OperationalError(
        "untrusted SQL and credentials",
        status_code=adbc.AdbcStatusCode.IO,
        details=[
            ("PG_DIAG_TABLE_NAME", b"visible_table"),
            ("PG_DIAG_INTERNAL_QUERY", b"SECRET SQL"),
            ("vendor_payload", b"secret"),
        ],
    )
    error.vendor_code = 17
    failure = classify_error(error)
    assert failure.cause is DatabaseCause.IO
    assert failure.native_status == "IO" and failure.vendor_code == 17
    assert failure.sqlstate is None and not failure.invalidated
    assert failure.effects is EffectKnowledge.UNCERTAIN
    assert failure.details == (("table_name", "visible_table"),)
    assert error.details[-1] == ("vendor_payload", b"secret")


@pytest.mark.parametrize(
    "status,cause",
    [
        ("CANCELLED", DatabaseCause.CANCELLED),
        ("TIMEOUT", DatabaseCause.OPERATION_DEADLINE),
        ("UNAUTHORIZED", DatabaseCause.PERMISSION),
        ("UNAUTHENTICATED", DatabaseCause.AUTHENTICATION),
        ("INTEGRITY", DatabaseCause.CONSTRAINT),
        ("NOT_IMPLEMENTED", DatabaseCause.UNSUPPORTED),
    ],
)
def test_adbc_native_status_never_fabricates_sqlstate_or_effects(status, cause):
    import adbc_driver_manager as adbc

    error = adbc.Error("driver", status_code=adbc.AdbcStatusCode[status])
    failure = classify_error(error)
    assert failure.cause is cause
    assert failure.sqlstate is None
    assert failure.vendor_code is None and failure.details == ()
    assert failure.effects is EffectKnowledge.UNCERTAIN


def test_adbc_supplied_sqlstate_and_fence_detail_have_native_authority():
    import adbc_driver_manager as adbc

    error = adbc.IntegrityError(
        "driver",
        status_code=adbc.AdbcStatusCode.INTEGRITY,
        details=[
            ("PG_DIAG_SQLSTATE", b"23505"),
            ("PG_DIAG_CONSTRAINT_NAME", b"uq_observation_task_id_ordinal"),
        ],
    )
    failure = classify_error(error)
    assert failure.cause is DatabaseCause.FENCING
    assert failure.sqlstate == "23505"
    assert failure.constraint == "uq_observation_task_id_ordinal"


def test_interrupted_receipt_resolution_retains_original_identity_and_propagates_interrupt(
    monkeypatch,
):
    engine = create_engine("sqlite://")
    original = psycopg.OperationalError("acknowledgement missing")
    interrupted = KeyboardInterrupt()

    def publish(conn, batch):
        return PublicationReceipt("batch-original", 1, "digest")

    def commit(driver):
        raise original

    def lookup(*args):
        raise interrupted

    monkeypatch.setattr(engine.dialect, "do_commit", commit)
    monkeypatch.setattr(publication, "lookup_receipt", lookup)
    try:
        with pytest.raises(KeyboardInterrupt) as caught:
            publication._publish(
                engine,
                PublicationBatch("release", "realization", "batch-original"),
                publish,
                attempts=3,
            )
        assert caught.value is interrupted
        context = operation_failure(caught.value)
        assert context.operation_id == "batch-original"
        assert context.release_id == "release" and context.realization_id == "realization"
        assert context.failure.phase is DatabasePhase.RESOLVING
        assert context.failure.effects is EffectKnowledge.UNCERTAIN
        assert context.failure.cancellation_requested
        assert context.remediation == "resolve_original_identity"
        assert operation_failure(original) == context
    finally:
        engine.dispose()


@pytest.mark.parametrize("transport", [False, True])
def test_requested_cancellation_never_advertises_transaction_retry(monkeypatch, transport):
    from contextlib import contextmanager

    from corpus_structure.core.db.lifetime import BorrowerCancellation

    class PolicyCancellation(BorrowerCancellation):
        # This control tests operation policy, not native cancellation/provider behavior.
        @contextmanager
        def borrow(self, connection):
            yield

    cancel = PolicyCancellation()
    engine = create_engine("sqlite://")
    seen = []

    def publish(conn, batch):
        seen.append(batch.batch_id)
        cancel.request_cancel()
        if transport:
            raise OperationalError(
                None, None, psycopg.OperationalError(), connection_invalidated=True
            )
        raise psycopg.errors.SerializationFailure()

    monkeypatch.setattr(
        publication, "lookup_receipt", lambda *args: pytest.fail("no commit attempted")
    )
    try:
        with pytest.raises((psycopg.errors.SerializationFailure, OperationalError)) as caught:
            publication._publish(
                engine, PublicationBatch("r", "z", "b"), publish, attempts=3, cancellation=cancel
            )
        assert seen == ["b"]
        assert operation_failure(caught.value).failure.cancellation_requested
        assert operation_failure(caught.value).remediation == "stop_cancelled_operation"
    finally:
        engine.dispose()


def test_cancellation_arriving_during_absent_receipt_resolution_preserves_uncertain_identity(
    monkeypatch,
):
    from contextlib import contextmanager

    from corpus_structure.core.db.lifetime import BorrowerCancellation

    class PolicyCancellation(BorrowerCancellation):
        @contextmanager
        def borrow(self, connection):
            yield

    cancellation = PolicyCancellation()
    engine = create_engine("sqlite://")
    original = OperationalError(None, None, psycopg.OperationalError(), connection_invalidated=True)
    attempts = []

    def publish(conn, batch):
        attempts.append(batch.batch_id)
        return PublicationReceipt("b", 1, "digest")

    def commit(driver):
        raise original

    def lookup(*args):
        cancellation.request_cancel()
        return None

    monkeypatch.setattr(engine.dialect, "do_commit", commit)
    monkeypatch.setattr(publication, "lookup_receipt", lookup)
    try:
        with pytest.raises(OperationalError) as caught:
            publication._publish(
                engine,
                PublicationBatch("r", "z", "b"),
                publish,
                attempts=3,
                cancellation=cancellation,
            )
        assert caught.value is original and attempts == ["b"]
        context = operation_failure(caught.value)
        assert context.failure.cancellation_requested
        assert context.failure.effects is EffectKnowledge.UNCERTAIN
        assert context.remediation == "resolve_original_identity"
        assert context.operation_id == "b"
    finally:
        engine.dispose()
