"""Actual M1 nominal schema/producer capture; no provider execution claim."""

from pathlib import Path
from types import SimpleNamespace

from corpus_structure.core.method import CoverageDraft
from corpus_structure.core.vocab import ObservationOutcome
from corpus_structure.methods.m1_source import M1CandidateProduct
from corpus_structure.semantic import prepare_release
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_member_contracts import derive_member_kinds
from corpus_structure.semantic.data_operation_model import BoundRoleMember, SubjectContext
from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
from corpus_structure.semantic.m1_products import (
    candidate_report,
    m1_operation_inputs,
    m1_operation_sources,
    m1_profile_assets,
)
from corpus_structure.semantic.source_products import FrozenNativeSource, source_subject
from corpus_structure.semantic.types import SourceArtifact, SourceBundle

ROOT = Path(__file__).resolve().parents[4]


def record_schemas():
    return SourceBundle(
        "statistics_semantic",
        (
            SourceArtifact(
                "statistics_semantic", (ROOT / "domains/statistics/semantic.yaml").read_bytes()
            ),
            SourceArtifact(
                "statistics_terminology",
                (ROOT / "domains/statistics/terminology.yaml").read_bytes(),
            ),
            SourceArtifact(
                "semantic_core",
                (
                    ROOT / "python/corpus-structure/src/corpus_structure/model/semantic/core.yaml"
                ).read_bytes(),
            ),
        ),
    )


def configuration():
    from corpus_structure.orchestrate.m1 import registry

    return registry(ROOT / "domains/statistics").overlay("extract.m1_candidates", "default")


def test_empty_m1_inspection_has_successful_typed_report_and_exact_denominator():
    prepared = prepare_release(m1_operation_inputs(record_schemas()))
    source = FrozenNativeSource.from_projection(
        prepared,
        document="original:doc",
        section_pointer="#/groups/0",
        membership="descendants",
        text="A valve opens.",
        pieces=[
            {
                "kind": "native_text",
                "item_ref": "#/texts/0",
                "source_field": "text",
                "start": 0,
                "end": 14,
            }
        ],
        items=[
            {
                "self_ref": "#/texts/0",
                "label": "text",
                "text": "A valve opens.",
                "orig": "A valve opens.",
                "prov": [],
            }
        ],
    )
    scope = json_bytes({"source": source.value["source"], "selectors": source.value["selectors"]})
    member = BoundRoleMember(
        "product:source-population",
        "kind:selected-source",
        source_subject(source.value["source"]),
        "original:doc",
        scope,
        b"{}",
        (),
        b"{}",
        member="member:source",
    )
    frame = DeclaredNativeFrameSource.acquire(prepared, source.value, member, project="p")
    product = M1CandidateProduct(
        ObservationOutcome.EMPTY,
        parse_detail={"inspected_regions": 1},
        coverage=(CoverageDraft(family="definition", scope="#/texts/0", outcome="complete"),),
        records=(),
        contributions=(),
    )
    report = candidate_report(
        prepared,
        SimpleNamespace(kinds=(), identities=()),
        product,
        frame,
        SubjectContext("p", member.subject, member.original_source, member.analyzed_scope),
    )
    assert report["inspection_outcome"] == "empty"
    assert report["members"] == ()
    assert report["coverage"] == (
        {"family": "definition", "scope": "#/texts/0", "outcome": "complete"},
    )
    assert report["diagnostics_json"] == '{"inspected_regions":1}'
    assert report["source_pin"]["source_member"] == "member:source"


def test_actual_m1_producer_captures_selection_witnesses_and_single_stored_member_families():
    bundle = m1_operation_inputs(record_schemas())
    model = compile_data_operations(
        bundle,
        python_sources=m1_operation_sources(configuration(), record_schemas=record_schemas()),
    )
    operation = model.operation("extract.m1_candidates")
    assert (
        operation.consumer_selection.entrypoint
        == "corpus_structure.methods.m1_declared.M1SourceCandidatesOperation.select_hydrated"
    )
    assert len(operation.output_witnesses) == 5
    assert {group.input_role for group in operation.output_witnesses} == {"primary", "sources"}
    output = next(role for role in operation.roles if role.direction == "output")
    assert derive_member_kinds(model, output.kind) == tuple(
        sorted(
            kind.semantic_id
            for kind in model.kinds
            if kind.name in {"DdoCandidateSourceRecord", "DdoCandidateSourceContribution"}
        )
    )


