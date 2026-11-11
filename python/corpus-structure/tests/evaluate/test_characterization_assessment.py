"""Independent adversarial expectations for characterization assessment, no model calls."""

import json
from copy import deepcopy
from dataclasses import asdict, replace
from typing import Any, cast

import pytest

from corpus_structure.evaluate.characterization_assessment import (
    LayerProjection,
    graph_equal,
    output_key,
    score_characterization,
)
from corpus_structure.evaluate.operation_assessment import (
    PROTOCOL,
    CharacterizationSourceOpportunity,
    OperationCase,
    OperationEvaluationFrameV3,
    decode_authored,
    decode_frame,
    encode_frame,
)
from corpus_structure.evaluate.semantic import ReferenceError

PIN = {"task_id": 7, "product_key": "layer", "content_digest": "a" * 64}
VIEW = {"task_id": 8, "product_key": "view", "content_digest": "b" * 64}
EXTENT = dict(source_view_id=23, projection="c" * 64, native_pointer="#/texts/0", start=0, end=20)


def frame(direction="source_first", **changes) -> OperationEvaluationFrameV3:
    common: dict[str, Any] = dict(
        unit="chapter5",
        release_id="release-1",
        guideline_version="independent-1",
        rubric_version="scope-1",
        context_policy="source-only-1",
        operation_question="predicate_scope",
        operation_version="1",
        domain="statistics",
        direction=direction,
        pin={"source_view_id": 23},
        source_group="book",
        partition="development",
        inspected_scope="original clause",
        opportunities=(
            CharacterizationSourceOpportunity("opportunity", (EXTENT,), "scope", "stated"),
        ),
    )
    if direction == "output_first":
        common.update(characterization_view=VIEW, selected_layers=(PIN,), outputs=())
    return OperationEvaluationFrameV3(**dict(common, **changes))


def case(**changes) -> OperationCase:
    common: dict[str, Any] = dict(
        case_id="scope-case",
        facet="scope",
        anchor_ids=(),
        inspected_scope="original clause",
        source_state="stated",
        judgment="supported",
        alternatives=({"value": {"kind": "operator", "value": "not"}},),
        explanation="Independently read not taking scope over every.",
        assessor_provenance={"actor": "independent-A"},
        opportunity_id="opportunity",
        required_family="prose.scope",
        candidate_selector={"collection": "terms", "value": {"family": "prose.scope"}},
    )
    return OperationCase(**dict(common, **changes))


def coverage(**changes):
    return dict(
        family="prose.scope",
        availability="available",
        outcome="complete",
        examined=[dict(projection=EXTENT["projection"], start=0, end=20)],
        **changes,
    )


def prediction(**changes):
    return dict(
        reference=dict(layer=PIN, collection="terms", local_id="term"),
        collection="terms",
        extents=[dict(EXTENT, start=1, end=4)],
        value=dict(kind="operator", value="not", family="prose.scope"),
        **changes,
    )


def payload(frozen, cases):
    return dict(
        protocol=PROTOCOL,
        release_id=frozen.release_id,
        unit_ref=frozen.unit,
        guideline=frozen.guideline_version,
        rubric_version=frozen.rubric_version,
        context_policy=frozen.context_policy,
        operation_question=frozen.operation_question,
        operation_version=frozen.operation_version,
        domain=frozen.domain,
        direction=frozen.direction,
        reason="independent source-only judgment",
        cases=[asdict(c) for c in cases],
    )


def test_v3_source_frame_roundtrip_preserves_discontinuity_and_never_binds_outputs():
    opportunity = CharacterizationSourceOpportunity(
        "opportunity", (EXTENT, dict(EXTENT, start=24, end=30)), "scope", "stated"
    )
    value = frame(opportunities=(opportunity,))
    assert decode_frame(encode_frame(value)) == value
    assert len(encode_frame(value)["evaluation_frame"]["opportunities"][0]["extents"]) == 2
    with pytest.raises(ReferenceError, match="source-first"):
        frame(characterization_view=VIEW)


def test_v3_explicit_empty_output_population_is_not_unbound():
    value = frame("output_first")
    assert value.outputs == ()
    assert decode_frame(encode_frame(value)) == value
    with pytest.raises(ReferenceError, match="requires exact"):
        replace(value, outputs=None)
    result = score_characterization(value, (), ())
    assert result["output_coverage"]["selected_count"] == 0
    assert result["cases"] == []


def test_case_cannot_backfill_output_id_or_move_source_opportunity():
    frozen = frame()
    assert (
        decode_authored(json.dumps(payload(frozen, (case(),))).encode(), frozen)["cases"][0]
        == case()
    )
    for invalid in (case(output_reference=prediction()["reference"]), case(opportunity_id="other")):
        with pytest.raises(ReferenceError):
            decode_authored(json.dumps(payload(frozen, (invalid,))).encode(), frozen)


