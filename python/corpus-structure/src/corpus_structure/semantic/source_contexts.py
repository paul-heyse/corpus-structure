"""Private, bounded native context preparation; no retrieval or routing execution.

Selected original-relative members retain their own immutable qualified pins. Relationship
and retrieval results are supplied context facts, not source-admission authority. Contexts
compose invocation-owned prepared indexes and explicit released readings over whitespace gaps. Source pieces remain in native projection
coordinates; model gap diagnostics never become a joined quote or a PDF glyph claim.
Original health, ancestry and recognition context remain in retained frame inputs.
"""

from __future__ import annotations

import json
from bisect import bisect_left, bisect_right
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from hashlib import sha256
from types import MappingProxyType
from typing import Any, Literal

from .declared_record_sources import (
    DeclaredNativeFrameSource,
    DeclaredSourcePin,
    DeclaredSourceSlice,
)
from .identity import canonical_bytes
from .proposals import native_address
from .types import PreparedRelease


class ContextRefused(ValueError):
    """The supplied request cannot satisfy this supported context contract."""


class ContextRelationship(StrEnum):
    ANCESTOR = "ancestor"
    NEIGHBOR = "neighbor"
    HEADER = "header"
    CAPTION = "caption"
    NOTE = "note"
    DECLARATION = "declaration"
    REFERENCE = "reference"


@dataclass(frozen=True)
class RelatedNativeSource:
    source: DeclaredNativeFrameSource
    relationship: ContextRelationship
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.relationship, ContextRelationship) or not self.reason.strip():
            raise ContextRefused("related source needs a typed relationship and reason")


class RetrievalOutcome(StrEnum):
    SELECTED = "selected"
    NO_MATCH = "no_match"
    AMBIGUOUS = "ambiguous"
    MISSING_SCOPE = "missing_scope"
    UNSUPPORTED = "unsupported"
    RESOURCE_LIMIT = "resource_limit"


@dataclass(frozen=True)
class SourceContextRequest:
    """A bounded structural lookup; missing roles are demands, never inferred facts."""

    pointer: str
    relationship: ContextRelationship
    missing_roles: tuple[str, ...]
    reason: str
    targets: tuple[str, ...] = ()

    def __post_init__(self):
        if (
            not self.pointer.startswith("#/")
            or not isinstance(self.relationship, ContextRelationship)
            or not isinstance(self.missing_roles, tuple)
            or not self.missing_roles
            or any(not role.strip() for role in self.missing_roles)
            or not self.reason.strip()
            or not isinstance(self.targets, tuple)
            or any(not pointer.startswith("#/") for pointer in self.targets)
        ):
            raise ContextRefused("context lookup requires native scope, missing roles and reason")


@dataclass(frozen=True)
class SourceContextRead:
    """Owned source views and the metadata universe considered before hydration."""

    sources: tuple[DeclaredNativeFrameSource, ...]
    candidates: tuple[DeclaredSourcePin, ...]
    membership_digest: str
    outcome: RetrievalOutcome
    terminal_reason: str


@dataclass(frozen=True)
class ContextRetrieval:
    """An upstream bounded search result, including failed and absent lookups.

    ``membership_digest`` pins the upstream scope snapshot, including membership and
    absent candidates. This operation cannot verify its currency without that owner.
    Candidate pins retain alternatives even when none was selected. No retrieval is
    performed, and this receipt alone establishes neither completeness nor note scope.
    """

    relationship: ContextRelationship
    reason: str
    scope_ref: str
    membership_digest: str
    candidates: tuple[DeclaredSourcePin, ...]
    selected: tuple[str, ...]
    excluded: tuple[str, ...]
    outcome: RetrievalOutcome
    terminal_reason: str

    def __post_init__(self) -> None:
        if any(
            not isinstance(value, tuple)
            for value in (self.candidates, self.selected, self.excluded)
        ):
            raise ContextRefused("retrieval membership must be immutable tuples")
        if (
            not isinstance(self.relationship, ContextRelationship)
            or not isinstance(self.outcome, RetrievalOutcome)
            or not all(
                value.strip() for value in (self.reason, self.scope_ref, self.terminal_reason)
            )
        ):
            raise ContextRefused("retrieval needs typed relationship, outcome and declared reasons")
        _require_digest(self.membership_digest)
        ids = {pin.source_key for pin in self.candidates}
        if (
            len(ids) != len(self.candidates)
            or len(set(self.selected)) != len(self.selected)
            or len(set(self.excluded)) != len(self.excluded)
            or set(self.selected) & set(self.excluded)
            or not set(self.selected).union(self.excluded) <= ids
        ):
            raise ContextRefused("retrieval membership is duplicate, absent or contradictory")
        if bool(self.selected) != (self.outcome == RetrievalOutcome.SELECTED):
            raise ContextRefused("only selected retrieval outcomes may carry selected sources")


