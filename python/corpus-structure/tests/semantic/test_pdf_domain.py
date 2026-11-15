"""Real PDF action projection and archived fixed-call correspondence, without a Run."""

import json
from dataclasses import replace
from hashlib import sha256

import pytest
from pydantic import ValidationError

from corpus_structure.semantic import PreparationProfile, ResolvedDependencies, prepare_release
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.operation_value_types import require_call_context
from corpus_structure.semantic.pdf_contracts import PreparedPdfContext, _boundary
from corpus_structure.semantic.pdf_domain import (
    PdfDomainContract,
    pdf_domain_artifacts,
    pdf_domain_sources,
)
from corpus_structure.semantic.pdf_domain_native import pdf_domain_native_sql
from corpus_structure.semantic.prepared_sql import prepare_sql
from corpus_structure.semantic.refusals import SemanticRefusal
from corpus_structure.semantic.types import SourceArtifact
from semantic.releases_support import source_bundle


@pytest.fixture(scope="module")
def domain():
    contract, *sources = pdf_domain_sources()
    return PdfDomainContract(contract.content, tuple(sources))


@pytest.fixture(scope="module")
def model(domain):
    from semantic.pdf_domain_support import bound_model
    return bound_model(domain)


def test_pdf_domain_projects_real_actions_and_native_schema_without_legacy_execution(domain):
    action = domain.require_operation("retain_pdf_original")
    assert action["implementation"]["owner"] == "semantic.pdf_contracts"
    action = domain.require_operation("begin_pdf_build")
    assert action["contract"]["calls"][0]["symbol"] == "ops.begin_pdf_build"
    with pytest.raises(ValueError, match="absent from archived PDF contract"):
        domain.require_operation("archive")
    assert all(not source.name.startswith("execution/") for source in domain.sources)
    context = PreparedPdfContext(
        "release:pdf", _boundary(domain.schema), domain,
        domain.source("schema/pdf_products").digest,
        SourceArtifact("pdf/staging-model.yaml", domain.source("implementation/pdf/staging-model.yaml").content),
    )
    assert (
        context.native_schema_digest
        == sha256(
            domain.source("implementation/pdf/docling-validation.schema.json").content
        ).hexdigest()
    )
    action = context.require_operation("prepare_native_document")
    assert isinstance(action, dict)
    assert action["contract"]["id"] == "prepare_native_document"
    assert "PdfNativeEnvelope" in context.boundary.index.definitions
    assert not hasattr(context, "execution")
    assert context.terminal_task_states == {"done", "empty", "failed", "cancelled"}


def test_pdf_domain_call_projection_checks_exact_variant_and_digest(domain, model):
    from corpus_structure.semantic._operation_calls import RETAIN_PDF_ORIGINAL_CONTRACT_DIGEST

    dependencies = ResolvedDependencies(
        (
            SourceArtifact("pdf-domain/contract.json", domain.content),
            *domain.sources,
        )
    )
    with pytest.raises(ValueError, match="not bound by a checked native PDF operation"):
        pdf_domain_artifacts(dependencies)
    artifacts = pdf_domain_artifacts(dependencies, model=model)
    prepared = prepare_release(source_bundle(), ResolvedDependencies(), PreparationProfile())
    prepared = replace(prepared, artifacts=(*prepared.artifacts, *artifacts))
    assert prepared.execution_model_id is None
    require_call_context(
        prepared, "retain_pdf_original", "retain_pdf_original", RETAIN_PDF_ORIGINAL_CONTRACT_DIGEST
    )
    with pytest.raises(SemanticRefusal, match="incompatible consumer"):
        require_call_context(prepared, "retain_pdf_original", "retain_pdf_original", "changed")
    with pytest.raises(SemanticRefusal, match="incompatible consumer"):
        require_call_context(
            prepared, "archive", "publish_release_archive", RETAIN_PDF_ORIGINAL_CONTRACT_DIGEST
        )
    changed = json.loads(domain.content)
    changed["inputs"][0]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="custody differs"):
        PdfDomainContract(canonical_bytes(changed), domain.sources)


def test_pdf_domain_native_checks_exact_frozen_facet_and_declared_action(domain):
    sql = pdf_domain_native_sql()
    assert len(prepare_sql(sql, source="PDF domain").statements) == 5
    assert sha256(domain.content).hexdigest() in sql
    assert "facet->'actions'->p_operation->'contract'->>'id'" in sql
    assert "sem.require_execution_operation" not in sql
    assert "current PDF domain contract is required" in sql
    assert "native-pdf-helper-bindings" in sql
    assert "pdf-domain/schema/pdf_products" not in sql  # One input prefix projection.


def test_pdf_domain_owns_observation_boundary_and_exact_published_read_calls(domain, model):
    from corpus_structure.semantic._operation_calls import (
        READ_PUBLISHED_SECTION_NODES_CONTRACT_DIGEST,
        READ_PUBLISHED_SECTIONS_CONTRACT_DIGEST,
    )

    boundary = _boundary(domain.schema)
    assert (
        boundary.index.definitions["PdfObservationProduct"].iri
        == "https://corpus-structure.dev/execution/PdfObservationProduct"
    )
    kind = boundary.property_adapter("PdfObservationProduct", "kind")
    assert kind.validate_python("recognition_observation", strict=True) == "recognition_observation"
    for other_kind in ("native", "integrated"):
        with pytest.raises(ValidationError):
            kind.validate_python(other_kind, strict=True)
    dependencies = ResolvedDependencies(
        (SourceArtifact("pdf-domain/contract.json", domain.content), *domain.sources)
    )
    prepared = replace(
        boundary, artifacts=(*boundary.artifacts, *pdf_domain_artifacts(dependencies, model=model))
    )
    for variant, digest in (
        ("read_published_sections", READ_PUBLISHED_SECTIONS_CONTRACT_DIGEST),
        ("read_published_section_nodes", READ_PUBLISHED_SECTION_NODES_CONTRACT_DIGEST),
    ):
        require_call_context(prepared, "read_native_source", variant, digest)
        with pytest.raises(SemanticRefusal, match="incompatible consumer"):
            require_call_context(prepared, "read_native_source", variant, "changed")
