"""`methods.llm.parse`: an authored batch and its frame to the stored batch on one rendition.

Agent-interface §3.1 (A0); D4 §4.3 step 2, D2 §7.3, D1 §10.3, D5 §5.6; ADR-0019; TM §7 (T1's
cascade half). A pure, schema-free function: it reads the rendition, the batch, the frame and the
schema version's name map, no database, clock or randomness that reaches its output (per-quote
timings are report-only).

**Frame resolution first.** Each frame entry is resolved with `core/frame.py`'s `resolve_frame` on
the locator resolver and checked against its recorded text. `resolved`; `relocated` when it did not
resolve as recorded but exactly one sentence of the rendition carries the recorded text (the report
then gives that sentence's locator on this rendition; nothing is written: a consumer that keeps the
re-location writes a new frame version); `unresolved` otherwise. Every entry that did not resolve as
recorded carries its `FrameFailureReason`, and a cited id the frame lacks is `not_in_frame`. The
batch's `unit_ref` resolves the same way to the unit segment.

**The cascade** (`cascade.py`) locates every quote among the resolved frame sentences: evidence,
`outside` descriptors, unsupported items and phrase leaves (values and condition nodes). A quote
that is not located keeps the cited sentence's span with `coarse: true`; a quote without a valid
cited sentence that is not located is dropped as `unlocated_quote` (a phrase leaf, whose sentence
is optional, falls back to a coarse span over the unit instead). A claim left without a placed
evidence quote or phrase is dropped as `unlocated_quote`; a statement whose anchor sentences are not
on the rendition (or whose unit is not) as `segment_not_on_rendition`. References to a dropped item
are left for `validate` and keying to report.

**Conversion.** Anchors `"unit"` and sentence ids become segment keys on the rendition. A local
entity's `extent` and a claim's `scope` qualifier resolve to a segment: `statement` -> the smallest
statement block enclosing the binding statement's anchors (a segment of a `statement_anchor` kind,
a unit or details block, or of a `sentence_split` kind, a paragraph, list item, table cell or
caption; so a sentence anchor gives its block), `section` -> the smallest section-like segment
holding the earliest evidence, `document` -> the document. A local entity's binding statement is the
earliest statement among the claims that mention it (subject, object, entity-valued qualifiers,
`variable`/`family_param` bindings, `pred` arguments). An extent that cannot be resolved is
reported as `unresolved_extent`; a `scope` qualifier is then left out and a local entity dropped,
never guessed. Names take their stored spelling from the version's name map
(`schema.lookup.NameMap`, passed as its `to_prefixed`): predicates,
entity types, identity slots, schema qualifiers and enums prefixed, pack members of the
version-scoped sets (statement kinds, modalities) as the map spells them. A name the map lacks is a
precondition failure: `validate` (S2) refuses unknown names before parse runs, and `UnknownName`
is the backstop.

**The report** carries `CASCADE_VERSION`, each frame entry's outcome, the unit's, every located
quote with its path (`claims[3].evidence[0]`), step, matches, scores and timeouts, and every drop
and unresolved extent with its code (DA-013).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, assert_never

from pydantic import MISSING, BaseModel

from corpus_structure.core import batch as B
from corpus_structure.core import values as V
from corpus_structure.core.evidence import MacroDef, RenditionContent, Segment, segment_key
from corpus_structure.core.frame import FrameOutcome, resolve_entry, sentences_by_text
from corpus_structure.core.locators import LocatorIndex, LocatorRefused, LocatorSyntaxError
from corpus_structure.core.locators import parse as parse_locator
from corpus_structure.core.vocab import (
    SECTION_LIKE,
    SENTENCE_SPLIT,
    STATEMENT_ANCHOR,
    BindKind,
    DropReason,
    EntityExtent,
    EntityScope,
    FrameFailureReason,
    ScopeExtent,
)
from corpus_structure.methods.llm.cascade import (
    CASCADE_VERSION,
    REFINE_TIMEOUT,
    REGEX_TIMEOUT,
    Cascade,
    FrameSentence,
    Located,
)

_ENTITY_BINDINGS = frozenset({BindKind.VARIABLE, BindKind.FAMILY_PARAM})
STATEMENT_BLOCK = STATEMENT_ANCHOR | SENTENCE_SPLIT


class UnknownName(KeyError):
    """A local name the schema version's name map lacks (`validate` refuses it before parse)."""


