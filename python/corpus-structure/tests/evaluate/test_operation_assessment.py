"""Independent operation expectations challenge local scoring, without model calls."""

import json
from dataclasses import asdict, replace

import pytest

from corpus_structure.evaluate.operation_assessment import (
    PROTOCOL,
    OperationCase,
    OperationEvaluationFrame,
    compare_assessments,
    decode_authored,
    decode_frame,
    encode_frame,
    score_cases,
)
from corpus_structure.evaluate.semantic import ReferenceError


@pytest.fixture
def frame():
    return OperationEvaluationFrame(
        unit="source:chapter5",
        release_id="release-1",
        guideline_version="source-only-1",
        rubric_version="local-1",
        context_policy="selected-source-1",
        operation_question="table-fields",
        operation_version="1",
        domain="scientific-source",
        direction="source_first",
        pin={"source_view_id": 23},
        anchor_ids=("cell-1", "cell-2", "term-1"),
    )


def case(identity="case-1", facet="value", anchors=("cell-1",), **kwargs):
    return OperationCase(
        case_id=identity,
        facet=facet,
        anchor_ids=anchors,
        inspected_scope="table-1/body-cell-1",
        source_state="stated",
        judgment="supported",
        alternatives=({"value": "12"},),
        explanation="Independently transcribed body cell is 12.",
        assessor_provenance={"actor": "independent-source-author", "assistance": "none"},
        **kwargs,
    )


def prediction(identity="p1", anchors=("cell-1",), **kwargs):
    return dict(
        contribution_id=identity,
        kind="proposal",
        semantic_type="table.value",
        anchors=[{"anchor_id": anchor} for anchor in anchors],
        value="12",
        **kwargs,
    )


def test_value_location_and_role_are_independent(frame):
    value = case()
    role = replace(
        value, case_id="role-1", facet="role", alternatives=({"semantic_type": "table.header"},)
    )
    located = replace(
        value,
        case_id="location-1",
        facet="location",
        contribution_kind="occurrence",
        alternatives=({"semantic_type": "source_occurrence"},),
    )
    location = dict(prediction("o1"), kind="occurrence", semantic_type="source_occurrence")
    result = score_cases(frame, (value, role, located), (prediction(), location))
    assert result["facets"]["value"]["supported"] == 1
    assert result["facets"]["location"]["supported"] == 1
    assert result["facets"]["role"]["unsupported"] == 1
    assert result["cases"][-1]["error_category"] == "wrong_structure"
    assert "accuracy" not in result and result["quality_claim"] == "not_established"


def test_retrieval_membership_and_witnessed_selection_grade_separately(frame):
    available = replace(
        case("candidate", facet="availability"),
        contribution_kind="contextual_candidate_list",
        alternatives=({"retrieval_target_id": "target-b"},),
    )
    selected = replace(
        case("edge", facet="selection"),
        contribution_kind="contextual_relationship_decision",
        alternatives=(
            {
                "retrieval_selected_edge": {
                    "member_target_ids": ["target-b"],
                    "relation": "denotes",
                }
            },
        ),
    )
    candidates = dict(
        prediction("list-1"),
        kind=available.contribution_kind,
        retrieval_candidates=[{"target_id": "target-a"}, {"target_id": "target-b"}],
    )
    decision = dict(
        prediction("decision-1"),
        kind=selected.contribution_kind,
        retrieval_selected_edges=[{"member_target_ids": ["target-b"], "relation": "denotes"}],
    )
    supported = score_cases(frame, (available, selected), (candidates, decision))
    assert [row["judgment"] for row in supported["cases"]] == ["supported", "supported"]
    wrong_relation = dict(
        decision,
        retrieval_selected_edges=[{"member_target_ids": ["target-b"], "relation": "compares-with"}],
    )
    unsupported = score_cases(frame, (available, selected), (candidates, wrong_relation))
    assert [row["judgment"] for row in unsupported["cases"]] == ["supported", "unsupported"]


