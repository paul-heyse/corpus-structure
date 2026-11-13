"""Actual retained occurrence retrieval over authenticated definition-component targets."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_bindings import BindingResult
from corpus_structure.semantic.data_operation_consumers import BoundConsumerSelection

from corpus_structure.core.db.lifetime import DatabaseOperationCancelled
from corpus_structure.core.method import Digest, Resources, UnitRef, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, TaskUnitType
from corpus_structure.semantic.contextual_links import (
    RelationKind,
    RelationshipConstraint,
    RelationshipWitness,
    select_relationships,
)
from corpus_structure.semantic.contextual_registry import (
    ExtractedComponentTarget,
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
from corpus_structure.semantic.contributions import (
    contribution_identity,
    occurrence_identity,
    operation_identity,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python, source_value
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.retained_contributions import RetainedContributionRef
from corpus_structure.semantic.source_contexts import (
    ContextRefused,
    NativeSourceContext,
    SourceSlice,
    evidence_anchor,
    record_source_pin,
)
from corpus_structure.semantic.structural_products import ExternalSourceRef

from .contextual_embeddings import (
    E5,
    QWEN,
    ContextCoreLimited,
    ContextInput,
    encode_contexts,
    verify_encoder_implementation,
)
from .contextual_query import QueryContextSelection, resolve_query_contexts


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


def relationship_contributions(decision, source_products, inventory, operation_key):
    """Project selected edges through witness-cited products of their own occurrence.

    The deterministic carrier is operational; the decision retains every qualifying witness.
    """
    rows = []
    for edge in decision.selected_edges:
        evidence = {identifier for witness in edge.witnesses for identifier in witness.evidence_ids}
        carriers = sorted(
            (
                product
                for product in source_products
                if product["occurrence_id"] == decision.occurrence_id
                and product["contribution_id"] in evidence
            ),
            key=lambda product: product["contribution_id"],
        )
        if not carriers:
            raise ValueError("selected relationship edge lacks a cited source occurrence product")
        source_product = carriers[0]
        target = next(
            group for group in inventory.semantic_groups if group.target_id == edge.target_id
        )
        row = dict(
            contract="RetainedContributionSemantics",
            kind="proposal",
            semantic_type="contextual.relationship",
            operation_key=operation_key,
            item_key=source_product["item_key"] + ":relationship:" + edge.edge_id,
            pin=source_product["pin"],
            anchors=source_product["anchors"],
            occurrence_id=source_product["occurrence_id"],
            members=(source_product["contribution_id"],),
            disposition="scoped_proposal",
            standing="retained_private",
            score_state="missing",
            computation_dependencies=(
                source_product["contribution_id"],
                decision.candidate_list_id,
                decision.decision_id,
                inventory.source_selection,
                edge.edge_id,
            ),
            value=source_value(
                json.loads(
                    canonical_bytes(
                        dict(
                            target=target.meaning,
                            relation=edge.relation,
                            scope=decision.scope,
                            effective_version=decision.effective_version,
                        )
                    )
                )
            ),
        )
        row["contribution_id"] = contribution_identity(row)
        rows.append(row)
    return tuple(rows)


def retained_definition_witnesses(
    upstream, products, occurrence, inventory, available, source_binding, scope, effective_version
):
    """A retained term role binds its own component without comparing target labels."""
    from corpus_structure.semantic.structural_products import RetainedComponentRef

    originals = {row["contribution_id"]: row for row in upstream.get("contributions", ())}
    found = []
    for product in products:
        if product["occurrence_id"] != occurrence:
            continue
        original = originals[product["computation_dependencies"][0]]
        if original["semantic_type"] != "definition.term":
            continue
        value = source_python(original["value"])
        if value.get("role") != "defined_term":
            continue
        reference = RetainedComponentRef.model_validate(value["component_reference"])
        for target in inventory.targets:
            if target.target_id not in available or target.target_id != reference.component_id:
                continue
            if target.source_binding != "definition-component:" + reference.identity:
                raise ValueError("definition term substitutes a different component origin")
            found.append(
                RelationshipWitness(
                    "retained-definition-term:"
                    + operation_identity(product["contribution_id"], reference.identity),
                    occurrence,
                    target.target_id,
                    "defined-by",
                    source_binding,
                    scope,
                    effective_version,
                    (product["contribution_id"],),
                    "producer_group",
                    "unassessed",
                )
            )
    return tuple(found)


def coincident_component_terms(frame, view, semantic_targets, pin):
    """Index component terms only when they are the same physical occurrence."""
    source_pin = {
        "native_product_key": pin["product_key"],
        "native_content_digest": pin["product_digest"],
        "projection_digest": pin["projection_digest"],
        "recipe_digest": pin["recipe_digest"],
    }
    local = {
        target_id: target["term"]
        for target_id, target in semantic_targets.items()
        if all(target["term"].get("source", {}).get(k) == v for k, v in source_pin.items())
    }
    if not local:
        return {}
    context = NativeSourceContext(
        frame,
        (),
        (SourceSlice(view.ref.id, 0, len(frame.text)),),
        "coincident retained component terms",
        "coincident-component-term-1",
        "exact source projection",
        max_chars=len(frame.text),
        max_pieces=max(1, len(view.pieces)),
    )
    by_occurrence = defaultdict(list)
    for target_id, term in local.items():
        try:
            pieces = context.map_span(
                term["start"], term["end"], literal=term["text"], allow_multiple=True
            )
        except ContextRefused:
            continue
        anchors = tuple(evidence_anchor(context, piece, native=True)[0] for piece in pieces)
        by_occurrence[occurrence_identity(anchors)].append(target_id)
    return by_occurrence


def _primary_named_record(product, nodes, original, marker, primary_layers, role):
    """Authenticate a retained source role; this projection characterizes no language."""
    from corpus_structure.semantic.constructions.navigation import NavigationIndex

    from .witnessed_source_links import navigation_index

    reference = marker.get("primary_node")
    if reference is None or original.get("primary_node") not in (None, reference):
        raise ValueError("named source meaning requires its exact primary characterization")
    if len(product["anchors"]) != 1:
        return None
    (anchor,) = product["anchors"]
    projection = anchor["pin"]["projection_digest"]
    index = (
        primary_layers
        if isinstance(primary_layers, NavigationIndex)
        else navigation_index(
            primary_layers, projection, source_view_id=anchor["pin"]["source_view_id"]
        )
    )
    found = [
        row
        for row in index.select("named_link", anchor["pointer"])
        if row.reference.values() == reference
    ]
    if len(found) != 1:
        raise ValueError("named source meaning lacks its retained primary node")
    (row,) = found
    extent = row.span(role)
    offset = original["start"] - anchor["start"]
    if (
        extent != (original["start"], original["end"])
        or anchor["precision"] != "exact"
        or nodes[anchor["pointer"]]["text"][anchor["start"] : anchor["end"]]
        != anchor["source_piece"]
        or row.text(role) != anchor["source_piece"]
        or (anchor["start"] + offset, anchor["end"] + offset) != extent
        or row.payload.get("designator") != marker.get("designator")
        or row.payload["relation_kind"] != marker["kind"]
        or any(
            e["projection"] != projection or e["source_view_id"] != anchor["pin"]["source_view_id"]
            for e in row.fragments(role)
        )
    ):
        raise ValueError("named source meaning differs from exact retained primary role")
    return row


def explicit_definition_section(
    product, nodes, *, scope=None, effective_version=None, primary_layers=None
):
    if len(product["anchors"]) != 1:
        return None
    value = source_python(product["value"])
    if value.get("producer_semantic_type") != "structural.located_participant":
        return None
    original = source_python(value["producer_value"])
    if original.get("role") == "named_link_definition_subject":
        exact = explicit_definition_subject(
            product,
            nodes,
            scope=scope,
            effective_version=effective_version,
            primary_layers=primary_layers,
        )
        return exact[0] if exact is not None else None
    marker = explicit_section_citation(product, nodes, primary_layers=primary_layers)
    if (
        marker is not None
        and marker["kind"] == "definition_reference"
        and (marker["scope"], marker.get("effective_version")) == (scope, effective_version)
    ):
        return marker["designator"]
    return None


def explicit_definition_subject(product, nodes, *, scope, effective_version, primary_layers=None):
    if len(product["anchors"]) != 1:
        return None
    value = source_python(product["value"])
    if value.get("producer_semantic_type") != "structural.located_participant":
        return None
    original = source_python(value["producer_value"])
    if original.get("role") != "named_link_definition_subject":
        return None
    marker = original["named_cue"]
    if (
        marker["kind"] != "definition_reference"
        or marker["resolution"] != "target_selection_required"
        or (marker["scope"], marker.get("effective_version")) != (scope, effective_version)
    ):
        return None
    row = _primary_named_record(
        product, nodes, original, marker, primary_layers, "definition_subject"
    )
    if row is None:
        return None
    kind = row.payload["definition_subject_kind"]
    if original.get("definition_subject_kind") != kind:
        raise ValueError("definition subject kind differs from retained primary characterization")
    return marker["designator"], row.text("definition_subject"), kind


def section_definition_subject_witnesses(
    carriers,
    nodes,
    targets,
    *,
    source_binding,
    scope,
    effective_version,
    primary_layers=None,
    aliases=None,
):
    witnesses = []
    for product in carriers:
        binding = explicit_definition_subject(
            product,
            nodes,
            scope=scope,
            effective_version=effective_version,
            primary_layers=primary_layers,
        )
        if binding is None:
            continue
        code, subject, kind = binding
        matched = [
            ref
            for ref, term in targets
            if term == subject
            or (
                kind == "term" and aliases and aliases.get(ref.component_id, ()).count(subject) == 1
            )
        ]
        if len(matched) != 1:
            continue
        (reference,) = matched
        witnesses.append(
            RelationshipWitness(
                "section-term-definition:"
                + operation_identity(product["contribution_id"], reference.identity, code),
                product["occurrence_id"],
                reference.component_id,
                "defined-by",
                source_binding,
                scope,
                effective_version,
                (product["contribution_id"],),
                "explicit_source_cue",
                "unassessed",
            )
        )
    return tuple(witnesses)


def explicit_section_citation(product, nodes, *, primary_layers=None):
    value = source_python(product["value"])
    if value.get("producer_semantic_type") != "structural.located_participant":
        return None
    original = source_python(value["producer_value"])
    marker = original.get("named_cue")
    if (
        original.get("role") != "named_link_subject"
        or not isinstance(marker, dict)
        or marker.get("kind") not in {"section_citation", "definition_reference"}
        or marker.get("resolution") != "target_selection_required"
        or len(product["anchors"]) != 1
    ):
        return None
    row = _primary_named_record(product, nodes, original, marker, primary_layers, "subject")
    return marker if row is not None else None


SECTION_CONSTRAINT = RelationshipConstraint(
    "section-citation", ("cites-section",), "citation", "heading", "one"
)


def outside_section_designators(selected, catalog) -> frozenset[str]:
    """Report positive catalog evidence for physical headings outside selected views."""
    selected_ids = {target.target_id for target in selected}
    return frozenset(
        target.designator for target in catalog if target.target_id not in selected_ids
    )


def section_citation_outcome(
    marker, ids, *, scope, effective_version, complete, budget, outside=()
):
    """The report distinguishes inadequate coverage from a complete empty inspection."""
    if (marker["scope"], marker.get("effective_version")) != (scope, effective_version):
        return "insufficient_evidence"
    if not complete:
        return "unavailable_representation"
    if len(ids) > budget:
        return "witness_budget_exceeded"
    if len(ids) > 1:
        return "ambiguous"
    if ids:
        return "selected"
    if marker["designator"] in outside:
        return "outside_inventory"
    return "no_compatible_candidate"


def section_citation_witnesses(
    carriers, heading_ids, *, source_binding, scope, effective_version, complete, budget, outside=()
):
    """Use all authenticated carriers in scope, withholding edges when coverage is limited."""
    matching = tuple(
        (product, marker)
        for product, marker in carriers
        if (marker["scope"], marker.get("effective_version")) == (scope, effective_version)
    )
    source, marker = (matching or carriers)[0]
    occurrence = source["occurrence_id"]
    ids = tuple(heading_ids.get(marker["designator"], ())) if matching else ()
    outcome = section_citation_outcome(
        marker,
        ids,
        scope=scope,
        effective_version=effective_version,
        complete=complete,
        budget=budget,
        outside=outside,
    )
    resolution = dict(
        occurrence_id=occurrence,
        designator=marker["designator"],
        outcome=outcome,
        eligible_target_ids=ids,
    )
    witnesses = tuple(
        RelationshipWitness(
            "section-citation:"
            + operation_identity(product["contribution_id"], target_id, marker["designator"]),
            occurrence,
            target_id,
            "cites-section",
            source_binding,
            scope,
            effective_version,
            (product["contribution_id"],),
            "explicit_source_cue",
            "unassessed" if outcome in {"selected", "ambiguous"} else "ambiguous",
        )
        for product, _ in matching
        for target_id in ids[:budget]
    )
    return resolution, witnesses


class ProducerRelationshipRecipe(BaseModel):
    """Domain-authored mapping from named producer roles to a scoped relationship."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    rule: str = Field(min_length=1)
    occurrence_role: str = Field(min_length=1)
    target_role: str = Field(min_length=1)
    relation: RelationKind


