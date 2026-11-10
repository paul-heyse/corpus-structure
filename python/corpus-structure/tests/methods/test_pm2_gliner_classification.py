"""Exact managed custody controls for a released choice on an operations document."""

import base64
import json
from copy import deepcopy
from dataclasses import asdict, replace
from hashlib import sha256
from importlib.resources import files
from types import SimpleNamespace

import pytest

from corpus_structure.core.method import SourceViewRef, UnitRef
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.methods.gliner import GlinerPack
from corpus_structure.methods.model_observation import (
    MODEL_OBSERVATION_INPUT,
    installed_policy,
    observation_digest,
    request_digest,
)
from corpus_structure.methods.pm2_gliner_classification import (
    FAMILY,
    METHOD,
    VERSION,
    ClassificationProfile,
    classification_mapping,
    classification_request,
    profile_digest,
)
from corpus_structure.methods.pm2_result import pm2_input_digest, pm2_unit_result
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.interpretation_questions import (
    QUESTION_INPUT,
    compile_question_families,
    declared_families,
)
from corpus_structure.semantic.observations import source_python, source_value
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.source_contexts import PreparedNativeSources
from corpus_structure.semantic.source_views import PreparedSourceView
from corpus_structure.semantic.types import SourceArtifact
from corpus_structure.serve.contribution_composition import composition_facets
from corpus_structure.serve.pm2_classification_replay import verify_classification_replay


@pytest.fixture
def case():
    literal = "At midnight, the duty officer reads the rotation log"
    pieces = (
        dict(
            kind="native_text", item_ref="#/texts/0", source_field="text", start=0, end=len(literal)
        ),
    )
    projection = dict(text=literal, pieces=pieces, items=["#/texts/0"], ancestors=[], health={})
    view = PreparedSourceView(
        SourceViewRef(
            5,
            "runbook",
            1,
            ProductReference(18, "integrated", "a" * 64),
            "#/groups/1",
            "direct",
            sha256(canonical_bytes(projection)).hexdigest(),
            "b" * 64,
        ),
        literal,
        pieces,
        (dict(self_ref="#/texts/0", text=literal),),
        (),
        {},
    )
    question = SourceArtifact(
        QUESTION_INPUT,
        canonical_bytes(
            [
                {
                    "family": FAMILY,
                    "questions": [
                        {
                            "key": "purpose",
                            "kind": "choice",
                            "instructions": "Which functions does the source perform?",
                            "multiple": True,
                            "minimum_probability": 0.7,
                            "options": [
                                {
                                    "key": "instruction",
                                    "criterion": "Directs a person to do something.",
                                },
                                {
                                    "key": "schedule",
                                    "criterion": "Specifies a time for an activity.",
                                },
                                {
                                    "key": "warning",
                                    "criterion": "States the consequences of a failure.",
                                },
                            ],
                        }
                    ],
                }
            ]
        ),
    )
    policy_bytes = files("corpus_structure.methods").joinpath("model_observation.json").read_bytes()
    manifest = canonical_bytes(
        {
            "dependencies": sorted(
                (
                    (question.name, question.digest),
                    (MODEL_OBSERVATION_INPUT, sha256(policy_bytes).hexdigest()),
                )
            )
        }
    )
    release_id = "release:" + sha256(manifest).hexdigest()
    registry = compile_question_families((question,))
    prepared = SimpleNamespace(release_id=release_id, registry_rows=registry, manifest=manifest)
    contract = {
        "release_id": release_id,
        "model_observation_policy": {
            "manifest_base64": base64.b64encode(manifest).decode(),
            "input_base64": base64.b64encode(policy_bytes).decode(),
        },
        "interpretation_question_inputs": {
            question.name: base64.b64encode(question.content).decode()
        },
    }
    profile = ClassificationProfile.model_validate(
        dict(
            provider="gliner",
            device="cpu",
            threshold=0.6,
            profile=dict(
                snapshot="/immutable/gliner-model",
                checkpoint="gliner/model",
                revision="f" * 40,
                artifact_hashes=[
                    [name, "d" * 64]
                    for name in (
                        "config.json",
                        "encoder_config/config.json",
                        "model.safetensors",
                        "tokenizer.json",
                        "tokenizer_config.json",
                    )
                ],
            ),
        )
    )
    source = native_source_frame(view, ())
    mapping = classification_mapping(source, (0, len(literal)), PreparedNativeSources((source,)))
    family = declared_families(registry)[FAMILY]
    request = classification_request(
        release_id, family, "purpose", mapping, profile, installed_policy()[0]["inference"]
    )
    return SimpleNamespace(
        view=view,
        source=source,
        mapping=mapping,
        profile=profile,
        family=family,
        prepared=prepared,
        request=request,
        contract=contract,
    )


def _reply(case, labels):
    from corpus_structure.methods.gliner import GlinerInput

    request = case.request
    pack = GlinerPack(**request["pack"])
    item = GlinerInput(**request["item"])
    profile = case.profile.profile
    digest = request_digest(
        pack, asdict(profile), (item,), 0.7, "flat", False, request["inference"]
    )
    raw_json = json.dumps({"purpose": labels}, separators=(",", ":"))
    effective = json.dumps(
        dict(
            profile=profile.fingerprint,
            device="cpu",
            dtype="float32",
            attention_backend="standard",
            threads=profile.threads,
            versions={"gliner2": "2.1.0"},
        )
    )
    return {
        "outcome": "succeeded",
        "gliner": dict(
            context_id=item.context_id,
            context_digest=item.context_digest,
            computation=digest,
            request_digest=digest,
            observation_digest=observation_digest(digest, raw_json, effective),
            profile=profile.fingerprint,
            pack=pack.fingerprint,
            preparation=dict(
                consumed_text=item.text + ".",
                synthetic_suffix=".",
                words=10,
                subwords=21,
                input_bytes=len(item.text.encode()),
            ),
            raw_json=raw_json,
            effective_profile_json=effective,
            inference_seconds=0.1,
            resident_reused=False,
        ),
    }


