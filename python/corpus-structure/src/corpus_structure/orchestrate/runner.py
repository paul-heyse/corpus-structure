"""Declarative method graph and shared unit projection; semantic execution owns persistence."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Connection

from corpus_structure.core.method import UnitRef, UnitView
from corpus_structure.core.vocab import RunKind, Stage, TaskUnitType

UnitSource = Callable[[Connection, Any, Any], Iterable[UnitRef]]


@dataclass(frozen=True)
class Step:
    config: str  # "<method>/<name>"
    upstream: tuple[str, ...] = ()
    units: UnitSource | None = None


@dataclass(frozen=True)
class Graph:
    """The configured stages and explicit proposal policy for a source workflow."""

    stages: tuple[tuple[Stage, tuple[Step, ...]], ...]
    policy_propose: bool = False

    def for_kind(self, kind: RunKind) -> Graph:
        if kind == RunKind.INGEST:
            return Graph(tuple((s, steps) for s, steps in self.stages if s == Stage.INGEST))
        return self


def unit_view(conn: Connection, view: Any, ref: UnitRef) -> UnitView:
    """A unit with its original document under the selected source binding."""
    document = None
    if ref.unit_type == TaskUnitType.DOCUMENT:
        document = ref.unit_id
    elif ref.unit_type == TaskUnitType.SOURCE_VIEW and ref.unit_id is not None:
        document = view.reader.source_view(ref.unit_id).ref.document_id
    return UnitView(ref, view, document_id=document)
