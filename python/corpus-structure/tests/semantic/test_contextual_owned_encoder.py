"""Owned CPU encoder controls; controlled models establish no provider qualification."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from corpus_structure.methods import contextual_embeddings as embeddings
from corpus_structure.semantic.contextual_encoder import (
    ContextualEncoderSelection,
    contextual_encoder_operation_sources,
)
from corpus_structure.semantic.contextual_operations import contextual_inputs
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
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
    with pytest.raises(ValueError, match="model bytes differ"):
        embeddings._owned_cpu_encoder(
            canonical_bytes(profile.semantic_configuration), str(tmp_path), (("weights", "0" * 64),)
        )
    prior = (("weights", model.stat()),)
    model.write_bytes(b"changed acquired bytes")
    with pytest.raises(ValueError, match="changed after verified loading"):
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
    model = compile_data_operations(bundle, python_sources=sources)
    operation = model.operation("retrieve.contextual_vectors/declared")
    assert operation.capabilities.prepared_factory is not None
    assert operation.result_fields == (("query", "query"), ("vectors", "vectors"))
    assert all(value.complete for value in model.implementation_slices)
    assert {name for name, _ in selection.artifacts} == {"config.json", "modules.json"}
