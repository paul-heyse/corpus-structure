"""Shared controlled inputs and builders for formal products support."""

from pathlib import Path

import pytest

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.formal_evidence import grammar_identity
from corpus_structure.semantic.formal_products import (
    FrozenFormalSource,
    formal_product_inputs,
    prepare_formal_evidence,
)


@pytest.fixture(scope="module")
def profile():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = formal_product_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    from corpus_structure.semantic.composed import data_operation_dependencies
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.formal_products import formal_operation_sources
    from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies

    prepared = prepare_release(
        bundle,
        data_operation_dependencies(
            ResolvedDependencies(), python_sources=formal_operation_sources()
        ),
        PreparationProfile(version="semantic-2"),
    )
    return prepare_formal_evidence(
        prepared, bound_data_operation_model(prepared), grammar=grammar_identity()
    )


def selected(profile, text="Quantity: 2 kg\nusing the equation x = 2.", **changes):
    value = dict(
        source=dict(
            document="document:original-content",
            section_pointer="#/groups/0",
            membership="descendants",
            projection="b" * 64,
        ),
        text=text,
        pieces=[
            dict(
                kind="native_text",
                start=0,
                end=len(text),
                item_ref="#/texts/0",
                source_field="text",
            )
        ],
        items=[
            dict(self_ref="#/texts/0", label="text", text=text, orig=text, prov=[dict(page_no=1)])
        ],
        recognition=[],
        selectors=[dict(projection="b" * 64, native_pointer="#/texts/0", start=0, end=len(text))],
    )
    value.update(changes)
    return acquire_source(profile, value)


def acquire_source(profile, value):
    from corpus_structure.semantic.source_products import native_projection_identity

    projection = native_projection_identity(
        value["text"], value["pieces"], value["items"], value.get("recognition", ())
    )
    value["source"]["projection"] = projection
    for selector in value["selectors"]:
        selector["projection"] = projection
    return FrozenFormalSource.acquire(profile.prepared, value)
