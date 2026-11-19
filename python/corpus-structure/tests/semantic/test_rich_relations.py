"""Actual set/view kernels over current typed relations, with independent expected rows."""

from types import SimpleNamespace

import pyarrow as pa
import pytest
from duckdb import BinderException

from corpus_structure.semantic.analytical_kernels import (
    VIEW_ALTERNATIVES,
    VIEW_CLAIMS,
    VIEW_ENTITIES,
    VIEW_IDENTITY,
    ViewSpec,
)
from corpus_structure.semantic.rich_relations import (
    RichRelationKernel,
)


def kernel(check_active=lambda: None):
    return RichRelationKernel(
        property_ids=frozenset({"p:value", "p:label"}),
        check_active=check_active,
    )


def test_actual_views_preserve_null_statement_same_slot_and_explicit_alternatives():
    claims = pa.Table.from_pylist(
        [
            {
                "claim": "a",
                "predicate": "p:value",
                "subject": "subject:1",
                "object": None,
                "statement": None,
            },
            {
                "claim": "b",
                "predicate": "p:value",
                "subject": "subject:1",
                "object": None,
                "statement": None,
            },
            {
                "claim": "c",
                "predicate": "p:value",
                "subject": "subject:1",
                "object": None,
                "statement": "statement:other",
            },
            {
                "claim": "label",
                "predicate": "p:label",
                "subject": "subject:1",
                "object": "entity:label",
                "statement": None,
            },
        ],
        schema=VIEW_CLAIMS,
    )
    entities = pa.Table.from_pylist(
        [
            {
                "entity": "entity:label",
                "key": None,
                "class_id": kind,
                "label": "Observed",
                "symbol": None,
            }
            for kind in ("kind:actual", "kind:second")
        ],
        schema=VIEW_ENTITIES,
    )
    identity = pa.Table.from_pylist([], schema=VIEW_IDENTITY)
    alternatives = pa.Table.from_pylist(
        [
            {"group": "alternative:actual", "claim": "a"},
            {"group": "alternative:actual", "claim": "c"},
        ],
        schema=VIEW_ALTERNATIVES,
    )
    specs = (
        ViewSpec(
            "labels", frozenset({"p:value"}), "p:label", "subject", "subject", "object", "label"
        ),
        ViewSpec(
            "classes", frozenset({"p:value"}), "p:label", "subject", "subject", "object", "types"
        ),
    )
    with kernel() as scope:
        output = scope.views(
            claims=claims,
            entities=entities,
            identity=identity,
            alternatives=alternatives,
            specs=specs,
        )
        rows = {(row["claim"], row["view"]): row["facts"] for row in output.to_pylist()}
        assert rows["a", "same_slot"] == ["b"]
        assert rows["c", "same_slot"] == []
        assert rows["a", "alternative_of"] == ["c"]
        assert rows["a", "labels"] == ["Observed"]
        assert rows["a", "classes"] == ["kind:actual", "kind:second"]
        with pytest.raises(ValueError, match="outside this release"):
            scope.views(
                claims=claims,
                entities=entities,
                identity=identity,
                alternatives=alternatives,
                specs=(
                    ViewSpec(
                        "unowned",
                        frozenset({"p:value"}),
                        "p:forged",
                        "subject",
                        "subject",
                        "object",
                        "label",
                    ),
                ),
            )
        with pytest.raises(ValueError, match="typed schema"):
            scope.views(
                claims=entities,
                entities=entities,
                identity=identity,
                alternatives=alternatives,
                specs=(),
            )


def test_cancellation_releases_input_relations_and_scope_reopens_cleanly():
    calls = []

    def check():
        calls.append(None)
        if len(calls) == 3:
            raise InterruptedError("cancelled")

    scope = kernel(check)
    with scope:

        def views():
            return scope.views(
                claims=pa.Table.from_pylist([], schema=VIEW_CLAIMS),
                entities=pa.Table.from_pylist([], schema=VIEW_ENTITIES),
                identity=pa.Table.from_pylist([], schema=VIEW_IDENTITY),
                alternatives=pa.Table.from_pylist([], schema=VIEW_ALTERNATIVES),
                specs=(),
            )

        with pytest.raises(InterruptedError):
            views()
        assert views().num_rows == 0
    assert scope._connection is None


def test_model_entity_slot_rename_requires_a_matching_working_shape(monkeypatch):
    view = SimpleNamespace(
        get_class=lambda name: SimpleNamespace(
            attributes={name: None for name in ("id", "key", "types", "caption", "symbol")}
        )
    )
    monkeypatch.setattr(
        "corpus_structure.model.compiled.running_model",
        lambda: SimpleNamespace(view=lambda name: view),
    )
    with kernel() as scope, pytest.raises(BinderException, match="e_caption"):
        scope.views(
            claims=pa.Table.from_pylist([], schema=VIEW_CLAIMS),
            entities=pa.Table.from_pylist([], schema=VIEW_ENTITIES),
            identity=pa.Table.from_pylist([], schema=VIEW_IDENTITY),
            alternatives=pa.Table.from_pylist([], schema=VIEW_ALTERNATIVES),
            specs=(),
        )
