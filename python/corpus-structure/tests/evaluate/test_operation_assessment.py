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
        unit="source:chapter5", release_id="release-1", guideline_version="source-only-1",
        rubric_version="local-1", context_policy="selected-source-1", operation_question="table-fields",
        operation_version="1", domain="scientific-source", direction="source_first",
        pin={"source_view_id": 23}, anchor_ids=("cell-1", "cell-2", "term-1"),
    )


def case(identity="case-1", facet="value", anchors=("cell-1",), **kwargs):
    return OperationCase(
        case_id=identity, facet=facet, anchor_ids=anchors, inspected_scope="table-1/body-cell-1",
        source_state="stated", judgment="supported", alternatives=({"value": "12"},),
        explanation="Independently transcribed body cell is 12.",
        assessor_provenance={"actor": "independent-source-author", "assistance": "none"},
        **kwargs,
    )


def prediction(identity="p1", anchors=("cell-1",), **kwargs):
    return dict(contribution_id=identity, kind="proposal", semantic_type="table.value",
                anchors=[{"anchor_id": anchor} for anchor in anchors], value="12", **kwargs)


def test_value_location_and_role_are_independent(frame):
    value = case()
    role = replace(value, case_id="role-1", facet="role", alternatives=({"semantic_type": "table.header"},))
    located = replace(value, case_id="location-1", facet="location", contribution_kind="occurrence",
                      alternatives=({"semantic_type": "source_occurrence"},))
    location = dict(prediction("o1"), kind="occurrence", semantic_type="source_occurrence")
    result = score_cases(frame, (value, role, located), (prediction(), location))
    assert result["facets"]["value"]["supported"] == 1
    assert result["facets"]["location"]["supported"] == 1
    assert result["facets"]["role"]["unsupported"] == 1
    assert result["cases"][-1]["error_category"] == "wrong_structure"
    assert "accuracy" not in result and result["quality_claim"] == "not_established"


@pytest.mark.parametrize("facet,expected,actual", [
    ("header", {"header": "speed"}, {"header": "distance"}),
    ("unit", {"unit": "m/s"}, {"unit": "m"}),
    ("negation", {"negated": True}, {"negated": False}),
    ("condition_extent", {"members": ["a", "b"]}, {"members": ["a"]}),
    ("version", {"version": "v2"}, {"version": "v1"}),
    ("inventory_target", {"target_state": "absent"}, {"target_state": "present"}),
    ("candidate_survival", {"retrieved": True}, {"retrieved": False}),
])
def test_structural_questions_do_not_change_value_truth(frame, facet, expected, actual):
    value = case()
    extra = replace(value, case_id="structural", facet=facet, alternatives=(expected,))
    result = score_cases(frame, (value, extra), (prediction(**actual),))
    assert result["facets"]["value"]["supported"] == 1
    assert result["facets"][facet]["unsupported"] == 1


def test_unstated_and_uninspected_are_not_pooled(frame):
    unstated = replace(case(), case_id="note-unstated", facet="note", source_state="unstated", alternatives=())
    uninspected = replace(unstated, case_id="note-uninspected", source_state="uninspected", judgment="unassessed")
    result = score_cases(frame, (unstated, uninspected), ())
    assert result["facets"]["note"] == {"supported": 0, "unsupported": 1, "ambiguous": 0, "unassessed": 1}
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
    flexible = replace(case("a"), alternatives=({"value": "12"}, {"value": "13"}),
                       permissible_anchor_sets=(("cell-2",),))
    exact = case("b")
    twelve = prediction()
    thirteen = dict(prediction("p2", anchors=("cell-2",)), value="13")
    result = score_cases(frame, (flexible, exact), (twelve, thirteen))
    assert [item["contribution_id"] for item in result["cases"]] == ["p2", "p1"]
    assert result == score_cases(frame, (exact, flexible), (thirteen, twelve))


def test_repeated_windows_do_not_multiply_one_physical_occurrence(frame):
    result = score_cases(frame, (case("a"), case("b")), (prediction("window-1"), prediction("window-2")))
    assert result["facets"]["value"]["supported"] == 1
    assert result["facets"]["value"]["unsupported"] == 1


def test_reused_task_sidecars_do_not_change_contribution_identity(frame):
    result = score_cases(frame, (case(),), (
        prediction(selected_task_id=1, origin_task_id=10, task_status="done", source_view_id=23, task_id=10, position=0),
        prediction(selected_task_id=2, origin_task_id=10, task_status="reused", source_view_id=23, task_id=10, position=0),
        prediction(selected_task_id=3, origin_task_id=11, task_status="done", source_view_id=23, task_id=11, position=2),
    ))
    assert result["prediction_count"] == 1
    assert result["prediction_count_grain"] == "unique_semantic_contribution_product"
    assert result["producer_observation_count"] == 2
    assert result["facets"]["value"]["supported"] == 1


def test_permissible_alternatives_stay_ambiguous(frame):
    ambiguous = replace(case(), judgment="ambiguous", source_state="unresolved",
                        alternatives=({"value": "12"}, {"value": "13"}))
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
    return dict(protocol=PROTOCOL, release_id=frame.release_id, unit_ref=frame.unit,
                guideline=frame.guideline_version, rubric_version=frame.rubric_version,
                context_policy=frame.context_policy, operation_question=frame.operation_question,
                operation_version=frame.operation_version, domain=frame.domain,
                direction=frame.direction, reason="Independent source pass", cases=[asdict(value) for value in cases])


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
    return dict(protocol="source-operation-evaluation-1", set_id=3, reference_snapshot=[{"pass_id": 7}],
                frame_digest="frozen", units=[dict(score_cases(frame, (case(),), predictions), unit_id=2)])


