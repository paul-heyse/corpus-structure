"""M01 on small HTML fixtures, one per D1 §3.1 convention (ingest and math §6 P0-I-1a), with the
package's revealing failure cases."""

from __future__ import annotations

from typing import Any

import pytest

from corpus_structure.core.evidence import (
    MacroDef,
    Segment,
    content_digest,
    rendition_key,
    segment_key,
)
from corpus_structure.core.payloads import AuthorMarkupPayload, SynthesizedClaim
from corpus_structure.core.values import EntityRef
from corpus_structure.core.vocab import DelimitingStatus, MarkupKind, SegmentKind, StatementKind
from corpus_structure.ingest import delimit
from corpus_structure.ingest.html import IngestRefused, IngestResult, build_rendition
from corpus_structure.ingest.profile import CompiledProfile
from corpus_structure.ingest.sentences import SentenceConfig

K = SegmentKind
SOURCE = "siegrist_random/random/test/Page.html"
DIAGNOSTIC_ATTRS = {"sourceline", "tag", "sid", "roles"}


def page(body: str, head: str = "") -> bytes:
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>t</title>'
        f"{head}</head><body>{body}</body></html>"
    ).encode()


def run(profile: CompiledProfile, body: str, source_uri: str = SOURCE) -> IngestResult:
    return build_rendition(page(body), profile, SentenceConfig(), source_uri=source_uri)


def segments(result: IngestResult, kind: SegmentKind | None = None) -> list[Segment]:
    return [s for s in result.content.document.walk() if kind is None or s.kind is kind]


def value(payload: AuthorMarkupPayload, key: str) -> Any:
    assert isinstance(payload.value, dict)
    return payload.value[key]


def texts(result: IngestResult, kind: SegmentKind) -> list[str]:
    return [result.content.text(s) for s in segments(result, kind)]


def attr(segment: Segment, key: str) -> Any:
    """An attribute as plain JSON data (attrs are typed `JsonValue`)."""
    return segment.attrs.get(key)


def test_an_empty_reference_link_renders_the_units_ordinal(profile: CompiledProfile) -> None:
    r = run(
        profile,
        '<div class="unit" id="u1"><p>One.</p></div><div class="unit" id="u2"><p>'
        'By <a class="ref" href="#u1"></a>, and <a class="ref" href="#nowhere"></a>,'
        " it holds.</p></div>",
    )
    assert texts(r, K.PARAGRAPH)[1] == "By [1], and , it holds."
    paragraph = segments(r, K.PARAGRAPH)[1]
    refs = [m for m in attr(paragraph, "markup") if m["markup"] == "ref"]
    assert [(m["rendered"], m["href"]) for m in refs] == [("[1]", "#u1"), ("", "#nowhere")]
    start = paragraph.start + 3
    assert (refs[0]["start"], refs[0]["end"]) == (start, start + 3)
    links = [d.payload for d in r.markup if d.payload.markup is MarkupKind.LINK]
    assert [(p.target, value(p, "rendered")) for p in links] == [("#u1", True), ("#nowhere", True)]


def test_q_content_stands_between_quotation_marks(profile: CompiledProfile) -> None:
    r = run(profile, "<p>The <q>location</q> parameter.</p>")
    assert texts(r, K.PARAGRAPH) == ["The “location” parameter."]
    (quote,) = attr(segments(r, K.PARAGRAPH)[0], "markup")
    assert (quote["markup"], quote["start"], quote["end"]) == ("quote", 4, 14)


def test_an_ordered_sub_list_item_starts_with_its_marker(profile: CompiledProfile) -> None:
    r = run(
        profile,
        '<ol class="sub" start="3"><li>first</li><li>second</li></ol><ol><li>plain</li></ol>',
    )
    assert texts(r, K.LIST_ITEM) == ["(c) first", "(d) second", "plain"]
    assert texts(r, K.LIST) == ["(c) first\n(d) second", "plain"]
    marker = attr(segments(r, K.LIST_ITEM)[0], "markup")
    assert marker == [{"markup": "list_marker", "start": 0, "end": 4}]
    assert segments(r, K.LIST)[0].attrs == {"classes": ["sub"], "start": "3"}


