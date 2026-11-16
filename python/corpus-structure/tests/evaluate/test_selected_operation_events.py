"""Independent current frame/feature/numeric expectations, without native authenticity claims."""

from math import log1p

import pytest
from pydantic import ValidationError

from corpus_structure.evaluate.operation_fitting import fit_operation_event
from corpus_structure.evaluate.selected_operation_events import (
    DdoOperationEventFrame, DdoOperationEventQuestion, IndependentEventJudgment, SelectedDefinitionEvent,
    SelectedEventRead, prepare_operation_event_frame,
)
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.declared_record_sources import DeclaredRecordSource
from corpus_structure.semantic.declared_structural_references import DeclaredProductRef, DeclaredStructuralSource
from corpus_structure.semantic.demand_results import CutSelection
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.structural_products import (
    DeclaredDefinitionComponentsProduct, DeclaredDefinitionComponentsReport,
    DeclaredStructuralInput, DeclaredStructuralInputPin, LocatedDefinitionSpan,
    StructuralPassage, declared_definition_component,
)
from semantic.test_demand_results import _page
from semantic.test_sentence_products import nominal_profile as nominal_profile
from semantic.test_sentence_products import nominal_schema as nominal_schema
from semantic.test_sentence_products import selected

PROJECT = "pure:operation-events"


def event_read(profile, name):
    page = _page()
    page.update(project_id=PROJECT, demand_id="pure-demand:"+name, read_id="pure-read:"+name,
                release_id=profile.prepared.release_id, runtime_id="pure-runtime:"+name)
    cut = CutSelection.from_native(page)
    return SelectedEventRead(
        project_id=PROJECT, demand_id=page["demand_id"], read_id=page["read_id"],
        release_id=page["release_id"], runtime_id=page["runtime_id"],
        cut_id=cut.identity, cut_canonical_json=cut.content.decode(),
    )


def event_value(profile, number, text="We call variance spread.", term="variance", content="spread", *, selected_start=0):
    """Unadmitted current domain values; no receipt, factory execution or native row is fabricated."""
    native = selected(profile, text)
    if selected_start:
        value = native.value
        value["selectors"][0]["start"] = selected_start
        native = type(native).acquire(profile.prepared, value)
    coordinate = native.value["source"]
    scope = dict(source=coordinate, selectors=native.value["selectors"])
    context = SubjectContext(PROJECT, "pure:source:"+str(number), coordinate["document"],
                             json_bytes(scope), subject_definition="original-source-view")
    source_kind = next(item.key for item in profile.model.identities if item.domain == "kind"
                      and item.owner == profile.prepared.index.definitions["DdoSelectedNativeSource"].iri)
    address = DeclaredRecordSource(
        coordinate["document"], coordinate["projection"], coordinate["section_pointer"],
        coordinate["membership"], context, "pure:source-product:"+str(number), "pure:source-member", source_kind,
    )
    pin = DeclaredStructuralSource.model_validate(address.pin())
    report_reference = DeclaredProductRef(
        product_id="pure:report:"+str(number), kind_contract="pure:component-kind",
        project_id=PROJECT, subject=context.subject, subject_definition=context.subject_definition,
        original_source=coordinate["document"], analyzed_scope_meaning=pin.analyzed_scope_meaning,
    )
    component = declared_definition_component(
        term=LocatedDefinitionSpan(passage_id="literal", start=text.index(term),
                                   end=text.index(term)+len(term), text=term),
        content=LocatedDefinitionSpan(passage_id="literal", start=text.index(content),
                                      end=text.index(content)+len(content), text=content),
        interpretation="unresolved", basis="unqualified", scope="block", alternatives=(),
        evidence=("literal",), reason="Unadmitted explicit role values for arithmetic control.",
    )
    report = DeclaredDefinitionComponentsReport(
        inputs=DeclaredStructuralInput(
            question="Which explicit term/content endpoints are under examination?", scope="block",
            inventory_id="pure:literal", policy_id="definition-scope-1", sources=(pin,),
            passages=(StructuralPassage(passage_id="literal", source_ref=pin.identity,
                                       start=0, end=len(text), text=text, scope="block"),),
            dependencies=(pin.source_product,),
        ),
        definition_components=DeclaredDefinitionComponentsProduct(components=(component,), stages=()),
        sources_input=(DeclaredStructuralInputPin(
            product_id=pin.source_product, member_id=pin.source_member, kind_contract=source_kind,
            project_id=PROJECT, subject=context.subject, subject_definition=context.subject_definition,
            original_source=coordinate["document"], analyzed_scope_meaning=pin.analyzed_scope_meaning,
            reference=pin.source,
        ),),
    )
    selector = SelectedDefinitionEvent(
        report=report_reference, component_id=component.component_id,
        use_id="pure:use:"+str(number), derivation_id="pure:episode:"+str(number),
        producer_operation="structure.definition_named_components/declared",
        producer_revision="implementation-slice:"+"a"*64,
        source=pin, origin_group="pure:origin:"+str(number),
    )
    return selector, report, native


def question(profile, values, judgments):
    cases = []
    for (selector, _, _), judgment in zip(values, judgments, strict=True):
        facets = dict.fromkeys(("attachment_head", "attachment_tail", "attachment_direction", "attachment_scope"), judgment)
        cases.append(IndependentEventJudgment.model_validate_json(canonical_bytes(dict(
            selection=selector.model_dump(mode="json"), judgment=judgment, facets=facets,
        ))))
    return DdoOperationEventQuestion(
        reference_name="pure-independent-C", author="independent literal author",
        partition="feature_fit", event="defining_text_attachment_correctness", corpus_id="pure-corpus",
        rubric_version="nce12-attachment-role-direction-scope-2", rubric="Independent head/tail/direction/scope judgments.",
        original_selection=event_read(profile, "original"), prediction_selection=event_read(profile, "prediction"),
        judgments=tuple(cases),
    )


