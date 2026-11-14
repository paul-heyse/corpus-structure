"""Private, bounded native context preparation; no retrieval or routing execution.

Selected sources retain their own immutable pins within one product. Relationship and
retrieval results are supplied context facts, not source-admission authority. Context1
keeps literal mapping; context2 composes invocation-owned prepared indexes and explicit
released readings over whitespace gaps. Source pieces remain in native projection
coordinates; model gap diagnostics never become a joined quote or a PDF glyph claim.
Original health, ancestry and recognition context remain in retained frame inputs.
"""

from __future__ import annotations

import json
from bisect import bisect_left, bisect_right
from collections.abc import Mapping
from dataclasses import InitVar, asdict, dataclass, field
from enum import StrEnum
from hashlib import sha256
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Literal

from pydantic import JsonValue

from .declared_record_sources import DeclaredNativeFrameSource, DeclaredSourcePin, DeclaredSourceSlice
from .identity import canonical_bytes
from .product_reference import ProductReference
from .proposals import NativeFrameSource, NativeProposalFrame, native_address
from .types import PreparedRelease

type SourceFrame = NativeFrameSource | DeclaredNativeFrameSource

if TYPE_CHECKING:
    from .source_views import PreparedSourceView


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
            type(self.source_key) is not int
            or self.source_key < 1
            or not self.unit_ref
            or not self.section_pointer.startswith("#/")
            or self.membership not in {"direct", "descendants"}
            or self.version not in {2, 3}
        ):
            raise ContextRefused("unsupported native source pin")
        for digest in (self.projection_digest, self.recipe_digest):
            _require_digest(digest)

    @property
    def source_key(self):
        return self.source_view_id

    @property
    def original_key(self):
        return self.native_product

    @classmethod
    def from_source(cls, source: SourceFrame) -> SourcePin:
        if isinstance(source, DeclaredNativeFrameSource):
            return source.pin
        return cls(**{name: getattr(source, name) for name in cls.__dataclass_fields__})

    def values(self) -> dict[str, JsonValue]:
        """JSON source identity, preserving every pin and coordinate version."""
        return {
            "source_view_id": self.source_key,
            "unit_ref": self.unit_ref,
            "native_product": {
                "task_id": self.native_product.task_id,
                "product_key": self.native_product.product_key,
                "content_digest": self.native_product.content_digest,
            },
            "section_pointer": self.section_pointer,
            "membership": self.membership,
            "projection_digest": self.projection_digest,
            "recipe_digest": self.recipe_digest,
            "version": self.version,
        }


@dataclass(frozen=True)
class RelatedNativeSource:
    source: SourceFrame
    relationship: ContextRelationship
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.relationship, ContextRelationship) or not self.reason.strip():
            raise ContextRefused("related source needs a typed relationship and reason")


type SourcePin = NativeSourcePin | DeclaredSourcePin


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

    sources: tuple[PreparedSourceView, ...]
    candidates: tuple[SourcePin, ...]
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
    candidates: tuple[SourcePin, ...]
    selected: tuple[int | str, ...]
    excluded: tuple[int | str, ...]
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


