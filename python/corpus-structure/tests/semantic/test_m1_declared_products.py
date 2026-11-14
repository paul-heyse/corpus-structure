"""Actual M1 nominal schema/producer capture; no provider execution claim."""

from pathlib import Path
from types import SimpleNamespace

from corpus_structure.core.method import CoverageDraft
from corpus_structure.core.vocab import ObservationOutcome
from corpus_structure.methods.m1_source import M1CandidateProduct
from corpus_structure.semantic import prepare_release
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import BoundRoleMember, SubjectContext
from corpus_structure.semantic.data_operation_member_contracts import derive_member_kinds
from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
from corpus_structure.semantic.m1_products import candidate_report, m1_operation_inputs, m1_operation_sources, m1_profile_assets
from corpus_structure.semantic.source_products import FrozenNativeSource, source_subject
from corpus_structure.semantic.types import SourceArtifact, SourceBundle

ROOT = Path(__file__).resolve().parents[4]


def record_schemas():
    return SourceBundle("statistics_semantic", (
        SourceArtifact("statistics_semantic", (ROOT / "domains/statistics/semantic.yaml").read_bytes()),
        SourceArtifact("statistics_terminology", (ROOT / "domains/statistics/terminology.yaml").read_bytes()),
        SourceArtifact("semantic_core", (ROOT / "python/corpus-structure/src/corpus_structure/model/semantic/core.yaml").read_bytes()),
    ))


def configuration():
    from corpus_structure.orchestrate.m1 import registry

    return registry(ROOT / "domains/statistics").overlay("extract.m1_candidates", "default")


def test_empty_m1_inspection_has_successful_typed_report_and_exact_denominator():
    prepared = prepare_release(m1_operation_inputs(record_schemas()))
    source = FrozenNativeSource.from_projection(prepared, document="original:doc", section_pointer="#/groups/0", membership="descendants", text="A valve opens.",
        pieces=[{"kind": "native_text", "item_ref": "#/texts/0", "source_field": "text", "start": 0, "end": 14}],
        items=[{"self_ref": "#/texts/0", "label": "text", "text": "A valve opens.", "orig": "A valve opens.", "prov": []}])
    scope = json_bytes({"source": source.value["source"], "selectors": source.value["selectors"]})
    member = BoundRoleMember("product:source-population", "kind:selected-source", source_subject(source.value["source"]), "original:doc", scope, b'{}', (), b'{}', member="member:source")
    frame = DeclaredNativeFrameSource.acquire(prepared, source.value, member, project="p")
    product = M1CandidateProduct(ObservationOutcome.EMPTY, parse_detail={"inspected_regions": 1}, coverage=(CoverageDraft(family="definition", scope="#/texts/0", outcome="complete"),), records=(), contributions=())
    report = candidate_report(prepared, SimpleNamespace(kinds=(), identities=()), product, frame, SubjectContext("p", member.subject, member.original_source, member.analyzed_scope))
    assert report["inspection_outcome"] == "empty"
    assert report["members"] == ()
    assert report["coverage"] == ({"family": "definition", "scope": "#/texts/0", "outcome": "complete"},)
    assert report["diagnostics_json"] == '{"inspected_regions":1}'
    assert report["source_pin"]["source_member"] == "member:source"


def test_actual_m1_producer_captures_selection_witnesses_and_single_stored_member_families():
    bundle = m1_operation_inputs(record_schemas())
    model = compile_data_operations(bundle, python_sources=m1_operation_sources(configuration(), record_schemas=record_schemas()))
    operation = model.operation("extract.m1_candidates")
    assert operation.consumer_selection.entrypoint == "corpus_structure.methods.m1_declared.M1SourceCandidatesOperation.select_hydrated"
    assert len(operation.output_witnesses) == 5
    assert {group.input_role for group in operation.output_witnesses} == {"primary", "sources"}
    output = next(role for role in operation.roles if role.direction == "output")
    assert derive_member_kinds(model, output.kind) == tuple(sorted(
        kind.semantic_id for kind in model.kinds if kind.name in {"DdoCandidateSourceRecord", "DdoCandidateSourceContribution"}
    ))


def test_m1_semantic_profile_excludes_snapshot_path_and_captures_record_schema():
    config = configuration()
    left = m1_profile_assets(config, record_schemas())
    right = m1_profile_assets(config.model_copy(update={"snapshot": Path("/different/physical/snapshot")}), record_schemas())
    assert left.content == right.content
    assert b'"schemas"' in left.content


