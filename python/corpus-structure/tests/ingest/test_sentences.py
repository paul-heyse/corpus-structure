"""M03's words-and-spaces Doc and b' semantics (ingest and math §3.4; D4 M03)."""

from __future__ import annotations

import pytest

from corpus_structure.ingest.profile import CompiledProfile
from corpus_structure.ingest.sentences import (
    Block,
    SentenceConfig,
    SentenceConfigError,
    make_doc,
    pipeline,
    split,
)

CONFIG = SentenceConfig()


def test_a_formula_straddling_tokenizer_boundaries_stays_one_token() -> None:
    """`mean\\( \\pm \\)standard`: expanding the span to tokens would take prose into the math."""
    text = "The mean\\( \\pm \\)standard deviation is shown."
    start = text.index("\\(")
    end = text.index("\\)") + 2
    doc = make_doc(pipeline(CONFIG), Block(text, [(start, end)], [], []))
    assert doc.text == text
    (token,) = [t for t in doc if t.idx == start]
    assert token.text == text[start:end] == "\\( \\pm \\)"
    assert token.tag_ == "NNP"


def test_the_doc_reproduces_text_with_markers_and_display_math() -> None:
    text = "By [3], we have \\[ x = 1. \\quad Y = 2 \\] for all \\(n\\). Then [4] holds."
    marker1, marker2 = (
        (text.index("[3]"), text.index("[3]") + 3),
        (text.index("[4]"), text.index("[4]") + 3),
    )
    display = (text.index("\\["), text.index("\\]") + 2)
    inline = (text.index("\\(n"), text.index("\\)") + 2)
    block = Block(text, [inline], [display], [marker1, marker2])
    doc = make_doc(pipeline(CONFIG), block)
    assert doc.text == text
    (extents,) = split([block], CONFIG)
    starts = [a for a, _ in extents]
    assert all(not display[0] < s < display[1] for s in starts)  # never inside display math
    assert all(not m[0] <= s < m[1] for s in starts for m in (marker1, marker2))
    assert [text[a:b] for a, b in extents][-1] == "Then [4] holds."


def test_sentences_are_trimmed_and_stay_inside_their_block() -> None:
    blocks = [
        Block("One sentence here. Another one follows.", [], [], []),
        Block("Single.", [], [], []),
    ]
    assert split(blocks, CONFIG) == [[(0, 18), (19, 39)], [(0, 7)]]


def test_a_configuration_naming_other_versions_is_refused() -> None:
    with pytest.raises(SentenceConfigError, match="spaCy"):
        pipeline(SentenceConfig(spacy_version="3.7.0"))
    with pytest.raises(SentenceConfigError, match="en_core_web_sm"):
        pipeline(SentenceConfig(model_version="3.7.1"))


def test_sentences_never_cross_a_block_in_a_rendition(profile: CompiledProfile) -> None:
    from corpus_structure.ingest.html import build_rendition

    raw = (
        b"<!DOCTYPE html><html><head><meta charset=utf-8></head><body><ul><li>First item. It has"
        b" two.</li><li>Second</li></ul><p>A para. Ends.</p></body></html>"
    )
    r = build_rendition(raw, profile, CONFIG, source_uri="siegrist_random/random/t/a.html")
    for segment in r.content.document.walk():
        sentences = [c for c in segment.children if c.kind == "sentence"]
        assert all(segment.start <= s.start < s.end <= segment.end for s in sentences)
    texts = [r.content.text(s) for s in r.content.document.walk() if s.kind == "sentence"]
    assert texts == ["First item.", "It has two.", "Second", "A para.", "Ends."]


def test_prepared_layout_roundtrips_absolute_offsets_without_retokenizing(monkeypatch: pytest.MonkeyPatch) -> None:
    import dataclasses
    import spacy
    from pydantic import TypeAdapter
    from corpus_structure.ingest.sentences import TextLayout, prepare_layout

    nlp = spacy.blank("en")
    text = " \tLet \\(x\\)  be\nreal [3].\n"
    a = text.index("\\(")
    b = text.index("\\)") + 2
    c = text.index("[3]")
    block = Block(text, [(a, b)], [], [(c, c + 3)])
    layout = prepare_layout(nlp, block, start=100)
    adapter = TypeAdapter(TextLayout)
    restored = adapter.validate_json(adapter.dump_json(layout))
    assert restored == layout
    assert layout.tokens[0].start == 100
    # A consumer can reconstruct even when prose tokenization is unavailable.
    monkeypatch.setattr(nlp, "tokenizer", lambda _: pytest.fail("retokenized prepared input"))
    first = make_doc(nlp, block, restored, start=100)
    second = make_doc(nlp, block, restored, start=100)
    assert first.text == second.text == text
    assert [(t.idx + 100, t.idx + 100 + len(t.text)) for t in first] == [
        (t.start, t.end) for t in layout.tokens
    ]
    first[0].tag_ = "ALTERED"
    assert second[0].tag_ != "ALTERED"
    with pytest.raises(ValueError, match="regenerate"):
        make_doc(nlp, block, dataclasses.replace(layout, text_digest="wrong"), start=100)
    with pytest.raises(ValueError, match="regenerate"):
        make_doc(nlp, block, restored, start=0)


def test_ingestion_retains_the_exact_layout_consumed_by_segmentation(profile: CompiledProfile) -> None:
    from corpus_structure.ingest.html import build_rendition
    from corpus_structure.methods.math.scope import segment_block

    built = build_rendition(
        b"<html><body><p>Let \\(x\\) be real. Then [3] holds.</p></body></html>",
        profile, CONFIG, source_uri="siegrist_random/random/t/a.html",
    )
    blocks = [s for s in built.content.document.walk() if any(c.kind == "sentence" for c in s.children)]
    assert len(built.text_layouts) == len(blocks) == 1
    for layout, segment in zip(built.text_layouts, blocks, strict=True):
        assert (layout.block_start, layout.block_end) == (segment.start, segment.end)
        reconstructed = make_doc(pipeline(CONFIG), segment_block(built.content, segment), layout,
                                 start=segment.start)
        assert reconstructed.text == built.content.text(segment)
        assert any(token.role == "math" for token in layout.tokens)
