"""Controlled target preparation and source projection; no provider qualification."""

import json
from dataclasses import replace
from pathlib import Path

from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.native_profiles import (
    NativeProfile,
    NativeSelection,
    gliner_selection,
    pm2_selection,
)
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.data_operation_consumers import resolve_prepared_factory
from corpus_structure.semantic.primary_operations import primary_operation_inputs


def test_learned_profile_captures_actual_provider_factories_and_private_outputs(
    tmp_path, monkeypatch
):
    from corpus_structure.methods import native_profiles
    from semantic.model_characterization_support import gliner_profile

    monkeypatch.setattr(
        native_profiles,
        "spacy_selection",
        lambda config: NativeSelection(
            NativeProfile(
                "spacy",
                {"controlled": "runtime"},
                {},
                config.model_dump(mode="json"),
                "float32",
                "cupy",
                4,
                1,
            ),
            tmp_path,
        ),
    )
    from corpus_structure.methods.gliner import CUDA_WHITESPACE_PROFILE

    gliner = replace(gliner_profile().profile, snapshot=tmp_path, version=CUDA_WHITESPACE_PROFILE)
    selected = {
        provider: pm2_selection(provider, tmp_path, {"controlled": "runtime"}, {})
        for provider in ("maverick", "dipo", "d1")
    }
    selected["gliner"] = gliner_selection(gliner, {"controlled": "runtime"})
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    inputs = primary_operation_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)),
        sentence_configuration=SentenceConfig(),
        hanlp_selection=pm2_selection("hanlp", tmp_path, {"controlled": "runtime"}, {}),
        learned_selections=selected,
    )
    from corpus_structure.semantic import data_operation_storage

    projection = data_operation_storage.data_operation_definition_projection

    def explain_incomplete(prepared, model, **options):
        try:
            return projection(prepared, model, **options)
        except ValueError as error:
            unknowns = [
                (item.root, [(row.location, row.reason) for row in item.unknowns if row.required])
                for item in model.implementation_slices
                if not item.complete
            ]
            raise ValueError(str(error) + ": " + repr(unknowns)) from error

    monkeypatch.setattr(
        data_operation_storage, "data_operation_definition_projection", explain_incomplete
    )
    prepared = prepare_release(inputs.bundle, inputs.dependencies, inputs.profile)
    model = bound_data_operation_model(prepared)
    expected = {
        "text." + name + "/source-native"
        for name in (
            "maverick",
            "dipo",
            "d1_source",
            "d1_candidates",
            "gliner_cues",
            "gliner_function",
        )
    }
    for identity in expected:
        operation = model.operation(identity)
        assert operation.capabilities.prepared_factory is not None
        assert callable(resolve_prepared_factory(model, inputs.sources, identity))
        assert {role.name for role in operation.roles if role.direction == "output"} == {
            "result",
            "candidates",
        }
        assert len(operation.output_witnesses) == 3
    assert model.operation("text.maverick/source-native").dependencies == (
        "segment.sentences/source-native",
    )
    assert set(model.operation("text.d1_candidates/source-native").dependencies) == {
        "text.formal_evidence/source-native",
        "text.constructions/source-native",
        "text.contextual_native/source-native",
    }
    frozen = json.loads(
        next(
            artifact.content
            for artifact in inputs.sources.boundary_contracts
            if artifact.name == "learned/execution-custody"
        )
    )
    assert frozen["selections"]["d1"]["profile"]["dtype"] == "bfloat16"
    assert frozen["selections"]["maverick"]["profile"]["dtype"] == "float32"
    assert frozen["selections"]["gliner"]["profile"]["device"] == "cuda"
