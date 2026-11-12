"""Project HanLP's UD, PTB, SRL and constituency evidence into private products."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from itertools import groupby
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, StrictInt, TypeAdapter

from .pm2_products import ParserProduct, ParserProducts
from .pm2_source import MappedSource, PM2TokenMap, SourceMapRefused, map_hanlp

_NATIVE_DEPENDENCIES = TypeAdapter(list[tuple[StrictInt, str]])
_NATIVE_SRL = TypeAdapter(list[list[tuple[str, str, StrictInt, StrictInt]]])


class _Payload(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class _Phrase(_Payload):
    scheme: Literal["hanlp-ptb-constituency-1"] = "hanlp-ptb-constituency-1"
    sentence: int
    label: str
    location: str


def _head(document: Mapping[str, Any], name: str) -> list[Any]:
    heads = [value for key, value in document.items() if key.split("/")[0] == name]
    if len(heads) != 1 or not isinstance(heads[0], list):
        raise ValueError(f"HanLP requires one ordered {name} head")
    return heads[0]


def _ranges(indices: set[int]) -> tuple[tuple[int, int], ...]:
    spans = []
    for _, group in groupby(enumerate(sorted(indices)), key=lambda item: item[1] - item[0]):
        items = tuple(index for _, index in group)
        spans.append((items[0], items[-1] + 1))
    return tuple(spans)


def _dependency_graph(
    rows: Any, size: int
) -> tuple[tuple[int | None, ...], tuple[str, ...], tuple[tuple[int, ...], ...]]:
    native = _NATIVE_DEPENDENCIES.validate_python(rows)
    if len(native) != size or any(
        not 0 <= head <= size or head == index + 1 or not label or (head == 0) != (label == "root")
        for index, (head, label) in enumerate(native)
    ):
        raise ValueError("HanLP returned malformed one-based dependency arcs")
    if sum(head == 0 for head, _ in native) != 1:
        raise ValueError("HanLP dependency tree must have one native root")
    heads = tuple(head - 1 if head else None for head, _ in native)
    children: list[list[int]] = [[] for _ in native]
    for index, head in enumerate(heads):
        if head is not None:
            children[head].append(index)
    root = heads.index(None)
    seen: set[int] = set()
    pending = [root]
    while pending:
        current = pending.pop()
        seen.add(current)
        pending.extend(children[current])
    if len(seen) != size:
        raise ValueError("HanLP dependency arcs do not reach the sentence root")
    return heads, tuple(label for _, label in native), tuple(tuple(row) for row in children)


def _constituency(tree: Any, prepared_words: list[str]) -> list[tuple[str, int, int]]:
    leaves: list[str] = []
    phrases: list[tuple[str, int, int]] = []

    def visit(node: Any, depth: int) -> None:
        if depth > 2 * len(prepared_words) + 2:
            raise ValueError("HanLP constituency depth exceeds the sentence bound")
        if isinstance(node, str):
            if len(leaves) == len(prepared_words):
                raise ValueError("HanLP constituency yield exceeds the sentence bound")
            leaves.append(node)
            return
        if (
            not isinstance(node, (list, tuple))
            or len(node) != 2
            or not isinstance(node[0], str)
            or not node[0]
            or not isinstance(node[1], (list, tuple))
            or not node[1]
        ):
            raise ValueError("HanLP returned a malformed constituency node")
        label, children = node
        start = len(leaves)
        for child in children:
            visit(child, depth + 1)
        phrases.append((label, start, len(leaves)))

    visit(tree, 0)
    if leaves != prepared_words:
        raise ValueError("HanLP constituency yield differs from its prepared canonical tokens")
    return phrases


@dataclass(slots=True)
class _Sentence:
    mapping: PM2TokenMap
    number: int
    lemmas: list[str]
    tags: list[str]
    heads: tuple[int | None, ...]
    labels: tuple[str, ...]
    children: tuple[tuple[int, ...], ...]
    locations: dict[str, MappedSource | SourceMapRefused]
    products: list[ParserProduct]

    def location(self, ranges: tuple[tuple[int, int], ...]) -> str:
        suffix = "+".join(f"{start}-{end}" for start, end in ranges)
        key = f"s{self.number}/span/{suffix}"
        if key not in self.locations:
            try:
                self.locations[key] = map_hanlp(
                    self.mapping,
                    self.number,
                    ranges,
                    scope_digest=self.mapping.mapping.scope_digest,
                )
            except SourceMapRefused as exc:
                self.locations[key] = exc
        return key

    def emit(self, key: str, semantic_type: str, value: _Payload, *members: str) -> None:
        self.products.append(
            ParserProduct(
                key, semantic_type, value.model_dump(mode="json"), tuple(dict.fromkeys(members))
            )
        )


def hanlp_products(
    mapping: PM2TokenMap, request: Mapping[str, Any], reply: Mapping[str, Any]
) -> ParserProducts:
    """Validate native head shapes and ground their private candidate products."""
    native, preparation = reply["native"], reply["preparation"]
    sentence_ids = tuple(sorted({token.sentence for token in mapping.tokens}))
    sentences = [[token.text for token in mapping.sentence_tokens(index)] for index in sentence_ids]
    if not sentences or request["sentences"] != sentences or native["tok"] != sentences:
        raise ValueError("HanLP input and native tokens differ from the canonical token map")
    columns = tuple(_head(native, head) for head in ("lem", "pos", "dep", "srl", "con"))
    if any(len(column) != len(sentences) for column in (*columns, preparation)):
        raise ValueError("HanLP heads and preparation must cover the admitted sentence population")

    locations: dict[str, MappedSource | SourceMapRefused] = {}
    products: list[ParserProduct] = []
    for number, words, prepared, lemmas, tags, arcs, srl, tree in zip(
        sentence_ids, sentences, preparation, *columns, strict=True
    ):
        prepared_words = prepared["prepared_words"]
        if any(
            not isinstance(column, list)
            or len(column) != len(words)
            or any(not isinstance(word, str) for word in column)
            for column in (prepared_words, lemmas, tags)
        ):
            raise ValueError("HanLP lexical heads do not cover the canonical words")
        heads, labels, children = _dependency_graph(arcs, len(words))
        phrases = _constituency(tree, prepared_words)
        sentence = _Sentence(
            mapping,
            number,
            [lemma.strip().casefold() for lemma in lemmas],
            tags,
            heads,
            labels,
            children,
            locations,
            products,
        )
        # Native SRL group and role order are preserved. Domain roles are bound later.
        for group in _NATIVE_SRL.validate_python(srl):
            if sum(label == "PRED" for _, label, _, _ in group) != 1:
                raise ValueError("HanLP SRL group has an ambiguous predicate")
            for text, label, start, end in group:
                if (
                    not label
                    or not 0 <= start < end <= len(words)
                    or " ".join(prepared_words[start:end]) != text
                ):
                    raise ValueError("HanLP SRL role differs from its exact prepared tokens")
        for index, (label, start, end) in enumerate(phrases):
            location = sentence.location(((start, end),))
            phrase = _Phrase(sentence=number, label=label, location=location)
            sentence.emit(f"s{number}/phrase/{index}", "linguistic.constituent", phrase, location)
    return ParserProducts(locations, tuple(products))
