"""The sampler, golden sets, the golden run and its settlement, and the unit list (P0-E-1;
evaluation §3.2, §3.4)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from hypothesis import given
from hypothesis import strategies as st
from sqlalchemy import Connection, text

from corpus_structure.core.db import repo
from corpus_structure.core.vocab import DocumentSplit
from corpus_structure.evaluate import sets
from corpus_structure.evaluate.sets import GoldenSetError, PoolUnit, allocate, sample
from corpus_structure.evaluate.split import load_eval, split_documents

# --- The sampler, by hand ------------------------------------------------------------------------


def test_allocation_gives_every_stratum_a_place_and_the_rest_by_largest_remainder() -> None:
    # exact shares 3.5, 1.05, 0.35, 0.1 of 5: floors 3, 1, 0, 0, lifted to at least 1 -> 6
    # places; only a may give one back without dropping below one place
    got = allocate({"a": 70, "b": 21, "c": 7, "d": 2}, {}, 5)
    assert {s: v["quota"] for s, v in got.items()} == {"a": 2, "b": 1, "c": 1, "d": 1}
    # 10 places of 6/3/1: exact 6, 3, 1, no remainder to share
    got = allocate({"a": 6, "b": 3, "c": 1}, {}, 10)
    assert {s: v["quota"] for s, v in got.items()} == {"a": 6, "b": 3, "c": 1}
    # 4 places of 5/5/2: exact 1.667, 1.667, 0.667 -> floors 1, 1, 0 (c lifted to 1) = 3; the
    # largest remainder (a's, then b's, tied 0.667 with c, by key) takes the fourth
    got = allocate({"a": 5, "b": 5, "c": 2}, {}, 4)
    assert {s: v["quota"] for s, v in got.items()} == {"a": 2, "b": 1, "c": 1}


def test_forced_excess_comes_from_the_stratum_furthest_above_its_share() -> None:
    # 6 places of 6/3/3: exact 3, 1.5, 1.5 -> 3, 1, 1, then b by remainder (tie, by key) -> 3, 2,
    # 1. Three units forced in c: 3, 2, 3 = 8 places; a is at its share (0), b 0.5 above, c is
    # held at its forced count: b gives one (1.5 -> 1, now 0.5 below), then a gives one.
    got = allocate({"a": 6, "b": 3, "c": 3}, {"c": 3}, 6)
    assert {s: v["quota"] for s, v in got.items()} == {"a": 2, "b": 1, "c": 3}
    assert got["c"]["forced"] == 3


def test_more_forced_units_than_places_is_refused() -> None:
    pool = [PoolUnit(f"p#u{i}", "definition", i / 10) for i in range(10)]
    with pytest.raises(GoldenSetError, match="exceed the set size"):
        sample(pool, 2, 0, ["p#u1", "p#u2", "p#u3"])
    with pytest.raises(GoldenSetError, match="outside the pool"):
        sample(pool, 5, 0, ["p#elsewhere"])


def test_forced_units_count_towards_their_strata() -> None:
    pool = [PoolUnit(f"p#u{i:02}", "definition" if i % 2 else "remark", i / 20) for i in range(20)]
    drawn = sample(pool, 8, 7, ["p#u01", "p#u03"])  # 6 strata: 2 kinds x 3 terciles
    assert len(drawn.units) == 8 and {"p#u01", "p#u03"} <= set(drawn.units)
    allocation = drawn.sampling["allocation"]
    assert len(allocation) == 6 and sum(v["quota"] for v in allocation.values()) == 8
    assert sum(v["forced"] for v in allocation.values()) == 2


@given(st.permutations(range(30)), st.integers(0, 5))
def test_permuting_the_pool_leaves_the_sample_unchanged(order: list[int], seed: int) -> None:
    pool = [
        PoolUnit(f"p#u{i}", ("definition", "remark", "theorem")[i % 3], (i * 7 % 11) / 11)
        for i in range(30)
    ]
    forced = ["p#u4", "p#u9"]
    drawn = sample(pool, 12, seed, forced)  # 9 strata
    again = sample([pool[i] for i in order], 12, seed, list(reversed(forced)))
    assert again == drawn




def test_unknown_source_math_share_has_its_own_stratum_not_a_numeric_zero():
    drawn=sample([PoolUnit('unknown','definition',None),PoolUnit('zero','definition',0.),PoolUnit('high','definition',1.)],3,7)
    assert drawn.sampling['cut_points']==[0.,1.]
    assert drawn.sampling['allocation']['definition/unknown']['pool']==1
    assert drawn.sampling['allocation']['definition/t0']['pool']==1
    all_unknown=sample([PoolUnit('one','paragraph',None)],1,0)
    assert all_unknown.sampling['cut_points'] is None
    assert set(all_unknown.sampling['allocation'])=={'paragraph/unknown'}