def test_m1_semantic_profile_excludes_snapshot_path_and_captures_record_schema():
    config = configuration()
    left = m1_profile_assets(config, record_schemas())
    right = m1_profile_assets(
        config.model_copy(update={"snapshot": Path("/different/physical/snapshot")}),
        record_schemas(),
    )
    assert left.content == right.content
    assert b'"schemas"' in left.content


def test_candidate_body_is_stored_once_and_keeps_required_source_record_anchors():
    import pytest
    from pydantic import ValidationError

    from corpus_structure.methods.record_assembly import (
        LiteralSpan,
        NativeRecordGroup,
        RoleInput,
        assemble_native_records,
    )
    from corpus_structure.semantic.data_operation_ports import project_product_members
    from corpus_structure.semantic.source_contexts import (
        NativeSourceContext,
        PreparedNativeSources,
        source_slice,
    )

    bundle = m1_operation_inputs(record_schemas())
    prepared = prepare_release(bundle)
    model = compile_data_operations(bundle)
    source = FrozenNativeSource.from_projection(
        prepared,
        document="original:doc",
        section_pointer="#/groups/0",
        membership="descendants",
        text="A valve opens.",
        pieces=[
            {
                "kind": "native_text",
                "item_ref": "#/texts/0",
                "source_field": "text",
                "start": 0,
                "end": 14,
            }
        ],
        items=[
            {
                "self_ref": "#/texts/0",
                "label": "text",
                "text": "A valve opens.",
                "orig": "A valve opens.",
                "prov": [],
            }
        ],
    )
    scope = json_bytes({"source": source.value["source"], "selectors": source.value["selectors"]})
    member = BoundRoleMember(
        "product:source-population",
        "kind:selected-source",
        source_subject(source.value["source"]),
        "original:doc",
        scope,
        b"{}",
        (),
        b"{}",
        member="member:source",
    )
    frame = DeclaredNativeFrameSource.acquire(prepared, source.value, member, project="p")
    context = NativeSourceContext(
        frame,
        (),
        (source_slice(frame, 0, 14),),
        "definition",
        "test",
        "selected",
        version=2,
        preparation=PreparedNativeSources((frame,)),
    )
    assembly = assemble_native_records(
        prepared,
        context,
        contract="DefinitionRecordFields",
        occurrence_roles=("term",),
        policy_version="reading-1",
        groups=(
            NativeRecordGroup(
                (RoleInput("term", spans=(LiteralSpan(2, 7, "valve"),)),), "explicit term"
            ),
        ),
    )
    records = tuple(record.model_dump(mode="python") for record in assembly.records)
    assert len(records) == 1
    product = M1CandidateProduct(ObservationOutcome.PRODUCED, records=records, contributions=())
    report = candidate_report(
        prepared,
        model,
        product,
        frame,
        SubjectContext("p", member.subject, member.original_source, member.analyzed_scope),
    )
    assert "records" not in report and "contributions" not in report
    (packet,) = report["members"]
    assert packet["member_id"] == "record:" + records[0]["record_id"]
    assert packet["body"]["candidate_type"] == "record"
    assert packet["body"]["record_id"] == records[0]["record_id"]
    kind = next(
        kind.semantic_id for kind in model.kinds if kind.name == "DdoCandidateInspectionReport"
    )
    assert len(project_product_members(model, kind, report)) == 1
    with pytest.raises(ValidationError):
        prepared.validate_json(
            "DdoCandidateSourceRecord",
            json_bytes(
                {name: value for name, value in packet["body"].items() if name != "anchors"}
            ),
        )


