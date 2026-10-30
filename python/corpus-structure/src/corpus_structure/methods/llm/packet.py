"""`methods.llm.packet`: the packet assembler (agent interface §3.3; D4 §4.1; D8 §3).

A packet is a **pure function of recorded inputs**: the unit's segments on the run's rendition of
its page, the rendition's title and section path, the source's statement-kind hint, the standing
context (I2a's `standing_context` over the rendition's stored `scope` observations, through the
adapter below), and, in agent mode, the known entities. Nothing read at serving time enters it.

**Rendering** is S0-R2's v1 (records `s0r2.inputs`, `s0r2.scores`): a header line with the unit
key, title, section path and hint; `## Standing context` with its note and `[cN]` lines or
`(none)`; in agent mode `## Known entities`; `## Text` with `[sN]` lines and inner headings as
`--- heading ---` lines, which carry no id. Golden-mode packets (no known entities) reproduce the
v1 packets and the pack's worked examples byte for byte.

**Parts and the cap.** A packet longer than `cap` characters is split at sentence boundaries;
every part repeats the header (with "part i of n"), the standing context and the known entities,
and sentence ids run through the parts. A sentence longer than the room in a part is a part of its
own, served whole and flagged. Header, context and entities alone over the cap raise
`PacketTooLarge`.

**The sentence map** gives each `sN` and `cN` its locator (generated on the rendition) and text;
the citation frame of a submission is the map's entries for the ids it cites. **The hash** is the
SHA-256 of the canonical JSON of the list of part texts.

**Stored scopes.** `stored_scopes` rebuilds, from the stored payloads alone (`ScopePayload` and
M09's `MentionPayload`), the views `standing_context` reads: each scope's mention (its start and
`math.in_subscript_of`), its symbol (`symbol_form` of the mention's text under the effective
macros, M13's rule) and its binding site's sentence and reopened site's sentence (the sentence
segments holding the stored offsets). Mentions are found by their offsets, as `MentionAt` intends.

**Known entities.** With a reference run: its global entities with a claim whose evidence lies on
its rendition of the same document, by key, at most 30, with class, label and aliases. Without one
(the bootstrap): the page title and the `dfn` terms of the rendition's author markup, as terms
without a class, in page order.
"""

from __future__ import annotations

import hashlib
from bisect import bisect_left, bisect_right
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, cast

from corpus_structure.core.batch import CitationFrame
from corpus_structure.core.canonical import canonical_json
from corpus_structure.core.evidence import MacroDef, RenditionContent, Segment
from corpus_structure.core.keys import symbol_form
from corpus_structure.core.locators import LocatorIndex
from corpus_structure.core.locators import parse as parse_locator
from corpus_structure.core.method import CoverageDraft, SourceCoverageReading
from corpus_structure.core.payloads import MentionAt, MentionPayload, ScopePayload
from corpus_structure.core.vocab import SegmentKind
from corpus_structure.methods.llm.parts import hint_of
from corpus_structure.methods.math.context import ContextSentence, standing_context

if TYPE_CHECKING:
    from corpus_structure.core.method import Reader

CONTEXT_NOTE = (
    "Sentences outside the unit that it depends on: where symbols it uses were introduced and are "
    "still in force, and section-wide suppositions. Cite them as `cN` (guideline §10.2)."
)
ENTITIES_NOTE = (
    "Labels already identified for this page; reuse a label when you mean the same thing."
)
MAX_KNOWN = 30
SCOPE_METHOD, MENTION_METHOD = "resolve.symbol_scope", "extract.math"


class PacketTooLarge(ValueError):
    """The header, standing context and known entities alone exceed the cap."""


@dataclass(frozen=True)
class SentenceEntry:
    id: str  # sN or cN
    locator: str
    text: str


@dataclass(frozen=True)
class KnownEntity:
    label: str
    cls: str | None = None  # None: a bootstrap term
    aliases: tuple[str, ...] = ()

    def line(self) -> str:
        if self.cls is None:
            return f'- term "{self.label}"'
        aliases = f" · aliases: {', '.join(self.aliases)}" if self.aliases else ""
        return f'- {self.cls} "{self.label}"{aliases}'


