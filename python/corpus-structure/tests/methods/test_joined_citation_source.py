"""Joined named-link cues retain exact source-owned annotation and native pieces."""

from dataclasses import replace
from hashlib import sha256

import pytest

from corpus_structure.methods.source_preparation import prepare_source
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.structural_products import (
    ExternalSourceRef,
    StructuralPassage,
)
from methods.m1_source_preparation_support import source
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
    view = source("fixture", labels=("text",))
    digest = sha256(
        canonical_bytes(
            dict(
                text=text,
                pieces=pieces,
                items=[item["self_ref"] for item in nodes],
                ancestors=[],
                health={},
            )
        )
    ).hexdigest()
    return replace(
        view, ref=replace(view.ref, projection_digest=digest), text=text, pieces=pieces, items=nodes
    )


def _joined_production(view, *, batch_size):
    release = "release:joined-source-control"
    named_version = "4"
    frame = native_source_frame(view, ())
    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.ingest.sentences import SentenceConfig, pipeline

    profile = AnnotationProfile(SentenceConfig(batch_size=batch_size, exclude=("ner",)))
    native_profile = pipeline(profile.configuration).selection().native
    annotations = prepare_source(view, profile=profile, annotations_only=True)
    assert not annotations.annotation_errors
    (block,) = annotations.annotations
    assert block.block_id == "#/texts/0"
    assert block.native_pieces[1].item_ref == "#/texts/1"
    ref = ExternalSourceRef(
        project_id="fixture",
        run_id=1,
        cut_id=1,
        release_id=release,
        result_revision=0,
        source_view_id=view.ref.id,
        native_task_id=view.ref.native_product.task_id,
        native_product_key=view.ref.native_product.product_key,
        native_content_digest=view.ref.native_product.content_digest,
        projection_digest=view.ref.projection_digest,
        recipe_digest=view.ref.recipe_digest,
        coordinate_version=3,
    )
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
        annotation_origin_task_id=41,
        passages=(passage,),
        predicate_version="5",
        witnessed_links_enabled=True,
        named_link_version=named_version,
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
