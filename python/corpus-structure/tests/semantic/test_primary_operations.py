"""The ordinary primary profile captures owned factories and frozen resources."""

import json
from pathlib import Path

from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.native_profiles import pm2_selection
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.data_operation_consumers import resolve_prepared_factory
from corpus_structure.semantic.primary_operations import primary_operation_inputs


def test_primary_inputs_compile_owned_factories_and_exact_provider_custody(tmp_path):
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
        "segment.sentences/source-native",
        "segment.sentences/canonical-projection",
        "text.hanlp_native/source-native",
        "text.formal_evidence/source-native",
        "text.constructions/source-native",
        "text.contextual_evaluation/source-native",
        "text.compose_view/source-native",
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
