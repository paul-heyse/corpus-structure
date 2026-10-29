"""Completed-result selection, semantic snapshot binding and stable named-query paging."""

from __future__ import annotations

import base64
import binascii
import json
from collections.abc import Mapping
from typing import Any, Literal
from uuid import uuid4

from pydantic import JsonValue
from sqlalchemy import Connection, select

from corpus_structure.core.canonical import canonical_json, digest
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.query import ReadSession, SnapshotBinding
from corpus_structure.semantic.releases import load_release
from corpus_structure.serve.protocol import DomainQuery, QueryContext, QueryResult, Scope

PROMOTED = "promoted"


class QueryRefused(ValueError):
    """A query that cannot name an authoritative completed result."""


class StaleToken(QueryRefused):
    pass


def check_finished(conn: Connection, run_id: int) -> int:
    completed = table("ops.completed_result")
    if (
        conn.execute(
            select(completed.c.run_id).where(completed.c.run_id == run_id)
        ).scalar_one_or_none()
        is None
    ):
        raise QueryRefused(f"no completed semantic result for run {run_id}")
    return run_id


def select_run(conn: Connection, project_id: str, run: int | str = PROMOTED) -> int:
    if run == PROMOTED:
        project = table("data.project")
        found = conn.execute(
            select(project.c.selected_result_run_id).where(project.c.project_id == project_id)
        ).scalar_one_or_none()
        if found is None:
            raise QueryRefused("no selected completed result")
        run = int(found)
    run_id = check_finished(conn, int(run))
    r = table("ops.run")
    if (
        project_id
        and conn.execute(select(r.c.project_id).where(r.c.id == run_id)).scalar_one() != project_id
    ):
        raise QueryRefused("run belongs to another project")
    return run_id


def bind_session(conn: Connection, run_id: int) -> ReadSession:
    if (
        conn.get_isolation_level() != "REPEATABLE READ"
        or conn.exec_driver_sql("SHOW transaction_read_only").scalar_one() != "on"
    ):
        raise QueryRefused("serving requires a read-only REPEATABLE READ transaction")
    check_finished(conn, run_id)
    completed, realization = table("ops.completed_result"), table("data.realization")
    row = conn.execute(
        select(
            completed.c.release_id, completed.c.output_realization_id, realization.c.data_revision
        )
        .join(realization, realization.c.realization_id == completed.c.output_realization_id)
        .where(completed.c.run_id == run_id)
    ).one()
    binding = SnapshotBinding(
        row.release_id, row.output_realization_id, row.data_revision, str(uuid4())
    )
    return ReadSession(conn, binding, load_release(conn, binding.release_id))


def coverage(ctx: QueryContext, scope: Scope):
    records = ctx.session.coverage()
    if scope.kind == "units":
        return tuple(c for c in records if c.scope in scope.unit_keys or c.scope == "*")
    if scope.kind == "documents":
        return tuple(
            c for c in records if c.scope in {str(d) for d in scope.documents} or c.scope == "*"
        )
    return records


def params_digest(params: Mapping[str, Any]) -> str:
    from corpus_structure.core.canonical import decimal_of_float

    def normalized(value: Any) -> Any:
        if isinstance(value, float):
            return {"$float": decimal_of_float(value)}
        if isinstance(value, dict):
            return {k: normalized(v) for k, v in value.items()}
        if isinstance(value, list):
            return [normalized(v) for v in value]
        return value

    return digest(normalized(dict(params)))


def encode_token(
    run_id: int,
    query: DomainQuery,
    params: Mapping[str, Any],
    position: JsonValue,
    *,
    binding: SnapshotBinding,
    projection: str,
) -> str:
    body = {
        "run": run_id,
        "query": query.name,
        "version": query.version,
        "params": params_digest(params),
        "position": position,
        "release": binding.release_id,
        "realization": binding.realization_id,
        "revision": binding.data_revision,
        "projection": projection,
        "arithmetic": "exact",
    }
    return base64.urlsafe_b64encode(canonical_json(body)).decode("ascii")


def decode_token(token: str) -> dict[str, Any]:
    try:
        body = json.loads(base64.urlsafe_b64decode(token.encode("ascii")))
    except binascii.Error, ValueError:
        raise StaleToken("not a page token") from None
    if not isinstance(body, dict) or set(body) != {
        "run",
        "query",
        "version",
        "params",
        "position",
        "release",
        "realization",
        "revision",
        "projection",
        "arithmetic",
    }:
        raise StaleToken("not a page token")
    return body


