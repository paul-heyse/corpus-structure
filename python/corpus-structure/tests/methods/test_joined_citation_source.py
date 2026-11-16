"""Joined named-link cues retain exact source-owned annotation and native pieces."""

import pytest

from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.structural_products import (
    DeclaredStructuralSource,
    StructuralPassage,
)
from methods.m1_source_preparation_support import prepare_declared_source, projection
from methods.scoped_relations_support import discover_relations


def _joined_view():
    first, second = "For more detail, ", "see Section 6.1."
    text = first + second
    owner, cited, inline = "#/texts/0", "#/texts/1", "#/groups/2"
    pieces = (
        dict(kind="native_text", item_ref=owner, source_field="text", start=0, end=len(first)),
        dict(
            kind="native_text", item_ref=cited, source_field="text", start=len(first), end=len(text)
        ),
    )
    nodes = (
        dict(self_ref=owner, label="text", text=first, content_layer="body", parent={}),
        dict(self_ref=inline, label="inline", parent={"$ref": owner}),
        dict(
            self_ref=cited, label="text", text=second, content_layer="body", parent={"$ref": inline}
        ),
    )
    return projection(text, pieces=pieces, items=nodes)


def _joined_production(view, *, batch_size):
    frame = view
    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.ingest.sentences import SentenceConfig, pipeline

    profile = AnnotationProfile(SentenceConfig(batch_size=batch_size, exclude=("ner",)))
    native_profile = pipeline(profile.configuration).selection().native
    annotations = prepare_declared_source(view, profile=profile, annotations_only=True)
    assert not annotations.annotation_errors
    (block,) = annotations.annotations
    assert block.block_id == "#/texts/0"
    assert block.native_pieces[1].item_ref == "#/texts/1"
    ref = DeclaredStructuralSource.model_validate(frame.pin.values())
    passage = StructuralPassage(
        passage_id="cross-reference",
        source_ref=ref.identity,
        start=0,
        end=len(view.text),
        scope="fixture",
        text=view.text,
    )
    output = discover_relations(
        frame,
        annotations=annotations.annotations,
        annotation_native_profile=native_profile,
        annotation_profile=profile,
        passages=(passage,),
        witnessed_links_enabled=True,
    )
    return output


@pytest.mark.parametrize("batch_size", [64, 2])
def test_joined_citation_keeps_exact_annotation_owner_and_native_piece(batch_size):
    output = _joined_production(_joined_view(), batch_size=batch_size)
    (cue,) = [
        row
        for row in output["contributions"]
        if row["kind"] == "occurrence"
        and source_python(row["value"]).get("role") == "named_link_cue"
    ]
    assert cue["anchors"][0]["pointer"] == "#/texts/1"
    assert cue["anchors"][0]["source_piece"] == "see"
    witness = source_python(cue["value"])["named_cue"]
    assert witness["block"] == "#/texts/0"