@pytest.mark.parametrize(
    "facet,expected,actual",
    [
        ("header", {"header": "speed"}, {"header": "distance"}),
        ("unit", {"unit": "m/s"}, {"unit": "m"}),
        ("negation", {"negated": True}, {"negated": False}),
        ("condition_extent", {"members": ["a", "b"]}, {"members": ["a"]}),
        ("version", {"version": "v2"}, {"version": "v1"}),
        ("inventory_target", {"target_state": "absent"}, {"target_state": "present"}),
        ("candidate_survival", {"retrieved": True}, {"retrieved": False}),
    ],
)
def test_structural_questions_do_not_change_value_truth(frame, facet, expected, actual):
    value = case()
    extra = replace(value, case_id="structural", facet=facet, alternatives=(expected,))
    result = score_cases(frame, (value, extra), (prediction(**actual),))
    assert result["facets"]["value"]["supported"] == 1
    assert result["facets"][facet]["unsupported"] == 1


def test_unstated_and_uninspected_are_not_pooled(frame):
    unstated = replace(
        case(), case_id="note-unstated", facet="note", source_state="unstated", alternatives=()
    )
    uninspected = replace(
        unstated, case_id="note-uninspected", source_state="uninspected", judgment="unassessed"
    )
    result = score_cases(frame, (unstated, uninspected), ())
    assert result["facets"]["note"] == {
        "supported": 0,
        "unsupported": 1,
        "ambiguous": 0,
        "unassessed": 1,
    }
    assert result["cases"][0]["error_category"] == "uninspected"
    with pytest.raises(ReferenceError, match="uninspected"):
        replace(unstated, source_state="uninspected")


def test_zero_prediction_preserves_real_missing_source_occurrence_without_id(frame):
    result = score_cases(frame, (case(),), ())
    assert result["prediction_count"] == 0
    assert result["cases"][0]["contribution_id"] is None
    assert result["cases"][0]["error_category"] == "missing_output"


def test_one_output_cannot_satisfy_two_reference_occurrences_per_facet(frame):
    result = score_cases(frame, (case("a"), case("b")), (prediction(),))
    assert result["facets"]["value"]["supported"] == 1
    assert result["cases"][1]["error_category"] == "duplicate_occurrence"


def test_assignment_does_not_greedily_consume_the_only_permissible_match(frame):
    flexible = replace(
        case("a"),
        alternatives=({"value": "12"}, {"value": "13"}),
        permissible_anchor_sets=(("cell-2",),),
    )
    exact = case("b")
    twelve = prediction()
    thirteen = dict(prediction("p2", anchors=("cell-2",)), value="13")
    result = score_cases(frame, (flexible, exact), (twelve, thirteen))
    assert [item["contribution_id"] for item in result["cases"]] == ["p2", "p1"]
    assert result == score_cases(frame, (exact, flexible), (thirteen, twelve))


def test_repeated_windows_do_not_multiply_one_physical_occurrence(frame):
    result = score_cases(
        frame, (case("a"), case("b")), (prediction("window-1"), prediction("window-2"))
    )
    assert result["facets"]["value"]["supported"] == 1
    assert result["facets"]["value"]["unsupported"] == 1


def test_reused_task_sidecars_do_not_change_contribution_identity(frame):
    result = score_cases(
        frame,
        (case(),),
        (
            prediction(
                selected_task_id=1,
                origin_task_id=10,
                task_status="done",
                source_view_id=23,
                task_id=10,
                position=0,
            ),
            prediction(
                selected_task_id=2,
                origin_task_id=10,
                task_status="reused",
                source_view_id=23,
                task_id=10,
                position=0,
            ),
            prediction(
                selected_task_id=3,
                origin_task_id=11,
                task_status="done",
                source_view_id=23,
                task_id=11,
                position=2,
            ),
        ),
    )
    assert result["prediction_count"] == 1
    assert result["prediction_count_grain"] == "unique_semantic_contribution_product"
    assert result["producer_observation_count"] == 2
    assert result["facets"]["value"]["supported"] == 1


def test_permissible_alternatives_stay_ambiguous(frame):
    ambiguous = replace(
        case(),
        judgment="ambiguous",
        source_state="unresolved",
        alternatives=({"value": "12"}, {"value": "13"}),
    )
    result = score_cases(frame, (ambiguous,), (prediction(),))
    assert result["cases"][0]["judgment"] == "ambiguous"
    assert result["cases"][0]["error_category"] == "permissible_alternatives"


