"""Compact inline-math candidate capture before native page cleanup; no second PDF parser."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

_MATH_FONT = re.compile(r"(?:CMMI|CMSY|CMEX|MSAM|MSBM|Math|Symbol|STIX)", re.I)
_MATH_TOKEN = re.compile(r"[=<>≤≥∈∉∪∩∑∏∫√∞α-ωΑ-Ω]|\\[A-Za-z]+|\b[A-Za-z]\s*\^")


@dataclass(frozen=True, slots=True)
class InlineCandidate:
    page_no: int
    text: str
    left: float
    top: float
    right: float
    bottom: float
    origin: str
    font: str | None
    basis: str
    before: str = ""
    after: str = ""

    def to_wire(self) -> dict[str, Any]:
        """An absent application slot is omitted; native document nulls are unrelated."""
        value = asdict(self)
        if self.font is None:
            value.pop("font")
        return value

    @classmethod
    def from_wire(cls, value: dict[str, Any]) -> InlineCandidate:
        return cls(
            page_no=value["page_no"],
            text=value["text"],
            left=value["left"],
            top=value["top"],
            right=value["right"],
            bottom=value["bottom"],
            origin=value["origin"],
            font=value.get("font"),
            basis=value["basis"],
            before=value.get("before", ""),
            after=value.get("after", ""),
        )


@dataclass(frozen=True, slots=True)
class CandidatePage:
    page_no: int
    has_words: bool
    has_chars: bool
    candidates: tuple[InlineCandidate, ...]
    has_vectors: bool = False

    def to_wire(self) -> dict[str, Any]:
        return dict(
            page_no=self.page_no,
            has_words=self.has_words,
            has_chars=self.has_chars,
            candidates=[candidate.to_wire() for candidate in self.candidates],
            has_vectors=self.has_vectors,
        )


def capture_candidates(page: Any) -> CandidatePage:
    """Enumerate available native words once; unknown extraction is not empty evidence.

    These are attributed discovery rules, not a universal mathematical-absence classifier.
    Recognition coverage is qualified separately over demanded source views.
    """
    parsed = page.parsed_page
    if parsed is None:
        return CandidatePage(page.page_no, False, False, ())
    rows = []
    words = parsed.word_cells
    for index, cell in enumerate(words):
        font = getattr(cell, "font_name", None)
        font_match = font is not None and _MATH_FONT.search(font) is not None
        token_match = _MATH_TOKEN.search(cell.text) is not None
        if not cell.text.strip() or not (font_match or token_match):
            continue
        box = cell.rect.to_bounding_box()
        if getattr(page, "size", None) is not None:
            box = box.to_top_left_origin(page.size.height)
            box.l = max(0, min(page.size.width, box.l))
            box.r = max(0, min(page.size.width, box.r))
            box.t = max(0, min(page.size.height, box.t))
            box.b = max(0, min(page.size.height, box.b))
            if box.area() <= 0:
                continue
        rows.append(
            InlineCandidate(
                page.page_no,
                cell.text,
                box.l,
                box.t,
                box.r,
                box.b,
                box.coord_origin.value,
                font,
                "native-math-font-v1" if font_match else "native-math-token-v1",
                " ".join(w.text for w in words[max(0, index - 2) : index]),
                " ".join(w.text for w in words[index + 1 : index + 3]),
            )
        )
    backend = getattr(page, "_backend", None)
    vectors = None if backend is None else vector_boxes(backend, page.size)
    if vectors is not None:
        height = page.size.height
        word_boxes = [
            (word, word.rect.to_bounding_box().to_top_left_origin(height)) for word in words
        ]
        gaps: dict[tuple[Any, Any], list[Any]] = {}
        for box in vectors:
            box = box.to_top_left_origin(height)
            if min(box.width, box.height) < 0.3 or (box.height < 1 and box.width > 8):
                continue
            center_y = (box.t + box.b) / 2
            nearby = [
                (word, wb)
                for word, wb in word_boxes
                if abs((wb.t + wb.b) / 2 - center_y) <= max(wb.height, box.height) / 2
            ]
            left = sorted(
                [(word, wb) for word, wb in nearby if wb.r <= box.l], key=lambda pair: pair[1].r
            )
            right = sorted(
                [(word, wb) for word, wb in nearby if wb.l >= box.r], key=lambda pair: pair[1].l
            )
            if not left and not right:
                continue
            gap_key = (id(left[-1][0]) if left else None, id(right[0][0]) if right else None)
            if gap_key not in gaps:
                gaps[gap_key] = [
                    box,
                    " ".join(word.text for word, _ in left[-2:]),
                    " ".join(word.text for word, _ in right[:2]),
                ]
            else:
                previous = gaps[gap_key][0]
                previous.l = min(previous.l, box.l)
                previous.t = min(previous.t, box.t)
                previous.r = max(previous.r, box.r)
                previous.b = max(previous.b, box.b)
        for box, before, after in gaps.values():
            rows.append(
                InlineCandidate(
                    page.page_no,
                    "",
                    box.l,
                    box.t,
                    box.r,
                    box.b,
                    "TOPLEFT",
                    None,
                    "native-vector-gap-v1",
                    before,
                    after,
                )
            )
    return CandidatePage(
        page.page_no, parsed.has_words, parsed.has_chars, tuple(rows), vectors is not None
    )


def vector_boxes(backend: Any, size: Any) -> list[Any] | None:
    """Filter decorative backgrounds BEFORE native-path connectivity.

    Public PageParseResult materialization escalates already computed shapes, without a second
    decode. The pinned Docling backend owns that result. Only compact boxes escape this stage.
    """
    import networkx as nx
    from docling.datamodel.spatial import BoundingBoxSpatialIndex
    from docling_core.types.doc import BoundingBox
    from docling_parse.pdf_parser import ContentConfig, ContentLevel

    result = getattr(backend, "_result", None)
    if result is None:
        return backend.get_connected_shape_bounding_boxes(tolerance=2.0)
    rich = result.get_page(
        content_config=ContentConfig(
            char_cells_content_level=ContentLevel.SKIP,
            word_cells_content_level=ContentLevel.SKIP,
            line_cells_content_level=ContentLevel.SKIP,
            shapes_content_level=ContentLevel.COMPUTE_AND_MATERIALIZE,
            bitmaps_content_level=ContentLevel.SKIP,
            include_bitmap_bytes=False,
        )
    )
    words = backend.get_segmented_page().word_cells
    word_boxes = [word.rect.to_bounding_box().to_top_left_origin(size.height) for word in words]
    word_index = BoundingBoxSpatialIndex()
    for index, box in enumerate(word_boxes):
        word_index.insert(index, box)
    boxes = []
    for shape in rich.shapes:
        if not shape.points:
            continue
        xs = [point[0] for point in shape.points]
        ys = [point[1] for point in shape.points]
        box = BoundingBox(
            l=min(xs), r=max(xs), t=max(ys), b=min(ys), coord_origin=shape.coord_origin
        )
        if shape.coord_origin.value == "TOPLEFT":
            box.t, box.b = min(ys), max(ys)
        box = box.to_top_left_origin(size.height)
        box.l = max(0, min(size.width, box.l))
        box.r = max(0, min(size.width, box.r))
        box.t = max(0, min(size.height, box.t))
        box.b = max(0, min(size.height, box.b))
        if min(box.width, box.height) < 0.3 or box.area() > size.width * size.height * 0.25:
            continue
        explained = sum(
            box.intersection_area_with(word_boxes[i]) for i in word_index.intersection(box)
        )
        if explained / box.area() > 0.6:
            continue
        boxes.append(box)
    index = BoundingBoxSpatialIndex()
    graph = nx.Graph()
    graph.add_nodes_from(range(len(boxes)))
    for number, box in enumerate(boxes):
        expanded = BoundingBox(l=box.l - 1.5, t=box.t - 1.5, r=box.r + 1.5, b=box.b + 1.5)
        graph.add_edges_from((number, other) for other in index.intersection(expanded))
        index.insert(number, expanded)
    return [
        BoundingBox(
            l=min(boxes[i].l for i in group),
            t=min(boxes[i].t for i in group),
            r=max(boxes[i].r for i in group),
            b=max(boxes[i].b for i in group),
        )
        for group in nx.connected_components(graph)
    ]


def rediscover_candidates(
    original: bytes, pages: tuple[int, ...], *, parser_threads: int = 8
) -> tuple[CandidatePage, ...]:
    """Repair discovery metadata from retained PDF backends only, never layout/OCR/formula models."""
    from io import BytesIO

    from docling.backend.docling_parse_backend import ThreadedDoclingParseDocumentBackend
    from docling.datamodel.backend_options import ThreadedDoclingParseBackendOptions
    from docling.datamodel.base_models import InputFormat, Page
    from docling.datamodel.document import InputDocument
    from docling.datamodel.settings import DocumentLimits

    numbers = sorted(set(pages))
    if any(number < 1 for number in numbers):
        raise ValueError("candidate discovery uses physical positive PDF pages")
    ranges = []
    for number in numbers:
        if ranges and number == ranges[-1][1] + 1:
            ranges[-1] = (ranges[-1][0], number)
        else:
            ranges.append((number, number))
    found = []
    for start, end in ranges:
        source = InputDocument(
            BytesIO(original),
            InputFormat.PDF,
            ThreadedDoclingParseDocumentBackend,
            backend_options=ThreadedDoclingParseBackendOptions(
                parser_threads=parser_threads,
                max_concurrent_results=parser_threads,
                render_pages=True,
            ),
            filename="retained.pdf",
            limits=DocumentLimits(page_range=(start, end)),
        )
        try:
            backend = source._backend
            if not source.valid or not isinstance(backend, ThreadedDoclingParseDocumentBackend):
                raise ValueError("retained original cannot initialize admitted native PDF backend")
            for native_page in backend.iter_pages():
                try:
                    page = Page(page_no=native_page.page_no, size=native_page.get_size())
                    page._backend = native_page
                    page.parsed_page = native_page.get_segmented_page()
                    found.append(capture_candidates(page))
                finally:
                    native_page.unload()
        finally:
            source.release()
    if {page.page_no for page in found} != set(numbers):
        raise ValueError("native PDF discovery did not return the selected physical pages")
    return tuple(found)
