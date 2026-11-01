"""Bulk deletion checked against public deletion and independent pointer meanings."""

from __future__ import annotations

import pytest
from docling_core.types.doc.document import (
    BoundingBox,
    CoordOrigin,
    DocItemLabel,
    DoclingDocument,
    FineRef,
    GraphCell,
    GraphCellLabel,
    GraphData,
    GroupLabel,
    KeyValueItem,
    Orientation,
    ProvenanceItem,
    RefItem,
    RichTableCell,
    Size,
    TableData,
)

from corpus_structure.ingest.pdf_bulk_remove import remove_pdf_subtrees


def mixed_document():
    doc = DoclingDocument(name="typed bulk deletion")
    doc.add_page(page_no=1, size=Size(width=200, height=300))
    doc.add_page(page_no=2, size=Size(width=300, height=200))
    drop = doc.add_text(label=DocItemLabel.TEXT, text="delete")
    listing = doc.add_list_group(name="delete subtree")
    doc.add_list_item(text="first", parent=listing)
    second = doc.add_list_item(text="second", parent=listing)
    doc.add_text(label=DocItemLabel.TEXT, text="nested", parent=second)
    caption = doc.add_text(label=DocItemLabel.CAPTION, text="caption")
    footnote = doc.add_text(label=DocItemLabel.FOOTNOTE, text="footnote")
    keep = doc.add_text(label=DocItemLabel.TEXT, text="literal #/texts/0 stays text")
    drop_table = doc.add_table(data=TableData(num_rows=0, num_cols=0))
    table = doc.add_table(data=TableData(num_rows=1, num_cols=1, orientation=Orientation.ROT_90))
    cell_root = doc.add_group(label=GroupLabel.INLINE, parent=table)
    cell_text = doc.add_text(label=DocItemLabel.TEXT, text="rich", parent=cell_root)
    table.data.table_cells = [
        RichTableCell(
            text="rich",
            ref=cell_root.get_ref(),
            start_row_offset_idx=0,
            end_row_offset_idx=1,
            start_col_offset_idx=0,
            end_col_offset_idx=1,
        )
    ]
    table.prov = [
        ProvenanceItem(
            page_no=2,
            charspan=(0, 4),
            bbox=BoundingBox(
                l=1,
                t=2,
                r=20,
                b=30,
                coord_origin=CoordOrigin.TOPLEFT,
            ),
        )
    ]
    table.captions = [caption.get_ref(), drop.get_ref(), caption.get_ref()]
    table.references = [keep.get_ref(), drop.get_ref()]
    table.footnotes = [footnote.get_ref(), drop.get_ref()]
    table.comments = [FineRef(cref=keep.self_ref, range=(2, 5))]
    graph = KeyValueItem(
        self_ref="#/key_value_items/0",
        graph=GraphData(
            cells=[
                GraphCell(
                    label=GraphCellLabel.KEY, cell_id=1, text="a", orig="a", item_ref=drop.get_ref()
                ),
                GraphCell(
                    label=GraphCellLabel.VALUE,
                    cell_id=2,
                    text="b",
                    orig="b",
                    item_ref=keep.get_ref(),
                ),
            ]
        ),
    )
    doc.append_child_item(child=graph)
    picture = doc.add_picture(caption=caption)
    doc.validate_tree(doc.body, raise_on_error=True)
    return doc, {
        "drop": drop,
        "listing": listing,
        "caption": caption,
        "footnote": footnote,
        "keep": keep,
        "drop_table": drop_table,
        "table": table,
        "cell_root": cell_root,
        "cell_text": cell_text,
        "graph": graph,
        "picture": picture,
    }


@pytest.mark.parametrize(
    "names", [(), ("drop",), ("listing",), ("drop", "listing", "drop_table"), ("table", "picture")]
)
def test_matches_public_delete_for_mixed_containment_and_typed_edges(names):
    doc, items = mixed_document()
    public = doc.model_copy(deep=True)
    public.delete_items(
        node_items=[RefItem(cref=items[name].self_ref).resolve(public) for name in names]
    )
    remove_pdf_subtrees(doc, [items[name] for name in names])
    assert doc.model_dump(mode="json", by_alias=True) == public.model_dump(
        mode="json", by_alias=True
    )
    assert doc.validate_tree(doc.body, raise_on_error=True)