def producer_relationship_witnesses(
    upstream,
    products,
    occurrence,
    inventory,
    available,
    recipes,
    source_binding,
    scope,
    effective_version,
):
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
            if not any(
                r["role"] == recipe.occurrence_role and r["outcome"] == "complete" for r in roles
            ):
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
                    if (
                        target.target_id not in available
                        or target.label.casefold() != label.casefold()
                    ):
                        continue
                    witness_id = "producer-group:" + operation_identity(
                        recipe.model_dump(mode="json"),
                        product["contribution_id"],
                        target_product["contribution_id"],
                        target.target_id,
                    )
                    witnesses.append(
                        RelationshipWitness(
                            witness_id,
                            occurrence,
                            target.target_id,
                            recipe.relation,
                            source_binding,
                            scope,
                            effective_version,
                            (product["contribution_id"], target_product["contribution_id"]),
                            "producer_group",
                            "unassessed",
                        )
                    )
    return tuple(witnesses)


class ContextualCandidateConfig(BaseModel):
    characterization_layers: tuple[dict, ...] = ()
    model_config = ConfigDict(frozen=True, extra="forbid")
    profile: Literal["e5", "qwen"] = "e5"
    source_dependencies: Literal["source_view_product"] = "source_view_product"
    source_dependency_method: str = Field(default="extract.m1_candidates", min_length=1)
    semantic_types: tuple[str, ...] = ()
    target_components: tuple[ExtractedComponentTarget, ...] = Field(default=(), max_length=256)
    section_sources: tuple[ExternalSourceRef, ...] = Field(
        default=(), max_length=256, exclude_if=lambda value: not value
    )
    section_catalog_sources: tuple[ExternalSourceRef, ...] = Field(
        default=(),
        max_length=256,
        exclude_if=lambda value: not value,
    )
    definition_alias_refs: tuple[RetainedContributionRef, ...] = Field(
        default=(), max_length=256, exclude_if=lambda value: not value
    )
    relationship_constraints: tuple[RelationshipConstraint, ...] = ()
    relationship_recipes: tuple[ProducerRelationshipRecipe, ...] = ()
    source_product_digest: str = Field(pattern="^[0-9a-f]{64}$")
    source_projection_digest: str = Field(pattern="^[0-9a-f]{64}$")
    scope: str = Field(min_length=1)
    effective_version: str | None = None
    unique_target_budget: int = Field(default=10, ge=1, le=100)
    channel_budget: int = Field(default=30, ge=1, le=256)

    @model_validator(mode="after")
    def exclusive_target_scope(self):
        if bool(self.target_components) == bool(self.section_sources):
            raise ValueError("choose exactly one component or section target inventory")
        if self.definition_alias_refs and (
            len({ref.contribution_id for ref in self.definition_alias_refs})
            != len(self.definition_alias_refs)
            or self.section_sources
            or not any("defined-by" in c.relation_kinds for c in self.relationship_constraints)
        ):
            raise ValueError(
                "definition aliases require distinct references and a definition inventory"
            )
        if self.unique_target_budget > self.channel_budget:
            raise ValueError("candidate target budget exceeds the channel budget")
        if self.section_sources:
            sources = (*self.section_sources, *self.section_catalog_sources)
            if (
                len(sources) > 256
                or len({ref.source_view_id for ref in sources}) != len(sources)
                or self.source_dependency_method != "structure.scoped_relations"
                or self.relationship_recipes
                or self.relationship_constraints not in ((), (SECTION_CONSTRAINT,))
            ):
                raise ValueError(
                    "section inventory requires distinct source views "
                    "and the scoped citation recipe"
                )
        elif (
            self.section_catalog_sources
            or not self.relationship_constraints
            or any(
                "cites-section" in constraint.relation_kinds
                for constraint in self.relationship_constraints
            )
        ):
            raise ValueError("component inventory requires non-heading relationship constraints")
        return self


