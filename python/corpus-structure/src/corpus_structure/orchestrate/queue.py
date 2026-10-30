"""Claiming, leases and fencing for workers (orchestration §3.6; D6 §3.2; D3 §8; store note §3, §4).

**The claim** is one `UPDATE … FROM (SELECT … FOR UPDATE SKIP LOCKED LIMIT n)` over `pending` or
lease-expired `running` tasks of one (run, stage, method configuration): it sets `running`,
increments `attempt`, names the holder and sets a 5-minute lease. The caller commits it at once,
and the method runs with no transaction open.

**The terminal write** is one transaction per task (`write_result`):
1. the fence: the task row locked at `(id, attempt, status = 'running')`; none raises `LeaseLost`
   and nothing is written;
2. the task's rows: for `ingest.html` its rendition and build (`store_rendition`), the drafts'
   spans (`upsert_spans`), observations (`write_observations`, binary COPY with their registered
   `payload_schema_id`) and measurements with `task_id`. A draft that names its segment by key in
   its value (`value.segment`, as the author-markup drafts do, which cannot know the ids before
   the rendition is stored) gets that segment's id on the stored rendition;
3. the outcome, `cost`, `error` and `finished_at = clock_timestamp()`, fenced again. An ingest
   result carries its rendition beside no observations (`empty` by D4 §1 rule 2); its task is
   written `done`, the status `kb.run_rendition` admits (D3 §8).

**Renewal and retry.** `renew` extends held leases, fenced on `attempt` (a worker's heartbeat calls
it about every minute on its second connection). A transient failure (`classify_error`: 40001,
40P01, a lost connection) takes the conditional retry write: `pending` while `attempt < 3`, else
`failed`. A `failed` unit result or any other exception is written `failed` at once. A unique
violation on `(task_id, ordinal)` is a fencing defect and is raised.
"""

from __future__ import annotations

import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy import Connection, Engine, text

from corpus_structure.core.db import repo
from corpus_structure.core.db.legacy_metadata import metadata
from corpus_structure.core.db.store import ErrorClass, classify_error
from corpus_structure.core.method import UnitResult
from corpus_structure.core.vocab import ObservationOutcome, Stage, TaskStatus

T = metadata.tables
WORKER_LEASE = timedelta(minutes=5)
MAX_ATTEMPTS = 3


# a unit result's outcome as the task's terminal status
OUTCOME_STATUS = {
    ObservationOutcome.PRODUCED: TaskStatus.DONE,
    ObservationOutcome.EMPTY: TaskStatus.EMPTY,
    ObservationOutcome.FAILED: TaskStatus.FAILED,
}


class LeaseLost(RuntimeError):
    """The task's attempt or status moved on: this worker's write commits nothing."""


@dataclass(frozen=True)
class Claimed:
    id: int
    attempt: int
    unit_type: str
    unit_id: int | None
    unit_key: str | None


# The candidates are a MATERIALIZED CTE, evaluated once: a LIMIT ... SKIP LOCKED subquery joined
# in UPDATE ... FROM can be rescanned under a nested-loop plan and claim more than `n` rows.
_CLAIM = text("""
WITH c AS MATERIALIZED (
  SELECT id FROM ops.task
  WHERE run_id = :run AND stage = :stage AND method_config_id = :config
    AND (status = 'pending' OR (status = 'running' AND lease_until < now()))
  ORDER BY priority DESC, id
  LIMIT :n FOR UPDATE SKIP LOCKED
)
UPDATE ops.task t
SET status = 'running', attempt = t.attempt + 1, claimed_by = :holder,
    lease_until = now() + CAST(:lease AS interval), started_at = coalesce(t.started_at,
    clock_timestamp())
FROM c
WHERE t.id = c.id
RETURNING t.id, t.attempt, t.unit_type, t.unit_id, t.unit_key
""")


def claim(
    conn: Connection,
    run_id: int,
    stage: Stage,
    method_config_id: int,
    holder: str,
    n: int = 1,
    lease: timedelta = WORKER_LEASE,
) -> list[Claimed]:
    """Claim up to `n` tasks (module doc); the caller commits at once."""
    rows = conn.execute(
        _CLAIM,
        {
            "run": run_id,
            "stage": stage.value,
            "config": method_config_id,
            "holder": holder,
            "n": n,
            "lease": f"{lease.total_seconds()} s",
        },
    )
    return sorted(
        (Claimed(int(r.id), int(r.attempt), r.unit_type, r.unit_id, r.unit_key) for r in rows),
        key=lambda c: c.id,
    )


