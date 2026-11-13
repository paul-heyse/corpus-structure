"""The existing deterministic method graph on explicitly selected semantic run bindings."""

from __future__ import annotations

import logging
from collections.abc import Callable, Generator, Mapping, Sequence
from contextlib import ExitStack
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field, JsonValue, TypeAdapter
from sqlalchemy import func, select

from corpus_structure.core.method import MethodContext, UnitRef, UnitView
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.orchestrate.liveness import (
    record_supervisor,
    run_supervisor,
    supervisor_connection,
)
from corpus_structure.semantic._operation_ids import CutId, DocumentId
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operation_results import ClaimedTask, MethodConfigId, RunId, TaskId
from corpus_structure.semantic.operations import (
    BoundReader,
    BoundSourceProducer,
    OperationBinding,
    OperationConflict,
    claim_tasks,
    create_run,
    create_task,
    record_method,
    run_view,
    seal_cut,
    start_run,
)
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.structural_products import ExternalSourceRef

_SAME_VIEW_DEPENDENCIES = {"source_view_interpretation", "source_view_product"}
_READY_SOURCE_TASKS = {"done", "empty", "reused"}


class BoundRunReport(BaseModel):
    run_id: RunId
    status: str
    release_id: str
    realization_id: str
    cut_id: CutId | None = None
    characterization_views: tuple[ProductReference, ...] = Field(
        default=(), exclude_if=lambda value: not value
    )


@dataclass(frozen=True)
class SourceRunCreated:
    """Committed native identity; neither source readiness nor effect permission."""

    run_id: RunId
    project: str
    release_id: str


def _source_configurations(registry, graph, overrides):
    """Resolve the one effective configuration owned by each method in a run."""
    configs = {}
    for _, steps in graph.stages:
        for step in steps:
            method, _, default = step.config.partition("/")
            name = overrides.get(method, default or "default")
            resolved = registry.resolve(method, name)
            previous = configs.get(method)
            if previous is not None and (
                previous.config_hash != resolved.config_hash
                or canonical_bytes(previous.params) != canonical_bytes(resolved.params)
            ):
                raise OperationConflict(
                    f"source execution requires one effective configuration for {method}; "
                    f"{previous.name} and {name} resolve differently"
                )
            configs.setdefault(method, resolved)
    return configs


def _claimed_source_producers(
    conn,
    claims: Sequence[ClaimedTask],
    params: Mapping[str, Any],
) -> dict[tuple[int, str], BoundSourceProducer]:
    kind = params.get("source_dependencies")
    if kind not in _SAME_VIEW_DEPENDENCIES:
        return {}
    method_name = params["source_dependency_method"]
    edge, task, config, method = map(
        table, ("ops.task_dependency", "ops.task", "ops.method_config", "ops.method")
    )
    parents = (
        conn.execute(
            select(
                edge.c.task_id.label("consumer_id"),
                task.c.id,
                task.c.reused_task_id,
                task.c.unit_id,
                task.c.unit_key,
                task.c.run_id,
                task.c.release_id,
            )
            .select_from(edge)
            .join(task, task.c.id == edge.c.dependency_task_id)
            .join(config, config.c.id == task.c.method_config_id)
            .join(method, method.c.id == config.c.method_id)
            .where(
                edge.c.task_id.in_([claim.task_id for claim in claims]),
                edge.c.kind == kind,
                task.c.status.in_(_READY_SOURCE_TASKS),
                task.c.unit_type == "source_view",
                method.c.name == method_name,
            )
        )
        .mappings()
        .all()
    )
    by_consumer = {parent["consumer_id"]: parent for parent in parents}
    if len(parents) != len(by_consumer) or len(by_consumer) != len(claims):
        raise OperationConflict("claimed source task requires one exact same-view producer")
    bindings = {}
    for claim in claims:
        parent = by_consumer[claim.task_id]
        if (
            claim.unit_id is None
            or parent["unit_id"] != claim.unit_id
            or parent["unit_key"] != claim.unit_key
            or parent["run_id"] != claim.run_id
            or parent["release_id"] != claim.release_id
        ):
            raise OperationConflict("source producer differs from the claimed run or source view")
        bindings[(claim.unit_id, method_name)] = BoundSourceProducer(
            parent["id"], parent["reused_task_id"] or parent["id"]
        )
    return bindings


def run_source_methods(
    engine: Any,
    *,
    project_id: str,
    prepared: Any,
    binding: OperationBinding,
    registry: Any,
    graph: Any,
    method_settings: Any,
    phase: int = 0,
    domain: str = "statistics",
    configurations: Mapping[str, str] | None = None,
    guideline: str = "",
    fresh: Any = (),
    corpus_record: Mapping[str, Any] | None = None,
    scope_record: Mapping[str, Any] | None = None,
    whole_document: bool = False,
    source_membership: str | None = None,
    policy_source: str | None = None,
    agent_mode: str = "complete",
    agent_reuse: str = "full",
    kind: str = "full",
    extraction_policy: str = "phase0",
    extraction_policy_config: str | None = None,
    record_acceptance: Sequence[Mapping[str, Any]] = (),
    local_semantic_admission: Sequence[Mapping[str, Any]] = (),
    structural_admission: Sequence[Mapping[str, Any]] = (),
    selected_sources: Sequence[ExternalSourceRef] = (),
    characterization_views: Sequence[ProductReference] = (),
    execution_preparation: Any = None,
    regional_preparation: Any = None,
    source_run_options: Mapping[str, Any] | Callable[[], Mapping[str, Any]] | None = None,
    freshness_seed: str | None = None,
    on_created: Callable[[SourceRunCreated], None] | None = None,
) -> BoundRunReport:
    arguments = locals()
    from .ready import owned_source_execution

    if execution_preparation is not None:
        if execution_preparation.require_release(prepared.release_id) is not prepared:
            raise ValueError("source invocation differs from verified preparation")
        return _run_source_methods(execution_preparation.cpu, **arguments)
    with owned_source_execution(prepared, policy=method_settings.execution_policy) as execution:
        arguments["execution_preparation"] = execution
        return _run_source_methods(execution.cpu, **arguments)


def _run_source_methods(cpu_execution, *args, **kwargs):
    from corpus_structure.core.work import drive_prepared_work

    return drive_prepared_work(_source_methods_plan(cpu_execution, *args, **kwargs), lambda: None)


def _method_plan(method, units, config, context):
    plan = getattr(method, "plan", None)
    if plan is not None:
        return (yield from plan(units, config, context))
    # Ordinary synchronous consumers retain their own semantic implementation.
    return method.run(units, config, context)


def _claim_source_work(engine, run_id, prepared, claimed, region, check_active):
    """Warm exact claimed sources under renewable ownership and cooperative byte admission."""
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.source_views import selected_source_views

    def read():
        check_active()
        with read_snapshot(engine) as conn:
            for task in claimed:
                if task.unit_type != "source_view":
                    continue
                selected = selected_source_views(conn, run_id, source_view_id=task.unit_id)
                if len(selected) != 1 or selected[0].id != task.unit_id:
                    raise OperationConflict("claimed source view is outside bound run")
                region.source_view(conn, selected[0], analysis=False, prepared=prepared)

    return region.read_work(read)


