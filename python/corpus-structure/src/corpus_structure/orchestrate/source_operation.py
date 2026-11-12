"""One source-operation resolution and execution owner for CLI and Python callers."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Engine

from corpus_structure.core.method import MethodSettings
from corpus_structure.semantic.product_reference import ProductReference

from .characterization import EnrichedDocumentResult
from .semantic import BoundRunReport, SourceRunCreated
from .source_lineage import SourceOperationLink
from .source_request import (
    Capture,
    ConfiguredGraph,
    M1Candidate,
    NamedScope,
    NamedSlice,
    PackDefault,
    Phase0Analysis,
    RetainedViews,
    SourceRequestError,
    SourceRunRequest,
    WholeDocument,
)

CommandError = SourceRequestError


class SourceOperationResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    operation_id: UUID
    capture: BoundRunReport | None = None
    analytical: BoundRunReport | None = None
    characterization: tuple[EnrichedDocumentResult, ...] = ()
    characterization_views: tuple[ProductReference, ...] = ()
    created_run_ids: tuple[int, ...] = ()
    execution_policy: dict[str, Any]

    @property
    def run(self) -> BoundRunReport:
        result = self.analytical if self.analytical is not None else self.capture
        if result is None:
            raise ValueError("source operation did not create a source run")
        return result


@dataclass(frozen=True)
class ResolvedSourceRun:
    request: SourceRunRequest
    project_id: str
    release_id: str
    realization_id: str
    domain: str
    prepared: Any
    binding: Any
    pack: Path
    corpus_record: dict
    scope_record: dict | None
    registry: Any
    graph: Any
    policy_source: str | None


def _selection(request):
    selection = request.selection
    return (
        selection.name if isinstance(selection, NamedSlice) else None,
        selection.name if isinstance(selection, NamedScope) else None,
        isinstance(selection, WholeDocument),
    )


def _workflow(request):
    workflow = request.workflow
    primary = getattr(workflow, "primary", getattr(workflow, "inputs", None))
    return (
        "m1-candidate" if isinstance(workflow, M1Candidate) else "phase0",
        workflow.configuration if isinstance(workflow, M1Candidate) else "default",
        json.loads(workflow.record_policy)
        if isinstance(workflow, M1Candidate) and workflow.record_policy is not None
        else None,
        isinstance(workflow, Capture),
        primary.views if isinstance(primary, RetainedViews) else (),
    )


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


def run_source_operation(
    engine: Engine,
    request: SourceRunRequest,
    method_settings: MethodSettings,
    *,
    domains: Path | None = None,
    graph=None,
    registry_for=None,
    on_created: Callable[[SourceRunCreated], None] | None = None,
) -> SourceOperationResult:
    """Execute validated intent; supplied implementations never select the workflow."""
    from corpus_structure.schema.pack import DOMAINS
    from corpus_structure.semantic.execution_preparation import prepare_execution
    from corpus_structure.semantic.runtime import resolve_source_binding

    from .commands import resolve_source_domain

    preflight_source_operation(request, method_settings, graph=graph, registry_for=registry_for)
    with engine.connect() as conn:
        release_id, realization_id = request.release_id, request.realization_id
        if release_id is None or realization_id is None:
            release_id, realization_id = resolve_source_binding(
                conn,
                request.project_id,
                release_id=release_id,
                realization_id=realization_id,
            )
        domain = resolve_source_domain(
            conn, request.project_id, release_id, request.domain, domains=domains
        )
        execution = prepare_execution(conn, release_id, policy=method_settings.execution_policy)
    selected = replace(request, release_id=release_id, realization_id=realization_id, domain=domain)
    created_run_ids = []
    operation_id = uuid4()

    def created(value):
        created_run_ids.append(int(value.run_id))
        if on_created is not None:
            on_created(value)

    with execution:
        if selected.registration_corpus is not None:
            from .project import _init_prepared_project

            with engine.begin() as conn:
                _init_prepared_project(
                    conn,
                    execution=execution,
                    domain=domain,
                    corpus=selected.registration_corpus,
                    release_id=release_id,
                    realization_id=realization_id,
                    name=selected.project_id,
                    domains=domains,
                    registry=registry_for((domains or DOMAINS) / domain)
                    if registry_for is not None
                    else None,
                    native_product=selected.native_product,
                    integrated_product=selected.integrated_product,
                )
        resolved = resolve_source_run(
            engine, execution, selected, domains=domains, graph=graph, registry_for=registry_for
        )
        resolved = replace(resolved, request=request)
        return _execute_source_run(
            engine, execution, resolved, method_settings, created, created_run_ids, operation_id
        )


def preflight_source_operation(request, method_settings, *, graph=None, registry_for=None):
    # Pure checks precede both engine acquisition in adapters and preparation here.
    request.__post_init__()
    if isinstance(request.workflow, M1Candidate) and (
        graph is not None or registry_for is not None
    ):
        raise SourceRequestError("M1 uses its explicit candidate graph and registry")
    if isinstance(request.workflow, ConfiguredGraph) and (graph is None or registry_for is None):
        raise SourceRequestError("configured graph requires its declared graph and registry")
    if not isinstance(method_settings, MethodSettings):
        raise SourceRequestError("source execution requires complete typed MethodSettings")


def resolve_source_run(engine, execution, request, *, domains=None, graph=None, registry_for=None):
    """Resolve exact source records and selected configurations once after registration."""
    from sqlalchemy import select

    from corpus_structure.orchestrate.phase0 import PHASE0, registry
    from corpus_structure.schema.pack import DOMAINS
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.operations import OperationBinding

    from .commands import CommandError

    release_id, realization_id, project_id, domain = (
        request.release_id,
        request.realization_id,
        request.project_id,
        request.domain,
    )
    phase, source_membership = request.phase, request.membership
    native_product, integrated_product = request.native_product, request.integrated_product
    slice, scope, whole_document = _selection(request)
    corpus = None
    extraction_policy, m1_configuration, record_policy, source_only, _ = _workflow(request)
    if isinstance(request.workflow, M1Candidate):
        from .m1 import registry as m1_registry
        from .m1 import source_graph

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
        if extraction_policy == "phase0" and isinstance(request.selection, PackDefault):
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
            and (graph if graph is not None else PHASE0).policy_propose
            and policy_source is not None
            and scope_record is None
            and not whole_document
        ):
            raise CommandError("phase 0 full run requires a scope or named slice")
    selected_graph = graph if graph is not None else PHASE0
    if source_only:
        from corpus_structure.core.vocab import Stage

        selected_graph = replace(
            selected_graph,
            policy_propose=False,
            stages=tuple(stage for stage in selected_graph.stages if stage[0] == Stage.INGEST),
        )
    selected_registry = (registry_for or registry)((domains or DOMAINS) / domain)
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
    return ResolvedSourceRun(
        request,
        project_id,
        release_id,
        realization_id,
        domain,
        prepared,
        binding,
        pack,
        corpus_record,
        scope_record,
        selected_registry,
        selected_graph,
        policy_source,
    )


def _execute_source_run(
    engine, execution, resolved, method_settings, on_created, created_run_ids, operation_id
):
    from sqlalchemy import select

    from corpus_structure.orchestrate.phase0 import registry
    from corpus_structure.orchestrate.semantic import run_source_methods
    from corpus_structure.schema.pack import DOMAINS
    from corpus_structure.semantic.metadata import table

    from .commands import CommandError

    request = resolved.request
    project_id, release_id, realization_id, domain = (
        resolved.project_id,
        resolved.release_id,
        resolved.realization_id,
        resolved.domain,
    )
    phase, fresh, source_membership = request.phase, request.fresh, request.membership
    agent_mode, agent_reuse = request.agent_mode, request.agent_reuse
    integrated_product = request.integrated_product
    slice, _scope, whole_document = _selection(request)
    extraction_policy, m1_configuration, record_policy, source_only, characterization_views = (
        _workflow(request)
    )
    prepared, binding, pack = resolved.prepared, resolved.binding, resolved.pack
    corpus_record, scope_record = resolved.corpus_record, resolved.scope_record
    selected_registry, selected_graph, policy_source = (
        resolved.registry,
        resolved.graph,
        resolved.policy_source,
    )
    domains = pack.parent
    capture, characterized = None, ()
    if (
        isinstance(request.workflow, (Phase0Analysis, M1Candidate))
        and not (
            isinstance(request.workflow, M1Candidate)
            and request.workflow.configuration == "source-only"
        )
        and not source_only
        and not characterization_views
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
            source_run_options=SourceOperationLink(
                operation_id=operation_id, role="capture"
            ).options(),
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
            source_operation=SourceOperationLink(
                operation_id=operation_id, role="primary", capture_run_id=int(capture.run_id)
            ),
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
    from corpus_structure.core.vocab import Stage

    capture_only = (
        isinstance(request.workflow, Capture)
        or (
            isinstance(request.workflow, M1Candidate)
            and request.workflow.configuration == "source-only"
        )
        or (
            isinstance(request.workflow, ConfiguredGraph)
            and not characterization_views
            and not selected_graph.policy_propose
            and all(stage == Stage.INGEST or not steps for stage, steps in selected_graph.stages)
        )
    )
    analytical = run_source_methods(
        engine,
        source_run_options=SourceOperationLink(
            operation_id=operation_id,
            role="capture" if capture_only else "analytical",
            capture_run_id=int(capture.run_id) if capture is not None else None,
        ).options(),
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

    if capture_only:
        capture, analytical = analytical, None
        if isinstance(request.workflow, Capture) and request.workflow.enrichment is not None:
            from .characterization import _characterize_captured_run

            characterized = _characterize_captured_run(
                execution,
                engine,
                capture,
                project_id=project_id,
                release_id=release_id,
                realization_id=realization_id,
                domain=domain,
                method_settings=method_settings,
                method_options=request.workflow.enrichment.options(),
                on_created=on_created,
                source_operation=SourceOperationLink(
                    operation_id=operation_id, role="primary", capture_run_id=int(capture.run_id)
                ),
            )
            characterization_views = tuple(result.view for result in characterized)
    return SourceOperationResult(
        operation_id=operation_id,
        capture=capture,
        analytical=analytical,
        characterization=tuple(characterized),
        characterization_views=tuple(characterization_views),
        created_run_ids=tuple(created_run_ids),
        execution_policy=asdict(execution.policy),
    )