def test_with_the_document_key_markup_names_its_segments_by_key(profile: CompiledProfile) -> None:
    body = (
        '<div class="unit" id="t1"><p class="math">A <dfn>theorem</dfn>.</p><details>'
        "<summary>Proof:</summary><p>Clear.</p></details></div>"
    )
    doc = "doc:0123456789abcdef0123456789abcdef"
    r = build_rendition(page(body), profile, SentenceConfig(), source_uri=SOURCE, document_key=doc)
    ren = rendition_key(doc, content_digest(r.content))
    keys = {segment_key(ren, s.kind, s.start, s.end): s for s in segments(r)}
    for d in r.markup:
        assert value(d.payload, "segment") == segment_key(ren, *d.segment)
    (details,) = [d.payload for d in r.markup if d.payload.markup is MarkupKind.DETAILS]
    unit = value(details, "unit")
    assert unit["locator"] == "test/Page.html#t1"
    assert keys[unit["segment"]].kind is K.UNIT
    plain = run(profile, body)  # without the key: the content is the same, no segment keys
    assert plain.content == r.content
    assert all("segment" not in value(d.payload, "unit") for d in plain.markup
               if d.payload.markup is MarkupKind.DETAILS)  # fmt: skip


def test_a_details_summary_is_a_heading_and_its_kind_is_declared(profile: CompiledProfile) -> None:
    r = run(
        profile,
        '<div class="unit" id="t1"><p class="math">A theorem.</p><details>'
        "<summary>Proof:</summary><p>Clear.</p></details></div>"
        '<h3>Computational Exercises</h3><div class="unit" id="e1"><p class="exercise">'
        "Compute.</p><details><summary>Details:</summary><p>Done.</p></details>"
        "<details><summary>Notes:</summary><p>Aside.</p></details></div>",
    )
    (details, _, _) = segments(r, K.DETAILS)
    assert [
        (k, r.content.text(c))
        for c in details.children
        for k in [c.kind]
        if c.kind is not K.SENTENCE
    ] == [(K.HEADING, "Proof:"), (K.PARAGRAPH, "Clear.")]
    drafts = [d for d in r.markup if d.payload.markup is MarkupKind.DETAILS]
    kinds = [value(d.payload, "statement_kind") for d in drafts]
    assert kinds == ["proof", "solution", "remark"]
    claim = drafts[0].payload.synthesize
    assert isinstance(claim, SynthesizedClaim) and isinstance(claim.object, EntityRef)
    assert claim.predicate == "core:proves"
    assert claim.object.ref == "test/Page.html#t1"
    (evidence,) = claim.evidence
    assert r.content.canonical_text[evidence.start : evidence.end] == "Proof:"
    assert "synthesize" not in drafts[2].payload.model_dump()  # remark declares no claim


def test_text_placed_directly_in_a_container_is_an_orphan_paragraph(
    profile: CompiledProfile,
) -> None:
    r = run(
        profile,
        '<div class="unit"><p>Let</p>\\[ x = 1 \\]<details><summary>Proof</summary>'
        "bare text</details></div>",
    )
    orphans = [s for s in segments(r, K.PARAGRAPH) if s.attrs.get("orphan")]
    assert [(r.content.text(s), s.attrs["container"]) for s in orphans] == [
        ("\\[ x = 1 \\]", "unit"),
        ("bare text", "details"),
    ]
    assert [c.kind for c in orphans[0].children] == [K.MATH_DISPLAY, K.SENTENCE]
    assert [o.container for o in r.parse_detail.orphans] == ["unit", "details"]


def test_a_bare_display_environment_is_display_math(profile: CompiledProfile) -> None:
    r = run(
        profile,
        "<p>So \\begin{align} a &amp;= b \\\\\n  c &amp;= d \\end{align} holds.</p>"
        "<p>\\begin{align*} e</p>",
    )
    first, second = segments(r, K.MATH_DISPLAY)
    assert r.content.text(first) == "\\begin{align} a &= b \\\\\n  c &= d \\end{align}"
    assert first.attrs == {"open": "\\begin{align}", "close": "\\end{align}"}
    assert (second.parse_status, second.parse_reason) == ("partial", "unclosed \\begin{align*}")