def source_slice(source: DeclaredNativeFrameSource, start: int, end: int) -> DeclaredSourceSlice:
    """Select an exact original extent from the frame's own frozen selectors."""
    if not source.contains_span(start, end):
        raise ContextRefused("context extent is outside its exact selected native source scope")
    return DeclaredSourceSlice(source.source_key, start, end)


@dataclass(frozen=True)
class SyntheticText:
    text: str
    reason: str

    def __post_init__(self) -> None:
        if not self.text or not self.reason.strip():
            raise ContextRefused("synthetic context text needs content and reason")


@dataclass(frozen=True)
class SourceInterval:
    model_start: int
    model_end: int
    source: DeclaredSourcePin
    source_start: int
    source_end: int
    locator: str
    item_locator: str
    cell_index: int | None
    source_field: str | None
    coordinate_space: Literal["native_projection"] = "native_projection"
    precision: Literal["exact"] = "exact"


@dataclass(frozen=True)
class SyntheticInterval:
    model_start: int
    model_end: int
    reason: str


@dataclass(frozen=True)
class NativeSpanEvidence:
    """One literal piece, with its own source pin and independently located quote."""

    source: DeclaredSourcePin
    start: int
    end: int
    locator: str
    item_locator: str
    cell_index: int | None
    source_field: str | None
    quote: str
    model_start: int
    model_end: int


@dataclass(frozen=True)
class NativeSpanReading:
    """Ordered genuine pieces and model-only gaps, never a continuous literal quote."""

    pieces: tuple[NativeSpanEvidence, ...]
    gaps: tuple[SyntheticInterval, ...]
    model_start: int
    model_end: int
    policy: str
    context_digest: str

    def receipt(self) -> dict:
        return dict(
            version=2,
            policy=self.policy,
            context_digest=self.context_digest,
            model_start=self.model_start,
            model_end=self.model_end,
            gaps=tuple(asdict(gap) for gap in self.gaps),
        )

    @property
    def original_pieces(self) -> tuple[str, ...]:
        return tuple(piece.quote for piece in self.pieces)