def renew(conn: Connection, held: Mapping[int, int], lease: timedelta = WORKER_LEASE) -> int:
    """Extend the leases of `held` (task id → attempt) still held; the number renewed."""
    if not held:
        return 0
    done = conn.execute(
        text(
            "UPDATE ops.task t SET lease_until = now() + CAST(:lease AS interval) FROM unnest("
            "CAST(:ids AS bigint[]), CAST(:attempts AS integer[])) AS h(id, attempt) WHERE t.id = "
            "h.id AND t.attempt = h.attempt AND t.status = 'running'"
        ),
        {"ids": list(held), "attempts": list(held.values()), "lease": f"{lease.total_seconds()} s"},
    )
    return done.rowcount


def _fence(conn: Connection, task_id: int, attempt: int) -> Any:
    row = conn.execute(
        text(
            "SELECT t.id, t.run_id, t.unit_id, t.unit_type, t.method_config_id FROM ops.task t "
            "WHERE t.id = :i AND t.attempt = :a AND t.status = 'running' FOR UPDATE"
        ),
        {"i": task_id, "a": attempt},
    ).first()
    if row is None:
        raise LeaseLost(f"task {task_id} is no longer running at attempt {attempt}")
    return row


def _payload_schema(conn: Connection, kind: str) -> int:
    ids = repo.registered_ids(conn, [kind])
    if kind not in ids:
        raise repo.UnregisteredPayload(f"no registered payload schema for {kind!r}")
    return ids[kind]


def _segment_named(payload: Any) -> str | None:
    """The segment key an ingest draft names in its value (`value.segment`; author markup)."""
    value = getattr(payload, "value", None)
    named = value.get("segment") if isinstance(value, dict) else None
    return named if isinstance(named, str) else None


def _rows(conn: Connection, task: Any, result: UnitResult, ts_config: str) -> None:
    rendition_id = None
    if result.rendition is not None:  # ingest.html: the rendition and its build
        doc = conn.execute(
            text("SELECT key FROM kb.document WHERE id = :d"), {"d": task.unit_id}
        ).scalar_one()
        stored = repo.store_rendition(
            conn,
            int(task.unit_id),
            str(doc),
            result.rendition,
            repo.Build(
                int(task.method_config_id),
                int(task.id),
                _payload_schema(conn, "parse_detail"),
                dict(result.parse_detail or {}),
                ts_config,
            ),
        )
        rendition_id = stored.id
    keys: dict[str, int] | None = None  # the stored rendition's segment ids, by key
    observations = []
    for ordinal, draft in enumerate(result.observations):
        ren = draft.rendition_id or rendition_id
        span_id = None
        if draft.span is not None:
            if ren is None:
                raise ValueError(f"task {task.id}: a span draft names no rendition")
            span_id = repo.upsert_spans(conn, ren, [draft.span])[0]
        segment_id = draft.segment_id
        named = _segment_named(draft.payload)
        if segment_id is None and named is not None and rendition_id is not None:
            if keys is None:
                keys = repo.segment_ids(conn, rendition_id)
            if named not in keys:
                raise ValueError(
                    f"task {task.id}: a draft names segment {named}, not on its rendition"
                )
            segment_id = keys[named]
        observations.append(
            repo.ObservationRow(
                ordinal,
                draft.kind.value,
                draft.payload,
                draft.outcome.value,
                ren,
                segment_id,
                span_id,
                draft.score,
            )
        )
    if observations:
        attempt = conn.execute(
            text("SELECT attempt FROM ops.task WHERE id = :i"), {"i": task.id}
        ).scalar_one()
        repo.write_observations(conn, int(task.id), int(attempt), observations)
    for m in result.measurements:
        conn.execute(
            T["ops.measurement"]
            .insert()
            .values(
                run_id=task.run_id,
                task_id=task.id,
                iteration=0,
                scope_type=m.scope_type.value,
                scope_id=m.scope_id,
                scope_key=m.scope_key,
                metric=m.metric,
                value=m.value,
                detail=dict(m.detail),
            )
        )