def test_missing_and_wrong_structure_are_distinct_from_unexamined_scope():
    correct = score_characterization(frame(), (case(),), (prediction(),), coverage=(coverage(),))
    assert correct["cases"][0]["judgment"] == "supported"
    missing = score_characterization(frame(), (case(),), (), coverage=(coverage(),))
    assert missing["cases"][0]["error_category"] == "missed_opportunity"
    wrong = prediction()
    wrong["value"]["value"] = "every"
    result = score_characterization(frame(), (case(),), (wrong,), coverage=(coverage(),))
    assert result["cases"][0]["error_category"] == "wrong_structure"
    unavailable = score_characterization(frame(), (case(),), (), coverage=())
    assert unavailable["cases"][0]["error_category"] == "prediction_scope_unavailable"


def test_inapplicable_is_visible_and_never_earns_semantic_credit():
    opportunity = replace(frame().opportunities[0], source_state="inapplicable")
    result = score_characterization(
        frame(opportunities=(opportunity,)),
        (case(source_state="inapplicable", alternatives=()),),
        (),
        coverage=(coverage(),),
    )
    assert result["cases"][0]["judgment"] == "unassessed"
    assert result["cases"][0]["error_category"] == "inapplicable"


def test_source_opportunity_stays_visible_without_reference_or_output():
    result = score_characterization(frame(), (), (), coverage=(coverage(),))
    assert result["source_coverage"]["opportunity_count"] == 1
    assert result["source_coverage"]["opportunities"][0]["assessment_status"] == "reference_missing"


def test_output_first_exact_identity_cannot_be_replaced_by_equal_text():
    original = prediction()["reference"]
    frozen = frame("output_first", outputs=(original,))
    other = prediction()
    other["reference"] = dict(original, local_id="other")
    with pytest.raises(ReferenceError, match="absent"):
        score_characterization(
            frozen, (case(output_reference=original),), (other,), coverage=(coverage(),)
        )


def graph() -> dict[str, Any]:
    return dict(
        root="choice",
        nodes=[
            dict(
                id="choice",
                value={"collection": "choices", "compatibility": "exclusive"},
                edges=[
                    {"label": "alternative", "target": "left", "position": 0},
                    {"label": "alternative", "target": "right", "position": 1},
                ],
            ),
            dict(
                id="left",
                value={"collection": "choice_member"},
                edges=[
                    {"label": "root", "target": "first"},
                    {"label": "required_choices", "target": "right", "position": 0},
                ],
            ),
            dict(
                id="right",
                value={"collection": "choice_member"},
                edges=[{"label": "root", "target": "second"}],
            ),
            dict(id="first", value={"kind": "operator", "value": "not"}, edges=[]),
            dict(id="second", value={"kind": "operator", "value": "not"}, edges=[]),
        ],
    )


def test_graph_alpha_renaming_preserves_independently_named_shared_identity():
    left = graph()
    right = deepcopy(left)
    names = {n["id"]: f"independent-{i}" for i, n in enumerate(right["nodes"])}
    right["root"] = names[right["root"]]
    for node in right["nodes"]:
        node["id"] = names[node["id"]]
        for edge in node["edges"]:
            edge["target"] = names[edge["target"]]
    assert graph_equal(left, right)


@pytest.mark.parametrize(
    "mutation", ("crossed", "merged", "unknown", "semantic_or", "role", "parallel")
)
def test_graph_comparison_refuses_lost_correlation_or_meaning(mutation):
    original, changed = graph(), graph()
    if mutation == "crossed":
        changed["nodes"][1]["edges"][1]["target"] = "left"
    elif mutation == "merged":
        changed["nodes"][2]["edges"][0]["target"] = "first"
        changed["nodes"].pop()
    elif mutation == "unknown":
        changed["nodes"][0]["value"]["compatibility"] = "unknown"
    elif mutation == "semantic_or":
        changed["nodes"][0]["value"] = {"kind": "operator", "value": "or"}
    elif mutation == "role":
        changed["nodes"][1]["edges"][0]["label"] = "participant"
    else:
        changed["nodes"][1]["edges"].append(dict(changed["nodes"][1]["edges"][0]))
    assert not graph_equal(original, changed)


def test_graph_projection_keeps_same_spelling_binders_distinct_and_linear():
    terms = [
        dict(
            local_id="root",
            kind="operator",
            value="and",
            children=[
                dict(role="left", target="one", structural=True, order=0),
                dict(role="right", target="two", structural=True, order=1),
            ],
        ),
        dict(local_id="one", kind="binder", value="x", children=[]),
        dict(local_id="two", kind="binder", value="x", children=[]),
    ]
    layer = {
        name: []
        for name in ("occurrences", "annotations", "memberships", "roles", "choices", "coverage")
    }
    layer["terms"] = terms
    actual = LayerProjection(lambda _: layer).project(
        dict(layer=PIN, collection="terms", local_id="root")
    )["graph"]
    assert isinstance(actual, dict)
    assert len(actual["nodes"]) == 3
    assert actual["nodes"][0]["edges"][0]["target"] != actual["nodes"][0]["edges"][1]["target"]
    assert (
        output_key(dict(layer=PIN, collection="coverage", local_id="native.tokens"))[-1]
        == "native.tokens"
    )


