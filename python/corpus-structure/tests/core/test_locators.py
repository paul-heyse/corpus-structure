"""Locators (D1 §3.4; ingest and math §3.1, §6 P0-I-0).

Hand-built renditions for every form and refusal, Hypothesis properties over generated pages with
repeated and prefix-related texts, and the four spike pages (thin fixture from the frozen S1
renditions, `tests/data/locators/`).
"""

from __future__ import annotations

import json
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st
from pydantic import JsonValue, ValidationError

from corpus_structure.core.evidence import RenditionContent, Segment, SegmentKind
from corpus_structure.core.locators import (
    Locator,
    LocatorIndex,
    LocatorRefused,
    LocatorSyntaxError,
    annotation_units,
    normalize,
    page_of,
    parse,
    source_uri_of,
)

PAGE = "special/Test.html"
DATA = Path(__file__).resolve().parents[1] / "data" / "locators"
ROOT = "siegrist_random/random"
PARAGRAPH, LIST_ITEM = SegmentKind.PARAGRAPH, SegmentKind.LIST_ITEM


# -- building renditions ---------------------------------------------------------------------


@dataclass(frozen=True)
class B:
    """A block: a leaf with text, or a container of blocks joined by blank lines."""

    kind: str
    body: str | tuple[B, ...]
    attrs: dict[str, JsonValue] = field(default_factory=dict)


def _emit(block: B, start: int) -> tuple[Segment, str]:
    if isinstance(block.body, str):
        end = start + len(block.body)
        segment = Segment(kind=SegmentKind(block.kind), start=start, end=end, attrs=block.attrs)
        return segment, block.body
    children: list[Segment] = []
    parts: list[str] = []
    position = start
    for i, child in enumerate(block.body):
        if i:
            parts.append("\n\n")
            position += 2
        segment, text = _emit(child, position)
        children.append(segment)
        parts.append(text)
        position += len(text)
    text = "".join(parts)
    segment = Segment(
        kind=SegmentKind(block.kind),
        start=start,
        end=start + len(text),
        attrs=block.attrs,
        children=tuple(children),
    )
    return segment, text


def rendition(*blocks: B) -> RenditionContent:
    document, text = _emit(B("document", tuple(blocks)), 0)
    return RenditionContent(canonical_text=text, document=document)


def p(text: str, **attrs: JsonValue) -> B:
    return B("paragraph", text, attrs)


def unit(*blocks: B, **attrs: JsonValue) -> B:
    return B("unit", tuple(blocks), attrs)


def index(*blocks: B) -> LocatorIndex:
    return LocatorIndex(rendition(*blocks), PAGE)


def by_text(idx: LocatorIndex, kind: SegmentKind, text: str) -> list[Segment]:
    return [s for s, _ in idx if s.kind is kind and idx.rendition.text(s) == text]


def strings(idx: LocatorIndex) -> list[str]:
    return [str(locator) for _, locator in idx]


# A page with every form: ids on units and on a paragraph, a duplicated id, a paragraph inside a
# unit, a top-level list, identical and prefix-related paragraphs.
PAGE_BLOCKS = (
    B("heading", "Title"),
    p("Lead in text."),
    B(
        "section",
        (
            B("heading", "First section"),
            unit(p("Suppose that X is real."), B("math_display", "\\[ x  =  1 \\]"), id="dfn1"),
            p("Proof.", id="p1"),
            p("Proof. By induction on n."),
            B("list", (B("list_item", "(a) one"), B("list_item", "(a) one"))),
            unit(p("Proof."), id="dup"),
            p("Other text", id="dup"),
            p("Café latte."),
        ),
    ),
)


@pytest.fixture(scope="module")
def page_index() -> LocatorIndex:
    return index(*PAGE_BLOCKS)


