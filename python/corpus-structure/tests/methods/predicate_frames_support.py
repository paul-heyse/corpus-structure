"""Controlled inputs and builders shared by the predicate frames consumers."""

from typing import Any, Literal

import pytest

from corpus_structure.ingest.annotations import AnnotationInput, AnnotationProfile, annotate
from corpus_structure.ingest.pdf_hierarchy import ProjectedPiece
from corpus_structure.ingest.sentences import Block, pipeline, prepare_layout

_PREFIX = "outside the block: "


@pytest.fixture(scope="module")
def profile():
    return AnnotationProfile()


def retained(
    text,
    profile,
    *,
    block_id="#/paragraphs/3",
    kind: Literal["paragraph", "list_item", "table_cell", "caption"] = "paragraph",
    pieces=None,
):
    block = Block(text, (), (), ())
    nlp: Any = pipeline(profile.configuration)
    native_profile = nlp.selection().native
    layout = prepare_layout(nlp, block, start=len(_PREFIX))
    if pieces is None:
        pieces = (ProjectedPiece("#/texts/3", len(_PREFIX), len(_PREFIX + text), "native_text"),)
    from dataclasses import replace

    from methods.declared_primary_fixture import selected_source
    from methods.navigation_fixture import source_primary_products

    pieces = tuple(replace(p, source_field="text") if p.source_field is None else p for p in pieces)
    complete = _PREFIX + text
    spellings = {}
    for piece in pieces:
        spellings[piece.item_ref] = (
            spellings.get(piece.item_ref, "") + complete[piece.start : piece.end]
        )
    inline = block_id + "/inline"
    items = [
        dict(self_ref=block_id, label=kind, children=[{"$ref": inline}]),
        dict(
            self_ref=inline,
            label="inline",
            parent={"$ref": block_id},
            children=[{"$ref": pointer} for pointer in spellings],
        ),
        *(
            dict(
                self_ref=pointer, label="text", text=literal, orig=literal, parent={"$ref": inline}
            )
            for pointer, literal in spellings.items()
        ),
    ]
    _source, frame, _context = selected_source(
        complete,
        pieces=[
            dict(kind="synthetic_separator", start=0, end=len(_PREFIX)),
            *(p.to_wire() for p in pieces),
        ],
        items=items,
    )
    request = AnnotationInput(frame.pin, block_id, kind, block, layout, pieces)
    (product,) = annotate((request,), profile)
    primary = source_primary_products(
        frame, (product,), profile=profile, native_profile=native_profile
    )
    return complete, product, primary


def strings(text, span):
    return tuple(text[a:b] for a, b in span.extents)
