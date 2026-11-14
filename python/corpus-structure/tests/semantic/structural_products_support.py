"""Shared controlled inputs and builders for structural products support."""

from corpus_structure.semantic.structural_products import (
    ExternalSourceRef,
    StructuralInput,
    StructuralPassage,
)


def inputs():
    a = ExternalSourceRef(
        project_id="book-a",
        run_id=1,
        cut_id=1,
        release_id="release:a",
        result_revision=1,
        source_view_id=1,
        native_task_id=1,
        native_product_key="document",
        native_content_digest="a" * 64,
        projection_digest="b" * 64,
        recipe_digest="c" * 64,
        coordinate_version=3,
    )
    b = a.model_copy(update={"project_id": "book-b", "run_id": 2, "source_view_id": 2})
    pa = StructuralPassage(
        passage_id="a", source_ref=a.identity, start=0, end=5, text="hello", scope="scope"
    )
    pb = StructuralPassage(
        passage_id="b", source_ref=b.identity, start=10, end=15, text="world", scope="scope"
    )
    return StructuralInput(
        question="compare source clauses",
        scope="scope",
        inventory_id="inventory",
        policy_id="literal-fields-1",
        sources=(a, b),
        passages=(pa, pb),
        dependencies=("input-policy:1", "component-product"),
    )
