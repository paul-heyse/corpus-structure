"""The quote cascade: where a quote lies among a citation frame's sentences (D4 §4.3 step 2).

Agent-interface §3.1 (A0). The cascade reads canonical text and the frame's resolved sentences, and
returns a span in the original text: no offset map exists, so a span is always the rendition's.
Its steps, in order:

1. exact in the cited sentence;
2. exact in the frame's other sentences (the unit's sentences and the standing context), the
   occurrence nearest the cited sentence first;
3. exact up to spacing: the quote's non-space characters joined by optional whitespace, spacing
   commands and math delimiters, a math delimiter of the quote matching optionally (`regex`, with a
   timeout); cited sentence, then the others;
4. as 3, with each argument-free macro of the effective table (the page's over the pack's fallback)
   matching either spelling (`\\R` or `\\mathbb{R}`);
5. the token step: quote and sentence split into TeX/word tokens (`core/tex.py`'s tokenizer, runs of
   word characters joined into one word), each distinct token mapped to one private-use character;
   `fuzz.partial_ratio_alignment` (cutoff 80) picks the window, widened by three tokens, and
   `Levenshtein.opcodes` aligns the quote in it; the span runs from the token aligned to the
   quote's first token to the one aligned to its last;
6. the character step when 5 finds nothing: `partial_ratio_alignment` (cutoff 85, trailing `.,;:`
   stripped) for the window, widened by 30% of the quote, refined by `regex` `BESTMATCH` with at
   most 15% of the quote's length in edits and a timeout; its `fuzzy_counts` are recorded;
7. when the cited sentence yields nothing at 5 and 6 (or no sentence is cited),
   `process.extractOne(..., scorer=fuzz.partial_ratio)` picks a frame sentence and 5 and 6 run
   there.

Every span is trimmed of surrounding whitespace and snapped outward to word boundaries inside its
sentence. Several equal matches at the deciding step are recorded (`matches > 1`); a fuzzy score is
never identity. A `regex` `TimeoutError` is a recorded step outcome and the cascade continues.

`CASCADE_VERSION` is bumped by any change that can alter a located span: a step, its order, a
cutoff, the window widening, the snapping, or a `regex` or rapidfuzz bump that changes an output.
"""

from __future__ import annotations

import dataclasses
import math
import time
from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Protocol, cast

import regex
from rapidfuzz import fuzz, process
from rapidfuzz.distance import Levenshtein

from corpus_structure.core import tex
from corpus_structure.core.evidence import MacroDef


class _PartialRatioScorer(Protocol):
    def __call__(
        self, __s1: Sequence[Hashable], __s2: Sequence[Hashable], *, score_cutoff: float | None
    ) -> float: ...


CASCADE_VERSION = "1"

TOKEN_CUTOFF = 80
TOKEN_PAD = 3  # tokens added on each side of the alignment window
CHAR_CUTOFF = 85
CHAR_PAD = 0.30  # window widening, share of the quote's length
CHAR_ERRORS = 0.15  # BESTMATCH edit bound, share of the quote's length
PICK_CUTOFF = 80  # step 7's sentence choice
REGEX_TIMEOUT = 1.0  # seconds, steps 3 and 4 per sentence
REFINE_TIMEOUT = 0.2  # seconds, step 6
TRAILING = ".,;:"

# spacing, spacing commands and math delimiters between two characters of the quote (lazy)
JOIN = r"(?:\s|\\[,;!]|\\[()\[\]])*?"
# a math delimiter written in the quote: optional, preferred
OPTIONAL_DELIMITER = r"(?:(?:\s|\\[,;!])*?(?:\\[()\[\]]|\$\$?))?"
_QUOTE_DELIMITER = regex.compile(r"\$\$|\$|\\[()\[\]]")
_WORD_CHAR = regex.compile(r"\w")


class Step(StrEnum):
    EXACT_CITED = "exact_cited"
    EXACT_FRAME = "exact_frame"
    SPACING = "spacing"
    MACROS = "macros"
    TOKENS = "tokens"
    CHARACTERS = "characters"


@dataclass(frozen=True, slots=True)
class FrameSentence:
    id: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class Located:
    """Where a quote lies: the span and the frame sentence holding it, or `start is None`."""

    start: int | None = None
    end: int | None = None
    step: Step | None = None
    sentence: str | None = None  # the frame sentence the span lies in
    matches: int = 0  # matches at the deciding step; more than one is an ambiguity
    score: float | None = None  # rapidfuzz score (steps 5 and 6)
    fuzzy_counts: tuple[int, int, int] | None = None  # step 6: substitutions, insertions, deletions
    picked: bool = False  # step 7 chose the sentence
    timeouts: tuple[Step, ...] = ()  # regex steps that timed out on the way
    ms: float = field(default=0.0, compare=False)  # report-only diagnostic

    @property
    def found(self) -> bool:
        return self.start is not None


