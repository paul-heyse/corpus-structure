"""Production renditions of the seven S0/S0-R2 pages against the spike renditions, the trace
segment fixtures, locators on them, content digests across M03 configurations, and M02.

ingest and math §5 P0-I-1a and §6. The spike side is the thin fixture `data/spike_renditions.json`
(written once from the frozen S1 renditions by `data/build.py`); the comparison never runs the
spike's code. The four spike pages are vendored (`fixtures/trace/corpus`); Pareto, ChiSquare and
Weibull come from the gitignored corpus.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest

from corpus_structure.core.evidence import RenditionContent, Segment, content_digest
from corpus_structure.core.locators import LocatorIndex, parse
from corpus_structure.core.vocab import SegmentKind
from corpus_structure.ingest.html import IngestResult, build_rendition
from corpus_structure.ingest.profile import CompiledProfile
from corpus_structure.ingest.profile_segments import MEASURED, features, measurements
from corpus_structure.ingest.sentences import SentenceConfig

REPO = Path(__file__).resolve().parents[4]
SPIKE = json.loads((Path(__file__).with_name("data") / "spike_renditions.json").read_text())
TRACE = REPO / "fixtures/trace"
CORPUS = REPO / "docs/statistics_corpus/corpus"
VENDORED_PAGES = (
    "special/LocationScale.html",
    "special/Normal.html",
    "special/LogNormal.html",
    "special/Gamma.html",
)
S0R2_PAGES = ("special/Pareto.html", "special/ChiSquare.html", "special/Weibull.html")
TRACE_UNITS = ("T1-leadin", "T1-dfn1", "T2", "T3", "T4")
Ingest = Callable[..., IngestResult]

# D2 §12.2 `trace` and `core12`, with the kind each selects (as P0-I-0's test lists them).
SLICE_LOCATORS = (
    ("special/LocationScale.html@p:As usual, our starting point", "paragraph"),
    ("special/LocationScale.html#dfn1", "unit"),
    (
        "special/Normal.html@p:Suppose again that \\( X \\) has the normal distribution with "
        "location parameter",
        "paragraph",
    ),
    ("special/Normal.html#rel1", "unit"),
    ("special/LogNormal.html#dfn", "unit"),
    ("special/Normal.html#rel2", "unit"),
    (
        "special/Normal.html@p:Recall that in general, if \\(X\\) is a random variable with mean",
        "paragraph",
    ),
    ("special/Normal.html@p:In some settings, it's convenient to consider a constant", "paragraph"),
    ("special/Normal.html@u:A metal rod is designed", "unit"),
    ("special/LogNormal.html@u:Suppose that \\(n \\in \\N_+\\) and that", "unit"),
    ("special/Gamma.html#dfn4", "unit"),
    ("special/Gamma.html#rel2", "unit"),
    ("special/Gamma.html#mom1", "unit"),
)


def projection(content: RenditionContent) -> tuple[list[list], list[list]]:
    """Segments and sentences as the fixture holds them: identities with their parent's."""
    segments: list[list] = []
    sentences: list[list] = []

    def visit(segment: Segment, parent: Segment | None) -> None:
        up = [parent.kind.value, parent.start, parent.end] if parent else [None, None, None]
        if segment.kind is SegmentKind.SENTENCE:
            sentences.append([segment.start, segment.end, *up])
        else:
            segments.append([segment.kind.value, segment.start, segment.end, *up])
        for child in segment.children:
            visit(child, segment)

    visit(content.document, None)
    return sorted(segments), sorted(sentences)


def assert_equals_spike(page: str, result: IngestResult) -> None:
    expected = SPIKE["pages"][page]
    text = result.content.canonical_text
    assert (hashlib.sha256(text.encode()).hexdigest(), len(text)) == (
        expected["canonical_sha256"],
        expected["chars"],
    )
    segments, sentences = projection(result.content)
    assert segments == expected["segments"]
    assert sentences == expected["sentences"]


@pytest.mark.parametrize("page", VENDORED_PAGES)
def test_the_spike_pages_equal_the_spike_renditions(page: str, ingest: Ingest) -> None:
    assert_equals_spike(page, ingest(page))


@pytest.mark.corpus
@pytest.mark.parametrize("page", S0R2_PAGES)
def test_the_s0r2_pages_equal_the_spike_renditions(page: str, ingest: Ingest) -> None:
    assert_equals_spike(page, ingest(page, CORPUS))


