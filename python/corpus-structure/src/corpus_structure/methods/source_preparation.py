"""M1 preparation: shared source custody and bounded typed region selections.

Every selected native item has a disposition. Unknown text receives the broad prose
packs; missing, empty and over-limit projections remain in the region denominator.
Related native sources retain independent pins; recognition alternatives remain separate.
"""

from __future__ import annotations

import json
from bisect import bisect_left, bisect_right
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
from itertools import pairwise
from typing import Any

from corpus_structure.core.method import SourcePreparationReader
from corpus_structure.ingest.annotations import (
    AnnotationInput,
    AnnotationProduct,
    AnnotationProfile,
    AnnotationUnavailable,
    annotate,
)
from corpus_structure.ingest.pdf_hierarchy import (
    ProjectedPiece,
    TextProjection,
    project_section_nodes,
    retained_formula_originals,
)
from corpus_structure.ingest.sentences import Block, pipeline, prepare_layout
from corpus_structure.semantic.declared_record_sources import (
    DeclaredNativeFrameSource,
    DeclaredSourceSlice,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.source_contexts import (
    ContextRefused,
    ContextRelationship,
    ContextRetrieval,
    NativeSourceContext,
    NativeSourcePin,
    PreparedNativeSources,
    RelatedNativeSource,
    RetrievalOutcome,
    SourceContextRequest,
    SourceFrame,
    SourceSlice,
    SyntheticText,
    source_slice,
)

PROSE_FAMILIES = ("definition", "assertion", "measurement")
POLICY = "m1-canonical-related-context-candidates-4"
POLICY_V5 = "m1-canonical-related-context-candidates-5"
POLICY_V6 = "m1-canonical-related-context-candidates-6"


@dataclass(frozen=True, slots=True)
class NativeTableTarget:
    cell_index: int
    row_extent: tuple[int, int] | None
    row_path: tuple[int, ...]
    header_path: tuple[int, ...]


def native_table_cell_projection(
    node, index, nodes, *, retained_originals: frozenset[str] = frozenset()
) -> TextProjection:
    """Use the canonical projector for rich-cell text and its exact child addresses.

    The cell's summary ``text`` is not its rich subtree projection. Child literals
    retain their own item locators; table/cell identities remain the parent's native
    cell address. Nested tabular/chart projections need a separate structural owner.
    """
    cell = node["data"]["table_cells"][index]
    reference = cell.get("ref")
    if reference is not None:
        pointer = reference.get("$ref")
        if not isinstance(pointer, str) or pointer not in nodes:
            raise ValueError("rich cell native subtree is unavailable")
        projection = project_section_nodes(
            nodes,
            "",
            pointer,
            "descendant",
            section_refs=frozenset((pointer,)),
            retained_originals=retained_originals,
        )
        if any(p.cell_index is not None for p in projection.pieces):
            raise ValueError("nested tabular rich cell requires its own structural scope")
        return replace(
            projection,
            pieces=tuple(
                replace(p, cell_index=index) if p.kind == "native_text" else p
                for p in projection.pieces
            ),
        )
    text = cell.get("text")
    if not isinstance(text, str):
        raise ValueError("native cell text is unavailable")
    return TextProjection(
        "",
        node["self_ref"],
        "descendant",
        text,
        (ProjectedPiece(node["self_ref"], 0, len(text), "native_text", index, "cell_text"),)
        if text
        else (),
    )


@dataclass(frozen=True, slots=True)
class _PreparedTableCells:
    projections: tuple[TextProjection | None, ...]
    ranges: tuple[tuple[int, int] | None, ...]
    piece_indices: tuple[int, ...]


def _prepare_table_cells(view, node, nodes, piece_lookup, retained_originals):
    projections, ranges, members = [], [], set()
    for index in range(len(node["data"]["table_cells"])):
        try:
            projection = native_table_cell_projection(
                node, index, nodes, retained_originals=retained_originals
            )
        except ValueError:
            projections.append(None)
            ranges.append(None)
            continue
        native = tuple(p for p in projection.pieces if p.kind == "native_text")
        keys = {(p.item_ref, index, p.source_field) for p in native}
        indices = sorted({i for key in keys for i in piece_lookup.get(key, ())})
        members.update(indices)
        span = (
            (view.pieces[indices[0]]["start"], view.pieces[indices[-1]]["end"]) if indices else None
        )
        valid = len(indices) == len(native) and all(
            view.pieces[i]["item_ref"] == expected.item_ref
            and view.pieces[i].get("source_field") == expected.source_field
            and view.text[view.pieces[i]["start"] : view.pieces[i]["end"]]
            == projection.text[expected.start : expected.end]
            for i, expected in zip(indices, native, strict=False)
        )
        valid = valid and (
            view.text[span[0] : span[1]] == projection.text
            if span is not None
            else projection.text == ""
        )
        projections.append(projection if valid else None)
        ranges.append(span if valid else None)
    return _PreparedTableCells(tuple(projections), tuple(ranges), tuple(sorted(members)))


def native_table_geometry(node) -> tuple[NativeTableTarget, ...]:
    """Resolve native containment paths once, preserving ambiguous paths as unresolved.

    Only declared header cells are considered for paths. Equal/crossing sibling
    bands do not choose an arbitrary header, and data-cell text never supplies one.
    """
    cells = node.get("data", {}).get("table_cells", ())

    def extent(cell, axis):
        a, b = cell.get(f"start_{axis}_offset_idx"), cell.get(f"end_{axis}_offset_idx")
        return (a, b) if type(a) is int and type(b) is int and 0 <= a < b else None

    headers = tuple(
        (index, cell, extent(cell, "row"), extent(cell, "col"))
        for index, cell in enumerate(cells)
        if cell.get("column_header") or cell.get("row_header")
    )

    def nested_path(candidates):
        ordered = sorted(candidates)
        if any(
            parent[1] > child[0] or parent[2] > child[2] or parent[3] < child[3]
            for parent, child in pairwise(ordered)
        ):
            return ()
        return tuple(candidate[4] for candidate in ordered)

    targets = []
    for index, cell in enumerate(cells):
        if cell.get("column_header") or cell.get("row_header"):
            continue
        target_row, target_col = extent(cell, "row"), extent(cell, "col")
        rows, columns = [], []
        if target_row is not None and target_col is not None:
            for other, header, row, col in headers:
                if row is None or col is None:
                    continue
                if (
                    header.get("row_header")
                    and row[0] <= target_row[0]
                    and row[1] >= target_row[1]
                    and col[1] <= target_col[0]
                ):
                    rows.append((*col, *row, other))
                if (
                    header.get("column_header")
                    and col[0] <= target_col[0]
                    and col[1] >= target_col[1]
                    and row[1] <= target_row[0]
                ):
                    columns.append((*row, *col, other))
        targets.append(
            NativeTableTarget(index, target_row, nested_path(rows), nested_path(columns))
        )
    return tuple(targets)


@dataclass(frozen=True, slots=True)
class ContextSelection:
    region: str
    start: int
    end: int
    families: tuple[str, ...]
    reason: str
    missing_roles: tuple[str, ...] = ()
    pieces: tuple[SourceSlice | DeclaredSourceSlice | SyntheticText, ...] = ()
    retrievals: tuple[ContextRetrieval, ...] = ()
    relationships: tuple[tuple[int | str, ContextRelationship, str], ...] = ()
    local_dispositions: tuple[tuple[str, str, str], ...] = ()
    # Actual native links; consumption/limits remain explicit in local_dispositions.
    local_relationships: tuple[tuple[str, ContextRelationship, str], ...] = ()
    table_targets: tuple[NativeTableTarget, ...] | None = None
    policy: str = POLICY

    def context(
        self,
        source: SourceFrame,
        *,
        max_chars: int,
        max_pieces: int,
        related: tuple[RelatedNativeSource, ...] = (),
        preparation: PreparedNativeSources | None = None,
        policy: str | None = None,
    ) -> NativeSourceContext:
        sources = {entry.source.source_key: entry.source for entry in related}
        return NativeSourceContext(
            source,
            tuple(
                RelatedNativeSource(sources[identity], relationship, reason)
                for identity, relationship, reason in self.relationships
            ),
            self.pieces or (source_slice(source, self.start, self.end),),
            ",".join(self.families),
            self.policy if policy is None else policy,
            self.reason,
            retrievals=self.retrievals,
            max_chars=max_chars,
            max_pieces=max_pieces,
            version=2 if preparation is not None else 1,
            preparation=preparation,
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
    source: SourceFrame
    annotations: tuple[AnnotationProduct, ...]
    selections: tuple[ContextSelection, ...]
    regions: tuple[RegionDisposition, ...]
    annotation_errors: tuple[str, ...] = ()
    related: tuple[RelatedNativeSource, ...] = ()
    preparation: PreparedNativeSources | None = None
    exclusions: tuple[str, ...] = (
        "bounded structural retrieval proposes context; semantic attachment remains unresolved",
        "recognition alternative anchors unsupported; canonical native projection only",
        "candidate-only; no acceptance, calibration or production selection",
    )


def _table_selections(view, node, indices, prepared_cells, *, frame, max_chars, max_pieces):
    """Keep small tables whole; dense tables use complete native rows or cells.

    A target retains every located cell fragment and its complete declared paths.
    A row that cannot fit separates independent cell targets, never cell contents or
    header paths. An indivisible over-limit cell remains an explicit region limit.
    """
    pointer = node["self_ref"]
    targets = native_table_geometry(node)
    a, b = view.pieces[indices[0]]["start"], view.pieces[indices[-1]]["end"]
    if (
        b - a <= max_chars
        and sum(piece["start"] < b and piece["end"] > a for piece in view.pieces) <= max_pieces
        and all(p is not None for p in prepared_cells.projections)
    ):
        return [
            ContextSelection(
                pointer, a, b, ("table",), "native structural trigger", table_targets=targets
            )
        ], []
    piece_starts = tuple(p["start"] for p in view.pieces)
    piece_ends = tuple(p["end"] for p in view.pieces)

    def pieces_for(group):
        required = {
            index
            for target in group
            for index in (*target.header_path, *target.row_path, target.cell_index)
        }
        selected = []
        for index in required:
            if prepared_cells.projections[index] is None:
                return None, "complete target/path cell projection unavailable"
            span = prepared_cells.ranges[index]
            if span is not None:
                selected.append((*span, index))
        pieces: list[SourceSlice | SyntheticText] = []
        previous = None
        for start, end, index in sorted(selected):
            if previous is not None and index != previous:
                pieces.append(SyntheticText("\n", "native table context cell separator"))
            pieces.append(source_slice(frame, start, end))
            previous = index
        if not pieces:
            return None, "no nonempty target/path cell projection"
        chars = sum(
            len(p.text) if isinstance(p, SyntheticText) else p.end - p.start for p in pieces
        )
        count = sum(
            1
            if isinstance(p, SyntheticText)
            else bisect_left(piece_starts, p.end) - bisect_right(piece_ends, p.start)
            for p in pieces
        )
        if chars > max_chars or count > max_pieces:
            return None, "complete target/path context bound exceeded"
        return tuple(pieces), None

    rows = {}
    for target in targets:
        # Invalid geometry never coalesces unrelated cells into an inferred row.
        key = target.row_extent if target.row_extent is not None else ("cell", target.cell_index)
        rows.setdefault(key, []).append(target)
    selections, limits = [], []
    for row in rows.values():
        groups = [tuple(row)]
        pieces, _ = pieces_for(groups[0])
        if pieces is None:
            groups = [(target,) for target in row]
        for group in groups:
            pieces, reason = pieces_for(group)
            if pieces is None:
                limits.extend(f"{pointer}/data/table_cells/{t.cell_index}: {reason}" for t in group)
                continue
            native = [p for p in pieces if isinstance(p, SourceSlice)]
            selections.append(
                ContextSelection(
                    pointer,
                    min(p.start for p in native),
                    max(p.end for p in native),
                    ("table",),
                    "bounded complete native table row"
                    if len(group) > 1
                    else "bounded native table cell",
                    pieces=pieces,
                    table_targets=group,
                )
            )
    if not targets:
        limits.append(f"{pointer}: over-limit table has no independently located data-cell targets")
    return selections, limits


def annotation_inputs(
    view: Any,
    *,
    profile: AnnotationProfile | None = None,
    max_annotation_chars: int = 32768,
    check_active: Callable[[], None] = lambda: None,
    region_pointers: tuple[str, ...] | None = None,
    source_frame: SourceFrame | None = None,
) -> tuple[AnnotationInput, ...]:
    """Prepare the canonical native blocks, table cells and protected atoms once.

    This is source preparation only. It performs tokenization but no model inference;
    consumers must account for blocks outside their supported size/selection separately.
    """
    if max_annotation_chars < 1:
        raise ValueError("annotation bound must be positive")
    profile = profile or AnnotationProfile()
    nlp = pipeline(profile.configuration)
    frame = native_source_frame(view, ()) if source_frame is None else source_frame
    pin = NativeSourcePin.from_source(frame)
    by_pointer = {item["self_ref"]: item for item in view.items}
    blocks: dict[str, list[int]] = {}
    for index, piece in enumerate(view.pieces):
        if piece["kind"] == "native_text":
            blocks.setdefault(annotation_block_owner(piece["item_ref"], by_pointer), []).append(
                index
            )
    requested_owners = (
        None
        if region_pointers is None
        else {annotation_block_owner(pointer, by_pointer) for pointer in region_pointers}
    )
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
        if requested_owners is not None and pointer not in requested_owners:
            continue
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
        if nlp is None:
            raise ValueError("annotation layout requires its locally owned language pipeline")
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
            ProjectedPiece(
                item_ref=piece.get("item_ref"),
                **{key: value for key, value in piece.items() if key != "item_ref"},
            )
            for piece in view.pieces[indices[0] : indices[-1] + 1]
        )
        inputs.append(AnnotationInput(pin, block_id, kind, block, layout, pieces))
    return tuple(inputs)


def annotation_block_owner(pointer: str, by_pointer: dict[str, Any]) -> str:
    """The canonical whole source unit owning one projected native piece."""
    node = by_pointer[pointer]
    parent = by_pointer.get(node.get("parent", {}).get("$ref"), {})
    if node.get("label") == "inline":
        return node.get("parent", {}).get("$ref", pointer)
    return (
        parent.get("parent", {}).get("$ref", pointer)
        if parent.get("label") == "inline"
        else pointer
    )


def prepare_source(
    view: Any,
    *,
    profile: AnnotationProfile | None = None,
    max_chars: int = 4096,
    max_pieces: int = 64,
    max_annotation_chars: int = 32768,
    check_active: Callable[[], None] = lambda: None,
    reader: SourcePreparationReader | None = None,
    read_budget: Any = None,
    persisted_annotations: tuple[AnnotationProduct, ...] | None = None,
    annotation_errors: tuple[str, ...] = (),
    annotations_only: bool = False,
    policy: str = POLICY,
    formula_prose: bool = False,
    region_pointers: tuple[str, ...] | None = None,
    source_frame: SourceFrame | None = None,
    context_population=None,
) -> PreparedCandidateSource:
    """Prepare annotations once per projected native piece, then coherent windows.

    Whole sentences are the smallest prose windows. An oversized sentence or native
    structure is explicitly limited rather than truncated. Native worker word/subword
    preparation remains a later, separately reported admission boundary.
    """
    if min(max_chars, max_pieces, max_annotation_chars) < 1:
        raise ValueError("source preparation bounds must be positive")
    if region_pointers is not None:
        if not region_pointers or len(set(region_pointers)) != len(region_pointers):
            raise ValueError("native region selection must be nonempty and distinct")
        missing = set(region_pointers) - {item["self_ref"] for item in view.items}
        if missing:
            raise ValueError(
                "unknown native region pointer in selected source view: "
                + ", ".join(sorted(missing))
            )
    if policy not in {POLICY, POLICY_V5, POLICY_V6} or (
        formula_prose and policy not in {POLICY_V5, POLICY_V6}
    ):
        raise ValueError("unsupported source preparation/routing policy")
    profile = profile or AnnotationProfile()
    frame = native_source_frame(view, ()) if source_frame is None else source_frame
    _pin = NativeSourcePin.from_source(frame)
    by_pointer = {item["self_ref"]: item for item in view.items}
    projected: dict[str, list[int]] = {}
    piece_starts = tuple(piece["start"] for piece in view.pieces)
    piece_ends = tuple(piece["end"] for piece in view.pieces)
    for index, piece in enumerate(view.pieces):
        if piece["kind"] == "native_text":
            projected.setdefault(piece["item_ref"], []).append(index)

    def block_owner(pointer: str) -> str:
        return annotation_block_owner(pointer, by_pointer)

    blocks: dict[str, list[int]] = {}
    for pointer, indices in projected.items():
        blocks.setdefault(block_owner(pointer), []).extend(indices)
    _requested_owners = (
        None if region_pointers is None else {block_owner(pointer) for pointer in region_pointers}
    )
    inputs = (
        ()
        if persisted_annotations is not None
        else annotation_inputs(
            view,
            profile=profile,
            max_annotation_chars=max_annotation_chars,
            check_active=check_active,
            region_pointers=region_pointers,
            source_frame=frame,
        )
    )
    products = list(persisted_annotations or ())
    errors = list(annotation_errors)
    if persisted_annotations is None:
        try:
            for product in annotate(inputs, profile):
                check_active()
                products.append(product)
        except AnnotationUnavailable as error:
            errors.append(str(error))
    if annotations_only:
        return PreparedCandidateSource(frame, tuple(products), (), (), tuple(errors))
    annotated = {product.block_id: product for product in products}
    piece_lookup = {}
    for index, piece in enumerate(view.pieces):
        if piece["kind"] == "native_text":
            key = (piece["item_ref"], piece.get("cell_index"), piece.get("source_field"))
            piece_lookup.setdefault(key, []).append(index)
    retained_originals = retained_formula_originals(view.pieces)
    prepared_tables = {
        node["self_ref"]: _prepare_table_cells(
            view, node, by_pointer, piece_lookup, retained_originals
        )
        for node in view.items
        if "table_cells" in node.get("data", {})
        and (region_pointers is None or node["self_ref"] in region_pointers)
    }
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
        prepared_cells = prepared_tables.get(pointer)
        if prepared_cells is not None:
            indices = tuple(sorted(set(indices) | set(prepared_cells.piece_indices)))
        families = (
            (("formula_context" if structural == "formula" else structural),)
            if structural
            else (*PROSE_FAMILIES, "formula_context")
            if formula_prose
            else PROSE_FAMILIES
        )
        if region_pointers is not None and pointer not in region_pointers:
            regions.append(
                RegionDisposition(
                    pointer,
                    label,
                    indices,
                    families,
                    "not_requested",
                    "outside explicit native region selection",
                    (),
                )
            )
            continue
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
            if structural == "table" and "table_cells" in node.get("data", {}):
                table_selections, table_limits = _table_selections(
                    view,
                    node,
                    indices,
                    prepared_cells,
                    frame=frame,
                    max_chars=max_chars,
                    max_pieces=max_pieces,
                )
                for selection in table_selections:
                    chosen.append(len(selections))
                    selections.append(selection)
                limits.extend(table_limits)
            elif structural:
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
    related = ()
    if source_frame is not None and reader is not None:
        raise ValueError("explicit source-frame preparation requires declared related inputs")
    if context_population is not None and source_frame is None:
        raise ValueError("declared related population requires an explicit source frame")
    if reader is not None or context_population is not None:
        selections, related = _widen_contexts(
            view,
            frame,
            selections,
            reader=reader,
            read_budget=read_budget,
            context_population=context_population,
            max_chars=max_chars,
            max_pieces=max_pieces,
            check_active=check_active,
        )
        for index, region in enumerate(regions):
            if region.families != ("formula_context",):
                continue
            incomplete = [
                (pointer, reason)
                for selected in region.selections
                for pointer, outcome, reason in selections[selected].local_dispositions
                if outcome != RetrievalOutcome.SELECTED.value
                and pointer
                in {
                    p
                    for p, relation, _ in selections[selected].local_relationships
                    if relation == ContextRelationship.ANCESTOR
                }
            ]
            if incomplete:
                regions[index] = replace(
                    region,
                    outcome="partial",
                    reason="; ".join(f"{pointer}: {reason}" for pointer, reason in incomplete),
                )
    preparation = PreparedNativeSources(
        (frame, *(entry.source for entry in related)), max_sources=9
    )
    if policy in {POLICY_V5, POLICY_V6}:
        selections = [replace(selection, policy=policy) for selection in selections]
        original_count = len(selections)
        selections, regions = _formula_windows(
            view,
            frame,
            selections,
            regions,
            tuple(products),
            related,
            preparation,
            max_chars=max_chars,
            max_pieces=max_pieces,
            check_active=check_active,
        )
        if policy == POLICY_V6:
            selections, regions = _prose_formula_neighborhoods(
                selections, regions, first_window=original_count
            )
    return PreparedCandidateSource(
        frame,
        tuple(products),
        tuple(selections),
        tuple(regions),
        tuple(errors),
        related,
        preparation,
    )


def _render_formula_window(
    selection, chosen, external, frame, related, preparation, *, max_chars, max_pieces
):
    """Render and admit one complete window from explicit invocation-owned inputs."""
    pieces = []
    for block in sorted(chosen.values(), key=lambda block: (block.block_start, block.block_end)):
        if pieces:
            pieces.append(SyntheticText("\n", "whole native block separator"))
        pieces.append(source_slice(frame, block.block_start, block.block_end))
    for piece in external:
        pieces.extend((SyntheticText("\n", "selected related source separator"), piece))
    candidate = replace(selection, pieces=tuple(pieces))
    candidate.context(
        frame,
        max_chars=max_chars,
        max_pieces=max_pieces,
        related=related,
        preparation=preparation,
        policy=selection.policy,
    )
    return candidate


def _formula_windows(
    view,
    frame,
    selections,
    regions,
    annotations,
    related,
    preparation,
    *,
    max_chars,
    max_pieces,
    check_active,
):
    """Three source-only whole-block alternatives per native primary formula.

    Keep the original selection, selected source custody and every failed lookup.
    An oversized nearest block stops that direction; it never licenses cropping
    or skipping to a more convenient passage. No role is inferred from proximity.
    """
    blocks = sorted(
        (
            a
            for a in annotations
            if a.kind in {"paragraph", "list_item", "caption"}
            and view.text[a.block_start : a.block_end].strip()
        ),
        key=lambda a: (a.block_start, a.block_end, a.block_id),
    )
    output = list(selections)
    variants = {}
    for original_index, selection in enumerate(selections):
        check_active()
        if selection.families != ("formula_context",):
            continue
        centers = [
            (index, block)
            for index, block in enumerate(blocks)
            if block.block_start <= selection.start < selection.end <= block.block_end
        ]
        if not centers:
            output[original_index] = replace(
                selection,
                local_dispositions=(
                    *selection.local_dispositions,
                    (selection.region, "unsupported", "no complete owned formula block"),
                ),
            )
            continue
        center, central = min(
            centers, key=lambda pair: (pair[1].block_end - pair[1].block_start, pair[1].block_id)
        )
        required = {(central.block_start, central.block_end): central}
        external = []
        unclosed = False
        for piece in selection.pieces:
            if not isinstance(piece, (SourceSlice, DeclaredSourceSlice)):
                continue
            if piece.source_key != frame.source_key:
                external.append(piece)
                continue
            owners = [b for b in blocks if b.block_start <= piece.start < piece.end <= b.block_end]
            if not owners:
                unclosed = True
                break
            owner = min(owners, key=lambda b: (b.block_end - b.block_start, b.block_id))
            required[owner.block_start, owner.block_end] = owner
        if unclosed:
            output[original_index] = replace(
                selection,
                local_dispositions=(
                    *selection.local_dispositions,
                    (
                        selection.region,
                        "unsupported",
                        "selected local context has no whole-block closure",
                    ),
                ),
            )
            continue

        original_pieces = selection.pieces or (source_slice(frame, selection.start, selection.end),)
        seen = {canonical_bytes([asdict(p) for p in original_pieces])}
        retained = []
        original_dispositions = list(output[original_index].local_dispositions)
        for mode, directions in (
            ("balanced", ("preceding", "following")),
            ("preceding", ("preceding",)),
            ("following", ("following",)),
        ):
            chosen = dict(required)
            try:
                candidate = _render_formula_window(
                    selection,
                    chosen,
                    external,
                    frame,
                    related,
                    preparation,
                    max_chars=max_chars,
                    max_pieces=max_pieces,
                )
            except ContextRefused as error:
                original_dispositions.append(
                    (selection.region, "resource_limit", f"{mode}: {error}")
                )
                continue
            cursors = {"preceding": center - 1, "following": center + 1}
            stopped = set()
            dispositions = []
            relationships = []
            while len(stopped) < len(directions):
                for direction in directions:
                    check_active()
                    if direction in stopped:
                        continue
                    index = cursors[direction]
                    if not 0 <= index < len(blocks):
                        stopped.add(direction)
                        continue
                    cursors[direction] += -1 if direction == "preceding" else 1
                    block = blocks[index]
                    key = block.block_start, block.block_end
                    if key in chosen:
                        continue
                    if any(
                        block.block_start < b.block_end and block.block_end > b.block_start
                        for b in chosen.values()
                    ):
                        stopped.add(direction)
                        dispositions.append(
                            (block.block_id, "unsupported", f"{mode}: overlapping whole block")
                        )
                        continue
                    try:
                        proposal = _render_formula_window(
                            selection,
                            {**chosen, key: block},
                            external,
                            frame,
                            related,
                            preparation,
                            max_chars=max_chars,
                            max_pieces=max_pieces,
                        )
                    except ContextRefused as error:
                        stopped.add(direction)
                        dispositions.append((block.block_id, "resource_limit", f"{mode}: {error}"))
                        continue
                    chosen[key] = block
                    candidate = proposal
                    dispositions.append(
                        (
                            block.block_id,
                            "selected",
                            f"{mode}: source-only whole block; role unresolved",
                        )
                    )
                    relationships.append(
                        (
                            block.block_id,
                            ContextRelationship.NEIGHBOR,
                            "whole block candidate; no semantic attachment",
                        )
                    )
            identity = canonical_bytes([asdict(p) for p in candidate.pieces])
            # Keep failures of duplicate or refused variants on the original too.
            original_dispositions.extend(dispositions)
            if identity in seen:
                continue
            seen.add(identity)
            retained.append(len(output))
            output.append(
                replace(
                    candidate,
                    reason=f"{selection.reason}; whole-native-block {mode} window",
                    local_dispositions=(*selection.local_dispositions, *dispositions),
                    local_relationships=(*selection.local_relationships, *relationships),
                )
            )
        output[original_index] = replace(
            output[original_index], local_dispositions=tuple(original_dispositions)
        )
        variants[original_index] = tuple(retained)
    regions = [
        replace(
            r,
            selections=tuple(
                index
                for original in r.selections
                for index in (original, *variants.get(original, ()))
            ),
        )
        for r in regions
    ]
    return output, regions


def _prose_formula_neighborhoods(selections, regions, *, first_window):
    """Share complete formula neighborhoods with prose, retaining every region link.

    Equal consumed pieces and selected/rejected retrieval dependencies permit one prose
    request across distinct formula primaries. Formula requests retain their own identity.
    Local routing dispositions are preserved as provenance, including failures; no report
    is replayed, retagged or cached under a different context.
    """
    output = list(selections)
    requests = {}
    linked = {}
    for index in range(first_window, len(selections)):
        selection = selections[index]
        if selection.families != ("formula_context",):
            continue
        key = canonical_bytes(
            dict(
                pieces=[asdict(piece) for piece in selection.pieces],
                retrievals=[asdict(retrieval) for retrieval in selection.retrievals],
                relationships=selection.relationships,
                missing_roles=selection.missing_roles,
                policy=selection.policy,
            )
        )
        if key not in requests:
            requests[key] = len(output)
            output.append(
                replace(
                    selection,
                    families=PROSE_FAMILIES,
                    reason="whole-native-block formula neighborhood shared with prose families",
                )
            )
        else:
            shared_index = requests[key]
            shared = output[shared_index]
            output[shared_index] = replace(
                shared,
                local_dispositions=tuple(
                    dict.fromkeys(
                        (
                            *shared.local_dispositions,
                            *selection.local_dispositions,
                        )
                    )
                ),
                local_relationships=tuple(
                    dict.fromkeys(
                        (
                            *shared.local_relationships,
                            *selection.local_relationships,
                        )
                    )
                ),
            )
        linked[index] = requests[key]
    return output, [
        replace(
            region,
            families=tuple(
                dict.fromkeys(
                    (
                        *region.families,
                        *(
                            family
                            for index in region.selections
                            if index in linked
                            for family in PROSE_FAMILIES
                        ),
                    )
                )
            ),
            selections=tuple(
                dict.fromkeys(
                    index
                    for original in region.selections
                    for index in (
                        original,
                        *((linked[original],) if original in linked else ()),
                    )
                )
            ),
        )
        for region in regions
    ]


def _widen_contexts(
    view,
    frame,
    selections,
    *,
    reader,
    read_budget,
    max_chars,
    max_pieces,
    check_active,
    context_population=None,
):
    """Use explicit structural scope, retaining failed/limited retrieval dependencies.

    This pass requests unresolved roles before extraction. It never concludes that a
    neighbor supplies a role, that a table-wide note applies to a cell, or that an
    enclosing section defines a symbol. The assembler/interpretation owns attachment.
    """
    from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
    from corpus_structure.semantic.query import ReadLimit

    budget = read_budget or PublishedReadBudget(max_rows=4096, max_bytes=4_194_304)
    nodes = {node["self_ref"]: node for node in view.items}
    local = {}
    for piece in view.pieces:
        if piece["kind"] == "native_text":
            local.setdefault(piece["item_ref"], []).append(piece)
    related = {}
    reads = {}
    retained_originals = retained_formula_originals(view.pieces)
    widened = []
    piece_starts = tuple(piece["start"] for piece in view.pieces)
    piece_ends = tuple(piece["end"] for piece in view.pieces)
    for selection in selections:
        check_active()
        node = nodes[selection.region]
        structural = selection.families in {("table",), ("formula_context",)}
        roles = (
            ("header_path", "unit", "caption", "note")
            if selection.families == ("table",)
            else ("declaration", "scope")
            if structural
            else ("scope", "condition", "referent")
        )
        requests = []
        for field, relation, missing in (
            ("captions", ContextRelationship.CAPTION, ("caption", "unit")),
            ("footnotes", ContextRelationship.NOTE, ("note", "unit")),
            ("references", ContextRelationship.REFERENCE, roles),
        ):
            targets = tuple(
                dict.fromkeys(
                    link["$ref"]
                    for link in node.get(field, ())
                    if isinstance(link, dict)
                    and isinstance(link.get("$ref"), str)
                    and link["$ref"].startswith("#/")
                )
            )
            if targets or (selection.families == ("table",) and field in {"captions", "footnotes"}):
                requests.append(
                    SourceContextRequest(
                        selection.region,
                        relation,
                        missing,
                        f"unresolved {','.join(missing)}; explicit native {field} link",
                        targets,
                    )
                )
        if not structural:
            requests.insert(
                0,
                SourceContextRequest(
                    selection.region,
                    ContextRelationship.NEIGHBOR,
                    roles,
                    "unresolved local scope/condition/referent; bounded native sibling context",
                ),
            )
        if selection.families == ("formula_context",):
            requests.insert(
                0,
                SourceContextRequest(
                    selection.region,
                    ContextRelationship.ANCESTOR,
                    roles,
                    "formula declaration/scope unresolved; direct enclosing context only",
                ),
            )
        pieces: list[SourceSlice | SyntheticText] = list(
            selection.pieces or (source_slice(frame, selection.start, selection.end),)
        )
        chars = sum(
            len(p.text) if isinstance(p, SyntheticText) else p.end - p.start for p in pieces
        )
        count = sum(
            1
            if isinstance(p, SyntheticText)
            else bisect_left(piece_starts, p.end) - bisect_right(piece_ends, p.start)
            for p in pieces
        )

        def already_consumed(a, b, selected_pieces=pieces):
            position = a
            for piece in sorted(
                (
                    p
                    for p in selected_pieces
                    if isinstance(p, (SourceSlice, DeclaredSourceSlice))
                    and p.source_key == frame.source_key
                ),
                key=lambda p: p.start,
            ):
                if piece.start > position:
                    break
                position = max(position, piece.end)
                if position >= b:
                    return True
            return False

        retrievals = []
        selected_relations = {}
        local_dispositions = []
        local_relationships = []
        for request in requests:
            check_active()
            if request.relationship == ContextRelationship.ANCESTOR:
                enclosure = _primary_formula_enclosure(
                    view, nodes, selection, local, retained_originals
                )
                if enclosure is not None:
                    pointer, span, outcome, reason = enclosure
                    if span is not None:
                        a, b = span
                        # Replace the consumed formula with its complete enclosure;
                        # appending it would duplicate the formula and its anchors.
                        extra = [
                            p
                            for p in pieces
                            if not (
                                isinstance(p, (SourceSlice, DeclaredSourceSlice))
                                and p.source_key == frame.source_key
                                and a <= p.start
                                and p.end <= b
                            )
                        ]
                        proposed = [source_slice(frame, a, b), *extra]
                        proposed_chars = sum(
                            len(p.text) if isinstance(p, SyntheticText) else p.end - p.start
                            for p in proposed
                        )
                        proposed_count = sum(
                            1
                            if isinstance(p, SyntheticText)
                            else (
                                bisect_left(piece_starts, p.end) - bisect_right(piece_ends, p.start)
                            )
                            for p in proposed
                        )
                        if proposed_chars <= max_chars and proposed_count <= max_pieces:
                            pieces, chars, count = proposed, proposed_chars, proposed_count
                        else:
                            outcome = RetrievalOutcome.RESOURCE_LIMIT
                            reason = (
                                "whole nearest native enclosure exceeds context "
                                "character/piece bound"
                            )
                    local_relationships.append((pointer, ContextRelationship.ANCESTOR, reason))
                    local_dispositions.append((pointer, outcome.value, reason))
            # Explicit links already available in the primary view retain primary
            # coordinates and are never relabelled as another selected source.
            local_targets = tuple(target for target in request.targets if target in local)
            if request.relationship == ContextRelationship.NEIGHBOR:
                parent = nodes.get(node.get("parent", {}).get("$ref"), {})
                siblings = [link.get("$ref") for link in parent.get("children", ())]
                if selection.region in siblings:
                    position = siblings.index(selection.region)
                    local_targets = tuple(
                        pointer
                        for index, pointer in enumerate(siblings)
                        if abs(index - position) == 1 and pointer in local
                    )
            for target in local_targets:
                native = local[target]
                a, b = native[0]["start"], native[-1]["end"]
                # A native item may contain several runs separated by synthetic
                # projection intervals. Context serialization consumes those too.
                target_count = bisect_left(piece_starts, b) - bisect_right(piece_ends, a)
                if already_consumed(a, b):
                    local_dispositions.append((target, "selected", "already in primary context"))
                    continue
                if chars + 1 + b - a <= max_chars and count + 1 + target_count <= max_pieces:
                    pieces.extend(
                        (
                            SyntheticText("\n", "context piece separator"),
                            source_slice(frame, a, b),
                        )
                    )
                    chars += 1 + b - a
                    count += 1 + target_count
                    local_dispositions.append(
                        (target, "selected", "explicit primary native context")
                    )
                else:
                    local_dispositions.append(
                        (target, "resource_limit", "local context character/piece bound exceeded")
                    )
            original = (
                frame.original_key
                if isinstance(frame, DeclaredNativeFrameSource)
                else frame.native_product.content_digest
            )
            scope = f"selected-product:{original}:{request.pointer}"
            remaining = (
                15 - len(selected_relations) - sum(len(row.candidates) for row in retrievals)
            )
            key = canonical_bytes(
                dict(
                    source=frame.source_key,
                    **asdict(request),
                    limit=max(1, min(4, remaining // 2)),
                )
            )
            if remaining < 2:
                retrievals.append(
                    ContextRetrieval(
                        request.relationship,
                        request.reason,
                        scope,
                        sha256(canonical_bytes([key.decode(), "source_pin_limit"])).hexdigest(),
                        (),
                        (),
                        (),
                        RetrievalOutcome.RESOURCE_LIMIT,
                        "context candidate/source pin bound exhausted before retrieval",
                    )
                )
                continue
            try:
                if key not in reads:
                    if context_population is not None:
                        from corpus_structure.semantic.declared_contexts import (
                            select_related_context,
                        )

                        reads[key] = select_related_context(
                            context_population, frame, request, limit=min(4, remaining // 2)
                        )
                    else:
                        reads[key] = reader.context_sources(
                            frame.source_key,
                            request,
                            limit=min(4, remaining // 2),
                            read_budget=budget,
                        )
                result = reads[key]
            except ReadLimit as error:
                retrievals.append(
                    ContextRetrieval(
                        request.relationship,
                        request.reason,
                        scope,
                        sha256(canonical_bytes([key.decode(), "read_limit"])).hexdigest(),
                        (),
                        (),
                        (),
                        RetrievalOutcome.RESOURCE_LIMIT,
                        str(error),
                    )
                )
                continue
            candidates, selected, excluded = result.candidates, [], []
            outcome, terminal = result.outcome, result.terminal_reason
            for source in result.sources:
                declared = isinstance(source, DeclaredNativeFrameSource)
                identity = source.source_key if declared else source.ref.id
                source_pieces = (
                    json.loads(source.native_context)["pieces"] if declared else source.pieces
                )
                # Overlapping primary contents need no second source custody. Prefer
                # explicit smaller views; broad projections remain an exclusion.
                target_pieces = tuple(p for p in source_pieces if p["kind"] == "native_text")
                overlaps = any(p["item_ref"] in local for p in target_pieces)
                if (
                    overlaps
                    or not source.text.strip()
                    or chars + 1 + len(source.text) > max_chars
                    or count + 1 + len(source_pieces) > max_pieces
                    or (identity not in related and len(related) >= 8)
                    or (
                        identity in selected_relations
                        and selected_relations[identity][0] != request.relationship
                    )
                ):
                    excluded.append(identity)
                    continue
                if identity in selected_relations:
                    selected.append(identity)
                    continue
                if identity not in related:
                    related[identity] = RelatedNativeSource(
                        source if declared else native_source_frame(source, ()),
                        request.relationship,
                        request.reason,
                    )
                pieces.extend(
                    (
                        SyntheticText("\n", "context piece separator"),
                        source_slice(
                            source if declared else related[identity].source, 0, len(source.text)
                        ),
                    )
                )
                chars += 1 + len(source.text)
                count += 1 + len(source_pieces)
                selected.append(identity)
                selected_relations[identity] = (request.relationship, request.reason)
            if outcome == RetrievalOutcome.SELECTED:
                outcome = RetrievalOutcome.SELECTED if selected else RetrievalOutcome.RESOURCE_LIMIT
                terminal = (
                    "selected bounded native context; role attachment remains unresolved"
                    if selected
                    else (
                        "related projection overlaps primary, conflicts in relation "
                        "or exceeds context bound"
                    )
                )
            retrievals.append(
                ContextRetrieval(
                    request.relationship,
                    request.reason,
                    scope,
                    result.membership_digest,
                    candidates,
                    tuple(selected),
                    tuple(excluded),
                    outcome,
                    terminal,
                )
            )
        widened.append(
            replace(
                selection,
                missing_roles=roles,
                pieces=tuple(pieces),
                retrievals=tuple(retrievals),
                local_dispositions=tuple(local_dispositions),
                local_relationships=tuple(local_relationships),
                relationships=tuple(
                    (identity, relation, reason)
                    for identity, (relation, reason) in selected_relations.items()
                ),
            )
        )
    return widened, tuple(related.values())


def _primary_formula_enclosure(view, nodes, selection, local, retained_originals):
    """Find one complete actual enclosure, never nearby prose or a cropped ancestor.

    Inline wrappers belong to the enclosing paragraph. Stop at its first genuine
    non-inline parent; a missing closure does not license a farther, broader scope.
    """
    pointer = selection.region
    seen = {pointer}
    while (parent := nodes[pointer].get("parent", {}).get("$ref")) is not None:
        if parent not in nodes:
            return (
                parent,
                None,
                RetrievalOutcome.MISSING_SCOPE,
                "native enclosing block is outside primary source",
            )
        if parent in seen or not any(
            child.get("$ref") == pointer for child in nodes[parent].get("children", ())
        ):
            return (
                parent,
                None,
                RetrievalOutcome.UNSUPPORTED,
                "native parent/child closure is unavailable",
            )
        seen.add(parent)
        pointer = parent
        if nodes[parent].get("label") != "inline":
            break
    else:
        return None
    if not pointer.startswith(("#/texts/", "#/groups/")):
        return (
            pointer,
            None,
            RetrievalOutcome.UNSUPPORTED,
            "enclosing native structure is not a paragraph/group scope",
        )
    span = None
    try:
        projection = project_section_nodes(
            nodes,
            "",
            pointer,
            "descendant",
            section_refs=frozenset((pointer,)),
            retained_originals=retained_originals,
        )
        native = tuple(p for p in projection.pieces if p.kind == "native_text")
        required = {(p.item_ref, p.source_field) for p in native}
        actual = sorted(
            (
                p
                for ref, field in required
                for p in local.get(ref, ())
                if p.get("source_field") == field
            ),
            key=lambda p: p["start"],
        )
        valid = len(actual) == len(native) and any(p.item_ref == selection.region for p in native)
        valid = valid and all(
            item["item_ref"] == expected.item_ref
            and item.get("source_field") == expected.source_field
            and (expected.cell_index is None or item.get("cell_index") == expected.cell_index)
            and view.text[item["start"] : item["end"]]
            == projection.text[expected.start : expected.end]
            for item, expected in zip(actual, native, strict=False)
        )
        if valid:
            a, b = actual[0]["start"], actual[-1]["end"]
            valid = a <= selection.start < selection.end <= b and view.text[a:b] == projection.text
            span = (a, b)
        if not valid or span is None:
            raise ValueError("complete native enclosing projection is absent from primary source")
    except (ValueError, KeyError, TypeError) as error:
        return pointer, None, RetrievalOutcome.UNSUPPORTED, str(error)
    return (
        pointer,
        span,
        RetrievalOutcome.SELECTED,
        (
            "complete nearest native ancestor consumed in primary source; "
            "declaration/scope unresolved"
        ),
    )
