"""Captured inference meaning and exact runtime profile attestations.

A semantic asset owns the provider projection. Runtime manifests attest an acquired
execution projection; neither caller inference strings nor current request settings
can supply an input's original producing profile.
"""
from __future__ import annotations

import json

from .data_operation_identity import canonical_identity, decode_semantic_value
from .identity import canonical_bytes
from .types import SourceArtifact

ROLE = "provider-inference-profile"
VERSION = "provider-inference-profile-v1"
EXECUTION_VERSION = "provider-profile-attestation-v1"


def _identity(key, meaning, domain):
    if not isinstance(meaning, list) or len(meaning) != 4 or meaning[:3] != ["ddo", domain, "1"]:
        raise ValueError("provider projection domain differs")
    # canonical_identity owns the envelope; decoding preserves tagged numeric meaning.
    expected = canonical_identity(domain, decode_semantic_value(meaning[3]))
    if expected.key != key or json.loads(expected.canonical_input) != meaning:
        raise ValueError("provider projection identity differs from canonical meaning")


def profile_asset(name, selection, policy):
    projections = selection.native.identity_projections(inference_policy=policy)
    return SourceArtifact(name, canonical_bytes({
        "version": VERSION,
        "identity": projections.inference.key,
        "meaning": json.loads(projections.inference.canonical_input),
    }))


def profile_attestation(selection, policy):
    projections = selection.native.identity_projections(inference_policy=policy)
    return {
        "version": EXECUTION_VERSION,
        "identity": projections.inference.key,
        "meaning": json.loads(projections.inference.canonical_input),
        "execution_identity": projections.execution.key,
        "execution_meaning": json.loads(projections.execution.canonical_input),
    }


def checked_profile(content):
    value = json.loads(content)
    if not isinstance(value, dict) or set(value) != {"version", "identity", "meaning"} or value["version"] != VERSION:
        raise ValueError("unsupported captured provider profile")
    _identity(value["identity"], value["meaning"], "inference")
    if canonical_bytes(value) != content:
        raise ValueError("provider profile is not canonical captured content")
    return value


def checked_attestation(value, profile):
    if not isinstance(value, dict) or set(value) != {"version", "identity", "meaning", "execution_identity", "execution_meaning"} or value["version"] != EXECUTION_VERSION:
        raise ValueError("unsupported provider execution attestation")
    if (value["identity"], value["meaning"]) != (profile["identity"], profile["meaning"]):
        raise ValueError("provider execution meaning differs from captured semantic profile")
    _identity(value["execution_identity"], value["execution_meaning"], "execution-profile")
    fields = decode_semantic_value(value["execution_meaning"][3])
    if not isinstance(fields, dict) or any(not isinstance(row, dict) or set(row) != {"role", "value"} or row["role"] not in {"semantic", "execution"} for row in fields.values()):
        raise ValueError("provider execution field roles differ")
    semantic = {name: row["value"] for name, row in fields.items() if row["role"] == "semantic"}
    from .data_operation_identity import semantic_fields
    expected = canonical_identity("inference", semantic_fields(semantic.items()))
    if expected.key != profile["identity"]:
        raise ValueError("execution profile semantic fields differ from provider profile")
    return value


def operation_profile(operation, contracts):
    selected = [asset for asset in operation.assets if asset.role == ROLE]
    if not selected:
        return None
    if len(selected) != 1:
        raise ValueError("operation must have one captured provider profile")
    asset = selected[0]
    supplied = {source.name: source for source in contracts}
    source = supplied.get(asset.contract)
    if source is None or source.digest != asset.content_digest:
        raise ValueError("provider profile lacks exact captured asset custody")
    return {**checked_profile(source.content), "contract": asset.contract, "sha256": source.digest}


def runtime_profiles(model, sources):
    """Resolve only explicitly supplied runtime archive inputs, never ambient resources."""
    contracts = tuple(SourceArtifact(source.name.removeprefix("data-operations/contracts/"), source.content)
        for source in sources if source.name.startswith("data-operations/contracts/"))
    result = {}
    for operation in model.operations:
        profile = operation_profile(operation, contracts)
        if profile is None:
            continue
        matches = []
        for source in contracts:
            try:
                document = json.loads(source.content)
            except (ValueError, UnicodeDecodeError):
                continue
            if isinstance(document, dict) and "provider_profile" in document:
                candidate = document["provider_profile"]
                if isinstance(candidate, dict) and candidate.get("identity") == profile["identity"]:
                    matches.append((source, checked_attestation(candidate, profile)))
        if len(matches) != 1:
            raise ValueError("provider operation requires one exact runtime profile attestation")
        source, attestation = matches[0]
        result[operation.semantic_id] = {"profile": profile, "attestation": attestation,
            "runtime_contract": source.name, "runtime_sha256": source.digest}
    return result
