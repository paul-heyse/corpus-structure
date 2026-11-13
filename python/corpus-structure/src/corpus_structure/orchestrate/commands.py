"""Current semantic project/run/task command operations and their typed reports."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field, JsonValue
from sqlalchemy import Connection, Engine

from corpus_structure.core.vocab import TaskStatus
from corpus_structure.semantic.pm2_coverage import ScopeCoverage, scope_coverage
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.settings import AnalyticsSettings

from .source_progress import SourceOperationProgress, read_source_operation_progress

if TYPE_CHECKING:
    from corpus_structure.orchestrate.semantic import SourceRunCreated


from .source_request import SourceRequestError, SourceWorkflow

CommandError = SourceRequestError


class CancelReport(BaseModel):
    run_id: int
    tasks_cancelled: int


class StageCount(BaseModel):
    stage: str
    status: str
    reason: str | None
    count: int


class RunProgress(BaseModel):
    run_id: int
    kind: str
    status: str
    started_at: datetime | None
    cut_at: datetime | None
    cut_m19_task_id: int | None
    finished_at: datetime | None
    release_id: str
    cut_id: int | None
    cut_name: str | None
    output_realization_id: str | None
    stages: list[StageCount]
    unresolved_agent_tasks: int
    readiness: Literal["completed", "source_ready", "incomplete", "terminal"]
    supervisor: Literal["active", "waiting", "orphaned", "unassessed", "terminal"]
    physical_policy: dict[str, JsonValue] | None = None
    characterization_anchor: int | None = None
    characterization_region: int | None = None
    characterization_stage: tuple[str, ...] | None = None
    operation: SourceOperationProgress | None = None
    operation_unavailable_reason: str | None = None
    pm2_scope_coverage: tuple[ScopeCoverage, ...] | None = Field(
        default=None, exclude_if=lambda value: value is None
    )


class StatusReport(BaseModel):
    run: RunProgress | None
    orphaned: list[int] | None = None
    settings: dict[str, str] = {}


class TaskRow(BaseModel):
    id: int
    stage: str
    unit_key: str | None
    config: str
    status: str
    reason: str | None
    rule_key: str | None
    cost: dict[str, JsonValue]


class TaskListing(BaseModel):
    run_id: int | None
    tasks: list[TaskRow]
    total: int
    limit: int


def start_bound_run(
    engine: Engine,
    *,
    release_id: str,
    realization_id: str,
    project_id: str,
    domain: str | None = None,
    method_settings: Any,
    phase: int = 0,
    domains: Path | None = None,
    fresh: Sequence[str] = (),
    slice: str | None = None,
    scope: str | None = None,
    whole_document: bool = False,
    source_membership: Literal["direct", "descendants"] | None = None,
    corpus: str | None = None,
    agent_mode: str = "complete",
    agent_reuse: str = "full",
    registry_for: Any = None,
    graph: Any = None,
    native_product: ProductReference | None = None,
    integrated_product: ProductReference | None = None,
    extraction_policy: str = "phase0",
    m1_configuration: str = "default",
    record_policy: dict[str, Any] | None = None,
    source_only: bool = False,
    characterization_views: Sequence[ProductReference] = (),
    workflow: SourceWorkflow | None = None,
    on_created: Callable[[SourceRunCreated], None] | None = None,
):
    from .source_operation import run_source_operation
    from .source_request import SourceRunRequest, source_selection, source_workflow

    if workflow is not None and (
        extraction_policy != "phase0"
        or m1_configuration != "default"
        or record_policy is not None
        or source_only
        or characterization_views
    ):
        raise SourceRequestError("explicit workflow cannot combine legacy workflow selectors")
    request = SourceRunRequest(
        project_id=project_id,
        release_id=release_id,
        realization_id=realization_id,
        domain=domain,
        selection=source_selection(
            slice=slice, scope=scope, whole_document=whole_document, corpus=corpus
        ),
        workflow=workflow
        if workflow is not None
        else source_workflow(
            extraction_policy=extraction_policy,
            m1_configuration=m1_configuration,
            record_policy=record_policy,
            source_only=source_only,
            characterization_views=characterization_views,
        ),
        membership=source_membership,
        native_product=native_product,
        integrated_product=integrated_product,
        fresh=tuple(fresh),
        phase=phase,
        agent_mode=agent_mode,
        agent_reuse=agent_reuse,
    )
    return run_source_operation(
        engine,
        request,
        method_settings,
        domains=domains,
        graph=graph,
        registry_for=registry_for,
        on_created=on_created,
    ).run


def resolve_source_domain(
    conn: Connection,
    project_id: str,
    release_id: str,
    domain: str | None,
    *,
    domains: Path | None = None,
) -> str:
    """Resolve a source pack from the release's archived module identities."""
    import json

    import yaml

    from corpus_structure.schema.pack import DOMAINS
    from corpus_structure.semantic.releases import open_release

    try:
        archive = json.loads(open_release(conn, release_id).manifest)
    except KeyError as error:
        raise CommandError("selected release has no archived executable pack") from error
    modules = {name for name, _ in archive["sources"]}
    candidates = []
    for path in sorted((domains or DOMAINS).glob("*/semantic.yaml")):
        if domain is not None and path.parent.name != domain:
            continue
        declaration = yaml.safe_load(path.read_bytes())
        if isinstance(declaration, dict) and declaration.get("name") in modules:
            candidates.append(path.parent.name)
    if len(candidates) == 1:
        return candidates[0]
    if candidates:
        raise CommandError(f"project {project_id!r} has multiple bound packs; select --domain")
    raise CommandError(f"project {project_id!r} has no matching executable pack for this release")


