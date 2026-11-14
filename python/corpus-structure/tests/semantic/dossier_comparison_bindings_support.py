"""Shared controlled inputs and builders for dossier comparison bindings support."""

from corpus_structure.methods.structural_products import compare_clauses
from corpus_structure.semantic.contextual_links import RetainedRelationshipDecisionRef
from corpus_structure.semantic.structural_admission import structural_statement
from corpus_structure.semantic.structural_products import (
    DIMENSIONS,
    ClauseField,
    ClauseFieldGroup,
    ClauseReading,
    DefinitionComponentsProduct,
    Dimension,
    DossierComparisonSelection,
    LocatedDefinitionSpan,
    RetainedComponentRef,
    RetainedStructuralRef,
    StructuralProductReport,
    definition_component,
)
from semantic.structural_products_support import inputs


def side_inputs():
    value = inputs()
    left, right = (
        p.model_copy(
            update=dict(text=t, start=0, end=len(t), scope="rules", effective_version="R2")
        )
        for p, t in zip(
            value.passages,
            ("Apply measure except in test runs.", "Measure is a control rule."),
            strict=True,
        )
    )
    return value.model_copy(update=dict(passages=(left, right), scope="rules"))


def span(passage, literal):
    start = passage.start + passage.text.index(literal)
    return LocatedDefinitionSpan(
        passage_id=passage.passage_id, start=start, end=start + len(literal), text=literal
    )


def custody(source, task_id):
    return dict(
        project_id=source.project_id,
        run_id=source.run_id,
        cut_id=source.cut_id,
        release_id=source.release_id,
        result_revision=source.result_revision,
        selected_task_id=task_id,
        origin_task_id=task_id,
        runtime_fingerprint="runtime",
    )


def fixture(value=None, *, exception=True, root_on_left=False, primary_layers=None):
    value = value or side_inputs()
    left, right = value.passages
    sources = {s.identity: s for s in value.sources}
    left_source, right_source = sources[left.source_ref], sources[right.source_ref]
    root_passage = left if root_on_left else right
    root = definition_component(
        term=span(root_passage, "Measure"),
        content=span(root_passage, "control rule"),
        scope=root_passage.scope,
        effective_version=root_passage.effective_version,
        interpretation="definition",
        basis="matched_cue",
        evidence=(root_passage.passage_id,),
        reason="Located definition component fixture.",
    )
    definition = StructuralProductReport(
        kind="definition_components",
        inputs=value,
        definition_components=DefinitionComponentsProduct(components=(root,), stages=()),
    )
    root_ref = RetainedComponentRef(
        **custody(sources[root_passage.source_ref], 30),
        component_id=root.component_id,
        product_id=definition.product_id,
        dependencies=value.dependencies,
        operation_id="structure.definition_components",
        operation_version="8",
    )
    empty = {dimension: ClauseFieldGroup(state="absent") for dimension in DIMENSIONS}
    groups: dict[Dimension, ClauseFieldGroup] = empty
    if exception:
        field = ClauseField(
            dimension="exception",
            lexical_value="except in test runs",
            evidence=(left.passage_id,),
            spans=(span(left, "except in test runs"),),
            contribution_id="source-contribution:" + "a" * 64,
        )
        groups = {
            **empty,
            "exception": ClauseFieldGroup(state="present", grouping="singleton", members=(field,)),
        }
    comparison = compare_clauses(
        value,
        primary_layers=primary_layers,
        left=ClauseReading(passage_id=left.passage_id, groups=groups),
        right=ClauseReading(passage_id=right.passage_id, groups=empty),
        left_reading=dict(
            contribution_id="source-contribution:" + "b" * 64, **custody(left_source, 31)
        ),
        right_reading=dict(
            contribution_id="source-contribution:" + "c" * 64, **custody(right_source, 32)
        ),
    )
    reference = RetainedStructuralRef(product_id=comparison.product_id, **custody(left_source, 33))
    selected = []
    relationships = {}
    for side, passage, source, literal, relation in (
        ("left", left, left_source, "measure", "specializes"),
        ("right", right, right_source, "Measure", "denotes"),
    ):
        rel_ref = RetainedRelationshipDecisionRef(
            **custody(source, 34 if side == "left" else 35),
            operation_key="contextual-operation",
            decision_id="decision-" + side,
            edge_id="edge-" + side,
            occurrence_contribution_id="occurrence-" + side,
        )
        selected.append(
            DossierComparisonSelection(
                comparison_product_id=comparison.product_id, side=side, relationship_ref=rel_ref
            )
        )
        relationships[rel_ref] = dict(
            decision=dict(scope=passage.scope, effective_version=passage.effective_version),
            edge=dict(relation=relation, member_target_ids=(root.component_id,)),
            source_view_id=source.source_view_id,
            component_targets=[dict(reference=root_ref.model_dump(mode="json"))],
            located_occurrence=[span(passage, literal).model_dump(exclude={"passage_id"})],
        )
    value = value.model_copy(
        update=dict(
            dependencies=(
                *value.dependencies,
                comparison.product_id,
                *(s.relationship_ref.edge_id for s in selected),
            )
        )
    )
    payload = dict(
        report=comparison.model_dump(mode="json"),
        public_assertions=[
            dict(assessment_id="exact-comparison-grade", statement=structural_statement(comparison))
        ],
    )
    return value, root, root_ref, reference, payload, selected, relationships