# -- parsing ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected", "canonical"),
    [
        ("special/Normal.html", Locator(page="special/Normal.html"), None),
        ("special/Normal.html#rel1", Locator(page="special/Normal.html", id="rel1"), None),
        (
            "special/Normal.html@p:Suppose again that \\( X \\) has",
            Locator(
                page="special/Normal.html",
                kind=SegmentKind.PARAGRAPH,
                prefix="Suppose again that \\( X \\) has",
            ),
            None,
        ),
        ("x@u[2]:Proof.", Locator(page="x", kind=SegmentKind.UNIT, prefix="Proof.", n=2), None),
        ("x@unit:Proof.", Locator(page="x", kind=SegmentKind.UNIT, prefix="Proof."), "x@u:Proof."),
        ("x@paragraph:a", Locator(page="x", kind=SegmentKind.PARAGRAPH, prefix="a"), "x@p:a"),
        ("x@list_item:(a) If", Locator(page="x", kind=LIST_ITEM, prefix="(a) If"), None),
        ("x@p:a#b@c:d \\(", Locator(page="x", kind=PARAGRAPH, prefix="a#b@c:d \\("), None),
        ("x#a@b:c", Locator(page="x", id="a@b:c"), None),
        ("x@p[12]:", Locator(page="x", kind=SegmentKind.PARAGRAPH, prefix="", n=12), None),
        ("x@p:  two  spaces ", Locator(page="x", kind=PARAGRAPH, prefix="  two  spaces "), None),
    ],
)
def test_parse_forms(text: str, expected: Locator, canonical: str | None) -> None:
    parsed = parse(text)
    assert parsed == expected
    assert str(parsed) == (canonical or text)
    assert parse(str(parsed)) == parsed


@pytest.mark.parametrize(
    ("text", "position", "reason"),
    [
        ("", 0, "empty page"),
        ("#x", 0, "empty page"),
        ("@p:x", 0, "empty page"),
        ("x#", 2, "empty id"),
        ("x#a b", 3, "whitespace in id"),
        ("x@", 2, "expected a segment kind"),
        ("x@P:a", 2, "expected a segment kind"),
        ("x@para:a", 2, "unknown segment kind 'para'"),
        ("x@p", 3, "expected ':'"),
        ("x@p a", 3, "expected ':'"),
        ("x@p[]:a", 4, "expected an ordinal"),
        ("x@p[x]:a", 4, "expected an ordinal"),
        ("x@p[0]:a", 4, "leading zeros"),
        ("x@p[01]:a", 4, "leading zeros"),
        ("x@p[2:a", 5, "expected ']'"),
        ("x@p[2]a", 6, "expected ':'"),
    ],
)
def test_parse_errors_name_the_position(text: str, position: int, reason: str) -> None:
    with pytest.raises(LocatorSyntaxError) as raised:
        parse(text)
    assert raised.value.position == position
    assert reason in raised.value.reason
    assert raised.value.locator == text
    assert f"position {position}" in str(raised.value)


@pytest.mark.parametrize(
    "fields",
    [
        {"page": "x", "id": "a", "kind": SegmentKind.UNIT},
        {"page": "x", "id": "a", "n": 1},
        {"page": "x", "kind": SegmentKind.UNIT},
        {"page": "x", "prefix": "a"},
        {"page": "x", "n": 1},
        {"page": "x", "kind": SegmentKind.UNIT, "prefix": "a", "n": 0},
        {"page": "x", "id": ""},
        {"page": "x", "id": "a b"},
        {"page": ""},
        {"page": "a#b"},
        {"page": "a@b"},
    ],
)
def test_the_model_holds_one_well_formed_form(fields: dict) -> None:
    with pytest.raises(ValidationError):
        Locator(**fields)


def test_structured_form_spells_kinds_in_full_and_never_hashes() -> None:
    doc = "doc:0123"
    assert parse("x").key_form(doc) == {"doc": doc}
    assert parse("x#rel1").key_form(doc) == {"doc": doc, "id": "rel1"}
    assert parse("x@u:A metal rod").key_form(doc) == {
        "doc": doc,
        "kind": "unit",
        "prefix": "A metal rod",
    }
    assert parse("x@p[2]:\n Proof.\n  By ").key_form(doc) == {
        "doc": doc,
        "kind": "paragraph",
        "prefix": "Proof. By",
        "n": 2,
    }
    # Whitespace and NFC variants of one locator share a structured form.
    nfd = unicodedata.normalize("NFD", "x@p:Café  au")
    assert parse(nfd).key_form(doc) == parse("x@paragraph:Café au").key_form(doc)


def test_normalize_collapses_whitespace_and_composes() -> None:
    assert normalize("  a \n\t b  ") == "a b"
    assert normalize("Cafe\u0301") == "Café"
    assert normalize("\\( x  =\n1 \\)") == "\\( x = 1 \\)"
    assert normalize(" \n ") == ""