def test_paired_changes_preserve_stale_reference_refusals(frame):
    empty, correct = assessment(frame, ()), assessment(frame, (prediction(),))
    assert len(compare_assessments(empty, correct)["changes"]["newly_captured"]) == 1
    assert len(compare_assessments(correct, empty)["changes"]["regressed"]) == 1
    changed = dict(correct, reference_snapshot=[{"pass_id": 8}])
    with pytest.raises(ReferenceError, match="same frozen"):
        compare_assessments(empty, changed)


def test_exact_relation_direction_and_order_cannot_be_renamed_as_match(frame):
    relation = replace(case(), contribution_kind="relation", alternatives=({"endpoints": [
        {"role": "unit", "contribution_id": "u"}, {"role": "value", "contribution_id": "v"}]},))
    reversed_relation = dict(prediction(), kind="relation", endpoints=[
        {"role": "value", "contribution_id": "u"}, {"role": "unit", "contribution_id": "v"}])
    closure = (prediction("u"), prediction("v", anchors=("cell-2",)))
    assert score_cases(frame, (relation,), (reversed_relation,), endpoint_closure=closure)["cases"][0]["judgment"] == "unsupported"


def test_unstated_note_does_not_mark_a_value_proposal_spurious(frame):
    note = replace(case(), facet="note", source_state="unstated", alternatives=(),
                   candidate_selector={"semantic_type": "table.note"})
    result = score_cases(frame, (note,), (prediction(),))
    assert result["cases"][0]["judgment"] == "unsupported"
    assert result["cases"][0]["error_category"] == "missing_output"


def test_true_negative_requires_declared_detection_question_and_separate_counts(frame):
    note = replace(case(), facet="note", source_state="unstated", alternatives=(),
                   candidate_selector={"semantic_type": "table.note"}, expectation_mode="absence_detection")
    result = score_cases(frame, (note,), ())
    assert result["cases"][0]["capture_outcome"] == "true_negative"
    assert result["facets"]["note"]["supported"] == 0
    assert result["absence_detection_facets"]["note"]["supported"] == 1


def test_explicit_unstated_field_capture_requires_actual_structure(frame):
    note = replace(case(), facet="note", source_state="unstated",
                   alternatives=({"source_field_state": "unstated", "anchor_role": "inspection_subject"},))
    assert score_cases(frame, (note,), ())["cases"][0]["error_category"] == "missing_output"
    output = prediction(source_field_state="unstated", anchor_role="inspection_subject")
    assert score_cases(frame, (note,), (output,))["cases"][0]["capture_outcome"] == "captured_structure"


def test_inspection_subject_quote_does_not_become_value_literal(frame):
    output = dict(prediction(), anchor_role="inspection_subject", source_field_state="unstated",
                  anchors=[{"anchor_id": "cell-1", "precision": "exact", "source_piece": "some inspected context"}])
    literal = replace(case(), alternatives=({"source_pieces": ["some inspected context"]},))
    assert score_cases(frame, (literal,), (output,))["cases"][0]["judgment"] == "unsupported"


def test_attachment_requires_right_cell_and_right_header_source_semantics(frame):
    primary = prediction("cell-value", anchors=("cell-1",))
    other = prediction("other-cell-value", anchors=("cell-2",))
    header = dict(prediction("header", anchors=("term-1",)), semantic_type="table.header_path", value="Speed")
    expected = replace(case(), facet="header_attachment", contribution_kind="relation", anchor_endpoint_role="cell_value",
        alternatives=({"semantic_type": "table.header_path_attachment", "endpoint_semantics": [
            {"role": "cell_value", "anchor_ids": ["cell-1"], "fields": {"value": "12"}},
            {"role": "header_path", "anchor_ids": ["term-1"], "fields": {"semantic_type": "table.header_path", "value": "Speed"}},
        ]},))
    relation = dict(contribution_id="attachment", kind="relation", anchors=[], semantic_type="table.header_path_attachment",
                    endpoints=[{"role": "cell_value", "contribution_id": "cell-value"},
                               {"role": "header_path", "contribution_id": "header"}])
    closure = (primary, other, header)
    correct = score_cases(frame, (expected,), (relation,), endpoint_closure=closure)
    assert correct["cases"][0]["judgment"] == "supported"
    wrong_cell = dict(relation, endpoints=[{"role": "cell_value", "contribution_id": "other-cell-value"},
                                         {"role": "header_path", "contribution_id": "header"}])
    wrong = score_cases(frame, (expected,), (wrong_cell,), endpoint_closure=closure)
    assert wrong["cases"][0]["judgment"] == "unsupported"
    # A correct header proposal existing elsewhere cannot establish attachment.
    assert score_cases(frame, (expected,), (header,), endpoint_closure=closure)["cases"][0]["judgment"] == "unsupported"
    with pytest.raises(ReferenceError, match="endpoint closure"):
        score_cases(frame, (expected,), (relation,))
