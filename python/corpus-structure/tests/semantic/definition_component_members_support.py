"""Explicit unadmitted component packet fixtures for pure structural tests."""

from corpus_structure.semantic.structural_products import (
    DeclaredDefinitionComponentPacket,
    DeclaredStructuralInputPin,
)


def unadmitted_component_members(components):
    return tuple(
        DeclaredDefinitionComponentPacket(
            body=component,
            member_id=component.component_id,
            kind_contract="unadmitted:definition-component",
            context=dict(
                subject="unadmitted:subject",
                subject_definition="unadmitted:definition",
                original_source="unadmitted:original",
                analyzed_scope={},
            ),
        )
        for component in components
    )


def unadmitted_component_source():
    return DeclaredStructuralInputPin(
        product_id="unadmitted:product",
        kind_contract="unadmitted:source",
        project_id="unadmitted:project",
        subject="unadmitted:subject",
        subject_definition="unadmitted:definition",
        original_source="unadmitted:original",
        analyzed_scope_meaning="{}",
        reference="unadmitted:source",
    )
