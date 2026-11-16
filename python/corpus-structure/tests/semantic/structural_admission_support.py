"""Shared controlled inputs and builders for structural admission support."""

from corpus_structure.semantic.declared_structural_references import DeclaredRelationshipRef
from semantic.structural_products_support import input_from_passages, root_references
from corpus_structure.semantic.structural_products import (
    ApplicabilityPremise,
    DeclaredDefinitionProduct,
    LocatedDefinitionSpan,
    DeclaredStructuralDefinitionReading,
    DeclaredStructuralProductReport,
    declared_definition_component,
)


def inputs():
    return input_from_passages(
        (
            dict(document="admission-original", passage_id="usage", start=0, text="mean"),
            dict(document="admission-original", passage_id="target", start=5, text="sum/count"),
        ),
        question="What defines this usage?",
        scope="statistics",
    )


def source():
    return inputs().sources[0]


def component_reference():
    return root_references(inputs())[0].model_copy(
        update=dict(product_id="component-product", component_id=fixture_component().component_id)
    )


def relationship_reference():
    root = component_reference()
    return DeclaredRelationshipRef(
        **{key: value for key, value in root.model_dump().items()
           if key not in {"component_id", "structural_id"}},
        edge_id="fixture:definition-edge",
    )


def fixture_component():
    passage = inputs().passages[1]
    span = LocatedDefinitionSpan(
        passage_id=passage.passage_id, start=passage.start, end=passage.end, text=passage.text
    )
    return declared_definition_component(
        term=span,
        content=span,
        interpretation="definition",
        basis="model_reading",
        scope=passage.scope,
        evidence=(passage.passage_id,),
        reason="Literal shape fixture",
    )


def definition():
    return DeclaredStructuralProductReport(
        kind="definition_applicability",
        inputs=inputs(),
        definition=DeclaredDefinitionProduct(
            usage_id="usage",
            candidate_list_id="list1",
            eligible_targets=(fixture_component().component_id,),
            candidate_targets=(fixture_component().component_id,),
            readings=(
                DeclaredStructuralDefinitionReading(
                    target_id=fixture_component().component_id,
                    component_ref=component_reference(),
                    link_ref=relationship_reference(),
                    component=fixture_component(),
                    premises=tuple(
                        ApplicabilityPremise(
                            dimension=dimension,
                            state="unknown"
                            if dimension in {"parent", "parameterization", "convention"}
                            else "compatible",
                            evidence=("target",),
                            reason="Independent explicit fixture premise",
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
                    outcome="unresolved",
                    evidence=("target",),
                    reason="supplied reading",
                ),
            ),
        ),
    )
