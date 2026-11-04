"""M1 preparation: shared source custody and bounded typed region selections.

Every selected native item has a disposition. Unknown text receives the broad prose
packs; missing, empty and over-limit projections remain in the region denominator.
Related native sources retain independent pins; recognition alternatives remain separate.
"""

from __future__ import annotations

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
)
from corpus_structure.ingest.sentences import Block, pipeline, prepare_layout
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.proposals import NativeFrameSource, native_source_frame
from corpus_structure.semantic.source_contexts import (
    ContextRelationship,
    ContextRetrieval,
    NativeSourceContext,
    NativeSourcePin,
    PreparedNativeSources,
    RelatedNativeSource,
    RetrievalOutcome,
    SourceContextRequest,
    SourceSlice,
    SyntheticText,
)

PROSE_FAMILIES = ("definition", "assertion", "measurement")
POLICY = "m1-canonical-related-context-candidates-3"


@dataclass(frozen=True, slots=True)
class NativeTableTarget:
    cell_index: int
    row_extent: tuple[int, int] | None
    row_path: tuple[int, ...]
    header_path: tuple[int, ...]


def native_table_cell_projection(node, index, nodes) -> TextProjection:
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
            nodes, "", pointer, "descendant", section_refs=frozenset((pointer,))
        )
        if any(p.cell_index is not None for p in projection.pieces):
            raise ValueError("nested tabular rich cell requires its own structural scope")
        return replace(projection, pieces=tuple(
            replace(p, cell_index=index) if p.kind == "native_text" else p
            for p in projection.pieces
        ))
    text = cell.get("text")
    if not isinstance(text, str):
        raise ValueError("native cell text is unavailable")
    return TextProjection(
        "", node["self_ref"], "descendant", text,
        (ProjectedPiece(node["self_ref"], 0, len(text), "native_text", index, "cell_text"),)
        if text else (),
    )


@dataclass(frozen=True, slots=True)
class _PreparedTableCells:
    projections: tuple[TextProjection | None, ...]
    ranges: tuple[tuple[int, int] | None, ...]
    piece_indices: tuple[int, ...]


