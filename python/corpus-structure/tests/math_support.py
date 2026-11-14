"""Shared fixtures of the math tests (ingest and math §6, P0-I-2a).

Pages are retained historical typed rendition inputs, read by the mathematical kernels.
The retired HTML writer is not part of current fixture setup. The four
spike pages are vendored under `fixtures/trace/corpus/` (P0-F-3), so their checks never skip; the
three S0-R2 pages and the 78-page run read the gitignored corpus and are `corpus`-marked.

Math stages run in spawned single-threaded worker processes, one page per task: the grammar's
deadline runs only on a process's main thread, and a page's spans take tens of seconds of CPU.

The pack constants below retain the independent historical oracle configuration; they are not
synchronized with current methods.yaml. Mathematical/TeX meaning is adjudicated under D1 §6.2
and the cited source, not by regenerating production output. A changed expectation selects a new
reference with its source, rationale and affected consumers, preserving the frozen witness.
"""

from __future__ import annotations

import json
import multiprocessing
import os
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from concurrent.futures import FIRST_COMPLETED, Future, ProcessPoolExecutor, wait
from dataclasses import dataclass
from functools import lru_cache, partial
from pathlib import Path
from typing import overload

from math_worker_transport import configure_worker_transport

from corpus_structure.core import tex
from corpus_structure.core.evidence import MacroDef, RenditionContent, Segment
from corpus_structure.methods.math.scope import Binders, Scope, resolve_scopes
from corpus_structure.methods.math.spans import (
    MathExtraction,
    SpanReading,
    SpanValue,
    extract,
    formula_values,
)

from corpus_structure.core.vocab import SegmentKind
from corpus_structure.methods.math.grammar import PARSE_SECONDS
from corpus_structure.methods.math.spans import MATH_KINDS, MathSpan

_ENVIRONMENT_OPENER = "\\begin"


def _inner(text: str, segment: Segment) -> tuple[int, int]:
    opener, closer = segment.attrs.get("open"), segment.attrs.get("close")
    a, b = 0, len(text)
    if (
        isinstance(opener, str)
        and isinstance(closer, str)
        and not opener.startswith(_ENVIRONMENT_OPENER)
        and text.startswith(opener)
        and text.endswith(closer)
        and len(text) >= len(opener) + len(closer)
    ):  # a pair, as the token form strips one; an unclosed span is read with its opener
        a, b = len(opener), len(text) - len(closer)
    while a < b and text[a].isspace():
        a += 1
    while b > a and text[b - 1].isspace():
        b -= 1
    return a, b


def math_spans(content: RenditionContent) -> list[MathSpan]:
    """Every math span of the rendition, in page order, with its parse input."""
    out = []
    for segment in content.document.walk():
        if segment.kind in MATH_KINDS:
            text = content.text(segment)
            a, b = _inner(text, segment)
            out.append(MathSpan(segment, text[a:b], segment.start + a))
    return sorted(out, key=lambda s: (s.segment.start, s.segment.end))


def read_spans(
    content: RenditionContent,
    macros: Mapping[str, MacroDef],
    constants: Sequence[str] = (),
    *,
    seconds: float = PARSE_SECONDS,
    prepared_context=None,
) -> list[SpanReading]:
    """Parse every math span under `any_value`; `macros` is the effective table
    (`core/tex.py` `effective_macros`), `constants` the pack's `math.constants`."""
    from corpus_structure.semantic.analysis_contracts import prepare_interpretation_context

    prepared_context = prepared_context or prepare_interpretation_context(
        macros=macros, constants=constants, demand="occurrences"
    )
    from corpus_structure.methods.math.prepared import PreparedMathInput

    readings = []
    for span in math_spans(content):
        prepared = PreparedMathInput(
            prepared_context,
            span.latex,
            "any_value",
            seconds,
            source_text=content.text(span.segment),
            source_start=span.segment.start,
            parse_start=span.offset,
        )
        result = prepared.symbolic_reading()
        prepared.context.validate_result(
            produced=("lexical", "syntax", "occurrences", "interpretation", "symbolic"),
            interpretation=result.status.value,
            completeness="failed" if result.failure else "complete",
        )
        readings.append(SpanReading(span, result, prepared))
    return readings


