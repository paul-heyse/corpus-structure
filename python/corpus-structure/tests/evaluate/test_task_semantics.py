"""Independent task expectations, producer-shaped controls; no book answers or inference."""

from copy import deepcopy
from typing import Any

import pytest

from corpus_structure.evaluate.characterization_assessment import LayerProjection
from corpus_structure.evaluate.task_semantics import (
    SemanticTaskReference,
    joint_outcome,
    score_task,
)

PIN = dict(task_id=7, product_key="layer", content_digest="a" * 64)
EXTENT = dict(source_view_id=23, projection="c" * 64, native_pointer="#/texts/0", start=0, end=1)


def extent(start, end):
    return dict(EXTENT, start=start, end=end)


def entity(identity, kind, start, end, **kw):
    return dict(
        id=identity,
        kind=kind,
        extents=[extent(start, end)],
        **({"support": "implicit_site"} if kind == "variable" and start == end else {}),
        **kw,
    )


def reference(**kw):
    value = dict(
        version="characterization-task-reference-v1",
        task="roles",
        role_scheme="construction-children-v1",
        mode="complete_slots",
        focus="p",
        entities=[entity("p", "predicate", 2, 5), entity("s", "participant", 0, 1)],
        assertions=[dict(subject="p", relation="grammatical_subject", object="s")],
        complete_slots=[dict(subject="p", relation="grammatical_subject")],
    )
    return dict(value, **kw)


def body(*, wrapped=True, wrong=False, extra=False, unlocated=False) -> dict[str, Any]:
    occurrences = [
        dict(local_id="p-loc", extents=[extent(2, 5)]),
        dict(local_id="s-loc", extents=[extent(0, 1)]),
        dict(local_id="whole", extents=[extent(0, 5)]),
        dict(local_id="bad-loc", extents=[extent(6, 7)]),
    ]
    subject = dict(role="grammatical_subject", target="s", structural=True)
    terms: list[dict[str, Any]] = [
        dict(
            local_id="s",
            family="construction.predication",
            kind="participant",
            value="x",
            occurrences=[] if unlocated else ["s-loc"],
            children=[],
        ),
        dict(
            local_id="bad",
            family="construction.predication",
            kind="participant",
            value="y",
            occurrences=["bad-loc"],
            children=[],
        ),
    ]
    if wrong:
        subject["target"] = "bad"
    if wrapped:
        terms.extend(
            [
                dict(
                    local_id="lexeme",
                    family="construction.predication",
                    kind="participant",
                    value="runs",
                    occurrences=["p-loc"],
                    children=[],
                ),
                dict(
                    local_id="p",
                    family="construction.predication",
                    kind="predicate",
                    value="verbal_predication",
                    occurrences=["whole"],
                    children=[
                        dict(role="predicate", target="lexeme", structural=True, order=1),
                        dict(subject, order=0),
                    ],
                ),
            ]
        )
    else:
        terms.append(
            dict(
                local_id="p",
                family="construction.predication",
                kind="predicate",
                value="provider-head-name",
                occurrences=["p-loc"],
                children=[subject],
            )
        )
    if extra:
        terms[-1]["children"].append(dict(subject, target="bad"))
    return dict(terms=terms, occurrences=occurrences, roles=[], choices=[], coverage=[])


def predictions(wire, family="construction.predication", selected=None):
    projection = LayerProjection(lambda pin: wire)
    outputs = [
        (name, row["local_id"])
        for name in ("terms", "roles", "choices", "annotations", "memberships")
        for row in wire.get(name, ())
    ]
    return [
        projection.project(dict(layer=PIN, collection=name, local_id=identity))
        for name, identity in outputs
        if selected is None or identity in selected
    ]


def test_declared_wrapper_and_incidental_predicate_labels_do_not_change_task_meaning():
    for wrapped in (False, True):
        result = score_task(
            reference(), "construction.predication", predictions(body(wrapped=wrapped))
        )
        assert result["status"] == "scored" and result["exact_match"] is True


@pytest.mark.parametrize("mutation", ["wrong", "extra", "wrong_role", "reversed", "multiplicity"])
def test_complete_named_role_slot_rejects_wrong_and_contradictory_assertions(mutation):
    wire = body(wrong=mutation == "wrong", extra=mutation == "extra")
    if mutation == "wrong_role":
        wire["terms"][-1]["children"][-1]["role"] = "grammatical_object"
    elif mutation == "reversed":
        wire["terms"][0]["children"] = [
            dict(role="grammatical_subject", target="p", structural=True)
        ]
        wire["terms"][-1]["children"] = wire["terms"][-1]["children"][:-1]
    elif mutation == "multiplicity":
        wire["terms"][-1]["children"].append(deepcopy(wire["terms"][-1]["children"][-1]))
    result = score_task(reference(), "construction.predication", predictions(wire))
    assert result["status"] == "scored" and result["exact_match"] is False
    assert result["differences"]


def test_positive_witness_explicitly_does_not_claim_complete_slot():
    ref = reference(mode="witness", complete_slots=[])
    assert (
        score_task(ref, "construction.predication", predictions(body(extra=True)))["exact_match"]
        is True
    )


def test_known_empty_slot_is_miss_but_unlocated_endpoint_is_contract_unavailable():
    wire = body()
    wire["terms"][-1]["children"] = wire["terms"][-1]["children"][:-1]
    assert (
        score_task(reference(), "construction.predication", predictions(wire))["exact_match"]
        is False
    )
    result = score_task(reference(), "construction.predication", predictions(body(unlocated=True)))
    assert (
        result["status"] == "unavailable"
        and result["differences"][0]["kind"] == "assessment_contract_unavailable"
    )


def test_unknown_adapter_is_not_a_linguistic_miss():
    result = score_task(reference(), "provider.unknown", [])
    assert result["status"] == "unavailable" and result["exact_match"] is None


def test_population_closes_named_slots_across_several_retained_roots():
    wire = body(wrapped=False)
    wire["terms"].append(
        dict(
            wire["terms"][-1],
            local_id="contradictory",
            children=[dict(role="grammatical_subject", target="bad", structural=True)],
        )
    )
    assert (
        score_task(reference(), "construction.predication", predictions(wire))["exact_match"]
        is False
    )


