"""M13 and the standing context (ingest and math §3.9, §3.10, §6 P0-I-2a; D4 M13, §4.1).

Against thin fixtures written once from the spike (`data/build.py`): the 20 annotated symbol scopes
of the S0 reference (record `s0.m13-probe-2`) and the 21 S0-R2 standing contexts
(`results/s0r2/sample.json`, records `s0r2.inputs`, `s0r2.scores`), as sentence texts and offsets,
with each context sentence's generated locator resolving to it. The core units' four pages are
vendored; the held-out and example units' three pages are `corpus`-marked.

Phase 0 M13 omits the paragraph rule, so the annotated scopes are reported, not required: 18 of 20,
U6's `X` and `Z` going to the section (OPEN-D4-5).

**H3 differs from `sample.json`, by a spike defect.** Pareto's sentences at 9504 ("Suppose again
that \\( X \\) has the Pareto distribution ... \\( b \\in (0, \\infty) \\).") and 11267 (the same
words opening the Moments section, without the period) share their first 100 characters. The
spike's `s0r2_sample.context_for` found a symbol's binding site again by its sentence's first 100
characters, so it took the earlier sentence's site for `X`, `a` and `b`, and with it that site's
reopen (2123). By D4 M13's rules H3's symbols bind at 11267, which reopens 9504: the standing
context is 9504 and 11267.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from corpus_structure.core import tex
from corpus_structure.core.keys import symbol_form
from corpus_structure.core.locators import LocatorIndex
from corpus_structure.core.vocab import MathKind, ScopeExtent, SegmentKind
from corpus_structure.ingest.html import build_rendition
from corpus_structure.ingest.profile import compile_profile, load_profile
from corpus_structure.ingest.sentences import SentenceConfig, split
from corpus_structure.methods.math.context import standing_context
from corpus_structure.methods.math.scope import resolve_scopes, segment_block
from corpus_structure.methods.math.spans import extract, formula_values, read_spans

CORRECTED = {"H3": [(9504, 9648), (11267, 11410)]}


def load(env: Any, name: str) -> dict[str, Any]:
    return json.loads((env.data / f"{name}.json").read_text(encoding="utf-8"))


def parts_of(page: Any, parts: list[dict[str, Any]]) -> list[Any]:
    wanted = {(p["kind"], p["start"], p["end"]) for p in parts}
    found = [s for s in page.content.document.walk() if (s.kind.value, s.start, s.end) in wanted]
    assert len(found) == len(parts), parts
    return found


def check_contexts(env: Any, pages: dict[str, Any], units: dict[str, Any]) -> list[str]:
    differ = []
    for uid, unit in units.items():
        page = pages[unit["page"]]
        got = standing_context(
            page.content, unit["page"], page.scopes, parts_of(page, unit["parts"])
        )
        index = LocatorIndex(page.content, unit["page"])
        for sentence in got:
            assert index.resolve(sentence.locator) == sentence.segment
            assert sentence.text == page.content.text(sentence.segment)
        assert [c.id for c in got] == [f"c{i + 1}" for i in range(len(got))]
        want = [(c["start"], c["end"], c["text"]) for c in unit["context"]]
        if uid in CORRECTED:
            text = page.content.canonical_text
            want = [(a, b, text[a:b]) for a, b in CORRECTED[uid]]
        mine = [(c.segment.start, c.segment.end, c.text) for c in got]
        if mine != want:
            differ.append(f"{uid}: {mine} != {want}")
    return differ


def test_core_standing_contexts(env: Any, spike_pages: dict[str, Any]) -> None:
    units = {u: v for u, v in load(env, "s0r2_contexts")["units"].items() if v["set"] == "core"}
    assert len(units) == 12
    assert check_contexts(env, spike_pages, units) == []


def test_suppose_again_yields_both_context_sentences(env: Any, spike_pages: dict[str, Any]) -> None:
    """T2 ("Suppose again ..."): its site's sentence and the sentence it reopens."""
    unit = load(env, "s0r2_contexts")["units"]["T2"]
    page = spike_pages[unit["page"]]
    got = standing_context(page.content, unit["page"], page.scopes, parts_of(page, unit["parts"]))
    assert [c.text[:24] for c in got] == [
        "Suppose that \\( X \\) has",
        "Let \\(F\\) denote the dis",
    ]
    scope = next(
        s
        for s in page.scopes
        if s.symbol == "X" and unit["parts"][0]["start"] <= s.mention.start and s.site is not None
    )
    assert scope.site is not None and scope.site.reopen and scope.reopens is not None


@pytest.mark.corpus
def test_held_out_and_example_standing_contexts(env: Any, s0r2_pages: dict[str, Any]) -> None:
    units = {u: v for u, v in load(env, "s0r2_contexts")["units"].items() if v["set"] != "core"}
    assert len(units) == 9
    assert check_contexts(env, s0r2_pages, units) == []


def test_annotated_scopes_reported(env: Any, spike_pages: dict[str, Any]) -> None:
    rows = load(env, "s0_scopes")["scopes"]
    assert len(rows) == 20
    report = []
    for row in rows:
        page = spike_pages[row["page"]]
        ranges = [(p["start"], p["end"]) for p in row["parts"]]
        symbol = symbol_form(row["symbol"], page.macros)
        inside = sorted(
            (
                s
                for s in page.scopes
                if s.symbol == symbol and any(a <= s.mention.start < b for a, b in ranges)
            ),
            key=lambda s: s.mention.start,
        )
        first = next((s for s in inside if s.site is not None), None)
        got = first.site.extent.value if first and first.site else "unresolved"
        report.append((row["unit"], row["symbol"], row["annotated"], got, row["spike"]))
    matched = sum(got == annotated for _, _, annotated, got, _ in report)
    print(f"\nannotated scopes reproduced: {matched} of {len(report)}")
    for line in report:
        print("  ", *line)
    assert [got for *_, got, _ in report] == [spike for *_, spike in report]
    assert matched == 18
    assert {(u, s) for u, s, a, g, _ in report if a != g} == {("U6", "X"), ("U6", "Z")}


