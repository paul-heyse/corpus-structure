"""The ordinary primary profile captures owned factories and frozen resources."""

import json
from pathlib import Path

from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.native_profiles import pm2_selection
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.data_operation_consumers import resolve_prepared_factory
from corpus_structure.semantic.primary_operations import primary_operation_inputs


def test_primary_inputs_compile_owned_factories_and_exact_provider_custody(tmp_path, monkeypatch):
    from corpus_structure.methods import native_profiles
    from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection

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
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    configuration = SentenceConfig(exclude=("ner", "lemmatizer"), batch_size=17)
    # This is controlled preparation evidence, with no actual-provider claim.
    selected = pm2_selection("hanlp", tmp_path, {"controlled": "runtime"}, {})
    inputs = primary_operation_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)),
        sentence_configuration=configuration,
        hanlp_selection=selected,
    )
    prepared = prepare_release(inputs.bundle, inputs.dependencies, inputs.profile)
    model = bound_data_operation_model(prepared)
    expected = {
        "source.selected_views/discovery",
        "segment.sentences/source-native",
        "segment.sentences/canonical-projection",
        "text.hanlp_native/source-native",
        "text.formal_evidence/source-native",
        "text.constructions/source-native",
        "text.contextual_evaluation/source-native",
        "text.compose_view/source-native",
        "text.compose_view/full-native",
    }
    factories = {
        operation.semantic_id
        for operation in model.operations
        if operation.capabilities.prepared_factory is not None
    }
    assert factories == expected
    for operation in sorted(expected):
        factory = resolve_prepared_factory(model, inputs.sources, operation)
        assert callable(factory)
    custody = {artifact.name: artifact for artifact in inputs.sources.boundary_contracts}
    assert json.loads(custody["sentences/execution-custody"].content)["configuration"] == (
        configuration.model_dump(mode="json")
    )
    assert json.loads(custody["hanlp/execution-custody"].content)["selection"] == (
        selected.declaration()
    )
    assert model.operation("profile.segments/source-native").capabilities.prepared_factory is None

    dependencies = {operation.semantic_id: operation.dependencies for operation in model.operations}
    assert dependencies["segment.sentences/canonical-projection"] == (
        "segment.sentences/source-native",
    )
    assert dependencies["text.hanlp_native/source-native"] == (
        "segment.sentences/canonical-projection",
    )
    assert dependencies["text.constructions/source-native"] == (
        "text.formal_evidence/source-native",
    )
    assert set(dependencies["text.contextual_evaluation/source-native"]) == {
        "text.formal_evidence/source-native",
        "text.constructions/source-native",
    }
    assert not model.operation("text.compose_view/source-native").potential_dependencies
    assert set(model.operation("text.compose_view/full-native").potential_dependencies) == {
        "segment.sentences/source-native",
        "segment.sentences/canonical-projection",
        "text.hanlp_native/source-native",
        "text.formal_evidence/source-native",
        "text.constructions/source-native",
        "text.contextual_evaluation/source-native",
    }

    full = model.operation("text.compose_view/full-native")
    inputs = {role.name: role for role in full.roles if role.direction == "input"}
    assert set(inputs) == {"sources", "annotations", "canonical", "hanlp", "formal", "constructions", "contextual"}
    assert all(role.presence == "alternative" and role.minimum == 0 and len(role.alternatives) == 1 for role in inputs.values())
    assert full.outcomes == ("success", "empty", "failed")
    assert full.dependencies == ("source.selected_views/discovery",)
    assert "DdoCharacterizedProduct" not in inputs["annotations"].kind
    assert model.operation("segment.sentences/source-native").roles[1].kind.endswith("/DdoSourceAnnotations")


def test_captured_primary_profile_declares_capture_views_and_authentic_full_fanin(tmp_path, monkeypatch):
    from corpus_structure.ingest.pdf import PdfRecipe
    from corpus_structure.ingest.pdf_assets import PreparedPdfAssets
    from corpus_structure.methods import native_profiles
    from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection
    from corpus_structure.semantic.pdf_capture import pdf_capture_operation_sources
    from corpus_structure.semantic.pdf_views import pdf_views_operation_sources
    import pytest

    monkeypatch.setattr(native_profiles, "spacy_selection", lambda config: NativeSelection(
        NativeProfile("spacy", {"controlled": "runtime"}, {}, config.model_dump(mode="json"), "float32", "cupy", 4, 1), tmp_path))
    with pytest.raises(ValueError, match="actual captured capture dependency"):
        pdf_views_operation_sources()
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    recipe = PdfRecipe("0" * 40, "1" * 40, recipe_id="docling-standard-pdf-stream-v1")
    capture = pdf_capture_operation_sources(recipe, PreparedPdfAssets(tmp_path, b"{}", ()), directory=tmp_path / "owned")
    acquired = primary_operation_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)),
        sentence_configuration=SentenceConfig(),
        hanlp_selection=pm2_selection("hanlp", tmp_path, {"controlled": "runtime"}, {}),
        capture_sources=capture,
    )
    prepared = prepare_release(acquired.bundle, acquired.dependencies, acquired.profile)
    model = bound_data_operation_model(prepared)
    views = model.operation("source.pdf_views/discovery")
    full = model.operation("text.compose_view/captured-full-native")
    assert views.dependencies == ("source.pdf/capture",)
    assert full.dependencies == ("source.pdf_views/discovery",)
    sources = next(role for role in full.roles if role.name == "sources")
    assert sources.selected == "source.pdf_views/discovery"
    assert sources.minimum == 0
    assert views.effects == ()
    for identity in (views.semantic_id, full.semantic_id):
        assert callable(resolve_prepared_factory(model, acquired.sources, identity))
    assert model.operation("text.compose_view/full-native").dependencies == ("source.selected_views/discovery",)