def choice_wire() -> dict[str, Any]:
    return dict(
        occurrences=[dict(local_id="cue", extents=[extent(1, 2)])],
        terms=[
            dict(
                local_id=identity,
                family="construction.scope",
                kind="operator",
                value="modality:" + value,
                occurrences=["cue"],
                children=[],
            )
            for identity, value in (
                ("a", "possibility"),
                ("b", "permission"),
                ("c", "necessity"),
                ("d", "obligation"),
            )
        ],
        choices=[
            dict(
                local_id="first",
                family="construction.scope",
                compatibility="exclusive",
                members=[
                    dict(local_id="ma", root="a", required_choices=["mc"]),
                    dict(local_id="mb", root="b", required_choices=["md"]),
                ],
            ),
            dict(
                local_id="second",
                family="construction.scope",
                compatibility="exclusive",
                members=[dict(local_id="mc", root="c"), dict(local_id="md", root="d")],
            ),
        ],
        coverage=[],
    )


def choice_reference():
    return reference(
        task="choices",
        focus="a",
        entities=[
            entity(identity, "operator", 1, 2, value="modality:" + value)
            for identity, value in (
                ("a", "possibility"),
                ("b", "permission"),
                ("c", "necessity"),
                ("d", "obligation"),
            )
        ],
        assertions=[],
        complete_slots=[],
        groups=[
            dict(
                id="first",
                compatibility="exclusive",
                members=[
                    dict(id="ma", root="a", requires=["mc"]),
                    dict(id="mb", root="b", requires=["md"]),
                ],
            ),
            dict(
                id="second",
                compatibility="exclusive",
                members=[dict(id="mc", root="c"), dict(id="md", root="d")],
            ),
        ],
        joint_queries=[
            dict(members=["ma", "mc"], expected="permitted"),
            dict(members=["ma", "md"], expected="forbidden"),
        ],
    )


def test_factorized_choices_preserve_cross_branch_correlation_without_expansion():
    wire, ref = choice_wire(), choice_reference()
    assert score_task(ref, "construction.scope", predictions(wire))["exact_match"] is True
    wire["choices"][0]["members"][0]["required_choices"] = ["md"]
    wire["choices"][0]["members"][1]["required_choices"] = ["mc"]
    assert score_task(ref, "construction.scope", predictions(wire))["exact_match"] is False


def test_unknown_choice_compatibility_is_unknown_not_forbidden():
    groups = [
        dict(
            id="g",
            compatibility="unknown",
            members=[dict(id="a", root="a"), dict(id="b", root="b")],
        )
    ]
    assert joint_outcome(groups, ["a", "b"]) == "unknown"
    assert joint_outcome([dict(groups[0], compatibility="exclusive")], ["a", "b"]) == "forbidden"


def test_task_reference_is_closed_and_requires_declared_roles_and_slots():
    for mutation in (
        dict(unknown=True),
        dict(assertions=[dict(subject="p", relation="agent_is_subject", object="s")]),
        dict(complete_slots=[]),
    ):
        with pytest.raises(ValueError):
            SemanticTaskReference.model_validate(reference(**mutation))


def scope_wire(*, merged=False, wrong_target=False) -> dict[str, Any]:
    terms = [
        dict(
            local_id="outer",
            kind="operator",
            value="negation",
            family="construction.scope",
            occurrences=["neg"],
            children=[
                dict(role="target", target="body" if wrong_target else "binder-a", structural=True)
            ],
        ),
        dict(
            local_id="binder-a",
            kind="binder",
            value="each",
            family="construction.scope",
            occurrences=["quant"],
            children=[
                dict(role="variable", target="variable-a", structural=True),
                dict(role="body", target="binder-b", structural=True),
            ],
        ),
        dict(
            local_id="binder-b",
            kind="binder",
            value="each",
            family="construction.scope",
            occurrences=["quant"],
            children=[
                dict(
                    role="variable",
                    target="variable-a" if merged else "variable-b",
                    structural=True,
                ),
                dict(role="body", target="body", structural=True),
            ],
        ),
        dict(
            local_id="variable-a",
            kind="participant",
            value="x",
            family="construction.scope",
            status="implicit",
            occurrences=["var"],
            children=[],
        ),
        dict(
            local_id="variable-b",
            kind="participant",
            value="x",
            family="construction.scope",
            status="implicit",
            occurrences=["var"],
            children=[],
        ),
        dict(
            local_id="body",
            kind="predicate",
            value="holds",
            family="construction.scope",
            occurrences=["body-loc"],
            children=[],
        ),
    ]
    if merged:
        terms = [term for term in terms if term["local_id"] != "variable-b"]
    return dict(
        terms=terms,
        occurrences=[
            dict(local_id=identity, extents=[extent(a, b)])
            for identity, a, b in (
                ("neg", 0, 1),
                ("quant", 2, 3),
                ("var", 4, 4),
                ("body-loc", 5, 8),
            )
        ],
        choices=[],
        coverage=[],
    )


def scope_reference():
    return reference(
        task="scope",
        focus="not",
        entities=[
            entity("not", "operator", 0, 1, value="negation"),
            entity("a", "binder", 2, 3),
            entity("b", "binder", 2, 3),
            entity("va", "variable", 4, 4),
            entity("vb", "variable", 4, 4),
            entity("body", "predicate", 5, 8),
        ],
        assertions=[
            dict(subject=s, relation=r, object=o)
            for s, r, o in (
                ("not", "target", "a"),
                ("a", "body", "b"),
                ("a", "variable", "va"),
                ("b", "body", "body"),
                ("b", "variable", "vb"),
            )
        ],
        complete_slots=[
            dict(subject=s, relation=r)
            for s, r in (
                ("not", "target"),
                ("a", "body"),
                ("a", "variable"),
                ("b", "body"),
                ("b", "variable"),
            )
        ],
    )


def test_nested_scope_direction_and_equal_spelled_binder_identity_are_conserved():
    ref = scope_reference()
    assert score_task(ref, "construction.scope", predictions(scope_wire()))["exact_match"] is True
    for kw in (dict(merged=True), dict(wrong_target=True)):
        assert (
            score_task(ref, "construction.scope", predictions(scope_wire(**kw)))["exact_match"]
            is False
        )


