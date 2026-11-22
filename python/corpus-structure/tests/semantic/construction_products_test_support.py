"""Shared authored scenarios and fixtures for construction products test support."""

from pathlib import Path
from typing import TypedDict

import pytest

from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.construction_products import (
    PreparedConstructionProfile,
    construction_product_inputs,
)
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
from corpus_structure.semantic.formal_evidence import grammar_identity
from corpus_structure.semantic.formal_products import (
    formal_operation_sources,
    prepare_formal_evidence,
)
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.types import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)


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


class _OriginalInputSupport(TypedDict):
    support_episodes: tuple[str, ...]
    support_evidence: bytes
    support_references: tuple[ComputationalSupportReference, ...]


def original_input_support(product, formal, *, sentences=None) -> _OriginalInputSupport:
    """Controlled original ledger for isolated acquired-consumer tests, not native evidence."""
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.producer_requirements import SelectedProducerContract
    from corpus_structure.semantic.reference_resolution import ProducingReferenceInput

    references = [
        ProducingReferenceInput(
            "formal",
            item.semantic_id,
            item._payload.kind_contract,
            occurrence=str(position),
            occurrence_position=True,
        )
        for position, item in enumerate(formal)
    ]
    if sentences is not None:
        kind = sentences.prepared.index.definitions["DdoSourceAnnotations"].iri
        kind_contract = next(
            identity.key
            for identity in sentences.model.identities
            if (identity.owner, identity.domain) == (kind, "kind")
        )
        references.append(
            ProducingReferenceInput("sentences", sentences.semantic_id, kind_contract)
        )
    producer = SelectedProducerContract(
        version="selected-producer-contract-v1",
        derivation_id="controlled-construction-origin",
        release_id=product.prepared.release_id,
        runtime_id="controlled-runtime",
        publication_receipt=True,
        cpu_receipt=False,
        admitted_effects=(),
        validity_families=(),
        reference_inputs=tuple(references),
        reference_inputs_complete=True,
    )
    return {
        "support_episodes": (producer.derivation_id,),
        "support_evidence": canonical_bytes(
            dict(producer_contract=producer.model_dump(mode="json"))
        ),
        "support_references": (
            ComputationalSupportReference(derivation_id=producer.derivation_id),
        ),
    }
