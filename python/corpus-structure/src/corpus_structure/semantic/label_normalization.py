"""Label normalization under the released class alias policy."""

from __future__ import annotations

import unicodedata

import regex
from pydantic import BaseModel, ConfigDict, Field, field_validator

from corpus_structure.core.vocab import CaseRule


def collapse(text: str) -> str:
    """NFC with whitespace runs collapsed to one space and the ends trimmed."""
    return " ".join(unicodedata.normalize("NFC", text).split())


def text_form(text: str, case: CaseRule = CaseRule.FOLD) -> str:
    """The D1 §6.2 text form: NFC, whitespace collapsed, and casefolded under the `fold` case
    policy (the default); `preserve` keeps case (math-bearing text, ADR-0023). It is also a string
    identifier's canonical form under its declared case."""
    nfc = unicodedata.normalize("NFC", text)
    return " ".join((nfc.casefold() if case is CaseRule.FOLD else nfc).split())


class Rewrite(BaseModel):
    """One pack rewrite (`match`/`replace`, applied with `regex.sub`) of the `aliases:` section.

    The pattern is compiled on validation, so a malformed one is a pack error, never a keying
    failure."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    match: str
    replace: str

    @field_validator("match")
    @classmethod
    def _compiles(cls, pattern: str) -> str:
        try:
            regex.compile(pattern)
        except regex.error as error:
            raise ValueError(f"rewrite pattern {pattern!r} does not compile: {error}") from None
        return pattern


class LabelRules(BaseModel):
    """Label-normalization data from the pack's `aliases:` section; core holds no word list."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    articles: tuple[str, ...] = ()
    head_words: dict[str, tuple[str, ...]] = Field(default_factory=dict)  # prefixed class -> words
    rewrites: tuple[Rewrite, ...] = ()


def normalize_label(
    text: str, type_: str, rules: LabelRules, case: CaseRule = CaseRule.FOLD
) -> str:
    """Text form under the class's case policy; one leading article removed; the rewrites in
    order; the class's head words removed as trailing whole words; whitespace collapsed again.
    Articles and head words match regardless of case. Never empties a label."""
    label = text_form(text, case)
    words = label.split(" ")
    articles = {text_form(a) for a in rules.articles}
    if len(words) > 1 and words[0].casefold() in articles:
        label = " ".join(words[1:])
    for rewrite in rules.rewrites:
        label = regex.sub(rewrite.match, rewrite.replace, label)
    label = text_form(label, case)
    heads = {text_form(w) for w in rules.head_words.get(type_, ())}
    words = label.split(" ") if label else []
    while len(words) > 1 and words[-1].casefold() in heads:
        words.pop()
    return text_form(" ".join(words), case)
