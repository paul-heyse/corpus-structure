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
            provider,
            {"fixture": "no provider execution"},
            {"files": {}},
            configuration.model_dump(mode="json") if provider == "spacy" else {},
            "float32",
            "cupy" if provider == "spacy" else "torch",
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


def test_primary_manifest_uses_shared_composition_and_retains_exact_profile_files(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace

    from corpus_structure.semantic import primary_operations
    from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies

    root = primary_profile_inputs(tmp_path)
    seen = []

    def compose(bundle, **arguments):
        seen.append(arguments)
        return SimpleNamespace(
            bundle=bundle,
            dependencies=ResolvedDependencies(),
            profile=PreparationProfile(version="semantic-2"),
        )

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
    assert {
        "target.yaml",
        "schema.yaml",
        "operations.yaml",
        "sentences.yaml",
        "spacy.json",
        "hanlp.json",
    } == set(captured)
    assert captured["spacy.json"] == (root / "spacy.json").read_bytes()


@pytest.mark.parametrize(
    "change", ["fingerprint", "provider", "configuration", "unavailable-assets"]
)
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
    with pytest.raises(ValueError, match=r"selection|configuration"):
        acquire_data_operation_inputs(root, "target.yaml")


def test_public_downstream_profile_acquires_native_consumers_without_model_execution(tmp_path):
    from pathlib import Path

    import yaml

    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.data_operation_consumers import resolve_prepared_factory

    root = primary_profile_inputs(tmp_path)
    from corpus_structure.methods.native_profiles import pm2_selection

    (root / "hanlp.json").write_bytes(
        canonical_bytes(
            pm2_selection(
                "hanlp", root / "assets", {"fixture": "no provider execution"}, {}
            ).declaration()
        )
    )
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    (root / "schema.yaml").write_bytes(core.read_bytes())
    manifest = yaml.safe_load((root / "target.yaml").read_bytes())
    manifest["root"] = "core"
    manifest["schemas"][0]["name"] = "core"
    manifest["primary_profile"]["downstream"] = True
    (root / "target.yaml").write_text(yaml.safe_dump(manifest))
    bundle, dependencies, profile, prepared = prepare_data_operation_inputs(root, "target.yaml")
    model = bound_data_operation_model(prepared)
    operations = {operation.semantic_id: operation for operation in model.operations}
    expected = {
        "structure.predicate_evidence/declared",
        "structure.scoped_relations/declared",
        "structure.artifact_identity/declared",
        "structure.definition_declaration_components/declared",
        "structure.definition_applicability/declared",
        "structure.definition_named_components/declared",
        "structure.dossier/declared",
        "structure.compare/declared",
        "structure.condition_qualification/declared",
        "retrieve.contextual/declared",
    }
    assert expected <= operations.keys()
    assert not any(identity.startswith("text.gliner") for identity in operations)
    from corpus_structure.semantic.composed import read_data_operation_inputs

    captured = read_data_operation_inputs(dependencies)
    assert captured is not None
    _, sources = captured
    assert sources is not None
    for identity in expected:
        assert callable(resolve_prepared_factory(model, sources, identity))
    assert "data_operation_contextual" in {source.name for source in bundle.sources}
    assert profile.version == "semantic-2"


@pytest.mark.parametrize("primary", [False, True])
def test_explicit_ontology_selection_reaches_actual_dependency_owner(
    tmp_path, monkeypatch, primary
):
    from types import SimpleNamespace

    import yaml

    from corpus_structure.semantic import primary_operations
    from corpus_structure.semantic.types import PreparationProfile

    root = primary_profile_inputs(tmp_path) if primary else inputs(tmp_path)
    literal = b"format-version: 1.2\n\n[Term]\nid: EX:1\nname: independent\n"
    (root / "ontology.obo").write_bytes(literal)
    path = root / "target.yaml"
    declaration = yaml.safe_load(path.read_bytes())
    declaration["dependencies"] = [dict(name="selected-ontology", path="ontology.obo")]
    declaration["ontology_sources"] = ["selected-ontology"]
    path.write_text(yaml.safe_dump(declaration))
    seen = []
    if primary:

        def compose(bundle, **arguments):
            seen.append(arguments["dependencies"])
            return SimpleNamespace(
                bundle=bundle,
                dependencies=arguments["dependencies"],
                profile=PreparationProfile(version="semantic-2"),
            )

        monkeypatch.setattr(primary_operations, "primary_operation_inputs", compose)
    acquired = acquire_data_operation_inputs(root, "target.yaml")
    assert acquired.dependencies.ontology_sources == ("selected-ontology",)
    assert (
        next(
            source.content
            for source in acquired.dependencies.artifacts
            if source.name == "selected-ontology"
        )
        == literal
    )
    assert dict(acquired.files)["ontology.obo"] == literal
    if primary:
        assert seen[0].ontology_sources == ("selected-ontology",)


@pytest.mark.parametrize("selection", [["absent"], ["selected-ontology", "selected-ontology"]])
def test_ontology_selection_refuses_undeclared_or_repeated_names(tmp_path, selection):
    import yaml

    root = inputs(tmp_path)
    (root / "ontology.obo").write_text("format-version: 1.2\n")
    path = root / "target.yaml"
    declaration = yaml.safe_load(path.read_bytes())
    declaration["dependencies"] = [dict(name="selected-ontology", path="ontology.obo")]
    declaration["ontology_sources"] = selection
    path.write_text(yaml.safe_dump(declaration))
    with pytest.raises(ValueError, match="unique declared dependency names"):
        acquire_data_operation_inputs(root, "target.yaml")


def test_recognition_acquisition_preserves_configured_interpreter_symlink(tmp_path, monkeypatch):
    import sys

    import yaml

    from corpus_structure.ingest.pdf import PdfRecipe
    from corpus_structure.ingest.pdf_recognition import NemotronRecipe
    from corpus_structure.semantic import pdf_capture, pdf_transforms
    from corpus_structure.semantic.data_operation_preparation import (
        PrimaryProfileInputs,
        _acquire_primary_profile,
    )

    root = primary_profile_inputs(tmp_path)
    interpreter = root / "runtime/bin/python"
    interpreter.parent.mkdir(parents=True)
    interpreter.symlink_to(sys.executable)
    worker = root / "worker.py"
    worker.write_text("# Never executed during acquisition.\n")
    (root / "pdf.json").write_bytes(PdfRecipe("0" * 40, "1" * 40).to_bytes())
    (root / "pdf-assets.json").write_bytes(
        canonical_bytes(
            {
                "recipe": "pdf-model-assets-v1",
                "repositories": [],
                "files": [],
            }
        )
    )
    (root / "recognition.yaml").write_text(
        yaml.safe_dump(asdict(NemotronRecipe("2" * 64, "3" * 64)))
    )
    (root / "integration.yaml").write_text(
        yaml.safe_dump(
            {
                "integration": {"integration_policy": {}},
                "recognition": {"recovery_policy": None},
            }
        )
    )
    (root / "resources.yaml").write_text(
        yaml.safe_dump(
            {
                "python": "runtime/bin/python",
                "script": "worker.py",
                "receipts": "receipts",
                "endpoint": "http://127.0.0.1:8123/v1",
                "timeout_seconds": 7,
            }
        )
    )
    profile_record = yaml.safe_load((root / "target.yaml").read_text())["primary_profile"]
    profile_record["capture"] = {
        "recipe": "pdf.json",
        "assets_manifest": "pdf-assets.json",
        "assets_root": "assets",
        "directory": "work",
        "recognition": {
            "recipe": "recognition.yaml",
            "options": "integration.yaml",
            "resources": "resources.yaml",
        },
    }
    seen = []
    monkeypatch.setattr(pdf_capture, "pdf_capture_operation_sources", lambda *args, **kwargs: None)

    def acquire(mode, **kwargs):
        seen.append((mode, kwargs["resources"]))
        return None

    monkeypatch.setattr(pdf_transforms, "pdf_transform_operation_sources", acquire)
    _acquire_primary_profile(
        PrimaryProfileInputs.model_validate(profile_record),
        lambda name: (root / name).read_bytes(),
        root,
    )
    ((mode, resources),) = seen
    assert mode == "integrated"
    assert resources.python == str(interpreter)
    assert resources.python != str(interpreter.resolve())
    assert resources.script == str(worker.resolve())
    assert resources.receipts == str((root / "receipts").resolve())
