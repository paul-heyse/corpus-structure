"""The run selector, coverage, page tokens and the journey (D8 §5; D3 §8-§9; consolidation and
queries §3.9-§3.10).

**The run selector.** `run` is a run id or `promoted`, resolved once at a journey's first call from
`meta.project.promoted_run_id` ("no promoted run" without one). A run that is not `finished` is
refused ("run not finished"): a finished run's rows never change.

**Coverage** counts the scope's `propose` fates through orchestration's fate reader, as of the
run's cut: `extracted` (`done`, `empty`, `reused`), `skipped` by `SkipReason` code (a cancelled
unit under its reason), `failed`, and `unresolved` (open, or finished after the cut). A result whose
coverage is not complete carries `partial: true`; a query never fails because of it.

**Page tokens** are the URL-safe base64 of canonical JSON: run id, query name, query version, the
parameters' digest and the position. A continuation names the token, so it names the run id, never
`promoted`. A token whose query's registered version or parameter digest differs, or whose run is
no longer `finished`, is stale and refused.

`serve_query` pins the run, validates the parameters with the query's model, skips to the token's
position and fills a page up to `max_rows` rows or `max_chars` characters of row JSON, then issues
a token when rows remain.
"""

from __future__ import annotations

import base64
import binascii
import json
from collections.abc import Mapping
from typing import Any

from pydantic import JsonValue
from sqlalchemy import Connection, text, select
from corpus_structure.core.db import metadata

from corpus_structure.core.canonical import canonical_json, digest
from corpus_structure.core.vocab import TaskStatus
from corpus_structure.orchestrate import fates
from corpus_structure.serve.protocol import (
    Coverage,
    DomainQuery,
    QueryContext,
    QueryResult,
    Scope,
)

PROMOTED = "promoted"
EXTRACTED = frozenset({TaskStatus.DONE.value, TaskStatus.EMPTY.value, TaskStatus.REUSED.value})


class QueryRefused(ValueError):
    """A call `serve` refuses, with the reason the caller reads."""


class StaleToken(QueryRefused):
    """A page token that no longer continues its journey."""


# --- The run selector --------------------------------------------------------------------------


def select_run(conn: Connection, project_id: int, run: int | str = PROMOTED) -> int:
    """The run a journey is pinned to (module doc)."""
    if run == PROMOTED:
        found = conn.execute(
            text("SELECT promoted_run_id FROM meta.project WHERE id = :p"), {"p": project_id}
        ).scalar()
        if found is None:
            raise QueryRefused("no promoted run")
        run = int(found)
    return check_finished(conn, int(run))


def check_finished(conn: Connection, run_id: int) -> int:
    status = conn.execute(text("SELECT status FROM ops.run WHERE id = :r"), {"r": run_id}).scalar()
    if status is None:
        raise QueryRefused(f"no run {run_id}")
    if status != "finished":
        raise QueryRefused(f"run not finished: run {run_id} is {status}")
    return run_id


# --- Coverage ----------------------------------------------------------------------------------


def coverage(conn: Connection, run_id: int, scope: Scope) -> Coverage:
    """The scope's propose fates as of the run's cut (module doc)."""
    found = fates.fates(
        conn,
        run_id,
        documents=scope.documents if scope.kind == "documents" else None,
        unit_keys=scope.unit_keys if scope.kind == "units" else None,
    )
    extracted = failed = unresolved = 0
    skipped: dict[str, int] = {}
    for f in found:
        if f.fate in EXTRACTED:
            extracted += 1
        elif f.fate == TaskStatus.FAILED.value:
            failed += 1
        elif f.fate == fates.UNRESOLVED:
            unresolved += 1
        else:
            reason = f.reason.value if f.reason is not None else f.fate
            skipped[reason] = skipped.get(reason, 0) + 1
    e, seg, rr = (metadata.tables[n] for n in ('kb.entity', 'kb.segment', 'kb.run_rendition'))
    stmt = select(e.c.id).where(e.c.run_id == run_id, e.c.type == 'core:ExternalReference', e.c.resolved_to_id.is_(None))
    if scope.kind == 'documents':
        stmt = stmt.join(seg, seg.c.id == e.c.scope_segment_id).join(rr, (rr.c.rendition_id == seg.c.rendition_id) & (rr.c.run_id == run_id)).where(rr.c.document_id.in_(scope.documents))
    elif scope.kind == 'units':
        # Fate keys correspond to unit anchors; offsets locate references within those units.
        task = metadata.tables['ops.task']
        unit = seg.alias('coverage_unit')
        stmt = stmt.join(seg, seg.c.id == e.c.scope_segment_id).join(unit, (unit.c.rendition_id == seg.c.rendition_id) & (unit.c.start_offset <= seg.c.start_offset) & (unit.c.end_offset >= seg.c.end_offset)).where(unit.c.id.in_(select(task.c.unit_id).where(task.c.run_id == run_id, task.c.stage == 'propose', task.c.unit_key.in_(scope.unit_keys)))).distinct()
    unresolved_references = len(list(conn.execute(stmt).scalars()))
    return Coverage(
        unresolved_references=unresolved_references,
        scope=scope.kind,
        eligible=len(found),
        extracted=extracted,
        skipped=dict(sorted(skipped.items())),
        failed=failed,
        unresolved=unresolved,
        partial=bool(skipped or failed or unresolved or unresolved_references),
    )


