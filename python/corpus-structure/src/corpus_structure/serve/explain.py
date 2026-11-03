"""Fact explanations and unit source-custody snapshots from the completed final cut."""

from __future__ import annotations

import base64
import json
from dataclasses import asdict
from typing import Literal

from pydantic import BaseModel, ConfigDict, JsonValue
from sqlalchemy import and_, select

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.query import AnswerSelection, ReadLimit, SnapshotBinding
from corpus_structure.semantic.query import Explanation as FactExplanation
from corpus_structure.semantic.query_compatibility import (
    BoundQuery,
    QueryBindingReference,
    QueryCompatibilityError,
)
from corpus_structure.semantic.refusals import InvalidContinuation, WrongBinding
from corpus_structure.serve.journey import QueryRefused, bind_session


class UnitTask(BaseModel):
    task_id: int
    origin_task_id: int | None
    method: str
    operation_version: str
    input_hash: str
    included_in_cut: bool
    source_result_available: bool


class UnitExplanation(BaseModel):
    cut_id: int
    unit_key: str
    tasks: tuple[UnitTask, ...]
    observations: tuple[dict[str, JsonValue], ...]
    population_complete: bool
    next_page_token: str | None = None


class Explanation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    contract_version: Literal[2] = 2
    cut_id: int | None = None
    run_id: int
    binding: SnapshotBinding
    kind: Literal["claim", "unit"]
    identifier: str
    detail: FactExplanation | UnitExplanation
    query_binding: QueryBindingReference | None = None
    selection: AnswerSelection | None = None


def explain(
    conn,
    run_id,
    kind: Literal["claim", "unit"],
    key,
    *,
    query: BoundQuery | None = None,
    continuation=None,
    limit=64,
    max_bytes=1024 * 1024,
    selection=None,
):
    if (
        type(limit) is not int
        or not 1 <= limit <= 1000
        or type(max_bytes) is not int
        or not 1 <= max_bytes <= 8 * 1024 * 1024
    ):
        raise QueryRefused("unsupported explanation page bounds")
    session = bind_session(conn, run_id)
    session._detail_selection(selection)
    if query is not None and query.release_id != session.binding.release_id:
        raise QueryCompatibilityError("explanation belongs to another producing query release")
    if kind == "claim":
        try:
            if continuation is not None:
                raise InvalidContinuation(
                    "claim explanations page their named inventory collections"
                )
            detail = session.explain(
                key,
                limit=limit,
                max_bytes=max_bytes,
                query_binding=query.reference if query is not None else None,
                selection=selection,
            )
        except KeyError:
            raise QueryRefused(f"no semantic fact {key}") from None
    else:
        completed, t, ct, result, config, method, observation = (
            table(n)
            for n in (
                "ops.completed_result",
                "ops.task",
                "ops.cut_task",
                "ops.task_result",
                "ops.method_config",
                "ops.method",
                "kb.observation",
            )
        )
        cut = conn.execute(
            select(completed.c.cut_id).where(completed.c.run_id == run_id)
        ).scalar_one()
        identity = {
            "version": 2,
            "run": run_id,
            "unit": key,
            "binding": {k: v for k, v in asdict(session.binding).items() if k != "capture_id"},
            "query_binding": query.reference.model_dump(mode="json") if query is not None else None,
            "selection": session._detail_selection(selection),
            "limit": limit,
            "max_bytes": max_bytes,
        }
        task_after, observation_after = 0, ""
        if continuation is not None:
            try:
                if len(continuation.encode("utf-8")) > 8192:
                    raise ValueError("oversized token")
                body = json.loads(base64.b64decode(continuation, altchars=b"-_", validate=True))
                if (
                    set(body) != {*identity, "task_after", "observation_after"}
                    or type(body["task_after"]) is not int
                    or not isinstance(body["observation_after"], str)
                ):
                    raise ValueError("invalid unit cursor")
                if canonical_bytes({k: body[k] for k in identity}) != canonical_bytes(identity):
                    raise WrongBinding("unit continuation differs from the requested binding")
                task_after, observation_after = body["task_after"], body["observation_after"]
            except (ValueError, TypeError) as error:
                if isinstance(error, WrongBinding):
                    raise
                raise InvalidContinuation("invalid unit continuation") from error
        rows = (
            conn.execute(
                select(
                    t.c.id,
                    t.c.input_hash,
                    ct.c.origin_task_id,
                    method.c.name,
                    method.c.version,
                    result.c.task_id.label("result_task_id"),
                )
                .select_from(
                    t.join(config, t.c.method_config_id == config.c.id)
                    .join(method, config.c.method_id == method.c.id)
                    .outerjoin(ct, and_(ct.c.task_id == t.c.id, ct.c.cut_id == cut))
                    .outerjoin(result, result.c.task_id == ct.c.origin_task_id)
                )
                .where(t.c.run_id == run_id, t.c.unit_key == key, t.c.id > task_after)
                .order_by(t.c.id)
                .limit(limit + 1)
            )
            .mappings()
            .all()
        )
        if not rows and continuation is None:
            raise QueryRefused(f"no source unit {key}")
        task_more, rows = len(rows) > limit, rows[:limit]
        origins = (
            select(ct.c.origin_task_id)
            .join(t, t.c.id == ct.c.task_id)
            .where(ct.c.cut_id == cut, t.c.run_id == run_id, t.c.unit_key == key)
        )
        observation_rows = (
            conn.execute(
                select(
                    observation.c.id,
                    observation.c.observation_key,
                    observation.c.task_id,
                    observation.c.kind,
                )
                .where(
                    observation.c.task_id.in_(origins),
                    observation.c.observation_key.collate("C") > observation_after,
                )
                .order_by(observation.c.observation_key.collate("C"))
                .limit(limit + 1)
            )
            .mappings()
            .all()
        )
        observation_more = len(observation_rows) > limit
        observations = tuple(
            {
                "observation_id": r["id"],
                "observation_key": r["observation_key"],
                "task_id": r["task_id"],
                "kind": r["kind"],
            }
            for r in observation_rows[:limit]
        )
        more = task_more or observation_more
        token = None
        if more:
            token = base64.urlsafe_b64encode(
                canonical_bytes(
                    {
                        **identity,
                        "task_after": rows[-1]["id"] if rows else task_after,
                        "observation_after": observations[-1]["observation_key"]
                        if observations
                        else observation_after,
                    }
                )
            ).decode("ascii")
            if len(token.encode("ascii")) > 8192:
                raise ReadLimit("unit cursor exceeds 8192 bytes", reason="oversized_item")

        detail = UnitExplanation(
            cut_id=cut,
            unit_key=key,
            tasks=tuple(
                UnitTask(
                    task_id=row["id"],
                    origin_task_id=row["origin_task_id"],
                    method=row["name"],
                    operation_version=row["version"],
                    input_hash=row["input_hash"],
                    included_in_cut=row["origin_task_id"] is not None,
                    source_result_available=row["result_task_id"] is not None,
                )
                for row in rows
            ),
            observations=observations,
            population_complete=not more,
            next_page_token=token,
        )
    response = Explanation(
        run_id=run_id,
        cut_id=session.completed_cut_id,
        binding=session.binding,
        kind=kind,
        identifier=key,
        detail=detail,
        query_binding=query.reference if query is not None else None,
        selection=selection,
    )
    if len(canonical_bytes(response.model_dump(mode="json"))) > max_bytes:
        raise ReadLimit("complete explanation envelope exceeds max_bytes", reason="oversized_item")
    return response


class UnitSourceReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    binding: SnapshotBinding
    query_binding: QueryBindingReference | None = None
    selection: AnswerSelection | None = None
    run_id: int
    cut_id: int | None = None
    unit_key: str
    collection: Literal["observation", "task_result"]
    identifier: str
    payload: dict[str, JsonValue]


def unit_source_report(
    conn,
    run_id,
    unit_key,
    collection,
    identifier,
    *,
    max_bytes=1024 * 1024,
    query=None,
    selection=None,
):
    """Read a body only through its immutable unit/completed-cut membership."""
    from sqlalchemy import Text, func

    if type(max_bytes) is not int or not 1 <= max_bytes <= 8 * 1024 * 1024:
        raise QueryRefused("unsupported source report byte bound")
    session = bind_session(conn, run_id)
    session._detail_selection(selection)
    if query is not None and query.release_id != session.binding.release_id:
        raise WrongBinding("source report belongs to another producing query release")
    completed, task, ct = (
        table(name) for name in ("ops.completed_result", "ops.task", "ops.cut_task")
    )
    origins = (
        select(ct.c.origin_task_id)
        .join(task, ct.c.task_id == task.c.id)
        .join(completed, completed.c.cut_id == ct.c.cut_id)
        .where(completed.c.run_id == run_id, task.c.run_id == run_id, task.c.unit_key == unit_key)
    )
    if collection == "observation":
        relation = table("kb.observation")
        identity = relation.c.observation_key == identifier
        scope = relation.c.task_id.in_(origins)
        payload = relation.c.payload
    elif collection == "task_result":
        relation = table("ops.task_result")
        try:
            task_id = int(identifier)
        except ValueError, TypeError:
            raise QueryRefused("task result identity must be an integer") from None
        identity, scope, payload = (
            relation.c.task_id == task_id,
            relation.c.task_id.in_(origins),
            relation.c.body,
        )
    else:
        raise QueryRefused("unsupported source report collection")
    # Refuse before transferring a body beyond the admitted physical JSON bound.
    stmt = select(payload).where(scope, identity)
    row = conn.execute(stmt.where(func.octet_length(payload.cast(Text)) <= max_bytes * 2)).first()
    if row is None:
        if conn.execute(select(1).select_from(relation).where(scope, identity)).first() is not None:
            raise ReadLimit("source report exceeds max_bytes", reason="oversized_item")
        raise WrongBinding("source report is unavailable under this unit and completed cut")
    result = UnitSourceReport(
        binding=session.binding,
        run_id=run_id,
        unit_key=unit_key,
        cut_id=session.completed_cut_id,
        query_binding=query.reference if query is not None else None,
        selection=selection,
        collection=collection,
        identifier=str(identifier),
        payload=row[0],
    )
    if len(canonical_bytes(result.model_dump(mode="json"))) > max_bytes:
        raise ReadLimit(
            "complete source report envelope exceeds max_bytes", reason="oversized_item"
        )
    return result
