"""Public downstream acquisition over controlled frozen inputs; no provider qualification."""

import json
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from corpus_structure.methods.contextual_embeddings import EncoderProfile
from corpus_structure.methods.gliner import CUDA_WHITESPACE_PROFILE
from corpus_structure.methods.m1_source import M1Config
from corpus_structure.methods.native_profiles import gliner_selection, pm2_selection
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.data_operation_consumers import resolve_prepared_factory
from corpus_structure.semantic.data_operation_preparation import (
    acquire_data_operation_inputs,
    prepare_data_operation_inputs,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies
from semantic.model_characterization_support import gliner_profile
from semantic.test_data_operation_preparation import primary_profile_inputs


def _manifest(root):
    return yaml.safe_load((root / "target.yaml").read_bytes())


def _write_manifest(root, value):
    (root / "target.yaml").write_text(yaml.safe_dump(value))


def test_public_learned_math_downstream_profile_has_complete_captured_factories(
    tmp_path, monkeypatch
):
    from corpus_structure.methods import native_profiles
    from corpus_structure.methods.native_host import NativeHostGroup
    from corpus_structure.semantic.composed import read_data_operation_inputs

    root = primary_profile_inputs(tmp_path)
    assets = root / "assets"
    for provider in ("hanlp", "maverick", "dipo", "d1"):
        selected = pm2_selection(provider, assets, {"controlled": "acquisition-only"}, {})
        (root / (provider + ".json")).write_bytes(canonical_bytes(selected.declaration()))
    gliner = replace(gliner_profile().profile, snapshot=assets, version=CUDA_WHITESPACE_PROFILE)
    selected_gliner = gliner_selection(gliner, {"controlled": "acquisition-only"})
    (root / "gliner.json").write_bytes(canonical_bytes(selected_gliner.declaration()))
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    (root / "schema.yaml").write_bytes(core.read_bytes())
    (root / "math.yaml").write_text("parse_seconds: 1.0\nconstants: [pi]\n")
    manifest = _manifest(root)
    manifest["root"] = "core"
    manifest["schemas"][0]["name"] = "core"
    manifest["primary_profile"].update(
        learned_selections={
            provider: provider + ".json" for provider in ("maverick", "dipo", "d1", "gliner")
        },
        math="math.yaml",
        downstream=True,
    )
    _write_manifest(root, manifest)

    def no_provider(*args, **kwargs):
        pytest.fail("public acquisition tried to acquire or start an unfrozen provider")

    monkeypatch.setattr(NativeHostGroup, "__init__", no_provider)
    monkeypatch.setattr(native_profiles, "preflight_native_runtime", no_provider)
    monkeypatch.setattr(native_profiles, "spacy_selection", no_provider)
    _, dependencies, preparation, prepared = prepare_data_operation_inputs(root, "target.yaml")
    model = bound_data_operation_model(prepared)
    captured = read_data_operation_inputs(dependencies)
    assert captured is not None and captured[1] is not None
    sources = captured[1]
    expected = {
        "segment.sentences/source-native",
        "segment.sentences/canonical-projection",
        "text.hanlp_native/source-native",
        "text.declaration_syntax/source-native",
        "text.maverick/source-native",
        "text.dipo/source-native",
        "text.d1_source/source-native",
        "text.d1_candidates/source-native",
        "text.gliner_cues/source-native",
        "text.gliner_function/source-native",
        "text.gliner_definitions/source-native",
        "extract.math/declared",
        "normalize.formula/declared",
        "resolve.symbol_scope/declared",
        "analyze.math/lexical",
        "analyze.math/contextual",
        "structure.predicate_evidence/declared",
        "structure.scoped_relations/declared",
        "structure.artifact_identity/declared",
        "structure.definition_declaration_components/declared",
        "structure.definition_named_components/declared",
        "structure.definition_components/declared",
        "structure.definition_applicability/declared",
        "structure.dossier/declared",
        "structure.compare/declared",
        "structure.condition_qualification/declared",
        "structure.clause_classification/declared",
        "retrieve.contextual/declared",
        "interpret.finite_candidates",
    }
    operations = {operation.semantic_id: operation for operation in model.operations}
    assert expected <= operations.keys()
    for identity in sorted(expected):
        assert operations[identity].capabilities.prepared_factory is not None, identity
        assert callable(resolve_prepared_factory(model, sources, identity)), identity
    incomplete = [
        (
            item.root,
            [(unknown.location, unknown.reason) for unknown in item.unknowns if unknown.required],
        )
        for item in model.implementation_slices
        if not item.complete
    ]
    assert not incomplete, incomplete
    assert preparation.version == "semantic-2" and prepared.execution_model_id is None

    components = operations["structure.definition_components/declared"]
    assert components.dependencies == ("text.gliner_definitions/source-native",)
    inputs = {role.name: role for role in components.roles if role.direction == "input"}
    assert set(inputs) == {"source", "observation", "candidates"}
    for role in inputs.values():
        assert role.support is not None
        assert role.support.provenance == "exact"
        assert role.support.identity_requirements == ("episode",)
    witnesses = {witness.input_role: witness for witness in components.output_witnesses}
    assert set(witnesses) == {"source", "candidates"}
    exact_fields = {
        "product",
        "reference",
        "kind_contract",
        "project_id",
        "subject",
        "original_source",
        "analyzed_scope",
    }
    for role, witness in witnesses.items():
        assert {comparison.input.field for comparison in witness.comparisons} == exact_fields
        assert all(comparison.input.role == role for comparison in witness.comparisons)
    custody = json.loads(
        next(
            artifact.content
            for artifact in sources.boundary_contracts
            if artifact.name == "learned/execution-custody"
        )
    )
    assert set(custody["selections"]) == {"maverick", "dipo", "d1", "gliner"}
    assert custody["selections"]["gliner"]["profile"]["device"] == "cuda"


def _optional_inputs(root):
    """Real local fixture bytes are captured, never described as executable model assets."""
    assets = root / "literal-assets"
    assets.mkdir()
    artifact_hashes = []
    for name in (
        "config.json",
        "encoder_config/config.json",
        "model.safetensors",
        "tokenizer.json",
        "tokenizer_config.json",
    ):
        path = assets / name
        path.parent.mkdir(exist_ok=True)
        content = canonical_bytes({"controlled-acquisition-file": name})
        path.write_bytes(content)
        artifact_hashes.append((name, sha256(content).hexdigest()))
    config = M1Config(
        snapshot=assets,
        checkpoint="controlled-acquisition",
        revision="a" * 40,
        artifact_hashes=tuple(artifact_hashes),
    )
    frozen = gliner_selection(config.profile(), {"controlled": "acquisition-only"})
    config = config.model_copy(update={"native_execution_profile": frozen.native.wire})
    (root / "m1.yaml").write_text(yaml.safe_dump(config.model_dump(mode="json")))
    (root / "records.yaml").write_text(
        "id: urn:controlled-records\nname: controlled_records\nclasses: {ControlledRecord: {}}\n"
    )
    encoder = root / "encoder-assets"
    encoder.mkdir()
    for name in ("config.json", "modules.json"):
        (encoder / name).write_bytes(b"{}")
    profile = EncoderProfile("controlled-acquisition", "b" * 40, 2, "query: ", "document: ", "mean")
    (root / "encoder.yaml").write_text(yaml.safe_dump(asdict(profile)))
    manifest = _manifest(root)
    manifest["primary_profile"].update(
        m1=dict(
            configuration="m1.yaml",
            schema_root="controlled_records",
            schemas=[dict(name="controlled_records", path="records.yaml")],
        ),
        contextual_encoder=dict(profile="encoder.yaml", model_path="encoder-assets"),
    )
    _write_manifest(root, manifest)


def test_optional_literal_and_encoder_acquisition_retains_exact_supplied_files(
    tmp_path, monkeypatch
):
    from corpus_structure.semantic import primary_operations

    root = primary_profile_inputs(tmp_path)
    _optional_inputs(root)
    seen = []

    def capture(bundle, **arguments):
        seen.append(arguments)
        return SimpleNamespace(
            bundle=bundle,
            dependencies=ResolvedDependencies(),
            profile=PreparationProfile(version="semantic-2"),
        )

    monkeypatch.setattr(primary_operations, "primary_operation_inputs", capture)
    acquired = acquire_data_operation_inputs(root, "target.yaml")
    (arguments,) = seen
    files = dict(acquired.files)
    for name in ("m1.yaml", "records.yaml", "encoder.yaml"):
        assert files[name] == (root / name).read_bytes()
    assert arguments["m1_configuration"].snapshot == root / "literal-assets"
    assert arguments["m1_configuration"].native_execution_profile is not None
    assert arguments["record_schemas"].sources[0].content == files["records.yaml"]
    selection = arguments["contextual_encoder"]
    assert selection.model_path == root / "encoder-assets"
    assert dict(selection.artifacts) == {
        name: sha256(b"{}").hexdigest() for name in ("config.json", "modules.json")
    }


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ("unfrozen-literal", "captured native execution profile"),
        ("duplicate-record-schema", "unique named schemas"),
        ("missing-encoder-modules", "actual model/module configuration"),
    ],
)
def test_optional_acquisition_refuses_incomplete_explicit_custody(tmp_path, change, reason):
    root = primary_profile_inputs(tmp_path)
    _optional_inputs(root)
    if change == "unfrozen-literal":
        config = yaml.safe_load((root / "m1.yaml").read_bytes())
        config.pop("native_execution_profile")
        (root / "m1.yaml").write_text(yaml.safe_dump(config))
    elif change == "duplicate-record-schema":
        manifest = _manifest(root)
        manifest["primary_profile"]["m1"]["schemas"] *= 2
        _write_manifest(root, manifest)
    else:
        (root / "encoder-assets/modules.json").unlink()
    with pytest.raises(ValueError, match=reason):
        acquire_data_operation_inputs(root, "target.yaml")