@pytest.mark.parametrize(
    ("html", "reasons"),
    [
        ("<p>where \\( x</p>", ["unclosed at block end"]),
        ("<p>where \\( x and \\[ y \\]</p>", ["unclosed \\( before next opener", None]),
        ("<p>where \\[ x \\) more</p>", ["\\[ closed by \\)"]),
    ],
)
def test_each_unbalanced_delimiter_makes_its_span_partial_with_the_reason(
    profile: CompiledProfile, html: str, reasons: list[str | None]
) -> None:
    r = run(profile, html)
    math = [s for s in segments(r) if s.kind in (K.MATH_INLINE, K.MATH_DISPLAY)]
    assert [s.parse_reason for s in math] == reasons
    assert [s.parse_status for s in math] == ["ok" if x is None else "partial" for x in reasons]
    assert segments(r, K.PARAGRAPH)[0].parse_status is DelimitingStatus.OK


def test_a_stray_closer_is_recorded_in_parse_detail(profile: CompiledProfile) -> None:
    r = run(profile, "<p>an x \\) stray and \\\\[2pt] a line break</p>")
    assert not [s for s in segments(r) if s.kind in (K.MATH_INLINE, K.MATH_DISPLAY)]
    (anomaly,) = r.parse_detail.math_anomalies
    assert (anomaly.kind, anomaly.delimiter) == ("stray closer", "\\)")


