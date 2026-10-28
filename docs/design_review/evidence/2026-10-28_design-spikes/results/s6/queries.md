# S6 queries (D3 §9, D8 §5.3)

Run 1 of `cs_spike_s6` (S6-B rows: the four spike pages, twelve core units of the v1 reference). PostgreSQL 18.6, project-local cluster; times are client wall times (median of 7) on tables of tens to thousands of rows, so plans show what the planner chose at this size, not at run scale (S6-E).

Query texts come from `code/s6_queries_d3.sql`; the only correction applied is F1's `::regconfig` cast in the BM25 query's repeated predicate (`bm25.md`).

## D3 §9 patterns

### family_profile(normal)

D3 §9 block (`s.type = 'DistributionFamily'`); 1 rows; median 0.111 ms.

| c0 | c1 | c2 | c3 |
|---|---|---|---|
| stat:transformation_of | standard normal distribution |  | accepted |

```
Nested Loop Left Join (actual rows=1.00 loops=1)
  Buffers: shared hit=9
  ->  Hash Join (actual rows=1.00 loops=1)
        Hash Cond: (c.subject_id = s.id)
        Buffers: shared hit=7
        ->  Seq Scan on claim c (actual rows=71.00 loops=1)
              Filter: ((status = ANY ('{accepted,candidate}'::text[])) AND (run_id = '1'::smallint))
              Buffers: shared hit=5
        ->  Hash (actual rows=1.00 loops=1)
              Buckets: 1024  Batches: 1  Memory Usage: 9kB
              Buffers: shared hit=2
              ->  Seq Scan on entity s (actual rows=1.00 loops=1)
                    Filter: ((type = 'DistributionFamily'::text) AND (key = 'ent:b82780ee4a41fab164fb1d171450d35a'::text))
                    Rows Removed by Filter: 66
                    Buffers: shared hit=2
  ->  Index Scan using entity_pkey on entity o (actual rows=1.00 loops=1)
        Index Cond: (id = c.object_entity_id)
        Index Searches: 1
        Buffers: shared hit=2
Planning:
  Buffers: shared hit=4
Planning Time: 0.051 ms
Execution Time: 0.021 ms
```

### family_profile(lognormal)

D3 §9 block (`s.type = 'DistributionFamily'`); 4 rows; median 0.135 ms.

| c0 | c1 | c2 | c3 |
|---|---|---|---|
| stat:transformation_of | normal distribution |  | accepted |
| stat:has_parameter | mu |  | accepted |
| stat:has_parameter | sigma |  | accepted |
| stat:has_parameter | scale parameter |  | accepted |

```
Nested Loop Left Join (actual rows=4.00 loops=1)
  Buffers: shared hit=15
  ->  Hash Join (actual rows=4.00 loops=1)
        Hash Cond: (c.subject_id = s.id)
        Buffers: shared hit=7
        ->  Seq Scan on claim c (actual rows=71.00 loops=1)
              Filter: ((status = ANY ('{accepted,candidate}'::text[])) AND (run_id = '1'::smallint))
              Buffers: shared hit=5
        ->  Hash (actual rows=1.00 loops=1)
              Buckets: 1024  Batches: 1  Memory Usage: 9kB
              Buffers: shared hit=2
              ->  Seq Scan on entity s (actual rows=1.00 loops=1)
                    Filter: ((type = 'DistributionFamily'::text) AND (key = 'ent:3eebf26bd56404b7adb59446e36f6045'::text))
                    Rows Removed by Filter: 66
                    Buffers: shared hit=2
  ->  Index Scan using entity_pkey on entity o (actual rows=1.00 loops=4)
        Index Cond: (id = c.object_entity_id)
        Index Searches: 4
        Buffers: shared hit=8
Planning:
  Buffers: shared hit=4
Planning Time: 0.058 ms
Execution Time: 0.021 ms
```

### statement reconstruction (T3 theorem)

D3 §9 block (`c.statement_id = :statement_id`); 4 rows; median 0.072 ms.

| c0 | c1 | c2 | c3 |
|---|---|---|---|
| premise | stat:has_distribution | T3/c_X_normal | False |
| definiens | stat:defined_as | T3/c_aX_def | True |
| conclusion | stat:has_distribution | T3/c_aX_normal | True |
| conclusion | stat:has_distribution | T3/D1 (derived, D3 §10) | True |

```
Sort (actual rows=4.00 loops=1)
  Sort Key: (CASE statement_role WHEN 'premise'::text THEN 0 WHEN 'definiens'::text THEN 1 WHEN 'restriction'::text THEN 2 ELSE 3 END)
  Sort Method: quicksort  Memory: 29kB
  Buffers: shared hit=5
  ->  Seq Scan on claim c (actual rows=4.00 loops=1)
        Filter: ((run_id = '1'::smallint) AND (statement_id = '15'::smallint))
        Rows Removed by Filter: 67
        Buffers: shared hit=5
Planning Time: 0.012 ms
Execution Time: 0.008 ms
```

### statement reconstruction (T4 definition)

D3 §9 block (`c.statement_id = :statement_id`); 17 rows; median 0.076 ms.

| c0 | c1 | c2 | c3 |
|---|---|---|---|
| premise | stat:has_distribution | T4/c_Y_normal | False |
| premise | stat:has_distribution | T4/c_Z_stdnormal | False |
| definiens | stat:has_distribution | T4/c_X_lognormal | True |
| definiens | stat:transformation_of | T4/c_LN_transform | False |
| definiens | stat:has_parameter | T4/c_hp_mu | False |
| definiens | stat:has_parameter | T4/c_hp_sigma | False |
| definiens | stat:parameter_domain | T4/c_dom_mu | False |
| definiens | stat:parameter_domain | T4/c_dom_sigma | False |
| definiens | stat:parameter_role | T4/c_role_sigma | False |
| definiens | stat:has_parameter | T4/c_hp_scale | False |
| definiens | stat:derived_parameter | T4/c_scale_derived | False |
| definiens | stat:defined_as | T4/c_W_def | False |
| definiens | stat:has_distribution | T4/c_W_stdlognormal | True |
| definiens | stat:transformation_of | T4/c_SLN_transform | False |
| definiens | stat:defined_as | T4/c_X_def | False |
| None | core:defines | T4/c_defines_SLN | False |
| None | core:defines | T4/c_defines_LN | False |

