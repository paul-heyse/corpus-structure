"""Configured source-method graph shared by semantic preparation and execution.

The base graph ingests/profile documents, recognizes mathematical source reports and queues
release-bound automated proposals. Semantic domain operations own final materialization;
independent reference evaluation uses evaluate.semantic. Config descriptors for those later
operations remain registered so existing methods.yaml declarations resolve consistently.
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

M01, M02 = "ingest.pdf", "profile.segments"
MATH_ENRICH = "enrich.pdf_math"
M09, M11, M13 = "extract.math", "normalize.formula", "resolve.symbol_scope"

PHASE0 = Graph(
    (
        (Stage.INGEST, (Step(f"{M01}/default"),)),
        (
            Stage.NORMALIZE,
            (
                Step(f"{MATH_ENRICH}/default", upstream=(M01,)),
                Step(f"{M02}/default", upstream=(MATH_ENRICH,)),
                Step(f"{M09}/default", upstream=(MATH_ENRICH,)),
                Step(f"{M11}/default", upstream=(MATH_ENRICH,)),
            ),
        ),
        (Stage.SCOPE, (Step(f"{M13}/default", upstream=(M09, M11)),)),
    ),
    policy_propose=True,
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
    native_names = {method.name for method in ingest_methods.METHODS}
    methods = (
        *ingest_methods.native_methods(),
        *(method for method in METHODS if method.name not in native_names),
    )
    return MethodRegistry(methods, load_methods(pack / "methods.yaml"))


def stub_pass(conn: Connection, run_id: int, pass_: str, m19_task_id: int | None) -> PassReport:
    """A pass that consolidates nothing (until P0-C-1)."""
    return PassReport()


def stub_evaluate(conn: Connection, run_id: int, task_id: int) -> TaskStatus:
    """No adjudicated unit in scope (until P0-E-2b)."""
    return TaskStatus.EMPTY
