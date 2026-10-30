"""The 78 first-pass Siegrist pages (corpus-gated; ingest and math §5 P0-I-1a): S1's structural
invariants, every element text against an independent path, the index counts, S1's `partial`
spans, orphan runs and figures, the macro tables, and locators on every segment.

S1's figures come from the thin fixture `data/s1_corpus.json` (record `s1.corpus-html5lib`); the
counts are compared with the corpus index itself.
"""

from __future__ import annotations

import csv
import itertools
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from lxml.cssselect import CSSSelector

from corpus_structure.core.evidence import Segment
from corpus_structure.core.locators import LocatorIndex
from corpus_structure.core.vocab import DelimitingStatus, SegmentKind, StatementKind
from corpus_structure.ingest.html import (
    IngestResult,
    SegmentRef,
    build_rendition_with_elements,
    parse,
)
from corpus_structure.ingest.profile import CompiledProfile, compile_profile, load_profile
from corpus_structure.ingest.sentences import SentenceConfig

pytestmark = pytest.mark.corpus

K = SegmentKind
REPO = Path(__file__).resolve().parents[4]
CORPUS = REPO / "docs/statistics_corpus"
ROOT = "siegrist_random/random"
S1 = json.loads((Path(__file__).with_name("data") / "s1_corpus.json").read_text(encoding="utf-8"))
COUNTED = ("units", "definition_units", "dfn_terms", "details_blocks", "display_math")