```
Sort (actual rows=17.00 loops=1)
  Sort Key: (CASE statement_role WHEN 'premise'::text THEN 0 WHEN 'definiens'::text THEN 1 WHEN 'restriction'::text THEN 2 ELSE 3 END)
  Sort Method: quicksort  Memory: 29kB
  Buffers: shared hit=5
  ->  Seq Scan on claim c (actual rows=17.00 loops=1)
        Filter: ((run_id = '1'::smallint) AND (statement_id = '20'::smallint))
        Rows Removed by Filter: 54
        Buffers: shared hit=5
Planning Time: 0.012 ms
Execution Time: 0.009 ms
```

### claims with qualifier param_values.variance

D3 §9 block (`qualifiers @?`); 5 rows; median 0.034 ms.

| c0 |
|---|
| T3/c_X_normal |
| T3/c_aX_normal |
| U5/c_Xi_normal |
| U5/c_S_normal |
| U7/c_const_normal |

```
Seq Scan on claim (actual rows=5.00 loops=1)
  Filter: ((qualifiers @? '$."param_values"."variance"'::jsonpath) AND (run_id = '1'::smallint) AND (predicate = 'stat:has_distribution'::text))
  Rows Removed by Filter: 66
  Buffers: shared hit=5
Planning Time: 0.011 ms
Execution Time: 0.007 ms
```

### evidence for T3 C3

D3 §9 block (`FROM kb.claim_evidence ce`); 2 rows; median 0.083 ms.

| c0 | c1 | c2 | c3 | c4 | c5 |
|---|---|---|---|---|---|
| primary | \(a + b X\) is normally distributed with mean \(a + b \mu\)  | 14525 | 14614 | sentence | None |
| condition | If \(a \in \R\) and \(b \in \R \setminus \{0\}\) | 14470 | 14518 | sentence | None |

```
Nested Loop (actual rows=2.00 loops=1)
  Buffers: shared hit=9
  ->  Hash Join (actual rows=2.00 loops=1)
        Hash Cond: (sp.id = ce.span_id)
        Buffers: shared hit=3
        ->  Seq Scan on span sp (actual rows=87.00 loops=1)
              Buffers: shared hit=2
        ->  Hash (actual rows=2.00 loops=1)
              Buckets: 1024  Batches: 1  Memory Usage: 9kB
              Buffers: shared hit=1
              ->  Seq Scan on claim_evidence ce (actual rows=2.00 loops=1)
                    Filter: (claim_id = '14'::smallint)
                    Rows Removed by Filter: 104
                    Buffers: shared hit=1
  ->  Index Scan using segment_pkey on segment seg (actual rows=1.00 loops=2)
        Index Cond: (id = sp.segment_id)
        Index Searches: 2
        Buffers: shared hit=6
Planning:
  Buffers: shared hit=10
Planning Time: 0.042 ms
Execution Time: 0.013 ms
```

### evidence for U12 c_X_stdgamma (context premise, c1)

D3 §9 block (`FROM kb.claim_evidence ce`); 1 rows; median 0.076 ms.

| c0 | c1 | c2 | c3 | c4 | c5 |
|---|---|---|---|---|---|
| primary | \( X \) has the standard gamma distribution with shape param | 7103 | 7191 | sentence | None |

```
Nested Loop (actual rows=1.00 loops=1)
  Buffers: shared hit=6
  ->  Hash Join (actual rows=1.00 loops=1)
        Hash Cond: (sp.id = ce.span_id)
        Buffers: shared hit=3
        ->  Seq Scan on span sp (actual rows=87.00 loops=1)
              Buffers: shared hit=2
        ->  Hash (actual rows=1.00 loops=1)
              Buckets: 1024  Batches: 1  Memory Usage: 9kB
              Buffers: shared hit=1
              ->  Seq Scan on claim_evidence ce (actual rows=1.00 loops=1)
                    Filter: (claim_id = '67'::smallint)
                    Rows Removed by Filter: 105
                    Buffers: shared hit=1
  ->  Index Scan using segment_pkey on segment seg (actual rows=1.00 loops=1)
        Index Cond: (id = sp.segment_id)
        Index Searches: 1
        Buffers: shared hit=3
Planning:
  Buffers: shared hit=10
Planning Time: 0.041 ms
Execution Time: 0.011 ms
```

### coverage of the four pages

D3 §9 block (`CROSS JOIN LATERAL`); 1 rows; median 0.36 ms.

| c0 | c1 | c2 |
|---|---|---|
| done | None | 12 |

```
GroupAggregate (actual rows=1.00 loops=1)
  Group Key: (CASE WHEN (t.finished_at <= r.finished_at) THEN t.status ELSE 'unresolved'::text END), (CASE WHEN (t.finished_at <= r.finished_at) THEN t.reason ELSE NULL::text END)
  Buffers: shared hit=192
  ->  Sort (actual rows=12.00 loops=1)
        Sort Key: (CASE WHEN (t.finished_at <= r.finished_at) THEN t.status ELSE 'unresolved'::text END), (CASE WHEN (t.finished_at <= r.finished_at) THEN t.reason ELSE NULL::text END), t.unit_key
        Sort Method: quicksort  Memory: 25kB
        Buffers: shared hit=192
        ->  Nested Loop (actual rows=12.00 loops=1)
              Join Filter: ((b.document_id = t_1.unit_id) AND (b.method_config_id = t_1.method_config_id))
              Rows Removed by Join Filter: 36
              Buffers: shared hit=192
              ->  Nested Loop (actual rows=48.00 loops=1)
                    Buffers: shared hit=96
                    ->  Nested Loop (actual rows=12.00 loops=1)
                          Buffers: shared hit=60
                          ->  Nested Loop (actual rows=12.00 loops=1)
                                Buffers: shared hit=4
                                ->  Seq Scan on run r (actual rows=1.00 loops=1)
                                      Filter: (id = '1'::smallint)
                                      Rows Removed by Filter: 2
                                      Buffers: shared hit=1
                                ->  Seq Scan on task t (actual rows=12.00 loops=1)
                                      Filter: ((run_id = '1'::smallint) AND (stage = 'propose'::text) AND (unit_type = 'segment'::text))
                                      Rows Removed by Filter: 47
                                      Buffers: shared hit=3
                          ->  Index Scan using segment_pkey on segment s (actual rows=1.00 loops=12)
                                Index Cond: (id = t.unit_id)
                                Index Searches: 12
                                Buffers: shared hit=46
                    ->  Seq Scan on task t_1 (actual rows=4.00 loops=12)
                          Filter: ((status = ANY ('{done,reused}'::text[])) AND (run_id = '1'::smallint) AND (stage = 'ingest'::text) AND (unit_type = 'document'::text))
                          Rows Removed by Filter: 55
                          Buffers: shared hit=36
              ->  Index Scan using rendition_build_rendition on rendition_build b (actual rows=1.00 loops=48)
                    Index Cond: (rendition_id = s.rendition_id)
                    Filter: (document_id = ANY ('{1,2,3,4}'::smallint[]))
                    Index Searches: 48
                    Buffers: shared hit=96
Planning:
  Buffers: shared hit=17
Planning Time: 0.170 ms
Execution Time: 0.111 ms
```

