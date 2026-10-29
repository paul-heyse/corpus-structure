"""Thin typed-query CLI adapter (D8 §4-§5)."""

from __future__ import annotations

import json as jsonlib
from contextlib import contextmanager
from dataclasses import asdict
from typing import Annotated, Any, Literal

import typer
from pydantic import ValidationError
from rich.table import Table
from sqlalchemy import text

from corpus_structure.cli.output import JsonOpt, emit, state, stderr_console
from corpus_structure.serve.journey import QueryRefused, select_run, serve_query
from corpus_structure.serve.queries import GENERIC
from corpus_structure.serve.registry import QueryRegistryError, build_registry


@contextmanager
def refusal(json: bool):
    try:
        yield
    except (
        QueryRefused,
        QueryRegistryError,
        ValidationError,
        ValueError,
        LookupError,
        OSError,
    ) as e:
        if json:
            from corpus_structure.semantic.types import PreparationError

            error: dict[str, Any] = {"code": type(e).__name__, "message": str(e)}
            if isinstance(e, PreparationError):
                error["diagnostics"] = [
                    {key: value for key, value in asdict(item).items() if value is not None}
                    for item in e.diagnostics
                ]
            typer.echo(jsonlib.dumps({"error": error}))
        else:
            stderr_console().print(f"refused: {e}")
        raise typer.Exit(1) from None


def context(conn: Any, project: str | None, run: str) -> tuple[str, int, Any]:
    from sqlalchemy import select

    from corpus_structure.schema.pack import DOMAINS
    from corpus_structure.semantic.metadata import table

    if run == "promoted" and not project:
        raise QueryRefused("a selected completed result needs its project")
    rid = select_run(conn, project or "", run if run == "promoted" else int(run))
    r = table("ops.run")
    row = conn.execute(select(r.c.project_id, r.c.options).where(r.c.id == rid)).one()
    domain = row.options.get("domain")
    if (
        not isinstance(domain, str)
        or not domain
        or __import__("pathlib").Path(domain).name != domain
    ):
        raise QueryRefused("completed run has no canonical domain pack")
    return row.project_id, rid, build_registry(GENERIC, DOMAINS / domain)


def render_query(result: Any) -> Table:
    table = Table(
        "semantic identity",
        "property / class",
        "value",
        title=f"run {result.run_id}: {result.query} ({result.projection})",
    )
    for row in result.rows:
        fact = (
            row.get("fact")
            or row.get("claim", {}).get("fact")
            or row.get("conclusion", {}).get("fact")
            or {}
        )
        entity = row.get("entity", {})
        evidence = row.get("evidence", {})
        identity = (
            fact.get("fact_id")
            or entity.get("entity_id")
            or evidence.get("evidence_id")
            or row.get("locator")
            or row.get("coverage_id", "")
        )
        relation = (
            fact.get("property_iri")
            or ", ".join(m["class_iri"] for m in entity.get("memberships", ()))
            or row.get("family", "")
        )
        value = fact.get("object", evidence.get("locator", row.get("text", row.get("outcome", ""))))
        if "claims" in row and "depth" in row:
            identity = " → ".join(claim["fact"]["fact_id"] for claim in row["claims"])
            value = f"{row['depth']} relations"
        table.add_row(str(identity), str(relation), str(value))
    if not result.coverage or any(c.outcome != "complete" for c in result.coverage):
        table.caption = "Coverage is incomplete or unknown; inspect --json for source outcomes."
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
    projection: Literal["occurrence", "fact", "accepted"] = "accepted",
    json: JsonOpt = False,
) -> None:
    from corpus_structure.semantic.runtime import open_runtime_engine

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
        settings = state(ctx).settings()
        if projection not in {"occurrence", "fact", "accepted"}:
            raise QueryRefused("invalid projection")
        with (
            open_runtime_engine(settings, application_name="ci-query", purpose="read") as engine,
            engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn,
            conn.begin(),
        ):
            conn.execute(text("SET TRANSACTION READ ONLY"))
            from corpus_structure.serve.journey import decode_token

            selected = str(decode_token(page_token)["run"]) if page_token else run
            pid, _, registry = context(
                conn,
                project or (settings.runtime.default_project if selected == "promoted" else None),
                selected,
            )
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
                projection=projection,
            )
            emit(result, json=json, render=render_query)


def register(app: typer.Typer) -> None:
    app.command("query")(query)