def test_scopes_are_typed_and_inside_their_extent(spike_pages: dict[str, Any]) -> None:
    for page in spike_pages.values():
        for scope in page.scopes:
            assert not scope.mention.constant
            site = scope.site
            if site is None:
                continue
            assert site.symbol == scope.symbol
            assert site.start <= scope.mention.start < site.end or site.mention == scope.mention
            assert site.sentence.start <= site.mention.start < site.sentence.end
            if site.extent is ScopeExtent.STATEMENT:
                assert (site.start, site.end) == (site.scope.start, site.scope.end)
            else:
                assert site.end == site.scope.end


def scopes_of(env: Any, html: str) -> tuple[Any, list[Any], list[Any]]:
    """M01 with M03, then M11, M09 and M13, on a small Siegrist-shaped page."""
    source_uri = "siegrist_random/random/test/Page.html"
    content = build_rendition(
        html.encode(),
        compile_profile(load_profile("siegrist")),
        SentenceConfig(),
        source_uri=source_uri,
    ).content
    macros = tex.effective_macros(content.macros, env.macros)
    readings = read_spans(content, macros, env.constants)
    values = formula_values(readings)
    found = extract(readings)
    return (
        content,
        values,
        resolve_scopes(
            content, values, found.mentions, found.relations, macros, env.binders, SentenceConfig()
        ),
    )


def test_a_list_binds_every_symbol(env: Any) -> None:
    """M11 reads `a, b` as a list; M13 binds both symbols at the binder sentence, and their later
    mentions in the unit go to those sites."""
    html = (
        "<html><body><h3>Sums</h3><div class='unit'><p>Let \\(a, b\\) be real numbers. "
        "Then \\(a + b\\) is real and \\(c\\) is free.</p></div></body></html>"
    )
    content, values, scopes = scopes_of(env, html)
    assert [v.math_kind for v in values][:1] == [MathKind.LIST]
    later = [s for s in scopes if content.canonical_text.index("Then") < s.mention.start]
    bound = {s.symbol: s.site for s in later}
    assert bound["c"] is None  # never bound: unresolved
    for symbol in ("a", "b"):
        site = bound[symbol]
        assert site is not None and site.extent is ScopeExtent.STATEMENT
        assert content.text(site.sentence) == "Let \\(a, b\\) be real numbers."
        assert site.rules == ("initial",)


def test_m13_rebuilds_the_block_m03_split(spike_pages: dict[str, Any]) -> None:
    """M13's block (`segment_block`, M03's `block_of` over the stored segment) splits into exactly
    the stored sentences: the two Docs are the same by construction."""
    checked = 0
    for page in spike_pages.values():
        content = page.content
        blocks, stored = [], []
        for segment in content.document.walk():
            sentences = [c for c in segment.children if c.kind is SegmentKind.SENTENCE]
            if not sentences:
                continue
            blocks.append(segment_block(content, segment))
            stored.append([(c.start - segment.start, c.end - segment.start) for c in sentences])
        assert split(blocks, SentenceConfig()) == stored
        checked += len(blocks)
    assert checked > 300


def test_interval_sweep_preserves_overlap_width_and_preorder_ties() -> None:
    from corpus_structure.core.evidence import Segment
    from corpus_structure.methods.math.scope import _enclosing_at

    outer = Segment(kind=SegmentKind.SECTION, start=0, end=100)
    first = Segment(kind=SegmentKind.SECTION, start=10, end=40)
    second = Segment(kind=SegmentKind.SECTION, start=20, end=50)
    inner = Segment(kind=SegmentKind.SECTION, start=24, end=28)
    got = _enclosing_at([outer, first, second, inner], [0, 20, 25, 28, 40, 50, 100])
    assert got == {0: outer, 20: first, 25: inner, 28: first, 40: second, 50: outer}


def test_site_index_preserves_same_position_exception_and_strict_reopen() -> None:
    from corpus_structure.core.evidence import Segment
    from corpus_structure.methods.math.scope import BindingSite, _site_assignments, _with_reopens
    from corpus_structure.methods.math.spans import SymbolMention

    sentence = Segment(kind=SegmentKind.SENTENCE, start=0, end=100)
    def site(pos: int, start: int, end: int, *, reopen: bool = False) -> BindingSite:
        mention = SymbolMention(sentence, pos, pos + 1, "x", "x", None, None, False, None)
        return BindingSite(mention, "x", sentence, ScopeExtent.SECTION, sentence,
                           start, end, (), reopen)

    earlier = site(5, 5, 90)
    same_first = site(20, 20, 60, reopen=True)
    same_second = site(20, 20, 50, reopen=True)
    outside_self = site(30, 31, 32)
    sites = [earlier, same_first, same_second, outside_self]
    got = _site_assignments(sites, [4, 5, 20, 30, 31, 32, 50, 90])
    assert got == {5: earlier, 20: same_second, 30: outside_self, 31: outside_self,
                   32: same_second, 50: same_first}
    reopened = _with_reopens(sites)
    assert reopened[1].reopens is earlier
    assert reopened[2].reopens is earlier
