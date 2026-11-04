"""Bounded detached record reads from one immutable completed result.

Serving supplies its existing read-only snapshot. The protected evaluator may use its
own transaction: completed results and their realization are immutable, and no selected
project pointer is consulted. The byte budget covers canonical JSON of the detached
rows and report-to-view map, including collection framing; it does not bound process
RSS or the archived prepared release.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields
from functools import cached_property
from types import MappingProxyType
from typing import Any

from pydantic import TypeAdapter
from sqlalchemy import Connection, func, select, tuple_

from .identity import canonical_bytes
from .metadata import table
from .query import SnapshotBinding, StaleSnapshot, WrongRelease
from .record_projection import (
    ARTIFACT,
    RECORD_ROW_TYPES,
    PreparedRecordProjection,
    RecordProjectionRows,
    index_record_projection,
    read_record_projection,
)
from .refusals import SemanticRefusal
from .releases import open_release
from .types import PreparedRelease

_PROJECTION_ROWS: TypeAdapter[RecordProjectionRows] = TypeAdapter(RecordProjectionRows)


class RecordReadLimit(SemanticRefusal):
    """The requested projection exceeds its explicit returned-data budget."""


@dataclass(frozen=True)
class RecordReadSelection:
    """Root selection before hydration; reports retain the separate source scope."""

    family: str | None = None
    standing: str | None = None
    record_id: str | None = None
    interpretation_id: str | None = None
    after: tuple[str, str] | None = None
    limit: int = 20


@dataclass(frozen=True)
class CompletedRecordProjection:
    run_id: int
    release_id: str
    realization_id: str
    data_revision: int
    cut_id: int
    projection_digest: str
    prepared: PreparedRelease
    rows: RecordProjectionRows
    source_view_ids: tuple[int, ...] | None
    report_source_view_ids: Mapping[int, int]
    selection: RecordReadSelection | None = None
    matching_records: int | None = None
    more_records: bool = False

    @cached_property
    def record_index(self) -> PreparedRecordProjection:
        return index_record_projection(self.rows)

    @property
    def binding(self) -> SnapshotBinding:
        return SnapshotBinding(
            self.release_id, self.realization_id, self.data_revision, f"cut:{self.cut_id}"
        )


def read_completed_record_projection(
    conn: Connection,
    *,
    run_id: int,
    project_id: str | None = None,
    source_view_ids: tuple[int, ...] | None = None,
    max_records: int = 10_000,
    max_rows: int = 100_000,
    max_bytes: int = 32 * 1024 * 1024,
    selection: RecordReadSelection | None = None,
) -> CompletedRecordProjection:
    """Read finite public rows, including report absence/empty and admission standing.

    One set-shaped query per relation uses the same primary record/report scope. There
    are no producer-envelope or per-record hydration reads. A limit refuses the whole
    result; it never returns a truncated collection as an evaluated denominator.
    """
    for value in (run_id, max_records, max_rows, max_bytes):
        if type(value) is not int or value < 1:
            raise ValueError("record read identities and budgets require positive integers")
    if selection is not None:
        if type(selection) is not RecordReadSelection:
            raise ValueError("record selection requires its typed reader contract")
        if type(selection.limit) is not int or not 1 <= selection.limit <= 10_000:
            raise ValueError("record selection limit requires a positive bounded integer")
        if any(
            value is not None and (type(value) is not str or not value)
            for value in (
                selection.family,
                selection.standing,
                selection.record_id,
                selection.interpretation_id,
            )
        ):
            raise ValueError("record selection filters require nonempty strings")
        if selection.interpretation_id is not None and selection.record_id is None:
            raise ValueError("an interpretation selector requires its record identity")
        if selection.after is not None and (
            type(selection.after) is not tuple
            or len(selection.after) != 2
            or any(type(value) is not str or not value for value in selection.after)
        ):
            raise ValueError("record continuation requires a pair of nonempty identities")
    if source_view_ids is not None:
        if any(type(value) is not int or value < 1 for value in source_view_ids):
            raise ValueError("record source-view selectors require positive integer identities")
        if len(set(source_view_ids)) != len(source_view_ids):
            raise ValueError("duplicate record source-view selector")
        source_view_ids = tuple(sorted(source_view_ids))
    completed, run, realization = (
        table("ops.completed_result"),
        table("ops.run"),
        table("data.realization"),
    )
    statement = (
        select(completed, realization.c.data_revision, run.c.project_id, run.c.status)
        .join(run, run.c.id == completed.c.run_id)
        .join(
            realization,
            (realization.c.release_id == completed.c.release_id)
            & (realization.c.realization_id == completed.c.output_realization_id),
        )
        .where(completed.c.run_id == run_id)
    )
    selected = conn.execute(statement).mappings().one_or_none()
    if selected is None or (project_id is not None and selected["project_id"] != project_id):
        raise SemanticRefusal(
            "record result does not belong to the requested completed run/project"
        )
    if selected["status"] != "finished":
        raise SemanticRefusal("record projection requires an immutable completed result")
    release_id, realization_id = selected["release_id"], selected["output_realization_id"]
    prepared = open_release(conn, release_id)
    try:
        # Read archived meaning; never compile installed declarations.
        released = read_record_projection(prepared)
    except ValueError as exc:
        raise SemanticRefusal("completed release has no supported record projection") from exc
    from .contracts import require_bound_operation

    require_bound_operation(prepared, "read_source_records")
    if selection is not None:
        if selection.family is not None and selection.family not in {
            row["family"] for row in released["families"]
        }:
            raise SemanticRefusal("record family is not declared by the completed release")
        if selection.standing is not None and selection.standing not in prepared.enum_members(
            "RecordStanding"
        ):
            raise SemanticRefusal("record standing is not declared by the completed release")
    artifact = next(a for a in prepared.artifacts if a.kind == ARTIFACT)
    reports, members, tasks = (
        table("data.record_report"),
        table("data.record_report_member"),
        table("ops.task"),
    )

    def scope(relation):
        return (relation.c.release_id == release_id) & (relation.c.realization_id == realization_id)

    report_query = select(reports.c.selected_task_id).where(
        scope(reports), reports.c.cut_id == selected["cut_id"]
    )
    if source_view_ids is not None:
        report_query = report_query.join(tasks, tasks.c.id == reports.c.selected_task_id).where(
            tasks.c.unit_type == "source_view", tasks.c.unit_id.in_(source_view_ids)
        )
        if source_view_ids:
            source, membership = table("kb.source_view"), table("ops.run_source_view")
            available = set(
                conn.execute(
                    select(source.c.id)
                    .join(membership, membership.c.source_view_id == source.c.id)
                    .where(membership.c.run_id == run_id, source.c.id.in_(source_view_ids))
                ).scalars()
            )
            if available != set(source_view_ids):
                raise SemanticRefusal("record source selector is outside the completed run")
    root_query = (
        select(members.c.record_id, members.c.interpretation_id)
        .where(scope(members), members.c.selected_task_id.in_(report_query))
        .distinct()
    )
    matching_records = None
    more_records = False
    if selection is not None:
        roots = table("data.source_record")
        root_query = root_query.join(
            roots,
            scope(roots)
            & (roots.c.record_id == members.c.record_id)
            & (roots.c.interpretation_id == members.c.interpretation_id),
        )
        admission = table("data.record_admission")
        root_query = root_query.join(
            admission,
            scope(admission)
            & (admission.c.record_id == roots.c.record_id)
            & (admission.c.interpretation_id == roots.c.interpretation_id),
        )
        for column in ("family", "standing", "record_id", "interpretation_id"):
            value = getattr(selection, column)
            if value is not None:
                root_query = root_query.where(
                    (admission.c.decision if column == "standing" else roots.c[column]) == value
                )
        matching_records = conn.scalar(select(func.count()).select_from(root_query.subquery()))
        if selection.after is not None:
            if (
                conn.execute(
                    root_query.where(
                        tuple_(members.c.record_id, members.c.interpretation_id) == selection.after
                    ).limit(1)
                ).first()
                is None
            ):
                from .refusals import InvalidContinuation

                raise InvalidContinuation("record continuation is outside the selected population")
            root_query = root_query.where(
                tuple_(members.c.record_id, members.c.interpretation_id) > selection.after
            )
        root_query = root_query.order_by(members.c.record_id, members.c.interpretation_id)
        root_count = conn.execute(root_query.limit(min(selection.limit, max_records) + 1)).all()
        if min(len(root_count), selection.limit) > max_records:
            raise RecordReadLimit("record count exceeds the requested projection budget")
        more_records = len(root_count) > selection.limit
        root_query = root_query.limit(selection.limit)
    else:
        root_count = conn.execute(root_query.limit(max_records + 1)).all()
        if len(root_count) > max_records:
            raise RecordReadLimit("record count exceeds the requested projection budget")
    metadata_query = (
        select(reports.c.selected_task_id, tasks.c.unit_id)
        .join(tasks, tasks.c.id == reports.c.selected_task_id)
        .where(
            scope(reports),
            reports.c.selected_task_id.in_(report_query),
            tasks.c.unit_type == "source_view",
        )
        .limit(max_rows + 1)
    )
    metadata = conn.execute(metadata_query).all()
    if len(metadata) > max_rows:
        raise RecordReadLimit("record report metadata exceeds the requested projection budget")
    report_source_view_ids = {int(row.selected_task_id): int(row.unit_id) for row in metadata}
    remaining_rows = max_rows
    raw_rows: dict[str, list[dict[str, Any]]] = {name: [] for name in RECORD_ROW_TYPES}
    remaining_bytes = max_bytes - len(
        canonical_bytes(dict(rows=raw_rows, report_source_view_ids=report_source_view_ids))
    )
    if remaining_bytes < 0:
        raise RecordReadLimit("record metadata bytes exceed the requested projection budget")
    for name, row_type in RECORD_ROW_TYPES.items():
        relation = table("data." + name)
        columns = tuple(field.name for field in fields(row_type))
        query = select(*(relation.c[column] for column in columns)).where(scope(relation))
        if name == "record_report" or name == "record_report_member":
            query = query.where(relation.c.selected_task_id.in_(report_query))
        if name != "record_report":
            query = query.where(
                tuple_(relation.c.record_id, relation.c.interpretation_id).in_(root_query)
            )
        # Stable ordering also makes detached output independent of physical scan order.
        query = query.order_by(*(relation.c[column] for column in columns)).limit(
            remaining_rows + 1
        )
        collected: list[dict[str, Any]] = []
        with conn.execute(query.execution_options(stream_results=True, yield_per=32)) as result:
            for row in result.mappings():
                if remaining_rows == 0:
                    raise RecordReadLimit(
                        "record row count exceeds the requested projection budget"
                    )
                payload: dict[str, Any] = {column: row[column] for column in columns}
                size = len(canonical_bytes(payload)) + bool(collected)
                if size > remaining_bytes:
                    raise RecordReadLimit("record bytes exceed the requested projection budget")
                remaining_rows -= 1
                remaining_bytes -= size
                collected.append(payload)
        raw_rows[name] = collected
    current = conn.execute(
        select(realization.c.release_id, realization.c.data_revision).where(
            realization.c.realization_id == realization_id
        )
    ).one()
    if current.release_id != release_id:
        raise WrongRelease("record realization release changed")
    if current.data_revision != selected["data_revision"]:
        raise StaleSnapshot("completed record realization changed during read")
    return CompletedRecordProjection(
        run_id,
        release_id,
        realization_id,
        current.data_revision,
        selected["cut_id"],
        artifact.digest,
        prepared,
        _PROJECTION_ROWS.validate_json(canonical_bytes(raw_rows), strict=True),
        source_view_ids,
        MappingProxyType(report_source_view_ids),
        selection,
        matching_records,
        more_records,
    )
