"""M01 `ingest.html` as a pure function: a document's bytes and a source profile to rendition
content (ingest and math §3.3; D4 M01; D1 §3.1-§3.2).

`build_rendition(raw, profile, sentences, source_uri=…)` returns an `IngestResult`:

- `content`: the `RenditionContent` (canonical text, the segment tree with sentences, the macro
  table), which F2a digests;
- `markup`: `author_markup` drafts (D3 §6.2), each typed by `MarkupKind`, on a segment named by its
  kind and offsets (the rendition's keys are the writer's, P0-I-1b);
- `title`, the page title, and `parse_detail`, the build's diagnostics.

Steps: parse with html5lib (`namespaceHTMLElements=False`, the original bytes, WHATWG sniffing, no
chardet), recording the encoding, parser errors and data-loss warnings; one pass of the profile's
`cssselect2.Matcher` gives every element its roles; the macro source is read by the tokenizer
reader; the body is walked in reading order (blocks `\\n\\n`, list items and rows `\\n`, cells
`\\t`; whitespace collapsed outside math, math verbatim; sections opened by the profile's headings
and nested by rank; text placed directly in a container becomes an orphan paragraph; a non-unit
`div` or `blockquote` is transparent); math is delimited per block; NFC is applied chunk by chunk
between math, markup and run boundaries so every offset stays exact; hints, titles and details
kinds are attached; M03 adds sentences. An element whose text is empty yields no segment (IR-13).

Diagnostics never enter attributes: parser errors, exclusions, anomalies, orphan statistics and
`sourceline` live in `parse_detail`, so the content digest covers whole segments.

Segment attributes hold author markup: `id`, `classes`, a list's `start`, the statement-kind
`hint`, a section's `level`, `heading_tag` and `title`, a math span's `open` and `close`, an orphan
paragraph's `orphan` and `container` (`inline_text_of` for the text of a block that also holds
blocks), and `markup`, the inline markup with canonical-text offsets: `dfn` terms, `link`s with
their `href`, and the rendered insertions a consumer may strip (`ref` markers with what they
render, `quote` spans whose first and last characters are the inserted quotation marks, and
`list_marker`s).
"""

from __future__ import annotations

import itertools
import re
import unicodedata
import warnings
from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from pathlib import PurePosixPath
from typing import Any

import cssselect2
from html5lib.constants import DataLossWarning
from lxml.html import html5parser
from pydantic import JsonValue

from corpus_structure.core.batch import StoredEvidence
from corpus_structure.core.evidence import (
    MacroDef,
    RenditionContent,
    Segment,
    content_digest,
    rendition_key,
    segment_key,
)
from corpus_structure.core.locators import LocatorIndex, page_of
from corpus_structure.core.parse_detail import (
    ExcludedElement,
    MathAnomaly,
    OrphanRun,
    ParseDetail,
    ParserError,
    RoleConflict,
    UnicodeChange,
)
from corpus_structure.core.payloads import AuthorMarkupPayload, SynthesizedClaim
from corpus_structure.core.values import EntityRef
from corpus_structure.core.vocab import (
    SENTENCE_SPLIT,
    DelimitingStatus,
    EvidenceRole,
    ListMarkerStyle,
    MarkupKind,
    QuoteRender,
    ReferenceRender,
    SegmentKind,
    StatementKind,
)
from corpus_structure.ingest import delimit, sentences
from corpus_structure.ingest.macros import MacroFragment, MacroSource, read_macros
from corpus_structure.ingest.profile import (
    EXCLUSIVE_ROLES,
    BlockHint,
    CompiledProfile,
    Rule,
    SourceProfile,
    compile_profile,
)
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.ingest.source_capture import (
    CaptureParser,
    Contribution,
    Projection,
    SourceCapture,
    SourceProduct,
    source_union,
)

K = SegmentKind

