"""Captured nominal private facets; controlled selection grants no native publication."""

from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from corpus_structure.semantic import prepare_release
from corpus_structure.semantic.candidate_contribution_facets import (
    CANDIDATE_NAMESPACE,
    FINITE_KIND,
    READING_KIND,
    CandidateFacetKinds,
    candidate_facets,
)
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
from corpus_structure.semantic.finite_interpretation_products import finite_interpretation_inputs
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.original_documents import original_document_subject
from corpus_structure.semantic.reading_resolution_products import reading_resolution_inputs
from corpus_structure.semantic.refusals import InvalidContinuation
from corpus_structure.semantic.rich_knowledge_contracts import DdoRichSelectedMember
from corpus_structure.semantic.rich_queries import RichQueryRefused
from corpus_structure.semantic.types import SourceArtifact, SourceBundle
from corpus_structure.serve import contribution_facets as serving


@pytest.fixture(scope="module")
def source():
    root = Path(__file__).parents[2] / "src/corpus_structure/model/semantic"
    bundle = finite_interpretation_inputs(
        reading_resolution_inputs(
            SourceBundle("core", (SourceArtifact("core", (root / "core.yaml").read_bytes()),))
        )
    )
    return SimpleNamespace(model=compile_data_operations(bundle), prepared=prepare_release(bundle))


def analyzed_scope():
    return dict(
        source=dict(
            document="document:original",
            document_subject=original_document_subject("document:original"),
            projection="a" * 64,
            section_pointer="#/texts/0",
            membership="direct",
        ),
        selectors=[dict(projection="a" * 64)],
    )


def pin():
    return dict(
        format="declared-native-source-v1",
        source='["source:original","source-member"]',
        source_product="source:original",
        source_member="source-member",
        kind_contract="kind:source",
        document="document:original",
        projection_digest="a" * 64,
        section_pointer="#/texts/0",
        membership="direct",
        project_id="project",
        subject="source-subject",
        subject_definition="original-source-view",
        original_source="document:original",
        analyzed_scope_meaning=canonical_bytes(semantic_value(analyzed_scope())).decode(),
    )


def contract(source, nominal):
    model = source.model
    return next(
        item.key for item in model.identities if item.domain == "kind" and item.owner == nominal
    )


def selected(model, body, nominal, *, member_id=None):
    return SimpleNamespace(
        body=body,
        nominal=nominal,
        use_id="selected-use",
        output={"role": "result", "position": 0},
        context=SubjectContext(
            "project",
            "source-subject",
            "document:original",
            json_bytes(analyzed_scope()),
            subject_definition="original-source-view",
        ),
        reference=DdoRichSelectedMember(
            product_id="selected-product",
            member_id=member_id,
            kind_contract=contract(model, nominal),
            support_references=(
                ComputationalSupportReference(
                    derivation_id="original-episode", admission_use_id="selected-use"
                ),
            ),
        ),
    )


def report(model):
    context = dict(
        subject="source-subject",
        subject_definition="original-source-view",
        original_source="document:original",
        analyzed_scope=analyzed_scope(),
    )
    anchor = dict(
        anchor_id="anchor:actual",
        pin=pin(),
        space="native",
        pointer="#/texts/0",
        precision="exact",
        start=4,
        end=7,
    )
    body = dict(
        candidate_type="record",
        record_id="one-occurrence",
        interpretation_id="reading:A",
        contract="ActualMeasurementFields",
        family="measurement",
        occurrence_recipe="actual-source-policy",
        pin=pin(),
        occurrence_anchors=["anchor:actual"],
        standing="candidate",
        policy_version="actual-v1",
        fields=[
            dict(
                role="value",
                kind="literal",
                state="present",
                meaning_changing=True,
                evidence_status="available",
                value=dict(kind="decimal", lexical="1.20e-3"),
                alternatives=[
                    dict(
                        alternative_id="other-value",
                        value=dict(kind="decimal", lexical="1.21e-3"),
                        reason="retained source alternative",
                    )
                ],
            )
        ],
        anchors=[anchor],
        computation_dependencies=["actual-observation"],
    )
    other = deepcopy(body)
    other["interpretation_id"] = "reading:B"
    other["fields"][0]["state"] = "unresolved"
    contribution = dict(
        candidate_type="contribution",
        contribution_id="relation:actual",
        contract="ActualRelation",
        kind="relation",
        semantic_type="actual-relation",
        operation_key="source-operation",
        item_key="source-item",
        pin=pin(),
        anchors=[anchor],
        disposition="retained",
        standing="retained_private",
        score_state="missing",
    )
    return dict(
        source_pin=pin(),
        inspection_outcome="produced",
        standing="private_uncalibrated_candidates",
        members=[
            dict(
                member_id=identifier,
                kind_contract=contract(model, CANDIDATE_NAMESPACE + name),
                context=context,
                body=value,
            )
            for identifier, name, value in (
                ("member:A", "DdoCandidateSourceRecord", body),
                ("member:B", "DdoCandidateSourceRecord", other),
                ("member:relation", "DdoCandidateSourceContribution", contribution),
            )
        ],
        operations=[],
        coordinate_texts=[],
        coverage=[
            dict(
                family="measurement",
                scope="#/texts/0",
                outcome="limited",
                reason="selected span only",
            )
        ],
        diagnostics_json='{"provider_score":0.25}',
    )


