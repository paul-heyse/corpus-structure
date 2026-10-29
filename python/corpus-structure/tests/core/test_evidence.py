"""Evidence types, the content digest and the doc/ren/seg/cfg keys (D1 §3, §10.1)."""

from __future__ import annotations

import hashlib
import re
from typing import Any

import pytest
from pydantic import ValidationError

from corpus_structure.core.canonical import CanonicalJsonError
from corpus_structure.core.evidence import (
    MacroDef,
    RenditionContent,
    Segment,
    SegmentKind,
    config_key,
    content_digest,
    document_key,
    rendition_key,
    segment_key,
)

TEXT = "Let \\(X\\) be real. It is.\n\nNext."


def seg(kind: str, start: int, end: int, *children: Segment, **extra: Any) -> Segment:
    return Segment(kind=SegmentKind(kind), start=start, end=end, children=children, **extra)


def content(
    text: str = TEXT,
    order: int = 1,
    paragraph_attrs: dict | None = None,
    math_status: tuple[str, str | None] = ("ok", None),
    macro_body: str = "\\mathbb{R}",
    math_kind: str = "math_inline",
    second_end: int = 32,
) -> RenditionContent:
    status, reason = math_status
    math = seg(math_kind, 4, 9, parse_status=status, parse_reason=reason)
    sentences = [seg("sentence", 0, 18, math), seg("sentence", 19, 25)]
    first = seg(
        "paragraph",
        0,
        25,
        *(sentences if order == 1 else reversed(sentences)),
        attrs=paragraph_attrs or {"id": "p1"},
    )
    second = seg("paragraph", 27, second_end)
    blocks = (first, second) if order == 1 else (second, first)
    return RenditionContent(
        canonical_text=text,
        document=seg("document", 0, len(text), *blocks),
        macros={"\\R": MacroDef(body=macro_body)},
    )


def test_text_offsets_are_code_points() -> None:
    c = content()
    math = c.document.children[0].children[0].children[0]
    assert c.text(math) == "\\(X\\)"
    assert len(TEXT) == 32


def test_children_sorted_so_construction_order_does_not_matter() -> None:
    a, b = content(order=1), content(order=2)
    assert a == b
    assert content_digest(a) == content_digest(b)
    # siblings that overlap: start, then the longer first, then kind
    p = seg("paragraph", 0, 10, seg("sentence", 0, 5), seg("math_inline", 0, 5), seg("unit", 0, 10))
    assert [c.kind.value for c in p.children] == ["unit", "math_inline", "sentence"]


def test_digest_of_a_minimal_content_covers_exactly_the_model() -> None:
    minimal = RenditionContent(canonical_text="ab", document=seg("document", 0, 2))
    # defaults are left out, so a defaulted field added later moves no digest
    expected = b'{"canonical_text":"ab","document":{"end":2,"kind":"document","start":0}}'
    assert content_digest(minimal) == hashlib.sha256(expected).hexdigest()


@pytest.mark.parametrize(
    "change",
    [
        {"text": TEXT.replace("real", "rial")},
        {"second_end": 31},
        {"math_kind": "math_display"},
        {"math_status": ("partial", "unclosed at block end")},
        {"paragraph_attrs": {"id": "p2"}},
        {"paragraph_attrs": {"id": "p1", "class": ["thm"]}},
        {"macro_body": "\\mathbf{R}"},
    ],
)
def test_digest_changes_with_any_one_change(change: dict) -> None:
    assert content_digest(content(**change)) != content_digest(content())


def test_parse_status_is_derived_and_not_in_the_digest() -> None:
    assert content().parse_status == "ok"
    partial = content(math_status=("partial", "unclosed at block end"))
    assert partial.parse_status == "partial"
    assert "parse_status" not in partial.model_dump()
    failed = RenditionContent(
        canonical_text="ab",
        document=seg("document", 0, 2, seg("paragraph", 0, 1, parse_status="failed",
                                            parse_reason="x")),
    )  # fmt: skip
    assert failed.parse_status == "failed"


@pytest.mark.parametrize(
    ("build", "message"),
    [
        (lambda: seg("paragraph", 5, 4), "start_offset 5 > end_offset 4"),
        (lambda: seg("paragraph", 0, 4, seg("sentence", 2, 6)), "outside its parent"),
        (lambda: seg("paragraph", 0, 4, parse_reason="x"), "parse_reason is absent exactly when"),
        (lambda: seg("paragraph", 0, 4, parse_status="partial"), "parse_reason is absent exactly"),
        (lambda: seg("paragraph", -1, 4), "greater than or equal"),
        (lambda: Segment(kind="para", start=0, end=1), "Input should be"),
        (lambda: seg("paragraph", 0, 1, diagnostics={}), "Extra inputs"),
        (lambda: MacroDef(body="x", default="y"), "at least one argument"),
        (lambda: MacroDef.model_validate({"nargs": 10, "body": "x"}), "less than or equal"),
    ],
)
def test_segment_and_macro_refusals(build, message: str) -> None:
    with pytest.raises(ValidationError, match=re.escape(message)):
        build()


# The model's KbSegment invariant, written out: parse_reason is absent (None) exactly when the
# status is ok, and a present reason is never empty or only whitespace (its pattern '\S', P0-M-2),
# as M2's CHECKs read them.
SEGMENT_STATUS = [
    ("ok", None, True), ("ok", "", False), ("ok", "x", False),
    ("partial", None, False), ("partial", "", False), ("partial", "unclosed at block end", True),
    ("failed", None, False), ("failed", " ", False), ("failed", "no closing delimiter", True),
]  # fmt: skip


