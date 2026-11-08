"""Portable current source projection checks derive pieces from native members."""

from hashlib import sha256

import pytest

from corpus_structure.ingest.pdf_hierarchy import section_text_recipe
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.serve.review_source_projection import verify_source_projection


def test_current_review_replays_selected_prose_and_qualified_exclusions():
    product = ProductReference(1, "native", "a" * 64)
    recipe = section_text_recipe(product, analysis_eligible=True)
    origin = "b" * 64
    root = "#/body"
    first = "#/texts/0"
    second = "#/texts/1"
    nested = "#/groups/0"
    value = dict(
        source_coverage="selected_projection_replay",
        ref=dict(
            native_product=product.values(),
            section_pointer=root,
            membership="direct",
            analysis_eligible=True,
            recipe_digest=sha256(recipe).hexdigest(),
        ),
        text="Required\nRetained",
        projection_inputs=dict(
            recipe=recipe.decode(),
            original_digest=origin,
            excluded={nested: dict(self_ref=nested, label="section")},
        ),
        context=dict(
            items=[
                dict(
                    self_ref=root,
                    label="body",
                    children=[{"$ref": first}, {"$ref": second}, {"$ref": nested}],
                ),
                dict(self_ref=first, label="text", text="Required"),
                dict(self_ref=second, label="text", text="Retained"),
            ],
            ancestors=[],
            pieces=[
                dict(item_ref=first, start=0, end=8, kind="native_text", source_field="text"),
                dict(start=8, end=9, kind="synthetic_separator"),
                dict(item_ref=second, start=9, end=17, kind="native_text", source_field="text"),
            ],
        ),
    )
    assert verify_source_projection(value) == origin
    value["text"] = "Retained"
    value["context"]["pieces"] = [
        dict(item_ref=second, start=0, end=8, kind="native_text", source_field="text"),
    ]
    with pytest.raises(ValueError, match="field address inventory"):
        verify_source_projection(value)
    del value["projection_inputs"]
    with pytest.raises(ValueError, match="replay inputs are missing"):
        verify_source_projection(value)
