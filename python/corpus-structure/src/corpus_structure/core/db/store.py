"""Connections (foundations §3.8; D3 §1; store note §5): one pool per process, lent to SQLAlchemy.

`open_store(settings, application_name, min_size, max_size)` opens one psycopg-pool
`ConnectionPool` with `close_returns=True` and `check=ConnectionPool.check_connection`. Its
`configure` callback only sets the JSON dumps and loads, leaving the connection idle. SQLAlchemy
borrows through `creator=pool.getconn` with `NullPool`, so closing an SQLAlchemy connection returns
it to the pool.

**The version check runs after the pool opens, never inside `configure`.** After `pool.open()` and
`pool.wait()`, one borrowed connection reads `pg_extension` and a mismatch with the record refuses
with `ExtensionVersionMismatch`. The pool treats every exception in `configure` as a connection
failure (`CLIENT_EXCEPTIONS = Exception`), so a check there would become retries and a
`PoolTimeout` that hides the cause.

Session state is set only with `SET LOCAL`. Native failures report physical cause separately
from operation-owned phase, effects and recovery policy.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import adbc_driver_manager as adbc
import psycopg
from psycopg.types.json import set_json_dumps, set_json_loads
from psycopg_pool import ConnectionPool, PoolClosed, PoolTimeout, TooManyRequests
from sqlalchemy import Engine, create_engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.pool import NullPool

from corpus_structure.core.db import extensions
from corpus_structure.core.db.lifetime import DatabaseOperationCancelled
from corpus_structure.settings import Settings

RETRYABLE = frozenset({"40001", "40P01"})  # serialization failure, deadlock detected
FENCING_CONSTRAINT = "uq_observation_task_id_ordinal"
LOG = logging.getLogger("corpus_structure.database")


def dumps(value: Any) -> str:
    """The JSON text written to `jsonb`: compact, UTF-8 as is (key order the dump's)."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def configure(conn: psycopg.Connection[Any]) -> None:
    """The pool's `configure`: JSON adapters only; no query, no transaction, no check."""
    set_json_dumps(dumps, context=conn)
    set_json_loads(json.loads, context=conn)
    conn.add_notice_handler(_notice)


@dataclass
class Store:
    """The process's pool and the SQLAlchemy engine that borrows from it."""

    pool: ConnectionPool
    engine: Engine
    application_name: str = ""

    def diagnostic(self, failure: DatabaseFailure | None = None) -> DatabaseDiagnostic:
        """Collect non-destructive native counters from this invocation's live pool."""
        return DatabaseDiagnostic(
            datetime.now(UTC).isoformat(),
            self.application_name,
            "closed" if self.pool.closed else "open",
            self.pool.get_stats(),
            failure,
        )

    def close(self) -> None:
        errors: list[BaseException] = []
        try:
            self.engine.dispose()
        except BaseException as error:
            errors.append(error)
        try:
            self.pool.close()
        except BaseException as error:
            errors.append(error)
        if errors:
            raise BaseExceptionGroup("database inventory cleanup failed", errors)

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *exc: object) -> None:
        try:
            self.close()
        except BaseException as cleanup:
            if len(exc) > 1 and isinstance(exc[1], BaseException):
                exc[1].add_note("database cleanup failed: " + repr(cleanup))
            else:
                raise


def open_store(
    settings: Settings,
    application_name: str,
    min_size: int | None = None,
    max_size: int | None = None,
    timeout: float | None = None,
    max_waiting: int | None = None,
) -> Store:
    """Open the pool, wait for it, check the extension versions, and lend it to SQLAlchemy."""
    database = settings.database
    min_size = database.pool_min_size if min_size is None else min_size
    max_size = database.pool_max_size if max_size is None else max_size
    timeout = database.checkout_timeout_seconds if timeout is None else timeout
    max_waiting = database.pool_max_waiting if max_waiting is None else max_waiting
    if min_size < 0 or max_size < 1 or min_size > max_size or timeout <= 0 or max_waiting < 1:
        raise ValueError("invalid database pool bounds or checkout timeout")
    pool: ConnectionPool = ConnectionPool(
        settings.database.url,
        kwargs={"application_name": application_name},
        min_size=min_size,
        max_size=max_size,
        open=False,
        configure=configure,
        check=ConnectionPool.check_connection,
        close_returns=True,
        name=application_name,
        timeout=timeout,
        max_waiting=max_waiting,
    )
    pool.open()
    try:
        pool.wait(timeout)
        with pool.connection() as conn:
            extensions.check(conn.execute(extensions.FOUND).fetchall())
    except BaseException:
        pool.close()
        raise
    engine = create_engine("postgresql+psycopg://", creator=pool.getconn, poolclass=NullPool)
    store = Store(pool, engine, application_name)
    engine.__dict__["_corpus_store"] = store
    engine.__dict__["_corpus_database_settings"] = settings.database
    return store


