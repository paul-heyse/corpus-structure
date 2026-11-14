"""Exact target runtime custody, separate from recipe equality and release identity."""

from __future__ import annotations

import json
import sys
from hashlib import sha256

from .data_operation_admission import bound_data_operation_model
from .data_operation_identity import execution_attestation, runtime_artifact_identity
from .identity import canonical_bytes
from .runtime_bindings import RuntimeBinding, RuntimeBindingError, _document, _inputs
from .types import PreparedRelease, SourceArtifact

VERSION = "data-operation-runtime-binding-v2"
HISTORICAL_VERSION = "data-operation-runtime-binding-v1"


def _required_inputs(prepared: PreparedRelease) -> list[dict[str, str]]:
    artifacts = [a for a in prepared.artifacts if a.kind == "data_operation_runtime_inputs.json"]
    if len(artifacts) != 1:
        raise RuntimeBindingError("target release lacks captured executable input requirements")
    return json.loads(artifacts[0].content)


def prepare_data_operation_runtime(
    prepared: PreparedRelease,
    inputs: tuple[SourceArtifact, ...],
    *,
    execution_profile: str,
    observed: dict,
    python_version: str = sys.version,
) -> RuntimeBinding:
    """Capture supplied executable bytes. Acquisition is the caller's explicit operation."""
    if not execution_profile or not python_version:
        raise RuntimeBindingError("target runtime requires execution profile and interpreter")
    model = bound_data_operation_model(prepared)
    sources = _inputs(inputs)
    identities = [{"name": source.name, "sha256": source.digest} for source in sources]
    artifact = runtime_artifact_identity({"python": python_version, "inputs": identities})
    attestation = execution_attestation(
        runtime_artifact=artifact.key,
        release=prepared.release_id,
        execution_profile=execution_profile,
        observed=observed,
    )
    from .data_operation_provider_profiles import runtime_profiles

    profiles = runtime_profiles(model, sources)
    manifest = canonical_bytes(
        {
            "version": VERSION,
            "provider_profiles": profiles,
            "release_id": prepared.release_id,
            "model_digest": sha256(model.content).hexdigest(),
            "python_version": python_version,
            "semantic_inputs": _required_inputs(prepared),
            "implementation_inputs": identities,
            "runtime_artifact": artifact.key,
            "runtime_meaning": json.loads(artifact.canonical_input),
            "attestation": attestation.key,
            "attestation_meaning": json.loads(attestation.canonical_input),
            "execution_profile": execution_profile,
            "observed": observed,
        }
    )
    archive = canonical_bytes(
        {
            "version": "runtime-source-archive-1",
            "inputs": [
                {"name": source.name, "sha256": source.digest, "content_hex": source.content.hex()}
                for source in sources
            ],
        }
    )
    binding = RuntimeBinding(
        prepared.release_id, "runtime:" + sha256(manifest).hexdigest(), manifest, archive
    )
    validate_data_operation_runtime(binding, prepared)
    return binding


def validate_data_operation_runtime(binding: RuntimeBinding, prepared: PreparedRelease) -> None:
    model = bound_data_operation_model(prepared)
    try:
        raw = json.loads(binding.manifest)
    except (TypeError, ValueError) as error:
        raise RuntimeBindingError("target runtime manifest is not JSON") from error
    if not isinstance(raw, dict):
        raise RuntimeBindingError("target runtime manifest requires an object")
    manifest = _document(
        binding.manifest,
        {
            "version",
            *(("provider_profiles",) if raw.get("version") == VERSION else ()),
            "release_id",
            "model_digest",
            "python_version",
            "semantic_inputs",
            "implementation_inputs",
            "runtime_artifact",
            "runtime_meaning",
            "attestation",
            "attestation_meaning",
            "execution_profile",
            "observed",
        },
    )
    archive = _document(binding.archive, {"version", "inputs"})
    if (
        manifest["version"] not in {VERSION, HISTORICAL_VERSION}
        or archive["version"] != "runtime-source-archive-1"
        or manifest["release_id"] != prepared.release_id
        or binding.release_id != prepared.release_id
        or manifest["model_digest"] != sha256(model.content).hexdigest()
        or binding.runtime_id != "runtime:" + sha256(binding.manifest).hexdigest()
    ):
        raise RuntimeBindingError("target runtime release, model or identity differs")
    try:
        if not isinstance(manifest["python_version"], str) or not manifest["python_version"]:
            raise ValueError("target runtime interpreter is missing")
        if not isinstance(manifest["execution_profile"], str) or not manifest["execution_profile"]:
            raise ValueError("target runtime execution profile is missing")
        sources = []
        for item in archive["inputs"]:
            if set(item) != {"name", "sha256", "content_hex"} or not item["name"]:
                raise ValueError("target runtime input shape differs")
            source = SourceArtifact(item["name"], bytes.fromhex(item["content_hex"]))
            if source.digest != item["sha256"] or source.content.hex() != item["content_hex"]:
                raise ValueError("target runtime input bytes differ")
            sources.append(source)
        ordered = _inputs(tuple(sources))
        actual = [{"name": source.name, "sha256": source.digest} for source in ordered]
        required = _required_inputs(prepared)
        if (
            sources != list(ordered)
            or manifest["implementation_inputs"] != actual
            or manifest["semantic_inputs"] != required
            or not {(item["name"], item["sha256"]) for item in required}
            <= {(item["name"], item["sha256"]) for item in actual}
        ):
            raise ValueError("target runtime does not retain its captured implementation inputs")
        from .data_operation_provider_profiles import runtime_profiles
        profiles = runtime_profiles(model, tuple(sources))
        if manifest["version"] == HISTORICAL_VERSION:
            if profiles:
                raise ValueError("historical runtime cannot attest provider profiles")
        elif manifest["provider_profiles"] != profiles:
            raise ValueError("runtime provider profile differs from captured inputs")
        artifact = runtime_artifact_identity(
            {"python": manifest["python_version"], "inputs": actual}
        )
        attestation = execution_attestation(
            runtime_artifact=artifact.key,
            release=prepared.release_id,
            execution_profile=manifest["execution_profile"],
            observed=manifest["observed"],
        )
        if (
            manifest["runtime_artifact"] != artifact.key
            or canonical_bytes(manifest["runtime_meaning"]) != artifact.canonical_input
            or manifest["attestation"] != attestation.key
            or canonical_bytes(manifest["attestation_meaning"]) != attestation.canonical_input
        ):
            raise ValueError("target runtime artifact or release attestation differs")
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeBindingError(str(error)) from error
