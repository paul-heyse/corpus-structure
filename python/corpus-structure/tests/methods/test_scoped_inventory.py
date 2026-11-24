"""Independent finite answers and complete-report parity for scoped analytical work."""

from collections import defaultdict
from contextlib import AbstractContextManager

import pytest

from corpus_structure.methods.scoped_inventory import ScopedInventory
from corpus_structure.methods.source_preparation import native_table_geometry
from corpus_structure.semantic.identity import canonical_bytes
from methods.inline_formula_support import _FROZEN_TEXT
from methods.m1_source_preparation_support import (
    native_table_source,
    projection,
    source,
    table_cell,
)
from methods.navigation_fixture import source_primary_products
from methods.scoped_relations_support import discover_relations


class ReferenceInventory(AbstractContextManager):
    """Small independent interpreter for the declared relational questions."""

    def __init__(self, pieces, selected_ranges, *, piece_schema=None):
        self.pieces = tuple(
            piece
            for piece in pieces
            if any(start <= piece["start"] < piece["end"] <= end for start, end in selected_ranges)
        )

    def __exit__(self, *exc):
        return None

    def table_targets(self, tables):
        return {pointer: native_table_geometry(table) for pointer, table in tables.items()}

    def containing_pieces(self, extents):
        answers = {}
        for start, end in extents:
            for piece in self.pieces:
                if (
                    piece.get("kind") == "native_text"
                    and piece["start"] <= start < end <= piece["end"]
                ):
                    answers[start, end] = piece
                    break
        return answers

    def contained_pairs(self, containers, members, *, overlap=False):
        answers = defaultdict(list)
        for outer, (a, b) in enumerate(containers):
            for inner, (c, d) in enumerate(members):
                if (a < d and c < b) if overlap else (a <= c < d <= b):
                    answers[outer].append(inner)
        return answers

    def unique_matches(self, mentions, captions):
        answers = []
        for mention, key in enumerate(mentions):
            matches = [i for i, other in enumerate(captions) if key == other]
            if len(matches) == 1:
                answers.append((mention, matches[0]))
        return answers

    def table_counterparts(self, tables, pairs):
        import re
        fields = ("start_row_offset_idx", "end_row_offset_idx", "start_col_offset_idx", "end_col_offset_idx")
        result = {}
        for pair in pairs:
            left, right = pair
            by_extent = {tuple(cell.get(name) for name in fields): (index, cell["text"].strip())
                for index, cell in enumerate(tables[right]["data"]["table_cells"])
                if all(type(cell.get(name)) is int for name in fields)}
            result[pair] = []
            for index, cell in enumerate(tables[left]["data"]["table_cells"]):
                counterpart = by_extent.get(tuple(cell.get(name) for name in fields))
                if counterpart is not None and re.fullmatch(r"\d+",cell.get("text", "").strip()):
                    result[pair].append((index, *counterpart))
        return result

    def formula_matches(self, questions, symbols):
        return {
            i: [j for j, (other, symbol) in enumerate(symbols) if formula == other and name == symbol["name"]]
            for i, (formula, name) in enumerate(questions)
        }

    def preceding_matches(self, questions, declarations):
        answers = {}
        for question in questions:
            matches = [
                row
                for row in declarations
                if row["passage"] == question["passage"]
                and row["parent"] == question["parent"]
                and row["symbol"] == question["symbol"]
                and row["piece"] < question["piece"]
            ]
            if len(matches) == 1 and matches[0]["record_count"] == 1:
                answers[question["ordinal"]] = matches[0]["ordinal"]
        return answers


def test_source_membership_and_first_piece_ties_have_independent_answers():
    pieces = (
        dict(kind="native_text", item_ref="first", start=0, end=8),
        dict(kind="native_text", item_ref="overlap", start=2, end=6),
        dict(kind="synthetic_separator", start=8, end=9),
        dict(kind="native_text", item_ref="excluded", start=9, end=12),
    )
    with ScopedInventory(pieces, ((0, 9), (1, 7))) as inventory:
        assert inventory.pieces == pieces[:3]
        assert inventory.containing_pieces(((2, 6), (0, 8), (4, 4), (8, 9), (9, 10))) == {
            (2, 6): pieces[0],
            (0, 8): pieces[0],
        }
        assert dict(inventory.contained_pairs(((0, 3), (3, 6)), ((0, 1), (3, 3), (2, 4)))) == {
            0: [0]
        }
        assert dict(
            inventory.contained_pairs(((0, 3), (3, 6)), ((2, 4), (6, 8)), overlap=True)
        ) == {0: [0], 1: [0]}


