"""Shared controlled inputs and builders for model characterization support."""

import json
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from corpus_structure.methods.gliner import GlinerPreparation, GlinerProfile, GlinerReport
from corpus_structure.methods.model_observation import installed_policy, observation_digest
from corpus_structure.methods.pm2_gliner_classification import ClassificationProfile
from corpus_structure.semantic.characterization import characterization_inputs
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.interpretation_questions import (
    characterization_question_dependencies,
)
from corpus_structure.semantic.model_characterization import (
    prepare_model_scope,
)
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.types import ResolvedDependencies, SourceArtifact, SourceBundle


@pytest.fixture(scope="module")
def prepared():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    return prepare_release(
        characterization_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))),
        characterization_question_dependencies(ResolvedDependencies()),
    )


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


def scope(text="may may", focal=None):
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.declared_record_sources import (
        DeclaredNativeFrameSource,
        DeclaredRecordSource,
    )
    from corpus_structure.semantic.source_products import native_projection_identity, source_subject

    pieces = [
        dict(kind="native_text", item_ref="#/texts/0", source_field="text", start=0, end=len(text))
    ]
    items = [dict(self_ref="#/texts/0", label="text", text=text)]
    projection = native_projection_identity(text, pieces, items)
    coordinate = dict(
        document="book", projection=projection, section_pointer="#/groups/0", membership="direct"
    )
    selectors = [dict(projection=projection, start=0, end=len(text))]
    context = SubjectContext(
        "p",
        source_subject(coordinate),
        "book",
        canonical_bytes(dict(source=coordinate, selectors=selectors)),
        subject_definition="original-source-view",
    )
    source = DeclaredRecordSource(
        "book", projection, "#/groups/0", "direct", context, "product:source", None, "kind:source"
    )
    frame = DeclaredNativeFrameSource(
        canonical_bytes(
            dict(
                source=coordinate,
                selectors=selectors,
                text=text,
                pieces=pieces,
                items=items,
                ancestors=[],
            )
        ).decode(),
        canonical_bytes(source.pin()).decode(),
    )
    return prepare_model_scope(frame, focal or (0, len(text)), (0, len(text)))
