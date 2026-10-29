"""The domain-query protocol, its context, scopes and the result model (D8 §5, §5.2;
consolidation and queries §3.9).

`serve` owns `DomainQuery`, `QueryContext`, `Scope` and `QueryResult`; a pack's `queries.py`
supplies only its named queries. `QueryContext` carries the pinned run id and the connection the
journey reads through; queries read, never write.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, JsonValue
from sqlalchemy import Connection


@dataclass(frozen=True)
class Scope:
    """The units coverage is over: the whole run, some documents, or some unit keys."""

    kind: Literal["run", "documents", "units"] = "run"
    documents: tuple[int, ...] = ()
    unit_keys: tuple[str, ...] = ()

    @classmethod
    def run(cls) -> Scope:
        return cls()

    @classmethod
    def of_documents(cls, documents: Sequence[int]) -> Scope:
        return cls("documents", documents=tuple(sorted(set(documents))))

    @classmethod
    def of_units(cls, unit_keys: Sequence[str]) -> Scope:
        return cls("units", unit_keys=tuple(sorted(set(unit_keys))))


@dataclass
class QueryContext:
    """What a query reads through: the pinned (finished) run and a connection."""

    run_id: int
    conn: Connection

    @cached_property
    def reader(self) -> Any:
        from corpus_structure.serve.read import Reader
        return Reader(self)

    @property
    def compiled(self) -> Any:
        return self.reader.compiled

    def claims(self, **filters: Any) -> Iterator[Any]:
        return self.reader.claims(**filters)

    def entities(self, key: str | None = None, label: str | None = None) -> list[dict[str, Any]]:
        return self.reader.entities(key, label)

    def evidence(self, claim_key: str) -> list[dict[str, Any]]:
        return self.reader.evidence(claim_key)


@dataclass(frozen=True)
class Positioned:
    row: BaseModel
    position: JsonValue


@runtime_checkable
class DomainQuery(Protocol):
    """One typed query (D8 §5.2): its name, version (bound into page tokens), params and row
    models, its rows in a deterministic order, and its scope."""

    @property
    def name(self) -> str: ...

    @property
    def version(self) -> str: ...

    @property
    def params(self) -> type[BaseModel]: ...

    @property
    def result(self) -> type[BaseModel]: ...

    def rows(self, ctx: QueryContext, p: Any, after: JsonValue = None) -> Iterator[Positioned]: ...

    def scope(self, ctx: QueryContext, p: Any) -> Scope: ...


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Coverage(_Frozen):
    """The fates of the scope's eligible units as of the run's cut (§3.10)."""

    scope: Literal["run", "documents", "units"]
    eligible: int
    extracted: int
    skipped: dict[str, int] = Field(default_factory=dict)  # SkipReason code -> units
    failed: int = 0
    unresolved: int = 0
    partial: bool = False
    unresolved_references: int = 0


class QueryResult(_Frozen):
    """What every query returns, and what `--json` writes."""

    run_id: int
    query: str
    version: str
    params: dict[str, JsonValue]
    coverage: Coverage
    rows: list[dict[str, JsonValue]]
    next_page_token: str | None = None
    truncated: bool = False
