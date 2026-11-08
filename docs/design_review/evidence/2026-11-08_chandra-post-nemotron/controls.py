"""Run bounded Docling Chandra parser and consumer controls on authored HTML."""

from __future__ import annotations

import argparse
import json
import logging
from importlib.metadata import version
from pathlib import Path
from types import SimpleNamespace

from docling.utils.chandra_utils import parse_chandra_html
from docling.utils.vlm_utils import normalize_section_header_levels
from docling_core.transforms.chunker.hierarchical_chunker import (
    ChunkingDocSerializer,
    ChunkingSerializerProvider,
    HierarchicalChunker,
)
from docling_core.transforms.serializer.markdown import MarkdownParams
from docling_core.types.doc import DoclingDocument, Size

from corpus_structure.ingest.pdf_recognition import crop_transform, render_affine, transform_point

SIZE = Size(width=600, height=800)


def parse(content, page=1, *, normalize=False):
    return parse_chandra_html(content, SIZE, page, normalize_heading_levels=normalize)


def block(label, content, bbox="100 200 800 300"):
    return f'<div data-label="{label}" data-bbox="{bbox}">{content}</div>'


def text_items(doc):
    return [(item.label.value, item.text, len(item.prov)) for item in doc.texts]


def layout():
    raw = block(
        "Text",
        "<p>Read <strong>this</strong> and <math>x^{2}</math> then <code>run</code> now."
        "<br>Next line.</p>",
    )
    doc = parse(raw)
    first = doc.texts[0].prov[0]
    bbox = first.bbox
    assert (bbox.l, bbox.t, bbox.r, bbox.b) == (60, 160, 480, 240)
    assert bbox.coord_origin.value == "TOPLEFT"
    assert sum(bool(item.prov) for item in doc.texts) == 1
    assert [item.text for item in doc.texts if item.label.value == "formula"] == ["x^{2}"]
    assert [item.text for item in doc.texts if item.label.value == "code"] == ["run"]

    def geometry(document):
        return [(item.text, len(item.prov)) for item in document.texts]

    malformed = geometry(parse(block("Text", "<p>Malformed box</p>", bbox="a b")))
    inverted = geometry(parse(block("Text", "<p>Inverted box</p>", bbox="800 700 100 200")))
    bare = geometry(parse("<p>Unlocated markup</p>"))
    missing = geometry(parse('<div data-label="Text"><p>Missing box</p></div>'))
    assert malformed == [("Malformed box", 0)]
    assert inverted == [("Inverted box", 0)]
    assert bare == [("Unlocated markup", 0)]
    assert missing == [("Missing box", 0)]
    errors = {}
    for name, value in {
        "plain_prose": "Just prose without any HTML",
        "json": '{"text":"Not Chandra HTML"}',
        "empty_script": "<script>alert(1)</script>",
        "label_without_content": block("Text", ""),
    }.items():
        try:
            parse(value)
        except ValueError as exc:
            errors[name] = str(exc)
        else:
            raise AssertionError(f"{name} unexpectedly parsed")
    for blank in (parse(block("Blank-Page", "")), parse("")):
        assert not (blank.texts or blank.tables or blank.pictures)
    return {
        "raw_inline_case": raw,
        "inline_runs": text_items(doc),
        "markdown": doc.export_to_markdown(),
        "box_in_top_left_points": [bbox.l, bbox.t, bbox.r, bbox.b],
        "first_run_charspan": first.charspan,
        "malformed_box": malformed,
        "inverted_box": inverted,
        "missing_box": missing,
        "bare_markup": bare,
        "value_errors": errors,
        "explicit_blank_and_empty_input": "both parse as pages with no document items",
    }


