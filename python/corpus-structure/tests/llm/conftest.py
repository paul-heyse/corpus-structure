"""Shared fixtures of the parse tests (agent interface §6, P0-A-0).

Renditions are retained historical inputs captured before the HTML writer retired. The four
spike pages are vendored under `fixtures/trace/corpus/`,
so their checks never skip; the three S0-R2 pages read the gitignored corpus and their tests are
`corpus`-marked. The spike side is the thin fixtures of `data/` (written once by `data/build.py`).

The pack's fallback macro map is D2 §12.1's `domains/statistics/methods.yaml` `math.macros`, written
here until that file exists.
"""

from __future__ import annotations

import functools
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from archived_source import archived_rendition

from corpus_structure.core import tex
from corpus_structure.core.batch import CitationFrame, FrameEntry
from corpus_structure.core.evidence import (
    MacroDef,
    RenditionContent,
    Segment,
    SegmentKind,
    content_digest,
    document_key,
    rendition_key,
)
from corpus_structure.core.locators import LocatorIndex
from corpus_structure.schema.lookup import name_map
from corpus_structure.schema.pack import load_pack

REPO = Path(__file__).resolve().parents[4]
VENDORED = REPO / "fixtures/trace/corpus"
CORPUS = REPO / "docs/statistics_corpus/corpus"
ROOT = "siegrist_random/random"
DATA = Path(__file__).with_name("data")
SPIKE_PAGES = frozenset(
    {
        "special/LocationScale.html",
        "special/Normal.html",
        "special/LogNormal.html",
        "special/Gamma.html",
    }
)

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


@functools.cache
def data(name: str) -> Any:
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


def raw_page(page: str) -> bytes:
    corpus = VENDORED if page in SPIKE_PAGES else CORPUS
    return (corpus / ROOT / page).read_bytes()


@dataclass(frozen=True)
class ArchivedPage:
    content: RenditionContent
    page: str
    key: str
    macros: dict[str, MacroDef]


def view_of(page: str, raw: bytes) -> ArchivedPage:
    """A production rendition of `raw` as parse reads it, with its `ren` key."""
    uri = f"{ROOT}/{page}"
    content = archived_rendition(page, raw)
    document = document_key("statistics", uri, hashlib.sha256(raw).hexdigest())
    return ArchivedPage(
        content,
        page,
        rendition_key(document, content_digest(content)),
        tex.effective_macros(content.macros, PACK_MACROS),
    )


@functools.cache
def page_view(page: str) -> ArchivedPage:
    return view_of(page, raw_page(page))


def sentence_at(content: RenditionContent, start: int, end: int) -> Segment:
    for s in content.document.walk():
        if s.kind is SegmentKind.SENTENCE and (s.start, s.end) == (start, end):
            return s
    raise AssertionError(f"no sentence [{start}, {end}) on the production rendition")


def frame_of(view: ArchivedPage, sentences: dict[str, list[int]]) -> CitationFrame:
    """The packet's frame of a spike unit on the production rendition: each sentence id's
    generated locator and text (the spike's offsets are the production rendition's, S1)."""
    index = LocatorIndex(view.content, view.page)
    entries = {}
    for sid, (start, end) in sentences.items():
        segment = sentence_at(view.content, start, end)
        entries[sid] = FrameEntry(
            locator=str(index.generate(segment)), text=view.content.text(segment)
        )
    return CitationFrame(entries)


@dataclass(frozen=True)
class Env:
    data: Callable[[str], Any]
    view: Callable[[str], ArchivedPage]
    view_of: Callable[[str, bytes], ArchivedPage]
    raw: Callable[[str], bytes]
    frame: Callable[[ArchivedPage, dict[str, list[int]]], CitationFrame]
    names: dict[str, str]
    fixtures: Path


@pytest.fixture(scope="session")
def env() -> Env:
    names = dict(name_map([load_pack(REPO / "domains/statistics")]).to_prefixed)
    return Env(data, page_view, view_of, raw_page, frame_of, names, REPO / "fixtures/s0")