@dataclass(frozen=True)
class StandingContextCoverage:
    coverage: CoverageDraft
    basis_digest: str
    source_tasks: tuple[tuple[int, str], ...] = ()


@dataclass(frozen=True)
class _CoverageIndex:
    rows: tuple[SourceCoverageReading, ...]
    starts: tuple[int, ...]
    prefix_ends: tuple[int, ...]
    unlocated: tuple[SourceCoverageReading, ...]
    math_ranges: tuple[tuple[int, int], ...]
    math_starts: tuple[int, ...]
    math_prefix_ends: tuple[int, ...]
    source_tasks: tuple[tuple[int, str], ...]

    @classmethod
    def prepare(cls, content, rows):
        from corpus_structure.methods.math.spans import math_spans

        located = tuple(
            sorted(
                (row for row in rows if row.start is not None and row.end is not None),
                key=lambda row: (row.start, row.end, row.task_id, row.position),
            )
        )
        starts, ends = [], []
        for row in located:
            starts.append(row.start)
            ends.append(max(ends[-1] if ends else 0, row.end))
        math_ranges = tuple((span.segment.start, span.segment.end) for span in math_spans(content))
        math_ends = []
        for _, end in math_ranges:
            math_ends.append(max(math_ends[-1] if math_ends else 0, end))
        return cls(
            located,
            tuple(starts),
            tuple(ends),
            tuple(row for row in rows if row.start is None or row.end is None),
            math_ranges,
            tuple(a for a, _ in math_ranges),
            tuple(math_ends),
            tuple(sorted({(row.task_id, row.release_id) for row in rows})),
        )

    def for_unit(self, key, unit, context):
        regions = [(part.start, part.end) for part in unit]
        regions += [(item.segment.start, item.segment.end) for item in context]
        selected = {(row.task_id, row.position): row for row in self.unlocated}
        for a, b in regions:
            lo, hi = bisect_right(self.prefix_ends, a), bisect_left(self.starts, b)
            for row in self.rows[lo:hi]:
                assert row.end is not None
                if row.end > a:
                    selected[row.task_id, row.position] = row
        expected = set()
        for a, b in regions:
            lo, hi = bisect_right(self.math_prefix_ends, a), bisect_left(self.math_starts, b)
            expected.update((start, end) for start, end in self.math_ranges[lo:hi] if end > a)
        rows = tuple(selected[key] for key in sorted(selected))
        covered = {(row.start, row.end) for row in rows}
        counts = Counter(row.coverage.outcome for row in rows)
        missing = bool(expected - covered)
        incomplete = missing or any(row.coverage.outcome != "complete" for row in rows)
        if (not expected and not rows) or (not incomplete and rows):
            outcome, reason = "complete", None
        else:
            outcome = (
                "partial"
                if counts["complete"] or counts["partial"]
                else "unsupported"
                if counts["unsupported"] and not missing
                else "unknown"
            )
            reasons = sorted({row.coverage.reason for row in rows if row.coverage.reason})
            if missing:
                reasons.insert(0, "required scope coverage unavailable")
            reason = "; ".join(reasons[:3]) or "scope coverage unavailable"
        basis = {
            "expected": sorted(expected),
            "rows": [asdict(row) for row in rows],
            "sources": self.source_tasks
            if not rows
            else sorted({(row.task_id, row.release_id) for row in rows}),
        }
        digest = hashlib.sha256(canonical_json(basis)).hexdigest()
        return StandingContextCoverage(
            CoverageDraft(
                family=SCOPE_METHOD,
                scope=key,
                outcome=outcome,
                reason=reason,
                required_capability="interpretation",
            ),
            digest,
            tuple(basis["sources"]),
        )


