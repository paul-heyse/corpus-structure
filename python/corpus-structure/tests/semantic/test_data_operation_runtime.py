"""Runtime artifact, release attestation and exact source custody stay distinct."""

import json
from dataclasses import replace

import pytest

from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_runtime import prepare_data_operation_runtime
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.runtime_bindings import RuntimeBindingError, validate_runtime_binding
from corpus_structure.semantic.types import ResolvedDependencies, SourceArtifact, SourceBundle


def prepared():
    bundle = SourceBundle(
        "tiny",
        (
            SourceArtifact(
                "tiny",
                b"""id: urn:tiny
name: tiny
prefixes: {t: 'urn:tiny:'}
default_prefix: t
classes: {Thing: {}}
""",
            ),
        ),
    )
    deps = data_operation_dependencies(ResolvedDependencies(), ())
    return prepare_release(bundle, deps)


def test_target_runtime_reuses_artifact_across_releases_but_attests_each_release():
    first = prepared()
    sources = (SourceArtifact("worker.py", b"def run(): return 1\n"),)
    binding = prepare_data_operation_runtime(
        first, sources, execution_profile="execution:one", observed={"device": "cuda"}
    )
    validate_runtime_binding(binding, first)
    # A distinct admitted release can retain the same executable artifact.
    manifest = json.loads(first.manifest)
    manifest["root"] = "another"
    manifest_bytes = canonical_bytes(manifest)
    from hashlib import sha256

    second = replace(
        first, manifest=manifest_bytes, release_id="release:" + sha256(manifest_bytes).hexdigest()
    )
    other = prepare_data_operation_runtime(
        second, sources, execution_profile="execution:one", observed={"device": "cuda"}
    )
    a, b = json.loads(binding.manifest), json.loads(other.manifest)
    assert a["runtime_artifact"] == b["runtime_artifact"]
    assert a["attestation"] != b["attestation"]
    assert binding.runtime_id != other.runtime_id


def test_target_runtime_rejects_changed_bytes_and_detached_attestation():
    release = prepared()
    binding = prepare_data_operation_runtime(
        release,
        (SourceArtifact("worker.py", b"one"),),
        execution_profile="execution:one",
        observed={},
    )
    archive = json.loads(binding.archive)
    archive["inputs"][0]["content_hex"] = b"two".hex()
    with pytest.raises(RuntimeBindingError, match="bytes"):
        validate_runtime_binding(replace(binding, archive=canonical_bytes(archive)), release)
    with pytest.raises(RuntimeBindingError, match="identity"):
        validate_runtime_binding(replace(binding, runtime_id="runtime:wrong"), release)
