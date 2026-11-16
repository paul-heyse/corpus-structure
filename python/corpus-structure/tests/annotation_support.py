"""Controlled inputs and builders shared by the annotations consumers."""

from dataclasses import replace
from types import SimpleNamespace
from typing import Literal

import pytest
import spacy
from spacy.tokens import Doc, MorphAnalysis

from corpus_structure.ingest import annotations
from corpus_structure.ingest.annotations import AnnotationInput
from corpus_structure.ingest.pdf_hierarchy import ProjectedPiece
from corpus_structure.ingest.sentences import Block, SentenceConfig, prepare_layout


class ControlledPipeline:
    """A unit fixture assigning deliberately wrong linguistic labels to native atoms."""

    def __init__(self):
        self.pipe_names = ["tok2vec", "tagger", "parser", "attribute_ruler", "lemmatizer"]
        blank = self.language = spacy.blank("en")
        self.tokenizer = blank.tokenizer
        self.vocab = blank.vocab
        self.config = SimpleNamespace(to_str=lambda: "controlled-unit-fixture-1")
        self.calls = []
        self.omit = None
        self.configuration = SentenceConfig(exclude=("ner",))

    def selection(self):
        from corpus_structure.methods.native_profiles import NativeProfile

        return SimpleNamespace(
            native=NativeProfile(
                "spacy",
                {"fixture": "controlled-native-columns-v1"},
                {"fixture": "no-model-weights"},
                self.configuration.model_dump(mode="json"),
                "float32",
                "cupy",
            )
        )

    def get_pipe_meta(self, name):
        return SimpleNamespace(factory="controlled-unit-fixture:" + name)

    def pipe(self, items, *, as_tuples, batch_size, n_process):
        self.calls.append((as_tuples, batch_size, n_process))
        assert as_tuples is True
        for doc, item in items:
            assert isinstance(doc, Doc)
            # A deterministic fixture, deliberately not a trained language model.
            for token in doc:
                token.is_sent_start = token.i == 0
            for token in doc:
                token.lemma_ = f"lemma:{token.i}"
                token.pos_ = "VERB"
                token.tag_ = "VB"
                token.morph = MorphAnalysis(doc.vocab, "VerbForm=Fin")
                token.dep_ = "ROOT" if token.i == 0 else "dep"
                token.head = doc[0]
            if self.omit == "lemma" and len(doc):
                doc[-1].lemma_ = ""
            if self.omit == "dependency":
                for token in doc:
                    token.dep_ = ""
            yield doc, item


@pytest.fixture
def controlled(monkeypatch):
    nlp = ControlledPipeline()

    def configured(configuration):
        nlp.configuration = configuration
        return nlp

    monkeypatch.setattr(annotations, "pipeline", configured)
    return nlp


def selected_item(
    nlp: ControlledPipeline,
    text="X X.",
    *,
    start=100,
    identity=7,
    block_id="paragraph:1",
    kind: Literal["paragraph", "list_item", "table_cell", "caption"] = "paragraph",
    block=None,
    pieces=None,
):
    block = Block(text, (), (), ()) if block is None else block
    layout = prepare_layout(nlp.language, block, start=start)
    if pieces is None:
        pieces = (
            (ProjectedPiece("#/texts/1", start, start + len(text), "native_text"),) if text else ()
        )
    from methods.declared_primary_fixture import selected_source

    pieces = tuple(
        replace(piece, source_field="text")
        if piece.kind == "native_text" and piece.source_field is None
        else piece
        for piece in pieces
    )
    complete_text = " " * start + block.text
    projection = [dict(kind="synthetic_separator", start=0, end=start)] if start else []
    projection.extend(piece.to_wire() for piece in pieces)
    spellings: dict[str, str] = {}
    for piece in pieces:
        if piece.kind != "native_text":
            continue
        pointer = piece.item_ref
        if pointer is None:
            raise ValueError("native annotation input requires its exact item pointer")
        spellings[pointer] = spellings.get(pointer, "") + complete_text[piece.start:piece.end]
    items = [dict(self_ref=f"#/groups/{identity}", label="section"), *(
        dict(self_ref=pointer, label="text", text=spelling, orig=spelling,
             parent={"$ref": f"#/groups/{identity}"})
        for pointer, spelling in spellings.items()
    )]
    source, frame, context = selected_source(complete_text, pieces=projection, items=items)
    return AnnotationInput(frame.pin, block_id, kind, block, layout, pieces), source, frame, context


def item(nlp, *args, **kwargs):
    """Raw annotation input; callers needing nominal products select the source explicitly."""
    return selected_item(nlp, *args, **kwargs)[0]
