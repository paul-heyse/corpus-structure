"""Shared controlled inputs and builders for model characterization support."""

import json
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path

import pytest

from corpus_structure.core.method import SourceViewRef
from corpus_structure.methods.gliner import GlinerPreparation, GlinerProfile, GlinerReport
from corpus_structure.methods.model_observation import installed_policy, observation_digest
from corpus_structure.methods.pm2_gliner_classification import ClassificationProfile
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.characterization import characterization_inputs
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.interpretation_questions import (
    CHARACTERIZATION_FAMILIES,
    characterization_question_dependencies,
)
from corpus_structure.semantic.model_characterization import (
    ModelCharacterizationBuilder,
    prepare_model_scope,
)
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.source_views import PreparedSourceView
from corpus_structure.semantic.types import ResolvedDependencies


@pytest.fixture(scope="module")
def prepared():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    return prepare_release(
        characterization_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))),
        characterization_question_dependencies(ResolvedDependencies()),
    )


def scope(text="may may", focal=None):
    pieces = (
        dict(kind="native_text", item_ref="#/texts/0", source_field="text", start=0, end=len(text)),
    )
    projection = dict(text=text, pieces=pieces, items=["#/texts/0"], ancestors=[], health={})
    view = PreparedSourceView(
        SourceViewRef(
            11,
            "model-source",
            3,
            ProductReference(7, "document", "a" * 64),
            "#/groups/0",
            "descendants",
            sha256(canonical_bytes(projection)).hexdigest(),
            "c" * 64,
        ),
        text,
        pieces,
        (dict(self_ref="#/texts/0", label="text", text=text),),
        (),
        {},
    )
    return prepare_model_scope(view, focal or (0, len(text)), (0, len(text)))


def builder(selected_scope):
    base = selected_scope.view.ref.native_product.values()
    ref = selected_scope.view.ref
    selected = dict(
        source_view_ids=[ref.id],
        source_views=[
            dict(
                source_view_id=ref.id,
                key=ref.key,
                base_document=base,
                section_pointer=ref.section_pointer,
                membership=ref.membership,
                projection_digest=ref.projection_digest,
                recipe_digest=ref.recipe_digest,
            )
        ],
        profile="model-test",
        selectors=[
            dict(projection=ref.projection_digest, start=0, end=len(selected_scope.view.text))
        ],
    )
    operation = dict(
        key="text.model_characterization",
        version="1",
        runtime="fixture-runtime",
        model="fixture-model",
        grammar="none",
        configuration="fixture-config",
        input="fixture-input",
        context="fixture-context",
    )
    return ModelCharacterizationBuilder(base, selected, operation)


def d1_reply(request, answers):
    rendered = json.dumps(request.payload["state"], ensure_ascii=False, separators=(",", ":"))
    start = rendered.index('"source":') + len('"source":') + 1
    end = start + len(json.dumps(request.payload["state"]["source"], ensure_ascii=False)[1:-1])
    native = {}
    for key, answer in answers.items():
        value = dict(answer)
        if "source_span" in value:
            a, b = value.pop("source_span")
            value.update(
                span=[start + a, start + b],
                text=request.payload["state"]["source"][a:b],
                path="/source",
            )
        native[key] = value
    return dict(
        outcome="succeeded",
        rendered_state=rendered,
        state_fields=[[start, end, "/source"]],
        native=dict(answers=native, usage=dict(input_tokens=42)),
    )


def mark_other_families_complete(output, selected_scope):
    for family in CHARACTERIZATION_FAMILIES:
        if not output.covered[family]:
            output.record(
                family,
                [
                    dict(
                        projection=selected_scope.view.ref.projection_digest,
                        start=0,
                        end=len(selected_scope.view.text),
                    )
                ],
            )


def gliner_profile():
    profile = GlinerProfile(
        Path("/fixture-gliner"),
        "fastino/gliner2.5-base-v1",
        "54785d51df8d86a0d8f2eb212fec15871aad2c4d",
        tuple(
            (name, "d" * 64)
            for name in (
                "config.json",
                "encoder_config/config.json",
                "model.safetensors",
                "tokenizer.json",
                "tokenizer_config.json",
            )
        ),
    )
    profile = replace(profile, version="gliner2-2.1.0-cpu-fp32-standard-whitespace-v1")
    return ClassificationProfile(provider="gliner", device="cpu", profile=profile)


def gliner_report(pack, item, profile, raw, *, overlap="nested", threshold=0.5):
    inference = installed_policy()[0]["inference"]
    from corpus_structure.methods.model_observation import batch_receipt

    receipt = batch_receipt(pack, asdict(profile), (item,), threshold, overlap, False, inference)
    expected = receipt["digest"]
    raw_json = json.dumps(raw)
    effective = json.dumps(
        dict(
            profile=profile.fingerprint,
            device=profile.device,
            dtype="float32",
            attention_backend="standard",
            threads=profile.threads,
            versions={"gliner2": "2.1.0"},
        )
    )
    suffix = "" if item.text.endswith((".", "!", "?")) else "."
    return GlinerReport(
        item.context_id,
        item.context_digest,
        expected,
        profile.fingerprint,
        pack.fingerprint,
        GlinerPreparation(item.text + suffix, suffix, 2, 2, len(item.text.encode())),
        raw_json,
        effective,
        0.1,
        False,
        request_digest=expected,
        observation_digest=observation_digest(
            expected, raw_json, effective, ordinal=0, member=receipt["members"][0]
        ),
        batch_receipt_json=json.dumps(receipt),
        member_ordinal=0,
    )
