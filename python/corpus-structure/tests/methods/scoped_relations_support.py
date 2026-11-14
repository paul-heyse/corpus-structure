"""Controlled inputs and builders shared by the scoped relations consumers."""

from dataclasses import replace
from typing import Any

from corpus_structure.methods.scoped_relations import discover_relations as _discover_relations
from corpus_structure.semantic.structural_products import (
    ExternalSourceRef,
    StructuralInput,
    StructuralPassage,
)


def discover_relations(frame, **kwargs):
    from dataclasses import fields

    from corpus_structure.methods.native_evidence_layers import PrimaryAnnotationProduct
    from corpus_structure.methods.source_preparation import prepare_source
    from methods.navigation_fixture import primary_navigation, view_from_frame

    view = view_from_frame(frame)
    native_profile = kwargs.pop("annotation_native_profile", None)
    if "annotations" in kwargs:
        products = tuple(kwargs["annotations"])
    else:
        from corpus_structure.ingest.annotations import AnnotationProfile
        from corpus_structure.ingest.sentences import pipeline

        profile = AnnotationProfile()
        nlp: Any = pipeline(profile.configuration)
        native_profile = nlp.selection().native
        products = prepare_source(view, profile=profile, annotations_only=True).annotations
    layers = dict(kwargs.pop("primary_layers", {}))
    layers.update(
        primary_navigation(view, products, formal=not layers, native_profile=native_profile)
    )
    kwargs["annotations"] = tuple(
        PrimaryAnnotationProduct(
            primary_layers=layers,
            **{field.name: getattr(product, field.name) for field in fields(product)},
        )
        for product in products
    )
    kwargs.pop("predicate_version", None)
    kwargs.pop("named_link_version", None)
    output = _discover_relations(
        frame, primary_layers=layers, predicate_version="6", named_link_version="4", **kwargs
    )
    return dict(output, _primary_layers=layers)


def complete_native_fields(view):
    nodes = {node["self_ref"]: dict(node) for node in view.items}
    for piece in view.pieces:
        if piece.get("kind") == "native_text" and piece.get("cell_index") is None:
            nodes[piece["item_ref"]]["text"] = view.text[piece["start"] : piece["end"]]
    return replace(view, items=tuple(nodes.values()))


def original_inputs(view):
    ref = view.ref
    original = ExternalSourceRef(
        project_id="original",
        run_id=10,
        cut_id=11,
        release_id="r",
        result_revision=1,
        source_view_id=ref.id,
        native_task_id=ref.native_product.task_id,
        native_product_key=ref.native_product.product_key,
        native_content_digest=ref.native_product.content_digest,
        projection_digest=ref.projection_digest,
        recipe_digest=ref.recipe_digest,
        coordinate_version=3,
    )
    return StructuralInput(
        question="Retain original annotations",
        scope="s",
        inventory_id="i",
        policy_id="p",
        sources=(original,),
        passages=(
            StructuralPassage(
                passage_id="original",
                source_ref=original.identity,
                start=0,
                end=len(view.text),
                text=view.text,
                scope="s",
            ),
        ),
        dependencies=("annotation:original",),
    )
