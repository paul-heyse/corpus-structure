"""Locators: the one locator contract (D1 §3.4; ADR-0019; coordinator decision 14).

Ingest and math §3.1 (package P0-I-0).

A locator names a segment by what the source shows, an author id or the opening words of its text,
so it resolves on every rendition of the document in which that text is unchanged. Forms:

- `page` selects the `document` segment;
- `page#id` selects the one segment of any kind whose `attrs.id` is `id`;
- `page@kind:prefix` selects the one segment of that kind whose text starts with `prefix`;
- `page@kind[n]:prefix` selects the `n`-th (from 1, document order) such segment.

`page` runs to the first `#` or `@`; everything after `:` is the prefix, verbatim. `kind` is a
`SegmentKind` value or the short forms `u` and `p`. Texts and prefixes are compared on NFC text
with whitespace runs collapsed to one space and trimmed, LaTeX verbatim; a prefix need not end on a
word boundary.

Everything here is a pure function of a rendition's segments and canonical text, so
content-identical renditions give identical locators. The resolver never falls back to a near
match: a locator that selects nothing, several without an ordinal, or fewer than its ordinal raises
`LocatorRefused` with the candidates; what a refusal means is the caller's decision. Generation
cannot fail, since an ordinal always separates identical texts. This module never hashes: keys take
the structured form (`Locator.key_form`) and hash it themselves (foundations F2b).
"""

from __future__ import annotations

import unicodedata
from bisect import bisect_left, bisect_right
from collections.abc import Iterator
from typing import Literal, NamedTuple, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from corpus_structure.core.evidence import RenditionContent, Segment, SegmentKind

SHORT_KINDS: dict[str, SegmentKind] = {"u": SegmentKind.UNIT, "p": SegmentKind.PARAGRAPH}
_SHORT_OF: dict[SegmentKind, str] = {kind: short for short, kind in SHORT_KINDS.items()}
_KIND_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz_")
OPENING_WORDS = 8

# Block kinds that are neither an annotation unit nor uncovered text at the top level: sections
# are descended into, and headings label their sections.
_NOT_UNCOVERED = frozenset({SegmentKind.SECTION, SegmentKind.HEADING})

RefusalReason = Literal["none", "several", "fewer than ordinal"]


def normalize(text: str) -> str:
    """NFC, whitespace runs collapsed to one space, trimmed: the comparison form of D1 §3.4."""
    return " ".join(unicodedata.normalize("NFC", text).split())


def _words(normalized: str) -> list[str]:
    return normalized.split(" ") if normalized else []


def _lcp(a: str, b: str) -> int:
    limit = min(len(a), len(b))
    i = 0
    while i < limit and a[i] == b[i]:
        i += 1
    return i


def _bad_id(value: str) -> str | None:
    if not value:
        return "empty id"
    if any(ch.isspace() for ch in value):
        return "whitespace in id"
    return None


def _bad_page(page: str) -> str | None:
    if not page:
        return "empty page"
    for ch in "#@":
        if ch in page:
            return f"{ch!r} in page"
    return None


class LocatorSyntaxError(ValueError):
    """A string that is not a locator; `position` is the 0-based offset of the fault."""

    def __init__(self, locator: str, position: int, reason: str) -> None:
        self.locator = locator
        self.position = position
        self.reason = reason
        super().__init__(f"{reason} at position {position} of locator {locator!r}")


class Candidate(NamedTuple):
    """A segment a refused locator selected: its generated locator and its opening words."""

    locator: str
    opening: str


class LocatorRefused(LookupError):
    """A locator that selects no segment, several without an ordinal, or fewer than its ordinal."""

    def __init__(
        self, locator: str, reason: RefusalReason, candidates: tuple[Candidate, ...]
    ) -> None:
        self.locator = locator
        self.reason = reason
        self.candidates = candidates
        listed = "".join(f"\n  {c.locator}  ({c.opening})" for c in candidates)
        count = f"{len(candidates)} candidate(s)" if candidates else "no candidates"
        super().__init__(f"locator {locator!r} refused ({reason}); {count}{listed}")


