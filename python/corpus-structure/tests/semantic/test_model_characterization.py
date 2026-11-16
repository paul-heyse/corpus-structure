"""Controlled current PM2 questions preserve exact sources, choices and raw observations."""

import json
from dataclasses import asdict, replace

import pytest

from corpus_structure.methods.pm2_interpretation_products import interpretation_products
from corpus_structure.methods.pm2_source import D1SourceField, MappedSource, SourceMapRefused
from corpus_structure.semantic.construction_products import CharacterizationSnapshot
from corpus_structure.semantic.data_product_reference import DataProductReference
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.interpretation_questions import (
    CHARACTERIZATION_FAMILIES,
    CHARACTERIZATION_QUESTION_INPUT,
    characterization_question_dependencies,
    compile_question_families,
    declared_families,
)
from corpus_structure.semantic.learned_primary import learned_d1_evidence
from corpus_structure.semantic.model_characterization import (
    GLINER_CUES,
    GLINER_FUNCTIONS,
    compile_question_stage,
    contextual_candidate_populations,
    declared_model_dependencies,
    freeze_candidates,
    gliner_cue_request,
)
from corpus_structure.semantic.types import ResolvedDependencies
from semantic.model_characterization_support import (
    d1_reply,
    gliner_profile,
    gliner_report,
    prepared as prepared,
    scope,
)


@pytest.fixture(scope="module")
def declarations():
    dependencies = characterization_question_dependencies(ResolvedDependencies())
    return declared_families(compile_question_families(dependencies.artifacts))


def answer(start=0, end=3):
    return dict(type="text", found=0.91, source_span=(start, end))


def interpret(request, reply):
    start, end, path = reply["state_fields"][0]
    located = learned_d1_evidence(
        request.scope, request, reply, D1SourceField(reply["rendered_state"], path, start, end)
    )
    return located, interpretation_products(request.family, request.payload, reply, located)


def test_current_question_inventory_and_acquired_bytes_are_explicit(declarations):
    assert (
        tuple(name for name in CHARACTERIZATION_FAMILIES if name in declarations)
        == CHARACTERIZATION_FAMILIES
    )
    dependencies = characterization_question_dependencies(ResolvedDependencies())
    assert characterization_question_dependencies(dependencies) is dependencies
    assert dependencies.artifacts[0].name == CHARACTERIZATION_QUESTION_INPUT
    with pytest.raises(ValueError, match="competing"):
        characterization_question_dependencies(dependencies, content=b"[]")


def test_source_first_state_preserves_focal_and_examined_regions(declarations):
    selected = scope("They may leave.", focal=(5, 14))
    for name in CHARACTERIZATION_FAMILIES[:4]:
        request = compile_question_stage(declarations[name], selected, 0)
        assert "candidates" not in request.payload["state"]
        assert request.payload["state"]["focal"] == dict(start=5, end=14)
        assert request.payload["interpretation"]["assessed_scope"]["projection_extent"] == [0, 15]
    with pytest.raises(ValueError, match="independent"):
        compile_question_stage(declarations["character_host_choice_v1"], selected, 0)


def test_stages_require_declared_earlier_answers(declarations):
    from corpus_structure.semantic.interpretation_questions import QuestionFamily

    family = declarations["character_scope_v1"]
    with pytest.raises(ValueError, match="prerequisites"):
        compile_question_stage(family, scope(), 2)
    invalid = family.model_dump(mode="json")
    invalid["questions"][0]["depends_on"] = ["relative_scope"]
    with pytest.raises(ValueError, match="earlier"):
        QuestionFamily.model_validate_json(json.dumps(invalid))


def test_second_repeated_literal_keeps_exact_location_and_raw_probability(declarations):
    request = compile_question_stage(declarations["character_modal_force_v1"], scope(), 0)
    reply = d1_reply(request, dict(modal_cue=answer(4, 7)))
    located, (product,) = interpret(request, reply)
    assert isinstance(located["modal_cue"], MappedSource)
    assert [(piece.start, piece.end, piece.quote) for piece in located["modal_cue"].pieces] == [
        (4, 7, "may")
    ]
    assert product.value["native_answer"]["found"] == 0.91
    assert product.value["state"] == "proposed" and product.members == ("modal_cue",)
    assert reply["native"]["answers"]["modal_cue"]["text"] == "may"


