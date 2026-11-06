"""Actual retained occurrence retrieval over authenticated definition-component targets."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.db.lifetime import DatabaseOperationCancelled
from corpus_structure.core.method import Digest, Resources, UnitRef, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.semantic.contextual_links import RelationKind, RelationshipConstraint, RelationshipWitness, select_relationships
from corpus_structure.semantic.contextual_registry import ExtractedComponentTarget, component_target_input
from corpus_structure.semantic.contextual_retrieval import freeze_inventory
from corpus_structure.semantic.contextual_storage import enrichment_report
from corpus_structure.semantic.contributions import (
    contribution_identity,
    occurrence_identity,
    operation_identity,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.source_contexts import record_source_pin

from .contextual_embeddings import (
    E5,
    QWEN,
    ContextInput,
    encode_contexts,
    verify_encoder_implementation,
)


def _phase_operation(phase, occurrence, dependencies, *, result_id=None, error=None, skipped=False):
    """Semantic child operation; its report digest references the intrinsic typed product ID."""
    row = dict(
        operation_key=operation_identity("contextual-phase-2", phase, occurrence, dependencies),
        question=(
            "contextual relationship selection for located occurrence"
            if phase == "relationship selection"
            else f"contextual {phase} for located occurrence {occurrence}"
        ),
        operation_version="2",
        inspected_count=1,
        emitted_count=0,
        computation_dependencies=tuple(dependencies),
        outcome="not_run" if skipped else ("failed" if error is not None else "succeeded"),
    )
    if result_id is not None:
        row["report_digest"] = result_id.rsplit(":", 1)[1]
    if error is not None:
        detail = getattr(
            getattr(getattr(error, "orig", None), "diag", None), "message_primary", None
        )
        message = detail or str(error.orig if isinstance(error, DBAPIError) else error)
        row["reason"] = (f"{type(error).__name__}: {message}")[:768]
    if skipped:
        row["reason"] = "candidate retrieval failed; relationship selection was not attempted"
    return row


def _propagate_cancellation(error, check_active):
    if isinstance(error, DatabaseOperationCancelled) or (
        isinstance(error, DBAPIError) and getattr(error.orig, "sqlstate", None) == "57014"
    ):
        raise error
    check_active()


def relationship_contributions(decision, source_product, inventory, operation_key):
    """Project each explicitly selected scoped edge without selecting from alternatives."""
    rows = []
    for edge in decision.selected_edges:
        target = next(t for t in inventory.targets if t.target_id == edge.target_id)
        row = dict(
            contract="RetainedContributionSemantics", kind="proposal",
            semantic_type="contextual.relationship", operation_key=operation_key,
            item_key=source_product["item_key"] + ":relationship:" + edge.edge_id,
            pin=source_product["pin"], anchors=source_product["anchors"],
            occurrence_id=source_product["occurrence_id"],
            members=(source_product["contribution_id"],), disposition="scoped_proposal",
            standing="retained_private", score_state="missing",
            computation_dependencies=(source_product["contribution_id"], decision.candidate_list_id,
                                      decision.decision_id, inventory.source_selection, edge.edge_id),
            value=source_value(dict(target_id=target.target_id, target_source_binding=target.source_binding,
                                    relation=edge.relation, scope=decision.scope,
                                    effective_version=decision.effective_version,
                                    edge_id=edge.edge_id, constraint_id=edge.constraint_id)),
        )
        row["contribution_id"] = contribution_identity(row)
        rows.append(row)
    return tuple(rows)


class ProducerRelationshipRecipe(BaseModel):
    """Domain-authored mapping from named producer roles to a scoped relationship."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    rule: str = Field(min_length=1)
    occurrence_role: str = Field(min_length=1)
    target_role: str = Field(min_length=1)
    relation: RelationKind