@dataclass(frozen=True)
class Packet:
    unit_key: str
    parts: tuple[str, ...]
    hash: str
    sentences: tuple[SentenceEntry, ...]  # cN first, then sN in order
    part_ids: tuple[tuple[str, ...], ...]  # each part's sN ids
    oversize: tuple[str, ...] = ()  # sentences served whole beyond the cap
    source_coverage: StandingContextCoverage | None = None

    @property
    def chars(self) -> int:
        return sum(len(p) for p in self.parts)

    def part_sentences(self, part: int) -> tuple[SentenceEntry, ...]:
        """The part's map: the context sentences (every part repeats them) and its own `sN`."""
        own = set(self.part_ids[part])
        return tuple(s for s in self.sentences if s.id.startswith("c") or s.id in own)

    def frame(self, ids: Iterable[str]) -> CitationFrame:
        by_id = {s.id: s for s in self.sentences}
        wanted = sorted(set(ids) & set(by_id), key=_id_order)
        return CitationFrame.model_validate(
            {i: {"locator": by_id[i].locator, "text": by_id[i].text} for i in wanted}
        )


def _id_order(sentence_id: str) -> tuple[str, int]:
    return sentence_id[0], int(sentence_id[1:])


def packet_hash(
    parts: Sequence[str], source_coverage: StandingContextCoverage | None = None
) -> str:
    value = list(parts) if source_coverage is None else [list(parts), asdict(source_coverage)]
    return hashlib.sha256(canonical_json(value)).hexdigest()


# --- The unit's place on the page -------------------------------------------------------------


def _ancestors(root: Segment, target: Segment) -> list[Segment]:
    """The chain from the root down to `target`'s parent."""
    path: list[Segment] = []

    def walk(node: Segment) -> bool:
        for child in node.children:
            if child is target or (child.kind, child.start, child.end) == (
                target.kind,
                target.start,
                target.end,
            ):
                return True
            if child.start <= target.start and target.end <= child.end:
                path.append(child)
                if walk(child):
                    return True
                path.pop()
        return False

    walk(root)
    return [root, *path]


def title_of(content: RenditionContent) -> str:
    """The page title: the document's own heading."""
    for child in content.document.children:
        if child.kind is SegmentKind.HEADING:
            return content.text(child)
    return ""


def header(content: RenditionContent, unit_key: str, unit: Sequence[Segment]) -> str:
    first = unit[0]
    sections = [s for s in _ancestors(content.document, first) if s.kind is SegmentKind.SECTION]
    path = " › ".join(  # noqa: RUF001 - the rendering's separator (S0-R2 v1)
        str((s.attrs or {}).get("title") or content.text(s).split("\n", 1)[0]) for s in sections
    )
    place = f"{title_of(content)} › {path}" if path else title_of(content)  # noqa: RUF001
    hint = hint_of(first).get("statement_kind")
    return f"# Unit {unit_key}  ·  {place}" + (f"  ·  the source marks it: {hint}" if hint else "")


def _text_items(content: RenditionContent, unit: Sequence[Segment]) -> list[tuple[str, Segment]]:
    """The unit's sentences and inner headings in page order."""
    items: list[tuple[int, str, Segment]] = []
    for part in unit:
        for s in part.walk():
            if s.kind is SegmentKind.SENTENCE:
                items.append((s.start, "s", s))
            elif s.kind is SegmentKind.HEADING and part.start <= s.start and s.end <= part.end:
                items.append((s.start, "h", s))
    return [(kind, s) for _, kind, s in sorted(items, key=lambda i: (i[0], i[1]))]


# --- Rendering --------------------------------------------------------------------------------


