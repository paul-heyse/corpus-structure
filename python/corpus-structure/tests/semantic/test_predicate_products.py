"""Declared predicate contracts; controlled preparation is not provider qualification."""

from pathlib import Path

from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection, pm2_selection
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.predicate_products import (
    predicate_inputs,
    predicate_operation_sources,
)
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.primary_operations import (
    combine_primary_sources,
    primary_operation_inputs,
)
from corpus_structure.semantic.types import ResolvedDependencies, SourceArtifact, SourceBundle


def test_predicate_capability_has_real_primary_inputs_and_exact_source_witnesses(
    tmp_path, monkeypatch
):
    from corpus_structure.methods import native_profiles

    monkeypatch.setattr(
        native_profiles,
        "spacy_selection",
        lambda configuration: NativeSelection(
            NativeProfile(
                "spacy",
                {"controlled": "preparation"},
                {},
                configuration.model_dump(mode="json"),
                "float32",
                "cupy",
                4,
                1,
            ),
            tmp_path,
        ),
    )
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    base = primary_operation_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)),
        sentence_configuration=SentenceConfig(),
        hanlp_selection=pm2_selection("hanlp", tmp_path, {"controlled": "preparation"}, {}),
    )
    sources = combine_primary_sources(base.sources, predicate_operation_sources())
    prepared = prepare_release(
        predicate_inputs(base.bundle),
        data_operation_dependencies(ResolvedDependencies(), python_sources=sources),
        base.profile,
    )
    model = bound_data_operation_model(prepared)
    operation = model.operation("structure.predicate_evidence/declared")
    assert operation.subject == "original-source-view"
    assert {role.name for role in operation.roles if role.direction == "input"} == {
        "source",
        "annotations",
        "constructions",
        "formal",
    }
    assert set(operation.dependencies) == {
        "segment.sentences/source-native",
        "text.constructions/source-native",
        "text.formal_evidence/source-native",
    }
    assert operation.output_witnesses and all(
        witness.input_role == "source" for witness in operation.output_witnesses
    )