def _source_methods_plan(cpu_execution, *args, **kwargs):
    from corpus_structure.core.work import PreparedWork

    from .ready import source_admission

    execution = kwargs["execution_preparation"]
    admission = source_admission(execution)
    waited = False

    def acquire_stage():
        nonlocal waited
        permit = admission.try_work("stage")
        if permit is None and not waited:
            from corpus_structure.cli.observation_logging import event

            details = kwargs.get("source_run_options") or {}
            if callable(details):
                details = details()
            event(
                "characterization_capacity_wait",
                "Waiting for stage capacity",
                activity="capacity_wait",
                anchor_run_id=details.get("characterization_anchor"),
                region=details.get("characterization_region"),
                stage=details.get("characterization_stage"),
            )
            waited = True
        return permit

    (permit,) = yield (PreparedWork(acquire_stage),)
    try:
        return (yield from _source_run_plan(cpu_execution, *args, **kwargs))
    finally:
        permit.release()


def _source_run_plan(
    cpu_execution,
    engine: Any,
    *,
    project_id: str,
    prepared: Any,
    binding: OperationBinding,
    registry: Any,
    graph: Any,
    method_settings: Any,
    phase: int = 0,
    domain: str = "statistics",
    configurations: Mapping[str, str] | None = None,
    guideline: str = "",
    fresh: Any = (),
    corpus_record: Mapping[str, Any] | None = None,
    scope_record: Mapping[str, Any] | None = None,
    whole_document: bool = False,
    source_membership: str | None = None,
    policy_source: str | None = None,
    agent_mode: str = "complete",
    agent_reuse: str = "full",
    kind: str = "full",
    extraction_policy: str = "phase0",
    extraction_policy_config: str | None = None,
    record_acceptance: Sequence[Mapping[str, Any]] = (),
    local_semantic_admission: Sequence[Mapping[str, Any]] = (),
    structural_admission: Sequence[Mapping[str, Any]] = (),
    selected_sources: Sequence[ExternalSourceRef] = (),
    characterization_views: Sequence[ProductReference] = (),
    execution_preparation: Any = None,
    regional_preparation: Any = None,
    source_run_options: Mapping[str, Any] | Callable[[], Mapping[str, Any]] | None = None,
    freshness_seed: str | None = None,
    on_created: Callable[[SourceRunCreated], None] | None = None,
) -> Generator[Any, Any, BoundRunReport]:
    """Run the current source graph; hand its immutable cut to consolidation/proposal owners.

    This result establishes source preparation only. It does not report grading, inference,
    or whole-run completion. Source work never chooses an unbound latest interpretation.
    """
    from corpus_structure.semantic.contracts import require_bound_operation

    require_bound_operation(prepared, "execute_source")
    from hashlib import sha256

    from corpus_structure.core.provenance import code_commit
    from corpus_structure.semantic.identity import canonical_bytes

    from .source_request import SourceRequestError, validate_source_agent_policy

    try:
        validate_source_agent_policy(agent_mode, agent_reuse)
    except SourceRequestError as error:
        raise OperationConflict(str(error)) from error
    if binding.release_id != prepared.release_id:
        raise OperationConflict("run release differs from prepared interpretation")
    import json

    from corpus_structure.semantic.contracts import execution_payload

    payload = execution_payload(prepared)
    if payload is not None:
        from corpus_structure.semantic.analysis_contracts import bind_analysis_family

        invocation_input = bind_analysis_family(prepared, "invocation").prepare(
            release=binding.release_id,
            source={
                "realization": binding.input_realization_id,
                "revision": binding.input_revision,
            },
            configuration={
                "methods": configurations or {},
                "phase": phase,
                "domain": domain,
                **(
                    {
                        "extraction_policy": extraction_policy,
                        "extraction_policy_config": extraction_policy_config,
                    }
                    if extraction_policy != "phase0"
                    else {}
                ),
            },
            policy={"source": policy_source, "agent_mode": agent_mode, "reuse": agent_reuse},
        )
        if invocation_input.release_id != prepared.release_id:
            raise OperationConflict("invocation preparation belongs to another release")
    registry = registry.bind_release(prepared)
    if execution_preparation is not None:
        execution_preparation.register_methods(registry)
    configurations = dict(configurations or {})
    configs = _source_configurations(registry, graph, configurations)
    if graph.policy_propose and policy_source is not None:
        from .policy import admit_source_policy

        admit_source_policy(policy_source, registry, prepared)
    from corpus_structure.semantic.operation_results import validate_method_dimension

    for method_name in configs:
        descriptor = registry.method(method_name)
        validate_method_dimension(prepared, method_name, "family", str(descriptor.family))
        validate_method_dimension(prepared, method_name, "tier", str(descriptor.tier))
        validate_method_dimension(
            prepared,
            method_name,
            "confidence_source",
            str(descriptor.confidence_source) if descriptor.confidence_source is not None else None,
        )
    if "enrich.pdf_math" in configs:
        from corpus_structure.semantic.contracts import require_database_operation

        with engine.connect() as admission_conn:
            require_database_operation(admission_conn, prepared.release_id, "enrich_pdf_math")
    native_source = any(
        registry.method(name).name in {"ingest.pdf", "ingest.pdf_integrated"}
        or registry.method(name).unit_type == TaskUnitType.SOURCE_VIEW
        for name in configs
    )
    if whole_document and scope_record is not None:
        raise OperationConflict("whole-document execution cannot bind a named scope")
    if source_membership not in {None, "direct", "descendants"}:
        raise OperationConflict("invalid source membership")
    if native_source and scope_record is not None:
        if scope_record.get("kind") != "native_sections":
            raise OperationConflict(
                "native PDF source execution cannot apply archived rendition or HTML locator "
                "scopes; select a native_sections scope or explicitly select all sources"
            )
        from corpus_structure.semantic.pdf_contracts import pdf_context_for_release

        with engine.connect() as conn:
            boundary = pdf_context_for_release(conn, prepared).boundary
            scope_record = boundary.validate_json(
                "PdfNativeSourceScope", canonical_bytes(dict(scope_record))
            ).model_dump(mode="json")
    selected_sources = tuple(selected_sources)
    if len({(source.run_id, source.source_view_id) for source in selected_sources}) != len(
        selected_sources
    ):
        raise OperationConflict("retained source selection contains duplicate original views")
    if any(source.project_id != project_id for source in selected_sources):
        raise OperationConflict("retained source selection belongs to another project")
    fresh = tuple(sorted(set(fresh)))
    unknown = set(fresh) - {method.name for method in registry.methods()}
    if unknown:
        raise OperationConflict("fresh names unregistered methods: " + ", ".join(sorted(unknown)))
    agent_configs = {}
    from corpus_structure.semantic.proposals import SEMANTIC_AGENT_VERSION

    operation_versions = {name: registry.method(name).version for name in configs}
    from corpus_structure.core.method import ArtifactRef, ConfigRef, PackSection, config_references

    for method_name, config_name in registry.named():
        from corpus_structure.methods.llm.producer import SUPPORTED_PRODUCERS, producer_binding

        if method_name not in SUPPORTED_PRODUCERS:
            continue
        config = registry.overlay(method_name, config_name)
        raw = config.model_dump(mode="json")
        markers = config_references(type(config))
        for path, marker in markers.items():
            if isinstance(marker, PackSection):
                if len(path) != 1:
                    raise OperationConflict("nested agent operation sections are unsupported")
                raw[path[0]] = registry.file.sections[marker.name]
            elif isinstance(marker, ConfigRef):
                if len(path) != 1:
                    raise OperationConflict("nested agent configuration references are unsupported")
                value = raw[path[0]]
                if isinstance(value, dict):
                    raw[path[0]] = (
                        registry.method(marker.method)
                        .Config.model_validate(value)
                        .model_dump(mode="json")
                    )
                else:
                    reference = str(value)
                    name = (
                        reference.split("/", 1)[1]
                        if reference.startswith(marker.method + "/")
                        else reference
                    )
                    raw[path[0]] = dict(registry.resolve(marker.method, name).params)
        values = type(config).model_validate(raw).model_dump(mode="json")
        for path, marker in markers.items():
            if isinstance(marker, ArtifactRef):
                values.pop(path[0], None)
        producer_binding(method_name, values)
        agent_configs[f"{method_name}/{config_name}"] = values
        operation_versions[method_name] = SEMANTIC_AGENT_VERSION
    with ExitStack() as startup:
        conn = supervisor_conn = startup.enter_context(supervisor_connection(engine))
        transaction = conn.begin()
        d = table("kb.document")
        docs = (
            conn.execute(select(d).where(d.c.project_id == project_id).order_by(d.c.key))
            .mappings()
            .all()
        )
        if corpus_record is not None:
            keys = set(corpus_record["documents"])
            docs = [d for d in docs if d["key"] in keys]
        if not docs and any(
            registry.method(name).unit_type != TaskUnitType.RUN for name in configs
        ):
            raise OperationConflict("bound project has no registered source documents")
        import json
        from importlib.metadata import version

        library_names = set()
        if set(configs) & {"structure.definition_components", "structure.clause_classification"}:
            library_names.update(
                (
                    "gliner2",
                    "torch",
                    "transformers",
                    "tokenizers",
                    "safetensors",
                    "threadpoolctl",
                    "spacy",
                    "en-core-web-sm",
                )
            )
        native_libraries = {}
        if set(configs) & {"ingest.pdf", "ingest.pdf_integrated", "enrich.pdf_math"}:
            from corpus_structure.ingest.pdf import pdf_package_versions

            native_libraries = dict(pdf_package_versions())
        if set(configs) & {
            "extract.math",
            "normalize.formula",
            "structure.compare",
            "structure.scoped_relations",
        }:
            library_names.add("lark")
        if set(configs) & {"extract.m1_annotations", "structure.scoped_relations"}:
            library_names.update(("spacy", "en-core-web-sm"))
        if "resolve.symbol_scope" in configs:
            library_names.update(("spacy", "en-core-web-sm"))
        if "extract.m1_candidates" in configs:
            library_names.update(
                (
                    "gliner2",
                    "torch",
                    "transformers",
                    "tokenizers",
                    "safetensors",
                    "threadpoolctl",
                    "spacy",
                    "en-core-web-sm",
                )
            )
        if graph.policy_propose:
            library_names.update(("rapidfuzz", "regex", "rule-engine"))
        from .characterization_recovery import native_thread_profile

        execution_native_profile = native_thread_profile(cpu_execution.policy)
        dependency_manifest = {
            **(
                {
                    "extraction_policy": extraction_policy,
                    "extraction_policy_config": extraction_policy_config,
                }
                if extraction_policy != "phase0"
                else {}
            ),
            "parent": json.loads(binding.dependencies),
            "libraries": {
                **{name: version(name) for name in sorted(library_names)},
                **native_libraries,
            },
            "source_documents": [
                {
                    "key": d["key"],
                    "uri": d["source_uri"],
                    "content_hash": d["content_hash"],
                    "metadata": d["meta"],
                }
                for d in docs
            ],
            "selected_sources": [source.model_dump(mode="json") for source in selected_sources],
            **(
                {"characterization_views": [pin.values() for pin in characterization_views]}
                if characterization_views
                else {}
            ),
            "operations": {
                name: {
                    "version": registry.method(name).version,
                    "family": str(registry.method(name).family),
                    "tier": str(registry.method(name).tier),
                    "confidence_source": str(registry.method(name).confidence_source)
                    if registry.method(name).confidence_source is not None
                    else None,
                    "configuration_hash": config.config_hash,
                    "parameters": dict(config.params),
                }
                for name, config in configs.items()
            },
            "guideline": guideline,
            "agent_configurations": agent_configs,
            "operation_versions": operation_versions,
            "corpus": dict(corpus_record) if corpus_record is not None else None,
            "scope": dict(scope_record) if scope_record is not None else None,
            "whole_document": whole_document,
            "source_membership": source_membership,
            "policy": policy_source,
            **({"record_acceptance": list(record_acceptance)} if record_acceptance else {}),
            **(
                {"structural_admission": list(structural_admission)} if structural_admission else {}
            ),
            **(
                {"local_semantic_admission": list(local_semantic_admission)}
                if local_semantic_admission
                else {}
            ),
        }
        binding = OperationBinding(
            binding.release_id,
            binding.input_realization_id,
            binding.input_revision,
            canonical_bytes(dependency_manifest),
        )
        from dataclasses import asdict

        resolved_run_options = (
            source_run_options() if callable(source_run_options) else source_run_options
        )
        options = {
            **dict(resolved_run_options or {}),
            "physical_policy": asdict(cpu_execution.policy),
            **({"extraction_policy": extraction_policy} if extraction_policy != "phase0" else {}),
            "domain": domain,
            "corpus": dict(corpus_record)
            if corpus_record is not None
            else {"documents": [d["key"] for d in docs]},
            "scope": dict(scope_record) if scope_record is not None else None,
            "whole_document": whole_document,
            "source_membership": source_membership,
            "policy": policy_source,
            "agent_mode": agent_mode,
            "agent_reuse": agent_reuse,
            "operation_versions": operation_versions,
            "configs": {m: c.config_hash for m, c in configs.items()},
            "agent_configs": agent_configs,
            "fresh": list(fresh),
            **(
                {"characterization_views": [pin.values() for pin in characterization_views]}
                if characterization_views
                else {}
            ),
        }
        rid = create_run(
            conn,
            project_id=project_id,
            binding=binding,
            kind=kind,
            options=options,
            code_commit=code_commit(),
            phase=phase,
            guideline=guideline,
        )
        startup.enter_context(run_supervisor(conn, rid))
        start_run(conn, rid)
        record_supervisor(conn, rid, waiting=False)
        if selected_sources:
            from sqlalchemy import text

            from corpus_structure.semantic._operation_calls import select_source_view
            from corpus_structure.semantic._operation_ids import SourceViewId

            for source in selected_sources:
                conn.execute(
                    text("SELECT ops.validate_structural_source(CAST(:source AS jsonb))"),
                    {"source": canonical_bytes(source.model_dump(mode="json")).decode()},
                ).scalar_one()
                select_source_view(
                    conn,
                    run_id=rid,
                    source_run_id=RunId(source.run_id),
                    source_view_id=SourceViewId(source.source_view_id),
                    projection_context=prepared,
                )
        transaction.commit()
        supervisor = startup.pop_all()
    holder = f"semantic-source:{rid}"
    run_context = ExitStack()
    try:
        from corpus_structure.cli.observation_logging import bound

        run_context.enter_context(
            bound(run_id=rid, project=project_id, release_id=prepared.release_id)
        )
        try:
            if on_created is not None:
                on_created(SourceRunCreated(RunId(rid), project_id, prepared.release_id))
            from corpus_structure.semantic.execution_preparation import RegionalPreparation

            source_reads = run_context.enter_context(RegionalPreparation(execution_preparation))
            registered = {}
            reported_prerequisite_wait = False
            reported_capacity_wait = False
            for stage, steps in graph.stages:
                for group in _source_step_groups(steps, configs, prepared):
                    scheduled = []

                    def register_ref(conn, method, config, cid, ref, stage=stage, *, producer=None):
                        from corpus_structure.semantic.execution_preparation import (
                            RegionalPreparation,
                        )

                        # Digest preparation can read full primary layers. A fresh reader
                        # keeps default analytical registration bounded to this unit.
                        with ExitStack() as inputs:
                            input_region = regional_preparation
                            if input_region is None:
                                input_region = inputs.enter_context(
                                    RegionalPreparation(execution_preparation)
                                )
                            input_view = run_view(
                                conn,
                                rid,
                                prepared,
                                cpu_execution=cpu_execution,
                                regional_preparation=input_region,
                            )
                            if not isinstance(input_view.reader, BoundReader):
                                raise TypeError("source dependency requires BoundReader")
                            input_view.reader.characterization_selection = tuple(
                                ProductReference(**pin)
                                for pin in config.params.get("characterization_layers", ())
                            )
                            if producer is not None:
                                input_view.reader.source_producers = {
                                    (
                                        ref.unit_id,
                                        config.params["source_dependency_method"],
                                    ): producer
                                }
                            unit = _unit(conn, input_view, ref)
                            digest = method.input_digest(unit, config.config)
                        from sqlalchemy import func, literal
                        from sqlalchemy.dialects.postgresql import JSONB

                        scoped_dependencies = conn.execute(
                            select(
                                func.ops.task_dependency_scope(
                                    literal(json.loads(binding.dependencies), type_=JSONB),
                                    method.name,
                                )
                            )
                        ).scalar_one()
                        inputs = [
                            prepared.release_id,
                            binding.input_realization_id,
                            binding.input_revision,
                            sha256(canonical_bytes(scoped_dependencies)).hexdigest(),
                            method.name,
                            method.version,
                            config.config_hash,
                            digest.bytes.hex(),
                        ]
                        if producer is not None:
                            # Reused parent invocations share the same immutable producer.
                            # A fresh origin invalidates the child even if its digest omits custody.
                            inputs.append(["source_producer_origin", producer.origin_task_id])
                        from .characterization import PRIMARY_PRODUCERS

                        if method.name in PRIMARY_PRODUCERS:
                            inputs.append(["execution_native_profile", execution_native_profile])
                        if freshness_seed is not None and method.name in fresh:
                            inputs.append(["characterization_freshness", freshness_seed])
                        ih = sha256(canonical_bytes(inputs)).hexdigest()
                        task_id = create_task(
                            conn,
                            run_id=rid,
                            config_id=cid,
                            stage=str(stage),
                            unit_type=str(ref.unit_type),
                            unit_id=ref.unit_id,
                            unit_key=ref.unit_key,
                            input_hash=ih,
                            packet_hash=digest.packet_hash,
                            fresh=method.name in fresh and freshness_seed is None,
                        )
                        if ref.unit_type == TaskUnitType.DOCUMENT and ref.unit_id is not None:
                            task_table = table("ops.task")
                            if (
                                conn.execute(
                                    select(task_table.c.status).where(task_table.c.id == task_id)
                                ).scalar_one()
                                == "reused"
                            ):
                                from corpus_structure.semantic.operations import read_original

                                read_original(conn, ref.unit_id, prepared=prepared)
                                from corpus_structure.semantic.source_views import (
                                    select_reused_source_views,
                                )

                                select_reused_source_views(conn, run_id=rid, task_id=task_id)
                        return task_id

                    def register_initial_group(group=group):
                        next_registered = dict(registered)
                        next_scheduled, next_deferred = [], []
                        with engine.begin() as conn:
                            for step in group:
                                name = step.config.split("/", 1)[0]
                                method = registry.method(name)
                                config = configs[name]
                                cid = record_method(
                                    conn,
                                    method,
                                    config.name,
                                    config.params,
                                    config.config_hash,
                                    prepared=prepared,
                                )
                                with ExitStack() as selection_inputs:
                                    selection_region = regional_preparation
                                    if selection_region is None:
                                        selection_region = selection_inputs.enter_context(
                                            RegionalPreparation(execution_preparation)
                                        )
                                    view = run_view(
                                        conn,
                                        rid,
                                        prepared,
                                        cpu_execution=cpu_execution,
                                        regional_preparation=selection_region,
                                    )
                                    from corpus_structure.semantic.product_reference import (
                                        ProductReference,
                                    )

                                    if not isinstance(view.reader, BoundReader):
                                        raise TypeError(
                                            "source selection requires its owned bound reader"
                                        )
                                    view.reader.characterization_selection = tuple(
                                        ProductReference(**pin)
                                        for pin in config.params.get("characterization_layers", ())
                                    )
                                    refs = list(method.select(view, config.config))
                                if (
                                    config.params.get("source_dependencies")
                                    == "ancestor_source_view"
                                ):

                                    def ancestor_refs(source_view_id):
                                        # Ancestor discovery hydrates the focal source. Only
                                        # detached refs survive this per-source read scope.
                                        with ExitStack() as inputs:
                                            ancestor_region = regional_preparation
                                            if ancestor_region is None:
                                                ancestor_region = inputs.enter_context(
                                                    RegionalPreparation(execution_preparation)
                                                )
                                            ancestor_view = run_view(
                                                conn,
                                                rid,
                                                prepared,
                                                cpu_execution=cpu_execution,
                                                regional_preparation=ancestor_region,
                                            )
                                            return ancestor_view.reader.ancestor_source_views(
                                                source_view_id
                                            )

                                    required = {ref.unit_id: ref for ref in refs}
                                    parent_ids = {}
                                    for ref in tuple(refs):
                                        for ancestor in ancestor_refs(ref.unit_id):
                                            required.setdefault(
                                                ancestor.id,
                                                UnitRef(
                                                    TaskUnitType.SOURCE_VIEW,
                                                    ancestor.id,
                                                    ancestor.key,
                                                ),
                                            )
                                    for identity in required:
                                        parent_ids[identity] = tuple(
                                            a.id
                                            for a in ancestor_refs(identity)
                                            if a.id in required
                                        )
                                    for identity, ref in required.items():
                                        if parent_ids[identity]:
                                            next_deferred.append(
                                                (
                                                    method,
                                                    config,
                                                    cid,
                                                    ref,
                                                    tuple(
                                                        (cid, parent)
                                                        for parent in parent_ids[identity]
                                                    ),
                                                )
                                            )
                                        else:
                                            next_registered[(cid, identity)] = register_ref(
                                                conn, method, config, cid, ref
                                            )
                                elif (
                                    config.params.get("source_dependencies")
                                    in _SAME_VIEW_DEPENDENCIES
                                ):
                                    prerequisite_name = config.params.get(
                                        "source_dependency_method"
                                    )
                                    if prerequisite_name not in configs:
                                        raise OperationConflict(
                                            "required source producer configuration is unavailable"
                                        )
                                    prerequisite = registry.method(prerequisite_name)
                                    prerequisite_config = configs[prerequisite_name]
                                    prerequisite_cid = record_method(
                                        conn,
                                        prerequisite,
                                        prerequisite_config.name,
                                        prerequisite_config.params,
                                        prerequisite_config.config_hash,
                                        prepared=prepared,
                                    )
                                    if not any(
                                        entry[2] == prerequisite_cid for entry in next_scheduled
                                    ):
                                        next_scheduled.append(
                                            (prerequisite, prerequisite_config, prerequisite_cid)
                                        )
                                    for ref in refs:
                                        key = (prerequisite_cid, ref.unit_id)
                                        if key not in next_registered:
                                            next_registered[key] = register_ref(
                                                conn,
                                                prerequisite,
                                                prerequisite_config,
                                                prerequisite_cid,
                                                ref,
                                            )
                                        next_deferred.append((method, config, cid, ref, (key,)))
                                else:
                                    for ref in refs:
                                        next_registered[(cid, ref.unit_id)] = register_ref(
                                            conn, method, config, cid, ref
                                        )
                                next_scheduled.append((method, config, cid))
                        return next_scheduled, next_deferred, next_registered

                    (registration,) = yield (source_reads.read_work(register_initial_group),)
                    scheduled, deferred, next_registered = registration
                    registered.update(next_registered)
                    from dataclasses import replace

                    from .source_reader import ScopedSourceReader

                    def execute_claim_body(method, config, claimed, claim_region):
                        with engine.connect() as conn:
                            view = run_view(
                                conn,
                                rid,
                                prepared,
                                cpu_execution=cpu_execution,
                                regional_preparation=claim_region,
                            )
                            bound_reader = view.reader
                            if not isinstance(bound_reader, BoundReader):
                                raise TypeError(
                                    "source execution requires the bound database adapter"
                                )
                            bound_reader.provider_execution = execution_preparation.providers
                        scoped_reader = ScopedSourceReader(engine, bound_reader)
                        method_view = replace(view, reader=scoped_reader)
                        from corpus_structure.semantic.claim_lifetime import maintained_claims

                        with maintained_claims(engine, claimed, holder) as check_active:
                            if any(task.unit_type == "source_view" for task in claimed):
                                yield (
                                    _claim_source_work(
                                        engine, rid, prepared, claimed, claim_region, check_active
                                    ),
                                )
                            _retain_source_originals(
                                engine,
                                claimed,
                                method,
                                config.config,
                                holder,
                                prepared,
                                check_active,
                            )
                            with engine.connect() as conn:
                                bound_reader.conn = conn
                                bound_reader.source_producers = _claimed_source_producers(
                                    conn, claimed, config.params
                                )
                                from corpus_structure.semantic.product_reference import (
                                    ProductReference,
                                )

                                bound_reader.characterization_selection = tuple(
                                    ProductReference(**pin)
                                    for pin in config.params.get("characterization_layers", ())
                                )
                                bound_reader.bind_source_tasks(
                                    {
                                        int(
                                            task.unit_id
                                            if task.unit_type == "document"
                                            else conn.execute(
                                                select(table("kb.source_view").c.document_id).where(
                                                    table("kb.source_view").c.id == task.unit_id
                                                )
                                            ).scalar_one()
                                        ): task.task_id
                                        for task in claimed
                                        if task.unit_type in {"document", "source_view"}
                                        and task.unit_id is not None
                                    }
                                )
                                units = [
                                    _unit(
                                        conn,
                                        view,
                                        UnitRef(TaskUnitType(t.unit_type), t.unit_id, t.unit_key),
                                    )
                                    for t in claimed
                                ]
                                from types import MappingProxyType

                                tasks_table = table("ops.task")
                                task_inputs = dict(
                                    conn.execute(
                                        select(tasks_table.c.id, tasks_table.c.input_hash).where(
                                            tasks_table.c.id.in_([t.task_id for t in claimed])
                                        )
                                    ).all()
                                )
                                runtime_id = conn.execute(
                                    select(table("ops.run").c.runtime_id).where(
                                        table("ops.run").c.id == rid
                                    )
                                ).scalar_one()
                                operation_identities = {
                                    UnitRef(
                                        TaskUnitType(t.unit_type), t.unit_id, t.unit_key
                                    ): MappingProxyType(
                                        {
                                            "key": method.name,
                                            "version": method.version,
                                            "runtime": runtime_id,
                                            "configuration": config.config_hash,
                                            "input": task_inputs[t.task_id],
                                            **{
                                                k: config.params.get(k)
                                                for k in ("model", "grammar", "context")
                                            },
                                        }
                                    )
                                    for t in claimed
                                }

                            def characterization_operation(
                                unit_ref, identities=operation_identities
                            ):
                                try:
                                    identity = identities[unit_ref]
                                    if any(
                                        not isinstance(value, str) or not value
                                        for value in identity.values()
                                    ):
                                        raise OperationConflict(
                                            "characterization requires exact frozen "
                                            "operation determinants"
                                        )
                                    return identity
                                except KeyError as exc:
                                    raise OperationConflict(
                                        "characterization unit is outside owned tasks"
                                    ) from exc

                            units = [replace(unit, run=method_view) for unit in units]

                            def retain_pdf_observation(
                                unit_ref,
                                product,
                                *,
                                claimed_tasks=tuple(claimed),
                                active=check_active,
                            ):
                                from corpus_structure.semantic.pdf_integrated import (
                                    store_pdf_observation,
                                )
                                from corpus_structure.semantic.product_reference import (
                                    ProductReference,
                                )

                                task = _retained_claim(unit_ref, claimed_tasks, active)
                                with engine.begin() as publication_conn:
                                    digest = store_pdf_observation(
                                        publication_conn,
                                        task_id=task.task_id,
                                        attempt=task.attempt,
                                        holder=holder,
                                        product=product,
                                    )
                                return ProductReference(
                                    task.task_id, product.values()["product_key"], digest
                                )

                            def retain_pdf_records(
                                unit_ref,
                                product,
                                *,
                                claimed_tasks=tuple(claimed),
                                active=check_active,
                            ):
                                from pathlib import Path

                                from corpus_structure.orchestrate.pdf_streaming import (
                                    publish_pdf_record_draft,
                                )
                                from corpus_structure.semantic.product_reference import (
                                    ProductReference,
                                )

                                task = _retained_claim(unit_ref, claimed_tasks, active)
                                published = publish_pdf_record_draft(
                                    engine,
                                    task,
                                    holder,
                                    product,
                                    directory=Path("build/pdf-publication"),
                                    check_active=active,
                                )
                                return ProductReference(
                                    published.task_id,
                                    published.product_key,
                                    published.logical_digest,
                                )

                            def produce_pdf_records(
                                unit_ref,
                                request,
                                *,
                                claimed_tasks=tuple(claimed),
                                active=check_active,
                            ):
                                from pathlib import Path

                                from corpus_structure.orchestrate.pdf_streaming import (
                                    produce_published_pdf_records,
                                )
                                from corpus_structure.semantic.product_reference import (
                                    ProductReference,
                                )

                                task = _retained_claim(unit_ref, claimed_tasks, active)
                                published = produce_published_pdf_records(
                                    engine,
                                    task,
                                    holder,
                                    request,
                                    directory=Path("build/pdf-production"),
                                    check_active=active,
                                )
                                return ProductReference(
                                    published.task_id,
                                    published.product_key,
                                    published.logical_digest,
                                )

                            from corpus_structure.cli.observation_logging import (
                                event,
                            )

                            event(
                                "method_started",
                                "Source method started",
                                selected_tasks=len(claimed),
                                run_id=rid,
                                method=method.name,
                                task_id=claimed[0].task_id,
                                attempt=claimed[0].attempt,
                                activity="computation",
                            )
                            results = yield from _method_plan(
                                method,
                                units,
                                config.config,
                                MethodContext(
                                    method_view,
                                    scoped_reader,
                                    method_settings,
                                    logging.getLogger(method.name),
                                    check_active=check_active,
                                    characterization_operation=characterization_operation,
                                    retain_pdf_records=retain_pdf_records,
                                    produce_pdf_records=produce_pdf_records,
                                    retain_pdf_observation=retain_pdf_observation,
                                ),
                            )
                            event(
                                "method_reduction",
                                "Reducing source method replies",
                                run_id=rid,
                                task_ids=[task.task_id for task in claimed],
                                method=method.name,
                                activity="reduction",
                            )
                            for task, result in zip(claimed, results, strict=True):
                                from corpus_structure.semantic.operations import (
                                    prepare_unit_completion,
                                )
                                from corpus_structure.semantic.query import read_snapshot

                                def prepare_completion(task=task, result=result):
                                    with read_snapshot(engine) as preparation_conn:
                                        return prepare_unit_completion(
                                            preparation_conn,
                                            task_id=task.task_id,
                                            attempt=task.attempt,
                                            holder=holder,
                                            prepared=prepared,
                                            result=result,
                                            method=method,
                                            configuration_hash=config.config_hash,
                                            source=result.ref.unit_key or "run",
                                            records=result.records,
                                            regional_preparation=claim_region,
                                        )

                                (intent,) = yield (claim_region.read_work(prepare_completion),)
                                event(
                                    "task_publication",
                                    "Publishing source task",
                                    run_id=rid,
                                    task_id=task.task_id,
                                    attempt=task.attempt,
                                    method=method.name,
                                    activity="publication",
                                )
                                check_active.settle(task, intent.apply)
                                if result.error is not None:
                                    raise OperationConflict(result.error)
                            event(
                                "method_finished",
                                "Source method finished",
                                selected_tasks=len(claimed),
                                run_id=rid,
                                method=method.name,
                                task_id=claimed[0].task_id,
                                attempt=claimed[0].attempt,
                            )

                    def execute_claim(method, config, claimed, permit):
                        from corpus_structure.semantic.execution_preparation import (
                            RegionalPreparation,
                        )

                        with ExitStack() as inputs:
                            claim_region = regional_preparation
                            if claim_region is None:
                                claim_region = inputs.enter_context(
                                    RegionalPreparation(execution_preparation)
                                )
                            return (
                                yield from execute_claim_body(method, config, claimed, claim_region)
                            )

                    from .ready import SourceClaimFrontier, source_admission

                    def register_ready_dependencies(pending=deferred):
                        nonlocal reported_prerequisite_wait
                        with engine.begin() as dependency_conn:
                            ready, updates = [], {}
                            for entry in pending:
                                method, config, cid, ref, parents = entry
                                if not all(
                                    parent in registered or parent in updates for parent in parents
                                ):
                                    continue
                                parent_tasks = [
                                    updates[parent] if parent in updates else registered[parent]
                                    for parent in parents
                                ]
                                task_table = table("ops.task")
                                parent_rows = dependency_conn.execute(
                                    select(
                                        task_table.c.id,
                                        task_table.c.status,
                                        task_table.c.reused_task_id,
                                    ).where(task_table.c.id.in_(parent_tasks))
                                ).all()
                                if len(parent_rows) != len(parent_tasks) or not all(
                                    row.status in _READY_SOURCE_TASKS for row in parent_rows
                                ):
                                    if not reported_prerequisite_wait:
                                        from corpus_structure.cli.observation_logging import (
                                            event,
                                        )

                                        event(
                                            "method_prerequisite_wait",
                                            "Waiting for method prerequisites",
                                            run_id=rid,
                                            task_ids=parent_tasks,
                                            method=method.name,
                                            activity="prerequisite_wait",
                                        )
                                        reported_prerequisite_wait = True
                                    continue
                                producer = None
                                if (
                                    config.params.get("source_dependencies")
                                    in _SAME_VIEW_DEPENDENCIES
                                ):
                                    (parent,) = parent_rows
                                    producer = BoundSourceProducer(
                                        parent.id, parent.reused_task_id or parent.id
                                    )
                                task_id = register_ref(
                                    dependency_conn,
                                    method,
                                    config,
                                    cid,
                                    ref,
                                    producer=producer,
                                )
                                for parent_task in parent_tasks:
                                    dependency_conn.execute(
                                        select(
                                            func.ops.add_source_task_dependency(
                                                task_id, parent_task
                                            )
                                        )
                                    )
                                updates[(cid, ref.unit_id)] = task_id
                                ready.append(entry)
                        return ready, updates

                    def prepare_claims(pending=deferred):
                        # Each transaction closes before a capacity wait. Only its
                        # committed identities enter invocation-local state.
                        if pending:
                            read = source_reads.read_work(register_ready_dependencies).try_submit()
                            if read is None:
                                return False
                            ready, updates = read.collect()
                            read.retire()
                            registered.update(updates)
                            pending[:] = [entry for entry in pending if entry not in ready]
                        return True

                    def claim_next(method, config, cid):
                        with engine.begin() as conn:
                            return claim_tasks(
                                conn,
                                run_id=RunId(rid),
                                config_id=MethodConfigId(cid),
                                holder=holder,
                                limit=1,
                                prepared=prepared,
                            )

                    def capacity_wait(method):
                        nonlocal reported_capacity_wait
                        if not reported_capacity_wait:
                            from corpus_structure.cli.observation_logging import event

                            event(
                                "method_capacity_wait",
                                "Waiting for method capacity",
                                run_id=rid,
                                method=method.name,
                                activity="capacity_wait",
                            )
                            reported_capacity_wait = True

                    yield from SourceClaimFrontier(
                        scheduled,
                        source_admission(execution_preparation),
                        claim=claim_next,
                        execute=execute_claim,
                        prepare=prepare_claims,
                        has_prerequisites=lambda pending=deferred: bool(pending),
                        capacity_wait=capacity_wait,
                    ).plan()
        finally:
            import sys

            if execution_preparation is None:
                _close_source_resources(registry, sys.exception())
        with supervisor_conn.begin():
            conn = supervisor_conn
            cut = seal_cut(conn, rid, "source-ready")
            queued = (
                propose_agents(conn, rid, prepared, registry, policy_source)
                if graph.policy_propose and policy_source is not None
                else 0
            )
            record_supervisor(conn, rid, waiting=True)
        from corpus_structure.semantic.operation_results import validate_result_dimension

        status = "awaiting_agent" if queued else "source_ready"
        validate_result_dimension(prepared, "execute_source", "readiness", status, field="status")
        return BoundRunReport(
            run_id=rid,
            status=status,
            release_id=prepared.release_id,
            realization_id=binding.input_realization_id,
            cut_id=cut,
            characterization_views=tuple(characterization_views),
        )
    except BaseException as exc:
        from asyncio import CancelledError

        from corpus_structure.semantic.operations import end_source_run

        failure = (
            None
            if isinstance(exc, (KeyboardInterrupt, CancelledError, GeneratorExit))
            else {"message": str(exc), "exception": type(exc).__name__}
        )
        try:
            with engine.begin() as conn:
                end_source_run(conn, RunId(rid), failure=failure, prepared=prepared)
        except BaseException as cleanup_error:
            exc.add_note(f"source run cleanup failed: {cleanup_error}")
        raise
    finally:
        try:
            supervisor.close()
        finally:
            run_context.close()


