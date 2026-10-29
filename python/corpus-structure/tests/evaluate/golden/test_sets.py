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


# --- Golden sets on the database ------------------------------------------------------------------


@pytest.fixture
def world(db: Connection, gw: SimpleNamespace, tmp_path: Path) -> SimpleNamespace:
    w = gw.setup_world(db, tmp_path)
    w.source = gw.ingest_run(db, w, gw.spike_contents(w))
    w.config = load_eval(w.pack)
    split_documents(db, w.project_id, w.config.split)
    return w


def create(db: Connection, w: SimpleNamespace, label: str = "p0", **kw) -> sets.CreatedSet:
    return sets.create_golden_set(
        db,
        project_id=w.project_id,
        split=kw.pop("split", DocumentSplit.DEV),
        label=label,
        config=w.config,
        registry=w.registry,
        commit="test",
        **kw,
    )


def test_a_dev_set_forces_the_13_core_units_and_opens_a_golden_run(
    db: Connection, world: SimpleNamespace
) -> None:
    made = create(db, world)
    assert (made.units, made.forced, made.tasks, made.source_run_id) == (40, 13, 80, world.source)
    keys = set(sets.golden_units(db, world.project_id, "p0").keys)
    forced = set(
        db.execute(
            text("SELECT jsonb_array_elements_text(sampling->'forced') FROM eval.golden_set "
                 "WHERE id = :s"), {"s": made.set_id}
        ).scalars()
    )  # fmt: skip
    assert len(forced) == 13 and forced <= keys
    assert "special/Gamma.html#mom1" in forced and "special/LocationScale.html#dfn1" in forced
    run = db.execute(
        text("SELECT kind, status, parent_run_id, options->'scope' AS scope FROM ops.run "
             "WHERE id = :r"), {"r": made.golden_run_id}
    ).one()  # fmt: skip
    assert (run.kind, run.status, run.parent_run_id) == ("golden", "awaiting_agent", world.source)
    assert run.scope["entries"] == sorted(keys)
    by_config = db.execute(
        text(
            "SELECT c.name, t.stage, t.unit_type, t.status, count(*) FROM ops.task t JOIN "
            "ops.method_config c ON c.id = t.method_config_id WHERE t.run_id = :r "
            "GROUP BY 1, 2, 3, 4 ORDER BY 1"
        ),
        {"r": made.golden_run_id},
    ).all()
    assert [tuple(r) for r in by_config] == [
        ("a", "evaluate", "golden_unit", "awaiting_agent", 40),
        ("b", "evaluate", "golden_unit", "awaiting_agent", 40),
    ]
    sampling = db.execute(
        text("SELECT sampling FROM eval.golden_set WHERE id = :s"), {"s": made.set_id}
    ).scalar_one()
    assert sampling["source_run"] == world.source and sampling["size"] == 40
    assert sum(v["quota"] for v in sampling["allocation"].values()) == 40


def test_the_same_seed_draws_the_same_sample_and_a_reused_label_is_refused(
    db: Connection, world: SimpleNamespace
) -> None:
    create(db, world, "p0", seed=3)
    create(db, world, "again", seed=3)
    assert (
        sets.golden_units(db, world.project_id, "p0").keys
        == sets.golden_units(db, world.project_id, "again").keys
    )
    with pytest.raises(GoldenSetError, match="labels are not reused"):
        create(db, world, "p0")


def test_the_golden_run_finishes_only_when_every_unit_is_adjudicated(
    db: Connection, world: SimpleNamespace
) -> None:
    made = create(db, world)
    units = db.execute(
        text("SELECT id FROM eval.golden_unit WHERE golden_set_id = :s ORDER BY id"),
        {"s": made.set_id},
    ).scalars()
    ids = list(units)
    for i in ids[:-1]:
        repo.set_golden_unit(db, i, "adjudicated", {})
    assert not sets.settle_golden_run(db, made.golden_run_id)
    repo.set_golden_unit(db, ids[-1], "stale", {})
    assert not sets.settle_golden_run(db, made.golden_run_id)
    repo.set_golden_unit(db, ids[-1], "adjudicated", {})
    assert sets.settle_golden_run(db, made.golden_run_id)
    row = db.execute(
        text("SELECT status, finished_at IS NOT NULL, cut_at IS NOT NULL FROM ops.run "
             "WHERE id = :r"), {"r": made.golden_run_id}
    ).one()  # fmt: skip
    assert tuple(row) == ("finished", True, True)


def test_the_source_run_must_have_m13_and_a_test_set_holds_no_dev_unit(
    db: Connection, gw: SimpleNamespace, world: SimpleNamespace
) -> None:
    unscoped = gw.ingest_run(db, world, gw.spike_contents(world), scope=False)
    with pytest.raises(GoldenSetError, match="did not cover"):
        create(db, world, from_run=unscoped)
    assert sets.source_run(db, world.project_id) == world.source  # the latest that covers
    # every spike page is forced to dev, so a test set has no pool here
    with pytest.raises(GoldenSetError, match="pool holds 0"):
        create(db, world, "t", split=DocumentSplit.TEST, size=5)
    with pytest.raises(GoldenSetError, match="no dev golden set"):
        sets.golden_units(db, world.project_id, "t")


def test_the_unit_list_holds_no_test_unit(db: Connection, world: SimpleNamespace) -> None:
    create(db, world, size=40)
    listed = sets.golden_units(db, world.project_id, "p0")
    assert listed.keys == tuple(sorted(listed.keys)) and len(listed.keys) == 40
    assert listed.hash == sets.unit_list_hash(listed.keys)
    db.execute(  # a page that sits in test (by an operator's reassignment, say)
        text("UPDATE eval.document_split SET split = 'test' WHERE document_id = :d"),
        {"d": world.documents["special/Gamma.html"].id},
    )
    with pytest.raises(GoldenSetError, match="off dev pages"):
        sets.golden_units(db, world.project_id, "p0")