def _use_core_schema(root):
    (root / "hanlp.json").write_bytes(
        canonical_bytes(
            pm2_selection(
                "hanlp", root / "assets", {"controlled": "acquisition-only"}, {}
            ).declaration()
        )
    )
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    (root / "schema.yaml").write_bytes(core.read_bytes())
    manifest = _manifest(root)
    manifest["root"] = "core"
    manifest["schemas"][0]["name"] = "core"
    _write_manifest(root, manifest)


def _compiled_acquisition(root):
    from corpus_structure.semantic.composed import read_data_operation_inputs

    _, dependencies, _, prepared = prepare_data_operation_inputs(root, "target.yaml")
    model = bound_data_operation_model(prepared)
    captured = read_data_operation_inputs(dependencies)
    assert captured is not None and captured[1] is not None
    incomplete = [
        (item.root, item.unknowns) for item in model.implementation_slices if not item.complete
    ]
    assert not incomplete, incomplete
    return model, captured[1]


def test_public_downstream_acquires_private_reading_resolution_without_model_selection(tmp_path):
    root = primary_profile_inputs(tmp_path)
    _use_core_schema(root)
    manifest = _manifest(root)
    manifest["primary_profile"]["downstream"] = True
    _write_manifest(root, manifest)
    model, sources = _compiled_acquisition(root)
    operation = model.operation("resolve.m1_readings/declared")
    assert operation.dependencies == ()
    assert callable(resolve_prepared_factory(model, sources, operation.semantic_id))
    roles = {role.name: role for role in operation.roles}
    assert roles["policy"].support is not None
    assert roles["policy"].support.origins == ("authored",)
    assert roles["result"].kind.endswith("/DdoResolvedReadingReport")
    assert "text.gliner_definitions/source-native" not in {
        item.semantic_id for item in model.operations
    }


