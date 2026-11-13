"""Nominal member contracts derive from typed edges, never a mirror inventory."""

from dataclasses import replace

import pytest

from corpus_structure.semantic.data_operation_member_contracts import derive_member_kinds
from corpus_structure.semantic.data_operation_model import (
    MODEL_VERSION,
    EffectiveDataOperationModel,
    EffectiveKind,
    SemanticEdge,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.types import PreparationError


def fixture_model():
    kinds = tuple(
        EffectiveKind(name, name, "class", canonical_bytes({"abstract": name == "Body"}))
        for name in ("Container", "Packet", "Body", "Concrete", "Nested", "Unrelated")
    )
    properties = (
        EffectiveKind(
            "Container/property/members",
            "members",
            "property",
            canonical_bytes({"name": "members", "range": "Packet", "multivalued": True}),
        ),
        EffectiveKind(
            "Packet/property/body",
            "body",
            "property",
            canonical_bytes({"name": "body", "range": "Body", "multivalued": False}),
        ),
    )
    edges = (
        SemanticEdge("Container", properties[0].semantic_id, "property", "members"),
        SemanticEdge(properties[0].semantic_id, "Packet", "range"),
        SemanticEdge("Packet", properties[1].semantic_id, "property", "body"),
        SemanticEdge(properties[1].semantic_id, "Body", "range"),
        SemanticEdge("Concrete", "Body", "inherits"),
        SemanticEdge("Nested", "Concrete", "inherits"),
    )
    return EffectiveDataOperationModel(MODEL_VERSION, (*kinds, *properties), (), (), (), edges)


def test_member_contracts_follow_nominal_body_range_and_transitive_declared_subtypes():
    model = fixture_model()
    assert derive_member_kinds(model, "Container") == ("Concrete", "Nested")
    assert derive_member_kinds(model, "Unrelated") == ()
    # Runtime spelling does not infer container or packet capability.
    assert derive_member_kinds(
        replace(model, kinds=tuple(replace(kind, name="Random") for kind in model.kinds)),
        "Container",
    ) == ("Concrete", "Nested")


def test_unknown_member_ranges_and_incomplete_subtypes_refuse():
    model = fixture_model()
    with pytest.raises(PreparationError, match="complete nominal kind"):
        derive_member_kinds(
            replace(
                model, kinds=tuple(kind for kind in model.kinds if kind.semantic_id != "Concrete")
            ),
            "Container",
        )
    with pytest.raises(PreparationError, match="complete nominal kind"):
        derive_member_kinds(
            replace(
                model,
                kinds=tuple(
                    replace(kind, complete=False) if kind.semantic_id == "Nested" else kind
                    for kind in model.kinds
                ),
            ),
            "Container",
        )
    with pytest.raises(PreparationError, match="effective graph"):
        derive_member_kinds(
            replace(
                model,
                edges=tuple(
                    edge
                    for edge in model.edges
                    if not (edge.source == "Packet/property/body" and edge.relation == "range")
                ),
            ),
            "Container",
        )


def test_generic_schema_records_do_not_become_member_containers_by_field_spelling():
    model = fixture_model()
    wire = replace(
        model.kinds[0],
        facts=canonical_bytes(
            {"json_schema": {"type": "object", "properties": {"members": {"type": "array"}}}}
        ),
    )
    assert derive_member_kinds(replace(model, kinds=(wire, *model.kinds[1:])), "Container") == ()
