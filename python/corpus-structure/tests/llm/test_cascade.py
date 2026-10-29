"""The quote cascade (agent interface §3.1, §6 P0-A-0; D4 §4.3 step 2).

Each step finds what it should and nothing it should not, on inline sentences; then the spike's
real quotes on production renditions (record `s0.stored`: 733 of 735 S0 quotes exact, 2 at
spacing; the S0-R2 sets) and the text-math note's L-10 perturbation set (at least 523 found, 428
exact, 514 at IoU >= 0.9, no mid-word cut). Expected spans come from the original text or the
spike's stored offsets, never from a second run of the cascade.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from corpus_structure.core.evidence import MacroDef
from corpus_structure.core.locators import LocatorIndex
from corpus_structure.methods.llm.cascade import Cascade, FrameSentence, Step, snap
from corpus_structure.methods.llm.parse import resolve_entries


def cascade(*sentences: str, macros: dict[str, MacroDef] | None = None, **kw: float) -> Cascade:
    """A text of sentences joined by spaces, sentence ids s1, s2, ... in order."""
    text, frame = "", []
    for i, s in enumerate(sentences, start=1):
        frame.append(FrameSentence(f"s{i}", len(text), len(text) + len(s)))
        text += s + " "
    return Cascade(text, frame, macros or {}, **kw)


def span(c: Cascade, quote: str, cited: str | None) -> tuple[str | None, Step | None]:
    found = c.locate(quote, cited)
    text = c.text[found.start : found.end] if found.start is not None else None
    return text, found.step


# --- Steps ------------------------------------------------------------------------------------


def test_exact_in_the_cited_sentence_first() -> None:
    c = cascade("Let \\(X\\) be normal.", "Then \\(X\\) is normal too.")
    found = c.locate("is normal", "s2")
    assert (found.step, found.sentence, c.text[found.start : found.end]) == (
        Step.EXACT_CITED,
        "s2",
        "is normal",
    )
    assert c.locate("\\(X\\)", "s2").sentence == "s2"


def test_exact_in_the_frame_nearest_the_cited_sentence() -> None:
    c = cascade("The mean is zero.", "Nothing here.", "Still nothing.", "The mean is zero.")
    found = c.locate("The mean is zero", "s3")
    assert (found.step, found.sentence, found.matches) == (Step.EXACT_FRAME, "s4", 2)


def test_a_context_quote_lands_in_the_context_sentence() -> None:
    """Revealing case: a `c1` quote whose text also occurs in the unit lands in `c1`."""
    c = Cascade(
        "Suppose that X is normal. Then X is normal again.",
        [FrameSentence("c1", 0, 25), FrameSentence("s1", 26, 49)],
    )
    found = c.locate("X is normal", "c1")
    assert (found.sentence, found.start, found.step) == ("c1", 13, Step.EXACT_CITED)


def test_spacing_and_math_delimiters() -> None:
    c = cascade("so \\(X = a + b \\, Z\\) holds.")
    assert span(c, "\\( X=a+b Z \\)", "s1") == ("\\(X = a + b \\, Z\\)", Step.SPACING)
    assert span(c, "$X = a + b Z$", "s1") == ("\\(X = a + b \\, Z\\)", Step.SPACING)
    assert span(c, "X = a+b Z", "s1") == ("X = a + b \\, Z", Step.SPACING)
    assert c.locate("X = c", "s1").step not in (Step.SPACING, Step.EXACT_CITED)


def test_macros_match_either_spelling() -> None:
    macros = {"\\R": MacroDef(body="\\mathbb{R}"), "\\f": MacroDef(nargs=1, body="#1")}
    c = cascade("with values in \\( \\R \\) only.", macros=macros)
    assert span(c, "values in \\(\\mathbb{R}\\)", "s1") == ("values in \\( \\R \\)", Step.MACROS)
    assert cascade("in \\( \\R \\).").locate("in \\(\\mathbb{R}\\)", "s1").step is not Step.MACROS


def test_a_span_is_snapped_to_whole_words() -> None:
    c = cascade("the normal distribution with mean zero")
    assert span(c, "ormal distribution with me", "s1") == (
        "normal distribution with mean",
        Step.EXACT_CITED,
    )
    assert snap("ab cd", 1, 4, 0, 5) == (0, 5)


def test_a_dropped_word_quote_longer_than_64_characters_returns_the_whole_span() -> None:
    """Revealing case: the alignment window has the needle's length, one token short; the token
    step's opcodes recover the whole span."""
    sentence = (
        "Suppose that \\(X\\) has the normal distribution with location parameter "
        "\\(\\mu \\in \\R\\) and scale parameter \\(\\sigma \\in (0, \\infty)\\)."
    )
    quote = (
        "\\(X\\) has the normal distribution with parameter \\(\\mu \\in \\R\\) and scale "
        "parameter \\(\\sigma \\in (0, \\infty)\\)"
    )
    assert len(quote) > 64
    c = cascade(sentence)
    text, step = span(c, quote, "s1")
    assert step is Step.TOKENS
    assert text == sentence[len("Suppose that ") : -1]


