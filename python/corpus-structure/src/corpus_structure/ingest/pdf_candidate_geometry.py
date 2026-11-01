"""Selected-page Arrow geometry; native Docling nodes retain text/structure authority."""

from __future__ import annotations

from collections.abc import Collection, Iterator
from dataclasses import dataclass
from itertools import chain
from typing import Any

import duckdb
import pyarrow as pa

from .pdf_candidate_source import CandidatePageSource, candidate_from_payload
from .pdf_candidates import InlineCandidate


@dataclass(frozen=True, slots=True)
class InlineGeometryMatch:
    page_no: int
    candidate_index: int
    item_ref: str
    match_count: int
    candidate: InlineCandidate | None
    top: float
    bottom: float
    spans: frozenset[tuple[int, int]]


@dataclass(frozen=True, slots=True)
class CandidatePageStatus:
    has_vectors: bool
    usable_words: bool
    has_ocr_regions: bool


def candidate_page_status(
    source: CandidatePageSource, page_nos: Collection[int]
) -> dict[int, CandidatePageStatus]:
    """Read page availability without hydrating candidate or OCR word collections."""
    result = {}
    for batch in source.iter_batches(
        page_nos,
        columns=("page_no", "has_words", "has_vectors", "native_text_quality", "ocr_regions"),
    ):
        for index in range(batch.num_rows):
            regions = batch.column("ocr_regions")[index]
            outcomes = regions.values.field("outcome").to_pylist() if regions.is_valid else []
            quality = batch.column("native_text_quality")[index].as_py()
            result[batch.column("page_no")[index].as_py()] = CandidatePageStatus(
                bool(batch.column("has_vectors")[index].as_py()),
                all(outcome == "complete" for outcome in outcomes)
                if outcomes
                else bool(batch.column("has_words")[index].as_py()) and quality != "broken",
                bool(outcomes),
            )
    return result


_BOX_SCHEMA = pa.schema(
    [
        ("page_no", pa.int64()),
        ("item_ref", pa.string()),
        ("index", pa.int64()),
        ("span_start", pa.int64()),
        ("span_end", pa.int64()),
        ("left", pa.float64()),
        ("top", pa.float64()),
        ("right", pa.float64()),
        ("bottom", pa.float64()),
    ]
)


