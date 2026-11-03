"""Completed-result selection, semantic snapshot binding and stable named-query paging."""

from __future__ import annotations

import base64
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import JsonValue
from sqlalchemy import Connection, select

from corpus_structure.core.canonical import canonical_json, digest
from corpus_structure.semantic.continuations import decode_continuation, validate_continuation
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.query import (
    AnswerSelection,
    Coverage,
    ReadLimit,
    ReadSession,
    SnapshotBinding,
    bind_completed_result,
)
from corpus_structure.semantic.query_compatibility import (
    BoundQuery,
    QueryCompatibilityError,
    validate_query_token,
)
from corpus_structure.semantic.refusals import (
    InvalidContinuation,
    SemanticRefusal,
    StaleSnapshot,
    WrongBinding,
)
from corpus_structure.serve.protocol import QueryContext, QueryResult

PROMOTED = "promoted"


class QueryRefused(SemanticRefusal):
    """A query that cannot name an authoritative completed result."""


class StaleToken(InvalidContinuation):
    pass


def parse_run(value: int | str) -> int:
    try:
        if isinstance(value, bool):
            raise ValueError("boolean run selector")
        return int(value)
    except (TypeError, ValueError) as error:
        raise QueryRefused("run selector must name a completed integer run") from error


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
    run_id = check_finished(conn, parse_run(run))
    r = table("ops.run")
    if (
        project_id
        and conn.execute(select(r.c.project_id).where(r.c.id == run_id)).scalar_one() != project_id
    ):
        raise QueryRefused("run belongs to another project")
    return run_id


