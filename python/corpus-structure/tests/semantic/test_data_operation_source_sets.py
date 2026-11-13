"""Frozen cross-source pins retain original references and reject widened custody."""

from dataclasses import replace

import pytest

from corpus_structure.semantic.data_operation_source_sets import (
    FrozenSourceSet,
    SourceSetEntry,
    read_source_sets,
    source_sets_record,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_products import ExternalSourceRef


def reference(project="project"):
    return ExternalSourceRef(
        project_id=project,
        run_id=1,
        cut_id=2,
        release_id="release",
        result_revision=0,
        source_view_id=3,
        native_task_id=4,
        native_product_key="native:key",
        native_content_digest="a" * 64,
        projection_digest="b" * 64,
        recipe_digest="c" * 64,
        coordinate_version=3,
    )


def entry(*, product="projection:one", source="source:one", member="member:one"):
    return SourceSetEntry.from_structural_source(
        reference(),
        original_source=source,
        subject="view:one",
        analyzed_scope=b'{"page":1}',
        product=product,
        member=member,
    )


def test_source_set_keeps_exact_original_reference_and_roundtrips():
    first = entry()
    second = entry(product="projection:two", member="member:two")
    scope = FrozenSourceSet("inputs", (second, first))
    encoded = source_sets_record((scope,))
    assert encoded["inputs"][0]["product"] == "projection:one"
    assert encoded["inputs"][0]["source_reference"] == reference().identity
    assert read_source_sets(encoded)[0].entries == (first, second)
    with pytest.raises(ValueError, match="unique"):
        FrozenSourceSet("inputs", (first, first))
    with pytest.raises(ValueError, match="identity/project"):
        replace(first, project_id="foreign")
    with pytest.raises(ValueError, match="identity/project"):
        replace(first, source_reference="forged")
    with pytest.raises(ValueError, match="canonical"):
        replace(first, analyzed_scope=canonical_bytes([1]))
