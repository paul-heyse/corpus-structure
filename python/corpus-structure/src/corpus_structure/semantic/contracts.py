"""Trusted finite execution contracts, separate from extractable domain classes.

LinkML owns the input field authority. Frozen dataclasses are normalized compiler products,
not a second validation schema. State/edge helpers validate finite declarations only; guards,
transactional authorization and effects retain their named implementations. In particular,
requiring ``execution.lifecycle.v1`` does not assert that it has been deployed.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from functools import lru_cache
from hashlib import sha256
from importlib.resources import files
from typing import Any, Literal, Never

import yaml
from cattrs import Converter
from cattrs.v import transform_error
from linkml_runtime.utils.yamlutils import DupCheckYamlLoader
from pydantic import ValidationError

from corpus_structure.schema.physical import (
    PHYSICAL_ROOT,
    linkml_types_source,
    physical_source_closure,
)

from .identity import canonical_bytes
from .types import ClassDefinition, Diagnostic, PreparationError, SourceArtifact, SourceBundle

EXECUTION_COMPILER_VERSION = "27"
# Prior products remain readable; execution fences remain current-only.
_READABLE_EXECUTION_COMPILERS = frozenset({"24", "25", "26", EXECUTION_COMPILER_VERSION})

# These are meaning-bearing model/grammar/output-contract assets, not executable provenance.
# New assets require an explicit role here; incidental Python/SQL implementation bytes belong
# to the separately archived runtime binding and must never determine semantic release identity.
SEMANTIC_IMPLEMENTATION_NAMES = frozenset(
    {
        "capture/companion-projection-model.yaml",
        "capture/operation-report-schemas.json",
        "pdf/payload-model.yaml",
        "pdf/selected-source-model.yaml",
        "records/reference-model.yaml",
        "records/policy-model.yaml",
        "pdf/docling-validation.schema.json",
        "pdf/section-text-recipe.json",
        "pdf/record-model.yaml",
        "unified/linkml-types.yaml",
        "pdf/record-physical.yaml",
        "pdf/read-projections.yaml",
        "pdf/staging-model.yaml",
        "grammar/extension.lark",
        "grammar/shipped.lark",
        "text/model.json",
        "libraries.json",
        "operations/section-packets.json",
        "operations/named-link-rules.json",
        "operations/named-link-coverage.json",
        "operations/predicate-interpretation.json",
        "operations/model-observation.json",
    }
)

_PHYSICAL_ARTIFACTS = {
    PHYSICAL_ROOT: "pdf/record-physical.yaml",
    "pdf-records.yaml": "pdf/record-model.yaml",
    "pdf-staging.yaml": "pdf/staging-model.yaml",
}
_PHYSICAL_IMPORT_PREFIX = "physical/imports/"


def _physical_import_artifact(name: str) -> bool:
    if not name.startswith(_PHYSICAL_IMPORT_PREFIX):
        return False
    filename = name.removeprefix(_PHYSICAL_IMPORT_PREFIX)
    return (
        filename.endswith(".yaml") and "/" not in filename and filename not in _PHYSICAL_ARTIFACTS
    )


def physical_import_sources(implementations: Mapping[str, bytes]) -> dict[str, bytes]:
    """Read the additional physical import artifacts by their local filenames."""
    return {
        name.removeprefix(_PHYSICAL_IMPORT_PREFIX): content
        for name, content in implementations.items()
        if _physical_import_artifact(name)
    }


def retained_physical_sources(implementations: Mapping[str, bytes]) -> dict[str, bytes]:
    """Resolve the physical closure from archived execution implementation inputs."""
    sources = {
        filename: implementations[artifact]
        for filename, artifact in _PHYSICAL_ARTIFACTS.items()
        if artifact in implementations
    }
    extra = physical_import_sources(implementations)
    closure = physical_source_closure(PHYSICAL_ROOT, (sources | extra).get)
    if not extra.keys() <= closure.keys():
        raise ValueError("unexpected retained physical imports")
    return closure


def semantic_implementation_inputs(
    inputs: tuple[SourceArtifact, ...],
) -> tuple[SourceArtifact, ...]:
    """Select the positively declared semantic assets from a captured runtime footprint."""
    unknown = {
        source.name
        for source in inputs
        if source.name not in SEMANTIC_IMPLEMENTATION_NAMES
        and not _physical_import_artifact(source.name)
        and not source.name.endswith((".py", ".sql"))
    }
    if unknown:
        raise ValueError(
            "implementation assets lack a declared role: " + ", ".join(sorted(unknown))
        )
    return tuple(
        source
        for source in inputs
        if source.name in SEMANTIC_IMPLEMENTATION_NAMES or _physical_import_artifact(source.name)
    )


POSTGRESQL_IMPLEMENTATION_SOURCES = (
    ("capture/companion-projection-model.yaml", "model/semantic/companion-projections.yaml"),
    ("capture/companion-projection.py", "semantic/companion_projection.py"),
    ("capture/projection-recipe.py", "semantic/projection_recipe.py"),
    ("capture/projection-analysis.py", "semantic/projection_analysis.py"),
    ("capture/projection-analysis-products.py", "semantic/projection_analysis_products.py"),
    ("capture/companion-projection-native.py", "semantic/companion_projection_native.py"),
    ("capture/comparison-projection.py", "semantic/comparison_projection.py"),
    ("invocation/invariant-failures.py", "semantic/invariant_failures.py"),
    ("invocation/operation-call-generation.py", "semantic/operation_call_generation.py"),
    ("invocation/operation-calls.py", "semantic/_operation_calls.py"),
    ("invocation/operation-identifiers.py", "semantic/_operation_ids.py"),
    ("capture/directions.sql", "semantic/sql/directions.sql"),
    ("invocation/directions.py", "intervene/directions.py"),
    ("invocation/operation-value-types.py", "semantic/operation_value_types.py"),
    ("invocation/operation-reporting.py", "semantic/operation_reporting.py"),
    ("invocation/alias-policy.py", "semantic/alias_policy.py"),
    ("capture/operation-report-schemas.json", "model/semantic/operation-report-schemas.json"),
    ("capture/companion-columns.py", "semantic/_companion_columns.py"),
    ("capture/companion-export.py", "serve/companion_export.py"),
    ("capture/arrow-transfer.py", "semantic/arrow_transfer.py"),
    ("capture/adbc-lifetime.py", "core/db/adbc_lifetime.py"),
    ("capture/operation-cancellation.py", "core/db/cancellation.py"),
    ("pdf/borrower-lifetime.py", "core/db/lifetime.py"),
    ("pdf/payload-model.yaml", "model/semantic/pdf-payloads.yaml"),
    ("pdf/payloads.py", "semantic/pdf_payloads.py"),
    ("pdf/payload-validation.py", "semantic/pdf_payload_validation.py"),
    ("pdf/selected-source-model.yaml", "model/semantic/selected-source.yaml"),
    ("pdf/selected-source.py", "serve/selected_source.py"),
    ("pdf/selected-source-native.py", "semantic/pdf_selected_source_native.py"),
    ("pdf/published-reader.py", "semantic/pdf_record_reader.py"),
    ("pdf/published-document.py", "semantic/published_document.py"),
    ("pdf/section-views.py", "ingest/pdf_section_views.py"),
    ("pdf/native-consumer-native.py", "semantic/native_consumer_native.py"),
    ("pdf/source-view-native.py", "semantic/source_view_native.py"),
    ("pdf/native-task-completion.sql", "semantic/sql/native_task_completion.sql"),
    ("records/source-record-completion.sql", "semantic/sql/source_record_completion.sql"),
    ("records/source-record-recognition.sql", "semantic/sql/source_record_recognition.sql"),
    ("records/source-record-report.sql", "semantic/sql/source_record_report.sql"),
    ("records/source-record-coordinates.sql", "semantic/sql/source_record_coordinates.sql"),
    ("records/record-projection.py", "semantic/record_projection.py"),
    ("contributions/contracts.py", "semantic/contributions.py"),
    ("operations/assessment.py", "evaluate/operation_assessment.py"),
    ("operations/assessment.sql", "semantic/sql/operation_assessment.sql"),
    ("operations/event-fitting.py", "evaluate/operation_fitting.py"),
    ("operations/event-policy.py", "semantic/operation_policy.py"),
    ("operations/event-fitting.sql", "semantic/sql/operation_event_fitting.sql"),
    ("operations/structural-base.py", "semantic/structural_base.py"),
    ("operations/retained-contributions.py", "semantic/retained_contributions.py"),
    ("operations/dossier-contributions.py", "methods/dossier_contributions.py"),
    ("operations/dossier-contributions.sql", "semantic/sql/dossier_contributions.sql"),
    ("operations/artifact-identity.py", "semantic/artifact_identity.py"),
    ("operations/identity-resolution.py", "semantic/identity_resolution.py"),
    ("operations/artifact-producer.py", "methods/artifact_identity.py"),
    ("operations/scoped-relations.py", "methods/scoped_relations.py"),
    ("operations/structural-roles.py", "methods/structural_roles.py"),
    ("operations/structural-producers.py", "methods/structural_products.py"),
    ("operations/structural-parsing.py", "semantic/structural_parsing.py"),
    ("operations/review-assessments.sql", "semantic/sql/review_assessments.sql"),
    ("operations/review-assessments.py", "evaluate/review_assessments.py"),
    ("operations/structural-assessment.py", "evaluate/structural_assessment.py"),
    ("operations/structural-products.sql", "semantic/sql/structural_products.sql"),
    ("operations/structural-products.py", "semantic/structural_products.py"),
    ("operations/structural-admission.py", "semantic/structural_admission.py"),
    ("operations/structural-publication.sql", "semantic/sql/structural_publication.sql"),
    ("contributions/read.py", "semantic/contribution_queries.py"),
    ("contributions/source-custody.py", "semantic/records.py"),
    ("contributions/native.sql", "semantic/sql/source_contributions.sql"),
    ("records/source-anchor-coordinates.sql", "semantic/sql/source_anchor_coordinates.sql"),
    ("records/publication.sql", "semantic/sql/record_publication.sql"),
    ("records/finalization.sql", "semantic/sql/native_finalization.sql"),
    ("records/read.py", "semantic/record_queries.py"),
    ("records/references.py", "evaluate/record_references.py"),
    ("records/reference-alignment.py", "evaluate/record_alignment.py"),
    ("records/reference-model.yaml", "model/semantic/record-references.yaml"),
    ("records/policy-model.yaml", "model/semantic/record-policy.yaml"),
    ("records/policy-products.py", "semantic/record_policy_products.py"),
    ("records/admission.py", "semantic/record_admission.py"),
    ("records/policy.py", "semantic/record_policy.py"),
    ("records/assertions.py", "semantic/record_assertions.py"),
    ("records/fitting.py", "evaluate/record_fitting.py"),
    ("records/policy-evaluation.py", "evaluate/record_policy.py"),
    ("records/policy.sql", "semantic/sql/record_policy.sql"),
    ("invocation/task-dependency.sql", "semantic/sql/task_dependency_scope.sql"),
    ("records/references.sql", "semantic/sql/record_references.sql"),
    ("records/graph-validation.sql", "semantic/sql/source_record_graph.sql"),
    ("records/release-projection.py", "semantic/releases.py"),
    ("records/graph-publication.py", "semantic/publication.py"),
    ("records/execution-projection-check.sql", "semantic/sql/execution_projection_check.sql"),
)


M1_IMPLEMENTATION_SOURCES = (
    ("records/m1-source.py", "methods/m1_source.py"),
    ("records/m1-annotations.py", "methods/m1_annotations.py"),
    ("records/m1-readings.py", "methods/m1_readings.py"),
    ("records/definition-terms.py", "methods/definition_terms.py"),
    ("records/contextual-candidates.py", "methods/contextual_candidates.py"),
    ("records/contribution-adapter.py", "methods/contribution_adapter.py"),
    ("records/assembly.py", "methods/record_assembly.py"),
    ("records/packs.py", "methods/record_packs.py"),
    ("records/readings.py", "methods/record_readings.py"),
    ("records/interpreter.py", "semantic/record_interpretation.py"),
    ("records/table-interpretation.py", "methods/table_interpretation.py"),
    ("records/local-interpretation.py", "methods/local_interpretation.py"),
    ("records/local-interpretation-reports.py", "semantic/local_interpretation_reports.py"),
    ("records/source-preparation.py", "methods/source_preparation.py"),
    ("records/annotations.py", "ingest/annotations.py"),
    ("records/annotation-rules.py", "methods/annotation_rules.py"),
    ("records/annotation-views.py", "ingest/annotation_views.py"),
    ("records/gliner.py", "methods/gliner.py"),
    ("records/gliner-worker.py", "methods/gliner_worker.py"),
    ("records/source-contexts.py", "semantic/source_contexts.py"),
    ("records/m1-graph.py", "orchestrate/m1.py"),
)


@lru_cache(maxsize=1)
def approved_implementations() -> Mapping[str, Any]:
    """Resolve only application-written imports, never catalog-authored module strings."""
    from types import MappingProxyType

    from corpus_structure.core.text_structure import capture_text
    from corpus_structure.evaluate import (
        operation_assessment,
        operation_fitting,
        record_policy,
        record_references,
    )
    from corpus_structure.evaluate import semantic as references
    from corpus_structure.ingest import pdf_reconciliation
    from corpus_structure.ingest.pdf import PdfConverter
    from corpus_structure.ingest.pdf_chandra import ChandraRuntime
    from corpus_structure.ingest.pdf_hierarchy import organize, project_section
    from corpus_structure.ingest.pdf_methods import EnrichPdfMath
    from corpus_structure.ingest.pdf_recognition import RecognitionWorker
    from corpus_structure.ingest.pdf_stream_reconciliation import reconcile_pdf_stream
    from corpus_structure.ingest.pdf_streaming import StreamingPdfProducer
    from corpus_structure.intervene.directions import record_direction
    from corpus_structure.intervene.semantic import ProposalSession
    from corpus_structure.methods.math.prepared import assess_parsing_math, interpret_parsing_math
    from corpus_structure.orchestrate import project, semantic
    from corpus_structure.orchestrate.pdf_streaming import run_private_pdf_build

    from . import (
        analytics,
        arrow_publication,
        consolidation,
        continuations,
        contribution_queries,
        domain_operations,
        inference,
        observations,
        ontology,
        operations,
        pdf_contracts,
        pdf_integrated,
        pdf_publication,
        pdf_staging,
        pdf_storage,
        prepare,
        proposals,
        publication,
        query,
        record_queries,
        releases,
        runtime,
        source_views,
    )

    return MappingProxyType(
        {
            "validate_continuation": continuations.validate_continuation,
            "graph_project": ontology.qualified_validation_graph,
            "graph_validate": ontology.validate_projected_graph,
            "prepare": prepare.prepare_release,
            "archive": releases.persist_release,
            "reload": releases.load_release,
            "activate": releases.activate_release,
            "project": project.init_bound_project,
            "start_run": operations.create_run,
            "method": operations.record_method,
            "schedule": operations.create_task,
            "claim": operations.claim_tasks,
            "renew_claim": operations.renew_claim,
            "release_claim": operations.release_claim,
            "complete": operations.complete_task,
            "complete_unit": operations.complete_unit_result,
            "hold": operations.hold_agent_result,
            "record_direction": record_direction,
            "cut": operations.seal_cut,
            "source_execution": semantic.run_source_methods,
            "end_run": operations.end_source_run,
            "register_document": operations.register_document,
            "read_original": operations.read_original,
            "prepare_parsing_text": capture_text,
            "interpret_parsing_math": interpret_parsing_math,
            "assess_parsing_math": assess_parsing_math,
            "retain_pdf_original": pdf_contracts.store_pdf_original,
            "stream_pdf_native": StreamingPdfProducer.run,
            "reconcile_pdf_stream": reconcile_pdf_stream,
            "stage_pdf_producer": run_private_pdf_build,
            "freeze_pdf_build": pdf_publication.freeze_pdf_build,
            "prepare_pdf_build": pdf_publication.prepare_pdf_build,
            "validate_pdf_build": pdf_publication.validate_pdf_build,
            "seal_pdf_build": pdf_publication.seal_pdf_build,
            "adopt_pdf_companion_batch": pdf_publication.adopt_pdf_companion_batch,
            "retain_pdf_stage_recipe": pdf_publication.retain_pdf_stage_recipe,
            "inspect_pdf_build": pdf_publication.inspect_pdf_build,
            "begin_pdf_build": pdf_staging.begin_pdf_build,
            "adopt_pdf_batch": pdf_staging.adopt_pdf_batch,
            "inspect_pdf_progress": pdf_staging.inspect_pdf_progress,
            "resume_pdf_build": pdf_staging.resume_pdf_build,
            "abandon_pdf_build": pdf_staging.abandon_pdf_build,
            "prepare_native_document": pdf_contracts.prepare_pdf_product,
            "recognize_pdf_observation": RecognitionWorker.recognize_pages,
            "recognize_chandra_observation": ChandraRuntime.recognize,
            "map_pdf_observation": pdf_reconciliation.map_pdf_observation,
            "compare_pdf_occurrences": pdf_reconciliation.compare_pdf_occurrences,
            "select_pdf_integration": pdf_reconciliation.select_pdf_integration,
            "prepare_integrated_pdf": pdf_integrated.prepare_integrated_pdf_product,
            "publish_pdf_observation": pdf_integrated.store_pdf_observation,
            "read_pdf_product": pdf_storage.read_pdf_product,
            "convert_pdf": PdfConverter.convert_bytes,
            "enrich_pdf_math": EnrichPdfMath.run,
            "organize_pdf": organize,
            "project_pdf_source": project_section,
            "publish_source_view": source_views.store_source_view,
            "read_source_view": source_views.load_source_view,
            "read_native_source": source_views.read_native_source,
            "capture_native_source_frame": source_views.store_native_source_frame,
            "request_native_source": source_views.request_source_view,
            "publish_pdf_region_artifact": source_views.store_region_artifact,
            "bind_report": observations.bind_result,
            "packet": proposals.proposal_packet,
            "locate": proposals.locate_proposal,
            "submission": ProposalSession.commit,
            "assemble": consolidation.assemble,
            "evaluate": domain_operations.consolidate_cut,
            "resolve_identity": domain_operations._entity_mappings,
            "scientific_policy": domain_operations.ReleasedRulesPolicy.evaluate,
            "derive": inference.derive,
            "publish_inference": inference.publish_inference,
            "publish": publication.publish_batch,
            "native_admission": publication.admit_release,
            "read": query.read_session,
            "query": query.ReadSession.query,
            "explain": query.ReadSession.explain,
            "projection": analytics.compile_projection,
            "capture": analytics.capture_packet,
            "analysis": analytics.AnalysisScope,
            "analysis_close": analytics.AnalysisScope.close,
            "publish_arrow": arrow_publication.publish_arrow,
            "reference_set": references.create_reference_set,
            "reference_pass": references.record_pass,
            "reference_items": references.ensure_items,
            "reference_grade": references.reference_evaluate,
            "reference_split": references.split_documents,
            "reference_operation_set": operation_assessment.create_reference_set,
            "reference_operation_pass": operation_assessment.record_pass,
            "reference_operation_grade": operation_assessment.reference_evaluate,
            "reference_operation_fit": operation_fitting.fit_native_operation_event,
            "read_source_contributions": contribution_queries.read_source_contributions,
            "reference_record_set": record_references.create_reference_set,
            "reference_record_pass": record_references.record_pass,
            "reference_record_grade": record_references.reference_evaluate,
            "reference_record_partition": record_references.assign_origin,
            "reference_record_fit": record_references.read_fitting_references,
            "reference_record_calibrate": record_policy.fit_record_policy,
            "read_source_records": record_queries.read_completed_record_projection,
            "select_result": runtime.select_completed_result,
        }
    )


@dataclass(frozen=True)
class ExecutionModelInputs:
    schema: SourceBundle
    catalog: SourceArtifact
    implementations: tuple[SourceArtifact, ...] = ()


@dataclass(frozen=True)
class AttributeDefinition:
    name: str
    range: str
    required: bool
    multivalued: bool


@dataclass(frozen=True)
class ConceptDefinition:
    id: str
    family: str
    meaning: str
    identity: str
    scope: str
    attributes: tuple[AttributeDefinition, ...]
    relationships: tuple[str, ...]


@dataclass(frozen=True)
class EndpointRole:
    role: str
    concept: str
    minimum: int
    maximum: int | None = field(default=None, kw_only=True)
    ordered: bool
    unresolved: bool
    unresolved_concept: str | None = field(default=None, kw_only=True)


@dataclass(frozen=True)
class RelationshipDefinition:
    id: str
    kind: str
    direction: str
    endpoints: tuple[EndpointRole, ...]
    cardinality_scope: str
    identity_kind: str
    identity_roles: tuple[str, ...]
    identity_context: tuple[str, ...]
    qualifications: tuple[str, ...]
    multiplicity: str
    reference_scope: str
    invariants: tuple[str, ...]


@dataclass(frozen=True)
class StateDimension:
    id: str
    values: tuple[str, ...]


@dataclass(frozen=True)
class StateValue:
    dimension: str
    value: str


@dataclass(frozen=True)
class ComposedState:
    id: str
    values: tuple[StateValue, ...]
    terminal: bool


@dataclass(frozen=True)
class LifecycleDefinition:
    id: str
    subject: str
    dimensions: tuple[StateDimension, ...]
    states: tuple[ComposedState, ...]
    initial_states: tuple[str, ...]
    transitions: tuple[str, ...]
    invariants: tuple[str, ...]

    def state(self, values: Mapping[str, str]) -> ComposedState:
        """Resolve an exact allowed combination, without authorizing a database operation."""
        for state in self.states:
            if {v.dimension: v.value for v in state.values} == dict(values):
                return state
        _fail("invalid_composed_state", self.id, f"unsupported combination {dict(values)!r}")


@dataclass(frozen=True)
class EffectDefinition:
    id: str
    version: str
    meaning: str


@dataclass(frozen=True)
class TransitionDefinition:
    id: str
    lifecycle: str
    operation: str
    from_states: tuple[str, ...]
    to_states: tuple[str, ...]
    immutable_bindings: tuple[str, ...]
    invariants: tuple[str, ...]
    effects: tuple[str, ...]
    outcomes: tuple[str, ...]


@dataclass(frozen=True)
class NativeDiagnosticBinding:
    operation: str
    kind: Literal["constraint", "guard"]
    sqlstate: str
    schema_name: str | None = None
    table_name: str | None = None
    constraint_name: str | None = None
    guard: str | None = None
    guard_version: str | None = None


@dataclass(frozen=True)
class InvariantDefinition:
    id: str
    meaning: str
    subjects: tuple[str, ...]
    relationships: tuple[str, ...]
    scope: str
    failure_code: str
    implementation: str
    required_capability: str | None = None
    observable: bool = False
    diagnostics: tuple[NativeDiagnosticBinding, ...] = ()


@dataclass(frozen=True)
class ImplementationBinding:
    id: str
    owner: str
    symbol: str
    version: str
    placement: str
    input_concepts: tuple[str, ...]
    result_concepts: tuple[str, ...]
    features: tuple[str, ...]
    effects: tuple[str, ...]
    required_capabilities: tuple[str, ...]


@dataclass(frozen=True)
class ResultDimension:
    id: str
    field: str
    outcome_domain: str


@dataclass(frozen=True)
class OperationFieldType:
    kind: str
    nullable: bool
    multivalued: bool
    enum_values: tuple[str, ...] = ()
    model_class: str | None = None


@dataclass(frozen=True)
class OperationFieldBinding:
    name: str
    source: str
    nullable: bool
    native_parameter: str | None = None
    native_field: str | None = None
    native_type: Literal["integer"] | None = None
    multivalued: bool = False
    semantic_type: str | None = None
    default_json: str | None = None
    transform: Literal["identity", "task_unit_type", "held_progress"] | None = None
    resolved: OperationFieldType | None = None


@dataclass(frozen=True)
class OperationRecordBinding:
    name: str
    fields: tuple[OperationFieldBinding, ...]


@dataclass(frozen=True)
class OperationCallBinding:
    id: str
    symbol: str
    parameters: tuple[OperationFieldBinding, ...]
    result_class: str | None = field(default=None, kw_only=True)
    result_fields: tuple[OperationFieldBinding, ...]
    cardinality: Literal["many", "one", "optional", "none"]
    ordered: bool
    source_digest: str | None = None
    result_mode: Literal["table", "scalar", "void", "json"] = "table"
    result_source: str | None = None
    requires_context: bool = False
    order_by: tuple[str, ...] = ()
    records: tuple[OperationRecordBinding, ...] = ()
    batch: bool = False
    json_read: Literal["native", "json-text-v1"] = "native"
    backend: Literal["native", "core"] = "native"


@dataclass(frozen=True)
class OperationContract:
    id: str
    inputs: tuple[str, ...]
    results: tuple[str, ...]
    applicability: tuple[str, ...]
    universe: str
    effects: tuple[str, ...]
    outcomes: tuple[str, ...]
    outcome_domain: str
    dependencies: tuple[str, ...]
    precision: str
    implementation: str | None = field(default=None, kw_only=True)
    transitions: tuple[str, ...]
    projections: tuple[str, ...]

    result_dimensions: tuple[ResultDimension, ...] = ()
    policy_version: str | None = None
    calls: tuple[OperationCallBinding, ...] = ()

    @property
    def call(self) -> OperationCallBinding | None:
        """Convenience for a single fixed variant; calls is the sole stored contract."""
        return self.calls[0] if len(self.calls) == 1 else None


@dataclass(frozen=True)
class GraphProjectionPolicy:
    universe: Literal["typed_reference_closure"]
    precision: Literal["exact_literals"]
    collections: Literal["positions_and_multiplicity"]
    lifetime: Literal["snapshot"]
    node_kinds: tuple[str, ...]


@dataclass(frozen=True)
class AnalyticalProjectionPolicy:
    input_kind: Literal["captured", "candidate", "accepted"]
    universe: Literal["full_spine", "cut_candidates", "eligible_positive_accepted"]
    collections: Literal["positions_and_multiplicity"]
    values: Literal["exact_with_separate_bounded_projection", "exact"]
    completeness: Literal["declared_universe"]
    arithmetic_profile: str | None = None


@dataclass(frozen=True)
class ProjectionContract:
    id: str
    sources: tuple[str, ...]
    relationships: tuple[str, ...]
    universe: str
    preserves: tuple[str, ...]
    omissions: tuple[str, ...]
    precision: str
    collections: str
    completeness: str
    lifetime: str
    implementation: str
    graph_policy: GraphProjectionPolicy | None = None
    analytical_policy: AnalyticalProjectionPolicy | None = None


@dataclass(frozen=True)
class OutcomeDomain:
    id: str
    authority: str
    values: tuple[str, ...]


@dataclass(frozen=True)
class OutcomeTranslation:
    source_domain: str
    source: str
    target_domain: str
    target: str
    retained_meaning: str
    invariant: str


@dataclass(frozen=True)
class NativeGuardBinding:
    id: str
    symbol: str
    version: str
    invariants: tuple[str, ...]


# Code-owned kernels, not arbitrary catalog-provided SQL names.
_APPROVED_NATIVE_GUARDS = {
    "execution_edge": ("ops.execution_edge(text,text,text)", "1"),
    "execution_task": ("ops.guard_execution_task()", "2"),
    "native_source_address": ("ops.complete_task(bigint,bigint,text,jsonb,text,jsonb,jsonb)", "2"),
    "execution_run": ("ops.guard_execution_run()", "1"),
    "conditional_kernel": ("data.validate_conditions(text,text)", "1"),
    "completed_result": ("data.finish_evaluation(bigint,text,text)", "1"),
    "reference_pass": ("eval.record_reference_pass(bigint,text,text,bytea,jsonb)", "1"),
    "reference_grade": ("eval.record_reference_evaluation(text,bigint,bigint,jsonb,jsonb)", "1"),
    "selected_result": ("data.select_project_result(text,bigint,bigint)", "1"),
}


@dataclass(frozen=True)
class AnalysisDemand:
    id: str
    prerequisites: tuple[str, ...]
    dependencies: tuple[str, ...]


@dataclass(frozen=True)
class BindingRoleRule:
    kind: str
    role: str


@dataclass(frozen=True)
class InputOwnershipContract:
    id: str
    concept: str
    operation: str
    lifetime: str
    dependencies: tuple[str, ...]


@dataclass(frozen=True)
class ScientificComputationProfile:
    policy_id: str
    symbolic_method: str
    numeric_method: str
    backend: str
    simplify_seconds: str
    points: int
    max_draws: int
    minimum_valid_points: int
    relative_tolerance: str
    absolute_tolerance: str
    seed: str
    numeric_requires: str


@dataclass(frozen=True)
class TextPreparationPolicy:
    recipe: str
    offsets: str
    atoms: str
    segmentation: str


@dataclass(frozen=True)
class AlignmentPolicyDefinition:
    recipe: str
    max_iterations: int
    solver: str
    topology: str
    ambiguity: str


@dataclass(frozen=True)
class PlacementPolicyDefinition:
    recipe: str
    candidate_limit: int = field(default=5, kw_only=True)
    token_cutoff: int
    token_pad: int
    char_cutoff: int
    char_pad: str
    char_errors: str
    pick_cutoff: int
    regex_timeout: str
    refine_timeout: str


@dataclass(frozen=True)
class CapturePolicyDefinition:
    modes: tuple[str, ...]
    manifest: str
    digest: str
    ordering: str
    completeness: str
    storage: str


@dataclass(frozen=True)
class InvocationPolicyDefinition:
    logical_recipe: str
    executable_recipe: str
    dependencies: tuple[str, ...]
    skipped_packet: str
    executable_packet: str


@dataclass(frozen=True)
class ScientificQuestionRule:
    question: str
    prerequisites: tuple[str, ...]
    result_basis: tuple[str, ...]


@dataclass(frozen=True)
class AnalysisProfile:
    id: str
    version: str
    demands: tuple[AnalysisDemand, ...]
    binding_roles: tuple[BindingRoleRule, ...]
    builtin_functions: tuple[str, ...]
    local_declaration_rules: tuple[str, ...]
    ownership: tuple[InputOwnershipContract, ...]
    grammar_recipe: str = ""
    transformer_recipe: str = ""
    shared_consumers: tuple[str, ...] = ()
    scientific_profiles: tuple[ScientificComputationProfile, ...] = ()
    scientific_questions: tuple[ScientificQuestionRule, ...] = ()
    mathematical_conventions: tuple[str, ...] = ()
    text_policy: TextPreparationPolicy | None = None
    alignment_policy: AlignmentPolicyDefinition | None = None
    placement_policy: PlacementPolicyDefinition | None = None
    capture_policy: CapturePolicyDefinition | None = None
    invocation_policy: InvocationPolicyDefinition | None = None


@dataclass(frozen=True)
class ParsingAdapterSupport:
    adapter_id: str
    implementation_revision: str
    frontend_revision: str
    coordinate_fidelity: str
    repair_policy: str
    ambiguity_policy: str
    lifetime: str
    capabilities: tuple[str, ...]
    provenance_universe: str
    grammar_revision: str | None = field(default=None, kw_only=True)


@dataclass(frozen=True)
class ExecutionModelProducts:
    model_id: str
    content: bytes
    required_capabilities: tuple[str, ...]
    concepts: tuple[ConceptDefinition, ...]
    relationships: tuple[RelationshipDefinition, ...]
    lifecycles: tuple[LifecycleDefinition, ...]
    transitions: tuple[TransitionDefinition, ...]
    operations: tuple[OperationContract, ...]
    invariants: tuple[InvariantDefinition, ...]
    implementations: tuple[ImplementationBinding, ...]
    projections: tuple[ProjectionContract, ...]
    outcome_domains: tuple[OutcomeDomain, ...]
    outcome_translations: tuple[OutcomeTranslation, ...]
    native_guards: tuple[NativeGuardBinding, ...]
    reference_splits: tuple[str, ...]
    effect_definitions: tuple[EffectDefinition, ...] = ()
    analysis_profiles: tuple[AnalysisProfile, ...] = ()
    implementation_digests: tuple[tuple[str, str], ...] = ()
    parsing_adapters: tuple[ParsingAdapterSupport, ...] = ()

    def operation(self, name: str) -> OperationContract:
        """Resolve a mandatory operation from this exact release-bound model."""
        for operation in self.operations:
            if operation.id == name:
                return operation
        raise PreparationError(
            (
                Diagnostic(
                    "missing_operation",
                    name,
                    "required operation is absent from the bound model",
                    contract_id=name,
                    consumer="bound_execution_model",
                    expected="declared owned operation",
                    actual="missing",
                    remedy=(
                        "include the required operation in the bound model and derive a new release"
                    ),
                ),
            )
        )

    def require_operation(self, name: str) -> OperationContract:
        """Resolve actual owned effect support; never substitute the installed model."""
        operation = self.operation(name)
        _validate_effect_support(self, operation)
        return operation

    def lifecycle(self, name: str) -> LifecycleDefinition:
        return next(item for item in self.lifecycles if item.id == name)

    def validate_edge(
        self, transition: str, before: Mapping[str, str], after: Mapping[str, str]
    ) -> TransitionDefinition:
        """Check a declared finite edge. Named guards/effects still require their native owner."""
        edge = next(item for item in self.transitions if item.id == transition)
        lifecycle = self.lifecycle(edge.lifecycle)
        prior, result = lifecycle.state(before), lifecycle.state(after)
        if prior.id not in edge.from_states or result.id not in edge.to_states:
            _fail("invalid_transition", edge.id, f"unsupported edge {prior.id} -> {result.id}")
        return edge


def _validate_effect_support(model: ExecutionModelProducts, operation: OperationContract) -> None:
    from .effect_support import SUPPORTED_EFFECTS

    if operation.implementation is None:
        raise PreparationError(
            (
                Diagnostic(
                    "unsupported_operation",
                    "operations/" + operation.id,
                    "operation is declared but has no qualified producer implementation",
                    contract_id=operation.id,
                    consumer="bound_execution_model",
                    expected="independently qualified implementation binding",
                    actual="unbound declaration",
                    remedy="qualify the producer and its consumers, then derive a new release",
                ),
            )
        )
    supported = SUPPORTED_EFFECTS.get(operation.id)
    binding = next(b for b in model.implementations if b.id == operation.implementation)
    actual = {
        "implementation": operation.implementation,
        "version": binding.version,
        "effects": tuple(sorted(operation.effects)),
        "transitions": {
            t.id: tuple(sorted(t.effects)) for t in model.transitions if t.operation == operation.id
        },
    }
    if supported != actual:
        raise PreparationError(
            (
                Diagnostic(
                    "unsupported_effect_profile",
                    operation.id,
                    "required effects differ from the owned implementation",
                    contract_id=operation.id,
                    consumer=f"{binding.owner}:{binding.symbol}",
                    expected=repr(supported),
                    actual=repr(actual),
                    remedy=(
                        "implement the required bounded effect profile, then "
                        "ci schema derive --out <new-directory> and deploy a reviewed "
                        "forward revision"
                    ),
                ),
            )
        )


def execution_payload(prepared) -> bytes | None:
    """Carry the exact owned execution recipe with a detached analytical input."""
    if prepared.execution_model_id is None:
        return None
    rows = [row for row in prepared.registry_rows if row.kind == "execution_model"]
    if len(rows) != 1 or rows[0].name != prepared.execution_model_id:
        _fail(
            "execution_binding",
            prepared.release_id,
            "exactly one matching execution product is required",
        )
    return rows[0].body


def require_bound_operation(prepared, name: str) -> None:
    payload = execution_payload(prepared)
    require_payload_operation(payload, prepared.execution_model_id, name)


def require_payload_operation(payload: bytes | None, model_id: str | None, name: str) -> None:
    if model_id is None:
        if payload is not None:
            _fail("execution_binding", name, "execution payload requires its model identity")
        _fail("missing_execution_model", name, "operation requires a composed execution binding")
    if payload is None:
        _fail(
            "missing_execution_model",
            name,
            "composed operation requires its bound execution payload",
        )
    data = json.loads(payload)
    if data.get("model_id") != model_id:
        _fail("execution_binding", name, "execution payload identity differs")
    _bound_execution_model(payload, model_id).require_operation(name)


def require_database_operation(connection, release_id: str, name: str) -> None:
    from ._operation_calls import require_execution_operation
    from ._operation_ids import ReleaseId

    require_execution_operation(
        connection,
        release_id=ReleaseId(release_id),
        operation=name,
    )


def bound_execution_model(prepared) -> ExecutionModelProducts:
    """Read a mandatory immutable execution product, without a current-model fallback."""
    if prepared.execution_model_id is None:
        _fail(
            "missing_execution_model",
            prepared.release_id,
            "operation requires a composed execution binding",
        )
    rows = [row for row in prepared.registry_rows if row.kind == "execution_model"]
    if len(rows) != 1 or rows[0].name != prepared.execution_model_id:
        _fail(
            "execution_binding",
            prepared.release_id,
            "exactly one matching execution model is required",
        )
    return _bound_execution_model(rows[0].body, prepared.execution_model_id)


@lru_cache(maxsize=16)
def _bound_execution_model(body: bytes, model_id: str) -> ExecutionModelProducts:
    try:
        data = json.loads(body)
    except ValueError as exc:
        _fail("contract_product", model_id, str(exc))
    if not isinstance(data, dict) or not isinstance(data.get("inputs"), dict):
        _fail("contract_product", model_id, "execution product and inputs must be objects")
    compiler = data["inputs"].get("compiler_version")
    if compiler not in _READABLE_EXECUTION_COMPILERS:
        _fail(
            "unsupported_execution_abi",
            model_id,
            f"execution product requires current compiler {EXECUTION_COMPILER_VERSION}; "
            "regenerate the release",
        )
    if data.get("model_id") != model_id:
        _fail("execution_binding", model_id, "execution product identity differs")
    # Archived products are normalized at their original preparation boundary. Reading
    # verified immutable bytes must not re-admit them against installed capability sets.
    # Actual execution still requires effect support, fixed-call continuity and native
    # release admission.
    try:
        if "content" in data:
            _fail("contract_product", model_id, "encoded execution product cannot contain content")
        return _PRODUCT_CONVERTER.structure(
            {
                **{k: v for k, v in data.items() if k not in {"model_id", "inputs"}},
                "model_id": model_id,
                "content": body,
            },
            ExecutionModelProducts,
        )
    except PreparationError:
        raise
    except Exception as exc:
        _fail("contract_product", model_id, "; ".join(transform_error(exc)))


def _fail(code: str, location: str, message: str) -> Never:
    raise PreparationError((Diagnostic(code, location, message),))


def trusted_execution_schema() -> SourceBundle:
    """Acquire the one closed schema bundle without implementation/provider acquisition."""
    root = files("corpus_structure").joinpath("model", "semantic")
    return SourceBundle(
        "contracts",
        (
            SourceArtifact("contracts", root.joinpath("contracts.yaml").read_bytes()),
            SourceArtifact("semantic_reference", root.joinpath("reference.yaml").read_bytes()),
            SourceArtifact("native_adapters", root.joinpath("native-adapters.yaml").read_bytes()),
            SourceArtifact("pdf_products", root.joinpath("pdf-products.yaml").read_bytes()),
            SourceArtifact("observations", root.joinpath("observations.yaml").read_bytes()),
            SourceArtifact(
                "operation_reports", root.joinpath("operation-reports.yaml").read_bytes()
            ),
        ),
    )


def trusted_execution_inputs(
    *, physical_sources: Mapping[str, bytes] | None = None
) -> ExecutionModelInputs:
    """Read bundled code-owned definitions once at an explicit application entry boundary."""
    root = files("corpus_structure").joinpath("model", "semantic")
    return ExecutionModelInputs(
        trusted_execution_schema(),
        SourceArtifact("execution-model.yaml", root.joinpath("execution-model.yaml").read_bytes()),
        semantic_implementation_inputs(
            analysis_implementation_inputs(physical_sources=physical_sources)
        ),
    )


def analysis_implementation_inputs(
    *, physical_sources: Mapping[str, bytes] | None = None
) -> tuple[SourceArtifact, ...]:
    """Acquire implementation determinants explicitly; the compiler never reads installed code."""
    from importlib.metadata import version
    from pathlib import Path

    math = files("corpus_structure").joinpath("methods", "math")
    root = files("corpus_structure")
    shipped = files("sympy").joinpath("parsing", "latex", "lark", "grammar", "latex.lark")
    from corpus_structure.ingest.pdf import pdf_package_versions

    model_root = root.joinpath("model/semantic")
    if physical_sources is None:
        physical_sources = physical_source_closure(
            PHYSICAL_ROOT, lambda name: model_root.joinpath(name).read_bytes()
        )

    def model_source(name: str) -> bytes:
        if name in physical_sources:
            return physical_sources[name]
        return model_root.joinpath(name).read_bytes()

    if PHYSICAL_ROOT not in physical_sources:
        raise ValueError("explicit physical sources lack the root declaration")

    captured = (
        *(
            SourceArtifact(name, root.joinpath(*path.split("/")).read_bytes())
            for name, path in (
                ("text/sentences.py", "ingest/sentences.py"),
                ("text/structure.py", "core/text_structure.py"),
                ("text/tex.py", "core/tex.py"),
                ("text/macros.py", "ingest/macros.py"),
                ("parsing/native_adapters.py", "semantic/native_adapter_contracts.py"),
                ("capture/analytics.py", "semantic/analytics.py"),
                ("invocation/scheduler.py", "orchestrate/semantic.py"),
                ("invocation/automated.py", "intervene/automated.py"),
                ("invocation/source_frames.py", "semantic/source_frames.py"),
                ("invocation/proposals.py", "semantic/proposals.py"),
                ("invocation/source_search.py", "serve/source_search.py"),
                ("pdf/native_source.py", "serve/native_source.py"),
                *POSTGRESQL_IMPLEMENTATION_SOURCES,
                ("invocation/server.py", "intervene/semantic_server.py"),
                ("invocation/method.py", "core/method.py"),
                ("invocation/operations.py", "semantic/operations.py"),
                ("invocation/runtime-bindings.py", "semantic/runtime_bindings.py"),
                ("invocation/runtime-binding-store.py", "semantic/runtime_binding_store.py"),
                ("invocation/runtime-bindings.sql", "semantic/sql/runtime_bindings.sql"),
                ("records/records.py", "semantic/records.py"),
                *M1_IMPLEMENTATION_SOURCES,
                ("records/record-contracts.py", "semantic/record_contracts.py"),
                ("records/observations.py", "semantic/observations.py"),
                ("operations/section-packets.json", "model/semantic/nce-section-packets.json"),
                ("operations/named-link-rules.json", "methods/named_link_rules.json"),
                ("operations/named-link-coverage.json", "methods/named_link_coverage.json"),
                (
                    "operations/predicate-interpretation.json",
                    "methods/predicate_interpretation.json",
                ),
                ("operations/model-observation.json", "methods/model_observation.json"),
                ("capture/storage.py", "semantic/capture_storage.py"),
                ("publication/arrow.py", "semantic/arrow_publication.py"),
                ("graph/ontology.py", "semantic/ontology.py"),
                ("text/scope.py", "methods/math/scope.py"),
                ("pdf/source_views.py", "semantic/source_views.py"),
                ("pdf/requests.py", "semantic/native_requests.py"),
                ("pdf/visual-requests.py", "semantic/visual_requests.py"),
                ("pdf/visual-mapping.py", "semantic/pdf_visual_mapping.py"),
                ("pdf/visual-reader.py", "serve/pdf_visual_evidence.py"),
                ("pdf/visual-packet.py", "serve/visual_evidence_packet.py"),
                ("pdf/chandra.py", "ingest/pdf_chandra.py"),
                ("pdf/capacity.py", "ingest/pdf_capacity.py"),
                ("pdf/claims.py", "semantic/claim_lifetime.py"),
                ("pdf/assets.py", "ingest/pdf_assets.py"),
                ("pdf/candidates.py", "ingest/pdf_candidates.py"),
                ("pdf/candidate-source.py", "ingest/pdf_candidate_source.py"),
                ("pdf/candidate-geometry.py", "ingest/pdf_candidate_geometry.py"),
                ("pdf/methods.py", "ingest/pdf_methods.py"),
                ("pdf/math.py", "methods/math/native.py"),
                ("pdf/analysis.py", "semantic/native_analysis.py"),
                ("pdf/topology.py", "methods/math/native_topology.py"),
                ("pdf/enrichment.py", "ingest/pdf_enrichment.py"),
                ("pdf/regions.py", "serve/native_regions.py"),
                ("alignment/semantic_alignment.py", "evaluate/semantic_alignment.py"),
                ("alignment/preparation.py", "evaluate/alignment_preparation.py"),
                ("ingest/methods.py", "ingest/methods.py"),
                ("pdf/converter.py", "ingest/pdf.py"),
                ("pdf/worker.py", "ingest/pdf_worker.py"),
                ("pdf/health.py", "ingest/pdf_health.py"),
                ("pdf/ocr.py", "ingest/pdf_ocr.py"),
                ("pdf/ocr_contracts.py", "semantic/pdf_ocr_contracts.py"),
                ("pdf/registry.py", "orchestrate/phase0.py"),
                ("pdf/hierarchy.py", "ingest/pdf_hierarchy.py"),
                ("placement/cascade.py", "methods/llm/cascade.py"),
            )
        ),
        SourceArtifact(
            "pdf/docling-validation.schema.json",
            root.joinpath("model", "semantic", "docling-validation.schema.json").read_bytes(),
        ),
        SourceArtifact(
            "pdf/section-text-recipe.json",
            root.joinpath("model", "semantic", "section-text-recipe.json").read_bytes(),
        ),
        SourceArtifact("pdf/record-model.yaml", model_source("pdf-records.yaml")),
        SourceArtifact("unified/linkml-types.yaml", linkml_types_source()),
        SourceArtifact("pdf/record-physical.yaml", physical_sources[PHYSICAL_ROOT]),
        *(
            SourceArtifact(_PHYSICAL_IMPORT_PREFIX + name, content)
            for name, content in sorted(physical_sources.items())
            if name not in _PHYSICAL_ARTIFACTS
        ),
        *(
            SourceArtifact(
                name,
                model_source("pdf-staging.yaml")
                if name == "pdf/staging-model.yaml"
                else root.joinpath(*path.split("/")).read_bytes(),
            )
            for name, path in (
                ("pdf/read-projections.yaml", "model/semantic/read-projections.yaml"),
                ("pdf/record-relational.py", "schema/relational.py"),
                ("pdf/record-boundaries.py", "semantic/pdf_record_model.py"),
                ("pdf/records.py", "semantic/pdf_records.py"),
                ("pdf/record-identity.py", "semantic/pdf_record_identity.py"),
                ("pdf/staging.py", "semantic/pdf_staging.py"),
                ("pdf/record-product.py", "ingest/pdf_record_product.py"),
                ("pdf/retained-stream.py", "ingest/pdf_retained_stream.py"),
                ("orchestration/semantic.py", "orchestrate/semantic.py"),
                ("orchestration/source-reader.py", "orchestrate/source_reader.py"),
                ("pdf/publication.py", "semantic/pdf_publication.py"),
                ("pdf/record-logical-identity.sql", "semantic/sql/pdf_record_logical_identity.sql"),
                ("pdf/record-proof-reader.sql", "semantic/sql/pdf_record_proof_reader.sql"),
                (
                    "pdf/record-access-correspondence.sql",
                    "semantic/sql/pdf_record_access_correspondence.sql",
                ),
                ("pdf/record-context.sql", "semantic/sql/pdf_record_context.sql"),
                ("pdf/publication-native.py", "semantic/pdf_publication_native.py"),
                ("pdf/record-reader-native.py", "semantic/pdf_record_reader_native.py"),
                ("pdf/staging-model.yaml", "model/semantic/pdf-staging.yaml"),
                ("pdf/streaming.py", "ingest/pdf_streaming.py"),
                ("pdf/assembly.py", "ingest/pdf_assembly.py"),
                ("pdf/stream-types.py", "ingest/pdf_stream_types.py"),
                ("pdf/stream-reconciliation.py", "ingest/pdf_stream_reconciliation.py"),
                ("pdf/incumbent-recovery.py", "ingest/pdf_incumbent_recovery.py"),
                ("pdf/stream-orchestration.py", "orchestrate/pdf_streaming.py"),
            )
        ),
        SourceArtifact(
            "pdf/contracts.py", root.joinpath("semantic", "pdf_contracts.py").read_bytes()
        ),
        SourceArtifact(
            "pdf/integrated.py", root.joinpath("semantic", "pdf_integrated.py").read_bytes()
        ),
        SourceArtifact(
            "pdf/recognition.py", root.joinpath("ingest", "pdf_recognition.py").read_bytes()
        ),
        SourceArtifact(
            "pdf/recognition_methods.py",
            root.joinpath("ingest", "pdf_recognition_methods.py").read_bytes(),
        ),
        SourceArtifact(
            "pdf/reconciliation.py", root.joinpath("ingest", "pdf_reconciliation.py").read_bytes()
        ),
        SourceArtifact(
            "pdf/bulk_remove.py", root.joinpath("ingest", "pdf_bulk_remove.py").read_bytes()
        ),
        SourceArtifact("pdf/storage.py", root.joinpath("semantic", "pdf_storage.py").read_bytes()),
        SourceArtifact("grammar/grammar.py", math.joinpath("grammar.py").read_bytes()),
        SourceArtifact("grammar/extension.lark", math.joinpath("extension.lark").read_bytes()),
        SourceArtifact("grammar/prepared.py", math.joinpath("prepared.py").read_bytes()),
        SourceArtifact(
            "grammar/source_context.py", math.joinpath("source_context.py").read_bytes()
        ),
        SourceArtifact("grammar/spans.py", math.joinpath("spans.py").read_bytes()),
        SourceArtifact("grammar/methods.py", math.joinpath("methods.py").read_bytes()),
        SourceArtifact("grammar/_tree.py", math.joinpath("_tree.py").read_bytes()),
        SourceArtifact("grammar/shipped.lark", shipped.read_bytes()),
        SourceArtifact("transformer/transform.py", math.joinpath("transform.py").read_bytes()),
        SourceArtifact(
            "transformer/native_context.py", math.joinpath("native_context.py").read_bytes()
        ),
        SourceArtifact(
            "text/model.json",
            canonical_bytes(
                {
                    str(path.relative_to(Path(str(files("en_core_web_sm"))))): sha256(
                        path.read_bytes()
                    ).hexdigest()
                    for path in sorted(Path(str(files("en_core_web_sm"))).rglob("*"))
                    if path.is_file() and path.suffix != ".pyc" and "__pycache__" not in path.parts
                }
            ),
        ),
        SourceArtifact(
            "libraries.json",
            canonical_bytes(
                {
                    name: version(name)
                    for name in (
                        "pyarrow",
                        "duckdb",
                        "sqlglot",
                        "sqlalchemy",
                        "pgvector",
                        "pyyaml",
                        "linkml-runtime",
                        "adbc-driver-postgresql",
                        "pgpq",
                        "rdflib",
                        "pyshacl",
                        "sympy",
                        "lark",
                        "spacy",
                        "en-core-web-sm",
                        "scipy",
                        "networkx",
                        "rapidfuzz",
                        "regex",
                    )
                }
                | dict(pdf_package_versions())
            ),
        ),
    )

    # Include the complete owned executable package as runtime custody. Named aliases above
    # remain for existing consumers; adding a helper must not escape the runtime fingerprint.
    package = Path(str(root))
    return (
        *captured,
        *(
            SourceArtifact("package/" + str(path.relative_to(package)), path.read_bytes())
            for path in sorted(package.rglob("*"))
            if path.is_file() and path.suffix in {".py", ".sql"}
        ),
    )


def _plain(value: Any) -> Any:
    # DupCheckYamlLoader returns location-tagged str subclasses. Lower only those wrappers;
    # do not coerce numbers, booleans, null or other invalid authored field values.
    if isinstance(value, str):
        return str.__str__(value)
    if isinstance(value, dict):
        return {_plain(k): _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


def _index(items: tuple[Any, ...], location: str) -> dict[str, Any]:
    index = {item.id: item for item in items}
    if len(index) != len(items):
        _fail("duplicate_definition", location, "definition ids must be unique")
    return index


def _refs(names: tuple[str, ...], index: Mapping[str, Any], location: str) -> None:
    if len(set(names)) != len(names):
        _fail("duplicate_reference", location, "repeated reference")
    for name in names:
        if name not in index:
            _fail("unresolved_contract_reference", location, name)


def _product_converter() -> Converter:
    """Prepare conversion for admitted records; never a replacement ingress validator."""
    converter = Converter(forbid_extra_keys=True, detailed_validation=True)

    def exact(value: Any, expected: type) -> Any:
        if type(value) is not expected:
            raise TypeError(f"expected {expected.__name__}, got {type(value).__name__}")
        return value

    # Register primitives before composite hooks capture their dependencies.
    for primitive in (str, int, bool, bytes, float):
        converter.register_structure_hook(primitive, exact)
    return converter


_PRODUCT_CONVERTER = _product_converter()


def _normalize(
    data: dict[str, Any],
    model_id: str,
    *,
    reference_splits: tuple[str, ...],
) -> ExecutionModelProducts:
    # Version is already checked by the admitted LinkML catalog boundary.
    fields = {key: value for key, value in data.items() if key != "version"}
    try:
        products = _PRODUCT_CONVERTER.structure(
            {
                **fields,
                "model_id": model_id,
                "content": b"",
                "reference_splits": reference_splits,
            },
            ExecutionModelProducts,
        )
    except Exception as exc:
        _fail("contract_product", "ExecutionCatalog", "; ".join(transform_error(exc)))
    _validate(products)
    return products


def _validate(
    products: ExecutionModelProducts,
) -> None:
    from .analysis_contracts import validate_analysis_profiles

    validate_analysis_profiles(products)
    c = _index(products.concepts, "concepts")
    r = _index(products.relationships, "relationships")
    lifecycles = _index(products.lifecycles, "lifecycles")
    t = _index(products.transitions, "transitions")
    o = _index(products.operations, "operations")
    i = _index(products.invariants, "invariants")
    b = _index(products.implementations, "implementations")
    p = _index(products.projections, "projections")
    domains = _index(products.outcome_domains, "outcome_domains")
    capabilities = {name: name for name in products.required_capabilities}
    _refs(products.required_capabilities, capabilities, "required_capabilities")
    for concept in products.concepts:
        if len({a.name for a in concept.attributes}) != len(concept.attributes):
            _fail("duplicate_attribute", concept.id, "attribute names must be unique")
        for attribute in concept.attributes:
            if attribute.range not in c and attribute.range not in {
                "text",
                "integer",
                "boolean",
                "decimal",
                "datetime",
                "bytes",
                "json",
            }:
                _fail("attribute_range", concept.id, attribute.range)
        _refs(concept.relationships, r, concept.id)
    for relation in products.relationships:
        roles = {e.role: e for e in relation.endpoints}
        if len(roles) != len(relation.endpoints):
            _fail("duplicate_role", relation.id, "endpoint roles must be unique")
        for endpoint in relation.endpoints:
            _refs((endpoint.concept,), c, relation.id)
            if endpoint.maximum is not None and endpoint.maximum < endpoint.minimum:
                _fail("cardinality", relation.id, endpoint.role)
            if endpoint.unresolved != (endpoint.unresolved_concept is not None):
                _fail("unresolved_endpoint", relation.id, endpoint.role)
            if endpoint.unresolved_concept is not None:
                _refs((endpoint.unresolved_concept,), c, relation.id)
        _refs(relation.identity_roles, roles, relation.id + "/identity_roles")
        _refs(relation.qualifications, c, relation.id + "/qualifications")
        _refs(relation.invariants, i, relation.id + "/invariants")
        scoped = any(c[e.concept].scope == "realization" for e in relation.endpoints)
        required_context = (
            {"release", "realization"}
            if relation.reference_scope == "same_realization"
            else {"input_release", "input_realization", "output_release", "output_realization"}
        )
        if scoped and (
            relation.reference_scope == "execution"
            or not required_context <= set(relation.identity_context)
        ):
            _fail(
                "unqualified_reference",
                relation.id,
                "scoped references require explicit release/realization context",
            )
        if relation.identity_kind == "unordered_distinct" and relation.multiplicity != "set":
            _fail(
                "relationship_identity",
                relation.id,
                "unordered distinct identity requires set membership",
            )
    for concept in products.concepts:
        for relation in concept.relationships:
            if concept.id not in {e.concept for e in r[relation].endpoints}:
                _fail("relationship_subject", concept.id, relation)
    for invariant in products.invariants:
        _refs(invariant.subjects, c, invariant.id)
        _refs(invariant.relationships, r, invariant.id)
        _refs((invariant.implementation,), b, invariant.id)
        if invariant.required_capability is not None:
            _refs((invariant.required_capability,), capabilities, invariant.id)
    guards = _index(products.native_guards, "native_guards")
    if set(guards) != set(_APPROVED_NATIVE_GUARDS):
        _fail("native_guard_coverage", "native_guards", "required native kernel binding is missing")
    for guard in products.native_guards:
        if _APPROVED_NATIVE_GUARDS.get(guard.id) != (guard.symbol, guard.version):
            _fail("unapproved_native_guard", guard.id, guard.symbol)
        _refs(guard.invariants, i, guard.id)
    from .effect_support import SUPPORTED_EFFECT_VERSIONS

    effects = _index(products.effect_definitions, "effect_definitions")
    for effect in effects.values():
        supported_version = SUPPORTED_EFFECT_VERSIONS.get(effect.id)
        if effect.version != supported_version or not effect.meaning.strip():
            raise PreparationError(
                (
                    Diagnostic(
                        "unsupported_effect",
                        effect.id,
                        "unsupported effect identity/version or empty description",
                        contract_id=effect.id,
                        consumer="owned effect implementation",
                        expected=repr(supported_version),
                        actual=effect.version,
                        remedy=(
                            "implement this effect version and derive a new reviewed "
                            "release before admission"
                        ),
                    ),
                )
            )
    for item in (*products.operations, *products.transitions, *products.implementations):
        _refs(item.effects, effects, item.id)
    owned = approved_implementations()
    for binding in products.implementations:
        implementation = owned.get(binding.id)
        expected = (
            (
                implementation.__module__.removeprefix("corpus_structure."),
                implementation.__qualname__,
            )
            if implementation is not None
            else None
        )
        if expected != (binding.owner, binding.symbol):
            _fail("unapproved_implementation", binding.id, f"{binding.owner}:{binding.symbol}")
        _refs(binding.input_concepts, c, binding.id)
        _refs(binding.result_concepts, c, binding.id)
        _refs(binding.required_capabilities, capabilities, binding.id)
    for lifecycle in products.lifecycles:
        _refs((lifecycle.subject,), c, lifecycle.id)
        dimensions = _index(lifecycle.dimensions, lifecycle.id)
        for dimension in lifecycle.dimensions:
            if len(set(dimension.values)) != len(dimension.values):
                _fail("duplicate_state_value", lifecycle.id, dimension.id)
        states = _index(lifecycle.states, lifecycle.id)
        combinations = set()
        for state in lifecycle.states:
            values = {v.dimension: v.value for v in state.values}
            if len(values) != len(state.values) or set(values) != set(dimensions):
                _fail("state_dimensions", lifecycle.id, state.id)
            for dimension, value in values.items():
                if value not in dimensions[dimension].values:
                    _fail("state_value", lifecycle.id, f"{dimension}={value}")
            combination = tuple(sorted(values.items()))
            if combination in combinations:
                _fail("duplicate_composed_state", lifecycle.id, state.id)
            combinations.add(combination)
        _refs(lifecycle.initial_states, states, lifecycle.id)
        _refs(lifecycle.transitions, t, lifecycle.id)
        _refs(lifecycle.invariants, i, lifecycle.id)
        for edge in lifecycle.transitions:
            if t[edge].lifecycle != lifecycle.id:
                _fail("transition_lifecycle", lifecycle.id, edge)
    for transition in products.transitions:
        _refs((transition.lifecycle,), lifecycles, transition.id)
        lifecycle = lifecycles[transition.lifecycle]
        states = {state.id: state for state in lifecycle.states}
        _refs(transition.from_states, states, transition.id)
        _refs(transition.to_states, states, transition.id)
        _refs((transition.operation,), o, transition.id)
        _refs(transition.invariants, i, transition.id)
        if (
            transition.id not in lifecycle.transitions
            or transition.id not in o[transition.operation].transitions
        ):
            _fail(
                "unlinked_transition",
                transition.id,
                "lifecycle and operation must both link their edge",
            )
        if any(states[s].terminal for s in transition.from_states):
            _fail("terminal_transition", transition.id, "terminal subjects cannot reopen")
        if not set(transition.outcomes) <= set(o[transition.operation].outcomes):
            _fail("transition_outcome", transition.id, "outcome outside operation contract")
    for operation in products.operations:
        if operation.policy_version is not None and not operation.policy_version.strip():
            _fail("operation_policy_version", operation.id, "policy version must be nonempty")
        _refs(operation.inputs, c, operation.id)
        _refs(operation.results, c, operation.id)
        _refs(operation.applicability, i, operation.id)
        if operation.implementation is not None:
            _refs((operation.implementation,), b, operation.id)
        _refs(operation.transitions, t, operation.id)
        _refs(operation.projections, p, operation.id)
        _refs((operation.outcome_domain,), domains, operation.id)
        _index(operation.result_dimensions, operation.id + "/result_dimensions")
        for dimension in operation.result_dimensions:
            _refs((dimension.outcome_domain,), domains, operation.id + "/" + dimension.id)
            if not dimension.field:
                _fail("result_dimension", operation.id, "result field must be explicit")
        domain = domains[operation.outcome_domain]
        if domain.authority == "code" and not set(operation.outcomes) <= set(domain.values):
            _fail("operation_outcome", operation.id, "outcome outside code-owned domain")
        if operation.implementation is None:
            if operation.effects or operation.transitions or operation.projections:
                _fail(
                    "unbound_operation_effects",
                    "operations/" + operation.id,
                    "unbound declarations cannot authorize effects, transitions or projections",
                )
            continue
        binding = b[operation.implementation]
        if set(operation.inputs) != set(binding.input_concepts) or set(operation.results) != set(
            binding.result_concepts
        ):
            _fail(
                "implementation_contract",
                operation.id,
                "typed input/result contract differs from implementation binding",
            )
        if set(operation.effects) != set(binding.effects):
            _fail(
                "implementation_effects",
                operation.id,
                "operation and implementation effects differ",
            )
        _validate_effect_support(products, operation)
        for edge in operation.transitions:
            if t[edge].operation != operation.id:
                _fail("operation_transition", operation.id, edge)
    if products.parsing_adapters:
        from .native_adapter_contracts import validate_native_adapters

        validate_native_adapters(products)
    for projection in products.projections:
        _refs(projection.sources, c, projection.id)
        _refs(projection.relationships, r, projection.id)
        _refs((projection.implementation,), b, projection.id)
    for domain in products.outcome_domains:
        if domain.authority == "code" and not domain.values:
            _fail(
                "outcome_authority",
                domain.id,
                "code-owned outcome domain must be finite and nonempty",
            )
        if len(set(domain.values)) != len(domain.values):
            _fail("duplicate_outcome", domain.id, "outcomes must be distinct")
        if domain.authority == "release" and domain.values:
            _fail(
                "outcome_authority", domain.id, "release-authored members require the bound release"
            )
    from .outcomes import CODE_OUTCOME_DOMAINS

    for name, annotation in CODE_OUTCOME_DOMAINS.items():
        if name not in domains or set(domains[name].values) != set(annotation):
            _fail(
                "outcome_implementation", name, "code outcome domain differs from trusted catalog"
            )
    translations = set()
    for translation in products.outcome_translations:
        _refs(
            (translation.source_domain, translation.target_domain), domains, "outcome_translation"
        )
        _refs((translation.invariant,), i, "outcome_translation")
        if (
            translation.source not in domains[translation.source_domain].values
            or translation.target not in domains[translation.target_domain].values
        ):
            _fail("translation_outcome", "outcome_translation", "unknown outcome")
        key = (translation.source_domain, translation.source, translation.target_domain)
        if key in translations:
            _fail("duplicate_translation", "outcome_translation", str(key))
        translations.add(key)
    from .invariant_failures import validate_invariant_diagnostics

    validate_invariant_diagnostics(products)


def _collection_defaults(
    name: str, body: dict[str, Any], definitions: Mapping[str, ClassDefinition]
) -> dict[str, Any]:
    """Normalize absent optional collections from the admitted schema, never nulls."""
    result = dict(body)
    for prop in definitions[name].properties:
        if prop.multivalued and not prop.required and prop.name not in result:
            result[prop.name] = []
        if prop.range in definitions and prop.name in result:
            value = result[prop.name]
            result[prop.name] = (
                [_collection_defaults(prop.range, row, definitions) for row in value]
                if prop.multivalued
                else _collection_defaults(prop.range, value, definitions)
            )
    return result


def compile_execution_model(inputs: ExecutionModelInputs) -> ExecutionModelProducts:
    """Compile only explicit immutable inputs, with bounded reuse of pure products."""
    try:
        hash(inputs)
    except TypeError:
        return _compile_execution_model(inputs)
    return _compile_execution_model_cached(inputs, EXECUTION_COMPILER_VERSION)


@lru_cache(maxsize=8)
def _compile_execution_model_cached(
    inputs: ExecutionModelInputs, compiler_version: str
) -> ExecutionModelProducts:
    return _compile_execution_model(inputs)


def _compile_execution_model(inputs: ExecutionModelInputs) -> ExecutionModelProducts:
    """Compile only supplied immutable bytes; no application defaults, imports or invocation."""

    from .prepare import prepare_release

    try:
        raw = _plain(yaml.load(inputs.catalog.content, Loader=DupCheckYamlLoader))
    except Exception as exc:
        _fail("contract_catalog", inputs.catalog.name, str(exc))
    # The existing admitted LinkML profile supplies the sole field/enum/local-shape authority.
    companion = prepare_release(inputs.schema)
    try:
        data = companion.validate_json("ExecutionCatalog", json.dumps(raw)).model_dump(mode="json")
    except (ValidationError, TypeError, ValueError) as exc:
        _fail("contract_catalog", inputs.catalog.name, str(exc))
    data = _collection_defaults(
        "ExecutionCatalog", data, {d.name: d for d in companion.definitions}
    )
    if not data["analysis_profiles"] or any(
        profile["version"] != "6" for profile in data["analysis_profiles"]
    ):
        _fail(
            "missing_analysis_profile",
            inputs.catalog.name,
            "declare the required analysis preparation profile",
        )
    names = tuple(item.name for item in inputs.implementations)
    required_implementations = {
        "invocation/scheduler.py",
        "invocation/automated.py",
        "invocation/source_frames.py",
        "invocation/proposals.py",
        "records/records.py",
        "records/record-contracts.py",
        "records/observations.py",
        "invocation/source_search.py",
        "pdf/native_source.py",
        "invocation/server.py",
        "text/sentences.py",
        "text/structure.py",
        "parsing/native_adapters.py",
        "capture/analytics.py",
        "capture/storage.py",
        "publication/arrow.py",
        "graph/ontology.py",
        "text/scope.py",
        "pdf/source_views.py",
        "pdf/requests.py",
        "pdf/claims.py",
        "pdf/assets.py",
        "pdf/candidates.py",
        "pdf/methods.py",
        "pdf/math.py",
        "pdf/analysis.py",
        "pdf/topology.py",
        "pdf/enrichment.py",
        "pdf/regions.py",
        "pdf/converter.py",
        "pdf/worker.py",
        "pdf/candidate-source.py",
        "pdf/candidate-geometry.py",
        "pdf/health.py",
        "pdf/ocr.py",
        "pdf/ocr_contracts.py",
        "pdf/registry.py",
        "pdf/hierarchy.py",
        "alignment/semantic_alignment.py",
        "placement/cascade.py",
        "alignment/preparation.py",
        "ingest/methods.py",
        "text/model.json",
        "grammar/grammar.py",
        "grammar/extension.lark",
        "grammar/prepared.py",
        "grammar/_tree.py",
        "grammar/shipped.lark",
        "transformer/transform.py",
        "transformer/native_context.py",
        "libraries.json",
        "pdf/record-model.yaml",
        "unified/linkml-types.yaml",
        "pdf/record-physical.yaml",
        "pdf/read-projections.yaml",
        "pdf/record-relational.py",
        "pdf/record-boundaries.py",
        "pdf/records.py",
        "pdf/record-identity.py",
        "pdf/staging.py",
        "pdf/record-product.py",
        "pdf/retained-stream.py",
        "orchestration/semantic.py",
        "orchestration/source-reader.py",
        "pdf/publication.py",
        "pdf/publication-native.py",
        "pdf/record-reader-native.py",
        "pdf/record-logical-identity.sql",
        "pdf/record-access-correspondence.sql",
        "pdf/record-context.sql",
        "pdf/staging-model.yaml",
        "pdf/streaming.py",
        "pdf/assembly.py",
        "pdf/stream-types.py",
        "pdf/stream-reconciliation.py",
        "pdf/stream-orchestration.py",
    }
    required_implementations.update(name for name, _ in POSTGRESQL_IMPLEMENTATION_SOURCES)
    required_implementations.update(name for name, _ in M1_IMPLEMENTATION_SOURCES)
    if "operations/section-packets.json" in names or "operations/named-link-rules.json" in names:
        required_implementations.update(
            {"operations/section-packets.json", "operations/named-link-rules.json"}
        )
    if "operations/named-link-coverage.json" in names:
        required_implementations.add("operations/named-link-coverage.json")
    required_implementations.update(
        {
            "pdf/section-text-recipe.json",
            "operations/predicate-interpretation.json",
            "operations/model-observation.json",
        }.intersection(names)
    )
    if any(profile.get("version") == "6" for profile in data["analysis_profiles"]):
        required_implementations.update(
            {
                "grammar/source_context.py",
                "grammar/spans.py",
                "grammar/methods.py",
                "text/tex.py",
                "text/macros.py",
                "invocation/method.py",
                "invocation/operations.py",
            }
        )
    if any(source.name == "pdf_products" for source in inputs.schema.sources):
        required_implementations.update({"pdf/contracts.py", "pdf/docling-validation.schema.json"})
    if any(
        operation["id"] in {"prepare_integrated_pdf", "publish_pdf_observation", "read_pdf_product"}
        for operation in data["operations"]
    ):
        required_implementations.update(
            {
                "pdf/integrated.py",
                "pdf/storage.py",
                "pdf/reconciliation.py",
                "pdf/bulk_remove.py",
                "pdf/recognition.py",
                "pdf/recognition_methods.py",
            }
        )
    required_implementations.intersection_update(SEMANTIC_IMPLEMENTATION_NAMES)
    required_implementations.update(name for name in names if _physical_import_artifact(name))
    if set(names) != required_implementations or len(names) != len(set(names)):
        _fail(
            "analysis_implementation_inputs",
            inputs.catalog.name,
            "supply the exact semantic model/grammar/output-contract input set",
        )
    identity = {
        "implementations": [
            {"name": item.name, "sha256": item.digest} for item in inputs.implementations
        ],
        "compiler_version": EXECUTION_COMPILER_VERSION,
        "schema": {
            "root": inputs.schema.root,
            "sources": [{"name": s.name, "sha256": s.digest} for s in inputs.schema.sources],
        },
        "catalog": {"name": inputs.catalog.name, "sha256": inputs.catalog.digest},
    }
    model_id = "execution:" + sha256(canonical_bytes(identity)).hexdigest()
    products = replace(
        _normalize(data, model_id, reference_splits=tuple(sorted(companion.reference_splits()))),
        implementation_digests=tuple((item.name, item.digest) for item in inputs.implementations),
    )
    from .operation_call_generation import validate_call_bindings

    products = validate_call_bindings(products, inputs)
    normalized = {
        key: value
        for key, value in _PRODUCT_CONVERTER.unstructure(products).items()
        if key != "content"
    }
    return replace(products, content=canonical_bytes({"inputs": identity, **normalized}))
