"""Shared authored scenarios and fixtures for construction products test support."""

from pathlib import Path

import pytest

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.construction_products import (
    PreparedConstructionProfile,
    construction_product_inputs,
)
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.formal_evidence import grammar_identity
from corpus_structure.semantic.formal_products import (
    formal_operation_sources,
    prepare_formal_evidence,
)
from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies


@pytest.fixture(scope="module")
def profiles():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = construction_product_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    prepared = prepare_release(
        bundle,
        data_operation_dependencies(
            ResolvedDependencies(), python_sources=formal_operation_sources()
        ),
        PreparationProfile(version="semantic-2"),
    )
    model = bound_data_operation_model(prepared)
    return prepare_formal_evidence(
        prepared, model, grammar=grammar_identity()
    ), PreparedConstructionProfile(prepared, model)


def publication_context(source, *, document=False):
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.source_products import source_subject

    value = source.value
    return SubjectContext(
        "family-test",
        value["source"]["document"] if document else source_subject(value["source"]),
        value["source"]["document"],
        canonical_bytes({"source": value["source"], "selectors": value["selectors"]}),
        subject_definition="original-source-view",
    )