def cancel_bound_run(engine: Engine, run_id: int) -> CancelReport:
    from corpus_structure.semantic.operation_results import RunId
    from corpus_structure.semantic.operations import end_source_run

    with engine.begin() as conn:
        return CancelReport(run_id=run_id, tasks_cancelled=end_source_run(conn, RunId(run_id)))


def _bound_run_id(conn: Connection, run_id: int | None, project_id: str | None) -> int | None:
    from sqlalchemy import select

    from corpus_structure.semantic.metadata import table

    runs = table("ops.run")
    query = select(runs.c.id)
    if run_id is not None:
        query = query.where(runs.c.id == run_id)
    if project_id is not None:
        query = query.where(runs.c.project_id == project_id)
    found = conn.execute(query.order_by(runs.c.id.desc()).limit(1)).scalar_one_or_none()
    if found is None and run_id is not None:
        raise CommandError(f"no semantic run {run_id} in the selected project")
    return found


def bound_task_listing(
    conn: Connection,
    run_id: int | None = None,
    *,
    project_id: str | None = None,
    statuses: Sequence[TaskStatus] = (),
    methods: Sequence[str] = (),
    limit: int = 50,
) -> TaskListing:
    from sqlalchemy import func, select

    from corpus_structure.semantic.metadata import table

    if limit < 0:
        raise CommandError("task limit must be nonnegative")
    run = _bound_run_id(conn, run_id, project_id)
    if run is None:
        return TaskListing(run_id=None, tasks=[], total=0, limit=limit)
    t, c, m = table("ops.task"), table("ops.method_config"), table("ops.method")
    query = (
        select(
            t.c.id,
            t.c.stage,
            t.c.unit_key,
            t.c.trigger,
            t.c.status,
            t.c.reason,
            t.c.cost,
            c.c.name.label("configuration"),
            m.c.name.label("method"),
        )
        .join(c, t.c.method_config_id == c.c.id)
        .join(m, c.c.method_id == m.c.id)
        .where(t.c.run_id == run)
    )
    if statuses:
        query = query.where(t.c.status.in_([s.value for s in statuses]))
    if methods:
        query = query.where(m.c.name.in_(methods))
    total = conn.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    rows = conn.execute(query.order_by(t.c.id).limit(limit)).mappings()
    return TaskListing(
        run_id=run,
        total=total,
        limit=limit,
        tasks=[
            TaskRow(
                id=r["id"],
                stage=r["stage"],
                unit_key=r["unit_key"],
                config=r["method"]
                + "/"
                + (r.get("trigger") or {}).get("configuration_name", r["configuration"]),
                status=r["status"],
                reason=r["reason"],
                rule_key=(r.get("trigger") or {}).get("rule_key"),
                cost=r["cost"] or {},
            )
            for r in rows
        ],
    )


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
    from corpus_structure.semantic.visual_requests import VISUAL_REQUEST_CODE_COMMIT

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
        if row["code_commit"] == VISUAL_REQUEST_CODE_COMMIT and (
            {"visual_request", "visual_group"} & row["options"].keys()
        ):
            raise DomainOperationRefused("visual evidence runs have no evaluated realization")
        if row["status"] in ("cancelled", "failed"):
            raise DomainOperationRefused("cancelled or failed run cannot finalize")
        unfinished = row["result_realization_id"] is None
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
    if unfinished:
        from corpus_structure.semantic.source_frames import backfill_source_frames

        backfill_source_frames(engine, run_id)
    return consolidate_cut(engine, cut, output_realization_id, analytics=analytics)


