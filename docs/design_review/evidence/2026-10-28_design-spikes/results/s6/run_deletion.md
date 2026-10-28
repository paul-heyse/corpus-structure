# S6 run deletion (D3 §8)

### Run 3: the second slice run (T2 and T3 materialized, S6-B)

Run 3 deleted; run 1 kept. Plans are `EXPLAIN (COSTS off)`; "index usable" plans are taken with `SET LOCAL enable_seqscan = off`.

**eval.result** — `DELETE FROM eval.result WHERE run_id = 3`

chosen plan:
```
Delete on result
  ->  Bitmap Heap Scan on result
        Recheck Cond: (run_id = '3'::smallint)
        ->  Bitmap Index Scan on result_run
              Index Cond: (run_id = '3'::smallint)
```
index usable:
```
Delete on result
  ->  Bitmap Heap Scan on result
        Recheck Cond: (run_id = '3'::smallint)
        ->  Bitmap Index Scan on result_run
              Index Cond: (run_id = '3'::smallint)
```

**eval.alignment** — `DELETE FROM eval.alignment WHERE run_id = 3`

chosen plan:
```
Delete on alignment
  ->  Bitmap Heap Scan on alignment
        Recheck Cond: (run_id = '3'::smallint)
        ->  Bitmap Index Scan on alignment_run
              Index Cond: (run_id = '3'::smallint)
```
index usable:
```
Delete on alignment
  ->  Bitmap Heap Scan on alignment
        Recheck Cond: (run_id = '3'::smallint)
        ->  Bitmap Index Scan on alignment_run
              Index Cond: (run_id = '3'::smallint)
```

**kb.claim_link** — `DELETE FROM kb.claim_link WHERE run_id = 3`

chosen plan:
```
Delete on claim_link
  ->  Seq Scan on claim_link
        Filter: (run_id = '3'::smallint)
```
index usable:
```
Delete on claim_link
  ->  Seq Scan on claim_link
        Disabled: true
        Filter: (run_id = '3'::smallint)
```

**kb.claim** — `DELETE FROM kb.claim WHERE run_id = 3`

chosen plan:
```
Delete on claim
  ->  Index Scan using claim_statement on claim
        Index Cond: (run_id = '3'::smallint)
```
index usable:
```
Delete on claim
  ->  Index Scan using claim_statement on claim
        Index Cond: (run_id = '3'::smallint)
```

**kb.entity** — `DELETE FROM kb.entity WHERE run_id = 3`

chosen plan:
```
Delete on entity
  ->  Bitmap Heap Scan on entity
        Recheck Cond: (run_id = '3'::smallint)
        ->  Bitmap Index Scan on entity_type
              Index Cond: (run_id = '3'::smallint)
```
index usable:
```
Delete on entity
  ->  Bitmap Heap Scan on entity
        Recheck Cond: (run_id = '3'::smallint)
        ->  Bitmap Index Scan on entity_type
              Index Cond: (run_id = '3'::smallint)
```

**Referential checks** run per deleted row (generic plans, as the RI triggers prepare them):

- kb.claim_evidence (claim_id): `Bitmap Heap Scan on claim_evidence x / Recheck Cond: (claim_id = $1) / ->  Bitmap Index Scan on claim_evidence_pkey / Index Cond: (claim_id = $1)`
- kb.claim_support (claim_id): `Bitmap Heap Scan on claim_support x / Recheck Cond: (claim_id = $1) / ->  Bitmap Index Scan on claim_support_pkey / Index Cond: (claim_id = $1)`
- kb.claim_link (from_claim_id): `Bitmap Heap Scan on claim_link x / Recheck Cond: (from_claim_id = $1) / ->  Bitmap Index Scan on claim_link_from_claim_id_link_type_to_claim_id_key / Index Cond: (from_claim_id = $1)`
- kb.claim_link (to_claim_id): `Bitmap Heap Scan on claim_link x / Recheck Cond: (to_claim_id = $1) / ->  Bitmap Index Scan on claim_link_to / Index Cond: (to_claim_id = $1)`
- kb.claim (subject_id): `Index Only Scan using claim_subject on claim x / Index Cond: (subject_id = $1)`
- kb.claim (object_entity_id): `Index Only Scan using claim_object on claim x / Index Cond: (object_entity_id = $1)`
- kb.claim (statement_id): `Index Only Scan using claim_statement on claim x / Index Cond: (statement_id = $1)`
- kb.entity_alias (entity_id): `Bitmap Heap Scan on entity_alias x / Recheck Cond: (entity_id = $1) / ->  Bitmap Index Scan on entity_alias_pkey / Index Cond: (entity_id = $1)`
- kb.entity_anchor (entity_id): `Bitmap Heap Scan on entity_anchor x / Recheck Cond: (entity_id = $1) / ->  Bitmap Index Scan on entity_anchor_pkey / Index Cond: (entity_id = $1)`
- kb.entity_mention (entity_id): `Bitmap Heap Scan on entity_mention x / Recheck Cond: (entity_id = $1) / ->  Bitmap Index Scan on entity_mention_pkey / Index Cond: (entity_id = $1)`
- eval.alignment (golden_item_id): `Seq Scan on alignment x / Disabled: true / Filter: (golden_item_id = $1)`

Executed (`EXPLAIN ANALYZE`, one transaction), trigger and execution lines:
```
eval.result: Delete on result (actual time=0.020..0.021 rows=0.00 loops=1)
eval.result: Execution Time: 0.026 ms
eval.alignment: Delete on alignment (actual time=0.005..0.005 rows=0.00 loops=1)
eval.alignment: Execution Time: 0.007 ms
kb.claim_link: Delete on claim_link (actual time=0.005..0.005 rows=0.00 loops=1)
kb.claim_link: Execution Time: 0.007 ms
kb.claim: Delete on claim (actual time=0.018..0.018 rows=0.00 loops=1)
kb.claim: Trigger for constraint claim_evidence_claim_id_fkey: time=0.102 calls=8
kb.claim: Trigger for constraint claim_support_claim_id_fkey: time=0.076 calls=8
kb.claim: Trigger for constraint claim_link_from_claim_id_fkey: time=0.071 calls=8
kb.claim: Trigger for constraint claim_link_to_claim_id_fkey: time=0.071 calls=8
kb.claim: Execution Time: 0.344 ms
kb.entity: Delete on entity (actual time=0.014..0.014 rows=0.00 loops=1)
kb.entity: Trigger for constraint entity_alias_entity_id_fkey: time=0.104 calls=11
kb.entity: Trigger for constraint entity_anchor_entity_id_fkey: time=0.081 calls=11
kb.entity: Trigger for constraint entity_mention_entity_id_fkey: time=0.079 calls=11
kb.entity: Trigger for constraint claim_subject_id_fkey: time=0.231 calls=11
kb.entity: Trigger for constraint claim_object_entity_id_fkey: time=0.197 calls=11
kb.entity: Trigger for constraint claim_statement_id_fkey: time=0.205 calls=11
kb.entity: Execution Time: 0.917 ms
```

| rows | before | after |
|---|---|---|
| kb.entity | 11 | 0 |
| kb.claim | 8 | 0 |
| kb.claim_link | 1 | 0 |
| eval.alignment | 1 | 0 |
| eval.result | 1 | 0 |
| ops.task | 6 | 6 |
| ops.measurement | 1 | 1 |
| ops.run | 1 | 1 |
| kb.claim_evidence | 10 | 0 |
| kb.entity_alias | 18 | 0 |

Kept run 1 unchanged: True. Outcome: passed.