### why a method ran (T3's unit)

D3 §9 block (`LEFT JOIN ops.policy_rule pr`); 2 rows; median 0.127 ms.

| c0 | c1 | c2 | c3 | c4 | c5 |
|---|---|---|---|---|---|
| propose | agent.opus | None | {} | done | {"model": "reference_v1", "wall_ms": 1} |
| escalate | agent.opus | escalate.low_confidence.agent | {"claims.min_confidence": 0.4} | done | {"wall_ms": 2, "tokens_in": 1200, "tokens_out": 300} |

```
Sort (actual rows=2.00 loops=1)
  Sort Key: t.id
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=6
  ->  Nested Loop Left Join (actual rows=2.00 loops=1)
        Join Filter: (pr.id = t.trigger_rule_id)
        Rows Removed by Join Filter: 1
        Buffers: shared hit=6
        ->  Hash Join (actual rows=2.00 loops=1)
              Hash Cond: (mc.method_id = m.id)
              Buffers: shared hit=5
              ->  Hash Join (actual rows=2.00 loops=1)
                    Hash Cond: (t.method_config_id = mc.id)
                    Buffers: shared hit=4
                    ->  Seq Scan on task t (actual rows=2.00 loops=1)
                          Filter: ((run_id = '1'::smallint) AND (unit_key = 'unit:5b96a7b488ae9dd5e0f664a95657c10c'::text))
                          Rows Removed by Filter: 57
                          Buffers: shared hit=3
                    ->  Hash (actual rows=8.00 loops=1)
                          Buckets: 1024  Batches: 1  Memory Usage: 9kB
                          Buffers: shared hit=1
                          ->  Seq Scan on method_config mc (actual rows=8.00 loops=1)
                                Buffers: shared hit=1
              ->  Hash (actual rows=6.00 loops=1)
                    Buckets: 1024  Batches: 1  Memory Usage: 9kB
                    Buffers: shared hit=1
                    ->  Seq Scan on method m (actual rows=6.00 loops=1)
                          Buffers: shared hit=1
        ->  Materialize (actual rows=1.00 loops=2)
              Storage: Memory  Maximum Storage: 17kB
              Buffers: shared hit=1
              ->  Seq Scan on policy_rule pr (actual rows=1.00 loops=1)
                    Buffers: shared hit=1
Planning:
  Buffers: shared hit=9
Planning Time: 0.053 ms
Execution Time: 0.016 ms
```

### The `@?` qualifier query and `claim_pred`

With `enable_seqscan = off` (tables are small, so the chosen plan may be a scan):

```
Bitmap Heap Scan on claim (actual rows=5.00 loops=1)
  Recheck Cond: ((run_id = '1'::smallint) AND (predicate = 'stat:has_distribution'::text))
  Filter: (qualifiers @? '$."param_values"."variance"'::jsonpath)
  Rows Removed by Filter: 17
  Heap Blocks: exact=5
  Buffers: shared hit=9
  ->  Bitmap Index Scan on claim_pred (actual rows=22.00 loops=1)
        Index Cond: ((run_id = '1'::smallint) AND (predicate = 'stat:has_distribution'::text))
        Index Searches: 1
        Buffers: shared hit=4
Planning Time: 0.048 ms
Execution Time: 0.031 ms
```

`claim_pred` carries it: True (index condition on `run_id, predicate`; the `@?` path test is a filter on the fetched rows).

## D8 §5.3 trace questions in SQL

Each query is a SQL sketch of the typed query over the D3 patterns, run on run 1 (all twelve core units of the v1 reference). Rows are shown as `unit/local_ref` with the trace C-ref where the row is a trace unit's target claim. The default filters (status `accepted`; modality not `supposed` unless `include_suppositions`, D8 §5) are shown as a column, not applied, so the comparison is visible.

### T1 · `statement(LocationScale#dfn1)`

Expected (D8 §5.3): Statement S1 (definition) with C2 (definiens, conditions), C3, C4–C8; C1 only with include_suppositions.

7 rows; median 1.184 ms. Trace refs returned: C2, C4, C5, C6, C7, C8, C3. Missing from the expected: none. Rows beyond the expected: none.

| row | unit/local_ref | trace |
|---|---|---|
| definition, definiens, stat:defined_as, defined, True, 2 | T1/c_X_def | C2 |
| definition, definiens, stat:construction_formula, defined, True, 3 | T1/c_constr | C4 |
| definition, definiens, stat:has_parameter, defined, False, 1 | T1/c_hp_loc | C5 |
| definition, definiens, stat:has_parameter, defined, False, 1 | T1/c_hp_scale | C6 |
| definition, definiens, stat:parameter_domain, defined, False, 1 | T1/c_dom_loc | C7 |
| definition, definiens, stat:parameter_domain, defined, False, 1 | T1/c_dom_scale | C8 |
| definition, None, core:defines, asserted, False, 1 | T1/c_defines | C3 |

