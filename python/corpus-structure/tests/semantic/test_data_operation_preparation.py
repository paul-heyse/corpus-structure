"""Explicit target acquisition and archive fidelity, independent of installed defaults."""

from __future__ import annotations

import json
from dataclasses import asdict
from hashlib import sha256

import pytest

from corpus_structure.semantic.archive_reader import open_release_parts
from corpus_structure.semantic.data_operation_model import MODEL_VERSION
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
        "version: " + MODEL_VERSION + "\noperations: []\nkinds: []\n"
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
    (root / "model.py").write_text(
        "from dataclasses import dataclass\n@dataclass\nclass Item:\n    value: int\n"
    )
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


def test_consumer_projection_schema_is_explicitly_acquired_and_archived(tmp_path):
    root = inputs(tmp_path)
    with (root / "target.yaml").open("a") as stream:
        stream.write("consumer_bindings: true\n")
    bundle, _, _, prepared = prepare_data_operation_inputs(root, "target.yaml")
    assert bundle.root == "data_operation_consumer_target"
    assert "data_operation_consumers" in {source.name for source in bundle.sources}
    effective = json.loads(
        next(
            artifact.content
            for artifact in prepared.artifacts
            if artifact.kind == "data_operations.json"
        )
    )
    names = {kind["name"] for kind in effective["kinds"]}
    assert {
        "DdoSourceViewBinding",
        "DdoPassageBinding",
        "DdoReadingBinding",
        "DdoOccurrenceBinding",
        "DdoAnchorBinding",
    } <= names
    fields = {kind["semantic_id"] for kind in effective["kinds"] if kind["category"] == "property"}
    assert any(name.endswith("DdoSourceViewBinding/property/document_subject") for name in fields)


def test_actual_colocated_consumer_contracts_are_captured_without_imports(tmp_path):
    from pathlib import Path

    root = inputs(tmp_path)
    methods = Path(__file__).resolve().parents[2] / "src/corpus_structure/methods"
    names = ("native_evidence", "m1_source", "structural_products", "contextual_candidates")
    for name in names:
        (root / (name + ".py")).write_bytes((methods / (name + ".py")).read_bytes())
    with (root / "target.yaml").open("a") as stream:
        stream.write(
            "consumer_bindings: true\npython:\n  interpreter: python-3.14\n"
            "  interpretation: closed-python-operations-v1\n"
            "  stub_policy: source-authoritative\n  sources:\n"
        )
        for name in names:
            stream.write(f"    - {{module: 'consumer.{name}', path: '{name}.py'}}\n")
    _, _, _, prepared = prepare_data_operation_inputs(root, "target.yaml")
    model = json.loads(
        next(
            artifact.content
            for artifact in prepared.artifacts
            if artifact.kind == "data_operations.json"
        )
    )
    operations = {operation["semantic_id"]: operation for operation in model["operations"]}
    assert {
        "text.native_evidence/selection",
        "extract.m1_candidates/selection",
        "structure.compare/selection",
        "retrieve.contextual/selection",
    } <= operations.keys()
    assert operations["text.native_evidence/selection"]["profile"] == "selection"
    assert (
        operations["text.native_evidence/selection"]["roles"][0]["subject_field"]
        == "document_subject"
    )


def test_original_source_schema_is_explicitly_acquired_for_native_admission(tmp_path):
    root = inputs(tmp_path)
    from pathlib import Path

    core = Path(__file__).resolve().parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    (root / "core.yaml").write_bytes(core.read_bytes())
    schema = (
        (root / "schema.yaml")
        .read_text()
        .replace("name: target\n", "name: target\nimports: [core]\n")
    )
    (root / "schema.yaml").write_text(schema)
    declaration = (
        (root / "target.yaml")
        .read_text()
        .replace(
            "schemas: [{name: target, path: schema.yaml}]",
            "schemas: [{name: target, path: schema.yaml}, {name: core, path: core.yaml}]",
        )
    )
    (root / "target.yaml").write_text(declaration + "source_bindings: true\n")
    bundle, _, _, prepared = prepare_data_operation_inputs(root, "target.yaml")
    assert "data_operation_source" in {source.name for source in bundle.sources}
    assert "DdoSelectedNativeSource" in prepared.index.definitions
    model = json.loads(
        next(
            artifact.content
            for artifact in prepared.artifacts
            if artifact.kind == "data_operations.json"
        )
    )
    source = next(kind for kind in model["kinds"] if kind["name"] == "DdoSelectedNativeSource")
    assert source["facts"]["json"]["universe"] == "source"


def primary_profile_inputs(tmp_path):
    """Frozen fixture selections exercise acquisition without starting any provider."""
    import yaml

    from corpus_structure.ingest.sentences import SentenceConfig
    from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection

    root = inputs(tmp_path)
    (root / "assets").mkdir()
    configuration = SentenceConfig(exclude=("ner",))
    (root / "sentences.yaml").write_text(yaml.safe_dump(configuration.model_dump(mode="json")))
    for provider in ("spacy", "hanlp"):
        native = NativeProfile(
            provider, {"fixture": "no provider execution"}, {"files": {}},
            configuration.model_dump(mode="json") if provider == "spacy" else {},
            "float32", "cupy" if provider == "spacy" else "torch",
        )
        (root / (provider + ".json")).write_bytes(
            canonical_bytes(NativeSelection(native, root / "assets").declaration())
        )
    with (root / "target.yaml").open("a") as output:
        output.write("""primary_profile:
  sentence_configuration: sentences.yaml
  sentence_selection: spacy.json
  hanlp_selection: hanlp.json
""")
    return root


def test_primary_manifest_uses_shared_composition_and_retains_exact_profile_files(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from corpus_structure.semantic import primary_operations
    from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies

    root = primary_profile_inputs(tmp_path)
    seen = []

    def compose(bundle, **arguments):
        seen.append(arguments)
        return SimpleNamespace(bundle=bundle, dependencies=ResolvedDependencies(), profile=PreparationProfile(version="semantic-2"))

    monkeypatch.setattr(primary_operations, "primary_operation_inputs", compose)
    acquired = acquire_data_operation_inputs(root, "target.yaml")
    (arguments,) = seen
    assert arguments["sentence_selection"].provider == "spacy"
    assert arguments["hanlp_selection"].provider == "hanlp"
    assert arguments["sentence_configuration"].exclude == ("ner",)
    assert arguments["sentence_selection"].assets == root / "assets"
    assert arguments["extra_sources"] is None
    assert [artifact.name for artifact in arguments["declarations"]] == ["operations"]
    captured = dict(acquired.files)
    assert {"target.yaml", "schema.yaml", "operations.yaml", "sentences.yaml", "spacy.json", "hanlp.json"} == set(captured)
    assert captured["spacy.json"] == (root / "spacy.json").read_bytes()


@pytest.mark.parametrize("change", ["fingerprint", "provider", "configuration", "unavailable-assets"])
def test_primary_manifest_refuses_changed_or_unavailable_explicit_selection(tmp_path, change):
    root = primary_profile_inputs(tmp_path)
    value = json.loads((root / "spacy.json").read_bytes())
    if change == "fingerprint":
        value["fingerprint"] = "changed"
    elif change == "provider":
        value = json.loads((root / "hanlp.json").read_bytes())
    elif change == "configuration":
        (root / "sentences.yaml").write_text("exclude: []\n")
    else:
        value["assets"] = str(root / "absent")
    (root / "spacy.json").write_bytes(canonical_bytes(value))
    with pytest.raises(ValueError, match="selection|configuration"):
        acquire_data_operation_inputs(root, "target.yaml")