# The walk's HTML element mapping (D1 §3.2's Siegrist column); a unit is whatever the profile's
# unit selector matches.
TAG_KIND: dict[str, SegmentKind] = {
    "body": K.DOCUMENT,
    "p": K.PARAGRAPH,
    "pre": K.PARAGRAPH,
    "ol": K.LIST,
    "ul": K.LIST,
    "dl": K.LIST,
    "li": K.LIST_ITEM,
    "dt": K.LIST_ITEM,
    "dd": K.LIST_ITEM,
    "details": K.DETAILS,
    "summary": K.HEADING,
    "table": K.TABLE,
    "tr": K.TABLE_ROW,
    "td": K.TABLE_CELL,
    "th": K.TABLE_CELL,
    "figure": K.FIGURE,
    "figcaption": K.CAPTION,
    **{f"h{n}": K.HEADING for n in range(1, 7)},
}
# Containers whose blocks attach to their parent and whose direct text is an orphan paragraph.
TRANSPARENT = frozenset(
    {
        "html",
        "header",
        "thead",
        "tbody",
        "tfoot",
        "main",
        "section",
        "article",
        "nav",
        "div",
        "blockquote",
    }
)
# Blocks whose own text is their content (D1 §3.1); text in any other block is an orphan paragraph.
TEXT_BLOCKS = frozenset({K.PARAGRAPH, K.LIST_ITEM, K.HEADING, K.TABLE_CELL, K.CAPTION})
LINE_SEPARATED = frozenset({K.LIST, K.LIST_ITEM, K.TABLE})
EXAMPLE_KINDS = frozenset({StatementKind.EXAMPLE, StatementKind.EXERCISE})  # details_kinds' context
_HEADING_TAG = re.compile(r"^h([1-6])$")
_WS = re.compile(r"\s+")


class IngestRefused(ValueError):
    """A document the profile does not apply to (D4 M01: no profile-free fallback)."""


def _collapse(text: str) -> str:
    return _WS.sub(" ", text).strip()


def _classes(el: Any) -> list[str]:
    return str(el.get("class") or "").split()


# --- Results -----------------------------------------------------------------------------------


class SegmentRef(tuple[str, int, int]):
    """A segment by kind and offsets, its identity within a rendition (D1 §10.1 `seg` parts)."""

    __slots__ = ()

    def __new__(cls, kind: SegmentKind | str, start: int, end: int) -> SegmentRef:
        return super().__new__(cls, (SegmentKind(kind).value, start, end))

    @classmethod
    def of(cls, segment: Segment) -> SegmentRef:
        return cls(segment.kind, segment.start, segment.end)

    @property
    def kind(self) -> SegmentKind:
        return SegmentKind(self[0])


@dataclass(frozen=True, slots=True)
class MarkupDraft:
    """One `author_markup` observation before the write: the segment it lies on, its span in the
    canonical text when it has one, and its payload."""

    segment: SegmentRef
    span: tuple[int, int] | None
    payload: AuthorMarkupPayload


@dataclass(frozen=True, slots=True)
class IngestResult:
    content: RenditionContent
    markup: tuple[MarkupDraft, ...]
    title: str | None
    page: str
    parse_detail: ParseDetail
    text_layouts: tuple[sentences.TextLayout, ...] = ()
    parsing_product: SourceProduct | None = None
    macro_sources: tuple[MacroSource, ...] = ()


# --- The walk ----------------------------------------------------------------------------------


@dataclass
class Run:
    """The inline text of a block between its block children, with inline markup events."""

    pieces: list[str] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)  # raw offsets
    size: int = 0

    origins: list[tuple[int, int, Contribution]] = field(default_factory=list)

    def add(self, text: str | None, origins: tuple[Contribution, ...] = ()) -> None:
        if text:
            start = self.size
            self.pieces.append(text)
            self.size += len(text)
            if not origins:
                origins = (Contribution(len(text), (), "unavailable run origin"),)
            for origin in origins:
                self.origins.append((start, start + origin.length, origin))
                start += origin.length
            if start != self.size:
                raise ValueError("source contribution differs from run extent")

    def raw(self) -> str:
        return "".join(self.pieces)


@dataclass
class Block:
    kind: SegmentKind
    tag: str
    attrs: dict[str, Any]
    element: Any
    children: list[Block | Run] = field(default_factory=list)
    section_rank: int | None = None
    summary: bool = False


@dataclass
class Node:
    """A segment under construction, offsets relative to its block until shifted."""

    kind: SegmentKind
    start: int
    end: int
    attrs: dict[str, Any] = field(default_factory=dict)
    status: DelimitingStatus = DelimitingStatus.OK
    reason: str | None = None
    children: list[Node] = field(default_factory=list)
    markup: list[dict[str, Any]] = field(default_factory=list)
    element: Any = None
    summary: bool = False
    projections: list[Projection] = field(default_factory=list)

    def shift(self, d: int) -> None:
        self.start += d
        self.end += d
        self.projections = [p.shifted(d) for p in self.projections]
        for event in self.markup:
            event["start"] += d
            event["end"] += d
        for child in self.children:
            child.shift(d)

    def walk(self, ancestors: tuple[Node, ...] = ()) -> Iterator[tuple[Node, tuple[Node, ...]]]:
        yield self, ancestors
        for child in self.children:
            yield from child.walk((*ancestors, self))