def test_unlocated_prediction_cannot_prove_a_correct_negative():
    unlocated = prediction()
    unlocated["extents"] = []
    c = case(source_state="unstated", alternatives=(), expectation_mode="absence_detection")
    result = score_characterization(frame(), (c,), (unlocated,), coverage=(coverage(),))
    assert result["cases"][0]["judgment"] == "unassessed"
    assert result["cases"][0]["error_category"] == "mapping_unavailable"


def test_another_completed_family_cannot_prove_scope_was_examined():
    unrelated = dict(coverage(), family="native.tokens")
    result = score_characterization(frame(), (case(),), (), coverage=(unrelated,))
    assert result["cases"][0]["error_category"] == "prediction_scope_unavailable"


def test_multiple_questions_on_one_opportunity_retain_each_assessment():
    result = score_characterization(
        frame(),
        (case(), case(case_id="other-question", alternatives=({"value": {"value": "every"}},))),
        (prediction(),),
        coverage=(coverage(),),
    )
    assessments = result["source_coverage"]["opportunities"][0]["assessments"]
    assert [v["case_id"] for v in assessments] == ["scope-case", "other-question"]
    assert [v["judgment"] for v in assessments] == ["supported", "unsupported"]


def test_native_only_formal_position_remains_unmapped_in_semantic_assessment():
    native_only = prediction()
    native_only["extents"] = [{"native_pointer": "#/texts/0"}]
    result = score_characterization(frame(), (case(),), (native_only,), coverage=(coverage(),))
    assert result["cases"][0]["error_category"] == "mapping_unavailable"


def captured_assessment(monkeypatch, *, extents, expected_case, coverage_row=None):
    """Exercise production capture and scoring; only retained ports/custody are doubled."""
    from types import SimpleNamespace

    from corpus_structure.evaluate import operation_assessment as assessment
    from corpus_structure.evaluate.characterization_assessment import evaluate_characterization
    from corpus_structure.semantic import characterization_store as store

    selected_coverage = coverage_row or dict(
        coverage(), eligible=[dict(projection=EXTENT["projection"], start=0, end=20)]
    )
    body = dict(
        source_scope={"source_view_ids": [23]},
        occurrences=[dict(local_id="location", extents=extents)],
        terms=[
            dict(
                local_id="term",
                kind="operator",
                value="not",
                family="prose.scope",
                occurrences=["location"],
                children=[],
            )
        ],
        annotations=[],
        memberships=[],
        roles=[],
        choices=[],
        coverage=[selected_coverage],
    )
    if expected_case.candidate_selector.get("collection") == "coverage":
        body["terms"] = []
    monkeypatch.setattr(
        store,
        "read_view",
        lambda *a, **k: SimpleNamespace(payload={"layers": [PIN], "active_layers": [PIN]}),
    )
    monkeypatch.setattr(store, "read_layer", lambda *a, **k: SimpleNamespace(payload=body))
    monkeypatch.setattr(
        store,
        "read_layer_manifest",
        lambda *a, **k: SimpleNamespace(payload={"source_scope": body["source_scope"]}),
    )
    opportunity = replace(frame().opportunities[0], source_state=expected_case.source_state)
    frozen = frame(opportunities=(opportunity,))
    snapshot = [{"unit_id": 2, "pass_id": 3, "frame_id": 4}]
    retained = []

    def call(_conn, statement, **values):
        if "native_reference_snapshot" in statement:
            return SimpleNamespace(scalar_one=lambda: snapshot)
        retained.append(json.loads(values["v"]))
        return SimpleNamespace(scalar_one=lambda: 99)

    monkeypatch.setattr(assessment, "_call", call)
    monkeypatch.setattr(assessment, "source_units", lambda *a: [{"source_view_id": 23}])
    monkeypatch.setattr(
        assessment, "read_pass", lambda *a, **k: {"payload": {"cases": [expected_case]}}
    )
    report = evaluate_characterization(
        None,
        project_id="book",
        run_id=5,
        set_id=6,
        completed={"cut_id": 1},
        prepared=SimpleNamespace(release_id="release-1"),
        definition={"sampling": {"partition": "development"}},
        units=[
            {
                "id": 2,
                "unit_key": "chapter5",
                "source_view_id": 23,
                "context": [encode_frame(frozen)],
            }
        ],
        frames={"chapter5": frozen},
        characterization_view=VIEW,
    )
    from corpus_structure.semantic.identity import canonical_bytes

    assert canonical_bytes(retained[0]) == canonical_bytes(report.result)
    return report.result["units"][0]


@pytest.mark.parametrize("extents", ([], [{"native_pointer": "#/texts/0"}]))
def test_evaluation_capture_retains_unmapped_outputs_before_absence_grading(monkeypatch, extents):
    report = captured_assessment(
        monkeypatch,
        extents=extents,
        expected_case=case(
            source_state="unstated", alternatives=(), expectation_mode="absence_detection"
        ),
    )
    assert report["output_coverage"]["selected_count"] == 1
    assert report["cases"][0]["judgment"] == "unassessed"
    assert report["cases"][0]["error_category"] == "mapping_unavailable"