def snap(text: str, a: int, b: int, lo: int, hi: int) -> tuple[int, int]:
    """Trim whitespace at the ends of `[a, b)`, then widen it so it neither starts nor ends inside a
    word, within `[lo, hi)`."""
    while a < b and text[a].isspace():
        a += 1
    while b > a and text[b - 1].isspace():
        b -= 1
    while lo < a < len(text) and text[a - 1].isalnum() and text[a].isalnum():
        a -= 1
    while 0 < b < hi and text[b - 1].isalnum() and text[b].isalnum():
        b += 1
    return a, b


def spacing_pattern(quote: str, macros: Mapping[str, str] | None = None) -> str:
    """The quote up to spacing (steps 3 and 4); with `macros` (name -> body), a macro or its body
    in the quote matches either spelling."""
    return _spacing_pattern(quote, _macro_alternatives(macros or {}))


def _macro_alternatives(
    macros: Mapping[str, str],
) -> tuple[tuple[regex.Pattern[str], regex.Pattern[str], str], ...]:
    alternatives = []
    for name, body in sorted(macros.items(), key=lambda kv: (-len(kv[0]), kv[0])):
        name_pattern = regex.escape(name) + r"(?![A-Za-z])"
        body_pattern = JOIN.join(regex.escape(c) for c in body if not c.isspace())
        if not body_pattern:
            continue
        alternatives.append(
            (
                regex.compile(name_pattern),
                regex.compile(body_pattern),
                f"(?:{name_pattern}|{body_pattern})",
            )
        )
    return tuple(alternatives)


def _spacing_pattern(
    quote: str, alternatives: tuple[tuple[regex.Pattern[str], regex.Pattern[str], str], ...]
) -> str:
    parts: list[str] = []
    i = 0
    while i < len(quote):
        if quote[i].isspace():
            i += 1
            continue
        if m := _QUOTE_DELIMITER.match(quote, i):
            parts.append(OPTIONAL_DELIMITER)
            i = m.end()
            continue
        hit = None
        for name_re, body_re, either in alternatives:
            mm = name_re.match(quote, i) or body_re.match(quote, i)
            if mm and mm.end() > i:
                hit = (mm.end(), either)
                break
        if hit is not None:
            parts.append(hit[1])
            i = hit[0]
            continue
        parts.append(regex.escape(quote[i]))
        i += 1
    return JOIN.join(parts)


def tokens(text: str, base: int = 0) -> list[tuple[str, int, int]]:
    """TeX/word tokens with offsets: `core/tex.py`'s tokens without whitespace, a run of word
    characters joined into one word."""
    out: list[tuple[str, int, int]] = []
    joinable = False
    for token in tex.tokens(text):
        if token.kind == "space":
            joinable = False
            continue
        word = token.kind == "char" and _WORD_CHAR.fullmatch(token.text) is not None
        if word and joinable and out[-1][2] == base + token.start:
            last = out[-1]
            out[-1] = (last[0] + token.text, last[1], base + token.end)
        else:
            out.append((token.text, base + token.start, base + token.end))
        joinable = word
    return out


@dataclass(frozen=True, slots=True)
class PlacementPolicy:
    """Admitted cascade semantics; model-bound callers supply their release projection."""

    token_cutoff: int = TOKEN_CUTOFF
    token_pad: int = TOKEN_PAD
    char_cutoff: int = CHAR_CUTOFF
    char_pad: float = CHAR_PAD
    char_errors: float = CHAR_ERRORS
    pick_cutoff: int = PICK_CUTOFF
    regex_timeout: float = REGEX_TIMEOUT
    refine_timeout: float = REFINE_TIMEOUT
    recipe: str = "citation-cascade-1"