def _retain_source_originals(engine, claimed, method, config, holder, prepared, active):
    """Prepare owned originals without holding another task's publication lock."""
    original_recipe = getattr(method, "original_recipe", None)
    if original_recipe is None:
        return
    from corpus_structure.semantic.operations import read_original
    from corpus_structure.semantic.pdf_contracts import store_pdf_original
    from corpus_structure.semantic.query import read_snapshot

    recipe = original_recipe(config)
    for task in claimed:
        active()
        with read_snapshot(engine) as conn:
            document_id = task.unit_id
            if task.unit_type == "source_view":
                document_id = conn.execute(
                    select(table("kb.source_view").c.document_id).where(
                        table("kb.source_view").c.id == task.unit_id
                    )
                ).scalar_one()
            if document_id is None or task.unit_type not in {"document", "source_view"}:
                raise OperationConflict("original preparation requires an original-bound task")
            original = read_original(conn, DocumentId(document_id), prepared=prepared)
        active()
        with engine.begin() as conn:
            store_pdf_original(
                conn,
                task_id=task.task_id,
                attempt=task.attempt,
                holder=holder,
                original=original,
                recipe_bytes=recipe,
            )


def _retained_claim(unit_ref, claimed_tasks, active):
    active()
    matches = [
        task
        for task in claimed_tasks
        if (task.unit_type, task.unit_id, task.unit_key)
        == (str(unit_ref.unit_type), unit_ref.unit_id, unit_ref.unit_key)
    ]
    if len(matches) != 1:
        raise OperationConflict("PDF publication is outside the claimed unit")
    return matches[0]


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


