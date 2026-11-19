"""Controlled encoder integration exercises real query12 projection without provider inference."""

from copy import deepcopy
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from corpus_structure.methods import contextual_embeddings as embeddings
from corpus_structure.semantic.contextual_encoder import (
    prepare_selected_query_context,
)
from corpus_structure.semantic.contextual_encoder_batch import execute_encoder_batch
from corpus_structure.semantic.data_operation_cpu_basis import cpu_authority_batch_values
from corpus_structure.semantic.data_operation_json import json_loads
from corpus_structure.semantic.identity import canonical_bytes
from semantic.selected_context_support import case
from semantic.test_contextual_encoder_batch import _query_members


@pytest.mark.parametrize(
    "recipe", ["located-frame-2", "located-referent-2", "located-discourse-neighbor-2"]
)
def test_selected_encoder_uses_exact_shared_recipe_and_vector_identity(recipe, monkeypatch):
    frame, occurrence, primary, binding, evidence, expected = case(recipe)
    context, inputs = prepare_selected_query_context(
        frame, occurrence, primary, binding=binding, recipe=recipe, evidence=evidence.values()
    )
    assert context["rendered"] == expected
    assert inputs[0]["product_id"] == "product:primary" and json_loads(inputs[0]["reference"]) == [
        "product:primary",
        None,
    ]
    calls = []

    def encode(role):
        def call(texts, **kwargs):
            calls.append((role, texts))
            return [(1.0, 0.0)] * len(texts)

        return call

    model = SimpleNamespace(
        tokenizer=SimpleNamespace(encode=lambda text, **k: tuple(text)),
        encode_query=encode("query"),
        encode_document=encode("document"),
    )
    monkeypatch.setattr(
        embeddings, "_owned_cpu_encoder", lambda *a: (model, (("controlled", "1"),), ())
    )
    profile = embeddings.EncoderProfile(
        "controlled-query12", "a" * 40, 2, "query: ", "document: ", "mean"
    )
    members, packet = _query_members(selected=True, recipe=recipe)
    reply = execute_encoder_batch(packet, asdict(profile), "", (), check_active=lambda: None)
    results = cpu_authority_batch_values(canonical_bytes(reply), expected_members=members)
    result = results[0]
    assert len(results) == 2
    assert canonical_bytes(results[1]["query"]["context"]) == canonical_bytes(context)
    assert expected in calls[0][1][0]
    assert canonical_bytes(result["query"]["context"]) == canonical_bytes(context)
    vector = result["vector"]["vector"]
    assert vector["representation_digest"] == context["representation_digest"]
    lexical_members, lexical_packet = _query_members(recipe=recipe)
    lexical_reply = execute_encoder_batch(
        lexical_packet, asdict(profile), "", (), check_active=lambda: None
    )
    lexical = cpu_authority_batch_values(
        canonical_bytes(lexical_reply), expected_members=lexical_members
    )[0]
    assert lexical["query"]["context"]["recipe"] == "lexical-native-1"
    lexical_vector = lexical["vector"]["vector"]
    assert lexical_vector["vector_id"] != vector["vector_id"]


def test_requested_context_refuses_wrong_member_source_dependency_and_missing_population():
    recipe = "located-frame-2"
    frame, occurrence, primary, binding, evidence, _ = case(recipe)
    for refs, match in (
        (dict(product_id="product:primary", member_id="absent"), "absent"),
        (dict(product_id="product:foreign", member_id="frame"), "closure"),
    ):
        with pytest.raises(ValueError, match=match):
            prepare_selected_query_context(
                frame, occurrence, primary, binding=binding, recipe=recipe, evidence=refs
            )
    changed = deepcopy(primary)
    changed[0]["source"]["document"] = "document:wrong"
    with pytest.raises(ValueError, match="source/scope"):
        prepare_selected_query_context(
            frame, occurrence, changed, binding=binding, recipe=recipe, evidence=evidence.values()
        )
    changed = deepcopy(primary)
    changed[0]["dependencies"] = [dict(product_id="product:missing")]
    with pytest.raises(ValueError, match="closure"):
        prepare_selected_query_context(
            frame, occurrence, changed, binding=binding, recipe=recipe, evidence=evidence.values()
        )
    with pytest.raises(ValueError, match="binding"):
        prepare_selected_query_context(
            frame, occurrence, (), binding=binding, recipe=recipe, evidence=evidence.values()
        )


@pytest.mark.parametrize("failure", ["missing", "empty"])
def test_named_context_failure_is_typed_before_model_allocation(failure, monkeypatch):
    from corpus_structure.semantic import contextual_encoder_batch as batch
    from corpus_structure.semantic.data_operation_values import (
        decode_semantic_value,
        semantic_value,
    )
    from semantic.test_contextual_encoder_batch import _query_members

    members, _ = _query_members(selected=True)
    for member in members:
        basis = decode_semantic_value(member["input_basis"])
        if failure == "missing":
            basis["roles"] = [role for role in basis["roles"] if role["role"] != "primary"]
        else:
            primary = next(role["body"] for role in basis["roles"] if role["role"] == "primary")
            next(row["body"] for row in primary["members"] if row["member_id"] == "predicate")[
                "occurrences"
            ] = []
        member["input_basis"] = semantic_value(basis)

    def refuse(*args, **kwargs):
        raise AssertionError("unavailable requested context reached model allocation")

    monkeypatch.setattr(embeddings, "_owned_cpu_encoder", refuse)
    packet = batch.encoder_packet(members, "retrieve.contextual_query/selected-context")
    prepared, failures = batch.prepare_encoder_members(packet, batch.unpack_encoder_packet(packet))
    assert prepared == () and set(failures) == {0, 1}
    assert all(
        value["encoder_member_failure"]["code"] == "selected-context-unavailable"
        for value in failures.values()
    )


def test_retrieval_refuses_query_vector_from_another_context_before_relation_allocation():
    from corpus_structure.semantic.contextual_operations import prepare_contextual_retrieval
    from semantic.test_declared_contextual_operations import inputs

    selected = inputs()
    selected["query"]["context"]["representation_digest"] = "different-selected-context"
    with pytest.raises(ValueError, match="retained source occurrence"):
        prepare_contextual_retrieval(**selected)
