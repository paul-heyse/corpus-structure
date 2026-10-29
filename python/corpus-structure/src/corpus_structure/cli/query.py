"""Thin typed-query CLI adapter (D8 §4-§5)."""

from __future__ import annotations

import json as jsonlib
from contextlib import contextmanager
from typing import Annotated, Any

import typer
from pydantic import ValidationError
from rich.table import Table
from sqlalchemy import text

from corpus_structure.cli.orchestrate import ENGINE
from corpus_structure.cli.output import JsonOpt, emit, state, stderr_console
from corpus_structure.serve.journey import QueryRefused, select_run, serve_query
from corpus_structure.serve.queries import GENERIC
from corpus_structure.serve.registry import QueryRegistryError, build_registry


@contextmanager
def refusal(json: bool):
    try:
        yield
    except (QueryRefused, QueryRegistryError, ValidationError, ValueError, LookupError) as e:
        if json:
            typer.echo(jsonlib.dumps({"error": {"code": type(e).__name__, "message": str(e)}}))
        else:
            stderr_console().print(f"refused: {e}")
        raise typer.Exit(1) from None


def context(conn: Any, project: str | None, run: str) -> tuple[int, int, Any]:
    from corpus_structure.orchestrate.commands import project_id
    from corpus_structure.schema.pack import DOMAINS

    if run != "promoted":
        row = conn.execute(
            text(
                "SELECT p.id,p.domain FROM ops.run r JOIN meta.project p ON "
                "p.id=r.project_id WHERE r.id=:r"
            ),
            {"r": int(run)},
        ).one_or_none()
        if row is None:
            raise QueryRefused(f"no run {run}")
        pid, domain = row
        if project is not None and project_id(conn, project)[0] != pid:
            raise QueryRefused("run belongs to another project")
        rid = select_run(conn, pid, int(run))
    else:
        pid, _ = project_id(conn, project)
        rid = select_run(conn, pid, run)
        domain = conn.execute(
            text("SELECT domain FROM meta.project WHERE id=:p"), {"p": pid}
        ).scalar_one()
    return pid, rid, build_registry(GENERIC, DOMAINS / domain)


def render_query(result: Any) -> Table:
    table = Table(
        "key", "predicate / type", "status / label", title=f"run {result.run_id}: {result.query}"
    )
    for row in result.rows:
        table.add_row(
            str(row.get("key", "")),
            str(row.get("predicate", row.get("type", ""))),
            str(row.get("status", row.get("label", ""))),
        )
    if result.coverage.partial:
        table.caption = "Partial coverage; inspect --json for fates and unresolved references."
    if result.next_page_token:
        table.caption = (table.caption or "") + " Next page: " + result.next_page_token
    return table


def query(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument()],
    run: str = "promoted",
    project: str | None = None,
    param: Annotated[list[str] | None, typer.Option("--param")] = None,
    page_token: str | None = None,
    max_rows: int | None = None,
    max_chars: int | None = None,
    json: JsonOpt = False,
) -> None:
    params = {}
    with refusal(json):
        for pair in param or []:
            if "=" not in pair:
                raise QueryRefused("--param needs NAME=VALUE")
            key, value = pair.split("=", 1)
            if key in params:
                raise QueryRefused(f"duplicate parameter {key}")
            try:
                params[key] = jsonlib.loads(value)
            except ValueError:
                params[key] = value
        with ENGINE(state(ctx).settings()) as engine, engine.connect() as conn:
            conn.execute(text("SET TRANSACTION READ ONLY"))
            from corpus_structure.serve.journey import decode_token

            selected = str(decode_token(page_token)["run"]) if page_token else run
            pid, _, registry = context(conn, project, selected)
            result = serve_query(
                conn,
                registry,
                name,
                params,
                project_id=pid,
                run=run if run == "promoted" else int(run),
                page_token=page_token,
                max_rows=max_rows,
                max_chars=max_chars,
            )
            emit(result, json=json, render=render_query)


def register(app: typer.Typer) -> None:
    app.command("query")(query)