def test_evaluation_capture_discards_provably_disjoint_output(monkeypatch):
    report = captured_assessment(
        monkeypatch,
        extents=[dict(EXTENT, start=25, end=28)],
        expected_case=case(
            source_state="unstated", alternatives=(), expectation_mode="absence_detection"
        ),
    )
    assert report["output_coverage"]["selected_count"] == 0
    assert report["cases"][0]["judgment"] == "supported"
    assert report["cases"][0]["error_category"] == "inspected_unstated"


def test_evaluation_capture_scores_coverage_using_declared_source_selectors(monkeypatch):
    report = captured_assessment(
        monkeypatch,
        extents=[],
        expected_case=case(
            candidate_selector={"collection": "coverage", "value": {"family": "prose.scope"}},
            alternatives=({"value": {"availability": "available", "outcome": "complete"}},),
        ),
    )
    assert report["cases"][0]["judgment"] == "supported"
    assert report["cases"][0]["matched_references"][0]["collection"] == "coverage"


def test_evaluation_coverage_reports_unavailable_truth_without_claiming_semantic_quality(
    monkeypatch,
):
    row = dict(
        coverage(),
        eligible=[dict(projection=EXTENT["projection"], start=0, end=20)],
        examined=[],
        availability="unavailable",
        outcome="failed",
    )
    report = captured_assessment(
        monkeypatch,
        extents=[],
        coverage_row=row,
        expected_case=case(
            candidate_selector={"collection": "coverage", "value": {"family": "prose.scope"}},
            alternatives=({"value": {"availability": "unavailable", "outcome": "failed"}},),
        ),
    )
    assert report["cases"][0]["judgment"] == "supported"
    assert report["quality_claim"] == "not_established"


def test_semantic_graph_projection_is_frozen_and_ignores_incidental_evidence():
    actual = graph()
    for node in actual["nodes"]:
        node["value"]["collection"] = node["value"].get("collection", "terms")
        node["value"]["scores"] = [{"value": 0.7}]
        node["value"]["provenance"] = ["provider-specific-runtime"]
    expected = deepcopy(actual)
    for node in expected["nodes"]:
        node["value"].pop("scores")
        node["value"].pop("provenance")
    assert graph_equal(actual, expected, "source_semantics")
    assert not graph_equal(actual, expected, "native_fidelity")
    changed = deepcopy(expected)
    changed["nodes"][1]["edges"][1]["target"] = "left"
    assert not graph_equal(actual, changed, "source_semantics")
    with pytest.raises(ReferenceError, match="declared comparison"):
        case(alternatives=({"graph": expected},))
    authored = case(alternatives=({"graph": expected},), graph_projection="source_semantics")
    assert (
        decode_authored(json.dumps(payload(frame(), (authored,))).encode(), frame())["cases"][
            0
        ].graph_projection
        == "source_semantics"
    )


def test_semantic_graph_projection_preserves_scope_and_shared_binders():
    actual = graph()
    for node in actual["nodes"]:
        node["value"]["collection"] = node["value"].get("collection", "terms")
    changed = deepcopy(actual)
    changed["nodes"][2]["edges"][0]["target"] = "first"
    changed["nodes"].pop()
    assert not graph_equal(actual, changed, "source_semantics")
    changed = deepcopy(actual)
    changed["nodes"][3]["value"]["value"] = "every"
    assert not graph_equal(actual, changed, "source_semantics")


def test_source_graph_preserves_model_answer_but_ignores_request_and_scores():
    from corpus_structure.semantic.observations import source_value

    answer: dict[str, Any] = dict(
        family="character_modal_force_v1",
        question_key="force",
        stage="2",
        answer_kind="choice",
        state="proposed",
        declaration_digest="d" * 64,
        request_digest="a" * 64,
        candidate_list_digest="c" * 64,
        native_answer=source_value({"choice": "possible", "score": 0.7}),
        selected_keys=["possible"],
        alternatives=[dict(key="possible", state="proposed", score={"value": 0.7})],
    )
    actual: dict[str, Any] = dict(
        root="a",
        nodes=[
            dict(
                id="a",
                value={
                    "collection": "annotations",
                    "kind": "modal",
                    "status": "private_proposal",
                    "model_answer": answer,
                },
                edges=[],
            )
        ],
    )
    expected = deepcopy(actual)
    expected_answer = expected["nodes"][0]["value"]["model_answer"]
    for name in ("declaration_digest", "request_digest", "candidate_list_digest"):
        expected_answer.pop(name)
    expected_answer["native_answer"] = source_value({"choice": "possible"})
    expected_answer["alternatives"] = [dict(key="possible", state="proposed")]
    assert graph_equal(actual, expected, "source_semantics")
    assert not graph_equal(actual, expected, "native_fidelity")
    changed = deepcopy(expected)
    changed["nodes"][0]["value"]["model_answer"]["selected_keys"] = ["necessary"]
    assert not graph_equal(actual, changed, "source_semantics")