def test_prior_answer_text_never_becomes_original_source(declarations):
    family = declarations["character_modal_force_v1"]
    first = compile_question_stage(family, scope(), 0)
    _, (prior,) = interpret(first, d1_reply(first, dict(modal_cue=answer())))
    second = compile_question_stage(family, first.scope, 1, prior={"modal_cue": prior.value})
    reply = d1_reply(second, dict(modal_target=answer()))
    copied = reply["rendered_state"].index('"text":"may"') + len('"text":"')
    reply["native"]["answers"]["modal_target"].update(
        span=[copied, copied + 3], path="/prior_answers/modal_cue/native_answer/text"
    )
    located, (product,) = interpret(second, reply)
    assert isinstance(located["modal_target"], SourceMapRefused)
    assert product.value["state"] == "unsupported"


@pytest.mark.parametrize(
    "literal_scope,start,expected",
    [("focal", 4, "proposed"), ("focal", 0, "unsupported"), ("context", 0, "proposed")],
)
def test_literal_policy_distinguishes_focal_and_examined_context(
    declarations, literal_scope, start, expected
):
    family = declarations["character_modal_force_v1"]
    family = family.model_copy(
        update={
            "questions": tuple(
                q.model_copy(update={"literal_scope": literal_scope}) for q in family.questions
            )
        }
    )
    request = compile_question_stage(family, scope("may may", focal=(4, 7)), 0)
    reply = d1_reply(request, dict(modal_cue=answer(start, start + 3)))
    original = canonical_bytes(reply)
    located, (product,) = interpret(request, reply)
    assert product.value["state"] == expected and canonical_bytes(reply) == original
    if expected == "unsupported":
        from corpus_structure.methods.pm2_result import pm2_contribution_values

        assert isinstance(located["modal_cue"], SourceMapRefused)
        rows, _, _ = pm2_contribution_values(
            request.scope.mapping,
            located,
            (product,),
            prepared=None,
            provider="d1",
            input_digest="controlled",
            operation_key="controlled",
            question=family.family,
            source_path="/source",
            parser_operation=False,
        )
        assert all(row["kind"] != "occurrence" for row in rows)
        assert len(rows) == 1 and rows[0]["kind"] == "proposal" and rows[0]["members"] == ()


@pytest.mark.parametrize("field", ["pin", "focal_extent", "projection_extent", "scope_digest"])
def test_changed_frozen_assessed_scope_refuses(declarations, field):
    request = compile_question_stage(declarations["character_modal_force_v1"], scope(), 0)
    payload = request.payload
    payload["interpretation"]["assessed_scope"][field] = "changed"
    request = replace(request, content=canonical_bytes(payload))
    with pytest.raises(ValueError, match="actual bound focal source"):
        interpret(request, d1_reply(request, dict(modal_cue=answer())))


def upstream(selected, *, roles=(), terms=(), choices=(), annotations=None):
    coordinate = selected.view.value["source"]
    occurrences = [
        dict(
            local_id=key + ":occ",
            extents=[
                dict(
                    projection=coordinate["projection"],
                    start=a,
                    end=b,
                    text=selected.view.text[a:b],
                )
            ],
        )
        for key, a, b in (("focus", 0, 1), ("B", 2, 3), ("C", 4, 5))
    ]
    annotations = (
        [
            dict(
                local_id=key,
                kind="native.mention",
                occurrences=[key + ":occ"],
                family="context.reference",
            )
            for key in ("focus", "B", "C")
        ]
        if annotations is None
        else annotations
    )
    inventory = dict(
        occurrences=occurrences,
        annotations=list(annotations),
        terms=list(terms),
        roles=list(roles),
        choices=list(choices),
        memberships=[],
    )
    packets = [
        dict(member_id=row["local_id"], body={"record_type": tag, **row})
        for name, tag in (
            ("occurrences", "occurrence"),
            ("annotations", "annotation"),
            ("terms", "term"),
            ("roles", "role"),
            ("choices", "choice"),
        )
        for row in inventory[name]
    ]
    product = CharacterizationSnapshot(
        "product:upstream",
        canonical_bytes(
            dict(
                source=coordinate,
                selectors=selected.view.value["selectors"],
                coverage=[
                    dict(
                        family=family,
                        availability="available",
                        outcome="complete",
                        examined=[dict(projection=coordinate["projection"], start=0, end=5)],
                        unexamined=[],
                    )
                    for family in ("context.host", "context.reference")
                ],
                members=packets,
            )
        ),
    )
    dependencies = declared_model_dependencies((product,), selected.view)
    return DataProductReference(product.semantic_id), dependencies