def agent_packet(
    conn: Any,
    run_id: int,
    task_id: int,
    prepared: Any,
    *,
    preparation: dict | None = None,
    read_budget=None,
):
    """Rebuild exactly the packet hashed by queue_agent; no active release lookup."""
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


def queue_agent(
    conn: Any,
    *,
    run_id: RunId,
    prepared: Any,
    configuration: Mapping[str, Any],
    units: Any,
    configuration_name: str = "extract",
    method_name: str = "agent.opus",
    trigger: Mapping[str, Any] | None = None,
    skip_reason: str | None = None,
    preparation: dict | None = None,
) -> list[TaskId]:
    """Queue policy-selected source units under the same packet definition used by MCP."""
    from hashlib import sha256

    from corpus_structure.methods.llm.agent_opus import AgentOpusConfig
    from corpus_structure.methods.llm.producer import producer_binding
    from corpus_structure.semantic.operations import OperationDescriptor

    units = tuple(units)
    producer = producer_binding(method_name, configuration)
    for ref in units:
        producer_binding(method_name, configuration, unit=ref.unit_type)
    method = OperationDescriptor(
        producer.method,
        producer.version,
        "agent",
        producer.execution_kind,
        TaskUnitType(producer.unit),
        AgentOpusConfig,
        "agent",
    )
    config_hash = (
        "configuration:"
        + sha256(canonical_bytes([method.name, method.version, dict(configuration)])).hexdigest()
    )
    preparation = {} if preparation is None else preparation
    if "view" not in preparation:
        preparation["view"] = run_view(conn, run_id, prepared)
    view = preparation["view"]
    binding = view.binding
    snapshot = view.options.get("agent_configs", {})
    if (
        not isinstance(snapshot, dict)
        or f"{method_name}/{configuration_name}" not in snapshot
        or canonical_bytes(snapshot[f"{method_name}/{configuration_name}"])
        != canonical_bytes(dict(configuration))
    ):
        raise OperationConflict("agent configuration differs from immutable run snapshot")
    recorded = preparation.setdefault("configurations", {})
    key = (method_name, configuration_name, config_hash)
    if key not in recorded:
        recorded[key] = record_method(
            conn, method, configuration_name, configuration, config_hash, prepared=prepared
        )
    config_id = recorded[key]
    fresh_names = view.options.get("fresh", [])
    if not isinstance(fresh_names, list) or any(not isinstance(name, str) for name in fresh_names):
        raise OperationConflict("run fresh selector is not a string list")
    tasks = []
    for ref in units:
        if ref.unit_type != method.unit_type:
            raise OperationConflict("agent unit differs from its declared method contract")
        from corpus_structure.semantic.analysis_contracts import invocation_identity

        packet = (
            None
            if skip_reason is not None
            else _packet_for_unit(conn, run_id, prepared, ref, configuration, preparation)
        )
        digest = invocation_identity(
            prepared,
            release=binding.release_id,
            source={
                "realization": binding.input_realization_id,
                "revision": binding.input_revision,
                "dependencies": binding.dependency_digest,
            },
            configuration={"method": method.name, "version": method.version, "hash": config_hash},
            policy={"trigger": dict(trigger or {}), "options": view.options},
            unit={"type": str(ref.unit_type), "id": ref.unit_id, "key": ref.unit_key},
            skip_reason=skip_reason,
            packet_hash=None if packet is None else packet.hash,
        )
        task_id = create_task(
            conn,
            run_id=run_id,
            config_id=config_id,
            stage="propose",
            unit_type=str(ref.unit_type),
            unit_id=ref.unit_id,
            unit_key=ref.unit_key,
            input_hash=digest,
            packet_hash=None if packet is None else packet.hash,
            agent=True,
            fresh=method_name in fresh_names,
            trigger={
                **dict(trigger or {}),
                "configuration_name": configuration_name,
                "producer_binding": producer.values(),
            },
            skip_reason=skip_reason,
        )
        tasks.append(task_id)
        if packet is not None:
            from corpus_structure.semantic.source_frames import capture_source_frame

            reused = conn.execute(
                select(table("ops.task").c.reused_task_id).where(table("ops.task").c.id == task_id)
            ).scalar_one()
            if reused is None:
                capture_source_frame(conn, task_id, packet)
    return tasks