def test_public_encoder_without_downstream_acquires_its_inventory_dependency(tmp_path, monkeypatch):
    from corpus_structure.methods import contextual_embeddings

    root = primary_profile_inputs(tmp_path)
    _use_core_schema(root)
    _optional_inputs(root)
    manifest = _manifest(root)
    manifest["primary_profile"].pop("m1")
    manifest["primary_profile"]["downstream"] = False
    _write_manifest(root, manifest)

    def forbidden(*args, **kwargs):
        pytest.fail("captured encoder acquisition started inference")

    monkeypatch.setattr(contextual_embeddings, "encode_contexts", forbidden)
    model, sources = _compiled_acquisition(root)
    encoder = model.operation("retrieve.contextual_vectors/declared")
    assert encoder.dependencies == ("retrieve.contextual_inventory/declared",)
    for identity in (encoder.semantic_id, *encoder.dependencies):
        assert callable(resolve_prepared_factory(model, sources, identity))
    assert "structure.dossier/declared" not in {item.semantic_id for item in model.operations}


def test_public_downstream_acquires_definition_location_with_exact_report_witnesses(tmp_path):
    root = primary_profile_inputs(tmp_path)
    _use_core_schema(root)
    manifest = _manifest(root)
    manifest["primary_profile"]["downstream"] = True
    _write_manifest(root, manifest)
    model, sources = _compiled_acquisition(root)
    operation = model.operation("locate.definition_terms/declared")
    inputs = {role.name: role for role in operation.roles if role.direction == "input"}
    assert inputs["components"].kind == "urn:corpus:structural:DeclaredDefinitionComponentsReport"
    assert inputs["selection"].support is not None and inputs["selection"].support.origins == (
        "authored",
    )
    assert callable(resolve_prepared_factory(model, sources, operation.semantic_id))
    witnesses = {witness.input_role: witness for witness in operation.output_witnesses}
    assert set(witnesses) == {"source", "components", "selection"}
    for role, witness in witnesses.items():
        assert all(comparison.input.role == role for comparison in witness.comparisons)
    # The existing contextual encoder accepts the authentic located member kind.
    output = next(role for role in operation.roles if role.direction == "output")
    assert output.kind.endswith("/DdoDefinitionLocationReport")
