"""Physical database failure classification at CLI and tool boundaries."""

from dataclasses import asdict
from typing import Any

import adbc_driver_manager
import psycopg
from psycopg_pool import PoolClosed, PoolTimeout, TooManyRequests
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.db.lifetime import DatabaseOperationCancelled
from corpus_structure.core.db.store import operation_failure

from .refusals import FailureContext, failure_context

DATABASE_ERRORS = (
    DBAPIError,
    adbc_driver_manager.Error,
    psycopg.Error,
    PoolClosed,
    PoolTimeout,
    TooManyRequests,
    DatabaseOperationCancelled,
)


def database_failure_code(error):
    """Name physical cause without selecting a domain replay policy."""
    return "database_" + operation_failure(error).failure.cause.value


def database_failure_report(
    error: BaseException, *, context: FailureContext | None = None
) -> dict[str, Any]:
    """Safe typed fields for both CLI and tool reports; no SQL or credentials."""
    native = operation_failure(error)
    report: dict[str, Any] = {
        "code": database_failure_code(error),
        "message": "database operation failed",
        **asdict(native),
    }
    report["validation"] = failure_context(error, context).report(error).model_dump(mode="json")
    diagnostic = getattr(error, "database_diagnostic", None)
    if diagnostic is not None:
        report["database"] = asdict(diagnostic)
    return report