class DatabaseCause(StrEnum):
    INVENTORY_CLOSED = "inventory_closed"
    ADMISSION_PRESSURE = "admission_pressure"
    ACQUISITION_DEADLINE = "acquisition_deadline"
    SERIALIZATION = "serialization"
    DEADLOCK = "deadlock"
    CANCELLED = "cancelled"
    FENCING = "fencing"
    CONSTRAINT = "constraint"
    CONNECTION_UNUSABLE = "connection_unusable"
    IO = "io"
    OPERATION_DEADLINE = "operation_deadline"
    PERMISSION = "permission"
    AUTHENTICATION = "authentication"
    UNSUPPORTED = "unsupported"
    UNKNOWN_OPERATIONAL = "unknown_operational"
    UNKNOWN = "unknown"


class DatabasePhase(StrEnum):
    ACQUIRING = "acquiring"
    EXECUTING = "executing"
    COMMITTING = "committing"
    RESOLVING = "resolving"
    UNKNOWN = "unknown"


class EffectKnowledge(StrEnum):
    NONE = "no_effects_started"
    ROLLED_BACK = "rollback_confirmed"
    COMMITTED = "commit_confirmed"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True)
class DatabaseFailure:
    cause: DatabaseCause
    phase: DatabasePhase = DatabasePhase.UNKNOWN
    effects: EffectKnowledge = EffectKnowledge.UNCERTAIN
    sqlstate: str | None = None
    constraint: str | None = None
    invalidated: bool = False
    cancellation_requested: bool = False
    native_status: str | None = None
    vendor_code: int | None = None
    details: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class DatabaseOperationFailure:
    failure: DatabaseFailure
    operation_id: str | None = None
    remediation: str = "inspect_failure"
    release_id: str | None = None
    realization_id: str | None = None


@dataclass(frozen=True)
class DatabaseDiagnostic:
    observed_at: str
    application_name: str
    lifecycle: str
    pool_stats: dict[str, int] | None
    failure: DatabaseFailure | None = None
    # Core borrows via getconn, outside pool.connection()'s usage timing.
    usage_scope: str = "pool_connection_scopes_only"


