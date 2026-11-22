"""Literal current domain inputs, without execution or native admission standing.

Assessment labels below are bounded inputs to the pure projection controls. They do
not represent protected native assessments or establish provider evidence.
"""

from corpus_structure.semantic.declared_structural_references import (
    DeclaredComponentRef,
    DeclaredRelationshipRef,
    DeclaredStructuralRef,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_admission import structural_statement
from corpus_structure.semantic.structural_products import (
    ApplicabilityPremise,
    DeclaredDefinitionApplicabilityReport,
    DeclaredDefinitionComponentsProduct,
    DeclaredDefinitionComponentsReport,
    DeclaredDefinitionProduct,
    DeclaredStructuralDefinitionReading,
    DeclaredStructuralInput,
    DeclaredStructuralInputPin,
    DefinitionOutcome,
    LocatedDefinitionSpan,
    declared_definition_component,
)
from semantic.structural_products_support import input_from_passages, inputs

OUTCOMES: tuple[DefinitionOutcome, ...] = (
    "applicable_definition",
    "applicable_explanation",
    "mention",
    "example",
    "incompatible",
    "unresolved",
)


def source_pin(source):
    return DeclaredStructuralInputPin(
        product_id=source.source_product,
        member_id=source.source_member,
        reference=source.source,
        kind_contract=source.kind_contract,
        project_id=source.project_id,
        subject=source.subject,
        subject_definition=source.subject_definition,
        original_source=source.original_source,
        analyzed_scope_meaning=source.analyzed_scope_meaning,
    )


def components(value: DeclaredStructuralInput | None = None, *, passage_id=None, span=None):
    value = inputs() if value is None else value
    passage_id = span.passage_id if span is not None else passage_id
    passage = next(p for p in value.passages if passage_id is None or p.passage_id == passage_id)
    span = (
        span
        if span is not None
        else LocatedDefinitionSpan(
            passage_id=passage.passage_id, start=passage.start, end=passage.end, text=passage.text
        )
    )
    return DeclaredDefinitionComponentsReport(
        inputs=value,
        sources_input=tuple(source_pin(source) for source in value.sources),
        definition_components=DeclaredDefinitionComponentsProduct(
            components=tuple(
                declared_definition_component(
                    term=span,
                    content=span,
                    interpretation=state,
                    basis="matched_cue",
                    scope=passage.scope,
                    evidence=(passage.passage_id,),
                    reason="Same literal source, distinct original interpretations.",
                )
                for state in ("definition", "explanation", "unresolved")
            ),
            stages=(),
        ),
    )


def report_reference(report):
    source = report.inputs.sources[0]
    return DeclaredStructuralRef(
        product_id="unadmitted:dossier-report:" + report.product_id,
        structural_id=report.product_id,
        kind_contract="unadmitted:" + report.kind,
        project_id=source.project_id,
        subject=source.subject,
        subject_definition=source.subject_definition,
        original_source=source.original_source,
        analyzed_scope_meaning=source.analyzed_scope_meaning,
    )


def component_reference(report, component):
    assert component in report.definition_components.components
    return DeclaredComponentRef(
        **report_reference(report).model_dump(), component_id=component.component_id
    )


def report_input_pin(report):
    reference = report_reference(report)
    return source_pin(report.inputs.sources[0]).model_copy(
        update=dict(
            product_id=reference.product_id,
            member_id=reference.member_id,
            kind_contract=reference.kind_contract,
            reference=canonical_bytes([reference.product_id, reference.member_id]).decode(),
        )
    )


def retained(report):
    reference = report_reference(report)
    value = report.inputs.model_copy(
        update=dict(
            dependencies=tuple(
                dict.fromkeys(
                    (*report.inputs.dependencies, reference.product_id, report.product_id)
                )
            )
        )
    )
    statements = (
        [
            structural_statement(report, component.component_id)
            for component in report.definition_components.components
            if component.interpretation != "unresolved"
        ]
        if report.definition_components is not None
        else [structural_statement(report)]
    )
    payload = dict(
        report=report.model_dump(mode="json", exclude_none=True),
        public_assertions=[
            dict(
                assessment_id="unadmitted:literal-assessment:" + report.product_id + ":" + str(i),
                statement=statement,
            )
            for i, statement in enumerate(statements)
        ],
    )
    return value, reference, payload


def applicability():
    value = input_from_passages(
        (
            dict(document="semantic-state-original", passage_id="usage", start=0, text="mean"),
            dict(
                document="semantic-state-original", passage_id="target", start=5, text="sum/count"
            ),
        ),
        scope="statistics",
    )
    originals = components(value, passage_id="target")
    by_state = {
        component.interpretation: component
        for component in originals.definition_components.components
    }
    component_pin = report_input_pin(originals)
    relationship_pin = component_pin.model_copy(
        update=dict(
            product_id="unadmitted:literal-relationship-ledger",
            kind_contract="unadmitted:relationship-ledger",
            reference=canonical_bytes(["unadmitted:literal-relationship-ledger", None]).decode(),
        )
    )
    relationship = DeclaredRelationshipRef(
        **relationship_pin.model_dump(exclude={"reference"}), edge_id="literal:usage-target"
    )
    value = value.model_copy(
        update=dict(
            dependencies=tuple(
                dict.fromkeys(
                    (
                        *value.dependencies,
                        component_pin.product_id,
                        originals.product_id,
                        relationship_pin.product_id,
                    )
                )
            )
        )
    )
    targets = tuple(by_state[state].component_id for state in ("definition", "explanation"))
    reports = []
    for outcome in OUTCOMES:
        component = by_state["explanation" if outcome == "applicable_explanation" else "definition"]
        reading = DeclaredStructuralDefinitionReading(
            target_id=component.component_id,
            component_ref=component_reference(originals, component),
            link_ref=relationship,
            component=component,
            outcome=outcome,
            evidence=("target",),
            premises=tuple(
                ApplicabilityPremise(
                    dimension=dimension,
                    state="incompatible"
                    if outcome == "incompatible" and dimension == "sense"
                    else "unknown"
                    if outcome == "unresolved" and dimension == "sense"
                    else "compatible",
                    evidence=("target",),
                    reason="Independent literal premise for this semantic-state control.",
                )
                for dimension in (
                    "sense",
                    "parameterization",
                    "convention",
                    "scope",
                    "version",
                    "parent",
                )
            ),
            reason="Independently supplied alternative applicability outcome.",
        )
        reports.append(
            DeclaredDefinitionApplicabilityReport(
                inputs=value,
                sources_input=tuple(source_pin(source) for source in value.sources),
                components_input=component_pin,
                relationship_input={"variant": "product", "role": "relationship"},
                definition=DeclaredDefinitionProduct(
                    usage_id="usage",
                    candidate_list_id="literal:fixed-targets",
                    eligible_targets=targets,
                    candidate_targets=targets,
                    readings=(reading,),
                ),
            )
        )
    return originals, tuple(reports)
