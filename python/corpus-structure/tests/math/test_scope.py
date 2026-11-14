"""Independent scope/extraction expectations over retained mathematical inputs."""

from __future__ import annotations

import json
from typing import Any

from math_support import primary_scope_fixture, read_spans, segment_block

from corpus_structure.core import tex
from corpus_structure.core.evidence import RenditionContent, Segment
from corpus_structure.core.keys import symbol_form
from corpus_structure.core.vocab import MathKind, ScopeExtent, SegmentKind
from corpus_structure.ingest.sentences import SentenceConfig, split
from corpus_structure.methods.math.scope import resolve_scopes
from corpus_structure.methods.math.spans import extract, formula_values


def load(env: Any, name: str) -> dict[str, Any]:
    return json.loads((env.data / f"{name}.json").read_text(encoding="utf-8"))


def test_annotated_scopes_reported(env: Any, spike_scoped: dict[str, Any]) -> None:
    rows = load(env, "s0_scopes")["scopes"]
    assert len(rows) == 20
    report = []
    for row in rows:
        page = spike_scoped[row["page"]]
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


def test_scopes_are_typed_and_inside_their_extent(spike_scoped: dict[str, Any]) -> None:
    for page in spike_scoped.values():
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


def scopes_of(env: Any, content: RenditionContent) -> tuple[Any, list[Any], list[Any]]:
    """Mathematical scope kernels over an independently constructed typed input."""
    macros = tex.effective_macros(content.macros, env.macros)
    readings = read_spans(content, macros, env.constants)
    values = formula_values(readings)
    found = extract(readings)
    return (
        content,
        values,
        resolve_scopes(
            content,
            values,
            found.mentions,
            found.relations,
            macros,
            primary_scope=primary_scope_fixture(content, env.binders),
        ),
    )


def test_a_list_binds_every_symbol(env: Any) -> None:
    """M11 reads `a, b` as a list; M13 binds both symbols at the binder sentence, and their later
    mentions in the unit go to those sites."""
    text = r"Let \(a, b\) be real numbers. Then \(a + b\) is real and \(c\) is free."
    math = []
    for value in (r"\(a, b\)", r"\(a + b\)", r"\(c\)"):
        start = text.index(value)
        math.append(
            Segment(
                kind=SegmentKind.MATH_INLINE,
                start=start,
                end=start + len(value),
                attrs={"open": r"\(", "close": r"\)"},
            )
        )
    split_at = text.index("Then")
    sentences = (
        Segment(kind=SegmentKind.SENTENCE, start=0, end=split_at - 1),
        Segment(kind=SegmentKind.SENTENCE, start=split_at, end=len(text)),
    )
    paragraph = Segment(
        kind=SegmentKind.PARAGRAPH, start=0, end=len(text), children=(*math, *sentences)
    )
    unit = Segment(kind=SegmentKind.UNIT, start=0, end=len(text), children=(paragraph,))
    source = RenditionContent(
        canonical_text=text,
        document=Segment(kind=SegmentKind.DOCUMENT, start=0, end=len(text), children=(unit,)),
    )
    content, values, scopes = scopes_of(env, source)
    assert [v.math_kind for v in values][:1] == [MathKind.LIST]
    later = [s for s in scopes if content.canonical_text.index("Then") < s.mention.start]
    bound = {s.symbol: s.site for s in later}
    assert bound["c"] is None  # never bound: unresolved
    for symbol in ("a", "b"):
        site = bound[symbol]
        assert site is not None and site.extent is ScopeExtent.STATEMENT
        assert content.text(site.sentence) == "Let \\(a, b\\) be real numbers."
        assert site.rules == ("initial",)


def test_m13_rebuilds_the_block_m03_split(spike_content: dict[str, Any]) -> None:
    """M13's block (`segment_block`, M03's `block_of` over the stored segment) splits into exactly
    the stored sentences: the two Docs are the same by construction."""
    checked = 0
    for page in spike_content.values():
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
        return BindingSite(
            mention, "x", sentence, ScopeExtent.SECTION, sentence, start, end, (), reopen
        )

    earlier = site(5, 5, 90)
    same_first = site(20, 20, 60, reopen=True)
    same_second = site(20, 20, 50, reopen=True)
    outside_self = site(30, 31, 32)
    sites = [earlier, same_first, same_second, outside_self]
    got = _site_assignments(sites, [4, 5, 20, 30, 31, 32, 50, 90])
    assert got == {
        5: earlier,
        20: same_second,
        30: outside_self,
        31: outside_self,
        32: same_second,
        50: same_first,
    }
    reopened = _with_reopens(sites)
    assert reopened[1].reopens is earlier
    assert reopened[2].reopens is earlier
