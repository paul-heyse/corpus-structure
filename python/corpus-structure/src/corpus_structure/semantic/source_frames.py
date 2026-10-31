"""Append-only source-frame coordinates consumed by native statement-anchor binding."""

from __future__ import annotations

import json

from sqlalchemy import Connection, Engine, func, select, text

from corpus_structure.core.evidence import RenditionContent, segment_key
from corpus_structure.core.locators import LocatorIndex, parse

from .metadata import table
from .operations import OperationConflict
from .proposals import NativeProposalFrame, ProposalFrame, ProposalPacket, ProposalSentence


def capture_source_frame(conn: Connection, task_id: int, packet: ProposalPacket) -> None:
    """Capture exact packet coordinates through the protected native append-only routine."""
    if isinstance(packet.frame, NativeProposalFrame):
        from dataclasses import asdict

        from .source_views import store_native_source_frame

        store_native_source_frame(
            conn, task_id=task_id, packet_hash=packet.hash, frame=asdict(packet.frame)
        )
        return
    tasks, renditions, segments, selected = map(
        table, ("ops.task", "kb.rendition", "kb.segment", "ops.run_rendition")
    )
    task = conn.execute(select(tasks).where(tasks.c.id == task_id)).mappings().one()
    if task["reused_task_id"] is not None:
        raise OperationConflict("a reused task consumes its origin source frame")
    packet_hash = packet.hash
    if task["packet_hash"] != packet_hash or task["unit_key"] != packet.frame.unit_ref:
        raise OperationConflict("source frame differs from the recorded packet hash")
    frames = table("ops.source_frame")
    existing = (
        conn.execute(select(frames).where(frames.c.task_id == task_id)).mappings().one_or_none()
    )
    if existing is not None:
        if existing["packet_hash"] != packet_hash or existing["unit_ref"] != task["unit_key"]:
            raise OperationConflict("captured source frame differs from its immutable task binding")
        if (task["unit_type"] == "segment" and existing["unit_segment_id"] != task["unit_id"]) or (
            task["unit_type"] == "rendition" and existing["rendition_id"] != task["unit_id"]
        ):
            raise OperationConflict("captured source frame differs from its native source unit")
        # Native capture checked geometry and custody once. The task's source binding, frame
        # and rendition are immutable; equal packet hashes commit to the complete same frame.
        return
    query = (
        select(renditions)
        .join(selected, selected.c.rendition_id == renditions.c.id)
        .where(selected.c.run_id == task["run_id"])
    )
    if task["unit_type"] == "segment":
        query = query.join(segments, segments.c.rendition_id == renditions.c.id).where(
            segments.c.id == task["unit_id"]
        )
    elif task["unit_type"] == "rendition":
        query = query.where(renditions.c.id == task["unit_id"])
    elif task["unit_type"] == "document":
        query = query.where(renditions.c.document_id == task["unit_id"])
    else:
        raise OperationConflict("source frame needs a native rendition-bound source unit")
    rendition = conn.execute(query).mappings().one()
    content = RenditionContent.model_validate(rendition["content"])
    if content.canonical_text != packet.frame.text:
        raise OperationConflict("source frame text differs from its immutable rendition")
    index = LocatorIndex(content, parse(packet.frame.unit_ref).page)
    unit = index.resolve(packet.frame.unit_ref)
    ids = {
        row.segment_key: row.id
        for row in conn.execute(
            select(segments.c.segment_key, segments.c.id).where(
                segments.c.rendition_id == rendition["id"]
            )
        )
    }
    unit_id = ids[segment_key(rendition["key"], unit.kind, unit.start, unit.end)]
    sentences = []
    for sentence in packet.frame.sentences:
        node = index.resolve(sentence.locator)
        if (node.start, node.end) != (sentence.start, sentence.end):
            raise OperationConflict(
                "source frame sentence coordinates differ from its immutable segment"
            )
        sentences.append(
            {
                "id": sentence.id,
                "locator": str(index.generate(node)),
                "segment_id": ids[segment_key(rendition["key"], node.kind, node.start, node.end)],
                "start": sentence.start,
                "end": sentence.end,
                "text": content.canonical_text[sentence.start : sentence.end],
            }
        )
    conn.execute(
        text(
            "SELECT ops.record_source_frame(:task,:hash,:rendition,:unit,:locator,:segment,"
            "CAST(:sentences AS jsonb))"
        ),
        {
            "task": task_id,
            "hash": packet_hash,
            "rendition": rendition["id"],
            "unit": packet.frame.unit_ref,
            "locator": str(index.generate(unit)),
            "segment": unit_id,
            "sentences": json.dumps(sentences),
        },
    )