# -- pages -----------------------------------------------------------------------------------


def test_pages_are_source_uris_less_the_profile_root() -> None:
    uri = "siegrist_random/random/special/Normal.html"
    assert page_of(uri, ROOT) == "special/Normal.html"
    assert page_of(uri, ROOT + "/") == "special/Normal.html"
    assert page_of(uri, "") == uri
    assert source_uri_of("special/Normal.html", ROOT) == uri
    assert source_uri_of(uri, "") == uri


@pytest.mark.parametrize(
    ("uri", "root"),
    [
        ("other/special/Normal.html", ROOT),
        ("siegrist_random/randomness/Normal.html", ROOT),
        ("siegrist_random/random/", ROOT),
        ("siegrist_random/random/a#b.html", ROOT),
        ("siegrist_random/random/a@b.html", ROOT),
    ],
)
def test_a_source_uri_without_a_page_is_refused(uri: str, root: str) -> None:
    with pytest.raises(ValueError):
        page_of(uri, root)


def test_source_uri_of_refuses_an_unrepresentable_page() -> None:
    with pytest.raises(ValueError):
        source_uri_of("a#b", ROOT)


# -- resolution ------------------------------------------------------------------------------


def test_page_selects_the_document(page_index: LocatorIndex) -> None:
    assert page_index.resolve(PAGE) is page_index.rendition.document


def test_id_selects_a_segment_of_any_kind(page_index: LocatorIndex) -> None:
    unit_segment = page_index.resolve(f"{PAGE}#dfn1")
    assert unit_segment.kind is SegmentKind.UNIT
    paragraph = page_index.resolve(parse(f"{PAGE}#p1"))
    assert paragraph.kind is SegmentKind.PARAGRAPH
    assert page_index.rendition.text(paragraph) == "Proof."


def test_an_id_two_segments_carry_is_refused_with_both(page_index: LocatorIndex) -> None:
    with pytest.raises(LocatorRefused) as raised:
        page_index.resolve(f"{PAGE}#dup")
    assert raised.value.reason == "several"
    assert [c.opening for c in raised.value.candidates] == ["Proof.", "Other text"]
    for candidate in raised.value.candidates:
        page_index.resolve(candidate.locator)  # candidates are resolvable locators


def test_an_unknown_id_is_refused(page_index: LocatorIndex) -> None:
    with pytest.raises(LocatorRefused) as raised:
        page_index.resolve(f"{PAGE}#missing")
    assert raised.value.reason == "none"
    assert raised.value.candidates == ()


def test_kind_prefix_includes_paragraphs_inside_units(page_index: LocatorIndex) -> None:
    # The spike restricted `@p:` to paragraphs outside units; D1 §3.4 does not.
    segment = page_index.resolve(f"{PAGE}@p:Suppose that")
    assert page_index.rendition.text(segment) == "Suppose that X is real."


def test_several_without_an_ordinal_are_refused_in_document_order(
    page_index: LocatorIndex,
) -> None:
    with pytest.raises(LocatorRefused) as raised:
        page_index.resolve(f"{PAGE}@p:Proof.")
    assert raised.value.reason == "several"
    assert [c.opening for c in raised.value.candidates] == [
        "Proof.",
        "Proof. By induction on n.",
        "Proof.",
    ]
    assert "refused (several)" in str(raised.value)


def test_an_ordinal_selects_in_document_order(page_index: LocatorIndex) -> None:
    third = page_index.resolve(f"{PAGE}@p[3]:Proof.")
    inside = by_text(page_index, SegmentKind.PARAGRAPH, "Proof.")[1]
    assert third is inside
    assert page_index.resolve(f"{PAGE}@p[1]:Proof.") is page_index.resolve(f"{PAGE}#p1")
    assert page_index.resolve(f"{PAGE}@p[1]:Other") is page_index.resolve(f"{PAGE}@p:Other")


def test_fewer_than_the_ordinal_is_refused(page_index: LocatorIndex) -> None:
    with pytest.raises(LocatorRefused) as raised:
        page_index.resolve(f"{PAGE}@p[4]:Proof.")
    assert raised.value.reason == "fewer than ordinal"
    assert len(raised.value.candidates) == 3


