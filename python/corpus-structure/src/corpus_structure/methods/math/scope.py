"""M13 `resolve.symbol_scope` as a pure function (ingest and math §3.9; D4 M13).

M13 reads the rendition's segments and sentences, M09's mentions and relations and M11's values
(their detected kind and parse outcome). It never parses math.

- **The Doc.** Per block that holds sentences, the words-and-spaces Doc of M03
  (`ingest.sentences.make_doc`), its sentence starts preset from the stored sentence segments, so
  the Doc cannot disagree with the rendition's sentences. No spaCy component runs.
- **Math tokens.** Each inline math word carries `Token._.math` (registered once per process
  behind `has_extension`): its span's `math_kind` (M11's) and the occurrences it binds. A span
  binds only when M11 read it `ok` or `ambiguous` with a `math_kind`:
  - a formula with one free, non-subscript occurrence and no `equals` binds that occurrence;
  - an equation whose left side holds one such occurrence binds it (a definition);
  - a list binds every such occurrence;
  - a membership binds its `in_set` heads;
  - a relation binds the head of its first relation (its left side).
- **Binding sites** come from patterns compiled from the pack's binder lexicon (D2 §12.1
  `binders`): `Matcher(validate=True)` for sentence-initial binders and for a clause binder
  followed by a math token; `PhraseMatcher(attr="LOWER")` for section-wide phrases, from
  `nlp.make_doc(phrase)`; a reopen pattern bound to the binder's sentence start (a sentence-initial
  binder, up to three words, a reopen word); and definitional equalities anywhere. A bound
  occurrence of a math token is a site when its sentence starts with a binder or holds a
  section-wide phrase, when a clause binder precedes the token, or when the token is a definition.
- **Extents and assignment** (D4 M13 rules 1-3): a site inside an annotation unit (the
  `annotation_unit` member property) binds to the unit, unless its sentence holds a section-wide
  phrase; a site outside units binds from its position to the end of the innermost section-like
  segment; a reopen links to the symbol's previous section-level site; every non-constant mention
  goes to the innermost site at or before it whose extent contains it, and with none it is
  `unresolved`.

The paragraph rule (a standalone claim-bearing paragraph is a statement extent) is omitted in phase
0 (OPEN-D4-5). `DependencyMatcher` is not used.
"""

from __future__ import annotations

import bisect
import dataclasses
import functools
import heapq
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field
from spacy.language import Language
from spacy.matcher import Matcher, PhraseMatcher
from spacy.tokens import Doc, Token

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
from corpus_structure.ingest.sentences import (
    Block,
    SentenceConfig,
    TextLayout,
    block_of,
    make_doc,
    pipeline,
)
from corpus_structure.methods.math.spans import MathRelation, SpanValue, SymbolMention

class ScopeContent(Protocol):
    """Text-kernel input, independent of persisted rendition or source authority."""
    @property
    def canonical_text(self) -> str: ...
    @property
    def document(self) -> Segment: ...
    def text(self,segment:Segment) -> str: ...


MAX_GAP = 3  # words allowed between a sentence-initial binder and a reopen word


class Binders(BaseModel):
    """The pack's binder lexicon (D2 §12.1 `methods.yaml` `binders`)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sentence_initial: tuple[str, ...] = Field(min_length=1)
    clause: tuple[str, ...] = ()
    reopen: tuple[str, ...] = ()
    section_wide: tuple[str, ...] = ()


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


def _register() -> None:
    if not Token.has_extension("math"):
        Token.set_extension("math", default=None)
    if not Token.has_extension("is_math"):
        Token.set_extension("is_math", getter=lambda t: t._.math is not None)


@functools.cache
def _matchers(nlp: Language, binders: Binders) -> tuple[Matcher, PhraseMatcher]:
    _register()
    initial = [w.lower() for w in binders.sentence_initial]
    matcher = Matcher(nlp.vocab, validate=True)
    matcher.add("INITIAL", [[{"IS_SENT_START": True, "LOWER": {"IN": initial}}]])
    if binders.clause:
        clause = [w.lower() for w in binders.clause]
        matcher.add("CLAUSE", [[{"LOWER": {"IN": clause}}, {"_": {"is_math": True}}]])
    if binders.reopen:
        reopen = [w.lower() for w in binders.reopen]
        matcher.add(
            "REOPEN",
            [
                [
                    {"IS_SENT_START": True, "LOWER": {"IN": initial}},
                    {"OP": f"{{0,{MAX_GAP}}}"},
                    {"LOWER": {"IN": reopen}},
                ]
            ],
        )
    phrases = PhraseMatcher(nlp.vocab, attr="LOWER")
    if binders.section_wide:
        phrases.add("SECTION_WIDE", [nlp.make_doc(p) for p in binders.section_wide])
    return matcher, phrases


def segment_block(content: ScopeContent, segment: Segment) -> Block:
    """The block M03 split, rebuilt from the segment by M03's own helper."""
    markup = segment.attrs.get("markup")
    return block_of(
        content.canonical_text,
        segment.start,
        segment.end,
        ((c.kind, c.start, c.end) for c in segment.children),
        [m for m in markup if isinstance(m, dict)] if isinstance(markup, list) else [],
    )


