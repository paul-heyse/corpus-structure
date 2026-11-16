"""Independent physical-cause and operation-context controls without a server."""

from __future__ import annotations

from types import SimpleNamespace

import psycopg
import pytest
from psycopg_pool import PoolClosed, PoolTimeout, TooManyRequests
from pydantic import ValidationError
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
