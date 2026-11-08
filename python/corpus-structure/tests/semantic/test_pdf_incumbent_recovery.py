"""Scoped native recovery keeps the existing selected occurrences and exact witnesses."""

import pytest
from docling_core.types.doc import (
    BoundingBox,
    DocItemLabel,
    DoclingDocument,
    PictureMeta,
    Size,
    TableCell,
    TableData,
)

from corpus_structure.ingest.pdf_hierarchy import native_nodes
from corpus_structure.ingest.pdf_incumbent_recovery import RecoveryEvidence, source_provenance
from corpus_structure.ingest.pdf_reconciliation import (
    _iter_selected_occurrences,
    _Origin,
    _repair_incumbent_source,
    _validate_native,
)


@pytest.mark.parametrize("qualified_panels", [True, False])
def test_source_recovery_keeps_one_caption_and_only_adds_the_witnessed_table(qualified_panels):
    document = DoclingDocument(name="Scoped native recovery")
    for page in (108, 151, 301):
        document.add_page(page, Size(width=600, height=800))

    def box(left, top, right, bottom):
        return BoundingBox(l=left, t=top, r=right, b=bottom)

    def data(text, cell_box=None):
        cell = TableCell(
            text=text,
            bbox=cell_box,
            row_span=1,
            col_span=1,
            start_row_offset_idx=0,
            end_row_offset_idx=1,
            start_col_offset_idx=0,
            end_col_offset_idx=1,
        )
        return TableData(num_rows=1, num_cols=1, table_cells=[cell])

    upper, lower = box(30, 40, 90, 80), box(30, 100, 90, 140)
    combined = box(29, 39, 91, 141)
    for literal in ("p = .5", "p = .3" if qualified_panels else "unresolved"):
        picture = document.add_picture(prov=source_provenance(combined, 108))
        picture.meta = PictureMeta.model_validate(
            {"tabular_chart": {"title": literal, "chart_data": data("chart")}}
        )
    existing = document.add_table(
        data("existing"), prov=source_provenance(box(20, 20, 60, 70), 151)
    )
    existing_caption = document.add_text(
        DocItemLabel.CAPTION,
        "Table 4.2: Joint distribution.",
        prov=source_provenance(box(22, 190, 62, 200), 151),
    )
    for title in ("Figure 11.", "Figure 12."):
        caption = document.add_text(DocItemLabel.CAPTION, title)
        document.add_picture(caption=caption, prov=source_provenance(combined, 301))
    p301_caption_refs = [picture.captions.copy() for picture in document.pictures[2:]]
    origins = {id(node): _Origin(0, ref) for ref, node in native_nodes(document).items()}
    witnesses = RecoveryEvidence(
        box(35, 150, 85, 160),
        (upper, lower),
        box(22, 190, 62, 200),
        box(20, 110, 70, 180),
        data("40/60", box(43, 135, 61, 143)),
    )
    reports = []
    _repair_incumbent_source(
        document,
        origins,
        witnesses,
        {
            "figure": (0, "#/texts/37"),
            "figure_recognition": (1, "block-1"),
            "table": (2, "block-4"),
        },
        reports,
    )
    _validate_native(document)

    figure_caption = next(
        node for node in document.texts if node.text == "Figure 3.5: Binomial distributions."
    )
    caption_ref = figure_caption.get_ref()
    assert document.body.children.count(caption_ref) == 1
    if qualified_panels:
        assert [p.captions for p in document.pictures[:2]] == [[caption_ref], [caption_ref]]
        assert [p.prov[0].bbox for p in document.pictures[:2]] == [upper, lower]
        assert not reports
    else:
        assert [p.captions for p in document.pictures[:2]] == [[], []]
        assert [p.prov[0].bbox for p in document.pictures[:2]] == [combined, combined]
        assert reports == [
            {
                "input_index": 1,
                "occurrence_id": "block-1",
                "outcome": "unresolved",
                "reason": "independent_figure_panels_lack_selected_occurrences",
            }
        ]
    assert [p.captions for p in document.pictures[2:]] == p301_caption_refs
    assert document.tables[0] is existing and existing.data.table_cells[0].text == "existing"
    table = document.tables[1]
    assert table.captions == [existing_caption.get_ref()]
    assert document.body.children.index(table.get_ref()) + 1 == document.body.children.index(
        existing_caption.get_ref()
    )
    selected_cell = next(
        row
        for row in _iter_selected_occurrences(document, origins)
        if row["occurrence_id"] == f"{table.self_ref}/data/table_cells/0"
    )
    assert selected_cell["precision"] == "cell"
    assert selected_cell["page_no"] == 151
    assert selected_cell["region"]["left"] == 43
    assert selected_cell["region"]["bottom"] == 143