def test_partial_produced_inspection_preserves_real_candidates_after_later_worker_failure():
    from corpus_structure.methods.contribution_adapter import adapt_native_groups
    from corpus_structure.methods.record_assembly import LiteralSpan, NativeRecordGroup, RoleInput
    from corpus_structure.semantic.m1_products import complete_m1_inspection
    from corpus_structure.semantic.source_contexts import (
        NativeSourceContext,
        PreparedNativeSources,
        source_slice,
    )

    bundle = m1_operation_inputs(record_schemas())
    prepared = prepare_release(bundle)
    model = compile_data_operations(bundle)
    source = FrozenNativeSource.from_projection(
        prepared,
        document="original:doc",
        section_pointer="#/groups/0",
        membership="descendants",
        text="A valve opens.",
        pieces=[
            {
                "kind": "native_text",
                "item_ref": "#/texts/0",
                "source_field": "text",
                "start": 0,
                "end": 14,
            }
        ],
        items=[
            {
                "self_ref": "#/texts/0",
                "label": "text",
                "text": "A valve opens.",
                "orig": "A valve opens.",
                "prov": [],
            }
        ],
    )
    scope = json_bytes({"source": source.value["source"], "selectors": source.value["selectors"]})
    member = BoundRoleMember(
        "product:source-population",
        "kind:selected-source",
        source_subject(source.value["source"]),
        "original:doc",
        scope,
        b"{}",
        (),
        b"{}",
        member="member:source",
    )
    frame = DeclaredNativeFrameSource.acquire(prepared, source.value, member, project="p")
    context = NativeSourceContext(
        frame,
        (),
        (source_slice(frame, 0, 14),),
        "definition",
        "test",
        "selected",
        version=2,
        preparation=PreparedNativeSources((frame,)),
    )
    contributions = adapt_native_groups(
        context,
        family="definition",
        groups=(
            NativeRecordGroup(
                (RoleInput("term", spans=(LiteralSpan(2, 7, "valve"),)),), "explicit term"
            ),
        ),
        item_key="native-before-worker-failure",
    )
    assert contributions.contributions
    coverage = (
        CoverageDraft(
            family="definition",
            scope="#/texts/0",
            outcome="partial",
            reason="later provider failed",
        ),
    )
    product = M1CandidateProduct(
        ObservationOutcome.PRODUCED,
        parse_detail={"producer_failure": "later provider failed"},
        contributions=contributions.contributions,
        contribution_operations=contributions.operations,
        contribution_coordinate_texts=contributions.coordinate_texts,
        coverage=coverage,
    )
    subject_context = SubjectContext(
        "p", member.subject, member.original_source, member.analyzed_scope
    )
    completed = complete_m1_inspection(prepared, model, product, frame, subject_context)
    assert completed.outcome is None
    assert completed.value["inspection_outcome"] == "produced"
    assert len(completed.value["members"]) == len(contributions.contributions)
    assert completed.value["coverage"][0]["outcome"] == "partial"
    assert completed.value["diagnostics_json"] == '{"producer_failure":"later provider failed"}'
    failed = complete_m1_inspection(
        prepared,
        model,
        M1CandidateProduct(ObservationOutcome.FAILED, error="worker failed"),
        None,
        subject_context,
    )
    assert failed.outcome == "failed" and failed.value is None


def test_m1_shared_provider_question_preserves_claim_membership_and_typed_refusal():
    """Controlled lane response checks custody only; this is not provider evidence."""
    from dataclasses import asdict

    import pytest

    from corpus_structure.methods.characterization_resources import ProviderReply
    from corpus_structure.methods.gliner import GlinerInput, GlinerPack
    from corpus_structure.methods.gliner_worker import GlinerAdmission
    from corpus_structure.methods.m1_source import M1GlinerRequest
    from corpus_structure.methods.native_host import NativeRetirementUncertain, payload_digest
    from corpus_structure.semantic.m1_products import plan_m1_gliner

    config = configuration().model_copy(update={"native_execution_profile": {"controlled": "custody-only"}})
    inputs = (GlinerInput("context:one", "a" * 64, "A valve opens."),)
    question = M1GlinerRequest(config.profile(), GlinerPack("controlled-pack", '{}'), inputs, 0.5, config.native_execution_profile)
    calls = []
    reservation = object()
    def work(request, *, reservation):
        calls.append((request, reservation))
        return "shared-provider-work"
    owner = SimpleNamespace(claim=SimpleNamespace(request_id="request:one", generation=2, task_id=3, attempt=4),
        reservation=reservation, providers=SimpleNamespace(work=work))
    receipts = []
    plan = plan_m1_gliner(question, config, execution_owner=owner, check_active=lambda: None, ordinal=2, receipts=receipts)
    assert next(plan) == ("shared-provider-work",)
    (request, credit), = calls
    assert credit is reservation and request.inputs is inputs and request.pack is question.pack
    logical, = request.logical_members
    assert (logical.request_id, logical.generation, logical.task_id, logical.attempt, logical.member) == ("request:one", 2, 3, 4, "m1-question:2")
    assert logical.input_digest == payload_digest([asdict(inputs[0])])
    receipt = object()
    refused = ProviderReply(request.correlation, admissions=(GlinerAdmission(0, "context:one", "a" * 64, False, "oversized input"),), execution_receipt=receipt)
    with pytest.raises(StopIteration) as stopped:
        plan.send((refused,))
    assert stopped.value.value.failure == "refused" and stopped.value.value.message == "oversized input"
    assert receipts == [receipt]
    uncertain = plan_m1_gliner(question, config, execution_owner=owner, check_active=lambda: None, ordinal=3, receipts=[])
    next(uncertain)
    with pytest.raises(NativeRetirementUncertain):
        uncertain.send((ProviderReply(calls[-1][0].correlation, retirement_uncertain=True, error_message="live native work"),))


