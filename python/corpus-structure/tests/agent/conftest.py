"""Agent-interface test support (agent interface §6, P0-A-1).

**The world** (on a committing clone): a project over the vendored trace pages with the
statistics pack and phase 0's registered methods (ingest, M09, M11, M13, M24, consolidation, M19);
a run with renditions, M09's mentions, M11's values, M13's scopes and M24 tasks for the five trace
units of `fixtures/s0`.
The stage runner creates every task, so M24's tasks carry their packet hashes exactly as in
production.

**The tools** are called through an in-process `Client(server)` on a `Session` the test holds, so
the lease, the served record and the caches persist across calls (`Tools.call`).

`importlib` import mode leaves this module unimportable from the tests; its parts are served by the
`agent` fixture.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import yaml

from corpus_structure.core import tex
from corpus_structure.core.evidence import MacroDef, RenditionContent, segment_key
from corpus_structure.core.payloads import MentionPayload, ScopePayload

REPO = Path(__file__).resolve().parents[4]
TRACE_CORPUS = REPO / "fixtures" / "trace" / "corpus"
S0 = REPO / "fixtures" / "s0"
STATISTICS = REPO / "domains" / "statistics"
ROOT = "siegrist_random/random"
TRACE_UNITS = ("T1-leadin", "T1-dfn1", "T2", "T3", "T4")
STATS_METHODS = yaml.safe_load((STATISTICS / "methods.yaml").read_text(encoding="utf-8"))
PACK_MACROS = {k: MacroDef(body=v) for k, v in STATS_METHODS["math"]["macros"].items()}


def s0(name: str) -> dict[str, Any]:
    return json.loads((S0 / f"{name}.json").read_text(encoding="utf-8"))


# --- In-memory analysis (the grammar runs here, in the test process's main thread) ---------------


@dataclass(frozen=True)
class Analysis:
    content: RenditionContent
    macros: dict[str, MacroDef]
    mentions: list[Any]
    scopes: list[Any]


_ANALYSES: dict[str, Analysis] = {}


def analyse(content: RenditionContent) -> Analysis:
    from corpus_structure.ingest.sentences import SentenceConfig
    from corpus_structure.methods.math.scope import Binders, resolve_scopes
    from corpus_structure.methods.math.spans import extract, formula_values, read_spans

    key = content.canonical_text
    if key not in _ANALYSES:
        macros = tex.effective_macros(content.macros, PACK_MACROS)
        readings = read_spans(content, macros, tuple(STATS_METHODS["math"]["constants"]))
        extraction = extract(readings)
        scopes = resolve_scopes(
            content,
            formula_values(readings),
            extraction.mentions,
            extraction.relations,
            macros,
            Binders(**STATS_METHODS["binders"]),
            SentenceConfig(),
        )
        _ANALYSES[key] = Analysis(content, dict(macros), list(extraction.mentions), scopes)
    return _ANALYSES[key]


@cache
def page_content(page: str) -> RenditionContent:
    from corpus_structure.ingest.html import build_rendition
    from corpus_structure.ingest.profile import compile_profile, load_profile
    from corpus_structure.ingest.sentences import SentenceConfig

    source = f"{ROOT}/{page}"
    corpus = (
        TRACE_CORPUS if (TRACE_CORPUS / source).exists() else REPO / "docs/statistics_corpus/corpus"
    )
    raw = (corpus / source).read_bytes()
    profile = compile_profile(load_profile("siegrist"))
    return build_rendition(raw, profile, SentenceConfig(), source_uri=source).content


def _rendition(content: RenditionContent, rendition_key: str) -> Any:
    from corpus_structure.methods.math.methods import _Rendition

    keys = {segment_key(rendition_key, x.kind, x.start, x.end): i
            for i, x in enumerate(content.document.walk())}  # fmt: skip
    return _Rendition(0, rendition_key, "", content, keys)


def mention_payloads(content: RenditionContent, rendition_key: str) -> list[MentionPayload]:
    """M09's stored mentions, by I2b's own draft builder over the in-memory analysis."""
    from corpus_structure.methods.math.methods import math_drafts

    a = analyse(content)
    drafts = math_drafts(_rendition(content, rendition_key), a.mentions, ())
    return [d.payload for d in drafts if isinstance(d.payload, MentionPayload)]


def scope_payloads(
    content: RenditionContent,
    rendition_key: str,
    m09_task: int | None,
    ordinals: dict[tuple[int, int], int],
) -> list[ScopePayload]:
    """M13's stored scopes, by I2b's own draft builder; `ordinals` maps a mention's (start, end)
    to its M09 ordinal."""
    from corpus_structure.core.payloads import MentionRef
    from corpus_structure.methods.math.methods import scope_drafts

    analysis = analyse(content)
    # The draft builder references the actual analysis occurrences; span ordinals belong only
    # to this stored-payload fixture's input boundary.
    refs: dict[int, MentionRef] = {}
    for mention in analysis.mentions:
        ordinal = ordinals[(mention.start, mention.end)]
        refs[id(mention)] = (
            MentionRef(task=m09_task, ordinal=ordinal)
            if m09_task is not None
            else MentionRef(ordinal=ordinal)
        )
    drafts = scope_drafts(_rendition(content, rendition_key), analysis.scopes, refs)
    return [d.payload for d in drafts if isinstance(d.payload, ScopePayload)]


@pytest.fixture
def agent() -> SimpleNamespace:
    return SimpleNamespace(
        s0=s0,
        TRACE_UNITS=TRACE_UNITS,
        page_content=page_content,
        analyse=analyse,
        mention_payloads=mention_payloads,
        scope_payloads=scope_payloads,
        PACK_MACROS=PACK_MACROS,
        STATISTICS=STATISTICS,
        REPO=REPO,
    )
