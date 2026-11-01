"""Independent geometry boundaries and selected Arrow consumption controls."""

from __future__ import annotations

from collections.abc import Collection, Iterator, Sequence
from dataclasses import replace

import pyarrow as pa
import pytest
from docling_core.types.doc import (
    BoundingBox,
    CoordOrigin,
    DocItemLabel,
    DoclingDocument,
    PageItem,
    ProvenanceItem,
    RefItem,
    RichTableCell,
    Size,
    TableCell,
    TableData,
)

from corpus_structure.ingest.pdf_candidate_geometry import CandidateGeometry, candidate_page_status
from corpus_structure.ingest.pdf_candidate_source import InMemoryCandidatePageSource
from corpus_structure.ingest.pdf_candidates import CandidatePage, InlineCandidate
from corpus_structure.ingest.pdf_enrichment import (
    classify_cells,
    positioned_inline_candidates,
    table_candidates,
)


class BatchOnlySource:
    """The analysis path may request selected batches, never domain page hydration."""

    def __init__(self, pages: tuple[CandidatePage, ...]):
        self.base = InMemoryCandidatePageSource(pages)
        self.payload_family = self.base.payload_family
        self.requests: list[tuple[set[int], tuple[str, ...] | None]] = []

    @property
    def page_nos(self) -> tuple[int, ...]:
        return self.base.page_nos

    def iter_batches(
        self, page_nos: Collection[int] | None = None, columns: Sequence[str] | None = None
    ) -> Iterator[pa.RecordBatch]:
        assert page_nos is not None, "analysis must declare its selected pages"
        self.requests.append((set(page_nos), tuple(columns) if columns else None))
        yield from self.base.iter_batches(page_nos, columns)

    def iter_pages(self, page_nos=None):
        raise AssertionError("analysis hydrated a page instead of selected matches")

    def encoded(self, page_no):
        return self.base.encoded(page_no)


def region(text: str, left: float, top: float, right: float, bottom: float, **kwargs):
    return InlineCandidate(
        1, text, left, top, right, bottom, "TOPLEFT", None, "native-math-token-v1", **kwargs
    )


def prose():
    document = DoclingDocument(name="independent center boundaries")
    document.pages[1] = PageItem(page_no=1, size=Size(width=100, height=100))
    item = document.add_text(
        label=DocItemLabel.TEXT,
        text="x y",
        prov=ProvenanceItem(
            page_no=1,
            bbox=BoundingBox(l=10, t=10, r=20, b=20, coord_origin=CoordOrigin.TOPLEFT),
            charspan=(0, 3),
        ),
    )
    return document, item


def test_inclusive_centers_deduplicate_provenance_and_keep_original_filtered_ordinals(monkeypatch):
    document, item = prose()
    item.prov.append(item.prov[0].model_copy(deep=True))
    candidates = (
        region("outside", 0, 0, 2, 2),
        region("x", 8, 8, 12, 12),  # center on top-left edge
        replace(region("y", 18, 82, 22, 78), origin="BOTTOMLEFT"),
    )
    source = BatchOnlySource(
        (
            CandidatePage(1, True, False, candidates, True),
            CandidatePage(99, True, False, (replace(candidates[0], page_no=99),), True),
        )
    )
    import corpus_structure.ingest.pdf_candidate_geometry as geometry_module

    original = geometry_module.candidate_from_payload
    hydrated = []

    def hydrate(row, family):
        hydrated.append(row["text"])
        return original(row, family)

    monkeypatch.setattr(geometry_module, "candidate_from_payload", hydrate)
    result = positioned_inline_candidates(document, source, frozenset({item.self_ref}))
    assert not result.reports
    assert [(part.start, part.end, part.candidate.text) for part in result.candidates] == [
        (0, 1, "x"),
        (2, 3, "y"),
    ]
    assert hydrated == ["x", "y"]
    assert all(numbers == {1} for numbers, _ in source.requests)

    other = document.add_text(label=DocItemLabel.TEXT, text="x y", prov=item.prov[0])
    hydrated.clear()
    result = positioned_inline_candidates(
        document, source, frozenset({item.self_ref, other.self_ref})
    )
    assert not result.candidates
    assert [report.candidate_index for report in result.reports] == [1, 2]
    assert all(report.item_pointers == (item.self_ref, other.self_ref) for report in result.reports)
    assert hydrated == []


def test_range_join_agrees_with_independent_center_oracle_for_both_origins():
    document, item = prose()
    other = document.add_text(
        label=DocItemLabel.TEXT,
        text="value",
        prov=ProvenanceItem(
            page_no=1,
            bbox=BoundingBox(l=15, t=15, r=30, b=30),
            charspan=(0, 5),
        ),
    )
    points = [(x, y) for x in (9, 10, 15, 20, 30, 31) for y in (9, 10, 15, 20, 30, 31)]
    candidates = tuple(
        replace(
            region(str(i), x - 1, 100 - (y - 1), x + 1, 100 - (y + 1)),
            origin="BOTTOMLEFT",
        )
        if i % 2
        else region(str(i), x - 1, y - 1, x + 1, y + 1)
        for i, (x, y) in enumerate(points)
    )
    source = BatchOnlySource((CandidatePage(1, True, False, candidates, True),))
    with CandidateGeometry(document, source, {1}) as geometry:
        actual = {
            (match.candidate_index, match.item_ref)
            for match in geometry.inline_matches(
                {item.self_ref: item, other.self_ref: other},
                frozenset({item.self_ref, other.self_ref}),
            )
        }
    expected = {
        (index, pointer)
        for index, (x, y) in enumerate(points)
        for pointer, (left, top, right, bottom) in (
            (item.self_ref, (10, 10, 20, 20)),
            (other.self_ref, (15, 15, 30, 30)),
        )
        if left <= x <= right and top <= y <= bottom
    }
    assert actual == expected


