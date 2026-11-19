"""Process and disk cache inspection and bounded disk pruning."""

import typer

from corpus_structure.cache_store import DiskSnapshot, Tier
from corpus_structure.caches import CacheSnapshot

from .output import JsonOpt, emit, state

app = typer.Typer(help="Inspect reuse and retention, and prune disk entries.", no_args_is_help=True)


class CacheReport(CacheSnapshot):
    disk: DiskSnapshot


@app.command("stats")
def stats(ctx: typer.Context, json: JsonOpt = False) -> None:
    """Report this invocation's counters and shared disk occupancy."""
    from corpus_structure.cache_store import configured_store
    from corpus_structure.caches import snapshot
    from corpus_structure.cli.failures import failure_boundary

    with failure_boundary(json, expected=(ValueError, OSError)):
        state(ctx).settings()
        emit(
            CacheReport(**snapshot(owner="ci").model_dump(), disk=configured_store().snapshot()),
            json=json,
        )


@app.command("prune")
def prune(ctx: typer.Context, tier: Tier | None = None, json: JsonOpt = False) -> None:
    """Bring disk tiers within their configured budgets and remove abandoned writers."""
    from corpus_structure.cache_store import configured_store
    from corpus_structure.cli.failures import failure_boundary

    with failure_boundary(json, expected=(ValueError, OSError)):
        state(ctx).settings()
        emit(configured_store().prune(tier), json=json)


def register(root: typer.Typer) -> None:
    root.add_typer(app, name="cache")
