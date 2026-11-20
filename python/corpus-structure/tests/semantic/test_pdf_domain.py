"""Real PDF action projection and archived fixed-call correspondence, without a Run."""

import json
from dataclasses import replace
from hashlib import sha256

import pytest
from pglast import ast
from pydantic import ValidationError

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.operation_value_types import require_call_context
from corpus_structure.semantic.pdf_contracts import PreparedPdfContext
from corpus_structure.semantic.pdf_domain import (
    PdfDomainContract,
    pdf_domain_artifacts,
    pdf_domain_sources,
)
from corpus_structure.semantic.pdf_domain_native import pdf_domain_native_sql
from corpus_structure.semantic.pdf_lowering import PRODUCER_IDENTITY_INPUTS
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.prepared_sql import prepare_sql
from corpus_structure.semantic.refusal_types import SemanticRefusal
from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies, SourceArtifact
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
    read = domain.require_operation("read_native_source")
    assert read["implementation"] == {
        "owner": "semantic.pdf_record_reader",
        "symbol": "published_record_reader",
        "version": "1",
    }
    legacy = json.loads(domain.content)
    legacy["actions"]["read_native_source"]["implementation"].update(
        owner="semantic.source_views", symbol="read_native_source"
    )
    with pytest.raises(ValueError, match="foreign or relabeled owner"):
        PdfDomainContract(canonical_bytes(legacy), domain.sources)
    action = domain.require_operation("retain_pdf_original")
    assert action["implementation"]["owner"] == "semantic.pdf_contracts"
    action = domain.require_operation("begin_pdf_build")
    assert action["contract"]["calls"][0]["symbol"] == "ops.begin_pdf_build"
    with pytest.raises(ValueError, match="absent from archived PDF contract"):
        domain.require_operation("archive")
    assert all(not source.name.startswith("execution/") for source in domain.sources)
    context = PreparedPdfContext(
        "release:pdf",
        prepare_release(domain.schema),
        domain,
        domain.source("schema/pdf_products").digest,
        SourceArtifact(
            "pdf/staging-model.yaml", domain.source("implementation/pdf/staging-model.yaml").content
        ),
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
    from corpus_structure.semantic._pdf_native_calls import RETAIN_PDF_ORIGINAL_CONTRACT_DIGEST

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
    statements = [item.stmt for item in prepare_sql(sql, source="PDF domain").statements]
    assert {
        tuple(part.sval for part in statement.funcname or ())
        for statement in statements
        if isinstance(statement, ast.CreateFunctionStmt)
    } == {
        ("ops", "pdf_contract_input"),
        ("sem", "admit_pdf_operation_contracts"),
        ("ops", "require_pdf_operation"),
    }
    inputs = json.loads(domain.content)["inputs"]
    frozen = [item for item in inputs if item["name"] not in PRODUCER_IDENTITY_INPUTS]
    producer = [item for item in inputs if item["name"] in PRODUCER_IDENTITY_INPUTS]
    assert frozen and producer
    assert all(item["sha256"] in sql for item in frozen)
    assert all(item["sha256"] not in sql for item in producer)
    assert "sem.pdf_operation_contract.contract_digest = facet_digest" in sql
    assert "PDF action contract identity differs" in sql
    assert "pdf_operation_contract.operation_id = p_operation" in sql
    assert "sem.require_execution_operation" not in sql
    assert "current PDF domain contract is required" in sql
    assert "native-pdf-helper-bindings" in sql
    assert "'pdf-domain/' || p_name" in sql


def test_pdf_domain_owns_observation_boundary_and_exact_published_read_calls(domain, model):
    from corpus_structure.semantic._pdf_native_calls import (
        READ_PUBLISHED_SECTION_NODES_CONTRACT_DIGEST,
        READ_PUBLISHED_SECTIONS_CONTRACT_DIGEST,
    )

    boundary = prepare_release(domain.schema)
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


def test_selected_pdf_receipt_read_requires_explicit_use_and_producer():
    from corpus_structure.semantic.data_operation_wire import validate_native_wire

    request = {
        "project_id": "project:one",
        "demand_id": "demand:one",
        "read_id": "read:one",
        "use_id": "use:one",
        "product_id": "product:one",
        "derivation_id": "episode:one",
    }
    assert validate_native_wire("read_selected_pdf_source", "input", request) == request
    for missing in ("project_id", "use_id", "derivation_id"):
        with pytest.raises(ValueError, match="schema"):
            validate_native_wire(
                "read_selected_pdf_source",
                "input",
                {key: value for key, value in request.items() if key != missing},
            )
    with pytest.raises(ValueError, match="schema"):
        validate_native_wire("read_selected_pdf_source", "input", {**request, "run_id": 7})


def test_current_pdf_facade_has_canonical_ids_and_no_stage_run_slot():
    from pathlib import Path

    from corpus_structure.semantic import _pdf_native_calls, _pdf_native_ids, identifiers
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.pdf_call_generation import generated_enums, generated_source

    assert _pdf_native_calls.TaskId is identifiers.TaskId
    assert _pdf_native_calls.TaskAttempt is identifiers.TaskAttempt
    assert not hasattr(_pdf_native_ids, "TaskId")
    assert "run_id" not in _pdf_native_calls.PdfStageBuild.model_fields
    assert "run_id" not in table("ops.pdf_stage_build").c
    assert Path(_pdf_native_calls.__file__).read_text() == generated_source()
    assert Path(_pdf_native_ids.__file__).read_text() == generated_enums()


def test_selected_pdf_cut_reuses_exact_read_owner_field_schemas():
    from corpus_structure.semantic._data_operation_wire import WireCutSelection
    from corpus_structure.semantic.data_operation_wire import wire_contracts

    result = wire_contracts()["read_selected_pdf_source"]["output"]
    cut = result["definitions"]["cut_selection"]
    page = wire_contracts()["read_demand_result"]["output"]["definitions"][
        "read_demand_result_result"
    ]
    expected = {
        "demand_id",
        "project_id",
        "release_id",
        "runtime_id",
        "selection",
        "trust_snapshot",
        "read_id",
        "read_snapshot",
        "frontier_at",
        "scope",
    }
    assert (
        set(WireCutSelection.__annotations__)
        == set(cut["required"])
        == set(cut["properties"])
        == expected
    )
    assert {field: page["properties"][field] for field in expected} == cut["properties"]


@pytest.mark.parametrize(
    "mutation", ["absent-variant", "wrong-digest", "changed-call", "missing-archive"]
)
def test_current_call_context_refuses_substitution_without_legacy_catalog_fallback(
    domain, model, mutation
):
    import json

    from corpus_structure.semantic._pdf_native_calls import RETAIN_PDF_ORIGINAL_CONTRACT_DIGEST
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.operation_value_types import require_call_context
    from corpus_structure.semantic.refusal_types import SemanticRefusal

    dependencies = ResolvedDependencies(
        (SourceArtifact("pdf-domain/contract.json", domain.content), *domain.sources)
    )
    base = prepare_release(source_bundle())
    prepared = replace(
        base, artifacts=(*base.artifacts, *pdf_domain_artifacts(dependencies, model=model))
    )
    operation = "retain_pdf_original"
    variant = "retain_pdf_original"
    digest = RETAIN_PDF_ORIGINAL_CONTRACT_DIGEST
    require_call_context(prepared, operation, variant, digest)
    if mutation == "absent-variant":
        variant = "absent"
    elif mutation == "wrong-digest":
        digest = "0" * 64
    elif mutation == "changed-call":
        artifact = next(
            a for a in prepared.artifacts if a.kind == "operation_call_correspondences.json"
        )
        values = json.loads(artifact.content)
        next(call for owner, call in values if owner == operation and call["id"] == variant)[
            "cardinality"
        ] = "many"
        altered = replace(artifact, content=canonical_bytes(values))
        prepared = replace(
            prepared, artifacts=tuple(altered if a is artifact else a for a in prepared.artifacts)
        )
    else:
        prepared = replace(
            prepared,
            artifacts=tuple(
                a for a in prepared.artifacts if a.kind != "operation_call_correspondences.json"
            ),
        )
    with pytest.raises(SemanticRefusal, match="correspondence"):
        require_call_context(prepared, operation, variant, digest)


def test_unsupported_pdf_consumer_read_profile_refuses_before_capture(domain, tmp_path):
    from corpus_structure.semantic.pdf_contracts import prepare_pdf_context
    from semantic.pdf_domain_support import altered_domain

    changed = altered_domain(domain, read_version="not-qualified")
    with pytest.raises(ValueError, match="read ABI is unsupported"):
        prepare_pdf_context(prepare_release(domain.schema), changed)
    assert not (tmp_path / "capture").exists()
