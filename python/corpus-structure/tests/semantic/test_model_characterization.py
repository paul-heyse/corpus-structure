"""Bounded model questions preserve their actual source, choices and event meanings."""

import json
from dataclasses import asdict, replace

import pytest

from corpus_structure.methods.model_observation import (
    installed_policy,
)
from corpus_structure.methods.pm2_gliner_classification import (
    classification_product,
    classification_request,
)
from corpus_structure.semantic.characterization import (
    decode_layer,
    encode_layer,
)
from corpus_structure.semantic.interpretation_questions import (
    CHARACTERIZATION_FAMILIES,
    CHARACTERIZATION_QUESTION_INPUT,
    QuestionFamily,
    characterization_question_dependencies,
    compile_question_families,
    declared_families,
)
from corpus_structure.semantic.model_characterization import (
    GLINER_CUES,
    GLINER_FUNCTIONS,
    compile_question_stage,
    contextual_candidate_populations,
    freeze_candidates,
    gliner_cue_request,
    project_gliner_cues,
)
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.types import ResolvedDependencies
from semantic.model_characterization_support import (
    builder as builder,
)
from semantic.model_characterization_support import (
    d1_reply as d1_reply,
)
from semantic.model_characterization_support import (
    gliner_profile as gliner_profile,
)
from semantic.model_characterization_support import (
    gliner_report as gliner_report,
)
from semantic.model_characterization_support import (
    mark_other_families_complete as mark_other_families_complete,
)
from semantic.model_characterization_support import (
    prepared as prepared,
)
from semantic.model_characterization_support import (
    scope as scope,
)


@pytest.fixture(scope="module")
def declarations():
    dependencies = characterization_question_dependencies(ResolvedDependencies())
    return declared_families(compile_question_families(dependencies.artifacts))


def read_answer(start=0, end=3):
    return dict(type="text", found=0.91, source_span=(start, end))


def test_eight_new_declarations_use_existing_archived_custody_and_preserve_old_serialization(
    declarations,
):
    assert (
        tuple(name for name in CHARACTERIZATION_FAMILIES if name in declarations)
        == CHARACTERIZATION_FAMILIES
    )
    dependencies = characterization_question_dependencies(ResolvedDependencies())
    assert characterization_question_dependencies(dependencies) is dependencies
    assert dependencies.artifacts[0].name == CHARACTERIZATION_QUESTION_INPUT
    with pytest.raises(ValueError, match="competing"):
        characterization_question_dependencies(dependencies, content=b"[]")
    old = QuestionFamily.model_validate_json(
        json.dumps(
            dict(
                family="literal_completion_v1",
                questions=[dict(key="literal", kind="text", instructions="Read source.")],
            )
        )
    )
    data = old.model_dump(mode="json")
    assert not {"provider", "renderer", "context_policy"} & data.keys()
    assert not {"stage", "depends_on", "projection_role"} & data["questions"][0].keys()


def test_source_first_state_needs_no_candidates_and_retains_focal_and_examined_scopes(declarations):
    selected = scope("They may leave.", focal=(5, 14))
    for name in CHARACTERIZATION_FAMILIES[:4]:
        request = compile_question_stage(declarations[name], selected, 0)
        assert "candidates" not in request.payload["state"]
        assert request.payload["state"]["focal"] == dict(start=5, end=14)
        assert request.payload["interpretation"]["assessed_scope"]["projection_extent"] == [0, 15]
    with pytest.raises(ValueError, match="independent"):
        compile_question_stage(declarations["character_host_choice_v1"], selected, 0)


def test_stages_are_acyclic_and_missing_prerequisites_do_not_become_scope_graphs(declarations):
    family = declarations["character_scope_v1"]
    with pytest.raises(ValueError, match="prerequisites"):
        compile_question_stage(family, scope(), 2)
    invalid = family.model_dump(mode="json")
    invalid["questions"][0]["depends_on"] = ["relative_scope"]
    with pytest.raises(ValueError, match="earlier"):
        QuestionFamily.model_validate_json(json.dumps(invalid))
    assert {option.key for option in family.questions[-1].options} >= {
        "negative_over_quantifier",
        "quantifier_over_negative",
        "insufficient",
    }


