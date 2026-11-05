"""The existing deterministic method graph on explicitly selected semantic run bindings."""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any

from pydantic import BaseModel, JsonValue, TypeAdapter
from sqlalchemy import select

from corpus_structure.core.method import MethodContext, UnitRef, UnitView
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.semantic._operation_ids import CutId, DocumentId
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operation_results import MethodConfigId, RunId, TaskId
from corpus_structure.semantic.operations import (
    BoundReader,
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


class BoundRunReport(BaseModel):
    run_id: RunId
    status: str
    release_id: str
    realization_id: str
    cut_id: CutId | None = None


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
    policy_source: str | None = None,
    agent_mode: str = "complete",
    agent_reuse: str = "full",
    kind: str = "full",
    extraction_policy: str = "phase0",
    extraction_policy_config: str | None = None,
    record_acceptance: Sequence[Mapping[str, Any]] = (),
    local_semantic_admission: Sequence[Mapping[str, Any]] = (),
    structural_admission: Sequence[Mapping[str, Any]] = (),
) -> BoundRunReport:
    """Run the current source graph; hand its immutable cut to consolidation/proposal owners.

    This result establishes source preparation only. It does not report grading, inference,
    or whole-run completion. Source work never chooses an unbound latest interpretation.
    """
    from corpus_structure.semantic.contracts import require_bound_operation

    require_bound_operation(prepared, "execute_source")
    from hashlib import sha256

    from corpus_structure.core.provenance import code_commit
    from corpus_structure.semantic.identity import canonical_bytes

    if agent_mode != "complete":
        raise OperationConflict(
            "semantic agent wait barrier is not implemented; "
            "use complete and finalize after automated tasks finish"
        )
    if agent_reuse != "full":
        raise OperationConflict(
            "semantic agent reuse requires the full immutable packet and configuration"
        )
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
    with engine.begin() as conn:
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
        if "structure.definitions" in configs:
            library_names.update(
                (
                    "gliner2",
                    "torch",
                    "transformers",
                    "tokenizers",
                    "safetensors",
                    "threadpoolctl",
                    "sentence-transformers",
                )
            )
        native_libraries = {}
        if set(configs) & {"ingest.pdf", "ingest.pdf_integrated", "enrich.pdf_math"}:
            from corpus_structure.ingest.pdf import pdf_package_versions

            native_libraries = dict(pdf_package_versions())
        if set(configs) & {"extract.math", "normalize.formula"}:
            library_names.add("lark")
        if "extract.m1_annotations" in configs:
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
        options = {
            **({"extraction_policy": extraction_policy} if extraction_policy != "phase0" else {}),
            "domain": domain,
            "corpus": dict(corpus_record)
            if corpus_record is not None
            else {"documents": [d["key"] for d in docs]},
            "scope": dict(scope_record) if scope_record is not None else None,
            "policy": policy_source,
            "agent_mode": agent_mode,
            "agent_reuse": agent_reuse,
            "operation_versions": operation_versions,
            "configs": {m: c.config_hash for m, c in configs.items()},
            "agent_configs": agent_configs,
            "fresh": list(fresh),
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
        start_run(conn, rid)
    holder = f"semantic-source:{rid}"
    try:
        try:
            registered = {}
            for stage, steps in graph.stages:
                for group in _source_step_groups(steps, configs, prepared):
                    scheduled = []

                    def register_ref(conn, view, method, config, cid, ref, stage=stage):
                        unit = _unit(conn, view, ref)
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
                        ih = sha256(
                            canonical_bytes(
                                [
                                    prepared.release_id,
                                    binding.input_realization_id,
                                    binding.input_revision,
                                    sha256(canonical_bytes(scoped_dependencies)).hexdigest(),
                                    method.name,
                                    method.version,
                                    config.config_hash,
                                    digest.bytes.hex(),
                                ]
                            )
                        ).hexdigest()
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
                            fresh=method.name in fresh,
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

                    deferred = []
                    for step in group:
                        name = step.config.split("/", 1)[0]
                        method = registry.method(name)
                        config = configs[name]
                        with engine.begin() as conn:
                            cid = record_method(
                                conn,
                                method,
                                config.name,
                                config.params,
                                config.config_hash,
                                prepared=prepared,
                            )
                            view = run_view(conn, rid, prepared)
                            refs = list(method.select(view, config.config))
                            if config.params.get("source_dependencies") == "ancestor_source_view":
                                required = {ref.unit_id: ref for ref in refs}
                                parent_ids = {}
                                for ref in tuple(refs):
                                    for ancestor in view.reader.ancestor_source_views(ref.unit_id):
                                        required.setdefault(
                                            ancestor.id,
                                            UnitRef(
                                                TaskUnitType.SOURCE_VIEW, ancestor.id, ancestor.key
                                            ),
                                        )
                                for identity in required:
                                    parent_ids[identity] = tuple(
                                        a.id
                                        for a in view.reader.ancestor_source_views(identity)
                                        if a.id in required
                                    )
                                for identity, ref in required.items():
                                    if parent_ids[identity]:
                                        deferred.append(
                                            (
                                                method,
                                                config,
                                                cid,
                                                ref,
                                                tuple(
                                                    (cid, parent) for parent in parent_ids[identity]
                                                ),
                                            )
                                        )
                                    else:
                                        registered[(cid, identity)] = register_ref(
                                            conn, view, method, config, cid, ref
                                        )
                            elif config.params.get("source_dependencies") in {
                                "source_view_interpretation",
                                "source_view_product",
                            }:
                                prerequisite_name = config.params.get("source_dependency_method")
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
                                if not any(entry[2] == prerequisite_cid for entry in scheduled):
                                    scheduled.append(
                                        (prerequisite, prerequisite_config, prerequisite_cid)
                                    )
                                for ref in refs:
                                    key = (prerequisite_cid, ref.unit_id)
                                    if key not in registered:
                                        registered[key] = register_ref(
                                            conn,
                                            view,
                                            prerequisite,
                                            prerequisite_config,
                                            prerequisite_cid,
                                            ref,
                                        )
                                    deferred.append((method, config, cid, ref, (key,)))
                            else:
                                for ref in refs:
                                    registered[(cid, ref.unit_id)] = register_ref(
                                        conn, view, method, config, cid, ref
                                    )
                        scheduled.append((method, config, cid))
                    shared_math_batch = None
                    if len(group) > 1:
                        from corpus_structure.methods.math.methods import MathReadingsBatch

                        shared_math_batch = MathReadingsBatch()
                    from dataclasses import replace

                    from .source_reader import ScopedSourceReader

                    with engine.connect() as conn:
                        view = run_view(conn, rid, prepared)
                        bound_reader = view.reader
                        if not isinstance(bound_reader, BoundReader):
                            raise TypeError("source execution requires the bound database adapter")
                        bound_reader.math_readings_batch = shared_math_batch
                    scoped_reader = ScopedSourceReader(engine, bound_reader)
                    method_view = replace(view, reader=scoped_reader)
                    while True:
                        # Child identity is formed only after its declared parent outputs exist.
                        # Ancestor context does not queue agent work or force math values.
                        if deferred:
                            with engine.begin() as dependency_conn:
                                ready = []
                                for entry in deferred:
                                    method, config, cid, ref, parents = entry
                                    if not all(parent in registered for parent in parents):
                                        continue
                                    parent_tasks = [registered[parent] for parent in parents]
                                    task_table = table("ops.task")
                                    statuses = list(
                                        dependency_conn.execute(
                                            select(task_table.c.status).where(
                                                task_table.c.id.in_(parent_tasks)
                                            )
                                        ).scalars()
                                    )
                                    if not all(
                                        status in {"done", "empty", "reused"} for status in statuses
                                    ):
                                        continue
                                    dependency_view = run_view(dependency_conn, rid, prepared)
                                    task_id = register_ref(
                                        dependency_conn, dependency_view, method, config, cid, ref
                                    )
                                    for parent_task in parent_tasks:
                                        dependency_conn.execute(
                                            __import__("sqlalchemy").text(
                                                "SELECT "
                                                "ops.add_source_task_dependency"
                                                "(:child,:parent)"
                                            ),
                                            dict(child=task_id, parent=parent_task),
                                        )
                                    registered[(cid, ref.unit_id)] = task_id
                                    ready.append(entry)
                                deferred = [entry for entry in deferred if entry not in ready]
                        work = []
                        for method, config, cid in scheduled:
                            with engine.begin() as conn:
                                claimed = claim_tasks(
                                    conn,
                                    run_id=RunId(rid),
                                    config_id=MethodConfigId(cid),
                                    holder=holder,
                                    limit=method.resources.batch_size,
                                    prepared=prepared,
                                )
                            if claimed:
                                work.append((method, config, claimed))
                                break
                        if not work:
                            if deferred:
                                raise OperationConflict(
                                    "required native ancestor context is not ready"
                                )
                            break
                        for method, config, claimed in work:
                            from corpus_structure.semantic.claim_lifetime import maintained_claims

                            with maintained_claims(engine, claimed, holder) as check_active:
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
                                    bound_reader.bind_source_tasks(
                                        {
                                            int(
                                                task.unit_id
                                                if task.unit_type == "document"
                                                else conn.execute(
                                                    select(
                                                        table("kb.source_view").c.document_id
                                                    ).where(
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
                                            UnitRef(
                                                TaskUnitType(t.unit_type), t.unit_id, t.unit_key
                                            ),
                                        )
                                        for t in claimed
                                    ]
                                units = [replace(unit, run=method_view) for unit in units]

                                def retain_pdf_observation(
                                    ref,
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

                                    task = _retained_claim(ref, claimed_tasks, active)
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
                                    ref,
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

                                    task = _retained_claim(ref, claimed_tasks, active)
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
                                    ref,
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

                                    task = _retained_claim(ref, claimed_tasks, active)
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

                                results = method.run(
                                    units,
                                    config.config,
                                    MethodContext(
                                        method_view,
                                        scoped_reader,
                                        method_settings,
                                        logging.getLogger(method.name),
                                        check_active=check_active,
                                        retain_pdf_records=retain_pdf_records,
                                        produce_pdf_records=produce_pdf_records,
                                        retain_pdf_observation=retain_pdf_observation,
                                    ),
                                )
                                for task, result in zip(claimed, results, strict=True):
                                    from corpus_structure.semantic.operations import (
                                        prepare_unit_completion,
                                    )
                                    from corpus_structure.semantic.query import read_snapshot

                                    with read_snapshot(engine) as preparation_conn:
                                        intent = prepare_unit_completion(
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
                                        )
                                    check_active.settle(task, intent.apply)
                                    if result.error is not None:
                                        raise OperationConflict(result.error)
        finally:
            import sys

            _close_source_resources(registry, sys.exception())
        with engine.begin() as conn:
            cut = seal_cut(conn, rid, "source-ready")
            queued = (
                propose_agents(conn, rid, prepared, registry, policy_source)
                if graph.policy_propose and policy_source is not None
                else 0
            )
        from corpus_structure.semantic.operation_results import validate_result_dimension

        status = "awaiting_agent" if queued else "source_ready"
        validate_result_dimension(prepared, "execute_source", "readiness", status, field="status")
        return BoundRunReport(
            run_id=rid,
            status=status,
            release_id=prepared.release_id,
            realization_id=binding.input_realization_id,
            cut_id=cut,
        )
    except BaseException as exc:
        from asyncio import CancelledError

        from corpus_structure.semantic.operations import end_source_run

        failure = (
            None
            if isinstance(exc, (KeyboardInterrupt, CancelledError))
            else {"message": str(exc), "exception": type(exc).__name__}
        )
        try:
            with engine.begin() as conn:
                end_source_run(conn, RunId(rid), failure=failure, prepared=prepared)
        except BaseException as cleanup_error:
            exc.add_note(f"source run cleanup failed: {cleanup_error}")
        raise


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


def _retained_claim(ref, claimed_tasks, active):
    active()
    matches = [
        task
        for task in claimed_tasks
        if (task.unit_type, task.unit_id, task.unit_key)
        == (str(ref.unit_type), ref.unit_id, ref.unit_key)
    ]
    if len(matches) != 1:
        raise OperationConflict("PDF publication is outside the claimed unit")
    return matches[0]


def _unit(conn: Any, view: Any, ref: Any) -> UnitView:
    if ref.unit_type == TaskUnitType.DOCUMENT:
        return UnitView(ref, view, document_id=ref.unit_id)
    if ref.unit_type == TaskUnitType.SOURCE_VIEW:
        source = view.reader.source_view(ref.unit_id)
        return UnitView(
            ref,
            view,
            document_id=source.ref.document_id,
            source_view_id=source.ref.id,
            context_only=(
                not source.ref.analysis_eligible
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
    packet = native_proposal_packet(
        view.reader, unit.source_view_id, prepared, configuration, known=known
    )
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
            select(t, c.c.params, m.c.name.label("method"), m.c.version.label("method_version"))
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
        if index + 1 < len(items) and supports_shared_math(prepared):
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
