"""M03 `segment.sentences`, variant b', as a step of M01's task (D4 M03; ingest and math §3.4).

Leaf text blocks (segments whose kind has the member property `sentence_split`, D4 M03's
`paragraph`, `list_item`, `table_cell` and `caption`, with no such segment inside) are split into
sentences on a spaCy `Doc` built from words and spaces: the prose between inline math spans and
rendered reference markers is tokenized with `nlp.tokenizer`, and each inline math span and each
marker enters as one word, so the Doc reproduces the block text exactly and token offsets are
canonical-text offsets. Math words are tagged `NNP`; `is_sent_start = False` is preset on
markers and on every token of a display formula after its first, which the parser respects. Docs
run through `nlp.pipe(..., as_tuples=True)` with the model loaded once per process. A sentence is
trimmed of surrounding whitespace and never crosses its block.

The configuration (`SentenceConfig`) names the spaCy version, the model package and version and
the excluded components; it is part of `ingest.html`'s configuration hash, and loading refuses an
installed spaCy or model that differs from it. The segments it produces are content.
"""

from __future__ import annotations

import functools
import itertools
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

import spacy
from pydantic import BaseModel, ConfigDict, Field
from spacy.language import Language
from spacy.tokens import Doc

from corpus_structure.core.vocab import SegmentKind

MATH_TAG = "NNP"


class SentenceConfig(BaseModel):
    """`segment.sentences/<name>`, resolved (D4 M03 "Configuration")."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # b': inline math and reference markers each one word of a words-and-spaces Doc (D4 M03)
    variant: Literal["math_as_word"] = "math_as_word"
    spacy_version: str = "3.8.18"
    model: str = "en_core_web_sm"
    model_version: str = "3.8.0"
    exclude: tuple[str, ...] = ("ner", "lemmatizer")
    batch_size: int = Field(default=64, ge=1)


class SentenceConfigError(RuntimeError):
    pass


@functools.cache
def pipeline(config: SentenceConfig) -> Language:
    """The configured pipeline, loaded once per process; refuses a version that differs."""
    if spacy.__version__ != config.spacy_version:
        raise SentenceConfigError(
            f"spaCy {spacy.__version__} is installed; the configuration names "
            f"{config.spacy_version}"
        )
    nlp = spacy.load(config.model, exclude=list(config.exclude))
    if nlp.meta.get("version") != config.model_version:
        raise SentenceConfigError(
            f"{config.model} {nlp.meta.get('version')} is installed, the configuration names "
            f"{config.model_version}"
        )
    return nlp


@dataclass(frozen=True, slots=True)
class Block:
    """One block to split: its text and, relative to it, inline math, display math and markers."""

    text: str
    inline: Sequence[tuple[int, int]]
    display: Sequence[tuple[int, int]]
    markers: Sequence[tuple[int, int]]


def block_of(
    text: str,
    start: int,
    end: int,
    children: Iterable[tuple[SegmentKind, int, int]],
    markup: Iterable[Mapping[str, Any]],
) -> Block:
    """The block M03 splits, from its canonical-text extent `[start, end)`, its children as
    `(kind, start, end)` and its inline markup (canonical-text offsets): inline and display math,
    and the rendered reference markers (`ref` markup with text). M01's sentence step and M13 both
    build their Docs from this, so the two Docs are identical by construction."""
    inline: list[tuple[int, int]] = []
    display: list[tuple[int, int]] = []
    for kind, a, b in children:
        if kind is SegmentKind.MATH_INLINE:
            inline.append((a - start, b - start))
        elif kind is SegmentKind.MATH_DISPLAY:
            display.append((a - start, b - start))
    markers = []
    for m in markup:
        a, b = m.get("start"), m.get("end")
        if m.get("markup") == "ref" and isinstance(a, int) and isinstance(b, int) and b > a:
            markers.append((a - start, b - start))
    return Block(text[start:end], inline, display, markers)


def make_doc(nlp: Language, block: Block) -> Doc:
    """The block's words-and-spaces Doc: inline math spans and markers are one word each."""
    atoms = sorted(
        [(a, b, True) for a, b in block.inline] + [(a, b, False) for a, b in block.markers]
    )
    words: list[str] = []
    spaces: list[bool] = []
    math_words: list[int] = []
    marker_words: list[int] = []
    text = block.text

    def prose(piece: str) -> None:
        for token in nlp.tokenizer(piece):
            words.append(token.text)
            spaces.append(bool(token.whitespace_))

    position = 0
    for start, end, is_math in atoms:
        if start < position:  # overlapping atoms cannot occur in M01's output; keep the first
            continue
        prose(text[position:start])
        (math_words if is_math else marker_words).append(len(words))
        words.append(text[start:end])
        follows_space = text.startswith(" ", end)
        spaces.append(follows_space)
        position = end + 1 if follows_space else end
    prose(text[position:])
    doc = Doc(nlp.vocab, words=words, spaces=spaces)
    if doc.text != text:
        raise AssertionError(
            f"the words-and-spaces Doc does not reproduce the block: {text[:80]!r}"
        )
    for i in math_words:
        doc[i].tag_ = MATH_TAG
    for i in marker_words:
        doc[i].is_sent_start = False
    for start, end in block.display:
        span = doc.char_span(start, end, alignment_mode="expand")
        if span is not None:
            for token in span[1:]:
                token.is_sent_start = False
    return doc


def boundaries(block: Block, doc: Doc) -> list[tuple[int, int]]:
    """Sentence extents in the block, trimmed of whitespace; never empty."""
    text = block.text
    starts = sorted({s.start_char for s in doc.sents if 0 < s.start_char < len(text)})
    cuts = [0, *starts, len(text)]
    out = []
    for a, e in itertools.pairwise(cuts):
        while a < e and text[a].isspace():
            a += 1
        while e > a and text[e - 1].isspace():
            e -= 1
        if e > a:
            out.append((a, e))
    return out


def split(blocks: Sequence[Block], config: SentenceConfig) -> list[list[tuple[int, int]]]:
    """Sentence extents of each block, relative to it, in input order."""
    nlp = pipeline(config)
    items = ((make_doc(nlp, block), n) for n, block in enumerate(blocks))
    out: list[list[tuple[int, int]]] = [[] for _ in blocks]
    for doc, n in nlp.pipe(items, batch_size=config.batch_size, as_tuples=True):
        out[n] = boundaries(blocks[n], doc)
    return out
