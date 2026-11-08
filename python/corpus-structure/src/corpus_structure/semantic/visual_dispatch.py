"""Dispatch optional visual work against an already published source-ready cut."""

from __future__ import annotations

from functools import partial
from hashlib import sha256
from itertools import batched
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel
from sqlalchemy import select, text

from .identity import canonical_bytes
from .metadata import table
from .operations import OperationConflict, seal_cut
from .query import read_snapshot
from .visual_requests import (
    MAX_VISUAL_GROUP,
    VISUAL_REQUEST_CODE_COMMIT,
    VisualGroupResult,
    VisualSelection,
    _bind_visual_run,
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
    nomination_run_id: int
    source_cut: int
    mode: VisualDispatchMode
    routes: VisualRouteReport
    groups: tuple[VisualGroupResult, ...]
    retried_failed_runs: tuple[int, ...] = ()
    result_id: str | None = None
    operation_account: dict | None = None


def _nominate(
    engine,
    source,
    source_cut,
    semantic_release,
    realization,
    mode,
    first,
    limit,
    artifacts,
    nomination_run_id,
):
    """Persist the decisions before dispatch, including a decision with no work."""
    runs = table("ops.run")
    demand = {
        "source": source.model_dump(mode="json"),
        "source_cut": source_cut,
        "release": semantic_release,
        "realization": realization,
        "mode": mode,
        "first": first,
        "limit": limit,
        "artifacts": str(artifacts),
    }
    if nomination_run_id is not None:
        with read_snapshot(engine) as conn:
            _require_dispatch_cut(conn, source, source_cut, semantic_release, realization)
            row = conn.execute(
                select(runs.c.options, runs.c.sealed).where(
                    runs.c.id == nomination_run_id,
                    runs.c.code_commit == VISUAL_REQUEST_CODE_COMMIT,
                )
            ).one_or_none()
            retained = row.options.get("visual_nomination") if row and row.sealed else None
            if (
                retained is None
                or retained.get("version") != "visual-nomination-v1"
                or retained.get("demand") != demand
            ):
                raise OperationConflict("visual dispatch differs from its retained nomination")
            return (
                nomination_run_id,
                VisualRouteReport.model_validate(retained["routes"]),
                tuple(VisualSelection.model_validate(scope) for scope in retained["selections"]),
            )

    with read_snapshot(engine) as conn:
        _require_dispatch_cut(conn, source, source_cut, semantic_release, realization)
        routes = read_visual_routes(conn, source, first=first, limit=limit)
    selections = visual_dispatch_selections(routes, mode)
    nomination = {
        "version": "visual-nomination-v1",
        "demand": demand,
        "routes": routes.model_dump(mode="json"),
        "selections": [selection.scope() for selection in selections],
    }
    identity = sha256(canonical_bytes(nomination)).hexdigest()
    with engine.begin() as conn:
        _require_dispatch_cut(conn, source, source_cut, semantic_release, realization)
        # Equal demand and decisions can replay the same run. The advisory lock
        # covers publication only and is released before any provider work.
        conn.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": identity}
        )
        retained = conn.scalar(
            select(runs.c.id)
            .where(
                runs.c.code_commit == VISUAL_REQUEST_CODE_COMMIT,
                runs.c.options["visual_nomination_id"].as_string() == identity,
                runs.c.options["visual_nomination"] == nomination,
                runs.c.sealed,
            )
            .order_by(runs.c.id)
            .limit(1)
        )
        if retained is not None:
            return retained, routes, selections
        project_id = conn.scalar(select(runs.c.project_id).where(runs.c.id == source.run_id))
        run_id, _, _, _ = _bind_visual_run(
            conn,
            project_id,
            semantic_release,
            realization,
            recognize=False,
            options={"visual_nomination": nomination, "visual_nomination_id": identity},
            resume_run_id=None,
        )
        seal_cut(conn, run_id, "visual-nomination", final=True)
        return run_id, routes, selections


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
    nomination_run_id: int | None = None,
    report_progress=None,
) -> VisualDispatchResult:
    """Evaluate one range, then settle its optional work through independent managed runs."""
    if mode not in ("selective", "all-page"):
        raise ValueError("visual dispatch mode must be selective or all-page")
    artifacts = artifacts.resolve()
    nomination_run_id, routes, requested = _nominate(
        engine,
        source,
        source_cut,
        semantic_release,
        realization,
        mode,
        first,
        limit,
        artifacts,
        nomination_run_id,
    )
    if report_progress is not None:
        report_progress(nomination_run_id, ())
    groups = []
    retried = []
    settled_ids = []
    for selections in batched(requested, MAX_VISUAL_GROUP, strict=False):
        key = sha256(
            canonical_bytes(
                {
                    "operation": "visual-postpublication-v3",
                    "nomination_run_id": nomination_run_id,
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
            nomination_run_id=nomination_run_id,
        )
        group = settle_group(campaign_group=key)
        settled_ids.append(group.run_id)
        if report_progress is not None:
            report_progress(nomination_run_id, tuple(settled_ids))
        if retry_failed and group.status == "failed":
            retried.append(group.run_id)
            retry_key = sha256(canonical_bytes({"retry_of": key, "attempt": 2})).hexdigest()
            group = settle_group(campaign_group=retry_key)
            settled_ids.append(group.run_id)
            if report_progress is not None:
                report_progress(nomination_run_id, tuple(settled_ids))
        groups.append(group)
    return VisualDispatchResult(
        nomination_run_id=nomination_run_id,
        source_cut=source_cut,
        mode=mode,
        routes=routes,
        groups=tuple(groups),
        retried_failed_runs=tuple(retried),
    )
