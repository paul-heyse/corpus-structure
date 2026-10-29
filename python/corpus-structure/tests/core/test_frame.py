"""Citation frames: resolution on a rendition and re-addressing to a served packet (D1 §10.3)."""

from __future__ import annotations

import pytest

from corpus_structure.core.batch import AuthoredBatch, CitationFrame, FrameEntry, cited_sentences
from corpus_structure.core.evidence import RenditionContent, Segment, SegmentKind
from corpus_structure.core.frame import (
    FrameRefused,
    readdress,
    resolve_entry,
    resolve_frame,
    sentences_by_text,
)
from corpus_structure.core.locators import LocatorIndex
from corpus_structure.core.vocab import FrameFailureReason as Reason

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
        "s7": entry("@sentence[0]:Then", "Then a + b X is normal."),  # malformed ordinal
    })  # fmt: skip
    with pytest.raises(FrameRefused) as caught:
        resolve_frame(frame, index)
    failures = {f.sentence: f for f in caught.value.failures}
    assert set(failures) == {"s1", "s2", "s3", "s4", "s5", "s7"}
    assert failures["s1"].code is Reason.LOCATOR_REFUSED
    assert failures["s1"].refusal == "several" and len(failures["s1"].candidates) == 2
    assert failures["s2"].code is Reason.TEXT_DIFFERS
    assert failures["s3"].code is Reason.NOT_A_SENTENCE
    assert failures["s3"].selected is SegmentKind.UNIT
    assert failures["s4"].code is Reason.LOCATOR_REFUSED and failures["s4"].refusal == "none"
    assert failures["s5"].code is Reason.OTHER_PAGE
    assert failures["s7"].code is Reason.LOCATOR_SYNTAX and failures["s7"].position is not None
    # the message is a projection of the code and the failure's fields
    assert "(several)" in failures["s1"].message and "(unit)" in failures["s3"].message
    assert "s7:" in str(caught.value)


def test_one_entry_resolves_relocates_or_stays_unresolved_with_its_code(index: LocatorIndex):
    """`resolve_entry` gives each entry's outcome without raising (A0 reports per entry)."""
    by_text = sentences_by_text(index)
    ok = resolve_entry("s1", FRAME["s1"], index, by_text)
    assert (ok.status, ok.code, ok.failure) == ("resolved", None, None)
    assert index.rendition.text(ok.segment) == "Suppose that X is normal."  # type: ignore[arg-type]
    # the locator names a unit, but exactly one sentence carries the recorded text: relocated
    moved = resolve_entry("s3", FrameEntry(locator=f"{PAGE}#u2",
                                           text="Suppose again that Y is normal."), index, by_text)
    assert (moved.status, moved.code) == ("relocated", Reason.NOT_A_SENTENCE)
    assert moved.locator == f"{PAGE}@sentence:Suppose again"
    assert moved.segment is not None and moved.segment.start == len("".join(SENTENCES[0])) + 4
    # the recorded text is on two sentences: never guessed
    twice = resolve_entry("s4", FrameEntry(locator=f"{PAGE}@sentence:Then",
                                           text="Then a + b X is normal."), index, by_text)
    assert (twice.status, twice.code, twice.segment) == ("unresolved", Reason.LOCATOR_REFUSED, None)
    assert twice.failure is not None and twice.failure.refusal == "several"
    absent = resolve_entry("s5", FrameEntry(locator=f"{PAGE}@sentence:Nothing", text="Nothing."),
                           index)  # fmt: skip
    assert (absent.status, absent.code) == ("unresolved", Reason.LOCATOR_REFUSED)


def test_resolve_frame_refuses_a_relocatable_entry(index: LocatorIndex) -> None:
    """Resolution never matches approximately: an entry that only relocates is a failure."""
    frame = CitationFrame.model_validate({"s1": entry("#u2", "Suppose again that Y is normal.")})
    with pytest.raises(FrameRefused) as caught:
        resolve_frame(frame, index)
    assert [f.code for f in caught.value.failures] == [Reason.NOT_A_SENTENCE]


def batch() -> AuthoredBatch:
    return AuthoredBatch.model_validate({
        "unit_ref": f"{PAGE}#u1",
        "statements": [{"local_ref": "st1", "kind": "theorem", "anchor": ["s1", "s2"]},
                       {"local_ref": "st0", "anchor": "outside",  # an ExternalReference
                        "descriptor": {"sentence": "s2", "quote": "is normal"}}],
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
    assert moved.statements[1].descriptor.sentence == "s7"  # type: ignore[union-attr]
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
    assert {f.code for f in caught.value.failures} == {Reason.NOT_IN_PACKET}
    partial = CitationFrame.model_validate({"s1": FRAME["s1"].model_dump()})
    with pytest.raises(FrameRefused, match="not in the batch's frame") as caught:
        readdress(batch(), partial, FRAME)
    assert {f.code for f in caught.value.failures} == {Reason.NOT_IN_FRAME}


def test_every_frame_failure_reason_has_a_case() -> None:
    """The cases above produce each `FrameFailureReason`; this keeps the list closed."""
    produced = {
        Reason.LOCATOR_SYNTAX, Reason.OTHER_PAGE, Reason.LOCATOR_REFUSED, Reason.NOT_A_SENTENCE,
        Reason.TEXT_DIFFERS, Reason.NOT_IN_FRAME, Reason.NOT_IN_PACKET,
    }  # fmt: skip
    assert produced == set(Reason)


def test_a_pack_qualifier_named_sentence_is_not_a_citation(index: LocatorIndex) -> None:
    """Citations are the fields typed `SentenceId`; a schema qualifier named `sentence` (raw JSON
    until S1 types it) is not one, so re-addressing leaves it as written (R03, DA-004)."""
    raw = batch().model_dump(mode="json")
    raw["claims"][0]["qualifiers"]["sentence"] = "s3"
    raw["claims"][0]["qualifiers"]["anchor"] = ["s9"]
    raw["claims"][0]["qualifiers"]["detail"] = {"sentence": "life imprisonment"}
    tagged = AuthoredBatch.model_validate(raw)
    assert cited_sentences(tagged) == cited_sentences(batch()) == ["s1", "s2", "c1"]
    assert resolve_frame(FRAME, index).keys() == {"s1", "s2", "c1"}
    served = CitationFrame.model_validate(
        {"s7": FRAME["s2"].model_dump(), "s3": FRAME["s1"].model_dump(),
         "c4": FRAME["c1"].model_dump()}
    )  # fmt: skip
    moved = readdress(tagged, FRAME, served)
    extra = moved.claims[0].qualifiers.__pydantic_extra__
    assert extra == {
        "sentence": "s3",
        "anchor": ["s9"],
        "detail": {"sentence": "life imprisonment"},
    }
    assert moved.claims[0].evidence[0].sentence == "s7"
