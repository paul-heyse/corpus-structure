"""Shared fixtures of the ingest tests (ingest and math §6, P0-I-1a).

The four spike pages are vendored under `fixtures/trace/corpus/` (P0-F-3), so their checks never
skip; the three S0-R2 pages and the 78-page run read the gitignored corpus and are `corpus`-marked.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from pathlib import Path

import pytest

from corpus_structure.ingest.html import IngestResult, build_rendition
from corpus_structure.ingest.profile import CompiledProfile, compile_profile, load_profile
from corpus_structure.ingest.sentences import SentenceConfig

REPO = Path(__file__).resolve().parents[4]
VENDORED = REPO / "fixtures/trace/corpus"
CORPUS = REPO / "docs/statistics_corpus/corpus"
ROOT = "siegrist_random/random"


@functools.cache
def siegrist() -> CompiledProfile:
    return compile_profile(load_profile("siegrist"))


@functools.cache
def ingest_page(page: str, corpus: Path = VENDORED) -> IngestResult:
    """A Siegrist page's production rendition, built once per test session."""
    source_uri = f"{ROOT}/{page}"
    raw = (corpus / source_uri).read_bytes()
    return build_rendition(raw, siegrist(), SentenceConfig(), source_uri=source_uri)


@pytest.fixture(scope="session")
def profile() -> CompiledProfile:
    return siegrist()


@pytest.fixture(scope="session")
def ingest() -> Callable[..., IngestResult]:
    return ingest_page