@pytest.mark.parametrize("page", VENDORED_PAGES)
def test_every_segment_round_trips_through_its_locator(page: str, ingest: Ingest) -> None:
    result = ingest(page)
    index = LocatorIndex(result.content, result.page)
    for segment, locator in index:
        assert index.resolve(locator) is segment


def test_the_thirteen_slice_locators_resolve_on_the_production_renditions(ingest: Ingest) -> None:
    for text, kind in SLICE_LOCATORS:
        locator = parse(text)
        segment = LocatorIndex(ingest(locator.page).content, locator.page).resolve(locator)
        assert segment.kind.value == kind, text


def markup(segment: Segment) -> list[dict[str, Any]]:
    return cast(list[dict[str, Any]], segment.attrs.get("markup", []))


def _trace(unit: str) -> dict:
    return json.loads((TRACE / f"{unit}.segments.json").read_text(encoding="utf-8"))


INSERTION_NAMES = {"a": {"link", "ref"}, "dfn": {"dfn"}, "list_marker": {"list_marker"}}


@pytest.mark.parametrize("unit", TRACE_UNITS)
def test_the_trace_segment_fixtures_match(unit: str, ingest: Ingest) -> None:
    """Kinds, locators, offsets, attributes and parse statuses of each trace unit's subtree and
    ancestors. The fixture's attributes are S1's, which kept inline markup apart; production keeps
    it under `attrs.markup`, which must hold the fixture's `markup` records."""
    fixture = _trace(unit)
    result = ingest(fixture["page"])
    index = LocatorIndex(result.content, result.page)
    top = index.resolve(fixture["unit_key"])
    assert index.unit_key(top) == fixture["unit_key"]
    ancestors = [
        s
        for s in result.content.document.walk()
        if s.start <= top.start
        and top.end <= s.end
        and s is not top
        and any(top is d for d in s.walk())
    ]

    def row(s: Segment) -> dict:
        out = {
            "kind": s.kind.value,
            "locator": str(index.generate(s)),
            "start": s.start,
            "end": s.end,
            "attrs": {k: v for k, v in s.attrs.items() if k != "markup"},
            "parse_status": s.parse_status.value,
        }
        if s.parse_reason is not None:
            out["parse_reason"] = s.parse_reason
        return out

    assert [row(s) for s in ancestors] == fixture["ancestors"]
    assert [row(s) for s in top.walk()] == fixture["segments"]
    produced = {(m["markup"], m["start"], m["end"]) for s in top.walk() for m in markup(s)}
    for record in fixture["markup"]:
        names = INSERTION_NAMES.get(record["markup"])
        if names is None:
            continue
        assert any((name, record["start"], record["end"]) in produced for name in names), record
        assert result.content.canonical_text[record["start"] : record["end"]] == record["text"]


def test_builds_whose_m03_configurations_differ_but_split_alike_share_a_digest() -> None:
    raw = (TRACE / "corpus/siegrist_random/random/special/LogNormal.html").read_bytes()
    uri = "siegrist_random/random/special/LogNormal.html"
    from corpus_structure.ingest.profile import compile_profile, load_profile

    prof = compile_profile(load_profile("siegrist"))
    one = build_rendition(raw, prof, SentenceConfig(batch_size=64), source_uri=uri)
    two = build_rendition(raw, prof, SentenceConfig(batch_size=7), source_uri=uri)
    assert SentenceConfig(batch_size=64) != SentenceConfig(batch_size=7)
    assert content_digest(one.content) == content_digest(two.content)


def test_m02_features_count_characters_and_math(ingest: Ingest, profile: CompiledProfile) -> None:
    result = ingest("special/Normal.html")
    rows = features(result.content)
    assert rows and {f.segment.kind for f in rows} <= MEASURED
    t2 = LocatorIndex(result.content, result.page).resolve(_trace("T2")["unit_key"])
    (f,) = [f for f in rows if f.segment is t2]
    assert (f.chars, f.inline_math, f.display_math) == (t2.end - t2.start, 3, 0)
    inside = sum(c.end - c.start for c in t2.children if c.kind is SegmentKind.MATH_INLINE)
    assert f.math_share == round(inside / f.chars, 6)
    drafts = measurements(result.content, lambda s: f"seg:{s.kind.value}:{s.start}")
    assert len(drafts) == 4 * len(rows)
    assert {d.metric for d in drafts} == {
        "segment.chars",
        "segment.math_share",
        "segment.inline_math",
        "segment.display_math",
    }