def render(
    content: RenditionContent,
    page: str,
    unit_key: str,
    unit: Sequence[Segment],
    context: Sequence[ContextSentence],
    known: Sequence[KnownEntity] | None = None,
    cap: int | None = None,
    *,
    source_coverage: StandingContextCoverage | None = None,
) -> Packet:
    """The packet (module doc); `known` None is golden mode (no known-entities section)."""
    index = LocatorIndex(content, page)
    head = header(content, unit_key, unit)
    shared = ["", "## Standing context", CONTEXT_NOTE, ""]
    if source_coverage is not None and source_coverage.coverage.outcome != "complete":
        coverage = source_coverage.coverage
        diagnostic = f"scope coverage {coverage.outcome}: {coverage.reason}"
        shared += [f"[{c.id}] {c.text}" for c in context] or [
            f"(no established context; {diagnostic})"
        ]
        if context:
            shared.append(f"Context may be incomplete; {diagnostic}.")
    else:
        shared += [f"[{c.id}] {c.text}" for c in context] or ["(none)"]
    if known is not None:
        shared += ["", "## Known entities", ENTITIES_NOTE, ""]
        shared += [k.line() for k in known] or ["(none)"]
    shared += ["", "## Text"]
    entries = [SentenceEntry(c.id, c.locator, c.text) for c in context]
    lines: list[tuple[str | None, str]] = []  # (sentence id or None for a heading, line)
    n = 0
    for kind, s in _text_items(content, unit):
        text = content.text(s)
        if kind == "h":
            lines.append((None, f"--- {text} ---"))
            continue
        n += 1
        sid = f"s{n}"
        entries.append(SentenceEntry(sid, str(index.generate(s)), text))
        lines.append((sid, f"[{sid}] {text}"))

    def assemble(head_line: str, body: Sequence[str]) -> str:
        return "\n".join([head_line, *shared, *body]) + "\n"

    whole = assemble(head, [line for _, line in lines])
    if cap is None or len(whole) <= cap:
        ids = tuple(i for i, _ in lines if i is not None)
        return Packet(
            unit_key,
            (whole,),
            packet_hash([whole], source_coverage),
            tuple(entries),
            (ids,),
            source_coverage=source_coverage,
        )
    room_head = f"{head}  ·  part 999 of 999"
    base = len(assemble(room_head, []))
    if base > cap:
        raise PacketTooLarge(
            f"{unit_key}: header, standing context and known entities take {base} characters, "
            f"over the cap of {cap}"
        )
    groups: list[list[tuple[str | None, str]]] = [[]]
    oversize: list[str] = []
    used = base
    for sid, line in lines:
        size = len(line) + 1
        if groups[-1] and used + size > cap:
            groups.append([])
            used = base
        groups[-1].append((sid, line))
        used += size
        if used > cap and sid is not None:
            oversize.append(sid)
    total = len(groups)
    parts = tuple(
        assemble(f"{head}  ·  part {i + 1} of {total}", [line for _, line in g])
        for i, g in enumerate(groups)
    )
    part_ids = tuple(tuple(sid for sid, _ in g if sid is not None) for g in groups)
    return Packet(
        unit_key,
        parts,
        packet_hash(parts, source_coverage),
        tuple(entries),
        part_ids,
        tuple(oversize),
        source_coverage,
    )


# --- Stored scopes (the adapter) --------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _MentionView:
    start: int
    end: int
    in_subscript_of: str | None


@dataclass(frozen=True, slots=True)
class _SiteView:
    sentence: Segment
    reopens: _SiteView | None = None


@dataclass(frozen=True, slots=True)
class ScopeView:
    """What `standing_context` reads of an M13 scope, rebuilt from stored payloads."""

    mention: _MentionView
    symbol: str
    site: _SiteView | None


def _sentence_at(sentences: Sequence[Segment], pos: int) -> Segment | None:
    for s in sentences:
        if s.start <= pos < s.end:
            return s
    return None


