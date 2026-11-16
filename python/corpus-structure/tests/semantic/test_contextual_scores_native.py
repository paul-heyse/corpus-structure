"""Actual backend scoring correspondence over controlled values, without producer standing.

These are numerical/kernel controls. Completion bypass and atomic publication need
an actual declared source/encoder/assembly/scoring chain and remain separate.
"""

import pytest
from sqlalchemy import bindparam, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.contextual_numerics import default_retrieval_numerics
from corpus_structure.semantic.contextual_operations import prepare_contextual_retrieval
from corpus_structure.semantic.contextual_scores import candidates_from_scores, query_contextual_scores
from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.observations import source_value
from semantic.test_declared_contextual_operations import inputs


def native_scores(connection, values, policy):
    return connection.scalar(select(func.ops.ddo_contextual_native_scores(
        *(bindparam(name, values[name], type_=JSONB) for name in ("query", "inventory", "vectors", "policy")),
        bindparam("numerics", policy.model_dump(mode="json"), type_=JSONB))))


def test_generated_native_function_matches_authoritative_core_scores_and_ties(native_rollback):
    connection = native_rollback.connection
    values = inputs()
    acquired = prepare_contextual_retrieval(**values)
    numerics = default_retrieval_numerics()
    expected = query_contextual_scores(connection, acquired, values["query"], values["policy"], numerical_policy=numerics)
    actual = native_scores(connection, values, numerics)
    assert actual == expected
    meaning = connection.scalar(select(func.ops.ddo_contextual_score_meaning(bindparam("scores", actual, type_=JSONB))))
    assert meaning == semantic_value(actual)
    assert [(row["target_id"], row["rank"]) for row in actual["hits"] if row["channel"] == "alias"] == [("one", 1), ("two", 2)]
    assert [row["score_float8_hex"] for row in actual["hits"] if row["channel"] == "dense"] == ["3ff0000000000000", "0000000000000000"]
    candidates = candidates_from_scores(acquired, actual, values["query"], values["policy"], numerical_policy=numerics)
    assert [row.target_id for row in candidates.candidates] == ["one", "two"]


def test_native_score_function_preserves_proven_empty_inventory(native_rollback):
    from dataclasses import asdict
    from corpus_structure.semantic.contextual_retrieval import freeze_inventory
    from corpus_structure.semantic.observations import source_python
    values = inputs()
    empty = freeze_inventory((), source_selection="explicit-empty", scope="source-scope")
    values["inventory"] = dict(inventory=source_value(asdict(empty)))
    vectors = source_python(values["vectors"]["vectors"])
    values["vectors"]["vectors"] = source_value([vectors[0]])
    values["vectors"]["lexical_targets"] = source_value([])
    acquired = prepare_contextual_retrieval(**values)
    numerics = default_retrieval_numerics()
    actual = native_scores(native_rollback.connection, values, numerics)
    assert actual["membership"] == actual["hits"] == []
    assert actual == query_contextual_scores(native_rollback.connection, acquired, values["query"], values["policy"], numerical_policy=numerics)


def test_native_score_refuses_another_backend_policy(native_rollback):
    numerics = default_retrieval_numerics()
    with pytest.raises(DBAPIError, match="exact declared policy"), native_rollback.connection.begin_nested():
        native_scores(native_rollback.connection, inputs(), numerics.model_copy(update={"postgres_version_num": 180008}))