def propose_agents(conn, run_id, prepared, registry, policy_source):
    """Evaluate the declared propose chain against frozen source reports, retaining unknowns."""
    from collections import Counter
    from types import SimpleNamespace

    from corpus_structure.core.vocab import MethodTier, PolicyChain
    from corpus_structure.orchestrate import policy

    view = run_view(conn, run_id, prepared)
    configs = TypeAdapter(dict[str, dict[str, JsonValue]]).validate_python(
        view.options.get("agent_configs")
    )
    rules = policy.admit_source_policy(policy_source, registry, prepared)
    t, c, m = table("ops.task"), table("ops.method_config"), table("ops.method")
    origin = t.alias("origin")
    from sqlalchemy import func

    states = {
        (r.method, r.unit_type, r.unit_id): r.status
        for r in conn.execute(
            select(
                m.c.name.label("method"),
                t.c.unit_type,
                t.c.unit_id,
                func.coalesce(origin.c.status, t.c.status).label("status"),
            )
            .join(c, t.c.method_config_id == c.c.id)
            .join(m, c.c.method_id == m.c.id)
            .outerjoin(origin, t.c.reused_task_id == origin.c.id)
            .where(t.c.run_id == run_id)
        )
    }
    native_allowed = None
    counts = Counter()
    scheduled = set()
    open_count = 0
    decisions = []
    preparations = {}
    unit_views = {}
    for entry in rules.entries(PolicyChain.PROPOSE):
        method = registry.method(entry.method)
        if method.tier != MethodTier.AGENT or entry.unit_type != method.unit_type:
            raise OperationConflict(
                "semantic propose requires a supported agent method with matching source unit type"
            )
        config_name = entry.entry.do.method.split("/", 1)[1]
        config = registry.overlay(entry.method, config_name)
        for ref in method.select(view, config):
            if ref not in unit_views:
                unit_views[ref] = _unit(conn, view, ref)
            unit = unit_views[ref]
            if unit.document_id is None or ref.unit_key is None:
                raise OperationConflict("propose requires a bound source document and unit key")
            if (
                unit.source_view_id is None
                or ref.unit_type is not TaskUnitType.SOURCE_VIEW
                or ref.unit_id != unit.source_view_id
            ):
                raise OperationConflict("propose requires a bound selected PDF SourceView")
            unit_kind = TaskUnitType.SOURCE_VIEW.value
            if native_allowed is None:
                native_allowed = {selected.id for selected in view.reader.source_views()}
            scope_allowed = unit.source_view_id in native_allowed
            # Recognized local blocks do not establish the semantics of the whole section.
            kind, bearing = None, None

            def outcome(name: str, unit: UnitView = unit) -> str | None:
                keys = [
                    (name, "source_view", unit.source_view_id),
                    (name, "document", unit.document_id),
                ]
                for key in keys:
                    if key in states:
                        return {"done": "produced", "empty": "empty", "failed": "failed"}.get(
                            states[key]
                        )
                return None

            thing = {
                "phase": view.phase,
                "iteration": 0,
                "unit": SimpleNamespace(kind=unit_kind, statement_kind=kind, claim_bearing=bearing),
                "ran": lambda name: outcome(name) is not None,
                "outcome": outcome,
            }
            if entry.key not in {match.key for match in rules.matches(PolicyChain.PROPOSE, thing)}:
                continue
            identity = (entry.method, canonical_bytes(configs[entry.entry.do.method]), ref.unit_key)
            if identity in scheduled:
                continue
            scheduled.add(identity)
            reason = (
                "scope"
                if not scope_allowed
                else "limit"
                if entry.entry.do.limit is not None and counts[entry.key] >= entry.entry.do.limit
                else None
            )
            trigger: dict[str, Any] = {
                "rule_key": entry.key,
                "configuration_name": config_name,
                "condition": entry.entry.when,
                "classification": "unknown" if bearing is None else "known",
                "values": {
                    "unit.kind": unit_kind,
                    "unit.statement_kind": kind,
                    "unit.claim_bearing": bearing,
                    "phase": view.phase,
                    "iteration": 0,
                },
            }
            trigger["scope_limit"] = {
                "scope": view.options.get("scope"),
                "limit": entry.entry.do.limit,
                "position": counts[entry.key],
            }
            decisions.append((ref, entry.method, config_name, trigger, reason))
            if reason is None:
                counts[entry.key] += 1
    for ref, method_name, config_name, trigger, reason in decisions:
        preparation = preparations.setdefault(
            (method_name, config_name),
            {
                "view": view,
                "units": unit_views,
            },
        )
        task = queue_agent(
            conn,
            run_id=run_id,
            prepared=prepared,
            configuration=configs[f"{method_name}/{config_name}"],
            units=[ref],
            configuration_name=config_name,
            method_name=method_name,
            trigger=trigger,
            skip_reason=reason,
            preparation=preparation,
        )[0]
        if reason is None and conn.execute(
            select(t.c.status).where(t.c.id == task)
        ).scalar_one() in ("pending", "running", "awaiting_agent"):
            open_count += 1
    return open_count