def rows(source, value, **kwargs):
    return [
        item.value
        for item in candidate_facets(
            value,
            CandidateFacetKinds.from_model(source.model, source.prepared),
            interpretation=True,
            assessment=True,
            **kwargs,
        )
    ]


def test_candidate_facets_keep_exact_alternatives_source_member_support_and_private_standing(
    source,
):
    body = report(source)
    value = selected(source, body, CANDIDATE_NAMESPACE + "DdoPredicateInspectionReport")
    actual = rows(source, value)
    interpreted = next(
        row["row"]
        for row in actual
        if row["population"] == "interpretation"
        and row["row"]["reference"]["member_id"] == "member:A"
    )
    assert interpreted["meaning"]["fields"][0]["value"] == {"kind": "decimal", "lexical": "1.20e-3"}
    assert interpreted["meaning"]["fields"][0]["alternatives"][0]["value"]["lexical"] == "1.21e-3"
    assert interpreted["source_pin"]["source_member"] == "source-member"
    assert interpreted["reference"]["product_id"] == "selected-product"
    assert interpreted["reference"]["support_references"][0]["derivation_id"] == "original-episode"
    assert (
        interpreted["standing"] == "candidate"
        and interpreted["scientific_truth"] == "not-established"
    )
    coverage = next(row["row"] for row in actual if row["population"] == "coverage")
    assert coverage["reference"]["member_id"] is None
    assert coverage["coverage"]["outcome"] == "limited"
    assert coverage["original_source_completeness"] == "unknown"
    assert all(
        row["row"]["availability"] == "unknown"
        for row in actual
        if row["population"] == "assessment"
    )
    single = rows(source, value, member_id="member:B")
    assert len(single) == 3
    assert all(row["row"]["reference"]["member_id"] == "member:B" for row in single)
    assert single[1]["row"]["meaning"]["fields"][0]["state"] == "unresolved"


def test_empty_candidate_inspection_retains_coverage_without_inventing_members(source):
    body = report(source)
    body.update(members=[], inspection_outcome="empty")
    actual = rows(
        source, selected(source, body, CANDIDATE_NAMESPACE + "DdoD1SourceCandidatesReport")
    )
    assert all(row["row"]["reference"]["member_id"] is None for row in actual)
    whole = next(row["row"] for row in actual if row["population"] == "interpretation")
    assert whole["meaning"]["inspection_outcome"] == "empty"
    assert whole["meaning"]["coverage"][0]["scope"] == "#/texts/0"


def test_missing_private_standing_is_not_synthesized_when_actual_owner_requires_it(source):
    body = report(source)
    body.pop("standing")
    with pytest.raises(ValueError, match="standing"):
        rows(source, selected(source, body, CANDIDATE_NAMESPACE + "DdoCandidateInspectionReport"))


