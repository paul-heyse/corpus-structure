"""Map retained native provider coordinates through a pinned source context."""

from __future__ import annotations

import json
from bisect import bisect_right
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from enum import StrEnum
from hashlib import sha256
from itertools import pairwise
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Literal, Self

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.source_contexts import (
    ContextRefused,
    NativeSourceContext,
    NativeSourcePin,
    NativeSpanEvidence,
    NativeSpanReading,
    SourceSlice,
    evidence_anchor,
)

if TYPE_CHECKING:
    from corpus_structure.ingest.annotations import AnnotationInput
    from corpus_structure.ingest.sentences import TextToken
    from corpus_structure.semantic.types import PreparedRelease


HANLP_SEAM_LAYOUT = "source-seam-continuation-1"


@dataclass(frozen=True, slots=True)
class SeamContinuation:
    """Exact projected coordinates of one local layout repair."""

    previous_sentence: tuple[int, int]
    orphan_sentence: tuple[int, int]
    punctuation_start: int
    coordinator: tuple[int, int]


@dataclass(frozen=True, slots=True)
class HanlpLayoutDecision:
    policy: Literal["source-seam-continuation-1"]
    outcome: Literal["unchanged", "ambiguous", "repaired"]
    repair: SeamContinuation | None = None

    def __post_init__(self):
        if self.policy != HANLP_SEAM_LAYOUT or (self.outcome == "repaired") != (
            self.repair is not None
        ):
            raise ValueError("HanLP layout decision differs from its declared outcome")


def hanlp_seam_layout(
    text: str,
    extent: tuple[int, int],
    tokens: tuple[TextToken, ...],
    sentences: Sequence[tuple[int, int]],
    pieces: Sequence[Mapping[str, Any]],
) -> tuple[tuple[TextToken, ...], tuple[tuple[int, int], ...], HanlpLayoutDecision]:
    """Repair only an orphan word plus period when native geometry proves the seam.

    Keep the canonical split on zero or competing repairs. A word wholly in one
    native field and a period starting the next native field are different from
    an abbreviation, a protected token, or punctuation guessed from model text.
    """
    from corpus_structure.ingest.sentences import TextToken

    start, end = extent
    covered = tuple((a, b) for a, b in sentences if a < end and start < b)
    if (
        not 0 <= start < end <= len(text)
        or end - start > 4096
        or not 1 <= len(covered) <= 8
        or covered[0][0] != start
        or covered[-1][1] != end
    ):
        raise ValueError("HanLP seam layout requires a bounded complete sentence scope")
    native_by_start = {
        row["start"]: row
        for row in pieces
        if row["kind"] == "native_text"
        and row.get("source_field") == "text"
        and row.get("item_ref")
        and row["start"] < end
        and row["end"] > start
    }
    by_start = {token.start: token for token in tokens}
    by_end = {token.end: token for token in tokens}
    candidates = []
    for previous, orphan in pairwise(covered):
        a, b = orphan
        last = by_end.get(previous[1])
        token = by_start.get(a)
        seam = b - 1
        word = text[a:seam]
        left, right = native_by_start.get(a), native_by_start.get(seam)
        if (
            token is None
            or token.role != "prose"
            or token.end != b
            or last is None
            or last.role != "prose"
            or text[last.start : last.end].lower() not in {"and", "or"}
            or text[last.end : a] != " "
            or len(word) != 1
            or not word.isalpha()
            or text[seam:b] != "."
            or left is None
            or right is None
            or left["end"] != seam
            or right["item_ref"] == left["item_ref"]
            or not any(
                row["start"] <= last.start < last.end < row["end"] == a
                for row in native_by_start.values()
            )
        ):
            continue
        candidates.append(SeamContinuation(previous, orphan, seam, (last.start, last.end)))
    if len(candidates) != 1:
        return (
            tokens,
            covered,
            HanlpLayoutDecision(HANLP_SEAM_LAYOUT, "ambiguous" if candidates else "unchanged"),
        )
    (repair,) = candidates
    a, b = repair.orphan_sentence
    updated = tuple(
        part
        for token in tokens
        for part in (
            (
                TextToken(a, repair.punctuation_start, False),
                TextToken(repair.punctuation_start, b, token.space),
            )
            if token.start == a
            else (token,)
        )
    )
    merged = tuple(
        (sentence[0], b) if sentence == repair.previous_sentence else sentence
        for sentence in covered
        if sentence != repair.orphan_sentence
    )
    return updated, merged, HanlpLayoutDecision(HANLP_SEAM_LAYOUT, "repaired", repair)