def test_source_and_output_frames_keep_their_populations_separate(frame):
    with pytest.raises(ReferenceError, match="source-first"):
        replace(frame, contribution_ids=("p1",))
    output = replace(frame, direction="output_first", contribution_ids=("p1",))
    judged = replace(case(), contribution_id="p1")
    assert score_cases(output, (judged,), (prediction(), prediction("p2")))["prediction_count"] == 1
    with pytest.raises(ReferenceError, match="absent"):
        score_cases(output, (judged,), ())


def payload(frame, cases):
    return dict(
        protocol=PROTOCOL,
        release_id=frame.release_id,
        unit_ref=frame.unit,
        guideline=frame.guideline_version,
        rubric_version=frame.rubric_version,
        context_policy=frame.context_policy,
        operation_question=frame.operation_question,
        operation_version=frame.operation_version,
        domain=frame.domain,
        direction=frame.direction,
        reason="Independent source pass",
        cases=[asdict(value) for value in cases],
    )


def test_protocol_rejects_source_release_mismatch_and_fabricated_output(frame):
    value = payload(frame, (case(),))
    assert decode_authored(json.dumps(value).encode(), frame)["cases"][0] == case()
    value["release_id"] = "different-source-release"
    with pytest.raises(ReferenceError, match="invalid operation"):
        decode_authored(json.dumps(value).encode(), frame)
    value = payload(frame, (replace(case(), contribution_id="fabricated"),))
    with pytest.raises(ReferenceError):
        decode_authored(json.dumps(value).encode(), frame)
    assert decode_frame(encode_frame(frame)) == frame


def test_old_reference_projection_is_not_a_fresh_operation_answer(frame):
    value = payload(frame, (case(),))
    value["cases"][0]["reference_projection"] = {"whole_reading_correct": True}
    with pytest.raises(ReferenceError):
        decode_authored(json.dumps(value).encode(), frame)


def assessment(frame, predictions):
    return dict(
        protocol="source-operation-evaluation-1",
        set_id=3,
        reference_snapshot=[{"pass_id": 7}],
        frame_digest="frozen",
        units=[dict(score_cases(frame, (case(),), predictions), unit_id=2)],
    )


def test_paired_changes_preserve_stale_reference_refusals(frame):
    empty, correct = assessment(frame, ()), assessment(frame, (prediction(),))
    assert len(compare_assessments(empty, correct)["changes"]["newly_captured"]) == 1
    assert len(compare_assessments(correct, empty)["changes"]["regressed"]) == 1
    changed = dict(correct, reference_snapshot=[{"pass_id": 8}])
    with pytest.raises(ReferenceError, match="same frozen"):
        compare_assessments(empty, changed)


def test_exact_relation_direction_and_order_cannot_be_renamed_as_match(frame):
    relation = replace(
        case(),
        contribution_kind="relation",
        alternatives=(
            {
                "endpoints": [
                    {"role": "unit", "contribution_id": "u"},
                    {"role": "value", "contribution_id": "v"},
                ]
            },
        ),
    )
    reversed_relation = dict(
        prediction(),
        kind="relation",
        endpoints=[
            {"role": "value", "contribution_id": "u"},
            {"role": "unit", "contribution_id": "v"},
        ],
    )
    closure = (prediction("u"), prediction("v", anchors=("cell-2",)))
    assert (
        score_cases(frame, (relation,), (reversed_relation,), endpoint_closure=closure)["cases"][0][
            "judgment"
        ]
        == "unsupported"
    )


def test_unstated_note_does_not_mark_a_value_proposal_spurious(frame):
    note = replace(
        case(),
        facet="note",
        source_state="unstated",
        alternatives=(),
        candidate_selector={"semantic_type": "table.note"},
    )
    result = score_cases(frame, (note,), (prediction(),))
    assert result["cases"][0]["judgment"] == "unsupported"
    assert result["cases"][0]["error_category"] == "missing_output"


def test_true_negative_requires_declared_detection_question_and_separate_counts(frame):
    note = replace(
        case(),
        facet="note",
        source_state="unstated",
        alternatives=(),
        candidate_selector={"semantic_type": "table.note"},
        expectation_mode="absence_detection",
    )
    result = score_cases(frame, (note,), ())
    assert result["cases"][0]["capture_outcome"] == "true_negative"
    assert result["facets"]["note"]["supported"] == 0
    assert result["absence_detection_facets"]["note"]["supported"] == 1


