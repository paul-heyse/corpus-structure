"""Selected-column private contribution inventory and bounded immutable detail reads."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, exists, false, func, literal, or_, select, text
from sqlalchemy.sql.elements import ColumnElement

from .metadata import table


@dataclass(frozen=True)
class ContributionInventory:
    reports: tuple[Mapping[str, Any], ...]
    operations: tuple[Mapping[str, Any], ...]
    contributions: tuple[Mapping[str, Any], ...]
    more: bool
    interpretations: tuple[Mapping[str, Any], ...] = ()


def read_source_contributions(
    conn,
    *,
    prepared,
    run_id: int,
    source_view_id: int | None = None,
    method: str | None = None,
    operation_key: str | None = None,
    operation_version: str | None = None,
    contribution_id: str | None = None,
    occurrence_id: str | None = None,
    kind: str | None = None,
    limit: int = 100,
    include_details: bool = False,
    include_interpretation: bool = False,
    cut_id: int | None = None,
    max_bytes: int = 8_000_000,
    operation_keys: tuple[str, ...] | None = None,
    anchor_ids: tuple[str, ...] | None = None,
    anchor_scopes: tuple[Mapping[str, Any], ...] | None = None,
    anchor_endpoint_roles: tuple[str, ...] | None = None,
    contribution_ids: tuple[str, ...] | None = None,
) -> ContributionInventory:
    """Read private products only under an exact selected run/cut, never graph membership.

    Reports include missing predecessor products and explicit empty product arrays. The
    operation population is read independently of contributions, preserving zero outputs.
    Source/method/operation selectors apply before any evidence payload is selected.
    """
    import json

    from .contracts import require_bound_operation

    require_bound_operation(prepared, "read_source_contributions")
    if run_id < 1 or not 1 <= limit <= 10_000 or max_bytes < 1:
        raise ValueError("contribution read requires positive run and bounded limits")
    selected, origin = table("ops.task"), table("ops.task").alias("origin")
    results, cfg, methods = (
        table("ops.task_result"),
        table("ops.method_config"),
        table("ops.method"),
    )
    run = table("ops.run")
    actual_release = conn.scalar(select(run.c.release_id).where(run.c.id == run_id))
    if actual_release != prepared.release_id:
        raise ValueError("contribution run differs from the requested release")
    if source_view_id is not None:
        membership = table("ops.run_source_view")
        if not conn.scalar(
            select(
                exists().where(
                    membership.c.run_id == run_id, membership.c.source_view_id == source_view_id
                )
            )
        ):
            raise ValueError("contribution source view is outside the selected run")
    query = (
        select(
            selected.c.id.label("selected_task_id"),
            origin.c.id.label("origin_task_id"),
            selected.c.unit_id.label("source_view_id"),
            selected.c.status.label("task_status"),
            methods.c.name.label("method"),
            results.c.body["source"].astext.label("source"),
            results.c.body.has_key("contributions").label("contributions_present"),
            results.c.body.has_key("contribution_operations").label("operations_present"),
            results.c.body["outcome"].astext.label("outcome"),
        )
        .select_from(selected)
        .join(run, run.c.id == selected.c.run_id)
        .join(origin, origin.c.id == func.coalesce(selected.c.reused_task_id, selected.c.id))
        .join(cfg, cfg.c.id == origin.c.method_config_id)
        .join(methods, methods.c.id == cfg.c.method_id)
        .outerjoin(results, results.c.task_id == origin.c.id)
        .where(
            selected.c.run_id == run_id,
            selected.c.release_id == prepared.release_id,
            run.c.release_id == prepared.release_id,
            origin.c.release_id == prepared.release_id,
            selected.c.unit_type == "source_view",
            selected.c.status.in_(("done", "empty", "failed", "reused", "skipped", "cancelled")),
        )
    )
    if cut_id is not None:
        cuts, cut_tasks = table("ops.input_cut"), table("ops.cut_task")
        if conn.scalar(select(cuts.c.run_id).where(cuts.c.id == cut_id)) != run_id:
            raise ValueError("contribution cut belongs to another run")
        query = query.outerjoin(
            cut_tasks, and_(cut_tasks.c.task_id == selected.c.id, cut_tasks.c.cut_id == cut_id)
        ).add_columns(cut_tasks.c.task_id.is_not(None).label("cut_member"))
    else:
        query = query.add_columns(literal(None).label("cut_member"))
    if source_view_id is not None:
        query = query.where(selected.c.unit_id == source_view_id)
    if method is not None:
        query = query.where(methods.c.name == method)
    reports = tuple(
        dict(row) for row in conn.execute(query.order_by(selected.c.id).limit(limit + 1)).mappings()
    )
    more = len(reports) > limit
    reports = reports[:limit]
    origins = {r["origin_task_id"]: r for r in reports}
    if not origins:
        return ContributionInventory(reports, (), (), more)
    operations = table("kb.source_contribution_operation")
    op_query = select(operations).where(operations.c.task_id.in_(origins))
    if operation_key is not None:
        op_query = op_query.where(operations.c.operation_key == operation_key)
    if operation_keys is not None:
        op_query = op_query.where(operations.c.operation_key.in_(operation_keys))
    if operation_version is not None:
        op_query = op_query.where(operations.c.operation_version == operation_version)
    op_rows = tuple(
        dict(row)
        for row in conn.execute(
            op_query.order_by(operations.c.task_id, operations.c.position).limit(limit + 1)
        ).mappings()
    )
    more = more or len(op_rows) > limit
    op_rows = op_rows[:limit]
    if op_rows:
        # Expand each selected origin's array once, rather than detoasting its
        # report once per operation. Only compact progress counters cross here.
        positions = {}
        for row in op_rows:
            positions.setdefault(row["task_id"], []).append(row["position"])
        count_rows = conn.execute(
            text("""
            SELECT r.task_id, c.value->>'operation_key' AS operation_key,
                   c.value#>'{contextual_enrichment,product_counts}' AS product_counts,
                   jsonb_array_length(COALESCE(
                     c.value#>'{contextual_enrichment,vector_reuse}', '[]'::jsonb))
                     AS reused_vector_count
            FROM jsonb_to_recordset(CAST(:selection AS jsonb))
              s(task_id bigint, positions bigint[])
            JOIN ops.task_result r ON r.task_id=s.task_id
            CROSS JOIN LATERAL jsonb_array_elements(r.body->'contribution_operations')
              WITH ORDINALITY c(value,ordinality)
            WHERE c.ordinality-1=ANY(s.positions) AND c.value ? 'contextual_enrichment'
        """),
            dict(
                selection=json.dumps(
                    [
                        dict(task_id=task, positions=selected_positions)
                        for task, selected_positions in positions.items()
                    ]
                )
            ),
        ).mappings()
        counters = {
            (row["task_id"], row["operation_key"]): {
                "product_counts": row["product_counts"],
                "reused_vector_count": row["reused_vector_count"],
            }
            for row in count_rows
        }
        op_rows = tuple(
            {**row, **counters.get((row["task_id"], row["operation_key"]), {})} for row in op_rows
        )
    contributions = table("kb.source_contribution")
    query = select(contributions).where(contributions.c.task_id.in_(origins))
    if operation_version is not None:
        query = query.join(
            operations,
            and_(
                operations.c.task_id == contributions.c.task_id,
                operations.c.operation_key == contributions.c.operation_key,
            ),
        ).where(operations.c.operation_version == operation_version)
    if contribution_id is not None:
        query = query.where(contributions.c.contribution_id == contribution_id)
    if occurrence_id is not None:
        query = query.where(contributions.c.occurrence_id == occurrence_id)
    if operation_key is not None:
        query = query.where(contributions.c.operation_key == operation_key)
    if operation_keys is not None:
        query = query.where(contributions.c.operation_key.in_(operation_keys))
    selectors: list[ColumnElement[bool]] = []
    anchors = table("kb.source_contribution_anchor")
    anchor_filters: list[ColumnElement[bool]] = []
    if anchor_ids is not None:
        anchor_filters.append(anchors.c.anchor_id.in_(anchor_ids))
    if anchor_scopes is not None:
        for scope in anchor_scopes:
            if scope["space"] == "selected_projection":
                raise ValueError("contribution scope requires canonical native coordinates")
            terms = [anchors.c.pointer == scope["pointer"], anchors.c.space == scope["space"]]
            if scope.get("pin", {}).get("source_view_id") is not None:
                terms.append(anchors.c.source_view_id == scope["pin"]["source_view_id"])
            if scope.get("start") is not None:
                terms.append(
                    or_(
                        anchors.c.start.is_(None),
                        and_(anchors.c.start < scope["end"], anchors.c.end > scope["start"]),
                    )
                )
            anchor_filters.append(and_(*terms))
    if anchor_ids is not None or anchor_scopes is not None:
        source_match = or_(*anchor_filters) if anchor_filters else false()
        selectors.append(
            exists(
                select(1)
                .select_from(anchors)
                .where(
                    anchors.c.task_id == contributions.c.task_id,
                    anchors.c.contribution_id == contributions.c.contribution_id,
                    source_match,
                )
            )
        )
        if anchor_endpoint_roles:
            endpoints = table("kb.source_contribution_endpoint")
            selectors.append(
                exists(
                    select(1)
                    .select_from(endpoints)
                    .join(
                        anchors,
                        and_(
                            anchors.c.task_id == endpoints.c.task_id,
                            anchors.c.contribution_id == endpoints.c.endpoint_id,
                        ),
                    )
                    .where(
                        endpoints.c.task_id == contributions.c.task_id,
                        endpoints.c.contribution_id == contributions.c.contribution_id,
                        endpoints.c.role.in_(anchor_endpoint_roles),
                        source_match,
                    )
                )
            )
    if contribution_ids is not None:
        selectors.append(contributions.c.contribution_id.in_(contribution_ids))
    if selectors:
        query = query.where(or_(*selectors))
    if kind is not None:
        query = query.where(contributions.c.kind == kind)
    if cut_id is not None:
        allowed_origins = {row["origin_task_id"] for row in reports if row["cut_member"]}
        query = query.where(contributions.c.task_id.in_(allowed_origins))
    rows = tuple(
        dict(row)
        for row in conn.execute(
            query.order_by(contributions.c.task_id, contributions.c.position).limit(limit + 1)
        ).mappings()
    )
    more = more or len(rows) > limit
    rows = rows[:limit]
    details = {}
    operation_details = {}
    if include_details or include_interpretation:
        # One expansion per report array in each query, independent of selected
        # row count. Admit the combined operation/contribution transfer budget
        # before either payload is decoded. PostgreSQL owns report expansion.
        requests = []
        total_bytes = 0
        grouped_sql = """
          SELECT r.task_id,jsonb_agg(c.value ORDER BY c.ordinality) AS selected_details
          FROM jsonb_to_recordset(CAST(:selection AS jsonb)) s(task_id bigint,positions bigint[])
          JOIN ops.task_result r ON r.task_id=s.task_id
          CROSS JOIN LATERAL jsonb_array_elements(r.body->:field)
            WITH ORDINALITY c(value,ordinality)
          WHERE c.ordinality-1=ANY(s.positions) GROUP BY r.task_id
        """
        byte_query = text(
            "SELECT COALESCE(sum(octet_length(selected_details::text)),0) FROM ("
            + grouped_sql
            + ") bounded"
        )
        for field, selected_rows, identity in (
            ("contributions", rows, "contribution_id"),
            ("contribution_operations", op_rows if include_details else (), "operation_key"),
        ):
            if not selected_rows:
                continue
            positions = {}
            for row in selected_rows:
                positions.setdefault(row["task_id"], []).append(row["position"])
            params = dict(
                field=field,
                selection=json.dumps(
                    [dict(task_id=task, positions=chosen) for task, chosen in positions.items()]
                ),
            )
            total_bytes += conn.scalar(byte_query, params)
            requests.append((field, identity, params))
        if total_bytes > max_bytes:
            raise ValueError("contribution detail read exceeds byte budget before hydration")
        for field, identity, params in requests:
            target = details if field == "contributions" else operation_details
            for report in conn.execute(text(grouped_sql), params).mappings():
                for raw in report["selected_details"]:
                    target[report["task_id"], raw[identity]] = raw
    output, interpretation_output = [], []
    for row in rows:
        report = origins[row["task_id"]]
        meta = {
            k: report[k]
            for k in (
                "selected_task_id",
                "origin_task_id",
                "source_view_id",
                "source",
                "method",
                "task_status",
                "cut_member",
            )
        }
        if include_details or include_interpretation:
            raw = details[row["task_id"], row["contribution_id"]]
            decoded = prepared.validate_json("SourceContribution", json.dumps(raw)).model_dump(
                mode="python"
            )
            if include_interpretation:
                interpretation_output.append({**decoded, **meta})
            if include_details:
                row = decoded
        output.append({**row, **meta})
    if include_details:
        op_rows = tuple(
            {
                **prepared.validate_json(
                    "SourceContributionOperation",
                    json.dumps(operation_details[row["task_id"], row["operation_key"]]),
                ).model_dump(mode="python"),
                "task_id": row["task_id"],
                "position": row["position"],
            }
            for row in op_rows
        )
    operation_output = tuple(
        {
            **row,
            **{
                k: origins[row["task_id"]][k]
                for k in (
                    "selected_task_id",
                    "origin_task_id",
                    "source_view_id",
                    "source",
                    "method",
                    "task_status",
                    "cut_member",
                )
            },
        }
        for row in op_rows
    )
    return ContributionInventory(
        reports, operation_output, tuple(output), more, tuple(interpretation_output)
    )