class SourceMapReason(StrEnum):
    WRONG_SCOPE = "wrong_source_scope"
    INVALID_EXTENT = "invalid_provider_extent"
    LITERAL_MISMATCH = "provider_literal_mismatch"
    UNMAPPED = "unmapped_provider_extent"
    PROTECTED_ATOM = "partial_protected_atom"
    SOURCE_REFUSED = "source_anchor_refused"
    INVALID_FIELD = "invalid_rendered_source_field"


class SourceMapRefused(ContextRefused):
    """Expected mapping failure with the input scope available to retained diagnostics."""

    def __init__(self, reason: SourceMapReason, scope_digest: str, detail: str):
        self.reason = reason
        self.scope_digest = scope_digest
        super().__init__(detail)


@dataclass(frozen=True, slots=True)
class ProviderSpan:
    start: int
    end: int
    literal: str


@dataclass(frozen=True, slots=True)
class SourceMapSegment:
    """A half-open provider character interval copied exactly from the source layout."""

    provider_start: int
    provider_end: int
    layout_start: int

    @property
    def layout_end(self) -> int:
        return self.layout_start + self.provider_end - self.provider_start


@dataclass(frozen=True, slots=True)
class MappedSource:
    scope_digest: str
    source_map_digest: str
    input_digest: str
    provider_spans: tuple[ProviderSpan, ...]
    pieces: tuple[NativeSpanEvidence, ...]
    anchors: tuple[dict[str, Any], ...]
    coordinate_texts: tuple[dict[str, Any], ...]
    provider_path: str | None = None


def _bounds(start: int, end: int, length: int) -> bool:
    return type(start) is int and type(end) is int and 0 <= start < end <= length


