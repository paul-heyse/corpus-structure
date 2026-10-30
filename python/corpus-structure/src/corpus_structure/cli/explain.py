"""Run-pinned claim and unit explanations."""

from __future__ import annotations

from typing import Literal

import typer

from corpus_structure.cli.output import JsonOpt, emit, state
from corpus_structure.cli.query import context, refusal

app = typer.Typer(help="Explain a claim or unit.")


def _explain(
    ctx: typer.Context,
    kind: Literal["claim", "unit"],
    key: str,
    run: str,
    project: str | None,
    json: bool,
) -> None:
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.serve.explain import explain as explain_query
    from corpus_structure.semantic.runtime import open_runtime_engine

    settings = state(ctx).settings()
    with (
        refusal(json),
        open_runtime_engine(settings, application_name="ci-explain", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        _, rid, _ = context(
            conn, project or (settings.runtime.default_project if run == "promoted" else None), run
        )
        emit(explain_query(conn, rid, kind, key), json=json)


@app.command("claim")
def claim(
    ctx: typer.Context,
    key: str,
    run: str = "promoted",
    project: str | None = None,
    json: JsonOpt = False,
) -> None:
    _explain(ctx, "claim", key, run, project, json)


@app.command("unit")
def unit(
    ctx: typer.Context,
    key: str,
    run: str = "promoted",
    project: str | None = None,
    json: JsonOpt = False,
) -> None:
    _explain(ctx, "unit", key, run, project, json)


def register(root: typer.Typer) -> None:
    root.add_typer(app, name="explain")
