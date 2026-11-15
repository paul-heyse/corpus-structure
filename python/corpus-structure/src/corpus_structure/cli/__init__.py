"""The explicit installed command registry (D8 §4)."""

from __future__ import annotations

from collections.abc import Callable

import typer

from corpus_structure.cli import (
    db,
    demands,
    interpretations,
    managed,
    mcp,
    model,
    operations,
    orchestrate,
    regenerate,
    research,
    schema,
    selected_assessment,
    selected_results,
    source,
    source_inspection,
    status,
    structure,
    testing,
)

REGISTRY: tuple[Callable[[typer.Typer], None], ...] = (
    operations.register,
    managed.register,
    testing.register,
    db.register,
    demands.register,
    regenerate.register,
    schema.register,
    model.register,
    source_inspection.register,
    orchestrate.register,
    status.register,
    source.register,
    selected_results.register,
    research.register,
    interpretations.register,
    structure.register,
    selected_assessment.register,
    mcp.register,
)