@dataclass(frozen=True, slots=True)
class PM2SourceMap:
    """Exact provider copies indexed in the character space of one source context.

    Unmapped provider intervals can retain inserted text. An exact extent must
    traverse only copied characters with contiguous layout coordinates.
    Protected atoms use layout coordinates and come from the prepared layout.
    """

    context: NativeSourceContext
    provider_text: str
    segments: tuple[SourceMapSegment, ...]
    protected_atoms: tuple[tuple[int, int], ...]
    input_digest: str = field(init=False)
    _segment_ends: tuple[int, ...] = field(init=False, repr=False, compare=False)
    _atom_ends: tuple[int, ...] = field(init=False, repr=False, compare=False)

    @classmethod
    def from_annotation_input(
        cls,
        context: NativeSourceContext,
        prepared: AnnotationInput,
        provider_text: str,
        segments: tuple[SourceMapSegment, ...],
    ) -> Self:
        """Bind the exact prepared native block and inherit its protected atoms."""
        layout = prepared.layout
        start, end = layout.block_start, layout.block_end
        pin = NativeSourcePin.from_source(context.primary)
        if (
            prepared.source != pin
            or not _bounds(start, end, len(context.primary.text))
            or context.pieces != (SourceSlice(pin.source_view_id, start, end),)
            or context.text != prepared.block.text
            or sha256(context.text.encode()).hexdigest() != layout.text_digest
        ):
            raise SourceMapRefused(
                SourceMapReason.WRONG_SCOPE,
                context.dependency_digest,
                "prepared layout belongs to another selected source block",
            )
        atoms = tuple(
            (token.start - start, token.end - start)
            for token in layout.tokens
            if token.role != "prose"
        )
        return cls(context, provider_text, segments, atoms)

    @property
    def scope_digest(self) -> str:
        return self.context.dependency_digest

    def refuse(self, reason: SourceMapReason, detail: str) -> SourceMapRefused:
        return SourceMapRefused(reason, self.scope_digest, detail)

    def __post_init__(self) -> None:
        try:
            self.context.require_native_projection()
        except ContextRefused as error:
            raise self.refuse(SourceMapReason.SOURCE_REFUSED, str(error)) from error
        if not isinstance(self.segments, tuple) or not isinstance(self.protected_atoms, tuple):
            raise self.refuse(SourceMapReason.INVALID_EXTENT, "mapping requires immutable extents")
        provider_end = layout_end = 0
        for segment in self.segments:
            start, end, layout = segment.provider_start, segment.provider_end, segment.layout_start
            if (
                not _bounds(start, end, len(self.provider_text))
                or type(layout) is not int
                or not _bounds(layout, segment.layout_end, len(self.context.text))
                or start < provider_end
                or layout < layout_end
            ):
                raise self.refuse(
                    SourceMapReason.INVALID_EXTENT, "mapping segments must be ordered and disjoint"
                )
            if self.provider_text[start:end] != self.context.text[layout : segment.layout_end]:
                raise self.refuse(
                    SourceMapReason.LITERAL_MISMATCH, "provider segment differs from source layout"
                )
            provider_end, layout_end = end, segment.layout_end
        previous = 0
        for start, end in self.protected_atoms:
            if not _bounds(start, end, len(self.context.text)) or start < previous:
                raise self.refuse(
                    SourceMapReason.INVALID_EXTENT, "protected atoms must be ordered and disjoint"
                )
            previous = end
        object.__setattr__(
            self, "_segment_ends", tuple(part.provider_end for part in self.segments)
        )
        object.__setattr__(self, "_atom_ends", tuple(end for _, end in self.protected_atoms))
        object.__setattr__(
            self,
            "input_digest",
            sha256(
                canonical_bytes(
                    {
                        "coordinate_space": "pm2-provider-character-map-1",
                        "scope_digest": self.scope_digest,
                        "provider_text": self.provider_text,
                        "segments": [asdict(segment) for segment in self.segments],
                        "protected_atoms": self.protected_atoms,
                    }
                )
            ).hexdigest(),
        )

    def require_scope(self, scope_digest: str) -> None:
        if self.scope_digest != scope_digest:
            raise self.refuse(
                SourceMapReason.WRONG_SCOPE, "provider output belongs to another source context"
            )

    def _layout_bounds(self, span: ProviderSpan) -> tuple[int, int]:
        if not _bounds(span.start, span.end, len(self.provider_text)):
            raise self.refuse(SourceMapReason.INVALID_EXTENT, "extent is outside provider text")
        if self.provider_text[span.start : span.end] != span.literal:
            raise self.refuse(SourceMapReason.LITERAL_MISMATCH, "extent differs from provider text")
        provider_position = span.start
        layout_start = layout_position = None
        first = bisect_right(self._segment_ends, provider_position)
        for index in range(first, len(self.segments)):
            segment = self.segments[index]
            if segment.provider_start > provider_position:
                break
            start = segment.layout_start + provider_position - segment.provider_start
            if layout_position is not None and start != layout_position:
                break
            if layout_start is None:
                layout_start = start
            end = min(span.end, segment.provider_end)
            layout_position = start + end - provider_position
            provider_position = end
            if end == span.end:
                assert layout_start is not None
                return layout_start, layout_position
        raise self.refuse(
            SourceMapReason.UNMAPPED, "extent crosses an unmapped provider or layout gap"
        )

    def _cuts_atom(self, position: int) -> bool:
        index = bisect_right(self._atom_ends, position)
        return index < len(self.protected_atoms) and self.protected_atoms[index][0] < position

    def map_whitespace_reading(
        self, span: ProviderSpan, *, scope_digest: str, prepared: PreparedRelease
    ) -> tuple[MappedSource, NativeSpanReading]:
        """Keep native pieces and explicit synthetic gaps in the same bounded reading."""
        self.require_scope(scope_digest)
        start, end = self._layout_bounds(span)
        if self._cuts_atom(start) or self._cuts_atom(end):
            raise self.refuse(SourceMapReason.PROTECTED_ATOM, "extent cuts a source atom")
        try:
            reading = self.context.read_span(
                start, end, prepared=prepared, policy="synthetic-whitespace-1", literal=span.literal
            )
            pieces = tuple(
                piece for piece in reading.pieces if isinstance(piece, NativeSpanEvidence)
            )
            if len(pieces) != len(reading.pieces):
                raise ContextRefused("reading is outside the native projection")
            anchors, texts = zip(
                *(evidence_anchor(self.context, piece) for piece in pieces), strict=True
            )
        except ContextRefused as error:
            raise self.refuse(SourceMapReason.SOURCE_REFUSED, str(error)) from error
        return (
            MappedSource(
                self.scope_digest,
                self.input_digest,
                self.input_digest,
                (span,),
                pieces,
                anchors,
                texts,
            ),
            reading,
        )

    def map_extents(
        self, spans: tuple[ProviderSpan, ...], *, scope_digest: str, native: bool = False
    ) -> MappedSource:
        self.require_scope(scope_digest)
        if not spans:
            raise self.refuse(
                SourceMapReason.INVALID_EXTENT, "at least one exact extent is required"
            )
        pieces = []
        anchors = []
        coordinate_texts = []
        previous = 0
        for span in spans:
            start, end = self._layout_bounds(span)
            if span.start < previous:
                raise self.refuse(
                    SourceMapReason.INVALID_EXTENT, "provider extents must be ordered and disjoint"
                )
            previous = span.end
            if self._cuts_atom(start) or self._cuts_atom(end):
                raise self.refuse(
                    SourceMapReason.PROTECTED_ATOM, "extent cuts an indivisible source atom"
                )
            try:
                mapped = self.context.map_span(
                    start, end, literal=span.literal, allow_multiple=True
                )
                for piece in mapped:
                    if not isinstance(piece, NativeSpanEvidence):
                        raise ContextRefused("mapped evidence is outside the native projection")
                    anchor, coordinate = evidence_anchor(self.context, piece, native=native)
                    pieces.append(piece)
                    anchors.append(anchor)
                    coordinate_texts.append(coordinate)
            except ContextRefused as error:
                raise self.refuse(SourceMapReason.SOURCE_REFUSED, str(error)) from error
        return MappedSource(
            self.scope_digest,
            self.input_digest,
            self.input_digest,
            spans,
            tuple(pieces),
            tuple(anchors),
            tuple(coordinate_texts),
        )