def test_repeated_literal_maps_the_returned_second_occurrence_and_preserves_probability_event(
    prepared, declarations
):
    selected = scope()
    output = builder(selected)
    request = compile_question_stage(declarations["character_modal_force_v1"], selected, 0)
    result = output.d1(
        request,
        d1_reply(request, dict(modal_cue=read_answer(4, 7))),
        runtime=dict(provider="fixture-d1", calibration="fixture-calibration"),
    )
    question = next(
        annotation for annotation in output.annotations if annotation["kind"] == "model.question"
    )
    proposal = next(
        annotation
        for annotation in output.annotations
        if annotation["kind"] == "model.span_proposal"
    )
    occurrence = output.occurrences[proposal["occurrences"][0]]["extents"][0]
    assert (occurrence["start"], occurrence["end"], occurrence["text"]) == (4, 7, "may")
    assert question["scores"][0]["meaning"] == "native span extraction presence"
    assert source_python(question["scores"][0]["value"]) == 0.91
    assert result["modal_cue"]["text"] == "may"
    assert (
        source_python(question["model_answer"]["native_answer"])["runtime"]["calibration"]
        == "fixture-calibration"
    )
    mark_other_families_complete(output, selected)
    retained = output.finish(prepared)
    restored = decode_layer(prepared, encode_layer(retained))
    assert any(
        extent["start"] == 4 and extent["end"] == 7
        for occurrence in restored.payload["occurrences"]
        for extent in occurrence["extents"]
    )
    assert not restored.payload["terms"]  # Bounded span reads are not a complete logical graph.


def test_copy_from_prior_answer_field_never_becomes_literal_source(declarations):
    selected = scope()
    output = builder(selected)
    family = declarations["character_modal_force_v1"]
    first = compile_question_stage(family, selected, 0)
    prior = output.d1(first, d1_reply(first, dict(modal_cue=read_answer())), runtime={})
    second = compile_question_stage(family, selected, 1, prior=prior)
    reply = d1_reply(second, dict(modal_target=read_answer()))
    rendered = reply["rendered_state"]
    copied = rendered.index('"text":"may"') + len('"text":"')
    reply["native"]["answers"]["modal_target"].update(
        span=[copied, copied + 3], path="/prior_answers/modal_cue/text"
    )
    output.d1(second, reply, runtime={})
    target = next(
        annotation
        for annotation in output.annotations
        if annotation.get("model_answer", {}).get("question_key") == "modal_target"
    )
    assert target["model_answer"]["state"] == "unsupported"
    assert target["model_answer"]["diagnostic"]["category"] == "invalid_rendered_source_field"
    assert not any(
        annotation["kind"] == "model.span_proposal"
        and target["local_id"] in annotation.get("premises", ())
        for annotation in output.annotations
    )


def test_focal_cue_read_cannot_steal_a_literal_from_examined_context(declarations):
    selected = scope("may may", focal=(4, 7))
    output = builder(selected)
    request = compile_question_stage(declarations["character_modal_force_v1"], selected, 0)
    output.d1(request, d1_reply(request, dict(modal_cue=read_answer(0, 3))), runtime={})
    question = next(
        annotation for annotation in output.annotations if annotation["kind"] == "model.question"
    )
    assert question["model_answer"]["state"] == "unsupported"
    assert not any(annotation["kind"] == "model.span_proposal" for annotation in output.annotations)


def upstream(prepared, selected):
    result = builder(selected)
    result.families = ("context.host", "context.reference")
    result.operation["produced_families"] = list(result.families)
    result.covered = {family: [] for family in result.families}
    for key, start, end in (("focus", 0, 1), ("B", 2, 3), ("C", 4, 5)):
        occurrence = result.occurrence(selected.view, start, end)
        result.annotations.append(
            dict(
                local_id=key,
                kind="native.mention",
                vocabulary="fixture-mention",
                occurrences=[occurrence],
                status="native_evidence",
                family="context.reference",
            )
        )
    for family in result.families:
        result.record(
            family, [dict(projection=selected.view.ref.projection_digest, start=0, end=5)]
        )
    layer = result.finish(prepared)
    return layer.reference(12), layer


