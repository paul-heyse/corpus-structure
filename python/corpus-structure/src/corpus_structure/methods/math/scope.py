"""Mathematical binding and scope assignment from retained primary source cues.

Native token/sentence and language recognition is owned by constructions.math_scope.
This kernel combines those facts with mathematical mentions/relations/values and
native section topology. It performs no tokenization, language matching or parsing.
"""

from __future__ import annotations

import bisect
import dataclasses
import heapq
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from corpus_structure.core.evidence import MacroDef, Segment
from corpus_structure.core.keys import symbol_form
from corpus_structure.core.vocab import (
    ANNOTATION_UNIT,
    SECTION_LIKE,
    MathKind,
    ParseOutcome,
    ScopeExtent,
    SegmentKind,
)
from corpus_structure.methods.math.spans import MathRelation, SpanValue, SymbolMention
from corpus_structure.semantic.constructions.math_scope import Binders as Binders
from corpus_structure.semantic.constructions.math_scope import MathScopeReadings


class ScopeContent(Protocol):
    """Text-kernel input, independent of persisted rendition or source authority."""

    @property
    def canonical_text(self) -> str: ...
    @property
    def document(self) -> Segment: ...
    def text(self, segment: Segment) -> str: ...


@dataclass(frozen=True, slots=True)
class MathToken:
    """`Token._.math`: the span's kind and the mentions it binds."""

    kind: MathKind | None
    bound: tuple[SymbolMention, ...]
    definition: bool


@dataclass(frozen=True, slots=True)
class BindingSite:
    mention: SymbolMention
    symbol: str  # the symbol's key form (F2b's symbol rule)
    sentence: Segment
    extent: ScopeExtent
    scope: Segment  # the unit, or the section-like segment the extent ends with
    start: int  # the extent: the unit, or from the site to the section's end
    end: int
    rules: tuple[str, ...]  # initial | clause | definition | section_wide
    reopen: bool  # the sentence reopens ("Suppose again ...")
    reopens: BindingSite | None = None  # the symbol's previous section-level site it reopens


@dataclass(frozen=True, slots=True)
class Scope:
    mention: SymbolMention
    symbol: str
    site: BindingSite | None  # None: unresolved

    @property
    def reopens(self) -> BindingSite | None:
        return self.site.reopens if self.site is not None else None


def _enclosing_at(segments: Sequence[Segment], positions: Iterable[int]) -> dict[int, Segment]:
    """Point-stabbing sweep; width then original traversal ordinal breaks overlap ties."""
    ordered = sorted(enumerate(segments), key=lambda item: item[1].start)
    active: list[tuple[int, int, int, Segment]] = []
    cursor = 0
    out: dict[int, Segment] = {}
    for pos in sorted(set(positions)):
        while cursor < len(ordered) and ordered[cursor][1].start <= pos:
            rank, segment = ordered[cursor]
            heapq.heappush(active, (segment.end - segment.start, rank, segment.end, segment))
            cursor += 1
        while active and active[0][2] <= pos:
            heapq.heappop(active)
        if active:
            out[pos] = active[0][3]
    return out


def _site_assignments(
    sites: Sequence[BindingSite], positions: Iterable[int]
) -> dict[int, BindingSite]:
    """Eligible active sites, including the historical same-position self exception."""
    ordered = sorted(enumerate(sites), key=lambda item: max(item[1].start, item[1].mention.start))
    same: dict[int, list[tuple[int, BindingSite]]] = {}
    for rank, site in enumerate(sites):
        same.setdefault(site.mention.start, []).append((rank, site))
    active: list[tuple[int, int, int, BindingSite]] = []
    cursor = 0
    out: dict[int, BindingSite] = {}
    for pos in sorted(set(positions)):
        while cursor < len(ordered):
            rank, site = ordered[cursor]
            if max(site.start, site.mention.start) > pos:
                break
            heapq.heappush(active, (site.end - site.start, rank, site.end, site))
            cursor += 1
        while active and active[0][2] <= pos:
            heapq.heappop(active)
        candidates = [(entry.end - entry.start, rank, entry) for rank, entry in same.get(pos, ())]
        if active:
            width, rank, _, site = active[0]
            candidates.append((width, rank, site))
        if candidates:
            out[pos] = min(candidates, key=lambda item: (item[0], item[1]))[2]
    return out


