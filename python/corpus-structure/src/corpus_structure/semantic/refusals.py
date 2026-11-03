"""Expected semantic caller failures, separate from database and programming failures."""

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from functools import wraps
from typing import TYPE_CHECKING, Any, Literal, Self

import adbc_driver_manager
import psycopg
from psycopg_pool import PoolClosed, PoolTimeout, TooManyRequests
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.db.lifetime import DatabaseOperationCancelled
from corpus_structure.core.db.store import operation_failure

if TYPE_CHECKING:
    from .types import PreparedRelease


class SemanticRefusal(ValueError):
    """An owned boundary deliberately refuses an unsupported or incompatible request."""


@dataclass(frozen=True)
class SemanticReason:
    """An operation's expected inability to decide, without interpreting human text."""

    code: Literal["missing_operands", "unsupported_interpretation", "incompatible_bindings", "preparation_failed"]
    operation: str
    release_id: str | None
    references: tuple[str, ...] = ()
    expected: str | None = None
    actual: str | None = None
    detail: str | None = None

    def render(self) -> str:
        return self.detail or self.code.replace("_", " ")


class SemanticOperationRefusal(SemanticRefusal):
    def __init__(self, reason: SemanticReason):
        self.semantic_reason = reason
        self.reason = reason.code
        super().__init__(reason.render())


def semantic_failure_fields(error: BaseException) -> dict[str, Any]:
    reason = getattr(error, "semantic_reason", None)
    return {"semantic_reason": asdict(reason)} if reason is not None else {}


@dataclass
class FailureContext:
    """Invocation-local context, bound only after trusted model resolution."""

    prepared: PreparedRelease | None = None
    operation: str | None = None
    scope: str = "boundary"
    release_id: str | None = None
    model_id: str | None = None

    def bind(
        self, prepared: PreparedRelease, operation: str | None = None, *, scope: str = "boundary"
    ) -> Self:
        self.prepared, self.operation, self.scope = prepared, operation, scope
        self.release_id, self.model_id = prepared.release_id, prepared.execution_model_id
        return self

    def report(self, error: BaseException):
        from .operation_reporting import validation_failure_report

        return validation_failure_report(
            error,
            prepared=self.prepared,
            operation=self.operation,
            scope=self.scope,
            release_id=self.release_id,
            model_id=self.model_id,
        )


@contextmanager
def located_failure_context(prepared, operation: str | None = None, *, scope="boundary"):
    """Carry trusted invocation identity on its exception, without ambient state."""
    context = FailureContext().bind(prepared, operation, scope=scope)
    try:
        yield context
    except Exception as error:
        error.__dict__.setdefault("semantic_failure_context", context)
        raise


def failure_context(error, fallback: FailureContext | None = None) -> FailureContext:
    return getattr(error, "semantic_failure_context", None) or fallback or FailureContext()


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


def tool_refusals(*expected: type[Exception]):
    """Translate expected exceptions inside FastMCP's tool/logging boundary."""

    def decorate(function):
        @wraps(function)
        def invoke(*args, **kwargs):
            from pydantic import ValidationError

            from .operation_value_types import NativeResultViolation

            try:
                return function(*args, **kwargs)
            except (SemanticRefusal, ValidationError, NativeResultViolation, *expected) as error:
                import json

                from fastmcp.exceptions import ToolError

                raise ToolError(
                    json.dumps(
                        {
                            "code": type(error).__name__,
                            "message": str(error),
                            **semantic_failure_fields(error),
                            "validation": failure_context(error)
                            .report(error)
                            .model_dump(mode="json"),
                        }
                    )
                ) from error
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