class _Walker:
    def __init__(self, root: Any, compiled: CompiledProfile, capture: SourceCapture) -> None:
        self.capture = capture
        self.profile = compiled.profile
        self.roles: dict[Any, list[Rule]] = {}
        self.role_conflicts: list[RoleConflict] = []
        self.exclusions: list[ExcludedElement] = []
        self.anomalies: list[MathAnomaly] = []
        self.orphans: list[OrphanRun] = []
        self.unicode_changed: list[UnicodeChange] = []
        self.refs_rendered = 0
        for wrapper in cssselect2.ElementWrapper.from_html_root(root).iter_subtree():
            rules = compiled.match(wrapper)
            if not rules:
                continue
            el = wrapper.etree_element
            self.roles[el] = rules
            exclusive = sorted({r.role for r in rules if r.role in EXCLUSIVE_ROLES})
            if len(exclusive) > 1:
                self.role_conflicts.append(
                    RoleConflict(tag=el.tag, classes=tuple(_classes(el)), roles=tuple(exclusive))
                )
        units = [el for el in root.iter() if self.has(el, "unit")]
        self.unit_ordinal: dict[str, int] = {}
        for n, el in enumerate(units, 1):  # the page script keeps the last of duplicate ids
            if el.get("id"):
                self.unit_ordinal[el.get("id")] = n

    def rules(self, el: Any, role: str) -> list[Rule]:
        return [r for r in self.roles.get(el, ()) if r.role == role]

    def has(self, el: Any, role: str) -> bool:
        return any(r.role == role for r in self.roles.get(el, ()))

    def excluded(self, el: Any) -> str | None:
        rules = self.rules(el, "exclude")
        if not rules:
            return None
        text = _collapse("".join(el.itertext()))
        self.exclusions.append(
            ExcludedElement(
                rule=rules[0].name, tag=el.tag, classes=tuple(_classes(el)), chars=len(text)
            )
        )
        self.capture.exclude(el, f"source-profile exclusion: {rules[0].name}")
        return rules[0].name

    def text(self, run: Run, element: Any, slot: str) -> None:
        run.add(getattr(element, slot), self.capture.slot(element, slot))

    @staticmethod
    def synthetic(run: Run, text: str, reason: str) -> None:
        run.add(text, (Contribution(len(text), (), reason, synthetic=True),))

    def is_block(self, el: Any) -> bool:
        return el.tag in TAG_KIND or el.tag in TRANSPARENT or self.has(el, "unit")

    def transparent(self, el: Any) -> bool:
        return el.tag in TRANSPARENT and not self.has(el, "unit")

    def attrs(self, el: Any) -> dict[str, Any]:
        a: dict[str, Any] = {}
        if el.get("id"):
            a["id"] = el.get("id")
        if _classes(el):
            a["classes"] = _classes(el)
        hints = self.rules(el, "block_hint")
        if hints:
            a["hint"] = _hint_attr(hints[-1].data)
        if el.tag == "ol" and el.get("start"):
            a["start"] = el.get("start")
        return a

    # inline content ---------------------------------------------------------------------------

    def inline(self, el: Any, run: Run) -> None:
        if self.excluded(el):
            return
        start = run.size
        render = self.profile.render
        references = self.rules(el, "reference")
        if references and not "".join(el.itertext()).strip():
            href = el.get("href") or ""
            target = href[href.find("#") + 1 :] if "#" in href else ""
            ordinal = self.unit_ordinal.get(target)
            text = {
                ReferenceRender.BROWSER: f"[{ordinal}]" if ordinal is not None else "",
                ReferenceRender.PLACEHOLDER: "[ref]",
                ReferenceRender.EMPTY: "",
            }[references[-1].data]
            self.refs_rendered += 1
            self.synthetic(run, text, "source-profile reference marker")
            run.events.append(
                {"markup": "ref", "start": start, "end": run.size, "href": href, "rendered": text}
            )
            return
        quotes = el.tag == "q" and render.q is QuoteRender.QUOTES
        if quotes:
            self.synthetic(run, "“", "source-profile opening quotation mark")
        if el.tag == "br":
            self.synthetic(run, " ", "HTML br separator")
        self.text(run, el, "text")
        for child in el:
            if isinstance(child.tag, str):
                self.inline(child, run)
            self.text(run, child, "tail")
        if quotes:
            self.synthetic(run, "”", "source-profile closing quotation mark")
            run.events.append({"markup": "quote", "start": start, "end": run.size})
        if el.tag == "dfn":
            run.events.append({"markup": "dfn", "start": start, "end": run.size})
        elif el.tag == "a" and el.get("href") is not None:
            run.events.append(
                {"markup": "link", "start": start, "end": run.size, "href": el.get("href")}
            )

    # block content ----------------------------------------------------------------------------

    def build(self, el: Any) -> Block:
        kind = K.UNIT if self.has(el, "unit") else TAG_KIND.get(el.tag, K.PARAGRAPH)
        blk = Block(kind, el.tag, self.attrs(el), el, summary=el.tag == "summary")
        sections = self.rules(el, "section")
        if kind is K.HEADING and sections and "".join(el.itertext()).strip():
            blk.section_rank = min(r.data for r in sections)  # an empty heading opens nothing
        run = Run()
        marker = self.list_marker(el) if el.tag == "li" else ""
        if marker:
            self.synthetic(run, marker, "source-profile list marker")
            run.events.append({"markup": "list_marker", "start": 0, "end": len(marker)})
        self.text(run, el, "text")

        def flush() -> None:
            nonlocal run
            if run.raw().strip():
                blk.children.append(run)
            elif run.pieces:
                self.capture.exclusions.append(
                    (
                        source_union(origin for _, _, origin in run.origins),
                        "canonical whitespace-only run",
                    )
                )
            run = Run()

        for child in el:
            if not isinstance(child.tag, str):  # a comment: skipped, its tail kept
                self.text(run, child, "tail")
                continue
            if self.excluded(child):
                self.text(run, child, "tail")
                continue
            if self.transparent(child):
                flush()
                blk.children.extend(self.build(child).children)
            elif self.is_block(child):
                flush()
                blk.children.append(self.build(child))
            else:
                self.inline(child, run)
            self.text(run, child, "tail")
        flush()
        if kind is K.DOCUMENT:
            blk.children = self.sectionize(blk.children)
        return blk

    def list_marker(self, li: Any) -> str:
        parent = li.getparent()
        rules = self.rules(parent, "list_marker") if parent is not None else []
        if (
            parent is None
            or parent.tag != "ol"
            or not rules
            or rules[-1].data is ListMarkerStyle.NONE
        ):
            return ""
        try:
            first = int(parent.get("start") or 1)
        except ValueError:
            first = 1
        items = [c for c in parent if isinstance(c.tag, str) and c.tag == "li"]
        letter = chr(ord("a") + first - 1 + items.index(li))
        parenthesized = rules[-1].data is ListMarkerStyle.PARENTHESIZED
        return f"({letter}) " if parenthesized else f"{letter}. "

    def sectionize(self, children: list[Block | Run]) -> list[Block | Run]:
        top: list[Block | Run] = []
        stack: list[tuple[int, Block]] = []
        for child in children:
            if not isinstance(child, Block) or child.section_rank is None:
                (stack[-1][1].children if stack else top).append(child)
                continue
            rank = child.section_rank
            while stack and stack[-1][0] >= rank:
                stack.pop()
            tag = _HEADING_TAG.match(child.tag)
            level = int(tag.group(1)) if tag else rank + 1
            section = Block(
                K.SECTION,
                "section",
                {"level": level, "heading_tag": child.tag},
                child.element,
                [child],
            )
            (stack[-1][1].children if stack else top).append(section)
            stack.append((rank, section))
        return top