def classify_error(
    exc: BaseException,
    *,
    phase: DatabasePhase = DatabasePhase.UNKNOWN,
    effects: EffectKnowledge = EffectKnowledge.UNCERTAIN,
    cancellation_requested: bool = False,
    broken: bool = False,
) -> DatabaseFailure:
    """Translate native facts; the operation supplies phase/effects and chooses recovery."""
    original = exc.orig if isinstance(exc, DBAPIError) else exc
    invalidated = (isinstance(exc, DBAPIError) and exc.connection_invalidated) or broken
    details = _adbc_details(original) if isinstance(original, adbc.Error) else ()
    native_details = dict(details)
    # A native SQLSTATE detail is supplied data, unlike a generic ADBC status.
    sqlstate = getattr(original, "sqlstate", None) or native_details.get("sqlstate")
    constraint = getattr(
        getattr(original, "diag", None), "constraint_name", None
    ) or native_details.get("constraint_name")
    status = original.status_code if isinstance(original, adbc.Error) else None
    native_status = status.name if status is not None else None
    vendor_code = original.vendor_code if isinstance(original, adbc.Error) else None
    if isinstance(original, PoolClosed):
        cause = DatabaseCause.INVENTORY_CLOSED
    elif isinstance(original, TooManyRequests):
        cause = DatabaseCause.ADMISSION_PRESSURE
    elif isinstance(original, PoolTimeout):
        cause = DatabaseCause.ACQUISITION_DEADLINE
    elif sqlstate == "40001":
        cause = DatabaseCause.SERIALIZATION
    elif sqlstate == "40P01":
        cause = DatabaseCause.DEADLOCK
    elif isinstance(original, DatabaseOperationCancelled) or sqlstate == "57014":
        cause = DatabaseCause.CANCELLED
    elif sqlstate == "23505" and constraint == FENCING_CONSTRAINT:
        cause = DatabaseCause.FENCING
    elif invalidated or (isinstance(sqlstate, str) and sqlstate.startswith("08")):
        cause = DatabaseCause.CONNECTION_UNUSABLE
    elif isinstance(sqlstate, str) and sqlstate.startswith("23"):
        cause = DatabaseCause.CONSTRAINT
    elif sqlstate == "42501" or status == adbc.AdbcStatusCode.UNAUTHORIZED:
        cause = DatabaseCause.PERMISSION
    elif (
        isinstance(sqlstate, str) and sqlstate.startswith("28")
    ) or status == adbc.AdbcStatusCode.UNAUTHENTICATED:
        cause = DatabaseCause.AUTHENTICATION
    elif status == adbc.AdbcStatusCode.CANCELLED:
        cause = DatabaseCause.CANCELLED
    elif status == adbc.AdbcStatusCode.TIMEOUT:
        cause = DatabaseCause.OPERATION_DEADLINE
    elif status == adbc.AdbcStatusCode.IO:
        # ADBC IO includes more than session loss. It supplies no effect knowledge.
        cause = DatabaseCause.IO
    elif status == adbc.AdbcStatusCode.INTEGRITY:
        cause = DatabaseCause.CONSTRAINT
    elif status == adbc.AdbcStatusCode.NOT_IMPLEMENTED:
        cause = DatabaseCause.UNSUPPORTED
    elif isinstance(original, (psycopg.OperationalError, adbc.OperationalError)):
        cause = DatabaseCause.UNKNOWN_OPERATIONAL
    else:
        cause = DatabaseCause.UNKNOWN
    return DatabaseFailure(
        cause,
        phase,
        effects,
        sqlstate,
        constraint,
        invalidated,
        cancellation_requested,
        native_status,
        vendor_code,
        details,
    )


_ADBC_DIAGNOSTICS = {
    "PG_DIAG_SQLSTATE": "sqlstate",
    "PG_DIAG_CONSTRAINT_NAME": "constraint_name",
    "PG_DIAG_SCHEMA_NAME": "schema_name",
    "PG_DIAG_TABLE_NAME": "table_name",
    "PG_DIAG_COLUMN_NAME": "column_name",
    "PG_DIAG_MESSAGE_HINT": "message_hint",
}


def _adbc_details(error: adbc.Error) -> tuple[tuple[str, str], ...]:
    """Copy known native fields; retain opaque/query/context payloads on the original error."""
    return tuple(
        (name, value.decode("utf-8", errors="replace"))
        for key, value in error.details
        if (name := _ADBC_DIAGNOSTICS.get(key)) is not None
    )


def operation_failure(error: BaseException) -> DatabaseOperationFailure:
    """Read typed owner context, leaving unowned effects explicitly uncertain."""
    context = getattr(error, "database_operation_failure", None)
    return (
        context
        if isinstance(context, DatabaseOperationFailure)
        else DatabaseOperationFailure(classify_error(error))
    )


def record_operation_failure(error: BaseException, context: DatabaseOperationFailure) -> None:
    """Retain native exception identity and traceback while adding typed operation context."""
    error.__dict__["database_operation_failure"] = context


def database_diagnostic(
    engine: Engine, failure: DatabaseFailure | None = None
) -> DatabaseDiagnostic:
    """Report the existing managed Store; never open inventory to diagnose inventory."""
    store = getattr(engine, "_corpus_store", None)
    if isinstance(store, Store):
        return store.diagnostic(failure)
    return DatabaseDiagnostic(datetime.now(UTC).isoformat(), "", "unmanaged", None, failure)


def diagnostic_fields(diag: Any) -> dict[str, str]:
    """Copy safe server diagnostics during a notice callback's valid lifetime."""
    return {
        name: value
        for name in (
            "sqlstate",
            "message_primary",
            "constraint_name",
            "schema_name",
            "table_name",
            "column_name",
            "message_hint",
        )
        if (value := getattr(diag, name, None)) is not None
    }


def _notice(diag: psycopg.errors.Diagnostic) -> None:
    # Diagnostic objects are only valid during this callback: copy values now.
    LOG.info("PostgreSQL notice", extra={"database_notice": diagnostic_fields(diag)})