def test_explicit_unstated_field_capture_requires_actual_structure(frame):
    note = replace(
        case(),
        facet="note",
        source_state="unstated",
        alternatives=({"source_field_state": "unstated", "anchor_role": "inspection_subject"},),
    )
    assert score_cases(frame, (note,), ())["cases"][0]["error_category"] == "missing_output"
    output = prediction(source_field_state="unstated", anchor_role="inspection_subject")
    assert (
        score_cases(frame, (note,), (output,))["cases"][0]["capture_outcome"]
        == "captured_structure"
    )


def test_inspection_subject_quote_does_not_become_value_literal(frame):
    output = dict(
        prediction(),
        anchor_role="inspection_subject",
        source_field_state="unstated",
        anchors=[
            {"anchor_id": "cell-1", "precision": "exact", "source_piece": "some inspected context"}
        ],
    )
    literal = replace(case(), alternatives=({"source_pieces": ["some inspected context"]},))
    assert score_cases(frame, (literal,), (output,))["cases"][0]["judgment"] == "unsupported"


def test_attachment_requires_right_cell_and_right_header_source_semantics(frame):
    primary = prediction("cell-value", anchors=("cell-1",))
    other = prediction("other-cell-value", anchors=("cell-2",))
    header = dict(
        prediction("header", anchors=("term-1",)), semantic_type="table.header_path", value="Speed"
    )
    expected = replace(
        case(),
        facet="header_attachment",
        contribution_kind="relation",
        anchor_endpoint_role="cell_value",
        alternatives=(
            {
                "semantic_type": "table.header_path_attachment",
                "endpoint_semantics": [
                    {"role": "cell_value", "anchor_ids": ["cell-1"], "fields": {"value": "12"}},
                    {
                        "role": "header_path",
                        "anchor_ids": ["term-1"],
                        "fields": {"semantic_type": "table.header_path", "value": "Speed"},
                    },
                ],
            },
        ),
    )
    relation = dict(
        contribution_id="attachment",
        kind="relation",
        anchors=[],
        semantic_type="table.header_path_attachment",
        endpoints=[
            {"role": "cell_value", "contribution_id": "cell-value"},
            {"role": "header_path", "contribution_id": "header"},
        ],
    )
    closure = (primary, other, header)
    correct = score_cases(frame, (expected,), (relation,), endpoint_closure=closure)
    assert correct["cases"][0]["judgment"] == "supported"
    wrong_cell = dict(
        relation,
        endpoints=[
            {"role": "cell_value", "contribution_id": "other-cell-value"},
            {"role": "header_path", "contribution_id": "header"},
        ],
    )
    wrong = score_cases(frame, (expected,), (wrong_cell,), endpoint_closure=closure)
    assert wrong["cases"][0]["judgment"] == "unsupported"
    # A correct header proposal existing elsewhere cannot establish attachment.
    assert (
        score_cases(frame, (expected,), (header,), endpoint_closure=closure)["cases"][0]["judgment"]
        == "unsupported"
    )
    with pytest.raises(ReferenceError, match="endpoint closure"):
        score_cases(frame, (expected,), (relation,))


def conditional_role_case(identity="role", anchor="term-1"):
    return replace(
        case(identity, facet="conditional_role", anchors=(anchor,)),
        contribution_kind="proposal",
        anchor_endpoint_role="mention",
        candidate_selector={"semantic_type": "attribute.role"},
        alternatives=(
            {
                "kind": "proposal",
                "semantic_type": "attribute.role",
                "value": {"kind": "text", "text": "defined_term"},
                "endpoint_semantics": [
                    {
                        "role": "mention",
                        "anchor_ids": [anchor],
                        "fields": {
                            "semantic_type": "entity.distribution",
                            "source_pieces": ["normal distribution"],
                        },
                    }
                ],
            },
        ),
    )


