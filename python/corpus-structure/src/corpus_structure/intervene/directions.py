"""Operator direction records in the semantic operation log."""

from __future__ import annotations

from sqlalchemy import Engine, select

from corpus_structure.intervene.service import DirectionRecorded, ToolFailure
from corpus_structure.semantic.metadata import table


def record_direction(
    engine: Engine,
    direction: str,
    scope: str | None = None,
    *,
    actor: str,
    session_ref: str | None = None,
    project: str | None = None,
    run_id: int | None = None,
) -> DirectionRecorded:
    """Append guidance as provenance, without mutating an admitted interpretation."""
    if not direction.strip():
        raise ToolFailure("a direction has text")
    runs = table("ops.run")
    with engine.begin() as conn:
        query = select(runs.c.id, runs.c.project_id, runs.c.release_id)
        if run_id is not None:
            query = query.where(runs.c.id == run_id)
        elif project is not None:
            query = query.where(
                runs.c.project_id == project, runs.c.status.in_(("created", "running"))
            )
        else:
            raise ToolFailure("a semantic project or run is required")
        row = conn.execute(query.order_by(runs.c.id.desc()).limit(1)).one_or_none()
        if row is None:
            raise ToolFailure(
                "initialize and start a semantic project run before recording guidance"
            )
        from corpus_structure.semantic._operation_calls import record_direction as invoke
        from corpus_structure.semantic._operation_ids import RunId
        from corpus_structure.semantic.contracts import require_bound_operation
        from corpus_structure.semantic.releases import open_release

        prepared = open_release(conn, row.release_id)
        require_bound_operation(prepared, "record_direction")
        iid = invoke(
            conn,
            run_id=RunId(row.id),
            actor=actor,
            session_ref=session_ref or "operator",
            body={"text": direction, "scope": scope or "all", "project_id": row.project_id},
            projection_context=prepared,
        )
    return DirectionRecorded(intervention_id=iid, project=row.project_id, file="ops.intervention")
