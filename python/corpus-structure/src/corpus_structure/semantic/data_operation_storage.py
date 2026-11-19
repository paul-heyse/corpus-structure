"""Trusted DDO protocol correspondence, admission and protected native storage ports.

The declaration file is the one operation inventory. Effective source facts and direct
call bindings are derived together; candidate operations cannot choose SQL symbols.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, replace
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy import Text, bindparam, cast, func, select, text
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.schema.integrity import role_name
from corpus_structure.semantic._data_operation_wire import (
    WireDemandId,
    WireReadIdentity,
)

from ._data_operation_wire import DataOperationCalls
from .data_operation_json import json_bytes, wire_json_loads
from .data_operation_jsonb import ContextJSONB, json_context_value
from .data_operation_model import MODEL_VERSION
from .identity import canonical_bytes
from .native_call_contracts import OperationCallBinding, OperationFieldBinding, OperationFieldType
from .types import SourceArtifact

if TYPE_CHECKING:
    from sqlalchemy import Connection
    from sqlalchemy.sql.selectable import FromClause

    from .data_operation_model import EffectiveDataOperationModel
    from .types import PreparedRelease

_ROOT = Path(__file__).resolve().parents[1] / "model" / "semantic"


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

    from .file_custody import observed_file

    path = _ROOT / "operation-vocabularies.yaml"
    record = observed_file(path)
    content = path.read_bytes()
    record.check()
    if sha256(content).hexdigest() != record.digest:
        raise ValueError("native operation vocabulary changed during capture")
    return SourceArtifact("native/validity-vocabulary.yaml", content)


def _captured_module(captured: dict[str, bytes] | None, filename: str) -> bytes:
    if captured is None:
        return Path(__file__).with_name(filename).read_bytes()
    try:
        return captured["semantic/" + filename]
    except KeyError as error:
        raise ValueError(
            f"native authoring provenance source was not captured: {filename}"
        ) from error


def _captured_source(captured: dict[str, bytes] | None, filename: str) -> bytes:
    if captured is None:
        return Path(__file__).resolve().parents[1].joinpath(filename).read_bytes()
    try:
        return captured[filename]
    except KeyError as error:
        raise ValueError(
            f"native authoring provenance source was not captured: {filename}"
        ) from error


def _native_protocol_sources(
    *,
    physical_sources=None,
    linkml_types=None,
    target_metadata=None,
    pdf_domain=None,
    logical_sources=None,
    model_sources=None,
    captured_module_sources=None,
    resource_sources=(),
    native_library_runtime=(),
) -> tuple[SourceArtifact, ...]:
    from corpus_structure.schema.physical import (
        compile_physical,
        linkml_types_source,
        physical_source_closure,
    )

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

    if physical_sources is None:
        physical_sources = physical_source_closure(
            "physical.yaml", lambda name: (_ROOT / name).read_bytes()
        )
        linkml_types = linkml_types_source() if linkml_types is None else linkml_types
    if not isinstance(linkml_types, bytes):
        raise ValueError("explicit native physical inputs lack captured LinkML types")
    try:
        protocol = physical_sources["data-operation-native.yaml"]
        physical = physical_sources["data-operation-physical.yaml"]
    except KeyError as error:
        raise ValueError("explicit native physical closure lacks DDO declarations") from error
    if target_metadata is None:
        target_metadata = compile_physical(physical_sources, linkml_types=linkml_types)
    from .data_operation_projections import capture_projection_sources

    logical = (
        native_logical_sources(model_sources=model_sources)
        if logical_sources is None
        else logical_sources
    )
    runtime = dict(native_library_runtime)
    resources = {item.name: item for item in resource_sources}
    if model_sources is None:
        raise ValueError("native authoring requires captured model sources")
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


class DataOperationStorage(DataOperationCalls):
    """Connection-scoped invocation; transaction and commit custody stay with the caller."""

    def __init__(self, connection: Connection):
        self.connection = connection

    def _invoke(self, name: str, payload: Any) -> Any:
        from .data_operation_wire import (
            encode_native_wire_request,
            validate_native_wire,
            wire_contract_digest,
            wire_role_kind,
        )

        # SQL owns request shape under its installed contract. The client keeps
        # exact JSON encodability and authenticates that contract before results.
        wire_role_kind(name, "input")
        encoded_payload = encode_native_wire_request(payload)
        encoded = self.connection.scalar(
            select(
                cast(getattr(func.ops, name)(cast(bindparam("payload", type_=Text), JSONB)), Text)
            ),
            {"payload": encoded_payload},
        )
        from .data_operation_wire import wire_role_kind
        from .operation_value_types import native_result_scope

        result_kind = wire_role_kind(name, "output")
        with native_result_scope("data." + name, result_kind):
            if not isinstance(encoded, str):
                raise ValueError("native data operation returned a malformed fixed envelope")
            value = wire_json_loads(encoded)
            if (
                not isinstance(value, dict)
                or set(value) != {"payload", "contract_digest"}
                or not isinstance(value["payload"], dict)
            ):
                raise ValueError("native data operation returned a malformed fixed envelope")
            if value["contract_digest"] != wire_contract_digest():
                raise ValueError("native installed wire contract differs from the prepared client")
            return validate_native_wire(name, "output", value["payload"])


def require_data_operation_native(connection: Connection, prepared: PreparedRelease) -> str:
    """Verify the installed native descriptor and required relations before admission."""
    from .execution_admission import require_native_execution

    require_native_execution(connection, prepared)
    return _require_native_kernel(connection, prepared)


def _require_native_kernel(connection: Connection, prepared: PreparedRelease) -> str:
    expected = prepared.native_kernel_digest
    actual = connection.scalar(text("SELECT sem.data_operation_native_descriptor()"))
    if (
        not isinstance(actual, dict)
        or actual.get("version") != "data-operation-native-v1"
        or actual.get("source_digest") != expected
    ):
        raise ValueError("release was prepared for a different native kernel; re-prepare it")
    return expected


def _kind_schema(prepared: PreparedRelease, kind) -> dict[str, Any]:
    from .data_operation_wire import checked_json_schema

    facts = json.loads(kind.facts)
    if "json_schema" in facts:
        return checked_json_schema(facts["json_schema"])
    if kind.category == "class" and kind.name in prepared.index.definitions:
        return prepared.json_schema(kind.name)
    if kind.category == "enum":
        return {"type": "string", "enum": sorted(prepared.enum_members(kind.name))}
    primitive = facts.get("primitive", facts.get("effective_primitive", kind.name))
    primitive = {
        "int": "integer",
        "str": "string",
        "bool": "boolean",
        "Decimal": "decimal",
        "AwareDatetime": "datetime",
        "bytes": "string",
    }.get(primitive, primitive)
    types = {
        "string": "string",
        "uri": "string",
        "uriorcurie": "string",
        "integer": "integer",
        "boolean": "boolean",
        "float": "number",
        "double": "number",
        "decimal": "number",
        "date": "string",
        "datetime": "string",
        "bytes": "string",
    }
    if primitive == "json":
        return {"type": ["null", "boolean", "string", "number", "array", "object"]}
    if primitive in types:
        return {"type": types[primitive]}
    # Unknown Python/class contracts cannot silently become unconstrained JSON.
    raise ValueError(f"no native body schema for effective kind {kind.semantic_id}")


def kind_meaning_schema(kind, kind_records, class_definitions, enum_members) -> dict[str, Any]:
    """Constrain the typed meaning before JSON projection can erase numeric/type tags."""
    definitions: dict[str, Any] = {}
    kinds = {item.semantic_id: item for item in kind_records}
    kinds.update({item.name: item for item in kind_records})

    def array(*items):
        return {
            "type": "array",
            "minItems": len(items),
            "maxItems": len(items),
            "items": list(items),
            "additionalItems": False,
        }

    def tagged(tag, payload=None):
        return array({"const": tag}) if payload is None else array({"const": tag}, payload)

    def primitive(name):
        if name == "json":
            if "json" not in definitions:
                definitions["json"] = {}
                ref = {"$ref": "#/definitions/json"}
                definitions["json"] = {
                    "anyOf": [
                        tagged("null"),
                        tagged("boolean", {"type": "boolean"}),
                        *(
                            tagged(t, {"type": "string"})
                            for t in ("string", "integer", "decimal", "float")
                        ),
                        tagged("sequence", {"type": "array", "items": ref}),
                        tagged(
                            "mapping", {"type": "array", "items": array({"type": "string"}, ref)}
                        ),
                    ]
                }
            return {"$ref": "#/definitions/json"}
        tag = {"uri": "string", "uriorcurie": "string", "double": "float"}.get(name, name)
        if tag in {"string", "integer", "decimal", "float", "date", "datetime"}:
            return tagged(tag, {"type": "string"})
        if tag == "boolean":
            return tagged(tag, {"type": "boolean"})
        raise ValueError(f"no native tagged primitive contract for {name}")

    def build(current):
        facts = json.loads(current.facts)
        if "json_schema" in facts:
            return primitive("json")
        primitive_name = facts.get("primitive", facts.get("effective_primitive", current.name))
        primitive_name = {
            "int": "integer",
            "str": "string",
            "bool": "boolean",
            "Decimal": "decimal",
            "AwareDatetime": "datetime",
            "bytes": "string",
        }.get(primitive_name, primitive_name)
        if current.category == "primitive" or primitive_name in {
            "json",
            "string",
            "integer",
            "boolean",
            "float",
            "double",
            "decimal",
            "date",
            "datetime",
            "uri",
            "uriorcurie",
        }:
            return primitive(primitive_name)
        if current.category == "enum":
            return tagged("string", {"type": "string", "enum": sorted(enum_members(current.name))})
        if current.category != "class" or current.name not in class_definitions:
            raise ValueError(f"no native tagged body contract for {current.semantic_id}")
        key = current.name
        if key in definitions:
            return {"$ref": "#/definitions/" + key}
        definitions[key] = {}
        definition = class_definitions[current.name]
        if definition.abstract:
            concrete = [
                child
                for child in class_definitions.values()
                if current.name in child.ancestors and not child.abstract
            ]
            if not concrete:
                raise ValueError("abstract meaning range has no concrete nominal members")
            definitions[key] = {"anyOf": [build(kinds[child.iri]) for child in concrete]}
            return {"$ref": "#/definitions/" + key}
        choices, required = [], []
        for prop in definition.properties:
            target = kinds.get(prop.range)
            value = (
                tagged("string", {"type": "string"})
                if target and target.category == "class" and not prop.inlined
                else build(target)
                if target
                else primitive(prop.range)
            )
            if prop.multivalued:
                sequence = {"type": "array", "items": value}
                if prop.minimum_cardinality is not None:
                    sequence["minItems"] = prop.minimum_cardinality
                if prop.maximum_cardinality is not None:
                    sequence["maxItems"] = prop.maximum_cardinality
                value = tagged("sequence", sequence)
            if prop.nullable:
                value = {"anyOf": [tagged("null"), value]}
            pair = array({"const": prop.name}, value)
            choices.append(pair)
            if prop.required:
                required.append({"contains": pair})
        entries: dict[str, Any] = {
            "type": "array",
            "items": {"anyOf": choices} if choices else False,
        }
        if required:
            entries["allOf"] = required
        definitions[key] = tagged("mapping", entries)
        return {"$ref": "#/definitions/" + key}

    body = build(kind)
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        **body,
        "definitions": definitions,
    }


def _meaning_schema(prepared, kind, model) -> dict[str, Any]:
    return kind_meaning_schema(kind, model.kinds, prepared.index.definitions, prepared.enum_members)


def _member_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """The declared container packet body owns the projected member payload shape."""

    def resolve(value):
        if not isinstance(value, dict):
            return {}
        seen = set()
        while "$ref" in value:
            reference = value["$ref"]
            if reference in seen or not reference.startswith("#/"):
                raise ValueError("member schema requires closed local references")
            seen.add(reference)
            value = schema
            for part in reference[2:].split("/"):
                value = value[part.replace("~1", "/").replace("~0", "~")]
        return value

    root = resolve(schema)
    members = root.get("properties", {}).get("members")
    if members is None:
        return {"not": {}}

    def variants(value):
        value = resolve(value)
        branches = value.get("oneOf", value.get("anyOf"))
        if branches is None:
            yield value
        else:
            for branch in branches:
                yield from variants(branch)

    candidates = []
    for variant in variants(members):
        if variant.get("type") != "array":
            continue
        packets = tuple(variants(variant.get("items", {})))
        if not packets:
            return {"not": {}}
        for packet in packets:
            fields = packet.get("properties", {})
            if not {"member_id", "kind_contract", "context", "body"} <= fields.keys():
                return {"not": {}}
            candidates.append(fields["body"])
    if not candidates:
        return {"not": {}}
    return {
        **({key: schema[key] for key in ("$schema", "$defs", "definitions") if key in schema}),
        **(candidates[0] if len(candidates) == 1 else {"anyOf": candidates}),
    }


def data_operation_definition_projection(
    prepared: PreparedRelease,
    model: EffectiveDataOperationModel,
    *,
    native_digest: str,
    captured_contracts=(),
) -> bytes:
    """Compile the fixed native projection for authenticated release archiving."""
    model_content = model.content
    archived_operations = {
        record["semantic_id"]: record for record in json.loads(model_content)["operations"]
    }
    ids = {(identity.owner, identity.domain): identity.key for identity in model.identities}
    kinds = []
    from .data_operation_compilation import native_kind_dependencies
    from .data_operation_kind_refinements import input_kind_contracts

    input_roots, member_contracts = native_kind_dependencies(model)
    accepted = input_kind_contracts(model, input_roots)
    for kind in model.kinds:
        if kind.semantic_id not in member_contracts:
            continue
        contract = ids.get((kind.semantic_id, "kind"))
        if contract is None:
            raise ValueError("cannot admit an incomplete effective kind")
        facts = json.loads(kind.facts)
        schema = _kind_schema(prepared, kind)
        member_kinds = member_contracts[kind.semantic_id]
        member_schema = _member_schema(schema) if member_kinds else {"not": {}}
        if member_kinds and member_schema == {"not": {}}:
            raise ValueError(
                "nominal container members require member_id/kind_contract/context/body packets"
            )
        universe = facts.get("universe", "ordinary")
        if universe not in {"ordinary", "source", "evaluator"}:
            raise ValueError("unknown effective kind data universe")
        kinds.append(
            {
                "kind_contract": contract,
                "kind": kind.semantic_id,
                "body_schema": schema,
                "meaning_schema": _meaning_schema(prepared, kind, model),
                "member_schema": member_schema,
                "member_contracts": [ids[member, "kind"] for member in member_kinds],
                "families": facts.get("projection_families", []),
                "universe": universe,
            }
        )
    from .data_operation_provider_profiles import operation_profile

    operations = []
    archived = json.loads(model.content)
    exported_bindings = {b["semantic_id"]: b["expression"] for b in archived["bindings"]}
    exported_roles = {o["semantic_id"]: o["roles"] for o in archived["operations"]}
    incomplete = [
        operation.semantic_id
        for operation in model.operations
        if ids.get((operation.semantic_id, "recipe")) is None
    ]
    if incomplete:
        details = [
            (
                part.root,
                [(issue.location, issue.reason) for issue in part.unknowns if issue.required],
            )
            for part in model.implementation_slices
            if not part.complete
        ]
        raise ValueError(
            f"cannot admit an incomplete implementation recipe: {incomplete!r}; required closure: {details!r}"
        )
    for operation in model.operations:
        recipe = ids[(operation.semantic_id, "recipe")]
        roles = []
        for role, archived_role in zip(
            operation.roles, exported_roles[operation.semantic_id], strict=True
        ):
            # Native admission independently checks the archived representation.
            # Do not apply the result-only/historical role serializer here: its
            # omission of default support origins changes that representation.
            record: dict[str, Any] = dict(archived_role)
            record["kind_contract"] = ids[role.kind, "kind"]
            record["identity_requirements"] = (
                list(role.support.identity_requirements) if role.support else []
            )
            if role.direction == "input":
                record["accepted_kind_contracts"] = accepted[role.kind]
            roles.append(record)
        operations.append(
            {
                "operation_id": operation.semantic_id,
                "validity_families": list(operation.validity.families),
                "validity_conservative": operation.validity.conservative,
                "subject_definition": operation.subject,
                "recipe": recipe,
                "profile": operation.profile,
                "binding": exported_bindings[operation.binding],
                "definition": ids[operation.semantic_id, "definition"],
                "eligibility": ids[operation.semantic_id, "eligibility"],
                "implementation_revision": next(
                    (
                        identity.key
                        for identity in model.identities
                        if identity.owner == operation.implementation_root
                        and identity.domain == "implementation-slice"
                    ),
                    "external:" + recipe if operation.external is not None else operation.behavior,
                ),
                "input_roles": [role for role in roles if role["direction"] == "input"],
                "output_roles": [role for role in roles if role["direction"] == "output"],
                "support_contract": {
                    "reuse_eligible": all(asset.reuse_eligible for asset in operation.assets),
                    "assets": archived_operations[operation.semantic_id]["assets"],
                    "numerical_policy": archived_operations[operation.semantic_id].get(
                        "numerical_policy"
                    ),
                    "result_fields": dict(operation.result_fields),
                    "coverage": archived_operations[operation.semantic_id]["coverage"],
                    **(
                        {"external": asdict(operation.external)}
                        if operation.external is not None
                        else {}
                    ),
                    **(
                        {"provider_profile": profile}
                        if (profile := operation_profile(operation, captured_contracts)) is not None
                        else {}
                    ),
                    **(
                        {
                            "output_witnesses": [
                                asdict(group) for group in operation.output_witnesses
                            ]
                        }
                        if operation.output_witnesses
                        else {}
                    ),
                    "policy": operation.support_policy,
                    "outcomes": operation.outcomes,
                    "replicate_policy": operation.replicate_policy,
                    "state_dimensions": [asdict(value) for value in operation.state_dimensions],
                    "transitions": [asdict(value) for value in operation.transitions],
                    "effects": [asdict(value) for value in operation.effects],
                    "capabilities": asdict(operation.capabilities),
                    "provenance": (
                        "value_substitution"
                        if all(
                            role.support is None or role.support.provenance == "value_substitution"
                            for role in operation.roles
                        )
                        else "exact"
                    ),
                },
            }
        )
    return canonical_bytes(
        {
            "model_digest": sha256(model_content).hexdigest(),
            "native_digest": native_digest,
            "kinds": kinds,
            "operations": operations,
        }
    )


def admit_data_operation_definitions(
    connection: Connection, prepared: PreparedRelease, model: EffectiveDataOperationModel
) -> str:
    """Install the authenticated exact fixed projection, never caller-shaped contracts."""
    from .execution_admission import require_native_execution, verify_deployment_functions
    from .native_definition_projection import read_native_definition_projection

    with connection.begin_nested():
        # Initial lowering establishes the protected facts required by the runtime guard.
        verify_deployment_functions(connection)
        native_digest = _require_native_kernel(connection, prepared)
        payload = read_native_definition_projection(prepared, model=model)
        value = connection.scalar(
            select(func.sem.admit_data_operation_definitions(bindparam("payload", type_=JSONB))),
            {"payload": {**payload, "release_id": prepared.release_id}},
        )
        if not isinstance(value, dict) or value.get("release_id") != prepared.release_id:
            raise ValueError("native definition admission did not return exact release identity")
        require_native_execution(connection, prepared)
    return native_digest


_UNQUALIFIED_CONTEXT_FIELD = object()


def _binding_context_parameter(value=_UNQUALIFIED_CONTEXT_FIELD, *, name):
    return bindparam(
        name,
        None if value is _UNQUALIFIED_CONTEXT_FIELD else json_context_value(value),
        type_=ContextJSONB(),
    )


def typed_field_projection(meaning, value, value_type, *, multivalued=False):
    """Decode one admitted tagged field for candidate filtering, never a raising native verifier."""
    from sqlalchemy import Boolean, Date, DateTime, Float, Numeric

    lexical = meaning[1].astext
    if multivalued:
        return value, "json"
    if value_type == "integer":
        return cast(lexical, Numeric()), value_type
    if value_type == "boolean":
        return cast(lexical, Boolean()), value_type
    if value_type in {"float", "double"}:
        return cast(lexical, Float()), "float"
    if value_type == "decimal":
        return cast(lexical, Numeric()), value_type
    if value_type == "date":
        return cast(lexical, Date()), value_type
    if value_type == "datetime":
        return cast(lexical, DateTime(timezone=True)), value_type
    if value_type in {"string", "uri", "uriorcurie"}:
        return lexical, "string"
    return value, "json"


@dataclass(frozen=True)
class AdmittedDataRead:
    """One authenticated binding-row base shared by selection and body hydration."""

    relation: FromClause
    accepted_kind_contracts: Mapping[str, tuple[str, ...]]
    admission_evidence: bytes


def admitted_data_read(
    connection: Connection,
    demand_id: str,
    operation_id: str,
    trust_snapshot: dict,
    model: EffectiveDataOperationModel,
    *,
    read_id: str,
    subject: str | None = None,
    original_source: Any = _UNQUALIFIED_CONTEXT_FIELD,
    analyzed_scope: Any = _UNQUALIFIED_CONTEXT_FIELD,
):
    """Construct SQL bindings only through the demand-pinned native admission reader.

    The query rechecks the trust snapshot when executed. Evidence captures the same
    pins, and contains no claim that a raw product row is admissible evidence.
    """
    from .data_operation_kind_refinements import input_kind_contracts

    operation = model.operation(operation_id)
    if (
        original_source is not _UNQUALIFIED_CONTEXT_FIELD
        and original_source is not None
        and (not isinstance(original_source, str) or not original_source)
    ):
        raise ValueError("source filter requires a nonempty identifier or explicit None")
    # Acquire the exact demand now; execution of the TVF repeats its pin check.
    acquired = DataOperationStorage(connection).read_demand_result(
        {
            "demand_id": WireDemandId(demand_id),
            "trust_snapshot": trust_snapshot,
            "read_id": WireReadIdentity(read_id),
            "limit": 1,
        }
    )
    # The native reader validates epoch meaning against this exact read_id.
    # Keep its canonical pins: a lazily materialized zero is not revocation.
    trust_snapshot = acquired["trust_snapshot"]
    accepted = input_kind_contracts(
        model, (role.kind for role in operation.roles if role.direction == "input")
    )
    from .data_operation_projections import binding_columns

    columns = binding_columns(decoder=True)
    relation = func.ops.data_binding_rows(
        demand_id,
        operation_id,
        bindparam("data_binding_trust", trust_snapshot, type_=JSONB),
        read_id,
        subject,
        _binding_context_parameter(original_source, name="data_binding_source"),
        _binding_context_parameter(analyzed_scope, name="data_binding_scope"),
    ).table_valued(*columns)
    # The admitted TVF authenticates this statement once. Role aliases and
    # constraint checks share its rows without sharing authority across reads.
    relation = (
        select(*relation.c)
        .cte("admitted_binding_rows")
        .prefix_with("MATERIALIZED", dialect="postgresql")
    )
    return AdmittedDataRead(
        relation,
        accepted,
        canonical_bytes(
            {
                "demand_id": demand_id,
                "operation_id": operation_id,
                "selection": acquired["selection"],
                "trust_snapshot": trust_snapshot,
                "read_id": read_id,
                "read_snapshot": acquired["read_snapshot"],
                "frontier_at": acquired["frontier_at"],
            }
        ),
    )


def admitted_data_projection(
    connection: Connection,
    demand_id: str,
    operation_id: str,
    trust_snapshot: dict,
    model: EffectiveDataOperationModel,
    *,
    read_id: str,
    subject: str | None = None,
    original_source: Any = _UNQUALIFIED_CONTEXT_FIELD,
    analyzed_scope: Any = _UNQUALIFIED_CONTEXT_FIELD,
):
    """Derive kind/property projections from the same admitted binding-row base."""
    from .data_operation_bindings import ProjectionBinding, ProjectionField
    from .data_operation_projections import binding_columns

    read = admitted_data_read(
        connection,
        demand_id,
        operation_id,
        trust_snapshot,
        model,
        read_id=read_id,
        subject=subject,
        original_source=original_source,
        analyzed_scope=analyzed_scope,
    )
    relation = read.relation
    accepted = read.accepted_kind_contracts
    operation = model.operation(operation_id)
    kinds = {kind.semantic_id: kind for kind in model.kinds}
    json_columns = {item.name for item in binding_columns() if isinstance(item.type, JSONB)}
    names = tuple(relation.c.keys())
    projections = []
    for kind_id in sorted({role.kind for role in operation.roles if role.direction == "input"}):
        kind = kinds[kind_id]
        fields = [
            ProjectionField(
                name,
                name,
                "json"
                if name in json_columns
                else "integer"
                if name in {"position", "multiplicity"}
                else "string",
            )
            for name in names
            if name != "body"
        ]
        selected = list(relation.c)
        facts = json.loads(kind.facts)
        properties = {prop["name"]: prop for prop in facts.get("properties", [])}
        for property_kind in model.kinds:
            if property_kind.category == "property" and property_kind.semantic_id.startswith(
                kind_id + "/property/"
            ):
                property_facts = json.loads(property_kind.facts)
                properties[property_facts["name"]] = property_facts
        for prop in properties.values():
            name = prop["name"]
            value_type = prop.get("range", "json")
            if value_type in kinds:
                field_kind = kinds[value_type]
                field_facts = json.loads(field_kind.facts)
                value_type = field_facts.get(
                    "primitive",
                    field_facts.get(
                        "effective_primitive",
                        "string"
                        if field_kind.category == "enum"
                        or (field_kind.category == "class" and not prop.get("inlined"))
                        else field_kind.name,
                    ),
                )
                value_type = {
                    "int": "integer",
                    "str": "string",
                    "bool": "boolean",
                    "Decimal": "decimal",
                    "AwareDatetime": "datetime",
                }.get(value_type, value_type)
            label = "body_" + name
            # Headers retain decoder columns. A semantic class property always
            # receives its own body column, including subject/position collisions.
            fields = [field for field in fields if field.name != name]
            meaning = cast(func.data.ddo_field(relation.c.meaning_body, name), JSONB)
            expression, value_type = typed_field_projection(
                meaning,
                relation.c.body[name],
                value_type,
                multivalued=bool(prop.get("multivalued")),
            )
            selected.append(expression.label(label))
            fields.append(ProjectionField(name, label, value_type))
        from .data_operation_subjects import subject_field_kind, subject_field_path

        subject_paths = {
            role.subject_field
            for role in operation.roles
            if role.direction == "input"
            and role.kind == kind_id
            and role.subject_field is not None
            and role.subject_field.startswith("/")
        }
        for path in sorted(subject_paths):
            subject_field_kind(kinds, kind_id, path)
            value = relation.c.meaning_body
            for name in subject_field_path(path):
                value = cast(func.data.ddo_field(value, name), JSONB)
            label = "body_subject_" + str(len(fields))
            selected.append(value[1].astext.label(label))
            fields.append(ProjectionField(path, label, "string"))
        scoped = select(*selected).where(relation.c.kind_contract.in_(accepted[kind_id])).subquery()
        projections.append(
            ProjectionBinding(
                kind_id,
                scoped,
                tuple(fields),
                read.admission_evidence,
            )
        )
    return tuple(projections)


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
