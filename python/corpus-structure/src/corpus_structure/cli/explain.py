"""Run-pinned claim and unit explanations."""

from __future__ import annotations

from typing import Literal

import typer
from sqlalchemy import text

from corpus_structure.cli.orchestrate import ENGINE
from corpus_structure.cli.output import JsonOpt, emit, state
from corpus_structure.cli.query import context, refusal
from corpus_structure.serve.explain import explain as explain_query

app = typer.Typer(help="Explain a claim or unit.")


def _explain(
    ctx: typer.Context,
    kind: Literal["claim", "unit"],
    key: str,
    run: str,
    project: str | None,
    json: bool,
) -> None:
    with refusal(json), ENGINE(state(ctx).settings()) as engine, engine.connect() as conn:
        conn.execute(text("SET TRANSACTION READ ONLY"))
        _, rid, _ = context(conn, project, run)
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
