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
the graph ends its base stages at `scope`. Until consolidation (P0-C-1) and evaluation (P0-E-2b)
land, `stub_pass` and `stub_evaluate` stand in: a pass that consolidates nothing and an evaluation
with no adjudicated unit in scope (`empty`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sqlalchemy import Connection

from corpus_structure.core.vocab import Stage, TaskStatus
from corpus_structure.ingest import methods as ingest_methods
from corpus_structure.orchestrate.registry import MethodRegistry, load_methods
from corpus_structure.orchestrate.runner import Graph, PassReport, Step

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


# The phase 0 methods, registered as their packages land (P0-I-1b, P0-I-2b, …).
METHODS: tuple[Any, ...] = (*ingest_methods.METHODS,)


def registry(pack: Path) -> MethodRegistry:
    """The phase 0 registry over the pack's `methods.yaml` (an absent file is an empty one)."""
    return MethodRegistry(METHODS, load_methods(pack / "methods.yaml"))


def stub_pass(conn: Connection, run_id: int, pass_: str, m19_task_id: int | None) -> PassReport:
    """A pass that consolidates nothing (until P0-C-1)."""
    return PassReport()


def stub_evaluate(conn: Connection, run_id: int, task_id: int) -> TaskStatus:
    """No adjudicated unit in scope (until P0-E-2b)."""
    return TaskStatus.EMPTY