def test_m1_scoped_source_and_direct_context_cannot_inspect_unselected_original_text():
    import pytest
    from corpus_structure.methods.source_preparation import prepare_source
    from corpus_structure.semantic.m1_products import NativeCandidateData
    from corpus_structure.semantic.source_contexts import ContextRefused, NativeSourceContext, PreparedNativeSources, source_slice
    from corpus_structure.semantic.declared_record_sources import DeclaredSourceSlice

    prepared = prepare_release(m1_operation_inputs(record_schemas()))
    base = FrozenNativeSource.from_projection(prepared, document="original:scope", section_pointer="#/body", membership="descendants",
        text="alpha\nbeta", pieces=[
            dict(kind="native_text", start=0, end=5, item_ref="#/texts/0", source_field="text"),
            dict(kind="synthetic_separator", start=5, end=6),
            dict(kind="native_text", start=6, end=10, item_ref="#/texts/1", source_field="text")],
        items=[dict(self_ref="#/texts/0", label="text", text="alpha", orig="alpha"),
            dict(self_ref="#/texts/1", label="text", text="beta", orig="beta")])

    def frame(selectors):
        value = {**base.value, "selectors": selectors}
        source = FrozenNativeSource.acquire(prepared, value)
        scope = json_bytes(dict(source=value["source"], selectors=selectors))
        member = BoundRoleMember("product:scope", "kind:source", source_subject(value["source"]), "original:scope", scope, b'{}', (), b'{}', member="selected:scope")
        return DeclaredNativeFrameSource.acquire(prepared, source.value, member, project="p")

    selected = frame([dict(projection=base.value["source"]["projection"], native_pointer="#/texts/0")])
    data = NativeCandidateData.from_frame(selected)
    assert [(piece["start"], piece["end"]) for piece in data.pieces] == [(0, 5)]
    original = prepare_source(data, source_frame=selected, persisted_annotations=())
    assert original.selections
    for selection in original.selections:
        context = selection.context(selected, preparation=original.preparation, policy=configuration().policy, max_chars=2048, max_pieces=64)
        assert context.text == "alpha"
    with pytest.raises(ContextRefused, match="selected native source scope"):
        source_slice(selected, 0, 10)
    with pytest.raises(ContextRefused, match="selected native source scope"):
        NativeSourceContext(selected, (), (DeclaredSourceSlice(selected.source_key, 0, 10),), "definition", "bounded", "selected", version=2, preparation=PreparedNativeSources((selected,)))
    clipped = frame([dict(projection=base.value["source"]["projection"], start=1, end=4)])
    partial = prepare_source(NativeCandidateData.from_frame(clipped), source_frame=clipped, persisted_annotations=())
    assert partial.selections == ()
    assert partial.regions and all(region.outcome == "unsupported" for region in partial.regions)


