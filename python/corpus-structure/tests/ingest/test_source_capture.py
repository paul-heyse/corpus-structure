"""Native Docling occurrence projections replace HTML lexical source capture."""

from docling_core.types.doc import DocItemLabel, DoclingDocument

from corpus_structure.ingest.pdf_hierarchy import (
    SectionPolicy,
    load_snapshot,
    organize,
    project_section,
    snapshot,
)


def test_native_item_identity_and_unicode_offsets_survive_section_projection():
    native = DoclingDocument(name="native Unicode occurrence fixture")
    native.add_heading(text="1.1: Sets", level=1)
    item = native.add_text(label=DocItemLabel.TEXT, text="Same \u03b1. Same \u03b1.")
    raw = snapshot(native)
    organized = organize(raw, SectionPolicy("fixture"))
    section = organized.sections[0].group_ref
    projected = project_section(
        load_snapshot(organized.document),
        organized.document.digest,
        section,
        "direct",
        section_refs=frozenset([section]),
    )
    piece = next(p for p in projected.pieces if p.item_ref == item.self_ref)
    assert projected.text[piece.start : piece.end] == "Same \u03b1. Same \u03b1."
    assert raw.payload == snapshot(native).payload


def test_chart_title_and_actual_cells_project_once_with_distinct_source_handles():
    from docling_core.types.doc import (
        GroupLabel,
        PictureMeta,
        TableCell,
        TableData,
        TabularChartMetaField,
    )

    from corpus_structure.core.method import SourceViewRef
    from corpus_structure.semantic.product_reference import ProductReference
    from corpus_structure.semantic.proposals import native_evidence_entries, native_source_frame
    from corpus_structure.semantic.source_views import PreparedSourceView

    document = DoclingDocument(name="Chart fixture")
    section = document.add_group(label=GroupLabel.SECTION, name="Chart section")
    picture = document.add_picture(parent=section)
    picture.meta = PictureMeta(
        tabular_chart=TabularChartMetaField(
            title="Measured output",
            chart_data=TableData(
                num_rows=2,
                num_cols=2,
                table_cells=[
                    TableCell(
                        text="Output",
                        start_row_offset_idx=0,
                        end_row_offset_idx=1,
                        start_col_offset_idx=0,
                        end_col_offset_idx=2,
                        col_span=2,
                        column_header=True,
                    ),
                    TableCell(
                        text="3",
                        start_row_offset_idx=1,
                        end_row_offset_idx=2,
                        start_col_offset_idx=0,
                        end_col_offset_idx=1,
                    ),
                    TableCell(
                        text="3",
                        start_row_offset_idx=1,
                        end_row_offset_idx=2,
                        start_col_offset_idx=1,
                        end_col_offset_idx=2,
                    ),
                ],
            ),
        )
    )
    projection = project_section(
        document, "a" * 64, section.self_ref, "direct", section_refs=frozenset({section.self_ref})
    )
    assert projection.text == "Measured output\nOutput\n3\n3"
    native_pieces = [piece for piece in projection.pieces if piece.kind == "native_text"]
    assert [(piece.source_field, piece.cell_index) for piece in native_pieces] == [
        ("chart_title", None),
        ("chart_cell_text", 0),
        ("chart_cell_text", 1),
        ("chart_cell_text", 2),
    ]
    assert all(piece.item_ref == picture.self_ref for piece in native_pieces)
    view = PreparedSourceView(
        SourceViewRef(
            1,
            "chart",
            1,
            ProductReference(1, "integrated", "a" * 64),
            section.self_ref,
            "direct",
            "b" * 64,
            "c" * 64,
        ),
        projection.text,
        tuple(piece.to_wire() for piece in projection.pieces),
        (picture.model_dump(mode="json", by_alias=True),),
        (),
        {},
    )
    entries = native_evidence_entries(native_source_frame(view, []))
    assert [entry.get("cell_index") for entry in entries] == [None, 0, 1, 2]
    assert [entry["text"] for entry in entries] == ["Measured output", "Output", "3", "3"]
    assert len({entry["handle"] for entry in entries}) == 4
    assert all(entry["pointer"] == picture.self_ref for entry in entries)
