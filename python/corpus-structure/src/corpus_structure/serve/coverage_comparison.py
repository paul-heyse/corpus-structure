"""Pinned comparison of declared PM2 scopes; no assessment or quality inference."""

from __future__ import annotations

import base64
import json
from collections import defaultdict
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.pm2_coverage import (
    ScopeCoverage,
    completed_scope_worklist,
    derive_scope_coverage,
)
from corpus_structure.semantic.query import SnapshotBinding, bind_completed_result
from corpus_structure.semantic.refusals import InvalidContinuation, SemanticRefusal
from corpus_structure.serve.journey import params_digest


class CoveragePin(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    run_id: int = Field(strict=True, gt=0)
    cut_id: int = Field(strict=True, gt=0)
    release_id: str = Field(min_length=1)


class CoverageComparisonRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    left: CoveragePin
    right: CoveragePin
    source_view_id: int | None = Field(default=None, strict=True, gt=0)
    question: str | None = None
    operation_version: str | None = None
    cursor: str | None = None
    limit: int = Field(default=100, strict=True, ge=1, le=1000)
    max_bytes: int = Field(default=8_000_000, strict=True, ge=1, le=134_217_728)
    page_bytes: int = Field(default=1_000_000, strict=True, ge=1, le=32_000_000)


class TaskBinding(BaseModel):
    id: int
    method_config_id: int


class CoverageContext(CoveragePin):
    binding: SnapshotBinding
    runtime_id: str | None
    task_bindings: list[TaskBinding]


class SourceBinding(BaseModel):
    id: int
    key: str
    release_id: str
    native_task_id: int
    native_product_key: str
    native_content_digest: str
    native_revision_id: str
    section_pointer: str
    membership: str
    projection_digest: str
    recipe_digest: str


class CoverageScopeRow(BaseModel):
    source_view_id: int
    extent: tuple[int, int]
    question: str
    operation_version: str
    standing: Literal["matched", "left_only", "right_only", "incomparable", "ambiguous"]
    reason: str | None
    left: list[ScopeCoverage]
    right: list[ScopeCoverage]


class CoverageSelection(BaseModel):
    left: CoveragePin
    right: CoveragePin
    source_view_id: int | None
    question: str | None
    operation_version: str | None


class CoverageComparison(BaseModel):
    version: Literal["coverage-comparison-1"] = "coverage-comparison-1"
    left: CoverageContext
    right: CoverageContext
    selection: CoverageSelection
    rows: list[CoverageScopeRow]
    selected_count: int
    source_bindings: list[SourceBinding]
    population_paging_complete: bool
    next_cursor: str | None = None
    assessment: Literal["not_included"] = "not_included"


def compare_scope_rows(left, right, *, same_release) -> list[CoverageScopeRow]:
    """Exact versioned keys pair first; changed versions remain incomparable."""
    sides = []
    for rows in (left, right):
        grouped = defaultdict(list)
        for row in rows:
            grouped[(row.source_view_id, row.extent, row.question, row.operation_version)].append(
                row
            )
        sides.append(grouped)
    result = []
    for key in sorted(sides[0].keys() | sides[1].keys()):
        left_rows, right_rows = sides[0].get(key, []), sides[1].get(key, [])
        if not same_release:
            standing, reason = "incomparable", "semantic_release_differs"
        elif len(left_rows) > 1 or len(right_rows) > 1:
            standing, reason = "ambiguous", "multiple_declared_scopes"
        elif not (left_rows and right_rows) and (
            (left_rows and any(other[:3] == key[:3] for other in sides[1]))
            or (right_rows and any(other[:3] == key[:3] for other in sides[0]))
        ):
            standing, reason = "incomparable", "operation_version_differs"
        else:
            if left_rows and right_rows:
                standing = "matched"
            elif left_rows:
                standing = "left_only"
            else:
                standing = "right_only"
            reason = None
        result.append(
            CoverageScopeRow.model_validate(
                dict(
                    source_view_id=key[0],
                    extent=key[1],
                    question=key[2],
                    operation_version=key[3],
                    standing=standing,
                    reason=reason,
                    left=left_rows,
                    right=right_rows,
                )
            )
        )
    return result


def compare_coverage(conn, request: CoverageComparisonRequest) -> CoverageComparison:
    contexts: list[CoverageContext] = []
    coverage = []
    for pin in (request.left, request.right):
        bound = bind_completed_result(conn, pin.run_id)
        if bound.completed_cut_id != pin.cut_id or bound.binding.release_id != pin.release_id:
            raise SemanticRefusal("coverage comparison pin differs from completed result")
        worklist = completed_scope_worklist(
            conn,
            **pin.model_dump(),
            source_view_id=request.source_view_id,
            question=request.question,
            operation_version=request.operation_version,
        )
        coverage.append(derive_scope_coverage(worklist, completed=True))
        run_table, task_table = table("ops.run"), table("ops.task")
        runtime_id = conn.scalar(select(run_table.c.runtime_id).where(run_table.c.id == pin.run_id))
        task_ids = [row.task_id for row in coverage[-1] if row.task_id is not None]
        task_bindings = (
            [
                dict(row)
                for row in conn.execute(
                    select(task_table.c.id, task_table.c.method_config_id)
                    .where(task_table.c.run_id == pin.run_id, task_table.c.id.in_(task_ids))
                    .order_by(task_table.c.id)
                ).mappings()
            ]
            if task_ids
            else []
        )
        contexts.append(
            CoverageContext.model_validate(
                dict(
                    **pin.model_dump(),
                    binding=bound.binding,
                    runtime_id=runtime_id,
                    task_bindings=task_bindings,
                )
            )
        )
    selection = request.model_dump(
        mode="json", exclude={"cursor", "limit", "max_bytes", "page_bytes"}
    )
    identity = params_digest(
        dict(
            version="coverage-comparison-1",
            # A capture labels this observation; it is not part of the immutable result pin.
            contexts=[
                x.model_dump(mode="json", exclude={"binding": {"capture_id"}}) for x in contexts
            ],
            selection=selection,
        )
    )
    offset = 0
    if request.cursor:
        try:
            token = json.loads(base64.b64decode(request.cursor, altchars=b"-_", validate=True))
            if (
                set(token) != {"query", "after"}
                or token["query"] != identity
                or type(token["after"]) is not int
                or token["after"] < 0
            ):
                raise ValueError("wrong continuation binding")
            offset = token["after"]
        except (ValueError, TypeError) as error:
            raise InvalidContinuation("invalid coverage comparison continuation") from error
    rows = compare_scope_rows(
        *coverage, same_release=request.left.release_id == request.right.release_id
    )
    if offset > len(rows):
        raise InvalidContinuation("coverage comparison continuation outside population")
    source = table("kb.source_view")
    source_ids = sorted({row.source_view_id for row in rows})
    sources = (
        [
            dict(row)
            for row in conn.execute(
                select(
                    source.c.id,
                    source.c.key,
                    source.c.release_id,
                    source.c.native_task_id,
                    source.c.native_product_key,
                    source.c.native_content_digest,
                    source.c.native_revision_id,
                    source.c.section_pointer,
                    source.c.membership,
                    source.c.projection_digest,
                    source.c.recipe_digest,
                )
                .where(source.c.id.in_(source_ids))
                .order_by(source.c.id)
            ).mappings()
        ]
        if source_ids
        else []
    )
    if (
        len(
            canonical_bytes(
                dict(
                    rows=[row.model_dump(mode="json") for row in rows],
                    sources=sources,
                    contexts=[x.model_dump(mode="json") for x in contexts],
                )
            )
        )
        > request.max_bytes
    ):
        raise SemanticRefusal("coverage comparison exceeds selected byte bound")
    end = min(offset + request.limit, len(rows))
    cursor = (
        base64.urlsafe_b64encode(canonical_bytes(dict(query=identity, after=end))).decode()
        if end < len(rows)
        else None
    )
    result = CoverageComparison(
        left=contexts[0],
        right=contexts[1],
        selection=CoverageSelection.model_validate(selection),
        rows=rows[offset:end],
        source_bindings=[SourceBinding.model_validate(x) for x in sources],
        selected_count=len(rows),
        population_paging_complete=cursor is None,
        next_cursor=cursor,
    )
    if len(result.model_dump_json().encode()) > request.page_bytes:
        raise SemanticRefusal("coverage comparison exceeds page byte bound; narrow selection")
    return result
