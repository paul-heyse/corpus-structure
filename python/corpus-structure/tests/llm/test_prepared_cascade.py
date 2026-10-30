"""Operation-owned citation preparation preserves source and occurrence semantics."""

from dataclasses import FrozenInstanceError

import pytest
from rapidfuzz import fuzz

from corpus_structure.core.evidence import MacroDef
from corpus_structure.methods.llm import cascade as module
from corpus_structure.methods.llm.cascade import Cascade, FrameSentence, Located, PlacementPolicy, Step


def test_frame_owns_input_collections_and_anchor_specific_decisions() -> None:
    text = "Identical words. Identical words."
    sentences = [FrameSentence("a", 0, 16), FrameSentence("b", 17, len(text))]
    macros = {"\\R": MacroDef(body="\\mathbb{R}")}
    frame = Cascade(text, sentences, macros)
    sentences.clear()
    macros.clear()
    assert frame.locate("Identical words", "a").start == 0
    assert frame.locate("Identical words", "b").start == 17
    assert len(frame.macros) == 1
    with pytest.raises(FrozenInstanceError):
        setattr(frame, "text", "changed")


def test_native_scorer_reaches_sentence_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    original = module.process.extractOne
    scorers = []

    def extract(*args, **kwargs):
        scorers.append(kwargs["scorer"])
        return original(*args, **kwargs)

    monkeypatch.setattr(module.process, "extractOne", extract)
    frame = Cascade("Nothing related. The scale parameter is positive.", [
        FrameSentence("a", 0, 16), FrameSentence("b", 17, 49)
    ])
    result = frame.locate("The scale parametr is positive", "a")
    assert result.found and result.sentence == "b" and result.picked
    assert scorers == [fuzz.partial_ratio]


def test_sentence_tokens_are_lazy_and_shared_between_distinct_quotes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = module.tokens
    calls = []

    def tokenize(text, base=0):
        calls.append((text, base))
        return original(text, base)

    monkeypatch.setattr(module, "tokens", tokenize)
    text = "The distribution has location mu and positive scale sigma."
    frame = Cascade(text, [FrameSentence("a", 0, len(text))])
    assert frame.locate("distribution", "a").step is Step.EXACT_CITED
    assert calls == []
    assert frame.locate("distribution has mu and positive scale sigma", "a").found
    assert frame.locate("distribution has location mu and scale sigma", "a").found
    assert calls.count((text, 0)) == 1


def test_timeout_outcomes_are_retried_and_elapsed_time_is_per_occurrence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []

    def locate(self, quote, cited):
        calls.append(quote)
        return Located(timeouts=(Step.SPACING,)) if len(calls) == 1 else Located()

    clock = iter([0.0, 0.1, 1.0, 1.02, 2.0, 2.001])
    monkeypatch.setattr(Cascade, "_locate", locate)
    monkeypatch.setattr(module.time, "perf_counter", lambda: next(clock))
    frame = Cascade("text", [FrameSentence("a", 0, 4)])
    first = frame.locate("absent", "a")
    second = frame.locate("absent", "a")
    third = frame.locate("absent", "a")
    assert first.timeouts == (Step.SPACING,)
    assert second.timeouts == third.timeouts == ()
    assert (first.ms, second.ms, third.ms) == (100.0, 20.0, 1.0)
    assert calls == ["absent", "absent"]


def test_declared_policy_controls_fuzzy_acceptance() -> None:
    text = "It is the nonnegative integer part."
    sentences = [FrameSentence("a", 0, len(text))]
    assert Cascade(text, sentences).locate("the nonnegativ integer", "a").found
    strict = PlacementPolicy(token_cutoff=100, char_cutoff=100, pick_cutoff=100)
    assert not Cascade(text, sentences, policy=strict).locate("the nonnegativ integer", "a").found
