"""Append-only source-frame coordinates consumed by native statement-anchor binding."""

from __future__ import annotations

import json
from sqlalchemy import Connection, Engine, func, select, text

from corpus_structure.core.evidence import RenditionContent, segment_key
from corpus_structure.core.locators import LocatorIndex, parse
from .metadata import table
from .operations import OperationConflict
from .proposals import ProposalFrame, ProposalPacket, ProposalSentence


def capture_source_frame(conn: Connection, task_id: int, packet: ProposalPacket) -> None:
    """Capture exact packet coordinates through the protected native append-only routine."""
    tasks, renditions, segments, selected = map(table, ("ops.task", "kb.rendition", "kb.segment", "ops.run_rendition"))
    task = conn.execute(select(tasks).where(tasks.c.id == task_id)).mappings().one()
    if task["reused_task_id"] is not None:
        raise OperationConflict("a reused task consumes its origin source frame")
    packet_hash = packet.hash
    if task["packet_hash"] != packet_hash or task["unit_key"] != packet.frame.unit_ref:
        raise OperationConflict("source frame differs from the recorded packet hash")
    frames = table("ops.source_frame")
    existing = conn.execute(select(frames).where(frames.c.task_id == task_id)).mappings().one_or_none()
    if existing is not None:
        if existing["packet_hash"] != packet_hash or existing["unit_ref"] != task["unit_key"]:
            raise OperationConflict("captured source frame differs from its immutable task binding")
        if ((task["unit_type"] == "segment" and existing["unit_segment_id"] != task["unit_id"])
            or (task["unit_type"] == "rendition" and existing["rendition_id"] != task["unit_id"])):
            raise OperationConflict("captured source frame differs from its native source unit")
        # Native capture checked geometry and custody once. The task's source binding, frame
        # and rendition are immutable; equal packet hashes commit to the complete same frame.
        return
    query = select(renditions).join(selected, selected.c.rendition_id == renditions.c.id).where(selected.c.run_id == task["run_id"])
    if task["unit_type"] == "segment":
        query = query.join(segments, segments.c.rendition_id == renditions.c.id).where(segments.c.id == task["unit_id"])
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
    ids = {row.segment_key: row.id for row in conn.execute(select(segments.c.segment_key, segments.c.id).where(segments.c.rendition_id == rendition["id"]))}
    unit_id = ids[segment_key(rendition["key"], unit.kind, unit.start, unit.end)]
    sentences = []
    for sentence in packet.frame.sentences:
        node = index.resolve(sentence.locator)
        if (node.start, node.end) != (sentence.start, sentence.end):
            raise OperationConflict("source frame sentence coordinates differ from its immutable segment")
        sentences.append({"id": sentence.id, "locator": str(index.generate(node)),
                          "segment_id": ids[segment_key(rendition["key"], node.kind, node.start, node.end)],
                          "start": sentence.start, "end": sentence.end,
                          "text": content.canonical_text[sentence.start:sentence.end]})
    conn.execute(text("SELECT ops.record_source_frame(:task,:hash,:rendition,:unit,:locator,:segment,CAST(:sentences AS jsonb))"),
                 {"task": task_id, "hash": packet_hash, "rendition": rendition["id"],
                  "unit": packet.frame.unit_ref, "locator": str(index.generate(unit)), "segment": unit_id,
                  "sentences": json.dumps(sentences)})


def load_source_frame(conn: Connection, task_id: int) -> ProposalFrame:
    frames, sentences, segments, renditions = map(table, ("ops.source_frame", "ops.source_frame_sentence", "kb.segment", "kb.rendition"))
    frame = conn.execute(select(frames, renditions.c.canonical_text).join(renditions, renditions.c.id == frames.c.rendition_id)
                         .where(frames.c.task_id == task_id)).mappings().one_or_none()
    if frame is None:
        raise OperationConflict(f"source task {task_id} lacks its immutable source frame; verify and backfill it first")
    rows = conn.execute(select(sentences.c.sentence_id, sentences.c.locator, segments.c.start_offset, segments.c.end_offset)
                        .join(segments, segments.c.id == sentences.c.segment_id).where(sentences.c.task_id == task_id)
                        .order_by(sentences.c.sentence_id)).all()
    return ProposalFrame(frame["unit_ref"], frame["canonical_text"], tuple(ProposalSentence(*row) for row in rows))


def backfill_source_frames(engine: Engine, run_id: int) -> int:
    """Append missing origin frames after rebuilding and verifying their original packet hash."""
    from corpus_structure.orchestrate.semantic import agent_packet
    from .releases import load_release

    tasks, observations, cuts, members, frames = map(table, ("ops.task", "kb.observation", "ops.input_cut", "ops.cut_task", "ops.source_frame"))
    with engine.begin() as conn:
        cut = conn.execute(select(cuts.c.id).where(cuts.c.run_id == run_id, cuts.c.final)).scalar_one_or_none()
        origin = tasks.alias("source_frame_origin")
        query = select(observations.c.task_id).join(origin, origin.c.id == observations.c.task_id).where(
            observations.c.payload_definition == "AgentStoredBatch", origin.c.packet_hash.is_not(None)
        )
        if cut is not None:
            query = query.join(members, members.c.origin_task_id == observations.c.task_id).where(members.c.cut_id == cut)
        else:
            query = query.join(tasks, observations.c.task_id == func.coalesce(tasks.c.reused_task_id, tasks.c.id)).where(tasks.c.run_id == run_id)
        missing = conn.execute(query.outerjoin(frames, frames.c.task_id == observations.c.task_id).where(frames.c.task_id.is_(None)).distinct()).scalars().all()
        for task_id in missing:
            task = conn.execute(select(tasks.c.run_id, tasks.c.release_id).where(tasks.c.id == task_id)).one()
            prepared = load_release(conn, task.release_id)
            # agent_packet verifies recorded packet_hash before the identical capture routine.
            agent_packet(conn, task.run_id, task_id, prepared)
        return len(missing)
