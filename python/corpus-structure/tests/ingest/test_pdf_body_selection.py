"""A root-body source is a residual scope, not a fabricated organizational section."""

import json

import pytest
from docling_core.types.doc import (
    ContentLayer,
    DocItemLabel,
    DoclingDocument,
    GroupLabel,
    NodeItem,
    RichTableCell,
    TableCell,
    TableData,
)

from corpus_structure.ingest.pdf_hierarchy import native_nodes, snapshot
from corpus_structure.ingest.pdf_methods import PdfIngestConfig, _drafts, _select_sections
from corpus_structure.ingest.pdf_section_views import published_section_drafts
from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader
from corpus_structure.semantic.product_reference import ProductReference


def test_native_graph_default_projection_covers_body_prefix_once_and_named_selection_does_not():
    document = DoclingDocument(name="source")
    prefix = document.add_text(label=DocItemLabel.TEXT, text="unheaded prefix")
    section = document.add_group(label=GroupLabel.SECTION, name="Named")
    document.add_text(label=DocItemLabel.TEXT, text="section content", parent=section)
    nodes = native_nodes(document)
    native = snapshot(document)
    cfg = PdfIngestConfig(membership="descendants")
    scopes = _select_sections(nodes, cfg)
    assert scopes == ("#/body", section.self_ref)
    drafts = _drafts(
        1,
        ProductReference(1, "native", native.digest),
        native,
        dict(conversion="success"),
        scopes,
        cfg.membership,
        "consumer",
        document=document,
        node_index=nodes,
    )
    assert [(d.section_pointer, d.membership, d.text) for d in drafts] == [
        ("#/body", "direct", "unheaded prefix"),
        (section.self_ref, "descendants", "section content"),
    ]
    assert drafts[0].items == ("#/body", prefix.self_ref)
    assert _select_sections(nodes, cfg.model_copy(update=dict(sections=("Named",)))) == (
        section.self_ref,
    )


def test_no_heading_graph_can_project_original_body_directly():
    document = DoclingDocument(name="unheaded")
    document.add_text(label=DocItemLabel.TEXT, text="all original body")
    nodes = native_nodes(document)
    native = snapshot(document)
    cfg = PdfIngestConfig()
    assert _select_sections(nodes, cfg) == ("#/body",)
    (draft,) = _drafts(
        1,
        ProductReference(1, "native", native.digest),
        native,
        dict(conversion="success"),
        ("#/body",),
        "descendants",
        "consumer",
        document=document,
        node_index=nodes,
    )
    assert (
        draft.section_pointer == "#/body"
        and draft.membership == "direct"
        and draft.text == "all original body"
    )


