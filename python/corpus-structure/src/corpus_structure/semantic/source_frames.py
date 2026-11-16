"""Append-only source-frame coordinates consumed by native statement-anchor binding."""

from __future__ import annotations

from sqlalchemy import Connection, func, select

from .metadata import table
from .proposals import NativeProposalFrame
from .refusals import OperationConflict




def load_source_frames(conn: Connection, task_ids) -> dict[int, NativeProposalFrame]:
    """Read exact captured PDF sources; historical HTML frames have no current reader."""
    from .source_views import load_native_source_frames

    wanted = sorted(set(task_ids))
    frames = load_native_source_frames(conn, wanted)
    if set(wanted) - frames.keys():
        raise OperationConflict("selected source tasks lack their immutable PDF packet frames")
    return frames


def load_source_frame(conn: Connection, task_id: int) -> NativeProposalFrame:
    return load_source_frames(conn, [task_id])[task_id]


def packet_bound_source_tasks(run_id: int, *, cut_id: int | None = None):
    """Source-frame obligations follow packet-bound, non-skipped origin tasks.

    Skipped tasks may carry a precomputed packet hash, but their explicit lifecycle outcome
    excludes them from the acquired source universe. Empty and failed reports do not.
    """
    tasks, members, cuts = map(table, ("ops.task", "ops.cut_task", "ops.input_cut"))
    origin = tasks.alias("packet_bound_origin")
    query = select(origin.c.id, origin.c.unit_type).where(
        origin.c.packet_hash.is_not(None), origin.c.status != "skipped"
    )
    if cut_id is not None:
        return (
            query.join(members, members.c.origin_task_id == origin.c.id)
            .join(cuts, cuts.c.id == members.c.cut_id)
            .where(cuts.c.id == cut_id, cuts.c.run_id == run_id)
        )
    return query.join(
        tasks, origin.c.id == func.coalesce(tasks.c.reused_task_id, tasks.c.id)
    ).where(tasks.c.run_id == run_id)
