"""Project HanLP's UD, PTB, SRL and constituency evidence into private products."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from itertools import groupby
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, StrictInt, TypeAdapter

from .pm2_products import ParserProduct, ParserProducts
from .pm2_source import MappedSource, PM2TokenMap, SourceMapRefused, map_hanlp

_NATIVE_DEPENDENCIES = TypeAdapter(list[tuple[StrictInt, str]])
_NATIVE_SRL = TypeAdapter(list[list[tuple[str, str, StrictInt, StrictInt]]])
_PHRASES = frozenset({"S", "SBAR", "SBARQ", "SINV", "SQ", "NP", "VP", "PP", "ADVP", "ADJP"})
_ARGUMENTS = frozenset({"nsubj", "csubj", "obj", "iobj", "obl", "xcomp", "ccomp"})
_CONDITIONS = frozenset({"if", "provided", "assuming"})
_EXCEPTIONS = frozenset({"unless", "except"})
_NEGATORS = frozenset({"not", "n't", "never"})
_REPORTING = frozenset({"say", "report", "claim", "state", "assert", "allege"})
_SCOPE_BOUNDARIES = frozenset({"acl", "advcl", "ccomp", "conj", "parataxis"})


class _Payload(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")


class _Argument(_Payload):
    role: str
    location: str
    head: int | None = None


class _SRLFrame(_Payload):
    predicate: str
    arguments: tuple[_Argument, ...]


class _Frame(_Payload):
    scheme: Literal["hanlp-ud-ptb-propbank-1"] = "hanlp-ud-ptb-propbank-1"
    sentence: int
    predicate_token: int
    syntactic_head: int
    predicate: str
    focus: str
    voice: Literal["active", "passive", "copular", "unresolved"]
    dependency_arguments: tuple[_Argument, ...]
    srl_frames: tuple[_SRLFrame, ...]


class _Cue(_Payload):
    scheme: Literal["hanlp-ud-cue-1"] = "hanlp-ud-cue-1"
    sentence: int
    kind: Literal["condition", "exception", "modality", "negation", "attribution"]
    location: str
    marker: str
    candidates: tuple[str, ...]
    attribution_source: str | None = None


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
        if label in _PHRASES:
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
    frames: dict[int, str] = field(default_factory=dict)
    head_frames: dict[int, list[int]] = field(default_factory=dict)

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

    def token(self, index: int) -> str:
        return self.location(((index, index + 1),))

    def subtree(self, head: int, *, stop: frozenset[str] = frozenset()) -> str:
        selected = set()
        pending = [head]
        while pending:
            token = pending.pop()
            selected.add(token)
            pending.extend(
                child
                for child in self.children[token]
                if self.labels[child].split(":")[0] not in stop
            )
        return self.location(_ranges(selected))

    def emit(self, key: str, semantic_type: str, value: _Payload, *members: str) -> None:
        self.products.append(
            ParserProduct(
                key, semantic_type, value.model_dump(mode="json"), tuple(dict.fromkeys(members))
            )
        )

    def build_frames(
        self, native: list[list[tuple[str, str, int, int]]], prepared_words: list[str]
    ) -> None:
        srl: dict[int, list[_SRLFrame]] = {}
        for frame in native:
            for text, label, start, end in frame:
                if not 0 <= start < end <= len(self.tags) or not label:
                    raise ValueError("HanLP SRL span lies outside its native sentence")
                if " ".join(prepared_words[start:end]) != text:
                    raise ValueError("HanLP SRL rendering differs from its prepared tokens")
            predicates = [(start, end) for _, label, start, end in frame if label == "PRED"]
            if len(predicates) != 1:
                raise ValueError("HanLP SRL group has an ambiguous predicate")
            start, end = predicates[0]
            heads = [
                index for index in range(start, end) if self.heads[index] not in range(start, end)
            ]
            if len(heads) != 1:
                raise ValueError("HanLP SRL predicate has no unique syntactic head")
            arguments = tuple(
                _Argument(role=label, location=self.location(((begin, stop),)))
                for _, label, begin, stop in frame
                if label != "PRED"
            )
            srl.setdefault(heads[0], []).append(
                _SRLFrame(predicate=self.location(((start, end),)), arguments=arguments)
            )

        for predicate, tag in enumerate(self.tags):
            relation = self.labels[predicate].split(":")[0]
            if (
                predicate not in srl
                and relation != "cop"
                and (not tag.startswith("VB") or relation == "aux")
            ):
                continue
            governor = self.heads[predicate]
            copular = relation == "cop" and governor is not None
            head = governor if copular else predicate
            assert head is not None
            arguments = tuple(
                _Argument(role=self.labels[index], location=self.subtree(index), head=index)
                for index in self.children[head]
                if self.labels[index].split(":")[0] in _ARGUMENTS
            )
            if copular:
                arguments = (
                    *arguments,
                    _Argument(
                        role="copular_head",
                        location=self.subtree(
                            head, stop=_SCOPE_BOUNDARIES | {"cop", "nsubj", "csubj"}
                        ),
                        head=head,
                    ),
                )
            passive = any(
                self.labels[index] in {"aux:pass", "nsubj:pass", "csubj:pass"}
                for index in self.children[head]
            )
            voice: Literal["active", "passive", "copular", "unresolved"] = "unresolved"
            if copular:
                voice = "copular"
            elif passive:
                voice = "passive"
            elif tag.startswith("VB") and relation != "aux":
                voice = "active"
            alternatives = tuple(srl.get(predicate, ()))
            value = _Frame(
                sentence=self.number,
                predicate_token=predicate,
                syntactic_head=head,
                predicate=self.token(predicate),
                focus=self.subtree(head, stop=_SCOPE_BOUNDARIES),
                voice=voice,
                dependency_arguments=arguments,
                srl_frames=alternatives,
            )
            key = f"s{self.number}/predicate/{predicate}"
            self.frames[predicate] = key
            self.head_frames.setdefault(head, []).append(predicate)
            members = [value.predicate, value.focus, *(argument.location for argument in arguments)]
            for alternative in alternatives:
                members.extend(
                    (
                        alternative.predicate,
                        *(argument.location for argument in alternative.arguments),
                    )
                )
            self.emit(key, "linguistic.predicate_frame", value, *members)

    def hosts(self, head: int, *, coordinated: bool = False) -> tuple[str, ...]:
        # Conjuncts remain alternative hosts. No scope inference is made across
        # an explicit predicate boundary other than a native coordination edge.
        group = {head}
        if coordinated:
            pending = [head]
            while pending:
                index = pending.pop()
                adjacent = [child for child in self.children[index] if self.labels[child] == "conj"]
                parent = self.heads[index]
                if self.labels[index] == "conj" and parent is not None:
                    adjacent.append(parent)
                for item in adjacent:
                    if item not in group:
                        group.add(item)
                        pending.append(item)
        return tuple(
            self.frames[predicate]
            for index in sorted(group)
            for predicate in self.head_frames.get(index, ())
            if isinstance(self.locations[self.token(predicate)], MappedSource)
        )

    def build_cues(self) -> None:
        surface = self.mapping.sentence_tokens(self.number)
        for index, (head, label, lemma, tag) in enumerate(
            zip(self.heads, self.labels, self.lemmas, self.tags, strict=True)
        ):
            if head is None:
                continue
            relation = label.split(":")[0]
            kind: Literal["condition", "exception", "modality", "negation", "attribution"]
            source = None
            marker = index
            word = surface[index].text.casefold()
            if relation == "mark" and word in _CONDITIONS | _EXCEPTIONS:
                kind = "condition" if word in _CONDITIONS else "exception"
                location = self.subtree(head)
                governor = self.heads[head]
                hosts = (
                    self.hosts(governor, coordinated=True)
                    if (governor is not None and self.labels[head] == "advcl")
                    else ()
                )
            elif relation == "aux" and tag == "MD":
                kind, location, hosts = "modality", self.token(index), self.hosts(head)
            elif relation in {"advmod", "neg"} and lemma in _NEGATORS:
                kind, location, hosts = "negation", self.token(index), self.hosts(head)
            elif relation == "ccomp" and self.lemmas[head] in _REPORTING:
                kind, location, hosts = "attribution", self.token(head), self.hosts(index)
                marker = head
                source = self.frames.get(head)
            else:
                continue
            if not isinstance(self.locations[location], MappedSource):
                hosts = ()
            value = _Cue(
                sentence=self.number,
                kind=kind,
                location=location,
                marker=self.token(marker),
                candidates=hosts,
                attribution_source=source,
            )
            members = (location, value.marker, *hosts, *((source,) if source else ()))
            self.emit(
                f"s{self.number}/cue/{index}/{kind}", "linguistic.qualifier_cue", value, *members
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
        sentence.build_frames(_NATIVE_SRL.validate_python(srl), prepared_words)
        sentence.build_cues()
        for index, (label, start, end) in enumerate(phrases):
            location = sentence.location(((start, end),))
            phrase = _Phrase(sentence=number, label=label, location=location)
            sentence.emit(f"s{number}/phrase/{index}", "linguistic.constituent", phrase, location)
    return ParserProducts(locations, tuple(products))