def test_source_graph_preserves_native_token_alignment_without_run_identity():
    token = dict(
        index=0,
        native_run="producer-run-1",
        container="doc-17",
        sentence="sentence-4",
        text="may",
        space=False,
        whitespace=" ",
        source_role="prose",
        pos="AUX",
        dependency="aux",
        native_head=1,
        head_index_base=0,
    )
    actual: dict[str, Any] = dict(
        root="token",
        nodes=[
            dict(
                id="token",
                value={"collection": "annotations", "kind": "native_token", "native_token": token},
                edges=[],
            )
        ],
    )
    expected = deepcopy(actual)
    details = expected["nodes"][0]["value"]["native_token"]
    for name in ("native_run", "container", "sentence"):
        details.pop(name)
    assert graph_equal(actual, expected, "source_semantics")
    assert not graph_equal(actual, expected, "native_fidelity")
    details["dependency"] = "subject"
    assert not graph_equal(actual, expected, "source_semantics")


def test_semantic_choice_and_prerequisite_order_is_not_incidental_identity():
    actual = graph()
    for node in actual["nodes"]:
        node["value"]["collection"] = node["value"].get("collection", "terms")
    expected = deepcopy(actual)
    expected["nodes"][0]["edges"].reverse()
    for position, edge in enumerate(expected["nodes"][0]["edges"]):
        edge["position"] = position
    assert graph_equal(actual, expected, "source_semantics")
    assert not graph_equal(actual, expected, "native_fidelity")
    crossed = deepcopy(expected)
    crossed["nodes"][1]["edges"][1]["target"] = "left"
    assert not graph_equal(actual, crossed, "source_semantics")


def test_unresolved_source_does_not_hide_false_unique_output_resolution():
    reference = prediction()["reference"]
    opportunity = replace(frame().opportunities[0], source_state="unresolved")
    frozen = frame("output_first", opportunities=(opportunity,), outputs=(reference,))
    result = score_characterization(
        frozen,
        (
            case(
                output_reference=reference,
                source_state="unresolved",
                judgment="unsupported",
                alternatives=(),
                error_category="unsupported_unique_resolution",
            ),
        ),
        (prediction(),),
        coverage=(coverage(),),
    )
    assert result["cases"][0]["judgment"] == "unsupported"
    assert result["cases"][0]["error_category"] == "unsupported_unique_resolution"


def test_named_binding_graph_alpha_renames_generated_refs_but_keeps_head_direction():
    def layer(prefix):
        def local(name):
            return prefix + name

        def ref(name):
            return dict(layer=PIN, local_id=local(name))

        occurrences = [
            dict(local_id=local(f"o{i}"), extents=[dict(EXTENT, start=i * 5, end=i * 5 + 1)])
            for i in (0, 1)
        ]
        tokens = [
            dict(
                local_id=local(f"token{i}"),
                kind="native_token",
                vocabulary="native",
                family="syntax",
                status="native_evidence",
                occurrences=[local(f"o{i}")],
                native_token=dict(
                    index=i,
                    native_run=prefix + "run",
                    container=prefix + "container",
                    sentence=prefix + "sentence",
                    text="x",
                    space=False,
                    whitespace=" ",
                    source_role="prose",
                ),
            )
            for i in (0, 1)
        ]
        match = dict(
            local_id=local("match"),
            kind="named",
            vocabulary="source",
            family="syntax",
            status="interpreted",
            occurrences=[local("o0")],
            named_match=dict(
                rule=prefix + "rule",
                variant="default",
                mechanism="dependency",
                protocol="named-1",
                dependency_digest=prefix + "digest",
                native_container=ref("token0"),
                status="complete",
                bindings=[
                    dict(
                        role="subject",
                        node=prefix + "pattern",
                        head=ref("token0"),
                        members=[ref("token1")],
                        expansion="head",
                        status="complete",
                    )
                ],
            ),
        )
        return dict(
            occurrences=occurrences,
            annotations=[*tokens, match],
            memberships=[],
            roles=[],
            terms=[],
            choices=[],
            coverage=[],
        ), ref("match")

    left, root = layer("producer-")
    right, expected_root = layer("independent-")
    actual = LayerProjection(lambda _: left).project(
        dict(layer=PIN, collection="annotations", local_id=root["local_id"])
    )["graph"]
    expected = LayerProjection(lambda _: right).project(
        dict(layer=PIN, collection="annotations", local_id=expected_root["local_id"])
    )["graph"]
    assert graph_equal(actual, expected, "source_semantics")
    right["annotations"][-1]["named_match"]["bindings"][0]["head"] = dict(
        layer=PIN, local_id="independent-token1"
    )
    reversed_head = LayerProjection(lambda _: right).project(
        dict(layer=PIN, collection="annotations", local_id=expected_root["local_id"])
    )["graph"]
    assert not graph_equal(actual, reversed_head, "source_semantics")


