"""The explicit installed command registry (D8 §4)."""

from __future__ import annotations

from collections.abc import Callable

import typer

from corpus_structure.cli import (
    contributions,
    db,
    explain,
    export,
    golden,
    managed,
    mcp,
    model,
    operations,
    orchestrate,
    query,
    records,
    regenerate,
    review,
    schema,
    source,
    status,
    structure,
    testing,
)
from corpus_structure.cli import eval as evaluation

REGISTRY: tuple[Callable[[typer.Typer], None], ...] = (
    operations.register,
    managed.register,
    testing.register,
    db.register,
    regenerate.register,
    schema.register,
    model.register,
    orchestrate.register,
    status.register,
    source.register,
    query.register,
    records.register,
    contributions.register,
    review.register,
    structure.register,
    explain.register,
    export.register,
    golden.register,
    evaluation.register,
    mcp.register,
)
