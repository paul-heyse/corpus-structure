"""Demanded native math enrichment; retained PDF and native products remain the source owners."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import asdict, dataclass, replace
from functools import cmp_to_key
from typing import Any, Literal

from .pdf import CellCandidate, CellEnrichment, PdfConversion, PdfConverter
from .pdf_candidate_geometry import CandidateGeometry, CandidatePageStatus, candidate_page_status
from .pdf_candidate_source import (
    CandidatePageSource,
    OverlayCandidatePageSource,
    as_candidate_source,
)
from .pdf_candidates import CandidatePage, InlineCandidate
from .pdf_health import FormulaOutcome, ObservedFormulaStage
from .pdf_hierarchy import NativeSnapshot, load_snapshot, native_nodes, snapshot


class RecognitionUnavailable(ValueError):
    """A required native candidate cannot yet be qualified; never successful empty coverage."""


class PdfRegionRenderer:
    """One owned PDF renderer, at most one detached page image live between crops."""

    def __init__(
        self, original: bytes, *, scale: float = 2.0, padding_points: float = 0.75
    ) -> None:
        import pypdfium2

        self.document = pypdfium2.PdfDocument(original)
        self.scale = scale
        self.padding_points = padding_points
        self._page_no: int | None = None
        self._image: Any = None

    def __enter__(self) -> PdfRegionRenderer:
        return self

    def __exit__(self, *args: Any) -> None:
        if self._image is not None:
            self._image.close()
        self.document.close()

    def __call__(self, page_no: int, bbox: Any) -> Any:
        if self._page_no != page_no:
            if self._image is not None:
                self._image.close()
            page = self.document[page_no - 1]
            try:
                bitmap = page.render(scale=self.scale)
                try:
                    self._image = bitmap.to_pil().copy()
                finally:
                    bitmap.close()
            finally:
                page.close()
            self._page_no = page_no
        height = self._image.height / self.scale
        box = bbox.to_top_left_origin(height)
        box = box.model_copy(
            update=dict(
                l=box.l - self.padding_points,
                t=box.t - self.padding_points,
                r=box.r + self.padding_points,
                b=box.b + self.padding_points,
            )
        )
        left = max(0, int(box.l * self.scale))
        top = max(0, int(box.t * self.scale))
        right = min(self._image.width, int(box.r * self.scale) + 1)
        bottom = min(self._image.height, int(box.b * self.scale) + 1)
        if left >= right or top >= bottom:
            raise RecognitionUnavailable("native math candidate has an empty PDF crop")
        return self._image.crop((left, top, right, bottom))


def table_candidates(document: Any, selected: frozenset[str]) -> tuple[CellCandidate, ...]:
    """Every nonempty cell in selected native tables, without a mathematical-looking filter."""
    nodes = native_nodes(document)
    candidates = []
    for pointer in selected:
        item = nodes[pointer]
        if not hasattr(item, "data") or not hasattr(item.data, "table_cells"):
            continue
        for index, cell in enumerate(item.data.table_cells):
            if not cell.text.strip():
                continue
            if cell.bbox is None:
                raise RecognitionUnavailable("nonempty table cell has no native crop geometry")
            pages = {p.page_no for p in item.prov}
            if len(pages) != 1:
                raise RecognitionUnavailable(
                    "cell page correspondence is ambiguous in a multi-page native table"
                )
            candidates.append(CellCandidate(pointer, index, next(iter(pages))))
    return tuple(sorted(candidates, key=lambda c: (c.page_no, c.table_ref, c.cell_index)))


@dataclass(frozen=True, slots=True)
class PositionedCandidate:
    item_ref: str
    start: int
    end: int
    candidate: InlineCandidate
    regions: tuple[InlineCandidate, ...] = ()


@dataclass(frozen=True, slots=True)
class InlineAlignmentReport:
    page_no: int
    candidate_index: int
    item_pointers: tuple[str, ...]
    basis: Literal["ambiguous-native-items", "unmatched-native-text"]
    detail: str
    outcome: Literal["unresolved"] = "unresolved"

    def to_wire(self) -> dict[str, Any]:
        value = asdict(self)
        value["item_pointers"] = list(self.item_pointers)
        return value


@dataclass(frozen=True, slots=True)
class InlineDiscovery:
    candidates: tuple[PositionedCandidate, ...]
    reports: tuple[InlineAlignmentReport, ...]


def _ordered_context_candidates(candidates, geometry_anchors):
    """Unique reading order within ONE native prose item and its own provenance spans."""
    anchors = {}
    for index, candidate in candidates:
        spans, top, bottom = geometry_anchors[candidate.page_no, index]
        if len(spans) != 1:
            return None
        anchors[candidate.page_no, index] = (next(iter(spans)), top, bottom)

    def compare(left, right):
        li, a = left
        ri, b = right
        a_span, a_top, a_bottom = anchors[a.page_no, li]
        b_span, b_top, b_bottom = anchors[b.page_no, ri]
        if a_span != b_span:
            if a_span[1] <= b_span[0]:
                return -1
            if b_span[1] <= a_span[0]:
                return 1
            return 0
        if a.page_no != b.page_no:
            return 0
        if a_bottom <= b_top:
            return -1
        if b_bottom <= a_top:
            return 1
        same_line = (
            abs((a_top + a_bottom - b_top - b_bottom) / 2)
            <= min(a_bottom - a_top, b_bottom - b_top) / 2
        )
        if same_line and a.right <= b.left:
            return -1
        if same_line and b.right <= a.left:
            return 1
        return 0

    ordered = sorted(candidates, key=cmp_to_key(compare))
    if any(
        compare(left, right) != -1 for i, left in enumerate(ordered) for right in ordered[i + 1 :]
    ):
        return None
    return ordered


def positioned_inline_candidates(
    document: Any,
    pages: tuple[CandidatePage, ...] | CandidatePageSource,
    selected: frozenset[str],
    *,
    geometry: CandidateGeometry | None = None,
) -> InlineDiscovery:
    """Locate exact native anchors; retain unresolved source custody without guessed offsets."""
    nodes = native_nodes(document)
    if geometry is None:
        page_nos = {
            prov.page_no for pointer in selected for prov in getattr(nodes[pointer], "prov", ())
        }
        with CandidateGeometry(document, as_candidate_source(pages), page_nos) as selected_geometry:
            return positioned_inline_candidates(
                document, pages, selected, geometry=selected_geometry
            )
    grouped: dict[tuple[str, str], list[tuple[int, InlineCandidate]]] = defaultdict(list)
    anchors: dict[str, dict[tuple[int, int], Any]] = defaultdict(dict)
    ambiguous: dict[tuple[int, int], list[str]] = defaultdict(list)
    reports = []
    for match in geometry.inline_matches(nodes, selected):
        if match.match_count > 1:
            ambiguous[match.page_no, match.candidate_index].append(match.item_ref)
        else:
            assert match.candidate is not None
            grouped[(match.item_ref, match.candidate.text)].append(
                (match.candidate_index, match.candidate)
            )
            anchors[match.item_ref][match.page_no, match.candidate_index] = (
                match.spans,
                match.top,
                match.bottom,
            )
    for (page_no, candidate_index), pointers in ambiguous.items():
        reports.append(
            InlineAlignmentReport(
                page_no,
                candidate_index,
                tuple(sorted(pointers)),
                "ambiguous-native-items",
                "candidate center belongs to multiple native prose items",
            )
        )
    positioned = []
    for (pointer, spelling), candidates in grouped.items():
        # Whole-word boundaries avoid matching a variable inside a prose identifier.
        pattern = (
            (
                r"(?<!\w)" + re.escape(spelling) + r"(?!\w)"
                if spelling.isalnum()
                else re.escape(spelling)
            )
            if spelling
            else r"\s*"
        )
        offsets = list(re.finditer(pattern, nodes[pointer].text))
        if spelling and len(offsets) == len(candidates):
            ordered = _ordered_context_candidates(candidates, anchors[pointer])
            if len(candidates) == 1 or ordered is not None:
                positioned.extend(
                    PositionedCandidate(pointer, m.start(), m.end(), candidate)
                    for m, (_, candidate) in zip(
                        offsets, candidates if ordered is None else ordered, strict=True
                    )
                )
                continue
        contexts = defaultdict(list)
        for candidate_index, candidate in candidates:
            contexts[candidate.before, candidate.after].append((candidate_index, candidate))
        for (before_text, after_text), context_candidates in contexts.items():

            def context_pattern(value: str) -> str:
                return r"\s+".join(re.escape(word) for word in value.split())

            before = context_pattern(before_text)
            after = context_pattern(after_text)
            qualified = (
                (before + r"\s*" if before else "")
                + r"(?P<math>"
                + pattern
                + r")"
                + (r"\s*" + after if after else "")
            )
            matches = list(re.finditer(qualified, nodes[pointer].text))
            ordered = (
                _ordered_context_candidates(context_candidates, anchors[pointer])
                if len(matches) == len(context_candidates)
                else None
            )
            if len(matches) == 1:
                assignments = [(candidate, matches[0]) for _, candidate in context_candidates]
            elif len(matches) > 1 and ordered is not None:
                assignments = [
                    (candidate, match)
                    for (_, candidate), match in zip(ordered, matches, strict=True)
                ]
            else:
                for candidate_index, candidate in context_candidates:
                    reports.append(
                        InlineAlignmentReport(
                            candidate.page_no,
                            candidate_index,
                            (pointer,),
                            "unmatched-native-text",
                            "native word context has no unique exact projection "
                            "anchor or reading order",
                        )
                    )
                continue
            positioned.extend(
                PositionedCandidate(pointer, match.start("math"), match.end("math"), candidate)
                for candidate, match in assignments
            )
    by_anchor: dict[tuple[str, int, int], list[PositionedCandidate]] = defaultdict(list)
    for part in positioned:
        by_anchor[(part.item_ref, part.start, part.end)].append(part)
    merged = []
    for (pointer, start, end), parts in by_anchor.items():
        regions = tuple(
            sorted((part.candidate for part in parts), key=lambda c: (c.page_no, c.top, c.left))
        )
        merged.append(
            PositionedCandidate(
                pointer, start, end, regions[0], regions if len(regions) > 1 else ()
            )
        )
    return InlineDiscovery(
        tuple(sorted(merged, key=lambda c: (c.item_ref, c.start, c.end))), tuple(reports)
    )


def enrich_inline(
    source: NativeSnapshot,
    candidates: tuple[PositionedCandidate, ...],
    *,
    stage: ObservedFormulaStage,
    render_region: Any,
) -> CellEnrichment:

    document = load_snapshot(source)
    outcomes, mappings = apply_inline(
        document, candidates, stage=stage, render_region=render_region
    )
    return CellEnrichment(source.digest, snapshot(document), outcomes, mappings)


def apply_inline(
    document: Any,
    candidates: tuple[PositionedCandidate, ...],
    *,
    stage: ObservedFormulaStage,
    render_region: Any,
):
    """Apply selected inline decomposition within one owned document-enrichment operation."""
    from docling.datamodel.base_models import ItemAndImageEnrichmentElement
    from docling_core.types.doc import BoundingBox, CoordOrigin, DocItemLabel, ProvenanceItem

    nodes = native_nodes(document)
    grouped: dict[str, list[PositionedCandidate]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate.item_ref].append(candidate)
    start = len(stage.outcomes)
    pending = []
    mappings = []
    size = max(1, stage.elements_batch_size)

    def flush():
        try:
            if len(list(stage(document, pending))) != len(pending):
                raise RecognitionUnavailable(
                    "native inline inference did not return its complete batch"
                )
        finally:
            for element in pending:
                element.image.close()
            pending.clear()

    for pointer, parts in grouped.items():
        item = nodes[pointer]
        original = item.text
        previous = 0
        for part in parts:
            source_span = original[part.start : part.end]
            vector_anchor = (
                part.candidate.basis == "native-vector-gap-v1" and not source_span.strip()
            )
            if part.start < previous or (not vector_anchor and source_span != part.candidate.text):
                raise RecognitionUnavailable(
                    "inline candidate offsets overlap or differ from native text"
                )
            previous = part.end
        group = document.add_inline_group(parent=item)
        item.text = ""  # Raw original stays in the parent product and this item's orig field.
        position = 0
        following_gap = False
        for part in parts:
            if position < part.start:
                raw = original[position : part.start]
                projected = (" " if following_gap and raw and raw[0].isalnum() else "") + raw
                child = document.add_text(
                    label=DocItemLabel.TEXT, text=projected, orig=raw, parent=group
                )
                mappings.append(
                    dict(
                        pointer=child.self_ref,
                        origin_pointer=pointer,
                        source_field="text",
                        start=position,
                        end=part.start,
                        kind="native_text_range",
                    )
                )
            c = part.candidate
            regions = part.regions or (c,)
            boxes = [
                BoundingBox(
                    l=r.left, t=r.top, r=r.right, b=r.bottom, coord_origin=CoordOrigin(r.origin)
                )
                for r in regions
            ]
            formula = document.add_text(
                label=DocItemLabel.FORMULA, text=c.text, orig=c.text, parent=group
            )
            formula.prov = [
                ProvenanceItem(page_no=r.page_no, bbox=box, charspan=(0, len(c.text)))
                for r, box in zip(regions, boxes, strict=True)
            ]
            crops = [render_region(r.page_no, box) for r, box in zip(regions, boxes, strict=True)]
            if len(crops) == 1:
                image = crops[0]
            else:
                from PIL import Image

                image = Image.new(
                    "RGB",
                    (
                        sum(crop.width for crop in crops) + 4 * (len(crops) - 1),
                        max(crop.height for crop in crops),
                    ),
                    "white",
                )
                x = 0
                for crop in crops:
                    image.paste(crop, (x, image.height - crop.height))
                    x += crop.width + 4
                    crop.close()
            pending.append(ItemAndImageEnrichmentElement(item=formula, image=image))
            if len(pending) >= size:
                flush()
            mappings.append(
                dict(
                    pointer=formula.self_ref,
                    origin_pointer=pointer,
                    source_field="text",
                    start=part.start,
                    end=part.end,
                    kind="vector_region_anchor" if not c.text else "native_text_range",
                )
            )
            position = part.end
            following_gap = not c.text
        if position < len(original):
            raw = original[position:]
            projected = (" " if following_gap and raw and raw[0].isalnum() else "") + raw
            child = document.add_text(
                label=DocItemLabel.TEXT, text=projected, orig=raw, parent=group
            )
            mappings.append(
                dict(
                    pointer=child.self_ref,
                    origin_pointer=pointer,
                    source_field="text",
                    start=position,
                    end=len(original),
                    kind="native_text_range",
                )
            )
    if pending:
        flush()
    return tuple(stage.outcomes[start:]), tuple(mappings)


def classify_cells(
    document: Any,
    candidates: tuple[CellCandidate, ...],
    pages: tuple[CandidatePage, ...] | CandidatePageSource,
    *,
    math_pattern: str,
    prose_pattern: str,
    geometry: CandidateGeometry | None = None,
    page_status: dict[int, CandidatePageStatus] | None = None,
) -> tuple[tuple[CellCandidate, ...], list[dict[str, Any]]]:
    """Account for every cell before recognition; nonempty model output is not a classifier."""
    nodes = native_nodes(document)
    page_nos = {candidate.page_no for candidate in candidates}
    source = as_candidate_source(pages)
    if geometry is None:
        with CandidateGeometry(document, source, page_nos) as selected_geometry:
            return classify_cells(
                document,
                candidates,
                source,
                math_pattern=math_pattern,
                prose_pattern=prose_pattern,
                geometry=selected_geometry,
                page_status=page_status,
            )
    by_page = page_status if page_status is not None else candidate_page_status(source, page_nos)
    intersections = geometry.intersecting_cells(nodes, candidates)
    demanded = []
    reports = []
    for candidate in candidates:
        cell = nodes[candidate.table_ref].data.table_cells[candidate.cell_index]
        page = by_page.get(candidate.page_no)
        intersects = candidate in intersections
        rich = getattr(cell, "ref", None)
        if rich is not None:
            reports.append(
                dict(
                    table_pointer=candidate.table_ref,
                    cell_index=candidate.cell_index,
                    page_no=candidate.page_no,
                    classification="math",
                    basis="native-rich-reference",
                    outcome="unknown",
                    formula_pointer=rich.cref,
                )
            )
            continue
        if intersects:
            classification, basis = "math", "native-candidate-intersection"
        elif re.search(math_pattern, cell.text):
            classification, basis = "math", "native-math-token"
        elif page and page.usable_words and re.fullmatch(prose_pattern, cell.text.strip()):
            classification, basis = (
                "prose",
                "ocr-word-text" if page.has_ocr_regions else "native-word-text",
            )
        else:
            classification, basis = "unknown", "unresolved-native-evidence"
        reports.append(
            dict(
                table_pointer=candidate.table_ref,
                cell_index=candidate.cell_index,
                page_no=candidate.page_no,
                classification=classification,
                basis=basis,
                outcome="not_requested" if classification == "prose" else "unknown",
            )
        )
        if classification == "math":
            demanded.append(candidate)
    return tuple(demanded), reports


@dataclass(frozen=True, slots=True)
class PdfEnrichmentRequest:
    conversion: PdfConversion
    original: bytes
    selected: frozenset[str]
    cell_math_pattern: str
    cell_prose_pattern: str
    crop_padding_points: float


@dataclass(frozen=True, slots=True)
class PdfEnrichmentResult:
    native: NativeSnapshot
    outcomes: tuple[FormulaOutcome, ...]
    mappings: tuple[dict[str, Any], ...]
    cell_reports: tuple[dict[str, Any], ...]
    candidate_pages: CandidatePageSource
    packages: tuple[tuple[str, str], ...]
    runtime: tuple[tuple[str, str], ...]
    effective_options: bytes
    alignment_reports: tuple[InlineAlignmentReport, ...] = ()


def compute_enrichment(
    request: PdfEnrichmentRequest, converter: PdfConverter
) -> PdfEnrichmentResult:
    """Finite native compute boundary: no Reader, database connection or publication handle."""
    from hashlib import sha256

    from .pdf import apply_cells, pdf_package_versions
    from .pdf_candidates import rediscover_candidates

    if sha256(request.original).hexdigest() != request.conversion.original_digest:
        raise ValueError("enrichment original differs from its pinned native product")
    document = load_snapshot(request.conversion.native)
    nodes = native_nodes(document)
    if not request.selected <= nodes.keys():
        raise ValueError("enrichment selection names missing native occurrences")
    all_pages = {
        prov.page_no for pointer in request.selected for prov in getattr(nodes[pointer], "prov", ())
    }
    source = as_candidate_source(request.conversion.inline_candidates)
    page_status = candidate_page_status(source, all_pages)
    overrides: dict[int, CandidatePage] = {}
    absent = {
        number
        for number in all_pages
        if number not in page_status or not page_status[number].has_vectors
    }
    if absent:
        # OCR words are hydrated only when rediscovery must merge recovered vectors.
        previous_ocr = {
            page.page_no: page
            for page in source.iter_pages(
                {
                    number
                    for number in absent
                    if number in page_status and page_status[number].has_ocr_regions
                }
            )
        }
        for discovered in rediscover_candidates(
            request.original,
            tuple(sorted(absent)),
            parser_threads=converter.recipe.parser_threads,
        ):
            previous = previous_ocr.get(discovered.page_no)
            if previous is not None and previous.ocr_regions:
                # Rediscovery recovers native vector availability, not the OCR run's words.
                # Preserve observed OCR custody instead of replacing it with corrupt native text.
                vectors = tuple(
                    candidate
                    for candidate in discovered.candidates
                    if candidate.basis == "native-vector-gap-v1"
                    and previous.native_text_quality != "broken"
                )
                overrides[discovered.page_no] = replace(
                    previous,
                    has_vectors=discovered.has_vectors,
                    candidates=previous.candidates + vectors,
                )
            else:
                overrides[discovered.page_no] = discovered
    candidates = OverlayCandidatePageSource(source, overrides)
    if overrides:
        page_status = candidate_page_status(candidates, all_pages)
    cells = table_candidates(document, request.selected)
    with CandidateGeometry(document, candidates, all_pages) as geometry:
        demanded, reports = classify_cells(
            document,
            cells,
            candidates,
            math_pattern=request.cell_math_pattern,
            prose_pattern=request.cell_prose_pattern,
            geometry=geometry,
            page_status=page_status,
        )
        discovery = positioned_inline_candidates(
            document, candidates, request.selected, geometry=geometry
        )
    repair_pages = {
        report.page_no
        for report in discovery.reports
        if report.basis == "unmatched-native-text"
        and not page_status[report.page_no].has_ocr_regions
    }
    if repair_pages:
        # Older captures excluded punctuation whose font metric box slightly overlapped
        # a vector glyph. Refresh only unresolved pages through the retained PDF backend.
        for page in rediscover_candidates(
            request.original,
            tuple(sorted(repair_pages)),
            parser_threads=converter.recipe.parser_threads,
        ):
            overrides[page.page_no] = page
        candidates = OverlayCandidatePageSource(source, overrides)
        discovery = positioned_inline_candidates(document, candidates, request.selected)
    inline = discovery.candidates
    cell_outcomes: tuple[FormulaOutcome, ...] = ()
    inline_outcomes: tuple[FormulaOutcome, ...] = ()
    cell_mappings: tuple[dict[str, Any], ...] = ()
    inline_mappings: tuple[dict[str, Any], ...] = ()
    if demanded or inline:
        stage = converter.formula_stage()
        with PdfRegionRenderer(
            request.original, padding_points=request.crop_padding_points
        ) as renderer:
            cell_outcomes, cell_mappings = apply_cells(
                document, demanded, stage=stage, render_region=renderer
            )
            inline_outcomes, inline_mappings = apply_inline(
                document, inline, stage=stage, render_region=renderer
            )
    outcomes = {
        outcome.item_ref: outcome for outcome in request.conversion.formula_outcomes + cell_outcomes
    }
    mappings = {(row["origin_pointer"], row["cell_index"]): row for row in cell_mappings}
    for report in reports:
        mapped = mappings.get((report["table_pointer"], report["cell_index"]))
        if mapped is not None:
            report["formula_pointer"] = mapped["pointer"]
        pointer = report.get("formula_pointer")
        outcome = outcomes.get(pointer) if isinstance(pointer, str) else None
        if outcome is not None:
            report["outcome"] = outcome.outcome
            if outcome.error:
                report["error"] = outcome.error
    import json

    prepared_runtime = json.loads(converter.prepared_options_report)
    if not prepared_runtime:
        retained_options = json.loads(request.conversion.effective_options)
        prepared_runtime = retained_options.get("_prepared_runtime", retained_options)
    effective = prepared_runtime.get("_preparation", {}).get("effective_options")
    if effective is None:
        effective = {
            key: value for key, value in prepared_runtime.items() if not key.startswith("_")
        }
    effective_options = {
        **effective,
        "_prepared_runtime": prepared_runtime,
        "_operation_render": {
            "scale": 2.0,
            "padding_points": request.crop_padding_points,
            "coordinate_frame": "PDF-TOPLEFT-points",
            "backend": "pypdfium2",
            "image_ownership": "detached-demand-crop",
            "requested": bool(demanded or inline),
        },
    }
    return PdfEnrichmentResult(
        snapshot(document),
        cell_outcomes + inline_outcomes,
        cell_mappings + inline_mappings,
        tuple(reports),
        candidates,
        pdf_package_versions(),
        converter.runtime_bindings(),
        json.dumps(effective_options, ensure_ascii=False, allow_nan=False).encode(),
        discovery.reports,
    )