def test_resolved_reading_events_join_exact_reading_and_keep_unavailable_and_orphan_events(source):
    body = report(source)
    events = [
        dict(
            record_id="one-occurrence",
            interpretation_id=key,
            outcome=outcome,
            final_event_score=score,
            event_procedure="actual-captured-event",
        )
        for key, outcome, score in (
            ("reading:A", "completed", -2.5),
            ("reading:B", "not_run", None),
            ("outside-selected-members", "limited", None),
        )
    ]
    body.update(reading_policy_digest="actual-policy-digest", reading_events=source_value(events))
    actual = rows(source, selected(source, body, READING_KIND))
    assessments = {
        row["row"]["reference"]["member_id"]: row["row"]
        for row in actual
        if row["population"] == "assessment"
    }
    assert assessments["member:A"]["reading_events"] == [events[0]]
    assert assessments["member:B"]["reading_events"] == [events[1]]
    assert assessments["member:B"]["availability"] == "observed"
    assert assessments["member:relation"]["availability"] == "unknown"
    assert assessments[None]["reading_events"] == events
    assert all(item["public_admission"] == "not-established" for item in assessments.values())


@pytest.mark.parametrize(
    "mode,outcome", [("records", "not_run"), ("local", "resource_limit"), ("table", "completed")]
)
def test_finite_reports_preserve_captured_mode_baseline_outcome_and_whole_reference(
    source, mode, outcome
):
    reports = [
        dict(
            outcome=outcome,
            interpretation_ids=["reading:A", "reading:B"],
            probability_standing="not_computed",
            baseline="retained-candidates",
            reason="actual captured reason",
            computation_dependencies=["actual-policy"],
        )
    ]
    body = dict(
        version="finite-interpretation-1",
        source_pin=pin(),
        mode=mode,
        standing="private_candidate_relative",
        reports=source_value(reports),
    )
    actual = rows(source, selected(source, body, FINITE_KIND))
    interpretation = next(
        row["row"]
        for row in actual
        if row["population"] == "interpretation" and "report_position" in row["row"]
    )
    assert interpretation["meaning"] == reports[0]
    assert interpretation["mode"] == mode and interpretation["report_position"] == 0
    assert all(row["row"]["reference"]["member_id"] is None for row in actual)
    assert interpretation["standing"] == "private_candidate_relative"
    assert interpretation["public_admission"] == "not-established"


def test_direct_selected_member_uses_existing_address_and_cannot_claim_parent_reading_events(
    source,
):
    packet = report(source)["members"][0]
    value = selected(
        source,
        packet["body"],
        CANDIDATE_NAMESPACE + "DdoCandidateSourceRecord",
        member_id="member:A",
    )
    actual = rows(source, value)
    assert len(actual) == 3
    assert all(row["row"]["reference"]["member_id"] == "member:A" for row in actual)
    assert actual[-1]["row"]["availability"] == "unknown"


def test_finite_empty_population_and_wrong_standing_remain_distinct(source):
    body = dict(
        version="finite-interpretation-1",
        source_pin=pin(),
        mode="records",
        standing="private_candidate_relative",
        reports=source_value([]),
    )
    actual = rows(source, selected(source, body, FINITE_KIND))
    assert [row["population"] for row in actual] == ["contribution", "interpretation"]
    assert actual[1]["row"]["report_count"] == 0
    assert actual[1]["row"]["meaning"]["source_pin"]["source_member"] == "source-member"
    body["standing"] = "accepted"
    with pytest.raises(ValueError):
        rows(source, selected(source, body, FINITE_KIND))


@pytest.mark.parametrize(
    "change",
    [
        "wrong-root-contract",
        "wrong-member-contract",
        "wrong-standing",
        "wrong-member-standing",
        "duplicate-member",
    ],
)
def test_candidate_refuses_nominal_substitution_and_private_standing_upgrade(source, change):
    body = report(source)
    value = selected(source, body, CANDIDATE_NAMESPACE + "DdoCandidateInspectionReport")
    if change == "wrong-root-contract":
        value.reference = value.reference.model_copy(
            update={"kind_contract": contract(source, FINITE_KIND)}
        )
    elif change == "wrong-member-contract":
        body["members"][0]["kind_contract"] = contract(
            source, CANDIDATE_NAMESPACE + "DdoCandidateSourceContribution"
        )
    elif change == "wrong-standing":
        body["standing"] = "accepted"
    elif change == "wrong-member-standing":
        body["members"][0]["body"]["standing"] = "accepted"
    else:
        body["members"].append(deepcopy(body["members"][0]))
    with pytest.raises(ValueError):
        rows(source, value)