def conditional_products(identity="attribute", mention="mention", anchor="term-1", **kwargs):
    subject = dict(
        contribution_id=mention,
        kind="occurrence",
        semantic_type="entity.distribution",
        anchors=[dict(anchor_id=anchor, precision="exact", source_piece="normal distribution")],
    )
    attribute = dict(
        contribution_id=identity,
        kind="proposal",
        semantic_type="attribute.role",
        anchors=[],
        endpoints=[dict(role="mention", contribution_id=mention)],
        value={"kind": "text", "text": "defined_term"},
        **kwargs,
    )
    return subject, attribute


def test_conditional_proposal_preserves_kind_and_exact_mention_semantics(frame):
    expected = conditional_role_case()
    mention, attribute = conditional_products()
    decoded = decode_authored(json.dumps(payload(frame, (expected,))).encode(), frame)
    assert decoded["cases"] == [expected]
    result = score_cases(frame, (expected,), (attribute,), endpoint_closure=(mention,))
    assert result["cases"][0]["judgment"] == "supported"
    assert result["cases"][0]["contribution_id"] == "attribute"
    assert attribute["kind"] == "proposal" and not attribute["anchors"]


# Independently required distinctions: do not derive this inventory from producer declarations.
CONDITIONAL_ROLE_CASES = (
    pytest.param("mention", "missing_output", id="role-correct-location-wrong-endpoint"),
    pytest.param("label", "wrong_structure", id="location-correct-role-wrong-label"),
    pytest.param("class", "wrong_structure", id="location-correct-wrong-entity-class"),
    pytest.param("endpoint_role", "missing_output", id="location-correct-wrong-endpoint-role"),
)
assert {parameter.values[0] for parameter in CONDITIONAL_ROLE_CASES} == {
    "mention",
    "label",
    "class",
    "endpoint_role",
}
assert len(CONDITIONAL_ROLE_CASES) == 4


@pytest.mark.parametrize("error,error_category", CONDITIONAL_ROLE_CASES)
def test_conditional_role_requires_correct_label_location_and_entity_class(
    frame, request, error, error_category
):
    mention, attribute = conditional_products()
    expected = conditional_role_case()
    positive = score_cases(frame, (expected,), (attribute,), endpoint_closure=(mention,))
    assert positive["cases"][0]["judgment"] == "supported"
    if error == "mention":
        mention["anchors"][0]["anchor_id"] = "cell-2"
    elif error == "label":
        attribute["value"] = {"kind": "text", "text": "mentioned_term"}
    elif error == "class":
        mention["semantic_type"] = "entity.quantity"
    else:
        attribute["endpoints"][0]["role"] = "unrelated"
    request.node.add_report_section(
        "call",
        "conditional-role-boundary",
        json.dumps(
            dict(
                unit=frame.unit,
                question=frame.operation_question,
                question_version=frame.operation_version,
                facet=expected.facet,
                case_id=expected.case_id,
                mutation=error,
                expected_endpoint_role=expected.anchor_endpoint_role,
                expected_anchor_ids=expected.anchor_ids,
                endpoint_members=attribute["endpoints"],
                endpoint_anchor_ids=[a["anchor_id"] for a in mention["anchors"]],
            ),
            sort_keys=True,
        ),
    )
    result = score_cases(frame, (expected,), (attribute,), endpoint_closure=(mention,))
    assert result["cases"][0]["judgment"] == "unsupported"
    assert result["cases"][0]["error_category"] == error_category


def test_conditional_proposal_requires_complete_endpoint_closure(frame):
    _, attribute = conditional_products()
    with pytest.raises(ReferenceError, match="endpoint closure"):
        score_cases(frame, (conditional_role_case(),), (attribute,))


def test_repeated_conditional_contexts_share_one_physical_facet_vote(frame):
    first, first_attribute = conditional_products(
        "attribute-a", "mention-a", score=0.9, origin_task_id=1
    )
    second, second_attribute = conditional_products(
        "attribute-b", "mention-b", score=0.3, origin_task_id=2
    )
    result = score_cases(
        frame,
        (conditional_role_case("a"), conditional_role_case("b")),
        (first_attribute, second_attribute),
        endpoint_closure=(first, second),
    )
    assert result["facets"]["conditional_role"]["supported"] == 1
    assert result["cases"][1]["error_category"] == "duplicate_occurrence"
    assert result["prediction_count"] == 2 and result["producer_observation_count"] == 2


