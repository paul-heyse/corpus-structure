"""Native protocol authoring and correspondence from captured domain inputs.

Runtime connection invocation and selected-read admission belong to data_operation_storage.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import TYPE_CHECKING, Any

from sqlalchemy import cast, func
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.schema.integrity import role_name

from .data_operation_json import json_bytes
from .data_operation_version import MODEL_VERSION
from .identity import canonical_bytes
from .native_call_contracts import OperationCallBinding, OperationFieldBinding, OperationFieldType
from .types import SourceArtifact

if TYPE_CHECKING:
    from .data_operation_model import EffectiveDataOperationModel

NATIVE_LOGICAL_FILES = (
    "observations.yaml",
    "pdf-actions.yaml",
    "data-operation-wire-types.yaml",
    "value-codec.yaml",
)


def native_logical_sources(*, model_sources=None) -> dict[str, bytes]:
    from corpus_structure.model.compiled import model_source

    supplied = {} if model_sources is None else model_sources
    return {
        name: supplied[name] if name in supplied else model_source(name)
        for name in NATIVE_LOGICAL_FILES
    }


def capture_native_package_resource() -> SourceArtifact:
    """Capture the package vocabulary bytes used by native declaration preparation."""
    from hashlib import sha256
    from pathlib import Path

    from .file_custody import observed_file

    path = (
        Path(__file__).resolve().parents[1] / "model" / "semantic" / "operation-vocabularies.yaml"
    )
    record = observed_file(path)
    content = path.read_bytes()
    record.check()
    if sha256(content).hexdigest() != record.digest:
        raise ValueError("native operation vocabulary changed during capture")
    return SourceArtifact("native/validity-vocabulary.yaml", content)


def _captured_module(captured: dict[str, bytes], filename: str) -> bytes:
    try:
        return captured["semantic/" + filename]
    except KeyError as error:
        raise ValueError(
            f"native authoring provenance source was not captured: {filename}"
        ) from error


def _captured_source(captured: dict[str, bytes], filename: str) -> bytes:
    try:
        return captured[filename]
    except KeyError as error:
        raise ValueError(
            f"native authoring provenance source was not captured: {filename}"
        ) from error


def _native_protocol_sources(
    *,
    physical_sources: dict[str, bytes],
    linkml_types: bytes,
    target_metadata,
    pdf_domain,
    logical_sources: dict[str, bytes],
    model_sources: dict[str, bytes],
    captured_module_sources: dict[str, bytes],
    resource_sources: tuple[SourceArtifact, ...],
    native_library_runtime: tuple[tuple[str, str], ...],
) -> tuple[SourceArtifact, ...]:
    from .artifact_admission_native import artifact_admission_native_sql
    from .authority_leaf import NativeAuthorityLeaf
    from .completion_validation_native import completion_validation_programs
    from .contextual_admission_native import contextual_admission_native_sql
    from .contextual_definition_native import contextual_definition_native_sql
    from .contextual_linguistics_native import contextual_linguistics_native_sql
    from .contextual_neighborhood import contextual_neighborhood_sql
    from .contextual_scoring_native import contextual_scoring_native_sql
    from .contextual_witness_native import contextual_witness_native_sql
    from .data_attempt_release_native import attempt_release_native_sql
    from .data_claim_batch_native import claim_batch_native_sql
    from .data_claim_native import claim_native_sql
    from .data_completion_settlement_native import completion_settlement_native_sql
    from .data_derivation_native import data_derivation_sql
    from .data_operation_binding_native import binding_native_sources
    from .data_operation_compiler_native import compiler_native_sql
    from .data_operation_cpu_basis import cpu_input_basis_native_sql
    from .data_operation_execution_evidence import SOURCE, execution_evidence_schema
    from .data_operation_read_native import read_native_sql
    from .data_operation_renewal import renewal_native_sql
    from .data_operation_source_native import source_native_sources
    from .data_operation_subjects import subject_scope_values
    from .data_operation_support import (
        ORIGINAL_SUPPORT_REFERENCE_SCHEMA,
        original_support_reference_schema,
    )
    from .data_operation_value_native import data_operation_value_sql
    from .data_operation_wire_native import wire_native_sources
    from .data_product_admission_native import product_admission_native_sql
    from .data_read_boundary_native import read_boundary_native_sql
    from .data_validity_native import data_validity_sql
    from .definition_admission_native import definition_admission_native_sql
    from .demand_authority_native import demand_authority_sql
    from .demand_registration_native import demand_intent_sql
    from .demand_result_native import demand_result_sql
    from .established_validity import product_validation_native_sql
    from .execution_evidence_leaf import (
        execution_evidence_leaf_native_sql,
        execution_evidence_leaf_schema,
    )
    from .external_execution_native import external_execution_native_sql
    from .native_objects import native_sql_script
    from .operation_event_native import operation_event_native_sources
    from .pdf_completion_native import pdf_completion_native_sql
    from .pdf_source_search import search_projection_sources
    from .population_acquisition_native import population_acquisition_native_sql
    from .record_grade_native import record_grade_native_sql
    from .record_policy_completion_native import record_policy_completion_native_sql
    from .record_policy_native import (
        EVENT_FRAME_SCHEMA_SOURCE,
        GRADE_SCHEMA_SOURCE,
        operation_event_frame_schema,
        record_policy_grade_schema,
        record_policy_native_sql,
    )
    from .request_attachment_native import request_attachment_native_sql
    from .rich_admission_native import rich_admission_native_sql
    from .source_value_native import source_value_native_sources
    from .structural_admission_native import structural_admission_native_sql
    from .support_trust_native import support_scope_sql, support_trust_native_sql

    if not isinstance(linkml_types, bytes):
        raise ValueError("explicit native physical inputs lack captured LinkML types")
    try:
        protocol = physical_sources["data-operation-native.yaml"]
        physical = physical_sources["data-operation-physical.yaml"]
    except KeyError as error:
        raise ValueError("explicit native physical closure lacks DDO declarations") from error
    from .data_operation_projections import capture_projection_sources

    logical = logical_sources
    runtime = dict(native_library_runtime)
    resources = {item.name: item for item in resource_sources}
    programs = (
        ("demand-values", "data_operation_value_native.py", data_operation_value_sql()),
        ("demand-validity", "data_validity_native.py", data_validity_sql(target_metadata)),
        ("demand-trust", "support_trust_native.py", support_trust_native_sql(target_metadata)),
        (
            "demand-authority",
            "demand_authority_native.py",
            demand_authority_sql(
                target_metadata,
                subject_scopes=subject_scope_values(),
            ),
        ),
        (
            "demand-intent",
            "demand_registration_native.py",
            demand_intent_sql(
                target_metadata,
                protocol=protocol,
            ),
        ),
        (
            "demand-result",
            "demand_result_native.py",
            demand_result_sql(
                target_metadata,
            ),
        ),
        (
            "demand-derivation",
            "data_derivation_native.py",
            data_derivation_sql(
                target_metadata,
            ),
        ),
    )
    captured = (
        *(
            artifact
            for name, module, program in programs
            for artifact in (
                SourceArtifact(f"native/{name}.sql", program.encode()),
                SourceArtifact(
                    f"native/{name}.py", _captured_module(captured_module_sources, module)
                ),
            )
        ),
        SourceArtifact(
            "native/data-operation-value-identity.py",
            _captured_module(captured_module_sources, "data_operation_identity.py"),
        ),
        SourceArtifact(
            "native/data-operation-definition-projection.py",
            _captured_module(captured_module_sources, "native_definition_projection.py"),
        ),
        *capture_projection_sources(
            physical_sources=physical_sources,
            linkml_types=linkml_types,
            target_metadata=target_metadata,
            captured_module_sources=captured_module_sources,
        ),
        SourceArtifact(
            "native/native-program.py",
            _captured_module(captured_module_sources, "native_program.py"),
        ),
        SourceArtifact(
            "native/native-program-libraries.json",
            canonical_bytes(
                {
                    library: runtime[library]
                    for library in ("pglast", "sqlalchemy", "linkml-runtime")
                }
            ),
        ),
        SourceArtifact(
            "native/data-operation-provider-profiles.py",
            _captured_module(captured_module_sources, "data_operation_provider_profiles.py"),
        ),
        SourceArtifact(SOURCE, execution_evidence_schema()),
        SourceArtifact(
            "native/data-operation-product-validation.sql",
            product_validation_native_sql(target_metadata=target_metadata).encode(),
        ),
        SourceArtifact(
            "native/data-operation-product-validation.py",
            _captured_module(captured_module_sources, "established_validity.py"),
        ),
        SourceArtifact(
            "native/pdf-observations.py",
            _captured_module(captured_module_sources, "pdf_observations.py"),
        ),
        SourceArtifact(
            "native/data-operation-external-receipts.py",
            _captured_module(captured_module_sources, "external_receipts.py"),
        ),
        SourceArtifact(
            "native/data-operation-pdf-completion.sql",
            pdf_completion_native_sql(target_metadata).encode(),
        ),
        SourceArtifact(
            "native/data-operation-pdf-effect-contract.py",
            _captured_module(captured_module_sources, "pdf_effect_contract.py"),
        ),
        SourceArtifact(
            "native/data-operation-record-grade-native.sql",
            record_grade_native_sql(target_metadata).encode(),
        ),
        SourceArtifact(
            "native/data-operation-cpu-basis.sql",
            cpu_input_basis_native_sql(target_metadata=target_metadata).encode(),
        ),
        SourceArtifact(
            "native/data-operation-cpu-basis.py",
            _captured_module(captured_module_sources, "data_operation_cpu_basis.py"),
        ),
        SourceArtifact(
            "native/data-operation-definition-admission.sql",
            definition_admission_native_sql(target_metadata=target_metadata).encode(),
        ),
        SourceArtifact(
            "native/data-operation-definition-admission.py",
            _captured_module(captured_module_sources, "definition_admission_native.py"),
        ),
        SourceArtifact(
            "native/data-operation-artifact-admission.sql",
            artifact_admission_native_sql(target_metadata=target_metadata).encode(),
        ),
        SourceArtifact(
            "native/data-operation-artifact-admission.py",
            _captured_module(captured_module_sources, "artifact_admission_native.py"),
        ),
        SourceArtifact(
            "native/data-operation-contextual-definition.sql",
            contextual_definition_native_sql(target_metadata=target_metadata).encode(),
        ),
        SourceArtifact(
            "native/data-operation-contextual-definition.py",
            _captured_module(captured_module_sources, "contextual_definition_native.py"),
        ),
        SourceArtifact(
            "native/data-operation-contextual-admission.sql",
            contextual_admission_native_sql(target_metadata=target_metadata).encode(),
        ),
        SourceArtifact(
            "native/data-operation-contextual-admission.py",
            _captured_module(captured_module_sources, "contextual_admission_native.py"),
        ),
        SourceArtifact(
            "native/data-operation-contextual-linguistics.sql",
            contextual_linguistics_native_sql().encode(),
        ),
        SourceArtifact(
            "native/data-operation-contextual-linguistics.py",
            _captured_module(captured_module_sources, "contextual_linguistics.py"),
        ),
        SourceArtifact(
            "native/data-operation-contextual-linguistics-native.py",
            _captured_module(captured_module_sources, "contextual_linguistics_native.py"),
        ),
        SourceArtifact(
            "native/data-operation-contextual-scoring.sql", contextual_scoring_native_sql().encode()
        ),
        SourceArtifact(
            "native/data-operation-contextual-scoring.py",
            _captured_module(captured_module_sources, "contextual_scoring_native.py"),
        ),
        SourceArtifact(
            "native/data-operation-contextual-score-query.py",
            _captured_module(captured_module_sources, "contextual_retrieval.py"),
        ),
        SourceArtifact(
            "native/data-operation-contextual-witness.sql",
            contextual_witness_native_sql(target_metadata=target_metadata).encode(),
        ),
        SourceArtifact(
            "native/data-operation-contextual-witness.py",
            _captured_module(captured_module_sources, "contextual_witness_native.py"),
        ),
        *source_value_native_sources(logical["observations.yaml"]),
        SourceArtifact("native/value-codec.yaml", logical["value-codec.yaml"]),
        SourceArtifact(
            "native/data-operation-execution-evidence-leaf.sql",
            execution_evidence_leaf_native_sql(target_metadata).encode(),
        ),
        SourceArtifact(
            "native/data-operation-execution-evidence-leaf.json",
            json_bytes(execution_evidence_leaf_schema()),
        ),
        SourceArtifact(
            "native/data-operation-execution-evidence-leaf.py",
            _captured_module(captured_module_sources, "execution_evidence_leaf.py"),
        ),
        SourceArtifact(
            "native/data-operation-cpu-receipts.py",
            _captured_module(captured_module_sources, "cpu_receipts.py"),
        ),
        SourceArtifact(
            "native/data-operation-rich-admission.sql",
            rich_admission_native_sql(target_metadata=target_metadata).encode(),
        ),
        SourceArtifact(
            "native/data-operation-rich-admission.py",
            _captured_module(captured_module_sources, "rich_admission_native.py"),
        ),
        SourceArtifact(
            "native/data-operation-record-grade-native.py",
            _captured_module(captured_module_sources, "record_grade_native.py"),
        ),
        *operation_event_native_sources(target_metadata=target_metadata),
        SourceArtifact(
            "native/data-operation-record-policy.sql",
            record_policy_native_sql(target_metadata=target_metadata).encode(),
        ),
        SourceArtifact(
            "native/data-operation-structural-admission.sql",
            structural_admission_native_sql(target_metadata).encode(),
        ),
        SourceArtifact(
            "native/data-operation-structural-admission-native.py",
            _captured_module(captured_module_sources, "structural_admission_native.py"),
        ),
        SourceArtifact(
            "native/data-operation-structural-admission.py",
            _captured_module(captured_module_sources, "declared_structural_admission.py"),
        ),
        SourceArtifact(GRADE_SCHEMA_SOURCE, record_policy_grade_schema()),
        SourceArtifact(EVENT_FRAME_SCHEMA_SOURCE, operation_event_frame_schema()),
        SourceArtifact(
            "native/data-operation-operation-events.py",
            _captured_source(captured_module_sources, "evaluate/selected_operation_events.py"),
        ),
        SourceArtifact(
            "native/data-operation-record-grade.py",
            _captured_source(captured_module_sources, "evaluate/declared_record_policy.py"),
        ),
        SourceArtifact(
            "native/data-operation-record-policy-completion.sql",
            record_policy_completion_native_sql(target_metadata).encode(),
        ),
        SourceArtifact(
            "native/data-operation-record-policy-completion.py",
            _captured_module(captured_module_sources, "record_policy_completion_native.py"),
        ),
        SourceArtifact(
            "native/data-operation-record-policy.py",
            _captured_module(captured_module_sources, "record_policy_native.py"),
        ),
        SourceArtifact(
            "native/data-operation-record-policy-authority.py",
            _captured_module(captured_module_sources, "record_policy_authority.py"),
        ),
        SourceArtifact(
            "native/data-operation-authority-leaf.json",
            canonical_bytes(NativeAuthorityLeaf.model_json_schema()),
        ),
        SourceArtifact(
            "native/data-operation-authority-leaf.py",
            _captured_module(captured_module_sources, "authority_leaf.py"),
        ),
        SourceArtifact(ORIGINAL_SUPPORT_REFERENCE_SCHEMA, original_support_reference_schema()),
        SourceArtifact(
            "native/data-operation-support.py",
            _captured_module(captured_module_sources, "data_operation_support.py"),
        ),
        SourceArtifact(
            "native/data-operation-execution-evidence.py",
            _captured_module(captured_module_sources, "data_operation_execution_evidence.py"),
        ),
        SourceArtifact("native/data-operation-protocol.yaml", protocol),
        SourceArtifact("native/data-operation-read.sql", read_native_sql(target_metadata).encode()),
        SourceArtifact(
            "native/data-operation-read.py",
            _captured_module(captured_module_sources, "data_operation_read_native.py"),
        ),
        SourceArtifact(
            "native/data-product-admission.sql",
            product_admission_native_sql(target_metadata).encode(),
        ),
        SourceArtifact(
            "native/data-product-admission-native.py",
            _captured_module(captured_module_sources, "data_product_admission_native.py"),
        ),
        SourceArtifact(
            "native/data-operation-compiler.sql",
            compiler_native_sql(target_metadata, subject_scopes=subject_scope_values()).encode(),
        ),
        SourceArtifact(
            "native/data-operation-compiler.py",
            _captured_module(captured_module_sources, "data_operation_compiler_native.py"),
        ),
        SourceArtifact(
            "native/effect-policy.py", _captured_module(captured_module_sources, "effect_policy.py")
        ),
        SourceArtifact(
            "native/data-completion-settlement.sql",
            completion_settlement_native_sql(target_metadata).encode(),
        ),
        SourceArtifact(
            "native/data-completion-validation.sql",
            native_sql_script(
                item.render() for item in completion_validation_programs(target_metadata)
            ).encode(),
        ),
        SourceArtifact(
            "native/completion-validation-native.py",
            _captured_module(captured_module_sources, "completion_validation_native.py"),
        ),
        SourceArtifact(
            "native/execution-origin-native.py",
            _captured_module(captured_module_sources, "execution_origin_native.py"),
        ),
        SourceArtifact(
            "native/data-completion-settlement-native.py",
            _captured_module(captured_module_sources, "data_completion_settlement_native.py"),
        ),
        SourceArtifact(
            "native/data-claim-batch.sql", claim_batch_native_sql(target_metadata).encode()
        ),
        SourceArtifact(
            "native/data-claim-batch.py",
            _captured_module(captured_module_sources, "data_claim_batch_native.py"),
        ),
        SourceArtifact(
            "native/data-claim.sql", claim_native_sql(target_metadata, protocol).encode()
        ),
        SourceArtifact(
            "native/data-claim.py",
            _captured_module(captured_module_sources, "data_claim_native.py"),
        ),
        SourceArtifact(
            "native/data-attempt-release.sql",
            attempt_release_native_sql(
                target_metadata, protocol, execution_evidence_schema()
            ).encode(),
        ),
        SourceArtifact(
            "native/data-attempt-release.py",
            _captured_module(captured_module_sources, "data_attempt_release_native.py"),
        ),
        SourceArtifact(
            "native/data-read-boundary.sql", read_boundary_native_sql(target_metadata).encode()
        ),
        SourceArtifact(
            "native/population-acquisition.sql",
            population_acquisition_native_sql(target_metadata).encode(),
        ),
        SourceArtifact(
            "native/request-attachment.sql",
            request_attachment_native_sql(target_metadata, protocol).encode(),
        ),
        SourceArtifact(
            "native/request-attachment.py",
            _captured_module(captured_module_sources, "request_attachment_native.py"),
        ),
        SourceArtifact(
            "native/population-acquisition.py",
            _captured_module(captured_module_sources, "population_acquisition_native.py"),
        ),
        SourceArtifact(
            "native/data-read-boundary.py",
            _captured_module(captured_module_sources, "data_read_boundary_native.py"),
        ),
        SourceArtifact(
            "native/data-operation-renewal.sql",
            renewal_native_sql(target_metadata, protocol).encode(),
        ),
        SourceArtifact(
            "native/data-operation-renewal.py",
            _captured_module(captured_module_sources, "data_operation_renewal.py"),
        ),
        SourceArtifact(
            "native/data-operation-support-scopes.sql",
            support_scope_sql(target_metadata).encode(),
        ),
        SourceArtifact(
            "native/contextual-neighborhood.sql",
            contextual_neighborhood_sql().encode(),
        ),
        SourceArtifact(
            "native/contextual-neighborhood.py",
            _captured_module(captured_module_sources, "contextual_neighborhood.py"),
        ),
        SourceArtifact(
            "native/data-operation-external.sql",
            external_execution_native_sql(target_metadata, protocol).encode(),
        ),
        SourceArtifact(
            "native/external-execution-native.py",
            _captured_module(captured_module_sources, "external_execution_native.py"),
        ),
        SourceArtifact(
            "native/data-operation-protocol.py",
            _captured_module(captured_module_sources, "data_operation_protocol.py"),
        ),
        SourceArtifact(
            "native/data-operation-storage.py",
            _captured_module(captured_module_sources, "data_operation_storage.py"),
        ),
        SourceArtifact(
            "native/native-protocol-authoring.py",
            _captured_module(captured_module_sources, "native_protocol_authoring.py"),
        ),
        SourceArtifact(
            "native/support-edges.py",
            _captured_module(captured_module_sources, "support_edges.py"),
        ),
        SourceArtifact(
            "native/validity-programs.py",
            _captured_module(captured_module_sources, "validity_programs.py"),
        ),
        SourceArtifact(
            "native/encoder-member-policy.py",
            _captured_module(captured_module_sources, "contextual_encoder_batch.py"),
        ),
        SourceArtifact(
            "native/validity-vocabulary.yaml",
            resources["native/validity-vocabulary.yaml"].content,
        ),
        SourceArtifact(
            "native/model-compiler.py",
            _captured_source(captured_module_sources, "model/compiled.py"),
        ),
        SourceArtifact(
            "native/native-field-kinds.yaml",
            model_sources["native-field-kinds.yaml"],
        ),
        SourceArtifact(
            "native/identifiers.py",
            _captured_module(captured_module_sources, "identifiers.py"),
        ),
        SourceArtifact(
            "native/native-call-contracts.py",
            _captured_module(captured_module_sources, "native_call_contracts.py"),
        ),
        SourceArtifact(
            "native/data-operation-member-contracts.py",
            _captured_module(captured_module_sources, "data_operation_member_contracts.py"),
        ),
        SourceArtifact(
            "native/data-operation-kind-refinements.py",
            _captured_module(captured_module_sources, "data_operation_kind_refinements.py"),
        ),
        SourceArtifact(
            "native/data-operation-graph-topology.py",
            _captured_module(captured_module_sources, "graph_topology.py"),
        ),
        SourceArtifact(
            "native/data-operation-graph-runtime.py",
            _captured_module(captured_module_sources, "graph_runtime.py"),
        ),
        SourceArtifact(
            "native/data-operation-graph-execution.json",
            canonical_bytes(
                {
                    "version": "data-operation-graph-execution-v1",
                    "networkx": runtime["networkx"],
                    "backend": "networkx",
                }
            ),
        ),
        SourceArtifact(
            "native/data-operation-subject-scopes.json", canonical_bytes(subject_scope_values())
        ),
        SourceArtifact(
            "native/data-operation-subjects.py",
            _captured_module(captured_module_sources, "data_operation_subjects.py"),
        ),
        SourceArtifact(
            "native/data-operation-physical.yaml",
            physical,
        ),
        *binding_native_sources(target_metadata=target_metadata),
        *wire_native_sources(logical["data-operation-wire-types.yaml"]),
        *search_projection_sources(target_metadata=target_metadata, pdf_domain=pdf_domain),
        *source_native_sources(
            physical_sources=physical_sources,
            linkml_types=linkml_types,
            target_metadata=target_metadata,
        ),
    )
    return tuple(
        replace(item, authoring_provenance=True) if item.name.endswith(".py") else item
        for item in captured
    )


def native_protocol_sources(
    *,
    physical_sources=None,
    linkml_types=None,
    target_metadata=None,
    pdf_domain=None,
    logical_sources=None,
) -> tuple[SourceArtifact, ...]:
    """Capture the exact installed program identities with their native model inputs."""
    from corpus_structure.schema.physical import compile_physical

    from .metadata import get_metadata
    from .pdf_domain import CONTRACT
    from .target_installation import capture_target_installation

    target = target_metadata
    if physical_sources is not None:
        if not isinstance(linkml_types, bytes):
            raise ValueError("explicit native physical inputs lack captured LinkML types")
        if target is None:
            target = compile_physical(physical_sources, linkml_types=linkml_types)
        elif physical_sources != target.info.get(
            "physical_sources"
        ) or linkml_types != target.info.get("physical_linkml_types"):
            raise ValueError("native program capture differs from the selected physical model")
    if target is None:
        target = get_metadata()
    pdf = (
        None
        if pdf_domain is None
        else (SourceArtifact(CONTRACT, pdf_domain.content), *pdf_domain.sources)
    )
    return capture_target_installation(
        target, logical_sources=logical_sources, pdf_sources=pdf
    ).authoring_inputs.native_sources


def _captured(sources) -> dict[str, bytes]:
    result = {source.name: source.content for source in sources}
    if len(result) != len(sources):
        raise ValueError("duplicate captured native protocol source")
    # Released correspondence needs generated SQL and protocol artifacts.
    required = {
        "native/data-operation-protocol.yaml",
        *(
            f"native/{name}.sql"
            for name in (
                "demand-values",
                "demand-validity",
                "demand-trust",
                "demand-authority",
                "demand-intent",
                "demand-result",
                "demand-derivation",
            )
        ),
        "native/pdf-source-search.sql",
        "native/pdf-source-search-contract.json",
        "native/data-operation-read.sql",
        "native/data-product-admission.sql",
        "native/data-operation-compiler.sql",
        "native/data-operation-support-scopes.sql",
        "native/contextual-neighborhood.sql",
        "native/data-operation-product-validation.sql",
        "native/data-operation-physical.yaml",
        "native/data-operation-bindings.sql",
        "native/data-operation-source-admission.sql",
        "native/data-operation-record-grade-native.sql",
        "native/data-operation-cpu-basis.sql",
        "native/data-operation-definition-admission.sql",
        "native/data-operation-artifact-admission.sql",
        "native/data-operation-contextual-definition.sql",
        "native/data-operation-contextual-admission.sql",
        "native/data-operation-contextual-linguistics.sql",
        "native/data-operation-contextual-scoring.sql",
        "native/data-operation-contextual-witness.sql",
        "native/data-operation-source-values.sql",
        "native/data-operation-execution-evidence-leaf.sql",
        "native/data-operation-execution-evidence-leaf.json",
        "native/data-operation-rich-admission.sql",
        "native/data-operation-operation-event.sql",
        "native/data-operation-record-policy.sql",
        "native/data-operation-structural-admission.sql",
        "native/data-operation-record-grade.schema.json",
        "native/data-operation-operation-event-frame.schema.json",
        "native/data-operation-record-policy-completion.sql",
        "native/data-operation-authority-leaf.json",
    }
    required.update(
        {
            "native/source-admission-calls.json",
            "native/source-originals.sql",
            "native/data-operation-graph-execution.json",
            "native/data-operation-original-support-reference.json",
            "native/data-operation-external.sql",
            "native/population-acquisition.sql",
            "native/request-attachment.sql",
        }
    )
    if not required <= result.keys():
        raise ValueError("target correspondence requires captured native protocol and SQL")
    if (
        result.get("native/projection-physical/data-operation-native.yaml")
        != result["native/data-operation-protocol.yaml"]
        or result.get("native/projection-physical/data-operation-physical.yaml")
        != result["native/data-operation-physical.yaml"]
    ):
        raise ValueError("Core projection physical/protocol capture differs from native custody")
    return result


def _protocol(sources=None) -> tuple[dict[str, Any], ...]:
    from .data_operation_wire import wire_operations

    captured = native_protocol_sources() if sources is None else tuple(sources)
    _captured(captured)
    return wire_operations(captured)


def native_source_digest(sources=None) -> str:
    from .native_program_registry import PROGRAM_MANIFEST_SOURCE, ProgramManifest

    content = _captured(sources if sources is not None else native_protocol_sources())
    manifest = content.get(PROGRAM_MANIFEST_SOURCE)
    if manifest is None:
        raise ValueError("current native operation capture requires the exact program manifest")
    return ProgramManifest.from_bytes(manifest).kernel_digest


def native_program_closures(sources):
    from .native_program_registry import PROGRAM_CLOSURES_SOURCE, ProgramClosures

    retained = _captured(sources).get(PROGRAM_CLOSURES_SOURCE)
    if retained is None:
        raise ValueError("current native operation capture requires the program closure identities")
    return ProgramClosures.from_bytes(retained)


def native_sql(sources=None) -> str:
    """Render the current operation programs for inspection and rollback-only tests."""
    from .native_objects import native_sql_script

    return native_sql_script(
        item.render() for item in data_operation_native_programs(sources=sources)
    )


def _wire_wrapper_programs(sources, operations):
    from sqlalchemy import JSON, Boolean, literal, or_

    from .data_operation_wire import wire_contract_digest, wire_contracts
    from .native_objects import NativeProgramAccess
    from .native_program import (
        Block,
        If,
        NativeRoutine,
        Parameter,
        Raise,
        Return,
        core_variable,
        pg_type,
    )
    from .native_program_registry import ProgramDeclaration

    contracts = wire_contracts(sources)
    contract_digest = wire_contract_digest(sources)
    payload = core_variable("p_payload", JSONB())
    wrappers = []
    for item in operations:
        name = item["name"]
        schema = cast(literal(canonical_bytes(contracts[name]["input"]).decode()), JSONB())
        conforms = func.public.json_matches_schema(
            cast(schema, JSON()), cast(payload, JSON()), type_=Boolean()
        )
        result = getattr(func.ops, "ddo_impl_" + name)(payload, type_=JSONB())
        routine = NativeRoutine(
            "ops",
            name,
            parameters=(Parameter("p_payload", pg_type("jsonb")),),
            returns=pg_type("jsonb"),
            body=Block(
                (
                    If(
                        or_(payload.is_(None), ~conforms),
                        (Raise(f"native wire violates {name} input schema", "23514"),),
                    ),
                    Return(
                        result.op("||", return_type=JSONB())(
                            func.jsonb_build_object(
                                "contract_digest", contract_digest, type_=JSONB()
                            )
                        )
                    ),
                )
            ),
            security_definer=True,
            search_path=("pg_catalog", "pg_temp"),
        )
        wrappers.append(
            ProgramDeclaration(
                routine,
                source="data-operations:wire wrapper",
                owner=role_name("publisher"),
                access=NativeProgramAccess(purposes=tuple(item["purposes"])),
            )
        )
    return tuple(wrappers)


def native_operation_declarations(sources=None) -> SourceArtifact:
    """Explicit captured operation facts for compilation into the shared effective IR."""
    from .data_operation_wire import wire_kind_declarations, wire_role_kind

    sources = native_protocol_sources() if sources is None else tuple(sources)
    closure = native_program_closures(sources)
    from .original_document_contracts import operation_asset

    source_owner, source_asset = operation_asset(sources)
    admission_sources = [
        source for source in sources if source.name == "native/data-operation-compiler.sql"
    ]
    if len(admission_sources) != 1:
        raise ValueError(
            "native operation coverage requires its actual captured SQL admission owner"
        )
    admission_asset = {
        "reference": "native-domain-admission",
        "contract": admission_sources[0].name,
        "role": "native-admission-policy",
        "content_digest": admission_sources[0].digest,
    }
    operations = []
    for item in _protocol(sources):
        name = item["name"]
        operations.append(
            {
                "id": "data." + name,
                "validity_family": ["none"],
                "profile": item["profile"],
                "subject": "authenticated-native-invocation",
                "subject_definition": {
                    "id": "authenticated-native-invocation",
                    "identifier_kind": "string",
                    "scope": "invocation",
                },
                "discovery_relation": "role-associated",
                "context": ["release", "purpose"],
                "roles": [
                    {
                        "name": "request",
                        "kind": wire_role_kind(name, "input", sources),
                        "direction": "input",
                        "minimum": 1,
                        "maximum": 1,
                        "collection": "scalar",
                        "presence": "required",
                        "parameter": "payload",
                        "support": {
                            "provenance": "exact",
                            "source": "authenticated-native-invocation",
                            "coverage": {"role": "request", "description": "whole-wire"},
                            "identity_requirements": ["episode"],
                        },
                    },
                    {
                        "name": "result",
                        "kind": wire_role_kind(name, "output", sources),
                        "direction": "output",
                        "minimum": 1,
                        "maximum": 1,
                        "collection": "scalar",
                        "presence": "required",
                        "parameter": "payload",
                    },
                ],
                "applicability": [{"kind": "documentation", "text": "native-deployment-admitted"}],
                "invariants": [
                    {"kind": "documentation", "text": text}
                    for text in (
                        "native-wire-and-purpose",
                        "native-attempt-fence",
                        "native-source-and-kind-custody",
                    )
                ],
                "coverage": {
                    "binding": "self",
                    "result_owners": [
                        {"kind": "native-admission", "reference": "native-domain-admission"}
                    ],
                    "description": "one-short-native-transaction",
                },
                "outcomes": ["returned"],
                "state_dimensions": [
                    {"name": "completion", "values": ["pending", "success", "empty", "failed"]}
                ],
                "transitions": [
                    {
                        "dimension": "completion",
                        "before": "pending",
                        "after": "success",
                        "outcome": "returned",
                        "effects": [],
                    }
                ],
                "precision_description": "exact",
                "dependencies": [],
                "effects": (
                    []
                    if item["profile"] == "read"
                    else [
                        {
                            "name": name,
                            "authorization": ["native-purpose:" + "|".join(item["purposes"])],
                            "idempotency": "immutable-receipt-or-explicit-append",
                            "fulfillment": "native-transaction",
                        }
                    ]
                ),
                "capabilities": {
                    "forms": ["scalar"],
                    "preparation": "none",
                    "cancellation": "transaction-boundary",
                    "ownership": "native-connection",
                },
                "behavior": "ddo-native-v1:" + closure.operations[name],
                "parameters": {},
                "assets": [
                    admission_asset,
                    *([source_asset] if "data." + name == source_owner else []),
                ],
                "binding": {"operator": "scan", "roles": ["request"]},
            }
        )
    return SourceArtifact(
        "native/data-operation-native.yaml",
        canonical_bytes(
            {
                "version": MODEL_VERSION,
                "operations": operations,
                "kinds": list(wire_kind_declarations(sources)),
            }
        ),
    )


def native_operation_calls(
    model: EffectiveDataOperationModel | None = None, *, sources=None
) -> tuple[tuple[str, OperationCallBinding], ...]:
    """Resolve the fixed protocol's signatures without accepting candidate SQL names."""
    sources = native_protocol_sources() if sources is None else tuple(sources)
    closure = native_program_closures(sources)
    from .data_operation_wire import (
        wire_contract_digest,
        wire_contracts,
        wire_nominal_correspondence,
    )

    schemas = wire_contracts(sources)
    nominals = wire_nominal_correspondence(sources)
    resolved = OperationFieldType("json_payload", False, False)
    protocol = _protocol(sources)
    captured = {"data." + item["name"] for item in protocol}
    owners = (
        captured if model is None else {operation.semantic_id for operation in model.operations}
    )
    if model is not None:
        for operation in model.operations:
            if (
                operation.semantic_id in captured or operation.behavior.startswith("ddo-native-v1:")
            ) and (
                operation.semantic_id not in captured
                or operation.behavior
                != "ddo-native-v1:"
                + closure.operations[operation.semantic_id.removeprefix("data.")]
            ):
                raise ValueError(
                    f"incompatible captured native protocol operation {operation.semantic_id}"
                )
    result = []
    for item in protocol:
        name = item["name"]
        owner = "data." + name
        if owner not in owners:
            continue
        result.append(
            (
                owner,
                OperationCallBinding(
                    id=name,
                    symbol="ops." + name,
                    parameters=(
                        OperationFieldBinding(
                            "payload",
                            "native-wire",
                            False,
                            native_parameter="p_payload",
                            resolved=resolved,
                            wire_schema=canonical_bytes(schemas[name]["input"]).decode(),
                            wire_nominals=nominals,
                        ),
                    ),
                    result_fields=(
                        OperationFieldBinding(
                            "payload",
                            "native-wire",
                            False,
                            native_field="payload",
                            resolved=resolved,
                            wire_schema=canonical_bytes(schemas[name]["output"]).decode(),
                            wire_nominals=nominals,
                        ),
                    ),
                    result_class="".join(word.title() for word in name.split("_")) + "Result",
                    cardinality="one",
                    ordered=False,
                    result_mode="json",
                    source_digest=closure.operations[name],
                    wire_contract_digest=wire_contract_digest(sources),
                ),
            )
        )
    return tuple(result)


