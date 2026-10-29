"""M13 `resolve.symbol_scope` as a pure function (ingest and math §3.9; D4 M13).

M13 reads the rendition's segments and sentences, M09's mentions and relations and M11's values
(their detected kind and parse outcome). It never parses math.

- **The Doc.** Per block that holds sentences, the words-and-spaces Doc of M03
  (`ingest.sentences.make_doc`), its sentence starts preset from the stored sentence segments, so
  the Doc cannot disagree with the rendition's sentences. No spaCy component runs.
- **Math tokens.** Each inline math word carries `Token._.math` (registered once per process
  behind `has_extension`): its span's kind and the occurrences it binds. A span binds only when M11
  read it `ok` or `ambiguous` with one kind:
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
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field
from spacy.language import Language
from spacy.matcher import Matcher, PhraseMatcher
from spacy.tokens import Doc, Token

from corpus_structure.core.evidence import MacroDef, RenditionContent, Segment
from corpus_structure.core.keys import symbol_form
from corpus_structure.core.vocab import (
    ANNOTATION_UNIT,
    SECTION_LIKE,
    ParseOutcome,
    ScopeExtent,
    SegmentKind,
)
from corpus_structure.ingest.sentences import Block, SentenceConfig, make_doc, pipeline
from corpus_structure.methods.math.spans import MathRelation, SpanValue, SymbolMention

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

    kind: str | None
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


def _block(content: RenditionContent, segment: Segment) -> Block:
    """The block M03 split: inline and display math and rendered reference markers, relative."""

    def rel(a: int, b: int) -> tuple[int, int]:
        return a - segment.start, b - segment.start

    markup = segment.attrs.get("markup")
    markers = [
        rel(m["start"], m["end"])
        for m in (markup if isinstance(markup, list) else [])
        if isinstance(m, dict)
        and m.get("markup") == "ref"
        and isinstance(m.get("start"), int)
        and isinstance(m.get("end"), int)
        and m["end"] > m["start"]  # type: ignore[operator]
    ]
    return Block(
        content.text(segment),
        [rel(c.start, c.end) for c in segment.children if c.kind is SegmentKind.MATH_INLINE],
        [rel(c.start, c.end) for c in segment.children if c.kind is SegmentKind.MATH_DISPLAY],
        markers,  # type: ignore[arg-type]
    )


def _blocks(content: RenditionContent) -> list[tuple[Segment, list[Segment]]]:
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
        kind = value.kind if read and value.kind != "ambiguous" else None
        equals = [r for r in rels if r.label == "equals"]

        def within(
            head: tuple[int, int], pool: Iterable[SymbolMention] = free
        ) -> list[SymbolMention]:
            return [m for m in pool if head[0] <= m.start < head[1]]

        bound: list[SymbolMention] = []
        definition = False
        if kind == "list":
            bound = list(free)
        elif kind == "formula" and not equals:
            bound = list(free) if len(free) == 1 else []
        elif kind == "formula":
            definition = True
            left = within(equals[0].head)
            bound = left if len(left) == 1 else []
        elif kind == "member":
            bound = [
                m
                for m in free
                if any(r.label == "in_set" and r.head[0] <= m.start < r.head[1] for r in rels)
            ]
        elif kind == "relation" and rels:
            bound = within(rels[0].head)
        out[value.segment.start] = MathToken(kind, tuple(bound), definition and bool(bound))
    return out


def resolve_scopes(
    content: RenditionContent,
    values: Sequence[SpanValue],
    mentions: Sequence[SymbolMention],
    relations: Sequence[MathRelation],
    macros: Mapping[str, MacroDef],
    binders: Binders,
    sentences: SentenceConfig,
) -> list[Scope]:
    """Every non-constant mention's scope: its binding site and the site it reopens, or none."""
    nlp = pipeline(sentences)
    matcher, phrases = _matchers(nlp, binders)
    tokens = math_tokens(values, mentions, relations)
    segments = list(content.document.walk())
    units = [s for s in segments if s.kind in ANNOTATION_UNIT]
    sections = [s for s in segments if s.kind in SECTION_LIKE]
    sites: list[BindingSite] = []
    for block, block_sentences in _blocks(content):
        sites += _sites(
            content, block, block_sentences, tokens, nlp, matcher, phrases, units, sections, macros
        )
    sites.sort(key=lambda s: s.mention.start)  # stable: page order, then creation
    sites = _with_reopens(sites)
    by_symbol: dict[str, list[BindingSite]] = {}
    for site in sites:
        by_symbol.setdefault(site.symbol, []).append(site)
    out = []
    for m in mentions:
        if m.constant:
            continue
        symbol = symbol_form(content.canonical_text[m.start : m.end], macros)
        candidates = [
            s
            for s in by_symbol.get(symbol, [])
            if (s.mention.start <= m.start and s.start <= m.start < s.end)
            or s.mention.start == m.start
        ]
        best = min(candidates, key=lambda s: s.end - s.start) if candidates else None
        out.append(Scope(m, symbol, best))
    return out


def _sites(
    content: RenditionContent,
    block: Segment,
    block_sentences: list[Segment],
    tokens: Mapping[int, MathToken],
    nlp: Language,
    matcher: Matcher,
    phrases: PhraseMatcher,
    units: list[Segment],
    sections: list[Segment],
    macros: Mapping[str, MacroDef],
) -> list[BindingSite]:
    doc: Doc = make_doc(nlp, _block(content, block))
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
                unit = _innermost(units, m.start)
                if unit is not None and not section_wide:
                    extent, scope, a, b = ScopeExtent.STATEMENT, unit, unit.start, unit.end
                else:
                    scope = _innermost(sections, m.start) or content.document
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
    out = []
    for site in sites:
        if site.reopen:
            previous = [
                p
                for p in sites
                if p.symbol == site.symbol
                and p.mention.start < site.mention.start
                and p.extent is not ScopeExtent.STATEMENT
            ]
            if previous:
                site = dataclasses.replace(site, reopens=previous[-1])
        out.append(site)
    return out