def modal_wire(*, force="epistemic", wrong_target=False) -> dict[str, Any]:
    annotations = [
        dict(
            local_id="cue-q",
            kind="model.question",
            family="character_modal_force_v1",
            occurrences=["whole"],
            model_answer=dict(
                family="character_modal_force_v1",
                question_key="modal_cue",
                state="proposed",
                answer_kind="text",
                depends_on=[],
            ),
        ),
        dict(
            local_id="target-q",
            kind="model.question",
            family="character_modal_force_v1",
            occurrences=["whole"],
            model_answer=dict(
                family="character_modal_force_v1",
                question_key="modal_target",
                state="proposed",
                answer_kind="text",
                depends_on=["cue-q"],
            ),
        ),
        dict(
            local_id="force-q",
            kind="model.question",
            family="character_modal_force_v1",
            occurrences=["whole"],
            model_answer=dict(
                family="character_modal_force_v1",
                question_key="modal_force",
                state="proposed",
                answer_kind="choice",
                selected_keys=[force],
                depends_on=["cue-q", "target-q"],
                native_answer={"probability": 0.99},
            ),
        ),
        dict(
            local_id="cue-proposal",
            kind="model.span_proposal",
            family="character_modal_force_v1",
            occurrences=["cue"],
            status="private_proposal",
        ),
        dict(
            local_id="target-proposal",
            kind="model.span_proposal",
            family="character_modal_force_v1",
            occurrences=["bad" if wrong_target else "target"],
            status="private_proposal",
        ),
    ]
    return dict(
        annotations=annotations,
        memberships=[
            dict(
                local_id=identity,
                family="character_modal_force_v1",
                group=group,
                member=member,
                role="private_proposal",
                occurrences=[occurrence],
            )
            for identity, group, member, occurrence in (
                ("cue-membership", "cue-q", "cue-proposal", "cue"),
                ("target-membership", "target-q", "target-proposal", "target"),
            )
        ],
        occurrences=[
            dict(local_id=identity, extents=[extent(a, b)])
            for identity, a, b in (
                ("whole", 0, 10),
                ("cue", 0, 3),
                ("target", 4, 10),
                ("bad", 11, 13),
            )
        ],
        coverage=[],
    )


def modal_reference():
    return reference(
        task="modal_force",
        focus="modal",
        entities=[
            entity("modal", "operator", 0, 3, value="modality:epistemic"),
            entity("cue", "source", 0, 3),
            entity("target", "source", 4, 10),
        ],
        assertions=[
            dict(subject="modal", relation=role, object=role, standing="private_proposal")
            for role in ("cue", "target")
        ],
        complete_slots=[dict(subject="modal", relation=role) for role in ("cue", "target")],
    )


def test_modal_question_adapter_uses_declared_choice_and_located_dependency_fields():
    ref = modal_reference()
    assert (
        score_task(ref, "character_modal_force_v1", predictions(modal_wire()))["exact_match"]
        is True
    )
    for kw in (dict(force="dynamic"), dict(wrong_target=True)):
        assert (
            score_task(ref, "character_modal_force_v1", predictions(modal_wire(**kw)))[
                "exact_match"
            ]
            is False
        )
    wire = modal_wire()
    wire["annotations"][2]["model_answer"]["depends_on"] = []
    result = score_task(ref, "character_modal_force_v1", predictions(wire))
    assert result["status"] == "unavailable"


def test_output_first_witnesses_do_not_authorize_unselected_context_claims():
    wire = body()
    wire["roles"] = [
        dict(
            local_id="unrelated-role",
            family="construction.predication",
            owner="p",
            member="s",
            role="subject",
            occurrences=["s-loc"],
        )
    ]
    selected = predictions(wire, selected={"unrelated-role"})
    assert (
        score_task(reference(), "construction.predication", selected, output_first=True)[
            "exact_match"
        ]
        is False
    )


def test_semantic_case_wire_is_v3_only_and_excludes_other_expectation_kinds():
    import json

    from evaluation_characterization_assessment_support import case, frame, payload

    from corpus_structure.evaluate.operation_assessment import decode_authored
    from corpus_structure.evaluate.semantic import ReferenceError

    semantic = case(
        alternatives=(),
        candidate_selector={},
        semantic_reference=reference(),
        required_family="construction.predication",
    )
    decoded = decode_authored(json.dumps(payload(frame(), [semantic])).encode(), frame())
    assert decoded["cases"][0].semantic_reference["version"] == "characterization-task-reference-v1"
    with pytest.raises(ReferenceError, match="cannot mix"):
        case(semantic_reference=reference())


def test_conditional_role_assertions_preserve_their_own_choice_prerequisite():
    wire = body(wrapped=False)
    wire["terms"][-1]["required_choices"] = ["a"]
    wire["choices"] = [
        dict(
            local_id="choice",
            family="construction.predication",
            compatibility="exclusive",
            members=[dict(local_id="a", root="p"), dict(local_id="b", root="s")],
        )
    ]
    ref = reference(
        groups=[
            dict(
                id="independent-choice",
                compatibility="exclusive",
                members=[dict(id="yes", root="p"), dict(id="other", root="s")],
            )
        ],
        assertions=[
            dict(subject="p", relation="grammatical_subject", object="s", requires=["yes"])
        ],
    )
    assert score_task(ref, "construction.predication", predictions(wire))["exact_match"] is True
    wire["terms"][-1]["required_choices"] = ["b"]
    assert score_task(ref, "construction.predication", predictions(wire))["exact_match"] is False


def test_explicit_empty_named_slot_never_credits_an_unlocated_implicit_participant():
    ref = reference(assertions=[])
    result = score_task(ref, "construction.predication", predictions(body(unlocated=True)))
    assert result["status"] == "unavailable" and result["exact_match"] is None


def test_context_binding_uses_literal_private_role_and_exact_external_proxy():
    wire = scope_wire()
    wire["annotations"] = [
        dict(
            local_id=identity,
            family="context.binding",
            kind="context.symbolic_site",
            occurrences=[occurrence],
            external_premises=[dict(layer=PIN, local_id=target)],
        )
        for identity, occurrence, target in (
            ("binder-proxy", "quant", "binder-a"),
            ("variable-proxy", "var", "variable-a"),
        )
    ]
    wire["roles"] = [
        dict(
            local_id="binding-role",
            family="context.binding",
            owner="binder-proxy",
            member="variable-proxy",
            role="declared_binding_site",
            scheme="contextual-source-hypotheses-1",
            occurrences=["quant"],
            basis=dict(status="private_proposal"),
        )
    ]
    ref = reference(
        task="binding",
        role_scheme="contextual-source-hypotheses-1",
        focus="binder",
        entities=[entity("binder", "binder", 2, 3), entity("variable", "variable", 4, 4)],
        assertions=[
            dict(
                subject="binder",
                relation="declared_binding_site",
                object="variable",
                standing="private_proposal",
            )
        ],
        complete_slots=[dict(subject="binder", relation="declared_binding_site")],
    )
    assert (
        score_task(ref, "context.binding", predictions(wire, selected={"binding-role"}))[
            "exact_match"
        ]
        is True
    )
    wire["roles"][0]["scheme"] = "subject-is-agent"
    assert (
        score_task(ref, "context.binding", predictions(wire, selected={"binding-role"}))["status"]
        == "unavailable"
    )


