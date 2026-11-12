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
import hashlib
import itertools
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

import spacy
from pydantic import BaseModel, ConfigDict, Field
from spacy.language import Language
from spacy.tokens import Doc

from corpus_structure.core.text_structure import source_atoms
from corpus_structure.core.vocab import SegmentKind

from .hosted_spacy import HostedPipeline

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
def pipeline(config: SentenceConfig) -> HostedPipeline:
    """The configured pipeline, loaded once per process; refuses a version that differs."""
    if spacy.__version__ != config.spacy_version:
        raise SentenceConfigError(
            f"spaCy {spacy.__version__} is installed; the configuration names "
            f"{config.spacy_version}"
        )
    return HostedPipeline(config)


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


@dataclass(frozen=True, slots=True)
class TextToken:
    """A token's absolute canonical extent and physical role, without repeated text."""

    start: int
    end: int
    space: bool
    role: Literal["prose", "math", "reference"] = "prose"


@dataclass(frozen=True, slots=True)
class TextLayout:
    """Owned pre-pipeline layout; semantic recipe/custody is bound by the caller."""

    block_start: int
    block_end: int
    text_digest: str
    tokens: tuple[TextToken, ...]
    display: tuple[tuple[int, int], ...]
    recipe: str = "canonical-token-layout-1"


def prepare_layout(
    nlp: Language | HostedPipeline,
    block: Block,
    *,
    start: int = 0,
    recipe: str = "canonical-token-layout-1",
) -> TextLayout:
    """Tokenize prose once, preserving atom boundaries and all whitespace tokens."""
    atoms = source_atoms(len(block.text), tuple(block.inline), tuple(block.markers))
    tokens: list[TextToken] = []
    text = block.text

    def prose(a: int, b: int) -> None:
        for token in nlp.tokenizer(text[a:b]):
            at = start + a + token.idx
            tokens.append(TextToken(at, at + len(token.text), bool(token.whitespace_)))

    position = 0
    for a, b, role in atoms:
        if a < position:  # Same first-overlap rule as the original atom tokenizer.
            continue
        prose(position, a)
        follows_space = text.startswith(" ", b)
        tokens.append(
            TextToken(
                start + a, start + b, follows_space, "math" if role == "math" else "reference"
            )
        )
        position = b + 1 if follows_space else b
    prose(position, len(text))
    return TextLayout(
        start,
        start + len(text),
        hashlib.sha256(text.encode()).hexdigest(),
        tuple(tokens),
        tuple((start + a, start + b) for a, b in block.display),
        recipe,
    )


def make_doc(
    nlp: Language | HostedPipeline,
    block: Block,
    layout: TextLayout | None = None,
    *,
    start: int = 0,
    recipe: str = "canonical-token-layout-1",
) -> Doc:
    """Create a consumer-owned mutable Doc from a source-bound prepared layout."""
    if layout is None:
        layout = prepare_layout(nlp, block, start=start, recipe=recipe)
    text = block.text
    if (
        layout.recipe != recipe
        or layout.block_start != start
        or layout.block_end != start + len(text)
        or layout.text_digest != hashlib.sha256(text.encode()).hexdigest()
        or layout.display != tuple((start + a, start + b) for a, b in block.display)
    ):
        raise ValueError("text layout does not match its source block; regenerate the layout")
    words = [text[t.start - start : t.end - start] for t in layout.tokens]
    doc = Doc(nlp.vocab, words=words, spaces=[t.space for t in layout.tokens])
    if doc.text != text:
        raise ValueError("text layout does not reconstruct its source; regenerate the layout")
    for token, entry in zip(doc, layout.tokens, strict=True):
        if token.idx + start != entry.start or entry.end != entry.start + len(token.text):
            raise ValueError("text layout has invalid offsets; regenerate the layout")
        if entry.role == "math":
            token.tag_ = MATH_TAG
        elif entry.role == "reference":
            token.is_sent_start = False
    for a, b in layout.display:
        span = doc.char_span(a - start, b - start, alignment_mode="expand")
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


def split(
    blocks: Sequence[Block],
    config: SentenceConfig,
    *,
    layouts: Sequence[TextLayout] | None = None,
    endpoint: str | None = None,
    policy: Any = None,
) -> list[list[tuple[int, int]]]:
    """Sentence extents of each block, relative to it, in input order."""
    from corpus_structure.semantic.analysis_contracts import prepare_text_policy

    policy = prepare_text_policy() if policy is None else policy
    nlp: Any = pipeline(config)
    if layouts is not None and len(layouts) != len(blocks):
        raise ValueError("one text layout is required per block")
    items = (
        (
            make_doc(nlp, block, layouts[n], start=layouts[n].block_start, recipe=policy.recipe)
            if layouts is not None
            else make_doc(nlp, block, recipe=policy.recipe),
            n,
        )
        for n, block in enumerate(blocks)
    )
    out: list[list[tuple[int, int]]] = [[] for _ in blocks]
    for doc, n in nlp.pipe(items, batch_size=config.batch_size, as_tuples=True, endpoint=endpoint):
        out[n] = boundaries(blocks[n], doc)
    return out