def test_formal_graph_keeps_source_link_and_meaning_without_generated_input_ids():
    def layer(prefix, symbol="x", correspondence_source="primary"):
        occurrence = dict(local_id=prefix + "occurrence", extents=[dict(EXTENT, start=0, end=1)])
        other = dict(local_id=prefix + "other-occurrence", extents=[dict(EXTENT, start=5, end=6)])
        source = dict(
            local_id=prefix + "input",
            kind="formal_input",
            vocabulary="formal",
            family="formal",
            status="native_evidence",
            occurrences=[occurrence["local_id"]],
            formal_input=dict(
                parent_occurrence=occurrence["local_id"],
                representation="source_text",
                text="x",
                grammar="grammar-" + prefix,
                start_symbol="expression",
                macro_identity=prefix + "macro",
                syntax_outcome="complete",
                interpretation_outcome="not_requested",
                symbol_outcome="not_requested",
                correspondence=[
                    dict(
                        input_start=0,
                        input_end=1,
                        relation="exact",
                        source_occurrences=[
                            occurrence["local_id"]
                            if correspondence_source == "primary"
                            else other["local_id"]
                        ],
                    )
                ],
            ),
        )
        token = dict(
            local_id=prefix + "token",
            kind="formal_node",
            vocabulary="formal",
            family="formal",
            status="native_evidence",
            occurrences=[occurrence["local_id"]],
            formal=dict(
                input_id=source["local_id"],
                node_kind="token",
                rule="identifier",
                start=0,
                end=1,
                normalized=dict(kind="identifier", value=symbol, domain_status="not_requested"),
            ),
        )
        return dict(
            occurrences=[occurrence, other],
            annotations=[source, token],
            memberships=[],
            roles=[],
            terms=[],
            choices=[],
            coverage=[],
        )

    actual = LayerProjection(lambda _: layer("producer-")).project(
        dict(layer=PIN, collection="annotations", local_id="producer-token")
    )["graph"]
    expected = LayerProjection(lambda _: layer("independent-")).project(
        dict(layer=PIN, collection="annotations", local_id="independent-token")
    )["graph"]
    assert graph_equal(actual, expected, "source_semantics")
    wrong = LayerProjection(lambda _: layer("independent-", "y")).project(
        dict(layer=PIN, collection="annotations", local_id="independent-token")
    )["graph"]
    assert not graph_equal(actual, wrong, "source_semantics")
    wrong_correspondence = LayerProjection(
        lambda _: layer("independent-", correspondence_source="other")
    ).project(dict(layer=PIN, collection="annotations", local_id="independent-token"))["graph"]
    assert not graph_equal(actual, wrong_correspondence, "source_semantics")


def test_navigation_graph_lifts_real_role_token_and_source_label_references():
    def layer(prefix, subject=0):
        occurrences = [
            dict(local_id=prefix + f"o{i}", extents=[dict(EXTENT, start=i * 5, end=i * 5 + 1)])
            for i in (0, 1)
        ]
        tokens = [
            dict(
                local_id=prefix + f"t{i}",
                kind="native_token",
                vocabulary="native",
                family="syntax",
                status="native_evidence",
                occurrences=[prefix + f"o{i}"],
                native_token=dict(
                    index=i,
                    native_run=prefix + "run",
                    container=prefix + "container",
                    sentence=prefix + "sentence",
                    text="x",
                    space=False,
                    whitespace=" ",
                    source_role="prose",
                ),
            )
            for i in (0, 1)
        ]
        annotation = dict(
            local_id=prefix + "navigation",
            kind="navigation",
            vocabulary="source",
            family="syntax",
            status="interpreted",
            occurrences=[prefix + "o0"],
            navigation=dict(
                codec="source-navigation-v1",
                kind="named_link",
                pointer=EXTENT["native_pointer"],
                status="complete",
                rule=prefix + "compiled-rule",
                block=prefix + "block",
                roles=[
                    dict(role="subject", occurrences=[prefix + f"o{subject}"]),
                    dict(role="cue", occurrences=[prefix + "o1"]),
                ],
                native_tokens=[
                    dict(name="head", index=0, native_node=dict(layer=PIN, local_id=prefix + "t0"))
                ],
                source_labels=[
                    dict(kind="numbering_namespace", value="Eq", occurrences=[prefix + "o0"])
                ],
            ),
        )
        return dict(
            occurrences=occurrences,
            annotations=[*tokens, annotation],
            memberships=[],
            roles=[],
            terms=[],
            choices=[],
            coverage=[],
        )

    actual = LayerProjection(lambda _: layer("producer-")).project(
        dict(layer=PIN, collection="annotations", local_id="producer-navigation")
    )["graph"]
    expected = LayerProjection(lambda _: layer("independent-")).project(
        dict(layer=PIN, collection="annotations", local_id="independent-navigation")
    )["graph"]
    assert graph_equal(actual, expected, "source_semantics")
    assert not graph_equal(actual, expected, "native_fidelity")
    wrong = LayerProjection(lambda _: layer("independent-", subject=1)).project(
        dict(layer=PIN, collection="annotations", local_id="independent-navigation")
    )["graph"]
    assert not graph_equal(actual, wrong, "source_semantics")


def native_reference(**changes):
    return dict(
        version="spacy-native-reference-v1",
        kind="spans",
        scheme="spacy",
        text="may",
        words=["may"],
        spaces=[False],
        span_key="sents",
        spans=[dict(start=0, end=3)],
        labeled=False,
        **changes,
    )