def formal_wire(*, swapped=False, variable="x", grouped=False) -> dict[str, Any]:
    terms: list[dict[str, Any]] = [
        dict(
            local_id="x",
            kind="participant",
            family="formal.math",
            value="symbol:" + variable,
            occurrences=["x-loc"],
            children=[],
        ),
        dict(
            local_id="y",
            kind="participant",
            family="formal.math",
            value="symbol:y",
            occurrences=["y-loc"],
            children=[],
        ),
        dict(
            local_id="plus",
            kind="participant",
            family="formal.math",
            value="+",
            occurrences=["plus-loc"],
            children=[],
        ),
        dict(
            local_id="sum",
            kind="operator",
            family="formal.math",
            value="add",
            occurrences=["whole"],
            children=[
                dict(role="left", target="y" if swapped else "x", structural=True, order=0),
                dict(role="cue", target="plus", structural=True, order=1),
                dict(role="right", target="x" if swapped else "y", structural=True, order=2),
            ],
        ),
    ]
    if grouped:
        terms.append(
            dict(
                local_id="identity-wrapper",
                kind="operator",
                family="formal.math",
                value="identity",
                occurrences=["whole"],
                children=[dict(role="content", target="sum", structural=True)],
            )
        )
        terms[-2]["children"][0]["target"] = "x"
    return dict(
        terms=terms,
        choices=[],
        coverage=[],
        occurrences=[
            dict(local_id=identity, extents=[extent(a, b)])
            for identity, a, b in (
                ("x-loc", 0, 1),
                ("plus-loc", 1, 2),
                ("y-loc", 2, 3),
                ("whole", 0, 3),
            )
        ],
    )


def formal_reference():
    return reference(
        task="formal",
        role_scheme="formal-children-v1",
        focus="sum",
        entities=[
            entity("sum", "formal", 0, 3, value="add"),
            entity("x", "formal", 0, 1, value="x"),
            entity("y", "formal", 2, 3, value="y"),
        ],
        assertions=[
            dict(subject="sum", relation="left", object="x", order=0),
            dict(subject="sum", relation="right", object="y", order=2),
        ],
        complete_slots=[dict(subject="sum", relation=role) for role in ("left", "right")],
    )


def test_formal_task_preserves_written_variables_and_ordered_operands():
    ref = formal_reference()
    assert (
        score_task(ref, "formal.math", predictions(formal_wire(grouped=True)))["exact_match"]
        is True
    )
    for kw in (dict(swapped=True), dict(variable="z")):
        assert (
            score_task(ref, "formal.math", predictions(formal_wire(**kw)))["exact_match"] is False
        )
    wire = formal_wire()
    wire["terms"][-1]["value"] = "uninterpreted:unsupported_production"
    assert score_task(ref, "formal.math", predictions(wire))["status"] == "unavailable"


def test_explicit_literal_head_wrappers_are_erased_without_guessing_noun_heads():
    wire = body()
    wire["occurrences"].append(dict(local_id="np-loc", extents=[extent(0, 2)]))
    wire["terms"].extend(
        [
            dict(
                local_id="np",
                kind="participant",
                family="construction.predication",
                value="nominal_modification",
                occurrences=["np-loc"],
                children=[dict(role="head", target="s", structural=True)],
            ),
            dict(
                local_id="written-cue",
                kind="participant",
                family="construction.predication",
                value="not",
                occurrences=["bad-loc"],
                children=[],
            ),
        ]
    )
    wire["terms"][3]["children"][-1]["target"] = "np"
    assert (
        score_task(reference(), "construction.predication", predictions(wire))["exact_match"]
        is True
    )


def test_same_local_labels_still_reject_crossed_joint_readings():
    wire = choice_wire()
    for term in wire["terms"]:
        term["value"] = "negation"
        term["children"] = [
            dict(role="target", target="target-" + term["local_id"], structural=True)
        ]
        term["required_choices"] = ["m" + term["local_id"]]
    for position, identity in enumerate(("a", "b", "c", "d")):
        wire["occurrences"].append(
            dict(local_id="loc-" + identity, extents=[extent(3 + position, 4 + position)])
        )
        wire["terms"].append(
            dict(
                local_id="target-" + identity,
                family="construction.scope",
                kind="predicate",
                value="local-label",
                occurrences=["loc-" + identity],
                children=[],
            )
        )
    ref = choice_reference()
    ref.update(
        task="scope",
        entities=[
            entity(identity, "operator", 1, 2, value="negation")
            for identity in ("a", "b", "c", "d")
        ]
        + [
            entity("target-" + identity, "predicate", 3 + position, 4 + position)
            for position, identity in enumerate(("a", "b", "c", "d"))
        ],
        assertions=[
            dict(
                subject=identity,
                relation="target",
                object="target-" + identity,
                requires=["m" + identity],
            )
            for identity in ("a", "b", "c", "d")
        ],
        complete_slots=[
            dict(subject=identity, relation="target") for identity in ("a", "b", "c", "d")
        ],
    )
    assert score_task(ref, "construction.scope", predictions(wire))["exact_match"] is True
    wire["choices"][0]["members"][0]["required_choices"] = ["md"]
    wire["choices"][0]["members"][1]["required_choices"] = ["mc"]
    assert score_task(ref, "construction.scope", predictions(wire))["exact_match"] is False


