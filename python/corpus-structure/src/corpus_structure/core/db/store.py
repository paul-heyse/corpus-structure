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

Session state is set only with `SET LOCAL`. `classify_error` separates retryable failures
(serialization, deadlock, a lost connection) from defects; a unique violation on an observation's
`(task_id, ordinal)` is a fencing defect, never a retry.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import psycopg
from psycopg.types.json import set_json_dumps, set_json_loads
from psycopg_pool import ConnectionPool
from sqlalchemy import Engine, create_engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.pool import NullPool

from corpus_structure.core.db import extensions
from corpus_structure.settings import Settings

RETRYABLE = frozenset({"40001", "40P01"})  # serialization failure, deadlock detected
FENCING_CONSTRAINT = "uq_observation_task_id_ordinal"


def dumps(value: Any) -> str:
    """The JSON text written to `jsonb`: compact, UTF-8 as is (key order the dump's)."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)


def configure(conn: psycopg.Connection[Any]) -> None:
    """The pool's `configure`: JSON adapters only; no query, no transaction, no check."""
    set_json_dumps(dumps, context=conn)
    set_json_loads(json.loads, context=conn)


@dataclass
class Store:
    """The process's pool and the SQLAlchemy engine that borrows from it."""

    pool: ConnectionPool
    engine: Engine

    def close(self) -> None:
        self.engine.dispose()
        self.pool.close()

    def __enter__(self) -> Store:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def open_store(
    settings: Settings,
    application_name: str,
    min_size: int = 1,
    max_size: int = 4,
    timeout: float = 30.0,
) -> Store:
    """Open the pool, wait for it, check the extension versions, and lend it to SQLAlchemy."""
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
    return Store(pool, engine)


class ErrorClass(StrEnum):
    RETRY = "retry"
    FENCING = "fencing"
    DEFECT = "defect"


def classify_error(exc: BaseException) -> ErrorClass:
    """Whether a failed transaction may be retried (module doc)."""
    orig = exc.orig if isinstance(exc, DBAPIError) else exc
    if isinstance(exc, DBAPIError) and exc.connection_invalidated:
        return ErrorClass.RETRY
    if isinstance(orig, psycopg.OperationalError) and getattr(orig, "sqlstate", None) is None:
        return ErrorClass.RETRY  # the connection was lost
    sqlstate = getattr(orig, "sqlstate", None)
    if sqlstate in RETRYABLE:
        return ErrorClass.RETRY
    diag = getattr(orig, "diag", None)
    if sqlstate == "23505" and getattr(diag, "constraint_name", None) == FENCING_CONSTRAINT:
        return ErrorClass.FENCING
    return ErrorClass.DEFECT