@pytest.mark.parametrize(
    ("name", "membership", "expected_sections"),
    [
        ("Outer", "direct", ("Outer", "Inner")),
        ("Outer", "descendants", ("Outer",)),
        ("Inner", "descendants", ("Inner",)),
    ],
)
def test_live_and_retained_views_project_selected_table_captions(
    name, membership, expected_sections
):
    document = DoclingDocument(name="table caption selection")
    outer = document.add_group(label=GroupLabel.SECTION, name="Outer")
    table = document.add_table(data=TableData(num_rows=1, num_cols=3), parent=outer)
    rich = document.add_group(label=GroupLabel.INLINE, parent=table)
    lead = document.add_text(label=DocItemLabel.TEXT, text="For ", parent=rich)
    formula = document.add_text(label=DocItemLabel.FORMULA, text="x", parent=rich)
    first = document.add_text(
        label=DocItemLabel.CAPTION,
        text="Same \u03b1",
        orig="Different original spelling",
        parent=table,
    )
    second = document.add_text(label=DocItemLabel.CAPTION, text="Same \u03b1", parent=table)
    rich_caption = document.add_text(label=DocItemLabel.CAPTION, text="Cell label", parent=table)
    furniture = document.add_text(
        label=DocItemLabel.CAPTION,
        text="Outside the body layer",
        parent=table,
        content_layer=ContentLayer.FURNITURE,
    )
    table.data.table_cells = [
        RichTableCell(
            text="flattened fallback",
            ref=rich.get_ref(),
            start_row_offset_idx=0,
            end_row_offset_idx=1,
            start_col_offset_idx=0,
            end_col_offset_idx=1,
        ),
        RichTableCell(
            text="another flattened fallback",
            ref=rich_caption.get_ref(),
            start_row_offset_idx=0,
            end_row_offset_idx=1,
            start_col_offset_idx=1,
            end_col_offset_idx=2,
        ),
        TableCell(
            text="Cell value",
            start_row_offset_idx=0,
            end_row_offset_idx=1,
            start_col_offset_idx=2,
            end_col_offset_idx=3,
        ),
    ]
    prose = document.add_text(label=DocItemLabel.TEXT, text="After the table", parent=outer)
    ordinary = document.add_text(label=DocItemLabel.CAPTION, text="Ordinary position", parent=outer)
    inner = document.add_group(label=GroupLabel.SECTION, name="Inner", parent=outer)
    inner_table = document.add_table(data=TableData(num_rows=0, num_cols=0), parent=inner)
    nested = document.add_text(
        label=DocItemLabel.CAPTION, text="Nested caption", parent=inner_table
    )
    foreign_section = document.add_group(label=GroupLabel.SECTION, name="Foreign")
    foreign = document.add_text(
        label=DocItemLabel.CAPTION, text="Foreign caption", parent=foreign_section
    )
    table.captions = [
        item.get_ref()
        for item in (ordinary, second, first, second, rich_caption, furniture, nested, foreign)
    ]
    native = snapshot(document)
    nodes = native_nodes(document)
    reference = ProductReference(42, "organized", native.digest)

    outer_members = (
        outer,
        table,
        rich,
        lead,
        formula,
        first,
        second,
        rich_caption,
        prose,
        ordinary,
    )
    inner_members = (inner, inner_table, nested)

    class ArchivedSelection(PublishedPdfReader):
        def __init__(self):
            self.reference = reference
            self.frontiers = []

        def sections(self, *, after=None, section_pointer=None, membership="direct", limit=None):
            assert (after, section_pointer, membership, limit) == (None, None, "direct", None)
            return [
                dict(pointer=outer.self_ref, name="Outer", ancestors=["#/body"]),
                dict(pointer=inner.self_ref, name="Inner", ancestors=["#/body", outer.self_ref]),
                dict(pointer=foreign_section.self_ref, name="Foreign", ancestors=["#/body"]),
            ]

        def section_nodes(self, section, membership):
            ancestors: tuple[NodeItem, ...]
            members: tuple[NodeItem, ...]
            if section == inner.self_ref:
                ancestors, members = (outer,), inner_members
            else:
                assert section == outer.self_ref
                ancestors, members = (), outer_members
                if membership == "descendants":
                    members = (*outer_members, *inner_members)
            return [
                dict(
                    pointer=item.self_ref,
                    role=role,
                    native_json=item.model_dump(mode="json", by_alias=True),
                )
                for role, items in (("selected", members), ("ancestor", ancestors))
                for item in items
            ]

        def selected_native_items(self, pointers):
            self.frontiers.append(pointers)
            assert pointers == (furniture.self_ref,)
            return {furniture.self_ref: furniture.model_dump(mode="json", by_alias=True)}

        def iter_companions(self, family):
            assert family == "health"
            yield dict(source_scope="whole_document", conversion="success")

        def has_native_metadata(self, kind):
            assert kind == "recognition_coverage"
            return False

        def section_reports(self, pointers, sections):
            return []

    selected = PdfIngestConfig(sections=(name,), membership=membership)
    scopes = _select_sections(nodes, selected)
    live = _drafts(
        1,
        reference,
        native,
        dict(conversion="success"),
        scopes,
        selected.membership,
        "consumer",
        document=document,
        node_index=nodes,
    )
    reader = ArchivedSelection()
    archived = published_section_drafts(
        reader,
        document_id=1,
        selections=selected.sections,
        membership=selected.membership,
        scope=None,
        consumer_release="consumer",
    )
    assert live == archived
    assert reader.frontiers == ([(furniture.self_ref,)] if name == "Outer" else [])
    assert tuple(nodes[draft.section_pointer].name for draft in live) == expected_sections

    outer_pieces = [
        (lead, "For ", "text", 0),
        (formula, "x", "text", 0),
        (rich_caption, "Cell label", "text", 1),
        (table, "Cell value", "cell_text", 2),
        (first, "Same \u03b1", "text", None),
        (second, "Same \u03b1", "text", None),
        (prose, "After the table", "text", None),
        (ordinary, "Ordinary position", "text", None),
    ]
    inner_piece = (nested, "Nested caption", "text", None)
    outer_text = (
        "For x\nCell label\nCell value\nSame \u03b1\nSame \u03b1"
        "\nAfter the table\nOrdinary position"
    )
    for draft in live:
        assert json.loads(draft.recipe_bytes) == dict(
            recipe="native-section-text-v8",
            content_layers=["body"],
            analysis_eligible=True,
            organization_owner=reference.values(),
        )
        if draft.section_pointer == inner.self_ref:
            expected, expected_text = [inner_piece], "Nested caption"
        elif membership == "descendants":
            expected, expected_text = [*outer_pieces, inner_piece], outer_text + "\nNested caption"
        else:
            expected, expected_text = outer_pieces, outer_text
        assert draft.text == expected_text

        actual = []
        for piece in draft.pieces:
            start, end = piece["start"], piece["end"]
            assert isinstance(start, int) and isinstance(end, int)
            spelling = draft.text[start:end]
            if piece["kind"] == "synthetic_separator":
                assert spelling == "\n"
            else:
                assert piece["kind"] == "native_text"
                actual.append(
                    (piece["item_ref"], spelling, piece["source_field"], piece.get("cell_index"))
                )
        assert actual == [
            (item.self_ref, spelling, field, index) for item, spelling, field, index in expected
        ]