REPO = Path(__file__).resolve().parents[3]
VENDORED = REPO / "fixtures/trace/corpus"
CORPUS = REPO / "docs/statistics_corpus/corpus"
INDEX = REPO / "docs/statistics_corpus/index/siegrist_sections.tsv"
ROOT = "siegrist_random/random"
DATA = Path(__file__).with_name("math") / "data"

SPIKE_PAGES = (
    "special/LocationScale.html",
    "special/Normal.html",
    "special/LogNormal.html",
    "special/Gamma.html",
)
S0R2_PAGES = ("special/Pareto.html", "special/ChiSquare.html", "special/Weibull.html")

PACK_MACROS: dict[str, MacroDef] = {
    name: MacroDef(body=body)
    for name, body in {
        "\\R": "\\mathbb{R}",
        "\\N": "\\mathbb{N}",
        "\\Z": "\\mathbb{Z}",
        "\\Q": "\\mathbb{Q}",
        "\\P": "\\mathbb{P}",
        "\\E": "\\mathbb{E}",
        "\\var": "\\text{var}",
        "\\sd": "\\text{sd}",
        "\\cov": "\\text{cov}",
        "\\cor": "\\text{cor}",
        "\\skw": "\\text{skew}",
        "\\kur": "\\text{kurt}",
        "\\mse": "\\text{mse}",
        "\\sgn": "\\text{sgn}",
        "\\bs": "\\boldsymbol",
        "\\ms": "\\mathscr",
    }.items()
}
CONSTANTS = ("e", "\\pi")
BINDERS = Binders(
    sentence_initial=("suppose", "let", "assume", "fix", "define", "consider", "recall", "if"),
    clause=("where", "for"),
    reopen=("again",),
    section_wide=("in this section", "throughout this section"),
)


@dataclass(frozen=True)
class PageContent:
    page: str
    content: RenditionContent
    macros: dict[str, MacroDef]


@dataclass(frozen=True)
class PageReadings(PageContent):
    readings: list[SpanReading]


@dataclass(frozen=True)
class PageExtraction(PageReadings):
    values: list[SpanValue]
    extraction: MathExtraction


@dataclass(frozen=True)
class PageMath(PageExtraction):
    scopes: list[Scope]


@lru_cache(maxsize=1)
def _retained_inputs() -> dict:
    fixture = REPO / "fixtures/trace/archived-renditions.json"
    retained = json.loads(fixture.read_bytes())
    if retained["source_revision"] != "7e6289a":
        raise ValueError("historical mathematical inputs require their retained source revision")
    return retained["pages"]


def corpus_of(page: str) -> Path:
    return VENDORED if (VENDORED / ROOT / page).exists() else CORPUS


def load_page(page: str) -> PageContent:
    """Load validated retained content and frozen effective macros, without parsing."""
    if page not in _retained_inputs():
        raise ValueError("no retained historical mathematical input for " + page)
    content = RenditionContent.model_validate(_retained_inputs()[page]["content"])
    macros = tex.effective_macros(content.macros, PACK_MACROS)
    return PageContent(page, content, macros)


def read_content(page: PageContent, *, seconds: float | None = None) -> list[SpanReading]:
    """Worker stage: transport finished readings, never process-owned preparation."""
    if seconds is None:
        return read_spans(page.content, page.macros, CONSTANTS)
    return read_spans(page.content, page.macros, CONSTANTS, seconds=seconds)


def extract_readings(readings: list[SpanReading]) -> tuple[list[SpanValue], MathExtraction]:
    """Worker stage: use finished readings without parsing again or resolving scopes."""
    return formula_values(readings), extract(readings)


def segment_block(content, segment):
    from corpus_structure.ingest.sentences import block_of

    markup = segment.attrs.get("markup")
    return block_of(
        content.canonical_text,
        segment.start,
        segment.end,
        ((c.kind, c.start, c.end) for c in segment.children),
        [m for m in markup if isinstance(m, dict)] if isinstance(markup, list) else [],
    )


