"""Finite historical contextual packets from explicit retained facts and controlled vectors.

This fixture starts no provider, worker or task. Native publication remains with the
calling scenario; current computation uses the declared contextual operation owners.
"""

import json
from collections import defaultdict
from dataclasses import asdict
from typing import Any

from sqlalchemy.exc import DBAPIError

from corpus_structure.core.db.lifetime import DatabaseOperationCancelled
from corpus_structure.core.method import UnitResult
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.methods.contextual_candidates import (
    SECTION_CONSTRAINT,
    ContextualQueryConfig,
    coincident_component_terms,
    explicit_definition_section,
    explicit_section_citation,
    outside_section_designators,
    producer_relationship_witnesses,
    relationship_contributions,
    retained_definition_witnesses,
    retained_occurrences,
    section_citation_witnesses,
    section_definition_subject_witnesses,
)
from corpus_structure.methods.contextual_embeddings import E5, QWEN, ContextInput
from corpus_structure.methods.contextual_query import resolve_query_contexts
from corpus_structure.methods.witnessed_source_links import navigation_index
from corpus_structure.semantic.contextual_links import RelationshipWitness, select_relationships
from corpus_structure.semantic.contextual_registry import (
    SectionHeadingTarget,
    component_target_input,
    section_target_input,
)
from corpus_structure.semantic.contextual_retrieval import (
    ChannelHit,
    freeze_inventory,
    fuse_candidates,
)
from corpus_structure.semantic.contextual_storage import enrichment_report
from corpus_structure.semantic.contributions import operation_identity
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.operations import OperationDescriptor
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.source_contexts import record_source_pin


def contextual_descriptor(version="12"):
    return OperationDescriptor(
        "retrieve.contextual",
        version,
        "resolve",
        "encoder",
        TaskUnitType.SOURCE_VIEW,
        ContextualQueryConfig,
    )


def contextual_fixture_inputs(reader, view, cfg):
    """Acquire only this explicit archived source and its exact selected dependencies."""
    exact = getattr(cfg, "required_occurrence_ids", ())
    upstream = reader.source_result(
        view.ref.id,
        cfg.source_dependency_method,
        **(dict(occurrence_ids=exact, semantic_types=cfg.semantic_types) if exact else {}),
    )
    if upstream is None:
        raise ValueError("selected retained occurrence producer is unavailable")
    primary = (
        reader.characterization_layers(
            tuple(ProductReference(**row) for row in cfg.characterization_layers)
        )
        if cfg.characterization_layers
        else {}
    )
    headings = (
        reader.contextual_section_headings(
            cfg.section_sources, view.ref.id, cfg.scope, cfg.effective_version
        )
        if cfg.section_sources
        else None
    )
    catalog = (
        reader.contextual_section_headings(
            (*cfg.section_sources, *cfg.section_catalog_sources),
            view.ref.id,
            cfg.scope,
            cfg.effective_version,
        )
        if cfg.section_catalog_sources
        else None
    )
    semantic = (
        {} if cfg.section_sources else reader.component_semantic_targets(cfg.target_components)
    )
    sections, aliases = {}, {}
    frame = native_source_frame(view, ())
    nodes = {
        node.get("self_ref", node.get("pointer")): node
        for node in json.loads(frame.native_context)["items"]
    }
    for pointer, node in tuple(nodes.items()):
        for index, cell in enumerate(node.get("data", {}).get("table_cells", ())):
            nodes[f"{pointer}/data/table_cells/{index}"] = cell
    carriers, _, _ = retained_occurrences(
        upstream,
        nodes,
        record_source_pin(frame),
        "sealed-fixture-acquisition",
        cfg.semantic_types,
        canonical_producer=bool(cfg.section_sources),
        required_occurrence_ids=exact,
    )
    navigation = navigation_index(primary, frame.projection_digest, source_view_id=view.ref.id)
    has_section_definition = (
        any(
            explicit_definition_section(
                product,
                nodes,
                scope=cfg.scope,
                effective_version=cfg.effective_version,
                primary_layers=navigation,
            )
            is not None
            for product in carriers
        )
        if any(
            "defined-by" in constraint.relation_kinds for constraint in cfg.relationship_constraints
        )
        else False
    )
    if has_section_definition:
        for target in cfg.target_components:
            reference = target.authenticated_reference()
            sections[reference.component_id] = reader.retained_component_section(
                reference, view.ref.native_product.content_digest
            )
            if cfg.definition_alias_refs:
                aliases[reference.component_id] = tuple(
                    reader.retained_component_alias(reference, alias)
                    for alias in cfg.definition_alias_refs
                )
    return dict(
        view=view,
        upstream=upstream,
        primary=primary,
        headings=headings,
        catalog=catalog,
        semantic=semantic,
        sections=sections,
        aliases=aliases,
    )