def test_a_delimiter_scan_timeout_makes_the_block_partial(
    profile: CompiledProfile, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(delimit, "SCAN_TIMEOUT", 1e-4)
    r = run(profile, "<p>\\begin{align} " + "x " * 400_000 + "</p><p>fine \\( y \\)</p>")
    slow, fine = segments(r, K.PARAGRAPH)
    assert (slow.parse_status, slow.parse_reason) == ("partial", delimit.TIMEOUT_REASON)
    assert not [c for c in slow.children if c.kind is K.MATH_DISPLAY]
    monkeypatch.setattr(delimit, "SCAN_TIMEOUT", 2.0)
    assert fine.parse_status == "ok"


def test_the_macro_reader_takes_renewcommand_and_its_kin(profile: CompiledProfile) -> None:
    r = run(
        profile,
        '<div class="latex">\\(\\newcommand{\\R}{\\mathbb{R}} \\renewcommand{\\P}'
        "{\\mathbb{P}} \\newcommand*{\\bs}[2][x]{\\boldsymbol{#1}_{#2}} "
        "\\newcommand{\\R}{\\mathbf{R}} \\providecommand{\\R}{no} "
        "\\DeclareMathOperator*{\\argmax}{arg\\,max}\\)</div><p>Text.</p>",
    )
    assert r.content.macros == {
        "\\R": MacroDef(body="\\mathbb{R}"),
        "\\P": MacroDef(body="\\mathbb{P}"),
        "\\bs": MacroDef(nargs=2, default="x", body="\\boldsymbol{#1}_{#2}"),
        "\\argmax": MacroDef(body="\\operatorname*{arg\\,max}"),
    }
    notes = r.parse_detail.macro_notes
    assert notes == (
        "\\P: \\renewcommand without a prior definition on the page",
        "\\R redefined by \\newcommand (TeX error; the first is kept)",
    )
    assert texts(r, K.PARAGRAPH) == ["Text."]  # the macro block is excluded
    assert [e.rule for e in r.parse_detail.exclusions] == ["macro_block"]


def test_a_non_unit_div_is_transparent(profile: CompiledProfile) -> None:
    r = run(
        profile,
        '<div class="box"><p>inside</p>loose text</div><blockquote><p>quoted</p></blockquote>',
    )
    top = [(c.kind, r.content.text(c), c.attrs) for c in r.content.document.children]
    assert top == [
        (K.PARAGRAPH, "inside", {}),
        (K.PARAGRAPH, "loose text", {"orphan": True, "container": "document"}),
        (K.PARAGRAPH, "quoted", {}),
    ]


def test_an_empty_element_yields_no_segment(profile: CompiledProfile) -> None:
    """IR-13: an empty segment's only locator is positional, which an earlier insertion moves."""
    r = run(
        profile,
        '<p></p><p> \n </p><ul><li></li><li> </li></ul><div class="unit" id="e">'
        "<p></p></div><details><summary></summary></details><h3> </h3><p>Text.</p>",
    )
    assert [(s.kind, r.content.text(s)) for s in segments(r)] == [
        (K.DOCUMENT, "Text."),
        (K.PARAGRAPH, "Text."),
        (K.SENTENCE, "Text."),
    ]
    assert all(s.end > s.start for s in segments(run(profile, "<p></p>")) if s.kind != K.DOCUMENT)


def test_an_unclosed_p_before_details_is_closed_by_the_parser(profile: CompiledProfile) -> None:
    """html5lib closes the paragraph; libxml2 would nest the proof inside it (4 Siegrist pages)."""
    r = run(
        profile,
        '<div class="unit"><p class="math">The theorem.<details><summary>Proof'
        "</summary><p>Easy.</p></details></div>",
    )
    (unit,) = segments(r, K.UNIT)
    assert [c.kind for c in unit.children] == [K.PARAGRAPH, K.DETAILS]
    assert texts(r, K.PARAGRAPH)[0] == "The theorem."


def test_hints_are_core_members_and_a_section_hint_keeps_the_block_hint(
    profile: CompiledProfile,
) -> None:
    r = run(
        profile,
        '<div class="unit" id="d"><p>Lead.</p><p class="dfn">A def.</p></div>'
        '<div class="unit" id="a"><p class="app">An app.</p></div>'
        '<h3>Computational Exercises</h3><h4>Sub</h4><div class="unit" id="x">'
        '<p class="math">A theorem.</p></div>',
    )
    d, a, x = segments(r, K.UNIT)
    assert d.attrs["hint"] == {"selector": "p.dfn", "statement_kind": "definition"}
    assert x.attrs["hint"] == {
        "selector": "section:Computational Exercises",
        "statement_kind": "exercise",
        "block_hint": {"selector": "p.math", "statement_kind": "theorem"},
    }
    assert attr(a, "hint")["claim_bearing"] is False
    for unit in (d, x, a):
        StatementKind(attr(unit, "hint")["statement_kind"])


def test_sections_nest_by_rank_and_carry_their_title(profile: CompiledProfile) -> None:
    r = run(profile, "<h3>One</h3><p>a</p><h4>Two</h4><p>b</p><h3>Three</h3><p>c</p>")
    sections = segments(r, K.SECTION)
    assert [(s.attrs["title"], s.attrs["level"], r.content.text(s)) for s in sections] == [
        ("One", 3, "One\n\na\n\nTwo\n\nb"),
        ("Two", 4, "Two\n\nb"),
        ("Three", 3, "Three\n\nc"),
    ]
    assert [c.kind for c in r.content.document.children] == [K.SECTION, K.SECTION]


def test_entities_are_decoded_once_and_diagnostics_stay_out_of_attrs(
    profile: CompiledProfile,
) -> None:
    r = run(
        profile,
        '<header><h2>The  Title</h2></header><p id="p1" class="x">a &amp;lt; b'
        " &lt; c&nbsp;d</p></foo>",
    )
    assert texts(r, K.PARAGRAPH) == ["a &lt; b < c d"]
    assert r.title == "The Title"
    for s in segments(r):
        assert not DIAGNOSTIC_ATTRS & set(s.attrs)
        assert isinstance(s.kind, SegmentKind) and isinstance(s.parse_status, DelimitingStatus)
    assert r.parse_detail.encoding == "utf-8"
    assert [e.code for e in r.parse_detail.parser_errors] == ["unexpected-end-tag"]


def test_a_document_outside_the_profiles_applies_to_is_refused(profile: CompiledProfile) -> None:
    with pytest.raises(IngestRefused, match="applies_to"):
        run(profile, "<p>x</p>", source_uri="nist/eda/page.htm")
