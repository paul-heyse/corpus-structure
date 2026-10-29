"""The phase 0 graph (orchestration §3.8; D6 §2, phase 0), as data.

| Stage | Steps | Upstream |
|---|---|---|
| `ingest` | `ingest.html/default` (M01, with M03); `profile.segments/default` (M02) | M02: M01 |
| `normalize` | `extract.math/default` (M09), `normalize.formula/default` (M11), independent | M01 |
| `scope` | `resolve.symbol_scope/default` (M13) | M09, M11 |
| `propose` | the `propose` chain (§3.10, P0-O-2) | M24: M01, M13 |
| `assemble` | one consolidation pass | — |
| `finalize` | the seal; the final pass with M19 as of the cut; measure, evaluate, finish | — |

Every step's units come from its method's `select`. The propose chain joins with P0-O-2; until then
the graph ends its base stages at `scope`. The passes run consolidation's `run_pass` (P0-C-1) under
`consolidate.claims`, with M19 (`validate.rules`) as of the cut. Until evaluation (P0-E-2b) lands,
`EvaluateStub` registers `evaluate.score`, whose task the seal creates, and `stub_evaluate` is its
outcome: no adjudicated unit in scope (`empty`). `stub_pass`, a pass that consolidates nothing,
serves tests.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Connection

from corpus_structure.consolidate.pass_ import ConsolidateMethod
from corpus_structure.core.method import (
    Digest,
    MethodContext,
    Resources,
    RunView,
    UnitRef,
    UnitResult,
    UnitView,
)
from corpus_structure.core.vocab import (
    ConfidenceSource,
    MethodFamily,
    MethodTier,
    Stage,
    TaskStatus,
    TaskUnitType,
)
from corpus_structure.ingest import methods as ingest_methods
from corpus_structure.methods.llm.agent_opus import AgentOpus
from corpus_structure.methods.math import methods as math_methods
from corpus_structure.orchestrate.registry import MethodRegistry, load_methods
from corpus_structure.orchestrate.runner import Graph, PassReport, Step
from corpus_structure.validate.runner import RulesMethod

M01, M02 = "ingest.html", "profile.segments"
M09, M11, M13 = "extract.math", "normalize.formula", "resolve.symbol_scope"

PHASE0 = Graph(
    (
        (Stage.INGEST, (Step(f"{M01}/default"), Step(f"{M02}/default", upstream=(M01,)))),
        (
            Stage.NORMALIZE,
            (Step(f"{M09}/default", upstream=(M01,)), Step(f"{M11}/default", upstream=(M01,))),
        ),
        (Stage.SCOPE, (Step(f"{M13}/default", upstream=(M09, M11)),)),
    )
)


class EvaluateConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class EvaluateStub:
    """`evaluate.score` until P0-E-2b: a run-unit method the runner calls; no worker runs it."""

    name = "evaluate.score"
    version = "stub"
    family = MethodFamily.EVAL
    unit_type = TaskUnitType.RUN
    tier = MethodTier.DETERMINISTIC
    confidence_source: ConfidenceSource | None = None
    Config = EvaluateConfig
    resources = Resources()

    def select(self, run: RunView, cfg: EvaluateConfig) -> Iterable[UnitRef]:
        return [UnitRef(TaskUnitType.RUN)]

    def input_digest(self, unit: UnitView, cfg: EvaluateConfig) -> Digest:
        return Digest(f"{self.name}|{self.version}".encode())

    def run(
        self, units: Sequence[UnitView], cfg: EvaluateConfig, ctx: MethodContext
    ) -> Sequence[UnitResult]:
        raise RuntimeError("evaluate.score runs in the runner's evaluate stage; no worker runs it")


# The phase 0 methods, registered as their packages land (P0-I-1b, P0-I-2b, …).
METHODS: tuple[Any, ...] = (
    *ingest_methods.METHODS,
    *math_methods.METHODS,
    AgentOpus(),
    ConsolidateMethod(),
    RulesMethod(),
    EvaluateStub(),
)


def registry(pack: Path) -> MethodRegistry:
    """The phase 0 registry over the pack's `methods.yaml` (an absent file is an empty one)."""
    return MethodRegistry(METHODS, load_methods(pack / "methods.yaml"))


def stub_pass(conn: Connection, run_id: int, pass_: str, m19_task_id: int | None) -> PassReport:
    """A pass that consolidates nothing (until P0-C-1)."""
    return PassReport()


def stub_evaluate(conn: Connection, run_id: int, task_id: int) -> TaskStatus:
    """No adjudicated unit in scope (until P0-E-2b)."""
    return TaskStatus.EMPTY
