"""Usage applicability over exact native decisions and separately bound components."""

from __future__ import annotations

from dataclasses import dataclass

from .identity import canonical_bytes
from .declared_structural_references import DeclaredComponentRef, DeclaredRelationshipRef
from .structural_products import ApplicabilityPremise, DeclaredLocatedDefinitionComponent


@dataclass(frozen=True)
class DeclaredApplicabilityCandidate:
    target_id: str
    reference: DeclaredComponentRef
    link_ref: DeclaredRelationshipRef
    component: DeclaredLocatedDefinitionComponent
    premises: tuple[ApplicabilityPremise, ...]


def selected_definition_applicability(
    inputs, usage_id, component_report, component_reference, relationship_reference,
    binding, *, usage_frame, defining_occurrence=False,
):
    """Reuse compatibility policy only after authenticating meaning and physical usage."""
    from corpus_structure.methods.definition_applicability import (
        applicability_reading_values, is_defining_occurrence,
    )
    from .source_contexts import (
        NativeSourceContext, PreparedNativeSources, evidence_anchor, source_slice,
    )
    from .structural_admission import structural_statement
    from .structural_products import ApplicabilityPremise, DeclaredStructuralDefinitionReading

    usage = next(passage for passage in inputs.passages if passage.passage_id == usage_id)
    if not any(start <= usage.start < usage.end <= end for start, end in usage_frame.selected_ranges):
        raise ValueError("usage passage exceeds its exact analyzed original source scope")
    matches = tuple(component for component in component_report.definition_components.components if component.component_id == component_reference.component_id)
    if len(matches) != 1 or component_reference.structural_id != component_report.product_id:
        raise ValueError("applicability component differs from the exact selected report")
    (component,) = matches
    if binding.edge.relation not in {"denotes", "defined-by"}:
        raise ValueError("applicability requires a selected usage-sense or defining edge")
    if binding.decision.scope != usage.scope or binding.decision.effective_version != usage.effective_version:
        raise ValueError("selected usage relationship differs from scope or version")
    if binding.source_pin != usage_frame.pin.values():
        raise ValueError("relationship usage differs from the admitted original source")
    if relationship_reference.edge_id != binding.edge.edge_id:
        raise ValueError("applicability substitutes its selected relationship edge")
    exact_binding = canonical_bytes(component_reference.model_dump(mode="json", exclude_none=True)).decode()
    carriers = tuple(value for value in binding.representations if value.target_id == component.component_id and value.source_binding == exact_binding and value.type_name == "definition")
    if len(carriers) != 1:
        raise ValueError("selected relationship does not carry this exact native component reference")
    meaning = structural_statement(component_report, component.component_id)["definition_component"]
    if canonical_bytes(meaning) != canonical_bytes(binding.target.meaning):
        raise ValueError("selected relationship changes source-resolved definition meaning")
    context = NativeSourceContext(
        usage_frame, (), (source_slice(usage_frame, usage.start, usage.end),),
        "usage occurrence", "witnessed-applicability-1", "exact selected physical occurrence",
        max_chars=len(usage.text), max_pieces=256, max_sources=1, version=2,
        preparation=PreparedNativeSources((usage_frame,), max_sources=1),
    )
    anchors = tuple(evidence_anchor(context, piece, native=True)[0] for piece in context.map_span(0, len(usage.text), literal=usage.text, allow_multiple=True))

    def physical(anchor):
        return canonical_bytes({key: anchor[key] for key in ("pin", "pointer", "start", "end", "source_piece")})

    if not anchors or {physical(anchor) for anchor in anchors} != {physical(anchor) for anchor in binding.anchors}:
        raise ValueError("usage passage is not the exact selected physical occurrence")
    introduction = defining_occurrence and is_defining_occurrence(inputs, usage, component, binding.edge.relation)
    candidate = DeclaredApplicabilityCandidate(
        binding.edge.target_id, component_reference, relationship_reference, component,
        (
            ApplicabilityPremise(dimension="sense", state="compatible", evidence=(usage_id, component.term.passage_id), reason="Actual selected usage relationship; independent semantic support remains separate."),
            *(ApplicabilityPremise(dimension=dimension, state="inapplicable" if introduction else "unknown", evidence=(usage_id, component.term.passage_id), reason="Same defining occurrence under the explicit introduction policy; no transfer asserted." if introduction else "No authenticated transfer correspondence has been established.") for dimension in ("parameterization", "convention")),
        ),
    )
    return DeclaredStructuralDefinitionReading(**applicability_reading_values(inputs, usage_id, candidate, defining_occurrence=introduction))


def execute_definition_applicability(receiver, source, components, relationship, *, component_id, decision_id, edge_id, usage_id, start, end, scope, effective_version, parent, defining_occurrence):
    from .contextual_operations import contextual_relationship_binding
    from .declared_structural_calls import PreparedStructuralInputs, _passage
    from .declared_structural_references import DeclaredComponentRef, DeclaredRelationshipRef
    from .structural_products import (
        DeclaredDefinitionComponentsReport, DeclaredDefinitionProduct, DeclaredDefinitionReport,
        DeclaredStructuralInput,
    )

    profile = receiver.inputs
    profile.check_active()
    exact = PreparedStructuralInputs(profile.prepared, profile.roles, profile.context.project_id, profile.check_active)
    frame = exact.frame("source", source)
    source_ref, usage = _passage(frame, passage_id=usage_id, start=start, end=end, scope=scope, version=effective_version, parent=parent)
    report = DeclaredDefinitionComponentsReport.model_validate(components)
    member = exact.member("components")
    component_reference = DeclaredComponentRef.from_bound(member, project=profile.context.project_id, structural_id=report.product_id, component_id=component_id)
    if component_reference.member_id is not None or any(pin.context != component_reference.context for pin in report.sources_input):
        raise ValueError("definition component report differs from its exact whole native source context")
    relation_reference = DeclaredRelationshipRef.from_bound(exact.member("relationship"), project=profile.context.project_id, edge_id=edge_id)
    if relation_reference.member_id is not None:
        raise ValueError("definition relationship requires its exact whole retained product")
    binding = contextual_relationship_binding(relationship, decision_id=decision_id, edge_id=edge_id)
    sources = {reference.identity: reference for reference in (*report.inputs.sources, source_ref)}
    passages = {passage.passage_id: passage for passage in report.inputs.passages}
    if usage_id in passages and passages[usage_id] != usage:
        raise ValueError("authored usage identity collides with a different retained passage")
    passages[usage_id] = usage
    inputs = DeclaredStructuralInput(
        question="Assess the selected usage binding to its actual retained definition.", scope=scope,
        inventory_id=binding.decision.candidate_list_id,
        policy_id="definition-introduction-1" if defining_occurrence else "witnessed-definition-applicability-1",
        sources=tuple(sources.values()), passages=tuple(passages.values()),
        dependencies=tuple(dict.fromkeys((*report.inputs.dependencies, member.product, exact.member("relationship").product))),
    )
    reading = selected_definition_applicability(inputs, usage_id, report, component_reference, relation_reference, binding, usage_frame=frame, defining_occurrence=defining_occurrence)
    result = DeclaredDefinitionReport(
        inputs=inputs,
        definition=DeclaredDefinitionProduct(usage_id=usage_id, candidate_list_id=binding.decision.candidate_list_id, eligible_targets=(reading.target_id,), candidate_targets=(reading.target_id,), readings=(reading,)),
        sources_input=(exact.reference("source"),),
        reports_input=(exact.reference("components"), exact.reference("relationship")),
    )
    profile.check_active()
    return result.model_dump(mode="json", exclude_none=True)