@dataclass(frozen=True)
class Cascade:
    """One immutable citation frame with operation-local, lazily prepared physical inputs.

    Caches belong to this frame and policy, never to global text identity. Tokens/patterns
    are prepared only when earlier cascade steps need them; exact citations pay no NLP cost.
    """

    text: str
    sentences: Sequence[FrameSentence]
    macros: Mapping[str, MacroDef] = field(default_factory=dict)
    regex_timeout: float | None = None
    refine_timeout: float | None = None
    policy: PlacementPolicy = field(default_factory=PlacementPolicy)
    _by_id: Mapping[str, FrameSentence] = field(init=False, repr=False, compare=False)
    _texts: Mapping[str, str] = field(init=False, repr=False, compare=False)
    _macro_bodies: Mapping[str, str] = field(init=False, repr=False, compare=False)
    _macro_patterns: tuple[tuple[regex.Pattern[str], regex.Pattern[str], str], ...] = field(
        init=False, repr=False, compare=False
    )
    _sentence_tokens: dict[str, tuple[tuple[str, int, int], ...]] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _quote_tokens: dict[str, tuple[tuple[str, int, int], ...]] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _patterns: dict[tuple[str, Step], regex.Pattern[str]] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _orders: dict[str | None, tuple[FrameSentence, ...]] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _results: dict[tuple[str, str | None], Located] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        sentences = tuple(sorted(self.sentences, key=lambda s: (s.start, s.end, s.id)))
        object.__setattr__(self, "sentences", sentences)
        object.__setattr__(self, "macros", MappingProxyType(dict(self.macros)))
        object.__setattr__(self, "_by_id", MappingProxyType({s.id: s for s in sentences}))
        object.__setattr__(
            self, "_texts", MappingProxyType({s.id: self.text[s.start : s.end] for s in sentences})
        )
        object.__setattr__(
            self,
            "_macro_bodies",
            MappingProxyType(
                {name: d.body for name, d in self.macros.items() if d.nargs == 0 and d.body.strip()}
            ),
        )
        object.__setattr__(self, "_macro_patterns", _macro_alternatives(self._macro_bodies))
        policy = dataclasses.replace(
            self.policy,
            regex_timeout=(
                self.policy.regex_timeout if self.regex_timeout is None else self.regex_timeout
            ),
            refine_timeout=(
                self.policy.refine_timeout if self.refine_timeout is None else self.refine_timeout
            ),
        )
        object.__setattr__(self, "policy", policy)
        object.__setattr__(self, "regex_timeout", policy.regex_timeout)
        object.__setattr__(self, "refine_timeout", policy.refine_timeout)

    def locate(self, quote: str, cited: str | None) -> Located:
        """Preserve occurrence reporting while sharing timeless placement decisions."""
        started = time.perf_counter()
        key = (quote, cited)
        found = self._results.get(key)
        if found is None:
            found = self._locate(quote, self._by_id.get(cited) if cited is not None else None)
            # A timeout can make the result depend on transient execution conditions.
            if not found.timeouts:
                self._results[key] = found
        ms = round((time.perf_counter() - started) * 1000, 3)
        return dataclasses.replace(found, ms=ms)

    # -- steps -----------------------------------------------------------------------------------

    def _locate(self, quote: str, cited: FrameSentence | None) -> Located:
        if not quote.strip():
            return Located()
        cited_id = cited.id if cited is not None else None
        others = self._orders.get(cited_id)
        if others is None:
            eligible = tuple(s for s in self.sentences if cited is None or s.id != cited.id)
            anchor = cited.start if cited is not None else (eligible[0].start if eligible else 0)
            others = tuple(sorted(eligible, key=lambda s: (abs(s.start - anchor), s.start)))
            self._orders[cited_id] = others
        anchor = cited.start if cited is not None else (others[0].start if others else 0)
        if cited is not None:
            hits = self._exact(quote, [cited])
            if hits:
                return self._found(hits[0], Step.EXACT_CITED, len(hits))
        hits = self._exact(quote, others)
        if hits:
            best = min(hits, key=lambda h: (abs(h[0] - anchor), h[0]))
            return self._found(best, Step.EXACT_FRAME, len(hits))
        timeouts: list[Step] = []
        steps: list[tuple[Step, Mapping[str, str] | None]] = [(Step.SPACING, None)]
        if self._macro_bodies:
            steps.append((Step.MACROS, self._macro_bodies))
        for step, macros in steps:
            pattern_key = (quote, step)
            pattern = self._patterns.get(pattern_key)
            if pattern is None:
                pattern = regex.compile(
                    _spacing_pattern(quote, self._macro_patterns if macros is not None else ())
                )
                self._patterns[pattern_key] = pattern
            for scope in ([cited] if cited is not None else [], others):
                hits, timed_out = self._search(pattern, scope)
                if timed_out:
                    timeouts.append(step)
                if hits:
                    best = min(hits, key=lambda h: (abs(h[0] - anchor), h[0]))
                    return self._found(best, step, len(hits), timeouts=tuple(timeouts))
        if cited is not None:
            fuzzy = self._fuzzy(quote, cited, timeouts)
            if fuzzy is not None:
                return fuzzy
        pool = others
        if pool:
            texts = [self._texts[s.id] for s in pool]
            # A typing-only cast preserves RapidFuzz's native scorer identity/C-API.
            choice = process.extractOne(
                quote,
                texts,
                scorer=cast(_PartialRatioScorer, fuzz.partial_ratio),
                score_cutoff=float(self.policy.pick_cutoff),
            )
            if choice is not None:
                fuzzy = self._fuzzy(quote, pool[choice[2]], timeouts, picked=True)
                if fuzzy is not None:
                    return fuzzy
        return Located(timeouts=tuple(timeouts))

    def _exact(
        self, quote: str, scope: Sequence[FrameSentence]
    ) -> list[tuple[int, int, FrameSentence]]:
        out = []
        for s in scope:
            i = self.text.find(quote, s.start, s.end)
            while i >= 0:
                out.append((i, i + len(quote), s))
                i = self.text.find(quote, i + 1, s.end)
        return out

    def _search(
        self, pattern: regex.Pattern[str], scope: Sequence[FrameSentence]
    ) -> tuple[list[tuple[int, int, FrameSentence]], bool]:
        out = []
        timed_out = False
        for s in scope:
            try:
                for m in pattern.finditer(
                    self.text, s.start, s.end, timeout=self.policy.regex_timeout
                ):
                    if m.end() > m.start():
                        out.append((m.start(), m.end(), s))
            except TimeoutError:
                timed_out = True
        return out, timed_out

    def _found(
        self,
        hit: tuple[int, int, FrameSentence],
        step: Step,
        matches: int,
        *,
        score: float | None = None,
        fuzzy_counts: tuple[int, int, int] | None = None,
        picked: bool = False,
        timeouts: tuple[Step, ...] = (),
    ) -> Located:
        a, b, s = hit
        a, b = snap(self.text, a, b, s.start, s.end)
        return Located(a, b, step, s.id, matches, score, fuzzy_counts, picked, timeouts)

    def _fuzzy(
        self, quote: str, s: FrameSentence, timeouts: list[Step], picked: bool = False
    ) -> Located | None:
        span = self._tokens(quote, s)
        if span is not None:
            a, b, score = span
            return self._found(
                (a, b, s), Step.TOKENS, 1, score=score, picked=picked, timeouts=tuple(timeouts)
            )
        refined = self._characters(quote, s, timeouts)
        if refined is not None:
            a, b, score, counts = refined
            return self._found(
                (a, b, s),
                Step.CHARACTERS,
                1,
                score=score,
                fuzzy_counts=counts,
                picked=picked,
                timeouts=tuple(timeouts),
            )
        return None

    def _tokens(self, quote: str, s: FrameSentence) -> tuple[int, int, float] | None:
        normalized = quote.rstrip(TRAILING) or quote
        needle = self._quote_tokens.get(normalized)
        if needle is None:
            needle = tuple(tokens(normalized))
            self._quote_tokens[normalized] = needle
        hay = self._sentence_tokens.get(s.id)
        if hay is None:
            hay = tuple(tokens(self._texts[s.id], s.start))
            self._sentence_tokens[s.id] = hay
        if not needle or not hay:
            return None
        q = [token for token, _, _ in needle]
        h = [token for token, _, _ in hay]
        window = fuzz.partial_ratio_alignment(q, h, score_cutoff=self.policy.token_cutoff)
        if window is None:
            return None
        w0, w1 = (
            max(0, window.dest_start - self.policy.token_pad),
            min(len(h), window.dest_end + self.policy.token_pad),
        )
        ops = [
            o
            for o in Levenshtein.opcodes(q, h[w0:w1])
            if o.tag != "insert" or o.src_start not in (0, len(q))
        ]
        used = [o for o in ops if o.tag in ("equal", "replace")]
        if not used:
            return None
        a, b = w0 + used[0].dest_start, w0 + used[-1].dest_end
        if b <= a:
            return None
        return hay[a][1], hay[b - 1][2], round(window.score, 1)

    def _characters(
        self, quote: str, s: FrameSentence, timeouts: list[Step]
    ) -> tuple[int, int, float, tuple[int, int, int]] | None:
        needle = quote.rstrip(TRAILING) or quote
        window = fuzz.partial_ratio_alignment(
            needle, self._texts[s.id], score_cutoff=self.policy.char_cutoff
        )
        if window is None:
            return None
        pad = math.ceil(self.policy.char_pad * len(needle))
        lo = max(s.start, s.start + window.dest_start - pad)
        hi = min(s.end, s.start + window.dest_end + pad)
        bound = max(1, math.ceil(self.policy.char_errors * len(needle)))
        pattern_key = (needle, Step.CHARACTERS)
        pattern = self._patterns.get(pattern_key)
        if pattern is None:
            pattern = regex.compile(r"(?b)(?:" + regex.escape(needle) + "){e<=" + str(bound) + "}")
            self._patterns[pattern_key] = pattern
        try:
            m = pattern.search(self.text, pos=lo, endpos=hi, timeout=self.policy.refine_timeout)
        except TimeoutError:
            timeouts.append(Step.CHARACTERS)
            return None
        if m is None or m.end() <= m.start():
            return None
        counts = m.fuzzy_counts
        return m.start(), m.end(), round(window.score, 1), (counts[0], counts[1], counts[2])
