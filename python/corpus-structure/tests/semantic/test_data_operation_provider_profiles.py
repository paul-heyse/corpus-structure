"""Provider inference meaning is authenticated independently of placement custody."""
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from corpus_structure.semantic.data_operation_identity import ProfileField, profile_identities
from corpus_structure.semantic.data_operation_model import OpaqueBoundary
from corpus_structure.semantic.data_operation_provider_profiles import checked_attestation, checked_profile, operation_profile, runtime_profiles
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.types import SourceArtifact


def _facts(model="model:A", threads=2):
    projections = profile_identities((ProfileField("model", model, "semantic"), ProfileField("threads", threads, "execution")))
    profile = {"version": "provider-inference-profile-v1", "identity": projections.inference.key, "meaning": json.loads(projections.inference.canonical_input)}
    attestation = {"version": "provider-profile-attestation-v1", "identity": projections.inference.key, "meaning": profile["meaning"], "execution_identity": projections.execution.key, "execution_meaning": json.loads(projections.execution.canonical_input)}
    source = SourceArtifact("provider/profile", canonical_bytes(profile))
    operation = SimpleNamespace(semantic_id="provider:one", assets=(OpaqueBoundary("provider:profile", source.name, "provider-inference-profile", source.digest),))
    return profile, attestation, source, operation


def test_profile_projection_accepts_changed_placement_but_refuses_changed_model():
    profile, attestation, source, operation = _facts()
    assert checked_profile(source.content) == profile
    assert operation_profile(operation, (source,))["identity"] == profile["identity"]
    _, moved, _, _ = _facts(threads=16)
    assert moved["execution_identity"] != attestation["execution_identity"]
    assert checked_attestation(moved, profile) == moved
    _, wrong, _, _ = _facts(model="model:B")
    with pytest.raises(ValueError, match="semantic profile"):
        checked_attestation(wrong, profile)


def test_profile_cannot_be_forged_by_copying_an_identity_or_contract_name():
    profile, attestation, source, operation = _facts()
    forged = {**profile, "meaning": _facts(model="model:B")[0]["meaning"]}
    with pytest.raises(ValueError, match="identity differs"):
        checked_profile(canonical_bytes(forged))
    with pytest.raises(ValueError, match="captured asset"):
        operation_profile(operation, (SourceArtifact(source.name, canonical_bytes(forged)),))
    # A matching semantic identifier cannot conceal different semantic fields in
    # the execution profile. The execution key itself is otherwise genuine.
    wrong_execution = _facts(model="model:B")[1]
    with pytest.raises(ValueError, match="semantic fields"):
        checked_attestation({**wrong_execution, "identity": profile["identity"], "meaning": profile["meaning"]}, profile)


def test_runtime_profiles_require_exact_captured_execution_asset_and_operation_coverage():
    profile, attestation, source, operation = _facts()
    model = SimpleNamespace(operations=(operation,))
    semantic = SourceArtifact("data-operations/contracts/" + source.name, source.content)
    runtime = SourceArtifact("data-operations/contracts/provider/runtime", canonical_bytes({"selection": {"provider": "fixed"}, "provider_profile": attestation}))
    actual = runtime_profiles(model, (semantic, runtime))
    assert set(actual) == {"provider:one"}
    assert actual["provider:one"]["profile"] == {**profile, "contract": source.name, "sha256": source.digest}
    assert actual["provider:one"]["runtime_sha256"] == runtime.digest
    with pytest.raises(ValueError, match="one exact runtime"):
        runtime_profiles(model, (semantic,))
    with pytest.raises(ValueError, match="one exact runtime"):
        runtime_profiles(model, (semantic, runtime, SourceArtifact("data-operations/contracts/duplicate", runtime.content)))
