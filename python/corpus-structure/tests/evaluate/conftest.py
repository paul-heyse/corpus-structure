"""Shared fixtures of the alignment tests (evaluation §6, P0-E-2a).

The statistics pack's lookup and name map, D2 §12.1's `aliases` label rules and `math` fallback
(written here until `domains/statistics/methods.yaml` exists), production renditions of the
vendored spike pages, and `fixtures/s0` batches parsed onto them by A0. The S0 parity test reads
the tracked spike results as data and imports no spike code.
"""

from __future__ import annotations

import functools
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from corpus_structure.core import tex
from corpus_structure.core.batch import AuthoredBatch, CitationFrame, StoredBatch
from corpus_structure.core.evidence import (
    MacroDef,
    Segment,
    content_digest,
    document_key,
    rendition_key,
)
from corpus_structure.core.keys import LabelRules, Rewrite
from corpus_structure.core.locators import LocatorIndex
from corpus_structure.evaluate.agreement import side_of
from corpus_structure.evaluate.align import AlignmentContext, AlignmentSide
from corpus_structure.evaluate.equivalence import ValueComparator
from corpus_structure.evaluate.goldens import context_refs
from corpus_structure.ingest.html import build_rendition
from corpus_structure.ingest.profile import compile_profile, load_profile
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.llm.parse import RenditionView, parse
from corpus_structure.schema.lookup import SchemaLookup, build_lookup, name_map
from corpus_structure.schema.pack import load_pack

REPO = Path(__file__).resolve().parents[4]
ROOT = "siegrist_random/random"
SPIKE = REPO / "docs/design_review/evidence/2026-10-28_design-spikes"
CONSTANTS = ("e", "\\pi")
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
LABELS = LabelRules(
    articles=("the", "a", "an"),
    head_words={"stat:DistributionFamily": ("distribution", "distributions")},
    rewrites=(
        Rewrite(match=r"^(\w+)ly distributed$", replace=r"\1"),
        Rewrite(match=r"^(\w+) distributed$", replace=r"\1"),
    ),
)


@functools.cache
def statistics() -> tuple[SchemaLookup, dict[str, str]]:
    pack = load_pack(REPO / "domains/statistics")
    return build_lookup([pack]), dict(name_map([pack]).to_prefixed)


@functools.cache
def view(page: str) -> RenditionView:
    uri = f"{ROOT}/{page}"
    raw = (REPO / "fixtures/trace/corpus" / uri).read_bytes()
    profile = compile_profile(load_profile("siegrist"))
    content = build_rendition(raw, profile, SentenceConfig(), source_uri=uri).content
    document = document_key("statistics", uri, hashlib.sha256(raw).hexdigest())
    return RenditionView(
        content,
        page,
        rendition_key(document, content_digest(content)),
        tex.effective_macros(content.macros, PACK_MACROS),
    )


def context(macros: dict[str, MacroDef], **decisions: Any) -> AlignmentContext:
    lookup, _ = statistics()
    comparator = ValueComparator(macros, CONSTANTS, decisions=decisions.get("decisions"))
    return AlignmentContext(lookup, LABELS, macros, comparator)


@dataclass(frozen=True)
class Fixture:
    name: str
    batch: AuthoredBatch
    frame: CitationFrame
    view: RenditionView
    unit: Segment

    def stored(self, batch: AuthoredBatch | None = None) -> StoredBatch:
        return parse(self.view, batch or self.batch, self.frame, statistics()[1]).stored

    def side(self, stored: StoredBatch | None = None, name: str = "") -> AlignmentSide:
        return side_of(
            stored or self.stored(),
            self.view.content,
            [self.unit],
            name or self.name,
            context_refs(self.batch),
        )


@functools.cache
def s0(name: str) -> Fixture:
    raw = json.loads((REPO / "fixtures/s0" / f"{name}.json").read_text(encoding="utf-8"))
    v = view(raw["provenance"]["rendition"]["page"])
    unit = LocatorIndex(v.content, v.page).resolve(raw["unit_key"])
    return Fixture(
        name,
        AuthoredBatch.model_validate(raw["batch"]),
        CitationFrame.model_validate(raw["frame"]),
        v,
        unit,
    )


@dataclass(frozen=True)
class Env:
    s0: Any
    context: Any
    statistics: Any
    view: Any
    spike: Path


@pytest.fixture(scope="session")
def env() -> Env:
    return Env(s0, context, statistics, view, SPIKE)
