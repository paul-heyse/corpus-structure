"""Remaining sealed-run finalization for legacy publication consumers.

Current operations use declared demand custody. This owner remains until its
publication consumers move to current consolidation.
"""

from __future__ import annotations

from sqlalchemy import Engine

from corpus_structure.settings import AnalyticsSettings


def finalize_bound_run(
    engine: Engine,
    run_id: int,
    output_realization_id: str,
    *,
    analytics: AnalyticsSettings | None = None,
):
    from corpus_structure.orchestrate.liveness import supervise_run

    with supervise_run(engine, run_id):
        return _finalize_bound_run(engine, run_id, output_realization_id, analytics=analytics)


def _finalize_bound_run(
    engine: Engine, run_id: int, output_realization_id: str, *, analytics: AnalyticsSettings | None
):
    from sqlalchemy import select

    from corpus_structure.semantic.domain_operations import DomainOperationRefused, consolidate_cut
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.operations import seal_cut

    t = table("ops.task")
    with engine.begin() as conn:
        from corpus_structure.semantic._operation_calls import lock_finalization_run
        from corpus_structure.semantic._operation_ids import RunId

        owned_run_id = RunId(run_id)
        row = lock_finalization_run(conn, run_id=owned_run_id).decoded_json_fields(
            operation="evaluate"
        )
        native_request = row["options"].get("native_request")
        if isinstance(native_request, dict) and native_request.get("demand") == "render":
            raise DomainOperationRefused("native render runs have no evaluated realization")
        if {"visual_request", "visual_group"} & row["options"].keys():
            raise DomainOperationRefused("visual evidence runs have no evaluated realization")
        if row["status"] in ("cancelled", "failed"):
            raise DomainOperationRefused("cancelled or failed run cannot finalize")
        if conn.execute(
            select(t.c.id).where(
                t.c.run_id == run_id, t.c.status.in_(["pending", "running", "awaiting_agent"])
            )
        ).first():
            raise DomainOperationRefused(
                "automated tasks are still open; finish them before finalization"
            )
        cuts = table("ops.input_cut")
        cut = conn.execute(
            select(cuts.c.id).where(cuts.c.run_id == run_id, cuts.c.final)
        ).scalar_one_or_none()
        if cut is None:
            cut = seal_cut(conn, owned_run_id, "evaluation", final=True)
    return consolidate_cut(engine, cut, output_realization_id, analytics=analytics)
