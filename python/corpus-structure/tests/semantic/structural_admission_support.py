"""Shared controlled inputs and builders for structural admission support."""

from corpus_structure.semantic.contextual_links import RetainedRelationshipDecisionRef
from corpus_structure.semantic.structural_products import (
    ApplicabilityPremise,
    DefinitionProduct,
    ExternalSourceRef,
    LocatedDefinitionSpan,
    RetainedComponentRef,
    StructuralDefinitionReading,
    StructuralInput,
    StructuralPassage,
    StructuralProductReport,
    definition_component,
)


def source():
    return ExternalSourceRef(
        project_id="source-project",
        run_id=1,
        cut_id=2,
        release_id="old",
        result_revision=4,
        source_view_id=5,
        native_task_id=6,
        native_product_key="book",
        native_content_digest="a" * 64,
        projection_digest="b" * 64,
        recipe_digest="c" * 64,
        coordinate_version=3,
    )


def inputs():
    ref = source()
    return StructuralInput(
        question="What defines this usage?",
        scope="statistics",
        inventory_id="frozen-targets",
        policy_id="declared-source-1",
        sources=(ref,),
        passages=(
            StructuralPassage(
                passage_id="usage",
                source_ref=ref.identity,
                start=0,
                end=4,
                text="mean",
                scope="statistics",
            ),
            StructuralPassage(
                passage_id="target",
                source_ref=ref.identity,
                start=5,
                end=14,
                text="sum/count",
                scope="statistics",
            ),
        ),
        dependencies=("frozen-source-input", "component-product"),
    )


def fixture_component():
    passage = inputs().passages[1]
    span = LocatedDefinitionSpan(
        passage_id=passage.passage_id, start=passage.start, end=passage.end, text=passage.text
    )
    return definition_component(
        term=span,
        content=span,
        interpretation="definition",
        basis="model_reading",
        scope=passage.scope,
        evidence=(passage.passage_id,),
        reason="Literal shape fixture",
    )


def definition():
    return StructuralProductReport(
        kind="definition_applicability",
        inputs=inputs(),
        definition=DefinitionProduct(
            usage_id="usage",
            candidate_list_id="list1",
            eligible_targets=(fixture_component().component_id,),
            candidate_targets=(fixture_component().component_id,),
            readings=(
                StructuralDefinitionReading(
                    target_id=fixture_component().component_id,
                    component_ref=RetainedComponentRef(
                        product_id="component-product",
                        component_id=fixture_component().component_id,
                        operation_id="structure.definition_components",
                        operation_version="1",
                        project_id="book",
                        run_id=1,
                        cut_id=1,
                        release_id="r",
                        result_revision=1,
                        selected_task_id=1,
                        origin_task_id=1,
                        runtime_fingerprint="runtime",
                        dependencies=("source",),
                    ),
                    link_ref=RetainedRelationshipDecisionRef(
                        project_id="book",
                        run_id=1,
                        cut_id=1,
                        release_id="r",
                        result_revision=1,
                        selected_task_id=2,
                        origin_task_id=2,
                        runtime_fingerprint="runtime",
                        operation_key="operation",
                        decision_id="decision",
                        edge_id="edge",
                        occurrence_contribution_id="occurrence",
                    ),
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