@pytest.mark.parametrize(
    ("choice", "expected"),
    [
        ("no_referent", "no_match"),
        ("missing_referent", "missing_candidate"),
        ("insufficient", "insufficient_evidence"),
    ],
)
def test_candidate_decisions_keep_none_missing_and_unknown_distinct(
    prepared, declarations, choice, expected
):
    selected = scope("A B C")
    pin, layer = upstream(prepared, selected)

    def ref(key):
        return dict(layer=pin.values(), local_id=key)

    family = declarations["character_referent_choice_v1"]
    candidates = freeze_candidates(
        family,
        selected,
        {pin: layer},
        focus=ref("focus"),
        alternatives=[
            dict(key="actual_B", members=[ref("B")]),
            dict(key="actual_C", members=[ref("C")]),
        ],
    )
    request = compile_question_stage(family, selected, 0, candidates=candidates)
    offered = request.payload["questions"]["referent"]["criteria"]
    reply = d1_reply(
        request,
        dict(
            referent=dict(
                type="choice",
                choice=choice,
                confidence=0.9,
                probabilities={key: 0.9 if key == choice else 0.025 for key in offered},
            )
        ),
    )
    output = builder(selected)
    output.d1(request, reply, runtime={})
    question = next(
        annotation for annotation in output.annotations if annotation["kind"] == "model.question"
    )
    assert question["model_answer"]["state"] == expected
    assert question["model_answer"]["selected_keys"] == []
    assert question["model_answer"]["candidate_list_digest"] == candidates.digest
    assert not output.roles
    assert [alternative["key"] for alternative in candidates.payload["alternatives"]] == [
        "actual_B",
        "actual_C",
    ]


def test_selected_referent_uses_exact_qualified_endpoint_not_provider_alias(prepared, declarations):
    selected = scope("A B C")
    pin, layer = upstream(prepared, selected)

    def ref(key):
        return dict(layer=pin.values(), local_id=key)

    family = declarations["character_referent_choice_v1"]
    candidates = freeze_candidates(
        family,
        selected,
        {pin: layer},
        focus=ref("focus"),
        alternatives=[dict(key="actual_B", members=[ref("B")])],
    )
    request = compile_question_stage(family, selected, 0, candidates=candidates)
    offered = request.payload["questions"]["referent"]["criteria"]
    alias = next(key for key in offered if key.startswith("option_"))
    reply = d1_reply(
        request,
        dict(
            referent=dict(
                type="choice",
                choice=alias,
                confidence=0.9,
                probabilities={key: 0.9 if key == alias else 0.03 for key in offered},
            )
        ),
    )
    output = builder(selected)
    output.d1(request, reply, runtime={})
    question = next(
        annotation for annotation in output.annotations if annotation["kind"] == "model.question"
    )
    assert question["model_answer"]["selected_keys"] == ["actual_B"]
    proposal = next(
        annotation
        for annotation in output.annotations
        if annotation["kind"] == "model.choice_proposal"
    )
    assert proposal["native_label"] == "actual_B"
    (role,) = output.roles
    endpoints = {annotation["local_id"]: annotation for annotation in output.annotations}
    assert endpoints[role["owner"]]["kind"] == "model.focus"
    assert endpoints[role["member"]]["kind"] == "model.candidate"
    assert endpoints[role["member"]]["external_premises"] == [ref("B")]
    assert role["role"] == "unresolved_referent"
    assert role["basis"]["status"] == "private_proposal"
    assert set(role["basis"]["premises"]) == {question["local_id"], proposal["local_id"]}
    mark_other_families_complete(output, selected)
    assert output.finish(prepared, dependencies={pin: layer}).payload["roles"]
    bad = dict(reply)
    bad["native"] = dict(
        answers=dict(
            referent=dict(
                type="choice", choice="never_offered", probabilities={key: 0.1 for key in offered}
            )
        )
    )
    with pytest.raises(ValueError, match="unoffered"):
        builder(selected).d1(request, bad, runtime={})


def test_missing_contextual_inventory_is_not_completed_empty(declarations):
    populations, complete = contextual_candidate_populations(
        declarations["character_referent_choice_v1"], scope(), {}
    )
    assert populations == () and complete is False