def math_tokens(
    values: Sequence[SpanValue],
    mentions: Sequence[SymbolMention],
    relations: Sequence[MathRelation],
) -> dict[int, MathToken]:
    """`Token._.math` per math span start, from M09's and M11's output."""
    by_span: dict[tuple[int, int], list[SymbolMention]] = {}
    for m in mentions:
        if not m.constant and m.in_subscript_of is None:
            by_span.setdefault((m.segment.start, m.segment.end), []).append(m)
    rel_by_span: dict[tuple[int, int], list[MathRelation]] = {}
    for r in relations:
        rel_by_span.setdefault((r.segment.start, r.segment.end), []).append(r)
    out: dict[int, MathToken] = {}
    for value in values:
        where = (value.segment.start, value.segment.end)
        free = by_span.get(where, [])
        rels = sorted(rel_by_span.get(where, []), key=lambda r: r.head)
        read = value.value.parse in (ParseOutcome.OK, ParseOutcome.AMBIGUOUS)
        kind = value.math_kind if read else None
        equals = [r for r in rels if r.label == "equals"]

        def within(
            head: tuple[int, int], pool: Iterable[SymbolMention] = free
        ) -> list[SymbolMention]:
            return [m for m in pool if head[0] <= m.start < head[1]]

        bound: list[SymbolMention] = []
        definition = False
        if kind is MathKind.LIST:
            bound = list(free)
        elif kind is MathKind.FORMULA and not equals:
            bound = list(free) if len(free) == 1 else []
        elif kind is MathKind.FORMULA:
            definition = True
            left = within(equals[0].head)
            bound = left if len(left) == 1 else []
        elif kind is MathKind.MEMBERSHIP:
            bound = [
                m
                for m in free
                if any(r.label == "in_set" and r.head[0] <= m.start < r.head[1] for r in rels)
            ]
        elif kind is MathKind.RELATION and rels:
            bound = within(rels[0].head)
        out[value.segment.start] = MathToken(kind, tuple(bound), definition and bool(bound))
    return out


def resolve_scopes(
    content: ScopeContent,
    values: Sequence[SpanValue],
    mentions: Sequence[SymbolMention],
    relations: Sequence[MathRelation],
    macros: Mapping[str, MacroDef],
    *,
    primary_scope: MathScopeReadings,
    sections_by_position: Mapping[int, Segment] | None = None,
) -> list[Scope]:
    """Every non-constant mention's scope: its binding site and the site it reopens, or none."""
    tokens = math_tokens(values, mentions, relations)
    segments = list(content.document.walk())
    units = [s for s in segments if s.kind in ANNOTATION_UNIT]
    sections = [s for s in segments if s.kind in SECTION_LIKE]
    positions = [m.start for m in mentions]
    unit_at = _enclosing_at(units, positions)
    section_at = (
        _enclosing_at(sections, positions)
        if sections_by_position is None
        else dict(sections_by_position)
    )
    if sections_by_position is not None and any(
        pos not in section_at
        or section_at[pos].kind not in SECTION_LIKE
        or not section_at[pos].start <= pos < section_at[pos].end
        for pos in positions
    ):
        raise ValueError("declared section topology does not cover every mention")
    sites: list[BindingSite] = []
    if primary_scope.complete:
        for at, info in tokens.items():
            sentence_span = next(
                (span for span in primary_scope.sentences if span[0] <= at < span[1]), None
            )
            if sentence_span is None or not info.bound:
                continue
            sentence = Segment(
                kind=SegmentKind.SENTENCE, start=sentence_span[0], end=sentence_span[1]
            )
            flags = primary_scope.flags(at)
            rules = tuple(
                rule
                for rule in ("initial", "clause", "definition", "section_wide")
                if rule in flags or (rule == "definition" and info.definition)
            )
            if not rules:
                continue
            for mention in info.bound:
                unit = unit_at.get(mention.start)
                if unit is not None and "section_wide" not in flags:
                    extent, scope, a, b = ScopeExtent.STATEMENT, unit, unit.start, unit.end
                else:
                    scope = section_at.get(mention.start) or content.document
                    extent = (
                        ScopeExtent.DOCUMENT
                        if scope.kind is SegmentKind.DOCUMENT
                        else ScopeExtent.SECTION
                    )
                    a, b = mention.start, scope.end
                symbol = symbol_form(content.canonical_text[mention.start : mention.end], macros)
                sites.append(
                    BindingSite(
                        mention, symbol, sentence, extent, scope, a, b, rules, "reopen" in flags
                    )
                )
    sites.sort(key=lambda s: s.mention.start)  # stable: page order, then creation
    sites = _with_reopens(sites)
    by_symbol: dict[str, list[BindingSite]] = {}
    for site in sites:
        by_symbol.setdefault(site.symbol, []).append(site)
    mention_symbols = [
        (m, symbol_form(content.canonical_text[m.start : m.end], macros))
        for m in mentions
        if not m.constant
    ]
    positions_by_symbol: dict[str, list[int]] = {}
    for mention, symbol in mention_symbols:
        positions_by_symbol.setdefault(symbol, []).append(mention.start)
    assignments = {
        symbol: _site_assignments(by_symbol.get(symbol, ()), points)
        for symbol, points in positions_by_symbol.items()
    }
    return [Scope(m, symbol, assignments[symbol].get(m.start)) for m, symbol in mention_symbols]