```
Sort (actual rows=7.00 loops=1)
  Sort Key: st.kind, (CASE c.statement_role WHEN 'premise'::text THEN 0 WHEN 'definiens'::text THEN 1 WHEN 'restriction'::text THEN 2 ELSE 3 END), c.id
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=489
  ->  Hash Join (actual rows=7.00 loops=1)
        Hash Cond: (c.statement_id = st.id)
        Buffers: shared hit=489
        ->  Seq Scan on claim c (actual rows=71.00 loops=1)
              Filter: ((run_id = '1'::smallint) AND (status = 'accepted'::text))
              Buffers: shared hit=5
        ->  Hash (actual rows=1.00 loops=1)
              Buckets: 1024  Batches: 1  Memory Usage: 9kB
              Buffers: shared hit=477
              ->  Subquery Scan on st (actual rows=1.00 loops=1)
                    Buffers: shared hit=477
                    ->  Unique (actual rows=1.00 loops=1)
                          Buffers: shared hit=477
                          ->  Sort (actual rows=3.00 loops=1)
                                Sort Key: e.id, e.kind
                                Sort Method: quicksort  Memory: 25kB
                                Buffers: shared hit=477
                                ->  Nested Loop (actual rows=3.00 loops=1)
                                      Join Filter: (b.rendition_id = seg.rendition_id)
                                      Buffers: shared hit=477
                                      ->  Nested Loop (actual rows=6.00 loops=1)
                                            Join Filter: ((b.document_id = t.unit_id) AND (b.method_config_id = t.method_config_id))
                                            Rows Removed by Join Filter: 40
                                            Buffers: shared hit=315
                                            ->  Nested Loop (actual rows=46.00 loops=1)
                                                  Buffers: shared hit=223
                                                  ->  Nested Loop (actual rows=46.00 loops=1)
                                                        Buffers: shared hit=51
                                                        ->  Nested Loop (actual rows=21.00 loops=1)
                                                              Buffers: shared hit=9
                                                              ->  Nested Loop (actual rows=1.00 loops=1)
                                                                    Join Filter: (d.id = t.unit_id)
                                                                    Rows Removed by Join Filter: 3
                                                                    Buffers: shared hit=7
                                                                    ->  Seq Scan on task t (actual rows=4.00 loops=1)
                                                                          Filter: ((status = ANY ('{done,reused}'::text[])) AND (stage = 'ingest'::text) AND (unit_type = 'document'::text) AND (run_id = '1'::smallint))
                                                                          Rows Removed by Filter: 55
                                                                          Buffers: shared hit=3
                                                                    ->  Seq Scan on document d (actual rows=1.00 loops=4)
                                                                          Filter: (source_uri = 'siegrist_random/random/special/LocationScale.html'::text)
                                                                          Rows Removed by Filter: 3
                                                                          Buffers: shared hit=4
                                                              ->  Seq Scan on entity e (actual rows=21.00 loops=1)
                                                                    Filter: ((run_id = '1'::smallint) AND (type = 'Statement'::text))
                                                                    Rows Removed by Filter: 46
                                                                    Buffers: shared hit=2
                                                        ->  Index Only Scan using entity_anchor_pkey on entity_anchor a (actual rows=2.19 loops=21)
                                                              Index Cond: (entity_id = e.id)
                                                              Heap Fetches: 46
                                                              Index Searches: 21
                                                              Buffers: shared hit=42
                                                  ->  Index Scan using segment_pkey on segment s (actual rows=1.00 loops=46)
                                                        Index Cond: (id = a.segment_id)
                                                        Index Searches: 46
                                                        Buffers: shared hit=155
                                            ->  Index Scan using rendition_build_rendition on rendition_build b (actual rows=1.00 loops=46)
                                                  Index Cond: (rendition_id = s.rendition_id)
                                                  Index Searches: 46
                                                  Buffers: shared hit=92
                                      ->  Index Scan using segment_kind on segment seg (actual rows=0.50 loops=6)
                                            Index Cond: ((rendition_id = s.rendition_id) AND (kind = 'unit'::text))
                                            Filter: ((s.start_offset >= start_offset) AND (s.end_offset <= end_offset) AND ((attrs ->> 'id'::text) = 'dfn1'::text))
                                            Rows Removed by Filter: 34
                                            Index Searches: 6
                                            Buffers: shared hit=162
        SubPlan 1
          ->  Aggregate (actual rows=1.00 loops=7)
                Buffers: shared hit=7
                ->  Seq Scan on claim_evidence ce (actual rows=1.43 loops=7)
                      Filter: (claim_id = c.id)
                      Rows Removed by Filter: 105
                      Buffers: shared hit=7
Planning:
  Buffers: shared hit=41
Planning Time: 0.848 ms
Execution Time: 0.189 ms
```

### T1 · `construction_profile(location-scale family)`

Expected (D8 §5.3): C4 with base variable Z and parameter symbols; parameters location and scale (C5, C6) with domains (C7, C8).

5 rows; median 0.301 ms. Trace refs returned: C4, C5, C6, C7, C8. Missing from the expected: none. Rows beyond the expected: none.

| row | unit/local_ref | trace |
|---|---|---|
| family, stat:construction_formula, None, defined | T1/c_constr | C4 |
| family, stat:has_parameter, location parameter, defined | T1/c_hp_loc | C5 |
| family, stat:has_parameter, scale parameter, defined | T1/c_hp_scale | C6 |
| parameter location parameter, stat:parameter_domain, None, defined | T1/c_dom_loc | C7 |
| parameter scale parameter, stat:parameter_domain, None, defined | T1/c_dom_scale | C8 |

FamilyParameter entities whose identity names it: location parameter (location); scale parameter (scale)

