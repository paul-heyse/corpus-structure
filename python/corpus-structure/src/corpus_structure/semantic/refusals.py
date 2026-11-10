"""Expected semantic caller failures, separate from database and programming failures."""

import re
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from functools import cache, wraps
from typing import TYPE_CHECKING, Any, Literal, Self

import adbc_driver_manager
import psycopg
from psycopg_pool import PoolClosed, PoolTimeout, TooManyRequests
from pydantic import ConfigDict, TypeAdapter
from pydantic.dataclasses import dataclass as validated_dataclass
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.db.lifetime import DatabaseOperationCancelled
from corpus_structure.core.db.store import operation_failure

if TYPE_CHECKING:
    from .types import PreparedRelease


class SemanticRefusal(ValueError):
    """An owned boundary deliberately refuses an unsupported or incompatible request."""


SemanticReasonCode = Literal[
    "missing_operands", "unsupported_interpretation", "incompatible_bindings", "preparation_failed"
]


@validated_dataclass(frozen=True, config=ConfigDict(strict=True, extra="forbid"))
class SemanticReason:
    """An operation's expected inability to decide, without interpreting human text."""

    code: SemanticReasonCode
    operation: str
    release_id: str | None
    references: tuple[str, ...] = ()
    expected: str | None = None
    actual: str | None = None
    detail: str | None = None

    def render(self) -> str:
        return self.detail or self.code.replace("_", " ")


@cache
def semantic_reason_adapter() -> TypeAdapter[SemanticReason]:
    return TypeAdapter(SemanticReason)


def decode_semantic_reason(value: object) -> SemanticReason | None:
    """Decode only the selected structured reason field; historical prose stays prose."""
    from .identity import canonical_bytes

    if value is None:
        return None
    if isinstance(value, SemanticReason):
        value = asdict(value)
    return semantic_reason_adapter().validate_json(
        value if isinstance(value, (str, bytes)) else canonical_bytes(value), strict=True
    )


def semantic_reason_identity(reason: SemanticReason) -> dict[str, Any]:
    """Human wording is not the identity of an expected semantic inability."""
    return {key: value for key, value in asdict(reason).items() if key != "detail"}


class SemanticOperationRefusal(SemanticRefusal):
    def __init__(self, reason: SemanticReason):
        self.semantic_reason = reason
        self.reason = reason.code
        super().__init__(reason.render())


def semantic_failure_fields(error: BaseException) -> dict[str, Any]:
    reason = getattr(error, "semantic_reason", None)
    ordinary_reason = getattr(error, "reason", None)
    fields: dict[str, Any] = {"reason": ordinary_reason} if isinstance(ordinary_reason, str) else {}
    if isinstance(reason, SemanticReason):
        fields.update(code=reason.code, semantic_reason=asdict(reason))
    return fields


@dataclass
class FailureContext:
    """Invocation-local context, bound only after trusted model resolution."""

    prepared: PreparedRelease | None = None
    operation: str | None = None
    scope: str = "boundary"
    release_id: str | None = None
    model_id: str | None = None
    correction_detail: bool = False
    raw_evidence: bool = False
    max_errors: int = 100
    max_depth: int = 8
    max_bytes: int = 262144
    retained_validation: Any = None
    retained_error: BaseException | None = None
    diagnostic_unavailable: str | None = None

    def bind(
        self, prepared: PreparedRelease, operation: str | None = None, *, scope: str = "boundary"
    ) -> Self:
        self.prepared, self.operation, self.scope = prepared, operation, scope
        self.release_id, self.model_id = prepared.release_id, prepared.execution_model_id
        return self

    def report(self, error: BaseException):
        from .operation_reporting import validation_failure_report

        if self.retained_error is error and self.retained_validation is not None:
            return self.retained_validation
        report = validation_failure_report(
            error,
            prepared=self.prepared,
            operation=self.operation,
            scope=self.scope,
            release_id=self.release_id,
            model_id=self.model_id,
            detail=self.correction_detail,
            raw_evidence=self.raw_evidence,
            max_errors=self.max_errors,
            max_depth=self.max_depth,
            max_bytes=self.max_bytes,
        )
        if self.diagnostic_unavailable:
            from .operation_reporting import _report

            fields = report.model_dump(
                mode="json", exclude={"report_version", "report_schema_digest"}
            )
            fields["evidence"] = dict(
                kind="marker",
                engine="boundary",
                media_type="application/json",
                sensitivity="safe",
                reason=self.diagnostic_unavailable,
            )
            report = _report("LocatedValidationReport", fields)
        return report


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


_CREDENTIAL = re.compile(
    r"(://[^:/@\s]+:)[^@/\s]+(?=@)|(?i:(password|token|api[_-]?key)=)([^\s&]+)"
)


def _safe_refusal_fields(value):
    if isinstance(value, str):
        return _CREDENTIAL.sub(lambda match: (match[1] or f"{match[2]}=") + "**********", value)
    if isinstance(value, dict):
        return {key: _safe_refusal_fields(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_safe_refusal_fields(item) for item in value]
    return value


def safe_failure_message(error, *, context=None):
    from jsonschema.exceptions import SchemaError
    from jsonschema.exceptions import ValidationError as JsonError
    from pydantic import ValidationError

    from .ontology import GraphExecutionError, GraphShapeError
    from .releases import ArchiveDecodeError
    from .types import PreparationError

    if isinstance(error, (PreparationError, ArchiveDecodeError)):
        return "Model preparation failed; request correction detail for structural paths."
    if isinstance(error, (GraphShapeError, GraphExecutionError)):
        return "Graph validation failed; request correction detail for structural paths."
    if isinstance(error, ValidationError):
        return f"invalid {error.title} input"
    if (
        isinstance(error, (JsonError, SchemaError))
        or getattr(error, "validation_capture", None) is not None
    ):
        return "Validation failed; request correction detail for structural paths."
    if getattr(error, "boundary_diagnostic", None) is not None:
        return "Boundary validation failed; request correction detail for structural paths."
    return str(error)[:512]


def semantic_refusal_report(
    error: BaseException, *, context: FailureContext | None = None
) -> dict[str, Any]:
    """Project the owned refusal meaning independently of its transport envelope."""

    message = safe_failure_message(error, context=context)
    return _safe_refusal_fields(
        {
            "code": type(error).__name__,
            "message": message,
            **semantic_failure_fields(error),
            "validation": failure_context(error, context).report(error).model_dump(mode="json"),
        }
    )


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

                raise ToolError(json.dumps(semantic_refusal_report(error))) from error
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