def test_the_character_step_takes_what_the_token_step_misses() -> None:
    c = cascade("It is the nonnegative integer part.")
    found = c.locate("the nonnegativ integer", "s1")
    assert found.step is Step.CHARACTERS
    assert c.text[found.start : found.end] == "the nonnegative integer"
    assert found.fuzzy_counts is not None and sum(found.fuzzy_counts) >= 1


def test_another_sentence_is_picked_when_the_cited_one_fails() -> None:
    c = cascade("Nothing related at all here.", "The variance is \\(\\sigma^2\\) for this family.")
    found = c.locate("The variance is \\(\\sigma^3\\) for this famly", "s1")
    assert (found.sentence, found.picked) == ("s2", True)
    assert found.step in (Step.TOKENS, Step.CHARACTERS)


def test_an_unlocated_quote_is_not_found() -> None:
    c = cascade("The normal distribution.")
    assert not c.locate("an entirely unrelated statement about gamma functions", "s1").found
    assert not c.locate("   ", "s1").found


def test_a_regex_timeout_is_recorded_and_the_cascade_continues() -> None:
    c = cascade("a " * 4000 + "b", regex_timeout=1e-9)
    found = c.locate("a  a  a  c", "s1")
    assert Step.SPACING in found.timeouts


# --- Hypothesis: word-aligned substrings of real sentences --------------------------------------


@pytest.fixture(scope="module")
def sentences(env: Any) -> list[str]:
    content = env.view("special/Normal.html").content
    return [content.text(s) for s in content.document.walk() if s.kind.value == "sentence"]


def _core(text: str) -> str:
    return re.sub(r"\s|\\[()\[\],;!]|\$", "", text)


def test_respaced_and_delimiter_swapped_substrings(sentences: list[str]) -> None:
    @settings(suppress_health_check=list(HealthCheck), deadline=None)
    @given(st.data())
    def check(draw: st.DataObject) -> None:
        sentence = draw.draw(st.sampled_from(sentences))
        words = sentence.split(" ")
        i = draw.draw(st.integers(0, len(words) - 1))
        j = draw.draw(st.integers(i + 1, len(words)))
        quote = " ".join(words[i:j])
        assume(sentence.count(quote) == 1 and any(ch.isalnum() for ch in quote))
        start = len(" ".join(words[:i])) + (1 if i else 0)
        expected = snap(sentence, start, start + len(quote), 0, len(sentence))
        variant = draw.draw(st.sampled_from(["as is", "respaced", "delimiters"]))
        if variant == "respaced":
            quote = " ".join(" ".join(quote).split())
        elif variant == "delimiters":
            quote = quote.replace("\\(", "$").replace("\\)", "$")
        # only a variant whose characters, spacing and delimiters aside, occur once is decidable
        assume(_core(sentence).count(_core(quote)) == 1)
        c = cascade(sentence)
        found = c.locate(quote, "s1")
        assert found.step in (Step.EXACT_CITED, Step.SPACING), (quote, found.step)
        assert (found.start, found.end) == expected, (variant, quote)

    check()


# --- The spike's quotes on production renditions -------------------------------------------------