def primary_scope_fixture(content, binders):
    """Prepare primary cues over frozen historical token and sentence fixtures."""
    from spacy.lang.en import English
    from spacy.tokens import Doc

    from corpus_structure.core.vocab import SegmentKind
    from corpus_structure.ingest.sentences import make_doc
    from corpus_structure.semantic.constructions.math_scope import (
        MathScopeReadings,
        PreparedScopeCues,
    )

    nlp = English()
    prepared = PreparedScopeCues(nlp.vocab, binders)
    sentences, cues = [], []
    for block in content.document.walk():
        stored = [s for s in block.children if s.kind is SegmentKind.SENTENCE]
        if not stored:
            continue
        native = make_doc(nlp, segment_block(content, block))
        starts = {s.start - block.start for s in stored}
        doc = Doc(
            nlp.vocab,
            words=[t.text for t in native],
            spaces=[bool(t.whitespace_) for t in native],
            sent_starts=[i == 0 or t.idx in starts for i, t in enumerate(native)],
        )
        atoms = {s.start for s in block.children if s.kind is SegmentKind.MATH_INLINE}
        for token in doc:
            token._.primary_math_atom = block.start + token.idx in atoms
        sentences.extend((s.start, s.end) for s in stored)
        for kind, a, b in prepared.match(doc):
            at = block.start + doc[a].idx
            sentence = next(s for s in stored if s.start <= at < s.end)
            target = (
                (block.start + doc[b - 1].idx, block.start + doc[b - 1].idx + len(doc[b - 1]))
                if kind == "clause"
                else None
            )
            cues.append((kind, (sentence.start, sentence.end), target))
    return MathScopeReadings(tuple(sentences), tuple(cues), (), True)


def scope_extraction(
    inputs: tuple[PageContent, list[SpanValue], MathExtraction],
) -> list[Scope]:
    """Worker stage: only content, macros and extracted results cross this boundary."""
    page, values, extraction = inputs
    return resolve_scopes(
        page.content,
        values,
        extraction.mentions,
        extraction.relations,
        page.macros,
        primary_scope=primary_scope_fixture(page.content, BINDERS),
    )


def read_page(page: str, *, seconds: float | None = None) -> PageReadings:
    """Direct reading path, also used by the narrow coverage worker."""
    retained = load_page(page)
    readings = (
        read_content(retained) if seconds is None else read_content(retained, seconds=seconds)
    )
    return PageReadings(page, retained.content, retained.macros, readings)


def analyse(page: str, scopes: bool = True) -> PageMath:
    """Direct whole-page job: the same stages under one submission deadline."""
    parsed = read_page(page)
    values, extraction = extract_readings(parsed.readings)
    found = scope_extraction((parsed, values, extraction)) if scopes else []
    return PageMath(page, parsed.content, parsed.macros, parsed.readings, values, extraction, found)


class PageWorkError(RuntimeError):
    """The page oracle is incomplete; no missing page has an invented result."""


@overload
def _run_pages[Payload, Result](
    work: Callable[[Payload], Result],
    pages: Mapping[str, Payload],
    *,
    timeout: float = 300,
    workers: int | None = None,
) -> dict[str, Result]: ...


@overload
def _run_pages[Result](
    work: Callable[[str], Result],
    pages: Iterable[str],
    *,
    timeout: float = 300,
    workers: int | None = None,
) -> dict[str, Result]: ...


