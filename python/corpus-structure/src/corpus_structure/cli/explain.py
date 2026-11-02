"""Run-pinned claim and unit explanations."""

from __future__ import annotations

from typing import Literal

import typer

from corpus_structure.cli.output import JsonOpt, emit, state
from corpus_structure.cli.query import refusal, result_context

app = typer.Typer(help="Explain a claim or unit.")


def _explain(
    ctx: typer.Context,
    kind: Literal["claim", "unit"],
    key: str,
    run: str,
    project: str | None,
    json: bool,
    query_token: str | None = None,
) -> None:
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.explain import explain as explain_query

    settings = state(ctx).settings()
    with (
        refusal(json),
        open_runtime_engine(settings, application_name="ci-explain", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        query = None
        if query_token is not None:
            from corpus_structure.cli.query import followup_context

            _, rid, query = followup_context(conn, query_token, project, run)
        else:
            _, rid = result_context(
                conn,
                project or (settings.runtime.default_project if run == "promoted" else None),
                run,
            )
        emit(explain_query(conn, rid, kind, key, query=query), json=json)


@app.command("claim")
def claim(
    ctx: typer.Context,
    key: str,
    run: str = "promoted",
    project: str | None = None,
    json: JsonOpt = False,
    query_token: str | None = None,
) -> None:
    _explain(ctx, "claim", key, run, project, json, query_token)


@app.command("unit")
def unit(
    ctx: typer.Context,
    key: str,
    run: str = "promoted",
    project: str | None = None,
    json: JsonOpt = False,
    query_token: str | None = None,
) -> None:
    _explain(ctx, "unit", key, run, project, json, query_token)


def register(root: typer.Typer) -> None:
    root.add_typer(app, name="explain")