def _hint_attr(hint: BlockHint) -> dict[str, JsonValue]:
    out: dict[str, JsonValue] = {
        "selector": hint.selector,
        "statement_kind": str(hint.statement_kind),
    }
    if hint.claim_bearing is not None:
        out["claim_bearing"] = hint.claim_bearing
    return out


# --- Runs and serialization --------------------------------------------------------------------


def _process_run(
    run: Run, walker: _Walker
) -> tuple[str, list[Node], list[dict[str, Any]], str | None, list[Projection]]:
    """A run's canonical text, its math segments, its markup (offsets in the text) and, when the
    delimiter scan timed out, the reason its block is partial."""
    raw = run.raw()
    scan = delimit.scan(raw, walker.profile.math, timeout=delimit.SCAN_TIMEOUT)
    for stray in scan.strays:
        context = raw[max(0, stray.position - 40) : stray.position + 40]
        walker.anomalies.append(
            MathAnomaly(kind="stray closer", delimiter=stray.delimiter, context=context)
        )
    in_math = [False] * len(raw)
    for span in scan.spans:
        for k in range(span.start, span.end):
            in_math[k] = True
    out: list[str] = []
    pos = [0] * (len(raw) + 1)
    for k, ch in enumerate(raw):
        pos[k] = len(out)
        if ch.isspace() and not in_math[k]:
            if out and out[-1] != " ":
                out.append(" ")
        else:
            out.append(ch)
    pos[len(raw)] = len(out)
    while out and out[-1] == " ":
        out.pop()
    length = len(out)
    text = "".join(out)

    def clamp(p: int) -> int:
        return min(p, length)

    # NFC chunk by chunk between boundaries, so boundary offsets stay exact.
    bounds = {0, length}
    for span in scan.spans:
        bounds |= {clamp(pos[span.start]), clamp(pos[span.end])}
    for event in run.events:
        bounds |= {clamp(pos[event["start"]]), clamp(pos[event["end"]])}
    for start, end, origin in run.origins:
        if origin.synthetic:
            bounds |= {clamp(pos[start]), clamp(pos[end])}
    ordered = sorted(bounds)
    newmap: dict[int, int] = {}
    pieces: list[str] = []
    projections: list[Projection] = []
    acc = 0
    origin_index = 0
    math_index = 0
    math_ranges = [(clamp(pos[span.start]), clamp(pos[span.end])) for span in scan.spans]
    for a, b in itertools.pairwise(ordered):
        newmap[a] = acc
        chunk = text[a:b]
        normalized = unicodedata.normalize("NFC", chunk)
        if normalized != chunk:
            walker.unicode_changed.append(UnicodeChange(before=chunk[:80], after=normalized[:80]))
        pieces.append(normalized)
        while origin_index < len(run.origins) and clamp(pos[run.origins[origin_index][1]]) <= a:
            origin_index += 1
        origins = []
        candidate = origin_index
        while candidate < len(run.origins) and clamp(pos[run.origins[candidate][0]]) < b:
            start, end, origin = run.origins[candidate]
            if clamp(pos[end]) > a:
                origins.append(origin)
            candidate += 1
        while math_index < len(math_ranges) and math_ranges[math_index][1] <= a:
            math_index += 1
        if normalized:
            synthetic = bool(origins) and all(origin.synthetic for origin in origins)
            category = (
                "marker"
                if synthetic
                else "math"
                if math_index < len(math_ranges)
                and math_ranges[math_index][0] <= a < b <= math_ranges[math_index][1]
                else "text"
            )
            known = bool(origins) and all(origin.sources or origin.synthetic for origin in origins)
            reasons = [origin.reason for origin in origins]
            if not synthetic:
                reasons.append("whitespace collapse and NFC canonical projection")
            projections.append(
                Projection(
                    acc,
                    acc + len(normalized),
                    source_union(origins),
                    category,
                    "; ".join(dict.fromkeys(reasons)),
                    synthetic,
                    known,
                )
            )
        acc += len(normalized)
    newmap[length] = acc
    text = "".join(pieces)

    def mapped(p: int) -> int:
        return newmap[clamp(pos[p])]

    math = [
        Node(
            K.MATH_DISPLAY if span.display else K.MATH_INLINE,
            mapped(span.start),
            mapped(span.end),
            {"open": span.open, "close": span.close},
            span.status,
            span.reason,
        )
        for span in scan.spans
    ]
    markup = [
        {**event, "start": mapped(event["start"]), "end": mapped(event["end"])}
        for event in run.events
    ]
    return text, math, markup, delimit.TIMEOUT_REASON if scan.timed_out else None, projections