def ref(pin, key):
    return dict(product_id=pin.product_id, member_id=key)


@pytest.mark.parametrize(
    "choice,expected",
    [
        ("no_referent", "no_match"),
        ("missing_referent", "missing_candidate"),
        ("insufficient", "insufficient_evidence"),
    ],
)
def test_candidate_answers_keep_explicit_unresolved_dispositions(declarations, choice, expected):
    selected = scope("A B C")
    pin, deps = upstream(selected)
    family = declarations["character_referent_choice_v1"]
    frozen = freeze_candidates(
        family,
        selected,
        deps,
        focus=ref(pin, "focus"),
        alternatives=[
            dict(key="actual_B", members=[ref(pin, "B")]),
            dict(key="actual_C", members=[ref(pin, "C")]),
        ],
    )
    request = compile_question_stage(family, selected, 0, candidates=frozen)
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
    _, (product,) = interpret(request, reply)
    assert product.value["state"] == expected and product.value["selected_keys"] == ()
    assert request.payload["interpretation"]["candidate_list_digest"] == frozen.digest
    assert [candidate["key"] for candidate in product.value["candidates"]] == [
        "actual_B",
        "actual_C",
    ]


def test_selected_provider_alias_keeps_exact_qualified_endpoint(declarations):
    selected = scope("A B C")
    pin, deps = upstream(selected)
    family = declarations["character_referent_choice_v1"]
    frozen = freeze_candidates(
        family,
        selected,
        deps,
        focus=ref(pin, "focus"),
        alternatives=[dict(key="actual_B", members=[ref(pin, "B")])],
    )
    request = compile_question_stage(family, selected, 0, candidates=frozen)
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
    _, (product,) = interpret(request, reply)
    assert product.value["selected_keys"] == ("actual_B",)
    assert product.value["candidates"][0]["members"][0]["reference"] == ref(pin, "B")
    reply["native"]["answers"]["referent"]["choice"] = "never_offered"
    with pytest.raises(ValueError, match="unoffered"):
        interpret(request, reply)


def test_missing_contextual_inventory_remains_incomplete(declarations):
    populations, complete = contextual_candidate_populations(
        declarations["character_referent_choice_v1"], scope(), {}
    )
    assert populations == () and complete is False


def test_rival_hypothesis_choices_remain_attached_to_each_exact_support(declarations):
    selected = scope("A B C")
    roles = [
        dict(
            local_id="role-" + key,
            owner="focus",
            member=key,
            role="source_local_coreference_candidate",
            family="context.reference",
            required_choices=["select-" + branch],
            basis=dict(kind="contextual_proposal", premises=["hypothesis-" + key]),
        )
        for key, branch in (("B", "left"), ("C", "right"))
    ]
    annotations = [
        dict(local_id=key, kind=kind, occurrences=[occ], family="context.reference")
        for key, kind, occ in (
            ("focus", "native.mention", "focus:occ"),
            ("B", "native.mention", "B:occ"),
            ("C", "native.mention", "C:occ"),
            ("hypothesis-B", "contextual.referent_hypothesis", "focus:occ"),
            ("hypothesis-C", "contextual.referent_hypothesis", "focus:occ"),
        )
    ]
    pin, deps = upstream(selected, roles=roles, annotations=annotations)
    (frozen,), complete = contextual_candidate_populations(
        declarations["character_referent_choice_v1"], selected, deps
    )
    assert complete
    assert [
        alternative["hypothesis_supports"][0]["required_external_choices"]
        for alternative in frozen.payload["alternatives"]
    ] == [[ref(pin, "select-left")], [ref(pin, "select-right")]]
    assert [
        alternative["hypothesis_supports"][0]["premises"][0]
        for alternative in frozen.payload["alternatives"]
    ] == [ref(pin, "role-B"), ref(pin, "role-C")]