def _prepare_table_cells(view, node, nodes, piece_lookup):
    projections, ranges, members = [], [], set()
    for index in range(len(node["data"]["table_cells"])):
        try:
            projection = native_table_cell_projection(node, index, nodes)
        except ValueError:
            projections.append(None)
            ranges.append(None)
            continue
        native = tuple(p for p in projection.pieces if p.kind == "native_text")
        keys = {(p.item_ref, index, p.source_field) for p in native}
        indices = sorted({i for key in keys for i in piece_lookup.get(key, ())})
        members.update(indices)
        span = (
            (view.pieces[indices[0]]["start"], view.pieces[indices[-1]]["end"])
            if indices else None
        )
        valid = len(indices) == len(native) and all(
            view.pieces[i]["item_ref"] == expected.item_ref
            and view.pieces[i].get("source_field") == expected.source_field
            and view.text[view.pieces[i]["start"]:view.pieces[i]["end"]]
                == projection.text[expected.start:expected.end]
            for i, expected in zip(indices, native, strict=False)
        )
        valid = valid and (
            view.text[span[0]:span[1]] == projection.text if span is not None
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
                    header.get("row_header") and row[0] <= target_row[0]
                    and row[1] >= target_row[1] and col[1] <= target_col[0]
                ):
                    rows.append((*col, *row, other))
                if (
                    header.get("column_header") and col[0] <= target_col[0]
                    and col[1] >= target_col[1] and row[1] <= target_row[0]
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
    pieces: tuple[SourceSlice | SyntheticText, ...] = ()
    retrievals: tuple[ContextRetrieval, ...] = ()
    relationships: tuple[tuple[int, ContextRelationship, str], ...] = ()
    local_dispositions: tuple[tuple[str, str, str], ...] = ()
    table_targets: tuple[NativeTableTarget, ...] | None = None

    def context(
        self,
        source: NativeFrameSource,
        *,
        max_chars: int,
        max_pieces: int,
        related: tuple[RelatedNativeSource, ...] = (),
        preparation: PreparedNativeSources | None = None,
    ) -> NativeSourceContext:
        sources = {entry.source.source_view_id: entry.source for entry in related}
        return NativeSourceContext(
            source,
            tuple(
                RelatedNativeSource(sources[identity], relationship, reason)
                for identity, relationship, reason in self.relationships
            ),
            self.pieces or (SourceSlice(source.source_view_id, self.start, self.end),),
            ",".join(self.families),
            POLICY,
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
    source: NativeFrameSource
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


def _table_selections(view, node, indices, prepared_cells, *, max_chars, max_pieces):
    """Keep small tables whole; dense tables use complete native rows or cells.

    A target retains every located cell fragment and its complete declared paths.
    A row that cannot fit separates independent cell targets, never cell contents or
    header paths. An indivisible over-limit cell remains an explicit region limit.
    """
    pointer = node["self_ref"]
    targets = native_table_geometry(node)
    a, b = view.pieces[indices[0]]["start"], view.pieces[indices[-1]]["end"]
    if b - a <= max_chars and sum(
        piece["start"] < b and piece["end"] > a for piece in view.pieces
    ) <= max_pieces and all(p is not None for p in prepared_cells.projections):
        return [ContextSelection(
            pointer, a, b, ("table",), "native structural trigger", table_targets=targets
        )], []
    piece_starts = tuple(p["start"] for p in view.pieces)
    piece_ends = tuple(p["end"] for p in view.pieces)

    def pieces_for(group):
        required = {
            index for target in group
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
            pieces.append(SourceSlice(view.ref.id, start, end))
            previous = index
        if not pieces:
            return None, "no nonempty target/path cell projection"
        chars = sum(
            len(p.text) if isinstance(p, SyntheticText) else p.end - p.start for p in pieces
        )
        count = sum(
            1 if isinstance(p, SyntheticText)
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
            selections.append(ContextSelection(
                pointer, min(p.start for p in native), max(p.end for p in native), ("table",),
                "bounded complete native table row"
                if len(group) > 1 else "bounded native table cell",
                pieces=pieces, table_targets=group,
            ))
    if not targets:
        limits.append(f"{pointer}: over-limit table has no independently located data-cell targets")
    return selections, limits


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
    nlp = pipeline(profile.configuration) if persisted_annotations is None else None
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
        if persisted_annotations is not None:
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
    prepared_tables = {
        node["self_ref"]: _prepare_table_cells(view, node, by_pointer, piece_lookup)
        for node in view.items if "table_cells" in node.get("data", {})
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
            if structural == "table" and "table_cells" in node.get("data", {}):
                table_selections, table_limits = _table_selections(
                    view, node, indices, prepared_cells, max_chars=max_chars, max_pieces=max_pieces
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
    if reader is not None:
        selections, related = _widen_contexts(
            view,
            frame,
            selections,
            reader=reader,
            read_budget=read_budget,
            max_chars=max_chars,
            max_pieces=max_pieces,
            check_active=check_active,
        )
    preparation = PreparedNativeSources(
        (frame, *(entry.source for entry in related)), max_sources=9
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


def _widen_contexts(
    view, frame, selections, *, reader, read_budget, max_chars, max_pieces, check_active
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
            requests.append(
                SourceContextRequest(
                    selection.region,
                    ContextRelationship.ANCESTOR,
                    roles,
                    "formula declaration/scope unresolved; direct enclosing context only",
                )
            )
        pieces: list[SourceSlice | SyntheticText] = list(selection.pieces or (
            SourceSlice(frame.source_view_id, selection.start, selection.end),
        ))
        chars = sum(
            len(p.text) if isinstance(p, SyntheticText) else p.end - p.start for p in pieces
        )
        count = sum(
            1 if isinstance(p, SyntheticText)
            else bisect_left(piece_starts, p.end) - bisect_right(piece_ends, p.start)
            for p in pieces
        )

        def already_consumed(a, b, selected_pieces=pieces):
            position = a
            for piece in sorted(
                (p for p in selected_pieces if isinstance(p, SourceSlice)
                 and p.source_view_id == frame.source_view_id), key=lambda p: p.start,
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
        for request in requests:
            check_active()
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
                            SourceSlice(frame.source_view_id, a, b),
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
            scope = f"selected-product:{frame.native_product.content_digest}:{request.pointer}"
            remaining = (
                15 - len(selected_relations) - sum(len(row.candidates) for row in retrievals)
            )
            key = canonical_bytes(
                dict(
                    source=frame.source_view_id,
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
                    reads[key] = reader.context_sources(
                        frame.source_view_id,
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
                identity = source.ref.id
                # Overlapping primary contents need no second source custody. Prefer
                # explicit smaller views; broad projections remain an exclusion.
                target_pieces = tuple(p for p in source.pieces if p["kind"] == "native_text")
                overlaps = any(p["item_ref"] in local for p in target_pieces)
                if (
                    overlaps
                    or not source.text.strip()
                    or chars + 1 + len(source.text) > max_chars
                    or count + 1 + len(source.pieces) > max_pieces
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
                        native_source_frame(source, ()), request.relationship, request.reason
                    )
                pieces.extend(
                    (
                        SyntheticText("\n", "context piece separator"),
                        SourceSlice(identity, 0, len(source.text)),
                    )
                )
                chars += 1 + len(source.text)
                count += 1 + len(source.pieces)
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
                relationships=tuple(
                    (identity, relation, reason)
                    for identity, (relation, reason) in selected_relations.items()
                ),
            )
        )
    return widened, tuple(related.values())