def test_native_case_expected_structure_is_explicit_and_closed():
    value = case(
        native_reference=native_reference(),
        required_family="spacy.sentences",
        alternatives=(),
        candidate_selector={},
    )
    assert (
        decode_authored(json.dumps(payload(frame(), (value,))).encode(), frame())["cases"][
            0
        ].native_reference
        == value.native_reference
    )
    for invalid in (
        dict(native_reference(), scheme="UD"),
        dict(native_reference(), text="changed"),
        dict(native_reference(), unknown_field="hidden"),
    ):
        with pytest.raises(ReferenceError, match="native scoring"):
            case(native_reference=invalid, alternatives=(), candidate_selector={})
    with pytest.raises(ReferenceError, match="own task"):
        case(native_reference=native_reference())


def test_native_partial_scores_never_become_semantic_credit():
    value = case(
        native_reference=native_reference(),
        required_family="spacy.sentences",
        alternatives=(),
        candidate_selector={},
    )
    result = score_characterization(
        frame(),
        (value,),
        (),
        native_scores={
            value.case_id: dict(
                status="partial",
                exact_match=True,
                reason="unalignable_reference",
                scores={"sents_f": 1.0},
                coverage={
                    "reference": {"scored": 1, "unalignable": 1},
                    "prediction": {"emitted": 1},
                },
            )
        },
    )
    assert result["cases"][0]["judgment"] == "unassessed"
    assert result["cases"][0]["native_metrics"]["scores"]["sents_f"] == 1.0


def test_native_exact_task_structure_judgment_does_not_use_a_score_threshold():
    value = case(
        native_reference=native_reference(),
        required_family="spacy.sentences",
        alternatives=(),
        candidate_selector={},
    )
    for exact, judgment in ((True, "supported"), (False, "unsupported")):
        result = score_characterization(
            frame(),
            (value,),
            (),
            native_scores={
                value.case_id: dict(
                    status="scored",
                    exact_match=exact,
                    reason=None,
                    scores={"sents_f": 0.999},
                    coverage={},
                )
            },
        )
        assert result["cases"][0]["judgment"] == judgment


def test_native_capture_restores_retained_block_by_exact_ordered_scope(monkeypatch):
    from types import SimpleNamespace

    from spacy.tokens import Doc

    from corpus_structure.evaluate.characterization_assessment import NativeCaseInputs
    from corpus_structure.methods import native_evidence_layers as restoration
    from corpus_structure.semantic import source_views

    text = "may"
    extent = dict(EXTENT, start=0, end=3, text=text, synthetic=False)
    body = dict(
        base_document=VIEW,
        operation={"produced_families": ["spacy.tokens", "spacy.sentences"]},
        source_scope={"source_view_ids": [23]},
        occurrences=[dict(local_id="block-occ", extents=[extent])],
        annotations=[
            dict(
                local_id="block",
                kind="native.block",
                family="spacy.tokens",
                occurrences=["block-occ"],
            ),
            dict(
                local_id="token",
                kind="native.token",
                family="spacy.tokens",
                native_token=dict(native_run="spacy", container="block"),
                occurrences=["block-occ"],
            ),
        ],
        memberships=[],
        roles=[],
        terms=[],
        choices=[],
        coverage=[],
    )
    projection = LayerProjection(lambda _: body)
    frozen = frame(
        opportunities=(
            replace(frame().opportunities[0], extents=({key: extent[key] for key in EXTENT},)),
        )
    )
    value = case(
        native_reference=native_reference(),
        required_family="spacy.sentences",
        alternatives=(),
        candidate_selector={},
    )
    restored = []

    def docs(layer, views, vocab, *, required):
        restored.append((layer.payload, required))
        return {"block": Doc(vocab, words=["may"], spaces=[False], sent_starts=[True])}

    monkeypatch.setattr(restoration, "retained_spacy_docs", docs)
    monkeypatch.setattr(
        source_views, "load_source_view", lambda *a, **k: SimpleNamespace(text=text)
    )
    native = NativeCaseInputs(
        None, frozen, [PIN], projection, [dict(coverage(), family="spacy.sentences")]
    )
    first, repeated = native.score(value), native.score(value)
    assert first["status"] == "scored" and first["exact_match"] is True
    assert repeated == first and len(restored) == 1
    token_ref = dict(layer=PIN, collection="annotations", local_id="token")
    output_frame = replace(
        frozen,
        direction="output_first",
        characterization_view=VIEW,
        selected_layers=(PIN,),
        outputs=(token_ref,),
    )
    unrelated_output = NativeCaseInputs(
        None, output_frame, [PIN], projection, [dict(coverage(), family="spacy.sentences")]
    ).score(replace(value, output_reference=token_ref))
    assert unrelated_output["status"] == "unavailable"
    assert unrelated_output["reason"] == "native_output_reference_incompatible"
    # Same literal string at another authentic source position must not select this block.
    other_scope = replace(
        frozen,
        opportunities=(
            replace(
                frozen.opportunities[0],
                extents=(dict(frozen.opportunities[0].extents[0], start=5, end=8),),
            ),
        ),
    )
    unrelated = NativeCaseInputs(
        None, other_scope, [PIN], projection, [dict(coverage(), family="spacy.sentences")]
    ).score(value)
    assert (
        unrelated["status"] == "unavailable"
        and unrelated["reason"] == "native_block_scope_unavailable"
    )