def table():
    source = (
        '<table><caption>Inside table</caption><thead><tr><th colspan="2">Both</th></tr>'
        "<tr><th>Region</th><th>Value</th></tr></thead><tbody>"
        '<tr><th rowspan="0" scope="row">East</th><td><p>m<sup>2</sup></p>'
        "<p><strong>Estimated</strong></p></td></tr><tr><td>43</td></tr></tbody></table>"
    )
    doc = parse(block("Table", source))
    grid = doc.tables[0]
    assert (grid.data.num_rows, grid.data.num_cols) == (4, 2)
    assert len(grid.captions) == 1 and grid.captions[0].resolve(doc).text == "Inside table"
    cells = grid.data.table_cells
    assert cells[0].col_span == 2 and cells[0].column_header
    assert cells[3].row_span == 2 and cells[3].row_header
    assert type(cells[4]).__name__ == "RichTableCell" and cells[4].ref.resolve(doc).children
    exponent = next(item for item in doc.texts if item.text == "2")
    assert exponent.formatting.script.value == "super"

    overflow_source = '<table><tr><td colspan="1001">lost cell</td></tr></table>'
    overflow = parse(block("Table", overflow_source) + block("Text", "<p>neighbor</p>"))
    assert len(overflow.tables) == 1 and not overflow.tables[0].data.table_cells
    assert [item.text for item in overflow.texts] == ["neighbor"]
    threshold_source = '<table><tr><td colspan="1000">valid cell</td></tr></table>'
    threshold = parse(block("Table", threshold_source))
    assert threshold.tables[0].data.num_cols == 1000
    empty_source = "<table><caption>Empty fallback caption</caption></table>"
    empty = parse(block("Table", empty_source))
    assert not empty.tables and empty.texts[0].text == "Empty fallback caption"

    page_one = parse(block("Table", "<table><tr><td>First part</td></tr></table>"))
    page_two = parse(block("Table", "<table><tr><td>Second part</td></tr></table>"), 2)
    separate = DoclingDocument.concatenate([page_one, page_two])
    assert [item.prov[0].page_no for item in separate.tables] == [1, 2]
    oversized_data = overflow.tables[0].data
    return {
        "rich_table_html": source,
        "table_cells": [cell.model_dump(mode="json") for cell in cells],
        "rich_exponent_formatting": exponent.formatting.model_dump(mode="json"),
        "rendered_table_markdown": doc.export_to_markdown(),
        "threshold_cell_columns": 1000,
        "oversize_cell_columns": 1001,
        "oversize_table_shape": [oversized_data.num_rows, oversized_data.num_cols],
        "oversize_surviving_texts": text_items(overflow),
        "empty_table_fallback_texts": text_items(empty),
        "continuation_remains_separate_on_pages": [
            item.prov[0].page_no for item in separate.tables
        ],
    }


def rotated_crop():
    media = [10, 20, 610, 820]
    cropbox = [60, 120, 560, 720]
    clipped_pixels = [100, 200, 300, 500]
    frame = render_affine(media=media, crop=cropbox, rotation=90, width=1200, height=1000)
    cropped_frame = crop_transform(frame, clipped_pixels)
    doc = parse_chandra_html(
        block("Text", "Crop-local text", bbox="100 200 500 600"),
        Size(width=200, height=300),
        7,
    )
    box = doc.texts[0].prov[0].bbox
    # The 2 px/pt clockwise page rotation and crop origin give x' = 1300 - 2y,
    # y' = 2x - 300. Compute corresponding PDF points independently.
    expected = [(180, 640), (240, 600)]
    mapped = [transform_point(cropped_frame["affine"], *point) for point in expected]
    assert mapped == [(box.l, box.t), (box.r, box.b)] == [(20, 60), (100, 180)]
    return {
        "media_box_absolute_bottom_left": media,
        "crop_box_absolute_bottom_left": cropbox,
        "render_size_pixels": [1200, 1000],
        "rotation_clockwise": 90,
        "clipped_pixel_extent": clipped_pixels,
        "crop_local_normalized_box": [100, 200, 500, 600],
        "crop_local_pixel_box": [box.l, box.t, box.r, box.b],
        "media_relative_top_left_box": [180, 600, 240, 640],
        "granularity": "block",
    }


class PictureChildSerializer(ChunkingSerializerProvider):
    def get_serializer(self, doc):
        return ChunkingDocSerializer(doc=doc, params=MarkdownParams(traverse_pictures=True))


def pictures():
    figure = (
        '<img alt="A blue chart"/>Duplicate bare description<p>Nested note</p>'
        "<table><tr><th>Trial</th><th>mL</th></tr><tr><td>East</td><td>40</td></tr></table>"
        '<pre class="mermaid">graph LR; A --&gt; B</pre><figcaption>Inside caption</figcaption>'
        '<div data-label="Footnote">Inside footnote</div>'
    )
    doc = parse(block("Figure", figure) + block("Caption", "Outside caption"))
    picture = doc.pictures[0]
    assert [ref.resolve(doc).text for ref in picture.captions] == ["Inside caption"]
    assert [ref.resolve(doc).text for ref in picture.footnotes] == ["Inside footnote"]
    assert picture.meta.description.text == "A blue chart"
    assert picture.meta.tabular_chart is None
    assert doc.tables[0].parent.cref == picture.self_ref and not doc.tables[0].prov
    assert not any("Duplicate bare description" in item.text for item in doc.texts)
    raw_copy = DoclingDocument.model_validate_json(doc.model_dump_json())
    assert raw_copy.tables[0].parent.cref == picture.self_ref

    markdown = doc.export_to_markdown()
    markdown_with_children = doc.export_to_markdown(traverse_pictures=True)
    default_chunks = [chunk.text for chunk in HierarchicalChunker().chunk(doc)]
    extended_chunks = [
        chunk.text
        for chunk in HierarchicalChunker(
            serializer_provider=PictureChildSerializer(),
        ).chunk(doc)
    ]
    for default, extended in (
        (markdown, markdown_with_children),
        ("\n".join(default_chunks), "\n".join(extended_chunks)),
    ):
        assert "graph LR; A --> B" not in default and "East" not in default
        assert "graph LR; A --> B" in extended and "East" in extended and "40" in extended

    molecule = parse(block("Chemical-Block", "<chem>CC(C)O</chem>")).pictures[0]
    two = parse(block("Chemical-Block", "<chem>CC</chem><chem>CO</chem>")).pictures[0]
    assert molecule.meta.molecule.smi == "CC(C)O" and two.meta.molecule is None
    return {
        "figure_html": figure,
        "picture_refs": [ref.cref for ref in picture.children],
        "picture_metadata": picture.meta.model_dump(mode="json", exclude_none=True),
        "nested_table_parent": doc.tables[0].parent.cref,
        "nested_table_provenance_count": len(doc.tables[0].prov),
        "caption_and_footnote_refs": [ref.cref for ref in [*picture.captions, *picture.footnotes]],
        "markdown_default": markdown,
        "markdown_traverse_pictures": markdown_with_children,
        "chunks_default": default_chunks,
        "chunks_traverse_pictures": extended_chunks,
        "single_chem_metadata": molecule.meta.molecule.model_dump(mode="json", exclude_none=True),
        "multiple_chem_metadata": None,
    }