```
Sort (actual rows=5.00 loops=1)
  Sort Key: ('family'::text), c.id
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=18
  ->  Append (actual rows=5.00 loops=1)
        Buffers: shared hit=18
        ->  Nested Loop Left Join (actual rows=3.00 loops=1)
              Buffers: shared hit=11
              ->  Hash Join (actual rows=3.00 loops=1)
                    Hash Cond: (c.subject_id = s.id)
                    Buffers: shared hit=7
                    ->  Seq Scan on claim c (actual rows=71.00 loops=1)
                          Filter: ((status = ANY ('{accepted,candidate}'::text[])) AND (run_id = '1'::smallint))
                          Buffers: shared hit=5
                    ->  Hash (actual rows=1.00 loops=1)
                          Buckets: 1024  Batches: 1  Memory Usage: 9kB
                          Buffers: shared hit=2
                          ->  Seq Scan on entity s (actual rows=1.00 loops=1)
                                Filter: (key = 'ent:e4348a6c8f312a5c5fe4069456a6a2d3'::text)
                                Rows Removed by Filter: 66
                                Buffers: shared hit=2
              ->  Index Scan using entity_pkey on entity o (actual rows=0.67 loops=3)
                    Index Cond: (id = c.object_entity_id)
                    Index Searches: 2
                    Buffers: shared hit=4
        ->  Nested Loop Left Join (actual rows=2.00 loops=1)
              Buffers: shared hit=7
              ->  Hash Join (actual rows=2.00 loops=1)
                    Hash Cond: (c_1.subject_id = p.id)
                    Buffers: shared hit=7
                    ->  Seq Scan on claim c_1 (actual rows=71.00 loops=1)
                          Filter: ((status = ANY ('{accepted,candidate}'::text[])) AND (run_id = '1'::smallint))
                          Buffers: shared hit=5
                    ->  Hash (actual rows=2.00 loops=1)
                          Buckets: 1024  Batches: 1  Memory Usage: 9kB
                          Buffers: shared hit=2
                          ->  Seq Scan on entity p (actual rows=2.00 loops=1)
                                Filter: ((run_id = '1'::smallint) AND (type = 'FamilyParameter'::text) AND ((attrs ->> 'family'::text) = 'ent:e4348a6c8f312a5c5fe4069456a6a2d3'::text))
                                Rows Removed by Filter: 65
                                Buffers: shared hit=2
              ->  Index Scan using entity_pkey on entity o_1 (actual rows=0.00 loops=2)
                    Index Cond: (id = c_1.object_entity_id)
                    Index Searches: 0
Planning:
  Buffers: shared hit=8
Planning Time: 0.155 ms
Execution Time: 0.058 ms
```

### T2 · `family_profile(normal)`

Expected (D8 §5.3): Parameters location and scale (FamilyParameter entities whose identity names the family), identical to mean and sd (C4, C5); no has_parameter claim; C1 only with include_suppositions.

3 rows; median 0.285 ms. Trace refs returned: C4, C5. Missing from the expected: none. Rows beyond the expected: U6/c_normal_from_std.

| row | unit/local_ref | trace |
|---|---|---|
| family, stat:transformation_of, standard normal distribution, asserted | U6/c_normal_from_std |  |
| parameter location parameter of the normal distribution, stat:identical_parameter, mean of the normal distribution, asserted | T2/c_loc_is_mean | C4 |
| parameter scale parameter of the normal distribution, stat:identical_parameter, standard deviation of the normal distribution, asserted | T2/c_scale_is_sd | C5 |

FamilyParameter entities whose identity names it: location parameter of the normal distribution (location); mean of the normal distribution (mean); scale parameter of the normal distribution (scale); standard deviation of the normal distribution (standard_deviation)

```
Sort (actual rows=3.00 loops=1)
  Sort Key: ('family'::text), c.id
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=20
  ->  Append (actual rows=3.00 loops=1)
        Buffers: shared hit=20
        ->  Nested Loop Left Join (actual rows=1.00 loops=1)
              Buffers: shared hit=9
              ->  Hash Join (actual rows=1.00 loops=1)
                    Hash Cond: (c.subject_id = s.id)
                    Buffers: shared hit=7
                    ->  Seq Scan on claim c (actual rows=71.00 loops=1)
                          Filter: ((status = ANY ('{accepted,candidate}'::text[])) AND (run_id = '1'::smallint))
                          Buffers: shared hit=5
                    ->  Hash (actual rows=1.00 loops=1)
                          Buckets: 1024  Batches: 1  Memory Usage: 9kB
                          Buffers: shared hit=2
                          ->  Seq Scan on entity s (actual rows=1.00 loops=1)
                                Filter: (key = 'ent:b82780ee4a41fab164fb1d171450d35a'::text)
                                Rows Removed by Filter: 66
                                Buffers: shared hit=2
              ->  Index Scan using entity_pkey on entity o (actual rows=1.00 loops=1)
                    Index Cond: (id = c.object_entity_id)
                    Index Searches: 1
                    Buffers: shared hit=2
        ->  Nested Loop Left Join (actual rows=2.00 loops=1)
              Buffers: shared hit=11
              ->  Hash Join (actual rows=2.00 loops=1)
                    Hash Cond: (c_1.subject_id = p.id)
                    Buffers: shared hit=7
                    ->  Seq Scan on claim c_1 (actual rows=71.00 loops=1)
                          Filter: ((status = ANY ('{accepted,candidate}'::text[])) AND (run_id = '1'::smallint))
                          Buffers: shared hit=5
                    ->  Hash (actual rows=4.00 loops=1)
                          Buckets: 1024  Batches: 1  Memory Usage: 9kB
                          Buffers: shared hit=2
                          ->  Seq Scan on entity p (actual rows=4.00 loops=1)
                                Filter: ((run_id = '1'::smallint) AND (type = 'FamilyParameter'::text) AND ((attrs ->> 'family'::text) = 'ent:b82780ee4a41fab164fb1d171450d35a'::text))
                                Rows Removed by Filter: 63
                                Buffers: shared hit=2
              ->  Index Scan using entity_pkey on entity o_1 (actual rows=1.00 loops=2)
                    Index Cond: (id = c_1.object_entity_id)
                    Index Searches: 2
                    Buffers: shared hit=4
Planning:
  Buffers: shared hit=8
Planning Time: 0.155 ms
Execution Time: 0.045 ms
```

### T3 · `transformations_of(normal)`