def test_related_m1_context_consumes_only_related_members_own_selected_span():
    from corpus_structure.methods.source_preparation import ContextSelection, _widen_contexts
    from corpus_structure.semantic.declared_contexts import DeclaredContextPopulation
    from corpus_structure.semantic.m1_products import NativeCandidateData
    from corpus_structure.semantic.source_contexts import PreparedNativeSources

    prepared = prepare_release(m1_operation_inputs(record_schemas()))
    primary = FrozenNativeSource.from_projection(prepared, document="original:related", section_pointer="#/groups/0", membership="direct", text="A",
        pieces=[dict(kind="native_text", start=0, end=1, item_ref="#/texts/0", source_field="text")],
        items=[dict(self_ref="#/texts/0", label="text", text="A", orig="A", captions=[{"$ref": "#/texts/1"}])])
    related = FrozenNativeSource.from_projection(prepared, document="original:related", section_pointer="#/groups/1", membership="direct", text="Caption\nSECRET",
        pieces=[dict(kind="native_text", start=0, end=7, item_ref="#/texts/1", source_field="text"), dict(kind="synthetic_separator", start=7, end=8),
            dict(kind="native_text", start=8, end=14, item_ref="#/texts/2", source_field="text")],
        items=[dict(self_ref="#/texts/1", label="caption", text="Caption", orig="Caption"),
            dict(self_ref="#/texts/2", label="text", text="SECRET", orig="SECRET")])
    value = related.value
    value["selectors"] = [dict(projection=value["source"]["projection"], native_pointer="#/texts/1")]
    related = FrozenNativeSource.acquire(prepared, value)
    def frame(source, ordinal):
        value = source.value
        member = BoundRoleMember("product:related", "kind:source", source_subject(value["source"]), "original:related",
            json_bytes(dict(source=value["source"], selectors=value["selectors"])), b'{}', (), b'{}', member="source:" + str(ordinal))
        return DeclaredNativeFrameSource.acquire(prepared, value, member, project="p")
    primary, related = frame(primary, 0), frame(related, 1)
    population = DeclaredContextPopulation((primary, related), b'{"identity":"closed:related","complete":true}')
    widened, retained = _widen_contexts(NativeCandidateData.from_frame(primary), primary,
        [ContextSelection("#/texts/0", 0, 1, ("definition",), "bounded source")], reader=None, read_budget=None,
        context_population=population, max_chars=100, max_pieces=16, check_active=lambda: None)
    assert [entry.source for entry in retained] == [related]
    context = widened[0].context(primary, max_chars=100, max_pieces=16, related=retained, preparation=PreparedNativeSources((primary, related)))
    assert context.text == "A\nCaption" and "SECRET" not in context.text
    related_intervals = [interval for interval in context.intervals if getattr(interval, "source", None) == related.pin]
    assert [(interval.source_start, interval.source_end) for interval in related_intervals] == [(0, 7)]


def test_m1_coalesced_success_preserves_report_and_rejects_foreign_source_reply():
    """The lane's successful scatter omits redundant per-input admission rows."""
    from dataclasses import replace
    import pytest
    from corpus_structure.methods.characterization_resources import ProviderReply
    from corpus_structure.methods.gliner import GlinerInput, GlinerPack, GlinerPreparation, GlinerReport
    from corpus_structure.methods.m1_source import M1GlinerRequest
    from corpus_structure.semantic.m1_products import plan_m1_gliner

    config = configuration().model_copy(update={"native_execution_profile": {"controlled": "custody-only"}})
    question = M1GlinerRequest(config.profile(), GlinerPack("controlled-pack", '{}'),
        (GlinerInput("context:scatter", "a" * 64, "A valve opens."),), .5, config.native_execution_profile)
    requests = []
    def work(request, *, reservation):
        requests.append(request)
        return "coalesced-work"
    owner = SimpleNamespace(claim=SimpleNamespace(request_id="request:scatter", generation=1, task_id=2, attempt=1),
        reservation=object(), providers=SimpleNamespace(work=work))
    report = GlinerReport("context:scatter", "a" * 64, "controlled", "controlled", "controlled",
        GlinerPreparation("A valve opens.", "", 4, 4, 14), '{"native_score":0.625}', '{}', 0., False)
    for foreign in (False, True):
        plan = plan_m1_gliner(question, config, execution_owner=owner, check_active=lambda: None, ordinal=1, receipts=[])
        assert next(plan) == ("coalesced-work",)
        reply = ProviderReply(requests[-1].correlation, reports=(replace(report, context_digest="b" * 64) if foreign else report,))
        if foreign:
            with pytest.raises(ValueError, match="original inference population"):
                plan.send((reply,))
        else:
            with pytest.raises(StopIteration) as stopped:
                plan.send((reply,))
            assert stopped.value.value.reports == (report,)
            assert stopped.value.value.reports[0].raw_json == '{"native_score":0.625}'
