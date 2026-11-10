"""Preparation lifetime is separate from query results and database borrowing."""

from dataclasses import replace
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy import Connection

from corpus_structure.methods.contextual_embeddings import EncodedVector
from corpus_structure.semantic.contextual_retrieval import freeze_inventory, target_representation
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.types import PreparedRelease


def inputs():
    target = target_representation("target", "source", "label", "description")
    inventory = freeze_inventory((target,), source_selection="source", scope="global")
    vectors = (
        EncodedVector(
            "v", "target", "source", "profile", "input", (1.0, 0.0), target.representation_digest
        ),
    )
    query = EncodedVector("q", "query", "source", "profile", "input", (0.0, 1.0))
    return inventory, vectors, query


def test_reader_prepares_once_and_keeps_queries_and_connections_separate(monkeypatch):
    from corpus_structure.semantic import contextual_retrieval, contextual_storage

    inventory, vectors, query = inputs()
    prepared = cast(
        PreparedRelease, SimpleNamespace(release_id="release", execution_model_id="model")
    )
    reader = BoundReader(cast(Connection, object()), 1, prepared)
    calls, observed = [], []
    original = contextual_storage.transient_vector_relation

    def prepare(*args, **kwargs):
        calls.append(args)
        return original(*args, **kwargs)

    def retrieve(conn, **kwargs):
        observed.append((conn, kwargs))
        return "result"

    monkeypatch.setattr(contextual_storage, "transient_vector_relation", prepare)
    monkeypatch.setattr(contextual_retrieval, "retrieve_candidates", retrieve)
    request = dict(
        occurrence_id="query",
        query=query,
        inventory=inventory,
        target_vectors=vectors,
        lexical_query="label",
        dimension=2,
        budget=10,
        channel_budget=30,
    )
    first_conn = reader.conn
    assert reader.contextual_candidates(**request) == "result"
    reader.conn = cast(Connection, object())
    reader.contextual_candidates(**dict(request, lexical_query="description"))
    assert len(calls) == 1
    assert observed[0][0] is first_conn and observed[1][0] is reader.conn
    assert observed[0][1]["relation"] is observed[1][1]["relation"]
    assert observed[1][1]["lexical_query"] == "description"
    reader.contextual_candidates(**dict(request, inventory=replace(inventory)))
    assert len(calls) == 2
    reader.contextual_candidates(**request)
    assert len(calls) == 3
    reader.cut_id = 2
    reader.contextual_candidates(**request)
    assert len(calls) == 4
    entry = reader._contextual_preparation
    assert entry is not None
    assert not any(value is reader.conn or value is first_conn for value in vars(entry).values())


@pytest.mark.parametrize(
    "change",
    [
        "vector_values",
        "vectors",
        "targets",
        "aliases",
        "vector_record",
        "target_record",
        "inventory_record",
    ],
)
def test_mutable_inputs_are_refused_before_preparation(change):
    from corpus_structure.semantic.contextual_storage import prepare_contextual_inventory

    inventory, vectors, _ = inputs()
    if change == "vector_values":
        vectors = (replace(vectors[0], values=cast(Any, [1.0, 0.0])),)
    elif change == "vectors":
        vectors = list(vectors)
    elif change == "targets":
        inventory = replace(inventory, targets=cast(Any, list(inventory.targets)))
    elif change == "vector_record":
        vectors = (cast(Any, SimpleNamespace(**vars(vectors[0]))),)
    elif change == "target_record":
        inventory = replace(
            inventory, targets=(cast(Any, SimpleNamespace(**vars(inventory.targets[0]))),)
        )
    elif change == "inventory_record":
        inventory = cast(Any, SimpleNamespace(**vars(inventory)))
    else:
        # Bypass constructor validation to challenge the preparation trust boundary.
        target = replace(inventory.targets[0])
        object.__setattr__(target, "aliases", ["mutable"])
        inventory = replace(inventory, targets=(target,))
    with pytest.raises(ValueError, match="immutable"):
        prepare_contextual_inventory(
            (1, None, "release", "model"), inventory, vectors, profile_id="profile", dimension=2
        )
