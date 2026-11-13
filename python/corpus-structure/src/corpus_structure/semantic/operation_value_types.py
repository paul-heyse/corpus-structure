"""Shared strict values used by generated operation results and held submission owners."""

from __future__ import annotations

from collections.abc import Callable, Generator
from contextlib import contextmanager
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar

from pydantic import BaseModel, ConfigDict, JsonValue, ValidationError
from sqlalchemy.exc import MultipleResultsFound, NoResultFound

from ._operation_ids import TaskAttempt

if TYPE_CHECKING:
    from .types import PreparedRelease


class OperationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class SqlNull(Enum):
    VALUE = "SQL NULL"


SQL_NULL = SqlNull.VALUE


def decode_json_text(value: str | None) -> JsonValue | SqlNull:
    """Decode only an explicitly declared native JSON-text field; retain SQL absence."""
    import json

    return SQL_NULL if value is None else json.loads(value)


class NativeRowResult(OperationResult):
    __json_fields__: ClassVar[tuple[str, ...]] = ()

    def decoded_json_fields(self, *, operation: str) -> dict[str, Any]:
        """The raw row retains text; domain consumers explicitly request decoded JSON fields."""
        values = self.model_dump(mode="python")
        for field in self.__json_fields__:
            with native_result_scope(operation, type(self).__name__, field):
                values[field] = decode_json_text(values[field])
        return values


class HeldProgress(OperationResult):
    attempt: TaskAttempt
    holder: str
    packet_hash: str
    result: dict[str, JsonValue]


class NativeResultViolation(ValueError):
    """A server result violates its selected materializer's required field contract."""

    def __init__(
        self,
        operation: str,
        result_class: str,
        field: str = "",
        *,
        original: BaseException | None = None,
    ):
        self.operation = operation
        self.result_class = result_class
        self.field = field
        self.original = original
        prefix = (field,) if field else ()
        errors = original.errors() if isinstance(original, ValidationError) else ()
        self.locations: tuple[tuple[str | int, ...], ...] = tuple(
            (*prefix, *error["loc"]) for error in errors
        ) or (prefix,)
        if not field and self.locations:
            self.field = "/".join(str(part) for part in self.locations[0])
        self.expected = "non-null" if original is None else "selected native result contract"
        self.actual = errors[0].get("input") if errors else None
        super().__init__(
            f"{operation}: native {result_class}/{self.field} violates result contract"
        )


@contextmanager
def native_result_scope(operation: str, result_class: str, field: str = "") -> Generator[None]:
    """Classify only materialization of an executed native result, never request input."""
    try:
        yield
    except NativeResultViolation:
        raise
    except (ValueError, TypeError, NoResultFound, MultipleResultsFound) as error:
        raise NativeResultViolation(operation, result_class, field, original=error) from error


def native_result_value[T, R](
    operation: str, result_class: str, field: str, decoder: Callable[[T], R], value: T
) -> R:
    try:
        with native_result_scope(operation, result_class, field):
            return decoder(value)
    except NativeResultViolation as error:
        if error.original is not None and not isinstance(error.original, ValidationError):
            error.actual = value
        raise


def held_progress(value: JsonValue) -> HeldProgress | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("native held-progress source must be a JSON object or null")
    if "semantic_proposal_first_result" not in value:
        return None
    return HeldProgress.model_validate(value["semantic_proposal_first_result"], strict=True)


def require_call_context(
    prepared: PreparedRelease, operation: str, variant: str, expected_digest: str
) -> None:
    """Check one consumer's immutable call contract without substituting installed meaning."""
    from dataclasses import asdict
    from hashlib import sha256

    from .contracts import bound_execution_model
    from .identity import canonical_bytes
    from .refusals import SemanticRefusal

    if prepared.execution_model_id is None:
        import json

        artifacts = [
            a for a in prepared.artifacts if a.kind == "operation_call_correspondences.json"
        ]
        if len(artifacts) != 1:
            raise SemanticRefusal("release lacks an unambiguous native call correspondence")
        calls = [
            call
            for owner, call in json.loads(artifacts[0].content)
            if owner == operation and call["id"] == variant
        ]
        if len(calls) != 1 or sha256(canonical_bytes(calls)).hexdigest() != expected_digest:
            raise SemanticRefusal(
                f"{operation}/{variant}: incompatible consumer call correspondence"
            )
        return
    model = bound_execution_model(prepared)
    calls = [call for call in model.require_operation(operation).calls if call.id == variant]
    if (
        len(calls) != 1
        or sha256(canonical_bytes([asdict(calls[0])])).hexdigest() != expected_digest
    ):
        raise SemanticRefusal(f"{operation}/{variant}: incompatible consumer call correspondence")
