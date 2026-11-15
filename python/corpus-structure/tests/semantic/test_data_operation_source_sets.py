"""Frozen cross-source pins retain original references and reject widened custody."""

from dataclasses import replace
from decimal import Decimal

import pytest

from corpus_structure.semantic.data_operation_source_sets import (
    FrozenSourceSet,
    SourceSetEntry,
    read_source_sets,
    source_sets_record,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_product_reference import DataProductReference, DataProductMemberReference


def entry(*, product="projection:one", source="source:one", member="member:one"):
    return SourceSetEntry.from_semantic_source(
        DataProductMemberReference(DataProductReference(product), member),
        context=SubjectContext("project", "view:one", source, b'{"page":1}', subject_definition="document"),
    )


def test_source_set_keeps_exact_original_reference_and_roundtrips():
    first = entry()
    second = entry(product="projection:two", member="member:two")
    scope = FrozenSourceSet("inputs", (second, first))
    encoded = source_sets_record((scope,))
    assert encoded["inputs"][0]["product"] == "projection:one"
    assert encoded["inputs"][0]["source_reference"] == DataProductMemberReference(DataProductReference("projection:one"), "member:one").identity
    assert read_source_sets(encoded)[0].entries == (first, second)
    with pytest.raises(ValueError, match="unique"):
        FrozenSourceSet("inputs", (first, first))
    with pytest.raises(ValueError, match="qualified"):
        replace(first, project_id="")
    with pytest.raises(ValueError, match="product/member"):
        replace(first, source_reference="forged")
    with pytest.raises(ValueError, match="canonical"):
        replace(first, analyzed_scope=canonical_bytes([1]))


def test_source_set_normalizes_exact_fraction_and_exponent_scope_without_float_roundtrip():
    first = replace(entry(), analyzed_scope=b'{"coordinate":0.123456789012345678901,"scale":1e+30}')
    encoded = source_sets_record((FrozenSourceSet("inputs", (first,)),))
    assert encoded["inputs"][0]["analyzed_scope"] == {
        "coordinate": Decimal("0.123456789012345678901"),
        "scale": Decimal("1e30"),
    }
    assert read_source_sets(encoded)[0].entries == (first,)
