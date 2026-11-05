"""Selected-column private contribution inventory and bounded immutable detail reads."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, func, select

from .metadata import table


@dataclass(frozen=True)
class ContributionInventory:
    reports: tuple[Mapping[str, Any], ...]
    operations: tuple[Mapping[str, Any], ...]
    contributions: tuple[Mapping[str, Any], ...]
    more: bool


def read_source_contributions(conn, *, prepared, run_id: int, source_view_id: int | None = None,
                              method: str | None = None, operation_key: str | None = None,
                              kind: str | None = None, limit: int = 100,
                              include_details: bool = False, cut_id: int | None = None,
                              max_bytes: int = 8_000_000) -> ContributionInventory:
    """Read private products only under an exact selected run/cut, never graph membership.

    Reports include missing predecessor products and explicit empty product arrays. The
    operation population is read independently of contributions, preserving zero outputs.
    Source/method/operation selectors apply before any evidence payload is selected.
    """
    from .contracts import require_bound_operation
    from .identity import canonical_bytes

    require_bound_operation(prepared, 'read_source_contributions')
    if run_id < 1 or not 1 <= limit <= 10_000 or max_bytes < 1:
        raise ValueError('contribution read requires positive run and bounded limits')
    selected, origin = table('ops.task'), table('ops.task').alias('origin')
    results, cfg, methods = table('ops.task_result'),table('ops.method_config'),table('ops.method')
    run=table('ops.run')
    query = (select(selected.c.id.label('selected_task_id'),origin.c.id.label('origin_task_id'),
        selected.c.unit_id.label('source_view_id'),methods.c.name.label('method'),
        results.c.body['source'].astext.label('source'),
        results.c.body.has_key('contributions').label('contributions_present'),
        results.c.body.has_key('contribution_operations').label('operations_present'),
        results.c.body['outcome'].astext.label('outcome'))
        .select_from(selected).join(run,run.c.id==selected.c.run_id)
        .join(origin,origin.c.id==func.coalesce(selected.c.reused_task_id,selected.c.id))
        .join(cfg,cfg.c.id==origin.c.method_config_id).join(methods,methods.c.id==cfg.c.method_id)
        .outerjoin(results,results.c.task_id==origin.c.id)
        .where(selected.c.run_id==run_id,selected.c.release_id==prepared.release_id,
            run.c.release_id==prepared.release_id,origin.c.release_id==prepared.release_id,
            selected.c.unit_type=='source_view',selected.c.status.in_(('done','empty','failed','reused'))))
    if cut_id is not None:
        cuts,cut_tasks=table('ops.input_cut'),table('ops.cut_task')
        query=query.join(cut_tasks,and_(cut_tasks.c.task_id==selected.c.id,cut_tasks.c.cut_id==cut_id)).join(
            cuts,and_(cuts.c.id==cut_tasks.c.cut_id,cuts.c.run_id==run_id))
    if source_view_id is not None:
        query=query.where(selected.c.unit_id==source_view_id)
    if method is not None:
        query=query.where(methods.c.name==method)
    reports=tuple(dict(row) for row in conn.execute(query.order_by(selected.c.id).limit(limit+1)).mappings())
    more=len(reports)>limit
    reports=reports[:limit]
    origins={r['origin_task_id']:r for r in reports}
    if not origins:
        return ContributionInventory(reports,(),(),more)
    operations=table('kb.source_contribution_operation')
    op_query=select(operations).where(operations.c.task_id.in_(origins))
    if operation_key is not None:
        op_query=op_query.where(operations.c.operation_key==operation_key)
    op_rows=tuple(dict(row) for row in conn.execute(op_query.order_by(operations.c.task_id,operations.c.position).limit(limit+1)).mappings())
    more=more or len(op_rows)>limit
    op_rows=op_rows[:limit]
    contributions=table('kb.source_contribution')
    query=select(contributions).where(contributions.c.task_id.in_(origins))
    if operation_key is not None:
        query=query.where(contributions.c.operation_key==operation_key)
    if kind is not None:
        query=query.where(contributions.c.kind==kind)
    if include_details:
        detail=results.c.body['contributions'][contributions.c.position]
        query=query.add_columns(detail.label('detail')).join(results,results.c.task_id==contributions.c.task_id)
    rows=tuple(dict(row) for row in conn.execute(query.order_by(contributions.c.task_id,contributions.c.position).limit(limit+1)).mappings())
    more=more or len(rows)>limit
    rows=rows[:limit]
    size=0
    output=[]
    for row in rows:
        report=origins[row['task_id']]
        meta={k:report[k] for k in ('selected_task_id','origin_task_id','source','method')}
        if include_details:
            raw=row.pop('detail')
            size+=len(canonical_bytes(raw))
            if size>max_bytes:
                raise ValueError('contribution detail read exceeds byte budget')
            row=prepared.validate_python('SourceContribution',raw).model_dump(mode='python')
        output.append({**row,**meta})
    operation_output=tuple({**row,**{k:origins[row['task_id']][k] for k in ('selected_task_id','origin_task_id','source','method')}} for row in op_rows)
    return ContributionInventory(reports,operation_output,tuple(output),more)
