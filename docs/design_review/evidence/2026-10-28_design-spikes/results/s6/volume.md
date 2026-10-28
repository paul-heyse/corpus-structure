# S6 volume (brief step 7)

Run 25 (`full`, finished): 2500 units, 12500 tasks, 100000 observations, 5000 entities, 20000 claims. PostgreSQL 18.6 on the project-local cluster (shared_buffers 160 MB, work_mem 4 MB); client wall times, median of 7.

| step | rows | ms | rows/s | mean payload B | note |
|---|---|---|---|---|---|
| copy ops.task | 12500 | 103.4 | 120894 |  | binary COPY, set_types |
| copy kb.observation | 100000 | 1109.7 | 90116 | 297 | mention mean 138 B; relation mean 205 B; scope mean 238 B; value mean 262 B; claim_proposal mean 4295 B |
| copy kb.entity | 5000 | 38.5 | 129828 |  |  |
| copy kb.claim | 20000 | 228.6 | 87478 |  | qualifiers and values of the v1 reference claims, cycled |
| copy kb.claim_support + kb.claim_evidence | 40000 | 213.7 | 187178 |  |  |

D6 §3 binary COPY notes (one row each, rolled back): score as float8 into real: 22P03: incorrect binary data format; payload as str into jsonb (declared jsonb): accepted

## claims with qualifier param_values.variance (`@?`, no GIN)

1410 rows; median 1.001 ms.

```
Bitmap Heap Scan on claim (actual rows=1410.00 loops=1)
  Recheck Cond: ((run_id = '25'::smallint) AND (predicate = 'stat:has_distribution'::text))
  Filter: (qualifiers @? '$."param_values"."variance"'::jsonpath)
  Rows Removed by Filter: 4505
  Heap Blocks: exact=1017
  Buffers: shared hit=1025
  ->  Bitmap Index Scan on claim_pred (actual rows=5915.00 loops=1)
        Index Cond: ((run_id = '25'::smallint) AND (predicate = 'stat:has_distribution'::text))
        Index Searches: 1
        Buffers: shared hit=8
Planning Time: 0.022 ms
Execution Time: 0.867 ms
```

## why a method ran (one unit)

5 rows; median 0.559 ms.

```
Sort (actual rows=5.00 loops=1)
  Sort Key: t.id
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=446
  ->  Nested Loop Left Join (actual rows=5.00 loops=1)
        Join Filter: (pr.id = t.trigger_rule_id)
        Rows Removed by Join Filter: 5
        Buffers: shared hit=446
        ->  Nested Loop (actual rows=5.00 loops=1)
              Join Filter: (m.id = mc.method_id)
              Rows Removed by Join Filter: 50
              Buffers: shared hit=445
              ->  Seq Scan on method m (actual rows=11.00 loops=1)
                    Buffers: shared hit=1
              ->  Materialize (actual rows=5.00 loops=11)
                    Storage: Memory  Maximum Storage: 17kB
                    Buffers: shared hit=444
                    ->  Nested Loop (actual rows=5.00 loops=1)
                          Join Filter: (mc.id = t.method_config_id)
                          Rows Removed by Join Filter: 60
                          Buffers: shared hit=444
                          ->  Seq Scan on method_config mc (actual rows=13.00 loops=1)
                                Buffers: shared hit=1
                          ->  Materialize (actual rows=5.00 loops=13)
                                Storage: Memory  Maximum Storage: 17kB
                                Buffers: shared hit=443
                                ->  Seq Scan on task t (actual rows=5.00 loops=1)
                                      Filter: ((run_id = '25'::smallint) AND (unit_key = 'unit:vol-1234'::text))
                                      Rows Removed by Filter: 12554
                                      Buffers: shared hit=443
        ->  Materialize (actual rows=1.00 loops=5)
              Storage: Memory  Maximum Storage: 17kB
              Buffers: shared hit=1
              ->  Seq Scan on policy_rule pr (actual rows=1.00 loops=1)
                    Buffers: shared hit=1
Planning:
  Buffers: shared hit=11
Planning Time: 0.059 ms
Execution Time: 0.441 ms
```