def test_literal_source_cue_kind_and_empty_closed_slot_have_explicit_meaning():
    wire = body(wrapped=False)
    wire["terms"][-1]["children"] = []
    ref = reference(entities=[entity("p", "predicate", 2, 5)], assertions=[])
    assert score_task(ref, "construction.predication", predictions(wire))["exact_match"] is True
    wire["terms"][-1].update(
        kind="operator",
        value="negation",
        family="construction.scope",
        children=[dict(role="cue", target="s", structural=True)],
    )
    ref = reference(
        task="scope",
        focus="operator",
        entities=[entity("operator", "operator", 0, 1), entity("cue", "source", 0, 1)],
        assertions=[dict(subject="operator", relation="cue", object="cue")],
        complete_slots=[dict(subject="operator", relation="cue")],
    )
    assert score_task(ref, "construction.scope", predictions(wire))["exact_match"] is True


def test_multi_root_population_shares_exact_witness_nodes_without_merging_roots():
    wire = body()
    projection = LayerProjection(lambda pin: wire)
    refs = [dict(layer=PIN, collection="terms", local_id=identity) for identity in ("p", "s")]
    rows = [projection.project(ref, include_graph=False) for ref in refs]
    shared = projection.graph_many([(PIN, "p"), (PIN, "s")])
    assert len(shared["roots"]) == 2 and shared["roots"][0] != shared["roots"][1]
    identities = [node["qualified_identity"]["local_id"] for node in shared["nodes"]]
    assert identities.count("s") == 1
    for row, root in zip(rows, shared["roots"], strict=True):
        assert "graph" not in row
        row["task_graph"], row["task_graph_root"] = shared, root
    assert score_task(reference(), "construction.predication", rows)["exact_match"] is True


def test_scalar_capture_does_not_build_graphs_it_cannot_consume(monkeypatch):
    from evaluation_characterization_assessment_support import captured_assessment, case

    def forbidden(*args, **kwargs):
        raise AssertionError("scalar case must not build a graph")

    monkeypatch.setattr(LayerProjection, "graph", forbidden)
    monkeypatch.setattr(LayerProjection, "graph_many", forbidden)
    result = captured_assessment(monkeypatch, extents=[dict(EXTENT, end=20)], expected_case=case())
    assert result["cases"][0]["judgment"] == "supported"


def test_object_level_disjunction_uses_literal_connective_not_analytical_groups():
    wire = dict(
        terms=[
            dict(
                local_id="coord",
                family="construction.coordination",
                kind="operator",
                value="coordination",
                occurrences=["whole"],
                children=[
                    dict(role="left", target="left", structural=True),
                    dict(role="connective", target="or", structural=True),
                    dict(role="right", target="right", structural=True),
                ],
            ),
            dict(
                local_id="left",
                family="construction.coordination",
                kind="participant",
                value="x",
                occurrences=["left-loc"],
                children=[],
            ),
            dict(
                local_id="right",
                family="construction.coordination",
                kind="participant",
                value="y",
                occurrences=["right-loc"],
                children=[],
            ),
            dict(
                local_id="or",
                family="construction.coordination",
                kind="participant",
                value="or",
                occurrences=["cue"],
                children=[],
            ),
        ],
        occurrences=[
            dict(local_id=identity, extents=[extent(a, b)])
            for identity, a, b in (
                ("whole", 0, 6),
                ("left-loc", 0, 1),
                ("cue", 2, 4),
                ("right-loc", 5, 6),
            )
        ],
        choices=[],
        coverage=[],
    )
    ref = reference(
        focus="or",
        entities=[
            entity("or", "operator", 2, 4),
            entity("literal", "source", 2, 4),
            entity("left", "participant", 0, 1),
            entity("right", "participant", 5, 6),
        ],
        assertions=[
            dict(subject="or", relation=role, object=target)
            for role, target in (("left", "left"), ("right", "right"), ("connective", "literal"))
        ],
        complete_slots=[
            dict(subject="or", relation=role) for role in ("left", "right", "connective")
        ],
    )
    assert score_task(ref, "construction.coordination", predictions(wire))["exact_match"] is True


def test_expected_unconditional_assertion_rejects_known_conditional_claim():
    wire = body(wrapped=False)
    wire["terms"][-1]["required_choices"] = ["a"]
    wire["choices"] = [
        dict(
            local_id="choice",
            family="construction.predication",
            compatibility="unknown",
            members=[dict(local_id="a", root="p"), dict(local_id="b", root="s")],
        )
    ]
    result = score_task(reference(), "construction.predication", predictions(wire))
    assert result["status"] == "scored" and result["exact_match"] is False
    assert result["differences"][0]["actual_groups"][0]["compatibility"] == "unknown"


@pytest.mark.parametrize("support", ["feasible", "impossible", "unknown", "cyclic"])
def test_positive_witness_requires_explicit_feasible_support(support):
    wire = body(wrapped=False)
    wire["terms"][-1]["required_choices"] = ["a"]
    a: dict[str, Any] = dict(local_id="a", root="p")
    b: dict[str, Any] = dict(local_id="b", root="s")
    if support != "feasible":
        a["required_choices"] = ["b"]
    if support == "cyclic":
        b["required_choices"] = ["a"]
    wire["choices"] = [
        dict(
            local_id="choice",
            family="construction.predication",
            compatibility="exclusive"
            if support in {"feasible", "impossible"}
            else "unknown"
            if support == "unknown"
            else "compatible",
            members=[a, b],
        )
    ]
    result = score_task(
        reference(mode="witness", complete_slots=[]), "construction.predication", predictions(wire)
    )
    if support == "feasible":
        assert result["status"] == "scored" and result["exact_match"] is True
    elif support == "impossible":
        assert result["status"] == "scored" and result["exact_match"] is False
        assert result["differences"][0]["reason"] == "exclusive_conflict"
    else:
        assert result["status"] == "unavailable" and result["exact_match"] is None
        assert result["differences"][0]["reason"] == (
            "cyclic_prerequisite" if support == "cyclic" else "unknown_compatibility"
        )


def test_witness_support_closure_is_distinct_from_exact_joint_selection_queries():
    from corpus_structure.evaluate.task_semantics import witness_support

    groups = [
        dict(id="one", compatibility="exclusive", members=[dict(id="a", root="p", requires=["b"])]),
        dict(id="two", compatibility="exclusive", members=[dict(id="b", root="s")]),
    ]
    assert joint_outcome(groups, ["a"]) == "forbidden"
    assert witness_support(groups, ["a"]) == dict(
        status="feasible", reason=None, members=["a", "b"]
    )
    assert witness_support(groups, ["missing"])["reason"] == "missing_prerequisite"
    assert witness_support(groups[:1], ["a"])["reason"] == "missing_prerequisite"