def test_known_ranks_relationships_pages_rotation_and_surviving_identity():
    doc, items = mixed_document()
    pages = doc.pages
    table = items["table"]
    cell = table.data.table_cells[0]
    assert isinstance(cell, RichTableCell)
    comment = table.comments[0]
    # A repeated, shared typed edge is rebased once, not successively twice.
    shared = items["keep"].get_ref()
    table.references = [shared, shared, items["drop"].get_ref()]
    remove_pdf_subtrees(doc, [items["drop"], items["listing"], items["drop_table"]])
    assert [node.text for node in doc.texts] == [
        "caption",
        "footnote",
        "literal #/texts/0 stays text",
        "rich",
    ]
    assert doc.tables[0] is table and table.self_ref == "#/tables/0"
    assert doc.texts[2] is items["keep"] and doc.texts[3] is items["cell_text"]
    assert table.data.table_cells[0] is cell and cell.ref.cref == "#/groups/0"
    assert cell.ref.resolve(doc) is items["cell_root"]
    assert items["cell_root"].parent is not None
    assert items["cell_root"].parent.cref == "#/tables/0"
    assert [ref.cref for ref in table.captions] == ["#/texts/0", "#/texts/0"]
    assert [ref.cref for ref in table.footnotes] == ["#/texts/1"]
    assert table.references == [RefItem(cref="#/texts/2"), RefItem(cref="#/texts/2")]
    assert table.references[0] is shared and table.references[1] is shared
    assert table.comments[0] is comment and (comment.cref, comment.range) == ("#/texts/2", (2, 5))
    assert items["graph"].graph.cells[0].item_ref is None
    retained_graph_ref = items["graph"].graph.cells[1].item_ref
    assert retained_graph_ref is not None and retained_graph_ref.resolve(doc) is items["keep"]
    assert doc.pages is pages and pages[2].size.as_tuple() == (300, 200)
    assert table.data.orientation == Orientation.ROT_90
    assert table.prov[0].model_dump() == {
        "page_no": 2,
        "charspan": (0, 4),
        "bbox": {"l": 1.0, "t": 2.0, "r": 20.0, "b": 30.0, "coord_origin": CoordOrigin.TOPLEFT},
    }


def test_removed_descendant_crossrefs_are_removed_instead_of_rebound_to_neighbor():
    doc, items = mixed_document()
    descendant = doc.texts[2]
    items["picture"].footnotes = [descendant.get_ref()]
    items["picture"].comments = [FineRef(cref=descendant.self_ref, range=(0, 1))]
    remove_pdf_subtrees(doc, [items["listing"]])
    assert items["picture"].footnotes == []
    assert items["picture"].comments == []
    assert [node.text for node in doc.texts][:2] == ["delete", "caption"]


def test_required_rich_cell_target_refuses_before_any_mutation():
    doc, items = mixed_document()
    before = doc.model_dump(mode="json", by_alias=True)
    with pytest.raises(
        ValueError, match=r"unsupported scalar reference .*\.ref -> removed #/groups/1"
    ):
        remove_pdf_subtrees(doc, [items["drop"], items["cell_root"]])
    assert doc.model_dump(mode="json", by_alias=True) == before


def test_surviving_orphan_parent_refuses_instead_of_inventing_parent():
    doc, items = mixed_document()
    # An invalid orphan is intentionally not included in the parent's children.
    orphan = items["keep"]
    doc.body.children = [ref for ref in doc.body.children if ref.cref != orphan.self_ref]
    orphan.parent = items["listing"].get_ref()
    before = doc.model_dump(mode="json", by_alias=True)
    with pytest.raises(
        ValueError, match=r"unsupported scalar reference .*\.parent -> removed #/groups/0"
    ):
        remove_pdf_subtrees(doc, [items["listing"]])
    assert doc.model_dump(mode="json", by_alias=True) == before
