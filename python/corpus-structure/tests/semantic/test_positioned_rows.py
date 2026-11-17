"""Ordered source joins preserve independently stated interval and output semantics."""

from corpus_structure.semantic.construction_products import _clip_sentence_regions
from corpus_structure.semantic.constructions.retained_rules import SourceLayoutIndex
from corpus_structure.semantic.positioned_rows import PositionedRows


def test_positioned_rows_keep_overlaps_containment_and_original_order():
    rows = ((8, 12, "last"), (0, 20, "outer"), (3, 6, "first"), (6, 8, "touching"))
    index = PositionedRows.build(rows, lambda row: row[:2])
    assert tuple(row[2] for row in index.containing(4, 5)) == ("outer", "first")
    assert tuple(row[2] for row in index.overlapping(5, 8)) == ("outer", "first", "touching")
    assert tuple(row[2] for row in index.overlapping(8, 9)) == ("last", "outer")
    assert index.containing(19, 21) == ()
    assert tuple(row[2] for row in index.contained(3, 12)) == ("last", "first", "touching")


def test_sentence_sweep_restores_region_and_retained_sentence_order():
    regions = ((5, 12), (0, 7), (3, 3), (12, 14))
    boundaries = ({"start": 7, "end": 12}, {"start": 0, "end": 7}, {"start": 12, "end": 15})
    assert _clip_sentence_regions(regions, boundaries) == [(7, 12), (5, 7), (0, 7), (12, 14)]


def test_layout_index_uses_nearest_preceding_heading_of_exact_parent():
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
    first, second = index.preceding(14), index.preceding(32)
    assert first is not None and first["item_ref"] == "example"
    assert second is not None and second["item_ref"] == "instruction"
    assert index.preceding(0) is None


def test_navigation_fragments_keep_role_order_and_refuse_repeated_role_identity():
    import pytest

    from corpus_structure.semantic.constructions.navigation import NavigationRecord

    occurrences = {
        "late": {"extents": [{"start": 4, "end": 7, "text": "two"}]},
        "early": {"extents": [{"start": 0, "end": 3, "text": "one"}]},
    }
    record = NavigationRecord(
        None, {"roles": [{"role": "name", "occurrences": ["late", "early"]}]}, occurrences
    )
    assert record.text("name") == "twoone" and record.span("name") == (0, 7)
    assert record.fragments("absent") == ()
    repeated = NavigationRecord(
        None,
        {"roles": [{"role": "name", "occurrences": []}, {"role": "name", "occurrences": []}]},
        occurrences,
    )
    with pytest.raises(ValueError, match="role identity repeats"):
        repeated.fragments("name")
