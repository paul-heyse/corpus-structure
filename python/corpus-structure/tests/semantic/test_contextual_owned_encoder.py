"""Owned CPU encoder controls; controlled models establish no provider qualification."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from corpus_structure.methods import contextual_embeddings as embeddings
from corpus_structure.semantic.contextual_encoder import (
    ContextualEncoderSelection,
    contextual_encoder_declarations,
    contextual_encoder_operation_sources,
)
from corpus_structure.semantic.contextual_operations import (
    contextual_inputs,
    contextual_operation_declarations,
)
from corpus_structure.semantic.declared_structural_calls import structural_operation_declarations
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.types import SourceArtifact, SourceBundle


def test_owned_encoder_keeps_original_query_document_calls_and_vectors(monkeypatch):
    calls = []

    def encode(role):
        def run(texts, **options):
            calls.append((role, texts, options))
            return [(1.0, 0.0)] * len(texts)

        return run

    model = SimpleNamespace(
        tokenizer=SimpleNamespace(encode=lambda text, **kwargs: tuple(text)),
        encode_query=encode("query"),
        encode_document=encode("document"),
    )
    monkeypatch.setattr(
        embeddings, "_owned_cpu_encoder", lambda *args: (model, (("controlled", "1"),), ())
    )
    profile = embeddings.EncoderProfile(
        "controlled-kernel", "a" * 40, 2, "query: ", "passage: ", "mean"
    )
    inputs = (
        embeddings.ContextInput("occurrence", "original", "query", "alpha", "alpha beta", 0, 5),
        embeddings.ContextInput(
            "target",
            "target-source",
            "document",
            "alpha",
            "alpha description",
            0,
            5,
            representation_digest="actual-description",
        ),
    )
    result = embeddings.encode_contexts(inputs, profile)
    assert [value.object_id for value in result.vectors] == ["occurrence", "target"]
    assert [row[0] for row in calls] == ["query", "document"]
    assert [row[2]["prompt"] for row in calls] == ["query: ", "passage: "]
    assert all(row[2]["precision"] == "float32" and row[2]["normalize_embeddings"] for row in calls)
    assert all(value.values == (1.0, 0.0) for value in result.vectors)


def test_owned_encoder_refuses_changed_model_before_import_or_allocation(tmp_path):
    model = tmp_path / "weights"
    model.write_bytes(b"actual acquired bytes")
    profile = embeddings.EncoderProfile(
        "controlled-kernel", "a" * 40, 2, "query: ", "passage: ", "mean"
    )
    with pytest.raises(ValueError, match="acquired file changed: .*restart required"):
        embeddings._owned_cpu_encoder(
            canonical_bytes(profile.semantic_configuration), str(tmp_path), (("weights", "0" * 64),)
        )
    from corpus_structure.semantic.file_custody import observed_file

    prior = (("weights", observed_file(model)),)
    model.write_bytes(b"changed acquired bytes")
    with pytest.raises(ValueError, match="acquired file changed: .*restart required"):
        embeddings._verify_cpu_artifacts(str(tmp_path), prior)


def test_contextual_encoder_captures_cpu_acquisition_and_closed_source_factory(tmp_path):
    for name in ("config.json", "modules.json"):
        (tmp_path / name).write_text("{}")
    profile = embeddings.EncoderProfile(
        "controlled-source-capture", "a" * 40, 2, "query: ", "passage: ", "mean"
    )
    selection = ContextualEncoderSelection.acquire(profile, tmp_path)
    sources = contextual_encoder_operation_sources(selection)
    root = Path(__file__).parents[2] / "src/corpus_structure/model/semantic"
    bundle = contextual_inputs(
        SourceBundle("core", (SourceArtifact("core", (root / "core.yaml").read_bytes()),))
    )
    from corpus_structure.semantic.composed import data_operation_dependencies
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.prepare import prepare_release
    from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies

    prepared = prepare_release(
        bundle,
        data_operation_dependencies(
            ResolvedDependencies(),
            declarations=(
                contextual_encoder_declarations(),
                contextual_operation_declarations(),
                structural_operation_declarations(),
            ),
            python_sources=sources,
        ),
        PreparationProfile(version="semantic-2"),
    )
    model = bound_data_operation_model(prepared)
    operation = model.operation("retrieve.contextual_query/declared")
    assert operation.capabilities.prepared_factory is not None
    for name in ("retrieve.contextual_query/declared", "retrieve.contextual_query/selected-context", "retrieve.contextual_target_vector/declared"):
        actual = model.operation(name)
        assert actual.capabilities.forms == ("batch",)
        assert set(actual.outcomes) == {"success", "failed"}
    assert operation.result_fields == (("query", "query"), ("vector", "vector"))
    selected = model.operation("retrieve.contextual_query/selected-context")
    assert selected.capabilities.prepared_factory is not None
    primary = next(role for role in selected.roles if role.name == "primary")
    assert primary.support is not None
    assert primary.support.source_set == "query-context-primary" and primary.minimum == 1
    for query_operation in (operation, selected):
        inputs = {role.name: role for role in query_operation.roles if role.direction == "input"}
        for name in ("source", "occurrence"):
            support = inputs[name].support
            assert support is not None
            assert support.source_set == "contextual-query-" + name
            assert inputs[name].minimum == inputs[name].maximum == 1
            assert inputs[name].subject_target == "subject"
    assert len(selected.output_witnesses) == 2
    assert all(value.complete for value in model.implementation_slices), [
        (value.root, value.unknowns) for value in model.implementation_slices if not value.complete
    ]
    assert {name for name, _ in selection.artifacts} == {"config.json", "modules.json"}
    from corpus_structure.semantic.data_operation_demands import (
        OperationSelection,
        RootSubject,
        freeze_demand,
    )

    assert operation.replicate_policy == selected.replicate_policy == "explicit-replicates"
    assert operation.precision_description is None and operation.numerical_policy is not None
    arguments = dict(
        roots=(RootSubject("source", "original", b"{}"),),
        targets=(operation.semantic_id,),
        inference="declared",
        execution_profile="cpu",
    )
    with pytest.raises(ValueError, match="explicit replicate selection is required"):
        freeze_demand(model, **arguments)
    from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet

    intent = freeze_demand(
        model,
        selections=(
            OperationSelection(operation.semantic_id, replicate="operator-selected-sample-A"),
        ),
        source_sets=tuple(
            FrozenSourceSet.unqualified(name, ())
            for name in ("contextual-query-source", "contextual-query-occurrence")
        ),
        **arguments,
    )
    frozen = next(
        value
        for value in intent.record["operations"]
        if value["operation"] == operation.semantic_id
    )
    assert frozen["replicate"] == "operator-selected-sample-A"


def test_encoder_numerical_policy_changes_space_without_approximate_product_equality(monkeypatch):
    profile = embeddings.E5
    original = profile.profile_id
    policy = embeddings.ENCODER_NUMERICS
    assert (
        profile.semantic_configuration["numerical_policy"]["nondeterminism"]
        == "cohort-and-order-dependent-native-float32"
    )
    assert (
        profile.semantic_configuration["numerical_policy"]["result_equality"]
        == "exact-canonical-value"
    )
    with pytest.raises(ValueError, match="L2-normalized"):
        embeddings.validate_vector((1.0001, 0.0), 2)
    monkeypatch.setattr(
        embeddings, "ENCODER_NUMERICS", policy.model_copy(update={"absolute_tolerance": 1e-3})
    )
    assert profile.profile_id != original
    assert embeddings.validate_vector((1.0001, 0.0), 2) == (1.0001, 0.0)
