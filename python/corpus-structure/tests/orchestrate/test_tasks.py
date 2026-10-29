"""Tasks, digests and reuse (P0-O-1, orchestration §3.5)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.method import UnitRef, UnitView
from corpus_structure.core.vocab import (
    MethodFamily,
    MethodTier,
    RunKind,
    SkipReason,
    Stage,
    TaskStatus,
    TaskUnitType,
)
from corpus_structure.orchestrate import context, runs, tasks


def world(db: Connection, orch: SimpleNamespace, tmp_path: Path) -> SimpleNamespace:
    def no_digest(unit: Any, cfg: Any) -> bytes:
        raise AssertionError("a skipped unit is never digested")

    m09 = orch.Stub("extract.math", TaskUnitType.RENDITION, MethodFamily.EXTRACT)
    agent = orch.Stub("agent.opus", TaskUnitType.SEGMENT, MethodFamily.AGENT, MethodTier.AGENT)
    m19 = orch.Stub(
        "validate.rules",
        TaskUnitType.RUN,
        MethodFamily.VALIDATE,
        digest=lambda unit, cfg: b"the run",
    )
    strict = orch.Stub("normalize.formula", TaskUnitType.RENDITION, digest=no_digest)
    methods = [orch.ingest_stub(), m09, agent, m19, strict]
    w = orch.setup_project(db, tmp_path, methods=methods)
    w.methods = {m.name: m for m in methods}
    return w


def new_run(db: Connection, w: SimpleNamespace, **explicit: Any) -> tuple[int, Any, dict]:
    created = runs.create_run(
        db,
        project_id=w.project_id,
        kind=RunKind.FULL,
        versions=w.versions,
        registry=w.registry,
        documents=w.documents,
        commit="t",
        explicit=explicit,
    )
    return created.id, context.run_view(db, created.id), dict(created.configs)


def units(view: Any, unit_type: TaskUnitType, keys: list[str]) -> list[UnitView]:
    return [
        UnitView(UnitRef(unit_type, i + 1, k), view, rendition_id=i + 1) for i, k in enumerate(keys)
    ]


def create(
    db: Connection,
    w: SimpleNamespace,
    run: int,
    view: Any,
    configs: dict,
    method: str,
    keys: list[str],
    unit_type: TaskUnitType = TaskUnitType.RENDITION,
    **kw: Any,
) -> list[tasks.CreatedTask]:
    return tasks.create_tasks(
        db,
        run,
        Stage.NORMALIZE,
        configs[f"{method}/default"],
        w.methods[method],
        units(view, unit_type, keys),
        **kw,
    )


def finish(db: Connection, ids: list[int], status: str = "done") -> None:
    db.execute(
        text("UPDATE ops.task SET status = :s, finished_at = clock_timestamp() WHERE id = ANY(:i)"),
        {"s": status, "i": ids},
    )


def test_reuse_at_creation_and_fresh(db: Connection, orch: SimpleNamespace, tmp_path: Path) -> None:
    w = world(db, orch, tmp_path)
    r1, v1, c1 = new_run(db, w)
    first = create(db, w, r1, v1, c1, "extract.math", ["a", "b"])
    assert [t.status for t in first] == [TaskStatus.PENDING] * 2
    finish(db, [first[0].id], "done")
    finish(db, [first[1].id], "empty")
    r2, v2, c2 = new_run(db, w)
    second = create(db, w, r2, v2, c2, "extract.math", ["a", "b", "c"])
    assert [t.status for t in second] == [TaskStatus.REUSED, TaskStatus.REUSED, TaskStatus.PENDING]
    assert [t.reused_task_id for t in second[:2]] == [first[0].id, first[1].id]
    stamped = db.execute(
        text("SELECT count(*) FROM ops.task WHERE id = ANY(:i) AND finished_at IS NOT NULL"),
        {"i": [t.id for t in second]},
    ).scalar_one()
    assert stamped == 2
    r3, v3, c3 = new_run(db, w, fresh=["extract.math"])
    third = create(db, w, r3, v3, c3, "extract.math", ["a"], fresh=True)
    assert third[0].status == TaskStatus.PENDING
    with pytest.raises(runs.RunError, match="unregistered"):
        new_run(db, w, fresh=["no.such"])


def test_run_tasks_are_never_reused_and_agent_tasks_start_awaiting(
    db: Connection, orch: SimpleNamespace, tmp_path: Path
) -> None:
    w = world(db, orch, tmp_path)
    r1, v1, c1 = new_run(db, w)
    run_task = create(db, w, r1, v1, c1, "validate.rules", ["run"], TaskUnitType.RUN)
    finish(db, [run_task[0].id])
    r2, v2, c2 = new_run(db, w)
    again = create(db, w, r2, v2, c2, "validate.rules", ["run"], TaskUnitType.RUN)
    assert again[0].status == TaskStatus.PENDING
    agent = create(db, w, r2, v2, c2, "agent.opus", ["u1"], TaskUnitType.SEGMENT)
    assert agent[0].status == TaskStatus.AWAITING_AGENT
    packet = db.execute(
        text("SELECT packet_hash FROM ops.task WHERE id = :i"), {"i": agent[0].id}
    ).scalar_one()
    assert packet.startswith("packet:")


def test_skipped_fates_and_prerequisite_failed(
    db: Connection, orch: SimpleNamespace, tmp_path: Path
) -> None:
    w = world(db, orch, tmp_path)
    r1, v1, c1 = new_run(db, w)
    skipped = create(db, w, r1, v1, c1, "normalize.formula", ["a"], skipped={0: SkipReason.SCOPE})
    row = db.execute(
        text(
            "SELECT status, reason, input_hash, finished_at IS NOT NULL FROM ops.task WHERE id = :i"
        ),
        {"i": skipped[0].id},
    ).one()
    assert tuple(row) == ("skipped", "scope", "skip:scope", True)
    upstream = create(db, w, r1, v1, c1, "extract.math", ["a", "b"])
    finish(db, [upstream[0].id], "failed")
    downstream = create(db, w, r1, v1, c1, "normalize.formula", ["a"], upstream=["extract.math"])
    reason = db.execute(
        text("SELECT status, reason FROM ops.task WHERE id = :i"), {"i": downstream[0].id}
    ).one()
    assert tuple(reason) == ("skipped", "prerequisite_failed")
    # a skipped task is never a reuse source: the same unit in a new run is digested afresh
    r2, v2, c2 = new_run(db, w)
    m09 = create(db, w, r2, v2, c2, "extract.math", ["a"], skipped={0: SkipReason.LIMIT})
    after = create(db, w, r2, v2, c2, "extract.math", ["a"])
    assert m09[0].status == TaskStatus.SKIPPED and after[0].status == TaskStatus.PENDING


@pytest.mark.parametrize(("column", "value"), [("reason", "scoop"), ("stage", "ingestion")])
def test_reasons_and_stages_outside_their_vocabularies_are_refused(
    db: Connection, orch: SimpleNamespace, tmp_path: Path, column: str, value: str
) -> None:
    w = world(db, orch, tmp_path)
    r1, v1, c1 = new_run(db, w)
    created = create(db, w, r1, v1, c1, "extract.math", ["a"])
    with pytest.raises(DBAPIError) as err, db.begin_nested():
        db.execute(
            text(f"UPDATE ops.task SET {column} = :v WHERE id = :i"),
            {"v": value, "i": created[0].id},
        )
    assert getattr(err.value.orig, "sqlstate", None) == "23514"