def test_candidate_body_is_stored_once_and_keeps_required_source_record_anchors():
    import pytest
    from pydantic import ValidationError
    from corpus_structure.methods.record_assembly import LiteralSpan, NativeRecordGroup, RoleInput, assemble_native_records
    from corpus_structure.semantic.data_operation_ports import project_product_members
    from corpus_structure.semantic.source_contexts import NativeSourceContext, PreparedNativeSources, source_slice

    bundle = m1_operation_inputs(record_schemas())
    prepared = prepare_release(bundle)
    model = compile_data_operations(bundle)
    source = FrozenNativeSource.from_projection(prepared, document="original:doc", section_pointer="#/groups/0", membership="descendants", text="A valve opens.",
        pieces=[{"kind": "native_text", "item_ref": "#/texts/0", "source_field": "text", "start": 0, "end": 14}],
        items=[{"self_ref": "#/texts/0", "label": "text", "text": "A valve opens.", "orig": "A valve opens.", "prov": []}])
    scope = json_bytes({"source": source.value["source"], "selectors": source.value["selectors"]})
    member = BoundRoleMember("product:source-population", "kind:selected-source", source_subject(source.value["source"]), "original:doc", scope, b'{}', (), b'{}', member="member:source")
    frame = DeclaredNativeFrameSource.acquire(prepared, source.value, member, project="p")
    context = NativeSourceContext(frame, (), (source_slice(frame, 0, 14),), "definition", "test", "selected", version=2, preparation=PreparedNativeSources((frame,)))
    assembly = assemble_native_records(prepared, context, contract="DefinitionRecordFields", occurrence_roles=("term",), policy_version="reading-1", groups=(NativeRecordGroup((RoleInput("term", spans=(LiteralSpan(2, 7, "valve"),)),), "explicit term"),))
    records = tuple(record.model_dump(mode="python") for record in assembly.records)
    assert len(records) == 1
    product = M1CandidateProduct(ObservationOutcome.PRODUCED, records=records, contributions=())
    report = candidate_report(prepared, model, product, frame, SubjectContext("p", member.subject, member.original_source, member.analyzed_scope))
    assert "records" not in report and "contributions" not in report
    (packet,) = report["members"]
    assert packet["member_id"] == "record:" + records[0]["record_id"]
    assert packet["body"]["candidate_type"] == "record"
    assert packet["body"]["record_id"] == records[0]["record_id"]
    kind = next(kind.semantic_id for kind in model.kinds if kind.name == "DdoCandidateInspectionReport")
    assert len(project_product_members(model, kind, report)) == 1
    with pytest.raises(ValidationError):
        prepared.validate_json("DdoCandidateSourceRecord", json_bytes({name: value for name, value in packet["body"].items() if name != "anchors"}))


def test_partial_produced_inspection_preserves_real_candidates_after_later_worker_failure():
    from corpus_structure.methods.contribution_adapter import adapt_native_groups
    from corpus_structure.methods.record_assembly import LiteralSpan, NativeRecordGroup, RoleInput
    from corpus_structure.semantic.m1_products import complete_m1_inspection
    from corpus_structure.semantic.source_contexts import NativeSourceContext, PreparedNativeSources, source_slice

    bundle = m1_operation_inputs(record_schemas())
    prepared = prepare_release(bundle)
    model = compile_data_operations(bundle)
    source = FrozenNativeSource.from_projection(prepared, document="original:doc", section_pointer="#/groups/0", membership="descendants", text="A valve opens.",
        pieces=[{"kind": "native_text", "item_ref": "#/texts/0", "source_field": "text", "start": 0, "end": 14}],
        items=[{"self_ref": "#/texts/0", "label": "text", "text": "A valve opens.", "orig": "A valve opens.", "prov": []}])
    scope = json_bytes({"source": source.value["source"], "selectors": source.value["selectors"]})
    member = BoundRoleMember("product:source-population", "kind:selected-source", source_subject(source.value["source"]), "original:doc", scope, b'{}', (), b'{}', member="member:source")
    frame = DeclaredNativeFrameSource.acquire(prepared, source.value, member, project="p")
    context = NativeSourceContext(frame, (), (source_slice(frame, 0, 14),), "definition", "test", "selected", version=2, preparation=PreparedNativeSources((frame,)))
    contributions = adapt_native_groups(context, family="definition", groups=(NativeRecordGroup((RoleInput("term", spans=(LiteralSpan(2, 7, "valve"),)),), "explicit term"),), item_key="native-before-worker-failure")
    assert contributions.contributions
    coverage = (CoverageDraft(family="definition", scope="#/texts/0", outcome="partial", reason="later provider failed"),)
    product = M1CandidateProduct(ObservationOutcome.PRODUCED, parse_detail={"producer_failure": "later provider failed"}, contributions=contributions.contributions, contribution_operations=contributions.operations, contribution_coordinate_texts=contributions.coordinate_texts, coverage=coverage)
    subject_context = SubjectContext("p", member.subject, member.original_source, member.analyzed_scope)
    completed = complete_m1_inspection(prepared, model, product, frame, subject_context)
    assert completed.outcome is None
    assert completed.value["inspection_outcome"] == "produced"
    assert len(completed.value["members"]) == len(contributions.contributions)
    assert completed.value["coverage"][0]["outcome"] == "partial"
    assert completed.value["diagnostics_json"] == '{"producer_failure":"later provider failed"}'
    failed = complete_m1_inspection(prepared, model, M1CandidateProduct(ObservationOutcome.FAILED, error="worker failed"), None, subject_context)
    assert failed.outcome == "failed" and failed.value is None