def producer_relationship_witnesses(upstream, products, occurrence, inventory, available,
                                    recipes, source_binding, scope, effective_version):
    originals = {p["contribution_id"]: p for p in upstream.get("contributions", ())}
    pairs = tuple((p, originals[p["computation_dependencies"][0]]) for p in products)
    witnesses = []
    for recipe in recipes:
        for product, original in pairs:
            if product["occurrence_id"] != occurrence:
                continue
            component = original.get("component", {})
            roles = component.get("roles", ())
            if component.get("kind") != "located_role" or component.get("rule") != recipe.rule:
                continue
            if not any(r["role"] == recipe.occurrence_role and r["outcome"] == "complete" for r in roles):
                continue
            group = original["item_key"].rsplit("/role/", 1)[0]
            for target_product, target_original in pairs:
                target_component = target_original.get("component", {})
                if target_original["item_key"].rsplit("/role/", 1)[0] != group:
                    continue
                if target_component.get("rule") != recipe.rule or not any(
                    r["role"] == recipe.target_role and r["outcome"] == "complete"
                    for r in target_component.get("roles", ())
                ):
                    continue
                label = " ".join(a["source_piece"] for a in target_product["anchors"])
                for target in inventory.targets:
                    if target.target_id not in available or target.label.casefold() != label.casefold():
                        continue
                    witness_id = "producer-group:" + operation_identity(recipe.model_dump(mode="json"), product["contribution_id"], target_product["contribution_id"], target.target_id)
                    witnesses.append(RelationshipWitness(
                        witness_id, occurrence, target.target_id, recipe.relation,
                        source_binding, scope, effective_version,
                        (product["contribution_id"], target_product["contribution_id"]),
                        "producer_group", "unassessed",
                    ))
    return tuple(witnesses)


class ContextualCandidateConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    profile: Literal["e5", "qwen"] = "e5"
    source_dependencies: Literal["source_view_product"] = "source_view_product"
    source_dependency_method: str = Field(default="extract.m1_candidates", min_length=1)
    semantic_types: tuple[str, ...] = ()
    target_components: tuple[ExtractedComponentTarget, ...] = Field(min_length=1, max_length=256)
    relationship_constraints: tuple[RelationshipConstraint, ...] = Field(min_length=1)
    relationship_recipes: tuple[ProducerRelationshipRecipe, ...] = ()
    source_product_digest: str = Field(pattern="^[0-9a-f]{64}$")
    source_projection_digest: str = Field(pattern="^[0-9a-f]{64}$")
    scope: str = Field(min_length=1)
    effective_version: str | None = None
    unique_target_budget: int = Field(default=10, ge=1, le=100)
    channel_budget: int = Field(default=30, ge=1, le=256)


def retained_occurrences(upstream, nodes, pin, operation_key, semantic_types=()):
    """Authenticate selected producer locations; role proposals remain distinct products.

    Multiple pieces in one native item may share an encoder context without making
    their intervening characters a new asserted source occurrence.
    """
    products, contexts, coordinates = [], {}, {}
    for original in upstream.get("contributions", ()):
        if semantic_types and original["semantic_type"] not in semantic_types:
            continue
        anchors = tuple(original.get("anchors", ()))
        if original.get("kind") not in {"occurrence", "proposal", "group"} or not anchors:
            continue
        for anchor in anchors:
            node = nodes.get(anchor["pointer"])
            if node is None or anchor["pin"] != pin or anchor["space"] != "native":
                raise ValueError("retained occurrence differs from actual native source")
            if node.get("text", "")[anchor["start"]:anchor["end"]] != anchor["source_piece"]:
                raise ValueError("retained occurrence source slice is invalid")
            coordinates[anchor["pointer"]] = dict(pin=pin, space="native", pointer=anchor["pointer"], text=node["text"])
        occurrence = occurrence_identity(anchors)
        if occurrence != original["occurrence_id"]:
            raise ValueError("retained occurrence identity differs from actual source anchors")
        product = dict(contract="RetainedContributionSemantics", kind="occurrence",
                       semantic_type="contextual.located_mention", operation_key=operation_key,
                       item_key=original["contribution_id"], pin=pin, anchors=anchors,
                       occurrence_id=occurrence, disposition="located_proposal",
                       standing="retained_private", score_state="missing",
                       value=source_value(dict(producer_semantic_type=original["semantic_type"],
                                               producer_component=original.get("component"),
                                               producer_value=original.get("value"))),
                       computation_dependencies=(original["contribution_id"], original["operation_key"]))
        product["contribution_id"] = contribution_identity(product)
        products.append(product)
        if len({a["pointer"] for a in anchors}) == 1:
            start, end = min(a["start"] for a in anchors), max(a["end"] for a in anchors)
            text = nodes[anchors[0]["pointer"]]["text"]
            contexts[occurrence] = (text, start, end, text[start:end])
    return tuple(products), contexts, tuple(coordinates.values())


