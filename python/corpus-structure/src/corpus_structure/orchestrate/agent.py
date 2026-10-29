"""Agent leases, the completion primitive and twins (orchestration §3.7; D6 §3.1, §4; D8 §2.1).

**Leasing** (`lease_agent_tasks`, one transaction): settle twins among the candidates; claim the
head `awaiting_agent` task of the given configurations whose lease is absent or expired, excluding a
task whose twin (same configuration and input hash) holds an unexpired lease and whatever the
caller's `where` excludes; set `claimed_by = 'agent:<session>'`, a 30-minute lease and `attempt +
1`, the status left `awaiting_agent`. Without a run, the newest run with a leasable task is used.
`renew_agent_lease` and `release` are fenced on `attempt`; release clears the lease.

**Completion** (`complete_agent_task`, in the caller's transaction, the only path that completes an
agent task): a first unclean submission is *held*: its result is kept in `ops.task.error` and the
lease renewed, fenced, and nothing else changes. A clean or second submission locks the task's run
row `FOR SHARE`, then sets the outcome with `finished_at = clock_timestamp()`, fenced on `(id,
attempt, status = 'awaiting_agent')`; zero rows raises `TaskNotOpen` with the reason read from the
row (`twin_settled`, `cancelled`, `leased_again`, `finished`). On `done` or `empty` it settles the
twins, and it sends `pg_notify('cs_agent_task_done', <run id>)`, delivered at commit. A `failed`
outcome settles nothing (failed tasks are never reused).

**Twins** (`settle_twins`): an `awaiting_agent` task, of a run whose `fresh` option does not name
its method (`--fresh` asks again, and settlement would undo it), whose twin is `done` or `empty`
becomes `reused` pointing at it, its lease cleared and `finished_at = clock_timestamp()`. The rows
of the runs that own the settled tasks are locked `FOR SHARE` in id order first. The share locks and
the stamp taken after them order every completion and settlement against each run's seal (§3.8),
which takes the run row's update lock: each falls on one side of `cut_at`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Literal

from sqlalchemy import Connection, text

from corpus_structure.core.db.store import dumps
from corpus_structure.core.vocab import TaskStatus

AGENT_LEASE = timedelta(minutes=30)
CHANNEL = "cs_agent_task_done"
NotOpenReason = Literal["twin_settled", "cancelled", "leased_again", "finished", "missing"]


class TaskNotOpen(RuntimeError):
    """A submission to a task that is no longer open to it; `reason` says why."""

    def __init__(self, task_id: int, reason: NotOpenReason) -> None:
        self.task_id, self.reason = task_id, reason
        super().__init__(f"task {task_id} is not open: {reason}")


@dataclass(frozen=True)
class AgentLease:
    id: int
    run_id: int
    attempt: int
    unit_type: str
    unit_id: int | None
    unit_key: str | None
    packet_hash: str | None


def _interval(delta: timedelta) -> str:
    return f"{delta.total_seconds()} s"


_TWINS = """
SELECT a.id AS task_id, a.run_id, f.id AS twin_id
FROM ops.task a
JOIN ops.run r ON r.id = a.run_id
JOIN ops.method_config c ON c.id = a.method_config_id
JOIN ops.method m ON m.id = c.method_id
JOIN LATERAL (
  SELECT f.id FROM ops.task f
  WHERE f.method_config_id = a.method_config_id AND f.input_hash = a.input_hash
    AND f.status IN ('done', 'empty')
  ORDER BY f.id LIMIT 1
) f ON true
WHERE a.status = 'awaiting_agent'
  AND NOT coalesce(r.options -> 'fresh' ? m.name, false)  -- a fresh run asks again
  {filter}
