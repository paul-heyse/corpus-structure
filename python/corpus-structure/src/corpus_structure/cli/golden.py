"""`ci golden split`, `ci golden create` and `ci golden status` (evaluation §3.1-§3.4, P0-E-1;
D8 §4).

The work is in `evaluate/split.py` and `evaluate/sets.py`; this layer opens the store through
`cli.orchestrate`'s seams (`ENGINE`, and `PHASE0` for the pack directory and the registry), reads
the pack's `eval/split.yaml`, and renders. A refused command exits 1 with its
reason on stderr. `status` prints counts only, never a golden item.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated, Any

import typer
from pydantic import BaseModel
from rich.console import Group, RenderableType
from rich.table import Table

from corpus_structure.cli import orchestrate as seams
from corpus_structure.cli.output import JsonOpt, emit, state, stderr_console
from corpus_structure.core.vocab import DocumentSplit

golden_app = typer.Typer(help="Golden split, creation and status.", no_args_is_help=True)
ProjectOpt = Annotated[str | None, typer.Option(help="The project (default: the only one).")]


@contextmanager
def _session(ctx: typer.Context, project: str | None) -> Iterator[tuple[Any, Any, Any]]:
    """A transaction, the project's id and its pack's (evaluation values, seams, root)."""
    from corpus_structure.evaluate import goldens, sets, split
    from corpus_structure.orchestrate import commands, registry, runs

    phase0 = seams.PHASE0()
    try:
        with seams.ENGINE(state(ctx).settings()) as engine, engine.begin() as conn:
            project_id, domain = commands.project_id(conn, project)
            pack = phase0["domains"] / domain
            yield conn, project_id, (split.load_eval(pack), phase0, pack)
    except (
        commands.CommandError,
        registry.RegistryError,
        split.SplitError,
        sets.GoldenSetError,
        goldens.GoldenStoreError,
        runs.RunError,
    ) as error:
        stderr_console().print(f"refused: {error}")
        raise typer.Exit(code=1) from None


def _table(title: str, result: BaseModel) -> Table:
    table = Table("field", "value", title=title)
    for name, value in result.model_dump(mode="json").items():
        table.add_row(name, str(value))
    return table


@golden_app.command("split")
def split_command(
    ctx: typer.Context,
    seed: Annotated[int | None, typer.Option(help="The split seed (default: the pack's).")] = None,
    project: ProjectOpt = None,
    json: JsonOpt = False,
) -> None:
    """Assign every registered page to dev, test or reserved, once."""
    from corpus_structure.evaluate.split import split_documents

    with _session(ctx, project) as (conn, project_id, (config, _, _)):
        report = split_documents(conn, project_id, config.split, seed)
    emit(report, json=json, render=lambda r: _table("split", r))


@golden_app.command("create")
def create_command(
    ctx: typer.Context,
    split: Annotated[DocumentSplit, typer.Option(help="dev or test.")],
    label: Annotated[str, typer.Option(help="The set's label.")],
    size: Annotated[int | None, typer.Option(help="Units (default: the pack's).")] = None,
    seed: Annotated[int | None, typer.Option(help="The sampling seed.")] = None,
    from_run: Annotated[int | None, typer.Option(help="The source run.")] = None,
    project: ProjectOpt = None,
    json: JsonOpt = False,
) -> None:
    """Sample a golden set and open its golden run with the pass A and B tasks."""
    from corpus_structure.evaluate.sets import create_golden_set

    with _session(ctx, project) as (conn, project_id, (config, phase0, pack)):
        created = create_golden_set(
            conn,
            project_id=project_id,
            split=split,
            label=label,
            config=config,
            registry=phase0["registry_for"](pack),
            size=size,
            seed=seed,
            from_run=from_run,
        )
    emit(created, json=json, render=lambda r: _table(f"golden set {label}", r))


def _render_status(result: BaseModel) -> RenderableType:
    from corpus_structure.evaluate.sets import GoldenStatus

    assert isinstance(result, GoldenStatus)
    tables = []
    for s in result.sets:
        table = Table("field", "value", title=f"golden set {s.label} ({s.split})")
        table.add_row("units", ", ".join(f"{k} {v}" for k, v in sorted(s.units.items())))
        table.add_row("golden run", f"{s.golden_run_id} {s.golden_run_status or ''}")
        table.add_row("stale", ", ".join(s.stale) or "none")
        table.add_row("coarse spans", ", ".join(f"{k} {v}" for k, v in s.coarse.items()) or "none")
        tables.append(table)
    return Group(*tables)


@golden_app.command("status")
def status_command(
    ctx: typer.Context,
    label: Annotated[str, typer.Option(help="The set's label.")],
    split: Annotated[DocumentSplit | None, typer.Option(help="dev or test.")] = None,
    project: ProjectOpt = None,
    json: JsonOpt = False,
) -> None:
    """Unit counts, the golden run (settled when every unit is adjudicated) and stale units."""
    from corpus_structure.evaluate.sets import golden_status

    with _session(ctx, project) as (conn, project_id, _):
        result = golden_status(conn, project_id, label, split)
    emit(result, json=json, render=_render_status)


def register(app: typer.Typer) -> None:
    app.add_typer(golden_app, name="golden")
