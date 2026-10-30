"""Expected semantic caller failures, separate from database and programming failures."""

from functools import wraps

from sqlalchemy.exc import DBAPIError


class SemanticRefusal(ValueError):
    """An owned boundary deliberately refuses an unsupported or incompatible request."""


def database_failure_code(error):
    """Use the storage owner's SQLSTATE policy without relabelling it as refusal."""
    from corpus_structure.core.db.store import classify_error

    return "database_" + classify_error(error).value


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
            except DBAPIError as error:
                from fastmcp.exceptions import ToolError

                raise ToolError(database_failure_code(error)) from error

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
