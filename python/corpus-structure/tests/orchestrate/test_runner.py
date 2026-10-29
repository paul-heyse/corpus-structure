"""The stage runner, the seal, the passes, measure, evaluate and finish (P0-O-1, orchestration
§3.8), and fates as of the cut (§3.9)."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
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
from corpus_structure.orchestrate import agent, context, fates, runs, tasks
from corpus_structure.orchestrate.registry import RunConfigs
from corpus_structure.orchestrate.runner import Graph, PassReport, Runner, Step, seal
from corpus_structure.pool.load import CutMismatch, connect, load

PARSE_DETAIL = (
    "INSERT INTO meta.payload_schema (model_revision_id, class, kind, version, "
    "compatibility_class, json_schema_id, arrow_schema, reason, authorized_by) SELECT id, "
    "'test:parse_detail', 'parse_detail', 1, 'initial', 'test', '', 'test', 'test' FROM "
    "meta.model_revision LIMIT 1 ON CONFLICT DO NOTHING"
)


def documents(conn: Connection, view: Any, cfg: Any) -> Iterable[UnitRef]:
    keys = view.options["corpus"]["documents"]
    rows = conn.execute(
        text(
            "SELECT d.id, d.key FROM kb.document d JOIN ops.run r ON "
            "r.project_id = d.project_id WHERE r.id = :r AND d.key = ANY(:k) "
            "ORDER BY d.key"
        ),
        {"r": view.run_id, "k": list(keys)},
    )
    return [UnitRef(TaskUnitType.DOCUMENT, int(r.id), str(r.key)) for r in rows]


def world(
    engine: Engine,
    orch: SimpleNamespace,
    tmp_path: Path,
    fail_first: bool = False,
    run_pass: Any = None,
    evaluate: Any = None,
) -> SimpleNamespace:
    def ingest(unit: UnitView, cfg: Any, ctx: Any) -> UnitResult:
        key = str(unit.ref.unit_key)
        if fail_first and key == min(d for d, _ in w.documents):
            return UnitResult(ref=unit.ref, outcome=ObservationOutcome.FAILED, error="unreadable")
        return UnitResult(
            ref=unit.ref,
            outcome=ObservationOutcome.EMPTY,
            rendition=orch.page_content(key),
            parse_detail={"warnings": []},
        )

    stubs = [
        orch.ingest_stub(result=ingest),
        orch.Stub("agent.opus", TaskUnitType.SEGMENT, MethodFamily.AGENT, MethodTier.AGENT),
        orch.Stub("consolidate.claims", TaskUnitType.RUN, MethodFamily.CONSOLIDATE),
        orch.Stub("validate.rules", TaskUnitType.RUN, MethodFamily.VALIDATE),
        orch.Stub("evaluate.score", TaskUnitType.RUN, MethodFamily.EVAL),
    ]
    with engine.begin() as conn:
        w = orch.setup_project(conn, tmp_path, methods=stubs)
        conn.execute(text(PARSE_DETAIL))
    w.calls = []

    def default_pass(conn: Connection, run_id: int, pass_: str, m19: int | None) -> PassReport:
        w.calls.append((pass_, m19))
        return PassReport(rule_counts={"R1": 2} if pass_ == "finalize" else {})

    graph = Graph(((Stage.INGEST, (Step("ingest.html/default", units=documents),)),))
    w.runner = Runner(
        engine,
        w.registry,
        graph,
        run_pass or default_pass,
        evaluate,
        MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
    )
    w.url = engine.url.set(drivername="postgresql").render_as_string(hide_password=False)
    return w


def new_run(engine: Engine, w: SimpleNamespace, kind: RunKind = RunKind.FULL) -> int:
    with engine.begin() as conn:
        return runs.create_run(
            conn,
            project_id=w.project_id,
            kind=kind,
            versions=w.versions,
            registry=w.registry,
            documents=w.documents,
            commit="t",
        ).id


def run_row(engine: Engine, run_id: int) -> Any:
    with engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT status, cut_at, cut_m19_task_id, finished_at, notes FROM "
                "ops.run WHERE id = :r"
            ),
            {"r": run_id},
        ).one()


def run_tasks(engine: Engine, run_id: int) -> dict[str, list[str]]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT m.name, t.status FROM ops.task t JOIN ops.method_config c "
                "ON c.id = t.method_config_id JOIN ops.method m ON m.id = "
                "c.method_id WHERE t.run_id = :r ORDER BY t.id"
            ),
            {"r": run_id},
        )
        out: dict[str, list[str]] = {}
        for name, status in rows:
            out.setdefault(name, []).append(status)
        return out


def test_a_full_run_seals_before_the_final_pass_reads_and_finishes(
    committing_db: Engine, orch: SimpleNamespace, tmp_path: Path
) -> None:
    loaded = []
    holder: dict[str, Any] = {}

    def run_pass(conn: Connection, run_id: int, pass_: str, m19: int | None) -> PassReport:
        if pass_ == "finalize":  # the pool loader reads the committed seal on its own connection
            cut = conn.execute(
                text("SELECT cut_at FROM ops.run WHERE id = :r"), {"r": run_id}
            ).scalar_one()
            with connect(holder["url"]) as adbc:
                loaded.append(load(adbc, run_id, cut))
        return PassReport(rule_counts={"R1": 2, "R2": 0} if pass_ == "finalize" else {})

    w = world(committing_db, orch, tmp_path, run_pass=run_pass)
    holder["url"] = w.url
    run = new_run(committing_db, w)
    assert w.runner.run(run) == RunStatus.FINISHED
    row = run_row(committing_db, run)
    assert row.status == "finished" and row.cut_at is not None and row.finished_at >= row.cut_at
    assert len(loaded) == 1
    got = run_tasks(committing_db, run)
    assert set(got["ingest.html"]) == {"done"}
    assert got["consolidate.claims"] == ["done", "done"]  # assemble, finalize
    assert got["validate.rules"] == ["done"] and got["evaluate.score"] == ["empty"]
    with committing_db.connect() as conn:
        m19 = conn.execute(
            text(
                "SELECT t.id FROM ops.task t JOIN ops.method_config c ON c.id = "
                "t.method_config_id JOIN ops.method m ON m.id = c.method_id WHERE "
                "t.run_id = :r AND m.name = 'validate.rules'"
            ),
            {"r": run},
        ).scalar_one()
        assert row.cut_m19_task_id == m19
        started = conn.execute(
            text("SELECT started_at FROM ops.task WHERE id = :t"), {"t": m19}
        ).scalar_one()
        assert started > row.cut_at  # stamped when the final pass starts, after the seal
        rules = dict(
            conn.execute(
                text(
                    "SELECT scope_key, value FROM ops.measurement WHERE "
                    "task_id = :t AND metric = 'rules.evaluated'"
                ),
                {"t": m19},
            ).all()
        )
        assert rules == {"R1": 2.0, "R2": 0.0}
        rate = conn.execute(
            text(
                "SELECT value FROM ops.measurement WHERE run_id = :r AND task_id "
                "IS NULL AND metric = 'method.failed_rate' AND scope_key = "
                "'ingest.html'"
            ),
            {"r": run},
        ).scalar_one()
        assert rate == 0.0
        # the run-level tasks finished after the cut and stay outside the fate rule
        assert fates.unresolved(conn, run, stage=None) == 0


def test_loading_before_the_seal_commits_is_refused_and_after_succeeds(
    committing_db: Engine, orch: SimpleNamespace, tmp_path: Path
) -> None:
    w = world(committing_db, orch, tmp_path)
    run = new_run(committing_db, w)
    with committing_db.begin() as conn:
        runs.transition(conn, run, [RunStatus.CREATED], RunStatus.RUNNING)
    with committing_db.begin() as conn:
        sealed = seal(
            conn, run, lambda c: w.runner._run_task(conn, run, Stage.FINALIZE, c), w.runner.graph
        )
        with connect(w.url) as adbc, pytest.raises(CutMismatch):
            load(adbc, run, sealed.cut_at)  # the seal is not committed yet
    with connect(w.url) as adbc:
        assert load(adbc, run, sealed.cut_at) is not None


def test_a_failed_final_pass_fails_the_run_and_keeps_the_cut(
    committing_db: Engine, orch: SimpleNamespace, tmp_path: Path
) -> None:
    def run_pass(conn: Connection, run_id: int, pass_: str, m19: int | None) -> PassReport:
        if pass_ == "finalize":
            conn.execute(
                text(
                    "INSERT INTO ops.measurement (run_id, iteration, scope_type, metric, "
                    "value) VALUES (:r, 0, 'run', 'rolled.back', 1)"
                ),
                {"r": run_id},
            )
            raise RuntimeError("invariant violated")
        return PassReport()

    w = world(committing_db, orch, tmp_path, run_pass=run_pass)
    run = new_run(committing_db, w)
    assert w.runner.run(run) == RunStatus.FAILED
    row = run_row(committing_db, run)
    assert row.status == "failed" and row.cut_at is not None and "invariant" in row.notes
    got = run_tasks(committing_db, run)
    assert got["consolidate.claims"] == ["done", "failed"] and got["validate.rules"] == ["failed"]
    with committing_db.connect() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM ops.measurement WHERE metric = 'rolled.back'")
            ).scalar_one()
            == 0
        )


def test_a_failed_ingest_fails_the_run_before_any_pass(
    committing_db: Engine, orch: SimpleNamespace, tmp_path: Path
) -> None:
    w = world(committing_db, orch, tmp_path, fail_first=True)
    run = new_run(committing_db, w)
    assert w.runner.run(run) == RunStatus.FAILED
    row = run_row(committing_db, run)
    assert row.status == "failed" and row.cut_at is None and w.calls == []
    assert "failed" in run_tasks(committing_db, run)["ingest.html"]


def test_a_failed_evaluate_writes_its_task_failed_and_the_run_finishes(
    committing_db: Engine, orch: SimpleNamespace, tmp_path: Path
) -> None:
    def evaluate(conn: Connection, run_id: int, task_id: int) -> TaskStatus:
        raise RuntimeError("no goldens")

    w = world(committing_db, orch, tmp_path, evaluate=evaluate)
    run = new_run(committing_db, w)
    assert w.runner.run(run) == RunStatus.FINISHED
    assert run_tasks(committing_db, run)["evaluate.score"] == ["failed"]


def test_an_ingest_run_finishes_without_passes(
    committing_db: Engine, orch: SimpleNamespace, tmp_path: Path
) -> None:
    w = world(committing_db, orch, tmp_path)
    run = new_run(committing_db, w, RunKind.INGEST)
    assert w.runner.run(run) == RunStatus.FINISHED
    row = run_row(committing_db, run)
    assert row.status == "finished" and row.cut_at is not None and w.calls == []
    with committing_db.connect() as conn:
        assert conn.execute(
            text("SELECT count(*) FROM kb.run_rendition WHERE run_id = :r"), {"r": run}
        ).scalar_one() == len(w.documents)


def agent_run(engine: Engine, w: SimpleNamespace, keys: list[str]) -> SimpleNamespace:
    run = new_run(engine, w)
    with engine.begin() as conn:
        runs.transition(conn, run, [RunStatus.CREATED], RunStatus.RUNNING)
        view = context.run_view(conn, run)
        rc = RunConfigs(w.registry, conn, runs.stored_options(conn, run).configs).config(
            "agent.opus", "default"
        )
        units = [
            UnitView(UnitRef(TaskUnitType.SEGMENT, i + 1, k), view) for i, k in enumerate(keys)
        ]
        tasks.create_tasks(conn, run, Stage.PROPOSE, rc, w.registry.method("agent.opus"), units)
    return SimpleNamespace(id=run, config=rc.method_config_id)


def test_a_completion_after_the_cut_is_unresolved_and_the_seal_waits_for_open_completions(
    committing_db: Engine, orch: SimpleNamespace, tmp_path: Path
) -> None:
    import sqlalchemy.exc

    w = world(committing_db, orch, tmp_path)
    r = agent_run(committing_db, w, ["u1", "u2", "u3"])

    def lease(conn: Connection) -> agent.AgentLease:
        (got,) = agent.lease_agent_tasks(
            conn, session_ref="s", method_configs=[r.config], run_id=r.id
        )
        return got

    with committing_db.begin() as conn:
        before, open_, after = lease(conn), lease(conn), lease(conn)
        agent.complete_agent_task(
            conn, before.id, before.attempt, "s", clean=True, outcome=TaskStatus.DONE
        )
    with committing_db.connect() as completer, committing_db.connect() as sealer:
        completing = completer.begin()
        agent.complete_agent_task(
            completer, open_.id, open_.attempt, "s", clean=True, outcome=TaskStatus.DONE
        )  # holds the run row FOR SHARE
        sealing = sealer.begin()
        sealer.execute(text("SET LOCAL lock_timeout = '300ms'"))
        with pytest.raises(sqlalchemy.exc.OperationalError):  # the seal waits for the completion
            seal(
                sealer,
                r.id,
                lambda c: w.runner._run_task(sealer, r.id, Stage.FINALIZE, c),
                w.runner.graph,
            )
        sealing.rollback()
        completing.commit()
    with committing_db.begin() as conn:
        seal(
            conn, r.id, lambda c: w.runner._run_task(conn, r.id, Stage.FINALIZE, c), w.runner.graph
        )
    with committing_db.begin() as conn:
        agent.complete_agent_task(
            conn, after.id, after.attempt, "s", clean=True, outcome=TaskStatus.DONE
        )
    with committing_db.connect() as conn:
        got = {f.unit_key: f.fate for f in fates.fates(conn, r.id)}
        assert got == {
            before.unit_key: "done",
            open_.unit_key: "done",
            after.unit_key: fates.UNRESOLVED,
        }
        assert fates.unresolved(conn, r.id) == 1
        status = conn.execute(
            text("SELECT status FROM ops.task WHERE id = :i"), {"i": after.id}
        ).scalar_one()
        assert status == "done"  # its status moved on; its fate for this run did not


@pytest.mark.parametrize("blocked", ["finalize", "evaluate"])
def test_a_completion_during_the_final_pass_or_evaluate_commits_without_waiting(
    committing_db: Engine, orch: SimpleNamespace, tmp_path: Path, blocked: str
) -> None:
    """While a stub final pass or `evaluate.score` is blocked mid-transaction, an agent completion
    on another connection commits under a 2 s lock timeout, and reads as unresolved for the run."""
    import threading

    entered, release = threading.Event(), threading.Event()

    def block() -> None:
        entered.set()
        assert release.wait(30)

    def run_pass(conn: Connection, run_id: int, pass_: str, m19: int | None) -> PassReport:
        if pass_ == blocked:
            block()
        return PassReport()

    def evaluate(conn: Connection, run_id: int, task_id: int) -> TaskStatus:
        if blocked == "evaluate":
            block()
        return TaskStatus.EMPTY

    w = world(committing_db, orch, tmp_path, run_pass=run_pass, evaluate=evaluate)
    one_unit = lambda conn, view, cfg: [UnitRef(TaskUnitType.SEGMENT, 1, "u1")]  # noqa: E731
    w.runner.graph = Graph((
        *w.runner.graph.stages,
        (Stage.PROPOSE, (Step("agent.opus/default", units=one_unit),)),
    ))  # fmt: skip
    run = new_run(committing_db, w)
    outcome: list[RunStatus] = []
    worker = threading.Thread(target=lambda: outcome.append(w.runner.run(run)))
    worker.start()
    try:
        assert entered.wait(60), "the runner never reached the blocked step"
        with committing_db.connect() as other:
            with other.begin():
                other.execute(text("SET LOCAL lock_timeout = '2s'"))
                config = other.execute(text(
                    "SELECT DISTINCT method_config_id FROM ops.task WHERE run_id = :r AND "
                    "stage = 'propose'"), {"r": run}).scalar_one()  # fmt: skip
                (lease,) = agent.lease_agent_tasks(other, session_ref="s", method_configs=[config],
                                                   run_id=run)  # fmt: skip
                agent.complete_agent_task(other, lease.id, lease.attempt, "s", clean=True,
                                          outcome=TaskStatus.DONE)  # fmt: skip
            # committed while the runner's transaction is still open
            assert worker.is_alive() and not release.is_set()
    finally:
        release.set()
        worker.join(60)
    assert outcome == [RunStatus.FINISHED]
    with committing_db.connect() as conn:
        (fate,) = fates.fates(conn, run)
        assert (fate.task_id, fate.fate) == (lease.id, fates.UNRESOLVED)
        assert conn.execute(text("SELECT status FROM ops.task WHERE id = :i"),
                            {"i": lease.id}).scalar_one() == "done"  # fmt: skip