def test_rival_hypotheses_keep_selected_alternative_choice_requirements(prepared, declarations):
    from corpus_structure.semantic.characterization import validate_layer

    selected = scope("A B C")
    _pin, source = upstream(prepared, selected)
    body = source.payload
    occurrence = body["annotations"][0]["occurrences"]
    body["terms"] = [
        dict(
            local_id=key,
            kind="predicate",
            vocabulary="fixture",
            value=key,
            status="unknown",
            family="context.reference",
            occurrences=occurrence,
        )
        for key in ("left", "right")
    ]
    body["choices"] = [
        dict(
            local_id="rivals",
            compatibility="exclusive",
            family="context.reference",
            members=[dict(local_id="select-" + key, root=key) for key in ("left", "right")],
        )
    ]
    for candidate, branch in (("B", "left"), ("C", "right")):
        hypothesis = "hypothesis-" + candidate
        body["annotations"].append(
            dict(
                local_id=hypothesis,
                kind="contextual.referent_hypothesis",
                vocabulary="fixture",
                status="private_proposal",
                family="context.reference",
                occurrences=occurrence,
            )
        )
        body["roles"].append(
            dict(
                local_id="role-" + candidate,
                owner="focus",
                member=candidate,
                role="source_local_coreference_candidate",
                scheme="fixture",
                family="context.reference",
                occurrences=occurrence,
                required_choices=["select-" + branch],
                basis=dict(
                    kind="contextual_proposal", status="private_proposal", premises=[hypothesis]
                ),
            )
        )
    source = validate_layer(prepared, body)
    pin = source.reference(12)
    family = declarations["character_referent_choice_v1"]
    populations, complete = contextual_candidate_populations(family, selected, {pin: source})
    (frozen,) = populations
    assert complete
    alternatives = frozen.payload["alternatives"]
    assert not frozen.payload["focus"]["required_external_choices"]
    assert [
        [
            row["local_id"]
            for row in alternative["hypothesis_supports"][0]["required_external_choices"]
        ]
        for alternative in alternatives
    ] == [["select-left"], ["select-right"]]
    request = compile_question_stage(family, selected, 0, candidates=frozen)
    assert request.payload["interpretation"]["frozen_candidates"] == frozen.payload
    offered = request.payload["questions"]["referent"]["criteria"]
    alias = next(key for key in offered if key.startswith("option_"))
    reply = d1_reply(
        request,
        dict(
            referent=dict(
                type="choice",
                choice=alias,
                confidence=0.9,
                probabilities={key: 0.9 if key == alias else 0.03 for key in offered},
            )
        ),
    )
    output = builder(selected)
    output.d1(request, reply, runtime={})
    (role,) = output.roles
    assert role["required_external_choices"] == [dict(layer=pin.values(), local_id="select-left")]
    assert dict(layer=pin.values(), local_id="role-B") in role["basis"]["external_premises"]
    assert dict(layer=pin.values(), local_id="role-C") not in role["basis"]["external_premises"]
    mark_other_families_complete(output, selected)
    output.finish(prepared, dependencies={pin: source})


def test_compatible_hosts_are_one_explicit_offered_set_and_wrong_source_refuses(
    prepared, declarations
):
    from corpus_structure.semantic.characterization import validate_layer

    selected = scope("A B C")
    _pin, layer = upstream(prepared, selected)
    body = layer.payload
    occurrences = [annotation["occurrences"] for annotation in body["annotations"]]
    body["terms"] = [
        dict(
            local_id=key,
            family="context.host",
            kind=kind,
            vocabulary="fixture-constructions",
            value=key,
            status="interpreted",
            occurrences=members,
        )
        for key, kind, members in (
            ("qualifier", "operator", occurrences[0]),
            ("host_B", "predicate", occurrences[1]),
            ("host_C", "predicate", occurrences[2]),
        )
    ]
    next(row for row in body["coverage"] if row["family"] == "context.host")["outcome"] = "complete"
    layer = validate_layer(prepared, body)
    pin = layer.reference(12)

    def ref(key):
        return dict(layer=pin.values(), local_id=key)

    family = declarations["character_host_choice_v1"]
    alternatives = [dict(key="shared_hosts", members=[ref("host_B"), ref("host_C")])]
    with pytest.raises(ValueError, match="compatible"):
        freeze_candidates(
            family, selected, {pin: layer}, focus=ref("qualifier"), alternatives=alternatives
        )
    alternatives[0]["compatibility"] = "compatible"
    frozen = freeze_candidates(
        family, selected, {pin: layer}, focus=ref("qualifier"), alternatives=alternatives
    )
    assert len(frozen.payload["alternatives"]) == 1
    assert [
        member["reference"]["local_id"] for member in frozen.payload["alternatives"][0]["members"]
    ] == ["host_B", "host_C"]
    wrong = scope("A B C")
    wrong = replace(
        wrong, view=replace(wrong.view, ref=replace(wrong.view.ref, projection_digest="e" * 64))
    )
    with pytest.raises(ValueError, match="examined"):
        freeze_candidates(
            family, wrong, {pin: layer}, focus=ref("qualifier"), alternatives=alternatives
        )


