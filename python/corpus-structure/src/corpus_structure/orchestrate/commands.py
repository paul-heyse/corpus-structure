"""Current semantic project/run/task command operations and their typed reports."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field, JsonValue
from sqlalchemy import Connection, Engine

from corpus_structure.core.vocab import TaskStatus
from corpus_structure.semantic.pm2_coverage import ScopeCoverage, scope_coverage
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.settings import AnalyticsSettings

if TYPE_CHECKING:
    from corpus_structure.orchestrate.semantic import SourceRunCreated


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


def _consumer_characterization_options(registry, graph, configurations):
    """Freeze selected consumers' declarations in their one primary producer."""
    from corpus_structure.semantic.identity import canonical_bytes

    from .semantic import _source_configurations

    rules = {}
    for resolved in _source_configurations(registry, graph, configurations).values():
        config = resolved.config
        for owner in (config, getattr(config, "witnessed", None)):
            for rule in getattr(owner, "annotation_rules", ()):
                identity = (rule.rule, rule.variant)
                encoded = rule.model_dump(mode="json")
                if identity in rules and canonical_bytes(rules[identity]) != canonical_bytes(
                    encoded
                ):
                    raise CommandError(
                        "selected consumers require conflicting named rule "
                        f"{identity[0]}/{identity[1]}"
                    )
                rules[identity] = encoded
    return {"text.constructions": {"annotation_rules": list(rules.values())}}


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
    whole_document: bool = False,
    source_membership: str | None = None,
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
    on_created: Callable[[SourceRunCreated], None] | None = None,
):
    arguments = locals()
    from corpus_structure.semantic.execution_preparation import prepare_execution

    with engine.connect() as conn:
        execution = prepare_execution(conn, release_id, policy=method_settings.execution_policy)
    with execution:
        return _start_bound_run(execution, **arguments)


