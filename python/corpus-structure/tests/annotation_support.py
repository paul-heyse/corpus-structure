"""Controlled inputs and builders shared by the annotations consumers."""

from types import SimpleNamespace
from typing import Literal

import pytest
import spacy
from spacy.tokens import Doc, MorphAnalysis

from corpus_structure.ingest import annotations
from corpus_structure.ingest.annotations import AnnotationInput, AnnotationProfile
from corpus_structure.ingest.pdf_hierarchy import ProjectedPiece
from corpus_structure.ingest.sentences import Block, SentenceConfig, prepare_layout
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.source_contexts import NativeSourcePin


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


def pin(identity=7):
    return NativeSourcePin(
        identity,
        f"source:{identity}",
        ProductReference(17, "integrated", "a" * 64),
        f"#/groups/{identity}",
        "descendants",
        "b" * 64,
        "c" * 64,
        3,
    )


def item(
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
    return AnnotationInput(pin(identity), block_id, kind, block, layout, pieces)


def primary_product(text, product, *, native_profile):
    """Characterize the authored columns before testing downstream interpretation."""
    from methods.primary_reading_fixture import primary_product as characterize

    return characterize(
        " " * product.block_start + text,
        product,
        AnnotationProfile(configuration=SentenceConfig.model_validate(native_profile.parameters)),
        native_profile=native_profile,
    )
