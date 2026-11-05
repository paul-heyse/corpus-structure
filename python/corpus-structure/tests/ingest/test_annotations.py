"""Independent coordinates and controlled annotation fixtures; provider checks are separate."""

from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace
from typing import Literal

import pytest
import spacy
from spacy.tokens import Doc, MorphAnalysis

from corpus_structure.ingest import annotations
from corpus_structure.ingest.annotations import (
    AnnotationInput,
    AnnotationProfile,
    AnnotationUnavailable,
    annotate,
)
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
    monkeypatch.setattr(annotations, "pipeline", lambda _: nlp)
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


def test_prepared_unicode_whitespace_math_and_reference_coordinates_survive_wrong_pos(controlled):
    text = " X  X\né e\u0301 x+y [3]."
    block = Block(text, ((11, 14),), (), ((15, 18),))
    pieces = (
        ProjectedPiece("#/texts/1", 100, 111, "native_text"),
        ProjectedPiece("#/texts/formula", 111, 114, "native_text"),
        ProjectedPiece("#/texts/1", 114, 115, "native_text"),
        ProjectedPiece("#/texts/reference", 115, 118, "native_text"),
        ProjectedPiece("#/texts/1", 118, 119, "native_text"),
    )
    request = item(controlled, text, block=block, pieces=pieces)
    (product,) = annotate((request,))
    assert [(row.start, row.end) for row in product.tokens] == [
        (100, 101),
        (101, 102),
        (103, 104),
        (104, 105),
        (105, 106),
        (106, 107),
        (108, 110),
        (111, 114),
        (115, 118),
        (118, 119),
    ]
    assert [(row.start, row.end) for row in product.sentences] == [(101, 119)]
    math, reference = product.tokens[7:9]
    assert (math.role, math.pos, math.piece_indices) == ("math", "VERB", (1,))
    assert product.native_pieces[math.piece_indices[0]].item_ref == "#/texts/formula"
    assert (reference.role, reference.piece_indices) == ("reference", (3,))
    assert product.native_pieces[reference.piece_indices[0]].item_ref == "#/texts/reference"
    assert [(product.tokens[index].start, product.tokens[index].lemma) for index in (1, 3)] == [
        (101, "lemma:1"),
        (104, "lemma:3"),
    ]
    assert product.tokens[7].morphology == ("VerbForm=Fin",)
    assert product.tokens[7].dependency == "dep" and product.tokens[7].head == 0
    assert {column.status for column in product.availability} == {"complete"}
    assert product.source == pin()


def test_annotation_reuses_layout_without_tokenization_and_batches_pinned_block_contexts(
    controlled,
):
    requests = (
        item(controlled, "X.", start=10, identity=1, block_id="p:1"),
        item(controlled, "X.", start=20, identity=2, block_id="li:1", kind="list_item"),
        item(controlled, "X.", start=30, identity=3, block_id="cell:1", kind="table_cell"),
    )
    controlled.tokenizer = lambda _: pytest.fail("annotation retokenized a prepared layout")
    products = tuple(
        annotate(iter(requests), AnnotationProfile(SentenceConfig(exclude=("ner",), batch_size=2)))
    )
    assert controlled.calls == [(True, 2, 1)]
    assert [
        (result.source.source_view_id, result.block_id, result.kind) for result in products
    ] == [
        (1, "p:1", "paragraph"),
        (2, "li:1", "list_item"),
        (3, "cell:1", "table_cell"),
    ]
    assert [[(row.start, row.end) for row in result.sentences] for result in products] == [
        [(10, 12)],
        [(20, 22)],
        [(30, 32)],
    ]
    assert all(result.tokens[0].head == 0 for result in products)


def test_empty_block_has_explicit_not_applicable_availability(controlled):
    (product,) = annotate((item(controlled, ""),))
    assert product.tokens == product.sentences == ()
    assert {column.status for column in product.availability} == {"not_applicable"}


