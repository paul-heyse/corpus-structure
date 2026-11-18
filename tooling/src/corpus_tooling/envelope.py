"""The result envelope every `tooling library` command returns (schema `tooling.library/1`).

The envelope is generic over two types a command module declares: its item kind (an `Item`
subclass with a one-value `kind` literal, its `columns` and its `sort_fields`) and its unresolved
kinds (an `Unresolved` subclass whose `kind` literal is that command's closed set). This module
never names a concrete kind, so adding a command adds no edit here.

`build_envelope` is the one place that sorts the selected view, applies `--limit`/`--offset` and
fills `truncated`. Coverage fields are always present, empty when not applicable. Skipped inputs
(not examined) and unresolved rows (examined, not attributable) are separate fields (DP-02).
"""

from __future__ import annotations

import typing
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA = "tooling.library/1"


@dataclass(frozen=True)
class Column:
    """One rendered column of an item kind: the model field and its header."""

    field: str
    header: str | None = None

    @property
    def title(self) -> str:
        return self.header or self.field.replace("_", " ")


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


def _literal_values(annotation: object) -> tuple[object, ...]:
    if typing.get_origin(annotation) is Literal:
        return typing.get_args(annotation)
    return ()


class Item(_Frozen):
    """Base of every item kind. A concrete kind narrows `kind` to a one-value literal with that
    value as default and declares `columns` (both renderings) and `sort_fields` (stable order)."""

    kind: str
    columns: ClassVar[tuple[Column, ...]] = ()
    sort_fields: ClassVar[tuple[str, ...]] = ()

    @classmethod
    def __pydantic_init_subclass__(cls, **kwargs: Any) -> None:
        super().__pydantic_init_subclass__(**kwargs)
        values = _literal_values(cls.model_fields["kind"].annotation)
        if not values:
            return  # an intermediate base that does not fix its kind yet
        if len(values) != 1 or cls.model_fields["kind"].default != values[0]:
            raise TypeError(f"{cls.__name__}: `kind` must be a one-value Literal with that default")
        missing = [
            name
            for name in (*(column.field for column in cls.columns), *cls.sort_fields)
            if name not in cls.model_fields
        ]
        if not cls.columns or not cls.sort_fields or missing:
            raise TypeError(
                f"{cls.__name__}: declare non-empty `columns` and `sort_fields` naming model "
                f"fields (unknown: {missing})"
            )

    def sort_key(self) -> tuple[object, ...]:
        """Stable order: `sort_fields` in turn, `None` first. A kind may override this."""
        return tuple(_ordered(getattr(self, name)) for name in self.sort_fields)


def _ordered(value: object) -> tuple[int, object]:
    if value is None:
        return (0, "")
    if isinstance(value, list | tuple | frozenset | set):
        return (1, tuple(sorted(str(part) for part in value)))
    return (1, value)


def kind_of(item_type: type[Item]) -> str:
    """The `kind` value a concrete item model declares; also the envelope's `view`."""
    values = _literal_values(item_type.model_fields["kind"].annotation)
    if len(values) != 1 or not isinstance(values[0], str):
        raise TypeError(f"{item_type.__name__} does not declare a one-value `kind` literal")
    return values[0]


class Unresolved(_Frozen):
    """An examined thing the command's method cannot attribute. A command narrows `kind` to its
    closed set of unresolved kinds; it may add fields. The base is used by commands with none."""

    kind: str
    subject: str = Field(description="What was examined, such as a written path or an alias.")
    location: str = Field(description="Where: `file:line:column` or an object path.")
    detail: str = ""

    def sort_key(self) -> tuple[str, str, str]:
        return (self.kind, self.location, self.subject)


class SkippedInput(_Frozen):
    """An input the tool could not examine. `reason` is a short stable token such as
    `parse_error`, `unreadable_metadata` or `compiled_without_stub`."""

    input: str
    reason: str
    detail: str = ""


class UnavailableMetadata(_Frozen):
    """A metadata field the authority does not provide for a subject."""

    subject: str
    field: str


class Coverage[U: Unresolved](_Frozen):
    scanned: int = 0
    no_hit_scopes: list[str] = Field(default_factory=list)
    excluded: list[str] = Field(default_factory=list)
    skipped_inputs: list[SkippedInput] = Field(default_factory=list)
    unresolved: list[U] = Field(default_factory=list)
    unavailable_metadata: list[UnavailableMetadata] = Field(default_factory=list)


class Truncation(_Frozen):
    list: str
    shown: int
    total: int


class ErrorInfo(_Frozen):
    kind: str
    message: str
    remedy: str


class ToolInfo(_Frozen):
    version: str
    authorities: dict[str, str] = Field(default_factory=dict)


class TargetPython(_Frozen):
    version: str
    implementation: str | None = None
    environment: str


class Baseline(_Frozen):
    revision: str | None
    dirty_paths: list[str]
    project: str | None
    python: TargetPython
    platform: str
    lock_digest: str | None


