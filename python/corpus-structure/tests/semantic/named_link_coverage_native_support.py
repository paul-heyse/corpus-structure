"""Shared controlled inputs and builders for named link coverage native support."""

import json
from dataclasses import replace

from sqlalchemy import text

from corpus_structure.semantic.identity import canonical_bytes


def primary_fixture(literal, *, label="text"):
    from methods.m1_source_preparation_support import source
    from methods.navigation_fixture import primary_navigation
    from methods.scoped_relations_support import complete_native_fields

    from corpus_structure.methods.witnessed_source_links import navigation_index

    view = complete_native_fields(source(literal, labels=(label,)))
    view = replace(view, items=tuple(dict(item, content_layer="body") for item in view.items))
    layers = primary_navigation(view)
    indexed = navigation_index(layers, view.ref.projection_digest, source_view_id=view.ref.id)
    wire = {canonical_bytes(pin.values()).decode(): layer.payload for pin, layer in layers.items()}
    physical = dict(
        id=view.ref.id,
        key=view.ref.key,
        projection_digest=view.ref.projection_digest,
        recipe_digest=view.ref.recipe_digest,
        native_task_id=view.ref.native_product.task_id,
        native_product_key=view.ref.native_product.product_key,
        native_content_digest=view.ref.native_product.content_digest,
        projection=dict(text=view.text, pieces=view.pieces),
    )
    return wire, indexed, physical


def native_navigation_call(
    conn, function, layers, reference, physical, *, role=None, field_start=None
):
    # The function name is a test-owned constant. No helper installs or replaces native policy.
    args = "layers,ref,ops.primary_navigation_node(layers,ref,'[]',view_),view_"
    if role is not None:
        args = "layers,ref,ops.primary_navigation_node(layers,ref,'[]',view_),:role,view_"
    if field_start is not None:
        args += ",:field_start"
    query = text(
        "WITH parameters AS (SELECT CAST(:layers AS jsonb) layers,CAST(:ref AS jsonb) ref,"
        "jsonb_populate_record(NULL::kb.source_view,CAST(:physical AS jsonb)) view_) "
        f"SELECT ops.{function}({args}) FROM parameters"
    )
    return conn.scalar(
        query,
        dict(
            layers=json.dumps(layers),
            ref=json.dumps(reference),
            physical=json.dumps(physical),
            role=role,
            field_start=field_start,
        ),
    )