Expected (D8 §5.3): C3 with conditions a ∈ ℝ, b ∈ ℝ∖{0} and premise C1, and C2 defining Y under the same restrictions; D1 from phase 2.

9 rows; median 0.431 ms. Trace refs returned: C1, C2, C3. Missing from the expected: none. Rows beyond the expected: U5/c_Xi_normal, U5/c_S_def, U5/c_S_normal, U5/c_S_mean, U5/c_S_var, T3/D1 (derived, D3 §10).

| row | unit/local_ref | trace |
|---|---|---|
| premise, stat:has_distribution, stated, supposed, None | T3/c_X_normal | C1 |
| premise, stat:has_distribution, stated, supposed, ['i', '\\{1, 2\\}'] | U5/c_Xi_normal |  |
| definiens, stat:defined_as, stated, defined, ['a', '\\R', 'b', '\\R \\setminus \\{0\\}'] | T3/c_aX_def | C2 |
| definiens, stat:defined_as, stated, defined, None | U5/c_S_def |  |
| conclusion, stat:has_distribution, stated, asserted, ['a', '\\R', 'b', '\\R \\setminus \\{0\\}'] | T3/c_aX_normal | C3 |
| conclusion, stat:has_distribution, stated, asserted, [] | U5/c_S_normal |  |
| conclusion, stat:mean_value, stated, asserted, [] | U5/c_S_mean |  |
| conclusion, stat:variance_value, stated, asserted, [] | U5/c_S_var |  |
| conclusion, stat:has_distribution, derived, asserted, ['a', '\\R', 'b', '\\R \\setminus \\{0\\}'] | T3/D1 (derived, D3 §10) |  |

FamilyParameter entities whose identity names it: location parameter of the normal distribution (location); mean of the normal distribution (mean); scale parameter of the normal distribution (scale); standard deviation of the normal distribution (standard_deviation)

```
Sort (actual rows=9.00 loops=1)
  Sort Key: (CASE c.statement_role WHEN 'premise'::text THEN 0 WHEN 'definiens'::text THEN 1 ELSE 2 END), c.id
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=27
  CTE concl
    ->  Nested Loop (actual rows=3.00 loops=1)
          Join Filter: (c_1.statement_id = c_2.statement_id)
          Buffers: shared hit=22
          ->  Nested Loop (actual rows=4.00 loops=1)
                Join Filter: (d.statement_id = c_2.statement_id)
                Rows Removed by Join Filter: 41
                Buffers: shared hit=12
                ->  Unique (actual rows=5.00 loops=1)
                      Buffers: shared hit=7
                      ->  Sort (actual rows=5.00 loops=1)
                            Sort Key: c_2.statement_id
                            Sort Method: quicksort  Memory: 25kB
                            Buffers: shared hit=7
                            ->  Nested Loop (actual rows=5.00 loops=1)
                                  Join Filter: (c_2.object_entity_id = o.id)
                                  Rows Removed by Join Filter: 5
                                  Buffers: shared hit=7
                                  ->  Seq Scan on entity o (actual rows=1.00 loops=1)
                                        Filter: (key = 'ent:b82780ee4a41fab164fb1d171450d35a'::text)
                                        Rows Removed by Filter: 66
                                        Buffers: shared hit=2
                                  ->  Seq Scan on claim c_2 (actual rows=10.00 loops=1)
                                        Filter: ((run_id = '1'::smallint) AND (predicate = 'stat:has_distribution'::text) AND (statement_role = 'premise'::text))
                                        Rows Removed by Filter: 61
                                        Buffers: shared hit=5
                ->  HashAggregate (actual rows=9.00 loops=5)
                      Group Key: d.statement_id, d.subject_id
                      Batches: 1  Memory Usage: 32kB
                      Buffers: shared hit=5
                      ->  Seq Scan on claim d (actual rows=9.00 loops=1)
                            Filter: ((run_id = '1'::smallint) AND (predicate = 'stat:defined_as'::text))
                            Rows Removed by Filter: 62
                            Buffers: shared hit=5
          ->  Index Scan using claim_subject on claim c_1 (actual rows=0.75 loops=4)
                Index Cond: ((run_id = '1'::smallint) AND (subject_id = d.subject_id))
                Filter: ((statement_role = 'conclusion'::text) AND (predicate = 'stat:has_distribution'::text) AND (statement_id = d.statement_id))
                Rows Removed by Filter: 2
                Index Searches: 4
                Buffers: shared hit=10
  ->  Hash Semi Join (actual rows=9.00 loops=1)
        Hash Cond: (c.statement_id = concl.statement_id)
        Buffers: shared hit=27
        ->  Seq Scan on claim c (actual rows=19.00 loops=1)
              Filter: ((run_id = '1'::smallint) AND ((ANY (subject_id = (hashed SubPlan 2).col1)) OR (statement_role = 'premise'::text)))
              Rows Removed by Filter: 52
              Buffers: shared hit=5
              SubPlan 2
                ->  CTE Scan on concl concl_1 (actual rows=3.00 loops=1)
                      Storage: Memory  Maximum Storage: 17kB
        ->  Hash (actual rows=3.00 loops=1)
              Buckets: 1024  Batches: 1  Memory Usage: 9kB
              Buffers: shared hit=22
              ->  CTE Scan on concl (actual rows=3.00 loops=1)
                    Storage: Memory  Maximum Storage: 17kB
                    Buffers: shared hit=22
Planning Time: 0.211 ms
Execution Time: 0.075 ms
```

### T4 · `statement(LogNormal#dfn)`

Expected (D8 §5.3): C1–C17 in the statement (with the standard lognormal, C13–C17).

17 rows; median 1.192 ms. Trace refs returned: C1, C13, C2, C3, C7, C5, C6, C11, C12, C8, C9, C10, C14, C15, C17, C4, C16. Missing from the expected: none. Rows beyond the expected: none.

