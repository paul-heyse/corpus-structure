"""Ordered source joins preserve independently stated interval and output semantics."""

from types import SimpleNamespace

from corpus_structure.semantic.construction_products import _clip_sentence_regions
from corpus_structure.semantic.constructions.retained_rules import SourceLayoutIndex, source_layout
from corpus_structure.semantic.positioned_rows import PositionedRows


def test_positioned_rows_keep_overlaps_containment_and_original_order():
    rows = ((8, 12, "last"), (0, 20, "outer"), (3, 6, "first"), (6, 8, "touching"))
    index = PositionedRows.build(rows, lambda row: row[:2])
    assert tuple(row[2] for row in index.containing(4, 5)) == ("outer", "first")
    assert tuple(row[2] for row in index.overlapping(5, 8)) == ("outer", "first", "touching")
    assert tuple(row[2] for row in index.overlapping(8, 9)) == ("last", "outer")
    assert index.containing(19, 21) == ()


def test_sentence_sweep_restores_region_and_retained_sentence_order():
    regions = ((5, 12), (0, 7), (3, 3), (12, 14))
    boundaries = ({"start": 7, "end": 12}, {"start": 0, "end": 7}, {"start": 12, "end": 15})
    assert _clip_sentence_regions(regions, boundaries) == [(7, 12), (5, 7), (0, 7), (12, 14)]


def test_layout_index_uses_nearest_preceding_heading_of_exact_parent():
    text = "Example\nPolicy\nbody\nInstructions\nnext"
    pieces = (
        {"start": 0, "end": 7, "item_ref": "example"},
        {"start": 7, "end": 8, "kind": "synthetic_separator"},
        {"start": 8, "end": 14, "item_ref": "policy"},
        {"start": 14, "end": 19, "item_ref": "body"},
        {"start": 19, "end": 32, "item_ref": "instruction"},
        {"start": 32, "end": 36, "item_ref": "next"},
    )
    items = {
        "example": {"parent": "local", "label": "section_header"},
        "policy": {"parent": "other", "label": "section_header"},
        "body": {"parent": "local", "label": "text"},
        "instruction": {"parent": "local", "label": "section_header"},
        "next": {"parent": "local", "label": "text"},
    }
    index = SourceLayoutIndex(pieces, items)
    product = SimpleNamespace(block_start=14, source=SimpleNamespace(projection_digest="projection"))
    layout, heading = source_layout(product, text, pieces, items, with_context=True, index=index)
    assert layout == "example" and heading["native_pointer"] == "example"
    product.block_start = 32
    _layout, heading = source_layout(product, text, pieces, items, with_context=True, index=index)
    assert heading["native_pointer"] == "instruction"