@pytest.mark.parametrize(
    ("state", "judgment"),
    (
        ("stated", "supported"),
        ("unstated", "supported"),
        ("unresolved", "ambiguous"),
        ("inapplicable", "unassessed"),
        ("uninspected", "unassessed"),
    ),
)
def test_uninspected_source_opportunity_freezes_scope_without_preauthoring_state(state, judgment):
    opportunity = replace(frame().opportunities[0], source_state="uninspected")
    frozen = frame(opportunities=(opportunity,))
    authored = case(
        source_state=state,
        judgment=judgment,
        alternatives=({"value": {"kind": "operator"}},) if state == "stated" else (),
        expectation_mode="absence_detection" if state == "unstated" else "structure",
    )
    decoded = decode_authored(json.dumps(payload(frozen, (authored,))).encode(), frozen)
    assert decoded["cases"][0].source_state == state
    restored = decode_frame(encode_frame(frozen))
    assert isinstance(restored, OperationEvaluationFrameV3)
    assert restored.opportunities[0].source_state == "uninspected"


def test_known_frozen_source_state_cannot_be_silently_relabelled():
    with pytest.raises(ReferenceError, match="invalid operation"):
        decode_authored(
            json.dumps(
                payload(
                    frame(),
                    (case(source_state="unresolved", judgment="ambiguous", alternatives=()),),
                )
            ).encode(),
            frame(),
        )


def test_output_author_packet_resolves_only_exact_witness_closure(monkeypatch):
    from types import SimpleNamespace

    from corpus_structure.evaluate import operation_assessment as assessment
    from corpus_structure.semantic import characterization_store as store

    dependency = dict(PIN, task_id=9, content_digest="d" * 64)
    selected = dict(layer=PIN, collection="choices", local_id="choice")
    body = dict(
        occurrences=[dict(local_id="location", extents=[EXTENT])],
        roles=[
            dict(
                local_id="role",
                owner="predicate",
                member="participant",
                role="subject",
                occurrences=["location"],
                basis={"kind": "native_prediction", "status": "recorded"},
            )
        ],
        terms=[
            dict(
                local_id="predicate",
                kind="predicate",
                children=[dict(role="subject", target="participant", structural=True)],
            ),
            dict(local_id="participant", kind="participant", occurrences=["location"]),
        ],
        choices=[
            dict(
                local_id="choice",
                compatibility="exclusive",
                members=[
                    dict(
                        local_id="reading",
                        root="role",
                        required_external_choices=[
                            dict(layer=dependency, local_id="external-reading")
                        ],
                    )
                ],
            )
        ],
    )
    dependency_body = dict(
        choices=[
            dict(
                local_id="dependency-choice",
                compatibility="unknown",
                members=[
                    dict(local_id="external-reading", root="other-root"),
                    dict(local_id="other-reading", root="other-root"),
                ],
            )
        ],
        terms=[dict(local_id="other-root", kind="predicate", value="other")],
    )
    packet = dict(selected_outputs=[dict(reference=selected, value=body["choices"][0])])
    monkeypatch.setattr(
        assessment, "_call", lambda *a, **kw: SimpleNamespace(scalar_one=lambda: deepcopy(packet))
    )
    monkeypatch.setattr(assessment, "_unit", lambda *a: {"source_run_id": 47})
    loaded = []

    def read(_conn, pin, *, run_id, max_bytes):
        assert run_id == 47 and 0 < max_bytes <= 8388608
        loaded.append(pin.task_id)
        return SimpleNamespace(payload=body if pin.task_id == PIN["task_id"] else dependency_body)

    monkeypatch.setattr(store, "read_layer", read)
    result = assessment.author_packet(cast(Any, None), 3)
    assert loaded == [7, 9]
    assert [item["reference"] for item in result["selected_outputs"]] == [selected]
    witness = result["selected_outputs"][0]["witness_context"]
    assert witness["purpose"] == "interpretation_only_not_assessed_population"
    identities = {node["qualified_identity"]["local_id"] for node in witness["graph"]["nodes"]}
    assert identities == {
        "choice",
        "reading",
        "role",
        "predicate",
        "participant",
        "location",
        "external-reading",
        "dependency-choice",
        "other-reading",
        "other-root",
    }
    assert any(
        node["value"].get("compatibility") == "unknown" for node in witness["graph"]["nodes"]
    )
    monkeypatch.setattr(assessment, "_AUTHOR_PACKET_BYTES", len(json.dumps(packet)))
    with pytest.raises(ReferenceError, match="byte bound"):
        assessment.author_packet(cast(Any, None), 3)


def test_author_witness_graph_enforces_budget_before_full_closure():
    body = {"terms": [dict(local_id="term", kind="predicate", value="x" * 100)]}
    with pytest.raises(ReferenceError, match="byte bound"):
        LayerProjection(lambda pin: body).graph(PIN, "term", max_bytes=32, witness_closure=True)
