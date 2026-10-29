"""Agent leases, the completion primitive and twins (P0-O-1, orchestration §3.7)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import Connection, Engine, text

from corpus_structure.core.method import UnitRef, UnitView
from corpus_structure.core.vocab import (
    MethodFamily,
    MethodTier,
    RunKind,
    Stage,
    TaskStatus,
    TaskUnitType,
)
from corpus_structure.orchestrate import agent, context, runs, tasks


def setup(db: Connection, orch: SimpleNamespace, tmp_path: Path) -> SimpleNamespace:
    stub = orch.Stub("agent.opus", TaskUnitType.SEGMENT, MethodFamily.AGENT, MethodTier.AGENT)
    w = orch.setup_project(db, tmp_path, methods=[orch.ingest_stub(), stub])
    w.stub = stub
    return w


def run_with_tasks(db: Connection, w: SimpleNamespace, keys: list[str]) -> SimpleNamespace:
    created = runs.create_run(
        db,
        project_id=w.project_id,
        kind=RunKind.FULL,
        versions=w.versions,
        registry=w.registry,
        documents=w.documents,
        commit="t",
    )
    view = context.run_view(db, created.id)
    rc = created.configs["agent.opus/default"]
    units = [UnitView(UnitRef(TaskUnitType.SEGMENT, i + 1, k), view) for i, k in enumerate(keys)]
    made = tasks.create_tasks(db, created.id, Stage.PROPOSE, rc, w.stub, units)
    return SimpleNamespace(id=created.id, config=rc.method_config_id, tasks=made)


def lease(db: Connection, r: SimpleNamespace, session: str = "s1") -> agent.AgentLease:
    (got,) = agent.lease_agent_tasks(
        db, session_ref=session, method_configs=[r.config], run_id=r.id
    )
    return got


def status(db: Connection, task_id: int) -> tuple:
    return tuple(
        db.execute(
            text(
                "SELECT status, reused_task_id, finished_at IS NOT NULL, error "
                "IS NOT NULL FROM ops.task WHERE id = :i"
            ),
            {"i": task_id},
        ).one()
    )


def test_a_first_unclean_submission_is_held_and_the_second_completes(
    db: Connection, orch: SimpleNamespace, tmp_path: Path
) -> None:
    w = setup(db, orch, tmp_path)
    r = run_with_tasks(db, w, ["u1"])
    got = lease(db, r)
    assert (got.attempt, got.packet_hash is not None) == (1, True)
    held = agent.complete_agent_task(
        db,
        got.id,
        got.attempt,
        "s1",
        clean=False,
        outcome=TaskStatus.DONE,
        first_result={"warnings": 2},
    )
    assert held == "held" and status(db, got.id) == ("awaiting_agent", None, False, True)
    done = agent.complete_agent_task(
        db, got.id, got.attempt, "s1", clean=False, outcome=TaskStatus.DONE
    )
    assert done == "completed" and status(db, got.id) == ("done", None, True, True)


def test_twins_settle_across_runs_but_never_from_failed(
    db: Connection, orch: SimpleNamespace, tmp_path: Path
) -> None:
    w = setup(db, orch, tmp_path)
    r1 = run_with_tasks(db, w, ["u1", "u2"])
    r2 = run_with_tasks(db, w, ["u1", "u2"])  # same configuration and inputs: twins
    first = lease(db, r1)
    agent.complete_agent_task(
        db, first.id, first.attempt, "s1", clean=True, outcome=TaskStatus.FAILED
    )
    twin_of_first = next(t for t in r2.tasks if t.unit_key == first.unit_key)
    assert status(db, twin_of_first.id)[0] == "awaiting_agent"  # failed settles nothing
    second = lease(db, r1)
    agent.complete_agent_task(
        db, second.id, second.attempt, "s1", clean=True, outcome=TaskStatus.DONE
    )
    twin = next(t for t in r2.tasks if t.unit_key == second.unit_key)
    assert status(db, twin.id) == ("reused", second.id, True, False)


def test_late_submissions_are_refused_with_their_reason(
    db: Connection, orch: SimpleNamespace, tmp_path: Path
) -> None:
    w = setup(db, orch, tmp_path)
    r1 = run_with_tasks(db, w, ["u1"])
    r2 = run_with_tasks(db, w, ["u1", "u9"])
    late = lease(db, r2)  # u1 in r2, leased before its twin finishes in r1
    db.execute(
        text("UPDATE ops.task SET lease_until = now() - interval '1 second' WHERE id = :i"),
        {"i": late.id},
    )
    owner = lease(db, r1)  # its twin's lease has expired, so it can be leased
    agent.complete_agent_task(
        db, owner.id, owner.attempt, "s1", clean=True, outcome=TaskStatus.DONE
    )
    with pytest.raises(agent.TaskNotOpen) as err:
        agent.complete_agent_task(
            db, late.id, late.attempt, "s1", clean=True, outcome=TaskStatus.DONE
        )
    assert err.value.reason == "twin_settled"
    other = lease(db, r2)
    db.execute(
        text("UPDATE ops.task SET lease_until = now() - interval '1 second' WHERE id = :i"),
        {"i": other.id},
    )
    again = lease(db, r2, "s2")
    assert again.id == other.id and again.attempt == other.attempt + 1
    with pytest.raises(agent.TaskNotOpen) as err:
        agent.complete_agent_task(
            db, other.id, other.attempt, "s1", clean=True, outcome=TaskStatus.DONE
        )
    assert err.value.reason == "leased_again"
    runs.cancel_run(db, r2.id)
    with pytest.raises(agent.TaskNotOpen) as err:
        agent.complete_agent_task(
            db, again.id, again.attempt, "s2", clean=True, outcome=TaskStatus.DONE
        )
    assert err.value.reason == "cancelled"


def test_a_twin_holding_a_lease_is_not_leased_and_release_keeps_the_status(
    db: Connection, orch: SimpleNamespace, tmp_path: Path
) -> None:
    w = setup(db, orch, tmp_path)
    r1 = run_with_tasks(db, w, ["u1"])
    r2 = run_with_tasks(db, w, ["u1"])
    held = lease(db, r1)
    assert (
        agent.lease_agent_tasks(db, session_ref="s2", method_configs=[r2.config], run_id=r2.id)
        == []
    )
    assert agent.release(db, held.id, held.attempt)
    assert status(db, held.id)[0] == "awaiting_agent"
    assert (
        len(agent.lease_agent_tasks(db, session_ref="s2", method_configs=[r2.config], run_id=r2.id))
        == 1
    )


def test_the_reuse_completion_race_is_settled_after_creation(
    committing_db: Engine, orch: SimpleNamespace, tmp_path: Path
) -> None:
    with committing_db.begin() as conn:
        w = setup(conn, orch, tmp_path)
        r1 = run_with_tasks(conn, w, ["u1"])
        owner = lease(conn, r1)
    with committing_db.connect() as creator, committing_db.connect() as completer:
        creating = creator.begin()
        r2 = run_with_tasks(creator, w, ["u1"])  # its lateral lookup finds no finished twin
        with completer.begin():
            agent.complete_agent_task(
                completer, owner.id, owner.attempt, "s1", clean=True, outcome=TaskStatus.DONE
            )
        creating.commit()
        assert status(creator, r2.tasks[0].id)[0] == "awaiting_agent"  # the gap
        creator.rollback()
        with creator.begin():
            assert agent.settle_twins(creator, run_id=r2.id) == 1  # settled after creation
        open_with_twin = creator.execute(
            text(
                "SELECT count(*) FROM ops.task a WHERE a.status = 'awaiting_agent' AND EXISTS "
                "(SELECT 1 FROM ops.task f WHERE f.method_config_id = a.method_config_id AND "
                "f.input_hash = a.input_hash AND f.status IN ('done', 'empty'))"
            )
        ).scalar_one()
    assert open_with_twin == 0
