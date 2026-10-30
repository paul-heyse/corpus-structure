"""Named composable domain queries on one release-bound semantic snapshot."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, JsonValue
from sqlalchemy import Connection

from corpus_structure.semantic.query import Coverage, ReadSession, SnapshotBinding


@dataclass(frozen=True)
class Scope:
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
    run_id: int
    conn: Connection
    row_batch: int = 64
    projection: Literal["occurrence", "fact", "accepted"] = "accepted"

    @cached_property
    def session(self) -> ReadSession:
        from corpus_structure.serve.journey import bind_session

        return bind_session(self.conn, self.run_id)

    @cached_property
    def reader(self) -> Any:
        from corpus_structure.serve.read import Reader

        return Reader(self)

    @property
    def compiled(self) -> Any:
        return self.session.prepared


@dataclass(frozen=True)
class Positioned:
    row: BaseModel
    position: JsonValue


@runtime_checkable
class DomainQuery(Protocol):
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


class QueryResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    run_id: int
    binding: SnapshotBinding
    projection: Literal["occurrence", "fact", "accepted"]
    arithmetic_profile: str = "exact"
    query: str
    version: str
    params: dict[str, JsonValue]
    coverage: tuple[Coverage, ...]
    knowledge: Literal["observed", "unknown", "absent"]
    coverage_diagnostic: str | None = None
    rows: list[dict[str, JsonValue]]
    next_page_token: str | None = None
    truncated: bool = False