def test_legitimate_witness_does_not_inherit_unrelated_assertion_failure():
    wire = body(wrapped=False, extra=True)
    wire["terms"].append(
        dict(
            local_id="other-p",
            kind="predicate",
            family="construction.predication",
            value="other",
            occurrences=["bad-loc"],
            children=[dict(role="grammatical_subject", target="bad", structural=True)],
            required_choices=["a"],
        )
    )
    wire["choices"] = [
        dict(
            local_id="choice",
            family="construction.predication",
            compatibility="exclusive",
            members=[
                dict(local_id="a", root="other-p", required_choices=["b"]),
                dict(local_id="b", root="bad"),
            ],
        )
    ]
    result = score_task(
        reference(mode="witness", complete_slots=[]), "construction.predication", predictions(wire)
    )
    assert result["status"] == "scored" and result["exact_match"] is True


@pytest.mark.parametrize("optional", ["order", "standing"])
def test_optional_assertion_constraint_applies_only_to_its_declared_assertion(optional):
    wire = body()
    wire["terms"][-1]["status"] = "interpreted"
    explicit = 0 if optional == "order" else "interpreted"
    ref = reference(
        entities=[
            entity("p", "predicate", 2, 5),
            entity("s", "participant", 0, 1),
            entity("head", "participant", 2, 5),
        ],
        assertions=[
            dict(subject="p", relation="grammatical_subject", object="s", **{optional: explicit}),
            dict(subject="p", relation="predicate", object="head"),
        ],
        complete_slots=[
            dict(subject="p", relation=role) for role in ("grammatical_subject", "predicate")
        ],
    )
    assert score_task(ref, "construction.predication", predictions(wire))["exact_match"] is True
    ref["assertions"][0][optional] = 8 if optional == "order" else "private_proposal"
    assert score_task(ref, "construction.predication", predictions(wire))["exact_match"] is False


def test_optional_semantic_value_constrains_only_the_entity_declaring_it():
    wire = dict(
        terms=[
            dict(
                local_id="outer",
                family="construction.scope",
                kind="operator",
                value="negation",
                occurrences=["outer-loc"],
                children=[dict(role="target", target="inner", structural=True)],
            ),
            dict(
                local_id="inner",
                family="construction.scope",
                kind="operator",
                value="modality:possibility",
                occurrences=["inner-loc"],
                children=[dict(role="target", target="body", structural=True)],
            ),
            dict(
                local_id="body",
                family="construction.scope",
                kind="predicate",
                value="body-name",
                occurrences=["body-loc"],
                children=[],
            ),
        ],
        occurrences=[
            dict(local_id=identity, extents=[extent(a, b)])
            for identity, a, b in (("outer-loc", 0, 1), ("inner-loc", 2, 3), ("body-loc", 4, 7))
        ],
        choices=[],
        coverage=[],
    )
    ref = reference(
        task="scope",
        focus="outer",
        entities=[
            entity("outer", "operator", 0, 1, value="negation"),
            entity("inner", "operator", 2, 3),
            entity("body", "predicate", 4, 7),
        ],
        assertions=[
            dict(subject="outer", relation="target", object="inner"),
            dict(subject="inner", relation="target", object="body"),
        ],
        complete_slots=[
            dict(subject=identity, relation="target") for identity in ("outer", "inner")
        ],
    )
    assert score_task(ref, "construction.scope", predictions(wire))["exact_match"] is True
    ref["entities"][1]["value"] = "modality:permission"
    assert score_task(ref, "construction.scope", predictions(wire))["exact_match"] is False


@pytest.mark.parametrize("exact", [True, False])
def test_formal_task_honors_retained_input_correspondence_precision(exact):
    wire = formal_wire()
    original = "x+y"
    for occurrence in wire["occurrences"]:
        for located in occurrence["extents"]:
            located.update(text=original[located["start"] : located["end"]], synthetic=False)
    wire["annotations"] = [
        dict(
            local_id="input",
            kind="formal.input",
            family="formal.math",
            occurrences=["whole"],
            formal_input=dict(
                representation="source_text" if exact else "recognized_latex",
                text=original,
                correspondence=[
                    dict(
                        input_start=0,
                        input_end=3,
                        relation="exact" if exact else "contained_in_atom",
                        source_occurrences=["whole"],
                    )
                ],
            ),
        )
    ]
    by_occurrence = {row["local_id"]: row for row in wire["occurrences"]}
    for term in wire["terms"]:
        source_extent = by_occurrence[term["occurrences"][0]]["extents"][0]
        syntax_id = "syntax-" + term["local_id"]
        term["premises"] = [syntax_id]
        wire["annotations"].append(
            dict(
                local_id=syntax_id,
                kind="formal.rule",
                family="formal.math",
                occurrences=term["occurrences"] if exact else ["whole"],
                formal=dict(
                    input_id="input",
                    node_kind="rule",
                    rule="public-synthetic-rule",
                    start=source_extent["start"],
                    end=source_extent["end"],
                ),
            )
        )
        if not exact:
            term["occurrences"] = ["whole"]
    result = score_task(formal_reference(), "formal.math", predictions(wire))
    if exact:
        assert result["status"] == "scored" and result["exact_match"] is True
    else:
        assert result["status"] == "unavailable" and result["exact_match"] is None
        assert "exact original-source correspondence" in result["reason"]


def test_witness_result_declares_existential_scope_and_actual_support_conditions():
    wire = body(wrapped=False)
    wire["terms"][-1]["required_choices"] = ["a"]
    wire["choices"] = [
        dict(
            local_id="g",
            family="construction.predication",
            compatibility="exclusive",
            members=[dict(local_id="a", root="p")],
        )
    ]
    result = score_task(
        reference(mode="witness", complete_slots=[]), "construction.predication", predictions(wire)
    )
    assert result["exact_match"] is True
    assert result["match_scope"]["unconditionality"] == "not_asserted"
    assert (
        result["match_scope"]["interpretation"]
        == "positive_existence_under_explicit_feasible_support"
    )
    assert result["support_conditions"]["status"] == "feasible"
    assert result["support_conditions"]["members"]


