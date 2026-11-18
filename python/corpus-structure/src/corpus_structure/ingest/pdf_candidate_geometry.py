"""Selected-page Arrow geometry; native Docling nodes retain text/structure authority."""

from __future__ import annotations

from collections.abc import Collection, Generator
from dataclasses import dataclass
from itertools import chain
from typing import Any

import duckdb
import pyarrow as pa
from duckdb import coalesce, col, count_all, fn, lit, star, when

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
            heights = self.connection.from_arrow(
                pa.table(
                    {
                        "page_no": pa.array(sorted(page_nos), type=pa.int64()),
                        "height": pa.array(
                            [document.pages[number].size.height for number in sorted(page_nos)],
                            type=pa.float64(),
                        ),
                    }
                )
            ).set_alias("h")
            # Assign ordinals before geometry predicates and consume the single-pass
            # Arrow input once into a connection-owned relation shared by both readers.
            flattened = self.connection.from_arrow(self.reader).select(
                col("page_no"), fn("unnest", col("candidates")).alias("candidate"),
                (fn("generate_subscripts", col("candidates"), lit(1)) - 1).alias("candidate_index"),
            ).set_alias("f")
            numeric_boxes = flattened.join(
                heights, col("f", "page_no") == col("h", "page_no")
            ).select(
                col("f", "page_no"), col("candidate_index"), col("candidate"), col("height"),
                *(
                    coalesce(
                        col("candidate")[edge]["integer"].cast("DOUBLE"),
                        col("candidate")[edge]["binary64"],
                    ).alias(name)
                    for edge, name in (
                        ("left", "x_left"), ("right", "x_right"),
                        ("top", "source_top"), ("bottom", "source_bottom"),
                    )
                ),
            )
            normalized = numeric_boxes.select(
                col("page_no"), col("candidate_index"), col("candidate"),
                col("x_left"), col("x_right"),
                *(
                    when(col("candidate")["origin"] == "BOTTOMLEFT")
                    .then(col("height") - col(source)).otherwise(col(source)).alias(edge)
                    for source, edge in (("source_top", "top"), ("source_bottom", "bottom"))
                ),
            )
            normalized.select(
                star(), ((col("x_left") + col("x_right")) / 2).alias("center_x"),
                ((col("top") + col("bottom")) / 2).alias("center_y"),
                fn("least", col("top"), col("bottom")).alias("min_y"),
                fn("greatest", col("top"), col("bottom")).alias("max_y"),
            ).create("candidate_geometry")
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
    ) -> Generator[InlineGeometryMatch]:
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
        prose = self.connection.from_arrow(pa.Table.from_pylist(rows, schema=_BOX_SCHEMA)).set_alias("p")
        geometry = self.connection.table("candidate_geometry").set_alias("c")
        matches = geometry.join(
            prose,
            (col("c", "page_no") == col("p", "page_no"))
            & (col("p", "left") <= col("c", "center_x"))
            & (col("c", "center_x") <= col("p", "right"))
            & (col("p", "top") <= col("c", "center_y"))
            & (col("c", "center_y") <= col("p", "bottom")),
        ).aggregate([
            col("c", "page_no"), col("c", "candidate_index"), col("p", "item_ref"),
            fn("any_value", col("c", "candidate")).alias("candidate"),
            fn("any_value", col("c", "top")).alias("top"),
            fn("any_value", col("c", "bottom")).alias("bottom"),
            fn("list_distinct", fn("list", fn("list_value", col("p", "span_start"), col("p", "span_end")))).alias("spans"),
        ])
        counted = matches.select(
            star(), count_all().over(partition_by=[col("page_no"), col("candidate_index")]).alias("match_count")
        )
        result = counted.select(
            col("page_no"), col("candidate_index"), col("item_ref"),
            when(col("match_count") == 1).then(col("candidate")).otherwise(None).alias("candidate"),
            col("top"), col("bottom"), col("spans"), col("match_count"),
        ).sort(col("page_no"), col("candidate_index"), col("item_ref")).to_arrow_reader(batch_size=1024)
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
        boxes = self.connection.from_arrow(pa.Table.from_pylist(rows, schema=_BOX_SCHEMA)).set_alias("b")
        geometry = self.connection.table("candidate_geometry").set_alias("c")
        result = boxes.join(
            geometry,
            (col("b", "page_no") == col("c", "page_no"))
            & (col("b", "left") < col("c", "x_right"))
            & (col("c", "x_left") < col("b", "right"))
            & (col("b", "top") < col("c", "max_y"))
            & (col("c", "min_y") < col("b", "bottom")),
        ).select(col("b", "page_no"), col("b", "item_ref"), col("b", "index")).distinct().to_arrow_table()
        keys = {(row["page_no"], row["item_ref"], row["index"]) for row in result.to_pylist()}
        return {
            candidate
            for candidate in candidates
            if (candidate.page_no, candidate.table_ref, candidate.cell_index) in keys
        }