@pytest.mark.parametrize(("status", "reason", "accepted"), SEGMENT_STATUS)
def test_a_segment_accepts_what_the_model_declares(status, reason, accepted: bool) -> None:
    def build() -> Segment:
        return seg("math_inline", 4, 9, parse_status=status, parse_reason=reason)

    if accepted:
        assert build().parse_reason == reason
    else:
        with pytest.raises(
            ValidationError, match=r"parse_reason is absent exactly when|does not match '\\\\S'"
        ):
            build()
    assert seg("math_inline", 4, 4).start == 4  # ordered_eq: an empty range is a segment


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"canonical_text": "ab", "document": seg("paragraph", 0, 2)}, "not document"),
        ({"canonical_text": "ab", "document": seg("document", 0, 3)}, "does not span"),
        ({"canonical_text": "ab", "document": seg("document", 0, 1)}, "does not span"),
        ({"canonical_text": "é", "document": seg("document", 0, 2)}, "NFC"),
        (
            {
                "canonical_text": "abc",
                "document": seg("document", 0, 3, seg("paragraph", 0, 3, seg("paragraph", 0, 3))),
            },
            "share a segment key",
        ),
        (
            {
                "canonical_text": "ab",
                "document": seg("document", 0, 2),
                "macros": {"R": MacroDef(body="x")},
            },
            "not a control word",
        ),
    ],
)
def test_rendition_refusals(kwargs: dict, message: str) -> None:
    with pytest.raises(ValidationError, match=re.escape(message)):
        RenditionContent(**kwargs)


def test_models_are_frozen() -> None:
    c = content()
    with pytest.raises(ValidationError):
        c.canonical_text = "x"
    with pytest.raises(ValidationError):
        c.document.children[0].start = 3


def test_round_trip_through_json() -> None:
    c = content(math_status=("partial", "unclosed at block end"))
    again = RenditionContent.model_validate_json(c.model_dump_json())
    assert again == c and content_digest(again) == content_digest(c)


def test_keys() -> None:
    doc = document_key("statistics", "siegrist/Prob/Prob2.html", "ab" * 32)
    assert re.fullmatch(r"doc:[0-9a-f]{32}", doc)
    assert doc != document_key("statistics2", "siegrist/Prob/Prob2.html", "ab" * 32)
    ren = rendition_key(doc, content_digest(content()))
    assert ren.startswith("ren:") and ren != rendition_key(doc, content_digest(content(order=2,
        macro_body="x")))  # fmt: skip
    s1 = segment_key(ren, SegmentKind.PARAGRAPH, 0, 26)
    assert s1.startswith("seg:")
    assert s1 == segment_key(ren, "paragraph", 0, 26)
    assert s1 != segment_key(ren, SegmentKind.SENTENCE, 0, 26)
    assert s1 != segment_key(ren, SegmentKind.PARAGRAPH, 0, 25)
    with pytest.raises(ValueError):
        segment_key(ren, "para", 0, 26)
    cfg = config_key("M01", "0.1.0", {"profile": "siegrist", "threshold": "0.5"})
    assert cfg.startswith("cfg:")
    assert cfg == config_key("M01", "0.1.0", {"threshold": "0.5", "profile": "siegrist"})
    assert cfg != config_key("M01", "0.1.1", {"profile": "siegrist", "threshold": "0.5"})


def test_a_float_in_a_configuration_never_hashes() -> None:
    with pytest.raises(CanonicalJsonError, match=r"\$\.params\.threshold: float"):
        config_key("M01", "0.1.0", {"threshold": 0.5})


@pytest.mark.parametrize("name", ["\\|", "\\,", "R", "\\R1"])
def test_macro_names_are_control_words(name: str) -> None:
    with pytest.raises(ValidationError, match="not a control word"):
        RenditionContent(canonical_text="ab", document=seg("document", 0, 2),
                         macros={name: MacroDef(body="x")})  # fmt: skip


@pytest.mark.parametrize("bad", ["0", 0.0, True])
def test_offsets_are_strict_integers(bad: object) -> None:
    with pytest.raises(ValidationError):
        Segment.model_validate({"kind": "paragraph", "start": bad, "end": 1})


@pytest.mark.parametrize(
    "attrs", [{"w": 1.5}, {"w": [1, {"x": float("nan")}]}, {"e\u0301": 1, "\u00e9": 2}]
)
def test_attrs_are_refused_at_validation_when_not_canonical_json(attrs: dict) -> None:
    with pytest.raises(ValidationError, match="not canonical JSON"):
        seg("paragraph", 0, 1, attrs=attrs)


def test_a_defaulted_field_given_explicitly_digests_alike() -> None:
    implicit = RenditionContent(canonical_text="ab", document=seg("document", 0, 2))
    explicit = RenditionContent(
        canonical_text="ab",
        document=seg("document", 0, 2, parse_status="ok", parse_reason=None, attrs={}),
        macros={},
    )
    assert content_digest(implicit) == content_digest(explicit)
    partial = RenditionContent(
        canonical_text="ab",
        document=seg("document", 0, 2, seg("paragraph", 0, 1, parse_status="partial",
                                            parse_reason="unclosed at block end")),
    )  # fmt: skip
    plain = RenditionContent(
        canonical_text="ab", document=seg("document", 0, 2, seg("paragraph", 0, 1))
    )
    assert content_digest(partial) != content_digest(plain)