def stored_scopes(
    content: RenditionContent,
    mentions: Iterable[Mapping[str, Any]],
    scopes: Iterable[Mapping[str, Any]],
    macros: Mapping[str, MacroDef],
) -> list[ScopeView]:
    """The scope views of a rendition from its stored M09 `mention` and M13 `scope` payloads
    (module doc); `macros` are the effective table (the page's over the pack's)."""
    by_span: dict[tuple[int, int], MentionPayload] = {}
    for raw in mentions:
        m = MentionPayload.model_validate(raw)
        by_span.setdefault((m.start, m.end), m)
    sentences = [s for s in content.document.walk() if s.kind is SegmentKind.SENTENCE]
    out = []
    for raw in scopes:
        scope = ScopePayload.model_validate(raw)
        mention = by_span.get((scope.start, scope.end))
        math = mention.math if mention is not None and isinstance(mention.math, dict) else {}
        sub = math.get("in_subscript_of")
        view = _MentionView(scope.start, scope.end, sub if isinstance(sub, str) else None)
        symbol = symbol_form(content.canonical_text[scope.start : scope.end], macros)
        site_sentence = _sentence_at(sentences, scope.binding_site.start)
        reopens = None
        if isinstance(scope.reopens, MentionAt):
            reopened = _sentence_at(sentences, scope.reopens.start)
            reopens = _SiteView(reopened) if reopened is not None else None
        site = _SiteView(site_sentence, reopens) if site_sentence is not None else None
        out.append(ScopeView(view, symbol, site))
    return out


def stored_bound_scopes(content: RenditionContent, mentions, scopes, macros) -> list[ScopeView]:
    """Match bound reports by stable source identity, preserving parallel same-span readings."""
    from corpus_structure.core.method import StableObservationReading

    by_key = {}
    for row in mentions:
        if not isinstance(row, StableObservationReading):
            raise ValueError("bound scope inputs require stable source reports")
        if row.observation_key in by_key:
            raise ValueError("duplicate source observation identity")
        by_key[row.observation_key] = row.payload
    out = []
    for row in scopes:
        if not isinstance(row, StableObservationReading):
            raise ValueError("bound scope input is not release-bound")
        refs = [ref for ref in row.input_refs if ref.role == "mention"]
        if len(refs) != 1 or refs[0].observation_key not in by_key:
            raise ValueError("bound scope lacks its exact source mention")
        mention = by_key[refs[0].observation_key]
        if (mention["start"], mention["end"]) != (row.payload["start"], row.payload["end"]):
            raise ValueError("bound mention coordinates differ from scope source")
        out.extend(stored_scopes(content, [mention], [row.payload], macros))
    return out


def context_from_stored(
    content: RenditionContent,
    page: str,
    unit: Sequence[Segment],
    views: Sequence[ScopeView],
) -> list[ContextSentence]:
    """I2a's standing context over the stored scope views (they carry what it reads)."""
    return standing_context(content, page, cast(Any, views), unit)


# --- Known entities ---------------------------------------------------------------------------


def bootstrap_terms(content: RenditionContent) -> list[KnownEntity]:
    """The page title and the `dfn` terms of the author markup, in page order, once each."""
    seen: dict[str, None] = {}
    title = title_of(content)
    if title:
        seen[title] = None
    spans: list[tuple[int, int]] = []
    for s in content.document.walk():
        marks = (s.attrs or {}).get("markup")
        for mark in marks if isinstance(marks, list) else ():
            if isinstance(mark, dict) and mark.get("markup") == "dfn":
                start, end = mark.get("start"), mark.get("end")
                if isinstance(start, int) and isinstance(end, int):
                    spans.append((start, end))
    for a, b in sorted(set(spans)):
        term = " ".join(content.canonical_text[a:b].split())
        if term:
            seen.setdefault(term, None)
    return [KnownEntity(t) for t in seen]


_KNOWN = """
SELECT e.key, e.type, e.label,
       coalesce((SELECT array_agg(a.alias ORDER BY a.alias) FROM kb.entity_alias a
                 WHERE a.entity_id = e.id AND a.alias <> e.label), '{}') AS aliases
FROM kb.entity e
WHERE e.run_id = :ref AND e.scope = 'global' AND EXISTS (
  SELECT 1 FROM kb.claim c
  JOIN kb.claim_evidence ce ON ce.claim_id = c.id
  JOIN kb.span s ON s.id = ce.span_id
  JOIN kb.run_rendition rr ON rr.rendition_id = s.rendition_id
  WHERE c.run_id = :ref AND (c.subject_id = e.id OR c.object_entity_id = e.id)
    AND rr.run_id = :ref AND rr.document_id = :doc)
ORDER BY e.key
LIMIT :limit
"""


