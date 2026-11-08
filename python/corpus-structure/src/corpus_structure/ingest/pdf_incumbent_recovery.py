"""Source-qualified repairs for the retained Grinstead and Snell qualification book."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from typing import Any

from docling_core.types.doc import BoundingBox, DocItemLabel, ProvenanceItem, TableCell, TableData

RECIPE = "grinstead-snell-witnessed-v1"
ORIGINAL = "763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474534460551a5e"
PREDECESSOR = {
    "task_id": 1389,
    "product_key": "integrated",
    "content_digest": "a491d3ddbf3ee964a8a95e6fc6bed59648fb5c5a77bc57cb84411a9205a749f2",
}
FIGURE_CAPTION = "Figure 3.5: Binomial distributions."
TABLE_CAPTION = "Table 4.2: Joint distribution."
FRACTIONS = ("40/60", "10/60", "7/60", "3/60")
PANEL_LABELS = ("p = .5", "p = .3")


@dataclass(frozen=True, slots=True)
class RecoveryEvidence:
    caption: BoundingBox
    panel_boxes: tuple[BoundingBox, BoundingBox]
    table_caption: BoundingBox
    table_box: BoundingBox
    table: TableData


def _contains(outer: BoundingBox, inner: BoundingBox) -> bool:
    return outer.l <= inner.l <= inner.r <= outer.r and outer.t <= inner.t <= inner.b <= outer.b


def _union(boxes: list[BoundingBox]) -> BoundingBox:
    return BoundingBox(
        l=min(box.l for box in boxes),
        t=min(box.t for box in boxes),
        r=max(box.r for box in boxes),
        b=max(box.b for box in boxes),
    )


def _unique_line(page, literal: str) -> BoundingBox:
    matches = [
        cell.rect.to_bounding_box()
        for cell in page.get_visible_text_cells() or ()
        if cell.text.strip() == literal
    ]
    if len(matches) != 1:
        raise ValueError(f"incumbent recovery lacks a unique positioned source line: {literal}")
    return matches[0]


def _figure(page) -> tuple[BoundingBox, tuple[BoundingBox, BoundingBox]]:
    caption = _unique_line(page, FIGURE_CAPTION)
    labels = [_unique_line(page, text) for text in PANEL_LABELS]
    shapes = page.get_connected_shape_bounding_boxes(tolerance=0) or ()
    panels = []
    for label in labels:
        matches = [shape for shape in shapes if _contains(shape, label)]
        if len(matches) != 1:
            raise ValueError("incumbent recovery lacks a unique source panel for the printed label")
        panels.append(matches[0])
    upper, lower = panels
    if upper.b >= lower.t or lower.b >= caption.t:
        raise ValueError("incumbent source panels do not precede the shared printed caption")
    gap = (upper.b + lower.t) / 2
    # Axes have text outside the painted frame. Include only located glyphs
    # within the corresponding panel band and adjacent to the drawn axes.
    text = [cell.rect.to_bounding_box() for cell in page.get_visible_text_cells() or ()]
    result = []
    for frame, bottom in ((upper, gap), (lower, caption.t)):
        result.append(
            _union(
                [
                    frame,
                    *[
                        box
                        for box in text
                        if frame.t <= box.t <= box.b < bottom
                        and frame.l - 25 <= box.l <= box.r <= frame.r + 5
                    ],
                ]
            )
        )
    return caption, (result[0], result[1])


def _table(page) -> tuple[BoundingBox, BoundingBox, TableData]:
    caption = _unique_line(page, TABLE_CAPTION)
    preceding = _unique_line(page, "Table 4.1: Smoking and cancer.")
    # TeX draws these rules with single-pixel stencil bitmaps. Use the native bitmap
    # rectangles as well as vector lines. The pixel control checks the rules.
    rules = list(page.get_shape_lines() or ()) + list(page.get_bitmap_rects())
    band = [box for box in rules if preceding.b < box.t <= box.b < caption.t]
    horizontal = [box for box in band if box.width >= 100 and box.height < 1]
    if len(horizontal) != 1:
        raise ValueError("incumbent recovery lacks the table's unique horizontal rule")
    boundary = horizontal[0]
    vertical = [
        box
        for box in band
        if box.height >= 10 and box.width < 1 and boundary.l < box.l <= box.r < boundary.r
    ]
    if not vertical or max(box.r for box in vertical) - min(box.l for box in vertical) >= 1:
        raise ValueError("incumbent recovery lacks the table's single vertical divider")
    frame = _union([boundary, *vertical])
    parsed = page.get_segmented_page()
    if parsed is None:
        raise ValueError("incumbent recovery lacks positioned PDF words")
    words = [
        (cell.text.strip(), box)
        for cell in parsed.word_cells
        if _contains(frame, box := cell.rect.to_bounding_box())
    ]

    def row(selected):
        return sorted(((text, box) for text, box in words if selected(box)), key=lambda x: x[1].l)

    left, right = min(box.l for box in vertical), max(box.r for box in vertical)
    above = row(lambda box: box.l > right and box.b < boundary.t)
    below = row(lambda box: box.t > boundary.b and box.l > right)
    headers = {text: box for text, box in above}
    row_labels = {text: box for text, box in row(lambda box: box.r < left and box.t > boundary.b)}
    values = {text: box for text, box in below}
    if (
        len(words) != 10
        or len(above) != 3
        or len(below) != 4
        or set(headers) != {"S", "0", "1"}
        or set(row_labels) != {"C", "0", "1"}
        or set(values) != set(FRACTIONS)
        or not headers["S"].b < min(headers["0"].t, headers["1"].t)
        or not headers["0"].r < headers["1"].l
        or not row_labels["0"].b < row_labels["C"].t < row_labels["C"].b < row_labels["1"].t
    ):
        raise ValueError("incumbent recovery cannot establish the complete table header topology")
    split = (headers["0"].r + headers["1"].l) / 2
    for index, text in enumerate(FRACTIONS):
        box = values[text]
        label = row_labels[str(index // 2)]
        if (
            min(box.b, label.b) <= max(box.t, label.t)
            or (index % 2 == 0 and box.r >= split)
            or (index % 2 == 1 and box.l <= split)
        ):
            raise ValueError("incumbent recovery cannot establish a positioned fraction binding")

    def cell(text, box, row, col, *, rows=1, cols=1, row_header=False, column_header=False):
        return TableCell(
            bbox=box,
            text=text,
            row_span=rows,
            col_span=cols,
            start_row_offset_idx=row,
            end_row_offset_idx=row + rows,
            start_col_offset_idx=col,
            end_col_offset_idx=col + cols,
            row_header=row_header,
            column_header=column_header,
        )

    cells = [
        cell("S", headers["S"], 0, 2, cols=2, column_header=True),
        cell("0", headers["0"], 1, 2, column_header=True),
        cell("1", headers["1"], 1, 3, column_header=True),
        cell("C", row_labels["C"], 2, 0, rows=2, row_header=True),
        cell("0", row_labels["0"], 2, 1, row_header=True),
        cell(FRACTIONS[0], values[FRACTIONS[0]], 2, 2),
        cell(FRACTIONS[1], values[FRACTIONS[1]], 2, 3),
        cell("1", row_labels["1"], 3, 1, row_header=True),
        cell(FRACTIONS[2], values[FRACTIONS[2]], 3, 2),
        cell(FRACTIONS[3], values[FRACTIONS[3]], 3, 3),
    ]
    return caption, frame, TableData(num_rows=4, num_cols=4, table_cells=cells)


def read_source_witness(original: bytes) -> RecoveryEvidence:
    """Compute witnesses from the exact source and finite page ranges without OCR."""
    from docling.backend.docling_parse_backend import ThreadedDoclingParseDocumentBackend
    from docling.datamodel.backend_options import ThreadedDoclingParseBackendOptions
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.document import InputDocument
    from docling.datamodel.settings import DocumentLimits

    if sha256(original).hexdigest() != ORIGINAL:
        raise ValueError("the witnessed incumbent repair requires the exact reviewed original")

    def read(number, callback):
        document = InputDocument(
            BytesIO(original),
            InputFormat.PDF,
            ThreadedDoclingParseDocumentBackend,
            backend_options=ThreadedDoclingParseBackendOptions(
                render_pages=True, parser_threads=1, max_concurrent_results=1
            ),
            limits=DocumentLimits(page_range=(number, number)),
            filename="retained.pdf",
        )
        try:
            backend = document._backend
            if not document.valid or not isinstance(backend, ThreadedDoclingParseDocumentBackend):
                raise ValueError("incumbent witness PDF backend is unavailable")
            pages = list(backend.iter_pages())
            if len(pages) != 1 or not pages[0].is_valid() or pages[0].page_no != number:
                raise ValueError("incumbent witness does not match the physical page")
            try:
                return callback(pages[0])
            finally:
                pages[0].unload()
        finally:
            document.release()

    caption, panels = read(108, _figure)
    table_caption, table_box, table = read(151, _table)
    return RecoveryEvidence(caption, panels, table_caption, table_box, table)


def source_provenance(box: BoundingBox, page: int, length: int = 0) -> ProvenanceItem:
    return ProvenanceItem(page_no=page, bbox=box, charspan=(0, length))


def _move_before(parent, node, anchor) -> None:
    parent.children.remove(node.get_ref())
    parent.children.insert(parent.children.index(anchor.get_ref()), node.get_ref())


def recover_table(document, witness: RecoveryEvidence, caption) -> tuple[Any, bool]:
    """Replace only a competing table at this exact source locus, or add it."""
    competing = []
    for table in document.tables:
        for prov in table.prov:
            if prov.page_no != 151:
                continue
            box = prov.bbox.to_top_left_origin(document.pages[151].size.height)
            if box.intersection_over_self(witness.table_box) > 0.5:
                competing.append(table)
                break
    if len(competing) > 1:
        raise ValueError("source-qualified table recovery has ambiguous selected table ownership")
    added = not competing
    if added:
        parent = caption.parent.resolve(document)
        table = document.add_table(
            witness.table, parent=parent, prov=source_provenance(witness.table_box, 151)
        )
        _move_before(parent, table, caption)
    else:
        table = competing[0]
        if (
            caption.parent not in (table.parent, table.get_ref())
            or any(ref != caption.get_ref() for ref in table.children)
            or any(ref != caption.get_ref() for ref in table.captions)
        ):
            raise ValueError("source-qualified table recovery has unresolved dependent items")
        table.data = witness.table
        table.prov = [source_provenance(witness.table_box, 151)]
    table.captions = [caption.get_ref()]
    return table, added


def recover_figure(document, witness: RecoveryEvidence, caption) -> tuple[Any, ...]:
    """Link one caption to two independently located selected picture occurrences."""
    panels = []
    for literal, box in zip(PANEL_LABELS, witness.panel_boxes, strict=True):
        matches = [
            picture
            for picture in document.pictures
            if picture.parent == caption.parent
            and picture.meta is not None
            and picture.meta.tabular_chart is not None
            and picture.meta.tabular_chart.title == literal
            and any(
                prov.page_no == 108
                and box.intersection_over_self(
                    prov.bbox.to_top_left_origin(document.pages[108].size.height)
                )
                >= 0.8
                for prov in picture.prov
            )
        ]
        if len(matches) != 1 or any(ref != caption.get_ref() for ref in matches[0].captions):
            return ()
        panels.append(matches[0])
    for panel, box in zip(panels, witness.panel_boxes, strict=True):
        panel.prov = [source_provenance(box, 108)]
        panel.captions = [caption.get_ref()]
    return tuple(panels)


def add_caption(document, parent, text: str, box: BoundingBox, page: int, *, after):
    caption = document.add_text(
        DocItemLabel.CAPTION, text, prov=source_provenance(box, page, len(text)), parent=parent
    )
    parent.children.remove(caption.get_ref())
    parent.children.insert(parent.children.index(after.get_ref()) + 1, caption.get_ref())
    return caption
