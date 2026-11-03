"""Private, bounded native context preparation; no retrieval or routing execution.

Version 1 consumes already selected, pinned sources of one product. Relationships and
retrieval results are supplied facts, not inferred here. Only literal copies in native
projection character coordinates are supported. Exactness concerns that projection;
it makes no stronger claim about PDF glyphs or recognized text. Original source health,
ancestry and integrated recognition context remain in the retained frame inputs.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from hashlib import sha256
from typing import Literal

from .identity import canonical_bytes
from .product_reference import ProductReference
from .proposals import NativeFrameSource, NativeProposalFrame, native_address


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
class NativeSourcePin:
    """Compact dependency reference; coordinates always belong to this source view."""

    source_view_id: int
    unit_ref: str
    native_product: ProductReference
    section_pointer: str
    membership: str
    projection_digest: str
    recipe_digest: str
    version: int

    def __post_init__(self) -> None:
        if (
            type(self.source_view_id) is not int
            or self.source_view_id < 1
            or not self.unit_ref
            or not self.section_pointer.startswith("#/")
            or self.membership not in {"direct", "descendants"}
            or self.version not in {2, 3}
        ):
            raise ContextRefused("unsupported native source pin")
        for digest in (self.projection_digest, self.recipe_digest):
            _require_digest(digest)

    @classmethod
    def from_source(cls, source: NativeFrameSource) -> NativeSourcePin:
        return cls(**{name: getattr(source, name) for name in cls.__dataclass_fields__})


@dataclass(frozen=True)
class RelatedNativeSource:
    source: NativeFrameSource
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
    candidates: tuple[NativeSourcePin, ...]
    selected: tuple[int, ...]
    excluded: tuple[int, ...]
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
        ids = {pin.source_view_id for pin in self.candidates}
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


@dataclass(frozen=True)
class SourceSlice:
    source_view_id: int
    start: int
    end: int
    coordinate_space: Literal["native_projection"] = "native_projection"
    precision: Literal["exact"] = "exact"

    def __post_init__(self) -> None:
        if (
            type(self.source_view_id) is not int
            or self.source_view_id < 1
            or type(self.start) is not int
            or type(self.end) is not int
            or not 0 <= self.start < self.end
        ):
            raise ContextRefused(
                "source slice requires positive source identity and character range"
            )
        if self.coordinate_space != "native_projection" or self.precision != "exact":
            raise ContextRefused("unsupported coordinate space or lossy source mapping")


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
    source: NativeSourcePin
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

    source: NativeSourcePin
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
class NativeSourceContext:
    """Versioned private serialization of explicit pieces, without silent truncation.

    Bounds apply to all supplied source/candidate pins and emitted intervals, including
    repeats. Different source recipes are retained independently. Legacy proposal frames
    keep their original direct-ancestor restriction; this context is not such a frame.
    """

    primary: NativeFrameSource
    related: tuple[RelatedNativeSource, ...]
    pieces: tuple[SourceSlice | SyntheticText, ...]
    purpose: str
    policy: str
    terminal_reason: str
    retrievals: tuple[ContextRetrieval, ...] = ()
    max_chars: int = 8192
    max_pieces: int = 64
    max_sources: int = 16
    version: int = 1
    text: str = field(init=False)
    intervals: tuple[SourceInterval | SyntheticInterval, ...] = field(init=False)
    dependency_digest: str = field(init=False)

    def __post_init__(self) -> None:
        if self.version != 1:
            raise ContextRefused("unsupported native source context version")
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
        by_id = {source.source_view_id: source for source in sources}
        if len(by_id) != len(sources) or len({source.unit_ref for source in sources}) != len(
            sources
        ):
            raise ContextRefused("context sources must have distinct source and unit identities")
        contexts = {source.source_view_id: _source_context(source) for source in sources}
        pins = {source.source_view_id: NativeSourcePin.from_source(source) for source in sources}
        known_pins = dict(pins)
        for pin in (*pins.values(), *candidate_pins):
            if pin.native_product != self.primary.native_product:
                raise ContextRefused("context supports only sources of the same pinned product")
            if known_pins.setdefault(pin.source_view_id, pin) != pin:
                raise ContextRefused(
                    "retrieval source pin is stale or contradicts another source pin"
                )
        # Preserve the old ancestor semantics by calling the existing owner only for that relation.
        ancestors = tuple(
            entry.source
            for entry in self.related
            if entry.relationship == ContextRelationship.ANCESTOR
        )
        if ancestors:
            NativeProposalFrame(**_source_fields(self.primary), context_sources=ancestors)
        for result in self.retrievals:
            selected = {
                pin.source_view_id: pin
                for pin in result.candidates
                if pin.source_view_id in result.selected
            }
            if any(pins.get(identity) != pin for identity, pin in selected.items()):
                raise ContextRefused("retrieval selected source is absent or stale")
            related = {entry.source.source_view_id: entry.relationship for entry in self.related}
            if any(related.get(identity) != result.relationship for identity in selected):
                raise ContextRefused(
                    "retrieval selected relationship differs from its related source"
                )
        chunks: list[str] = []
        intervals: list[SourceInterval | SyntheticInterval] = []
        consumed: set[int] = set()
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
            if not isinstance(piece, SourceSlice):
                raise ContextRefused("unsupported context piece")
            source = by_id.get(piece.source_view_id)
            if source is None or piece.end > len(source.text):
                raise ContextRefused("source slice is absent or outside its pinned projection")
            for native in contexts[source.source_view_id]["pieces"]:
                start, end = max(piece.start, native["start"]), min(piece.end, native["end"])
                if start >= end:
                    continue
                text = source.text[start:end]
                model_end = position + len(text)
                if native["kind"] == "synthetic_separator":
                    interval = SyntheticInterval(position, model_end, "source projection separator")
                else:
                    consumed.add(source.source_view_id)
                    interval = SourceInterval(
                        position,
                        model_end,
                        pins[source.source_view_id],
                        start,
                        end,
                        native_address(source, start=start, end=end),
                        native_address(source, pointer=native["item_ref"]),
                        native.get("cell_index"),
                        native.get("source_field"),
                    )
                append(text, interval)
        if consumed != set(by_id) or not any(isinstance(row, SourceInterval) for row in intervals):
            raise ContextRefused("each selected source must be consumed with source evidence")
        object.__setattr__(self, "text", "".join(chunks))
        object.__setattr__(self, "intervals", tuple(intervals))
        identity = {
            "version": self.version,
            "primary": asdict(self.primary),
            "related": [asdict(entry) for entry in self.related],
            "pieces": [asdict(piece) for piece in self.pieces],
            "retrievals": [asdict(result) for result in self.retrievals],
            "purpose": self.purpose,
            "policy": self.policy,
            "terminal_reason": self.terminal_reason,
            "bounds": [self.max_chars, self.max_pieces, self.max_sources],
        }
        object.__setattr__(self, "dependency_digest", sha256(canonical_bytes(identity)).hexdigest())

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
        rows = tuple(
            row for row in self.intervals if row.model_start < end and row.model_end > start
        )
        if any(isinstance(row, SyntheticInterval) for row in rows):
            raise ContextRefused("model span intersects synthetic text and cannot become evidence")
        if len(rows) > 1 and not allow_multiple:
            raise ContextRefused(
                "model span requires explicit permission for multiple source anchors"
            )
        sources = {
            source.source_view_id: source
            for source in (self.primary, *(entry.source for entry in self.related))
        }
        evidence = []
        for row in rows:
            assert isinstance(row, SourceInterval)
            left, right = max(start, row.model_start), min(end, row.model_end)
            source_start = row.source_start + left - row.model_start
            source_end = source_start + right - left
            source = sources[row.source.source_view_id]
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


def _require_digest(value: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ContextRefused("context dependency requires a SHA-256 digest")


def _source_fields(source: NativeFrameSource) -> dict:
    """Keep product and sentence types when reusing the old frame's validator."""
    return {name: getattr(source, name) for name in NativeFrameSource.__dataclass_fields__}


