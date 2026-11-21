"""Host reacquisition keeps admitted inference and other runtime inputs intact."""

import json
from dataclasses import replace
from typing import cast

from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection
from corpus_structure.semantic import native_host_reacquisition
from corpus_structure.semantic.data_operation_runtime import RuntimeBinding
from corpus_structure.semantic.hanlp_products import hanlp_execution_custody
from corpus_structure.semantic.sentence_products import sentence_execution_custody
from corpus_structure.semantic.types import PreparedRelease, SourceArtifact


def test_reacquires_both_admitted_profiles_with_one_installation_observation(monkeypatch, tmp_path):
    config = SentenceConfig()
    original = {"lock_sha256": "before"}

    def selected(provider, artifacts, parameters, backend):
        return NativeSelection(
            NativeProfile(provider, original, artifacts, parameters, "float32", backend),
            tmp_path,
        )

    artifacts = (
        sentence_execution_custody(
            config,
            selection=selected("spacy", {"files": {}}, config.model_dump(mode="json"), "cupy"),
        ),
        hanlp_execution_custody(selected("hanlp", {}, {}, "sdpa")),
    )
    sources = tuple(replace(item, name="runtime-transport/" + item.name) for item in artifacts)
    attestations = {item.name: json.loads(item.content)["provider_profile"] for item in sources}
    unrelated = SourceArtifact("other-input", b"unchanged")
    prior = RuntimeBinding(
        "release:old",
        "runtime:old",
        json.dumps(
            {
                "execution_profile": "source-native",
                "provider_profiles": {
                    name: {"runtime_contract": name, "attestation": value}
                    for name, value in attestations.items()
                },
            }
        ).encode(),
        json.dumps(
            {
                "inputs": [
                    {"name": item.name, "content_hex": item.content.hex()}
                    for item in (*sources, unrelated)
                ]
            }
        ).encode(),
    )
    observed = []
    current = {"lock_sha256": "after"}

    def preflight(**options):
        observed.append(options["providers"])
        return current

    refreshed = replace(prior, runtime_id="runtime:new")

    def prepare(prepared, inputs, *, execution_profile, observed):
        assert execution_profile == "source-native"
        assert observed["prior_runtime"] == prior.runtime_id
        assert observed["shared_host_providers"] == ["hanlp", "spacy"]
        for item in inputs:
            if item.name == unrelated.name:
                assert item == unrelated
                continue
            value = json.loads(item.content)
            assert value["selection"]["profile"]["runtime_identity"] == current
            previous = attestations[item.name]
            assert value["provider_profile"]["identity"] == previous["identity"]
            assert value["provider_profile"]["meaning"] == previous["meaning"]
            assert value["provider_profile"]["execution_identity"] != previous["execution_identity"]
        return refreshed

    monkeypatch.setattr(native_host_reacquisition, "preflight_pm2_residents", preflight)
    monkeypatch.setattr(native_host_reacquisition, "prepare_data_operation_runtime", prepare)
    assert (
        native_host_reacquisition.reacquire_shared_host_runtime(
            cast(PreparedRelease, object()), prior
        )
        == refreshed
    )
    assert observed == [("hanlp", "spacy")]