def located_sets(env: Any, sets: list[str]) -> tuple[Counter[str], list[tuple[Any, ...]]]:
    steps: Counter[str] = Counter()
    differ: list[tuple[Any, ...]] = []
    cascades: dict[tuple[str, str], Cascade] = {}
    for name in sets:
        quote_set = env.data("quotes")[name]
        units = env.data("units")[quote_set["units"]]
        for uid, loc, quote, sentence, start, end, step in quote_set["quotes"]:
            unit = units[uid]
            if (quote_set["units"], uid) not in cascades:
                view = env.view(unit["page"])
                frame = env.frame(view, unit["sentences"])
                outcomes = resolve_entries(frame, LocatorIndex(view.content, view.page))
                assert all(o.status == "resolved" for o in outcomes.values())
                cascades[(quote_set["units"], uid)] = Cascade(
                    view.content.canonical_text,
                    [
                        FrameSentence(o.sentence, o.segment.start, o.segment.end)
                        for o in outcomes.values()
                        if o.segment is not None
                    ],
                    view.macros,
                )
            found = cascades[(quote_set["units"], uid)].locate(quote, sentence)
            got = found.step.value if found.step else "unlocated"
            steps[got] += 1
            if (found.start, found.end, got) != (start, end, step):
                differ.append(
                    (name, uid, loc, quote, (start, end, step), (found.start, found.end, got))
                )
    return steps, differ


S0_SETS = ["pass_a", "pass_b", "pass_p", "pass_h", "adjudication_d7", "trace", "reference"]


def test_the_s0_sets_reproduce_s0_stored(env: Any) -> None:
    steps, differ = located_sets(env, S0_SETS)
    assert differ == []
    assert steps == Counter({"exact_cited": 721, "exact_frame": 12, "spacing": 2})


def test_the_s0r2_sets_on_the_spike_pages(env: Any) -> None:
    sets = ["pass_hv", "pass_sv", "adjudication_v1"]
    _, differ = located_sets(env, sets)
    assert [d for d in differ if not d[1].startswith("H")] == []


@pytest.mark.corpus
def test_the_s0r2_sets_on_every_page(env: Any) -> None:
    steps, differ = located_sets(env, ["pass_hv", "pass_sv", "adjudication_v1"])
    assert differ == []
    assert steps == Counter({"exact_cited": 584, "spacing": 1})


def test_the_l10_perturbations(env: Any) -> None:
    units = env.data("units")["s0"]
    rows = env.data("perturbations")["rows"]
    assert len(rows) == 527
    counts: Counter[str] = Counter()
    cuts = []
    by_kind: dict[str, Counter[str]] = {}
    for uid, sentence, kind, _quote, changed, start, end in rows:
        unit = units[uid]
        view = env.view(unit["page"])
        text = view.content.canonical_text
        sentences = [FrameSentence(sid, a, b) for sid, (a, b) in unit["sentences"].items()]
        found = Cascade(text, sentences, view.macros).locate(changed, sentence)
        tally = by_kind.setdefault(kind, Counter())
        tally["n"] += 1
        if not found.found:
            continue
        assert found.start is not None and found.end is not None
        counts["found"] += 1
        tally["found"] += 1
        exact = (found.start, found.end) == (start, end)
        counts["exact"] += exact
        tally["exact"] += exact
        overlap = max(0, min(found.end, end) - max(found.start, start))
        union = max(found.end, end) - min(found.start, start)
        counts["iou>=0.9"] += overlap / union >= 0.9
        a, b = found.start, found.end
        if (a > 0 and text[a - 1].isalnum() and text[a].isalnum()) or (
            b < len(text) and text[b - 1].isalnum() and text[b].isalnum()
        ):
            cuts.append((uid, kind, changed))
    print(f"\nL-10 perturbations: {dict(counts)} of {len(rows)}; by kind {by_kind}")
    assert counts["found"] >= 523 and counts["exact"] >= 428 and counts["iou>=0.9"] >= 514
    assert cuts == []


def test_token_alignment_keeps_unicode_source_coordinates_and_repeated_candidates() -> None:
    sentence = "😀 The distribution has location μ and positive scale \u03c3."
    c = cascade(sentence, sentence)
    quote = "The distribution has μ and positive scale \u03c3"
    found = c.locate(quote, "s2")
    assert found.step is Step.TOKENS
    assert found.sentence == "s2"
    assert found.start == len(sentence) + 1 + len("😀 ")
    assert c.text[found.start : found.end] == sentence[len("😀 ") : -1]
