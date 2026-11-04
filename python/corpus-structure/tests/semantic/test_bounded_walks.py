"""Independent bounded-walk witnesses and replay/work refusal expectations."""

from collections.abc import Iterable
from functools import cached_property
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydantic import JsonValue
from sqlalchemy import Connection as SqlConnection
from sqlalchemy import select

from corpus_structure.semantic.query import EntityReference, QueryRow, ReadLimit
from corpus_structure.semantic.refusals import InvalidContinuation
from corpus_structure.serve.protocol import Positioned, QueryContext
from corpus_structure.serve.read import T
from corpus_structure.serve.registry import build_registry
from corpus_structure.serve.results import ClaimAnswer, RelationAnswer


def query():
    return build_registry([], Path(__file__).resolve().parents[4] / "domains/statistics")[
        "relations_between"
    ]


class Rows:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def all(self):
        return self.rows


class Connection:
    def __init__(self, edges):
        self.edges, self.batch_sizes = edges, []

    def execute(self, stmt):
        p = stmt.compile().params
        subject = p["subject_id_1"]
        after = next(
            (v for k, v in p.items() if k.startswith("param") and isinstance(v, str)), None
        )
        limit = stmt._limit_clause.value
        self.batch_sizes.append(limit)
        rows = sorted(
            (
                dict(fact_id=k, subject_id=s, target=t)
                for k, s, t in self.edges
                if s == subject and (after is None or k > after)
            ),
            key=lambda r: r["fact_id"],
        )
        return Rows(rows[:limit])


class Reader:
    def fact_statement(self, **kwargs):
        return select(T["fact"])

    def iri(self, name):
        return name

    def resolve(self, value, limit=None):
        return [value]

    def claims(self, *, statement):
        ids = statement.compile().params["fact_id_1"]
        for key in sorted(ids):
            yield ClaimAnswer(
                fact=QueryRow(
                    fact_id=key,
                    subject=EntityReference(entity_id="A", memberships=()),
                    property_iri="edge",
                    object_value_id="v",
                    object="B",
                    qualification_value_id=None,
                    qualification=None,
                )
            )


class WalkContext(QueryContext):
    def __init__(self, edges):
        self.adjacency = Connection(edges)
        conn = MagicMock(spec=SqlConnection)
        conn.execute.side_effect = self.adjacency.execute
        super().__init__(run_id=1, conn=conn, row_batch=64)

    @cached_property
    def reader(self) -> Reader:
        return Reader()


def context(edges) -> WalkContext:
    return WalkContext(edges)


def paths(rows: Iterable[Positioned]) -> list[tuple[str, ...]]:
    witnesses = []
    for row in rows:
        assert isinstance(row.row, RelationAnswer)
        witnesses.append(tuple(claim.fact.fact_id for claim in row.row.claims))
    return witnesses


def depth(row: Positioned) -> int:
    position = row.position
    assert isinstance(position, dict)
    value = position["depth"]
    assert type(value) is int
    return value


def test_cycles_repeated_edges_parallel_edges_and_depth_four():
    q = query()
    ctx = context([("e1", "A", "B"), ("e2", "B", "A")])
    p = q.params(a="A", b="B")
    result = list(q.rows(ctx, p))
    assert paths(result) == [("e1",), ("e1", "e2", "e1")]
    assert [depth(r) for r in result] == [1, 3]
    assert next(q.rows(ctx, p, after=result[0].position)).position == result[1].position
    ctx = context([("a", "A", "A"), ("b", "A", "B"), ("c", "A", "B")])
    assert paths(q.rows(ctx, q.params(a="A", b="B", depth=2))) == [
        ("b",),
        ("c",),
        ("a", "b"),
        ("a", "c"),
    ]


def test_nonmatching_intermediate_is_expanded_and_replay_is_not_a_last_row_seek():
    q = query()
    ctx = context([("e1", "A", "X"), ("e2", "X", "B")])
    result = list(q.rows(ctx, q.params(a="A", b="B")))
    assert paths(result) == [("e1", "e2")]
    with pytest.raises(InvalidContinuation, match="not a matching witness"):
        list(
            q.rows(
                ctx,
                q.params(a="A", b="B"),
                after={"walk_version": 2, "depth": 1, "origin": "A", "path": ["e1"]},
            )
        )
    with pytest.raises(InvalidContinuation):
        list(q.rows(ctx, q.params(a="A", b="B"), after="e1|e2"))


def test_adjacency_frontier_and_replay_work_are_bounded():
    q = query()
    edges = [(f"e{i:03}", "A", "B") for i in range(200)]
    ctx = context(edges)
    p = q.params(a="A", b="Z", max_edges=70)
    with pytest.raises(ReadLimit) as caught:
        list(q.rows(ctx, p))
    assert caught.value.reason == "work_limit"
    assert ctx.adjacency.batch_sizes == [64, 7]
    with pytest.raises(ReadLimit):
        list(q.rows(context(edges), q.params(a="A", b="Z", max_frontier=5)))
    with pytest.raises(ReadLimit):
        list(q.rows(context(edges), q.params(a="A", b="Z", max_state_bytes=10)))
    # Even the continuation prefix is examined anew and spends the same edge budget.
    position: JsonValue = {"walk_version": 2, "depth": 1, "origin": "A", "path": ["e100"]}
    with pytest.raises(ReadLimit):
        next(q.rows(context(edges), q.params(a="A", b="B", max_edges=70), after=position))
