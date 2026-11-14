"""Exact historical packet reconstruction for sealed source-frame recovery.

This reader creates no work, methods, runs, queues or claims. The existing packet
hash and immutable release/configuration own its meaning; capture only repairs a
missing append-only frame for that same already selected packet.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import select

from corpus_structure.core.method import UnitRef, UnitView
from corpus_structure.core.vocab import TaskUnitType
from .identity import canonical_bytes
from .metadata import table
from .operations import OperationConflict, run_view


def _unit(conn: Any, view: Any, ref: Any) -> UnitView:
    if ref.unit_type == TaskUnitType.DOCUMENT:
        return UnitView(ref, view, document_id=ref.unit_id)
    if ref.unit_type == TaskUnitType.SOURCE_VIEW:
        source = view.reader.source_view_ref(ref.unit_id)
        return UnitView(
            ref,
            view,
            document_id=source.document_id,
            source_view_id=source.id,
            context_only=(
                not source.analysis_eligible
                or ref.unit_id not in {r.id for r in view.reader.source_views()}
            ),
        )
    if ref.unit_type == TaskUnitType.RUN:
        return UnitView(ref, view)
    raise OperationConflict("source execution accepts document, SourceView and run units")


def _packet_for_unit(
    conn: Any,
    run_id: int,
    prepared: Any,
    ref: Any,
    configuration: Mapping[str, Any],
    preparation: dict | None = None,
    *,
    read_budget=None,
):
    """Shared queue/serve preparation including recorded M13 standing context."""
    from corpus_structure.orchestrate.semantic_references import document_references
    from corpus_structure.semantic.operations import lock_input_snapshot
    from corpus_structure.semantic.proposals import MAX_KNOWN

    lock_input_snapshot(conn, run_id)
    preparation = {} if preparation is None else preparation
    if "view" not in preparation:
        preparation["view"] = run_view(conn, run_id, prepared, read_budget=read_budget)
    view = preparation["view"]
    if view.reader.read_budget is not read_budget:
        raise OperationConflict("packet preparation uses a different source read budget")
    snapshot = view.options.get("agent_configs")
    if not isinstance(snapshot, dict) or not any(
        canonical_bytes(value) == canonical_bytes(dict(configuration))
        for value in snapshot.values()
    ):
        raise OperationConflict("agent configuration differs from immutable run snapshot")
    units = preparation.setdefault("units", {})
    if ref not in units:
        units[ref] = _unit(conn, view, ref)
    unit = units[ref]
    if unit.source_view_id is None:
        raise OperationConflict("agent proposals require a selected PDF SourceView")
    from corpus_structure.methods.math.native import native_proposal_packet

    known = document_references(
        conn, view, unit.document_id, limit=MAX_KNOWN, read_budget=read_budget
    )
    from corpus_structure.semantic.product_reference import ProductReference

    previous_selection = view.reader.characterization_selection
    view.reader.characterization_selection = tuple(
        ProductReference(**value) for value in configuration.get("characterization_layers", ())
    )
    try:
        packet = native_proposal_packet(
            view.reader, unit.source_view_id, prepared, configuration, known=known
        )
    finally:
        view.reader.characterization_selection = previous_selection
    if read_budget is not None:
        from corpus_structure.semantic.query import ReadLimit

        if sum(len(part.text.encode("utf-8")) for part in packet.parts()) > read_budget.max_bytes:
            raise ReadLimit(
                "complete interactive packet exceeds byte budget", reason="oversized_item"
            )
    return packet


def retained_agent_packet(
    conn: Any,
    run_id: int,
    task_id: int,
    prepared: Any,
    *,
    preparation: dict | None = None,
    read_budget=None,
    sealed_context_run_id: int | None = None,
):
    """Rebuild an existing immutable packet for a sealed selected result only."""
    context_run = run_id if sealed_context_run_id is None else sealed_context_run_id
    runs = table("ops.run")
    if conn.execute(select(runs.c.sealed).where(runs.c.id == context_run)).scalar_one() is not True:
        raise OperationConflict("retained packet inspection requires a sealed historical run")
    if context_run != run_id:
        members, cuts = table("ops.cut_task"), table("ops.input_cut")
        selected = conn.execute(select(members.c.origin_task_id).join(cuts, cuts.c.id == members.c.cut_id).where(cuts.c.run_id == context_run, members.c.origin_task_id == task_id).limit(1)).scalar_one_or_none()
        if selected != task_id:
            raise OperationConflict("packet origin is outside the sealed selected result")
    t, c, m = table("ops.task"), table("ops.method_config"), table("ops.method")
    row = (
        conn.execute(
            select(
                t.c.unit_type,
                t.c.unit_id,
                t.c.unit_key,
                t.c.packet_hash,
                c.c.params,
                m.c.name.label("method"),
                m.c.version.label("method_version"),
            )
            .join(c, t.c.method_config_id == c.c.id)
            .join(m, m.c.id == c.c.method_id)
            .where(t.c.id == task_id, t.c.run_id == run_id)
        )
        .mappings()
        .one()
    )
    ref = UnitRef(TaskUnitType(row["unit_type"]), row["unit_id"], row["unit_key"])
    from corpus_structure.methods.llm.producer import producer_binding

    producer_binding(
        row["method"], row["params"], unit=ref.unit_type, method_version=row["method_version"]
    )
    from corpus_structure.semantic.proposals import ProposalRefused

    try:
        packet = _packet_for_unit(
            conn, run_id, prepared, ref, row["params"], preparation, read_budget=read_budget
        )
    except OperationConflict as exc:
        raise ProposalRefused(str(exc)) from exc
    if row["packet_hash"] != packet.hash:
        raise ProposalRefused("recorded agent packet changed")
    from corpus_structure.semantic.source_frames import capture_source_frame

    capture_source_frame(conn, task_id, packet)
    return packet