| row | unit/local_ref | trace |
|---|---|---|
| definition, premise, stat:has_distribution, supposed, False, 1 | T4/c_Y_normal | C1 |
| definition, premise, stat:has_distribution, supposed, False, 1 | T4/c_Z_stdnormal | C13 |
| definition, definiens, stat:defined_as, defined, False, 1 | T4/c_X_def | C2 |
| definition, definiens, stat:has_distribution, defined, True, 3 | T4/c_X_lognormal | C3 |
| definition, definiens, stat:transformation_of, defined, False, 2 | T4/c_LN_transform | C7 |
| definition, definiens, stat:has_parameter, defined, False, 1 | T4/c_hp_mu | C5 |
| definition, definiens, stat:has_parameter, defined, False, 1 | T4/c_hp_sigma | C6 |
| definition, definiens, stat:parameter_domain, defined, False, 1 | T4/c_dom_mu | C11 |
| definition, definiens, stat:parameter_domain, defined, False, 1 | T4/c_dom_sigma | C12 |
| definition, definiens, stat:parameter_role, defined, False, 1 | T4/c_role_sigma | C8 |
| definition, definiens, stat:has_parameter, defined, False, 1 | T4/c_hp_scale | C9 |
| definition, definiens, stat:derived_parameter, defined, False, 1 | T4/c_scale_derived | C10 |
| definition, definiens, stat:defined_as, defined, False, 1 | T4/c_W_def | C14 |
| definition, definiens, stat:has_distribution, defined, True, 2 | T4/c_W_stdlognormal | C15 |
| definition, definiens, stat:transformation_of, defined, False, 1 | T4/c_SLN_transform | C17 |
| definition, None, core:defines, asserted, False, 1 | T4/c_defines_LN | C4 |
| definition, None, core:defines, asserted, False, 1 | T4/c_defines_SLN | C16 |

```
Sort (actual rows=17.00 loops=1)
  Sort Key: st.kind, (CASE c.statement_role WHEN 'premise'::text THEN 0 WHEN 'definiens'::text THEN 1 WHEN 'restriction'::text THEN 2 ELSE 3 END), c.id
  Sort Method: quicksort  Memory: 26kB
  Buffers: shared hit=499
  ->  Hash Join (actual rows=17.00 loops=1)
        Hash Cond: (c.statement_id = st.id)
        Buffers: shared hit=499
        ->  Seq Scan on claim c (actual rows=71.00 loops=1)
              Filter: ((run_id = '1'::smallint) AND (status = 'accepted'::text))
              Buffers: shared hit=5
        ->  Hash (actual rows=1.00 loops=1)
              Buckets: 1024  Batches: 1  Memory Usage: 9kB
              Buffers: shared hit=477
              ->  Subquery Scan on st (actual rows=1.00 loops=1)
                    Buffers: shared hit=477
                    ->  Unique (actual rows=1.00 loops=1)
                          Buffers: shared hit=477
                          ->  Sort (actual rows=1.00 loops=1)
                                Sort Key: e.id, e.kind
                                Sort Method: quicksort  Memory: 25kB
                                Buffers: shared hit=477
                                ->  Nested Loop (actual rows=1.00 loops=1)
                                      Join Filter: (b.rendition_id = seg.rendition_id)
                                      Buffers: shared hit=477
                                      ->  Nested Loop (actual rows=6.00 loops=1)
                                            Join Filter: ((b.document_id = t.unit_id) AND (b.method_config_id = t.method_config_id))
                                            Rows Removed by Join Filter: 40
                                            Buffers: shared hit=315
                                            ->  Nested Loop (actual rows=46.00 loops=1)
                                                  Buffers: shared hit=223
                                                  ->  Nested Loop (actual rows=46.00 loops=1)
                                                        Buffers: shared hit=51
                                                        ->  Nested Loop (actual rows=21.00 loops=1)
                                                              Buffers: shared hit=9
                                                              ->  Nested Loop (actual rows=1.00 loops=1)
                                                                    Join Filter: (d.id = t.unit_id)
                                                                    Rows Removed by Join Filter: 3
                                                                    Buffers: shared hit=7
                                                                    ->  Seq Scan on task t (actual rows=4.00 loops=1)
                                                                          Filter: ((status = ANY ('{done,reused}'::text[])) AND (stage = 'ingest'::text) AND (unit_type = 'document'::text) AND (run_id = '1'::smallint))
                                                                          Rows Removed by Filter: 55
                                                                          Buffers: shared hit=3
                                                                    ->  Seq Scan on document d (actual rows=1.00 loops=4)
                                                                          Filter: (source_uri = 'siegrist_random/random/special/LogNormal.html'::text)
                                                                          Rows Removed by Filter: 4
                                                                          Buffers: shared hit=4
                                                              ->  Seq Scan on entity e (actual rows=21.00 loops=1)
                                                                    Filter: ((run_id = '1'::smallint) AND (type = 'Statement'::text))
                                                                    Rows Removed by Filter: 46
                                                                    Buffers: shared hit=2
                                                        ->  Index Only Scan using entity_anchor_pkey on entity_anchor a (actual rows=2.19 loops=21)
                                                              Index Cond: (entity_id = e.id)
                                                              Heap Fetches: 46
                                                              Index Searches: 21
                                                              Buffers: shared hit=42
                                                  ->  Index Scan using segment_pkey on segment s (actual rows=1.00 loops=46)
                                                        Index Cond: (id = a.segment_id)
                                                        Index Searches: 46
                                                        Buffers: shared hit=155
                                            ->  Index Scan using rendition_build_rendition on rendition_build b (actual rows=1.00 loops=46)
                                                  Index Cond: (rendition_id = s.rendition_id)
                                                  Index Searches: 46
                                                  Buffers: shared hit=92
                                      ->  Index Scan using segment_kind on segment seg (actual rows=0.17 loops=6)
                                            Index Cond: ((rendition_id = s.rendition_id) AND (kind = 'unit'::text))
                                            Filter: ((s.start_offset >= start_offset) AND (s.end_offset <= end_offset) AND ((attrs ->> 'id'::text) = 'dfn'::text))
                                            Rows Removed by Filter: 19
                                            Index Searches: 6
                                            Buffers: shared hit=162
        SubPlan 1
          ->  Aggregate (actual rows=1.00 loops=17)
                Buffers: shared hit=17
                ->  Seq Scan on claim_evidence ce (actual rows=1.24 loops=17)
                      Filter: (claim_id = c.id)
                      Rows Removed by Filter: 105
                      Buffers: shared hit=17
Planning:
  Buffers: shared hit=41
Planning Time: 0.846 ms
Execution Time: 0.199 ms
```