def serve_query(
    conn: Connection,
    registry: Mapping[str, DomainQuery],
    name: str,
    params: Mapping[str, Any] | None = None,
    *,
    project_id: str | None = None,
    run: int | str = PROMOTED,
    page_token: str | None = None,
    max_rows: int | None = None,
    max_chars: int | None = None,
    projection: Literal["occurrence", "fact", "accepted"] = "accepted",
) -> QueryResult:
    """One page of a query's journey (module doc)."""
    if name not in registry:
        raise QueryRefused(f"no query {name!r}")
    query = registry[name]
    p = query.params.model_validate(dict(params or {}))
    dumped: dict[str, JsonValue] = p.model_dump(mode="json")
    if projection == "accepted" and (
        getattr(p, "include_candidates", False) or getattr(p, "status", None) == "candidate"
    ):
        projection = "fact"
    position: JsonValue = None
    body: dict[str, Any] | None = None
    if page_token is not None:
        body = decode_token(page_token)
        if body["query"] != query.name:
            raise StaleToken(f"the token continues {body['query']!r}, not {query.name!r}")
        if body["version"] != query.version:
            raise StaleToken(
                f"stale token: {query.name} is version {query.version}, the token's is "
                f"{body['version']}"
            )
        if body["params"] != params_digest(dumped):
            raise StaleToken("stale token: the parameters differ from the journey's")
        try:
            run_id = check_finished(conn, int(body["run"]))
        except QueryRefused as error:
            raise StaleToken(f"stale token: {error}") from None
        position = body["position"]
    else:
        if run == PROMOTED and project_id is None:
            raise QueryRefused("a promoted run needs its project")
        run_id = (
            select_run(conn, project_id or "", run)
            if run == PROMOTED
            else check_finished(conn, int(run))
        )
    ctx = QueryContext(
        run_id,
        conn,
        row_batch=min(max_rows + 1, 64) if max_rows is not None and max_rows > 0 else 64,
        projection=projection,
    )
    binding = ctx.session.binding
    if body is not None:
        if any(
            body[k] != v
            for k, v in {
                "release": binding.release_id,
                "realization": binding.realization_id,
                "revision": binding.data_revision,
                "projection": projection,
                "arithmetic": "exact",
            }.items()
        ):
            raise StaleToken("stale token: semantic snapshot or projection differs")
    for bound in (max_rows, max_chars):
        if bound is not None and bound <= 0:
            raise QueryRefused("page bounds must be positive")
    rows: list[dict[str, JsonValue]] = []
    scope = query.scope(ctx, p)
    cov = coverage(ctx, scope)
    family = getattr(p, "predicate", None)
    if family is not None:
        cov = tuple(c for c in cov if c.family == ctx.reader.iri(family))
    complete_cov = bool(family and cov) and all(c.outcome == "complete" for c in cov)

    # Query-owned cursor: no replay or hydration of a previous page's prefix.
    def response(more: bool, cursor: JsonValue) -> QueryResult:
        return QueryResult(
            run_id=run_id,
            binding=binding,
            projection=projection,
            knowledge="observed" if rows else "absent" if complete_cov else "unknown",
            query=query.name,
            version=query.version,
            params=dumped,
            coverage=cov,
            rows=rows,
            next_page_token=encode_token(
                run_id, query, dumped, cursor, binding=binding, projection=projection
            )
            if more
            else None,
            truncated=more,
        )

    cursor = position
    iterator = query.rows(ctx, p, after=position)
    try:
        found = next(iterator, None)
        while found is not None:
            if max_rows is not None and len(rows) >= max_rows:
                return response(True, cursor)
            following = next(iterator, None)
            item = found.row.model_dump(mode="json", serialize_as_any=True)
            rows.append(item)
            # Reserve the continuation envelope too, even for a last row.
            if (
                max_chars is not None
                and len(response(following is not None, found.position).model_dump_json())
                > max_chars
            ):
                rows.pop()
                if not rows:
                    raise QueryRefused(
                        "size limit: a complete row and response envelope do not fit; raise "
                        "max_chars"
                    )
                return response(True, cursor)
            cursor = found.position
            found = following
    finally:
        close = getattr(iterator, "close", None)
        if close is not None:
            close()
    result = response(False, cursor)
    if max_chars is not None and len(result.model_dump_json()) > max_chars:
        raise QueryRefused("size limit: response envelope does not fit; raise max_chars")
    return result