@dataclass(frozen=True, slots=True)
class ProviderToken:
    """One effective token and its sentence, or an injected token without source offsets."""

    text: str
    start: int | None
    end: int | None
    sentence: int


@dataclass(frozen=True, slots=True)
class PM2TokenMap:
    mapping: PM2SourceMap
    tokens: tuple[ProviderToken, ...]
    layout: HanlpLayoutDecision | None = None
    input_digest: str = field(init=False)
    _sentence_ranges: Mapping[int, tuple[int, int]] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.tokens, tuple):
            raise self.mapping.refuse(SourceMapReason.INVALID_EXTENT, "token map must be immutable")
        previous = 0
        sentence = 0
        ranges = {}
        for index, token in enumerate(self.tokens):
            if type(token.sentence) is not int or token.sentence < sentence or not token.text:
                raise self.mapping.refuse(
                    SourceMapReason.INVALID_EXTENT, "tokens must retain their ordered sentences"
                )
            sentence = token.sentence
            sentence_start, _ = ranges.get(sentence, (index, index))
            ranges[sentence] = (sentence_start, index + 1)
            start, end = token.start, token.end
            if start is None and end is None:
                continue
            if (
                start is None
                or end is None
                or not _bounds(start, end, len(self.mapping.provider_text))
                or start < previous
            ):
                raise self.mapping.refuse(
                    SourceMapReason.INVALID_EXTENT, "token offsets must be ordered and disjoint"
                )
            if self.mapping.provider_text[start:end] != token.text:
                raise self.mapping.refuse(
                    SourceMapReason.LITERAL_MISMATCH, "effective token differs from provider text"
                )
            previous = end
        object.__setattr__(self, "_sentence_ranges", MappingProxyType(ranges))
        object.__setattr__(
            self,
            "input_digest",
            sha256(
                canonical_bytes(
                    {
                        "character_map": self.mapping.input_digest,
                        "tokens": [asdict(token) for token in self.tokens],
                        **({"layout": asdict(self.layout)} if self.layout is not None else {}),
                    }
                )
            ).hexdigest(),
        )

    def sentence_tokens(self, sentence: int) -> tuple[ProviderToken, ...]:
        start, end = self._sentence_ranges.get(sentence, (0, 0))
        return self.tokens[start:end]

    def span(self, selected: tuple[ProviderToken, ...]) -> ProviderSpan:
        text = self.mapping.provider_text
        ranges = []
        for token in selected:
            if token.start is None or token.end is None:
                raise self.mapping.refuse(
                    SourceMapReason.UNMAPPED, "extent contains an injected token"
                )
            ranges.append((token.start, token.end))
        for (_, end), (start, _) in pairwise(ranges):
            if start > end and not text[end:start].isspace():
                raise self.mapping.refuse(
                    SourceMapReason.UNMAPPED, "extent skips non-whitespace provider characters"
                )
        start, end = ranges[0][0], ranges[-1][1]
        return ProviderSpan(start, end, text[start:end])