### T4 · `family_profile(lognormal)`

Expected (D8 §5.3): parameters mu, sigma and scale (C5, C6, C9) with domains (C11, C12), sigma's role shape (C8), scale = e^μ (C10), transformation of normal (C7).

8 rows; median 0.309 ms. Trace refs returned: C7, C5, C6, C9, C11, C10, C12, C8. Missing from the expected: none. Rows beyond the expected: none.

| row | unit/local_ref | trace |
|---|---|---|
| family, stat:transformation_of, normal distribution, defined | T4/c_LN_transform | C7 |
| family, stat:has_parameter, mu, defined | T4/c_hp_mu | C5 |
| family, stat:has_parameter, sigma, defined | T4/c_hp_sigma | C6 |
| family, stat:has_parameter, scale parameter, defined | T4/c_hp_scale | C9 |
| parameter mu, stat:parameter_domain, None, defined | T4/c_dom_mu | C11 |
| parameter scale parameter, stat:derived_parameter, None, defined | T4/c_scale_derived | C10 |
| parameter sigma, stat:parameter_domain, None, defined | T4/c_dom_sigma | C12 |
| parameter sigma, stat:parameter_role, None, defined | T4/c_role_sigma | C8 |

FamilyParameter entities whose identity names it: mu (mu); scale parameter (scale); sigma (sigma)

```
Sort (actual rows=8.00 loops=1)
  Sort Key: ('family'::text), c.id
  Sort Method: quicksort  Memory: 25kB
  Buffers: shared hit=22
  ->  Append (actual rows=8.00 loops=1)
        Buffers: shared hit=22
        ->  Nested Loop Left Join (actual rows=4.00 loops=1)
              Buffers: shared hit=15
              ->  Hash Join (actual rows=4.00 loops=1)
                    Hash Cond: (c.subject_id = s.id)
                    Buffers: shared hit=7
                    ->  Seq Scan on claim c (actual rows=71.00 loops=1)
                          Filter: ((status = ANY ('{accepted,candidate}'::text[])) AND (run_id = '1'::smallint))
                          Buffers: shared hit=5
                    ->  Hash (actual rows=1.00 loops=1)
                          Buckets: 1024  Batches: 1  Memory Usage: 9kB
                          Buffers: shared hit=2
                          ->  Seq Scan on entity s (actual rows=1.00 loops=1)
                                Filter: (key = 'ent:3eebf26bd56404b7adb59446e36f6045'::text)
                                Rows Removed by Filter: 66
                                Buffers: shared hit=2
              ->  Index Scan using entity_pkey on entity o (actual rows=1.00 loops=4)
                    Index Cond: (id = c.object_entity_id)
                    Index Searches: 4
                    Buffers: shared hit=8
        ->  Nested Loop Left Join (actual rows=4.00 loops=1)
              Buffers: shared hit=7
              ->  Hash Join (actual rows=4.00 loops=1)
                    Hash Cond: (c_1.subject_id = p.id)
                    Buffers: shared hit=7
                    ->  Seq Scan on claim c_1 (actual rows=71.00 loops=1)
                          Filter: ((status = ANY ('{accepted,candidate}'::text[])) AND (run_id = '1'::smallint))
                          Buffers: shared hit=5
                    ->  Hash (actual rows=3.00 loops=1)
                          Buckets: 1024  Batches: 1  Memory Usage: 9kB
                          Buffers: shared hit=2
                          ->  Seq Scan on entity p (actual rows=3.00 loops=1)
                                Filter: ((run_id = '1'::smallint) AND (type = 'FamilyParameter'::text) AND ((attrs ->> 'family'::text) = 'ent:3eebf26bd56404b7adb59446e36f6045'::text))
                                Rows Removed by Filter: 64
                                Buffers: shared hit=2
              ->  Index Scan using entity_pkey on entity o_1 (actual rows=0.00 loops=4)
                    Index Cond: (id = c_1.object_entity_id)
                    Index Searches: 0
Planning:
  Buffers: shared hit=8
Planning Time: 0.147 ms
Execution Time: 0.046 ms
```

## Differences and observations (2026-10-28)

- **D8 §5.3 against the v1 rows:** every trace question returns all its expected trace claims (missing: none in all six). Rows beyond the expectation come from other core units in the same run (U6's `transformation_of` for the normal family; U5's sum theorem under `transformations_of(normal)`) and from the derived D1 the loader adds as D3 §10 describes; D8 expects D1 only from phase 2.
- **`family_profile` needs the parameter branch.** D3 §9's pattern (claims whose subject is the family) returns 1 row for the normal family; T2's answer (C4, C5) lives on `FamilyParameter` entities whose identity names the family, reached here through `kb.entity.attrs ->> 'family'` (the identity attribute stored as the family's entity key). D3 §9 should carry that branch; with no index on `attrs` it is a filter over the run's `FamilyParameter` rows (`entity_type`).
- **`statement(LocationScale#dfn1)`** resolves to the unit's statements only: the T1 assumption (C1) sits in the lead-in paragraph, outside unit `dfn1`, so no option of a unit-locator query reaches it; D8's "C1 only with include_suppositions" needs the composite locator (lead-in paragraph + unit) the sample uses, or the premise-through-conditions rule.
- **Evidence `unit_id` is null** for spans whose smallest containing segment is a `sentence` or `math_inline` (every row here): D3 §9's `seg.attrs ->> 'id' AS unit_id` reads the span's own segment; the unit needs an ancestor lookup (`kb.segment` range or `parent_id` walk).
- **The `@?` qualifier query** is carried by `claim_pred` (index condition on `run_id, predicate`; the path test filters the fetched rows).
- **v1 misfit:** U6's `e_last_result` (a `Statement`-typed entity without a kind) and its claim `c_follows` were not loaded (`rows.json`); OPEN-D1-5.

