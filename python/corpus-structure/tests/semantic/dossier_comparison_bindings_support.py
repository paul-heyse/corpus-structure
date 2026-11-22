"""Shared controlled inputs and builders for dossier comparison bindings support."""

from corpus_structure.methods.structural_products import compare_clauses
from corpus_structure.semantic.contextual_links import RelationshipDecision, RelationshipEdge
from corpus_structure.semantic.contextual_operations import ContextualRelationshipBinding
from corpus_structure.semantic.contextual_retrieval import (
    SemanticTargetGroup,
    target_representation,
)
from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
from corpus_structure.semantic.declared_structural_references import (
    DeclaredComponentRef,
    DeclaredRelationshipRef,
    DeclaredStructuralRef,
)
from corpus_structure.semantic.dossier_products import DossierRelationship
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_admission import structural_statement
from corpus_structure.semantic.structural_products import (
    DIMENSIONS,
    DeclaredClauseField,
    DeclaredClauseFieldGroup,
    DeclaredClauseReading,
    DeclaredComparisonReport,
    DeclaredDefinitionComponentsProduct,
    DeclaredDossierComparisonSelection,
    DeclaredStructuralInputPin,
    DeclaredStructuralProductReport,
    Dimension,
    LocatedDefinitionSpan,
    declared_definition_component,
)
from semantic.structural_products_support import input_from_passages, native_source


def side_inputs():
    return input_from_passages(
        (
            dict(
                passage_id="a",
                document="book-a",
                text="Apply measure except in test runs.",
                start=0,
                scope="rules",
                effective_version="R2",
            ),
            dict(
                passage_id="b",
                document="book-b",
                text="Measure is a control rule.",
                start=0,
                scope="rules",
                effective_version="R2",
            ),
        ),
        scope="rules",
    )


def span(passage, literal):
    start = passage.start + passage.text.index(literal)
    return LocatedDefinitionSpan(
        passage_id=passage.passage_id, start=start, end=start + len(literal), text=literal
    )


def custody(source, identifier):
    return dict(
        product_id=f"unadmitted:product:{identifier}",
        kind_contract="unadmitted:fixture-kind",
        project_id=source.project_id,
        subject=source.subject,
        subject_definition=source.subject_definition,
        original_source=source.original_source,
        analyzed_scope_meaning=source.analyzed_scope_meaning,
    )


def fixture(value=None, *, exception=True, root_on_left=False, primary_layers=None):
    value = value or side_inputs()
    left, right = value.passages
    sources = {s.identity: s for s in value.sources}
    left_source, right_source = sources[left.source_ref], sources[right.source_ref]
    root_passage = left if root_on_left else right
    root = declared_definition_component(
        term=span(root_passage, "Measure"),
        content=span(root_passage, "control rule"),
        scope=root_passage.scope,
        effective_version=root_passage.effective_version,
        interpretation="definition",
        basis="matched_cue",
        evidence=(root_passage.passage_id,),
        reason="Located definition component fixture.",
    )
    definition = DeclaredStructuralProductReport(
        kind="definition_components",
        inputs=value,
        definition_components=DeclaredDefinitionComponentsProduct(components=(root,), stages=()),
    )
    root_ref = DeclaredComponentRef(
        **custody(sources[root_passage.source_ref], 30),
        component_id=root.component_id,
        structural_id=definition.product_id,
    )
    empty = {dimension: DeclaredClauseFieldGroup(state="absent") for dimension in DIMENSIONS}
    groups: dict[Dimension, DeclaredClauseFieldGroup] = empty
    if exception:
        field = DeclaredClauseField(
            dimension="exception",
            lexical_value="except in test runs",
            evidence=(left.passage_id,),
            spans=(span(left, "except in test runs"),),
            contribution_id="source-contribution:" + "a" * 64,
        )
        groups = {
            **empty,
            "exception": DeclaredClauseFieldGroup(
                state="present", grouping="singleton", members=(field,)
            ),
        }
    comparison = compare_clauses(
        value,
        primary_readings=primary_layers,
        left=DeclaredClauseReading(passage_id=left.passage_id, groups=groups),
        right=DeclaredClauseReading(passage_id=right.passage_id, groups=empty),
        left_reading=dict(
            contribution_id="source-contribution:" + "b" * 64, **custody(left_source, 31)
        ),
        right_reading=dict(
            contribution_id="source-contribution:" + "c" * 64, **custody(right_source, 32)
        ),
    )
    comparison = DeclaredComparisonReport(
        **comparison.model_dump(exclude_none=True),
        sources_input=tuple(
            DeclaredStructuralInputPin(
                **custody(source, "source:" + str(i)), reference=source.source
            )
            for i, source in enumerate(value.sources)
        ),
        reports_input=tuple(
            DeclaredStructuralInputPin(
                **custody(source, 31 + i),
                reference=canonical_bytes([f"unadmitted:product:{31 + i}", None]).decode(),
            )
            for i, source in enumerate((left_source, right_source))
        ),
    )
    reference = DeclaredStructuralRef(
        structural_id=comparison.product_id, **custody(left_source, 33)
    )
    selected = []
    relationships = {}
    for side, passage, source, literal, relation in (
        ("left", left, left_source, "measure", "specializes"),
        ("right", right, right_source, "Measure", "denotes"),
    ):
        rel_ref = DeclaredRelationshipRef(
            **custody(source, 34 if side == "left" else 35), edge_id="edge-" + side
        )
        selected.append(
            DeclaredDossierComparisonSelection(
                comparison_product_id=reference.product_id, side=side, relationship_ref=rel_ref
            )
        )
        from semantic.formal_products_support import released_profile

        frozen = native_source(released_profile().prepared, value, source)
        frame = DeclaredNativeFrameSource.from_retained_record(
            frozen.content.decode(),
            canonical_bytes(source.model_dump(mode="json", exclude_none=True)).decode(),
        )
        located = span(passage, literal)
        piece = next(
            piece
            for piece in frame.pieces
            if piece["kind"] == "native_text"
            and piece["start"] <= located.start < located.end <= piece["end"]
        )
        edge = RelationshipEdge(
            rel_ref.edge_id,
            "supplied:constraint",
            "supplied:occurrence",
            root.component_id,
            (root.component_id,),
            relation,
            (),
            "preferred",
        )
        decision = RelationshipDecision(
            "supplied:decision:" + side,
            "supplied:candidate-list",
            "supplied:occurrence",
            passage.scope,
            passage.effective_version,
            "supplied:policy",
            "supplied:exclusions",
            "selected",
            (),
            (),
            (edge,),
            (),
            (),
            None,
            None,
            source.source,
            (),
        )
        carrier = target_representation(
            root.component_id,
            canonical_bytes(root_ref.model_dump(mode="json", exclude_none=True)).decode(),
            "Measure",
            "control rule",
            type_name="definition",
            scope=root.scope,
            effective_version=root.effective_version,
        )
        meaning = structural_statement(definition, root.component_id)["definition_component"]
        binding = ContextualRelationshipBinding(
            decision,
            edge,
            SemanticTargetGroup(root.component_id, (root.component_id,), meaning),
            (carrier,),
            frame.pin.values(),
            (
                dict(
                    pin=frame.pin.values(),
                    space="native",
                    precision="exact",
                    pointer=piece["item_ref"],
                    start=located.start - piece["start"],
                    end=located.end - piece["start"],
                    source_piece=literal,
                ),
            ),
        )
        relationships[rel_ref] = DossierRelationship(binding, frame, meaning)
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