def test_selected_batches_preserve_cross_page_regions_at_one_native_anchor():
    document, item = prose()
    item.text = "before after"
    item.prov[0].charspan = (0, len(item.text))
    document.pages[2] = PageItem(page_no=2, size=Size(width=100, height=100))
    item.prov.append(item.prov[0].model_copy(update={"page_no": 2}, deep=True))
    gap = region("", 11, 11, 13, 13, before="before", after="after")
    source = BatchOnlySource(
        (
            CandidatePage(1, True, False, (gap,), True),
            CandidatePage(2, True, False, (replace(gap, page_no=2),), True),
        )
    )
    result = positioned_inline_candidates(document, source, frozenset({item.self_ref}))
    assert not result.reports
    (position,) = result.candidates
    assert position.start == position.end == len("before ")
    assert [part.page_no for part in position.regions] == [1, 2]
    assert source.requests == [({1, 2}, ("page_no", "candidates"))]


@pytest.mark.parametrize("origin", ["TOPLEFT", "BOTTOMLEFT"])
def test_cell_intersection_is_strict_and_precedes_token_and_prose_classification(origin):
    document = DoclingDocument(name="independent strict overlap")
    document.pages[1] = PageItem(page_no=1, size=Size(width=100, height=100))
    cells = [
        TableCell(
            text=text,
            bbox=BoundingBox(l=10, t=top, r=20, b=top + 10),
            start_row_offset_idx=index,
            end_row_offset_idx=index + 1,
            start_col_offset_idx=0,
            end_col_offset_idx=1,
        )
        for index, (text, top) in enumerate((("Plain", 10), ("Plain", 30), ("x", 50), ("???", 70)))
    ]
    table = document.add_table(
        data=TableData(num_rows=4, num_cols=1, table_cells=cells),
        prov=ProvenanceItem(page_no=1, bbox=BoundingBox(l=10, t=10, r=20, b=80), charspan=(0, 0)),
    )
    regions = (region("edge", 20, 10, 25, 20), region("inside", 19, 30, 25, 40))
    if origin == "BOTTOMLEFT":
        regions = tuple(
            replace(
                candidate, top=100 - candidate.top, bottom=100 - candidate.bottom, origin=origin
            )
            for candidate in regions
        )
    source = BatchOnlySource((CandidatePage(1, True, False, regions, True),))
    demanded, reports = classify_cells(
        document,
        table_candidates(document, frozenset({table.self_ref})),
        source,
        math_pattern=r"^x$",
        prose_pattern=r"[A-Za-z]+",
    )
    assert [row["basis"] for row in reports] == [
        "native-word-text",
        "native-candidate-intersection",
        "native-math-token",
        "unresolved-native-evidence",
    ]
    assert [candidate.cell_index for candidate in demanded] == [1, 2]

    formula = document.add_text(label=DocItemLabel.FORMULA, text="already recognized")
    table.data.table_cells[1] = RichTableCell(
        **cells[1].model_dump(), ref=RefItem(cref=formula.self_ref)
    )
    demanded, reports = classify_cells(
        document,
        table_candidates(document, frozenset({table.self_ref})),
        source,
        math_pattern=r"^x$",
        prose_pattern=r"[A-Za-z]+",
    )
    assert reports[1]["basis"] == "native-rich-reference"
    assert reports[1]["formula_pointer"] == formula.self_ref
    assert [candidate.cell_index for candidate in demanded] == [2]


def test_page_status_uses_ocr_completion_and_preserves_native_broken_text_rule():
    word = dict(
        word_index=0,
        text="x",
        confidence=1,
        start=0,
        end=1,
        raster_left=0,
        raster_top=0,
        raster_right=10,
        raster_bottom=10,
        left=0,
        top=0,
        right=10,
        bottom=10,
    )
    complete = dict(
        region_index=0,
        engine="rapidocr",
        raster_width=100,
        raster_height=100,
        scale=1,
        orientation=0,
        outcome="complete",
        lines=[dict(line_index=0, text="x", words=[word])],
        left=0,
        top=0,
        right=100,
        bottom=100,
    )
    source = BatchOnlySource(
        (
            CandidatePage(1, True, False, (), True, "broken"),
            CandidatePage(2, False, False, (), True, "broken", (complete,)),
            CandidatePage(
                3, True, False, (), True, "not_flagged", (dict(complete, outcome="partial"),)
            ),
        )
    )
    statuses = candidate_page_status(source, {1, 2, 3})
    assert [statuses[number].usable_words for number in (1, 2, 3)] == [False, True, False]
    assert all("candidates" not in columns for _, columns in source.requests if columns)