def test_gliner_overlapping_literal_cues_keep_repeated_occurrences_and_observability(
    prepared, declarations
):
    selected = scope()
    family, profile = declarations[GLINER_CUES], gliner_profile()
    pack, item = gliner_cue_request(prepared.release_id, family, selected)
    raw = dict(entities={question.key: [] for question in family.questions})
    raw["entities"]["modal_cue"] = [
        dict(text="may", start=0, end=3, confidence=0.8),
        dict(text="may", start=4, end=7, confidence=0.85),
    ]
    raw["entities"]["term"] = [dict(text="may", start=0, end=3, confidence=0.6)]
    native = gliner_report(pack, item, profile.profile, raw)
    output = builder(selected)
    project_gliner_cues(
        output,
        family,
        selected,
        pack,
        item,
        native,
        profile.profile,
        installed_policy()[0]["inference"],
        threshold=0.5,
    )
    modal = [
        annotation
        for annotation in output.annotations
        if annotation["kind"] == "model.span_proposal" and annotation["native_label"] == "modal_cue"
    ]
    assert [
        (
            output.occurrences[annotation["occurrences"][0]]["extents"][0]["start"],
            output.occurrences[annotation["occurrences"][0]]["extents"][0]["end"],
        )
        for annotation in modal
    ] == [(0, 3), (4, 7)]
    assert all(annotation["status"] == "private_proposal" for annotation in modal)
    event = next(
        annotation for annotation in output.annotations if annotation["kind"] == "model.question"
    )
    assert source_python(event["model_answer"]["native_answer"])["report"]["diagnostics"][0] == [
        "proposal_pool",
        "unavailable",
    ]


def test_gliner_passage_category_never_supplies_literal_witness(prepared, declarations):
    from corpus_structure.methods.gliner import GlinerInput, GlinerPack

    selected, profile = scope(), gliner_profile()
    family = declarations[GLINER_FUNCTIONS]
    request = classification_request(
        prepared.release_id,
        family,
        "functions",
        selected.mapping,
        profile,
        installed_policy()[0]["inference"],
        characterization_family=family.family,
    )
    pack, item = GlinerPack(**request["pack"]), GlinerInput(**request["item"])
    native = gliner_report(
        pack,
        item,
        profile.profile,
        dict(functions=[dict(label="assertion", confidence=0.8)]),
        overlap="flat",
    )
    product = classification_product(request, asdict(native), profile)
    output = builder(selected)
    output.classification(family, selected, request, product, native)
    assert not any(annotation["kind"] == "model.span_proposal" for annotation in output.annotations)
    assert next(
        annotation for annotation in output.annotations if annotation["kind"] == "model.question"
    )["model_answer"]["selected_keys"] == ["assertion"]


def test_current_d1_projection_refuses_historical_cohort_or_cpu_runtime(declarations):
    selected = scope()
    output = builder(selected)
    output.operation["version"] = "2"
    request = compile_question_stage(declarations["character_modal_force_v1"], selected, 0)
    reply = d1_reply(request, dict(modal_cue=read_answer()))
    with pytest.raises(ValueError, match="CUDA bfloat16"):
        output.d1(request, reply, runtime={"device": "cpu", "dtype": "torch.float32"})
    with pytest.raises(ValueError, match="ordered version2"):
        output.d1(
            request,
            {**reply, "batch_receipt": {"version": 1}},
            runtime={"device": "cuda:0", "dtype": "torch.bfloat16"},
        )
