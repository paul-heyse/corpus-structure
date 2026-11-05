"""Exact executable provenance, separate from a semantic release's data meaning.

Acquisition is explicit at an execution boundary. Semantic preparation consumes only declared
model/grammar/output-contract assets; runtime archives retain every executable input as well.
An archived fingerprint establishes custody, not that source bytes executed or produced truth.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from .identity import canonical_bytes
from .refusals import SemanticRefusal
from .types import PreparedRelease, SourceArtifact


class RuntimeBindingError(SemanticRefusal):
    """Runtime custody or its explicit semantic compatibility cannot be established."""


def _inputs(inputs: tuple[SourceArtifact, ...] | None) -> tuple[SourceArtifact, ...]:
    if inputs is None:
        from .contracts import analysis_implementation_inputs

        inputs = analysis_implementation_inputs()
    if len({item.name for item in inputs}) != len(inputs):
        raise RuntimeBindingError("runtime input names must be unique")
    return tuple(sorted(inputs, key=lambda item: item.name))


def runtime_implementation_digests(
    inputs: tuple[SourceArtifact, ...] | None = None,
) -> tuple[tuple[str, str], ...]:
    return tuple((item.name, item.digest) for item in _inputs(inputs))


def runtime_fingerprint(
    inputs: tuple[SourceArtifact, ...] | None = None,
    *,
    digests: tuple[tuple[str, str], ...] | None = None,
) -> str:
    """Unbound computation/cache identity; it never replaces the semantic release identity."""
    if inputs is not None and digests is not None:
        raise ValueError("supply runtime inputs or their digests, not both")
    captured = runtime_implementation_digests(inputs) if digests is None else tuple(sorted(digests))
    return (
        "runtime-code:"
        + sha256(
            canonical_bytes(
                {"version": "runtime-code-1", "python": sys.version, "inputs": captured}
            )
        ).hexdigest()
    )


def _document(content: bytes, keys: set[str]) -> dict[str, Any]:
    try:
        value = json.loads(content)
    except ValueError as error:
        raise RuntimeBindingError("runtime archive is not JSON") from error
    if not isinstance(value, dict) or set(value) != keys or canonical_bytes(value) != content:
        raise RuntimeBindingError("runtime archive has a noncanonical or unsupported shape")
    return value


@dataclass(frozen=True)
class RuntimeBinding:
    release_id: str
    runtime_id: str
    manifest: bytes
    archive: bytes

    @property
    def implementation_digests(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            (item["name"], item["sha256"])
            for item in json.loads(self.manifest)["implementation_inputs"]
        )

    def input(self, name: str) -> SourceArtifact:
        for item in json.loads(self.archive)["inputs"]:
            if item["name"] == name:
                return SourceArtifact(name, bytes.fromhex(item["content_hex"]))
        raise RuntimeBindingError("runtime source input is unavailable: " + name)


def _execution(prepared: PreparedRelease):
    from .contracts import bound_execution_model, execution_payload

    payload = execution_payload(prepared)
    if payload is None:
        raise RuntimeBindingError("runtime binding requires a composed semantic release")
    return bound_execution_model(prepared), json.loads(payload)["inputs"]["compiler_version"]


def _manifest(
    prepared: PreparedRelease,
    inputs: tuple[SourceArtifact, ...],
    *,
    python_version: str,
) -> bytes:
    model, compiler = _execution(prepared)
    sources = _inputs(inputs)
    return canonical_bytes(
        {
            "version": "runtime-binding-1",
            "release_id": prepared.release_id,
            "execution_model_id": model.model_id,
            "execution_compiler_version": compiler,
            "python_version": python_version,
            "semantic_inputs": [
                {"name": name, "sha256": digest}
                for name, digest in sorted(model.implementation_digests)
            ],
            "implementation_inputs": [
                {"name": item.name, "sha256": item.digest} for item in sources
            ],
        }
    )


def _binding(
    prepared: PreparedRelease,
    inputs: tuple[SourceArtifact, ...],
    *,
    python_version: str,
) -> RuntimeBinding:
    sources = _inputs(inputs)
    manifest = _manifest(prepared, sources, python_version=python_version)
    archive = canonical_bytes(
        {
            "version": "runtime-source-archive-1",
            "inputs": [
                {"name": item.name, "sha256": item.digest, "content_hex": item.content.hex()}
                for item in sources
            ],
        }
    )
    binding = RuntimeBinding(
        prepared.release_id, "runtime:" + sha256(manifest).hexdigest(), manifest, archive
    )
    validate_runtime_binding(binding, prepared)
    return binding


def validate_runtime_binding(binding: RuntimeBinding, prepared: PreparedRelease) -> None:
    """Authenticate exact retained bytes and their released meaning, without installed defaults."""
    model, compiler = _execution(prepared)
    manifest = _document(
        binding.manifest,
        {
            "version",
            "release_id",
            "execution_model_id",
            "execution_compiler_version",
            "python_version",
            "semantic_inputs",
            "implementation_inputs",
        },
    )
    archive = _document(binding.archive, {"version", "inputs"})
    if (
        manifest["version"] != "runtime-binding-1"
        or archive["version"] != "runtime-source-archive-1"
        or binding.release_id != prepared.release_id
        or manifest["release_id"] != prepared.release_id
        or manifest["execution_model_id"] != model.model_id
        or manifest["execution_compiler_version"] != compiler
        or not isinstance(manifest["python_version"], str)
        or not manifest["python_version"]
        or binding.runtime_id != "runtime:" + sha256(binding.manifest).hexdigest()
    ):
        raise RuntimeBindingError("runtime binding differs from its identity or semantic release")
    try:
        if not isinstance(archive["inputs"], list) or not isinstance(
            manifest["implementation_inputs"], list
        ):
            raise ValueError("runtime input collections must be arrays")
        sources = []
        for item in archive["inputs"]:
            if set(item) != {"name", "sha256", "content_hex"} or not isinstance(item["name"], str):
                raise ValueError("runtime source shape differs")
            source = SourceArtifact(item["name"], bytes.fromhex(item["content_hex"]))
            if (
                not source.name
                or source.digest != item["sha256"]
                or source.content.hex() != item["content_hex"]
            ):
                raise ValueError("runtime source digest differs")
            sources.append(source)
        ordered = _inputs(tuple(sources))
        expected = [{"name": item.name, "sha256": item.digest} for item in ordered]
        semantic = [
            {"name": name, "sha256": digest}
            for name, digest in sorted(model.implementation_digests)
        ]
        if (
            sources != list(ordered)
            or manifest["implementation_inputs"] != expected
            or manifest["semantic_inputs"] != semantic
            or not set(model.implementation_digests)
            <= {(item.name, item.digest) for item in ordered}
        ):
            raise ValueError("runtime source set or semantic determinants differ")
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeBindingError(str(error)) from error


def _qualified_inputs(
    prepared: PreparedRelease, inputs: tuple[SourceArtifact, ...] | None = None
) -> tuple[SourceArtifact, ...]:
    from .contracts import EXECUTION_COMPILER_VERSION, semantic_implementation_inputs

    model, compiler = _execution(prepared)
    if compiler != EXECUTION_COMPILER_VERSION:
        raise RuntimeBindingError("historical execution bindings are read-only")
    sources = _inputs(inputs)
    semantic = semantic_implementation_inputs(sources)
    if tuple(sorted((item.name, item.digest) for item in semantic)) != tuple(
        sorted(model.implementation_digests)
    ):
        raise RuntimeBindingError("runtime semantic assets differ from the released contract")
    for operation in model.operations:
        if operation.implementation is not None:
            model.require_operation(operation.id)
    return sources


def installed_runtime_id(
    prepared: PreparedRelease, inputs: tuple[SourceArtifact, ...] | None = None
) -> str:
    """Check execution compatibility without rendering or hydrating its source archive again."""
    manifest = _manifest(prepared, _qualified_inputs(prepared, inputs), python_version=sys.version)
    return "runtime:" + sha256(manifest).hexdigest()


def prepare_runtime_binding(
    prepared: PreparedRelease, inputs: tuple[SourceArtifact, ...] | None = None
) -> RuntimeBinding:
    return _binding(prepared, _qualified_inputs(prepared, inputs), python_version=sys.version)


def require_installed_runtime(
    prepared: PreparedRelease, binding: RuntimeBinding | None = None
) -> RuntimeBinding:
    if binding is not None:
        validate_runtime_binding(binding, prepared)
        if binding.runtime_id != installed_runtime_id(prepared):
            raise RuntimeBindingError("installed runtime differs from the archived execution pin")
        return binding
    return prepare_runtime_binding(prepared)


def legacy_runtime_binding(
    prepared: PreparedRelease, inputs: tuple[SourceArtifact, ...]
) -> RuntimeBinding:
    """Read legacy provenance exclusively from its archive; this cannot authorize execution."""
    from .contracts import EXECUTION_COMPILER_VERSION

    model, compiler = _execution(prepared)
    if compiler == EXECUTION_COMPILER_VERSION:
        raise RuntimeBindingError("current execution requires its explicit immutable runtime pin")
    sources = _inputs(inputs)
    if tuple(sorted(model.implementation_digests)) != tuple(
        (item.name, item.digest) for item in sources
    ):
        raise RuntimeBindingError("legacy runtime source custody is incomplete")
    try:
        python_version = json.loads(prepared.manifest)["libraries"]["python"]
    except (ValueError, KeyError, TypeError) as error:
        raise RuntimeBindingError("legacy interpreter provenance is unavailable") from error
    return _binding(prepared, sources, python_version=python_version)
