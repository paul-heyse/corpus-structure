"""The `ci` command groups, registered from one tuple (D8 §4; coordinator decision 10).

Typer and Rich are imported only under this package. Each owning document adds its module here
(`cli/<group>.py` with a `register(app)`) in place of its `Planned` entry.
"""

from __future__ import annotations

from collections.abc import Callable

import typer

from corpus_structure.cli import (
    db,
    explain,
    export,
    golden,
    mcp,
    orchestrate,
    query,
    regenerate,
    schema,
    status,
    source,
)
from corpus_structure.cli import eval as evaluation
from corpus_structure.cli.planned import Planned

_F, _S, _I, _O = "foundations", "schema and rules", "ingest and math", "orchestration"
_C, _E, _A = "consolidation and queries", "evaluation and goldens", "agent interface"

REGISTRY: tuple[Callable[[typer.Typer], None], ...] = (
    db.register,
    regenerate.register,
    schema.register,
    Planned("ingest", "Run M01-M03 over a slice or paths.", f"{_I}, P0-I-1b").register,
    orchestrate.register,
    status.register,
    source.register,
    query.register,
    explain.register,
    export.register,
    golden.register,
    evaluation.register,
    Planned("digest", "The operator digest.", _E).register,
    Planned("promote", "Promote a run.", f"{_E}, P0-E-2b").register,
    Planned("experiment", "Experiments (phase 1).", _E).register,
    mcp.register,
    Planned("ack", "Acknowledge a change (phase 1).", _A).register,
    Planned("veto", "Veto an experiment (phase 1).", _A).register,
)
