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


def test_downstream_enclosure_and_rich_cell_reuse_the_selected_formula_field():
    from types import SimpleNamespace

    from corpus_structure.ingest.pdf_hierarchy import retained_formula_originals
    from corpus_structure.methods.source_preparation import (
        _primary_formula_enclosure,
        native_table_cell_projection,
    )

    enclosing, formula = "#/texts/0", "#/texts/1"
    nodes = {
        enclosing: dict(
            self_ref=enclosing,
            label="text",
            text="Before",
            children=[{"$ref": formula}],
        ),
        formula: dict(
            self_ref=formula,
            label="formula",
            text="r",
            orig="x+y",
            parent={"$ref": enclosing},
        ),
    }
    before = dict(item_ref=enclosing, kind="native_text", source_field="text", start=0, end=6)
    display = dict(item_ref=formula, kind="native_text", source_field="orig", start=7, end=10)
    view = SimpleNamespace(text="Before\nx+y", pieces=(before, display))
    selected = retained_formula_originals(view.pieces)
    selection = SimpleNamespace(region=formula, start=7, end=10)
    result = _primary_formula_enclosure(
        view, nodes, selection, {enclosing: [before], formula: [display]}, selected
    )
    assert result is not None
    assert result[:2] == (enclosing, (0, 10))

    table = dict(self_ref="#/tables/0", data=dict(table_cells=[{"ref": {"$ref": enclosing}}]))
    cell = native_table_cell_projection(table, 0, nodes, retained_originals=selected)
    assert cell.text == "Before\nx+y"
    assert cell.pieces[-1].source_field == "orig"
    assert cell.pieces[-1].cell_index == 0
