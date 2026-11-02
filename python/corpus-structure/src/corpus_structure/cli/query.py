"""Thin typed-query CLI adapter (D8 §4-§5)."""

from __future__ import annotations

import json as jsonlib
from contextlib import contextmanager
from typing import Annotated, Any, Literal

import typer
from rich.table import Table

from corpus_structure.cli.output import JsonOpt, emit, state


@contextmanager
def refusal(json: bool):
    from corpus_structure.serve.registry import QueryRegistryError

    from .failures import failure_boundary

    with failure_boundary(json, expected=(QueryRegistryError,)):
        yield


def result_context(conn: Any, project: str | None, run: str) -> tuple[str, int]:
    from sqlalchemy import select

    from corpus_structure.semantic.metadata import table
    from corpus_structure.serve.journey import QueryRefused, parse_run, select_run

    if run == "promoted" and not project:
        raise QueryRefused("a selected completed result needs its project")
    rid = select_run(conn, project or "", run if run == "promoted" else parse_run(run))
    r = table("ops.run")
    return conn.execute(select(r.c.project_id).where(r.c.id == rid)).scalar_one(), rid


def context(
    conn: Any, project: str | None, run: str, *, query_name: str | None = None
) -> tuple[str, int, Any]:
    from sqlalchemy import select

    from corpus_structure.schema.pack import DOMAINS
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.query_compatibility import open_query_registry
    from corpus_structure.serve.journey import QueryRefused, bind_session

    project_id, rid = result_context(conn, project, run)
    row = conn.execute(select(table("ops.run").c.options).where(table("ops.run").c.id == rid)).one()
    domain = row.options.get("domain")
    if (
        not isinstance(domain, str)
        or not domain
        or __import__("pathlib").Path(domain).name != domain
    ):
        raise QueryRefused("completed run has no canonical domain pack")
    return (
        project_id,
        rid,
        open_query_registry(
            bind_session(conn, rid).prepared, DOMAINS / domain, query_name=query_name
        ),
    )


def followup_context(conn: Any, token: str, project: str | None, run: str):
    from corpus_structure.semantic.continuations import validate_continuation
    from corpus_structure.semantic.query_compatibility import validate_query_token
    from corpus_structure.serve.journey import bind_session, decode_token, parse_run

    body = decode_token(token)
    pid, rid, registry = context(conn, project, str(body["run"]), query_name=body["query"])
    query = registry[body["query"]]
    session = bind_session(conn, rid)
    validate_query_token(query, body)
    validate_continuation(
        session.prepared,
        body,
        {
            "release": session.binding.release_id,
            "realization": session.binding.realization_id,
            "revision": session.binding.data_revision,
            "query": query.name,
            "version": query.version,
            **({"run": parse_run(run)} if run != "promoted" else {}),
        },
    )
    return pid, rid, query


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
    origin_token: str | None = None,
    max_rows: int | None = None,
    max_chars: int | None = None,
    projection: Literal["occurrence", "fact", "accepted"] = "accepted",
    json: JsonOpt = False,
) -> None:
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.serve.journey import QueryRefused, parse_run, serve_query

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
            read_snapshot(engine) as conn,
        ):
            from corpus_structure.serve.journey import decode_token

            selected = str(decode_token(page_token)["run"]) if page_token else run
            serving_run = run if run == "promoted" else parse_run(run)
            origin_query = None
            if origin_token is not None:
                _, origin_run, origin_query = followup_context(
                    conn, origin_token, project, selected if page_token else run
                )
                if page_token is None:
                    selected = str(origin_run)
                    serving_run = origin_run
            try:
                pid, _, registry = context(
                    conn,
                    project
                    or (settings.runtime.default_project if selected == "promoted" else None),
                    selected,
                    query_name=name,
                )
            except QueryRefused as error:
                if page_token is None:
                    raise
                from corpus_structure.semantic.refusals import StaleSnapshot

                raise StaleSnapshot(
                    f"continuation result is unavailable: {error}", reason="unavailable_result"
                ) from error
            result = serve_query(
                conn,
                registry,
                name,
                params,
                project_id=pid,
                run=serving_run,
                page_token=page_token,
                max_rows=max_rows,
                max_chars=max_chars,
                projection=projection,
                origin_query=origin_query,
            )
            emit(result, json=json, render=render_query)


def register(app: typer.Typer) -> None:
    app.command("query")(query)
