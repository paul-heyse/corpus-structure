"""Same-view M1 preparation: shared source custody and compact region selections.

Every selected native item has a disposition. Unknown text receives the broad prose
packs; missing, empty and over-limit projections remain in the region denominator.
Related-source and recognition coordinates are deliberately outside this first route.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from corpus_structure.ingest.annotations import (
    AnnotationInput,
    AnnotationProduct,
    AnnotationProfile,
    AnnotationUnavailable,
    annotate,
)
from corpus_structure.ingest.pdf_hierarchy import ProjectedPiece
from corpus_structure.ingest.sentences import Block, pipeline, prepare_layout
from corpus_structure.semantic.proposals import NativeFrameSource, native_source_frame
from corpus_structure.semantic.source_contexts import (
    NativeSourceContext,
    NativeSourcePin,
    SourceSlice,
)

PROSE_FAMILIES = ("definition", "assertion", "measurement")
POLICY = "m1-canonical-same-view-candidates-1"


@dataclass(frozen=True, slots=True)
class ContextSelection:
    region: str
    start: int
    end: int
    families: tuple[str, ...]
    reason: str

    def context(
        self, source: NativeFrameSource, *, max_chars: int, max_pieces: int
    ) -> NativeSourceContext:
        return NativeSourceContext(
            source,
            (),
            (SourceSlice(source.source_view_id, self.start, self.end),),
            ",".join(self.families),
            POLICY,
            self.reason,
            max_chars=max_chars,
            max_pieces=max_pieces,
        )


@dataclass(frozen=True, slots=True)
class RegionDisposition:
    pointer: str
    label: str
    piece_indices: tuple[int, ...]
    families: tuple[str, ...]
    outcome: str
    reason: str
    selections: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class PreparedCandidateSource:
    source: NativeFrameSource
    annotations: tuple[AnnotationProduct, ...]
    selections: tuple[ContextSelection, ...]
    regions: tuple[RegionDisposition, ...]
    annotation_errors: tuple[str, ...] = ()
    exclusions: tuple[str, ...] = (
        "related-source context retrieval unsupported in canonical same-view route",
        "recognition alternative anchors unsupported; canonical native projection only",
        "candidate-only; no acceptance, calibration or production selection",
    )


def prepare_source(
    view: Any,
    *,
    profile: AnnotationProfile | None = None,
    max_chars: int = 4096,
    max_pieces: int = 64,
    max_annotation_chars: int = 32768,
    check_active: Callable[[], None] = lambda: None,
) -> PreparedCandidateSource:
    """Prepare annotations once per projected native piece, then coherent windows.

    Whole sentences are the smallest prose windows. An oversized sentence or native
    structure is explicitly limited rather than truncated. Native worker word/subword
    preparation remains a later, separately reported admission boundary.
    """
    if min(max_chars, max_pieces, max_annotation_chars) < 1:
        raise ValueError("source preparation bounds must be positive")
    profile = profile or AnnotationProfile()
    frame = native_source_frame(view, ())
    pin = NativeSourcePin.from_source(frame)
    nlp = pipeline(profile.configuration)
    by_pointer = {item["self_ref"]: item for item in view.items}
    projected: dict[str, list[int]] = {}
    piece_starts = tuple(piece["start"] for piece in view.pieces)
    piece_ends = tuple(piece["end"] for piece in view.pieces)
    for index, piece in enumerate(view.pieces):
        if piece["kind"] == "native_text":
            projected.setdefault(piece["item_ref"], []).append(index)

    def block_owner(pointer: str) -> str:
        node = by_pointer[pointer]
        parent = by_pointer.get(node.get("parent", {}).get("$ref"), {})
        if node.get("label") == "inline":
            return node.get("parent", {}).get("$ref", pointer)
        return (
            parent.get("parent", {}).get("$ref", pointer)
            if parent.get("label") == "inline"
            else pointer
        )

    blocks: dict[str, list[int]] = {}
    for pointer, indices in projected.items():
        blocks.setdefault(block_owner(pointer), []).extend(indices)
    inputs = []
    annotation_blocks = []
    for pointer, indices in blocks.items():
        if by_pointer.get(pointer, {}).get("label") == "table":
            annotation_blocks.extend(
                (pointer, [index], f"{pointer}:cell:{view.pieces[index].get('cell_index', index)}")
                for index in indices
            )
        else:
            annotation_blocks.append((pointer, indices, pointer))
    for pointer, unsorted, block_id in annotation_blocks:
        check_active()
        indices = sorted(unsorted)
        start, end = view.pieces[indices[0]]["start"], view.pieces[indices[-1]]["end"]
        if end - start > max_annotation_chars:
            continue
        node = by_pointer.get(pointer, {})
        text = view.text[start:end]
        if not text.strip():
            continue
        math, display, references = [], [], []
        for index in indices:
            piece = view.pieces[index]
            child = by_pointer[piece["item_ref"]]
            extent = (piece["start"] - start, piece["end"] - start)
            if child.get("label") == "formula":
                math.append(extent)
                if by_pointer.get(child.get("parent", {}).get("$ref"), {}).get("label") != "inline":
                    display.append(extent)
            if child.get("label") in {"reference", "reference_marker"}:
                references.append(extent)
        block = Block(text, tuple(math), tuple(display), tuple(references))
        layout = prepare_layout(nlp, block, start=start)
        kind = (
            "table_cell"
            if node.get("label") == "table"
            else "list_item"
            if node.get("label") == "list_item"
            else "caption"
            if node.get("label") == "caption"
            else "paragraph"
        )
        pieces = tuple(
            ProjectedPiece(**piece) for piece in view.pieces[indices[0] : indices[-1] + 1]
        )
        inputs.append(AnnotationInput(pin, block_id, kind, block, layout, pieces))
    products = []
    annotation_errors = []
    try:
        for product in annotate(inputs, profile):
            check_active()
            products.append(product)
    except AnnotationUnavailable as error:
        annotation_errors.append(str(error))
    annotated = {product.block_id: product for product in products}
    selections = []
    selected_ranges = {}
    regions = []
    for node in view.items:
        check_active()
        pointer, label = node["self_ref"], node.get("label", "unknown")
        owner = block_owner(pointer)
        indices = tuple(sorted(blocks.get(owner, ())))
        structural = (
            "table"
            if label == "table" or pointer.startswith("#/tables/")
            else "formula"
            if label == "formula"
            else None
        )
        families = (
            (("formula_context" if structural == "formula" else structural),)
            if structural
            else PROSE_FAMILIES
        )
        chosen = []
        limits = []
        if not indices:
            outcome, reason = (
                "unsupported",
                "no canonical projected text; native/recognition anchors remain pending",
            )
        elif not any(
            view.text[view.pieces[i]["start"] : view.pieces[i]["end"]].strip() for i in indices
        ):
            outcome, reason = "empty", "inspected canonical projection is empty"
        else:
            ranges = []
            if structural:
                direct = tuple(projected.get(pointer, ())) if structural == "formula" else indices
                ranges = (
                    [(view.pieces[direct[0]]["start"], view.pieces[direct[-1]]["end"])]
                    if direct
                    else []
                )
            else:
                for a, b in [(view.pieces[indices[0]]["start"], view.pieces[indices[-1]]["end"])]:
                    if b - a <= max_chars:
                        ranges.append((a, b))
                        continue
                    product = annotated.get(owner)
                    if product is None:
                        limits.append("annotation preparation bound exceeded")
                        continue
                    cursor = a
                    for sentence in product.sentences:
                        if sentence.end - cursor > max_chars:
                            if cursor < sentence.start and sentence.start - cursor <= max_chars:
                                ranges.append((cursor, sentence.start))
                            cursor = sentence.start
                        if sentence.end - cursor > max_chars:
                            limits.append(
                                "coherent sentence exceeds character bound:"
                                f"{sentence.start}:{sentence.end}"
                            )
                            cursor = sentence.end
                        elif sentence.end - cursor >= max_chars // 2:
                            ranges.append((cursor, sentence.end))
                            cursor = sentence.end
                    if cursor < b:
                        if b - cursor <= max_chars:
                            ranges.append((cursor, b))
                        else:
                            limits.append("remaining coherent region exceeds character bound")
            for a, b in ranges:
                count = bisect_left(piece_starts, b) - bisect_right(piece_ends, a)
                if b - a > max_chars or count > max_pieces:
                    limits.append(f"native context bound exceeded:{a}:{b}")
                    continue
                if not view.text[a:b].strip():
                    continue
                key = (a, b, families)
                if key not in selected_ranges:
                    selected_ranges[key] = len(selections)
                    selections.append(
                        ContextSelection(
                            pointer if structural else owner,
                            a,
                            b,
                            families,
                            "native structural trigger"
                            if structural
                            else "bounded broad fallback; no classifier exclusion",
                        )
                    )
                chosen.append(selected_ranges[key])
            outcome = "partial" if limits else "selected" if chosen else "empty"
            reason = (
                "; ".join(limits)
                if limits
                else "all canonical region windows retained"
                if chosen
                else "no nonempty canonical window"
            )
        regions.append(
            RegionDisposition(pointer, label, indices, families, outcome, reason, tuple(chosen))
        )
    return PreparedCandidateSource(
        frame, tuple(products), tuple(selections), tuple(regions), tuple(annotation_errors)
    )