def _separator(kind: SegmentKind) -> str:
    if kind in LINE_SEPARATED:
        return "\n"
    if kind is K.TABLE_ROW:
        return "\t"
    return "\n\n"


def _serialize(blk: Block, walker: _Walker) -> tuple[str, Node]:
    parts: list[str] = []
    node = Node(blk.kind, 0, 0, dict(blk.attrs), element=blk.element, summary=blk.summary)
    offset = 0
    sep = _separator(blk.kind)
    has_blocks = any(isinstance(c, Block) for c in blk.children)
    for child in blk.children:
        own: Node | None
        if isinstance(child, Run):
            text, math, markup, timeout, projections = _process_run(child, walker)
            if not text:
                continue
            if blk.kind in TEXT_BLOCKS and not has_blocks:
                placed, own = math, None
                node.markup += [_shifted(m, offset) for m in markup]
                if timeout:
                    node.status, node.reason = DelimitingStatus.PARTIAL, timeout
            else:
                attrs: dict[str, Any] = (
                    {"inline_text_of": blk.kind.value}
                    if blk.kind in TEXT_BLOCKS
                    else {"orphan": True, "container": blk.kind.value}
                )
                kind = K.PARAGRAPH if blk.kind in TEXT_BLOCKS else walker.profile.orphan_text
                own = Node(kind, 0, len(text), attrs, children=math, markup=markup)
                if timeout:
                    own.status, own.reason = DelimitingStatus.PARTIAL, timeout
                if blk.kind not in TEXT_BLOCKS:
                    line = blk.element.sourceline if blk.element is not None else None
                    walker.orphans.append(
                        OrphanRun(
                            container=blk.kind,
                            text=text[:80],
                            **({} if line is None else {"sourceline": line}),
                        )
                    )
                placed = [own]
        else:
            text, own = _serialize(child, walker)
            projections = own.projections
            if not text:
                continue
            placed = [own]
        if parts:
            parts.append(sep)
            node.projections.append(
                Projection(
                    offset,
                    offset + len(sep),
                    (),
                    "canonical_separator",
                    f"{blk.kind.value} canonical separator",
                    True,
                )
            )
            offset += len(sep)
        node.projections.extend(p.shifted(offset) for p in projections)
        for segment in placed:
            segment.shift(offset)
            node.children.append(segment)
        parts.append(text)
        offset += len(text)
    text = "".join(parts)
    node.end = len(text)
    return text, node