def test_equal_conditional_literals_at_distinct_mentions_remain_distinct(frame):
    first, first_attribute = conditional_products("attribute-a", "mention-a")
    second, second_attribute = conditional_products("attribute-b", "mention-b", anchor="cell-2")
    result = score_cases(
        frame,
        (conditional_role_case("a"), conditional_role_case("b", anchor="cell-2")),
        (first_attribute, second_attribute),
        endpoint_closure=(first, second),
    )
    assert result["facets"]["conditional_role"]["supported"] == 2


@pytest.mark.parametrize("kind", ("occurrence", "composite", "diagnostic"))
def test_endpoint_anchored_case_refuses_other_contribution_kinds(kind):
    with pytest.raises(ReferenceError, match="proposal or relation"):
        replace(conditional_role_case(), contribution_kind=kind)


@pytest.mark.parametrize("role", ("", " ", True))
def test_endpoint_anchored_case_requires_declared_role(role):
    with pytest.raises(ReferenceError, match="declared role"):
        replace(conditional_role_case(), anchor_endpoint_role=role)


def test_v2_frame_preserves_unalignable_opportunities_and_exposure_partition(frame):
    from corpus_structure.evaluate.operation_assessment import (
        OperationEvaluationFrameV2,
        OperationSourceOpportunity,
    )

    opportunity = OperationSourceOpportunity(
        "source-span-without-tokens", 23, 0, 4, "role", "stated"
    )
    frozen = OperationEvaluationFrameV2(
        **asdict(frame),
        source_group="book-origin",
        partition="development",
        inspected_scope="original-native-passage",
        opportunities=(opportunity,),
        exposure_history=("development-feedback",),
    )
    encoded = encode_frame(frozen)
    assert encoded["protocol"] == "source-operation-frame-2"
    assert decode_frame(encoded) == frozen
    assert not frozen.contribution_ids
    with pytest.raises(ReferenceError, match="exposed source"):
        replace(frozen, partition="final_assessment")
    with pytest.raises(ReferenceError, match="distinct source opportunities"):
        replace(frozen, opportunities=(opportunity, opportunity))
    with pytest.raises(ReferenceError, match="outside frozen"):
        replace(frozen, opportunities=(replace(opportunity, source_view_id=24),))


@pytest.mark.parametrize(
    "emitted,expected_status,expected_error",
    [
        pytest.param(False, "not_captured", "missing_output", id="source-opportunity-after-filter"),
        pytest.param(True, "captured_structure", None, id="source-opportunity-with-output"),
    ],
)
def test_v2_coverage_preserves_missing_reference_and_missing_prediction(
    frame, request, emitted, expected_status, expected_error
):
    from corpus_structure.evaluate.operation_assessment import (
        OperationEvaluationFrameV2,
        OperationSourceOpportunity,
    )

    frozen = OperationEvaluationFrameV2(
        **asdict(frame),
        source_group="book",
        partition="development",
        inspected_scope="source scope",
        opportunities=(
            OperationSourceOpportunity("case-1", 23, 0, 2, "value", "stated"),
            OperationSourceOpportunity("not-authored", 23, 2, 4, "role", "uninspected"),
        ),
    )
    predictions = (prediction(),) if emitted else ()
    request.node.add_report_section(
        "call",
        "source-opportunity-population",
        json.dumps(
            dict(
                unit=frozen.unit,
                release_id=frozen.release_id,
                source_group=frozen.source_group,
                partition=frozen.partition,
                question=frozen.operation_question,
                opportunity_ids=[item.opportunity_id for item in frozen.opportunities],
                emitted_ids=[row["contribution_id"] for row in predictions],
            ),
            sort_keys=True,
        ),
    )
    result = score_cases(frozen, (case(),), predictions)
    assert result["source_coverage"]["opportunity_count"] == 2
    assert [v["assessment_status"] for v in result["source_coverage"]["opportunities"]] == [
        expected_status,
        "reference_missing",
    ]
    assert result["source_coverage"]["opportunities"][0]["error_category"] == expected_error
    assert result["source_coverage"]["opportunities"][1]["judgment"] == "unassessed"