class CandidateGeometry:
    """Normalize selected candidate coordinates once for both geometry consumers.

    The query engine holds columnar selected-page candidates, never a book-sized Python
    candidate collection. Only selected matching inline rows cross the hydration boundary.
    """

    def __init__(
        self, document: Any, source: CandidatePageSource, page_nos: Collection[int]
    ) -> None:
        self.document = document
        self.payload_family = source.payload_family
        self.connection = duckdb.connect(config={"threads": 1})
        self.reader: pa.RecordBatchReader | None = None
        self.available = False
        try:
            batches = iter(source.iter_batches(page_nos, columns=("page_no", "candidates")))
            first = next(batches, None)
            if first is None:
                return
            self.reader = pa.RecordBatchReader.from_batches(first.schema, chain((first,), batches))
            self.connection.register("candidate_pages", self.reader)
            self.connection.register(
                "page_heights",
                pa.table(
                    {
                        "page_no": pa.array(sorted(page_nos), type=pa.int64()),
                        "height": pa.array(
                            [document.pages[number].size.height for number in sorted(page_nos)],
                            type=pa.float64(),
                        ),
                    }
                ),
            )
            # Ordinality is assigned to the original nested list before any geometry
            # predicate. Tagged numbers become doubles only in this analytical projection.
            self.connection.execute(
                """
                CREATE TEMP TABLE candidate_geometry AS
                WITH flattened AS (
                    SELECT page_no, unnest(candidates) AS candidate,
                           generate_subscripts(candidates, 1) - 1 AS candidate_index
                    FROM candidate_pages
                ), numeric_boxes AS (
                    SELECT f.*,
                           coalesce(candidate.left.integer::DOUBLE,
                                    candidate.left.binary64) AS x_left,
                           coalesce(candidate.right.integer::DOUBLE,
                                    candidate.right.binary64) AS x_right,
                           coalesce(candidate.top.integer::DOUBLE,
                                    candidate.top.binary64) AS source_top,
                           coalesce(candidate.bottom.integer::DOUBLE,
                                    candidate.bottom.binary64) AS source_bottom,
                           h.height
                    FROM flattened f JOIN page_heights h USING (page_no)
                ), normalized AS (
                    SELECT page_no, candidate_index, candidate, x_left, x_right,
                           CASE WHEN candidate.origin = 'BOTTOMLEFT'
                                THEN height - source_top ELSE source_top END AS top,
                           CASE WHEN candidate.origin = 'BOTTOMLEFT'
                                THEN height - source_bottom ELSE source_bottom END AS bottom
                    FROM numeric_boxes
                )
                SELECT *, (x_left + x_right) / 2 AS center_x,
                          (top + bottom) / 2 AS center_y,
                          least(top, bottom) AS min_y,
                          greatest(top, bottom) AS max_y
                FROM normalized
                """
            ).complete()
            self.available = True
        except BaseException:
            self.close()
            raise

    def __enter__(self) -> CandidateGeometry:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        self.connection.close()
        if self.reader is not None:
            self.reader.close()

    def _box(self, page_no: int, box: Any, **identity: Any) -> dict[str, Any]:
        normalized = box.to_top_left_origin(self.document.pages[page_no].size.height)
        return dict(
            page_no=page_no,
            left=normalized.l,
            top=min(normalized.t, normalized.b),
            right=normalized.r,
            bottom=max(normalized.t, normalized.b),
            **identity,
        )

    def inline_matches(
        self, nodes: dict[str, Any], selected: frozenset[str]
    ) -> Iterator[InlineGeometryMatch]:
        if not self.available:
            return
        rows = []
        for pointer in sorted(selected):
            item = nodes[pointer]
            if str(item.label) not in {"text", "list_item", "caption", "footnote"} or item.children:
                continue
            for prov in item.prov:
                rows.append(
                    self._box(
                        prov.page_no,
                        prov.bbox,
                        item_ref=pointer,
                        index=0,
                        span_start=prov.charspan[0],
                        span_end=prov.charspan[1],
                    )
                )
        if not rows:
            return
        self.connection.register("prose_boxes", pa.Table.from_pylist(rows, schema=_BOX_SCHEMA))
        result = self.connection.sql(
            """
            WITH matches AS (
                SELECT c.page_no, c.candidate_index, p.item_ref,
                       any_value(c.candidate) AS candidate,
                       any_value(c.top) AS top, any_value(c.bottom) AS bottom,
                       list(DISTINCT [p.span_start, p.span_end]) AS spans
                FROM candidate_geometry c JOIN prose_boxes p
                  ON c.page_no = p.page_no
                 AND p.left <= c.center_x AND c.center_x <= p.right
                 AND p.top <= c.center_y AND c.center_y <= p.bottom
                GROUP BY c.page_no, c.candidate_index, p.item_ref
            )
            SELECT page_no, candidate_index, item_ref,
                   CASE WHEN match_count = 1 THEN candidate ELSE NULL END AS candidate,
                   top, bottom, spans, match_count
            FROM (
                SELECT *, count(*) OVER (PARTITION BY page_no, candidate_index) AS match_count
                FROM matches
            ) ORDER BY page_no, candidate_index, item_ref
            """
        ).to_arrow_reader(batch_size=1024)
        try:
            for batch in result:
                for row in batch.to_pylist():
                    yield InlineGeometryMatch(
                        row["page_no"],
                        row["candidate_index"],
                        row["item_ref"],
                        row["match_count"],
                        candidate_from_payload(row["candidate"], self.payload_family)
                        if row["match_count"] == 1
                        else None,
                        row["top"],
                        row["bottom"],
                        frozenset(tuple(span) for span in row["spans"]),
                    )
        finally:
            result.close()

    def intersecting_cells(self, nodes: dict[str, Any], candidates: Any) -> set[Any]:
        if not self.available or not candidates:
            return set()
        rows = [
            self._box(
                candidate.page_no,
                nodes[candidate.table_ref].data.table_cells[candidate.cell_index].bbox,
                item_ref=candidate.table_ref,
                index=candidate.cell_index,
                span_start=0,
                span_end=0,
            )
            for candidate in candidates
        ]
        self.connection.register("cell_boxes", pa.Table.from_pylist(rows, schema=_BOX_SCHEMA))
        result = self.connection.sql(
            """
            SELECT DISTINCT b.page_no, b.item_ref, b.index
            FROM cell_boxes b JOIN candidate_geometry c
              ON b.page_no = c.page_no
             AND b.left < c.x_right AND c.x_left < b.right
             AND b.top < c.max_y AND c.min_y < b.bottom
            """
        ).to_arrow_table()
        keys = {(row["page_no"], row["item_ref"], row["index"]) for row in result.to_pylist()}
        return {
            candidate
            for candidate in candidates
            if (candidate.page_no, candidate.table_ref, candidate.cell_index) in keys
        }
