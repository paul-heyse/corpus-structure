"""Declarative method graph and shared unit projection; semantic execution owns persistence."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy import Connection

from corpus_structure.core.method import UnitRef, UnitView
from corpus_structure.core.vocab import RunKind, Stage, TaskStatus, TaskUnitType


class PassOutcome(Protocol):
    """What the runner reads of a pass's report, structurally: consolidation returns its own
    report type (it does not import `orchestrate`)."""

    @property
    def counts(self) -> Mapping[str, int]: ...

    @property
    def rule_counts(self) -> Mapping[str, int]: ...

    @property
    def consumed(self) -> tuple[int, ...]: ...


@dataclass(frozen=True)
class PassReport:
    """A minimal `PassOutcome` (stubs and tests): counts by code, M19's per-rule evaluated counts
    and the propose tasks it consumed (D5 §1, §11)."""

    counts: Mapping[str, int] = field(default_factory=dict)
    rule_counts: Mapping[str, int] = field(default_factory=dict)
    consumed: tuple[int, ...] = ()


PassRunner = Callable[[Connection, int, str, int | None], PassOutcome]


Evaluate = Callable[[Connection, int, int], TaskStatus]


UnitSource = Callable[[Connection, Any, Any], Iterable[UnitRef]]


@dataclass(frozen=True)
class Step:
    config: str  # "<method>/<name>"
    upstream: tuple[str, ...] = ()
    units: UnitSource | None = None


@dataclass(frozen=True)
class Graph:
    """The base stages and the run-level configurations of the passes (phase 0, §3.8)."""

    stages: tuple[tuple[Stage, tuple[Step, ...]], ...]
    pass_config: str = "consolidate.claims/default"
    m19_config: str = "validate.rules/default"
    evaluate_config: str = "evaluate.score/default"
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
