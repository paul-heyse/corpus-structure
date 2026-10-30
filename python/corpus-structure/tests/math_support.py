"""Shared fixtures of the math tests (ingest and math §6, P0-I-2a).

Pages are the production renditions (`ingest.html.build_rendition` with the Siegrist profile and
the default sentence configuration), read by the production grammar, M11, M09 and M13. The four
spike pages are vendored under `fixtures/trace/corpus/` (P0-F-3), so their checks never skip; the
three S0-R2 pages and the 78-page run read the gitignored corpus and are `corpus`-marked.

Pages are analysed in spawned single-threaded worker processes, one page per task: the grammar's
deadline runs only on a process's main thread, and a page's spans take tens of seconds of CPU.

The pack constants below retain the independent historical oracle configuration.
"""

from __future__ import annotations

import multiprocessing
import os
import time
from collections.abc import Callable, Iterable
from concurrent.futures import FIRST_COMPLETED, Future, ProcessPoolExecutor, wait
from dataclasses import dataclass
from pathlib import Path

from corpus_structure.core import tex
from corpus_structure.core.evidence import MacroDef, RenditionContent
from corpus_structure.ingest.html import build_rendition
from corpus_structure.ingest.profile import CompiledProfile, compile_profile, load_profile
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.math.scope import Binders, Scope, resolve_scopes
from corpus_structure.methods.math.spans import (
    MathExtraction,
    SpanReading,
    SpanValue,
    extract,
    formula_values,
    read_spans,
)

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
class PageReadings:
    page: str
    content: RenditionContent
    macros: dict[str, MacroDef]
    readings: list[SpanReading]


@dataclass(frozen=True)
class PageMath:
    page: str
    content: RenditionContent
    macros: dict[str, MacroDef]  # the effective table
    readings: list[SpanReading]
    values: list[SpanValue]
    extraction: MathExtraction
    scopes: list[Scope]


_PROFILE: list[CompiledProfile] = []


def _profile() -> CompiledProfile:
    if not _PROFILE:
        _PROFILE.append(compile_profile(load_profile("siegrist")))
    return _PROFILE[0]


def corpus_of(page: str) -> Path:
    return VENDORED if (VENDORED / ROOT / page).exists() else CORPUS


def read_page(page: str) -> PageReadings:
    """Build a rendition and read its spans, without downstream extraction."""
    source_uri = f"{ROOT}/{page}"
    raw = (corpus_of(page) / source_uri).read_bytes()
    content = build_rendition(raw, _profile(), SentenceConfig(), source_uri=source_uri).content
    macros = tex.effective_macros(content.macros, PACK_MACROS)
    readings = read_spans(content, macros, CONSTANTS)
    return PageReadings(page, content, macros, readings)


def analyse(page: str, scopes: bool = True) -> PageMath:
    """A page's readings, values, extraction and optional scopes."""
    parsed = read_page(page)
    content, macros, readings = parsed.content, parsed.macros, parsed.readings
    values = formula_values(readings)
    extraction = extract(readings)
    found = (
        resolve_scopes(
            content,
            values,
            extraction.mentions,
            extraction.relations,
            macros,
            BINDERS,
            SentenceConfig(),
        )
        if scopes
        else []
    )
    return PageMath(page, content, macros, readings, values, extraction, found)


class PageWorkError(RuntimeError):
    """The page oracle is incomplete; no missing page has an invented result."""


def _run_pages[Result](
    work: Callable[[str], Result],
    pages: Iterable[str],
    *,
    timeout: float = 300,
    workers: int | None = None,
) -> dict[str, Result]:
    """Bound outstanding page jobs and kill the complete pool on any failure.

    The deadline starts at submission, including spawn/startup time. Never use the
    executor context manager here: its normal shutdown would wait for a stuck job.
    """
    pages = tuple(pages)
    if timeout <= 0 or (workers is not None and workers <= 0):
        raise ValueError("page timeout and worker count must be positive")
    if len(set(pages)) != len(pages):
        raise ValueError("page work requires distinct page identities")
    if not pages:
        return {}
    count = min(8, len(pages), workers or os.process_cpu_count() or 1)
    pool = ProcessPoolExecutor(max_workers=count, mp_context=multiprocessing.get_context("spawn"))
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
            active[pool.submit(work, page)] = (page, submitted + timeout)
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