@dataclass(frozen=True)
class PreparedNativeSource:
    source: DeclaredNativeFrameSource
    pin: DeclaredSourcePin = field(init=False)
    pieces: tuple[Mapping, ...] = field(init=False)
    ends: tuple[int, ...] = field(init=False)
    ancestors: tuple[str, ...] = field(init=False)
    pointers: frozenset[str] = field(init=False)
    item_locators: Mapping[tuple[str, int | None], str] = field(init=False)
    dependency_digest: str = field(init=False)
    _items: Mapping[str, Mapping[str, Any]] = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        from .declared_proposal_frames import DeclaredProposalFrame

        if not isinstance(self.source, DeclaredNativeFrameSource):
            raise ContextRefused("source context requires a current original-relative frame")
        if isinstance(self.source, DeclaredProposalFrame) and self.source.context_sources:
            raise ContextRefused("context sources must be supplied explicitly as related sources")
        try:
            view = self.source.view
        except ValueError as exc:
            raise ContextRefused(str(exc)) from exc
        context = view.columns
        object.__setattr__(
            self,
            "_items",
            view.items_by_ref,
        )
        object.__setattr__(self, "pin", self.source.pin)
        object.__setattr__(
            self,
            "pointers",
            frozenset(
                item.get("self_ref", item.get("pointer"))
                for item in (*context["items"], *context["ancestors"])
            ),
        )
        pieces = view.pieces
        object.__setattr__(self, "pieces", pieces)
        object.__setattr__(self, "ends", view.ends)
        object.__setattr__(
            self,
            "item_locators",
            MappingProxyType(
                {
                    (piece["item_ref"], piece.get("cell_index")): native_address(
                        self.source, pointer=piece["item_ref"]
                    )
                    for piece in pieces
                    if piece["kind"] == "native_text"
                }
            ),
        )
        object.__setattr__(
            self,
            "ancestors",
            tuple(item.get("self_ref", item.get("pointer")) for item in context["ancestors"]),
        )
        object.__setattr__(
            self,
            "dependency_digest",
            sha256(canonical_bytes(self.source.record)).hexdigest(),
        )

    def selected_pieces(self, start, end):
        index = bisect_right(self.ends, start)
        while index < len(self.pieces) and self.pieces[index]["start"] < end:
            yield self.pieces[index]
            index += 1

    def native_field(self, pointer: str, piece: NativeSpanEvidence) -> tuple[str, int]:
        """Find the unchanged native field behind an exact selected projection piece."""
        matches = [
            row
            for row in self.selected_pieces(piece.start, piece.end)
            if row.get("kind") == "native_text"
            and row["item_ref"] == pointer
            and row.get("source_field") == piece.source_field
            and row.get("cell_index") == piece.cell_index
            and row["start"] <= piece.start < piece.end <= row["end"]
        ]
        node = self._items.get(pointer)
        if piece.source_field == "cell_text" and node is not None:
            node = node.get("data", {}).get("table_cells", ())[piece.cell_index]
        text = node.get("text") if node is not None else None
        if len(matches) != 1 or not isinstance(text, str):
            raise ContextRefused("exact native field bridge is unavailable")
        projection = matches[0]
        if self.source.text[projection["start"] : projection["end"]] != text:
            raise ContextRefused("projection is not an unchanged complete native text field")
        return text, projection["start"]


@dataclass(frozen=True)
class PreparedNativeSources:
    """Invocation-owned immutable preparation; dropping the owner releases all indexes."""

    sources: tuple[DeclaredNativeFrameSource, ...]
    max_sources: int = 16
    by_id: Mapping[str, PreparedNativeSource] = field(init=False)

    def __post_init__(self):
        if (
            not isinstance(self.sources, tuple)
            or type(self.max_sources) is not int
            or self.max_sources < 1
            or not 0 < len(self.sources) <= self.max_sources
        ):
            raise ContextRefused("prepared sources require a bounded immutable tuple")
        prepared = {source.source_key: PreparedNativeSource(source) for source in self.sources}
        if len(prepared) != len(self.sources):
            raise ContextRefused("prepared source identities must be distinct")
        object.__setattr__(self, "by_id", MappingProxyType(prepared))

    def require(self, source):
        prepared = self.by_id.get(source.source_key)
        if prepared is None or prepared.source is not source:
            raise ContextRefused("context source is not its exact invocation-owned preparation")
        return prepared