def load_source_frames(
    conn: Connection, task_ids
) -> dict[int, ProposalFrame | NativeProposalFrame]:
    """Acquire distinct immutable origins in bounded sets, independent of observations."""
    tasks = table("ops.task")
    wanted = sorted(set(task_ids))
    native_ids = set(
        conn.execute(
            select(tasks.c.id).where(tasks.c.id.in_(wanted), tasks.c.unit_type == "source_view")
        ).scalars()
    )
    native_frames: dict[int, ProposalFrame | NativeProposalFrame] = {}
    if native_ids:
        from .source_views import load_native_source_frames

        native_frames.update(load_native_source_frames(conn, native_ids))
        if native_ids - native_frames.keys():
            raise OperationConflict("native source tasks lack their immutable packet frame")
    frames, sentences, segments, renditions = map(
        table, ("ops.source_frame", "ops.source_frame_sentence", "kb.segment", "kb.rendition")
    )
    ids = [id for id in wanted if id not in native_ids]
    headers = {}
    coordinates = {}
    for start in range(0, len(ids), 512):
        chunk = ids[start : start + 512]
        headers.update(
            (row["task_id"], row)
            for row in conn.execute(select(frames).where(frames.c.task_id.in_(chunk))).mappings()
        )
        for row in conn.execute(
            select(
                sentences.c.task_id,
                sentences.c.sentence_id,
                sentences.c.locator,
                segments.c.start_offset,
                segments.c.end_offset,
            )
            .join(segments, segments.c.id == sentences.c.segment_id)
            .where(sentences.c.task_id.in_(chunk))
            .order_by(sentences.c.task_id, sentences.c.sentence_id)
        ):
            coordinates.setdefault(row.task_id, []).append(ProposalSentence(*row[1:]))
    missing = set(ids) - headers.keys()
    if missing:
        raise OperationConflict(
            f"source tasks {sorted(missing)} lack their immutable source frames; "
            "verify and backfill them first"
        )
    rendition_ids = sorted({row["rendition_id"] for row in headers.values()})
    texts = {}
    for start in range(0, len(rendition_ids), 512):
        texts.update(
            conn.execute(
                select(renditions.c.id, renditions.c.canonical_text).where(
                    renditions.c.id.in_(rendition_ids[start : start + 512])
                )
            ).all()
        )
    return {
        **native_frames,
        **{
            task_id: ProposalFrame(
                row["unit_ref"], texts[row["rendition_id"]], tuple(coordinates.get(task_id, ()))
            )
            for task_id, row in headers.items()
        },
    }


def load_source_frame(conn: Connection, task_id: int) -> ProposalFrame | NativeProposalFrame:
    return load_source_frames(conn, [task_id])[task_id]


def packet_bound_source_tasks(run_id: int, *, cut_id: int | None = None):
    """Source-frame obligations follow packet-bound, non-skipped origin tasks.

    Skipped tasks may carry a precomputed packet hash, but their explicit lifecycle outcome
    excludes them from the acquired source universe. Empty and failed reports do not.
    """
    tasks, members, cuts = map(table, ("ops.task", "ops.cut_task", "ops.input_cut"))
    origin = tasks.alias("packet_bound_origin")
    query = select(origin).where(origin.c.packet_hash.is_not(None), origin.c.status != "skipped")
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

    tasks, cuts, frames = map(table, ("ops.task", "ops.input_cut", "ops.source_frame"))
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