def _source_context(source: NativeFrameSource) -> dict:
    if isinstance(source, NativeProposalFrame) and source.context_sources:
        raise ContextRefused("context sources must be supplied explicitly as related sources")
    context = json.loads(source.native_context)
    NativeSourcePin.from_source(source)
    items = [item.get("self_ref", item.get("pointer")) for item in context["items"]]
    ancestors = [item.get("self_ref", item.get("pointer")) for item in context["ancestors"]]
    if any(
        not isinstance(pointer, str) or not pointer.startswith("#/")
        for pointer in (*items, *ancestors)
    ):
        raise ContextRefused("source context has unsupported native pointers")
    projection = dict(
        text=source.text,
        pieces=context["pieces"],
        items=items,
        ancestors=ancestors,
        health=context["health"],
    )
    if sha256(canonical_bytes(projection)).hexdigest() != source.projection_digest:
        raise ContextRefused("source projection differs from its retained digest")
    position = 0
    for piece in context["pieces"]:
        if (
            type(piece.get("start")) is not int
            or type(piece.get("end")) is not int
            or piece["start"] != position
            or not position < piece["end"] <= len(source.text)
        ):
            raise ContextRefused("source pieces must partition the pinned projection")
        if piece.get("kind") == "native_text":
            if piece.get("item_ref") not in items:
                raise ContextRefused("source piece has no retained native item")
        elif piece.get("kind") != "synthetic_separator":
            raise ContextRefused("unsupported or lossy native projection piece")
        position = piece["end"]
    if position != len(source.text):
        raise ContextRefused("source pieces do not cover the pinned projection")
    return context
