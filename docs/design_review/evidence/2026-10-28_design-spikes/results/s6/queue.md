# S6 queue under concurrency (brief step 7b)

Run 26: 10000 pending tasks of one stage and configuration, batches of 50, lease 2.0 s, wait timeout 1.0 s (production: 5 min, 30–60 s). Processes: W1 (killed with SIGKILL holding its third batch), Z (claims one batch, stalls 2.5 leases without renewing, then tries to complete), W2 (throughout; listens on `cs_task_ready`). Outcome: **passed**.

## Claim statement (D6 §3, store note §4)

```sql
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
RETURNING t.id, t.attempt, t.lease_until, now()
```

Plan on the seeded table:

```
Update on task t
  ->  Nested Loop
        ->  Subquery Scan on picked
              ->  Limit
                    ->  LockRows
                          ->  Sort
                                Sort Key: task.priority DESC, task.id
                                ->  Bitmap Heap Scan on task
                                      Recheck Cond: (((run_id = '26'::smallint) AND (stage = 'work'::text) AND (method_config_id = '25'::smallint) AND (status = 'pending'::text)) OR ((lease_until < now()) AND (status = 'running'::text)))
                                      Filter: ((run_id = '26'::smallint) AND (stage = 'work'::text) AND (method_config_id = '25'::smallint) AND ((status = 'pending'::text) OR ((status = 'running'::text) AND (lease_until < now()))))
                                      ->  BitmapOr
                                            ->  Bitmap Index Scan on task_pending
                                                  Index Cond: ((run_id = '26'::smallint) AND (stage = 'work'::text) AND (method_config_id = '25'::smallint))
                                            ->  Bitmap Index Scan on task_lease
                                                  Index Cond: (lease_until < now())
        ->  Index Scan using task_pkey on task t
              Index Cond: (id = picked.id)
```

## Fencing and completion (one transaction)

```sql
UPDATE ops.task t SET lease_until = t.lease_until
FROM unnest(%(ids)s::bigint[], %(attempts)s::int[]) AS f(id, attempt)
WHERE t.id = f.id AND t.attempt = f.attempt AND t.status = 'running'
RETURNING t.id, t.attempt
-- then COPY kb.observation (binary, Copy.set_types) for the fenced-in ids
UPDATE ops.task SET status = 'done', cost = %(cost)s, finished_at = clock_timestamp(), claimed_by = NULL, lease_until = NULL
WHERE id = ANY(%(ids)s)
```

## Results

| check | value |
|---|---|
| tasks (10,000 + 100 notified + 100 silent) / done | 10200 / 10200 |
| observations / tasks with exactly one | 10200 / 10200 |
| observations whose attempt differs from the task's final attempt | 0 |
| claims logged / tasks claimed more than once | 10300 / 100 |
| a claim while the previous lease was live | 0 |
| re-claimed tasks = W1's in-flight batch (50) ∪ Z's batch (50) | True |
| re-claimed by | W2 (the ordinary claim; no reaper) |
| tasks at attempt 2 / above 2 | 100 / 0 |
| Z's fencing UPDATE matched / observations written by Z | 0 / 0 |
| observations written by W1 (batches completed before the kill) | 100 |
| kill to all 10,000 done / start to done | 3.22 s / 3.27 s |
| NOTIFY with the insert: commit to first claim / batch done | 0.0 s / 0.045 s |
| insert without NOTIFY: insert to first claim (timeout re-query) / batch done | 0.686 s / 0.725 s |
| W2 waits / woken by a notification / median wait | 6 / 1 / 1.0 s |