def test_compatible_host_set_is_explicit_and_changed_source_refuses(declarations):
    selected = scope("A B C")
    terms = [
        dict(local_id=key, kind=kind, occurrences=[occ], family="context.host")
        for key, kind, occ in (
            ("qualifier", "operator", "focus:occ"),
            ("host_B", "predicate", "B:occ"),
            ("host_C", "predicate", "C:occ"),
        )
    ]
    pin, deps = upstream(selected, terms=terms)
    family = declarations["character_host_choice_v1"]
    alternatives = [dict(key="shared_hosts", members=[ref(pin, "host_B"), ref(pin, "host_C")])]
    with pytest.raises(ValueError, match="compatible"):
        freeze_candidates(
            family, selected, deps, focus=ref(pin, "qualifier"), alternatives=alternatives
        )
    alternatives[0]["compatibility"] = "compatible"
    frozen = freeze_candidates(
        family, selected, deps, focus=ref(pin, "qualifier"), alternatives=alternatives
    )
    assert [member["reference"] for member in frozen.payload["alternatives"][0]["members"]] == [
        ref(pin, "host_B"),
        ref(pin, "host_C"),
    ]
    wrong = scope("X B C")
    with pytest.raises(ValueError, match="examined"):
        freeze_candidates(
            family, wrong, deps, focus=ref(pin, "qualifier"), alternatives=alternatives
        )


def test_current_gliner_literals_keep_repeated_offsets_raw_scores_and_diagnostics(
    prepared, declarations
):
    from corpus_structure.methods.gliner import map_literal
    from corpus_structure.methods.model_observation import installed_policy
    from corpus_structure.methods.pm2_gliner_classification import authenticated_gliner_report

    selected, profile = scope(), gliner_profile()
    family = declarations[GLINER_CUES]
    pack, item = gliner_cue_request(prepared.release_id, family, selected)
    raw = dict(entities={question.key: [] for question in family.questions})
    raw["entities"]["modal_cue"] = [
        dict(text="may", start=0, end=3, confidence=0.8),
        dict(text="may", start=4, end=7, confidence=0.85),
    ]
    raw["entities"]["term"] = [dict(text="may", start=0, end=3, confidence=0.6)]
    native = gliner_report(pack, item, profile.profile, raw)
    authenticated = authenticated_gliner_report(
        dict(
            pack=asdict(pack),
            item=asdict(item),
            threshold=0.5,
            inference=installed_policy()[0]["inference"],
        ),
        asdict(native),
        profile,
        overlap_policy="nested",
    )
    assert [
        (piece.start, piece.end)
        for span in authenticated.raw["entities"]["modal_cue"]
        for piece in map_literal(authenticated, selected.mapping.context, span)
    ] == [(0, 3), (4, 7)]
    assert [span["confidence"] for span in authenticated.raw["entities"]["modal_cue"]] == [
        0.8,
        0.85,
    ]
    assert authenticated.diagnostics[0] == ("proposal_pool", "unavailable")


def test_current_gliner_category_has_no_literal_witness(prepared, declarations):
    from corpus_structure.methods.gliner import GlinerInput, GlinerPack
    from corpus_structure.methods.model_observation import installed_policy
    from corpus_structure.methods.pm2_gliner_classification import (
        classification_product,
        classification_request,
    )

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
    assert product.members == () and product.value["selected_keys"] == ("assertion",)