def reference_entities(conn: Any, reference_run: int, document_id: int) -> list[KnownEntity]:
    from sqlalchemy import text

    rows = conn.execute(
        text(_KNOWN), {"ref": reference_run, "doc": document_id, "limit": MAX_KNOWN}
    )
    return [KnownEntity(r.label, r.type, tuple(r.aliases or ())) for r in rows]


# --- A unit's packet from the run's recorded inputs -------------------------------------------


@dataclass(frozen=True)
class UnitInputs:
    """What the assembler reads for one unit, gathered from the run (`unit_inputs`)."""

    content: RenditionContent
    page: str
    unit_key: str
    unit: tuple[Segment, ...]
    context: tuple[ContextSentence, ...]
    known: tuple[KnownEntity, ...] | None
    macros: Mapping[str, MacroDef] = field(default_factory=dict)
    source_coverage: StandingContextCoverage | None = None

    def packet(self, cap: int | None) -> Packet:
        coverage = self.source_coverage or _CoverageIndex.prepare(self.content, ()).for_unit(
            self.unit_key, self.unit, self.context
        )
        return render(
            self.content,
            self.page,
            self.unit_key,
            self.unit,
            self.context,
            self.known,
            cap,
            source_coverage=coverage,
        )


def unit_inputs(
    reader: Reader,
    *,
    rendition_id: int,
    document_id: int | None,
    unit_key: str,
    reference_run_id: int | None,
    pack_macros: Mapping[str, MacroDef],
    golden: bool = False,
    preparation: dict | None = None,
    coordinate_index: LocatorIndex | None = None,
) -> UnitInputs:
    """A unit's recorded inputs through the run's reader (module doc)."""
    from corpus_structure.core import tex
    from corpus_structure.core.vocab import ObservationKind

    cache_key = (rendition_id, document_id, reference_run_id, golden)
    if preparation is not None and cache_key in preparation:
        content, page, index, macros, views, known, coverage_index = preparation[cache_key]
        unit = (index.resolve(unit_key),)
        context = tuple(context_from_stored(content, page, unit, views))
        return UnitInputs(
            content,
            page,
            unit_key,
            unit,
            context,
            known,
            macros,
            coverage_index.for_unit(unit_key, unit, context),
        )
    content = (
        reader.content(rendition_id) if coordinate_index is None else coordinate_index.rendition
    )
    page = parse_locator(unit_key).page
    index = LocatorIndex(content, page) if coordinate_index is None else coordinate_index
    unit = (index.resolve(unit_key),)
    macros = tex.effective_macros(content.macros, pack_macros)
    from corpus_structure.core.method import StableObservationReading

    mention_rows = list(reader.observations(rendition_id, MENTION_METHOD, ObservationKind.MENTION))
    scope_rows = list(reader.observations(rendition_id, SCOPE_METHOD, ObservationKind.SCOPE))
    if any(isinstance(row, StableObservationReading) for row in (*mention_rows, *scope_rows)):
        views = stored_bound_scopes(content, mention_rows, scope_rows, macros)
    else:
        views = stored_scopes(
            content,
            [row.payload for row in mention_rows],
            [row.payload for row in scope_rows],
            macros,
        )
    context = tuple(context_from_stored(content, page, unit, views))
    coverage_index = _CoverageIndex.prepare(
        content, reader.source_coverage(rendition_id, SCOPE_METHOD)
    )
    known: tuple[KnownEntity, ...] | None
    if golden:
        known = None
    elif reference_run_id is not None and document_id is not None:
        with reader.connection() as conn:
            known = tuple(reference_entities(conn, reference_run_id, document_id))
    else:
        known = tuple(bootstrap_terms(content))
    if preparation is not None:
        preparation[cache_key] = (content, page, index, macros, views, known, coverage_index)
    return UnitInputs(
        content,
        page,
        unit_key,
        unit,
        context,
        known,
        macros,
        coverage_index.for_unit(unit_key, unit, context),
    )