def test_caption_counts_and_predecessor_counts_preserve_ambiguity_and_occurrences():
    with ScopedInventory((), ()) as inventory:
        assert inventory.unique_matches(
            (("table", "1"), ("table", "2"), ("figure", "1"), ("table", "1")),
            (("table", "1"), ("table", "2"), ("table", "2"), ("figure", "1")),
        ) == [(0, 0), (2, 3), (3, 0)]
        declaration = dict(ordinal=0, passage=0, piece=0, parent="same", symbol="x", record_count=1)
        question = dict(declaration, ordinal=8, piece=2, record_count=0)
        assert inventory.preceding_matches((question,), (declaration,)) == {8: 0}
        assert inventory.preceding_matches((question,), (dict(declaration, record_count=2),)) == {}
        assert (
            inventory.preceding_matches((question,), (declaration, dict(declaration, ordinal=1)))
            == {}
        )
        assert inventory.preceding_matches((question,), (dict(declaration, passage=1),)) == {}


def test_empty_named_selection_does_not_inspect_unselected_source_pieces():
    from types import SimpleNamespace
    from typing import cast

    from corpus_structure.methods.witnessed_source_links import match_named_source_links
    from corpus_structure.semantic.constructions.navigation import NativeNavigationIndex

    missing = SimpleNamespace(payload={"pointer": "#/texts/unselected"})
    navigation = SimpleNamespace(
        complete=False,
        select=lambda kind: (missing,) if kind == "named_link" else (),
    )
    observed = match_named_source_links(
        "", (), {}, (), navigation=cast(NativeNavigationIndex, navigation)
    )
    assert observed.matches == () and observed.inspected_count == 0


def test_formal_inventory_is_prepared_once_and_keeps_equal_positions_from_two_products():
    from corpus_structure.methods.structural_roles import captured_formula_symbols
    from corpus_structure.semantic.data_product_reference import DataProductReference
    from corpus_structure.semantic.declared_formal_readings import prepare_formal_layers

    class CountingReport:
        reads = 0

        @property
        def payload(self):
            self.reads += 1
            return dict(
                occurrences=[
                    dict(
                        local_id="parent",
                        extents=[
                            dict(
                                projection="exact",
                                native_pointer="#/formula",
                                start=0,
                                end=1,
                                text="x",
                            )
                        ],
                    )
                ],
                annotations=[
                    dict(
                        local_id="input",
                        family="formal.math",
                        kind="formal.input",
                        formal_input=dict(
                            text="x",
                            representation="source_text",
                            parent_occurrence="parent",
                            syntax_outcome="complete",
                            symbol_outcome="complete",
                        ),
                    ),
                    dict(
                        local_id="symbol",
                        kind="formal.symbol",
                        formal=dict(
                            input_id="input",
                            start=0,
                            end=1,
                            normalized=dict(kind="identifier", value="x"),
                        ),
                    ),
                ],
            )

    first, second = CountingReport(), CountingReport()
    first_pin, second_pin = (
        DataProductReference("product:first"),
        DataProductReference("product:second"),
    )
    layers = prepare_formal_layers({first_pin: first})
    for _ in range(2):
        symbols, state = captured_formula_symbols(
            "x",
            primary_layers=layers,
            projection="exact",
            source_start=0,
            native_pointer="#/formula",
        )
        assert state == "parsed" and len(symbols) == 1
        assert symbols[0]["primary_node"]["product_id"] == "product:first"
    assert first.reads == 1
    both = prepare_formal_layers({first_pin: first, second_pin: second})
    assert captured_formula_symbols(
        "x",
        primary_layers=both,
        projection="exact",
        source_start=0,
        native_pointer="#/formula",
    ) == ((), "ambiguous")
    assert len(both.symbols) == 2 and second.reads == 1


@pytest.mark.parametrize("defect", ("nested", "crossing", "equal", "missing", "zero", "bool"))
def test_header_windows_match_the_independent_native_geometry_contract(defect):
    cells = [
        dict(table_cell("outer", 0, 1, column_header=True), end_col_offset_idx=4),
        dict(table_cell("inner", 1, 1, column_header=True), end_col_offset_idx=3),
        table_cell("row", 2, 0, row_header=True),
        table_cell("exact 123456789012345678901234567890.123456789", 2, 1),
    ]
    if defect == "crossing":
        cells[1]["start_row_offset_idx"] = 0
    elif defect == "equal":
        cells[1] = dict(cells[0])
    elif defect == "missing":
        cells[1].pop("end_col_offset_idx")
    elif defect == "zero":
        cells[1]["end_row_offset_idx"] = cells[1]["start_row_offset_idx"]
    elif defect == "bool":
        cells[1]["start_row_offset_idx"] = False
    table = dict(data=dict(table_cells=cells))
    with ScopedInventory((), ()) as inventory:
        assert inventory.table_targets({"first": table, "second": table}) == {
            "first": native_table_geometry(table),
            "second": native_table_geometry(table),
        }


