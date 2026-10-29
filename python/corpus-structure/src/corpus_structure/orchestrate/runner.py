"""The stage runner (orchestration §3.8; D6 §2, §6; D3 §5, §8; R08, RC10, DA-015, DA-024).

A **graph** is an ordered tuple of base stages, each a tuple of steps; a step names a configuration
(`<method>/<name>`), its upstream methods and, optionally, a unit source (default: the method's
`select`). For each step the runner creates its tasks (reuse at creation, §3.5), settles agent
twins, and runs the worker loop inline until none of the step's tasks is `pending` or `running`
(`workers=0`; open agent tasks are the agent barrier's business, P0-O-2). A `failed` task in
`ingest` fails the run; later stages skip downstream units (`prerequisite_failed`).

**Passes.** At `assemble` the runner creates the pass task (unit `run`, `running`, claimed by
`orchestrator:<pid>`, attempt 1), commits, then calls `run_pass(conn, run, 'assemble', None)` and
writes the task's fenced terminal status in one transaction.

**The seal** opens finalize, one short transaction: lock the run row `FOR NO KEY UPDATE` (it
conflicts with completions' `FOR SHARE`, not with foreign-key inserts' `FOR KEY SHARE`); create the
finalize pass, the M19 and the `evaluate.score` tasks; stamp `cut_at = clock_timestamp()`, record
the M19 task as `cut_m19_task_id` and set `consolidating`, conditional on `running`; commit. It is
the only writer of the cut and the final M19 task, and it commits before the final pass reads the
pool, which reads only committed data as of that cut.

**The final pass** is its own transaction: stamp the pass and M19 tasks' `started_at`; call
`run_pass(conn, run, 'finalize', m19_task)`; write the M19 per-rule counts as `rules.evaluated`
measurements of the M19 task (scope `rule`); write both tasks' fenced terminal status; commit. A
failure rolls back and a second transaction writes the pass tasks `failed` and the run `failed`; the
cut stays. Then, each in its own transaction: **measure** (the phase 0 run metrics, no `task_id`;
a failure fails the run), **evaluate** (the `evaluate.score` task; a failure writes the task
`failed` and the run still finishes) and **finish** (`finished`, `finished_at` last).
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from sqlalchemy import Connection, Engine, text

from corpus_structure.core.method import MethodContext, MethodSettings, UnitRef, UnitView
from corpus_structure.core.vocab import (
    MethodTier,
    RunKind,
    RunStatus,
    Stage,
    TaskStatus,
    TaskUnitType,
)
from corpus_structure.orchestrate import agent, context, queue, runs, tasks
from corpus_structure.orchestrate.registry import RunConfigs


class PassOutcome(Protocol):
    """What the runner reads of a pass's report, structurally: consolidation returns its own
    report type (it does not import `orchestrate`)."""

    @property
    def counts(self) -> Mapping[str, int]: ...

    @property
    def rule_counts(self) -> Mapping[str, int]: ...

    @property
    def consumed(self) -> tuple[int, ...]: ...


@dataclass(frozen=True)
class PassReport:
    """A minimal `PassOutcome` (stubs and tests): counts by code, M19's per-rule evaluated counts
    and the propose tasks it consumed (D5 §1, §11)."""

    counts: Mapping[str, int] = field(default_factory=dict)
    rule_counts: Mapping[str, int] = field(default_factory=dict)
    consumed: tuple[int, ...] = ()


# (conn, run, pass name, the final M19 task at finalize) -> the pass's report
PassRunner = Callable[[Connection, int, str, int | None], PassOutcome]
# (conn, run, the evaluate.score task) -> its terminal status
Evaluate = Callable[[Connection, int, int], TaskStatus]
UnitSource = Callable[[Connection, Any, Any], Iterable[UnitRef]]


@dataclass(frozen=True)
class Step:
    config: str  # "<method>/<name>"
    upstream: tuple[str, ...] = ()
    units: UnitSource | None = None


@dataclass(frozen=True)
class Graph:
    """The base stages and the run-level configurations of the passes (phase 0, §3.8)."""

    stages: tuple[tuple[Stage, tuple[Step, ...]], ...]
    pass_config: str = "consolidate.claims/default"
    m19_config: str = "validate.rules/default"
    evaluate_config: str = "evaluate.score/default"
    policy_propose: bool = False

    def for_kind(self, kind: RunKind) -> Graph:
        if kind == RunKind.INGEST:
            return Graph(tuple((s, steps) for s, steps in self.stages if s == Stage.INGEST))
        return self


class RunFailed(RuntimeError):
    pass


def unit_view(conn: Connection, view: Any, ref: UnitRef) -> UnitView:
    """A unit with its document and rendition, where they apply."""
    document = rendition = None
    if ref.unit_type == TaskUnitType.DOCUMENT:
        document = ref.unit_id
    elif ref.unit_type == TaskUnitType.RENDITION and ref.unit_id is not None:
        rendition = ref.unit_id
        document = conn.execute(
            text("SELECT document_id FROM kb.rendition WHERE id = :r"), {"r": rendition}
        ).scalar()
    elif ref.unit_type == TaskUnitType.SEGMENT and ref.unit_id is not None:
        row = conn.execute(
            text(
                "SELECT s.rendition_id, r.document_id FROM kb.segment s JOIN "
                "kb.rendition r ON r.id = s.rendition_id WHERE s.id = :s"
            ),
            {"s": ref.unit_id},
        ).first()
        if row is not None:
            rendition, document = row
    return UnitView(ref, view, document_id=document, rendition_id=rendition)


@dataclass
class Runner:
    """Runs one run through its graph (module doc)."""

    engine: Engine
    registry: Any  # MethodRegistry
    graph: Graph
    run_pass: PassRunner
    evaluate: Evaluate | None = None
    settings: MethodSettings | None = None
    holder: str = field(default_factory=lambda: f"orchestrator:{os.getpid()}")
    batch: int = 8
    log: list[str] = field(default_factory=list)

    # -- the run --------------------------------------------------------------------------

    def run(self, run_id: int) -> RunStatus:
        with self.engine.begin() as conn:
            kind = RunKind(
                conn.execute(
                    text("SELECT kind FROM ops.run WHERE id = :r"), {"r": run_id}
                ).scalar_one()
            )
            runs.transition(conn, run_id, [RunStatus.CREATED], RunStatus.RUNNING)
        graph = self.graph.for_kind(kind)
        try:
            for stage, steps in graph.stages:
                for step in steps:
                    self.step(run_id, stage, step)
            if graph.policy_propose:
                from corpus_structure.orchestrate.routing import propose

                with self.engine.begin() as conn:
                    propose(conn, run_id, self.registry)
        except (RunFailed, ValueError) as error:
            with self.engine.begin() as conn:
                runs.fail_run(conn, run_id, str(error))
            return RunStatus.FAILED
        if kind == RunKind.INGEST:
            with self.engine.begin() as conn:
                runs.finish_run(conn, run_id)
            return RunStatus.FINISHED
        self.assemble(run_id)
        sealed = self.seal(run_id)
        if not self.final_pass(run_id, sealed):
            return RunStatus.FAILED
        try:
            with self.engine.begin() as conn:
                measure(conn, run_id)
        except Exception as error:
            with self.engine.begin() as conn:
                runs.fail_run(conn, run_id, f"measure: {error}")
            return RunStatus.FAILED
        self.evaluate_stage(run_id, sealed.evaluate_task)
        with self.engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE ops.run SET status = 'finished', finished_at = "
                    "clock_timestamp() WHERE id = :r AND status = 'consolidating'"
                ),
                {"r": run_id},
            )
        return RunStatus.FINISHED

    # -- base steps -----------------------------------------------------------------------

    def _configs(self, conn: Connection, run_id: int) -> RunConfigs:
        return RunConfigs(self.registry, conn, runs.stored_options(conn, run_id).configs)

    def step(self, run_id: int, stage: Stage, step: Step) -> None:
        method_name, name = step.config.split("/", 1)
        method = self.registry.method(method_name)
        with self.engine.begin() as conn:
            view = context.run_view(conn, run_id)
            rc = self._configs(conn, run_id).config(method_name, name)
            source = step.units or (lambda c, v, cfg: method.select(v, cfg))
            refs = list(source(conn, view, rc.config))
            units = [unit_view(conn, view, r) for r in refs]
            fresh = method_name in runs.stored_options(conn, run_id).fresh
            tasks.create_tasks(
                conn, run_id, stage, rc, method, units, upstream=step.upstream, fresh=fresh
            )
        if method.tier == MethodTier.AGENT:
            with self.engine.begin() as conn:
                agent.settle_twins(conn, run_id=run_id, method_configs=[rc.method_config_id or 0])
            return
        self.work(run_id, stage, rc, method)
        if stage == Stage.INGEST:
            with self.engine.connect() as conn:
                failed = conn.execute(
                    text(
                        "SELECT count(*) FROM ops.task WHERE run_id = :r AND method_config_id = :c "
                        "AND status = 'failed'"
                    ),
                    {"r": run_id, "c": rc.method_config_id},
                ).scalar_one()
            if failed:
                raise RunFailed(f"ingest: {failed} {method_name} task(s) failed")

    def work(self, run_id: int, stage: Stage, rc: Any, method: Any) -> None:
        """The inline worker loop: claim, run with no transaction open, settle each task."""
        language = _profile_language(rc.params)
        while True:
            with self.engine.begin() as conn:
                claimed = queue.claim(
                    conn, run_id, stage, rc.method_config_id, self.holder, self.batch
                )
            if not claimed:
                return
            with self.engine.connect() as conn:
                view = context.run_view(conn, run_id)
                units = [
                    unit_view(conn, view, UnitRef(TaskUnitType(c.unit_type), c.unit_id, c.unit_key))
                    for c in claimed
                ]
                ctx = MethodContext(view, view.reader, self._settings(), _logger(method.name))
                try:
                    results: Sequence[Any] = method.run(units, rc.config, ctx)
                except Exception as error:
                    results = [error] * len(claimed)
                conn.rollback()
            for c, result in zip(claimed, results, strict=True):
                queue.settle(self.engine, c, result, language)

    def _settings(self) -> MethodSettings:
        if self.settings is not None:
            return self.settings
        from corpus_structure.settings import Settings

        paths = Settings().paths
        return MethodSettings(data_dir=paths.data_dir, model_cache=paths.model_cache)

    # -- passes and the seal --------------------------------------------------------------

    def _run_task(
        self, conn: Connection, run_id: int, stage: Stage, config: str, started: bool = False
    ) -> int:
        """A run-level task, `running` and held by the orchestrator at attempt 1; `started` stamps
        `started_at` now (the seal's tasks are stamped when their stage starts)."""
        method_name, name = config.split("/", 1)
        rc = self._configs(conn, run_id).config(method_name, name)
        return int(
            conn.execute(
                text(
                    "INSERT INTO ops.task (run_id, stage, unit_type, unit_key, method_config_id, "
                    "input_hash, status, claimed_by, attempt, started_at) VALUES (:r, :s, 'run', "
                    "'run', "
                    ":c, :h, 'running', :holder, 1, CASE WHEN :started THEN clock_timestamp() END) "
                    "RETURNING id"
                ),
                {
                    "r": run_id,
                    "s": stage.value,
                    "c": rc.method_config_id,
                    "h": f"run:{run_id}:{stage.value}:{config}",
                    "holder": self.holder,
                    "started": started,
                },
            ).scalar_one()
        )

    def _start(self, conn: Connection, *task_ids: int) -> None:
        done = conn.execute(
            text(
                "UPDATE ops.task SET started_at = clock_timestamp() WHERE id = ANY(:i) AND "
                "attempt = 1 "
                "AND status = 'running'"
            ),
            {"i": list(task_ids)},
        )
        if done.rowcount != len(task_ids):
            raise queue.LeaseLost(f"run-level tasks {task_ids} are no longer running")

    def _finish_task(
        self, conn: Connection, task_id: int, status: TaskStatus, error: str | None = None
    ) -> None:
        done = conn.execute(
            text(
                "UPDATE ops.task SET status = :s, error = CAST(:e AS jsonb), finished_at = "
                "clock_timestamp() WHERE id = :i AND attempt = 1 AND status = 'running'"
            ),
            {
                "s": status.value,
                "e": None if error is None else queue._json({"message": error}),
                "i": task_id,
            },
        )
        if done.rowcount != 1:
            raise queue.LeaseLost(f"run-level task {task_id} is no longer running")

    def assemble(self, run_id: int) -> None:
        with self.engine.begin() as conn:
            task = self._run_task(conn, run_id, Stage.ASSEMBLE, self.graph.pass_config, True)
        with self.engine.begin() as conn:
            self.run_pass(conn, run_id, "assemble", None)
            self._finish_task(conn, task, TaskStatus.DONE)

    def seal(self, run_id: int) -> Sealed:
        """The seal (module doc), committed before the final pass reads."""
        with self.engine.begin() as conn:
            return seal(
                conn,
                run_id,
                lambda config: self._run_task(conn, run_id, Stage.FINALIZE, config),
                self.graph,
            )

    def final_pass(self, run_id: int, sealed: Sealed) -> bool:
        try:
            with self.engine.begin() as conn:
                self._start(conn, sealed.pass_task, sealed.m19_task)
                report = self.run_pass(conn, run_id, "finalize", sealed.m19_task)
                for rule, n in sorted(report.rule_counts.items()):
                    conn.execute(
                        text(
                            "INSERT INTO ops.measurement (run_id, task_id, iteration, scope_type, "
                            "scope_key, metric, value) VALUES (:r, :t, 0, 'rule', :k, "
                            "'rules.evaluated', :v)"
                        ),
                        {"r": run_id, "t": sealed.m19_task, "k": rule, "v": n},
                    )
                self._finish_task(conn, sealed.pass_task, TaskStatus.DONE)
                self._finish_task(conn, sealed.m19_task, TaskStatus.DONE)
        except Exception as error:
            with self.engine.begin() as conn:
                for task in (sealed.pass_task, sealed.m19_task):
                    self._finish_task(
                        conn, task, TaskStatus.FAILED, f"{type(error).__name__}: {error}"
                    )
                runs.fail_run(conn, run_id, f"finalize pass: {error}")
            return False
        return True

    def evaluate_stage(self, run_id: int, task: int) -> None:
        try:
            with self.engine.begin() as conn:
                self._start(conn, task)
                status = (
                    self.evaluate(conn, run_id, task)
                    if self.evaluate is not None
                    else TaskStatus.EMPTY
                )
                self._finish_task(conn, task, status)
        except Exception as error:
            with self.engine.begin() as conn:
                self._finish_task(conn, task, TaskStatus.FAILED, f"{type(error).__name__}: {error}")


@dataclass(frozen=True)
class Sealed:
    cut_at: Any
    pass_task: int
    m19_task: int
    evaluate_task: int


def seal(conn: Connection, run_id: int, make_task: Callable[[str], int], graph: Graph) -> Sealed:
    """The seal's statements, in the caller's (short) transaction (module doc)."""
    conn.execute(text("SELECT 1 FROM ops.run WHERE id = :r FOR NO KEY UPDATE"), {"r": run_id})
    pass_task = make_task(graph.pass_config)
    m19 = make_task(graph.m19_config)
    evaluate = make_task(graph.evaluate_config)
    row = conn.execute(
        text(
            "UPDATE ops.run SET cut_at = clock_timestamp(), cut_m19_task_id = :m, status = "
            "'consolidating' WHERE id = :r AND status = 'running' AND cut_at IS NULL RETURNING "
            "cut_at"
        ),
        {"r": run_id, "m": m19},
    ).first()
    if row is None:
        raise runs.IllegalTransition(f"run {run_id} is not running or is already sealed")
    return Sealed(row.cut_at, pass_task, m19, evaluate)


# --- Measure ---------------------------------------------------------------------------------


def _profile_language(params: Mapping[str, Any]) -> str:
    """A configuration's source-profile language: a resolved profile is a mapping with `root`
    and `language`."""
    for value in params.values():
        if isinstance(value, Mapping) and "root" in value and "language" in value:
            return str(value["language"] or "english")
    return "english"


def _logger(name: str) -> Any:
    import logging

    return logging.getLogger(f"corpus_structure.method.{name}")


_METRICS = """
INSERT INTO ops.measurement (run_id, iteration, scope_type, scope_id, scope_key, metric, value,
                             detail)
SELECT :run, 0, m.scope_type, m.scope_id, m.scope_key, m.metric, m.value, '{}' FROM (
  SELECT 'run' AS scope_type, NULL::bigint AS scope_id, NULL::text AS scope_key,
         'unit.claims' AS metric,
         (SELECT count(*) FROM kb.claim WHERE run_id = :run)::float8
         / greatest(1, (SELECT count(DISTINCT unit_key) FROM ops.task
                        WHERE run_id = :run AND stage = 'propose')) AS value
  UNION ALL
  SELECT 'predicate', NULL, predicate, 'run.status.' || status, count(*)::float8
  FROM kb.claim WHERE run_id = :run GROUP BY predicate, status
  UNION ALL
  SELECT 'run', NULL, NULL, 'run.conflicts', count(*)::float8
  FROM kb.claim_link WHERE run_id = :run AND link_type = 'contradicts'
  UNION ALL
  SELECT 'method', NULL, m.name, x.metric, x.value
  FROM ops.method_config c JOIN ops.method m ON m.id = c.method_id
  CROSS JOIN LATERAL (
    SELECT count(*) FILTER (WHERE t.status IN ('done', 'empty', 'failed')) AS ran,
           count(*) FILTER (WHERE t.status = 'empty') AS empty,
           count(*) FILTER (WHERE t.status = 'failed') AS failed
    FROM ops.task t WHERE t.run_id = :run AND t.method_config_id = c.id AND t.unit_type <> 'run'
  ) n
  CROSS JOIN LATERAL (VALUES ('method.empty_rate', n.empty::float8 / n.ran),
                             ('method.failed_rate', n.failed::float8 / n.ran)) AS x(metric, value)
  WHERE n.ran > 0
  UNION ALL
  SELECT 'run', NULL, NULL, 'math.parse_rate',
         avg(CASE WHEN o.payload ? 'parse_error' THEN 0.0 ELSE 1.0 END)::float8
  FROM kb.run_observation o WHERE o.run_id = :run AND o.kind = 'value'
  HAVING count(*) > 0
  UNION ALL
  SELECT 'rendition', o.rendition_id, NULL, 'math.parse_rate',
         avg(CASE WHEN o.payload ? 'parse_error' THEN 0.0 ELSE 1.0 END)::float8
  FROM kb.run_observation o WHERE o.run_id = :run AND o.kind = 'value'
  GROUP BY o.rendition_id
  UNION ALL
  SELECT 'run', NULL, NULL, 'cost.agent_packets', count(*)::float8
  FROM ops.task t JOIN ops.method_config c ON c.id = t.method_config_id
  WHERE t.run_id = :run AND c.tier = 'agent' AND t.unit_type <> 'run'
    AND t.status NOT IN ('reused', 'skipped')
) m
"""


def measure(conn: Connection, run_id: int) -> int:
    """The phase 0 run metrics (D6 §6, §3.8's subset); the rows written."""
    return int(conn.execute(text(_METRICS), {"run": run_id}).rowcount)
