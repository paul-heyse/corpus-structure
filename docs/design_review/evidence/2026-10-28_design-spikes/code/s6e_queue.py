"""S6-E step 7b: the work queue under concurrency (D3 §8, D6 §3; P0-O-1).

    uv run python code/s6e_queue.py      # on cs_spike_s6 after s6b_rows.py

10,000 ``pending`` tasks of one run, stage and configuration. Worker processes, each with its own
connections, claim with the D6 §3 statement (store note §4: ``UPDATE … FROM (SELECT … FOR UPDATE
SKIP LOCKED LIMIT n)`` that also takes expired leases and increments ``attempt``), commit the
claim, "run" the method outside a transaction, then complete in one transaction: a fencing
``UPDATE`` conditioned on ``(id, attempt, status = 'running')``, the observations by binary COPY
with ``Copy.set_types``, and the outcome with ``cost`` and ``finished_at``.

- W1 claims normally and is killed abruptly (SIGKILL) while it holds its third batch;
- Z claims one batch and stalls past its lease without renewing (a worker paused or partitioned),
  then tries to complete: its fencing UPDATE must match nothing and it must commit no observation;
- W2 runs throughout; it takes the expired leases through the ordinary claim (no reaper).
  When a claim returns nothing it waits on ``LISTEN cs_task_ready`` (dedicated autocommit
  connection, ``LISTEN`` before re-checking the table) with a timeout, and re-queries.
- After the 10,000 are done: 100 tasks inserted with ``NOTIFY cs_task_ready`` in the same
  transaction (wake-up latency), then 100 without a notification (the timeout path).

The lease is 2 s and the wait timeout 1 s here (production: 5 min and 30–60 s), so expiry happens
within the test. Checks: every task done once with exactly one observation, written by the
attempt that finished it; a task is claimed again only after its previous lease expired; the
re-claimed tasks are exactly W1's and Z's in-flight batches; Z's late write commits nothing.
Writes ``results/s6/queue.md`` and ``results/s6/queue.json``; raw claim logs go to ``--log-dir``.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import signal
import statistics
import time
from pathlib import Path

from s6_db import RESULTS, app, write_json

N, BATCH, LEASE_S, WAIT_S = 10_000, 50, 2.0, 1.0

CLAIM = """
UPDATE ops.task t
SET status = 'running', claimed_by = %(worker)s, attempt = t.attempt + 1,
    lease_until = now() + make_interval(secs => %(lease)s), started_at = coalesce(t.started_at, now())
FROM (SELECT id FROM ops.task
      WHERE run_id = %(run)s AND stage = %(stage)s AND method_config_id = %(cfg)s
        AND (status = 'pending' OR (status = 'running' AND lease_until < now()))
      ORDER BY priority DESC, id
      LIMIT %(n)s
      FOR UPDATE SKIP LOCKED) picked