class Locator(BaseModel):
    """A parsed or generated locator. `str()` gives its string form, with `u` and `p`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    page: str
    id: str | None = None
    kind: SegmentKind | None = None
    prefix: str | None = None
    n: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _one_form(self) -> Self:
        if (fault := _bad_page(self.page)) is not None:
            raise ValueError(fault)
        if self.id is not None:
            if self.kind is not None or self.prefix is not None or self.n is not None:
                raise ValueError("an id locator has no kind, prefix or ordinal")
            if (fault := _bad_id(self.id)) is not None:
                raise ValueError(fault)
        elif (self.kind is None) != (self.prefix is None):
            raise ValueError("a prefix locator has both a kind and a prefix")
        elif self.kind is None and self.n is not None:
            raise ValueError("only a prefix locator has an ordinal")
        return self

    @property
    def form(self) -> Literal["page", "id", "prefix"]:
        if self.id is not None:
            return "id"
        return "page" if self.kind is None else "prefix"

    def __str__(self) -> str:
        if self.id is not None:
            return f"{self.page}#{self.id}"
        if self.kind is None or self.prefix is None:
            return self.page
        kind = _SHORT_OF.get(self.kind, self.kind.value)
        ordinal = "" if self.n is None else f"[{self.n}]"
        return f"{self.page}@{kind}{ordinal}:{self.prefix}"

    def key_form(self, document_key: str) -> dict[str, JsonValue]:
        """The structured form keys use (D1 §3.4, §10.1): the document key in place of the page,
        the kind spelled in full, the prefix in comparison form. The caller hashes it."""
        if self.id is not None:
            return {"doc": document_key, "id": self.id}
        if self.kind is None or self.prefix is None:
            return {"doc": document_key}
        form: dict[str, JsonValue] = {
            "doc": document_key,
            "kind": self.kind.value,
            "prefix": normalize(self.prefix),
        }
        if self.n is not None:
            form["n"] = self.n
        return form


def parse(text: str) -> Locator:
    """Parse a locator string; a malformed one raises `LocatorSyntaxError` naming the position."""
    cut = min((i for i in (text.find("#"), text.find("@")) if i >= 0), default=len(text))
    page = text[:cut]
    if not page:
        raise LocatorSyntaxError(text, 0, "empty page")
    if cut == len(text):
        return Locator(page=page)
    if text[cut] == "#":
        value = text[cut + 1 :]
        if not value:
            raise LocatorSyntaxError(text, cut + 1, "empty id")
        for offset, ch in enumerate(value):
            if ch.isspace():
                raise LocatorSyntaxError(text, cut + 1 + offset, "whitespace in id")
        return Locator(page=page, id=value)
    i = cut + 1
    while i < len(text) and text[i] in _KIND_CHARS:
        i += 1
    name = text[cut + 1 : i]
    if not name:
        raise LocatorSyntaxError(text, cut + 1, "expected a segment kind")
    kind = SHORT_KINDS.get(name)
    if kind is None:
        try:
            kind = SegmentKind(name)
        except ValueError:
            raise LocatorSyntaxError(text, cut + 1, f"unknown segment kind {name!r}") from None
    n: int | None = None
    if i < len(text) and text[i] == "[":
        start = i + 1
        j = start
        while j < len(text) and "0" <= text[j] <= "9":
            j += 1
        digits = text[start:j]
        if not digits:
            raise LocatorSyntaxError(text, start, "expected an ordinal")
        if digits[0] == "0":
            raise LocatorSyntaxError(text, start, "an ordinal starts from 1, without leading zeros")
        if j >= len(text) or text[j] != "]":
            raise LocatorSyntaxError(text, j, "expected ']'")
        n = int(digits)
        i = j + 1
    if i >= len(text) or text[i] != ":":
        raise LocatorSyntaxError(text, i, "expected ':'")
    return Locator(page=page, kind=kind, prefix=text[i + 1 :], n=n)


def _root(root: str) -> str:
    return root.strip("/")


def page_of(source_uri: str, root: str) -> str:
    """A document's page: its source URI less the source profile's `root` (D1 §3.4, D2 §12.1)."""
    base = _root(root)
    if base:
        if not source_uri.startswith(base + "/"):
            raise ValueError(f"source URI {source_uri!r} is not under the profile root {root!r}")
        page = source_uri[len(base) + 1 :]
    else:
        page = source_uri
    if (fault := _bad_page(page)) is not None:
        raise ValueError(f"source URI {source_uri!r} has no locator page: {fault}")
    return page


def source_uri_of(page: str, root: str) -> str:
    """The inverse of `page_of` under the same profile root."""
    if (fault := _bad_page(page)) is not None:
        raise ValueError(f"page {page!r}: {fault}")
    base = _root(root)
    return f"{base}/{page}" if base else page


class AnnotationUnit(NamedTuple):
    key: str
    locator: Locator
    segment: Segment


class AnnotationUnits(NamedTuple):
    """Annotation units in document order, and the top-level blocks no unit holds."""

    units: tuple[AnnotationUnit, ...]
    uncovered: tuple[Segment, ...]


type _Identity = tuple[SegmentKind, int, int]


def _identity(segment: Segment) -> _Identity:
    return (segment.kind, segment.start, segment.end)


class LocatorIndex:
    """Generate and resolve on one rendition of one page; built once per rendition and use.

    Per kind, the segments' comparison texts are sorted by code point, so the segments a prefix
    selects are one contiguous range and each segment's shortest unique prefix follows from its
    common prefix with its neighbours.
    """

    def __init__(self, rendition: RenditionContent, page: str) -> None:
        if (fault := _bad_page(page)) is not None:
            raise ValueError(f"page {page!r}: {fault}")
        self.rendition = rendition
        self.page = page
        self._segments: tuple[Segment, ...] = tuple(rendition.document.walk())
        self._texts: tuple[str, ...] = tuple(normalize(rendition.text(s)) for s in self._segments)
        self._position: dict[_Identity, int] = {
            _identity(s): i for i, s in enumerate(self._segments)
        }
        self._ids: dict[str, list[int]] = {}
        by_kind: dict[SegmentKind, list[int]] = {}
        for i, segment in enumerate(self._segments):
            value = segment.attrs.get("id")
            if isinstance(value, str):
                self._ids.setdefault(value, []).append(i)
            by_kind.setdefault(segment.kind, []).append(i)
        # Per kind: positions sorted by (text, document order), and their texts in that order.
        self._sorted: dict[SegmentKind, list[int]] = {}
        self._keys: dict[SegmentKind, list[str]] = {}
        for kind, positions in by_kind.items():
            ordered = sorted(positions, key=lambda p: (self._texts[p], p))
            self._sorted[kind] = ordered
            self._keys[kind] = [self._texts[p] for p in ordered]
        self._locators: tuple[Locator, ...] = tuple(
            self._generate(i) for i in range(len(self._segments))
        )

    # -- generation -------------------------------------------------------------------------

    def _generate(self, position: int) -> Locator:
        segment = self._segments[position]
        if segment.kind is SegmentKind.DOCUMENT:
            return Locator(page=self.page)
        value = segment.attrs.get("id")
        if isinstance(value, str) and _bad_id(value) is None and len(self._ids[value]) == 1:
            return Locator(page=self.page, id=value)
        kind = segment.kind
        keys, ordered = self._keys[kind], self._sorted[kind]
        text = self._texts[position]
        words = _words(text)
        rank = bisect_left(keys, text)
        while ordered[rank] != position:  # equal texts sort by document order
            rank += 1
        neighbours = [keys[r] for r in (rank - 1, rank + 1) if 0 <= r < len(keys)]
        shared = max((_lcp(text, other) for other in neighbours), default=-1)
        if len(text) > shared:
            k = self._shortest(words, shared)
            return Locator(page=self.page, kind=kind, prefix=" ".join(words[:k]))
        # Another segment of the kind starts with this whole text: prefix the group, add [n].
        lo, hi = self._range(kind, text)
        outside = [keys[r] for r in (lo - 1, hi) if 0 <= r < len(keys)]
        shared = max((_lcp(text, other) for other in outside), default=-1)
        k = self._shortest(words, shared)
        group = sorted(ordered[lo:hi])
        return Locator(
            page=self.page, kind=kind, prefix=" ".join(words[:k]), n=group.index(position) + 1
        )

    @staticmethod
    def _shortest(words: list[str], shared: int) -> int:
        """The fewest words (at least one, when there are any) whose join is longer than
        `shared`, the longest common prefix with a segment the prefix must not select."""
        if not words:
            return 0
        length = -1  # the length of " ".join(words[:k]) is the word lengths plus k - 1 spaces
        for k, word in enumerate(words, start=1):
            length += len(word) + 1
            if length > shared:
                return k
        raise AssertionError("a segment's whole text always separates it")  # pragma: no cover

    def _range(self, kind: SegmentKind, prefix: str) -> tuple[int, int]:
        keys = self._keys.get(kind, [])
        width = len(prefix)
        lo = bisect_left(keys, prefix, key=lambda s: s[:width])
        hi = bisect_right(keys, prefix, key=lambda s: s[:width])
        return lo, hi

    def _position_of(self, segment: Segment) -> int:
        position = self._position.get(_identity(segment))
        if position is None or (
            self._segments[position] is not segment and self._segments[position] != segment
        ):
            where = f"{segment.kind} [{segment.start}, {segment.end})"
            raise ValueError(f"{where} is not a segment of this rendition")
        return position

    def generate(self, segment: Segment) -> Locator:
        """The segment's generated locator (D1 §3.4 generator)."""
        return self._locators[self._position_of(segment)]

    def unit_key(self, segment: Segment) -> str:
        """The string form of the segment's generated locator: the unit key of D1 §3.4."""
        return str(self.generate(segment))

    def __iter__(self) -> Iterator[tuple[Segment, Locator]]:
        """Every segment with its generated locator, in document order."""
        return iter(zip(self._segments, self._locators, strict=True))

    # -- resolution -------------------------------------------------------------------------

    def _candidates(self, positions: list[int]) -> tuple[Candidate, ...]:
        return tuple(
            Candidate(str(self._locators[p]), " ".join(_words(self._texts[p])[:OPENING_WORDS]))
            for p in positions
        )

    def resolve(self, locator: Locator | str) -> Segment:
        """The one segment the locator selects, or `LocatorRefused` with the candidates."""
        parsed = parse(locator) if isinstance(locator, str) else locator
        if parsed.page != self.page:
            raise ValueError(f"locator {str(parsed)!r} names another page than {self.page!r}")
        if parsed.form == "page":
            return self.rendition.document
        if parsed.id is not None:
            hits = list(self._ids.get(parsed.id, []))
        else:
            assert parsed.kind is not None and parsed.prefix is not None
            lo, hi = self._range(parsed.kind, normalize(parsed.prefix))
            hits = sorted(self._sorted.get(parsed.kind, [])[lo:hi])
        shown = locator if isinstance(locator, str) else str(parsed)
        if not hits:
            raise LocatorRefused(shown, "none", ())
        if parsed.n is None:
            if len(hits) > 1:
                raise LocatorRefused(shown, "several", self._candidates(hits))
            return self._segments[hits[0]]
        if parsed.n > len(hits):
            raise LocatorRefused(shown, "fewer than ordinal", self._candidates(hits))
        return self._segments[hits[parsed.n - 1]]

    # -- annotation units -------------------------------------------------------------------

    def annotation_units(self) -> AnnotationUnits:
        """Every `unit` segment and every paragraph whose ancestors are only sections and the
        document, in document order, with their unit keys; and as `uncovered`, the other blocks at
        that level (lists, tables, figures, …; not headings), which belong to no unit."""
        units: list[AnnotationUnit] = []
        uncovered: list[Segment] = []

        def visit(parent: Segment, top: bool) -> None:
            for child in parent.children:
                is_unit = child.kind is SegmentKind.UNIT
                if is_unit or (top and child.kind is SegmentKind.PARAGRAPH):
                    locator = self.generate(child)
                    units.append(AnnotationUnit(str(locator), locator, child))
                elif top and child.kind not in _NOT_UNCOVERED:
                    uncovered.append(child)
                visit(child, top and child.kind is SegmentKind.SECTION)

        visit(self.rendition.document, True)
        return AnnotationUnits(tuple(units), tuple(uncovered))


def annotation_units(rendition: RenditionContent, page: str) -> AnnotationUnits:
    """`LocatorIndex(rendition, page).annotation_units()`, for a caller with no index yet."""
    return LocatorIndex(rendition, page).annotation_units()
