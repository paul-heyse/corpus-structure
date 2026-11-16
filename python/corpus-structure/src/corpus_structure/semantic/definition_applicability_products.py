"""Usage applicability over exact native decisions and separately bound components."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .declared_structural_references import DeclaredComponentRef, DeclaredRelationshipRef
from .identity import canonical_bytes
from .structural_products import ApplicabilityPremise, DeclaredLocatedDefinitionComponent


def applicability_inputs(bundle):
    from .contextual_operations import contextual_inputs
    from .declared_structural_calls import structural_inputs
    return structural_inputs(contextual_inputs(bundle))


def applicability_profile_assets():
    from pathlib import Path
    from .python_module_projection import admitted_operation_module_meaning
    from .types import SourceArtifact
    root = Path(__file__).parents[1]
    files = ("methods/definition_applicability_declared.py", "semantic/definition_applicability_products.py",
        "methods/definition_applicability.py", "semantic/contextual_target_products.py",
        "semantic/contextual_operations.py", "semantic/contextual_links.py", "semantic/contextual_retrieval.py",
        "semantic/declared_structural_calls.py", "semantic/declared_structural_references.py",
        "semantic/declared_record_sources.py", "semantic/structural_products.py",
        "semantic/data_operation_cpu_basis.py", "semantic/data_operation_prepared_call.py")
    return SourceArtifact("definition-applicability/profile-assets", canonical_bytes(dict(
        version="declared-definition-applicability-1", files=[(name,
            admitted_operation_module_meaning((root/name).read_bytes()).hex() if name.startswith("methods/")
            else (root/name).read_bytes().hex()) for name in files])))


def applicability_operation_sources():
    from pathlib import Path
    from .python_operation_sources import PythonSource, PythonSourceCollection
    root = Path(__file__).parents[1]
    return PythonSourceCollection(tuple(PythonSource("corpus_structure."+name.removesuffix(".py").replace("/", "."),
        (root/name).read_bytes(), str(root/name)) for name in (
            "methods/definition_applicability_declared.py", "semantic/definition_applicability_products.py",
            "methods/definition_applicability.py", "semantic/data_operation_prepared_call.py")),
        boundary_contracts=(applicability_profile_assets(),))


@dataclass(frozen=True)
class PreparedApplicabilityInputs:
    prepared: Any
    roles: tuple
    context: Any
    check_active: Any


def applicability_kernel(arguments: dict, roles: tuple, context: Any, input_basis: list,
    *, prepared: Any, check_active: Any) -> dict:
    from corpus_structure.methods.definition_applicability_declared import DefinitionApplicabilityOperation
    from .data_operation_cpu_basis import cpu_authority_reply, require_consumed_cpu_basis
    from .data_operation_identity import semantic_value
    names = {role.role for role in roles}
    if names != {"source", "components", "relationship"} or any(
        role.state != "present" or len(role.members) != 1 for role in roles):
        raise ValueError("applicability requires its exact scalar input population")
    require_consumed_cpu_basis(input_basis, context, roles,
        {name: (arguments[name],) for name in names}, parameters=canonical_bytes(semantic_value(
            {name: value for name, value in arguments.items() if name not in names})))
    result = DefinitionApplicabilityOperation(PreparedApplicabilityInputs(prepared, roles, context,
        check_active)).run(**arguments)
    return cpu_authority_reply(input_basis, result)


@dataclass
class ApplicabilityCallPlan:
    prepared: Any
    port: Any = None

    def verify(self):
        if applicability_profile_assets() != self.port.assets[0]:
            raise ValueError("definition applicability source or policy changed")

    def plan(self, arguments, *, binding, check_active, execution_owner):
        import inspect
        from .data_operation_cpu_basis import cpu_input_basis_from_binding
        if binding is None or binding.subject_context is None:
            raise ValueError("applicability requires its actual qualified binding")
        processed = cpu_input_basis_from_binding(self.port.operation.recipe, binding,
            {role.role: (arguments.arguments[role.role],) for role in binding.roles})
        bound = inspect.signature(applicability_kernel, eval_str=True).bind(arguments=arguments.arguments,
            roles=binding.roles, context=binding.subject_context, input_basis=processed,
            prepared=self.prepared, check_active=check_active)
        return (yield from self.port.plan_cpu(applicability_kernel, bound, applicability_operation_sources(),
            prepared_release_id=self.prepared.release_id, verify=self.verify,
            execution_owner=execution_owner, check_active=check_active))


def resolve_applicability_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.methods.definition_applicability_declared import DefinitionApplicabilityOperation
    from .data_operation_ports import PortRefusal
    from .data_operation_prepared_call import PreparedOriginalCallPort
    selected = model.operation(operation)
    if selected.semantic_id != DefinitionApplicabilityOperation.__data_operation__["id"]:
        raise PortRefusal("applicability factory differs from its actual operation")
    receiver, plan = DefinitionApplicabilityOperation(None), ApplicabilityCallPlan(prepared)
    port = PreparedOriginalCallPort(identity, model, selected, sources, custody, receiver.run, plan.plan,
        "corpus_structure.semantic.definition_applicability_products.ApplicabilityCallPlan.plan",
        authorize, (applicability_profile_assets(),), applicability_operation_sources(),
        functions=(("corpus_structure.semantic.definition_applicability_products.applicability_kernel", applicability_kernel),
            ("corpus_structure.semantic.definition_applicability_products.execute_definition_applicability", execute_definition_applicability)),
        requires_prepared_schema=True, retain_cpu_reply=True)
    plan.port = port
    return port


@dataclass(frozen=True)
class DeclaredApplicabilityCandidate:
    target_id: str
    reference: DeclaredComponentRef
    link_ref: DeclaredRelationshipRef
    component: DeclaredLocatedDefinitionComponent
    premises: tuple[ApplicabilityPremise, ...]


def selected_definition_applicability(
    inputs,
    usage_id,
    component_report,
    component_reference,
    relationship_reference,
    binding,
    *,
    usage_frame,
    defining_occurrence=False,
):
    """Reuse compatibility policy only after authenticating meaning and physical usage."""
    from corpus_structure.methods.definition_applicability import (
        applicability_assessment,
        is_defining_occurrence,
    )

    from .source_contexts import (
        NativeSourceContext,
        PreparedNativeSources,
        evidence_anchor,
        source_slice,
    )
    from .contextual_target_products import component_target_values
    from .contextual_retrieval import _meaning
    from .structural_products import ApplicabilityPremise, DeclaredStructuralDefinitionReading

    usage = next(passage for passage in inputs.passages if passage.passage_id == usage_id)
    if not any(
        start <= usage.start < usage.end <= end for start, end in usage_frame.selected_ranges
    ):
        raise ValueError("usage passage exceeds its exact analyzed original source scope")
    matches = tuple(
        component
        for component in component_report.definition_components.components
        if component.component_id == component_reference.component_id
    )
    if len(matches) != 1 or component_reference.structural_id != component_report.product_id:
        raise ValueError("applicability component differs from the exact selected report")
    (component,) = matches
    if binding.edge.relation not in {"denotes", "defined-by"}:
        raise ValueError("applicability requires a selected usage-sense or defining edge")
    if (
        binding.decision.scope != usage.scope
        or binding.decision.effective_version != usage.effective_version
    ):
        raise ValueError("selected usage relationship differs from scope or version")
    if binding.source_pin != usage_frame.pin.values():
        raise ValueError("relationship usage differs from the admitted original source")
    if relationship_reference.edge_id != binding.edge.edge_id:
        raise ValueError("applicability substitutes its selected relationship edge")
    target, meaning = component_target_values(component_report, component,
        original_source=component_reference.original_source)
    carriers = tuple(
        value
        for value in binding.representations
        if value.target_id == component.component_id
        and value == target
        and value.type_name == "definition"
    )
    if len(carriers) != 1:
        raise ValueError(
            "selected relationship does not carry this exact native component reference"
        )
    if canonical_bytes(_meaning(meaning)) != canonical_bytes(binding.target.meaning):
        raise ValueError("selected relationship changes source-resolved definition meaning")
    context = NativeSourceContext(
        usage_frame,
        (),
        (source_slice(usage_frame, usage.start, usage.end),),
        "usage occurrence",
        "witnessed-applicability-1",
        "exact selected physical occurrence",
        max_chars=len(usage.text),
        max_pieces=256,
        max_sources=1,
        version=2,
        preparation=PreparedNativeSources((usage_frame,), max_sources=1),
    )
    anchors = tuple(
        evidence_anchor(context, piece, native=True)[0]
        for piece in context.map_span(0, len(usage.text), literal=usage.text, allow_multiple=True)
    )

    def physical(anchor):
        return canonical_bytes(
            {key: anchor[key] for key in ("pin", "pointer", "start", "end", "source_piece")}
        )

    if not anchors or {physical(anchor) for anchor in anchors} != {
        physical(anchor) for anchor in binding.anchors
    }:
        raise ValueError("usage passage is not the exact selected physical occurrence")
    introduction = defining_occurrence and is_defining_occurrence(
        inputs, usage, component, binding.edge.relation
    )
    candidate = DeclaredApplicabilityCandidate(
        binding.edge.target_id,
        component_reference,
        relationship_reference,
        component,
        (
            ApplicabilityPremise(
                dimension="sense",
                state="compatible",
                evidence=(usage_id, component.term.passage_id),
                reason="Actual selected usage relationship; independent semantic support remains separate.",
            ),
            *(
                ApplicabilityPremise(
                    dimension=dimension,
                    state="inapplicable" if introduction else "unknown",
                    evidence=(usage_id, component.term.passage_id),
                    reason="Same defining occurrence under the explicit introduction policy; no transfer asserted."
                    if introduction
                    else "No authenticated transfer correspondence has been established.",
                )
                for dimension in ("parameterization", "convention")
            ),
        ),
    )
    assessment = applicability_assessment(
        inputs, usage_id, candidate, defining_occurrence=introduction
    )
    return DeclaredStructuralDefinitionReading(
        target_id=candidate.target_id,
        component_ref=candidate.reference,
        link_ref=candidate.link_ref,
        component=candidate.component,
        outcome=assessment.outcome,
        evidence=assessment.evidence,
        premises=assessment.premises,
        reason=assessment.reason,
    )


def execute_definition_applicability(
    receiver,
    source,
    components,
    relationship,
    *,
    component_id,
    decision_id,
    edge_id,
    usage_id,
    start,
    end,
    scope,
    effective_version,
    parent,
    defining_occurrence,
):
    from .contextual_operations import contextual_relationship_binding
    from .declared_structural_calls import PreparedStructuralInputs, _passage
    from .declared_structural_references import DeclaredComponentRef, DeclaredRelationshipRef
    from .structural_products import (
        DeclaredDefinitionApplicabilityReport,
        DeclaredDefinitionComponentsReport,
        DeclaredDefinitionProduct,
        DeclaredStructuralInput,
    )

    profile = receiver.inputs
    profile.check_active()
    exact = PreparedStructuralInputs(
        profile.prepared, profile.roles, profile.context.project_id, profile.check_active
    )
    frame = exact.frame("source", source)
    source_ref, usage = _passage(
        frame,
        passage_id=usage_id,
        start=start,
        end=end,
        scope=scope,
        version=effective_version,
        parent=parent,
    )
    report = DeclaredDefinitionComponentsReport.model_validate(components)
    member = exact.member("components")
    component_reference = DeclaredComponentRef.from_bound(
        member,
        project=profile.context.project_id,
        structural_id=report.product_id,
        component_id=component_id,
    )
    if component_reference.member_id is not None or any(
        pin.context != component_reference.context for pin in report.sources_input
    ):
        raise ValueError(
            "definition component report differs from its exact whole native source context"
        )
    relation_reference = DeclaredRelationshipRef.from_bound(
        exact.member("relationship"), project=profile.context.project_id, edge_id=edge_id
    )
    if relation_reference.member_id is not None:
        raise ValueError("definition relationship requires its exact whole retained product")
    binding = contextual_relationship_binding(
        relationship, decision_id=decision_id, edge_id=edge_id
    )
    sources = {reference.identity: reference for reference in (*report.inputs.sources, source_ref)}
    passages = {passage.passage_id: passage for passage in report.inputs.passages}
    if usage_id in passages and passages[usage_id] != usage:
        raise ValueError("authored usage identity collides with a different retained passage")
    passages[usage_id] = usage
    inputs = DeclaredStructuralInput(
        question="Assess the selected usage binding to its actual retained definition.",
        scope=scope,
        inventory_id=binding.decision.candidate_list_id,
        policy_id="definition-introduction-1"
        if defining_occurrence
        else "witnessed-definition-applicability-1",
        sources=tuple(sources.values()),
        passages=tuple(passages.values()),
        dependencies=tuple(
            dict.fromkeys(
                (*report.inputs.dependencies, member.product, exact.member("relationship").product)
            )
        ),
    )
    reading = selected_definition_applicability(
        inputs,
        usage_id,
        report,
        component_reference,
        relation_reference,
        binding,
        usage_frame=frame,
        defining_occurrence=defining_occurrence,
    )
    result = DeclaredDefinitionApplicabilityReport(
        inputs=inputs,
        definition=DeclaredDefinitionProduct(
            usage_id=usage_id,
            candidate_list_id=binding.decision.candidate_list_id,
            eligible_targets=(reading.target_id,),
            candidate_targets=(reading.target_id,),
            readings=(reading,),
        ),
        sources_input=(exact.reference("source"),),
        components_input=exact.reference("components"),
        relationship_input=exact.reference("relationship"),
    )
    profile.check_active()
    return result.model_dump(mode="json", exclude_none=True)
