"""Read retained visual campaigns and reproduce their diagnostic scopes."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel
from sqlalchemy import select

from corpus_structure.serve.pdf_visual_evidence import VisualEvidencePin

from .metadata import table
from .operations import OperationConflict
from .visual_requests import (
    VISUAL_NOMINATION_VERSION,
    VISUAL_REQUEST_CODE_COMMIT,
    VISUAL_REQUEST_CUT,
    VisualSelection,
    _visual_mapping_raw_pin,
    _visual_product_pin,
    _visual_task,
)
from .visual_routing import VisualRouteReport

VisualDispatchMode = Literal["selective", "all-page"]
_REQUEST_REASONS = {
    "missing_structure",
    "incomplete_request",
    "incomplete_ocr_region",
    "located_disagreement",
    "omitted_crop",
}


class VisualMemberProgress(BaseModel):
    selection: VisualSelection
    inference: str | None = None
    mapping: str | None = None
    raw: VisualEvidencePin | None = None
    mapped: VisualEvidencePin | None = None


class VisualGroupProgress(BaseModel):
    run_id: int
    status: str
    cut_id: int | None = None
    members: tuple[VisualMemberProgress, ...]


class VisualDispatchProgress(BaseModel):
    nomination_run_id: int
    source_cut: int
    mode: VisualDispatchMode
    routes: VisualRouteReport
    groups: tuple[VisualGroupProgress, ...]


def read_visual_dispatch_progress(conn, nomination_run_id: int) -> VisualDispatchProgress:
    """Project decisions and all observable member effects from one native snapshot."""
    runs, cuts = map(table, ("ops.run", "ops.input_cut"))
    row = conn.execute(
        select(
            runs.c.options, runs.c.project_id, runs.c.release_id, runs.c.input_realization_id
        ).where(
            runs.c.id == nomination_run_id,
            runs.c.sealed,
            runs.c.code_commit == VISUAL_REQUEST_CODE_COMMIT,
        )
    ).one_or_none()
    if row is None:
        raise OperationConflict("current visual nomination is unavailable")
    nomination = row.options.get("visual_nomination")
    if nomination is None or nomination.get("version") != VISUAL_NOMINATION_VERSION:
        raise OperationConflict("current visual nomination is unavailable")
    group_rows = conn.execute(
        select(runs.c.id, runs.c.status, runs.c.options["visual_group"], cuts.c.id)
        .outerjoin(
            cuts,
            (cuts.c.run_id == runs.c.id) & cuts.c.final & (cuts.c.name == VISUAL_REQUEST_CUT),
        )
        .where(
            runs.c.code_commit == VISUAL_REQUEST_CODE_COMMIT,
            runs.c.project_id == row.project_id,
            runs.c.release_id == row.release_id,
            runs.c.input_realization_id == row.input_realization_id,
            runs.c.options.contains({"visual_nomination_run_id": nomination_run_id}),
            runs.c.options.has_key("visual_group"),
        )
        .order_by(runs.c.id)
    )
    groups = []
    for run_id, status, group, cut_id in group_rows:
        members = []
        for scope in group["selections"]:
            if scope not in nomination["selections"]:
                raise OperationConflict("visual progress differs from the frozen nomination")
            selection = VisualSelection.model_validate(scope)
            inference = _visual_task(conn, run_id, "inference", selection)
            mapping = _visual_task(conn, run_id, "mapping", selection)
            raw = _visual_product_pin(conn, inference) or _visual_mapping_raw_pin(
                conn, mapping, selection, row.project_id
            )
            members.append(
                VisualMemberProgress(
                    selection=selection,
                    inference=inference.status
                    if inference is not None
                    else "replayed"
                    if raw
                    else None,
                    mapping=mapping.status if mapping is not None else None,
                    raw=raw,
                    mapped=_visual_product_pin(conn, mapping),
                )
            )
        groups.append(
            VisualGroupProgress(run_id=run_id, status=status, cut_id=cut_id, members=tuple(members))
        )
    return VisualDispatchProgress(
        nomination_run_id=nomination_run_id,
        source_cut=nomination["demand"]["source_cut"],
        mode=nomination["demand"]["mode"],
        routes=VisualRouteReport.model_validate(nomination["routes"]),
        groups=tuple(groups),
    )


def visual_dispatch_selections(
    report: VisualRouteReport, mode: VisualDispatchMode
) -> tuple[VisualSelection, ...]:
    """Reproduce distinct scopes for historical and comparative analysis."""
    selections = []
    for page in report.pages:
        if mode == "all-page":
            selections.append(VisualSelection(source=report.source, page_no=page.page_no))
        elif page.action == "recognize":
            for reason in page.reasons:
                if reason.code in _REQUEST_REASONS:
                    crop = reason.crop.model_dump() if reason.crop else {}
                    selections.append(
                        VisualSelection(source=report.source, page_no=page.page_no, **crop)
                    )
    return tuple(dict.fromkeys(selections))