@dataclass(frozen=True)
class NativeSourceContext:
    """Versioned private serialization of explicit pieces, without silent truncation.

    Bounds apply to all supplied qualified source/candidate pins and emitted intervals,
    including repeats. Each selected source retains its own exact member and context.
    """

    primary: DeclaredNativeFrameSource
    related: tuple[RelatedNativeSource, ...]
    pieces: tuple[DeclaredSourceSlice | SyntheticText, ...]
    purpose: str
    policy: str
    terminal_reason: str
    retrievals: tuple[ContextRetrieval, ...] = ()
    max_chars: int = 8192
    max_pieces: int = 64
    max_sources: int = 16
    version: int = 2
    preparation: PreparedNativeSources = field(kw_only=True, repr=False, compare=False)
    text: str = field(init=False)
    intervals: tuple[SourceInterval | SyntheticInterval, ...] = field(init=False)
    dependency_digest: str = field(init=False)
    _native_sources: Mapping[str, PreparedNativeSource] = field(
        init=False, repr=False, compare=False
    )
    _interval_ends: tuple[int, ...] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if (
            not isinstance(self.primary, DeclaredNativeFrameSource)
            or self.version != 2
            or not isinstance(self.preparation, PreparedNativeSources)
        ):
            raise ContextRefused(
                "current source context requires its explicit invocation-owned preparation"
            )
        if not all(value.strip() for value in (self.purpose, self.policy, self.terminal_reason)):
            raise ContextRefused("context requires purpose, policy and terminal reason")
        if any(
            not isinstance(value, tuple) for value in (self.related, self.pieces, self.retrievals)
        ):
            raise ContextRefused("context inputs must be immutable tuples")
        if any(
            type(bound) is not int or bound < 1
            for bound in (self.max_chars, self.max_pieces, self.max_sources)
        ):
            raise ContextRefused("context bounds must be positive integers")
        sources = (self.primary, *(entry.source for entry in self.related))
        candidate_pins = tuple(pin for result in self.retrievals for pin in result.candidates)
        if len(sources) + len(candidate_pins) > self.max_sources:
            raise ContextRefused("context source bound exceeded")
        if not self.pieces or max(len(self.pieces), len(self.retrievals)) > self.max_pieces:
            raise ContextRefused("context piece bound exceeded")
        by_id = {source.source_key: source for source in sources}
        if len(by_id) != len(sources) or len({source.unit_ref for source in sources}) != len(
            sources
        ):
            raise ContextRefused("context sources must have distinct source and unit identities")
        preparation = self.preparation
        contexts = {source.source_key: preparation.require(source) for source in sources}
        object.__setattr__(self, "_native_sources", MappingProxyType(contexts))
        pins = {identity: prepared.pin for identity, prepared in contexts.items()}
        known_pins = dict(pins)
        for pin in (*pins.values(), *candidate_pins):
            if pin.original_key != self.primary.original_key:
                raise ContextRefused("context supports only sources of the same pinned product")
            if known_pins.setdefault(pin.source_key, pin) != pin:
                raise ContextRefused(
                    "retrieval source pin is stale or contradicts another source pin"
                )
        ancestors = tuple(
            entry.source
            for entry in self.related
            if entry.relationship == ContextRelationship.ANCESTOR
        )
        if any(
            source.section_pointer not in contexts[self.primary.source_key].ancestors
            or source.membership != "direct"
            for source in ancestors
        ):
            raise ContextRefused("context requires a distinct direct ancestor")
        for result in self.retrievals:
            selected = {
                pin.source_key: pin
                for pin in result.candidates
                if pin.source_key in result.selected
            }
            if any(pins.get(identity) != pin for identity, pin in selected.items()):
                raise ContextRefused("retrieval selected source is absent or stale")
            related = {entry.source.source_key: entry.relationship for entry in self.related}
            if any(related.get(identity) != result.relationship for identity in selected):
                raise ContextRefused(
                    "retrieval selected relationship differs from its related source"
                )
        chunks: list[str] = []
        intervals: list[SourceInterval | SyntheticInterval] = []
        consumed: set[str] = set()
        position = 0

        def append(text: str, interval: SourceInterval | SyntheticInterval) -> None:
            nonlocal position
            if position + len(text) > self.max_chars or len(intervals) >= self.max_pieces:
                raise ContextRefused("serialized context character or interval bound exceeded")
            chunks.append(text)
            intervals.append(interval)
            position += len(text)

        for piece in self.pieces:
            if isinstance(piece, SyntheticText):
                append(
                    piece.text,
                    SyntheticInterval(position, position + len(piece.text), piece.reason),
                )
                continue
            if not isinstance(piece, DeclaredSourceSlice):
                raise ContextRefused("unsupported context piece")
            source = by_id.get(piece.source_key)
            if source is not None and not source.contains_span(piece.start, piece.end):
                raise ContextRefused(
                    "context extent is outside its exact selected native source scope"
                )
            if source is None or piece.end > len(source.text):
                raise ContextRefused("source slice is absent or outside its pinned projection")
            for native in contexts[source.source_key].selected_pieces(piece.start, piece.end):
                start, end = max(piece.start, native["start"]), min(piece.end, native["end"])
                if start >= end:
                    continue
                text = source.text[start:end]
                model_end = position + len(text)
                if native["kind"] == "synthetic_separator":
                    interval = SyntheticInterval(position, model_end, "source projection separator")
                else:
                    consumed.add(source.source_key)
                    interval = SourceInterval(
                        position,
                        model_end,
                        pins[source.source_key],
                        start,
                        end,
                        native_address(source, start=start, end=end),
                        contexts[source.source_key].item_locators[
                            (native["item_ref"], native.get("cell_index"))
                        ],
                        native.get("cell_index"),
                        native.get("source_field"),
                    )
                append(text, interval)
        if consumed != set(by_id) or not any(isinstance(row, SourceInterval) for row in intervals):
            raise ContextRefused("each selected source must be consumed with source evidence")
        object.__setattr__(self, "text", "".join(chunks))
        object.__setattr__(self, "intervals", tuple(intervals))
        object.__setattr__(self, "_interval_ends", tuple(row.model_end for row in intervals))
        identity: dict[str, Any] = {
            "version": self.version,
            "primary": contexts[self.primary.source_key].dependency_digest,
            "related": [
                dict(
                    source=contexts[entry.source.source_key].dependency_digest,
                    relationship=entry.relationship,
                    reason=entry.reason,
                )
                for entry in self.related
            ],
            "pieces": [asdict(piece) for piece in self.pieces],
            "retrievals": [asdict(result) for result in self.retrievals],
            "purpose": self.purpose,
            "policy": self.policy,
            "terminal_reason": self.terminal_reason,
            "bounds": [self.max_chars, self.max_pieces, self.max_sources],
        }
        object.__setattr__(self, "dependency_digest", sha256(canonical_bytes(identity)).hexdigest())

    def _overlapping_intervals(self, start: int, end: int):
        first = bisect_right(self._interval_ends, start)
        stop = bisect_left(self._interval_ends, end) + 1
        return self.intervals[first:stop]

    def map_span(
        self, start: int, end: int, *, literal: str | None = None, allow_multiple: bool = False
    ) -> tuple[NativeSpanEvidence, ...]:
        """Map native literal model characters before normalization or preprocessing.

        Synthetic-only and synthetic-crossing spans refuse. Adjacent real pieces may
        produce multiple anchors only when the caller declares that role permits them.
        Callers must refuse changed model input; this owner does not guess provider deltas.
        """
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(self.text):
            raise ContextRefused("model span lies outside the serialized character coordinates")
        if literal is not None and literal != self.text[start:end]:
            raise ContextRefused("literal model span differs from the serialized source context")
        rows = self._overlapping_intervals(start, end)
        if any(isinstance(row, SyntheticInterval) for row in rows):
            raise ContextRefused("model span intersects synthetic text and cannot become evidence")
        if len(rows) > 1 and not allow_multiple:
            raise ContextRefused(
                "model span requires explicit permission for multiple source anchors"
            )
        evidence: list[NativeSpanEvidence] = []
        for row in rows:
            assert isinstance(row, SourceInterval)
            left, right = max(start, row.model_start), min(end, row.model_end)
            source_start = row.source_start + left - row.model_start
            source_end = source_start + right - left
            source = self._native_sources[row.source.source_key].source
            evidence.append(
                NativeSpanEvidence(
                    row.source,
                    source_start,
                    source_end,
                    native_address(source, start=source_start, end=source_end),
                    row.item_locator,
                    row.cell_index,
                    row.source_field,
                    source.text[source_start:source_end],
                    left,
                    right,
                )
            )
        return tuple(evidence)

    def read_span(
        self,
        start: int,
        end: int,
        *,
        prepared: PreparedRelease,
        policy: str,
        literal: str | None = None,
    ) -> NativeSpanReading:
        """Explicit v2 reading over whitespace gaps; strict map_span remains unchanged."""
        if self.version != 2 or policy != "synthetic-whitespace-1":
            raise ContextRefused("unsupported context reading version or policy")
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(self.text):
            raise ContextRefused("model span lies outside the serialized character coordinates")
        if literal is not None and literal != self.text[start:end]:
            raise ContextRefused("literal model span differs from the serialized source context")
        rows = self._overlapping_intervals(start, end)
        if (
            not rows
            or isinstance(rows[0], SyntheticInterval)
            or isinstance(rows[-1], SyntheticInterval)
        ):
            raise ContextRefused("reading needs genuine source pieces at both bounds")
        pieces = []
        gaps = []
        for row in rows:
            left, right = max(start, row.model_start), min(end, row.model_end)
            if isinstance(row, SyntheticInterval):
                if not self.text[left:right].isspace():
                    raise ContextRefused("reading intersects synthetic labels or punctuation")
                gaps.append(SyntheticInterval(left, right, row.reason))
            else:
                pieces.extend(self.map_span(left, right))
        reading = NativeSpanReading(
            tuple(pieces), tuple(gaps), start, end, policy, self.dependency_digest
        )
        prepared.validate_python("RecordContextReading", reading.receipt())
        return reading


