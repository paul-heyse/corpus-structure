"""Actual set/view kernels over current typed relations, with independent expected rows."""

import pyarrow as pa
import pytest

from corpus_structure.semantic.analytical_kernels import (
    VIEW_ALTERNATIVES,
    VIEW_CLAIMS,
    VIEW_ENTITIES,
    VIEW_IDENTITY,
    ViewSpec,
)
from corpus_structure.semantic.rich_relations import (
    RICH_FUSION_INPUT,
    RICH_MEANINGS,
    RichRelationKernel,
)


def kernel(check_active=lambda: None):
    return RichRelationKernel(
        property_ids=frozenset({"p:value", "p:label"}),
        threads=1,
        memory_limit="128MB",
        check_active=check_active,
    )


def test_actual_set_kernels_keep_unknown_distinct_and_union_exact_supports_without_spine():
    with kernel() as scope:
        meanings = pa.Table.from_pylist(
            [
                {"key": "slot:a", "meaning": None},
                {"key": "slot:a", "meaning": "known"},
                {"key": "slot:b", "meaning": "same"},
                {"key": "slot:b", "meaning": "same"},
            ],
            schema=RICH_MEANINGS,
        )
        assert scope.disagreements(meanings).to_pylist() == [
            {"key": "slot:a", "meaning": None},
            {"key": "slot:a", "meaning": "known"},
        ]
        candidates = pa.Table.from_pylist(
            [
                {"fact_id": "fact:a", "occurrence_id": "source:b", "evidence": ["pin:2", "pin:1"]},
                {"fact_id": "fact:a", "occurrence_id": "source:a", "evidence": ["pin:2"]},
                {"fact_id": "fact:a", "occurrence_id": None, "evidence": []},
            ],
            schema=RICH_FUSION_INPUT,
        )
        output = scope.fuse(candidates)
        assert output.to_pylist() == [
            {
                "fact_id": "fact:a",
                "supports": ["source:a", "source:b"],
                "candidates": 3,
                "evidence": ["pin:1", "pin:2"],
            }
        ]
    # Actual Arrow result remains usable after connection and input relations are released.
    assert output.num_rows == 1
    with pytest.raises(RuntimeError, match="closed"):
        scope.fuse(candidates)


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
            scope.disagreements(claims)


def test_cancellation_releases_input_relations_and_scope_reopens_cleanly():
    calls = []

    def check():
        calls.append(None)
        if len(calls) == 3:
            raise InterruptedError("cancelled")

    scope = kernel(check)
    values = pa.Table.from_pylist([], schema=RICH_MEANINGS)
    with scope:
        with pytest.raises(InterruptedError):
            scope.disagreements(values)
        assert scope.disagreements(values).num_rows == 0
    assert scope._connection is None


def test_empty_inputs_and_empty_supports_keep_typed_results():
    with kernel() as scope:
        assert scope.fuse(pa.Table.from_pylist([], schema=RICH_FUSION_INPUT)).to_pylist() == []
        assert scope.fuse(
            pa.Table.from_pylist(
                [{"fact_id": "f", "occurrence_id": None, "evidence": []}],
                schema=RICH_FUSION_INPUT,
            )
        ).to_pylist() == [
            {"fact_id": "f", "supports": [], "candidates": 1, "evidence": []}
        ]
        assert scope.views(
            claims=pa.Table.from_pylist([], schema=VIEW_CLAIMS),
            entities=pa.Table.from_pylist([], schema=VIEW_ENTITIES),
            identity=pa.Table.from_pylist([], schema=VIEW_IDENTITY),
            alternatives=pa.Table.from_pylist([], schema=VIEW_ALTERNATIVES),
            specs=(),
        ).to_pylist() == []