def _shifted(event: dict[str, Any], d: int) -> dict[str, Any]:
    return {**event, "start": event["start"] + d, "end": event["end"] + d}


# --- After the walk: titles, hints, details ----------------------------------------------------


def _titles(root: Node, text: str) -> None:
    for node, _ in root.walk():
        if node.kind is K.SECTION:
            heading = next((c for c in node.children if c.kind is K.HEADING), None)
            node.attrs["title"] = text[heading.start : heading.end] if heading else None


def _hints(root: Node, profile: SourceProfile) -> None:
    """A unit takes the hint of its first hinted block; the hint of the innermost section whose
    title the profile names takes precedence and keeps the block hint beside it."""
    by_title = {h.title: h.statement_kind for h in profile.section_hints}
    for node, ancestors in root.walk():
        if node.kind is not K.UNIT:
            continue
        block = next((c.attrs["hint"] for c in node.children if "hint" in c.attrs), None)
        if block is not None:
            node.attrs["hint"] = block
        section = next(
            (
                a
                for a in reversed(ancestors)
                if a.kind is K.SECTION and a.attrs.get("title") in by_title
            ),
            None,
        )
        if section is not None:
            title = section.attrs["title"]
            hint: dict[str, Any] = {
                "selector": f"section:{title}",
                "statement_kind": str(by_title[title]),
            }
            if block is not None:
                hint["block_hint"] = block
            node.attrs["hint"] = hint


def _hint_kind(node: Node) -> str | None:
    hint = node.attrs.get("hint")
    return hint.get("statement_kind") if isinstance(hint, dict) else None


# --- Segments ----------------------------------------------------------------------------------


def _leaf_blocks(root: Node) -> list[Node]:
    return [
        node
        for node, _ in root.walk()
        if node.kind in SENTENCE_SPLIT and not any(c.kind in SENTENCE_SPLIT for c in node.children)
    ]


def _add_sentences(
    root: Node, text: str, config: SentenceConfig
) -> tuple[sentences.TextLayout, ...]:
    leaves = _leaf_blocks(root)
    blocks = [
        sentences.block_of(
            text,
            node.start,
            node.end,
            ((c.kind, c.start, c.end) for c in node.children),
            node.markup,
        )
        for node in leaves
    ]
    from corpus_structure.semantic.analysis_contracts import prepare_text_policy

    policy = prepare_text_policy()
    nlp = sentences.pipeline(config)
    layouts = tuple(
        sentences.prepare_layout(nlp, block, start=node.start, recipe=policy.recipe)
        for node, block in zip(leaves, blocks, strict=True)
    )
    for node, extents in zip(leaves, sentences.split(blocks, config, layouts=layouts), strict=True):
        node.children += [Node(K.SENTENCE, node.start + a, node.start + b) for a, b in extents]
    return layouts


def _segment(node: Node) -> Segment:
    attrs = dict(node.attrs)
    if node.markup:
        attrs["markup"] = sorted(node.markup, key=lambda m: (m["start"], -m["end"], m["markup"]))
    return Segment(
        kind=node.kind,
        start=node.start,
        end=node.end,
        parse_status=node.status,
        parse_reason=node.reason,
        attrs=attrs,
        children=tuple(_segment(c) for c in node.children),
    )


# --- Author markup drafts ----------------------------------------------------------------------