def test_candidate_complete_member_and_nested_bounds_refuse_without_forged_partial_rows(source):
    value = selected(source, report(source), CANDIDATE_NAMESPACE + "DdoCandidateInspectionReport")
    with pytest.raises(RichQueryRefused, match="actual member bound"):
        rows(source, value, max_members=1)
    with pytest.raises(RichQueryRefused, match="complete nested-member bound"):
        rows(source, value, max_nested_members=1)


def test_current_delivery_dispatches_real_candidates_and_pins_pagination_and_byte_bounds(
    source, monkeypatch
):
    body = report(source)
    # A real member spelling must not collide with the whole report's local
    # display position and cause a continuation to replay earlier rows.
    body["members"][0]["member_id"] = "whole"
    value = selected(source, body, CANDIDATE_NAMESPACE + "DdoCandidateInspectionReport")
    cut = SimpleNamespace(
        record=dict(read_id="native-read", project_id="project"), identity="actual-cut"
    )
    scope = SimpleNamespace(
        model=source.model,
        prepared=source.prepared,
        cut=cut,
        index=SimpleNamespace(retained_records=7),
        products=lambda **kwargs: iter((value,)),
    )

    @contextmanager
    def acquire(connection, request):
        if request.read_id is not None:
            assert (request.read_id, request.expected_cut) == ("native-read", "actual-cut")
        yield scope

    monkeypatch.setattr(serving, "selected_contribution_scope", acquire)
    request = serving.ContributionFacetsRequest(
        demand_id="actual-demand", project_id="project", include_operations=False, limit=1
    )
    pages = []
    cursor = None
    for _ in range(32):
        page = serving.serve_contribution_facets(
            None, request.model_copy(update={"cursor": cursor})
        )
        pages.extend(page["items"])
        cursor = page["cursor"]
        if cursor is None:
            break
    else:
        pytest.fail("candidate continuation did not exhaust its actual finite row population")
    assert pages == [item.value for item in serving.contribution_rows(scope, request)]
    assert any(item["row"]["reference"]["member_id"] == "member:B" for item in pages)
    first = serving.serve_contribution_facets(None, request)
    with pytest.raises(InvalidContinuation):
        serving.serve_contribution_facets(
            None, request.model_copy(update={"cursor": first["cursor"], "member_id": "member:B"})
        )
    with pytest.raises(RichQueryRefused, match="max_bytes"):
        serving.serve_contribution_facets(None, request.model_copy(update={"max_bytes": 1024}))


@pytest.mark.parametrize("question", ["qualification_scope", "relation_interpretation"])
def test_current_finite_facets_preserve_exact_focus_raw_scores_and_negative_observation(source, question):
    """These are controlled captured reports, not inferred accepted relations."""
    focus = dict(product_id="actual-selected-primary", member_id="predicate", kind_contract="kind:predicate")
    alternative = dict(product_id="actual-selected-primary", member_id="qualifier", kind_contract="kind:qualifier")
    scope = dict(source_pin=pin(), selectors=[dict(native_pointer="#/texts/0", start=4, end=7)])
    native = dict(scores={"no_match": 0.1, "a": 0.8, "b": 0.1})
    binary = dict(direction="negative", positive_probability=0.4,
        positive_criterion="Explicitly presented as a reason.", negative_criterion="No reason is presented.")
    captured = dict(question=question, assessed_scope=scope, focus=focus,
        candidates=[dict(key="a", reference=alternative), dict(key="b", reference=focus)],
        selected_keys=["a"], native_answer=native, binary_observation=binary,
        state="observed_negative")
    body = dict(version="finite-interpretation-1", source_pin=pin(), mode="local",
        standing="private_candidate_relative", reports=source_value([captured]))
    actual = rows(source, selected(source, body, FINITE_KIND))
    interpreted = next(item["row"] for item in actual
        if item["population"] == "interpretation" and "report_position" in item["row"])
    assert interpreted["meaning"] == captured
    assert interpreted["meaning"]["focus"]["member_id"] == "predicate"
    assert [value["key"] for value in interpreted["meaning"]["candidates"]] == ["a", "b"]
    assert interpreted["meaning"]["native_answer"] == native
    assert interpreted["meaning"]["binary_observation"] == binary
    assert interpreted["reference"]["product_id"] == "selected-product"
    assert interpreted["reference"]["member_id"] is None
    assert interpreted["standing"] == "private_candidate_relative"
    assert interpreted["public_admission"] == "not-established"
