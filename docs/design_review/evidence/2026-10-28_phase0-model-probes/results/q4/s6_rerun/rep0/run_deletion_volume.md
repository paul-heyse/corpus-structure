# S6 run deletion at volume (D3 §8)

### Volume run 4 (5,000 entities, 20,000 claims)

Run 4 deleted; run 1 kept. Plans are `EXPLAIN (COSTS off)`; "index usable" plans are taken with `SET LOCAL enable_seqscan = off`.

**eval.result** — `DELETE FROM eval.result WHERE run_id = 4`

chosen plan:
```
Delete on result
  ->  Seq Scan on result
        Filter: (run_id = '4'::smallint)
```
index usable:
```
Delete on result
  ->  Index Scan using result_run on result
        Index Cond: (run_id = '4'::smallint)
```

**eval.alignment** — `DELETE FROM eval.alignment WHERE run_id = 4`

chosen plan:
```
Delete on alignment
  ->  Seq Scan on alignment
        Filter: (run_id = '4'::smallint)
```
index usable:
```
Delete on alignment
  ->  Index Scan using alignment_run on alignment
        Index Cond: (run_id = '4'::smallint)
```

**kb.claim_link** — `DELETE FROM kb.claim_link WHERE run_id = 4`

chosen plan:
```
Delete on claim_link
  ->  Seq Scan on claim_link
        Filter: (run_id = '4'::smallint)
```
index usable:
```
Delete on claim_link
  ->  Seq Scan on claim_link
        Disabled: true
        Filter: (run_id = '4'::smallint)
```

**kb.claim** — `DELETE FROM kb.claim WHERE run_id = 4`

chosen plan:
```
Delete on claim
  ->  Seq Scan on claim
        Filter: (run_id = '4'::smallint)
```
index usable:
```
Delete on claim
  ->  Index Scan using claim_statement on claim
        Index Cond: (run_id = '4'::smallint)
```

**kb.entity** — `DELETE FROM kb.entity WHERE run_id = 4`

chosen plan:
```
Delete on entity
  ->  Seq Scan on entity
        Filter: (run_id = '4'::smallint)
```
index usable:
```
Delete on entity
  ->  Index Scan using entity_type on entity
        Index Cond: (run_id = '4'::smallint)
```

**Referential checks** run per deleted row (generic plans, as the RI triggers prepare them):

- kb.claim_evidence (claim_id): `Index Only Scan using claim_evidence_pkey on claim_evidence x / Index Cond: (claim_id = $1)`
- kb.claim_support (claim_id): `Index Only Scan using claim_support_pkey on claim_support x / Index Cond: (claim_id = $1)`
- kb.claim_link (from_claim_id): `Index Only Scan using claim_link_from_claim_id_link_type_to_claim_id_key on claim_link x / Index Cond: (from_claim_id = $1)`
- kb.claim_link (to_claim_id): `Index Only Scan using claim_link_to on claim_link x / Index Cond: (to_claim_id = $1)`
- kb.claim (subject_id): `Index Only Scan using claim_subject on claim x / Index Cond: (subject_id = $1)`
- kb.claim (object_entity_id): `Index Only Scan using claim_object on claim x / Index Cond: (object_entity_id = $1)`
- kb.claim (statement_id): `Index Only Scan using claim_statement on claim x / Index Cond: (statement_id = $1)`
- kb.entity_alias (entity_id): `Index Only Scan using entity_alias_pkey on entity_alias x / Index Cond: (entity_id = $1)`
- kb.entity_anchor (entity_id): `Index Only Scan using entity_anchor_pkey on entity_anchor x / Index Cond: (entity_id = $1)`
- kb.entity_mention (entity_id): `Index Only Scan using entity_mention_pkey on entity_mention x / Index Cond: (entity_id = $1)`
- eval.alignment (golden_item_id): `Seq Scan on alignment x / Disabled: true / Filter: (golden_item_id = $1)`

Executed (`EXPLAIN ANALYZE`, one transaction), trigger and execution lines:
```
eval.result: Delete on result (actual time=0.003..0.003 rows=0.00 loops=1)
eval.result: Execution Time: 0.006 ms
eval.alignment: Delete on alignment (actual time=0.001..0.001 rows=0.00 loops=1)
eval.alignment: Execution Time: 0.002 ms
kb.claim_link: Delete on claim_link (actual time=0.001..0.001 rows=0.00 loops=1)
kb.claim_link: Execution Time: 0.002 ms
kb.claim: Delete on claim (actual time=7.509..7.510 rows=0.00 loops=1)
kb.claim: Trigger for constraint claim_evidence_claim_id_fkey: time=46.029 calls=20000
kb.claim: Trigger for constraint claim_support_claim_id_fkey: time=42.687 calls=20000
kb.claim: Trigger for constraint claim_link_from_claim_id_fkey: time=36.671 calls=20000
kb.claim: Trigger for constraint claim_link_to_claim_id_fkey: time=36.450 calls=20000
kb.claim: Execution Time: 171.735 ms
kb.entity: Delete on entity (actual time=1.892..1.893 rows=0.00 loops=1)
kb.entity: Trigger for constraint entity_alias_entity_id_fkey: time=20.259 calls=5000
kb.entity: Trigger for constraint entity_anchor_entity_id_fkey: time=17.019 calls=5000
kb.entity: Trigger for constraint entity_mention_entity_id_fkey: time=15.339 calls=5000
kb.entity: Trigger for constraint claim_subject_id_fkey: time=28.052 calls=5000
kb.entity: Trigger for constraint claim_object_entity_id_fkey: time=26.692 calls=5000
kb.entity: Trigger for constraint claim_statement_id_fkey: time=22.340 calls=5000
kb.entity: Execution Time: 132.510 ms
```

| rows | before | after |
|---|---|---|
| kb.entity | 5000 | 0 |
| kb.claim | 20000 | 0 |
| kb.claim_link | 0 | 0 |
| eval.alignment | 0 | 0 |
| eval.result | 0 | 0 |
| ops.task | 12500 | 12500 |
| ops.measurement | 0 | 0 |
| ops.run | 1 | 1 |
| kb.claim_evidence | 20000 | 0 |
| kb.entity_alias | 0 | 0 |

Kept run 1 unchanged: True. Outcome: passed.