## effective observations of one task (kb.run_observation)

1 rows; median 0.559 ms.

```
Aggregate (actual rows=1.00 loops=1)
  Buffers: shared hit=448
  ->  Nested Loop (actual rows=16.00 loops=1)
        Buffers: shared hit=448
        ->  Nested Loop (actual rows=1.00 loops=1)
              Join Filter: ((r.finished_at IS NULL) OR (t.finished_at <= r.finished_at))
              Buffers: shared hit=444
              ->  Seq Scan on run r (actual rows=1.00 loops=1)
                    Filter: (id = '25'::smallint)
                    Rows Removed by Filter: 3
                    Buffers: shared hit=1
              ->  Seq Scan on task t (actual rows=1.00 loops=1)
                    Filter: ((run_id = '25'::smallint) AND (COALESCE(reused_task_id, id) = '6247'::smallint) AND (status = ANY ('{done,empty,reused}'::text[])))
                    Rows Removed by Filter: 12558
                    Buffers: shared hit=443
        ->  Materialize (actual rows=16.00 loops=1)
              Storage: Memory  Maximum Storage: 17kB
              Buffers: shared hit=4
              ->  Index Only Scan using observation_task_id_ordinal_key on observation o (actual rows=16.00 loops=1)
                    Index Cond: (task_id = '6247'::smallint)
                    Heap Fetches: 16
                    Index Searches: 1
                    Buffers: shared hit=4
Planning:
  Buffers: shared hit=3
Planning Time: 0.044 ms
Execution Time: 0.496 ms
```

## observations of the run by kind (kb.run_observation)

5 rows; median 17.931 ms.

```
Sort (actual rows=5.00 loops=1)
  Sort Key: o.kind
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=5148
  ->  HashAggregate (actual rows=5.00 loops=1)
        Group Key: o.kind
        Batches: 1  Memory Usage: 32kB
        Buffers: shared hit=5148
        ->  Hash Join (actual rows=100000.00 loops=1)
              Hash Cond: (COALESCE(t.reused_task_id, t.id) = o.task_id)
              Buffers: shared hit=5148
              ->  Nested Loop (actual rows=12500.00 loops=1)
                    Join Filter: ((r.finished_at IS NULL) OR (t.finished_at <= r.finished_at))
                    Buffers: shared hit=444
                    ->  Seq Scan on run r (actual rows=1.00 loops=1)
                          Filter: (id = '25'::smallint)
                          Rows Removed by Filter: 3
                          Buffers: shared hit=1
                    ->  Seq Scan on task t (actual rows=12500.00 loops=1)
                          Filter: ((run_id = '25'::smallint) AND (status = ANY ('{done,empty,reused}'::text[])))
                          Rows Removed by Filter: 59
                          Buffers: shared hit=443
              ->  Hash (actual rows=100014.00 loops=1)
                    Buckets: 131072  Batches: 1  Memory Usage: 5889kB
                    Buffers: shared hit=4704
                    ->  Seq Scan on observation o (actual rows=100014.00 loops=1)
                          Buffers: shared hit=4704
Planning:
  Buffers: shared hit=3
Planning Time: 0.136 ms
Execution Time: 19.616 ms
```

## claims of one subject

1 rows; median 0.037 ms.

```
Aggregate (actual rows=1.00 loops=1)
  Buffers: shared hit=6
  ->  Index Only Scan using claim_subject on claim (actual rows=4.00 loops=1)
        Index Cond: ((run_id = '25'::smallint) AND (subject_id = '182'::smallint))
        Heap Fetches: 4
        Index Searches: 1
        Buffers: shared hit=6
Planning Time: 0.010 ms
Execution Time: 0.005 ms
```

