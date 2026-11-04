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
from typing import Any

from corpus_structure.core.method import SourcePreparationReader
from corpus_structure.ingest.annotations import (
    AnnotationInput,
    AnnotationProduct,
    AnnotationProfile,
    AnnotationUnavailable,
    annotate,
)
from corpus_structure.ingest.pdf_hierarchy import ProjectedPiece
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
POLICY = "m1-canonical-related-context-candidates-2"


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
            ProjectedPiece(**piece) for piece in view.pieces[indices[0] : indices[-1] + 1]
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
        pieces: list[SourceSlice | SyntheticText] = [
            SourceSlice(frame.source_view_id, selection.start, selection.end)
        ]
        chars, count = (
            selection.end - selection.start,
            sum(
                piece["start"] < selection.end and piece["end"] > selection.start
                for piece in view.pieces
            ),
        )
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
                if selection.start <= a and b <= selection.end:
                    local_dispositions.append((target, "selected", "already in primary context"))
                    continue
                if chars + 1 + b - a <= max_chars and count + 1 + len(native) <= max_pieces:
                    pieces.extend(
                        (
                            SyntheticText("\n", "context piece separator"),
                            SourceSlice(frame.source_view_id, a, b),
                        )
                    )
                    chars += 1 + b - a
                    count += 1 + len(native)
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
