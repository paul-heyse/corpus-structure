"""Detached native linguistic columns over the shared, atom-preserving text layout.

This private producer consumes explicit source/block pins. It does not select source
regions, publish observations or assess linguistic accuracy. Native atom roles and
piece identities remain source facts even when a linguistic model labels them poorly.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from typing import Literal

from corpus_structure.core.text_structure import source_atoms
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.source_contexts import NativeSourcePin

from .pdf_hierarchy import ProjectedPiece
from .sentences import (
    Block,
    SentenceConfig,
    TextLayout,
    boundaries,
    make_doc,
    pipeline,
)

_COMPONENTS = ("tok2vec", "tagger", "parser", "attribute_ruler", "lemmatizer")
_ATTRIBUTES = ("LEMMA", "POS", "TAG", "MORPH", "DEP", "SENT_START")


@dataclass(frozen=True, slots=True)
class AnnotationProfile:
    """One richer profile; the existing sentence-only configuration stays unchanged."""

    configuration: SentenceConfig = field(default_factory=lambda: SentenceConfig(exclude=("ner",)))
    recipe: str = "native-linguistic-columns-1"
    version: int = 1

    def __post_init__(self) -> None:
        if self.version != 1 or self.recipe != "native-linguistic-columns-1":
            raise ValueError("unsupported linguistic annotation profile")

    def identity(self) -> dict:
        return dict(
            version=self.version,
            recipe=self.recipe,
            configuration=self.configuration.model_dump(mode="json"),
        )


@dataclass(frozen=True, slots=True)
class AnnotationInput:
    source: NativeSourcePin
    block_id: str
    kind: Literal["paragraph", "list_item", "table_cell", "caption"]
    block: Block
    layout: TextLayout
    native_pieces: tuple[ProjectedPiece, ...]

    def __post_init__(self) -> None:
        if not self.block_id or self.kind not in {
            "paragraph",
            "list_item",
            "table_cell",
            "caption",
        }:
            raise ValueError("annotations require a named supported native block")
        if not isinstance(self.native_pieces, tuple):
            raise ValueError("native piece identity must be immutable")
        if self.layout.block_start < 0:
            raise ValueError("source-bound block cannot begin before its projection")
        position = self.layout.block_start
        for piece in self.native_pieces:
            if (
                type(piece.start) is not int
                or type(piece.end) is not int
                or piece.start != position
                or not position < piece.end <= self.layout.block_end
                or piece.kind not in {"native_text", "synthetic_separator"}
                or (piece.kind == "native_text" and not (piece.item_ref or "").startswith("#/"))
            ):
                raise ValueError("native pieces must partition the source-bound block")
            position = piece.end
        if position != self.layout.block_end:
            raise ValueError("native pieces do not cover the source-bound block")
        expected_atoms = tuple(
            (self.layout.block_start + start, self.layout.block_start + end, role)
            for start, end, role in source_atoms(
                len(self.block.text), tuple(self.block.inline), tuple(self.block.markers)
            )
        )
        actual_atoms = tuple(
            (token.start, token.end, token.role)
            for token in self.layout.tokens
            if token.role != "prose"
        )
        if actual_atoms != expected_atoms:
            raise ValueError("prepared atom roles differ from the source-bound block")


@dataclass(frozen=True, slots=True)
class AnnotationAvailability:
    attribute: str
    status: Literal["complete", "partial", "absent", "not_applicable"]


class AnnotationUnavailable(RuntimeError):
    """Required components or annotation columns cannot satisfy the richer profile."""

    def __init__(
        self,
        message: str,
        *,
        missing_components: tuple[str, ...] = (),
        availability: tuple[AnnotationAvailability, ...] = (),
    ) -> None:
        super().__init__(message)
        self.missing_components = missing_components
        self.availability = availability


@dataclass(frozen=True, slots=True)
class ComponentPin:
    name: str
    factory: str


@dataclass(frozen=True, slots=True)
class TokenAnnotation:
    start: int
    end: int
    space: bool
    role: Literal["prose", "math", "reference"]
    lemma: str
    pos: str
    tag: str
    morphology: tuple[str, ...]
    dependency: str
    head: int
    sentence: int | None
    piece_indices: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class SentenceAnnotation:
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class AnnotationProduct:
    """Immutable columns; token heads are indices in this block's token tuple.

    Offsets and ``display_spans`` are absolute native projection characters. Token
    roles retain the prepared inline/reference atom roles; display formula membership
    is the separate source-owned span column, including formulas with prose-tokenized
    contents. Lemmas, tags and dependencies
    are model annotations, not accepted mathematical or semantic interpretations.
    Component implementations are pinned together by the spaCy/model versions and
    effective pipeline configuration digest, rather than invented component versions.
    """

    source: NativeSourcePin
    block_id: str
    kind: str
    block_start: int
    block_end: int
    display_spans: tuple[tuple[int, int], ...]
    text_digest: str
    native_pieces: tuple[ProjectedPiece, ...]
    layout_digest: str
    layout_recipe: str
    profile_recipe: str
    profile_digest: str
    spacy_version: str
    model: str
    model_version: str
    components: tuple[ComponentPin, ...]
    pipeline_config_digest: str
    availability: tuple[AnnotationAvailability, ...]
    tokens: tuple[TokenAnnotation, ...]
    sentences: tuple[SentenceAnnotation, ...]
    dependency_digest: str


def annotate(
    inputs: Iterable[AnnotationInput],
    profile: AnnotationProfile | None = None,
) -> Iterator[AnnotationProduct]:
    """Stream consumer-owned Docs through the existing resident, pinned pipeline.

    ``batch_size`` bounds spaCy's buffering; no new process pool, tokenizer or Doc cache
    is introduced. Inputs may reuse the same prepared layout across different consumers.
    A required annotation gap refuses that product with explicit availability details.
    """
    profile = AnnotationProfile() if profile is None else profile
    nlp = pipeline(profile.configuration)
    missing = tuple(name for name in _COMPONENTS if name not in nlp.pipe_names)
    if missing:
        raise AnnotationUnavailable(
            "richer annotation profile is missing required components: " + ", ".join(missing),
            missing_components=missing,
        )
    components = tuple(
        ComponentPin(name, nlp.get_pipe_meta(name).factory) for name in nlp.pipe_names
    )
    pipeline_digest = sha256(nlp.config.to_str().encode()).hexdigest()
    profile_digest = sha256(canonical_bytes(profile.identity())).hexdigest()
    items = (
        (
            make_doc(
                nlp,
                item.block,
                item.layout,
                start=item.layout.block_start,
                recipe=item.layout.recipe,
            ),
            item,
        )
        for item in inputs
    )
    for doc, item in nlp.pipe(
        items, as_tuples=True, batch_size=profile.configuration.batch_size, n_process=1
    ):
        if doc.text != item.block.text or len(doc) != len(item.layout.tokens):
            raise ValueError("linguistic pipeline changed the prepared source layout")
        availability = tuple(
            AnnotationAvailability(
                attribute,
                "not_applicable"
                if not len(doc)
                else "complete"
                if doc.has_annotation(attribute, require_complete=True)
                else "partial"
                if doc.has_annotation(attribute)
                else "absent",
            )
            for attribute in _ATTRIBUTES
        )
        if any(column.status not in {"complete", "not_applicable"} for column in availability):
            raise AnnotationUnavailable(
                "required linguistic annotations are incomplete", availability=availability
            )
        extents = boundaries(item.block, doc)
        sentences = tuple(
            SentenceAnnotation(item.layout.block_start + start, item.layout.block_start + end)
            for start, end in extents
        )
        tokens = []
        sentence_index = 0
        piece_index = 0
        for token, layout in zip(doc, item.layout.tokens, strict=True):
            start = item.layout.block_start + token.idx
            end = start + len(token.text)
            if (start, end) != (layout.start, layout.end) or bool(
                token.whitespace_
            ) != layout.space:
                raise ValueError("linguistic pipeline changed prepared token coordinates")
            while sentence_index < len(sentences) and sentences[sentence_index].end <= start:
                sentence_index += 1
            sentence = (
                sentence_index
                if sentence_index < len(sentences) and end > sentences[sentence_index].start
                else None
            )
            while (
                piece_index < len(item.native_pieces)
                and item.native_pieces[piece_index].end <= start
            ):
                piece_index += 1
            indices = []
            index = piece_index
            while index < len(item.native_pieces) and item.native_pieces[index].start < end:
                indices.append(index)
                index += 1
            tokens.append(
                TokenAnnotation(
                    start,
                    end,
                    layout.space,
                    layout.role,
                    token.lemma_,
                    token.pos_,
                    token.tag_,
                    tuple(str(token.morph).split("|")) if str(token.morph) else (),
                    token.dep_,
                    token.head.i,
                    sentence,
                    tuple(indices),
                )
            )
        layout_digest = sha256(canonical_bytes(asdict(item.layout))).hexdigest()
        identity = dict(
            source=asdict(item.source),
            block_id=item.block_id,
            kind=item.kind,
            native_pieces=[piece.to_wire() for piece in item.native_pieces],
            layout_digest=layout_digest,
            profile_digest=profile_digest,
            components=[asdict(component) for component in components],
            pipeline_config_digest=pipeline_digest,
        )
        yield AnnotationProduct(
            item.source,
            item.block_id,
            item.kind,
            item.layout.block_start,
            item.layout.block_end,
            item.layout.display,
            item.layout.text_digest,
            item.native_pieces,
            layout_digest,
            item.layout.recipe,
            profile.recipe,
            profile_digest,
            profile.configuration.spacy_version,
            profile.configuration.model,
            profile.configuration.model_version,
            components,
            pipeline_digest,
            availability,
            tuple(tokens),
            sentences,
            sha256(canonical_bytes(identity)).hexdigest(),
        )
