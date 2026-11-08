"""Dispatch optional visual work against an already published source-ready cut."""

from __future__ import annotations

from functools import partial
from hashlib import sha256
from itertools import batched
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel
from sqlalchemy import select

from .identity import canonical_bytes
from .metadata import table
from .query import read_snapshot
from .releases import open_release
from .runtime_bindings import installed_runtime_id
from .visual_requests import (
    MAX_VISUAL_GROUP,
    VisualGroupResult,
    VisualSelection,
    request_visual_group,
)
from .visual_routing import VisualRouteReport, read_visual_routes

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy import Engine

    from corpus_structure.serve.pdf_visual_evidence import VisualEvidencePin

VisualDispatchMode = Literal["selective", "all-page"]
_REQUEST_REASONS = {
    "missing_structure",
    "incomplete_request",
    "incomplete_ocr_region",
    "located_disagreement",
    "omitted_crop",
}


class VisualDispatchResult(BaseModel):
    source_cut: int
    mode: VisualDispatchMode
    routes: VisualRouteReport
    groups: tuple[VisualGroupResult, ...]
    retried_failed_runs: tuple[int, ...] = ()


def visual_dispatch_selections(
    report: VisualRouteReport, mode: VisualDispatchMode
) -> tuple[VisualSelection, ...]:
    """Coalesce equal effective requests without incorporating the nomination reasons."""
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


def _require_dispatch_cut(conn, source, source_cut, semantic_release, realization):
    cuts, members, runs, realizations = map(
        table, ("ops.input_cut", "ops.cut_task", "ops.run", "data.realization")
    )
    committed = conn.scalar(
        select(cuts.c.id)
        .join(runs, runs.c.id == cuts.c.run_id)
        .join(members, members.c.cut_id == cuts.c.id)
        .join(realizations, realizations.c.project_id == runs.c.project_id)
        .where(
            cuts.c.id == source_cut,
            cuts.c.run_id == source.run_id,
            cuts.c.name == "source-ready",
            members.c.task_id == source.task_id,
            members.c.origin_task_id == source.task_id,
            realizations.c.realization_id == realization,
            realizations.c.release_id == semantic_release,
            realizations.c.state == "active",
        )
        .limit(1)
    )
    if committed is None:
        raise ValueError(
            "visual dispatch requires the producing source-ready cut and active writer realization"
        )


def dispatch_visual_work(
    engine: Engine,
    *,
    source: VisualEvidencePin,
    source_cut: int,
    semantic_release: str,
    realization: str,
    mode: VisualDispatchMode,
    first: int,
    limit: int,
    artifacts: Path,
    receipts: Path,
    nemotron_endpoint: str | None,
    retry_failed: bool = False,
) -> VisualDispatchResult:
    """Evaluate one range, then settle its optional work through independent managed runs."""
    from corpus_structure.ingest.pdf_chandra import ChandraRuntime

    if mode not in ("selective", "all-page"):
        raise ValueError("visual dispatch mode must be selective or all-page")
    with read_snapshot(engine) as conn:
        _require_dispatch_cut(conn, source, source_cut, semantic_release, realization)
        routes = read_visual_routes(conn, source, first=first, limit=limit)
        requested = visual_dispatch_selections(routes, mode)
        if not requested:
            return VisualDispatchResult(source_cut=source_cut, mode=mode, routes=routes, groups=())
        runtime_id = installed_runtime_id(open_release(conn, semantic_release))

    artifacts = artifacts.resolve()
    recipe = ChandraRuntime(artifacts).identity()
    groups = []
    retried = []
    for selections in batched(requested, MAX_VISUAL_GROUP, strict=False):
        key = sha256(
            canonical_bytes(
                {
                    "operation": "visual-postpublication-v2",
                    "runtime": runtime_id,
                    "recipe": recipe,
                    "release": semantic_release,
                    "realization": realization,
                    "artifacts": str(artifacts),
                    "selections": [selection.scope() for selection in selections],
                }
            )
        ).hexdigest()
        settle_group = partial(
            request_visual_group,
            engine,
            selections=selections,
            semantic_release=semantic_release,
            realization=realization,
            receipts=receipts,
            artifacts=artifacts,
            nemotron_endpoint=nemotron_endpoint,
        )
        group = settle_group(campaign_group=key)
        if retry_failed and group.status == "failed":
            retried.append(group.run_id)
            retry_key = sha256(canonical_bytes({"retry_of": key, "attempt": 2})).hexdigest()
            group = settle_group(campaign_group=retry_key)
        groups.append(group)
    return VisualDispatchResult(
        source_cut=source_cut,
        mode=mode,
        routes=routes,
        groups=tuple(groups),
        retried_failed_runs=tuple(retried),
    )