@dataclass(frozen=True)
class RenditionView:
    """What parse reads of a rendition: its content, page, `ren` key and effective macro table
    (`core/tex.py` `effective_macros`: the page's over the pack's fallback)."""

    content: RenditionContent
    page: str
    rendition_key: str
    macros: Mapping[str, MacroDef] = field(default_factory=dict)


@dataclass(frozen=True)
class UnitOutcome:
    locator: str
    segment: Segment | None
    code: FrameFailureReason | None = None


@dataclass(frozen=True)
class QuoteRecord:
    """One quote's outcome: located, coarse (the cited sentence's span) or dropped."""

    path: str
    quote: str
    sentence: str | None  # the cited sentence id, as authored
    located: Located
    coarse: bool = False
    dropped: DropReason | None = None
    frame: FrameFailureReason | None = None  # the cited sentence's frame code, when it failed


@dataclass(frozen=True)
class Problem:
    """A dropped item or an unresolved extent, with its code."""

    path: str
    code: DropReason
    detail: str
    frame: FrameFailureReason | None = None


@dataclass(frozen=True)
class ParseReport:
    cascade_version: str
    unit: UnitOutcome
    frame: tuple[FrameOutcome, ...]
    quotes: tuple[QuoteRecord, ...]
    problems: tuple[Problem, ...]

    def by_step(self) -> Counter[str]:
        out: Counter[str] = Counter()
        for q in self.quotes:
            if q.dropped is not None:
                out["dropped"] += 1
            elif q.coarse:
                out["coarse"] += 1
            else:
                assert q.located.step is not None
                out[q.located.step.value] += 1
        return out


@dataclass(frozen=True)
class Parsed:
    stored: B.StoredBatch
    report: ParseReport


# --- Frame resolution -------------------------------------------------------------------------


def resolve_entries(
    frame: B.CitationFrame, index: LocatorIndex, cited: Sequence[str] = ()
) -> dict[str, FrameOutcome]:
    """Every frame entry's outcome, and `not_in_frame` for each cited id the frame lacks."""
    by_text = sentences_by_text(index)
    out = {s: resolve_entry(s, entry, index, by_text) for s, entry in frame.root.items()}
    for sentence in cited:
        if sentence not in out:
            out[sentence] = FrameOutcome(sentence, "unresolved", FrameFailureReason.NOT_IN_FRAME)
    return out


def _resolve_unit(unit_ref: str, index: LocatorIndex) -> UnitOutcome:
    try:
        locator = parse_locator(unit_ref)
    except LocatorSyntaxError:
        return UnitOutcome(unit_ref, None, FrameFailureReason.LOCATOR_SYNTAX)
    if locator.page != index.page:
        return UnitOutcome(unit_ref, None, FrameFailureReason.OTHER_PAGE)
    try:
        return UnitOutcome(unit_ref, index.resolve(locator))
    except LocatorRefused:
        return UnitOutcome(unit_ref, None, FrameFailureReason.LOCATOR_REFUSED)


# --- Parse --------------------------------------------------------------------------------------


def parse(
    view: RenditionView,
    batch: B.AuthoredBatch,
    frame: B.CitationFrame,
    names: Mapping[str, str],
    *,
    cascade: Mapping[str, float] | None = None,
) -> Parsed:
    """The stored batch on `view`'s rendition and the report. `names` is the version's name map,
    local -> stored spelling; `cascade` may override the cascade's regex timeouts (tests)."""
    return _Parser(view, batch, frame, names, dict(cascade or {})).run()


