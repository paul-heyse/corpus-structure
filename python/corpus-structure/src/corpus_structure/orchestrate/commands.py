"""What `ci project init`, `ci run`, `ci run cancel`, `ci status` and `ci tasks` do (orchestration
§3.13; D8 §4; D6 §8), with the result models their `--json` emits. The Typer layer is
`cli/orchestrate.py`; everything here takes an engine.

**Projects.** A run belongs to one project: `--project NAME`, or the only project there is.

**`ci run`** (P0-O-1: over the project's whole corpus; `--slice`, `--scope` and `--corpus` are
P0-O-2's) records the pack's versions, creates the run with the explicit options, takes the run's
liveness lock on its own connection, runs it through the graph and reports the run's final status
and every option as resolved with its source.

**`ci status [RUN]`** (the latest run by default): task counts per stage by status and reason; the
cut and the final M19 task once sealed; agent tasks unresolved as of the cut (or open, unsealed);
the orphaned runs. The CLI adds the settings it resolved.

**`ci tasks [RUN] [--status S] [--method M]`**: at most `limit` tasks (unit key, configuration,
status, reason, rule key, cost) and the count of all that match.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, JsonValue
from sqlalchemy import Connection, Engine, text

from corpus_structure.core.vocab import AgentMode, MethodTier, RunKind, RunStatus, TaskStatus
from corpus_structure.orchestrate import fates, project, runs
from corpus_structure.orchestrate.registry import MethodRegistry
from corpus_structure.orchestrate.runner import Evaluate, Graph, PassRunner, Runner


class CommandError(ValueError):
    """A refused command; its message is what the operator reads."""


def project_id(conn: Connection, name: str | None) -> tuple[int, str]:
    """The project named, or the only one."""
    rows = conn.execute(text("SELECT id, name, domain FROM meta.project ORDER BY id")).all()
    if name is not None:
        rows = [r for r in rows if r.name == name]
        if not rows:
            raise CommandError(f"no project {name!r}")
    if not rows:
        raise CommandError("no project: run `ci project init` first")
    if len(rows) > 1:
        raise CommandError(f"{len(rows)} projects: name one with --project")
    return int(rows[0].id), str(rows[0].domain)


# --- ci run -----------------------------------------------------------------------------------


class RunReport(BaseModel):
    run_id: int
    status: RunStatus
    options: runs.OptionsReport


def start_run(
    engine: Engine,
    *,
    url: str,
    registry_for: Any,  # (pack root) -> MethodRegistry
    graph: Graph,
    run_pass: PassRunner,
    evaluate: Evaluate | None = None,
    project_name: str | None = None,
    kind: RunKind = RunKind.FULL,
    phase: int = 0,
    explicit: dict[str, Any] | None = None,
    settings: Any = None,
    domains: Path | None = None,
    method_settings: Any = None,
    slice: str | None = None,
    scope: str | None = None,
    corpus: str | None = None,
) -> RunReport:
    """Create the run and run it to its end (module doc)."""
    from corpus_structure.schema.pack import DOMAINS

    with engine.begin() as conn:
        pid, domain = project_id(conn, project_name)
        pack = (domains or DOMAINS) / domain
        registry: MethodRegistry = registry_for(pack)
        versions = project.ensure_pack_versions(conn, pid, pack, "human:operator")
        documents = [
            tuple(r)
            for r in conn.execute(
                text(
                    "SELECT key, content_hash FROM kb.document WHERE project_id = :p ORDER BY key"
                ),
                {"p": pid},
            )
        ]
        if not documents:
            raise CommandError("the project has no documents")
        from corpus_structure.orchestrate.slices import record
        corpus_record, scope_record = record(conn, pid, pack, slice=slice, scope=scope, corpus=corpus)
        if slice:
            kind = RunKind.SLICE
        explicit = dict(explicit or {})
        if scope_record is not None:
            explicit['scope'] = scope_record
        if graph.policy_propose and phase == 0 and kind == RunKind.FULL and scope_record is None:
            raise CommandError('phase 0 full run requires a scope')
        selected_keys = set(corpus_record['documents'])
        documents = [d for d in documents if d[0] in selected_keys]
        debug_slice_id = None
        if slice:
            import yaml
            from corpus_structure.core.db import metadata
            from sqlalchemy.dialects.postgresql import insert
            declarations = yaml.safe_load((pack / 'slices.yaml').read_text())
            declarations = declarations.get('slices', declarations)
            table = metadata.tables['ops.debug_slice']
            stmt = insert(table).values(project_id=pid, name=slice, selector=declarations[slice])
            debug_slice_id = conn.execute(stmt.on_conflict_do_update(
                index_elements=['project_id', 'name'], set_={'selector': stmt.excluded.selector}
            ).returning(table.c.id)).scalar_one()
        created = runs.create_run(
            conn,
            project_id=pid,
            kind=kind,
            versions=versions,
            registry=registry,
            documents=documents,
            corpus=corpus_record,
            debug_slice_id=debug_slice_id,
            phase=phase,
            explicit=explicit,
            settings=settings,
        )
        if graph.policy_propose and created.options.options.agent_mode == AgentMode.WAIT:
            raise CommandError('the phase 0 wait barrier is not implemented; use agent_mode=complete')
    runner = Runner(engine, registry, graph, run_pass, evaluate, method_settings)
    with runs.Liveness(url, created.id):
        status = runner.run(created.id)
    return RunReport(run_id=created.id, status=status, options=created.options)


class CancelReport(BaseModel):
    run_id: int
    tasks_cancelled: int


def cancel(engine: Engine, run_id: int) -> CancelReport:
    with engine.begin() as conn:
        try:
            n = runs.cancel_run(conn, run_id)
        except runs.IllegalTransition as error:
            raise CommandError(str(error)) from None
    return CancelReport(run_id=run_id, tasks_cancelled=n)


# --- ci status --------------------------------------------------------------------------------


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


def _run_id(conn: Connection, run_id: int | None) -> int | None:
    if run_id is not None:
        if conn.execute(text("SELECT 1 FROM ops.run WHERE id = :r"), {"r": run_id}).first() is None:
            raise CommandError(f"no run {run_id}")
        return run_id
    latest = conn.execute(text("SELECT max(id) FROM ops.run")).scalar()
    return None if latest is None else int(latest)


def status(conn: Connection, run_id: int | None = None) -> StatusReport:
    run = _run_id(conn, run_id)
    orphans = runs.orphaned(conn)
    if run is None:
        return StatusReport(run=None, orphaned=orphans)
    row = conn.execute(
        text(
            "SELECT kind, status, started_at, cut_at, cut_m19_task_id, finished_at "
            "FROM ops.run WHERE id = :r"
        ),
        {"r": run},
    ).one()
    counts = conn.execute(
        text(
            "SELECT t.stage, t.status, t.reason, count(*) AS n FROM ops.task t WHERE t.run_id = :r "
            "GROUP BY t.stage, t.status, t.reason ORDER BY min(t.id), t.status, t.reason"
        ),
        {"r": run},
    )
    return StatusReport(
        run=RunProgress(
            run_id=run,
            kind=row.kind,
            status=row.status,
            started_at=row.started_at,
            cut_at=row.cut_at,
            cut_m19_task_id=row.cut_m19_task_id,
            finished_at=row.finished_at,
            stages=[
                StageCount(stage=c.stage, status=c.status, reason=c.reason, count=int(c.n))
                for c in counts
            ],
            unresolved_agent_tasks=fates.unresolved(conn, run, stage=None, tier=MethodTier.AGENT),
        ),
        orphaned=orphans,
    )


# --- ci tasks ---------------------------------------------------------------------------------


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


def task_listing(
    conn: Connection,
    run_id: int | None = None,
    *,
    statuses: Sequence[TaskStatus] = (),
    methods: Sequence[str] = (),
    limit: int = 50,
) -> TaskListing:
    run = _run_id(conn, run_id)
    if run is None:
        return TaskListing(run_id=None, tasks=[], total=0, limit=limit)
    where = ["t.run_id = :r"]
    params: dict[str, Any] = {"r": run, "limit": limit}
    if statuses:
        where.append("t.status = ANY(:statuses)")
        params["statuses"] = [s.value for s in statuses]
    if methods:
        where.append("m.name = ANY(:methods)")
        params["methods"] = list(methods)
    sql = (
        "SELECT t.id, t.stage, t.unit_key, m.name || '/' || c.name AS config, t.status, t.reason, "
        "p.rule_key, t.cost, count(*) OVER () AS total FROM ops.task t "
        "JOIN ops.method_config c ON c.id = t.method_config_id JOIN ops.method m ON m.id = "
        "c.method_id LEFT JOIN ops.policy_rule p ON p.id = t.trigger_rule_id WHERE "
        + " AND ".join(where)
        + " ORDER BY t.id LIMIT :limit"
    )
    rows = conn.execute(text(sql), params).all()
    total = int(rows[0].total) if rows else 0
    return TaskListing(
        run_id=run,
        tasks=[
            TaskRow(
                id=int(r.id),
                stage=r.stage,
                unit_key=r.unit_key,
                config=r.config,
                status=r.status,
                reason=r.reason,
                rule_key=r.rule_key,
                cost=r.cost or {},
            )
            for r in rows
        ],
        total=total,
        limit=limit,
    )


def start_bound_run(engine: Engine, *, release_id: str, realization_id: str,
                    project_id: str, domain: str, method_settings: Any,
                    phase: int = 0, domains: Path | None = None,fresh: Sequence[str]=()):
    """Explicit semantic source execution through the current command entry point."""
    from corpus_structure.semantic.releases import load_release
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.operations import OperationBinding
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.orchestrate.semantic import run_source_methods
    from corpus_structure.orchestrate.phase0 import registry, PHASE0
    from corpus_structure.schema.pack import DOMAINS
    from sqlalchemy import select
    with engine.connect() as conn:
        prepared=load_release(conn,release_id)
        r=table('data.realization')
        row=conn.execute(select(r).where(r.c.realization_id==realization_id,r.c.project_id==project_id)).mappings().one()
        if row['release_id']!=release_id:raise CommandError('requested realization has another semantic release')
        binding=OperationBinding(release_id,realization_id,row['data_revision'],canonical_bytes({'domain':domain,'release':release_id}))
    return run_source_methods(engine,project_id=project_id,prepared=prepared,binding=binding,
        registry=registry((domains or DOMAINS)/domain),graph=PHASE0,method_settings=method_settings,phase=phase,
        guideline=((domains or DOMAINS)/domain/'guideline.md').read_text(),fresh=fresh)
