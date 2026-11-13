"""Actual provider-profile projections, without loading models or acquiring a GPU."""

import json
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from corpus_structure.methods.gliner import CUDA_CODEPOINT_PROFILE, GlinerProfile
from corpus_structure.methods.native_profiles import NativeProfile, gliner_selection, pm2_selection


def policy():
    path = Path(__file__).parents[2] / "src/corpus_structure/methods/model_observation.json"
    return json.loads(path.read_bytes())["batch_execution"]


def d1(**changes):
    values: dict[str, Any] = {
        "provider": "d1",
        "runtime_identity": {"torch": "captured-runtime"},
        "artifacts": {"model": "a" * 64},
        "parameters": {"adapter": "pm2-native-1"},
        "dtype": "bfloat16",
        "backend": "d1",
    }
    return NativeProfile(**{**values, **changes})


def gliner(**changes):
    names = (
        "config.json",
        "encoder_config/config.json",
        "model.safetensors",
        "tokenizer.json",
        "tokenizer_config.json",
    )
    profile = GlinerProfile(
        Path("/captured-model"),
        "checkpoint",
        "immutable-revision",
        tuple((name, "a" * 64) for name in names),
    )
    return gliner_selection(replace(profile, **changes), {"torch": "captured-runtime"}).native


def test_actual_d1_selector_separates_runtime_threads_from_semantic_recipe():
    original = pm2_selection(
        "d1", Path("/captured-model"), {"torch": "runtime-a"}, {"weights": "a" * 64}
    ).native
    changed = pm2_selection(
        "d1",
        Path("/captured-model"),
        {"torch": "runtime-b"},
        {"weights": "a" * 64},
        threads=8,
        interop_threads=2,
    ).native
    a = original.identity_projections(inference_policy=policy())
    b = changed.identity_projections(inference_policy=policy())
    assert a.inference == b.inference
    assert a.execution != b.execution
    assert original.fingerprint != changed.fingerprint


@pytest.mark.parametrize(
    "changes",
    [
        {"artifacts": {"model": "b" * 64}},
        {"parameters": {"adapter": "changed-preprocessing"}},
        {"backend": "changed-attention"},
    ],
)
def test_result_affecting_actual_profile_fields_change_inference(changes):
    assert (
        d1().identity_projections(inference_policy=policy()).inference
        != d1(**changes).identity_projections(inference_policy=policy()).inference
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"dtype": "float32"},
        {"device": "cpu"},
        {"matmul_precision": "high"},
        {"cudnn_allow_tf32": True},
    ],
)
def test_profile_refuses_unqualified_precision_or_device(changes):
    with pytest.raises(ValueError):
        d1(**changes)


def test_actual_gliner_nested_execution_settings_do_not_salt_inference():
    original = gliner()
    changed = gliner(threads=8, max_batch=8, max_words=1024, timeout_seconds=240)
    assert (
        original.parameters["gliner_profile"]["threads"]
        != changed.parameters["gliner_profile"]["threads"]
    )
    a, b = (item.identity_projections(inference_policy=policy()) for item in (original, changed))
    assert a.inference == b.inference and a.execution != b.execution
    assert original.content != changed.content
    codepoints = gliner(version=CUDA_CODEPOINT_PROFILE)
    assert codepoints.identity_projections(inference_policy=policy()).inference != a.inference


@pytest.mark.parametrize(
    "field,value",
    [
        ("version", "gliner2-2.1.0-cpu-fp32-standard-whitespace-v1"),
        ("version", "unsupported-profile"),
        ("threads", 0),
        ("max_words", -1),
        ("timeout_seconds", 0),
        ("max_metadata_bytes", 1),
        ("artifact_hashes", [["config.json", "not-a-sha256"]]),
    ],
)
def test_nested_gliner_content_is_validated_without_inventing_acquisition(field, value):
    values = gliner().wire
    values["parameters"]["gliner_profile"][field] = value
    # Legacy decoding remains exact; the new qualified projection refuses bad content.
    retained = NativeProfile.from_content(json.dumps(values).encode())
    with pytest.raises(ValueError):
        retained.identity_projections(inference_policy=policy())