@pytest.mark.parametrize("shape", ("table", "formulas", "unicode"))
def test_complete_report_bytes_match_independent_question_answers(monkeypatch, shape):
    from corpus_structure.methods import scoped_relations

    if shape == "table":
        frame = native_table_source(
            (
                table_cell("Probability %", 0, 1, column_header=True),
                table_cell("Heads", 1, 0, row_header=True),
                table_cell("50", 1, 1),
                table_cell("50", 2, 1),
            ),
            caption="Table 5.1 Coin",
            note="Only the Heads row uses percentages.",
        )
    elif shape == "formulas":
        frame = source("Let x be count.\nx+x=2", labels=("text", "formula"))
        frame = projection(
            frame.text,
            pieces=frame.pieces,
            items=tuple(dict(item, parent={"$ref": "#/groups/1"}) for item in frame.items),
        )
    else:
        frame = source(_FROZEN_TEXT.replace("µ", "μ"), labels=("text",))
    primary = source_primary_products(frame)
    actual = discover_relations(
        frame, primary=primary, source_work="actual-parent", inline_equations_enabled=True
    )
    monkeypatch.setattr(scoped_relations, "ScopedInventory", ReferenceInventory)
    expected = discover_relations(
        frame, primary=primary, source_work="actual-parent", inline_equations_enabled=True
    )
    assert canonical_bytes(actual) == canonical_bytes(expected)


@pytest.mark.provider_evidence
@pytest.mark.prerequisite("provider_book_panel")
def test_recorded_book_sections_keep_complete_report_bytes(monkeypatch, request):
    """Real retained HTML excerpts carry authored projection coordinates, without native admission."""
    import json
    from unittest.mock import patch

    from semantic.provider_book_panel_support import book_panel, panel_release

    from corpus_structure.methods import scoped_relations

    observations = []
    for section in book_panel(panel_release()):
        primary = source_primary_products(section.frame)
        actual = discover_relations(
            section.frame,
            primary=primary,
            source_work=section.path,
            inline_equations_enabled=True,
            witnessed_links_enabled=True,
        )
        with patch.object(scoped_relations, "ScopedInventory", ReferenceInventory):
            expected = discover_relations(
                section.frame,
                primary=primary,
                source_work=section.path,
                inline_equations_enabled=True,
                witnessed_links_enabled=True,
            )
        assert canonical_bytes(actual) == canonical_bytes(expected)
        observations.append(
            dict(
                path=section.path,
                original_digest=section.original_digest,
                selector=section.selector,
                contributions=len(actual["contributions"]),
            )
        )
    assert len(observations) == 4
    request.node.user_properties.append(
        ("scoped_real_book_parity", json.dumps(observations, sort_keys=True))
    )


def test_formula_join_keeps_repeated_symbols_and_product_occurrences():
    symbols = ((0, {"name": "x"}), (0, {"name": "x"}), (1, {"name": "x"}), (0, {"name": "y"}))
    with ScopedInventory((), ()) as inventory:
        assert dict(inventory.formula_matches(((0, "x"), (1, "x"), (0, "z")), symbols)) == {0: [0, 1], 1: [2]}


def test_ordered_witness_join_counts_cues_before_matching_declarations():
    questions = [dict(ordinal=0, parent="section", position=3, symbol="x", name="count", start=20)]
    declarations = [dict(ordinal=0, parent="section", position=0, symbol="x", name="count", cue=1, end=10)]
    with ScopedInventory((), ()) as inventory:
        assert inventory.ordered_matches(questions, declarations, [(1, "x")]) == [(0, 0)]
        assert inventory.ordered_matches(questions, declarations, [(1, "x"), (15, "x")]) == []
        assert inventory.ordered_matches(questions, [dict(declarations[0], parent="other")], [(1, "x")]) == []


def test_schematic_join_uses_the_last_equal_extent_and_observed_encounter_order():
    tables = {
        "observed": {"data": {"table_cells": [table_cell("2", 1, 1), table_cell("word", 2, 1)]}},
        "schematic": {"data": {"table_cells": [table_cell("old", 1, 1), table_cell("Sij", 1, 1)]}},
    }
    with ScopedInventory((), ()) as inventory:
        assert inventory.table_counterparts(tables, (("observed", "schematic"),)) == {("observed", "schematic"): [(0, 1, "Sij")]}