def bound_status(
    conn: Connection,
    run_id: int | None = None,
    *,
    project_id: str | None = None,
    operation_cursor: str | None = None,
    operation_region_limit: int = 8,
) -> StatusReport:
    from sqlalchemy import func, select

    from corpus_structure.orchestrate.liveness import observe_supervisor
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.visual_requests import (
        VISUAL_REQUEST_CODE_COMMIT,
        VISUAL_REQUEST_CUT,
    )

    run = _bound_run_id(conn, run_id, project_id)
    if run is None:
        return StatusReport(run=None, orphaned=None)
    r, t, c, m, cut = map(
        table, ("ops.run", "ops.task", "ops.method_config", "ops.method", "ops.input_cut")
    )
    row = (
        conn.execute(
            select(
                *(column for column in r.c if column.name != "options"),
                r.c.options.op("-")("characterization_demand").label("options"),
                r.c.options.op("?", is_comparison=True)("characterization_demand").label(
                    "has_characterization_demand"
                ),
            ).where(r.c.id == run)
        )
        .mappings()
        .one()
    )
    latest_cut = conn.execute(
        select(cut.c.id, cut.c.name, cut.c.final)
        .where(cut.c.run_id == run)
        .order_by(cut.c.final.desc(), cut.c.id.desc())
        .limit(1)
    ).one_or_none()
    counts = conn.execute(
        select(t.c.stage, t.c.status, t.c.reason, func.count().label("count"))
        .where(t.c.run_id == run)
        .group_by(t.c.stage, t.c.status, t.c.reason)
        .order_by(t.c.stage, t.c.status, t.c.reason)
    ).mappings()
    unresolved = conn.execute(
        select(func.count())
        .select_from(t)
        .join(c, t.c.method_config_id == c.c.id)
        .join(m, c.c.method_id == m.c.id)
        .where(
            t.c.run_id == run,
            m.c.tier == "agent",
            t.c.status.in_(["pending", "running", "awaiting_agent"]),
        )
    ).scalar_one()
    status = row["status"]
    visual_ready = (
        row["code_commit"] == VISUAL_REQUEST_CODE_COMMIT
        and ({"visual_request", "visual_group"} & row["options"].keys())
        and row["sealed"]
        and latest_cut is not None
        and latest_cut.final
        and latest_cut.name == VISUAL_REQUEST_CUT
    )
    native_request = row["options"].get("native_request")
    render_ready = (
        isinstance(native_request, dict)
        and native_request.get("demand") == "render"
        and status == "consolidating"
        and row["sealed"]
        and latest_cut is not None
        and latest_cut.final
        and latest_cut.name == "native-request-source"
    )
    evidence_ready = visual_ready or render_ready
    source_ready = evidence_ready or run_source_ready(conn, run)
    if evidence_ready:
        status = "source_ready"
    elif status == "running":
        if unresolved:
            status = "awaiting_agent"
        elif source_ready:
            status = "source_ready"
    readiness = run_readiness(row["status"], row["result_realization_id"], source_ready)
    supervisor: Literal["active", "waiting", "orphaned", "unassessed", "terminal"]
    if readiness in {"terminal", "completed"}:
        supervisor = "terminal"
    else:
        active, waiting = observe_supervisor(conn, run)
        if active:
            supervisor = "active"
        elif evidence_ready or (waiting is True and row["status"] == "running"):
            supervisor = "waiting"
        elif waiting is not None:
            supervisor = "orphaned"
        else:
            supervisor = "unassessed"
    operation = read_source_operation_progress(
        conn, row, cursor=operation_cursor, region_limit=operation_region_limit
    )
    return StatusReport(
        run=RunProgress(
            run_id=run,
            kind=row["kind"],
            status=status,
            started_at=None,
            cut_at=None,
            cut_m19_task_id=None,
            finished_at=None,
            release_id=row["release_id"],
            cut_id=latest_cut.id if latest_cut else None,
            cut_name=latest_cut.name if latest_cut else None,
            output_realization_id=row["result_realization_id"],
            physical_policy=row["options"].get("physical_policy"),
            characterization_anchor=(
                run
                if row["has_characterization_demand"]
                else row["options"].get("characterization_anchor")
            ),
            characterization_region=row["options"].get("characterization_region"),
            characterization_stage=row["options"].get("characterization_stage"),
            operation=operation,
            operation_unavailable_reason=None
            if operation is not None
            else (
                "No native source-operation link or characterization anchor "
                "is recorded for this run."
            ),
            stages=[StageCount.model_validate(dict(x)) for x in counts],
            unresolved_agent_tasks=unresolved,
            readiness=readiness,
            supervisor=supervisor,
            pm2_scope_coverage=(
                scope_coverage(conn, run, row["options"]["pm2_scope_intents"])
                if "pm2_scope_intents" in row["options"]
                else None
            ),
        ),
        orphaned=[run] if supervisor == "orphaned" else None if supervisor == "unassessed" else [],
    )


def run_source_ready(conn: Connection, run_id: int) -> bool:
    from sqlalchemy import select

    from corpus_structure.semantic.metadata import table

    cuts = table("ops.input_cut")
    return (
        conn.scalar(select(cuts.c.id).where(cuts.c.run_id == run_id, cuts.c.name == "source-ready"))
        is not None
    )


def run_readiness(
    status: str, output_realization: str | None, source_ready: bool
) -> Literal["completed", "source_ready", "incomplete", "terminal"]:
    if status == "finished" and output_realization is not None:
        return "completed"
    if status in {"cancelled", "failed", "finished"}:
        return "terminal"
    if source_ready:
        return "source_ready"
    return "incomplete"
