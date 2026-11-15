"""Runtime artifact, release attestation and exact source custody stay distinct."""

import json
from dataclasses import replace

import pytest

from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_runtime import prepare_data_operation_runtime
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.data_operation_runtime import RuntimeBindingError, validate_data_operation_runtime
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
    validate_data_operation_runtime(binding, first)
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
        validate_data_operation_runtime(replace(binding, archive=canonical_bytes(archive)), release)
    with pytest.raises(RuntimeBindingError, match="identity"):
        validate_data_operation_runtime(replace(binding, runtime_id="runtime:wrong"), release)


def test_unprofiled_historical_runtime_v1_is_refused():
    from hashlib import sha256

    release = prepared()
    binding = prepare_data_operation_runtime(
        release,
        (SourceArtifact("worker.py", b"one"),),
        execution_profile="execution:one",
        observed={},
    )
    manifest = json.loads(binding.manifest)
    assert manifest.pop("provider_profiles") == {}
    manifest["version"] = "data-operation-runtime-binding-v1"
    content = canonical_bytes(manifest)
    historical = replace(
        binding, runtime_id="runtime:" + sha256(content).hexdigest(), manifest=content
    )
    with pytest.raises(RuntimeBindingError, match="runtime version"):
        validate_data_operation_runtime(historical, release)


def test_current_runtime_persistence_has_no_legacy_facade_dependency(monkeypatch):
    import sys
    from unittest.mock import MagicMock

    from corpus_structure.semantic.runtime_binding_store import persist_runtime_binding

    release = prepared()
    binding = prepare_data_operation_runtime(
        release,
        (SourceArtifact("worker.py", b"one"),),
        execution_profile="execution:one",
        observed={},
    )
    connection = MagicMock()
    connection.scalar.return_value = binding.runtime_id
    monkeypatch.setitem(sys.modules, "corpus_structure.semantic._operation_calls", None)
    assert persist_runtime_binding(connection, release, binding) == binding.runtime_id
    parameters = connection.scalar.call_args.args[1]
    assert parameters == {
        "release": release.release_id,
        "runtime": binding.runtime_id,
        "manifest": binding.manifest,
        "archive": binding.archive,
    }
    connection.scalar.return_value = "runtime:foreign"
    with pytest.raises(RuntimeBindingError, match="different runtime identity"):
        persist_runtime_binding(connection, release, binding)


def test_current_runtime_persistence_refuses_historical_manifest_before_effects():
    from hashlib import sha256
    from unittest.mock import MagicMock

    from corpus_structure.semantic.runtime_binding_store import persist_runtime_binding

    release = prepared()
    binding = prepare_data_operation_runtime(
        release,
        (SourceArtifact("worker.py", b"one"),),
        execution_profile="execution:one",
        observed={},
    )
    manifest = json.loads(binding.manifest)
    manifest["version"] = "data-operation-runtime-binding-v1"
    manifest.pop("provider_profiles")
    content = canonical_bytes(manifest)
    historical = replace(
        binding, runtime_id="runtime:" + sha256(content).hexdigest(), manifest=content
    )
    connection = MagicMock()
    with pytest.raises(RuntimeBindingError, match="runtime version"):
        persist_runtime_binding(connection, release, historical)
    connection.scalar.assert_not_called()


@pytest.mark.parametrize("version", ["data-operation-runtime-binding-v1", "runtime-binding-1"])
def test_native_runtime_validator_refuses_previous_versions(native_rollback, version):
    from pathlib import Path

    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    from corpus_structure.semantic import runtime_binding_store
    from corpus_structure.semantic.prepared_sql import prepare_sql

    connection = native_rollback.connection
    source = (
        Path(runtime_binding_store.__file__)
        .with_name("sql")
        .joinpath("runtime_bindings.sql")
        .read_text()
    )
    validator = prepare_sql(source, source="current-runtime-validator").excerpt(0)
    connection.exec_driver_sql(validator, execution_options={"no_parameters": True})
    with (
        pytest.raises(DBAPIError, match="unsupported target runtime version") as refusal,
        connection.begin_nested(),
    ):
        connection.execute(
            text("SELECT sem.validate_runtime_binding(:release,:runtime,:manifest,:archive)"),
            {
                "release": "absent-release",
                "runtime": "runtime:untrusted",
                "manifest": canonical_bytes({"version": version}),
                "archive": canonical_bytes({"version": "runtime-source-archive-1", "inputs": []}),
            },
        )
    assert getattr(refusal.value.orig, "sqlstate", None) == "23514"
