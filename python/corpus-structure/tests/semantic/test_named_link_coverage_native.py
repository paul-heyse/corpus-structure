"""Native navigation guards conserve retained primary refs, choices and literal pieces."""

import json
from copy import deepcopy
from dataclasses import replace

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.identity import canonical_bytes


def primary_fixture(literal, *, label="text"):
    from methods.navigation_fixture import primary_navigation
    from methods.test_m1_source_preparation import source
    from methods.test_scoped_relations import complete_native_fields

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


@pytest.mark.parametrize(
    "mutation",
    (
        None,
        "foreign_layer",
        "foreign_node",
        "foreign_view",
        "native_index",
        "missing_cue",
        "repeated_cue",
        "clipped_source",
    ),
)
def test_native_named_navigation_conserves_primary_identity_and_role_source(
    semantic_db_engine, mutation
):
    literal = 'Use definition ID "PX:18.1" as defined in Section 6.2.'
    layers, index, physical = primary_fixture(literal)
    (record,) = index.select("named_link")
    reference = record.reference.values()
    node = next(
        a
        for a in layers[canonical_bytes(reference["layer"]).decode()]["annotations"]
        if a["local_id"] == reference["local_id"]
    )
    if mutation == "foreign_layer":
        reference["layer"]["content_digest"] = "f" * 64
    elif mutation == "foreign_node":
        reference["local_id"] = "unknown-node"
    elif mutation == "foreign_view":
        physical["id"] += 1
    elif mutation == "native_index":
        node["navigation"]["native_tokens"][0]["index"] += 1
    elif mutation == "missing_cue":
        node["navigation"]["roles"] = [r for r in node["navigation"]["roles"] if r["role"] != "cue"]
    elif mutation == "repeated_cue":
        node["navigation"]["roles"].append(
            deepcopy(next(r for r in node["navigation"]["roles"] if r["role"] == "cue"))
        )
    elif mutation == "clipped_source":
        physical["projection"]["text"] = literal[:2]
    with semantic_db_engine.connect() as conn, conn.begin():
        if mutation is None:
            extents = native_navigation_call(
                conn, "primary_navigation_role_extents", layers, reference, physical, role="cue"
            )
            assert [(e["start"], e["end"], e["text"]) for e in extents] == [
                (
                    literal.index("as defined in"),
                    literal.index("as defined in") + len("as defined in"),
                    "as defined in",
                )
            ]
            subject = native_navigation_call(
                conn,
                "primary_navigation_role_extents",
                layers,
                reference,
                physical,
                role="definition_subject",
            )
            assert [e["text"] for e in subject] == ["PX:18.1"]
        else:
            with pytest.raises(DBAPIError) as refused:
                native_navigation_call(
                    conn, "primary_navigation_role_extents", layers, reference, physical, role="cue"
                )
            assert getattr(refused.value.orig, "sqlstate", None) == "23514"
