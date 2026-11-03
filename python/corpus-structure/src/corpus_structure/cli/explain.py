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
    page_token: str | None = None,
    limit: int = 64,
    max_bytes: int = 1024 * 1024,
    collection: str | None = None,
    report: str | None = None,
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
        if report is not None:
            from corpus_structure.serve.explain import unit_source_report
            from corpus_structure.serve.journey import bind_session

            value = (
                bind_session(conn, rid).source_report(key, report, max_bytes=max_bytes)
                if kind == "claim"
                else unit_source_report(conn, rid, key, collection, report, max_bytes=max_bytes)
            )
        elif collection is not None:
            from corpus_structure.serve.journey import bind_session

            if kind != "claim":
                raise ValueError("unit inventories are selected through explain unit")
            value = bind_session(conn, rid).inventory(
                key, collection, continuation=page_token, limit=limit, max_bytes=max_bytes
            )
        else:
            value = explain_query(
                conn,
                rid,
                kind,
                key,
                query=query,
                continuation=page_token,
                limit=limit,
                max_bytes=max_bytes,
            )
        emit(value, json=json)


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
    page_token: str | None = None,
    limit: int = 64,
    max_bytes: int = 1024 * 1024,
) -> None:
    _explain(ctx, "unit", key, run, project, json, query_token, page_token, limit, max_bytes)


@app.command("inventory")
def inventory(
    ctx: typer.Context,
    key: str,
    collection: str,
    run: str = "promoted",
    project: str | None = None,
    json: JsonOpt = False,
    query_token: str | None = None,
    page_token: str | None = None,
    limit: int = 64,
    max_bytes: int = 1024 * 1024,
) -> None:
    """Read one claim evidence/reference inventory page."""
    _explain(
        ctx, "claim", key, run, project, json, query_token, page_token, limit, max_bytes, collection
    )


@app.command("report")
def report(
    ctx: typer.Context,
    kind: Literal["claim", "unit"],
    key: str,
    identifier: str,
    collection: str = "observation",
    run: str = "promoted",
    project: str | None = None,
    json: JsonOpt = False,
    query_token: str | None = None,
    max_bytes: int = 1024 * 1024,
) -> None:
    """Explicitly read an immutable observation or unit task-result body."""
    _explain(
        ctx,
        kind,
        key,
        run,
        project,
        json,
        query_token,
        max_bytes=max_bytes,
        collection=collection,
        report=identifier,
    )


def register(root: typer.Typer) -> None:
    root.add_typer(app, name="explain")