def _blocks(content: ScopeContent) -> list[tuple[Segment, list[Segment]]]:
    """Every block holding sentences, with its sentences in order."""
    out = []
    for segment in content.document.walk():
        sentences = [c for c in segment.children if c.kind is SegmentKind.SENTENCE]
        if sentences:
            out.append((segment, sentences))
    return out


def _innermost(segments: Sequence[Segment], pos: int) -> Segment | None:
    inside = [s for s in segments if s.start <= pos < s.end]
    return min(inside, key=lambda s: s.end - s.start) if inside else None


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
    binders: Binders,
    sentences: SentenceConfig,
    *,
    text_layouts: Mapping[tuple[int, int], TextLayout] | None = None,
    text_policy: Any = None,
    sections_by_position: Mapping[int,Segment] | None = None,
) -> list[Scope]:
    """Every non-constant mention's scope: its binding site and the site it reopens, or none."""
    from corpus_structure.semantic.analysis_contracts import prepare_text_policy

    policy = prepare_text_policy() if text_policy is None else text_policy
    nlp = pipeline(sentences)
    matcher, phrases = _matchers(nlp, binders)
    tokens = math_tokens(values, mentions, relations)
    segments = list(content.document.walk())
    units = [s for s in segments if s.kind in ANNOTATION_UNIT]
    sections = [s for s in segments if s.kind in SECTION_LIKE]
    positions = [m.start for m in mentions]
    unit_at = _enclosing_at(units, positions)
    section_at = _enclosing_at(sections, positions) if sections_by_position is None else dict(sections_by_position)
    if sections_by_position is not None and any(pos not in section_at or
        section_at[pos].kind not in SECTION_LIKE or not section_at[pos].start<=pos<section_at[pos].end for pos in positions):
        raise ValueError("declared section topology does not cover every mention")
    sites: list[BindingSite] = []
    for block, block_sentences in _blocks(content):
        sites += _sites(
            content,
            block,
            block_sentences,
            tokens,
            nlp,
            matcher,
            phrases,
            unit_at,
            section_at,
            macros,
            text_layouts.get((block.start, block.end)) if text_layouts is not None else None,
            policy.recipe,
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


def _sites(
    content: ScopeContent,
    block: Segment,
    block_sentences: list[Segment],
    tokens: Mapping[int, MathToken],
    nlp: Language,
    matcher: Matcher,
    phrases: PhraseMatcher,
    unit_at: Mapping[int, Segment],
    section_at: Mapping[int, Segment],
    macros: Mapping[str, MacroDef],
    layout: TextLayout | None = None,
    recipe: str = "canonical-token-layout-1",
) -> list[BindingSite]:
    doc: Doc = make_doc(
        nlp, segment_block(content, block), layout, start=block.start, recipe=recipe
    )
    starts = {s.start - block.start for s in block_sentences}
    for token in doc[1:]:
        token.is_sent_start = token.idx in starts
    for token in doc:
        info = tokens.get(block.start + token.idx)
        if info is not None and token.tag_ == "NNP":
            token._.math = info
    flags: dict[int, set[str]] = {}
    clause_tokens: set[int] = set()
    for match_id, start, end in matcher(doc):
        rule = nlp.vocab.strings[match_id]
        flags.setdefault(doc[start].sent.start, set()).add(rule)
        if rule == "CLAUSE":
            clause_tokens.add(end - 1)
    for _match_id, start, _end in phrases(doc):
        flags.setdefault(doc[start].sent.start, set()).add("SECTION_WIDE")
    stored = sorted(block_sentences, key=lambda s: s.start)
    stored_starts = [s.start for s in stored]
    out = []
    for sent in doc.sents:
        found = flags.get(sent.start, set())
        for token in sent:
            info: MathToken | None = token._.math
            if info is None or not info.bound:
                continue
            rules = []
            if "INITIAL" in found:
                rules.append("initial")
            if token.i in clause_tokens:
                rules.append("clause")
            if info.definition:
                rules.append("definition")
            section_wide = "SECTION_WIDE" in found
            if section_wide:
                rules.append("section_wide")
            if not rules:
                continue
            at = block.start + token.idx
            k = bisect.bisect_right(stored_starts, at) - 1
            sentence = stored[k] if k >= 0 else stored[0]
            for m in info.bound:
                unit = unit_at.get(m.start)
                if unit is not None and not section_wide:
                    extent, scope, a, b = ScopeExtent.STATEMENT, unit, unit.start, unit.end
                else:
                    scope = section_at.get(m.start) or content.document
                    extent = (
                        ScopeExtent.DOCUMENT
                        if scope.kind is SegmentKind.DOCUMENT
                        else ScopeExtent.SECTION
                    )
                    a, b = m.start, scope.end
                symbol = symbol_form(content.canonical_text[m.start : m.end], macros)
                out.append(
                    BindingSite(
                        m, symbol, sentence, extent, scope, a, b, tuple(rules), "REOPEN" in found
                    )
                )
    return out


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