@dataclass(frozen=True)
class SourceSlice:
    source_view_id: int
    start: int
    end: int
    coordinate_space: Literal["native_projection"] = "native_projection"
    precision: Literal["exact"] = "exact"

    @property
    def source_key(self):
        return self.source_view_id

    def __post_init__(self) -> None:
        if (
            type(self.source_key) is not int
            or self.source_key < 1
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
    source: SourcePin
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

    source: SourcePin
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
class PreparedCapturedCoordinate:
    """Released supplied coordinate input; native ingress must still authenticate custody."""

    selected: SourceFrame
    coordinate_json: str
    release: InitVar[PreparedRelease]
    coordinate_id: str = field(init=False)
    release_id: str = field(init=False)
    pin: Mapping[str, Any] = field(init=False)
    recognition: Mapping[str, Any] = field(init=False)
    pointer: str = field(init=False)
    text: str = field(init=False)

    def __post_init__(self, release):
        if isinstance(self.selected, DeclaredNativeFrameSource):
            raise ContextRefused("captured coordinates require their declared original-relative binding")
        from .record_contracts import validate_anchor_binding

        row = release.validate_json("RecordCoordinateText", self.coordinate_json).model_dump(
            mode="python"
        )
        if row["space"] != "captured_recognition" or "recognition" not in row:
            raise ContextRefused("captured preparation requires its distinct released coordinate")
        expected = dict(
            native_product_task_id=self.selected.native_product.task_id,
            product_key=self.selected.native_product.product_key,
            product_digest=self.selected.native_product.content_digest,
            projection_digest=self.selected.projection_digest,
            recipe_digest=self.selected.recipe_digest,
            source_view_id=self.selected.source_key,
        )
        if not row["pin"]["source"].strip() or any(
            row["pin"].get(key) != value for key, value in expected.items()
        ):
            raise ContextRefused("captured coordinate differs from its selected source pin")
        validate_anchor_binding(
            dict(
                pin=row["pin"],
                space=row["space"],
                precision="exact",
                recognition=row["recognition"],
                binding=dict(
                    version=2, relationship="primary", policy="attributed-selected-source-2"
                ),
            ),
            row["pin"],
        )
        provider = json.loads(row["recognition"]["provider_occurrence_json"])
        if provider["text"] != row["text"]:
            raise ContextRefused(
                "captured coordinate text differs from its unchanged provider occurrence"
            )
        object.__setattr__(self, "coordinate_json", canonical_bytes(row).decode())
        object.__setattr__(self, "release_id", release.release_id)
        object.__setattr__(
            self, "coordinate_id", sha256(canonical_bytes([release.release_id, row])).hexdigest()
        )
        object.__setattr__(self, "pin", MappingProxyType(dict(row["pin"])))
        object.__setattr__(self, "recognition", MappingProxyType(dict(row["recognition"])))
        object.__setattr__(self, "pointer", row["pointer"])
        object.__setattr__(self, "text", row["text"])

    @classmethod
    def from_coordinate(cls, selected, prepared, coordinate):
        return cls(selected, canonical_bytes(coordinate).decode(), prepared)


@dataclass(frozen=True)
class CapturedRecognitionSlice:
    coordinate_id: str
    start: int
    end: int

    def __post_init__(self):
        _require_digest(self.coordinate_id)
        if (
            type(self.start) is not int
            or type(self.end) is not int
            or not 0 <= self.start < self.end
        ):
            raise ContextRefused("captured recognition slice requires character bounds")


@dataclass(frozen=True)
class CapturedRecognitionInterval:
    model_start: int
    model_end: int
    source: SourcePin
    coordinate: PreparedCapturedCoordinate
    source_start: int
    source_end: int
    coordinate_space: Literal["captured_recognition"] = "captured_recognition"
    precision: Literal["exact"] = "exact"


@dataclass(frozen=True)
class CapturedSpanEvidence:
    """Captured text address, deliberately without a canonical locator or source_field."""

    source: SourcePin
    coordinate: PreparedCapturedCoordinate
    start: int
    end: int
    quote: str
    model_start: int
    model_end: int

    def record_anchor(self, *, relationship: Literal["primary", "selected_context"]) -> dict:
        from .record_contracts import anchor_identity

        if relationship not in {"primary", "selected_context"}:
            raise ContextRefused("unsupported captured source relationship")
        anchor = dict(
            pin=dict(self.coordinate.pin),
            space="captured_recognition",
            pointer=self.coordinate.pointer,
            recognition=dict(self.coordinate.recognition),
            precision="exact",
            start=self.start,
            end=self.end,
            source_piece=self.quote,
            binding=dict(
                version=2, relationship=relationship, policy="attributed-selected-source-2"
            ),
        )
        anchor["anchor_id"] = anchor_identity(anchor)
        return anchor


@dataclass(frozen=True)
class NativeSpanReading:
    """Ordered genuine pieces and model-only gaps, never a continuous literal quote."""

    pieces: tuple[NativeSpanEvidence | CapturedSpanEvidence, ...]
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
    source: SourceFrame
    pin: SourcePin = field(init=False)
    pieces: tuple[Mapping, ...] = field(init=False)
    ends: tuple[int, ...] = field(init=False)
    ancestors: tuple[str, ...] = field(init=False)
    pointers: frozenset[str] = field(init=False)
    item_locators: Mapping[tuple[str, int | None], str] = field(init=False)
    dependency_digest: str = field(init=False)
    _items: Mapping[str, Mapping[str, Any]] = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        context = _source_context(self.source)
        object.__setattr__(
            self,
            "_items",
            MappingProxyType(
                {item.get("self_ref", item.get("pointer")): item for item in context["items"]}
            ),
        )
        object.__setattr__(self, "pin", NativeSourcePin.from_source(self.source))
        object.__setattr__(
            self,
            "pointers",
            frozenset(
                item.get("self_ref", item.get("pointer"))
                for item in (*context["items"], *context["ancestors"])
            ),
        )
        pieces = tuple(MappingProxyType(dict(piece)) for piece in context["pieces"])
        object.__setattr__(self, "pieces", pieces)
        object.__setattr__(self, "ends", tuple(piece["end"] for piece in pieces))
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
            self, "dependency_digest", sha256(canonical_bytes(self.source.record if isinstance(self.source, DeclaredNativeFrameSource) else asdict(self.source))).hexdigest()
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

    sources: tuple[SourceFrame, ...]
    max_sources: int = 16
    captured: tuple[PreparedCapturedCoordinate, ...] = ()
    max_captured: int = 64
    max_captured_chars: int = 1_048_576
    by_id: Mapping[int | str, PreparedNativeSource] = field(init=False)
    captured_by_id: Mapping[str, PreparedCapturedCoordinate] = field(init=False)

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
        if (
            not isinstance(self.captured, tuple)
            or any(
                type(bound) is not int or bound < 1
                for bound in (self.max_captured, self.max_captured_chars)
            )
            or len(self.captured) > self.max_captured
            or sum(len(row.text) for row in self.captured) > self.max_captured_chars
            or len({row.coordinate_id for row in self.captured}) != len(self.captured)
            or len({row.release_id for row in self.captured}) > 1
        ):
            raise ContextRefused(
                "captured preparation requires bounded distinct addresses of one release"
            )
        for coordinate in self.captured:
            selected = self.require(coordinate.selected)
            if coordinate.pointer not in selected.pointers:
                raise ContextRefused("captured selected pointer is outside its selected source")
        object.__setattr__(
            self,
            "captured_by_id",
            MappingProxyType({row.coordinate_id: row for row in self.captured}),
        )

    def require(self, source):
        prepared = self.by_id.get(source.source_key)
        if prepared is None or prepared.source is not source:
            raise ContextRefused("context source is not its exact invocation-owned preparation")
        return prepared


@dataclass(frozen=True)
class NativeSourceContext:
    """Versioned private serialization of explicit pieces, without silent truncation.

    Bounds apply to all supplied source/candidate pins and emitted intervals, including
    repeats. Different source recipes are retained independently. Legacy proposal frames
    keep their original direct-ancestor restriction; this context is not such a frame.
    """

    primary: SourceFrame
    related: tuple[RelatedNativeSource, ...]
    pieces: tuple[SourceSlice | DeclaredSourceSlice | CapturedRecognitionSlice | SyntheticText, ...]
    purpose: str
    policy: str
    terminal_reason: str
    retrievals: tuple[ContextRetrieval, ...] = ()
    max_chars: int = 8192
    max_pieces: int = 64
    max_sources: int = 16
    version: int = 1
    preparation: PreparedNativeSources | None = field(default=None, repr=False, compare=False)
    captured_dependencies: tuple[str, ...] = ()
    captured_coordinates: tuple[PreparedCapturedCoordinate, ...] = field(init=False, repr=False)
    text: str = field(init=False)
    intervals: tuple[SourceInterval | CapturedRecognitionInterval | SyntheticInterval, ...] = field(
        init=False
    )
    dependency_digest: str = field(init=False)
    _native_sources: Mapping[int | str, PreparedNativeSource] = field(
        init=False, repr=False, compare=False
    )
    _interval_ends: tuple[int, ...] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if isinstance(self.primary, DeclaredNativeFrameSource) and (self.version != 2 or self.preparation is None):
            raise ContextRefused("declared source context requires its explicit invocation-owned preparation")
        if self.version not in {1, 2} or (self.version == 2 and self.preparation is None):
            raise ContextRefused("unsupported native source context version or missing preparation")
        if not all(value.strip() for value in (self.purpose, self.policy, self.terminal_reason)):
            raise ContextRefused("context requires purpose, policy and terminal reason")
        if any(
            not isinstance(value, tuple)
            for value in (self.related, self.pieces, self.retrievals, self.captured_dependencies)
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
        preparation = self.preparation or PreparedNativeSources(tuple(sources), self.max_sources)
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
        # Preserve the old ancestor semantics by calling the existing owner only for that relation.
        ancestors = tuple(
            entry.source
            for entry in self.related
            if entry.relationship == ContextRelationship.ANCESTOR
        )
        if ancestors:
            if self.version == 1:
                NativeProposalFrame(**_source_fields(self.primary), context_sources=ancestors)
            elif any(
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
        capture_ids = tuple(
            dict.fromkeys(
                (
                    *(
                        piece.coordinate_id
                        for piece in self.pieces
                        if isinstance(piece, CapturedRecognitionSlice)
                    ),
                    *self.captured_dependencies,
                )
            )
        )
        if (
            not isinstance(self.captured_dependencies, tuple)
            or len(set(self.captured_dependencies)) != len(self.captured_dependencies)
            or (self.version == 1 and capture_ids)
            or len(sources) + len(candidate_pins) + len(capture_ids) > self.max_sources
        ):
            raise ContextRefused("unsupported or unbounded captured context dependencies")
        for captured_id in capture_ids:
            coordinate = preparation.captured_by_id.get(captured_id)
            if (
                coordinate is None
                or coordinate.selected.original_key != self.primary.original_key
            ):
                raise ContextRefused(
                    "captured dependency is absent or outside the selected native product"
                )
        object.__setattr__(
            self,
            "captured_coordinates",
            tuple(preparation.captured_by_id[identity] for identity in capture_ids),
        )
        chunks: list[str] = []
        intervals: list[SourceInterval | CapturedRecognitionInterval | SyntheticInterval] = []
        consumed: set[int] = set()
        position = 0

        def append(
            text: str, interval: SourceInterval | CapturedRecognitionInterval | SyntheticInterval
        ) -> None:
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
            if isinstance(piece, CapturedRecognitionSlice):
                coordinate = preparation.captured_by_id[piece.coordinate_id]
                source = coordinate.selected
                if by_id.get(source.source_key) is not source or piece.end > len(
                    coordinate.text
                ):
                    raise ContextRefused(
                        "captured slice is absent or outside its selected captured text"
                    )
                consumed.add(source.source_key)
                text = coordinate.text[piece.start : piece.end]
                append(
                    text,
                    CapturedRecognitionInterval(
                        position,
                        position + len(text),
                        pins[source.source_key],
                        coordinate,
                        piece.start,
                        piece.end,
                    ),
                )
                continue
            if not isinstance(piece, (SourceSlice, DeclaredSourceSlice)):
                raise ContextRefused("unsupported context piece")
            source = by_id.get(piece.source_key)
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
        if consumed != set(by_id) or not any(
            isinstance(row, (SourceInterval, CapturedRecognitionInterval)) for row in intervals
        ):
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
        if self.version == 2:
            identity["captured_dependencies"] = [
                dict(
                    coordinate=identity,
                    selected=preparation.require(
                        preparation.captured_by_id[identity].selected
                    ).dependency_digest,
                )
                for identity in capture_ids
            ]
        if self.version == 1:
            identity["primary"] = asdict(self.primary)
            identity["related"] = [asdict(entry) for entry in self.related]
        object.__setattr__(self, "dependency_digest", sha256(canonical_bytes(identity)).hexdigest())

    def require_native_projection(self) -> None:
        if any(isinstance(row, CapturedRecognitionInterval) for row in self.intervals):
            raise ContextRefused(
                "captured recognition context is unsupported by this canonical consumer"
            )

    def _overlapping_intervals(self, start: int, end: int):
        first = bisect_right(self._interval_ends, start)
        stop = bisect_left(self._interval_ends, end) + 1
        return self.intervals[first:stop]

    def map_span(
        self, start: int, end: int, *, literal: str | None = None, allow_multiple: bool = False
    ) -> tuple[NativeSpanEvidence | CapturedSpanEvidence, ...]:
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
        evidence: list[NativeSpanEvidence | CapturedSpanEvidence] = []
        for row in rows:
            if isinstance(row, CapturedRecognitionInterval):
                left, right = max(start, row.model_start), min(end, row.model_end)
                source_start = row.source_start + left - row.model_start
                source_end = source_start + right - left
                evidence.append(
                    CapturedSpanEvidence(
                        row.source,
                        row.coordinate,
                        source_start,
                        source_end,
                        row.coordinate.text[source_start:source_end],
                        left,
                        right,
                    )
                )
                continue
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
        if any(row.release_id != prepared.release_id for row in self.captured_coordinates):
            raise ContextRefused("captured reading belongs to another effective release")
        reading = NativeSpanReading(
            tuple(pieces), tuple(gaps), start, end, policy, self.dependency_digest
        )
        prepared.validate_python("RecordContextReading", reading.receipt())
        return reading


def _require_digest(value: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ContextRefused("context dependency requires a SHA-256 digest")


def _source_fields(source: SourceFrame) -> dict:
    """Keep product and sentence types when reusing the old frame's validator."""
    return {name: getattr(source, name) for name in NativeFrameSource.__dataclass_fields__}


def _source_context(source: SourceFrame) -> dict:
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
    if isinstance(source, DeclaredNativeFrameSource):
        from .source_products import native_projection_identity

        value = source.value
        projection = native_projection_identity(source.text, value["pieces"], value["items"], value.get("recognition", ()), value.get("ancestors", ()))
        if projection != source.projection_digest:
            raise ContextRefused("declared native projection differs from its selected source")
    else:
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


def record_source_pin(source: SourceFrame) -> dict[str, Any]:
    """The existing record/contribution pin shape for an owned source view."""
    if isinstance(source, DeclaredNativeFrameSource):
        return source.pin.values()
    product = source.native_product
    return dict(
        source=source.unit_ref,
        native_product_task_id=product.task_id,
        product_key=product.product_key,
        product_digest=product.content_digest,
        projection_digest=source.projection_digest,
        recipe_digest=source.recipe_digest,
        source_view_id=source.source_key,
    )


def evidence_anchor(
    context: NativeSourceContext,
    piece: NativeSpanEvidence | CapturedSpanEvidence,
    *,
    native: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Translate source-owner evidence once for records and local contributions.

    No substring search or coordinate conversion occurs here. The evidence must belong
    to the exact supplied source context; native and captured spaces stay distinct.
    """
    from .record_contracts import anchor_identity

    prepared = context._native_sources.get(piece.source.source_key)
    if prepared is None or prepared.pin != piece.source:
        raise ContextRefused("evidence belongs to another source context")
    source = prepared.source
    relationship = "primary" if source is context.primary else "selected_context"
    if isinstance(piece, CapturedSpanEvidence):
        if piece.coordinate not in context.captured_coordinates:
            raise ContextRefused("captured evidence coordinate is outside the context")
        anchor = piece.record_anchor(relationship=relationship)
        coordinate = dict(
            pin=anchor["pin"],
            space=anchor["space"],
            pointer=anchor["pointer"],
            recognition=anchor["recognition"],
            text=piece.coordinate.text,
        )
        return anchor, coordinate
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
    return anchor, dict(pin=pin, space=anchor["space"], pointer=pointer, text=text)


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
