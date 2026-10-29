"""The query layer's protocol, registry, run selector, page tokens and coverage (P0-C-2;
consolidation and queries §3.9-§3.10). Task rows are written directly, so coverage is read as of
`cut_at` with a task finished between the cut and `finished_at`."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel
from sqlalchemy import Connection, text

from corpus_structure.serve.journey import QueryRefused, StaleToken, coverage, serve_query
from corpus_structure.serve.protocol import QueryContext, Scope, Positioned
from corpus_structure.serve.registry import QueryRegistryError, build_registry

CUT = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)


class CountParams(BaseModel):
    n: int = 5


class CountRow(BaseModel):
    i: int
    run: int


class Count:
    """A test query: the integers below `n`, each with the run it was served from."""

    name = "count"
    params = CountParams
    result = CountRow

    def __init__(self, version: str = "1", units: tuple[str, ...] = ()) -> None:
        self.version = version
        self.units = units

    def rows(self, ctx: QueryContext, p: CountParams, after=None) -> Iterator[Positioned]:
        for i in range(0 if after is None else after + 1, p.n):
            yield Positioned(CountRow(i=i, run=ctx.run_id), i)

    def scope(self, ctx: QueryContext, p: CountParams) -> Scope:
        return Scope.of_units(self.units) if self.units else Scope.run()


# --- The registry (no database) ------------------------------------------------------------------


def test_the_registry_loads_a_pack_plugin_and_refuses_malformed_ones(tmp_path: Path) -> None:
    pack = tmp_path / "toy"
    pack.mkdir()
    (pack / "queries.py").write_text(
        "from pydantic import BaseModel\n"
        "class P(BaseModel):\n    x: int = 0\n"
        "class Q:\n    name, version, params, result = 'plug', '1', P, P\n"
        "    def rows(self, ctx, p):\n        return iter(())\n"
        "    def scope(self, ctx, p):\n        return None\n"
        "class NoRows:\n    name, version, params, result = 'broken', '1', P, P\n"
        "    def scope(self, ctx, p):\n        return None\n"
        "QUERIES = [Q()]\n",
        encoding="utf-8",
    )
    assert set(build_registry([Count()], pack)) == {"count", "plug"}
    assert set(build_registry([Count()], tmp_path / "absent")) == {"count"}
    with pytest.raises(QueryRegistryError, match="clashes"):
        build_registry([Count(), Count()])
    (pack / "queries.py").write_text(
        (pack / "queries.py").read_text().replace("QUERIES = [Q()]", "QUERIES = [NoRows()]")
    )
    with pytest.raises(QueryRegistryError, match=r"broken.*|no rows\(\)"):
        build_registry([], pack)


# --- Runs, journeys and tokens --------------------------------------------------------------------


def finished_run(db: Connection, w: SimpleNamespace, helpers: SimpleNamespace) -> int:
    return helpers.new_run(
        db, w, status="finished", cut_at=CUT, finished_at=CUT + timedelta(minutes=5)
    )


def promote(db: Connection, w: SimpleNamespace, run: int) -> None:
    db.execute(
        text("UPDATE meta.project SET promoted_run_id = :r WHERE id = :p"),
        {"r": run, "p": w.project},
    )


def test_the_selector_pins_the_promoted_run_and_refuses_unfinished_ones(
    db: Connection, world: SimpleNamespace, helpers: SimpleNamespace
) -> None:
    registry = build_registry([Count()])
    with pytest.raises(QueryRefused, match="no promoted run"):
        serve_query(db, registry, "count", project_id=world.project)
    with pytest.raises(QueryRefused, match="run not finished"):
        serve_query(db, registry, "count", run=world.run)  # the world's run is running
    first = finished_run(db, world, helpers)
    promote(db, world, first)
    result = serve_query(db, registry, "count", {"n": 3}, project_id=world.project)
    assert (result.run_id, [r["i"] for r in result.rows]) == (first, [0, 1, 2])
    assert result.next_page_token is None and not result.truncated
    with pytest.raises(QueryRefused, match="no query"):
        serve_query(db, registry, "nothing", run=first)


def test_a_promotion_between_pages_leaves_the_journey_on_its_run(
    db: Connection, world: SimpleNamespace, helpers: SimpleNamespace
) -> None:
    registry = build_registry([Count()])
    first, second = finished_run(db, world, helpers), finished_run(db, world, helpers)
    promote(db, world, first)
    page = serve_query(db, registry, "count", {"n": 5}, project_id=world.project, max_rows=2)
    assert [r["i"] for r in page.rows] == [0, 1] and page.truncated and page.next_page_token
    promote(db, world, second)
    seen = [r["i"] for r in page.rows]
    while page.next_page_token:
        page = serve_query(
            db, registry, "count", {"n": 5}, page_token=page.next_page_token, max_rows=2
        )
        assert page.run_id == first and {r["run"] for r in page.rows} == {first}
        seen += [r["i"] for r in page.rows]
    assert seen == [0, 1, 2, 3, 4]
    with pytest.raises(QueryRefused, match="size limit"):
        serve_query(db, registry, "count", {"n": 5}, run=second, max_chars=20)


def test_stale_tokens_are_refused(
    db: Connection, world: SimpleNamespace, helpers: SimpleNamespace
) -> None:
    run = finished_run(db, world, helpers)
    page = serve_query(db, build_registry([Count()]), "count", {"n": 4}, run=run, max_rows=1)
    token = page.next_page_token
    assert token is not None
    with pytest.raises(StaleToken, match="version 2"):
        serve_query(db, build_registry([Count("2")]), "count", {"n": 4}, page_token=token)
    with pytest.raises(StaleToken, match="parameters differ"):
        serve_query(db, build_registry([Count()]), "count", {"n": 9}, page_token=token)
    with pytest.raises(StaleToken, match="not a page token"):
        serve_query(db, build_registry([Count()]), "count", {"n": 4}, page_token="%%")
    db.execute(text("UPDATE ops.run SET status = 'failed' WHERE id = :r"), {"r": run})
    with pytest.raises(StaleToken, match="run not finished"):
        serve_query(db, build_registry([Count()]), "count", {"n": 4}, page_token=token)


# --- Coverage -------------------------------------------------------------------------------------


def test_coverage_counts_the_fates_as_of_the_cut(
    db: Connection, world: SimpleNamespace, helpers: SimpleNamespace
) -> None:
    run = finished_run(db, world, helpers)
    before, after = CUT - timedelta(minutes=1), CUT + timedelta(minutes=1)
    done = helpers.new_task(
        db, world, run, stage="propose", unit_type="segment", unit_key="u1", input_hash="h1",
        status="done", finished_at=before,
    )  # fmt: skip
    rows: list[dict[str, Any]] = [
        {"unit_key": "u2", "status": "reused", "finished_at": before, "reused_task_id": done},
        {"unit_key": "u3", "status": "skipped", "finished_at": before, "reason": "scope"},
        {"unit_key": "u4", "status": "skipped", "finished_at": before, "reason": "scope"},
        {"unit_key": "u5", "status": "failed", "finished_at": before},
        {"unit_key": "u6", "status": "awaiting_agent"},
        {"unit_key": "u7", "status": "done", "finished_at": after},  # after the cut
    ]
    for n, row in enumerate(rows):
        helpers.new_task(db, world, run, stage="propose", unit_type="segment",
                         input_hash=f"x{n}", **row)  # fmt: skip
    helpers.new_task(db, world, run, stage="ingest", input_hash="ingest", status="done",
                     finished_at=before)  # fmt: skip
    whole = coverage(db, run, Scope.run())
    assert whole.model_dump() == {
        "scope": "run",
        "eligible": 7,
        "extracted": 2,
        "skipped": {"scope": 2},
        "failed": 1,
        "unresolved": 2,
        "partial": True,
        "unresolved_references": 0,
    }
    units = coverage(db, run, Scope.of_units(["u1", "u2"]))
    assert (units.eligible, units.extracted, units.partial) == (2, 2, False)
    registry = build_registry([Count(units=("u1", "u3"))])
    result = serve_query(db, registry, "count", {"n": 1}, run=run)
    assert result.coverage.partial and result.coverage.skipped == {"scope": 1}
    assert result.rows  # partial coverage never fails a query


def test_serialized_response_character_bound_counts_envelope(db,world,helpers):
    run=finished_run(db,world,helpers)
    reg=build_registry([Count()])
    first=serve_query(db,reg,'count',{'n':5},run=run,max_rows=1)
    bound=len(first.model_dump_json())
    page=serve_query(db,reg,'count',{'n':5},run=run,max_chars=bound)
    found=list(page.rows)
    assert len(page.model_dump_json())<=bound
    while page.next_page_token:
        page=serve_query(db,reg,'count',{'n':5},page_token=page.next_page_token,max_chars=bound)
        assert len(page.model_dump_json())<=bound
        found+=page.rows
    assert [r['i'] for r in found]==list(range(5))