def _markup_drafts(
    root: Node,
    content: RenditionContent,
    profile: SourceProfile,
    page: str,
    notes: list[str],
    document_key: str | None = None,
) -> list[MarkupDraft]:
    """The `author_markup` drafts. With the document's key, each value names its segment by key
    (`segment`) and a synthesized claim's enclosing unit by key beside its locator."""
    drafts: list[MarkupDraft] = []
    text = content.canonical_text
    index: LocatorIndex | None = None
    segments = {SegmentRef.of(s): s for s in content.document.walk()}
    ren_key = rendition_key(document_key, content_digest(content)) if document_key else None

    def key_of(node: Node) -> str | None:
        return segment_key(ren_key, node.kind, node.start, node.end) if ren_key else None

    def draft(
        node: Node,
        markup: MarkupKind,
        value: dict[str, JsonValue],
        span: tuple[int, int] | None = None,
        **extra: Any,
    ) -> None:
        key = key_of(node)
        if key is not None:
            value = {**value, "segment": key}
        payload = AuthorMarkupPayload(markup=markup, value=value, **extra)
        drafts.append(MarkupDraft(SegmentRef(node.kind, node.start, node.end), span, payload))

    for node, ancestors in root.walk():
        ids = {k: node.attrs[k] for k in ("id", "classes") if k in node.attrs}
        if node.kind is K.UNIT:
            draft(node, MarkupKind.UNIT, ids)
        elif "classes" in node.attrs:
            draft(node, MarkupKind.CLASS, {"classes": node.attrs["classes"]})
        for event in node.markup:
            span = (event["start"], event["end"]) if event["end"] > event["start"] else None
            if event["markup"] == "dfn":
                term = text[event["start"] : event["end"]]
                draft(
                    node,
                    MarkupKind.DFN,
                    {"term": term, "start": event["start"], "end": event["end"]},
                    span,
                )
            elif event["markup"] in ("link", "ref"):
                value: dict[str, JsonValue] = {
                    "text": text[event["start"] : event["end"]],
                    "start": event["start"],
                    "end": event["end"],
                }
                if event["markup"] == "ref":
                    value["rendered"] = True
                draft(node, MarkupKind.LINK, value, span, target=event["href"])
        if node.kind is not K.DETAILS:
            continue
        summary = next((c for c in node.children if c.summary), None)
        summary_text = text[summary.start : summary.end] if summary else None
        unit = next((a for a in reversed(ancestors) if a.kind is K.UNIT), None)
        kind = profile.details_kinds.kind_of(
            summary_text, unit is not None and _hint_kind(unit) in EXAMPLE_KINDS
        )
        details: dict[str, JsonValue] = {"statement_kind": str(kind), "summary": summary_text}
        rule = profile.details_kinds.rule_for(kind)
        extra: dict[str, Any] = {}
        if rule is not None and (unit is None or summary is None):
            notes.append(
                f"details at {node.start}: {kind} declares synthesize, but the block has "
                f"no {'enclosing unit' if unit is None else 'summary'}"
            )
        elif rule is not None and unit is not None and summary is not None:
            if index is None:
                index = LocatorIndex(content, page)
            unit_key = index.unit_key(segments[SegmentRef(unit.kind, unit.start, unit.end)])
            enclosing: dict[str, JsonValue] = {"locator": unit_key}
            unit_segment = key_of(unit)
            if unit_segment is not None:
                enclosing["segment"] = unit_segment
            details["unit"] = enclosing
            extra["synthesize"] = SynthesizedClaim(
                predicate=rule.predicate,
                object=EntityRef(ref=unit_key),
                evidence=(
                    StoredEvidence(start=summary.start, end=summary.end, role=EvidenceRole.PRIMARY),
                ),
            )
        draft(node, MarkupKind.DETAILS, details, **extra)
    return drafts


# --- The function ------------------------------------------------------------------------------


def _parse_with_capture(raw: bytes) -> tuple[Any, ParseDetail, SourceCapture]:
    """Native html5lib tree, diagnostics and operation-owned source capture."""
    parser = CaptureParser()  # stateful: one per document
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DataLossWarning)
        root = html5parser.document_fromstring(raw, guess_charset=False, parser=parser)
    detail = ParseDetail(
        encoding=parser.documentEncoding,
        parser_errors=tuple(
            ParserError(line=line, column=column, code=code)
            for (line, column), code, _ in parser.errors
        ),
        data_loss_warnings=sum(1 for w in caught if issubclass(w.category, DataLossWarning)),
    )
    return root, detail, SourceCapture(raw, parser)


def parse(raw: bytes) -> tuple[Any, ParseDetail]:
    root, detail, _ = _parse_with_capture(raw)
    return root, detail


def _macro_fragments(el: Any, walker: _Walker) -> tuple[str, tuple[MacroFragment, ...]]:
    pieces: list[str] = []
    fragments: list[MacroFragment] = []
    position = 0

    def slot(node: Any, name: str) -> None:
        nonlocal position
        value = getattr(node, name) or ""
        pieces.append(value)
        for contribution in walker.capture.slot(node, name):
            fragments.append(
                MacroFragment(
                    position,
                    position + contribution.length,
                    tuple((s.start, s.end) for s in contribution.sources),
                    contribution.reason,
                )
            )
            position += contribution.length

    def collect(node: Any) -> None:
        if isinstance(node.tag, str):
            slot(node, "text")
        for child in node:
            collect(child)
            slot(child, "tail")

    collect(el)
    return "".join(pieces), tuple(fragments)


