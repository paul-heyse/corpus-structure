"""M11's grammar part and M09 over a rendition's math spans (ingest and math §3.8, §6 P0-I-2a).

The spike pages' production renditions are the input. M09's offsets are checked against the source
substring of every occurrence: the canonical text at a mention's offsets is the occurrence's text in
the parse input, lies inside its span, and begins and ends on TeX token boundaries of the span.
"""

from __future__ import annotations

from typing import Any

import pytest

from corpus_structure.core import tex
from corpus_structure.core.evidence import MacroDef, RenditionContent, Segment
from corpus_structure.core.keys import symbol_form
from corpus_structure.core.values import Formula, SetValue
from corpus_structure.core.vocab import BindKind, MathKind, ParseOutcome, SegmentKind
from corpus_structure.methods.math.spans import (
    extract,
    formula_values,
    math_spans,
    read_spans,
)

pytestmark = pytest.mark.filterwarnings("error::sympy.utilities.exceptions.SymPyDeprecationWarning")


def rendition(*formulas: str, display: bool = False) -> RenditionContent:
    """A one-paragraph rendition whose math spans are `formulas`, separated by prose."""
    opener, closer = ("\\[", "\\]") if display else ("\\(", "\\)")
    kind = SegmentKind.MATH_DISPLAY if display else SegmentKind.MATH_INLINE
    text, children = "Let ", []
    for formula in formulas:
        span = f"{opener} {formula} {closer}"
        children.append(
            Segment(
                kind=kind,
                start=len(text),
                end=len(text) + len(span),
                attrs={"open": opener, "close": closer},
            )
        )
        text += span + " and "
    paragraph = Segment(
        kind=SegmentKind.PARAGRAPH, start=0, end=len(text), children=tuple(children)
    )
    root = Segment(kind=SegmentKind.DOCUMENT, start=0, end=len(text), children=(paragraph,))
    return RenditionContent(canonical_text=text, document=root)


def test_the_parse_input_excludes_the_delimiter_pair_and_its_whitespace() -> None:
    content = rendition("x + y")
    (span,) = math_spans(content)
    assert span.latex == "x + y"
    assert content.canonical_text[span.offset : span.offset + len(span.latex)] == "x + y"
    assert span.offset == span.segment.start + len("\\( ")


def test_an_unclosed_span_and_an_environment_keep_their_opener() -> None:
    text = "\\begin{align} a & = b \\end{align} then \\[ x"
    env = Segment(
        kind=SegmentKind.MATH_DISPLAY,
        start=0,
        end=33,
        attrs={"open": "\\begin{align}", "close": "\\end{align}"},
    )
    unclosed = Segment(
        kind=SegmentKind.MATH_DISPLAY,
        start=39,
        end=len(text),
        parse_status="partial",
        parse_reason="unclosed at block end",
        attrs={"open": "\\[", "close": None},
    )
    root = Segment(kind=SegmentKind.DOCUMENT, start=0, end=len(text), children=(env, unclosed))
    spans = math_spans(RenditionContent(canonical_text=text, document=root))
    assert [s.latex for s in spans] == ["\\begin{align} a & = b \\end{align}", "\\[ x"]


def test_m09_writes_no_letters_of_an_unknown_arrow() -> None:
    """Revealing case: under the spike's prefix `\\left`, `x \\leftarrow y` read as the product
    `x·arrow·y` and gave the mentions `a`, `r`, `o`, `w`."""
    content = rendition("x \\leftarrow y")
    readings = read_spans(content, {})
    assert readings[0].result.status is ParseOutcome.FAILED
    assert extract(readings).mentions == ()