def _source_step_groups(steps, configs, prepared):
    """Fuse only the admitted, compatible adjacent rendition consumers."""
    from corpus_structure.methods.math.methods import ExtractMathConfig, NormalizeFormulaConfig
    from corpus_structure.semantic.analysis_contracts import supports_shared_math

    items = list(steps)
    index = 0
    while index < len(items):
        first = items[index]
        group = [first]
        if index + 1 < len(items) and {
            first.config.split("/", 1)[0],
            items[index + 1].config.split("/", 1)[0],
        } == {"text.native_evidence", "text.formal_evidence"}:
            group.append(items[index + 1])
            index += 1
        elif index + 1 < len(items) and supports_shared_math(prepared):
            second = items[index + 1]
            names = (first.config.split("/", 1)[0], second.config.split("/", 1)[0])
            if set(names) == {"normalize.formula", "extract.math"}:
                left, right = (configs[name].config for name in names)
                if (
                    isinstance(left, (ExtractMathConfig, NormalizeFormulaConfig))
                    and isinstance(right, (ExtractMathConfig, NormalizeFormulaConfig))
                    and left.section() == right.section()
                    and left.parse_seconds == right.parse_seconds
                ):
                    group.append(second)
                    index += 1
        yield group
        index += 1


def _close_source_resources(registry, primary: BaseException | None) -> None:
    """Attempt every owned closer before returning or cancelling the source run."""
    errors = []
    for method in registry.methods():
        close = getattr(method, "close", None)
        if close is None:
            continue
        try:
            close()
        except BaseException as error:
            errors.append(error)
    if not errors:
        return
    if primary is not None:
        for error in errors:
            primary.add_note("source resource teardown failed: " + str(error)[:1800])
        return
    fatal = next((error for error in errors if not isinstance(error, Exception)), errors[0])
    for error in errors:
        if error is not fatal:
            fatal.add_note("additional source resource teardown failure: " + str(error)[:1800])
    raise fatal