def _macro_table(
    root: Any, walker: _Walker
) -> tuple[dict[str, MacroDef], list[str], tuple[MacroSource, ...]]:
    table: dict[str, MacroDef] = {}
    notes: list[str] = []
    sources: list[MacroSource] = []
    for el in root.iter():
        if not isinstance(el.tag, str) or not walker.has(el, "macros"):
            continue
        macro_text, fragments = _macro_fragments(el, walker)
        source = "page-macros:" + str(len(sources))
        read = read_macros(macro_text, source_ref=source)
        for name, definition in read.table.items():
            if name in table:
                if table[name] != definition:
                    notes.append(f"{name} defined again by a later macro block; the later is kept")
                for index, prior in enumerate(sources):
                    events = tuple(
                        replace(event, status="replaced")
                        if event.name == name and event.status == "accepted"
                        else event
                        for event in prior.read.events
                    )
                    sources[index] = replace(prior, read=replace(prior.read, events=events))
            table[name] = definition
        notes.extend(read.notes)
        sources.append(MacroSource(source, "".join(pieces), read, tuple(fragments)))
    return table, notes, tuple(sources)


def build_rendition_with_elements(
    raw: bytes,
    profile: SourceProfile | CompiledProfile,
    sentence_config: SentenceConfig,
    *,
    source_uri: str,
    document_key: str | None = None,
) -> tuple[IngestResult, dict[SegmentRef, Any]]:
    """`build_rendition`, and the source element of each segment built from one (for the
    independent text path of the corpus checks; the elements are not part of the result)."""
    compiled = profile if isinstance(profile, CompiledProfile) else compile_profile(profile)
    prof = compiled.profile
    if not PurePosixPath(source_uri).full_match(prof.applies_to):
        raise IngestRefused(
            f"{source_uri!r} is not matched by the profile's applies_to {prof.applies_to!r}"
        )
    page = page_of(source_uri, prof.root)
    root, detail, capture = _parse_with_capture(raw)
    walker = _Walker(root, compiled, capture)
    macros, macro_notes, macro_sources = _macro_table(root, walker)
    head = root.find("head")
    if head is not None:
        capture.exclude(head, "canonical reading-body selection")
    body = root.find("body")
    tree = walker.build(body)
    text, top = _serialize(tree, walker)
    _titles(top, text)
    _hints(top, prof)
    text_layouts = _add_sentences(top, text, sentence_config)
    content = RenditionContent(canonical_text=text, document=_segment(top), macros=macros)
    synth_notes: list[str] = []
    drafts = _markup_drafts(top, content, prof, page, synth_notes, document_key)
    titles = [el for el in root.iter() if isinstance(el.tag, str) and walker.has(el, "title")]
    detail = ParseDetail(
        encoding=detail.encoding,
        parser_errors=detail.parser_errors,
        data_loss_warnings=detail.data_loss_warnings,
        role_conflicts=tuple(walker.role_conflicts),
        exclusions=tuple(walker.exclusions),
        math_anomalies=tuple(walker.anomalies),
        orphans=tuple(walker.orphans),
        unicode_changed=tuple(walker.unicode_changed),
        references_rendered=walker.refs_rendered,
        macro_notes=tuple(macro_notes),
        synthesize_notes=tuple(synth_notes),
    )
    result = IngestResult(
        content=content,
        markup=tuple(drafts),
        title=_collapse("".join(titles[0].itertext())) if titles else None,
        page=page,
        parse_detail=detail,
        text_layouts=text_layouts,
        parsing_product=capture.finish(text, tuple(top.projections)),
        macro_sources=macro_sources,
    )
    elements = {
        SegmentRef(n.kind, n.start, n.end): n.element
        for n, _ in top.walk()
        if n.element is not None
    }
    return result, elements


def build_rendition(
    raw: bytes,
    profile: SourceProfile | CompiledProfile,
    sentence_config: SentenceConfig,
    *,
    source_uri: str,
    document_key: str | None = None,
) -> IngestResult:
    """M01 with M03 on one document's original bytes (pure: no database, no clock). Given the
    document's key (`doc:`, which names the project), the markup drafts name their segments by
    key on this rendition (D1 §10.1)."""
    return build_rendition_with_elements(
        raw, profile, sentence_config, source_uri=source_uri, document_key=document_key
    )[0]
