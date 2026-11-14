"""Controlled inputs and builders shared by the predicate frames consumers."""

from typing import Any, Literal

import pytest

from corpus_structure.ingest.annotations import AnnotationInput, AnnotationProfile, annotate
from corpus_structure.ingest.pdf_hierarchy import ProjectedPiece
from corpus_structure.ingest.sentences import Block, pipeline, prepare_layout
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.source_contexts import NativeSourcePin

_PREFIX = "outside the block: "


@pytest.fixture(scope="module")
def profile():
    return AnnotationProfile()


def retained(
    text,
    profile,
    *,
    block_id="paragraph:3",
    kind: Literal["paragraph", "list_item", "table_cell", "caption"] = "paragraph",
    pieces=None,
):
    block = Block(text, (), (), ())
    nlp: Any = pipeline(profile.configuration)
    native_profile = nlp.selection().native
    layout = prepare_layout(nlp, block, start=len(_PREFIX))
    source = NativeSourcePin(
        7,
        "source:7",
        ProductReference(17, "integrated", "a" * 64),
        "#/groups/7",
        "descendants",
        "b" * 64,
        "c" * 64,
        3,
    )
    if pieces is None:
        pieces = (ProjectedPiece("#/texts/3", len(_PREFIX), len(_PREFIX + text), "native_text"),)
    request = AnnotationInput(source, block_id, kind, block, layout, pieces)
    (product,) = annotate((request,), profile)
    from methods.primary_reading_fixture import primary_product

    return _PREFIX + text, primary_product(
        _PREFIX + text, product, profile, native_profile=native_profile
    )


def strings(text, span):
    return tuple(text[a:b] for a, b in span.extents)