def retained_occurrences(
    upstream,
    nodes,
    pin,
    operation_key,
    semantic_types=(),
    *,
    canonical_producer=False,
    required_occurrence_ids: tuple[str, ...] = (),
):
    """Authenticate selected producer locations; role proposals remain distinct products.

    Multiple pieces in one native item may share an encoder context without making
    their intervening characters a new asserted source occurrence.
    """
    products, contexts, coordinates = [], {}, {}
    required = set(required_occurrence_ids)
    for original in upstream.get("contributions", ()):
        if semantic_types and original["semantic_type"] not in semantic_types:
            continue
        if required and original.get("occurrence_id") not in required:
            continue
        anchors = tuple(original.get("anchors", ()))
        if original.get("kind") not in {"occurrence", "proposal", "group"} or not anchors:
            continue
        has_exact_context = True
        for anchor in anchors:
            node = nodes.get(anchor["pointer"])
            if node is None or anchor["pin"] != pin or anchor["space"] != "native":
                raise ValueError("retained occurrence differs from actual native source")
            start, end = anchor.get("start"), anchor.get("end")
            if anchor["precision"] != "exact":
                has_exact_context = False
            elif (
                type(start) is not int
                or type(end) is not int
                or not 0 <= start < end <= len(node.get("text", ""))
                or node["text"][start:end] != anchor["source_piece"]
            ):
                raise ValueError("retained occurrence source slice is invalid")
            coordinates[anchor["pointer"]] = dict(
                pin=pin, space="native", pointer=anchor["pointer"], text=node.get("text", "")
            )
        occurrence = occurrence_identity(anchors)
        if occurrence != original["occurrence_id"]:
            raise ValueError("retained occurrence identity differs from actual source anchors")
        component, value = original.get("component"), original.get("value")
        if canonical_producer:
            # SourceValue records object key order. Heading identities must survive
            # both PostgreSQL JSONB and canonical detached JSON representations.
            component = json.loads(canonical_bytes(component))
            value = json.loads(canonical_bytes(value))
        product = dict(
            contract="RetainedContributionSemantics",
            kind="occurrence",
            semantic_type="contextual.located_mention",
            operation_key=operation_key,
            item_key=original["contribution_id"],
            pin=pin,
            anchors=anchors,
            occurrence_id=occurrence,
            disposition="located_proposal",
            standing="retained_private",
            score_state="missing",
            value=source_value(
                dict(
                    producer_semantic_type=original["semantic_type"],
                    producer_component=component,
                    producer_value=value,
                )
            ),
            computation_dependencies=(original["contribution_id"], original["operation_key"]),
        )
        product["contribution_id"] = contribution_identity(product)
        products.append(product)
        if has_exact_context and len({a["pointer"] for a in anchors}) == 1:
            start, end = min(a["start"] for a in anchors), max(a["end"] for a in anchors)
            text = nodes[anchors[0]["pointer"]]["text"]
            contexts[occurrence] = (text, start, end, text[start:end])
    if missing := required - contexts.keys():
        raise ValueError(
            "selected producer lacks an exact native query carrier for "
            + ", ".join(sorted(missing))
        )
    return tuple(products), contexts, tuple(coordinates.values())