class _Parser:
    def __init__(
        self,
        view: RenditionView,
        batch: B.AuthoredBatch,
        frame: B.CitationFrame,
        names: Mapping[str, str],
        timeouts: dict[str, float],
    ) -> None:
        self.view = view
        self.text = view.content.canonical_text
        self.batch = batch
        self.names = names
        self.index = LocatorIndex(view.content, view.page)
        self.outcomes = resolve_entries(frame, self.index, B.cited_sentences(batch))
        self.unit = _resolve_unit(batch.unit_ref, self.index)
        sentences = [
            FrameSentence(o.sentence, o.segment.start, o.segment.end)
            for o in self.outcomes.values()
            if o.segment is not None
        ]
        if set(timeouts) - {"regex_timeout", "refine_timeout"}:
            raise ValueError("unknown citation cascade timeout option")
        self.cascade = Cascade(
            self.text,
            sentences,
            view.macros,
            regex_timeout=timeouts.get("regex_timeout", REGEX_TIMEOUT),
            refine_timeout=timeouts.get("refine_timeout", REFINE_TIMEOUT),
        )
        self.segments: list[Segment] = list(view.content.document.walk())
        self.quotes: list[QuoteRecord] = []
        self.problems: list[Problem] = []

    # -- helpers ----------------------------------------------------------------------------------

    def key(self, segment: Segment) -> str:
        return segment_key(self.view.rendition_key, segment.kind, segment.start, segment.end)

    def name(self, local: str) -> str:
        stored = self.names.get(local)
        if stored is None:
            raise UnknownName(local)
        return stored

    def member(self, local: str) -> str:
        """A member of a version-scoped set: a pack member as the map spells it, a core one bare."""
        return self.names.get(local, local)

    def drop(
        self, path: str, code: DropReason, detail: str, frame: FrameFailureReason | None = None
    ) -> None:
        self.problems.append(Problem(path, code, detail, frame))

    def segment_of(self, sentence: str | None) -> Segment | None:
        outcome = self.outcomes.get(sentence) if sentence is not None else None
        return outcome.segment if outcome is not None else None

    def place(
        self, path: str, quote: str, sentence: str | None, fallback: Segment | None = None
    ) -> tuple[int, int, bool] | None:
        """A quote's span and whether it is coarse, or None when it is dropped (recorded)."""
        cited = self.segment_of(sentence)
        frame_code = (
            self.outcomes[sentence].code
            if sentence is not None and sentence in self.outcomes and cited is None
            else None
        )
        located = self.cascade.locate(quote, sentence if cited is not None else None)
        if located.found:
            assert located.start is not None and located.end is not None
            self.quotes.append(QuoteRecord(path, quote, sentence, located, frame=frame_code))
            return located.start, located.end, False
        coarse = cited if cited is not None else fallback
        if coarse is not None:
            self.quotes.append(
                QuoteRecord(path, quote, sentence, located, coarse=True, frame=frame_code)
            )
            return coarse.start, coarse.end, True
        code = DropReason.UNLOCATED_QUOTE
        self.quotes.append(
            QuoteRecord(path, quote, sentence, located, dropped=code, frame=frame_code)
        )
        self.drop(
            path, code, "unlocated, and its cited sentence is not on the rendition", frame_code
        )
        return None

    def enclosing(self, segments: Sequence[Segment]) -> Segment | None:
        """The smallest statement block enclosing all of `segments`: a segment of a
        `statement_anchor` kind (a unit, a details block) or a sentence-holding block
        (`sentence_split`: a paragraph, a list item, ...), so a sentence anchor gives its block."""
        if not segments:
            return None
        lo, hi = min(s.start for s in segments), max(s.end for s in segments)
        inside = [
            s for s in self.segments if s.kind in STATEMENT_BLOCK and s.start <= lo and hi <= s.end
        ]
        return min(inside, key=lambda s: s.end - s.start) if inside else None

    def section(self, offset: int) -> Segment:
        inside = [s for s in self.segments if s.kind in SECTION_LIKE and s.start <= offset < s.end]
        return min(inside, key=lambda s: s.end - s.start) if inside else self.view.content.document

    # -- the batch --------------------------------------------------------------------------------

    def run(self) -> Parsed:
        b = self.batch
        statements, anchors = self.statements(b.statements)
        claims, starts = self.claims(b.claims, anchors)
        stored = B.StoredBatch(
            unit_ref=b.unit_ref,
            rendition=self.view.rendition_key,
            entities=self.entities(b.entities, b.claims, b.statements, anchors, starts),
            statements=statements,
            claims=claims,
            alternatives=b.alternatives,
            unsupported=self.unsupported(b.unsupported),
        )
        report = ParseReport(
            CASCADE_VERSION,
            self.unit,
            tuple(self.outcomes.values()),
            tuple(self.quotes),
            tuple(self.problems),
        )
        return Parsed(stored, report)

    def statements(
        self, items: Sequence[B.AuthoredStatement | B.AuthoredOutside]
    ) -> tuple[list[B.StoredStatement | B.StoredOutside], dict[str, list[Segment]]]:
        out: list[B.StoredStatement | B.StoredOutside] = []
        anchors: dict[str, list[Segment]] = {}
        for i, item in enumerate(items):
            path = f"statements[{i}]"
            if isinstance(item, B.AuthoredOutside):
                d = item.descriptor
                placed = self.place(f"{path}.descriptor", d.quote, d.sentence)
                if placed is None:
                    continue
                a, e, coarse = placed
                descriptor = B.StoredDescriptor(
                    start=a, end=e, **_coarse(coarse), **_present(target=d.target)
                )
                out.append(
                    B.StoredOutside(
                        local_ref=item.local_ref, anchor="outside", descriptor=descriptor
                    )
                )
                continue
            if item.anchor == "unit":
                segments = [self.unit.segment] if self.unit.segment is not None else []
                if not segments:
                    self.drop(
                        path,
                        DropReason.SEGMENT_NOT_ON_RENDITION,
                        "anchored to the unit, which is not on the rendition",
                        self.unit.code,
                    )
                    continue
            else:
                segments = []
                for k, sentence in enumerate(item.anchor):
                    segment = self.segment_of(sentence)
                    if segment is None:
                        self.drop(
                            f"{path}.anchor[{k}]",
                            DropReason.SEGMENT_NOT_ON_RENDITION,
                            f"anchor sentence {sentence} is not on the rendition",
                            self.outcomes[sentence].code,
                        )
                    else:
                        segments.append(segment)
                if not segments:
                    self.drop(
                        path,
                        DropReason.SEGMENT_NOT_ON_RENDITION,
                        "no anchor sentence is on the rendition",
                    )
                    continue
            anchors[item.local_ref] = segments
            out.append(
                B.StoredStatement(
                    local_ref=item.local_ref,
                    kind=self.member(item.kind),
                    anchor=tuple(self.key(s) for s in segments),
                )
            )
        return out, anchors

    def claims(
        self, items: Sequence[B.AuthoredClaim], anchors: Mapping[str, list[Segment]]
    ) -> tuple[list[B.StoredClaim], dict[str, int]]:
        out: list[B.StoredClaim] = []
        starts: dict[str, int] = {}
        for i, c in enumerate(items):
            path = f"claims[{i}]"
            evidence = []
            for k, ev in enumerate(c.evidence):
                placed = self.place(f"{path}.evidence[{k}]", ev.quote, ev.sentence)
                if placed is not None:
                    a, e, coarse = placed
                    evidence.append(
                        B.StoredEvidence(start=a, end=e, role=ev.role, **_coarse(coarse))
                    )
            if not evidence:
                self.drop(path, DropReason.UNLOCATED_QUOTE, "no evidence quote is placed")
                continue
            starts[c.local_ref] = min(e.start for e in evidence)
            obj = self.value(c.object, f"{path}.object")
            qualifiers = self.qualifiers(c, f"{path}.qualifiers", anchors, starts[c.local_ref])
            if obj is _DROPPED or qualifiers is _DROPPED:
                self.drop(
                    path,
                    DropReason.UNLOCATED_QUOTE,
                    "a phrase of the claim is not placed",
                )
                continue
            fields = {
                name: getattr(c, name)
                for name in (
                    "local_ref",
                    "subject",
                    "statement",
                    "statement_role",
                    "establishment",
                    "derived_from",
                    "rule",
                )
                if getattr(c, name) is not MISSING
            }
            out.append(
                B.StoredClaim(
                    **fields,
                    predicate=self.name(c.predicate),
                    object=obj,
                    qualifiers=qualifiers,
                    evidence=tuple(evidence),
                )
            )
        return out, starts

    def qualifiers(
        self, c: B.AuthoredClaim, path: str, anchors: Mapping[str, list[Segment]], start: int
    ) -> B.StoredQualifiers | object:
        q = c.qualifiers
        out: dict[str, Any] = {}
        if q.modality != B.DEFAULT_MODALITY:
            out["core:modality"] = self.member(q.modality)
        if q.polarity != B.DEFAULT_POLARITY:
            out["core:polarity"] = q.polarity
        if q.attribution is not MISSING:
            out["core:attribution"] = q.attribution
        if q.valid_time is not MISSING:
            out["core:valid_time"] = q.valid_time
        if q.hedge is not MISSING:
            hedge = self.phrase(q.hedge, f"{path}.hedge")
            if hedge is None:
                return _DROPPED
            out["core:hedge"] = hedge
        if q.conditions is not MISSING:
            conditions = self.condition(q.conditions, f"{path}.conditions")
            if conditions is None:
                return _DROPPED
            out["core:conditions"] = conditions
        if q.scope is not MISSING:
            segment = self.scope_segment(q.scope, c, anchors, start, f"{path}.scope")
            if segment is not None:
                out["core:scope"] = B.StoredScope(extent=q.scope, segment=self.key(segment))
        for name, raw in (q.__pydantic_extra__ or {}).items():
            converted = self.raw(raw, f"{path}.{name}")
            if converted is _DROPPED:
                return _DROPPED
            out[self.name(name)] = converted
        return B.StoredQualifiers.model_validate(out)

    def scope_segment(
        self,
        extent: ScopeExtent,
        c: B.AuthoredClaim,
        anchors: Mapping[str, list[Segment]],
        start: int,
        path: str,
    ) -> Segment | None:
        match extent:
            case ScopeExtent.STATEMENT:
                stmt = c.statement if c.statement is not MISSING else None
                segment = self.enclosing(anchors.get(stmt, [])) if stmt is not None else None
            case ScopeExtent.SECTION:
                segment = self.section(start)
            case ScopeExtent.DOCUMENT:
                segment = self.view.content.document
            case _:
                assert_never(extent)
        if segment is None:
            self.drop(
                path,
                DropReason.UNRESOLVED_EXTENT,
                f"scope {extent.value!r} has no segment; the qualifier is left out",
            )
        return segment

    def unsupported(self, items: Sequence[B.AuthoredUnsupported]) -> list[B.StoredUnsupported]:
        out = []
        for i, u in enumerate(items):
            placed = self.place(f"unsupported[{i}]", u.quote, u.sentence)
            if placed is None:
                continue
            a, e, coarse = placed
            out.append(
                B.StoredUnsupported(
                    local_ref=u.local_ref, start=a, end=e, reason=u.reason, **_coarse(coarse)
                )
            )
        return out

    def entities(
        self,
        items: Sequence[B.AuthoredEntity],
        claims: Sequence[B.AuthoredClaim],
        statements: Sequence[B.AuthoredStatement | B.AuthoredOutside],
        anchors: Mapping[str, list[Segment]],
        starts: Mapping[str, int],
    ) -> list[B.StoredEntity]:
        local = {e.local_ref for e in items if e.scope is EntityScope.LOCAL}
        mentions: dict[str, list[B.AuthoredClaim]] = {}
        for c in claims:
            for ref in _entity_refs(c):
                if ref in local and c not in mentions.setdefault(ref, []):
                    mentions[ref].append(c)
        order = [s.local_ref for s in statements]
        out = []
        for i, e in enumerate(items):
            fields: dict[str, Any] = {
                "local_ref": e.local_ref,
                "type": self.name(e.type),
                "label": e.label,
                "scope": e.scope,
                "aliases": e.aliases,
                "identity": {self.name(slot): v for slot, v in e.identity.items()},
                **_present(extent=e.extent, symbol=e.symbol),
            }
            if e.scope is EntityScope.LOCAL:
                segment = self.extent(e, mentions.get(e.local_ref, []), order, anchors, starts)
                if segment is None:  # reported, the entity kept without the field (never guessed)
                    self.drop(
                        f"entities[{i}]",
                        DropReason.UNRESOLVED_EXTENT,
                        f"extent {_text(e.extent)!r} of local entity {e.local_ref!r} "
                        "has no segment",
                    )
                else:
                    fields["scope_segment"] = self.key(segment)
            out.append(B.StoredEntity(**fields))
        return out

    def extent(
        self,
        e: B.AuthoredEntity,
        claims: Sequence[B.AuthoredClaim],
        order: list[str],
        anchors: Mapping[str, list[Segment]],
        starts: Mapping[str, int],
    ) -> Segment | None:
        with_statement = [c for c in claims if c.statement is not MISSING]
        binding: str | None = None
        if with_statement:
            first = min(
                with_statement,
                key=lambda c: (
                    starts.get(c.local_ref, 10**12),
                    order.index(c.statement) if c.statement in order else 10**6,
                ),
            )
            binding = str(first.statement)
        elif len(order) == 1:
            binding = order[0]
        match e.extent:
            case EntityExtent.STATEMENT:
                return self.enclosing(anchors.get(binding, [])) if binding is not None else None
            case EntityExtent.SECTION:
                evidence = [starts[c.local_ref] for c in claims if c.local_ref in starts]
                if evidence:
                    return self.section(min(evidence))
                bound = anchors.get(binding, []) if binding is not None else []
                if bound:
                    return self.section(min(s.start for s in bound))
                if self.unit.segment is not None:
                    return self.section(self.unit.segment.start)
                return None
            case _:
                return None  # a local entity without an extent

    # -- values, phrases, conditions --------------------------------------------------------------

    def phrase(self, p: V.AuthoredPhrase, path: str) -> V.StoredPhrase | None:
        placed = self.place(path, p.text, _text(p.sentence), fallback=self.unit.segment)
        if placed is None:
            return None
        a, e, coarse = placed
        text = p.text if coarse else self.text[a:e]
        return V.StoredPhrase(t="phrase", text=text, start=a, end=e, **_coarse(coarse))

    def value(self, v: V.EntityRef | Any, path: str) -> Any:
        if isinstance(v, V.AuthoredPhrase):
            stored = self.phrase(v, path)
            return _DROPPED if stored is None else stored
        if isinstance(v, V.AuthoredEnumValue):
            return V.StoredEnumValue(t="enum", enum=self.name(v.enum), v=v.v)
        return v

    def condition(self, node: V.AuthoredCondition, path: str) -> V.StoredCondition | None:
        match node:
            case V.AuthoredAnd() | V.AuthoredOr():
                args = [self.condition(a, f"{path}.args[{i}]") for i, a in enumerate(node.args)]
                if any(a is None for a in args):
                    return None
                kept = tuple(a for a in args if a is not None)
                if isinstance(node, V.AuthoredAnd):
                    return V.StoredAnd(op="and", args=kept)
                return V.StoredOr(op="or", args=kept)
            case V.AuthoredNot():
                arg = self.condition(node.arg, f"{path}.arg")
                return None if arg is None else V.StoredNot(op="not", arg=arg)
            case V.AuthoredForall():
                body = self.condition(node.body, f"{path}.body")
                if body is None:
                    return None
                return V.StoredForall(op="forall", var=node.var, set=node.set, body=body)
            case V.AuthoredUnsupportedNode():
                placed = self._node_span(node, path)
                if placed is None:
                    return None
                text, a, e, coarse = placed
                return V.StoredUnsupportedNode(
                    op="unsupported",
                    text=text,
                    start=a,
                    end=e,
                    reason=node.reason,
                    **_coarse(coarse),
                )
            case V.AuthoredPhraseNode():
                placed = self._node_span(node, path)
                if placed is None:
                    return None
                text, a, e, coarse = placed
                return V.StoredPhraseNode(op="phrase", text=text, start=a, end=e, **_coarse(coarse))
            case V.ClaimNode() | V.MemberNode() | V.CmpNode() | V.PredNode():
                return node
            case _:
                assert_never(node)

    def _node_span(
        self, node: V.AuthoredPhraseNode | V.AuthoredUnsupportedNode, path: str
    ) -> tuple[str, int, int, bool] | None:
        placed = self.place(path, node.text, _text(node.sentence), fallback=self.unit.segment)
        if placed is None:
            return None
        a, e, coarse = placed
        return (node.text if coarse else self.text[a:e]), a, e, coarse

    def raw(self, value: Any, path: str) -> Any:
        """A schema qualifier's raw JSON: phrase values and nodes located, enums prefixed."""
        if isinstance(value, dict):
            if value.get("t") == "phrase" or value.get("op") in ("phrase", "unsupported"):
                sentence = value.get("sentence")
                placed = self.place(
                    path,
                    str(value.get("text", "")),
                    sentence if isinstance(sentence, str) else None,
                    fallback=self.unit.segment,
                )
                if placed is None:
                    return _DROPPED
                a, e, coarse = placed
                out = {k: v for k, v in value.items() if k != "sentence"}
                out.update(start=a, end=e)
                if coarse:
                    out["coarse"] = True
                else:
                    out["text"] = self.text[a:e]
                return out
            if value.get("t") == "enum" and isinstance(value.get("enum"), str):
                return {**value, "enum": self.name(value["enum"])}
            converted = {}
            for k, v in value.items():
                c = self.raw(v, f"{path}.{k}")
                if c is _DROPPED:
                    return _DROPPED
                converted[k] = c
            return converted
        if isinstance(value, list):
            items = [self.raw(v, f"{path}[{i}]") for i, v in enumerate(value)]
            return _DROPPED if any(v is _DROPPED for v in items) else items
        return value