def _index(name: str) -> list[dict[str, str]]:
    with (CORPUS / "index" / name).open(encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


class Page:
    def __init__(self, row: dict[str, str], profile: CompiledProfile) -> None:
        self.row = row
        self.path = row["path"]
        self.raw = (CORPUS / "corpus" / ROOT / self.path).read_bytes()
        self.result: IngestResult
        self.result, self.elements = build_rendition_with_elements(
            self.raw, profile, SentenceConfig(), source_uri=f"{ROOT}/{self.path}"
        )

    @property
    def segments(self) -> list[Segment]:
        return list(self.result.content.document.walk())


@pytest.fixture(scope="module")
def pages() -> list[Page]:
    profile = compile_profile(load_profile("siegrist"))
    rows = [r for r in _index("siegrist_sections.tsv") if r["first_pass"] == "yes"]
    assert len(rows) == S1["pages"] == 78
    return [Page(r, profile) for r in rows]


def test_the_structural_invariants_hold(pages: list[Page]) -> None:
    for page in pages:
        for segment in page.segments:
            assert segment.end > segment.start or segment.kind is K.DOCUMENT, (page.path, segment)
            assert isinstance(segment.parse_status, DelimitingStatus)
            blocks = [c for c in segment.children if c.kind is not K.SENTENCE]
            sentences = [c for c in segment.children if c.kind is K.SENTENCE]
            for group in (blocks, sentences):
                for a, b in itertools.pairwise(group):
                    assert a.end <= b.start, (page.path, a, b)
            hint = attr(segment, "hint")
            if hint is not None:
                StatementKind(hint["statement_kind"])


def attr(segment: Segment, key: str) -> Any:
    return segment.attrs.get(key)


def _insertions(segment: Segment) -> list[tuple[int, int]]:
    return [
        (m["start"], m["end"])
        for s in segment.walk()
        for m in attr(s, "markup") or []
        if m["markup"] in ("ref", "list_marker")
    ]


def test_every_element_text_equals_an_independent_path(pages: list[Page]) -> None:
    """Each element's XPath `string(.)`, after removing the profile's exclusions found through the
    cssselect→XPath export on a fresh parse, equals its segment's text without the rendered
    insertions, whitespace removed."""
    profile = load_profile("siegrist")
    checked = 0
    mismatches: list[tuple[str, str, str, str]] = []
    for page in pages:
        root, _ = parse(page.raw)
        ours = next(iter(page.elements.values())).getroottree()
        located = {
            ref: root.xpath(ours.getpath(el))[0]
            for ref, el in page.elements.items()
            if ref.kind is not K.SECTION
        }
        for rule in profile.exclude:
            for el in CSSSelector(rule.selector, translator="html")(root):
                parent = el.getparent()
                if parent is None:
                    continue
                previous = el.getprevious()
                if previous is not None:
                    previous.tail = (previous.tail or "") + (el.tail or "")
                else:
                    parent.text = (parent.text or "") + (el.tail or "")
                parent.remove(el)
        by_ref = {SegmentRef.of(s): s for s in page.segments}
        text = page.result.content.canonical_text
        for ref, el in located.items():
            segment = by_ref[ref]
            cut = _insertions(segment)
            kept = "".join(
                c
                for i, c in enumerate(text[segment.start : segment.end], segment.start)
                if not any(a <= i < b for a, b in cut)
            )
            actual = re.sub(r"\s+", "", kept.replace("“", "").replace("”", ""))
            expected = re.sub(r"\s+", "", unicodedata.normalize("NFC", el.xpath("string(.)")))
            checked += 1
            if actual != expected:
                mismatches.append((page.path, ref[0], expected[:80], actual[:80]))
    assert mismatches == []
    assert checked == S1["independent_texts_checked"]


def _hint_selectors(unit: Segment) -> set[str]:
    hint = attr(unit, "hint") or {}
    found = {hint.get("selector"), (hint.get("block_hint") or {}).get("selector")}
    return {selector for selector in found if selector is not None}


def test_the_counts_equal_the_index_on_77_of_78_pages(pages: list[Page]) -> None:
    terms: dict[str, Counter[str]] = {}
    for row in _index("siegrist_defined_terms.tsv"):
        terms.setdefault(row["path"], Counter())[" ".join(row["term"].split())] += 1
    differing = []
    for page in pages:
        segments = page.segments
        units = [s for s in segments if s.kind is K.UNIT]
        text = page.result.content.canonical_text
        dfn = [
            text[m["start"] : m["end"]]
            for s in segments
            for m in attr(s, "markup") or []
            if m["markup"] == "dfn"
        ]
        ours = {
            "units": len(units),
            "definition_units": sum("p.dfn" in _hint_selectors(u) for u in units),
            "dfn_terms": len(dfn),
            "details_blocks": sum(s.kind is K.DETAILS for s in segments),
            "display_math": sum(
                s.kind is K.MATH_DISPLAY and s.attrs.get("open") == "\\[" for s in segments
            ),
        }
        if any(ours[k] != int(page.row[k]) for k in COUNTED):
            differing.append(page.path)
        assert Counter(" ".join(t.split()) for t in dfn) == terms.get(page.path, Counter()), (
            page.path
        )
    assert differing == S1["index_count_exceptions"] == ["special/ExponentialLogarithmic.html"]


def test_eight_math_spans_are_partial_each_with_its_reason(pages: list[Page]) -> None:
    partial = []
    strays = []
    for page in pages:
        text = page.result.content.canonical_text
        for s in page.segments:
            if s.kind in (K.MATH_INLINE, K.MATH_DISPLAY) and s.parse_status != "ok":
                partial.append(
                    {
                        "page": page.path,
                        "reason": s.parse_reason,
                        "opening": text[s.start : s.end][:40],
                    }
                )
            elif s.parse_status != "ok":
                pytest.fail(f"{page.path}: a {s.kind} segment is {s.parse_status}")
        strays += [
            {"page": page.path, "delimiter": a.delimiter}
            for a in page.result.parse_detail.math_anomalies
        ]
    assert len(partial) == 8
    assert partial == S1["partial_math"]
    assert strays == S1["stray_closers"]


def test_orphan_runs_and_figures(pages: list[Page]) -> None:
    orphans = Counter(o.container for p in pages for o in p.result.parse_detail.orphans)
    assert dict(orphans) == S1["orphans_by_container"] and orphans.total() == 44
    marked = sum(bool(s.attrs.get("orphan")) for p in pages for s in p.segments)
    assert marked == 44
    assert sum(s.kind is K.FIGURE for p in pages for s in p.segments) == S1["figures"] == 51
    for p in pages:
        for figure in (s for s in p.segments if s.kind is K.FIGURE):
            assert any(c.kind is K.CAPTION for c in figure.children)


def test_the_macro_tables_hold_p_on_the_22_renewcommand_pages(pages: list[Page]) -> None:
    renewed = [
        p
        for p in pages
        if "\\P: \\renewcommand without a prior definition on the page"
        in p.result.parse_detail.macro_notes
    ]
    assert len(renewed) == 22
    for p in renewed:
        assert p.result.content.macros["\\P"].body == "\\mathbb{P}"
    # Without those 22, the tables are S1's pylatexenc tables, definition by definition.
    definitions: Counter[str] = Counter()
    for p in pages:
        for name, m in p.result.content.macros.items():
            if p in renewed and name == "\\P":
                continue
            assert m.default is None
            definitions[f"{name} -> {m.body} ({m.nargs})"] += 1
    assert dict(definitions) == S1["macro_definitions"]


def test_no_segment_is_empty_and_locators_round_trip(pages: list[Page]) -> None:
    for page in pages:
        index = LocatorIndex(page.result.content, page.result.page)
        for segment, locator in index:
            if segment.kind is not K.DOCUMENT:
                assert segment.end > segment.start, (page.path, segment.kind)
            assert index.resolve(locator) is segment, (page.path, str(locator))


def test_parse_detail_records_the_parser(pages: list[Page]) -> None:
    assert {p.result.parse_detail.encoding for p in pages} == {"utf-8"}
    assert sum(len(p.result.parse_detail.parser_errors) for p in pages) == 17
    assert sum(p.result.parse_detail.data_loss_warnings for p in pages) == 2
    assert all(p.result.parse_detail.role_conflicts == () for p in pages)


def test_corpus_source_products_reach_the_trusted_partition_and_origin_boundary(
    pages: list[Page],
) -> None:
    from corpus_structure.semantic.parsing_products import prepare_parsing_product

    for page in pages:
        product = page.result.parsing_product
        assert product is not None, page.path
        prepared = prepare_parsing_product(product.values(), product.original)
        assert prepared.original == page.raw, page.path
        values = prepared.values()
        assert values["provenance_universe"] == "canonical_output", page.path
        assert values["provenance_state"] == "complete", page.path