@pytest.mark.parametrize(
    "locator",
    [
        f"{PAGE}@p:Nothing like this",
        f"{PAGE}@p:Proof. By induction on m",  # one character from a paragraph: never a near match
        f"{PAGE}@p:proof.",  # comparison is case-sensitive
        f"{PAGE}@u:Suppose that X is real. \\[ x = 2",
        f"{PAGE}@table:Proof.",  # a kind the page does not hold
        f"{PAGE}@p[2]:Other",
    ],
)
def test_nothing_selected_is_refused(page_index: LocatorIndex, locator: str) -> None:
    with pytest.raises(LocatorRefused) as raised:
        page_index.resolve(locator)
    assert raised.value.reason in {"none", "fewer than ordinal"}
    if raised.value.reason == "none":
        assert raised.value.candidates == ()


def test_prefixes_compare_on_collapsed_nfc_text(page_index: LocatorIndex) -> None:
    longer = by_text(page_index, SegmentKind.PARAGRAPH, "Proof. By induction on n.")[0]
    assert page_index.resolve(f"{PAGE}@p:\n Proof.\n   By  induction ") is longer
    assert page_index.resolve(f"{PAGE}@p:Proof. By ind") is longer  # not on a word boundary
    nfd = unicodedata.normalize("NFD", f"{PAGE}@p:Café")
    assert nfd != unicodedata.normalize("NFC", nfd)
    assert page_index.rendition.text(page_index.resolve(nfd)) == "Café latte."
    display = page_index.resolve(f"{PAGE}@math_display:\\[ x = 1")
    assert page_index.rendition.text(display) == "\\[ x  =  1 \\]"
    unit_segment = page_index.resolve(f"{PAGE}@u:Suppose that X is real. \\[ x = 1")
    assert unit_segment is page_index.resolve(f"{PAGE}#dfn1")


def test_another_page_is_a_caller_error(page_index: LocatorIndex) -> None:
    with pytest.raises(ValueError, match="another page"):
        page_index.resolve("special/Other.html@p:Proof.")


def test_an_edited_page_refuses_instead_of_matching_near() -> None:
    before = index(p("Suppose that X is real."), p("Then Y is real."))
    locator = before.generate(by_text(before, SegmentKind.PARAGRAPH, "Suppose that X is real.")[0])
    after = index(p("Assume that X is real."), p("Then Y is real."))
    with pytest.raises(LocatorRefused) as raised:
        after.resolve(locator)
    assert raised.value.reason == "none"


# -- generation ------------------------------------------------------------------------------


def test_generation_prefers_a_unique_author_id(page_index: LocatorIndex) -> None:
    unit_segment = page_index.resolve(f"{PAGE}#dfn1")
    assert str(page_index.generate(unit_segment)) == f"{PAGE}#dfn1"
    assert page_index.unit_key(unit_segment) == f"{PAGE}#dfn1"


def test_a_shared_id_falls_back_to_a_prefix(page_index: LocatorIndex) -> None:
    other = by_text(page_index, SegmentKind.PARAGRAPH, "Other text")[0]
    assert str(page_index.generate(other)) == f"{PAGE}@p:Other"
    dup_unit = [s for s, _ in page_index if s.attrs.get("id") == "dup" and s.kind.value == "unit"]
    assert str(page_index.generate(dup_unit[0])) == f"{PAGE}@u:Proof."


@pytest.mark.parametrize("value", ["", "a b", "a\tb"])
def test_an_id_no_locator_can_carry_is_never_generated(value: str) -> None:
    idx = index(p("Alpha", id=value), p("Beta"))
    alpha = by_text(idx, SegmentKind.PARAGRAPH, "Alpha")[0]
    assert str(idx.generate(alpha)) == f"{PAGE}@p:Alpha"


def test_the_document_generates_the_bare_page(page_index: LocatorIndex) -> None:
    assert page_index.generate(page_index.rendition.document) == Locator(page=PAGE)


def test_shortest_unique_whole_word_prefix() -> None:
    idx = index(p("Alpha beta gamma"), p("Alpha beta delta"), p("Omega rest"), p("Alphabet"))
    assert strings(idx)[1:] == [
        f"{PAGE}@p:Alpha beta gamma",
        f"{PAGE}@p:Alpha beta delta",
        f"{PAGE}@p:Omega",
        f"{PAGE}@p:Alphabet",
    ]


