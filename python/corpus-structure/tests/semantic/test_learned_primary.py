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


def test_explicit_learned_focus_keeps_context_and_unknown_remainder_separate():
    from types import SimpleNamespace

    from corpus_structure.semantic.learned_primary import (
        learned_focal_scopes,
        uncovered_focal_scopes,
    )

    frame = SimpleNamespace(
        text="First. Focus. Last.",
        source_key="native-original:book",
        projection_digest="projection",
        selected_ranges=((0, 19),),
    )
    (scope,) = learned_focal_scopes(
        frame,
        [{"focal_extent": [7, 13], "projection_extent": [0, 19]}],
        max_context_chars=64,
        exact=False,
    )
    assert scope.focal == (7, 13) and (scope.start, scope.end) == (0, 19)
    assert tuple(uncovered_focal_scopes(frame, (scope,))) == (
        {"projection": "projection", "start": 0, "end": 7},
        {"projection": "projection", "start": 13, "end": 19},
    )
    (exact,) = learned_focal_scopes(
        frame,
        [{"focal_extent": [7, 13], "projection_extent": [7, 13]}],
        max_context_chars=64,
        exact=True,
    )
    assert exact.focal == (exact.start, exact.end)


def test_explicit_learned_focus_refuses_widening_duplicate_and_inexact_gliner_scope():
    from types import SimpleNamespace

    import pytest

    from corpus_structure.semantic.learned_primary import learned_focal_scopes

    frame = SimpleNamespace(
        text="First. Focus. Last.",
        source_key="native-original:book",
        projection_digest="projection",
        selected_ranges=((7, 13),),
    )
    with pytest.raises(ValueError, match="exact admitted source"):
        learned_focal_scopes(
            frame,
            [{"focal_extent": [7, 13], "projection_extent": [0, 19]}],
            max_context_chars=64,
            exact=False,
        )
    with pytest.raises(ValueError, match="provider question scope"):
        learned_focal_scopes(
            frame,
            [{"focal_extent": [8, 12], "projection_extent": [7, 13]}],
            max_context_chars=64,
            exact=True,
        )
    selected = {"focal_extent": [7, 13], "projection_extent": [7, 13]}
    with pytest.raises(ValueError, match="repeats identical captured work"):
        learned_focal_scopes(frame, [selected, selected], max_context_chars=64, exact=True)