def bind_session(conn: Connection, run_id: int) -> ReadSession:
    try:
        return bind_completed_result(conn, run_id)
    except WrongBinding, StaleSnapshot, InvalidContinuation:
        raise
    except SemanticRefusal as error:
        raise QueryRefused(str(error)) from error


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
    query: BoundQuery,
    params: Mapping[str, Any],
    position: JsonValue,
    *,
    binding: SnapshotBinding,
    projection: str,
) -> str:
    body = {
        "token_version": 2,
        "query_contract": query.contract,
        "implementation": query.implementation,
        "compatibility": query.compatibility,
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
    token = base64.urlsafe_b64encode(canonical_json(body)).decode("ascii")
    if len(token.encode("ascii")) > 8192:
        raise ReadLimit("continuation exceeds 8192 encoded bytes", reason="oversized_item")
    return token


def decode_token(token: str) -> dict[str, Any]:
    if len(token.encode("utf-8")) > 8192:
        raise InvalidContinuation("continuation exceeds 8192 encoded bytes")
    return decode_continuation(token, kind="named")


def serve_query(
    conn: Connection,
    registry: Mapping[str, BoundQuery],
    name: str,
    params: Mapping[str, Any] | None = None,
    *,
    project_id: str | None = None,
    run: int | str = PROMOTED,
    page_token: str | None = None,
    max_rows: int | None = None,
    max_chars: int | None = None,
    max_bytes: int = 1024 * 1024,
    projection: Literal["occurrence", "fact", "accepted"] = "accepted",
    origin_query: BoundQuery | None = None,
) -> QueryResult:
    """One page of a query's journey (module doc)."""
    if name not in registry:
        raise QueryRefused(f"no query {name!r}")
    query = registry[name]
    if not isinstance(query, BoundQuery):
        raise QueryCompatibilityError(
            "named query requires its release-bound registry", reason="unavailable_query"
        )
    position: JsonValue = None
    body: dict[str, Any] | None = None
    if page_token is not None:
        body = decode_token(page_token)
        try:
            run_id = check_finished(conn, parse_run(body["run"]))
        except QueryRefused as error:
            raise StaleSnapshot(
                f"continuation result is unavailable: {error}", reason="unavailable_result"
            ) from error
        position = body["position"]
    else:
        if run == PROMOTED and project_id is None:
            raise QueryRefused("a promoted run needs its project")
        run_id = (
            select_run(conn, project_id or "", run)
            if run == PROMOTED
            else check_finished(conn, parse_run(run))
        )
    if max_rows is None:
        max_rows = 100
    if type(max_rows) is not int or not 1 <= max_rows <= 1000:
        raise QueryRefused("max_rows must be between 1 and 1000")
    if type(max_bytes) is not int or not 1 <= max_bytes <= 8 * 1024 * 1024:
        raise QueryRefused("max_bytes must be between 1 and 8388608")
    ctx = QueryContext(
        run_id,
        conn,
        row_batch=min(max_rows + 1, 64) if max_rows is not None and max_rows > 0 else 64,
        projection=projection,
        query_binding=query.reference,
    )
    binding = ctx.session.binding
    if query.release_id != binding.release_id:
        raise QueryCompatibilityError("query registry belongs to another producing release")
    if origin_query is not None and origin_query.release_id != binding.release_id:
        raise QueryCompatibilityError("follow-up query belongs to another producing release")
    p = query.params.model_validate(dict(params or {}))
    dumped: dict[str, JsonValue] = p.model_dump(mode="json")
    if projection == "accepted" and (
        getattr(p, "include_candidates", False) or getattr(p, "status", None) == "candidate"
    ):
        projection = "fact"
        ctx.projection = projection
    ctx.answer_selection = AnswerSelection(
        parameter_digest=params_digest(dumped), projection=projection
    )
    if body is not None:
        validate_query_token(query, body)
        validate_continuation(
            ctx.session.prepared,
            body,
            {
                "release": binding.release_id,
                "realization": binding.realization_id,
                "query": query.name,
                "params": params_digest(dumped),
                "projection": projection,
                "arithmetic": "exact",
                "revision": binding.data_revision,
                "version": query.version,
                **({"run": parse_run(run)} if run != PROMOTED else {}),
            },
        )
        validate_position = getattr(query, "validate_position", None)
        if validate_position is not None:
            validate_position(position)
    for bound in (max_rows, max_chars):
        if bound is not None and bound <= 0:
            raise QueryRefused("page bounds must be positive")
    rows: list[dict[str, JsonValue]] = []
    scope = query.scope(ctx, p)
    family = getattr(p, "predicate", None)
    requirement = None
    if family is not None:
        members = scope.unit_keys if scope.kind == "units" else scope.documents
        requirement = ctx.session.required_coverage(
            run_id, ctx.reader.iri(family), scope.kind, members
        )
    summary = ctx.session.coverage_summary(requirement)
    complete_cov = summary.state == "established"
    coverage_diagnostic = summary.diagnostic
    coverage_detail = (
        None
        if requirement is None
        else ctx.session.coverage_details(
            requirement.family,
            requirement.members | {"*"},
            limit=64,
            max_bytes=max_bytes,
            query_binding=query.reference,
            selection=ctx.answer_selection,
        )
    )
    cov = () if coverage_detail is None else tuple(Coverage(**row) for row in coverage_detail.items)
    coverage_more = coverage_detail is not None and not coverage_detail.population_complete

    # Query-owned cursor: bounded walks deliberately replay under their own work bounds.
    def response(more: bool, cursor: JsonValue, *, with_rows: bool = True) -> QueryResult:
        return QueryResult(
            run_id=run_id,
            cut_id=ctx.session.completed_cut_id,
            binding=binding,
            projection=projection,
            knowledge=(
                "observed" if rows else "absent" if complete_cov and position is None else "unknown"
            ),
            query=query.name,
            version=query.version,
            query_contract=query.contract,
            producing_implementation=query.producing_implementation,
            implementation=query.implementation,
            compatibility=query.compatibility,
            origin_binding=origin_query.reference if origin_query is not None else None,
            params=dumped,
            coverage=cov,
            coverage_summary=summary,
            coverage_detail=coverage_detail,
            coverage_population_complete=not coverage_more,
            coverage_diagnostic=coverage_diagnostic,
            rows=rows if with_rows else [],
            next_page_token=encode_token(
                run_id, query, dumped, cursor, binding=binding, projection=projection
            )
            if more
            else None,
            truncated=more,
        )

    cursor = position
    iterator = query.rows(ctx, p, after=position)
    encoded_rows = 0
    try:
        found = next(iterator, None)
        while found is not None:
            if len(rows) >= max_rows:
                result = response(True, cursor)
                if len(canonical_bytes(result.model_dump(mode="json"))) > max_bytes:
                    raise ReadLimit("complete response exceeds max_bytes", reason="oversized_item")
                return result
            following = next(iterator, None)
            admitted = query.result.model_validate(dict(found.row))
            item = admitted.model_dump(mode="json", serialize_as_any=True)
            item_bytes = len(canonical_bytes(item))
            if item_bytes > max_bytes:
                raise ReadLimit("a complete row exceeds max_bytes", reason="oversized_item")
            rows.append(item)
            encoded_rows += item_bytes
            # Encode rows once; only the small envelope is remeasured for admission.
            envelope = response(following is not None, found.position, with_rows=False).model_dump(
                mode="json"
            )
            byte_size = len(canonical_bytes(envelope)) + encoded_rows + max(0, len(rows) - 1)
            chars_over = (
                max_chars is not None
                and len(response(following is not None, found.position).model_dump_json())
                > max_chars
            )
            if byte_size > max_bytes or chars_over:
                rows.pop()
                encoded_rows -= item_bytes
                if not rows:
                    if chars_over:
                        raise QueryRefused(
                            "size limit: a complete row and response envelope do not fit; "
                            "raise max_chars"
                        )
                    raise ReadLimit(
                        "a complete row and response envelope exceed the requested size",
                        reason="oversized_item",
                    )
                result = response(True, cursor)
                if len(canonical_bytes(result.model_dump(mode="json"))) > max_bytes:
                    raise ReadLimit("complete response exceeds max_bytes", reason="oversized_item")
                return result
            cursor = found.position
            found = following
    finally:
        close = getattr(iterator, "close", None)
        if close is not None:
            close()
    result = response(False, cursor)
    if len(canonical_bytes(result.model_dump(mode="json"))) > max_bytes:
        raise ReadLimit("complete response exceeds max_bytes", reason="oversized_item")
    if max_chars is not None and len(result.model_dump_json()) > max_chars:
        raise QueryRefused("size limit: response envelope does not fit; raise max_chars")
    return result
