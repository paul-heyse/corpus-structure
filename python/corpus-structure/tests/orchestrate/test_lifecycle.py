"""The lifecycle state machine (P0-O-1, orchestration §6; D9 §4).

Rules create tasks (in a run, or a new one), claim, renew, complete, fail and expire worker leases,
write late from stale leases, lease, release, hold and complete agent tasks, settle twins and seal
runs. A reference model of each task's status, attempt, holder and lease, and of the finished
(configuration, hash) pairs, predicts every outcome; the invariants are checked after every step.

Each example runs in one rolled-back transaction on a clone holding a committed project; savepoints
stand in for the separate transactions of claims and writes. `now()` is fixed within the example,
so a lease expires by moving its `lease_until` into the past. Scheduling is not explored (real
interleavings are the two-connection tests' and `s6.queue`'s).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from hypothesis import HealthCheck, settings
from hypothesis import strategies as st
from hypothesis.stateful import (
    Bundle,
    RuleBasedStateMachine,
    consumes,
    invariant,
    precondition,
    rule,
    run_state_machine_as_test,
)
from sqlalchemy import Connection, Engine, text

from corpus_structure.core.method import MethodSettings, UnitRef, UnitResult, UnitView
from corpus_structure.core.vocab import (
    MethodFamily,
    MethodTier,
    ObservationOutcome,
    RunKind,
    RunStatus,
    Stage,
    TaskStatus,
    TaskUnitType,
)
from corpus_structure.orchestrate import agent, context, phase0, queue, runs, tasks
from corpus_structure.orchestrate.registry import RunConfigs
from corpus_structure.orchestrate.runner import Graph, Runner, seal

KEYS = ("a", "b", "c")  # a small alphabet of inputs, so reuse and twins occur
FINISHED = (TaskStatus.DONE, TaskStatus.EMPTY)
TERMINAL = (
    *FINISHED,
    TaskStatus.FAILED,
    TaskStatus.REUSED,
    TaskStatus.SKIPPED,
    TaskStatus.CANCELLED,
)


def pick_from[T](data: st.DataObject, options: list[T]) -> T:
    """An element of the model's ordered list, drawn by index: the database's ids differ between
    replays (sequences never roll back), so the draw must not see them."""
    return options[data.draw(st.integers(0, len(options) - 1))]


@dataclass
class Model:
    id: int
    run: int
    kind: str  # worker | agent
    config: int
    hash: str
    status: TaskStatus
    attempt: int = 0
    holder: str | None = None
    expired: bool = False  # the lease's lease_until is in the past
    held: bool = False  # an agent task holding a first unclean submission
    reused_from: int | None = None

    @property
    def lease_active(self) -> bool:
        return self.holder is not None and not self.expired


@dataclass(frozen=True)
class Lease:
    task: int
    attempt: int
    holder: str


@dataclass
class Runs:
    status: dict[int, RunStatus] = field(default_factory=dict)
    cut: dict[int, Any] = field(default_factory=dict)
    terminal_at_seal: dict[int, set[int]] = field(default_factory=dict)


class Lifecycle(RuleBasedStateMachine):
    worker_leases = Bundle("worker_leases")
    agent_leases = Bundle("agent_leases")

    def __init__(self, engine: Engine, w: SimpleNamespace) -> None:
        super().__init__()
        self.w = w
        self.conn: Connection = engine.connect()
        self.outer = self.conn.begin()
        self.tasks: dict[int, Model] = {}
        self.runs = Runs()
        self.attempts: dict[int, int] = {}
        self.sessions = 0
        self.new_run()

    def teardown(self) -> None:
        self.outer.rollback()
        self.conn.close()

    # -- helpers -------------------------------------------------------------------------------

    def new_run(self) -> int:
        run = runs.create_run(
            self.conn,
            project_id=self.w.project_id,
            kind=RunKind.FULL,
            versions=self.w.versions,
            registry=self.w.registry,
            documents=self.w.documents,
            commit="t",
        ).id
        runs.transition(self.conn, run, [RunStatus.CREATED], RunStatus.RUNNING)
        self.runs.status[run] = RunStatus.RUNNING
        return run

    def config(self, run: int, kind: str) -> Any:
        method = "extract.math" if kind == "worker" else "agent.opus"
        return RunConfigs(
            self.w.registry, self.conn, runs.stored_options(self.conn, run).configs
        ).config(method, "default")

    def finished(self, config: int, hash_: str) -> Model | None:
        done = [
            t
            for t in self.tasks.values()
            if t.config == config and t.hash == hash_ and t.status in FINISHED
        ]
        return min(done, key=lambda t: t.id) if done else None

    def settle_model(
        self, config: int | None = None, hash_: str | None = None, run: int | None = None
    ) -> None:
        for t in self.tasks.values():
            if t.status != TaskStatus.AWAITING_AGENT:
                continue
            if (config, hash_) != (None, None) and (t.config, t.hash) != (config, hash_):
                continue
            if run is not None and t.run != run:
                continue
            twin = self.finished(t.config, t.hash)
            if twin is not None:
                t.status, t.reused_from, t.holder, t.expired = (
                    TaskStatus.REUSED,
                    twin.id,
                    None,
                    False,
                )

    def live_runs(self) -> list[int]:
        return sorted(r for r, s in self.runs.status.items() if s == RunStatus.RUNNING)

    # -- creation ------------------------------------------------------------------------------

    @rule(
        kind=st.sampled_from(["worker", "agent"]),
        keys=st.lists(st.sampled_from(KEYS), min_size=1, max_size=3, unique=True),
        fresh_run=st.booleans(),
    )
    def create(self, kind: str, keys: list[str], fresh_run: bool) -> None:
        run = self.new_run() if fresh_run or not self.live_runs() else self.live_runs()[-1]
        rc = self.config(run, kind)
        method = self.w.registry.method("extract.math" if kind == "worker" else "agent.opus")
        view = context.run_view(self.conn, run)
        # a unit per key; the segment id is arbitrary, the digest is the key
        units = [UnitView(UnitRef(TaskUnitType.SEGMENT, 1 + KEYS.index(k), k), view) for k in keys]
        stage = Stage.NORMALIZE if kind == "worker" else Stage.PROPOSE
        made = tasks.create_tasks(self.conn, run, stage, rc, method, units)
        for m in made:
            row = self.conn.execute(
                text("SELECT input_hash, status FROM ops.task WHERE id = :i"), {"i": m.id}
            ).one()
            twin = self.finished(int(rc.method_config_id), row.input_hash)
            initial = TaskStatus.PENDING if kind == "worker" else TaskStatus.AWAITING_AGENT
            expected = TaskStatus.REUSED if twin is not None else initial
            assert row.status == expected, (m, row, twin)
            self.tasks[m.id] = Model(
                m.id,
                run,
                kind,
                int(rc.method_config_id),
                row.input_hash,
                expected,
                reused_from=twin.id if twin else None,
            )

    # -- worker leases -------------------------------------------------------------------------

    @precondition(lambda self: any(t.kind == "worker" for t in self.tasks.values()))
    @rule(target=worker_leases, data=st.data())
    def claim(self, data: st.DataObject) -> Any:
        worker = [t for t in self.tasks.values() if t.kind == "worker"]
        pick = pick_from(data, sorted({(t.run, t.config) for t in worker}))
        holder = f"w{len(self.attempts)}"
        candidates = sorted(
            (
                t
                for t in worker
                if (t.run, t.config) == pick
                and (
                    t.status == TaskStatus.PENDING or (t.status == TaskStatus.RUNNING and t.expired)
                )
            ),
            key=lambda t: t.id,
        )
        with self.conn.begin_nested():
            got = queue.claim(self.conn, pick[0], Stage.NORMALIZE, pick[1], holder, 1)
        if not candidates:
            assert got == []
            return Lease(-1, 0, holder)  # a lease that holds nothing
        t = candidates[0]
        assert [c.id for c in got] == [t.id] and got[0].attempt == t.attempt + 1
        t.status, t.attempt, t.holder, t.expired = TaskStatus.RUNNING, t.attempt + 1, holder, False
        self.attempts[t.id] = t.attempt
        return Lease(t.id, t.attempt, holder)

    def holds(self, lease: Lease, status: TaskStatus) -> bool:
        t = self.tasks.get(lease.task)
        return t is not None and t.status == status and t.attempt == lease.attempt

    @rule(lease=worker_leases)
    def renew(self, lease: Lease) -> None:
        with self.conn.begin_nested():
            n = queue.renew(self.conn, {lease.task: lease.attempt}) if lease.task > 0 else 0
        assert n == (1 if self.holds(lease, TaskStatus.RUNNING) else 0)
        if n:
            self.tasks[lease.task].expired = False

    @rule(lease=consumes(worker_leases), empty=st.booleans())
    def complete(self, lease: Lease, empty: bool) -> None:
        """Completion; from a stale lease it is the late write, which commits nothing."""
        if lease.task < 0:
            return
        t = self.tasks[lease.task]
        result = UnitResult(ref=UnitRef(TaskUnitType.SEGMENT, 1), outcome=ObservationOutcome.EMPTY)
        held = self.holds(lease, TaskStatus.RUNNING)
        before = self.conn.execute(
            text("SELECT status, attempt, finished_at FROM ops.task WHERE id = :i"), {"i": t.id}
        ).one()
        try:
            with self.conn.begin_nested():
                status = queue.write_result(self.conn, t.id, lease.attempt, result)
        except queue.LeaseLost:
            assert not held
            after = self.conn.execute(
                text("SELECT status, attempt, finished_at FROM ops.task WHERE id = :i"), {"i": t.id}
            ).one()
            assert tuple(after) == tuple(before)  # a stale lease commits nothing
            return
        assert held and status == TaskStatus.EMPTY
        t.status, t.holder = TaskStatus.EMPTY, None

    @rule(lease=consumes(worker_leases), transient=st.booleans())
    def fail(self, lease: Lease, transient: bool) -> None:
        if lease.task < 0:
            return
        t = self.tasks[lease.task]
        held = self.holds(lease, TaskStatus.RUNNING)
        with self.conn.begin_nested():
            if transient:
                got = queue.retry_task(self.conn, t.id, lease.attempt, "40001")
            else:
                ok = queue.fail_task(self.conn, t.id, lease.attempt, "defect")
                got = TaskStatus.FAILED if ok else None
        if not held:
            assert got is None
            return
        expected = (
            TaskStatus.PENDING
            if transient and t.attempt < queue.MAX_ATTEMPTS
            else TaskStatus.FAILED
        )
        assert got == expected
        t.status, t.holder, t.expired = expected, None, False

    @precondition(lambda self: any(t.holder for t in self.tasks.values()))
    @rule(data=st.data())
    def expire(self, data: st.DataObject) -> None:
        held = sorted(t.id for t in self.tasks.values() if t.holder)
        t = self.tasks[pick_from(data, held)]
        self.conn.execute(
            text("UPDATE ops.task SET lease_until = now() - interval '1 second' WHERE id = :i"),
            {"i": t.id},
        )
        t.expired = True

    # -- agent leases --------------------------------------------------------------------------

    @precondition(lambda self: any(t.kind == "agent" for t in self.tasks.values()))
    @rule(target=agent_leases, data=st.data())
    def agent_lease(self, data: st.DataObject) -> Any:
        mine = [t for t in self.tasks.values() if t.kind == "agent"]
        run, config = pick_from(data, sorted({(t.run, t.config) for t in mine}))
        self.sessions += 1
        session = f"s{self.sessions}"
        self.settle_model(run=run)
        with self.conn.begin_nested():
            got = agent.lease_agent_tasks(
                self.conn, session_ref=session, method_configs=[config], run_id=run
            )
        candidates = sorted(
            (
                t
                for t in mine
                if t.run == run
                and t.config == config
                and t.status == TaskStatus.AWAITING_AGENT
                and not t.lease_active
                and not any(
                    y.id != t.id
                    and y.config == t.config
                    and y.hash == t.hash
                    and y.status == TaskStatus.AWAITING_AGENT
                    and y.lease_active
                    for y in self.tasks.values()
                )
            ),
            key=lambda t: t.id,
        )
        if not candidates:
            assert got == []
            return Lease(-1, 0, session)
        t = candidates[0]
        assert [g.id for g in got] == [t.id] and got[0].attempt == t.attempt + 1
        t.attempt, t.holder, t.expired = t.attempt + 1, f"agent:{session}", False
        self.attempts[t.id] = t.attempt
        return Lease(t.id, t.attempt, session)

    def agent_open(self, lease: Lease) -> bool:
        t = self.tasks.get(lease.task)
        return (
            t is not None
            and t.status == TaskStatus.AWAITING_AGENT
            and t.attempt == lease.attempt
            and t.holder == f"agent:{lease.holder}"
        )

    def expected_reason(self, lease: Lease) -> str:
        t = self.tasks[lease.task]
        if t.status == TaskStatus.REUSED:
            return "twin_settled"
        if t.status == TaskStatus.CANCELLED:
            return "cancelled"
        if t.status == TaskStatus.AWAITING_AGENT:
            return "leased_again"
        return "finished"

    @rule(lease=consumes(agent_leases))
    def agent_release(self, lease: Lease) -> None:
        if lease.task < 0:
            return
        with self.conn.begin_nested():
            ok = agent.release(self.conn, lease.task, lease.attempt)
        t = self.tasks[lease.task]
        open_ = t.status == TaskStatus.AWAITING_AGENT and t.attempt == lease.attempt
        assert ok == open_
        if ok:
            t.holder, t.expired = None, False

    @rule(
        lease=agent_leases,
        clean=st.booleans(),
        outcome=st.sampled_from([TaskStatus.DONE, TaskStatus.EMPTY, TaskStatus.FAILED]),
    )
    def agent_complete(self, lease: Lease, clean: bool, outcome: TaskStatus) -> None:
        """Hold (a first unclean submission) or complete; a lease no longer open is refused."""
        if lease.task < 0:
            return
        t = self.tasks[lease.task]
        open_ = self.agent_open(lease)
        try:
            with self.conn.begin_nested():
                got = agent.complete_agent_task(
                    self.conn, t.id, lease.attempt, lease.holder, clean=clean, outcome=outcome
                )
        except agent.TaskNotOpen as error:
            assert not open_ and error.reason == self.expected_reason(lease)
            return
        assert open_
        if not clean and not t.held:
            assert got == "held"
            t.held, t.expired = True, False
            return
        assert got == "completed"
        t.status, t.holder, t.expired = outcome, None, False
        if outcome in FINISHED:
            self.settle_model(t.config, t.hash)

    @rule()
    def settle(self) -> None:
        with self.conn.begin_nested():
            agent.settle_twins(self.conn)
        self.settle_model()
        open_with_twin = self.conn.execute(
            text(
                "SELECT count(*) FROM ops.task a WHERE a.status = 'awaiting_agent' AND EXISTS "
                "(SELECT 1 FROM ops.task f WHERE f.method_config_id = a.method_config_id AND "
                "f.input_hash = a.input_hash AND f.status IN ('done', 'empty'))"
            )
        ).scalar_one()
        assert open_with_twin == 0

    # -- the seal ------------------------------------------------------------------------------

    @precondition(lambda self: bool(self.live_runs()))
    @rule(data=st.data())
    def seal_run(self, data: st.DataObject) -> None:
        run = pick_from(data, self.live_runs())
        with self.conn.begin_nested():
            sealed = seal(
                self.conn,
                run,
                lambda c: self.w.runner._run_task(self.conn, run, Stage.FINALIZE, c),
                self.w.runner.graph,
            )
        self.runs.status[run] = RunStatus.CONSOLIDATING
        self.runs.cut[run] = sealed.cut_at
        self.runs.terminal_at_seal[run] = {
            t.id for t in self.tasks.values() if t.run == run and t.status in TERMINAL
        }

    # -- invariants ----------------------------------------------------------------------------

    @invariant()
    def matches_the_model(self) -> None:
        rows = self.conn.execute(
            text(
                "SELECT t.id, t.run_id, t.status, t.attempt, t.claimed_by, t.reused_task_id, "
                "t.finished_at, t.method_config_id, t.input_hash, f.status AS twin_status, "
                "f.method_config_id AS twin_config, f.input_hash AS twin_hash FROM ops.task t "
                "LEFT JOIN ops.task f ON f.id = t.reused_task_id WHERE t.unit_type <> 'run'"
            )
        ).all()
        assert {r.id for r in rows} == set(self.tasks)
        for r in rows:
            t = self.tasks[r.id]
            assert (r.status, r.attempt, r.reused_task_id) == (t.status, t.attempt, t.reused_from)
            if r.status in (TaskStatus.RUNNING, TaskStatus.AWAITING_AGENT):
                assert r.claimed_by == t.holder  # never held by two
            assert r.attempt >= self.attempts.get(r.id, 0)  # attempt never decreases
            if r.status == TaskStatus.REUSED:
                assert r.twin_status in FINISHED
                assert (r.twin_config, r.twin_hash) == (r.method_config_id, r.input_hash)
            assert (r.finished_at is not None) == (r.status in TERMINAL)
            cut = self.runs.cut.get(r.run_id)
            if (
                cut is not None
                and r.status in TERMINAL
                and r.id not in self.runs.terminal_at_seal[r.run_id]
            ):
                assert r.finished_at > cut  # a later step never stamps at or before the cut
            self.attempts[r.id] = r.attempt


@pytest.fixture
def world(committing_db: Engine, orch: SimpleNamespace, tmp_path: Path) -> SimpleNamespace:
    stubs = [
        orch.ingest_stub(),
        orch.Stub("extract.math", TaskUnitType.SEGMENT, MethodFamily.EXTRACT),
        orch.Stub("agent.opus", TaskUnitType.SEGMENT, MethodFamily.AGENT, MethodTier.AGENT),
        orch.Stub("consolidate.claims", TaskUnitType.RUN, MethodFamily.CONSOLIDATE),
        orch.Stub("validate.rules", TaskUnitType.RUN, MethodFamily.VALIDATE),
        orch.Stub("evaluate.score", TaskUnitType.RUN, MethodFamily.EVAL),
    ]
    with committing_db.begin() as conn:
        w = orch.setup_project(conn, tmp_path, methods=stubs)
    w.runner = Runner(
        committing_db,
        w.registry,
        Graph(()),
        phase0.stub_pass,
        None,
        MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
    )
    return w


def test_the_task_lifecycle(committing_db: Engine, world: SimpleNamespace) -> None:
    class Bound(Lifecycle):  # Hypothesis builds the machine from a class with no arguments
        def __init__(self) -> None:
            super().__init__(committing_db, world)

    run_state_machine_as_test(
        Bound,
        settings=settings(
            max_examples=60,
            stateful_step_count=50,
            deadline=None,
            suppress_health_check=[HealthCheck.too_slow],
        ),
    )
