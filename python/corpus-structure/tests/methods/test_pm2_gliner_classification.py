"""Exact managed custody controls for a released choice on an operations document."""

import base64
import json
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
from importlib.resources import files
from types import SimpleNamespace

import pytest

from corpus_structure.core.method import SourceViewRef, UnitRef
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.methods.gliner import GlinerPack
from corpus_structure.methods.model_observation import (
    MODEL_OBSERVATION_INPUT,
    batch_receipt,
    installed_policy,
    observation_digest,
    request_digest,
)
from corpus_structure.methods.pm2_gliner_classification import (
    FAMILY,
    VERSION,
    ClassificationProfile,
    GlinerRefused,
    classification_mapping,
    classification_product,
    classification_request,
)
from corpus_structure.methods.pm2_result import pm2_input_digest, pm2_unit_result
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.interpretation_questions import (
    QUESTION_INPUT,
    compile_question_families,
    declared_families,
)
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.source_contexts import PreparedNativeSources
from corpus_structure.semantic.source_views import PreparedSourceView
from corpus_structure.semantic.types import SourceArtifact


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
                version="gliner2-2.1.0-cpu-fp32-standard-whitespace-v1",
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
            observation_digest=observation_digest(
                digest,
                raw_json,
                effective,
                ordinal=0,
                member=batch_receipt(
                    pack, asdict(profile), (item,), 0.7, "flat", False, request["inference"]
                )["members"][0],
            ),
            batch_receipt_json=json.dumps(
                batch_receipt(
                    pack, asdict(profile), (item,), 0.7, "flat", False, request["inference"]
                )
            ),
            member_ordinal=0,
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


def test_batch_receipt_keeps_exact_member_and_choice_projection(case):
    from dataclasses import replace
    from hashlib import sha256

    from corpus_structure.methods.gliner import GlinerInput
    from corpus_structure.methods.model_observation import batch_receipt

    request = case.request
    item = GlinerInput(**request["item"])
    other = replace(item, context_id="other-context", context_digest="f" * 64)
    receipt = batch_receipt(
        GlinerPack(**request["pack"]),
        asdict(case.profile.profile),
        (other, item),
        0.7,
        "flat",
        False,
        request["inference"],
    )
    # Independently assert the wire commitment domains and original ordinal.
    assert (
        receipt["members"][1]
        == sha256(
            canonical_bytes(
                [
                    "located-model-member-2",
                    item.operation,
                    item.context_id,
                    item.context_digest,
                    item.text,
                ]
            )
        ).hexdigest()
    )
    assert (
        receipt["digest"]
        == sha256(
            canonical_bytes(
                [
                    "located-model-request-2",
                    receipt["header"],
                    receipt["members"],
                ]
            )
        ).hexdigest()
    )
    reply = _reply(case, [{"label": "schedule", "confidence": 0.9}])["gliner"]
    reply.update(
        computation=receipt["digest"],
        request_digest=receipt["digest"],
        batch_receipt_json=json.dumps(receipt),
        member_ordinal=1,
    )
    reply["observation_digest"] = sha256(
        canonical_bytes(
            [
                "located-model-observation-2",
                receipt["digest"],
                1,
                receipt["members"][1],
                reply["raw_json"],
                reply["effective_profile_json"],
            ]
        )
    ).hexdigest()
    product = classification_product(request, reply, case.profile)
    assert product.value["selected_keys"] == ("schedule",)
    reply["member_ordinal"] = 0
    with pytest.raises(GlinerRefused, match="exact released request"):
        classification_product(request, reply, case.profile)