"""


def settle_twins(
    conn: Connection,
    *,
    method_configs: Sequence[int] | None = None,
    run_id: int | None = None,
    config_hash: tuple[int, str] | None = None,
) -> int:
    """Settle open agent tasks whose twin finished (module doc); the number settled."""
    clauses, params = [], {}
    if method_configs is not None:
        clauses.append("a.method_config_id = ANY(:configs)")
        params["configs"] = list(method_configs)
    if run_id is not None:
        clauses.append("a.run_id = :run")
        params["run"] = run_id
    if config_hash is not None:
        clauses.append("a.method_config_id = :cfg AND a.input_hash = :hash")
        params["cfg"], params["hash"] = config_hash
    found = conn.execute(
        text(_TWINS.format(filter="".join(f" AND {c}" for c in clauses))), params
    ).all()
    if not found:
        return 0
    for run in sorted({r.run_id for r in found}):  # the runs' share locks, in id order
        conn.execute(text("SELECT 1 FROM ops.run WHERE id = :r FOR SHARE"), {"r": run})
    done = conn.execute(
        text(
            "UPDATE ops.task t SET status = 'reused', reused_task_id = s.twin_id, lease_until = "
            "NULL, "
            "claimed_by = NULL, finished_at = clock_timestamp() FROM unnest(CAST(:ids AS "
            "bigint[]), "
            "CAST(:twins AS bigint[])) AS s(id, twin_id) WHERE t.id = s.id AND t.status = "
            "'awaiting_agent'"
        ),
        {"ids": [r.task_id for r in found], "twins": [r.twin_id for r in found]},
    )
    return done.rowcount


_LEASE = """
WITH c AS MATERIALIZED (  -- evaluated once: a rescanned LIMIT subquery could lease more
  SELECT x.id FROM ops.task x
  WHERE x.status = 'awaiting_agent' AND x.method_config_id = ANY(:configs) {run}
    AND (x.lease_until IS NULL OR x.lease_until < now())
    AND NOT EXISTS (SELECT 1 FROM ops.task y WHERE y.method_config_id = x.method_config_id
                    AND y.input_hash = x.input_hash AND y.id <> x.id
                    AND y.status = 'awaiting_agent' AND y.lease_until > now())
    {where}
  ORDER BY x.run_id DESC, x.priority DESC, x.id
  LIMIT 1 FOR UPDATE SKIP LOCKED
)
UPDATE ops.task t
SET claimed_by = :holder, lease_until = now() + CAST(:lease AS interval), attempt = t.attempt + 1
FROM c
WHERE t.id = c.id
RETURNING t.id, t.run_id, t.attempt, t.unit_type, t.unit_id, t.unit_key, t.packet_hash
"""


def lease_agent_tasks(
    conn: Connection,
    *,
    session_ref: str,
    method_configs: Sequence[int],
    run_id: int | None = None,
    where: str | None = None,
    params: dict[str, Any] | None = None,
    max_units: int = 1,
    lease: timedelta = AGENT_LEASE,
) -> list[AgentLease]:
    """Lease the head agent task (module doc). `where` is an SQL condition over the candidate `x`,
    with its own `params`."""
    if max_units != 1:
        raise ValueError("max_units stays 1 until A3 decides")
    settle_twins(conn, method_configs=method_configs, run_id=run_id)
    sql = _LEASE.format(
        run="AND x.run_id = :run" if run_id is not None else "",
        where=f"AND ({where})" if where else "",
    )
    rows = conn.execute(
        text(sql),
        {
            **(params or {}),
            "holder": f"agent:{session_ref}",
            "lease": _interval(lease),
            "configs": list(method_configs),
            "run": run_id,
        },
    )
    return [
        AgentLease(
            int(r.id),
            int(r.run_id),
            int(r.attempt),
            r.unit_type,
            r.unit_id,
            r.unit_key,
            r.packet_hash,
        )
        for r in rows
    ]


def _fenced(attempt_clause: str) -> str:
    return f"WHERE id = :i AND attempt = :a AND status = 'awaiting_agent' {attempt_clause}"


def renew_agent_lease(
    conn: Connection, task_id: int, attempt: int, lease: timedelta = AGENT_LEASE
) -> bool:
    done = conn.execute(
        text("UPDATE ops.task SET lease_until = now() + CAST(:lease AS interval) " + _fenced("")),
        {"i": task_id, "a": attempt, "lease": _interval(lease)},
    )
    return done.rowcount == 1


def release(conn: Connection, task_id: int, attempt: int) -> bool:
    """Give the task back: its lease cleared, its status kept."""
    done = conn.execute(
        text("UPDATE ops.task SET lease_until = NULL, claimed_by = NULL " + _fenced("")),
        {"i": task_id, "a": attempt},
    )
    return done.rowcount == 1


def _not_open(conn: Connection, task_id: int, attempt: int, holder: str) -> TaskNotOpen:
    """Why a fenced write found no row: `leased_again` covers an open task whose lease this
    holder no longer has (leased to another attempt, or released)."""
    row = conn.execute(
        text("SELECT status, attempt, claimed_by FROM ops.task WHERE id = :i"), {"i": task_id}
    ).first()
    if row is None:
        return TaskNotOpen(task_id, "missing")
    reason: NotOpenReason
    if row.status == TaskStatus.REUSED:
        reason = "twin_settled"
    elif row.status == TaskStatus.CANCELLED:
        reason = "cancelled"
    elif row.status == TaskStatus.AWAITING_AGENT and (
        row.attempt != attempt or row.claimed_by != holder
    ):
        reason = "leased_again"
    else:
        reason = "finished"
    return TaskNotOpen(task_id, reason)


def complete_agent_task(
    conn: Connection,
    task_id: int,
    attempt: int,
    session_ref: str,
    *,
    clean: bool,
    outcome: TaskStatus,
    first_result: Any = None,
    lease: timedelta = AGENT_LEASE,
) -> Literal["held", "completed"]:
    """The only path that completes an agent task (module doc)."""
    if outcome not in (TaskStatus.DONE, TaskStatus.EMPTY, TaskStatus.FAILED):
        raise ValueError(f"an agent task completes done, empty or failed, not {outcome}")
    holder = f"agent:{session_ref}"
    held = conn.execute(
        text(
            "SELECT error IS NOT NULL AS held, run_id, method_config_id, "
            "input_hash FROM ops.task WHERE id = :i"
        ),
        {"i": task_id},
    ).first()
    if held is None:
        raise TaskNotOpen(task_id, "missing")
    if not clean and not held.held:
        done = conn.execute(
            text(
                "UPDATE ops.task SET error = CAST(:e AS jsonb), lease_until = now() + CAST(:lease "
                "AS "
                "interval) " + _fenced("AND claimed_by = :holder")
            ),
            {
                "e": dumps({"message": "held for resubmission", "detail": first_result}),
                "lease": _interval(lease),
                "i": task_id,
                "a": attempt,
                "holder": holder,
            },
        )
        if done.rowcount != 1:
            raise _not_open(conn, task_id, attempt, holder)
        return "held"
    conn.execute(text("SELECT 1 FROM ops.run WHERE id = :r FOR SHARE"), {"r": held.run_id})
    done = conn.execute(
        text(
            "UPDATE ops.task SET status = :s, finished_at = clock_timestamp(), lease_until = NULL "
            + _fenced("AND claimed_by = :holder")
        ),
        {"s": outcome.value, "i": task_id, "a": attempt, "holder": holder},
    )
    if done.rowcount != 1:
        raise _not_open(conn, task_id, attempt, holder)
    if outcome in (TaskStatus.DONE, TaskStatus.EMPTY):
        settle_twins(conn, config_hash=(int(held.method_config_id), str(held.input_hash)))
    conn.execute(text("SELECT pg_notify(:c, :p)"), {"c": CHANNEL, "p": str(held.run_id)})
    return "completed"
