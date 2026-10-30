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
