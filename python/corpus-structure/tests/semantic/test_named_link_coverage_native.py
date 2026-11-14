"""Native navigation guards conserve retained primary refs, choices and literal pieces."""

from copy import deepcopy

import pytest
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.identity import canonical_bytes
from semantic.named_link_coverage_native_support import (
    native_navigation_call as native_navigation_call,
)
from semantic.named_link_coverage_native_support import (
    primary_fixture as primary_fixture,
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
    commit_db_engine, mutation
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
    with commit_db_engine.connect() as conn, conn.begin():
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