def headings_and_form():
    first = block("Section-Header", "<h1>Chapter A</h1>")
    next_page = block("Section-Header", "<h2>Section B</h2>")
    local = parse(next_page, normalize=True)
    merged = DoclingDocument.concatenate([parse(first), parse(next_page, 2)])
    normalize_section_header_levels(merged)
    headings = [(item.text, item.level, item.prov[0].page_no) for item in merged.texts]
    assert headings == [("Chapter A", 1, 1), ("Section B", 2, 2)]
    assert local.texts[0].level == 1
    form = (
        '<p>Sample code <input type="text" value="BX-71"/></p>'
        '<p><input type="checkbox" checked/> Sealed</p><p><input type="checkbox"/> Retest</p>'
        '<p><input type="radio" checked/> Select C</p>'
    )
    doc = parse(block("Form", form))
    assert len(doc.field_regions) == 1 and len(doc.field_regions[0].prov) == 1
    control_items = [
        (item.label.value, item.text, getattr(item, "kind", None))
        for item in doc.texts
        if item.label.value != "text"
    ]
    assert control_items == [
        ("field_value", "BX-71", "fillable"),
        ("checkbox_selected", "", None),
        ("checkbox_unselected", "", None),
        ("checkbox_selected", "", None),
    ]
    return {
        "local_second_page_heading_level": local.texts[0].level,
        "joined_normalized_headings": headings,
        "form_html": form,
        "control_items": control_items,
        "form_markdown": doc.export_to_markdown(),
        "form_children_with_direct_geometry": sum(bool(item.prov) for item in doc.texts),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING)
    report = {
        "versions": {package: version(package) for package in ("docling", "docling-core")},
        "scope": "Authored HTML fixture controls, no provider inference",
        "layout": layout(),
        "table": table(),
        "rotated_crop": rotated_crop(),
        "pictures": pictures(),
        "headings_and_form": headings_and_form(),
    }
    if args.baseline is not None:
        report["response_status"] = response_status()
        baseline = json.loads(args.baseline.read_text())
        report["baseline_comparison"] = {
            "versions": baseline["versions"],
            "old_inline_runs": baseline["layout"]["inline_runs"],
            "old_first_run_charspan": baseline["layout"]["first_run_charspan"],
            "old_rendered_table_markdown": baseline["table"]["rendered_table_markdown"],
        }
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")


def response_status():
    from docling.datamodel.base_models import ConversionStatus, VlmPrediction, VlmStopReason
    from docling.pipeline.vlm_pipeline import VlmPipeline

    truncated = '<div data-label="Text" data-bbox="100 200 800 300"><p>First part only'
    repeated = block("Text", "Repeated sentence. " * 24)
    cases = (
        ("explicit_length", truncated, VlmStopReason.LENGTH, "partial_success"),
        ("unmarked_truncation", truncated, VlmStopReason.UNSPECIFIED, "success"),
        ("unmarked_repetition", repeated, VlmStopReason.UNSPECIFIED, "success"),
        ("explicit_error", "", VlmStopReason.INFERENCE_ERROR, "failure"),
    )
    outcomes = {}
    for label, html, stop_reason, expected in cases:
        prediction = VlmPrediction(text=html, stop_reason=stop_reason)
        page = SimpleNamespace(page_no=1, predictions=SimpleNamespace(vlm_response=prediction))
        result = SimpleNamespace(status=ConversionStatus.SUCCESS, pages=[page], errors=[])
        status = VlmPipeline._determine_status(None, result).value
        assert status == expected
        outcomes[label] = {"status": status, "native_texts": text_items(parse(html))}
    assert "First part only" in outcomes["unmarked_truncation"]["native_texts"][0][1]
    assert outcomes["unmarked_repetition"]["native_texts"][0][1].count("Repeated sentence.") == 24
    return outcomes


if __name__ == "__main__":
    main()