def test_m11_values() -> None:
    macros = {"\\R": MacroDef(body="\\mathbb{R}")}
    content = rendition(
        "\\R \\setminus \\{0\\}",
        "X_1 + \\sigma^2 e",
        "x +",
        "x_i \\in \\R",
        "f(x) = 2 x, \\quad x \\in [0, 1]",
        "(0, 1)",
    )
    values = formula_values(read_spans(content, macros, ("e",)))
    assert [type(v.value) for v in values] == [
        SetValue,
        Formula,
        Formula,
        Formula,
        Formula,
        Formula,
    ]
    assert [v.value.parse for v in values] == [
        ParseOutcome.OK,
        ParseOutcome.OK,
        ParseOutcome.FAILED,
        ParseOutcome.OK,
        ParseOutcome.OK,
        ParseOutcome.AMBIGUOUS,
    ]
    assert [v.math_kind for v in values] == [
        MathKind.SET,
        MathKind.FORMULA,
        None,
        MathKind.MEMBERSHIP,
        MathKind.LIST,
        None,  # interval or pair: no one kind
    ]
    assert values[1].value.latex == "X_1 + \\sigma^2 e"
    assert set(values[1].value.symbols) == {"X_1", "sigma"}  # the constant e is not free
    assert all(b.bind is BindKind.UNRESOLVED for b in values[1].value.symbols.values())
    assert set(values[3].value.symbols) == {"x_i"}  # the index i is not a symbol of its own
    assert values[2].parse_error == "incomplete"
    assert values[0].parse_error is None


def relations_of(formula: str) -> list[tuple[str, str, str]]:
    content = rendition(formula)
    macros = {"\\R": MacroDef(body="\\mathbb{R}"), "\\P": MacroDef(body="\\mathbb{P}")}
    found = extract(read_spans(content, macros))
    text = content.canonical_text
    return [(r.label, text[slice(*r.head)], text[slice(*r.tail)]) for r in found.relations]


def test_m09_relations() -> None:
    assert relations_of("a, b \\in \\R") == [("in_set", "a", "\\R"), ("in_set", "b", "\\R")]
    assert relations_of("Y = a + b X") == [("equals", "Y", "a + b X")]
    assert relations_of("0 < p \\le 1") == [("compares", "0", "p"), ("compares", "p", "1")]
    assert relations_of("X \\sim N(\\mu, \\sigma^2)") == [("compares", "X", "N(\\mu, \\sigma^2)")]
    assert relations_of("p = \\P(X = 1) \\in [0, 1]") == [
        ("equals", "p", "\\P(X = 1)"),
        ("in_set", "\\P(X = 1)", "[0, 1]"),
    ]
    assert relations_of("f(x) = 2 x, \\quad x \\in [0, 1]") == [
        ("equals", "f(x)", "2 x"),
        ("in_set", "x", "[0, 1]"),
    ]
    assert relations_of("\\P(X = x)") == []  # a condition inside an operator is not the value's
    assert relations_of("x \\notin A") == []


def test_m09_on_the_spike_pages(spike_extraction: dict[str, Any]) -> None:
    checked = 0
    for page in spike_extraction.values():
        text = page.content.canonical_text
        mentions = page.extraction.mentions
        by_span = {(r.span.segment.start, r.span.segment.end): r for r in page.readings}
        assert [m.start for m in mentions] == sorted(m.start for m in mentions)
        for m in mentions:
            reading = by_span[(m.segment.start, m.segment.end)]
            span = reading.span
            local = (m.start - span.offset, m.end - span.offset)
            assert text[m.start : m.end] == span.latex[local[0] : local[1]]  # offsets shifted only
            assert m.segment.start <= m.start < m.end <= m.segment.end
            boundaries = {t.start for t in tex.tokens(text[m.segment.start : m.segment.end])}
            boundaries |= {t.end for t in tex.tokens(text[m.segment.start : m.segment.end])}
            assert m.start - m.segment.start in boundaries and m.end - m.segment.start in boundaries
            assert m.name == tex.token_form(text[m.start : m.end], page.macros)
            checked += 1
        for value in page.values:
            reading = by_span[(value.segment.start, value.segment.end)]
            assert value.value.parse is reading.result.status
            for name in value.value.symbols:
                assert name == symbol_form(name, page.macros)
        for relation in page.extraction.relations:
            assert (
                relation.segment.start
                <= relation.head[0]
                < relation.head[1]
                <= relation.segment.end
            )
            assert (
                relation.segment.start
                <= relation.tail[0]
                < relation.tail[1]
                <= relation.segment.end
            )
    print(f"\nM09: {checked} mentions on the spike pages")
    assert checked > 1000