def test_a_whole_text_opening_another_gets_an_ordinal_over_both() -> None:
    # The revealing case: `Proof.` opens `Proof. By induction…`, so no prefix of the shorter one
    # selects it alone; it gets an ordinal over both, never a prefix that also selects the longer.
    idx = index(p("Proof. By induction on n."), p("Proof."), p("Other"))
    assert strings(idx)[1:] == [
        f"{PAGE}@p:Proof. By",
        f"{PAGE}@p[2]:Proof.",
        f"{PAGE}@p:Other",
    ]
    for segment, locator in idx:
        assert idx.resolve(locator) is segment


def test_identical_texts_are_told_apart_by_ordinal() -> None:
    idx = index(p("Details:"), p("Something else"), p("Details:"), p("Details:"))
    assert strings(idx)[1:] == [
        f"{PAGE}@p[1]:Details:",
        f"{PAGE}@p:Something",
        f"{PAGE}@p[2]:Details:",
        f"{PAGE}@p[3]:Details:",
    ]


def test_a_word_prefix_that_is_a_string_prefix_of_another_is_not_unique() -> None:
    # `a b` is not unique beside `a bc`: the resolver compares strings, so the generator does too.
    # The group prefix is the shortest that selects exactly the group, shorter than the text.
    idx = index(p("a b"), p("a bc"), p("w"))
    assert strings(idx)[1:] == [f"{PAGE}@p[1]:a", f"{PAGE}@p:a bc", f"{PAGE}@p:w"]


def test_the_group_prefix_excludes_segments_outside_the_group() -> None:
    idx = index(p("x y"), p("x z"), p("x y z"))
    assert strings(idx)[1:] == [f"{PAGE}@p[1]:x y", f"{PAGE}@p:x z", f"{PAGE}@p:x y z"]


def test_an_empty_text_gets_an_empty_prefix_and_an_ordinal() -> None:
    idx = index(p("Alpha"), p(""), p(""))
    # Every paragraph starts with the empty text, so the group is all three; Alpha is unique.
    assert strings(idx)[1:] == [f"{PAGE}@p:Alpha", f"{PAGE}@p[2]:", f"{PAGE}@p[3]:"]
    alone = index(p(""))
    assert strings(alone)[1:] == [f"{PAGE}@p:"]
    for idx_ in (idx, alone):
        for segment, locator in idx_:
            assert idx_.resolve(locator) is segment


def test_generated_kinds_use_short_forms_only_for_units_and_paragraphs(
    page_index: LocatorIndex,
) -> None:
    generated = dict(zip(strings(page_index), (s for s, _ in page_index), strict=True))
    assert f"{PAGE}@heading:Title" in generated
    assert f"{PAGE}@list_item[1]:(a)" in generated
    assert f"{PAGE}@list_item[2]:(a)" in generated
    assert f"{PAGE}@math_display:\\[" in generated
    assert f"{PAGE}@section:First" in generated


def test_generate_refuses_a_segment_of_another_rendition(page_index: LocatorIndex) -> None:
    stranger = Segment(kind=SegmentKind.PARAGRAPH, start=0, end=3)
    with pytest.raises(ValueError, match="not a segment of this rendition"):
        page_index.generate(stranger)


def test_an_index_needs_a_representable_page() -> None:
    with pytest.raises(ValueError):
        LocatorIndex(rendition(p("a")), "a#b")


# -- annotation units ------------------------------------------------------------------------


def test_annotation_units_and_uncovered_blocks(page_index: LocatorIndex) -> None:
    result = page_index.annotation_units()
    assert [u.key for u in result.units] == [
        f"{PAGE}@p:Lead",
        f"{PAGE}#dfn1",
        f"{PAGE}#p1",
        f"{PAGE}@p:Proof. By",
        f"{PAGE}@u:Proof.",
        f"{PAGE}@p:Other",
        f"{PAGE}@p:Café",
    ]
    for unit_ in result.units:
        assert unit_.key == str(unit_.locator) == page_index.unit_key(unit_.segment)
        assert page_index.resolve(unit_.key) is unit_.segment
    assert [s.kind for s in result.uncovered] == [SegmentKind.LIST]
    assert annotation_units(page_index.rendition, PAGE) == result