def test_unknown_positive_support_remains_unassessed_in_case_grading():
    from evaluation_characterization_assessment_support import case, coverage, frame

    from corpus_structure.evaluate.characterization_assessment import score_characterization

    wire = body(wrapped=False)
    wire["terms"][-1]["required_choices"] = ["a"]
    wire["choices"] = [
        dict(
            local_id="choice",
            family="construction.predication",
            compatibility="unknown",
            members=[
                dict(local_id="a", root="p", required_choices=["b"]),
                dict(local_id="b", root="s"),
            ],
        )
    ]
    authored = case(
        alternatives=(),
        candidate_selector={},
        required_family="construction.predication",
        semantic_reference=reference(mode="witness", complete_slots=[]),
    )
    result = score_characterization(
        frame(),
        (authored,),
        predictions(wire),
        coverage=(dict(coverage(), family="construction.predication"),),
    )
    graded = result["cases"][0]
    assert (
        graded["judgment"] == "unassessed" and graded["error_category"] == "witness_support_unknown"
    )
    assert graded["semantic_metrics"]["exact_match"] is None


def test_output_first_choice_cannot_substitute_correct_unselected_witness_group():
    wire = choice_wire()
    for identity, value in (("c", "modality:possibility"), ("d", "modality:permission")):
        next(term for term in wire["terms"] if term["local_id"] == identity)["value"] = value
    wire["choices"][0]["compatibility"] = "unknown"
    wire["choices"][0]["members"][0]["required_choices"] = ["mc"]
    wire["choices"][0]["members"][1].pop("required_choices", None)
    ref = reference(
        task="choices",
        mode="witness",
        complete_slots=[],
        assertions=[],
        focus="a",
        entities=[
            entity("a", "operator", 1, 2, value="modality:possibility"),
            entity("b", "operator", 1, 2, value="modality:permission"),
        ],
        groups=[
            dict(
                id="expected-group",
                compatibility="exclusive",
                members=[dict(id="expected-a", root="a"), dict(id="expected-b", root="b")],
            )
        ],
    )

    def selected(group):
        projection = LayerProjection(lambda pin: wire)
        row = projection.project(
            dict(layer=PIN, collection="choices", local_id=group), include_graph=False
        )
        graph = projection.graph_many([(PIN, group)], witness_closure=True)
        row["task_graph"], row["task_graph_root"] = graph, graph["roots"][0]
        return [row]

    # The frozen unknown group cannot borrow the correct exclusive group reached
    # only through its prerequisite witness, even at identical source anchors.
    result = score_task(ref, "construction.scope", selected("first"), output_first=True)
    assert result["status"] == "scored" and result["exact_match"] is False
    assert result["differences"][0]["kind"] == "frozen_choice_group_not_matched"
    assert result["match_scope"]["assessed_choice_groups"][0]["local_id"] == "first"
    assert (
        score_task(ref, "construction.scope", selected("second"), output_first=True)["exact_match"]
        is True
    )
    # Source-first witness semantics still asks whether the relevant population
    # contains a supported positive characterization, rather than a selected ID.
    assert score_task(ref, "construction.scope", selected("first"))["exact_match"] is True


def candidate_question_wire(
    task: str = "host_choice", *, state: str = "proposed", compatible: bool = False
) -> dict[str, Any]:
    family = "character_host_choice_v1" if task == "host_choice" else "character_referent_choice_v1"
    question = "host" if task == "host_choice" else "referent"

    def description(identity: str, start: int, end: int) -> dict[str, Any]:
        return dict(
            reference=dict(layer=PIN, local_id=identity),
            source_members=[extent(start, end)],
            required_external_choices=[],
        )

    focus = description("focal", 0, 2)
    members = [description("endpoint", 3, 6)]
    if compatible:
        members.append(description("second", 7, 9))
    frozen = dict(
        focus=focus,
        alternatives=[
            dict(
                key="offered-1",
                members=members,
                compatibility="compatible" if compatible else "exclusive",
            )
        ],
    )
    return dict(
        annotations=[
            dict(
                local_id=identity,
                kind="native.mention",
                occurrences=[identity + "-loc"],
                family="context.reference",
            )
            for identity in ("focal", "endpoint", "second")
        ]
        + [
            dict(
                local_id="question",
                kind="model.question",
                family=family,
                occurrences=["focal-loc"],
                external_premises=[
                    dict(layer=PIN, local_id=identity)
                    for identity in ("focal", "endpoint", "second")
                ],
                model_answer=dict(
                    family=family,
                    question_key=question,
                    answer_kind="choice",
                    state=state,
                    selected_keys=["offered-1"] if state == "proposed" else [],
                    native_answer=dict(request=dict(interpretation=dict(frozen_candidates=frozen))),
                ),
            )
        ],
        occurrences=[
            dict(local_id=identity + "-loc", extents=[extent(a, b)])
            for identity, a, b in (("focal", 0, 2), ("endpoint", 3, 6), ("second", 7, 9))
        ],
        coverage=[],
    )


def candidate_question_reference(
    task: str = "host_choice", *, state: str = "proposed", compatible: bool = False
) -> dict[str, Any]:
    role = "host" if task == "host_choice" else "referent"
    endpoints = [entity("target", "source", 3, 6)] if state == "proposed" else []
    if compatible and state == "proposed":
        endpoints.append(entity("second", "source", 7, 9))
    return reference(
        task=task,
        role_scheme="model-question-source-v1",
        focus="question",
        entities=[
            entity("question", "operator", 0, 2, value=task + ":" + state),
            entity("focus", "source", 0, 2),
            *endpoints,
        ],
        assertions=[
            dict(subject="question", relation="focus", object="focus", standing="private_proposal"),
            *(
                dict(subject="question", relation=role, object=e["id"], standing="private_proposal")
                for e in endpoints
            ),
        ],
        complete_slots=[dict(subject="question", relation=r) for r in ("focus", role)],
    )


def candidate_predictions(wire: dict[str, Any], **kwargs):
    from corpus_structure.semantic.observations import source_value

    retained = deepcopy(wire)
    for node in retained["annotations"]:
        if "native_answer" in node.get("model_answer", {}):
            node["model_answer"]["native_answer"] = source_value(
                node["model_answer"]["native_answer"]
            )
    return predictions(retained, **kwargs)