def test_v2_coverage_distinguishes_permissible_alternative_from_unresolved_no_output(frame):
    from corpus_structure.evaluate.operation_assessment import (
        OperationEvaluationFrameV2,
        OperationSourceOpportunity,
    )

    frozen = OperationEvaluationFrameV2(
        **asdict(frame),
        source_group="book",
        partition="development",
        inspected_scope="source",
        opportunities=(OperationSourceOpportunity("case-1", 23, 0, 2, "value", "unresolved"),),
    )
    ambiguous = replace(case(), judgment="ambiguous", source_state="unresolved")
    present = score_cases(frozen, (ambiguous,), (prediction(),))
    missing = score_cases(frozen, (ambiguous,), ())
    assert (
        present["source_coverage"]["opportunities"][0]["assessment_status"]
        == "permissible_alternative"
    )
    assert present["source_coverage"]["opportunities"][0]["judgment"] == "ambiguous"
    assert missing["source_coverage"]["opportunities"][0]["assessment_status"] == "unresolved"
    assert missing["source_coverage"]["opportunities"][0]["error_category"] == "unresolved"


def test_output_first_scores_each_frozen_observation_at_a_shared_occurrence(frame):
    output = replace(frame, direction="output_first", contribution_ids=("p1", "p2"))
    cases = (case("first", contribution_id="p1"), case("second", contribution_id="p2"))
    predictions = (prediction("p1", origin_task_id=1), prediction("p2", origin_task_id=2))
    assessed = score_cases(output, cases, predictions)
    assert [
        (c["contribution_id"], c["judgment"], c["error_category"]) for c in assessed["cases"]
    ] == [("p1", "supported", None), ("p2", "supported", None)]
    source = score_cases(frame, (case("first"), case("second")), predictions)
    assert source["facets"]["value"]["supported"] == 1
    assert source["cases"][1]["error_category"] == "duplicate_occurrence"


OUTPUT_CAPTURE_CASES = (
    pytest.param("complete", None, id="output-frozen-ids-complete"),
    pytest.param("extra", None, id="output-unselected-id-excluded"),
    pytest.param("duplicate_sidecar", None, id="output-repeated-view-one-id"),
    pytest.param("missing", "frozen output population is absent", id="output-frozen-id-missing"),
    pytest.param("conflict", "conflicting retained payloads", id="output-same-id-conflicting-body"),
    pytest.param("duplicate_frame", "repeats an identity", id="output-frozen-id-duplicated"),
)
assert {parameter.values[0] for parameter in OUTPUT_CAPTURE_CASES} == {
    "complete",
    "extra",
    "duplicate_sidecar",
    "missing",
    "conflict",
    "duplicate_frame",
}
assert len(OUTPUT_CAPTURE_CASES) == 6


@pytest.mark.parametrize("capture,error", OUTPUT_CAPTURE_CASES)
def test_output_capture_preserves_exact_frozen_ids(frame, request, capture, error):
    frozen_ids = ("p1", "p2")
    predictions = [prediction("p1", origin_task_id=1), prediction("p2", origin_task_id=2)]
    if capture == "extra":
        predictions.append(prediction("unselected", anchors=("cell-2",)))
    elif capture == "duplicate_sidecar":
        predictions.append(dict(predictions[0], selected_task_id=99, task_status="reused"))
    elif capture == "missing":
        predictions.pop()
    elif capture == "conflict":
        predictions.append(dict(predictions[0], value="13"))
    elif capture == "duplicate_frame":
        frozen_ids = ("p1", "p1")
    request.node.add_report_section(
        "call",
        "output-population",
        json.dumps(
            dict(
                unit=frame.unit,
                question=frame.operation_question,
                version=frame.operation_version,
                direction="output_first",
                frozen_ids=frozen_ids,
                captured_ids=[row["contribution_id"] for row in predictions],
            ),
            sort_keys=True,
        ),
    )

    def assess():
        frozen = replace(frame, direction="output_first", contribution_ids=frozen_ids)
        expected = (case("first", contribution_id="p1"), case("second", contribution_id="p2"))
        return score_cases(frozen, expected, predictions)

    if error:
        with pytest.raises(ReferenceError, match=error):
            assess()
    else:
        result = assess()
        assert result["prediction_count"] == 2
        assert [(row["contribution_id"], row["judgment"]) for row in result["cases"]] == [
            ("p1", "supported"),
            ("p2", "supported"),
        ]