def map_hanlp(
    tokens: PM2TokenMap,
    sentence: int,
    spans: tuple[tuple[int, int], ...],
    *,
    scope_digest: str,
    native: bool = False,
) -> MappedSource:
    """Map half-open HanLP token ranges within the named supplied sentence."""
    mapping = tokens.mapping
    mapping.require_scope(scope_digest)
    if type(sentence) is not int or sentence < 0:
        raise mapping.refuse(SourceMapReason.INVALID_EXTENT, "invalid HanLP sentence index")
    selected = tokens.sentence_tokens(sentence)
    extents = []
    for start, end in spans:
        if not _bounds(start, end, len(selected)):
            raise mapping.refuse(
                SourceMapReason.INVALID_EXTENT, "extent is outside the HanLP sentence"
            )
        extents.append(tokens.span(selected[start:end]))
    mapped = mapping.map_extents(tuple(extents), scope_digest=scope_digest, native=native)
    return replace(mapped, input_digest=tokens.input_digest)


def map_maverick(
    tokens: PM2TokenMap,
    first: int,
    last: int,
    *,
    scope_digest: str,
    native: bool = False,
) -> MappedSource:
    """Map a zero-based inclusive mention over the effective document tokens."""
    mapping = tokens.mapping
    mapping.require_scope(scope_digest)
    if type(last) is not int or not _bounds(first, last + 1, len(tokens.tokens)):
        raise mapping.refuse(SourceMapReason.INVALID_EXTENT, "invalid Maverick mention endpoints")
    if tokens.tokens[first].sentence != tokens.tokens[last].sentence:
        raise mapping.refuse(SourceMapReason.INVALID_EXTENT, "Maverick mention crosses sentences")
    mapped = mapping.map_extents(
        (tokens.span(tokens.tokens[first : last + 1]),), scope_digest=scope_digest, native=native
    )
    return replace(mapped, input_digest=tokens.input_digest)