def native_calls_from_dependencies(model, dependencies):
    return native_operation_calls(model, sources=dependencies.artifacts)


def native_digest_from_dependencies(dependencies):
    return native_source_digest(dependencies.artifacts)


def data_operation_immutable_relations(target_metadata, physical_sources):
    """Derive DDO trigger ownership from captured classes and approved tables."""
    from corpus_structure.schema.physical import physical_model_documents

    documents = physical_model_documents(physical_sources)
    declaration = documents.get("data-operation-physical.yaml")
    if declaration is None or not isinstance(declaration.get("classes"), dict):
        raise ValueError("captured DDO physical classes must be a mapping")
    relations = []
    for model_class, definition in sorted(declaration["classes"].items()):
        selected = [
            table
            for table in target_metadata.tables.values()
            if table.info.get("model_class") == model_class
        ]
        if len(selected) != 1:
            raise ValueError("approved DDO physical class lacks one table: " + model_class)
        relation = selected[0]
        immutability = definition.get("annotations", {}).get("ph:immutability")
        if relation.info.get("immutability") != immutability:
            raise ValueError(
                "approved DDO table immutability differs from captured class: " + model_class
            )
        if immutability == "intrinsic":
            relations.append(relation)
    return tuple(relations)


def data_operation_native_programs(*, target_metadata=None, sources=None, pdf_domain=None):
    """Declare every operation implementation and its validated wire entry."""
    from dataclasses import replace

    from .completion_validation_native import completion_validation_programs
    from .contextual_definition_native import contextual_definition_native_programs
    from .contextual_linguistics_native import contextual_linguistics_native_programs
    from .contextual_neighborhood import contextual_neighborhood_programs
    from .contextual_scoring_native import contextual_scoring_native_programs
    from .contextual_witness_native import contextual_witness_native_programs
    from .data_attempt_release_native import attempt_release_native_programs
    from .data_claim_batch_native import claim_batch_native_programs
    from .data_claim_native import claim_native_programs
    from .data_completion_settlement_native import completion_settlement_native_programs
    from .data_derivation_native import data_derivation_programs
    from .data_operation_binding_native import binding_native_programs
    from .data_operation_compiler_native import (
        compiler_native_programs,
        data_operation_native_descriptor_program,
    )
    from .data_operation_cpu_basis import cpu_input_basis_native_programs
    from .data_operation_execution_evidence import SOURCE
    from .data_operation_read_native import read_native_programs
    from .data_operation_renewal import renewal_native_programs
    from .data_operation_source_native import source_native_programs
    from .data_operation_subjects import subject_scope_values
    from .data_operation_value_native import data_operation_value_programs
    from .data_product_admission_native import product_admission_native_programs
    from .data_read_boundary_native import read_boundary_native_programs
    from .data_validity_native import data_validity_programs
    from .demand_authority_native import demand_authority_programs
    from .demand_registration_native import demand_intent_programs
    from .demand_result_native import demand_result_programs
    from .established_validity import product_validation_native_programs
    from .execution_evidence_leaf import execution_evidence_leaf_native_programs
    from .external_execution_native import external_execution_native_programs
    from .native_objects import INTERNAL_PROGRAM
    from .native_program_registry import (
        PROGRAM_MANIFEST_SOURCE,
        ProgramDeclaration,
    )
    from .pdf_source_search import search_projection_programs
    from .population_acquisition_native import population_acquisition_native_programs
    from .record_policy_native import record_policy_native_programs
    from .request_attachment_native import request_attachment_native_programs
    from .source_value_native import source_value_native_programs
    from .structural_admission_native import structural_admission_native_programs
    from .support_trust_native import support_scope_programs
    from .validity_programs import registered_family_sources

    if sources is not None:
        captured = tuple(sources)
    elif target_metadata is None:
        captured = native_protocol_sources()
    else:
        sources = target_metadata.info.get("physical_sources")
        types = target_metadata.info.get("physical_linkml_types")
        if not isinstance(sources, Mapping) or not sources or not isinstance(types, bytes):
            raise ValueError(
                "native candidate metadata lacks explicit captured physical inputs/types"
            )
        captured = native_protocol_sources(
            physical_sources=sources, linkml_types=types, target_metadata=target_metadata
        )
    captured_map = _captured(captured)
    physical_sources = {
        source.name.removeprefix("native/projection-physical/"): source.content
        for source in captured
        if source.name.startswith("native/projection-physical/")
    }
    if target_metadata is None:
        from corpus_structure.schema.physical import compile_physical

        target_metadata = compile_physical(
            physical_sources, linkml_types=captured_map["native/projection-linkml-types.yaml"]
        )
    elif physical_sources != target_metadata.info.get("physical_sources") or captured_map[
        "native/projection-linkml-types.yaml"
    ] != target_metadata.info.get("physical_linkml_types"):
        raise ValueError(
            "native definitions and target metadata require the same captured physical sources"
        )
    operations = _protocol(captured)
    public = {item["name"] for item in operations}
    protocol = physical_sources["data-operation-native.yaml"]
    if PROGRAM_MANIFEST_SOURCE in captured_map:
        descriptor = (
            data_operation_native_descriptor_program(
                native_source_digest(captured), native_program_closures(captured)
            ),
        )
    else:
        descriptor = ()
    scopes = subject_scope_values()

    def declarations(source, routines):
        return tuple(
            ProgramDeclaration(routine, source, role_name("publisher"), INTERNAL_PROGRAM)
            for routine in routines
        )

    cohorts = {
        "native/demand-values.sql": data_operation_value_programs(),
        "native/data-operation-compiler.sql": (
            *descriptor,
            *compiler_native_programs(target_metadata, subject_scopes=scopes),
        ),
        "native/data-operation-source-values.sql": source_value_native_programs(
            captured_map["native/data-operation-source-values-model.yaml"]
        ),
        "native/data-operation-cpu-basis.sql": cpu_input_basis_native_programs(
            target_metadata=target_metadata
        ),
        "native/data-operation-external.sql": external_execution_native_programs(
            target_metadata, protocol
        ),
        "native/data-operation-read.sql": read_native_programs(target_metadata),
        "native/demand-authority.sql": demand_authority_programs(
            target_metadata, subject_scopes=scopes
        ),
        "native/demand-intent.sql": demand_intent_programs(target_metadata, protocol=protocol),
        "native/demand-result.sql": demand_result_programs(target_metadata),
        "native/demand-validity.sql": data_validity_programs(target_metadata),
        **{
            source: declarations(source, routines)
            for source, routines in (
                (
                    "native/data-completion-validation.sql",
                    completion_validation_programs(target_metadata),
                ),
                (
                    "native/population-acquisition.sql",
                    population_acquisition_native_programs(target_metadata),
                ),
                (
                    "native/request-attachment.sql",
                    request_attachment_native_programs(target_metadata, protocol),
                ),
                (
                    "native/demand-derivation.sql",
                    data_derivation_programs(target_metadata),
                ),
                (
                    "native/data-completion-settlement.sql",
                    completion_settlement_native_programs(target_metadata),
                ),
                (
                    "native/data-product-admission.sql",
                    product_admission_native_programs(target_metadata),
                ),
                ("native/data-claim.sql", claim_native_programs(target_metadata, protocol)),
                ("native/data-claim-batch.sql", claim_batch_native_programs(target_metadata)),
                (
                    "native/data-attempt-release.sql",
                    attempt_release_native_programs(
                        target_metadata, protocol, captured_map[SOURCE]
                    ),
                ),
                (
                    "native/data-operation-renewal.sql",
                    renewal_native_programs(target_metadata, protocol),
                ),
                ("native/data-read-boundary.sql", read_boundary_native_programs(target_metadata)),
            )
        },
        "native/data-operation-execution-evidence-leaf.sql": execution_evidence_leaf_native_programs(
            target_metadata
        ),
        "native/contextual-neighborhood.sql": contextual_neighborhood_programs(),
        "native/data-operation-contextual-definition.sql": contextual_definition_native_programs(
            target_metadata=target_metadata
        ),
        "native/data-operation-contextual-linguistics.sql": contextual_linguistics_native_programs(),
        "native/data-operation-contextual-scoring.sql": contextual_scoring_native_programs(),
        "native/data-operation-contextual-witness.sql": contextual_witness_native_programs(
            target_metadata=target_metadata
        ),
        "native/data-operation-support-scopes.sql": support_scope_programs(target_metadata),
        "native/data-operation-product-validation.sql": product_validation_native_programs(
            target_metadata=target_metadata
        ),
        "native/data-operation-structural-admission.sql": structural_admission_native_programs(
            target_metadata
        ),
        "native/data-operation-record-policy.sql": record_policy_native_programs(
            target_metadata=target_metadata
        ),
        **dict(registered_family_sources(target_metadata)),
    }
    cohorts["native/pdf-source-search.sql"] = search_projection_programs(
        captured, target_metadata=target_metadata, pdf_domain=pdf_domain
    )
    cohorts["binding-programs"] = binding_native_programs(
        target_metadata=target_metadata, sources=captured
    )
    cohorts["source-programs"] = source_native_programs(
        target_metadata=target_metadata, sources=captured
    )
    implementations = {
        source: tuple(
            replace(item, routine=replace(item.routine, name="ddo_impl_" + item.routine.name))
            if item.routine.schema == "ops" and item.routine.name in public
            else item
            for item in items
        )
        for source, items in cohorts.items()
    }
    declarations_by_source = {
        **implementations,
        "wire-wrappers": _wire_wrapper_programs(captured, operations),
    }
    return tuple(item for items in declarations_by_source.values() for item in items)
