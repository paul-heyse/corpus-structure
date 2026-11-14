"""Actual retained occurrence retrieval over authenticated definition-component targets."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from corpus_structure.semantic.contextual_links import (
    RelationKind,
    RelationshipConstraint,
    RelationshipWitness,
)
from corpus_structure.semantic.contextual_registry import (
    ExtractedComponentTarget,
)
from corpus_structure.semantic.contributions import (
    contribution_identity,
    occurrence_identity,
    operation_identity,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python, source_value
from corpus_structure.semantic.retained_contributions import RetainedContributionRef
from corpus_structure.semantic.source_contexts import (
    ContextRefused,
    NativeSourceContext,
    SourceSlice,
    evidence_anchor,
)
from corpus_structure.semantic.structural_products import ExternalSourceRef


from .contextual_query import QueryContextSelection






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
