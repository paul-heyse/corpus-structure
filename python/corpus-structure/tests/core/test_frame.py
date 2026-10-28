"""Citation frames: resolution on a rendition and re-addressing to a served packet (D1 §10.3)."""

from __future__ import annotations

import pytest

from corpus_structure.core.batch import AuthoredBatch, CitationFrame
from corpus_structure.core.evidence import RenditionContent, Segment, SegmentKind
from corpus_structure.core.frame import FrameRefused, readdress, resolve_frame
from corpus_structure.core.locators import LocatorIndex

PAGE = "special/Test.html"
SENTENCES = (
    ("Suppose that X is normal.", "Then a + b X is normal.", "Then a + b X is normal."),
    ("Suppose again that Y is normal.",),
)


def rendition() -> RenditionContent:
    """Two units of sentences; the second sentence repeats, so it needs an ordinal locator."""
    text, units = "", []
    for i, sentences in enumerate(SENTENCES):
        if text:
            text += "\n\n"
        start = len(text)
        parts = []
        for sentence in sentences:
            if parts:
                text += " "
            parts.append(Segment(kind=SegmentKind.SENTENCE, start=len(text),
                                 end=len(text) + len(sentence)))  # fmt: skip
            text += sentence
        paragraph = Segment(kind=SegmentKind.PARAGRAPH, start=start, end=len(text), children=parts)
        units.append(Segment(kind=SegmentKind.UNIT, start=start, end=len(text),
                             attrs={"id": f"u{i + 1}"}, children=(paragraph,)))  # fmt: skip
    root = Segment(kind=SegmentKind.DOCUMENT, start=0, end=len(text), children=units)
    return RenditionContent(canonical_text=text, document=root)


@pytest.fixture
def index() -> LocatorIndex:
    return LocatorIndex(rendition(), PAGE)


def entry(locator: str, text: str) -> dict:
    return {"locator": f"{PAGE}{locator}", "text": text}


FRAME = CitationFrame.model_validate({
    "s1": entry("@sentence:Suppose that", "Suppose that X is normal."),
    "s2": entry("@sentence[1]:Then", "Then a + b X is normal."),
    "c1": entry("@sentence:Suppose again", "Suppose again that Y is normal."),
})  # fmt: skip


def test_every_entry_resolves_to_its_sentence(index: LocatorIndex) -> None:
    resolved = resolve_frame(FRAME, index)
    assert {k: index.rendition.text(s) for k, s in resolved.items()} == {
        "s1": "Suppose that X is normal.",
        "s2": "Then a + b X is normal.",
        "c1": "Suppose again that Y is normal.",
    }
    assert resolved["s2"].start < index.resolve(f"{PAGE}@sentence[2]:Then").start


def test_failures_are_listed_together_with_candidates(index: LocatorIndex) -> None:
    frame = CitationFrame.model_validate({
        "s1": entry("@sentence:Then", "Then a + b X is normal."),  # several, no ordinal
        "s2": entry("@sentence:Suppose that", "Suppose that X is normal [1]."),  # text differs
        "s3": entry("#u1", "Suppose that X is normal."),  # a unit, not a sentence
        "s4": entry("@sentence:Nothing", "Nothing."),
        "s5": {"locator": "other/Page.html@sentence:Suppose", "text": "x"},
        "s6": entry("@sentence:Suppose again", "Suppose again that Y is normal."),  # resolves
    })  # fmt: skip
    with pytest.raises(FrameRefused) as caught:
        resolve_frame(frame, index)
    failures = {f.sentence: f for f in caught.value.failures}
    assert set(failures) == {"s1", "s2", "s3", "s4", "s5"}
    assert failures["s1"].reason == "several" and len(failures["s1"].candidates) == 2
    assert failures["s2"].reason == "sentence text differs"
    assert "not a sentence" in failures["s3"].reason
    assert failures["s4"].reason == "none"
    assert "another page" in failures["s5"].reason


def batch() -> AuthoredBatch:
    return AuthoredBatch.model_validate({
        "unit_ref": f"{PAGE}#u1",
        "statements": [{"local_ref": "st1", "kind": "theorem", "anchor": ["s1", "s2"]},
                       {"local_ref": "st0", "kind": "theorem", "anchor": "outside"}],
        "entities": [{"local_ref": "X", "type": "RandomVariable", "label": "X",
                      "scope": "local", "symbol": "X"}],
        "claims": [{
            "local_ref": "c1", "predicate": "has_distribution", "subject": "X",
            "object": {"t": "text", "v": "normal"},
            "qualifiers": {"hedge": {"t": "phrase", "text": "again", "sentence": "c1"},
                           "conditions": {"op": "phrase", "text": "Y", "sentence": "c1"}},
            "evidence": [{"sentence": "s2", "quote": "is normal", "role": "primary"}],
        }],
        "unsupported": [{"local_ref": "u", "sentence": "s1", "quote": "Suppose", "reason": "r"}],
    })  # fmt: skip


def test_readdress_maps_every_sentence_id_by_locator_and_text() -> None:
    served = CitationFrame.model_validate(
        {"s7": FRAME["s2"].model_dump(), "s3": FRAME["s1"].model_dump(),
         "c4": FRAME["c1"].model_dump()}
    )  # fmt: skip
    moved = readdress(batch(), FRAME, served)
    claim = moved.claims[0]
    assert moved.statements[0].anchor == ("s3", "s7")
    assert moved.statements[1].anchor == "outside"
    assert claim.evidence[0].sentence == "s7"
    assert claim.qualifiers.hedge.sentence == "c4"  # type: ignore[union-attr]
    assert claim.qualifiers.conditions.sentence == "c4"  # type: ignore[union-attr]
    assert moved.unsupported[0].sentence == "s3"
    assert readdress(moved, served, FRAME) == batch()


def test_readdress_refuses_an_entry_the_packet_lacks() -> None:
    served = CitationFrame.model_validate({"s1": FRAME["s1"].model_dump()})
    with pytest.raises(FrameRefused) as caught:
        readdress(batch(), FRAME, served)
    assert {f.sentence for f in caught.value.failures} == {"s2", "c1"}
    partial = CitationFrame.model_validate({"s1": FRAME["s1"].model_dump()})
    with pytest.raises(FrameRefused, match="not in the batch's frame"):
        readdress(batch(), partial, FRAME)
