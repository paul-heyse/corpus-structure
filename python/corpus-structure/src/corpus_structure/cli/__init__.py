"""The `ci` command groups, registered from one tuple (D8 §4; coordinator decision 10).

Typer and Rich are imported only under this package. Each owning document adds its module here
(`cli/<group>.py` with a `register(app)`) in place of its `Planned` entry.
"""

from __future__ import annotations

from collections.abc import Callable

import typer

from corpus_structure.cli import schema, status
from corpus_structure.cli.planned import Planned

_F, _S, _I, _O = "foundations", "schema and rules", "ingest and math", "orchestration"
_C, _E, _A = "consolidation and queries", "evaluation and goldens", "agent interface"

REGISTRY: tuple[Callable[[typer.Typer], None], ...] = (
    Planned("db", "Create or migrate the database.", f"{_F}, P0-F-4").register,
    schema.register,
    Planned("ingest", "Run M01-M03 over a slice or paths.", f"{_I}, P0-I-1b").register,
    Planned("project", "Create the project from a pack and corpus.", f"{_O}, P0-O-1").register,
    Planned("run", "Start or cancel a run.", f"{_O}, P0-O-1").register,
    status.register,
    Planned("tasks", "List a run's tasks.", f"{_O}, P0-O-1").register,
    Planned("query", "Run a typed query.", f"{_C}, P0-C-2").register,
    Planned("explain", "Explain a claim or unit.", f"{_C}, P0-C-2").register,
    Planned("golden", "Golden split, creation and status.", f"{_E}, P0-E-1").register,
    Planned("eval", "Score a run.", f"{_E}, P0-E-2b").register,
    Planned("digest", "The operator digest.", _E).register,
    Planned("promote", "Promote a run.", f"{_E}, P0-E-2b").register,
    Planned("experiment", "Experiments (phase 1).", _E).register,
    Planned("mcp", "Serve the MCP tools on stdio.", f"{_A}, P0-A-1").register,
    Planned("direct", "Record an operator direction.", f"{_A}, P0-A-1").register,
    Planned("ack", "Acknowledge a change (phase 1).", _A).register,
    Planned("veto", "Veto an experiment (phase 1).", _A).register,
)
