"""Append-only source-frame coordinates consumed by native statement-anchor binding."""

from __future__ import annotations

from sqlalchemy import Connection, Engine, func, select

from .metadata import table
from .operations import OperationConflict
from .proposals import NativeProposalFrame, ProposalPacket


def capture_source_frame(conn: Connection, task_id: int, packet: ProposalPacket) -> None:
    """Capture exact packet coordinates through the protected native append-only routine."""
    if not isinstance(packet.frame, NativeProposalFrame):
        raise OperationConflict("source-frame capture requires a pinned PDF SourceView")
    from dataclasses import asdict

    from .source_views import store_native_source_frame

    store_native_source_frame(
        conn, task_id=task_id, packet_hash=packet.hash, frame=asdict(packet.frame)
    )


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


def backfill_source_frames(engine: Engine, run_id: int) -> int:
    """Append missing origin frames after rebuilding and verifying their original packet hash."""
    from corpus_structure.orchestrate.semantic import agent_packet

    from .releases import open_release

    tasks, cuts, frames = map(table, ("ops.task", "ops.input_cut", "ops.native_source_frame"))
    with engine.begin() as conn:
        cut = conn.execute(
            select(cuts.c.id).where(cuts.c.run_id == run_id, cuts.c.final)
        ).scalar_one_or_none()
        origin = packet_bound_source_tasks(run_id, cut_id=cut).subquery()
        missing = (
            conn.execute(
                select(origin.c.id)
                .outerjoin(frames, frames.c.task_id == origin.c.id)
                .where(frames.c.task_id.is_(None))
                .distinct()
                .order_by(origin.c.id)
            )
            .scalars()
            .all()
        )
        for task_id in missing:
            task = conn.execute(
                select(tasks.c.run_id, tasks.c.release_id).where(tasks.c.id == task_id)
            ).one()
            prepared = open_release(conn, task.release_id)
            # agent_packet verifies recorded packet_hash before the identical capture routine.
            agent_packet(conn, task.run_id, task_id, prepared)
        return len(missing)
