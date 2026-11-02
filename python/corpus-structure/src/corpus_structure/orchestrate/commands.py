"""Current semantic project/run/task command operations and their typed reports."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, JsonValue
from sqlalchemy import Connection, Engine

from corpus_structure.core.vocab import TaskStatus
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.settings import AnalyticsSettings


class CommandError(ValueError):
    """A refused command; its message is what the operator reads."""


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
    stages: list[StageCount]
    unresolved_agent_tasks: int


class StatusReport(BaseModel):
    run: RunProgress | None
    orphaned: list[int]
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
    domain: str,
    method_settings: Any,
    phase: int = 0,
    domains: Path | None = None,
    fresh: Sequence[str] = (),
    slice: str | None = None,
    scope: str | None = None,
    corpus: str | None = None,
    agent_mode: str = "complete",
    agent_reuse: str = "full",
    registry_for: Any = None,
    graph: Any = None,
    native_product: ProductReference | None = None,
    integrated_product: ProductReference | None = None,
):
    """Explicit semantic source execution through the current command entry point."""
    from sqlalchemy import select

    from corpus_structure.orchestrate.phase0 import PHASE0, registry
    from corpus_structure.orchestrate.semantic import run_source_methods
    from corpus_structure.schema.pack import DOMAINS
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.operations import OperationBinding
    from corpus_structure.semantic.releases import load_release

    with engine.connect() as conn:
        prepared = load_release(conn, release_id)
        r = table("data.realization")
        row = (
            conn.execute(
                select(r).where(r.c.realization_id == realization_id, r.c.project_id == project_id)
            )
            .mappings()
            .one()
        )
        if row["release_id"] != release_id:
            raise CommandError("requested realization has another semantic release")
        binding = OperationBinding(
            release_id,
            realization_id,
            row["data_revision"],
            canonical_bytes({"domain": domain, "release": release_id}),
        )
        import yaml

        from corpus_structure.orchestrate.slices import records

        pack = (domains or DOMAINS) / domain
        d = table("kb.document")
        docs = [
            {
                "id": row["id"],
                "key": row["key"],
                "content_hash": row["content_hash"],
                "mime": row["mime"],
                "meta": row["meta"],
            }
            for row in conn.execute(
                select(d).where(d.c.project_id == project_id).order_by(d.c.key)
            ).mappings()
        ]
        data = (
            yaml.safe_load((pack / "slices.yaml").read_text())
            if (pack / "slices.yaml").exists()
            else {}
        )
        if slice is None and scope is None:
            scope = data.get("default_scope")
        corpus_record, scope_record = records(
            docs, data.get("slices", data), slice=slice, scope=scope, corpus=corpus
        )
        policy_source = (
            (pack / "policies.yaml").read_text() if (pack / "policies.yaml").exists() else None
        )
        if (
            phase == 0
            and (graph or PHASE0).policy_propose
            and policy_source is not None
            and scope_record is None
        ):
            raise CommandError("phase 0 full run requires a scope or named slice")
    selected_graph = graph or PHASE0
    selected_registry = (registry_for or registry)((domains or DOMAINS) / domain)
    if native_product is not None and integrated_product is not None:
        raise CommandError("select one exact native or integrated PDF input role")
    if native_product is not None or integrated_product is not None:
        from corpus_structure.orchestrate.phase0 import bind_pdf_source

        native_configs = {
            (step.config.partition("/")[0], step.config.partition("/")[2] or "default")
            for _, steps in selected_graph.stages
            for step in steps
            if step.config.partition("/")[0] in {"ingest.pdf", "ingest.pdf_integrated"}
        }
        if len(native_configs) != 1:
            raise CommandError(
                "native source binding requires exactly one PDF ingestion configuration"
            )
        method_name, configuration = next(iter(native_configs))
        input_product = native_product if native_product is not None else integrated_product
        if input_product is None:
            raise CommandError("PDF input product is missing")
        selected_registry = bind_pdf_source(
            selected_registry,
            input_product,
            configuration=configuration,
            method_name=method_name,
            input_role="native" if native_product is not None else "integrated",
        )
    return run_source_methods(
        engine,
        project_id=project_id,
        domain=domain,
        prepared=prepared,
        binding=binding,
        registry=selected_registry,
        graph=selected_graph,
        method_settings=method_settings,
        phase=phase,
        guideline=((domains or DOMAINS) / domain / "guideline.md").read_text(),
        fresh=fresh,
        corpus_record=corpus_record,
        scope_record=scope_record,
        policy_source=policy_source,
        agent_mode=agent_mode,
        agent_reuse=agent_reuse,
        kind="slice" if slice else "full",
    )


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
        select(t, c.c.name.label("configuration"), m.c.name.label("method"))
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
    conn: Connection, run_id: int | None = None, *, project_id: str | None = None
) -> StatusReport:
    from sqlalchemy import func, select

    from corpus_structure.semantic.metadata import table

    run = _bound_run_id(conn, run_id, project_id)
    if run is None:
        return StatusReport(run=None, orphaned=[])
    r, t, c, m, cut = map(
        table, ("ops.run", "ops.task", "ops.method_config", "ops.method", "ops.input_cut")
    )
    row = conn.execute(select(r).where(r.c.id == run)).mappings().one()
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
    if status == "running":
        if unresolved:
            status = "awaiting_agent"
        elif conn.execute(
            select(cut.c.id).where(cut.c.run_id == run, cut.c.name == "source-ready")
        ).first():
            status = "source_ready"
    return StatusReport(
        run=RunProgress(
            run_id=run,
            kind=row["kind"],
            status=status,
            started_at=None,
            cut_at=None,
            cut_m19_task_id=None,
            finished_at=None,
            stages=[StageCount.model_validate(dict(x)) for x in counts],
            unresolved_agent_tasks=unresolved,
        ),
        orphaned=[],
    )