def test_retained_native_view_restores_exact_columns_and_absolute_heads(controlled):
    from corpus_structure.ingest.annotation_views import annotation_view

    request = item(controlled, " X  X\né e\u0301 x+y [3].")
    (product,) = annotate((request,))
    controlled.tokenizer = lambda _: pytest.fail("retained consumer retokenized")
    view = annotation_view(product, request.block.text, controlled.vocab)
    assert view.doc.text == request.block.text
    assert [token.head.i for token in view.doc] == [0] * len(product.tokens)
    assert [(token.lemma_, token.dep_) for token in view.doc] == [
        (f"lemma:{i}", "ROOT" if i == 0 else "dep") for i in range(len(product.tokens))
    ]
    with pytest.raises(ValueError, match="text differs"):
        annotation_view(product, request.block.text.replace("\n", " "), controlled.vocab)
    with pytest.raises(AnnotationUnavailable, match="columns"):
        annotation_view(replace(product, availability=()), request.block.text, controlled.vocab)
    with view.doc.retokenize() as retokenizer:
        retokenizer.merge(view.doc[1:3])
    with pytest.raises(ValueError, match="population changed"):
        view.check_layout()


def test_retained_matchers_preserve_overlaps_and_source_coordinates(controlled):
    from corpus_structure.ingest.annotation_views import annotation_view
    from corpus_structure.methods.annotation_rules import PreparedAnnotationRules

    request = item(controlled, "X X .", start=100)
    (product,) = annotate((request,))
    view = annotation_view(product, request.block.text, controlled.vocab)
    rules = PreparedAnnotationRules(
        controlled.vocab,
        token_rules={"cue": [[{"TEXT": "X"}]]},
        phrase_rules={"name": [("X", "X")]},
        dependency_rules={
            "role": [
                [
                    {"RIGHT_ID": "root", "RIGHT_ATTRS": {"DEP": "ROOT"}},
                    {
                        "LEFT_ID": "root",
                        "REL_OP": ">",
                        "RIGHT_ID": "other",
                        "RIGHT_ATTRS": {"TEXT": "X"},
                    },
                ]
            ]
        },
    )
    matches = rules.match(view)
    assert [(m.rule, m.extents) for m in matches[:3]] == [
        ("cue", ((100, 101),)),
        ("cue", ((102, 103),)),
        ("name", ((100, 101), (102, 103))),
    ]
    assert matches[-1].mechanism == "dependency" and matches[-1].nodes == (0, 1)
    assert all(m.dependency_digest == product.dependency_digest for m in matches)


def test_products_are_detached_immutable_and_do_not_copy_passages_into_rows(controlled):
    (product,) = annotate((item(controlled),))
    assert not hasattr(product, "text")
    assert not hasattr(product.tokens[0], "text")
    for target, attribute, value in (
        (product.tokens[0], "lemma", "changed"),
        (product.source, "membership", "direct"),
    ):
        with pytest.raises(FrozenInstanceError):
            setattr(target, attribute, value)


def test_missing_required_components_are_explicit_and_sentence_only_default_is_preserved(
    controlled,
):
    assert SentenceConfig().exclude == ("ner", "lemmatizer")
    assert AnnotationProfile().configuration.exclude == ("ner",)
    controlled.pipe_names = ["tok2vec", "tagger", "parser", "attribute_ruler"]
    with pytest.raises(AnnotationUnavailable, match="missing required components") as failure:
        tuple(annotate((item(controlled),)))
    assert failure.value.missing_components == ("lemmatizer",)
    assert controlled.calls == []


@pytest.mark.parametrize(
    "omission,attribute,status", [("lemma", "LEMMA", "partial"), ("dependency", "DEP", "absent")]
)
def test_a_doc_object_or_component_names_do_not_establish_annotation_availability(
    controlled, omission, attribute, status
):
    controlled.omit = omission
    with pytest.raises(AnnotationUnavailable, match="incomplete") as failure:
        tuple(annotate((item(controlled),)))
    assert [
        (column.attribute, column.status)
        for column in failure.value.availability
        if column.attribute == attribute
    ] == [
        (attribute, status),
    ]


