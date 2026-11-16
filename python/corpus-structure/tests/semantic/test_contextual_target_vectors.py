"""Independent target-local and exact-selection controls; no provider qualification."""

from copy import deepcopy
from dataclasses import asdict, replace
from types import SimpleNamespace

import pytest

from corpus_structure.methods import contextual_embeddings as embeddings
from corpus_structure.semantic.contextual_encoder import execute_target_encoder_kernel
from corpus_structure.semantic.contextual_operations import contextual_inventory_values
from corpus_structure.semantic.contextual_retrieval import freeze_inventory
from corpus_structure.semantic.contextual_target_products import (
    curated_target_population,
    materialize_target,
    selected_vector_frame,
)
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.observations import source_python, source_value


def population(names):
    return curated_target_population(
        dict(
            targets=source_value(
                [
                    dict(target_id=name, label="alpha", description="Meaning " + name)
                    for name in names
                ]
            )
        ),
        kind_contract="kind:actual-curated-member",
    )


def controlled_model(monkeypatch):
    calls = []

    def encode(texts, **options):
        calls.append((texts, options))
        return [(1.0, 0.0)] * len(texts)

    model = SimpleNamespace(
        tokenizer=SimpleNamespace(encode=lambda text, **k: tuple(text)),
        encode_document=encode,
        encode_query=encode,
    )
    monkeypatch.setattr(
        embeddings, "_owned_cpu_encoder", lambda *a: (model, (("controlled", "1"),), ())
    )
    return calls


def profile():
    return embeddings.EncoderProfile(
        "controlled-targets", "a" * 40, 2, "query: ", "passage: ", "mean"
    )


def inputs(monkeypatch):
    controlled_model(monkeypatch)
    selected = population(("one", "two"))
    values = tuple(
        execute_target_encoder_kernel(
            packet["body"], asdict(profile()), "", (), check_active=lambda: None
        )
        for packet in selected["members"]
    )
    targets = [source_python(packet["body"]["descriptor"]) for packet in selected["members"]]
    inventory = contextual_inventory_values(
        dict(
            source_selection="selected-curated",
            scope="global",
            targets=source_value(targets),
            semantic_targets=source_value({}),
        )
    )
    encoded = embeddings.encode_contexts(
        (embeddings.ContextInput("query", "source:query", "query", "alpha", "alpha query", 0, 5),),
        profile(),
    )
    query = dict(
        original_source="actual-query-original",
        profile=source_value(asdict(profile())),
        vector=asdict(encoded.vectors[0]),
        rendered=asdict(encoded.inputs[0]),
    )
    return inventory, query, values


def test_inventory_expansion_keeps_standalone_target_values_and_project_origins():
    before, after = population(("one", "two")), population(("one", "two", "three"))
    assert before != after and len(before["members"]) == 2 and len(after["members"]) == 3
    by_id = {value["member_id"]: value for value in after["members"]}
    for packet in before["members"]:
        assert packet == by_id[packet["member_id"]]
        assert packet["context"]["original_source"] is None
        assert packet["body"]["original_source"] is None
        context = SubjectContext(
            "project",
            packet["context"]["subject"],
            None,
            json_bytes(packet["context"]["analyzed_scope"]),
            subject_definition="contextual-target",
        )
        assert materialize_target(packet["body"], context=context) == packet["body"]
        with pytest.raises(ValueError, match="exact discovered context"):
            materialize_target(
                packet["body"], context=replace(context, original_source="query-document")
            )


def test_target_encoding_uses_document_profile_rendering_and_only_one_target(monkeypatch):
    calls = controlled_model(monkeypatch)
    packet = population(("one",))["members"][0]
    result = execute_target_encoder_kernel(
        packet["body"], asdict(profile()), "", (), check_active=lambda: None
    )
    assert result["original_source"] is None
    assert result["vector"]["object_id"] == "one"
    assert result["vector"]["values"] == (1.0, 0.0)
    assert result["rendered"]["role"] == "document"
    assert len(calls) == 1 and len(calls[0][0]) == 1
    assert calls[0][1]["prompt"] == "passage: "
    assert calls[0][1]["batch_size"] == 16
    assert calls[0][1]["normalize_embeddings"] and calls[0][1]["precision"] == "float32"


def test_selection_preserves_exact_prior_vector_bytes_and_does_no_encoding(monkeypatch):
    inventory, query, targets = inputs(monkeypatch)
    original = deepcopy(targets)

    def forbidden(*args, **kwargs):
        pytest.fail("selection performed inference")

    monkeypatch.setattr(embeddings, "encode_contexts", forbidden)
    frame = selected_vector_frame(inventory, query, tuple(reversed(targets)))
    vectors = source_python(frame["vectors"])
    assert [value["object_id"] for value in vectors] == ["one", "query", "two"]
    assert vectors[0] == dict(original[0]["vector"], values=list(original[0]["vector"]["values"]))
    assert targets == original


@pytest.mark.parametrize(
    "corruption",
    [
        "missing",
        "duplicate",
        "foreign",
        "profile",
        "source",
        "representation",
        "input",
        "vector_id",
        "vector_profile",
        "dimension",
        "nonfinite",
        "zero",
        "rendering",
    ],
)
def test_selection_refuses_thirteen_independent_corruptions_before_retrieval(
    monkeypatch, corruption
):
    inventory, query, targets = inputs(monkeypatch)
    targets = list(deepcopy(targets))
    value, vector = targets[0], targets[0]["vector"]
    if corruption == "missing":
        targets.pop()
    elif corruption == "duplicate":
        targets.append(deepcopy(value))
    elif corruption == "foreign":
        vector["object_id"] = "foreign"
    elif corruption == "profile":
        value["profile"] = source_value(asdict(replace(profile(), document_prompt="changed: ")))
    elif corruption == "source":
        vector["source_binding"] = "another-source"
    elif corruption == "representation":
        vector["representation_digest"] = "another-description"
    elif corruption == "input":
        vector["input_digest"] = "another-rendering"
    elif corruption == "vector_id":
        vector["vector_id"] = "another-vector"
    elif corruption == "vector_profile":
        vector["profile_id"] = "another-profile"
    elif corruption == "dimension":
        vector["values"] = (1.0,)
    elif corruption == "nonfinite":
        vector["values"] = (float("nan"), 0.0)
    elif corruption == "zero":
        vector["values"] = (0.0, 0.0)
    else:
        value["rendered"]["text"] = "forged tokenizer input"
    with pytest.raises(ValueError):
        selected_vector_frame(inventory, query, tuple(targets))


def test_explicit_empty_selection_is_distinct_from_missing_vectors(monkeypatch):
    inventory, query, _ = inputs(monkeypatch)
    with pytest.raises(ValueError, match="missing required inventory"):
        selected_vector_frame(inventory, query, ())
    empty = dict(
        inventory=source_value(
            asdict(freeze_inventory((), source_selection="explicit-empty", scope="global"))
        )
    )
    frame = selected_vector_frame(empty, query, ())
    assert [value["object_id"] for value in source_python(frame["vectors"])] == ["query"]