_DROPPED: Any = object()  # a sentinel: the containing claim is dropped


def _coarse(coarse: bool) -> dict[str, bool]:
    return {"coarse": True} if coarse else {}


def _present(**fields: Any) -> dict[str, Any]:
    return {k: v for k, v in fields.items() if v is not MISSING}


def _text(value: Any) -> Any:
    return None if value is MISSING else value


def _entity_refs(claim: B.AuthoredClaim) -> Iterator[str]:
    """The entity refs a claim mentions: subject, object, entity-valued qualifiers,
    `variable`/`family_param` bindings and `pred` arguments (raw schema qualifiers included)."""
    yield claim.subject

    def walk(node: Any) -> Iterator[str]:
        if isinstance(node, V.EntityRef):
            yield node.ref
        elif isinstance(node, V.SymbolBinding):
            if node.bind in _ENTITY_BINDINGS and node.entity is not MISSING:
                yield node.entity
        elif isinstance(node, BaseModel):
            for name in type(node).model_fields:
                yield from walk(getattr(node, name))
            for extra in (node.__pydantic_extra__ or {}).values():
                yield from walk(extra)
        elif isinstance(node, dict):
            if isinstance(node.get("ref"), str) and "op" not in node:
                yield node["ref"]
            if node.get("bind") in _ENTITY_BINDINGS and isinstance(node.get("entity"), str):
                yield node["entity"]
            for item in node.values():
                yield from walk(item)
        elif isinstance(node, tuple | list):
            for item in node:
                yield from walk(item)

    yield from walk(claim.object)
    yield from walk(claim.qualifiers)