def map_dipo(
    mapping: PM2SourceMap,
    spans: tuple[ProviderSpan, ...],
    *,
    scope_digest: str,
    native: bool = False,
) -> MappedSource:
    """Map final EDU character extents in the actual parser text, in native order."""
    return mapping.map_extents(spans, scope_digest=scope_digest, native=native)


@dataclass(frozen=True, slots=True)
class D1SourceField:
    """An allowlisted rendered JSON string, with bounds that exclude its quotes."""

    rendered_state: str
    path: str
    start: int
    end: int


def _unique_object(entries: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in entries:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def _json_pointer(state: Any, path: str) -> Any:
    if not path:
        return state
    if not path.startswith("/"):
        raise ValueError("invalid JSON pointer")
    for token in path[1:].split("/"):
        key = token.replace("~1", "/").replace("~0", "~")
        if key.replace("~", "~0").replace("/", "~1") != token:
            raise ValueError("invalid JSON pointer escape")
        if isinstance(state, list):
            index = int(key)
            if str(index) != key or index < 0:
                raise ValueError("invalid JSON array index")
            state = state[index]
        elif isinstance(state, dict):
            state = state[key]
        else:
            raise ValueError("JSON pointer leaves the rendered state")
    return state


def _json_string(text: str) -> str:
    return json.loads('"' + text + '"')


def map_d1(
    mapping: PM2SourceMap,
    span: ProviderSpan,
    *,
    scope_digest: str,
    field: D1SourceField | None = None,
    path: str | None = None,
    native: bool = False,
) -> MappedSource:
    """Map d1's rendered state offsets and independently check its decoded literal."""
    mapping.require_scope(scope_digest)
    if field is None:
        if path is not None:
            raise mapping.refuse(SourceMapReason.INVALID_FIELD, "plain d1 input has no JSON path")
        return mapping.map_extents((span,), scope_digest=scope_digest, native=native)

    state = field.rendered_state
    if (
        path != field.path
        or not _bounds(field.start, field.end, len(state))
        or not _bounds(span.start, span.end, len(state))
        or not field.start <= span.start < span.end <= field.end
    ):
        raise mapping.refuse(
            SourceMapReason.INVALID_FIELD, "span is outside the allowlisted d1 field"
        )

    try:
        whole = _json_string(state[field.start : field.end])
        original = json.loads(state, object_pairs_hook=_unique_object)
        # Blank only the declared string contents to prove which occurrence owns the
        # offsets, including when candidate and source fields contain identical text.
        blanked = json.loads(
            state[: field.start] + state[field.end :], object_pairs_hook=_unique_object
        )
        if (
            whole != mapping.provider_text
            or _json_pointer(original, field.path) != whole
            or _json_pointer(blanked, field.path) != ""
        ):
            raise ValueError("rendered offsets do not designate the selected source field")
        prefix = _json_string(state[field.start : span.start])
        literal = _json_string(state[span.start : span.end])
        suffix = _json_string(state[span.end : field.end])
        if prefix + literal + suffix != whole:
            raise ValueError("d1 extent cuts an escaped character")
    except (ValueError, KeyError, IndexError, RecursionError) as error:
        raise mapping.refuse(SourceMapReason.INVALID_FIELD, str(error)) from error
    if literal != span.literal:
        raise mapping.refuse(
            SourceMapReason.LITERAL_MISMATCH, "d1 literal differs from rendered text"
        )

    decoded = ProviderSpan(len(prefix), len(prefix) + len(literal), literal)
    mapped = mapping.map_extents((decoded,), scope_digest=scope_digest, native=native)
    digest = sha256(
        canonical_bytes(
            {
                "coordinate_space": "pm2-d1-rendered-state-1",
                "character_map": mapping.input_digest,
                "source_field": asdict(field),
            }
        )
    ).hexdigest()
    return replace(mapped, input_digest=digest, provider_spans=(span,), provider_path=path)