class ContextualCandidates:
    name = "retrieve.contextual"
    version = "3"
    family = MethodFamily.RESOLVE
    unit_type = TaskUnitType.SOURCE_VIEW
    tier = MethodTier.ENCODER
    confidence_source = None
    Config = ContextualCandidateConfig
    resources = Resources(worker="cpu", batch_size=1, max_concurrency=1)

    def select(self, run, cfg):
        selected = tuple(
            UnitRef(TaskUnitType.SOURCE_VIEW, view.id, view.key)
            for view in run.reader.source_views()
            if view.native_product.content_digest == cfg.source_product_digest
            and view.projection_digest == cfg.source_projection_digest
        )
        if len(selected) != 1:
            raise ValueError(
                "contextual source input must select exactly one immutable native view"
            )
        return selected

    def input_digest(self, unit, cfg):
        view = unit.run.reader.source_view(unit.ref.unit_id)
        return Digest(
            canonical_bytes(
                dict(
                    configuration=cfg.model_dump(mode="json"),
                    source=view.ref.native_product.values(),
                    projection=view.ref.projection_digest,
                    input_population="retained-producer-occurrences-1",
                    producer=unit.run.reader.source_result(unit.ref.unit_id, cfg.source_dependency_method),
                )
            )
        )

    def run(self, units, cfg, ctx):
        profile = E5 if cfg.profile == "e5" else QWEN
        verify_encoder_implementation(profile)
        ctx.reader.validate_component_targets(cfg.target_components)
        registry_id, targets = component_target_input(cfg.target_components)
        inventory = freeze_inventory(
            targets,
            source_selection=registry_id,
            scope=cfg.scope,
            effective_version=cfg.effective_version,
        )
        
        results = []
        for unit in units:
            ctx.check_active()
            view = ctx.reader.source_view(unit.ref.unit_id)
            frame = native_source_frame(view, ())
            pin = record_source_pin(frame)
            nodes = {
                node.get("self_ref", node.get("pointer")): node
                for node in json.loads(frame.native_context)["items"]
            }
            operation_key = operation_identity(
                self.name, self.version, cfg.model_dump(mode="json"), pin
            )
            upstream = ctx.reader.source_result(unit.ref.unit_id, cfg.source_dependency_method)
            if upstream is None:
                raise ValueError("selected retained occurrence producer is unavailable")
            source_products, contexts, coordinates = retained_occurrences(
                upstream, nodes, pin, operation_key, cfg.semantic_types
            )
            products = list(source_products)
            inputs = [ContextInput(occurrence, frame.unit_ref, "query", mention, text, start, end)
                      for occurrence, (text, start, end, mention) in contexts.items()]
            if len(inputs) + len(targets) > profile.max_items:
                raise ValueError("contextual combined input population exceeds encoder bound")
            cached = ctx.reader.cached_contextual_vectors(
                profile_id=profile.profile_id, targets=inventory.targets
            )
            for target in inventory.targets:
                text = target.label + "\n" + target.description
                inputs.append(
                    ContextInput(
                        target.target_id,
                        target.source_binding,
                        "document",
                        target.label,
                        text,
                        0,
                        len(target.label),
                        parent=target.parent or "",
                        heading=("Aliases: " + ", ".join(target.aliases)) if target.aliases else "",
                        type_name=target.type_name,
                        representation_digest=target.representation_digest,
                    )
                )
            encoded = encode_contexts(
                inputs,
                profile,
                check_active=ctx.check_active,
                cached_vectors=tuple(item.vector for item in cached),
            )
            cached = tuple(
                item for item in cached if item.vector.vector_id in encoded.reused_vector_ids
            )
            all_vectors = (*encoded.vectors, *(item.vector for item in cached))
            vectors = {v.object_id: v for v in all_vectors}
            target_vectors = tuple(v for v in all_vectors if v.object_id in inventory.target_ids)
            lists, decisions, phases = [], [], []
            for occurrence in sorted({p["occurrence_id"] for p in source_products} - contexts.keys()):
                phase = _phase_operation("candidate retrieval", occurrence, (inventory.inventory_id,))
                phase.update(outcome="not_run", reason="multi-item occurrence has no single owned encoder context")
                phases.append(phase)
                phases.append(_phase_operation("relationship selection", occurrence, (inventory.inventory_id,), skipped=True))
            for occurrence, (text, start, end, mention) in contexts.items():
                product = next(p for p in source_products if p["occurrence_id"] == occurrence)
                ctx.check_active()
                occurrence = product["occurrence_id"]
                dependencies = (
                    vectors[occurrence].vector_id,
                    inventory.inventory_id,
                    profile.profile_id,
                )
                try:
                    candidate_list = ctx.reader.contextual_candidates(
                        occurrence_id=occurrence,
                        query=vectors[occurrence],
                        inventory=inventory,
                        target_vectors=target_vectors,
                        lexical_query=mention,
                        dimension=profile.dimension,
                        budget=cfg.unique_target_budget,
                        channel_budget=cfg.channel_budget,
                    )
                except (ValueError, DBAPIError, TimeoutError, OSError) as error:
                    _propagate_cancellation(error, ctx.check_active)
                    phases.append(
                        _phase_operation(
                            "candidate retrieval", occurrence, dependencies, error=error
                        )
                    )
                    phases.append(
                        _phase_operation(
                            "relationship selection", occurrence, dependencies, skipped=True
                        )
                    )
                    continue
                lists.append(candidate_list)
                phases.append(
                    _phase_operation(
                        "candidate retrieval",
                        occurrence,
                        dependencies,
                        result_id=candidate_list.list_id,
                    )
                )
                try:
                    available = {c.target_id for c in candidate_list.candidates}
                    witnesses = tuple(
                        RelationshipWitness(
                            "component-label:" + source_product["contribution_id"] + ":" + target.target_id,
                            occurrence,
                            target.target_id,
                            "denotes",
                            frame.unit_ref,
                            cfg.scope,
                            cfg.effective_version,
                            (source_product["contribution_id"],),
                            "producer_group",
                            "unassessed",
                        )
                        for source_product in source_products
                        for target in inventory.targets
                        if source_product["occurrence_id"] == occurrence
                        and any("denotes" in c.relation_kinds for c in cfg.relationship_constraints)
                        and target.target_id in available
                        and mention.lower()
                        in {target.label.lower(), *(a.lower() for a in target.aliases)}
                    )
                    witnesses += producer_relationship_witnesses(
                        upstream, source_products, occurrence, inventory, available,
                        cfg.relationship_recipes, frame.unit_ref, cfg.scope, cfg.effective_version,
                    )
                    decision = select_relationships(
                        candidates=candidate_list,
                        inventory=inventory,
                        source_binding=frame.unit_ref,
                        scope=cfg.scope,
                        effective_version=cfg.effective_version,
                        constraints=cfg.relationship_constraints,
                        witnesses=witnesses,
                        insufficient_reason="no exact full-term component label witness",
                    )
                except (ValueError, TimeoutError, OSError) as error:
                    _propagate_cancellation(error, ctx.check_active)
                    phases.append(
                        _phase_operation(
                            "relationship selection",
                            occurrence,
                            (candidate_list.list_id,),
                            error=error,
                        )
                    )
                    continue
                decisions.append(decision)
                phase = _phase_operation(
                    "relationship selection",
                    occurrence,
                    (candidate_list.list_id,),
                    result_id=decision.decision_id,
                )
                proposals = relationship_contributions(decision, product, inventory, phase["operation_key"])
                products.extend(proposals)
                phase["emitted_count"] = len(proposals)
                phase["computation_dependencies"] = tuple(dict.fromkeys(
                    dependency for proposal in proposals for dependency in proposal["computation_dependencies"]
                )) or (candidate_list.list_id,)
                phases.append(phase)
            report = enrichment_report(
                profiles=(profile,),
                vectors=all_vectors,
                inventories=(inventory,),
                candidate_lists=lists,
                relationship_decisions=decisions,
                component_targets=tuple(t.model_dump(mode="python") for t in cfg.target_components),
                vector_reuse=tuple(item.reuse for item in cached),
            )
            operation = dict(
                operation_key=operation_key,
                question="retained producer occurrence roles and contextual encoder products",
                operation_version=self.version,
                outcome="succeeded",
                inspected_count=len(source_products),
                emitted_count=len(source_products),
                contextual_enrichment=report,
                computation_dependencies=(
                    registry_id,
                    profile.profile_id,
                    view.ref.projection_digest,
                ),
            )
            results.append(
                UnitResult(
                    ref=unit.ref,
                    outcome=ObservationOutcome.PRODUCED,
                    contribution_operations=(operation, *phases),
                    contributions=tuple(products),
                    contribution_coordinate_texts=coordinates,
                    parse_detail=json.loads(
                        canonical_bytes(
                            dict(
                                input_population="retained-producer-occurrences-1",
                                target_standing="retained_component_private_proposal",
                                encoder_implementation=encoded.implementation,
                                fresh_vector_count=len(encoded.vectors),
                                reused_vector_count=len(cached),
                                encoder_inputs=[asdict(i) for i in encoded.inputs],
                            )
                        )
                    ),
                )
            )
        return results
