"""Independent declaration factory contracts; controlled custody makes no provider claim."""

from pathlib import Path

from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection, pm2_selection
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.data_operation_consumers import resolve_prepared_factory
from corpus_structure.semantic.declaration_products import (
    declaration_inputs,
    declaration_operation_sources,
)
from corpus_structure.semantic.primary_operations import (
    combine_primary_sources,
    primary_operation_inputs,
)
from corpus_structure.semantic.types import ResolvedDependencies


def test_declaration_syntax_is_distinct_from_source_grammar_and_uses_actual_canonical_hanlp(
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
    sources = combine_primary_sources(base.sources, declaration_operation_sources())
    prepared = prepare_release(
        declaration_inputs(base.bundle),
        data_operation_dependencies(ResolvedDependencies(), python_sources=sources),
        base.profile,
    )
    model = bound_data_operation_model(prepared)
    operation = model.operation("text.declaration_syntax/source-native")
    assert {role.name for role in operation.roles if role.direction == "input"} == {
        "source",
        "canonical",
        "hanlp",
    }
    assert set(operation.dependencies) == {
        "segment.sentences/canonical-projection",
        "text.hanlp_native/source-native",
    }
    assert not model.operation("text.constructions/source-native").potential_dependencies
    assert next(role for role in operation.roles if role.direction == "output").kind.endswith(
        "/DdoDeclarationSyntaxProduct"
    )
    assert callable(resolve_prepared_factory(model, sources, operation.semantic_id))
    full = model.operation("text.compose_view/full-native")
    syntax = next(role for role in full.roles if role.name == "declaration_syntax")
    assert syntax.kind.endswith("/DdoConstructionManifest")
    assert syntax.alternatives == ("text.declaration_syntax/source-native",)
    assert syntax.selected == "text.declaration_syntax/source-native"
    assert operation.semantic_id in full.potential_dependencies
    from corpus_structure.semantic.characterization import characterization_profiles

    assert (
        "construction.declaration_syntax"
        in characterization_profiles(prepared)["full_characterization"]
    )