WHERE t.id = picked.id
RETURNING t.id, t.attempt, t.lease_until, now()"""

FENCE = """
UPDATE ops.task t SET lease_until = t.lease_until
FROM unnest(%(ids)s::bigint[], %(attempts)s::int[]) AS f(id, attempt)
WHERE t.id = f.id AND t.attempt = f.attempt AND t.status = 'running'
RETURNING t.id, t.attempt"""

DONE = """
UPDATE ops.task SET status = 'done', cost = %(cost)s, finished_at = clock_timestamp(), claimed_by = NULL, lease_until = NULL
WHERE id = ANY(%(ids)s)"""


def complete(c, worker, claimed, log):
    """One transaction: fence, COPY observations for the fenced-in tasks, write the outcome."""
    from psycopg.types.json import Jsonb
    ids, attempts = [t[0] for t in claimed], [t[1] for t in claimed]
    with c.transaction():
        ok = c.execute(FENCE, {"ids": ids, "attempts": attempts}).fetchall()
        if ok:
            with c.cursor().copy("COPY kb.observation (task_id, ordinal, kind, payload, score, outcome) FROM STDIN (FORMAT BINARY)") as cp:
                cp.set_types(["int8", "int4", "text", "jsonb", "float4", "text"])
                for tid, att in ok:
                    cp.write_row((tid, 0, "record", {"structure": "s6.queue", "fields": {}, "worker": worker, "attempt": att}, 1.0, "produced"))
            c.execute(DONE, {"ids": [t[0] for t in ok], "cost": Jsonb({"wall_ms": 1})})
    log.write(json.dumps({"ev": "complete", "w": worker, "claimed": len(ids), "fenced_in": len(ok), "t": time.time()}) + "\n")
    log.flush()
    return len(ok)


def claim(c, worker, ctx, log, n=BATCH):
    with c.transaction():
        rows = c.execute(CLAIM, {"worker": worker, "lease": LEASE_S, "run": ctx["run"], "stage": "work", "cfg": ctx["cfg"], "n": n}).fetchall()
    for tid, att, lease, at in rows:
        log.write(json.dumps({"ev": "claim", "w": worker, "id": tid, "attempt": att, "lease_until": lease.timestamp(), "at": at.timestamp()}) + "\n")
    log.flush()
    return [(r[0], r[1]) for r in rows]


def worker_main(worker, ctx, role, events, log_dir):
    log = open(Path(log_dir) / f"{worker}.jsonl", "w")
    c = app(autocommit=False)
    listener = None
    if role == "steady":
        listener = app(autocommit=True)
        listener.execute("LISTEN cs_task_ready")       # LISTEN first, then check the table
    batches = 0
    while True:
        got = claim(c, worker, ctx, log)
        if got:
            batches += 1
            if role == "zombie":
                events["z_claimed"].set()
                time.sleep(LEASE_S * 2.5)                # stalls past its lease, never renews
                n = complete(c, worker, got, log)
                log.write(json.dumps({"ev": "zombie_result", "fenced_in": n, "t": time.time()}) + "\n")
                log.close()
                return
            if role == "victim" and batches == 3:
                events["w1_mid"].set()
                time.sleep(60)                           # killed here, holding its third batch
            time.sleep(0.0002 * len(got))                # the method, outside any transaction
            complete(c, worker, got, log)
            continue
        if events["stop"].is_set():
            break
        if listener is None:
            time.sleep(0.05)
            continue
        t0 = time.time()
        woke = False
        for _ in listener.notifies(timeout=WAIT_S, stop_after=1):
            woke = True
        log.write(json.dumps({"ev": "wait", "w": worker, "woke": woke, "waited": time.time() - t0, "t": time.time()}) + "\n")
        log.flush()
    log.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log-dir", default=str(Path(os.environ.get("TMPDIR", "/tmp")) / "s6_queue_logs"))
    a = ap.parse_args()
    Path(a.log_dir).mkdir(parents=True, exist_ok=True)
    with app() as c:
        proj = c.execute("SELECT id FROM meta.project LIMIT 1").fetchone()[0]
        sv = c.execute("SELECT id FROM meta.schema_version ORDER BY id LIMIT 1").fetchone()[0]
        pol = c.execute("SELECT id FROM ops.policy_version LIMIT 1").fetchone()[0]
        c.execute("DELETE FROM ops.method WHERE name = 'queue.work' AND NOT EXISTS (SELECT 1 FROM ops.method_config mc WHERE mc.method_id = ops.method.id)")
        mid = c.execute("INSERT INTO ops.method (name, version, family) VALUES ('queue.work', %s, 'measure') RETURNING id", (str(time.time()),)).fetchone()[0]
        cfg = c.execute("INSERT INTO ops.method_config (method_id, params, config_hash, tier) VALUES (%s, '{}', %s, 'deterministic') RETURNING id",
                        (mid, f"cfg:queue-{time.time()}")).fetchone()[0]
        run = c.execute("INSERT INTO ops.run (project_id, kind, phase, corpus_hash, schema_version_id, policy_version_id, code_commit, status, started_at) "
                        "VALUES (%s, 'experiment', 0, 'queue-test', %s, %s, '35ea59a', 'running', now()) RETURNING id", (proj, sv, pol)).fetchone()[0]
        with c.cursor().copy("COPY ops.task (run_id, stage, unit_type, unit_id, unit_key, method_config_id, input_hash, status, priority) FROM STDIN (FORMAT BINARY)") as cp:
            cp.set_types(["int8", "text", "text", "int8", "text", "int8", "text", "text", "int4"])
            for i in range(N):
                cp.write_row((run, "work", "segment", None, f"unit:q-{i}", cfg, f"h{i}", "pending", i % 3))
        c.commit()
        c.execute("ANALYZE ops.task")
        c.commit()
        ctx = {"run": run, "cfg": cfg}
        with c.transaction(force_rollback=True):
            claim_plan = [r[0] for r in c.execute("EXPLAIN (COSTS off) " + CLAIM, {"worker": "explain", "lease": LEASE_S, "run": run, "stage": "work", "cfg": cfg, "n": BATCH})]

    mpc = mp.get_context("fork")
    events = {k: mpc.Event() for k in ("z_claimed", "w1_mid", "stop")}
    t_start = time.time()
    z = mpc.Process(target=worker_main, args=("Z", ctx, "zombie", events, a.log_dir))
    z.start()
    events["z_claimed"].wait(10)
    w1 = mpc.Process(target=worker_main, args=("W1", ctx, "victim", events, a.log_dir))
    w2 = mpc.Process(target=worker_main, args=("W2", ctx, "steady", events, a.log_dir))
    w1.start()
    w2.start()
    events["w1_mid"].wait(30)
    os.kill(w1.pid, signal.SIGKILL)
    t_kill = time.time()
    w1.join()

    def remaining(c):
        return c.execute("SELECT count(*) FROM ops.task WHERE run_id = %s AND status <> 'done'", (run,)).fetchone()[0]

    with app(autocommit=True) as c:
        deadline = time.time() + 180
        while remaining(c) and time.time() < deadline:
            time.sleep(0.2)
        t_drained = time.time()
        z.join(30)
        time.sleep(WAIT_S * 1.5)   # W2 is now waiting on LISTEN
        # wake-up by NOTIFY: tasks and notification in one transaction; delivered at commit
        with c.transaction():
            with c.cursor().copy("COPY ops.task (run_id, stage, unit_type, unit_key, method_config_id, input_hash, status) FROM STDIN (FORMAT BINARY)") as cp:
                cp.set_types(["int8", "text", "text", "text", "int8", "text", "text"])
                for i in range(100):
                    cp.write_row((run, "work", "segment", f"unit:qn-{i}", cfg, f"n{i}", "pending"))
            c.execute("NOTIFY cs_task_ready")
        t_notify = time.time()
        while remaining(c):
            time.sleep(0.01)
        t_notify_done = time.time()
        time.sleep(WAIT_S * 0.3)
        with c.transaction():  # no notification: found on the next timeout re-query
            with c.cursor().copy("COPY ops.task (run_id, stage, unit_type, unit_key, method_config_id, input_hash, status) FROM STDIN (FORMAT BINARY)") as cp:
                cp.set_types(["int8", "text", "text", "text", "int8", "text", "text"])
                for i in range(100):
                    cp.write_row((run, "work", "segment", f"unit:qt-{i}", cfg, f"t{i}", "pending"))
        t_silent = time.time()
        while remaining(c):
            time.sleep(0.01)
        t_silent_done = time.time()
        events["stop"].set()
        w2.join(10)
        c.execute("UPDATE ops.run SET status = 'finished', finished_at = now() WHERE id = %s", (run,))

        # checks
        logs = {w: [json.loads(x) for x in (Path(a.log_dir) / f"{w}.jsonl").read_text().splitlines()] for w in ("W1", "W2", "Z")}
        claims = [e for w in logs.values() for e in w if e["ev"] == "claim"]
        by_task = {}
        for e in claims:
            by_task.setdefault(e["id"], []).append(e)
        overlapping = 0
        reclaimed = {}
        for tid, es in by_task.items():
            es.sort(key=lambda e: e["attempt"])
            for prev, nxt in zip(es, es[1:]):
                if nxt["at"] <= prev["lease_until"]:
                    overlapping += 1
                reclaimed[tid] = (prev["w"], nxt["w"], nxt["attempt"])
        w1_claims = [e for e in logs["W1"] if e["ev"] == "claim"]
        w1_batches, cur, last_at = [], [], None
        for e in w1_claims:
            if last_at is not None and e["at"] != last_at:
                w1_batches.append(cur)
                cur = []
            cur.append(e["id"])
            last_at = e["at"]
        w1_batches.append(cur)
        w1_inflight = set(w1_batches[-1])
        z_ids = {e["id"] for e in logs["Z"] if e["ev"] == "claim"}
        z_result = next((e for e in logs["Z"] if e["ev"] == "zombie_result"), None)
        db = dict(zip(("tasks", "done", "attempt_2", "attempt_gt_2", "obs", "tasks_with_one_obs", "obs_attempt_mismatch", "z_obs", "w1_obs"), c.execute("""
            SELECT count(*), count(*) FILTER (WHERE status = 'done'), count(*) FILTER (WHERE attempt = 2), count(*) FILTER (WHERE attempt > 2),
                   (SELECT count(*) FROM kb.observation o JOIN ops.task t2 ON t2.id = o.task_id WHERE t2.run_id = %(run)s),
                   count(*) FILTER (WHERE (SELECT count(*) FROM kb.observation o WHERE o.task_id = t.id) = 1),
                   (SELECT count(*) FROM kb.observation o JOIN ops.task t2 ON t2.id = o.task_id WHERE t2.run_id = %(run)s AND (o.payload ->> 'attempt')::int <> t2.attempt),
                   (SELECT count(*) FROM kb.observation o JOIN ops.task t2 ON t2.id = o.task_id WHERE t2.run_id = %(run)s AND o.payload ->> 'worker' = 'Z'),
                   (SELECT count(*) FROM kb.observation o JOIN ops.task t2 ON t2.id = o.task_id WHERE t2.run_id = %(run)s AND o.payload ->> 'worker' = 'W1')
            FROM ops.task t WHERE t.run_id = %(run)s""", {"run": run}).fetchone()))
        waits = [e for e in logs["W2"] if e["ev"] == "wait"]
        first_claim_after = lambda t: min((e["at"] for e in logs["W2"] if e["ev"] == "claim" and e["at"] >= t - 0.05), default=None)  # noqa: E731
        notify_latency = (first_claim_after(t_notify) or 0) - t_notify
        silent_latency = (first_claim_after(t_silent) or 0) - t_silent
        res = {
            "run": run, "tasks_seeded": N, "batch": BATCH, "lease_s": LEASE_S, "wait_timeout_s": WAIT_S, "db": db,
            "claims_logged": len(claims), "tasks_claimed_more_than_once": len(reclaimed), "overlapping_live_leases": overlapping,
            "reclaimed_are_w1_inflight_and_z": set(reclaimed) == (w1_inflight | z_ids),
            "w1_inflight": len(w1_inflight), "z_batch": len(z_ids), "z_fenced_in": z_result["fenced_in"] if z_result else None,
            "reclaimed_by": sorted({v[1] for v in reclaimed.values()}),
            "seconds_kill_to_drained": round(t_drained - t_kill, 2), "seconds_total_10000": round(t_drained - t_start, 2),
            "notify_wake_latency_s": round(notify_latency, 3), "notify_batch_done_s": round(t_notify_done - t_notify, 3),
            "silent_pickup_latency_s": round(silent_latency, 3), "silent_batch_done_s": round(t_silent_done - t_silent, 3),
            "waits": len(waits), "waits_woken_by_notify": sum(1 for e in waits if e["woke"]),
            "wait_durations_s_median": round(statistics.median([e["waited"] for e in waits]), 3) if waits else None,
            "claim_plan": claim_plan,
        }
        ok = (db["tasks"] == N + 200 and db["done"] == db["tasks"] and db["tasks_with_one_obs"] == db["tasks"] and db["obs"] == db["tasks"]
              and db["obs_attempt_mismatch"] == 0 and db["z_obs"] == 0 and overlapping == 0 and res["reclaimed_are_w1_inflight_and_z"]
              and res["z_fenced_in"] == 0 and db["attempt_2"] == len(w1_inflight | z_ids) and db["attempt_gt_2"] == 0
              and 0 <= notify_latency < WAIT_S and silent_latency <= WAIT_S * 1.5)
        res["outcome"] = "passed" if ok else "failed"
    write_json(RESULTS / "queue.json", res)
    md = ["# S6 queue under concurrency (brief step 7b)", "",
          f"Run {run}: {N} pending tasks of one stage and configuration, batches of {BATCH}, lease {LEASE_S} s, wait timeout {WAIT_S} s "
          "(production: 5 min, 30–60 s). Processes: W1 (killed with SIGKILL holding its third batch), Z (claims one batch, stalls 2.5 leases "
          "without renewing, then tries to complete), W2 (throughout; listens on `cs_task_ready`). Outcome: **" + res["outcome"] + "**.", "",
          "## Claim statement (D6 §3, store note §4)", "", "```sql", CLAIM.strip(), "```", "", "Plan on the seeded table:", "", "```", *claim_plan, "```", "",
          "## Fencing and completion (one transaction)", "", "```sql", FENCE.strip(), "-- then COPY kb.observation (binary, Copy.set_types) for the fenced-in ids", DONE.strip(), "```", "",
          "## Results", "",
          "| check | value |", "|---|---|",
          f"| tasks (10,000 + 100 notified + 100 silent) / done | {db['tasks']} / {db['done']} |",
          f"| observations / tasks with exactly one | {db['obs']} / {db['tasks_with_one_obs']} |",
          f"| observations whose attempt differs from the task's final attempt | {db['obs_attempt_mismatch']} |",
          f"| claims logged / tasks claimed more than once | {len(claims)} / {len(reclaimed)} |",
          f"| a claim while the previous lease was live | {overlapping} |",
          f"| re-claimed tasks = W1's in-flight batch ({len(w1_inflight)}) ∪ Z's batch ({len(z_ids)}) | {res['reclaimed_are_w1_inflight_and_z']} |",
          f"| re-claimed by | {', '.join(res['reclaimed_by'])} (the ordinary claim; no reaper) |",
          f"| tasks at attempt 2 / above 2 | {db['attempt_2']} / {db['attempt_gt_2']} |",
          f"| Z's fencing UPDATE matched / observations written by Z | {res['z_fenced_in']} / {db['z_obs']} |",
          f"| observations written by W1 (batches completed before the kill) | {db['w1_obs']} |",
          f"| kill to all 10,000 done / start to done | {res['seconds_kill_to_drained']} s / {res['seconds_total_10000']} s |",
          f"| NOTIFY with the insert: commit to first claim / batch done | {res['notify_wake_latency_s']} s / {res['notify_batch_done_s']} s |",
          f"| insert without NOTIFY: insert to first claim (timeout re-query) / batch done | {res['silent_pickup_latency_s']} s / {res['silent_batch_done_s']} s |",
          f"| W2 waits / woken by a notification / median wait | {res['waits']} / {res['waits_woken_by_notify']} / {res['wait_durations_s_median']} s |", ""]
    (RESULTS / "queue.md").write_text("\n".join(md) + "\n")
    print(json.dumps({k: v for k, v in res.items() if k != "claim_plan"}, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