def _start_bound_run(
    execution,
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
    whole_document: bool = False,
    source_membership: str | None = None,
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
    on_created: Callable[[SourceRunCreated], None] | None = None,
):
    """Explicit semantic source execution through the current command entry point."""
    from sqlalchemy import select

    from corpus_structure.orchestrate.phase0 import PHASE0, registry
    from corpus_structure.orchestrate.semantic import run_source_methods
    from corpus_structure.schema.pack import DOMAINS
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.operations import OperationBinding

    if whole_document and (slice is not None or scope is not None):
        raise CommandError("whole-document is mutually exclusive with slice and scope")
    if source_membership not in {None, "direct", "descendants"}:
        raise CommandError("source membership must be direct or descendants")
    ordinary_graph = graph is None and registry_for is None
    if record_policy is not None and (
        extraction_policy != "m1-candidate" or m1_configuration not in {"readings", "contextual"}
    ):
        raise CommandError(
            "record policy parameters require an M1 reading-resolution configuration"
        )
    if extraction_policy not in {"phase0", "m1-candidate"}:
        raise CommandError("unknown extraction policy")
    if extraction_policy == "phase0" and m1_configuration != "default":
        raise CommandError("nondefault M1 configuration requires the m1-candidate policy")
    if extraction_policy == "m1-candidate":
        if native_product is not None or not isinstance(integrated_product, ProductReference):
            raise CommandError(
                "M1 requires one exact retained integrated PDF product; "
                "conversion and fallback are disabled"
            )
        if graph is not None or registry_for is not None:
            raise CommandError("M1 uses its explicit candidate graph and registry")
        from corpus_structure.orchestrate.m1 import registry as m1_registry
        from corpus_structure.orchestrate.m1 import source_graph

        graph, registry_for = source_graph(m1_configuration), m1_registry

    with engine.connect() as conn:
        prepared = execution.require_release(release_id)
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
        if extraction_policy == "phase0" and not whole_document and slice is None and scope is None:
            scope = data.get("default_scope")
        corpus_record, scope_record = records(
            docs, data.get("slices", data), slice=slice, scope=scope, corpus=corpus
        )
        retained_input_document = None
        if extraction_policy == "m1-candidate":
            from corpus_structure.orchestrate.m1 import retained_document

            if integrated_product is None:
                raise CommandError("M1 retained integrated product is missing")
            selected_keys = set(corpus_record["documents"])
            retained_input_document = retained_document(
                conn,
                integrated_product,
                prepared=prepared,
                project_id=project_id,
                documents=[document for document in docs if document["key"] in selected_keys],
            )
            # An exact product consumes its one registered original, not every PDF
            # in the project or a pack's incidental acquisition default.
            selected_docs = [
                document for document in docs if document["id"] == retained_input_document.id
            ]
            corpus_record, scope_record = records(
                selected_docs, data.get("slices", data), slice=slice, scope=scope, corpus=corpus
            )
        if extraction_policy == "phase0" and (
            integrated_product is not None or native_product is not None
        ):
            from corpus_structure.orchestrate.pdf_source import retained_source_document

            exact_product = integrated_product if integrated_product is not None else native_product
            assert exact_product is not None
            retained_input_document = retained_source_document(
                conn,
                exact_product,
                prepared=prepared,
                project_id=project_id,
                documents=docs,
                role="integrated" if integrated_product is not None else "native",
            )
            corpus_record, scope_record = records(
                [document for document in docs if document["id"] == retained_input_document.id],
                data.get("slices", data),
                slice=slice,
                scope=scope,
                corpus=corpus,
            )
        policy_source = (
            (pack / "policies.yaml").read_text()
            if extraction_policy == "phase0" and (pack / "policies.yaml").exists()
            else None
        )
        if (
            phase == 0
            and not source_only
            and (graph or PHASE0).policy_propose
            and policy_source is not None
            and scope_record is None
            and not whole_document
        ):
            raise CommandError("phase 0 full run requires a scope or named slice")
    selected_graph = graph or PHASE0
    if source_only:
        from corpus_structure.core.vocab import Stage

        selected_graph = replace(
            selected_graph,
            policy_propose=False,
            stages=tuple(stage for stage in selected_graph.stages if stage[0] == Stage.INGEST),
        )
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
    if retained_input_document is not None and extraction_policy == "m1-candidate":
        from corpus_structure.orchestrate.m1 import bind_retained_document

        selected_registry = bind_retained_document(selected_registry, retained_input_document)
        if m1_configuration != "source-only":
            selected_registry.resolve("extract.m1_candidates", m1_configuration)
        if record_policy is not None:
            from corpus_structure.orchestrate.m1 import bind_record_policy

            selected_registry = bind_record_policy(selected_registry, prepared, record_policy)
    if source_membership is not None or (
        retained_input_document is not None and extraction_policy == "phase0"
    ):
        from corpus_structure.orchestrate.phase0 import bind_pdf_selection

        selected_registry = bind_pdf_selection(
            selected_registry,
            document=retained_input_document if extraction_policy == "phase0" else None,
            membership=source_membership,
        )
    selected_registry = selected_registry.bind_release(prepared)
    if (
        ordinary_graph
        and not source_only
        and not characterization_views
        and any(
            "characterization_layers"
            in selected_registry.method(step.config.partition("/")[0]).Config.model_fields
            for _, steps in selected_graph.stages
            for step in steps
        )
    ):
        from corpus_structure.core.vocab import Stage

        from .characterization import PRIMARY_PRODUCERS, _characterize_captured_run

        overrides = (
            {"extract.m1_candidates": m1_configuration}
            if extraction_policy == "m1-candidate" and m1_configuration != "default"
            else {}
        )
        options = _consumer_characterization_options(selected_registry, selected_graph, overrides)
        capture = run_source_methods(
            engine,
            execution_preparation=execution,
            on_created=on_created,
            project_id=project_id,
            domain=domain,
            prepared=prepared,
            binding=binding,
            registry=selected_registry,
            graph=replace(
                selected_graph,
                policy_propose=False,
                stages=tuple(pair for pair in selected_graph.stages if pair[0] == Stage.INGEST),
            ),
            method_settings=method_settings,
            phase=phase,
            fresh=fresh,
            corpus_record=corpus_record,
            scope_record=scope_record,
            whole_document=whole_document,
            source_membership=source_membership,
            kind="slice" if slice else "full",
        )
        characterized = _characterize_captured_run(
            execution,
            engine,
            capture,
            project_id=project_id,
            release_id=release_id,
            realization_id=realization_id,
            domain=domain,
            method_settings=method_settings,
            method_options=options,
            registry=registry(pack).bind_release(prepared),
            on_created=on_created,
            fresh_methods=tuple(name for name in fresh if name in PRIMARY_PRODUCERS),
        )
        characterization_views = tuple(result.view for result in characterized)
        if not characterization_views:
            raise CommandError("analytical execution has no captured primary source views")
    selected_primary_sources = ()
    if characterization_views:
        from corpus_structure.orchestrate.characterization import (
            bind_characterization_views,
            characterization_sources,
        )
        from corpus_structure.semantic.characterization_store import read_layer_manifest, read_view
        from corpus_structure.semantic.query import read_snapshot

        if len(characterization_views) > 256 or len(set(characterization_views)) != len(
            characterization_views
        ):
            raise CommandError(
                "analytical source binding requires 1..256 distinct enriched-document views"
            )
        views, layers, primary_sources = [], {}, {}
        with read_snapshot(engine) as conn:
            producing_task, producing_run = table("ops.task"), table("ops.run")
            for reference in characterization_views:
                owner = conn.scalar(
                    select(producing_run.c.project_id)
                    .select_from(
                        producing_task.join(
                            producing_run, producing_run.c.id == producing_task.c.run_id
                        )
                    )
                    .where(producing_task.c.id == reference.task_id)
                )
                if owner != project_id:
                    raise CommandError("characterization view belongs to a different project")
                view = read_view(conn, reference)
                if integrated_product is not None and view.base_document != integrated_product:
                    raise CommandError(
                        "characterization view belongs to a different integrated document"
                    )
                views.append(view)
                for source in characterization_sources(
                    conn, reference, view, project_id=project_id
                ):
                    prior = primary_sources.setdefault(source.source_view_id, source)
                    if prior != source:
                        raise CommandError(
                            "enriched views select different original custody for one source"
                        )
                for value in view.payload["layers"]:
                    pin = ProductReference(**value)
                    if pin not in layers:
                        layers[pin] = read_layer_manifest(conn, pin)
        selected_registry = bind_characterization_views(selected_registry, views, layers)
        selected_primary_sources = tuple(primary_sources.values())
        from corpus_structure.core.vocab import Stage

        # Exact retained primary inputs already include capture/recognition. New
        # release-specific SourceViews would no longer address those layer pins.
        selected_graph = replace(
            selected_graph,
            stages=tuple(
                (
                    stage,
                    tuple(
                        step for step in steps if step.config.partition("/")[0] != "enrich.pdf_math"
                    ),
                )
                for stage, steps in selected_graph.stages
                if stage != Stage.INGEST
            ),
        )
    return run_source_methods(
        engine,
        execution_preparation=execution,
        on_created=on_created,
        project_id=project_id,
        domain=domain,
        prepared=prepared,
        binding=binding,
        registry=selected_registry,
        graph=selected_graph,
        selected_sources=selected_primary_sources,
        characterization_views=characterization_views,
        method_settings=method_settings,
        phase=phase,
        guideline=(
            (domains or DOMAINS)
            / domain
            / ("m1-guideline.md" if extraction_policy == "m1-candidate" else "guideline.md")
        ).read_text(),
        fresh=fresh,
        corpus_record=corpus_record,
        scope_record=scope_record,
        whole_document=whole_document,
        source_membership=source_membership,
        policy_source=policy_source,
        agent_mode=agent_mode,
        agent_reuse=agent_reuse,
        kind="slice" if slice else "full",
        extraction_policy=extraction_policy,
        record_acceptance=tuple(record_policy.get("record_acceptance", ()))
        if record_policy
        else (),
        extraction_policy_config=(pack / "m1-methods.yaml").read_text()
        if extraction_policy == "m1-candidate"
        else None,
        configurations={"extract.m1_candidates": m1_configuration}
        if extraction_policy == "m1-candidate" and m1_configuration != "default"
        else None,
    )


def resolve_source_domain(
    conn: Connection, project_id: str, release_id: str, domain: str | None
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
    for path in sorted(DOMAINS.glob("*/semantic.yaml")):
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
    conn: Connection, run_id: int | None = None, *, project_id: str | None = None
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
    row = conn.execute(select(r).where(r.c.id == run)).mappings().one()
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
                if "characterization_demand" in row["options"]
                else row["options"].get("characterization_anchor")
            ),
            characterization_region=row["options"].get("characterization_region"),
            characterization_stage=row["options"].get("characterization_stage"),
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