@pytest.mark.parametrize("task", ["host_choice", "referent_choice"])
def test_candidate_question_task_resolves_frozen_exact_source_endpoints(task):
    wire = candidate_question_wire(task)
    family = wire["annotations"][-1]["family"]
    result = score_task(candidate_question_reference(task), family, candidate_predictions(wire))
    assert result["status"] == "scored" and result["exact_match"] is True
    wrong = candidate_question_reference(task)
    wrong["entities"][-1]["extents"] = [extent(7, 9)]
    assert score_task(wrong, family, candidate_predictions(wire))["exact_match"] is False
    assert (
        score_task(
            candidate_question_reference(task),
            family,
            candidate_predictions(wire, selected=["question"]),
            output_first=True,
        )["exact_match"]
        is True
    )
    assert (
        score_task(
            candidate_question_reference(task),
            family,
            candidate_predictions(wire, selected=["endpoint"]),
            output_first=True,
        )["exact_match"]
        is False
    )


@pytest.mark.parametrize(
    "state", ["no_match", "missing_candidate", "insufficient_evidence", "withheld"]
)
def test_candidate_question_nonpositive_states_remain_distinct_without_invented_edges(state):
    wire = candidate_question_wire(state=state)
    family = wire["annotations"][-1]["family"]
    assert (
        score_task(candidate_question_reference(state=state), family, candidate_predictions(wire))[
            "exact_match"
        ]
        is True
    )
    assert (
        score_task(
            candidate_question_reference(state="proposed"), family, candidate_predictions(wire)
        )["exact_match"]
        is False
    )


def test_candidate_question_compatible_host_set_keeps_every_member():
    wire = candidate_question_wire(compatible=True)
    family = wire["annotations"][-1]["family"]
    assert (
        score_task(
            candidate_question_reference(compatible=True), family, candidate_predictions(wire)
        )["exact_match"]
        is True
    )
    assert (
        score_task(candidate_question_reference(), family, candidate_predictions(wire))[
            "exact_match"
        ]
        is False
    )


@pytest.mark.parametrize(
    "mutation",
    ["unoffered", "wrong_source", "wrong_identity", "incompatible", "duplicate", "missing_choice"],
)
def test_candidate_question_refuses_unbound_or_undeclared_frozen_population(mutation):
    wire = candidate_question_wire(compatible=True)
    answer = wire["annotations"][-1]["model_answer"]
    frozen = answer["native_answer"]["request"]["interpretation"]["frozen_candidates"]
    offered = frozen["alternatives"][0]
    if mutation == "unoffered":
        answer["selected_keys"] = ["not-offered"]
    elif mutation == "wrong_source":
        offered["members"][0]["source_members"][0]["source_view_id"] = 99
    elif mutation == "wrong_identity":
        offered["members"][0]["reference"]["layer"] = dict(PIN, task_id=88)
    elif mutation == "incompatible":
        offered["compatibility"] = "exclusive"
    elif mutation == "missing_choice":
        offered["members"][0]["required_external_choices"] = [
            dict(layer=PIN, local_id="unretained-choice")
        ]
    else:
        offered["members"].append(deepcopy(offered["members"][0]))
    result = score_task(
        candidate_question_reference(compatible=True),
        "character_host_choice_v1",
        candidate_predictions(wire),
    )
    assert result["status"] == "unavailable"


@pytest.mark.parametrize("state", ["failed", "dependency_unresolved"])
def test_candidate_question_unavailable_scope_does_not_poison_other_foci(state):
    wire = candidate_question_wire()
    failed = deepcopy(wire["annotations"][-1])
    failed.update(local_id="failed-question", occurrences=["other-loc"], external_premises=[])
    failed["model_answer"].update(state=state, selected_keys=[])
    failed["model_answer"].pop("native_answer")
    wire["annotations"].append(failed)
    wire["occurrences"].append(dict(local_id="other-loc", extents=[extent(15, 20)]))
    assert (
        score_task(
            candidate_question_reference(), "character_host_choice_v1", candidate_predictions(wire)
        )["exact_match"]
        is True
    )
    failed["occurrences"] = ["focal-loc"]
    assert (
        score_task(
            candidate_question_reference(), "character_host_choice_v1", candidate_predictions(wire)
        )["status"]
        == "unavailable"
    )
    wire["annotations"] = [row for row in wire["annotations"] if row["local_id"] != "question"]
    failed["occurrences"] = ["other-loc"]
    result = score_task(
        candidate_question_reference(), "character_host_choice_v1", candidate_predictions(wire)
    )
    assert result["status"] == "scored" and result["exact_match"] is False


def test_candidate_choice_prerequisite_preserves_full_term_root_not_normalized_head():
    wire = candidate_question_wire()
    # The offered endpoint is an entire retained predicate term; its lexical head
    # is narrower. Choice roots and selected endpoints must use the same exact one.
    wire["annotations"] = [row for row in wire["annotations"] if row["local_id"] != "endpoint"]
    wire["terms"] = [
        dict(
            local_id="endpoint",
            family="construction.predication",
            kind="predicate",
            occurrences=["endpoint-loc"],
            children=[dict(role="predicate", target="head", structural=True)],
        ),
        dict(
            local_id="head",
            family="construction.predication",
            kind="participant",
            occurrences=["head-loc"],
            children=[],
        ),
    ]
    wire["occurrences"].append(dict(local_id="head-loc", extents=[extent(4, 5)]))
    wire["choices"] = [
        dict(
            local_id="host-choice",
            family="construction.predication",
            compatibility="exclusive",
            members=[dict(local_id="host-member", root="endpoint")],
        )
    ]
    question = wire["annotations"][-1]
    question["external_premises"].append(dict(layer=PIN, local_id="host-member"))
    frozen = question["model_answer"]["native_answer"]["request"]["interpretation"][
        "frozen_candidates"
    ]
    frozen["alternatives"][0]["members"][0]["required_external_choices"] = [
        dict(layer=PIN, local_id="host-member")
    ]
    ref = candidate_question_reference()
    ref["groups"] = [
        dict(
            id="selected-host",
            compatibility="exclusive",
            members=[dict(id="one-host", root="target")],
        )
    ]
    ref["assertions"][-1]["requires"] = ["one-host"]
    result = score_task(ref, "character_host_choice_v1", candidate_predictions(wire))
    assert result["status"] == "scored" and result["exact_match"] is True
    ref["entities"][-1]["extents"] = [extent(4, 5)]
    assert (
        score_task(ref, "character_host_choice_v1", candidate_predictions(wire))["exact_match"]
        is False
    )