def test_replay_uses_same_source_layout_and_profile_dependencies(controlled):
    request = item(controlled)
    first, second = annotate((request, request))
    assert first == second
    assert first.dependency_digest == second.dependency_digest
    changes = (
        replace(request, source=replace(request.source, projection_digest="d" * 64)),
        replace(request, source=replace(request.source, recipe_digest="e" * 64)),
        replace(request, source=replace(request.source, membership="direct")),
        replace(
            request,
            source=replace(
                request.source, native_product=ProductReference(18, "integrated", "f" * 64)
            ),
        ),
        replace(request, block_id="paragraph:2"),
        replace(request, layout=replace(request.layout, recipe="layout-recipe-2")),
        replace(request, native_pieces=(replace(request.native_pieces[0], item_ref="#/texts/2"),)),
    )
    assert all(
        next(annotate((changed,))).dependency_digest != first.dependency_digest
        for changed in changes
    )
    changed_profile = AnnotationProfile(
        SentenceConfig(exclude=("ner",), model_version="fixture-other-model")
    )
    assert next(annotate((request,), changed_profile)).dependency_digest != first.dependency_digest
    controlled.config = SimpleNamespace(to_str=lambda: "changed-component-config")
    assert next(annotate((request,))).dependency_digest != first.dependency_digest


def test_native_table_cell_and_synthetic_boundaries_are_retained_once(controlled):
    pieces = (
        ProjectedPiece("#/tables/0", 100, 101, "native_text", 3, "cell_text"),
        ProjectedPiece(None, 101, 102, "synthetic_separator"),
        ProjectedPiece("#/tables/0", 102, 103, "native_text", 4, "cell_text"),
    )
    (product,) = annotate((item(controlled, "X\nX", kind="table_cell", pieces=pieces),))
    assert product.native_pieces == pieces
    assert [(row.start, row.end, row.piece_indices) for row in product.tokens] == [
        (100, 101, (0,)),
        (101, 102, (1,)),
        (102, 103, (2,)),
    ]


def test_stale_layout_and_changed_native_atom_roles_refuse(controlled):
    request = item(controlled)
    with pytest.raises(ValueError, match="regenerate"):
        tuple(annotate((replace(request, layout=replace(request.layout, text_digest="wrong")),)))
    with pytest.raises(ValueError, match="atom roles differ"):
        replace(request, block=Block("X X.", ((0, 1),), (), ()))


@pytest.mark.parametrize(
    "pieces",
    [
        (),
        (ProjectedPiece("#/texts/1", 100, 103, "native_text"),),
        (ProjectedPiece("#/texts/1", 99, 104, "native_text"),),
        (ProjectedPiece(None, 100, 104, "native_text"),),
    ],
)
def test_incomplete_or_incompatible_native_piece_custody_refuses(controlled, pieces):
    with pytest.raises(ValueError, match="source-bound block"):
        item(controlled, pieces=pieces)


def test_pipeline_retokenization_cannot_silently_reassign_atom_positions(controlled, monkeypatch):
    request = item(controlled, "X X", block=Block("X X", ((0, 3),), (), ()))

    def retokenized(items, **kwargs):
        for _, source in items:
            yield Doc(controlled.vocab, words=["X", "X"], spaces=[True, False]), source

    monkeypatch.setattr(controlled, "pipe", retokenized)
    with pytest.raises(ValueError, match="changed the prepared source layout"):
        tuple(annotate((request,)))


def test_real_pipeline_version_mismatch_reuses_existing_deterministic_refusal():
    from corpus_structure.ingest.sentences import SentenceConfigError

    with pytest.raises(SentenceConfigError, match="spaCy"):
        tuple(
            annotate((), AnnotationProfile(SentenceConfig(spacy_version="0.0.0", exclude=("ner",))))
        )


def test_display_only_formula_retains_absolute_scope_and_native_identity_despite_wrong_pos(
    controlled,
):
    block = Block("x + y", (), ((0, 5),), ())
    request = item(
        controlled,
        "x + y",
        start=200,
        block=block,
        pieces=(ProjectedPiece("#/texts/display-formula", 200, 205, "native_text"),),
    )
    (product,) = annotate((request,))
    assert product.display_spans == ((200, 205),)
    assert [(token.start, token.end, token.pos) for token in product.tokens] == [
        (200, 201, "VERB"),
        (202, 203, "VERB"),
        (204, 205, "VERB"),
    ]
    assert [(sentence.start, sentence.end) for sentence in product.sentences] == [(200, 205)]
    assert all(token.piece_indices == (0,) for token in product.tokens)
    assert product.native_pieces[0].item_ref == "#/texts/display-formula"
