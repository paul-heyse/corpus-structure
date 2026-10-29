"""The existing deterministic method graph on explicitly selected semantic run bindings."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel, JsonValue, TypeAdapter
from sqlalchemy import select

from corpus_structure.core.method import MethodContext, UnitRef, UnitView
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import (
    OperationBinding,
    OperationConflict,
    claim_tasks,
    complete_unit_result,
    create_run,
    create_task,
    record_method,
    run_view,
    seal_cut,
    start_run,
)


class BoundRunReport(BaseModel):
    run_id: int
    status: str
    release_id: str
    realization_id: str
    cut_id: int | None = None


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
) -> BoundRunReport:
    """Run the current source graph; hand its immutable cut to consolidation/proposal owners.

    This result establishes source preparation only. It does not report grading, inference,
    or whole-run completion. Source work never chooses an unbound latest interpretation.
    """
    from hashlib import sha256

    from corpus_structure.orchestrate.runs import code_commit
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
    registry = registry.bind_release(prepared)
    configurations = dict(configurations or {})
    configs = {}
    for _, steps in graph.stages:
        for step in steps:
            method, _, default = step.config.partition("/")
            name = configurations.get(method, default or "default")
            configs[method] = registry.resolve(method, name)
    fresh = tuple(sorted(set(fresh)))
    unknown = set(fresh) - {method.name for method in registry.methods()}
    if unknown:
        raise OperationConflict("fresh names unregistered methods: " + ", ".join(sorted(unknown)))
    agent_configs = {}
    from corpus_structure.semantic.proposals import SEMANTIC_AGENT_VERSION

    operation_versions = {name: registry.method(name).version for name in configs}
    from corpus_structure.core.method import ArtifactRef, PackSection, config_references

    for method_name, config_name in registry.named():
        if method_name != "agent.opus":
            continue
        config = registry.overlay(method_name, config_name)
        raw = config.model_dump(mode="json")
        markers = config_references(type(config))
        for path, marker in markers.items():
            if isinstance(marker, PackSection):
                if len(path) != 1:
                    raise OperationConflict("nested agent operation sections are unsupported")
                raw[path[0]] = registry.file.sections[marker.name]
        values = type(config).model_validate(raw).model_dump(mode="json")
        for path, marker in markers.items():
            if isinstance(marker, ArtifactRef):
                values.pop(path[0], None)
        agent_configs[config_name] = values
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
        if not docs:
            raise OperationConflict("bound project has no registered source documents")
        import json
        from importlib.metadata import version

        library_names = set()
        if "ingest.html" in configs:
            library_names.update(
                ("regex", "spacy", "en-core-web-sm", "html5lib", "lxml", "cssselect2")
            )
        if set(configs) & {"extract.math", "normalize.formula"}:
            library_names.add("lark")
        if "resolve.symbol_scope" in configs:
            library_names.update(("spacy", "en-core-web-sm"))
        if graph.policy_propose:
            library_names.update(("rapidfuzz", "regex", "rule-engine"))
        dependency_manifest = {
            "parent": json.loads(binding.dependencies),
            "libraries": {name: version(name) for name in sorted(library_names)},
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
        }
        binding = OperationBinding(
            binding.release_id,
            binding.input_realization_id,
            binding.input_revision,
            canonical_bytes(dependency_manifest),
        )
        options = {
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
        for stage, steps in graph.stages:
            for step in steps:
                name = step.config.split("/", 1)[0]
                method = registry.method(name)
                config = configs[name]
                with engine.begin() as conn:
                    cid = record_method(
                        conn, method, config.name, config.params, config.config_hash
                    )
                    view = run_view(conn, rid, prepared)
                    for ref in method.select(view, config.config):
                        unit = _unit(conn, view, ref)
                        digest = method.input_digest(unit, config.config)
                        ih = sha256(
                            canonical_bytes(
                                [
                                    prepared.release_id,
                                    binding.input_realization_id,
                                    binding.input_revision,
                                    binding.dependency_digest,
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
                            fresh=name in fresh,
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

                                read_original(conn, ref.unit_id)
                while True:
                    with engine.begin() as conn:
                        claimed = claim_tasks(
                            conn,
                            run_id=rid,
                            config_id=cid,
                            holder=holder,
                            limit=method.resources.batch_size,
                        )
                    if not claimed:
                        break
                    with engine.connect() as conn:
                        view = run_view(conn, rid, prepared)
                        units = [
                            _unit(
                                conn,
                                view,
                                UnitRef(TaskUnitType(t.unit_type), t.unit_id, t.unit_key),
                            )
                            for t in claimed
                        ]
                        results = method.run(
                            units,
                            config.config,
                            MethodContext(
                                view, view.reader, method_settings, logging.getLogger(method.name)
                            ),
                        )
                        conn.rollback()
                    for task, result in zip(claimed, results, strict=True):
                        with engine.begin() as conn:
                            complete_unit_result(
                                conn,
                                task_id=task.task_id,
                                attempt=task.attempt,
                                holder=holder,
                                prepared=prepared,
                                result=result,
                                method=method,
                                configuration_hash=config.config_hash,
                                source=result.ref.unit_key or "run",
                            )
                        if result.error is not None:
                            raise OperationConflict(result.error)
        with engine.begin() as conn:
            cut = seal_cut(conn, rid, "source-ready")
            queued = (
                propose_agents(conn, rid, prepared, registry, policy_source)
                if graph.policy_propose and policy_source is not None
                else 0
            )
        return BoundRunReport(
            run_id=rid,
            status="awaiting_agent" if queued else "source_ready",
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
                end_source_run(conn, rid, failure=failure)
        except BaseException as cleanup_error:
            exc.add_note(f"source run cleanup failed: {cleanup_error}")
        raise


def _unit(conn: Any, view: Any, ref: Any) -> UnitView:
    if ref.unit_type == TaskUnitType.DOCUMENT:
        return UnitView(ref, view, document_id=ref.unit_id)
    if ref.unit_type == TaskUnitType.RENDITION:
        r = table("kb.rendition")
        doc = conn.execute(select(r.c.document_id).where(r.c.id == ref.unit_id)).scalar_one()
        return UnitView(ref, view, document_id=doc, rendition_id=ref.unit_id)
    if ref.unit_type == TaskUnitType.SEGMENT:
        s = table("kb.segment")
        r = table("kb.rendition")
        row = conn.execute(
            select(s.c.rendition_id, r.c.document_id)
            .join(r, s.c.rendition_id == r.c.id)
            .where(s.c.id == ref.unit_id)
        ).one()
        return UnitView(ref, view, document_id=row.document_id, rendition_id=row.rendition_id)
    return UnitView(ref, view)


def _packet_for_unit(
    conn: Any, run_id: int, prepared: Any, ref: Any, configuration: Mapping[str, Any]
):
    """Shared queue/serve preparation including recorded M13 standing context."""
    from corpus_structure.core.evidence import MacroDef
    from corpus_structure.methods.llm.packet import MAX_KNOWN, PacketTooLarge, unit_inputs
    from corpus_structure.orchestrate.semantic_references import document_references
    from corpus_structure.semantic.operations import lock_input_snapshot
    from corpus_structure.semantic.proposals import (
        KnownProposalEntity,
        proposal_packet,
        source_frame,
    )

    lock_input_snapshot(conn, run_id)
    view = run_view(conn, run_id, prepared)
    snapshot = view.options.get("agent_configs")
    if not isinstance(snapshot, dict) or not any(
        canonical_bytes(value) == canonical_bytes(dict(configuration))
        for value in snapshot.values()
    ):
        raise OperationConflict("agent configuration differs from immutable run snapshot")
    unit = _unit(conn, view, ref)
    if unit.rendition_id is None or unit.document_id is None or ref.unit_key is None:
        raise OperationConflict("an agent proposal requires a located source unit")
    raw_math = configuration.get("math", {})
    macros = {name: MacroDef(body=body) for name, body in raw_math.get("macros", {}).items()}
    inputs = unit_inputs(
        view.reader,
        rendition_id=unit.rendition_id,
        document_id=unit.document_id,
        unit_key=ref.unit_key,
        reference_run_id=None,
        pack_macros=macros,
    )
    references = document_references(conn, view, unit.document_id, limit=MAX_KNOWN)
    if references:
        from dataclasses import replace

        from corpus_structure.methods.llm.packet import KnownEntity

        inputs = replace(
            inputs,
            known=tuple(
                KnownEntity(entity.label, ",".join(entity.classes), entity.aliases)
                for entity in references
            ),
        )
    try:
        rendered = inputs.packet(configuration.get("packet_cap_chars", 18000))
    except PacketTooLarge as exc:
        raise OperationConflict(str(exc)) from exc
    return proposal_packet(
        prepared,
        source_frame(ref.unit_key, inputs.content, inputs.page, rendered.sentences),
        guideline=view.reader.guideline(),
        configuration=configuration,
        macros=inputs.macros,
        known_classes={entity.entity_id: entity.classes for entity in references},
        known_entities=tuple(
            KnownProposalEntity(entity.entity_id, entity.label, entity.aliases)
            for entity in references
        ),
        bootstrap_terms=tuple(entity.label for entity in inputs.known or () if entity.cls is None)
        if not references
        else (),
    )


def agent_packet(conn: Any, run_id: int, task_id: int, prepared: Any):
    """Rebuild exactly the packet hashed by queue_agent; no active release lookup."""
    t, c = table("ops.task"), table("ops.method_config")
    row = (
        conn.execute(
            select(t, c.c.params)
            .join(c, t.c.method_config_id == c.c.id)
            .where(t.c.id == task_id, t.c.run_id == run_id)
        )
        .mappings()
        .one()
    )
    ref = UnitRef(TaskUnitType(row["unit_type"]), row["unit_id"], row["unit_key"])
    from corpus_structure.semantic.proposals import ProposalRefused

    try:
        packet = _packet_for_unit(conn, run_id, prepared, ref, row["params"])
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
    run_id: int,
    prepared: Any,
    configuration: Mapping[str, Any],
    units: Any,
    configuration_name: str = "extract",
    trigger: Mapping[str, Any] | None = None,
    skip_reason: str | None = None,
) -> list[int]:
    """Queue policy-selected source units under the same packet definition used by MCP."""
    from hashlib import sha256

    from corpus_structure.semantic.operations import OperationDescriptor
    from corpus_structure.semantic.proposals import SEMANTIC_AGENT_VERSION

    if not configuration.get("model"):
        raise ValueError("agent configuration declares its model")
    from corpus_structure.methods.llm.agent_opus import AgentOpusConfig

    method = OperationDescriptor(
        "agent.opus",
        SEMANTIC_AGENT_VERSION,
        "agent",
        "agent",
        TaskUnitType.SEGMENT,
        AgentOpusConfig,
        "agent",
    )
    config_hash = (
        "configuration:"
        + sha256(canonical_bytes([method.name, method.version, dict(configuration)])).hexdigest()
    )
    config_id = record_method(conn, method, configuration_name, configuration, config_hash)
    view = run_view(conn, run_id, prepared)
    binding = view.binding
    snapshot = view.options.get("agent_configs", {})
    if (
        not isinstance(snapshot, dict)
        or configuration_name not in snapshot
        or canonical_bytes(snapshot[configuration_name]) != canonical_bytes(dict(configuration))
    ):
        raise OperationConflict("agent configuration differs from immutable run snapshot")
    fresh_names = view.options.get("fresh", [])
    if not isinstance(fresh_names, list) or any(not isinstance(name, str) for name in fresh_names):
        raise OperationConflict("run fresh selector is not a string list")
    tasks = []
    for ref in units:
        if ref.unit_type != method.unit_type:
            raise OperationConflict("agent unit differs from its declared method contract")
        packet = _packet_for_unit(conn, run_id, prepared, ref, configuration)
        digest = sha256(
            canonical_bytes(
                [
                    binding.release_id,
                    binding.input_realization_id,
                    binding.input_revision,
                    binding.dependency_digest,
                    method.version,
                    config_hash,
                    packet.hash,
                ]
            )
        ).hexdigest()
        task_id = create_task(
            conn,
            run_id=run_id,
            config_id=config_id,
            stage="propose",
            unit_type=str(ref.unit_type),
            unit_id=ref.unit_id,
            unit_key=ref.unit_key,
            input_hash=digest,
            packet_hash=packet.hash,
            agent=True,
            fresh="agent.opus" in fresh_names,
            trigger={**dict(trigger or {}), "configuration_name": configuration_name},
            skip_reason=skip_reason,
        )
        tasks.append(task_id)
        if skip_reason is None:
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

    from corpus_structure.core.locators import LocatorIndex
    from corpus_structure.core.vocab import MethodTier, PolicyChain
    from corpus_structure.orchestrate import policy
    from corpus_structure.orchestrate.slices import selected

    view = run_view(conn, run_id, prepared)
    configs = TypeAdapter(dict[str, dict[str, JsonValue]]).validate_python(
        view.options.get("agent_configs")
    )
    names = policy.registry_configs(registry)
    from corpus_structure.semantic.statement_types import statement_kinds

    language = policy.unit_language(statement_kinds(prepared), names, nullable_claim_bearing=True)
    rules = policy.compile_policy(policy.parse_policy(policy_source), language, names)
    bearing_kinds = statement_kinds(prepared, subset="claim_bearing")
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
    indices = {}
    counts = Counter()
    scheduled = set()
    open_count = 0
    for entry in rules.entries(PolicyChain.PROPOSE):
        method = registry.method(entry.method)
        if (
            entry.method != "agent.opus"
            or method.tier != MethodTier.AGENT
            or entry.unit_type != method.unit_type
        ):
            raise OperationConflict(
                "semantic propose requires a supported agent method with matching source unit type"
            )
        config_name = entry.entry.do.method.split("/", 1)[1]
        config = registry.overlay(entry.method, config_name)
        for ref in method.select(view, config):
            unit = _unit(conn, view, ref)
            if unit.rendition_id is None or unit.document_id is None or ref.unit_key is None:
                raise OperationConflict("propose requires located source units")
            if unit.rendition_id not in indices:
                d = table("kb.document")
                page = conn.execute(
                    select(d.c.meta).where(d.c.id == unit.document_id)
                ).scalar_one()["page"]
                index = LocatorIndex(view.reader.content(unit.rendition_id), page)
                scope = view.options.get("scope")
                locators = None
                if scope is not None:
                    if not isinstance(scope, dict):
                        raise OperationConflict("recorded scope must be a locator mapping")
                    locators = TypeAdapter(list[str]).validate_python(scope.get("locators"))
                indices[unit.rendition_id] = (index, selected(index, locators))
            index, allowed = indices[unit.rendition_id]
            segment = index.resolve(ref.unit_key)
            hint = segment.attrs.get("hint", {})
            kind = hint.get("statement_kind") if isinstance(hint, dict) else None
            bearing = hint.get("claim_bearing") if isinstance(hint, dict) else None
            if bearing is None and kind is not None:
                bearing = kind in bearing_kinds
            if bearing is not None and not isinstance(bearing, bool):
                raise OperationConflict(
                    "source claim-bearing classification must be boolean or unknown"
                )

            def outcome(name: str, unit: UnitView = unit) -> str | None:
                for key in (
                    (name, "segment", unit.ref.unit_id),
                    (name, "rendition", unit.rendition_id),
                    (name, "document", unit.document_id),
                ):
                    if key in states:
                        return {"done": "produced", "empty": "empty", "failed": "failed"}.get(
                            states[key]
                        )
                return None

            thing = {
                "phase": view.phase,
                "iteration": 0,
                "unit": SimpleNamespace(
                    kind=segment.kind.value, statement_kind=kind, claim_bearing=bearing
                ),
                "target": SimpleNamespace(kind=None, size=None, max_confidence=None, margin=None),
                "budget": SimpleNamespace(agent_packets_left=None, llm_tokens_left=None),
                "ran": lambda name: outcome(name) is not None,
                "outcome": outcome,
                "judged_by": lambda name: False,
                "decision": lambda name: None,
                "confidence": lambda name: None,
            }
            if entry.key not in {match.key for match in rules.matches(PolicyChain.PROPOSE, thing)}:
                continue
            identity = (entry.method, canonical_bytes(configs[config_name]), ref.unit_key)
            if identity in scheduled:
                continue
            scheduled.add(identity)
            reason = (
                "scope"
                if ref.unit_key not in allowed
                else "limit"
                if entry.entry.do.limit is not None and counts[entry.key] >= entry.entry.do.limit
                else None
            )
            trigger = {
                "rule_key": entry.key,
                "configuration_name": config_name,
                "condition": entry.entry.when,
                "classification": "unknown" if bearing is None else "known",
                "values": {
                    "unit.kind": segment.kind.value,
                    "unit.statement_kind": kind,
                    "unit.claim_bearing": bearing,
                    "phase": view.phase,
                    "iteration": 0,
                },
            }
            task = queue_agent(
                conn,
                run_id=run_id,
                prepared=prepared,
                configuration=configs[config_name],
                units=[ref],
                configuration_name=config_name,
                trigger=trigger,
                skip_reason=reason,
            )[0]
            if reason is None:
                counts[entry.key] += 1
            if reason is None and conn.execute(
                select(t.c.status).where(t.c.id == task)
            ).scalar_one() in ("pending", "running", "awaiting_agent"):
                open_count += 1
    return open_count