def _run_pages[Result](
    work: Callable[..., Result],
    pages: Mapping[str, object] | Iterable[str],
    *,
    timeout: float = 300,
    workers: int | None = None,
) -> dict[str, Result]:
    """Bound outstanding page jobs and kill the complete pool on any failure.

    The deadline starts at submission, including spawn/startup time. Never use the
    executor context manager here: its normal shutdown would wait for a stuck job.
    """
    payloads = pages if isinstance(pages, Mapping) else None
    pages = tuple(pages)
    if timeout <= 0 or (workers is not None and workers <= 0):
        raise ValueError("page timeout and worker count must be positive")
    if len(set(pages)) != len(pages):
        raise ValueError("page work requires distinct page identities")
    if not pages:
        return {}
    count = min(8, len(pages), workers or os.process_cpu_count() or 1)
    configure_worker_transport()
    pool = ProcessPoolExecutor(
        max_workers=count,
        mp_context=multiprocessing.get_context("spawn"),
        initializer=configure_worker_transport,
    )
    active: dict[Future[Result], tuple[str, float]] = {}
    completed: dict[str, Result] = {}
    remaining = iter(pages)
    submitted_pages: set[str] = set()

    def refill() -> None:
        while len(active) < count:
            page = next(remaining, None)
            if page is None:
                return
            submitted = time.monotonic()
            payload = payloads[page] if payloads is not None else page
            active[pool.submit(work, payload)] = (page, submitted + timeout)
            submitted_pages.add(page)

    try:
        refill()
        while active:
            earliest = min(deadline for _, deadline in active.values())
            done, _ = wait(
                active, timeout=max(0, earliest - time.monotonic()), return_when=FIRST_COMPLETED
            )
            for future in done:
                page, _ = active.pop(future)
                try:
                    completed[page] = future.result()
                except Exception as error:
                    raise PageWorkError(f"page {page!r} failed: {error}") from error
            expired = [page for page, deadline in active.values() if deadline <= time.monotonic()]
            if expired:
                raise PageWorkError(f"page submission-to-result deadline exceeded: {expired!r}")
            refill()
        pool.shutdown(wait=True)
    except BaseException as error:
        error.add_note(
            f"completed pages: {sorted(completed)!r}; "
            f"incomplete pages: {sorted(set(pages) - completed.keys())!r}; "
            f"not submitted pages: {sorted(set(pages) - submitted_pages)!r}"
        )
        pool.kill_workers()
        raise
    return completed


def retained_pages(pages: Iterable[str]) -> dict[str, PageContent]:
    return {page: load_page(page) for page in pages}


def reading_pages(
    pages: Mapping[str, PageContent], *, seconds: float | None = None
) -> dict[str, PageReadings]:
    work = read_content if seconds is None else partial(read_content, seconds=seconds)
    readings = _run_pages(work, pages)
    return {
        key: PageReadings(key, page.content, page.macros, readings[key])
        for key, page in pages.items()
    }


def extraction_pages(pages: Mapping[str, PageReadings]) -> dict[str, PageExtraction]:
    extracted = _run_pages(extract_readings, {key: page.readings for key, page in pages.items()})
    return {
        key: PageExtraction(key, page.content, page.macros, page.readings, *extracted[key])
        for key, page in pages.items()
    }


def scoped_pages(pages: Mapping[str, PageExtraction]) -> dict[str, PageMath]:
    # Do not send the complete extraction view: scopes do not consume its readings.
    scopes = _run_pages(
        scope_extraction,
        {
            key: (PageContent(key, page.content, page.macros), page.values, page.extraction)
            for key, page in pages.items()
        },
    )
    return {
        key: PageMath(
            key, page.content, page.macros, page.readings, page.values, page.extraction, scopes[key]
        )
        for key, page in pages.items()
    }


def _without_scopes(page: str) -> PageMath:
    return analyse(page, scopes=False)


def analyse_all(pages: Iterable[str], scopes: bool = True) -> dict[str, PageMath]:
    return _run_pages(analyse if scopes else _without_scopes, pages)


@dataclass(frozen=True)
class MathEnv:
    """The pack values and the page analyser, for the test modules."""

    macros: dict[str, MacroDef]
    constants: tuple[str, ...]
    binders: Binders
    data: Path
    index: Path


@dataclass(frozen=True)
class SpanRow:
    """One span's reading, compactly: for the 78-page coverage report."""

    start: int
    end: int
    status: str
    kind: str | None
    category: str | None
    agrees: bool | None  # the tree/token property; None when nothing was read
    text: str


def coverage_rows(page: str) -> list[SpanRow]:
    from corpus_structure.methods.math.printer import print_tree

    analysed = read_page(page)
    rows = []
    for reading in analysed.readings:
        result = reading.result
        given = analysed.content.text(reading.span.segment)
        agrees = None
        if result.tree is not None:
            printed = print_tree(result.tree, result.latex, result.macros, result.tail)
            agrees = printed == tex.token_form(given, result.macros)
        rows.append(
            SpanRow(
                reading.span.segment.start,
                reading.span.segment.end,
                result.status.value,
                result.kind,
                result.failure.category if result.failure else None,
                agrees,
                given,
            )
        )
    return rows


def coverage_all(pages: Iterable[str]) -> dict[str, list[SpanRow]]:
    return _run_pages(coverage_rows, pages)