def _require_digest(value: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ContextRefused("context dependency requires a SHA-256 digest")



def record_source_pin(source: DeclaredNativeFrameSource) -> dict[str, Any]:
    """Render the owned current pin at the record/contribution boundary."""
    return source.pin.values()


def evidence_anchor(
    context: NativeSourceContext,
    piece: NativeSpanEvidence,
    *,
    native: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Translate source-owner evidence once for records and local contributions.

    No substring search or coordinate conversion occurs here. The evidence must belong
    to the exact supplied native source context.
    """
    from .record_contracts import anchor_identity

    prepared = context._native_sources.get(piece.source.source_key)
    if prepared is None or prepared.pin != piece.source:
        raise ContextRefused("evidence belongs to another source context")
    source = prepared.source
    relationship = "primary" if source is context.primary else "selected_context"
    if piece.source_field not in {None, "text", "orig", "cell_text"}:
        raise ContextRefused("unsupported native source text field")
    if source.text[piece.start : piece.end] != piece.quote:
        raise ContextRefused("evidence quote differs from pinned source")
    item_pointer = json.loads(piece.item_locator.removeprefix("pdf:"))["pointer"]
    pointer = item_pointer
    if piece.cell_index is not None and piece.source_field == "cell_text":
        pointer += f"/data/table_cells/{piece.cell_index}"
    pin = record_source_pin(source)
    start, end, text, space = piece.start, piece.end, source.text, "selected_projection"
    projection_start = 0
    if native:
        # The projection owner emits complete unchanged native fields. Establish that
        # exact bridge before dropping view-relative offsets from physical identity.
        text, projection_start = prepared.native_field(item_pointer, piece)
        start, end, space = piece.start - projection_start, piece.end - projection_start, "native"
    anchor = dict(
        pin=pin,
        space=space,
        pointer=pointer,
        precision="exact",
        start=start,
        end=end,
        source_piece=piece.quote,
    )
    if relationship != "primary":
        anchor["binding"] = dict(
            version=2, relationship=relationship, policy="attributed-selected-source-2"
        )
    anchor["anchor_id"] = anchor_identity(anchor)
    coordinate = dict(pin=pin, space=anchor["space"], pointer=pointer, text=text)
    if native:
        coordinate["projection_start"] = projection_start
    return anchor, coordinate


def native_item_anchor(context: NativeSourceContext, pointer: str) -> dict[str, Any]:
    """Locate an actual native item/cell, without inventing an exact text quote."""
    from .record_contracts import anchor_identity

    native = json.loads(context.primary.native_context)
    pointers = set()
    for item in (*native["items"], *native["ancestors"]):
        item_pointer = item.get("self_ref", item.get("pointer"))
        pointers.add(item_pointer)
        if isinstance(item_pointer, str) and item_pointer.startswith("#/tables/"):
            pointers.update(
                f"{item_pointer}/data/table_cells/{index}"
                for index, _ in enumerate(item.get("data", {}).get("table_cells", ()))
            )
    if pointer not in pointers:
        raise ContextRefused("native pointer is outside the explicitly retained source view")
    anchor = dict(
        pin=record_source_pin(context.primary), space="native", pointer=pointer, precision="item"
    )
    anchor["anchor_id"] = anchor_identity(anchor)
    return anchor
