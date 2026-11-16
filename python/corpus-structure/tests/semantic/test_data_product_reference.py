"""Shared nominal addresses retain exact governed product/member qualification."""

from pathlib import Path

import pytest

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.data_product_reference import (
    DataProductMemberReference,
    DataProductReference,
    member_reference,
    read_member_reference,
    reference_inputs,
)
from corpus_structure.semantic.identity import canonical_bytes


def test_shared_reference_schema_matches_actual_addresses_and_refuses_unqualified_members():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = reference_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    assert reference_inputs(bundle) is bundle
    prepared = prepare_release(bundle)
    product = DataProductReference("product:actual")
    member = DataProductMemberReference(product, "token:one")
    for name, value in (
        ("DdoSemanticProductReference", product.values()),
        ("DdoSemanticMemberReference", member.values()),
    ):
        assert prepared.validate_json(name, canonical_bytes(value)).model_dump() == value
    for value in ({"member_id": "token:one"}, {"product_id": "p", "member_id": ""}):
        with pytest.raises(ValueError):
            prepared.validate_json("DdoSemanticMemberReference", canonical_bytes(value))
    other = DataProductMemberReference(DataProductReference("product:other"), "token:one")
    assert member.identity != other.identity


def test_member_decoder_retains_qualified_identity_and_refuses_other_address_spaces():
    left = member_reference(DataProductReference("product:left"), "token:one")
    right = member_reference(DataProductReference("product:right"), "token:one")
    assert left != right and left.identity != right.identity
    assert read_member_reference(left.values()) == left
    assert left.values() == {"product_id": "product:left", "member_id": "token:one"}
    for value in (
        {
            "layer": {"task_id": 9, "product_key": "report", "content_digest": "a" * 64},
            "local_id": "token:one",
        },
        {**left.values(), "local_id": "token:one"},
        {"product_id": "product:left", "member_id": ""},
        {"product_id": True, "member_id": "token:one"},
    ):
        with pytest.raises(ValueError):
            read_member_reference(value)
