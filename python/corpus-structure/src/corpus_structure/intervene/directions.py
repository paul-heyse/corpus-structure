"""Operator direction records in the semantic operation log."""

from __future__ import annotations

import json
from sqlalchemy import Engine, select, text
from corpus_structure.intervene.service import DirectionRecorded, ToolFailure
from corpus_structure.semantic.metadata import table


def record_direction(engine: Engine, direction: str, scope: str | None = None, *,
                     actor: str, session_ref: str | None = None,
                     project: str | None = None, run_id: int | None = None) -> DirectionRecorded:
    """Append guidance as provenance, without mutating an admitted interpretation."""
    if not direction.strip():
        raise ToolFailure("a direction has text")
    runs = table("ops.run")
    with engine.begin() as conn:
        query = select(runs.c.id, runs.c.project_id)
        if run_id is not None:
            query = query.where(runs.c.id == run_id)
        elif project is not None:
            query = query.where(runs.c.project_id == project)
        else:
            raise ToolFailure("a semantic project or run is required")
        row = conn.execute(query.order_by(runs.c.id.desc()).limit(1)).one_or_none()
        if row is None:
            raise ToolFailure("initialize and start a semantic project run before recording guidance")
        iid = conn.execute(text("SELECT ops.record_direction(:r,:a,:s,CAST(:b AS jsonb))"),
            {"r": row.id, "a": actor, "s": session_ref or "operator",
             "b": json.dumps({"text": direction, "scope": scope or "all", "project_id": row.project_id})}).scalar_one()
    return DirectionRecorded(intervention_id=iid, project=row.project_id, file="ops.intervention")