def test_units_inside_lists_or_details_count_but_their_paragraphs_do_not() -> None:
    idx = index(
        B("details", (p("Proof inside details"),)),
        B("list", (B("list_item", "item"),)),
        unit(p("Inside a unit")),
        B("figure", (B("caption", "A caption"),)),
    )
    result = idx.annotation_units()
    assert [u.segment.kind for u in result.units] == [SegmentKind.UNIT]
    assert [s.kind for s in result.uncovered] == [
        SegmentKind.DETAILS,
        SegmentKind.LIST,
        SegmentKind.FIGURE,
    ]


# -- properties ------------------------------------------------------------------------------

WORDS = ("a", "ab", "b", "Proof.", "\\(x\\)", "é", "x")
SEPARATORS = (" ", " ", "  ", "\n")
IDS = (None, None, None, "i1", "i2")

word_lists = st.lists(st.sampled_from(WORDS), max_size=4)


@st.composite
def leaves(draw: st.DrawFn, kinds: Sequence[str] = ("paragraph", "paragraph", "heading")) -> B:
    words = draw(word_lists)
    separator = draw(st.sampled_from(SEPARATORS))
    ident = draw(st.sampled_from(IDS))
    kind = draw(st.sampled_from(kinds))
    return B(kind, separator.join(words), {"id": ident} if ident else {})


@st.composite
def units(draw: st.DrawFn) -> B:
    children = draw(st.lists(leaves(("paragraph", "math_display")), max_size=3))
    ident = draw(st.sampled_from(IDS))
    return B("unit", tuple(children), {"id": ident} if ident else {})


pages = st.lists(st.one_of(leaves(), leaves(), units()), max_size=8)


def check_round_trip(idx: LocatorIndex) -> None:
    for segment, locator in idx:
        assert idx.resolve(locator) is segment
        assert idx.resolve(str(locator)) is segment
        assert idx.resolve(parse(str(locator))) is segment


@given(pages)
def test_generate_then_resolve_is_the_identity(blocks: list[B]) -> None:
    check_round_trip(index(*blocks))


@given(pages)
def test_content_identical_renditions_give_identical_locators(blocks: list[B]) -> None:
    first = rendition(*blocks)
    second = RenditionContent.model_validate_json(first.model_dump_json())
    assert second is not first
    a, b = LocatorIndex(first, PAGE), LocatorIndex(second, PAGE)
    assert strings(a) == strings(b)
    assert [loc.key_form("doc:k") for _, loc in a] == [loc.key_form("doc:k") for _, loc in b]


@given(pages)
def test_structured_forms_never_hold_a_short_kind(blocks: list[B]) -> None:
    full = {kind.value for kind in SegmentKind}
    for _, locator in index(*blocks):
        form = locator.key_form("doc:k")
        if "kind" in form:
            assert form["kind"] in full
            assert form["kind"] not in {"u", "p"}


@given(pages)
def test_generated_prefixes_are_whole_words(blocks: list[B]) -> None:
    idx = index(*blocks)
    for segment, locator in idx:
        if locator.prefix is None:
            continue
        words = normalize(idx.rendition.text(segment)).split()
        counts = [k for k in range(len(words) + 1) if " ".join(words[:k]) == locator.prefix]
        assert counts, (locator, words)
        assert counts[0] >= 1 or not words


def _replace(blocks: list[B], position: int, text: str) -> list[B]:
    edited = list(blocks)
    edited[position] = B(blocks[position].kind, text, blocks[position].attrs)
    return edited


@given(pages, st.data())
def test_an_edit_after_a_prefix_leaves_every_other_locator_unchanged(
    blocks: list[B], data: st.DataObject
) -> None:
    idx = index(*blocks)
    top = idx.rendition.document.children
    eligible = [
        i
        for i, block in enumerate(blocks)
        if block.kind == "paragraph"
        and (loc := idx.generate(top[i])).form == "prefix"
        and loc.n is None
    ]
    assume(eligible)
    chosen = data.draw(st.sampled_from(eligible))
    prefix = idx.generate(top[chosen]).prefix
    assert prefix is not None
    tail = data.draw(word_lists)
    edited_text = " ".join([prefix, *tail]) if prefix else " ".join(tail)
    edited = index(*_replace(blocks, chosen, edited_text))
    check_round_trip(edited)
    before, after = strings(idx), strings(edited)
    edited_position = [segment for segment, _ in idx].index(top[chosen])
    if prefix:  # the edited block keeps its own locator too; an empty prefix grows to one word
        assert after == before
    else:
        del before[edited_position], after[edited_position]
        assert after == before