class ContextualCandidates:
    name = "retrieve.contextual"
    version = "7"
    family = MethodFamily.RESOLVE
    unit_type = TaskUnitType.SOURCE_VIEW
    tier = MethodTier.ENCODER
    confidence_source = None
    Config = ContextualCandidateConfig
    resources = Resources(worker="cpu", batch_size=1, max_concurrency=1)

    __selection_operation__ = {'id': 'retrieve.contextual/selection',
 'profile': 'selection',
 'subject': 'original-source-view',
 'context': ['project', 'original-source', 'frozen-selection'],
 'roles': [{'name': 'view',
            'kind': 'https://corpus-structure.dev/semantic/data-operation-consumers/DdoSourceViewBinding',
            'direction': 'input',
            'minimum': 1,
            'maximum': 1,
            'collection': 'scalar',
            'presence': 'required',
            'support': {'provenance': 'exact',
                        'source': 'same-original',
                        'coverage': 'qualified-selected-population',
                        'identity_requirements': ['episode']}},
           {'name': 'occurrences',
            'kind': 'https://corpus-structure.dev/semantic/data-operation-consumers/DdoOccurrenceBinding',
            'direction': 'input',
            'minimum': 0,
            'maximum': None,
            'collection': 'set',
            'presence': 'optional',
            'support': {'provenance': 'exact',
                        'source': 'same-original',
                        'coverage': 'qualified-selected-population',
                        'identity_requirements': ['episode']},
            'subject_field': 'view_subject'}],
 'applicability': ['admitted-selected-populations'],
 'invariants': ['original-subject-and-source-preserved'],
 'coverage': 'qualified-selected-population',
 'outcomes': ['selected', 'unavailable', 'invalid'],
 'precision': 'exact',
 'dependencies': [],
 'effects': [],
 'capabilities': {'forms': ['scalar'],
                  'preparation': 'none',
                  'cancellation': 'call-boundary',
                  'ownership': 'immutable-selection'},
 'behavior': 'retained-binding-selection-v1',
 'parameters': {'source_product': {'value_type': 'string'},
                'source_projection': {'value_type': 'string'},
                'semantic_types': {'value_type': 'string', 'many': True, 'required': False},
                'required_occurrence_ids': {'value_type': 'string',
                                            'many': True,
                                            'required': False}},
 'binding': {'operator': 'all',
             'children': [{'operator': 'equal',
                           'operands': [{'kind': 'field',
                                         'value_type': 'DdoBindingText',
                                         'field': {'role': 'view',
                                                   'projection': 'https://corpus-structure.dev/semantic/data-operation-consumers/DdoSourceViewBinding',
                                                   'field': 'base_product'}},
                                        {'kind': 'parameter',
                                         'name': 'source_product',
                                         'value_type': 'DdoBindingText'}]},
                          {'operator': 'equal',
                           'operands': [{'kind': 'field',
                                         'value_type': 'DdoBindingText',
                                         'field': {'role': 'view',
                                                   'projection': 'https://corpus-structure.dev/semantic/data-operation-consumers/DdoSourceViewBinding',
                                                   'field': 'projection_digest'}},
                                        {'kind': 'parameter',
                                         'name': 'source_projection',
                                         'value_type': 'DdoBindingText'}]},
                          {'operator': 'forall',
                           'roles': ['occurrences'],
                           'population': 'selected-retained-occurrences',
                           'children': [{'operator': 'literal',
                                         'fields': [{'role': 'occurrences',
                                                     'projection': 'https://corpus-structure.dev/semantic/data-operation-consumers/DdoOccurrenceBinding',
                                                     'field': 'anchors_valid'}],
                                         'value': True},
                                        {'operator': 'optional',
                                         'children': [{'operator': 'membership',
                                                       'operands': [{'kind': 'field',
                                                                     'value_type': 'DdoBindingText',
                                                                     'field': {'role': 'occurrences',
                                                                               'projection': 'https://corpus-structure.dev/semantic/data-operation-consumers/DdoOccurrenceBinding',
                                                                               'field': 'semantic_type'}},
                                                                    {'kind': 'parameter',
                                                                     'name': 'semantic_types',
                                                                     'value_type': 'DdoBindingText'}]}]},
                                        {'operator': 'optional',
                                         'children': [{'operator': 'membership',
                                                       'operands': [{'kind': 'field',
                                                                     'value_type': 'DdoBindingText',
                                                                     'field': {'role': 'occurrences',
                                                                               'projection': 'https://corpus-structure.dev/semantic/data-operation-consumers/DdoOccurrenceBinding',
                                                                               'field': 'occurrence_id'}},
                                                                    {'kind': 'parameter',
                                                                     'name': 'required_occurrence_ids',
                                                                     'value_type': 'DdoBindingText'}]},
                                                      {'operator': 'literal',
                                                       'fields': [{'role': 'occurrences',
                                                                   'projection': 'https://corpus-structure.dev/semantic/data-operation-consumers/DdoOccurrenceBinding',
                                                                   'field': 'exact_context'}],
                                                       'value': True}]}]},
                          {'operator': 'optional',
                           'children': [{'operator': 'covers',
                                         'operands': [{'kind': 'field',
                                                       'value_type': 'DdoBindingText',
                                                       'field': {'role': 'occurrences',
                                                                 'projection': 'https://corpus-structure.dev/semantic/data-operation-consumers/DdoOccurrenceBinding',
                                                                 'field': 'occurrence_id'}},
                                                      {'kind': 'parameter',
                                                       'name': 'required_occurrence_ids',
                                                       'value_type': 'DdoBindingText'}]}]}]}}

    def select_bound(self, binding: BindingResult) -> BoundConsumerSelection:
        """Consume the target operation's retained relational selection unchanged."""
        return BoundConsumerSelection.from_binding(binding, operation=self.__selection_operation__["id"])

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
                    producer=self._producer_input(unit.run.reader, unit.ref.unit_id, cfg),
                )
            )
        )

    @staticmethod
    def _producer_input(reader, source_view_id, cfg):
        exact = getattr(cfg, "required_occurrence_ids", ())
        if exact:
            return reader.source_result(
                source_view_id,
                cfg.source_dependency_method,
                occurrence_ids=exact,
                semantic_types=cfg.semantic_types,
            )
        return reader.source_result(source_view_id, cfg.source_dependency_method)

    def run(self, units, cfg, ctx):
        profile = E5 if cfg.profile == "e5" else QWEN
        constraints = (SECTION_CONSTRAINT,) if cfg.section_sources else cfg.relationship_constraints
        results = []
        for unit in units:
            ctx.check_active()
            view = ctx.reader.source_view(unit.ref.unit_id)
            frame = native_source_frame(view, ())
            pin = record_source_pin(frame)
            heading_targets = ()
            section_complete = True
            outside_designators: frozenset[str] = frozenset()
            if cfg.section_sources:
                if view.ref.id not in {source.source_view_id for source in cfg.section_sources}:
                    raise ValueError("section inventory must include the original cue source view")
                headings = ctx.reader.contextual_section_headings(
                    cfg.section_sources, view.ref.id, cfg.scope, cfg.effective_version
                )
                section_complete = headings["complete"]
                heading_targets = tuple(
                    SectionHeadingTarget.model_validate(row) for row in headings["targets"]
                )
                if cfg.section_catalog_sources:
                    catalog = ctx.reader.contextual_section_headings(
                        (*cfg.section_sources, *cfg.section_catalog_sources),
                        view.ref.id,
                        cfg.scope,
                        cfg.effective_version,
                    )
                    if catalog["complete"]:
                        outside_designators = outside_section_designators(
                            heading_targets,
                            tuple(
                                SectionHeadingTarget.model_validate(row)
                                for row in catalog["targets"]
                            ),
                        )
                registry_id, targets, semantic_targets = section_target_input(
                    cfg.section_sources, heading_targets
                )
            else:
                semantic_targets = ctx.reader.component_semantic_targets(cfg.target_components)
                registry_id, targets = component_target_input(cfg.target_components)
            inventory = freeze_inventory(
                targets,
                source_selection=registry_id,
                scope=cfg.scope,
                effective_version=cfg.effective_version,
                reliable_type="section-heading" if cfg.section_sources else None,
                semantic_targets=semantic_targets,
            )
            nodes = {
                node.get("self_ref", node.get("pointer")): node
                for node in json.loads(frame.native_context)["items"]
            }
            # Native table-cell evidence names a physical field within its parent item.
            # Retain that exact field coordinate rather than treating the parent text
            # or the selected projection as the asserted occurrence.
            for pointer, node in tuple(nodes.items()):
                for index, cell in enumerate(node.get("data", {}).get("table_cells", ())):
                    nodes[f"{pointer}/data/table_cells/{index}"] = cell
            operation_key = operation_identity(
                self.name, self.version, cfg.model_dump(mode="json"), pin
            )
            upstream = self._producer_input(ctx.reader, unit.ref.unit_id, cfg)
            if upstream is None:
                raise ValueError("selected retained occurrence producer is unavailable")
            source_products, contexts, coordinates = retained_occurrences(
                upstream,
                nodes,
                pin,
                operation_key,
                cfg.semantic_types,
                canonical_producer=bool(cfg.section_sources),
                required_occurrence_ids=getattr(cfg, "required_occurrence_ids", ()),
            )
            from corpus_structure.semantic.product_reference import ProductReference

            from .witnessed_source_links import navigation_index

            primary = (
                ctx.reader.characterization_layers(
                    tuple(ProductReference(**value) for value in cfg.characterization_layers)
                )
                if cfg.characterization_layers
                else {}
            )
            primary_navigation = navigation_index(
                primary, frame.projection_digest, source_view_id=view.ref.id
            )
            heading_mentions = defaultdict(list)
            heading_ids = defaultdict(list)
            section_resolutions = []
            if cfg.section_sources:
                for product in source_products:
                    marker = explicit_section_citation(
                        product, nodes, primary_layers=primary_navigation
                    )
                    if marker is not None:
                        heading_mentions[product["occurrence_id"]].append((product, marker))
                source_products = tuple(
                    product for carriers in heading_mentions.values() for product, _ in carriers
                )
                contexts = {
                    key: value for key, value in contexts.items() if key in heading_mentions
                }
                if contexts.keys() != heading_mentions.keys():
                    raise ValueError("retained section cue lacks a single exact native context")
                eligible_headings = set(inventory.target_ids)
                for target in sorted(heading_targets, key=lambda target: target.target_id):
                    if target.target_id in eligible_headings:
                        heading_ids[target.designator].append(target.target_id)
            own_terms = (
                coincident_component_terms(frame, view, semantic_targets, pin)
                if any("denotes" in c.relation_kinds for c in constraints)
                else {}
            )
            section_mentions = {}
            section_targets = defaultdict(list)
            section_aliases = {}
            if cfg.definition_alias_refs and self.version not in {"10", "11", "12"}:
                raise ValueError("definition alias bindings require contextual operation 10")
            if any("defined-by" in c.relation_kinds for c in constraints):
                for product in source_products:
                    section = explicit_definition_section(
                        product,
                        nodes,
                        scope=cfg.scope,
                        effective_version=cfg.effective_version,
                        primary_layers=primary_navigation,
                    )
                    if section is not None:
                        section_mentions.setdefault(product["occurrence_id"], (section, []))[
                            1
                        ].append(product)
                if section_mentions:
                    selected_codes = {code for code, _ in section_mentions.values()}
                    for target in cfg.target_components:
                        reference = target.authenticated_reference()
                        if reference.component_id not in inventory.target_ids:
                            continue
                        code = ctx.reader.retained_component_section(
                            reference, pin["product_digest"]
                        )
                        if code in selected_codes:
                            section_targets[code].append(reference)
                            if cfg.definition_alias_refs:
                                section_aliases[reference.component_id] = tuple(
                                    ctx.reader.retained_component_alias(reference, alias_ref)
                                    for alias_ref in cfg.definition_alias_refs
                                )
            products = list(source_products)
            query_context = {}
            selected_context = getattr(cfg, "query_context", None)
            if selected_context is not None:
                if self.version != "12":
                    raise ValueError("located query context requires contextual operation 12")
                if any(b.occurrence_id not in contexts for b in selected_context.bindings):
                    raise ValueError("query context has no single exact native encoder input")
                query_context = resolve_query_contexts(
                    selected_context, primary, source_products, frame
                )
            inputs = []
            for occurrence, (text, start, end, mention) in contexts.items():
                signal = query_context.get(occurrence)
                inputs.append(
                    ContextInput(
                        occurrence,
                        frame.unit_ref,
                        "query",
                        mention,
                        text,
                        start,
                        end,
                        representation_digest=signal.representation_digest if signal else "",
                        query_context=signal.rendered if signal and signal.signals else None,
                    )
                )
            encoder_error = None
            try:
                verify_encoder_implementation(profile)
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
                            heading=("Aliases: " + ", ".join(target.aliases))
                            if target.aliases
                            else "",
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
            except (ValueError, DBAPIError, RuntimeError, TimeoutError, OSError) as error:
                _propagate_cancellation(error, ctx.check_active)
                encoder_error = error
                encoded, cached, all_vectors = None, (), ()
            vectors = {v.object_id: v for v in all_vectors}
            limited_queries = frozenset(encoded.limited_query_ids) if encoded else frozenset()
            target_vectors = tuple(v for v in all_vectors if v.object_id in inventory.target_ids)
            lists, decisions, phases = [], [], []
            for occurrence in sorted(
                {p["occurrence_id"] for p in source_products} - contexts.keys()
            ):
                phase = _phase_operation(
                    "candidate retrieval", occurrence, (inventory.inventory_id,)
                )
                phase.update(
                    outcome="not_run",
                    reason="occurrence has no single exact owned encoder context",
                )
                phases.append(phase)
                phases.append(
                    _phase_operation(
                        "relationship selection",
                        occurrence,
                        (inventory.inventory_id,),
                        skipped=True,
                    )
                )
            for occurrence, (_text, _start, _end, mention) in contexts.items():
                ctx.check_active()
                query = vectors.get(occurrence)
                dependencies = (
                    (query.vector_id, inventory.inventory_id, profile.profile_id)
                    if query is not None
                    else (inventory.inventory_id,)
                )
                section_outcome = None
                try:
                    exact_witnesses = ()
                    section_nominations = {}
                    if cfg.section_sources:
                        resolution, exact_witnesses = section_citation_witnesses(
                            heading_mentions[occurrence],
                            heading_ids,
                            source_binding=frame.unit_ref,
                            scope=cfg.scope,
                            effective_version=cfg.effective_version,
                            complete=section_complete,
                            budget=cfg.unique_target_budget,
                            outside=outside_designators,
                        )
                        section_outcome = resolution["outcome"]
                        section_resolutions.append(resolution)
                    if any("defined-by" in c.relation_kinds for c in constraints):
                        exact_witnesses += retained_definition_witnesses(
                            upstream,
                            source_products,
                            occurrence,
                            inventory,
                            set(inventory.target_ids),
                            frame.unit_ref,
                            cfg.scope,
                            cfg.effective_version,
                        )
                    if occurrence in section_mentions:
                        code, carriers = section_mentions[occurrence]
                        if self.version in {"9", "10", "11", "12"}:
                            # A section locates a population. Its designation does
                            # not identify the definition of an unrelated concept.
                            section_nominations = {
                                reference.component_id: {p["contribution_id"] for p in carriers}
                                for reference in section_targets[code]
                            }
                            exact_witnesses += section_definition_subject_witnesses(
                                carriers,
                                nodes,
                                tuple(
                                    (
                                        reference,
                                        semantic_targets[reference.component_id]["term"]["text"],
                                    )
                                    for reference in section_targets[code]
                                ),
                                source_binding=frame.unit_ref,
                                scope=cfg.scope,
                                effective_version=cfg.effective_version,
                                primary_layers=primary_navigation,
                                aliases=section_aliases
                                if upstream.get("operation_version") == "17"
                                else None,
                            )
                        else:
                            exact_witnesses += tuple(
                                RelationshipWitness(
                                    "section-definition:"
                                    + operation_identity(
                                        product["contribution_id"], reference.identity, code
                                    ),
                                    occurrence,
                                    reference.component_id,
                                    "defined-by",
                                    frame.unit_ref,
                                    cfg.scope,
                                    cfg.effective_version,
                                    (product["contribution_id"],),
                                    "explicit_source_cue",
                                    "unassessed",
                                )
                                for reference in section_targets[code]
                                for product in carriers
                            )
                    retrieval_error = (
                        ContextCoreLimited(
                            "required located query context exceeds encoder token bound"
                        )
                        if occurrence in limited_queries
                        else encoder_error
                    )
                    channels = {}
                    if query is not None:
                        try:
                            exploratory = ctx.reader.contextual_candidates(
                                occurrence_id=occurrence,
                                query=query,
                                inventory=inventory,
                                target_vectors=target_vectors,
                                lexical_query=mention,
                                dimension=profile.dimension,
                                budget=cfg.unique_target_budget,
                                channel_budget=cfg.channel_budget,
                            )
                            channels = {c.channel: c.hits for c in exploratory.channel_results}
                        except (ValueError, DBAPIError, TimeoutError, OSError) as error:
                            _propagate_cancellation(error, ctx.check_active)
                            retrieval_error = error
                    if retrieval_error is not None and not (
                        cfg.section_sources or exact_witnesses or section_nominations
                    ):
                        raise retrieval_error
                    if cfg.section_sources or exact_witnesses or section_nominations:
                        evidence = defaultdict(set)
                        evidence.update(section_nominations)
                        for witness in exact_witnesses:
                            evidence[witness.target_id].update(witness.evidence_ids)
                        channels["witness"] = tuple(
                            ChannelHit(target_id, 1.0, tuple(sorted(evidence[target_id])))
                            for target_id in sorted(evidence)
                        )
                    candidate_list = fuse_candidates(
                        occurrence_id=occurrence,
                        query=query if retrieval_error is None else None,
                        inventory=inventory,
                        channels=channels,
                        budget=cfg.unique_target_budget,
                        channel_budget=cfg.channel_budget,
                        lexical_query=mention,
                    )
                except (ValueError, DBAPIError, RuntimeError, TimeoutError, OSError) as error:
                    _propagate_cancellation(error, ctx.check_active)
                    phase = _phase_operation(
                        "candidate retrieval", occurrence, dependencies, error=error
                    )
                    if isinstance(error, ContextCoreLimited):
                        phase["outcome"] = "limited"
                    phases.append(phase)
                    phases.append(
                        _phase_operation(
                            "relationship selection", occurrence, dependencies, skipped=True
                        )
                    )
                    continue
                lists.append(candidate_list)
                phase = _phase_operation(
                    "candidate retrieval",
                    occurrence,
                    dependencies,
                    result_id=candidate_list.list_id,
                    error=retrieval_error,
                )
                if retrieval_error is not None:
                    phase["outcome"] = "limited"
                    phase["reason"] = (
                        "Exploratory retrieval unavailable. " + str(phase["reason"])[:730]
                    )
                phases.append(phase)
                try:
                    available = {c.target_id for c in candidate_list.candidates}
                    witnesses = exact_witnesses + producer_relationship_witnesses(
                        upstream,
                        source_products,
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
                            + operation_identity(source_product["contribution_id"], target_id),
                            occurrence,
                            target_id,
                            "denotes",
                            frame.unit_ref,
                            cfg.scope,
                            cfg.effective_version,
                            (source_product["contribution_id"],),
                            "producer_group",
                            "unassessed",
                        )
                        for source_product in source_products
                        if source_product["occurrence_id"] == occurrence
                        for target_id in own_terms.get(occurrence, ())
                        if target_id in available
                    )
                    decision = select_relationships(
                        candidates=candidate_list,
                        inventory=inventory,
                        source_binding=frame.unit_ref,
                        scope=cfg.scope,
                        effective_version=cfg.effective_version,
                        constraints=constraints,
                        witnesses=witnesses,
                        insufficient_reason=(
                            section_outcome.replace("_", " ")
                            if section_outcome is not None
                            else "explicit definition section is outside the represented "
                            "target inventory"
                            if occurrence in section_mentions
                            and not section_targets[section_mentions[occurrence][0]]
                            else "no source-grounded relationship witness"
                        ),
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
                proposals = relationship_contributions(
                    decision, source_products, inventory, phase["operation_key"]
                )
                products.extend(proposals)
                phase["emitted_count"] = len(proposals)
                phase["computation_dependencies"] = tuple(
                    dict.fromkeys(
                        dependency
                        for proposal in proposals
                        for dependency in proposal["computation_dependencies"]
                    )
                ) or (candidate_list.list_id,)
                phases.append(phase)
            report = enrichment_report(
                profiles=(profile,) if encoded is not None else (),
                vectors=all_vectors,
                inventories=(inventory,),
                candidate_lists=lists,
                relationship_decisions=decisions,
                component_targets=tuple(t.model_dump(mode="python") for t in cfg.target_components),
                section_sources=cfg.section_sources,
                section_catalog_sources=cfg.section_catalog_sources,
                section_source_origin_task_id=upstream.get("origin_task_id")
                if cfg.section_sources
                else None,
                section_targets=heading_targets,
                section_resolutions=tuple(
                    sorted(section_resolutions, key=lambda row: row["occurrence_id"])
                ),
                vector_reuse=tuple(item.reuse for item in cached),
            )
            if self.version in {"9", "10", "11", "12"}:
                neighborhood = ctx.reader.contextual_mutual_neighbors(report)
                report["neighborhood"] = dict(
                    neighborhood,
                    directed_ranks=tuple(neighborhood["directed_ranks"]),
                    edges=tuple(neighborhood["edges"]),
                )
            operation = dict(
                operation_key=operation_key,
                question="retained producer occurrence roles and contextual encoder products",
                operation_version=self.version,
                outcome="succeeded" if encoder_error is None and not limited_queries else "limited",
                inspected_count=len(source_products),
                emitted_count=len(source_products),
                contextual_enrichment=report,
                computation_dependencies=(
                    registry_id,
                    profile.profile_id,
                    view.ref.projection_digest,
                    *dict.fromkeys(signal.evidence.identity for signal in query_context.values()),
                ),
            )
            if encoder_error is not None:
                operation["reason"] = "configured contextual encoder unavailable for this selection"
            elif limited_queries:
                operation["reason"] = (
                    "some required located query contexts exceeded the token bound"
                )
            query_detail = (
                {
                    "query_context": {
                        occurrence: dict(
                            signal.report(),
                            outcome=(
                                "limited"
                                if occurrence in limited_queries
                                else "unavailable"
                                if not signal.signals
                                else "rendered"
                                if occurrence in vectors
                                else "encoder_unavailable"
                            ),
                        )
                        for occurrence, signal in query_context.items()
                    }
                }
                if query_context
                else {}
            )
            results.append(
                UnitResult(
                    ref=unit.ref,
                    outcome=ObservationOutcome.PRODUCED if products else ObservationOutcome.EMPTY,
                    contribution_operations=(operation, *phases),
                    contributions=tuple(products),
                    contribution_coordinate_texts=coordinates,
                    parse_detail=json.loads(
                        canonical_bytes(
                            dict(
                                input_population="retained-producer-occurrences-1",
                                target_standing=(
                                    "retained_heading_private_proposal"
                                    if cfg.section_sources
                                    else "retained_component_private_proposal"
                                ),
                                encoder_implementation=encoded.implementation if encoded else None,
                                fresh_vector_count=len(encoded.vectors) if encoded else 0,
                                reused_vector_count=len(cached),
                                encoder_inputs=[asdict(i) for i in encoded.inputs]
                                if encoded
                                else [],
                                **query_detail,
                            )
                        )
                    ),
                )
            )
        return results


class ContextualCandidatesWithNeighborhood(ContextualCandidates):
    version = "9"


class ContextualCandidatesWithNamedBindings(ContextualCandidatesWithNeighborhood):
    version = "10"


class ContextualQueryConfig(ContextualCandidateConfig):
    """Separate persisted configuration for the opt-in query context operation."""

    # A literal-only control uses the same exact carrier population as the enriched arm.
    required_occurrence_ids: tuple[
        Annotated[str, Field(pattern=r"^source-occurrence:[0-9a-f]{64}$")], ...
    ] = Field(default=(), max_length=256, exclude_if=lambda value: not value)
    query_context: QueryContextSelection | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def component_context(self):
        if self.section_sources:
            if self.query_context is not None or self.required_occurrence_ids:
                raise ValueError(
                    "section inventories cannot combine component query carrier controls"
                )
            return self
        if len(set(self.required_occurrence_ids)) != len(self.required_occurrence_ids):
            raise ValueError(
                "exact occurrence selection requires distinct component query carriers"
            )
        if self.query_context is None and not self.required_occurrence_ids:
            raise ValueError("the literal-only control requires explicit exact carriers")
        if self.query_context is not None:
            from corpus_structure.semantic.product_reference import ProductReference

            selected = {ProductReference(**value) for value in self.characterization_layers}
            if any(
                binding.evidence.layer not in selected for binding in self.query_context.bindings
            ):
                raise ValueError("query context requires its exact selected primary layer")
        return self


class ContextualCandidatesWithQueryContext(ContextualCandidatesWithNamedBindings):
    version = "12"
    Config = ContextualQueryConfig