def _with_reopens(sites: Sequence[BindingSite]) -> list[BindingSite]:
    """Each reopening site with the symbol's previous section-level site."""
    previous_by_symbol: dict[str, list[BindingSite]] = {}
    for site in sites:
        if site.extent is not ScopeExtent.STATEMENT:
            previous_by_symbol.setdefault(site.symbol, []).append(site)
    starts_by_symbol = {
        symbol: [site.mention.start for site in previous]
        for symbol, previous in previous_by_symbol.items()
    }
    out = []
    for site in sites:
        if site.reopen:
            previous = previous_by_symbol.get(site.symbol, ())
            index = (
                bisect.bisect_left(starts_by_symbol.get(site.symbol, ()), site.mention.start) - 1
            )
            if index >= 0:
                site = dataclasses.replace(site, reopens=previous[index])
        out.append(site)
    return out


@dataclass(frozen=True)
class ScopeCoverage:
    """Availability of this method's required inputs and source binding result."""

    segment: Segment
    outcome: Literal["complete", "partial", "unknown", "unsupported"]
    reason: str | None = None


def scope_coverage(
    content: ScopeContent,
    values: Sequence[SpanValue],
    mentions: Sequence[SymbolMention],
    scopes: Sequence[Scope],
) -> list[ScopeCoverage]:
    """Do not turn missing interpretation or unresolved bindings into covered absence."""
    from corpus_structure.methods.math.spans import MATH_KINDS

    value_by_span: dict[tuple[int, int], list[SpanValue]] = {}
    mentions_by_span: dict[tuple[int, int], list[SymbolMention]] = {}
    scope_by_mention = {id(scope.mention): scope for scope in scopes}
    for value in values:
        value_by_span.setdefault((value.segment.start, value.segment.end), []).append(value)
    for mention in mentions:
        if not mention.constant:
            mentions_by_span.setdefault((mention.segment.start, mention.segment.end), []).append(
                mention
            )
    results = []
    for segment in content.document.walk():
        if segment.kind not in MATH_KINDS:
            continue
        key = segment.start, segment.end
        interpretations = value_by_span.get(key, [])
        if len(interpretations) != 1:
            results.append(
                ScopeCoverage(
                    segment,
                    "unknown" if not interpretations else "partial",
                    "mathematical interpretation unavailable"
                    if not interpretations
                    else "multiple mathematical interpretations",
                )
            )
            continue
        value = interpretations[0]
        if value.value.parse is not ParseOutcome.OK:
            status = value.value.parse
            unsupported = value.parse_error in {
                "unknown-command",
                "unsupported-relation",
                "environment",
                "text-in-math",
            }
            outcome = (
                "unsupported"
                if unsupported
                else "unknown"
                if not isinstance(status, ParseOutcome) or status is ParseOutcome.FAILED
                else "partial"
            )
            description = status.value if isinstance(status, ParseOutcome) else "unavailable"
            results.append(
                ScopeCoverage(
                    segment,
                    outcome,
                    "mathematical interpretation "
                    + description
                    + (": " + value.parse_error if value.parse_error else ""),
                )
            )
            continue
        source_mentions = mentions_by_span.get(key, [])
        if value.value.symbols and not source_mentions:
            results.append(
                ScopeCoverage(segment, "unknown", "symbol occurrence extraction unavailable")
            )
        elif any(
            id(mention) not in scope_by_mention or scope_by_mention[id(mention)].site is None
            for mention in source_mentions
        ):
            results.append(ScopeCoverage(segment, "partial", "required symbol binding unresolved"))
        else:
            results.append(ScopeCoverage(segment, "complete"))
    return results