def write_result(
    conn: Connection, task_id: int, attempt: int, result: UnitResult, ts_config: str = "english"
) -> TaskStatus:
    """The task's terminal write in the caller's transaction (module doc); `ts_config` is the
    build's text-search configuration, its source profile's `language`."""
    task = _fence(conn, task_id, attempt)
    if result.outcome != ObservationOutcome.FAILED:
        _rows(conn, task, result, ts_config)
    status = OUTCOME_STATUS[result.outcome]
    if result.rendition is not None and status is TaskStatus.EMPTY:
        status = TaskStatus.DONE  # the rendition is its output (D3 §8's kb.run_rendition)
    cost = result.cost.model_dump(mode="json") if result.cost is not None else {}
    error = {"message": result.error} if result.error else None
    done = conn.execute(
        text(
            "UPDATE ops.task SET status = :s, cost = CAST(:cost AS jsonb), error = CAST(:error AS "
            "jsonb), lease_until = NULL, finished_at = clock_timestamp() WHERE id = :i AND "
            "attempt = :a AND status = 'running'"
        ),
        {"s": status.value, "cost": _json(cost), "error": _json(error), "i": task_id, "a": attempt},
    )
    if done.rowcount != 1:
        raise LeaseLost(f"task {task_id} lost its lease during the write")
    return status


def _json(value: Any) -> str | None:
    from corpus_structure.core.db.store import dumps

    return None if value is None else dumps(value)


def fail_task(conn: Connection, task_id: int, attempt: int, message: str) -> bool:
    """Write a claimed task `failed` with its error, fenced; whether it was still held."""
    done = conn.execute(
        text(
            "UPDATE ops.task SET status = 'failed', error = CAST(:e AS jsonb), lease_until = NULL, "
            "finished_at = clock_timestamp() WHERE id = :i AND attempt = :a AND status = 'running'"
        ),
        {"e": _json({"message": message}), "i": task_id, "a": attempt},
    )
    return done.rowcount == 1


def retry_task(conn: Connection, task_id: int, attempt: int, message: str) -> TaskStatus | None:
    """The conditional retry write: `pending` while `attempt < 3`, else `failed`; None when the
    lease was lost."""
    row = conn.execute(
        text(
            "UPDATE ops.task SET status = CASE WHEN attempt < :max THEN 'pending' ELSE 'failed' "
            "END, "
            "error = CAST(:e AS jsonb), lease_until = NULL, finished_at = CASE WHEN attempt < :max "
            "THEN NULL ELSE clock_timestamp() END WHERE id = :i AND attempt = :a AND status = "
            "'running' RETURNING status"
        ),
        {"max": MAX_ATTEMPTS, "e": _json({"message": message}), "i": task_id, "a": attempt},
    ).first()
    return None if row is None else TaskStatus(row[0])


def settle(
    engine: Engine, claimed: Claimed, result: UnitResult | BaseException, ts_config: str = "english"
) -> TaskStatus | None:
    """Write one task's outcome in its own transaction: the result, a retry, or `failed`."""
    if isinstance(result, BaseException):
        kind = classify_error(result)
        with engine.begin() as conn:
            if kind is ErrorClass.RETRY:
                return retry_task(conn, claimed.id, claimed.attempt, str(result))
            if kind is ErrorClass.FENCING:
                raise result
            return (
                TaskStatus.FAILED
                if fail_task(
                    conn, claimed.id, claimed.attempt, f"{type(result).__name__}: {result}"
                )
                else None
            )
    try:
        with engine.begin() as conn:
            return write_result(conn, claimed.id, claimed.attempt, result, ts_config)
    except LeaseLost:
        return None
    except Exception as error:  # a write that failed: classify it like a method's failure
        return settle(engine, claimed, error)


class Heartbeat:
    """Renews a worker's held leases on its own connection about every `every` seconds."""

    def __init__(self, engine: Engine, every: float = 60.0) -> None:
        self.engine, self.every = engine, every
        self.held: dict[int, int] = {}
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self._stop.wait(self.every):
            held = dict(self.held)
            if held:
                with self.engine.begin() as conn:
                    renew(conn, held)

    def __enter__(self) -> Heartbeat:
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        self._thread.join(timeout=5)


def task_rows(conn: Connection, ids: Sequence[int]) -> list[Any]:
    rows = conn.execute(
        text(
            "SELECT id, status, attempt, reason, finished_at FROM ops.task "
            "WHERE id = ANY(:i) ORDER BY id"
        ),
        {"i": list(ids)},
    )
    return list(rows)