def _phase(name, occurrence, dependencies, *, result=None, error=None, skipped=False):
    row = dict(
        operation_key=operation_identity("contextual-phase-2", name, occurrence, dependencies),
        question="contextual relationship selection for located occurrence"
        if name == "relationship selection"
        else f"contextual {name} for located occurrence {occurrence}",
        operation_version="2",
        inspected_count=1,
        emitted_count=0,
        computation_dependencies=tuple(dependencies),
        outcome="not_run" if skipped else "failed" if error is not None else "succeeded",
    )
    if result is not None:
        row["report_digest"] = result.rsplit(":", 1)[1]
    if error is not None:
        row["reason"] = f"{type(error).__name__}: {error}"[:768]
    if skipped:
        row["reason"] = "candidate retrieval failed; relationship selection was not attempted"
    return row


def _raise_cancellation(error):
    if isinstance(error, DatabaseOperationCancelled) or (
        isinstance(error, DBAPIError) and getattr(error.orig, "sqlstate", None) == "57014"
    ):
        raise error


def contextual_fixture_result(
    inputs,
    cfg,
    ref,
    *,
    encode=None,
    retrieve=None,
    neighborhood=None,
    choose=select_relationships,
    version="12",
):
    """Assemble one historical packet through actual pure domain kernels.

    ``encode`` is explicitly controlled test data, never a provider success claim.
    Optional retrieval uses the caller's genuine native PostgreSQL read boundary.
    """
    view, upstream, primary = inputs["view"], inputs["upstream"], inputs["primary"]
    if (ref.unit_id, ref.unit_key) != (view.ref.id, view.ref.key):
        raise ValueError("contextual fixture requires its exact original source unit")
    frame = native_source_frame(view, ())
    pin = record_source_pin(frame)
    headings = tuple(
        SectionHeadingTarget.model_validate(row)
        for row in (inputs["headings"] or {}).get("targets", ())
    )
    if cfg.section_sources:
        registry, targets, semantic = section_target_input(cfg.section_sources, headings)
    else:
        registry, targets = component_target_input(cfg.target_components)
        semantic = inputs["semantic"]
    inventory = freeze_inventory(
        targets,
        source_selection=registry,
        scope=cfg.scope,
        effective_version=cfg.effective_version,
        reliable_type="section-heading" if cfg.section_sources else None,
        semantic_targets=semantic,
    )
    nodes = {
        node.get("self_ref", node.get("pointer")): node
        for node in json.loads(frame.native_context)["items"]
    }
    for pointer, node in tuple(nodes.items()):
        for index, cell in enumerate(node.get("data", {}).get("table_cells", ())):
            nodes[f"{pointer}/data/table_cells/{index}"] = cell
    op = operation_identity("retrieve.contextual", version, cfg.model_dump(mode="json"), pin)
    products, contexts, coordinates = retained_occurrences(
        upstream,
        nodes,
        pin,
        op,
        cfg.semantic_types,
        canonical_producer=bool(cfg.section_sources),
        required_occurrence_ids=getattr(cfg, "required_occurrence_ids", ()),
    )
    navigation = navigation_index(primary, frame.projection_digest, source_view_id=view.ref.id)
    heading_mentions, heading_ids, section_mentions, section_targets = (
        {},
        defaultdict(list),
        {},
        defaultdict(list),
    )
    if cfg.section_sources:
        for product in products:
            marker = explicit_section_citation(product, nodes, primary_layers=navigation)
            if marker is not None:
                heading_mentions.setdefault(product["occurrence_id"], []).append((product, marker))
        products = tuple(
            product for carriers in heading_mentions.values() for product, _ in carriers
        )
        contexts = {key: value for key, value in contexts.items() if key in heading_mentions}
        for target in headings:
            if target.target_id in inventory.target_ids:
                heading_ids[target.designator].append(target.target_id)
    for product in products:
        if any(
            "defined-by" in constraint.relation_kinds for constraint in cfg.relationship_constraints
        ):
            section = explicit_definition_section(
                product,
                nodes,
                scope=cfg.scope,
                effective_version=cfg.effective_version,
                primary_layers=navigation,
            )
            if section is not None:
                section_mentions.setdefault(product["occurrence_id"], (section, []))[1].append(
                    product
                )
    for target in cfg.target_components:
        reference = target.authenticated_reference()
        if reference.component_id in inventory.target_ids:
            section_targets[inputs["sections"].get(reference.component_id)].append(reference)
    own_terms = (
        coincident_component_terms(frame, view, semantic, pin)
        if any(
            "denotes" in constraint.relation_kinds for constraint in cfg.relationship_constraints
        )
        else {}
    )
    query_context = (
        resolve_query_contexts(cfg.query_context, primary, products, frame)
        if getattr(cfg, "query_context", None)
        else {}
    )
    profile = E5 if cfg.profile == "e5" else QWEN
    encoder_inputs = [
        ContextInput(
            occurrence,
            frame.unit_ref,
            "query",
            mention,
            text,
            start,
            end,
            representation_digest=query_context[occurrence].representation_digest
            if occurrence in query_context
            else "",
            query_context=query_context[occurrence].rendered
            if occurrence in query_context and query_context[occurrence].signals
            else None,
        )
        for occurrence, (text, start, end, mention) in contexts.items()
    ]
    encoder_inputs.extend(
        ContextInput(
            target.target_id,
            target.source_binding,
            "document",
            target.label,
            target.label + "\n" + target.description,
            0,
            len(target.label),
            parent=target.parent or "",
            type_name=target.type_name,
            representation_digest=target.representation_digest,
        )
        for target in inventory.targets
    )
    encoded, encoder_error = None, None
    try:
        if encode is None:
            raise OSError("controlled encoder failure")
        encoded = encode(encoder_inputs, profile)
    except (ValueError, DBAPIError, RuntimeError, TimeoutError, OSError) as error:
        _raise_cancellation(error)
        encoder_error = error
    vectors = {vector.object_id: vector for vector in encoded.vectors} if encoded else {}
    lists, decisions, phases, resolutions = [], [], [], []
    result_products = list(products)
    for occurrence, (_text, _start, _end, mention) in contexts.items():
        query, retrieval_error = vectors.get(occurrence), encoder_error
        dependencies = (
            (query.vector_id, inventory.inventory_id, profile.profile_id)
            if query
            else (inventory.inventory_id,)
        )
        witnesses, nominations, section_outcome = (), {}, None
        if cfg.section_sources:
            outside = (
                outside_section_designators(
                    headings,
                    tuple(
                        SectionHeadingTarget.model_validate(row)
                        for row in inputs["catalog"]["targets"]
                    ),
                )
                if inputs["catalog"] and inputs["catalog"]["complete"]
                else frozenset()
            )
            resolution, witnesses = section_citation_witnesses(
                heading_mentions[occurrence],
                heading_ids,
                source_binding=frame.unit_ref,
                scope=cfg.scope,
                effective_version=cfg.effective_version,
                complete=inputs["headings"]["complete"],
                budget=cfg.unique_target_budget,
                outside=outside,
            )
            resolutions.append(resolution)
            section_outcome = resolution["outcome"]
        elif any(
            "defined-by" in constraint.relation_kinds for constraint in cfg.relationship_constraints
        ):
            witnesses = retained_definition_witnesses(
                upstream,
                products,
                occurrence,
                inventory,
                set(inventory.target_ids),
                frame.unit_ref,
                cfg.scope,
                cfg.effective_version,
            )
        if occurrence in section_mentions:
            code, carriers = section_mentions[occurrence]
            nominations = {
                reference.component_id: {product["contribution_id"] for product in carriers}
                for reference in section_targets[code]
            }
            witnesses += section_definition_subject_witnesses(
                carriers,
                nodes,
                tuple(
                    (reference, semantic[reference.component_id]["term"]["text"])
                    for reference in section_targets[code]
                ),
                source_binding=frame.unit_ref,
                scope=cfg.scope,
                effective_version=cfg.effective_version,
                primary_layers=navigation,
                aliases=inputs["aliases"] if upstream.get("operation_version") == "17" else None,
            )
        try:
            channels = {}
            if query is not None and retrieve is not None:
                try:
                    exploratory = retrieve(
                        occurrence_id=occurrence,
                        query=query,
                        inventory=inventory,
                        target_vectors=tuple(
                            vector for key, vector in vectors.items() if key in inventory.target_ids
                        ),
                        lexical_query=mention,
                        dimension=profile.dimension,
                        budget=cfg.unique_target_budget,
                        channel_budget=cfg.channel_budget,
                    )
                    channels = {
                        channel.channel: channel.hits for channel in exploratory.channel_results
                    }
                except (ValueError, DBAPIError, TimeoutError, OSError) as error:
                    _raise_cancellation(error)
                    retrieval_error = error
            if retrieval_error is not None and not (
                cfg.section_sources or witnesses or nominations
            ):
                raise retrieval_error
            evidence = defaultdict(set)
            evidence.update(nominations)
            for witness in witnesses:
                evidence[witness.target_id].update(witness.evidence_ids)
            if cfg.section_sources or witnesses or nominations:
                channels["witness"] = tuple(
                    ChannelHit(target, 1.0, tuple(sorted(evidence[target])))
                    for target in sorted(evidence)
                )
            candidates = fuse_candidates(
                occurrence_id=occurrence,
                query=query if retrieval_error is None else None,
                inventory=inventory,
                channels=channels,
                budget=cfg.unique_target_budget,
                channel_budget=cfg.channel_budget,
                lexical_query=mention,
            )
        except (ValueError, DBAPIError, RuntimeError, TimeoutError, OSError) as error:
            _raise_cancellation(error)
            phases.extend(
                (
                    _phase("candidate retrieval", occurrence, dependencies, error=error),
                    _phase("relationship selection", occurrence, dependencies, skipped=True),
                )
            )
            continue
        lists.append(candidates)
        phase = _phase(
            "candidate retrieval",
            occurrence,
            dependencies,
            result=candidates.list_id,
            error=retrieval_error,
        )
        if retrieval_error is not None:
            phase["outcome"] = "limited"
        phases.append(phase)
        available = {candidate.target_id for candidate in candidates.candidates}
        witnesses += producer_relationship_witnesses(
            upstream,
            products,
            occurrence,
            inventory,
            available,
            cfg.relationship_recipes,
            frame.unit_ref,
            cfg.scope,
            cfg.effective_version,
        )
        witnesses += tuple(
            RelationshipWitness(
                "coincident-component-term:"
                + operation_identity(product["contribution_id"], target),
                occurrence,
                target,
                "denotes",
                frame.unit_ref,
                cfg.scope,
                cfg.effective_version,
                (product["contribution_id"],),
                "producer_group",
                "unassessed",
            )
            for product in products
            if product["occurrence_id"] == occurrence
            for target in own_terms.get(occurrence, ())
            if target in available
        )
        decision = choose(
            candidates=candidates,
            inventory=inventory,
            source_binding=frame.unit_ref,
            scope=cfg.scope,
            effective_version=cfg.effective_version,
            constraints=(SECTION_CONSTRAINT,)
            if cfg.section_sources
            else cfg.relationship_constraints,
            witnesses=witnesses,
            insufficient_reason=section_outcome.replace("_", " ")
            if section_outcome
            else "no source-grounded relationship witness",
        )
        decisions.append(decision)
        phase = _phase(
            "relationship selection", occurrence, (candidates.list_id,), result=decision.decision_id
        )
        projected = relationship_contributions(
            decision, products, inventory, phase["operation_key"]
        )
        result_products.extend(projected)
        phase["emitted_count"] = len(projected)
        phase["computation_dependencies"] = tuple(
            dict.fromkeys(
                dependency
                for proposal in projected
                for dependency in proposal["computation_dependencies"]
            )
        ) or (candidates.list_id,)
        phases.append(phase)
    report = enrichment_report(
        profiles=(profile,) if encoded else (),
        vectors=tuple(vectors.values()),
        inventories=(inventory,),
        candidate_lists=lists,
        relationship_decisions=decisions,
        component_targets=tuple(
            target.model_dump(mode="python") for target in cfg.target_components
        ),
        section_sources=cfg.section_sources,
        section_catalog_sources=cfg.section_catalog_sources,
        section_source_origin_task_id=upstream.get("origin_task_id")
        if cfg.section_sources
        else None,
        section_targets=headings,
        section_resolutions=tuple(sorted(resolutions, key=lambda row: row["occurrence_id"])),
    )
    if neighborhood is not None:
        report["neighborhood"] = neighborhood(report)
    operation = dict(
        operation_key=op,
        question="retained producer occurrence roles and contextual encoder products",
        operation_version=version,
        outcome="succeeded" if encoder_error is None else "limited",
        inspected_count=len(products),
        emitted_count=len(products),
        contextual_enrichment=report,
        computation_dependencies=(
            registry,
            profile.profile_id,
            view.ref.projection_digest,
            *dict.fromkeys(signal.evidence.identity for signal in query_context.values()),
        ),
    )
    if encoder_error is not None:
        operation["reason"] = "configured contextual encoder unavailable for this selection"
    detail: dict[str, Any] = dict(
        input_population="retained-producer-occurrences-1",
        target_standing="retained_heading_private_proposal"
        if cfg.section_sources
        else "retained_component_private_proposal",
        encoder_implementation=encoded.implementation if encoded else None,
        fresh_vector_count=len(vectors),
        encoder_inputs=[asdict(item) for item in encoded.inputs] if encoded else [],
    )
    if query_context:
        detail["query_context"] = {
            occurrence: dict(
                signal.report(),
                outcome="rendered" if occurrence in vectors else "encoder_unavailable",
            )
            for occurrence, signal in query_context.items()
        }
    return UnitResult(
        ref=ref,
        outcome=ObservationOutcome.PRODUCED if result_products else ObservationOutcome.EMPTY,
        contribution_operations=(operation, *phases),
        contributions=tuple(result_products),
        contribution_coordinate_texts=coordinates,
        parse_detail=json.loads(canonical_bytes(detail)),
    )
