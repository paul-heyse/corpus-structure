"""Expected semantic caller failures, separate from database and programming failures."""

from dataclasses import asdict
from functools import wraps
from typing import Any

import adbc_driver_manager
import psycopg
from psycopg_pool import PoolClosed, PoolTimeout, TooManyRequests
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.db.lifetime import DatabaseOperationCancelled
from corpus_structure.core.db.store import operation_failure


class SemanticRefusal(ValueError):
    """An owned boundary deliberately refuses an unsupported or incompatible request."""


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


def database_failure_report(error: BaseException) -> dict[str, Any]:
    """Safe typed fields for both CLI and tool reports; no SQL or credentials."""
    context = operation_failure(error)
    report: dict[str, Any] = {
        "code": database_failure_code(error),
        "message": "database operation failed",
        **asdict(context),
    }
    diagnostic = getattr(error, "database_diagnostic", None)
    if diagnostic is not None:
        report["database"] = asdict(diagnostic)
    return report


def tool_refusals(*expected: type[Exception]):
    """Translate expected exceptions inside FastMCP's tool/logging boundary."""

    def decorate(function):
        @wraps(function)
        def invoke(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except expected as error:
                from fastmcp.exceptions import ToolError

                raise ToolError(str(error)) from error
            except DATABASE_ERRORS as error:
                import json

                from fastmcp.exceptions import ToolError

                raise ToolError(json.dumps(database_failure_report(error))) from error

        return invoke

    return decorate


class ContinuationRefusal(SemanticRefusal):
    """A continuation cannot be used, with a stable machine-readable reason."""

    reason = "invalid_token"

    def __init__(self, message: str, *, reason: str | None = None):
        super().__init__(message)
        if reason is not None:
            self.reason = reason


class InvalidContinuation(ContinuationRefusal):
    """The token or query-owned cursor is malformed or unsupported."""


class WrongBinding(ContinuationRefusal):
    """The token describes another request identity."""

    reason = "wrong_query"


class WrongRelease(WrongBinding):
    """A handle or selector belongs to another semantic release."""

    reason = "wrong_release"


class StaleSnapshot(ContinuationRefusal):
    """The bound revision or implementation no longer supports continuation."""

    reason = "stale_revision"
