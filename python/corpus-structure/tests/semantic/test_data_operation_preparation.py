"""Explicit target acquisition and archive fidelity, independent of installed defaults."""

from __future__ import annotations

import json
from dataclasses import asdict
from hashlib import sha256

import pytest

from corpus_structure.semantic.archive_reader import open_release_parts
from corpus_structure.semantic.data_operation_preparation import (
    acquire_data_operation_inputs,
    prepare_data_operation_inputs,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.releases import _archive_bytes, _validate_manifest


def inputs(tmp_path):
    (tmp_path / "schema.yaml").write_text("""id: urn:target
name: target
prefixes:
  t: 'urn:target:'
default_prefix: t
classes:
  Thing:
    description: Explicit target input
""")
    (tmp_path / "operations.yaml").write_text(
        "version: data-operation-model-v1\noperations: []\nkinds: []\n"
    )
    (tmp_path / "target.yaml").write_text("""version: data-operation-inputs-v1
root: target
schemas: [{name: target, path: schema.yaml}]
declarations: [{name: operations, path: operations.yaml}]
""")
    return tmp_path


def test_target_preparation_archives_without_legacy_acquisition(tmp_path):
    root = inputs(tmp_path)
    bundle, deps, profile, prepared = prepare_data_operation_inputs(root, "target.yaml")
    assert prepared.execution_model_id is None
    assert not any(a.name.startswith("execution/") for a in deps.artifacts)
    _validate_manifest(bundle, deps, profile, prepared)
    archive = _archive_bytes(bundle, deps, prepared)
    source_rows = [
        {
            "input_kind": kind,
            "input_name": source.name,
            "content": source.content,
            "content_digest": source.digest,
        }
        for kind, sources in (("source", bundle.sources), ("dependency", deps.artifacts))
        for source in sources
    ]
    for kind, content in (
        ("profile", canonical_bytes(asdict(profile))),
        ("vocabulary", canonical_bytes([asdict(v) for v in deps.vocabularies])),
        ("ontology_sources", canonical_bytes(list(deps.ontology_sources))),
    ):
        source_rows.append(
            {
                "input_kind": kind,
                "input_name": kind,
                "content": content,
                "content_digest": sha256(content).hexdigest(),
            }
        )
    artifacts = [
        {
            "artifact_name": a.kind,
            "content": a.content,
            "content_digest": a.digest,
            "media_type": "application/octet-stream",
        }
        for a in prepared.artifacts
    ]
    opened = open_release_parts(
        prepared.release_id,
        {
            "prepared_bytes": archive,
            "manifest_bytes": prepared.manifest,
            "content_digest": sha256(archive).hexdigest(),
            "profile": profile.version,
        },
        source_rows,
        artifacts,
    )
    assert opened.manifest == prepared.manifest
    assert opened.artifacts == prepared.artifacts
    assert json.loads(opened.manifest)["data_operation_model"]


@pytest.mark.parametrize("path", ["../outside", "/etc/passwd", "missing"])
def test_target_acquisition_refuses_escaped_or_unavailable_files(tmp_path, path):
    root = inputs(tmp_path)
    declaration = (root / "target.yaml").read_text().replace("schema.yaml", path)
    (root / "target.yaml").write_text(declaration)
    with pytest.raises(ValueError, match="input"):
        acquire_data_operation_inputs(root, "target.yaml")


def test_target_acquisition_pins_python_bytes_without_importing(tmp_path):
    root = inputs(tmp_path)
    (root / "never.py").write_text("raise RuntimeError('must not import')\n")
    with (root / "target.yaml").open("a") as output:
        output.write("""python:
  interpreter: python-3.14
  interpretation: closed-python-operations-v1
  stub_policy: source-authoritative
  sources: [{module: never, path: never.py}]
""")
    acquired = acquire_data_operation_inputs(root, "target.yaml")
    assert dict(acquired.files)["never.py"].startswith(b"raise RuntimeError")
    assert any(a.name.endswith("python/0.py") for a in acquired.dependencies.artifacts)


def test_target_acquisition_archives_generated_interface_selection(tmp_path):
    root = inputs(tmp_path)
    (root / "model.py").write_text("from dataclasses import dataclass\n@dataclass\nclass Item:\n    value: int\n")
    with (root / "target.yaml").open("a") as output:
        output.write("""python:
  interpreter: python-3.14
  interpretation: closed-python-operations-v1
  stub_policy: source-authoritative
  generated_interfaces: [dataclasses]
  sources: [{module: model, path: model.py}]
""")
    bundle, deps, profile, prepared = prepare_data_operation_inputs(root, "target.yaml")
    manifest = next(a for a in deps.artifacts if a.name.endswith("data-operations/manifest.json"))
    assert json.loads(manifest.content)["python"]["generated_interfaces"] == ["dataclasses"]
    _validate_manifest(bundle, deps, profile, prepared)