class Envelope[I: Item, U: Unresolved](_Frozen):
    schema_: Literal["tooling.library/1"] = Field(default=SCHEMA, alias="schema")
    status: Literal["ok", "failed"] = "ok"
    error: ErrorInfo | None = Field(default=None, exclude_if=lambda value: value is None)
    tool: ToolInfo
    command: str
    generated_at: datetime
    baseline: Baseline | None = Field(description="Null only when the command failed early.")
    view: str | None = Field(description="The item kind held; null only when failed.")
    items: list[I] = Field(default_factory=list)
    coverage: Coverage[U] = Field(default_factory=Coverage)
    truncated: list[Truncation] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    # `schema` would shadow a BaseModel attribute; the field is `schema_`, serialized as `schema`.
    model_config = ConfigDict(
        frozen=True, extra="forbid", validate_by_name=True, serialize_by_alias=True
    )

    @classmethod
    def item_type(cls) -> type[Item]:
        args = cls.__pydantic_generic_metadata__["args"]
        return args[0] if args else Item


def tool_version() -> str:
    try:
        return version("corpus-tooling")
    except PackageNotFoundError:
        return "unknown"


def page[T](
    values: list[T], *, name: str, limit: int, offset: int
) -> tuple[list[T], Truncation | None]:
    """Apply `--limit` (0 = all) and `--offset` to one sorted list."""
    shown = values[offset:] if limit == 0 else values[offset : offset + limit]
    if len(shown) == len(values):
        return shown, None
    return shown, Truncation(list=name, shown=len(shown), total=len(values))


def _inferred_type(rows: list[Any]) -> type[Any]:
    types = {type(row) for row in rows}
    if len(types) > 1:
        names = sorted(kind.__name__ for kind in types)
        raise TypeError(f"unresolved rows mix types {names}; declare one Unresolved subclass")
    return types.pop() if types else Unresolved


def _require_exact(what: str, rows: list[Any], expected: type[Any]) -> None:
    wrong = sorted({type(row).__name__ for row in rows if type(row) is not expected})
    if wrong:
        raise TypeError(f"{what} must be exactly {expected.__name__}, not {wrong}")


def build_envelope[I: Item, U: Unresolved](
    item_type: type[I],
    items: Iterable[I],
    *,
    unresolved_type: type[U] | None = None,
    tool: ToolInfo,
    command: str,
    baseline: Baseline,
    limit: int,
    offset: int,
    scanned: int = 0,
    no_hit_scopes: Iterable[str] = (),
    excluded: Iterable[str] = (),
    skipped_inputs: Iterable[SkippedInput] = (),
    unresolved: Iterable[U] = (),
    unavailable_metadata: Iterable[UnavailableMetadata] = (),
    notes: Iterable[str] = (),
) -> Envelope[I, U]:
    """Sort, bound and assemble a delivered result. Coverage lists are sorted, not bounded;
    identical skipped inputs are reported once.

    Rows must be exactly the declared types: a pydantic list of a base type would serialize a
    subclass row as the base and drop its extra fields. `unresolved_type` is inferred from the
    rows when omitted (the base `Unresolved` when there are none)."""
    item_rows = list(items)
    _require_exact("items", item_rows, item_type)
    unresolved_rows = list(unresolved)
    row_type = unresolved_type or _inferred_type(unresolved_rows)
    _require_exact("unresolved rows", unresolved_rows, row_type)
    ordered = sorted(item_rows, key=lambda item: item.sort_key())
    shown, truncation = page(ordered, name="items", limit=limit, offset=offset)
    coverage = Coverage[row_type](
        scanned=scanned,
        no_hit_scopes=sorted(set(no_hit_scopes)),
        excluded=sorted(set(excluded)),
        skipped_inputs=sorted(
            set(skipped_inputs), key=lambda row: (row.input, row.reason, row.detail)
        ),
        unresolved=sorted(unresolved_rows, key=lambda row: row.sort_key()),
        unavailable_metadata=sorted(unavailable_metadata, key=lambda row: (row.subject, row.field)),
    )
    return Envelope[item_type, row_type](
        tool=tool,
        command=command,
        generated_at=datetime.now(UTC),
        baseline=baseline,
        view=kind_of(item_type),
        items=shown,
        coverage=coverage,
        truncated=[truncation] if truncation else [],
        notes=list(dict.fromkeys(notes)),
    )


def failed_envelope(
    *,
    command: str,
    error: ErrorInfo,
    baseline: Baseline | None = None,
    authorities: Mapping[str, str] | None = None,
    notes: Iterable[str] = (),
) -> Envelope[Item, Unresolved]:
    return Envelope[Item, Unresolved](
        status="failed",
        error=error,
        tool=ToolInfo(version=tool_version(), authorities=dict(authorities or {})),
        command=command,
        generated_at=datetime.now(UTC),
        baseline=baseline,
        view=None,
        notes=list(dict.fromkeys(notes)),
    )