def test_gliner_artifact_map_order_is_semantically_irrelevant_for_both_projections():
    original = gliner()
    hashes = tuple(
        (item[0], item[1]) for item in original.parameters["gliner_profile"]["artifact_hashes"]
    )
    first = GlinerProfile(Path("/captured-model"), "checkpoint", "immutable-revision", hashes)
    second = replace(first, artifact_hashes=tuple(reversed(hashes)))
    assert first.fingerprint == second.fingerprint
    left, right = (
        gliner_selection(item, {"torch": "captured-runtime"}).native for item in (first, second)
    )
    assert left.content != right.content and left.fingerprint != right.fingerprint
    assert left.identity_projections(inference_policy=policy()) == right.identity_projections(
        inference_policy=policy()
    )


@pytest.mark.parametrize(
    "change", ["unknown-field", "bitwise", "dtype", "missing-provider", "float-version"]
)
def test_projection_requires_complete_compatible_explicit_policy(change):
    selected = policy()
    if change == "unknown-field":
        selected["unqualified_assumption"] = True
    elif change == "bitwise":
        selected["reuse"] = "bitwise-fresh-execution-equivalence"
    elif change == "dtype":
        selected["providers"]["d1"]["dtype"] = "float32"
    elif change == "float-version":
        selected["version"] = 4.0
    else:
        del selected["providers"]["d1"]
    with pytest.raises(ValueError):
        d1().identity_projections(inference_policy=selected)


def test_policy_is_a_selected_semantic_determinant_not_the_other_provider_roster():
    selected = policy()
    expected = d1().identity_projections(inference_policy=selected)
    assert b"native-cuda-bfloat16-batch-observation-v1" in expected.inference.canonical_input
    selected["providers"]["gliner"]["numerical_contract"] = "unrelated-new-contract"
    assert d1().identity_projections(inference_policy=selected) == expected
    with pytest.raises(ValueError, match="qualified numerical"):
        pm2_selection("hanlp", Path("/captured-model"), {}, {}).native.identity_projections(
            inference_policy=policy()
        )


def test_top_level_and_nested_unknown_or_undeclared_fields_refuse(monkeypatch):
    original = d1()
    object.__setattr__(original, "_content", json.dumps({**original.wire, "new_field": 1}).encode())
    with pytest.raises(ValueError, match="complete identity"):
        original.identity_projections(inference_policy=policy())
    monkeypatch.setitem(NativeProfile.__init__.__annotations__, "threads", int)
    with pytest.raises(ValueError, match="declared identity role"):
        d1().identity_projections(inference_policy=policy())
    monkeypatch.undo()
    original = gliner()
    values = original.wire
    values["parameters"]["gliner_profile"]["future_resource"] = 1
    with pytest.raises(ValueError, match="complete identity"):
        NativeProfile(**values).identity_projections(inference_policy=policy())
    monkeypatch.setitem(GlinerProfile.__annotations__, "max_batch", int)
    with pytest.raises(ValueError, match="declared identity role"):
        gliner().identity_projections(inference_policy=policy())


def test_role_metadata_changes_no_legacy_profile_bytes_defaults_or_hashes():
    original = d1()
    expected = {
        "provider": "d1",
        "runtime_identity": {"torch": "captured-runtime"},
        "artifacts": {"model": "a" * 64},
        "parameters": {"adapter": "pm2-native-1"},
        "dtype": "bfloat16",
        "backend": "d1",
        "threads": 4,
        "interop_threads": 1,
        "device": "cuda",
        "matmul_precision": "highest",
        "cudnn_allow_tf32": False,
        "version": "nlp-gpu-profile-1",
    }
    encoded = json.dumps(
        expected, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    assert original.content == encoded
    assert original.fingerprint == sha256(encoded).hexdigest()
    assert NativeProfile.from_content(encoded) == original
    artifact_names = (
        "config.json",
        "encoder_config/config.json",
        "model.safetensors",
        "tokenizer.json",
        "tokenizer_config.json",
    )
    profile = GlinerProfile(
        Path("/captured-model"),
        "checkpoint",
        "immutable-revision",
        tuple((name, "a" * 64) for name in artifact_names),
    )
    assert asdict(profile)["threads"] == 4 and asdict(profile)["max_words"] == 512
    assert asdict(profile)["snapshot"] == Path("/captured-model")