@given(pages, st.data())
def test_an_edit_inside_a_prefix_moves_only_same_kind_locators_it_touched(
    blocks: list[B], data: st.DataObject
) -> None:
    # D1 §10.3: an edit moves the edited block's locator and can lengthen or shorten the prefix of
    # another block of the same kind. Here: a block whose locator moves is a paragraph whose first
    # word opens the edited paragraph's old or new text.
    idx = index(*blocks)
    top = idx.rendition.document.children
    paragraphs = [i for i, block in enumerate(blocks) if block.kind == "paragraph"]
    assume(paragraphs)
    chosen = data.draw(st.sampled_from(paragraphs))
    new_text = " ".join(data.draw(word_lists))
    edited = index(*_replace(blocks, chosen, new_text))
    check_round_trip(edited)
    old_text = normalize(idx.rendition.text(top[chosen]))
    chosen_identity = (top[chosen].kind, top[chosen].start)
    for (segment, before), (_, after) in zip(idx, edited, strict=True):
        if str(before) == str(after) or (segment.kind, segment.start) == chosen_identity:
            continue
        assert segment.kind is SegmentKind.PARAGRAPH, (before, after)
        words = normalize(idx.rendition.text(segment)).split()
        first = words[0] if words else ""
        assert old_text.startswith(first) or normalize(new_text).startswith(first)


# -- the four spike pages --------------------------------------------------------------------

# D2 §12.2 `trace` and `core12` (copied from the S1 spike's `code/profile/slices.yaml`), with the
# kind each selects.
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
SPIKE_PAGES = (
    "special/LocationScale.html",
    "special/Normal.html",
    "special/LogNormal.html",
    "special/Gamma.html",
)


@pytest.fixture(scope="module")
def spike() -> dict[str, LocatorIndex]:
    indexes: dict[str, LocatorIndex] = {}
    for page in SPIKE_PAGES:
        path = DATA / (page.removesuffix(".html").replace("/", "__") + ".json")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert page_of(data["source_uri"], ROOT) == data["page"] == page
        content = RenditionContent.model_validate(
            {"canonical_text": data["canonical_text"], "document": data["document"]}
        )
        indexes[page] = LocatorIndex(content, page)
    return indexes


def test_the_thirteen_slice_locators_each_select_one_segment(
    spike: dict[str, LocatorIndex],
) -> None:
    assert len(SLICE_LOCATORS) == 13
    for text, kind in SLICE_LOCATORS:
        locator = parse(text)
        idx = spike[locator.page]
        segment = idx.resolve(locator)
        assert segment.kind.value == kind, text
        if locator.id is not None:
            assert segment.attrs["id"] == locator.id
        else:
            assert locator.prefix is not None
            assert normalize(idx.rendition.text(segment)).startswith(normalize(locator.prefix))


def test_every_spike_segment_round_trips(spike: dict[str, LocatorIndex]) -> None:
    for idx in spike.values():
        check_round_trip(idx)


def test_spike_annotation_units(spike: dict[str, LocatorIndex]) -> None:
    uncovered: dict[str, list[str]] = {}
    for page, idx in spike.items():
        result = idx.annotation_units()
        starts = [u.segment.start for u in result.units]
        assert starts == sorted(starts)
        for unit_ in result.units:
            assert idx.resolve(unit_.key) is unit_.segment
        uncovered[page] = [s.kind.value for s in result.uncovered]
    # The plan's open question (ingest and math §3.1): two lists on Normal, a figure on Gamma.
    assert uncovered == {
        "special/LocationScale.html": [],
        "special/Normal.html": ["list", "list"],
        "special/LogNormal.html": [],
        "special/Gamma.html": ["figure"],
    }
    rel1 = spike["special/Normal.html"].resolve("special/Normal.html#rel1")
    assert spike["special/Normal.html"].unit_key(rel1) == "special/Normal.html#rel1"