def _result(case, reply, request=None):
    request = request or case.request
    digest = pm2_input_digest(
        case.mapping, case.profile.startup, request, question=FAMILY, operation_version=VERSION
    )
    result = pm2_unit_result(
        UnitRef(TaskUnitType.SOURCE_VIEW, case.view.ref.id, case.view.ref.key),
        case.mapping,
        profile=case.profile.startup,
        request=request,
        reply=reply,
        question=FAMILY,
        operation_version=VERSION,
        input_digest=digest,
        prepared=case.prepared,
    )
    assert result.outcome == ObservationOutcome.PRODUCED
    return result, digest


@pytest.mark.parametrize(
    ("labels", "observed", "selected", "states"),
    [
        (
            [{"label": "warning", "confidence": 0.6}],
            ["warning"],
            [],
            ["unresolved", "unresolved", "policy_withheld"],
        ),
        (
            [
                {"label": "warning", "confidence": 0.94},
                {"label": "instruction", "confidence": 0.81},
            ],
            ["instruction", "warning"],
            ["instruction", "warning"],
            ["proposed", "unresolved", "proposed"],
        ),
        ([], [], [], ["unresolved", "unresolved", "unresolved"]),
    ],
)
def test_managed_choice_keeps_raw_scores_and_release_order(
    case, labels, observed, selected, states
):
    result, _ = _result(case, _reply(case, labels))
    assert result.contributions is not None
    (row,) = result.contributions
    assert row["kind"] == "proposal"
    assert row["standing"] == "retained_private"
    assert row["anchors"] == row["members"] == ()
    value = source_python(row["value"])
    assert value["observed_keys"] == observed
    assert value["selected_keys"] == selected
    assert list(value["alternative_states"].values()) == states
    assert value["native_answer"]["scores"] == {
        item["label"]: item["confidence"] for item in labels
    }
    assert "probabilities" not in value["native_answer"]
    detail = result.parse_detail
    for key in ("pm2_native", "native", "gliner", "preparation"):
        assert isinstance(detail, dict)
        detail = detail[key]
    assert isinstance(detail, dict) and detail["synthetic_suffix"] == "."
    meta = dict(
        method=METHOD,
        source_view_id=case.view.ref.id,
        source=case.view.ref.key,
        cut_member=True,
        selected_task_id=11,
        origin_task_id=11,
    )
    assert result.contribution_operations is not None
    (operation,) = result.contribution_operations
    facets = composition_facets(
        [{**operation, **meta}],
        [{**row, **meta}],
    )
    (facet,) = facets.values()
    assert [role["option_key"] for role in facet["roles"]] == ["instruction", "schedule", "warning"]
    assert [role["option_key"] for role in facet["roles"] if "native_score" in role] == observed


@pytest.mark.parametrize("change", ["question", "source", "choice_order", "profile", "digest"])
def test_custody_refuses_changed_source_question_order_profile_or_reply(case, change):
    request = deepcopy(case.request)
    reply = _reply(case, [{"label": "schedule", "confidence": 0.8}])
    if change == "question":
        request["question_key"] = "unreleased"
    elif change == "source":
        request["item"]["text"] = "A different operational instruction"
    elif change == "choice_order":
        request["label_keys"].reverse()
    elif change == "profile":
        reply["gliner"]["profile"] = "0" * 64
    else:
        reply["gliner"]["observation_digest"] = "0" * 64
    with pytest.raises(ValueError, match=r"(unavailable|exact released request|released source)"):
        _result(case, reply, request)


def test_detached_replay_verifies_archived_question_and_raw_task_custody(case):
    result, digest = _result(case, _reply(case, [{"label": "schedule", "confidence": 0.8}]))
    assert result.contributions is not None
    (row,) = result.contributions
    config_hash = profile_digest(case.profile)
    raw = {
        "method": METHOD,
        "origin_unit_id": case.view.ref.id,
        "configuration": case.profile.startup,
        "config_hash": config_hash,
        "input_hash": digest,
        "body": {
            "method": METHOD,
            "operation_version": VERSION,
            "source": case.source.unit_ref,
            "outcome": "produced",
            "release_id": case.prepared.release_id,
            "configuration_hash": config_hash,
            "input_hash": digest,
            "parse_detail": source_value(result.parse_detail),
            "contribution_operations": json.loads(canonical_bytes(result.contribution_operations)),
        },
    }
    verify_classification_replay(raw, row, case.view, case.contract)
    wrong_version = deepcopy(raw)
    wrong_version["body"]["operation_version"] = "2"
    with pytest.raises(ValueError, match="exact producer"):
        verify_classification_replay(wrong_version, row, case.view, case.contract)
    wrong_source = replace(case.view, text="X" + case.view.text[1:])
    with pytest.raises(ValueError):
        verify_classification_replay(raw, row, wrong_source, case.contract)
    wrong_declaration = deepcopy(case.contract)
    wrong_declaration["interpretation_question_inputs"][QUESTION_INPUT] = base64.b64encode(
        b"[]"
    ).decode()
    with pytest.raises(ValueError, match="question input digest"):
        verify_classification_replay(raw, row, case.view, wrong_declaration)
    false_product = source_python(row["value"])
    false_product["native_answer"]["scores"]["schedule"] = 0.7
    with pytest.raises(ValueError, match="replayed raw observation"):
        verify_classification_replay(
            raw, {**row, "value": source_value(false_product)}, case.view, case.contract
        )