# --- Page tokens -------------------------------------------------------------------------------


def params_digest(params: Mapping[str, Any]) -> str:
    from corpus_structure.core.canonical import decimal_of_float
    def normalized(value: Any) -> Any:
        if isinstance(value, float):
            return {'$float': decimal_of_float(value)}
        if isinstance(value, dict):
            return {k: normalized(v) for k, v in value.items()}
        if isinstance(value, list):
            return [normalized(v) for v in value]
        return value
    return digest(normalized(dict(params)))


def encode_token(run_id: int, query: DomainQuery, params: Mapping[str, Any], position: JsonValue) -> str:
    body = {
        "run": run_id,
        "query": query.name,
        "version": query.version,
        "params": params_digest(params),
        "position": position,
    }
    return base64.urlsafe_b64encode(canonical_json(body)).decode("ascii")


def decode_token(token: str) -> dict[str, Any]:
    try:
        body = json.loads(base64.urlsafe_b64decode(token.encode("ascii")))
    except binascii.Error, ValueError, UnicodeEncodeError:
        raise StaleToken("not a page token") from None
    if not isinstance(body, dict) or set(body) != {"run", "query", "version", "params", "position"}:
        raise StaleToken("not a page token")
    return body


# --- The journey -------------------------------------------------------------------------------


def serve_query(
    conn: Connection,
    registry: Mapping[str, DomainQuery],
    name: str,
    params: Mapping[str, Any] | None = None,
    *,
    project_id: int | None = None,
    run: int | str = PROMOTED,
    page_token: str | None = None,
    max_rows: int | None = None,
    max_chars: int | None = None,
) -> QueryResult:
    """One page of a query's journey (module doc)."""
    if name not in registry:
        raise QueryRefused(f"no query {name!r}")
    query = registry[name]
    p = query.params.model_validate(dict(params or {}))
    dumped: dict[str, JsonValue] = p.model_dump(mode="json")
    position: JsonValue = None
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
            select_run(conn, project_id or 0, run)
            if run == PROMOTED
            else check_finished(conn, int(run))
        )
    ctx = QueryContext(run_id, conn, row_batch=min(max_rows + 1,64) if max_rows is not None and max_rows > 0 else 64)
    for bound in (max_rows, max_chars):
        if bound is not None and bound <= 0:
            raise QueryRefused("page bounds must be positive")
    rows: list[dict[str, JsonValue]] = []
    scope = query.scope(ctx, p)
    cov = coverage(conn, run_id, scope)
    # Query-owned cursor: no replay or hydration of a previous page's prefix.
    def response(more: bool, cursor: JsonValue) -> QueryResult:
        return QueryResult(run_id=run_id, query=query.name, version=query.version,
            params=dumped, coverage=cov, rows=rows,
            next_page_token=encode_token(run_id, query, dumped, cursor) if more else None,
            truncated=more)
    cursor = position
    iterator = query.rows(ctx, p, after=position)
    try:
        found = next(iterator, None)
        while found is not None:
            following = next(iterator, None)
            if max_rows is not None and len(rows) >= max_rows:
                return response(True, cursor)
            item = found.row.model_dump(mode="json")
            rows.append(item)
            # Reserve the continuation envelope too, even for a last row.
            candidate = response(following is not None, found.position)
            if max_chars is not None and len(candidate.model_dump_json()) > max_chars:
                rows.pop()
                if not rows:
                    raise QueryRefused("size limit: a complete row and response envelope do not fit; raise max_chars")
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
