"""Protected attachment authenticates provider identity from producing custody."""

import json
from dataclasses import replace

import pytest
import yaml
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_identity import (
    ProfileField,
    canonical_identity,
    decode_semantic_value,
    profile_identities,
    semantic_value,
)
from corpus_structure.semantic.data_operation_runtime import validate_data_operation_runtime
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.runtime_bindings import RuntimeBindingError
from semantic.test_data_operation_pinned_reuse_native import (
    CONSUMER,
    PINNED,
    PRODUCER,
    _produce,
    _ready,
    _register,
)
from semantic.test_data_operation_transitive_read_native import _entry


def _profile_recipe():
    projections = profile_identities(
        (
            ProfileField("model", "native-test-provider", "semantic"),
            ProfileField("threads", 2, "execution"),
        )
    )
    profile = {
        "version": "provider-inference-profile-v1",
        "identity": projections.inference.key,
        "meaning": json.loads(projections.inference.canonical_input),
    }
    attestation = {
        "version": "provider-profile-attestation-v1",
        "identity": projections.inference.key,
        "meaning": profile["meaning"],
        "execution_identity": projections.execution.key,
        "execution_meaning": json.loads(projections.execution.canonical_input),
    }
    from hashlib import sha256

    profile_bytes = canonical_bytes(profile)
    assert PINNED.declaration_content is not None
    document = json.loads(PINNED.declaration_content)
    producer = next(op for op in document["operations"] if op["id"] == PRODUCER)
    producer["assets"] = [
        {
            "reference": "native-test-provider",
            "contract": "provider/profile",
            "role": "provider-inference-profile",
            "content_digest": sha256(profile_bytes).hexdigest(),
        }
    ]
    consumer = next(op for op in document["operations"] if op["id"] == CONSUMER)
    consumer["roles"][0]["support"]["identity_requirements"] = ["provider"]
    manifest = yaml.safe_load(PINNED.manifest_text)
    manifest["python"] = {
        "sources": [],
        "interpreter": "python-3.14",
        "interpretation": "closed-python-operations-v1",
        "stub_policy": "source-authoritative",
        "boundary_contracts": [
            {"name": "provider/profile", "path": "provider.json"},
            {"name": "provider/execution", "path": "provider-execution.json"},
        ],
    }
    return replace(
        PINNED,
        name="provider-selected-custody",
        declaration_content=canonical_bytes(document),
        manifest_text=yaml.safe_dump(manifest),
        additional_files=(
            ("provider.json", profile_bytes),
            (
                "provider-execution.json",
                canonical_bytes(
                    {
                        "selection": {"model": "native-test-provider", "threads": 2},
                        "provider_profile": attestation,
                    }
                ),
            ),
        ),
    ), profile


PROFILED, PROFILE = _profile_recipe()


@pytest.mark.db
@pytest.mark.parametrize("ddo_kernel", [PROFILED], indirect=True, ids=["provider-custody"])
def test_native_provider_selected_attachment_and_forgery_refusal(ddo_kernel):
    _, episode, _ = _produce(ddo_kernel, subject="subject:B", value=42)
    demand = _register(ddo_kernel, _entry(ddo_kernel, episode))
    _, (ready,) = _ready(ddo_kernel, demand)
    assert ready.binding_result.roles[0].members[0].provider_identity == PROFILE["identity"]
    with ddo_kernel["engine"].begin() as connection:
        with (
            pytest.raises(DBAPIError, match="exact native read acquisition"),
            connection.begin_nested(),
        ):
            connection.execute(
                text("SELECT * FROM ops.data_binding_rows(:demand,:operation,'{}'::jsonb)"),
                {"demand": demand["demand_id"], "operation": ready.operation},
            )
        assert (
            connection.scalar(
                text("SELECT ops.ddo_episode_provider_identity(:episode)"),
                {"episode": episode["derivation_id"]},
            )
            == PROFILE["identity"]
        )
        meaning = decode_semantic_value(json.loads(ready.request)[3])
        meaning["inputs"]["items"]["value"].value[0]["provider"] = "inference:forged"
        forged = canonical_identity("semantic-request", meaning)
        binding = json.loads(ready.binding)
        binding["request_inputs"] = semantic_value(meaning["inputs"])
        with (
            pytest.raises(DBAPIError, match="provider identity differs"),
            connection.begin_nested(),
        ):
            DataOperationStorage(connection).invoke(
                "attach_data_request",
                {
                    "obligation_id": ready.obligation,
                    "request_meaning": json.loads(forged.canonical_input),
                    "request_key": forged.key,
                    "binding": binding,
                    "replicate": None,
                },
            )


@pytest.mark.parametrize("ddo_kernel", [PROFILED], indirect=True, ids=["provider-runtime"])
def test_profiled_runtime_refuses_missing_forged_or_historical_profile_attestation(ddo_kernel):
    from hashlib import sha256

    binding = ddo_kernel.preparation.runtime
    for mutation in ("missing", "forged", "historical"):
        manifest = json.loads(binding.manifest)
        if mutation == "missing":
            manifest["provider_profiles"] = {}
        elif mutation == "forged":
            manifest["provider_profiles"][PRODUCER]["attestation"]["identity"] = "inference:forged"
        else:
            manifest.pop("provider_profiles")
            manifest["version"] = "data-operation-runtime-binding-v1"
        content = canonical_bytes(manifest)
        with pytest.raises(RuntimeBindingError, match=r"profile|attestation|historical"):
            validate_data_operation_runtime(
                replace(
                    binding, runtime_id="runtime:" + sha256(content).hexdigest(), manifest=content
                ),
                ddo_kernel["prepared"],
            )


def _unprofiled_recipe():
    assert PINNED.declaration_content is not None
    document = json.loads(PINNED.declaration_content)
    consumer = next(
        operation for operation in document["operations"] if operation["id"] == CONSUMER
    )
    consumer["roles"][0]["support"]["identity_requirements"] = ["provider"]
    return replace(
        PINNED,
        name="missing-producing-provider-custody",
        declaration_content=canonical_bytes(document),
    )


UNPROFILED = _unprofiled_recipe()


@pytest.mark.db
@pytest.mark.parametrize("ddo_kernel", [UNPROFILED], indirect=True, ids=["unprofiled-event"])
def test_producing_event_without_captured_profile_cannot_satisfy_provider_sensitive_role(
    ddo_kernel,
):
    _, episode, _ = _produce(ddo_kernel, subject="subject:B", value=42)
    with ddo_kernel["engine"].connect() as connection:
        assert (
            connection.scalar(
                text("SELECT ops.ddo_episode_provider_identity(:episode)"),
                {"episode": episode["derivation_id"]},
            )
            is None
        )
    demand = _register(ddo_kernel, _entry(ddo_kernel, episode))
    _, ready = _ready(ddo_kernel, demand)
    assert ready == ()