def frame(profile, values, judgments):
    reference = values[0][0].report.model_copy(update={"product_id":"pure:C-question", "kind_contract":"pure:question-kind"})
    return prepare_operation_event_frame(
        question(profile, values, judgments), reference,
        {selector.report.product_id: report for selector, report, _ in values},
        {selector.source.source: source for selector, _, source in values},
    )


def test_current_attachment_features_are_literal_source_arithmetic_without_task_aliases(nominal_profile):
    values = [event_value(nominal_profile, 1)]
    actual = frame(nominal_profile, values, ("supported",))
    assert actual.observations[0].features == pytest.approx((log1p(8), log1p(6), 1/24, 1.0))
    assert actual.event_version == "defining-text-attachment-scope-features-2"
    assert actual.feature_names == ("term_log_length", "content_log_length", "signed_passage_separation", "declared_cue")
    assert not any(key in actual.canonical_content for key in (b"origin_task_id", b"source_view_id", b"contribution_id"))
    assert actual.fit_digest != actual.reference_digest
    assert actual.question.original_selection.cut_id != actual.question.prediction_selection.cut_id


def test_current_frame_reuses_real_numeric_kernel_and_keeps_unknown_labels_out_of_binary_counts(nominal_profile):
    values = [event_value(nominal_profile, 1), event_value(nominal_profile, 2, "We call x y.", "x", "y"),
              event_value(nominal_profile, 3), event_value(nominal_profile, 4)]
    actual = frame(nominal_profile, values, ("supported", "unsupported", "ambiguous", "unassessed"))
    result = fit_operation_event(actual)
    assert result.status == "fitted"
    assert (result.observations, result.labeled, result.positive, result.negative) == (4, 2, 1, 1)
    assert result.origin_groups == 4
    assert result.parameters is not None
    assert result.parameters.frame_digest == actual.fit_digest
    assert result.parameters.reference_digest == actual.question.digest
    public = canonical_bytes(result.parameters.model_dump(mode="json"))
    assert all(name not in public for name in (b"judgment", b"facets", b"pure:use:", b"pure:episode:"))


def test_default_event_has_absent_native_score_indicator_instead_of_invented_confidence(nominal_profile):
    values = [event_value(nominal_profile, 1)]
    original = question(nominal_profile, values, ("supported",))
    independent = DdoOperationEventQuestion.model_validate_json(canonical_bytes({
        **original.model_dump(mode="json"), "event":"defined_by_correctness",
    }))
    actual = prepare_operation_event_frame(
        independent, values[0][0].report,
        {values[0][0].report.product_id: values[0][1]}, {values[0][0].source.source: values[0][2]},
    )
    assert actual.observations[0].features == (0.0, 0.0, 1.0, 1.0)
    assert actual.event_version == "defined-by-exact-endpoints-scope-1"


def test_duplicate_exposure_stale_cut_and_changed_C_judgment_cannot_silently_change_frame(nominal_profile):
    value = event_value(nominal_profile, 1)
    original = question(nominal_profile, [value], ("supported",))
    with pytest.raises(ValidationError, match="unique exposed events"):
        DdoOperationEventQuestion.model_validate_json(canonical_bytes({
            **original.model_dump(mode="json"), "judgments":[original.judgments[0].model_dump(mode="json")]*2,
        }))
    with pytest.raises(ValidationError, match="exact native cut"):
        SelectedEventRead.model_validate_json(canonical_bytes({
            **original.prediction_selection.model_dump(mode="json"), "runtime_id":"another-runtime",
        }))
    actual = frame(nominal_profile, [value], ("supported",))
    changed = actual.model_dump(mode="json")
    changed["observations"][0]["judgment"] = "unsupported"
    with pytest.raises(ValidationError, match="C judgment"):
        type(actual).model_validate_json(canonical_bytes(changed))


def test_clipped_original_scope_is_unavailable_without_making_a_negative_label(nominal_profile):
    value = event_value(nominal_profile, 1, selected_start=9)
    actual = frame(nominal_profile, [value], ("supported",))
    assert actual.observations == ()
    assert actual.feature_unavailable[0].reason == "incomparable_endpoint_anchors"
    assert actual.feature_unavailable[0].judgment == "supported"
    result = fit_operation_event(actual)
    assert result.status == "unavailable" and result.parameters is None
    assert (result.labeled, result.positive, result.negative) == (0, 0, 0)


def test_source_order_stays_signed_and_canonical_frame_bytes_are_retained(nominal_profile):
    value = event_value(nominal_profile, 1, "spread is called variance.")
    actual = frame(nominal_profile, [value], ("supported",))
    assert actual.observations[0].features == pytest.approx((log1p(8), log1p(6), -11/26, 1.0))
    protected = DdoOperationEventFrame.capture(actual)
    assert protected.frame_canonical_json.encode() == actual.canonical_content
    assert protected.frame_digest == actual.fit_digest
    with pytest.raises(ValidationError, match="canonical owner"):
        DdoOperationEventFrame.model_validate_json(canonical_bytes({
            **protected.model_dump(mode="json"), "frame_digest":"0"*64,
        }))
