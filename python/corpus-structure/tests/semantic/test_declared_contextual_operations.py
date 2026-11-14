"""Exact native ranking and current consumers over explicitly retained vector facts."""

from dataclasses import asdict
from pathlib import Path

import pytest

from corpus_structure.methods.contextual_embeddings import EncodedVector, EncoderProfile, identity
from corpus_structure.semantic.contextual_operations import (
    contextual_inputs,
    contextual_interpretation_candidates,
    contextual_operation_sources,
    contextual_retrieval_values,
)
from corpus_structure.semantic.contextual_retrieval import freeze_inventory, target_representation
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.observations import source_python, source_value
from corpus_structure.semantic.types import SourceArtifact, SourceBundle


def inputs():
    profile = EncoderProfile("controlled-retained-vectors", "a" * 40, 2, "query: ", "passage: ", "mean")
    targets = tuple(target_representation(key, "source:" + key, "alpha", "alpha " + key) for key in ("one", "two"))
    inventory = freeze_inventory(targets, source_selection="selected-authored-targets", scope="source-scope")

    def vector(object_id, binding, representation, values):
        digest = identity("context-vector", [object_id, binding, profile.profile_id, "actual-input", representation])
        return EncodedVector(digest, object_id, binding, profile.profile_id, "actual-input", values, representation)

    query_vector = vector("occurrence", "source:original", "located-query-context", (1.0, 0.0))
    vectors = (query_vector, *(vector(target.target_id, target.source_binding, target.representation_digest, values) for target, values in zip(targets, ((1.0, 0.0), (0.0, 1.0)), strict=True)))
    query = {"source_pin": {"source": "source:original"}, "occurrence_id": "occurrence", "lexical_query": "alpha", "query_vector_id": query_vector.vector_id, "anchors": ({"anchor_id": "original-relative-location"},)}
    policy = {"budget": 2, "channel_budget": 3, "constraints": source_value([{"constraint_id": "meaning", "relation_kinds": ["denotes"], "occurrence_role": "mention", "target_role": "concept", "multiplicity": "one"}]), "witnesses": source_value([]), "exclusions": source_value([])}
    return {"query": query, "inventory": {"inventory": source_value(asdict(inventory))}, "vectors": {"profile": source_value(asdict(profile)), "vectors": source_value([asdict(value) for value in vectors])}, "policy": policy}


def test_contextual_retrieval_captures_factory_and_source_witness():
    root = Path(__file__).parents[2] / "src/corpus_structure/model/semantic"
    bundle = contextual_inputs(SourceBundle("core", (SourceArtifact("core", (root / "core.yaml").read_bytes()),)))
    model = compile_data_operations(bundle, python_sources=contextual_operation_sources())
    operation = model.operation("retrieve.contextual/declared")
    assert operation.capabilities.prepared_factory is not None
    assert len(operation.output_witnesses) == 1
    assert all(item.complete for item in model.implementation_slices)


def test_contextual_native_ranking_preserves_equal_labels_and_private_standing(native_rollback):
    product = contextual_retrieval_values(native_rollback.connection, **inputs())
    candidates = contextual_interpretation_candidates(product)
    assert [(value.target_id, value.label, value.rank) for value in candidates.targets] == [("one", "alpha", 1), ("two", "alpha", 2)]
    decision = source_python(product["relationship_decision"])
    assert decision["outcome"] == "insufficient_evidence"
    assert decision["selected_edges"] == []
    assert candidates.anchors == ({"anchor_id": "original-relative-location"},)


def test_contextual_retrieval_refuses_duplicate_or_foreign_vector_before_database():
    values = inputs()
    raw = source_python(values["vectors"]["vectors"])
    values["vectors"]["vectors"] = source_value([*raw, raw[0]])
    with pytest.raises(ValueError, match="membership"):
        contextual_retrieval_values(None, **values)
    values = inputs()
    raw = source_python(values["vectors"]["vectors"])
    raw[1]["representation_digest"] = "foreign-description"
    raw[1]["vector_id"] = identity("context-vector", [raw[1]["object_id"], raw[1]["source_binding"], raw[1]["profile_id"], raw[1]["input_digest"], raw[1]["representation_digest"]])
    values["vectors"]["vectors"] = source_value(raw)
    with pytest.raises(ValueError, match="another representation"):
        contextual_retrieval_values(None, **values)
