# S6 vectors (brief step 6)

pgvector 0.8.7, pgvector-python 0.5.1 (`HalfVector`, binary COPY). Random unit vectors (seed 20261028); recall@10 against the exact top 10 (`enable_indexscan = off`). The query: one embedding configuration, `target_type = 'segment'`, joined to `kb.segment` with `kind = 'paragraph'` (one in four of the segment rows), `ORDER BY vec <=> $q LIMIT 10`.

## 1024 dimensions

COPY of 10000 rows: 145 ms; table 29073408 bytes. Half-precision round trip, max abs error over 3 rows: 5.11e-05.

### global hnsw (D3), iterative_scan off, planner's choice

build 3670 ms, 27320320 bytes; median 0.68 ms, p95 0.79 ms; recall@10 1.000; results short of 10 in 0 of 50 queries.

```
Limit
  ->  Sort
        Sort Key: ((e.vec <=> '[query vector]'::halfvec))
        ->  Hash Join
              Hash Cond: (e.target_id = s.id)
              ->  Seq Scan on embedding e
                    Filter: ((target_type = 'segment'::text) AND (model_config_id = '26'::smallint))
              ->  Hash
                    ->  Bitmap Heap Scan on segment s
                          Recheck Cond: (kind = 'paragraph'::text)
                          ->  Bitmap Index Scan on segment_kind
                                Index Cond: (kind = 'paragraph'::text)
```

### global hnsw (D3), iterative_scan relaxed_order, planner's choice

build 3670 ms, 27320320 bytes; median 0.68 ms, p95 0.74 ms; recall@10 1.000; results short of 10 in 0 of 50 queries.

```
Limit
  ->  Sort
        Sort Key: ((e.vec <=> '[query vector]'::halfvec))
        ->  Hash Join
              Hash Cond: (e.target_id = s.id)
              ->  Seq Scan on embedding e
                    Filter: ((target_type = 'segment'::text) AND (model_config_id = '26'::smallint))
              ->  Hash
                    ->  Bitmap Heap Scan on segment s
                          Recheck Cond: (kind = 'paragraph'::text)
                          ->  Bitmap Index Scan on segment_kind
                                Index Cond: (kind = 'paragraph'::text)
```

### global hnsw (D3), iterative_scan strict_order, planner's choice

build 3670 ms, 27320320 bytes; median 0.69 ms, p95 0.75 ms; recall@10 1.000; results short of 10 in 0 of 50 queries.

```
Limit
  ->  Sort
        Sort Key: ((e.vec <=> '[query vector]'::halfvec))
        ->  Hash Join
              Hash Cond: (e.target_id = s.id)
              ->  Seq Scan on embedding e
                    Filter: ((target_type = 'segment'::text) AND (model_config_id = '26'::smallint))
              ->  Hash
                    ->  Bitmap Heap Scan on segment s
                          Recheck Cond: (kind = 'paragraph'::text)
                          ->  Bitmap Index Scan on segment_kind
                                Index Cond: (kind = 'paragraph'::text)
```

### global hnsw (D3), iterative_scan off, HNSW forced (enable_seqscan, enable_sort off)

build 3670 ms, 27320320 bytes; median 0.50 ms, p95 0.76 ms; recall@10 0.150; results short of 10 in 50 of 50 queries.

```
Limit
  ->  Nested Loop
        ->  Index Scan using embedding_hnsw on embedding e
              Order By: (vec <=> '[query vector]'::halfvec)
              Filter: ((target_type = 'segment'::text) AND (model_config_id = '26'::smallint))
        ->  Memoize
              Cache Key: e.target_id
              Cache Mode: logical
              ->  Index Scan using segment_pkey on segment s
                    Index Cond: (id = e.target_id)
                    Filter: (kind = 'paragraph'::text)
```

### global hnsw (D3), iterative_scan relaxed_order, HNSW forced (enable_seqscan, enable_sort off)

build 3670 ms, 27320320 bytes; median 2.50 ms, p95 3.25 ms; recall@10 0.868; results short of 10 in 38 of 50 queries.

```
Limit
  ->  Nested Loop
        ->  Index Scan using embedding_hnsw on embedding e
              Order By: (vec <=> '[query vector]'::halfvec)
              Filter: ((target_type = 'segment'::text) AND (model_config_id = '26'::smallint))
        ->  Memoize
              Cache Key: e.target_id
              Cache Mode: logical
              ->  Index Scan using segment_pkey on segment s
                    Index Cond: (id = e.target_id)
                    Filter: (kind = 'paragraph'::text)
```

### global hnsw (D3), iterative_scan strict_order, HNSW forced (enable_seqscan, enable_sort off)

build 3670 ms, 27320320 bytes; median 3.20 ms, p95 3.84 ms; recall@10 0.464; results short of 10 in 50 of 50 queries.

```
Limit
  ->  Nested Loop
        ->  Index Scan using embedding_hnsw on embedding e
              Order By: (vec <=> '[query vector]'::halfvec)
              Filter: ((target_type = 'segment'::text) AND (model_config_id = '26'::smallint))
        ->  Memoize
              Cache Key: e.target_id
              Cache Mode: logical
              ->  Index Scan using segment_pkey on segment s
                    Index Cond: (id = e.target_id)
                    Filter: (kind = 'paragraph'::text)
```

### partial hnsw per target_type, iterative_scan off, planner's choice

build 3091 ms, 27344896 bytes; median 0.67 ms, p95 0.84 ms; recall@10 1.000; results short of 10 in 0 of 50 queries.

```
Limit
  ->  Sort
        Sort Key: ((e.vec <=> '[query vector]'::halfvec))
        ->  Hash Join
              Hash Cond: (e.target_id = s.id)
              ->  Seq Scan on embedding e
                    Filter: ((target_type = 'segment'::text) AND (model_config_id = '26'::smallint))
              ->  Hash
                    ->  Bitmap Heap Scan on segment s
                          Recheck Cond: (kind = 'paragraph'::text)
                          ->  Bitmap Index Scan on segment_kind
                                Index Cond: (kind = 'paragraph'::text)
```

### partial hnsw per target_type, iterative_scan relaxed_order, planner's choice

build 3091 ms, 27344896 bytes; median 0.68 ms, p95 0.77 ms; recall@10 1.000; results short of 10 in 0 of 50 queries.

```
Limit
  ->  Sort
        Sort Key: ((e.vec <=> '[query vector]'::halfvec))
        ->  Hash Join
              Hash Cond: (e.target_id = s.id)
              ->  Seq Scan on embedding e
                    Filter: ((target_type = 'segment'::text) AND (model_config_id = '26'::smallint))
              ->  Hash
                    ->  Bitmap Heap Scan on segment s
                          Recheck Cond: (kind = 'paragraph'::text)
                          ->  Bitmap Index Scan on segment_kind
                                Index Cond: (kind = 'paragraph'::text)
```

### partial hnsw per target_type, iterative_scan strict_order, planner's choice

build 3091 ms, 27344896 bytes; median 0.67 ms, p95 0.81 ms; recall@10 1.000; results short of 10 in 0 of 50 queries.

```
Limit
  ->  Sort
        Sort Key: ((e.vec <=> '[query vector]'::halfvec))
        ->  Hash Join
              Hash Cond: (e.target_id = s.id)
              ->  Seq Scan on embedding e
                    Filter: ((target_type = 'segment'::text) AND (model_config_id = '26'::smallint))
              ->  Hash
                    ->  Bitmap Heap Scan on segment s
                          Recheck Cond: (kind = 'paragraph'::text)
                          ->  Bitmap Index Scan on segment_kind
                                Index Cond: (kind = 'paragraph'::text)
```

### partial hnsw per target_type, iterative_scan off, HNSW forced (enable_seqscan, enable_sort off)

build 3091 ms, 27344896 bytes; median 0.45 ms, p95 0.69 ms; recall@10 0.162; results short of 10 in 50 of 50 queries.

```
Limit
  ->  Nested Loop
        ->  Index Scan using embedding_hnsw_segment on embedding e
              Order By: (vec <=> '[query vector]'::halfvec)
              Filter: (model_config_id = '26'::smallint)
        ->  Memoize
              Cache Key: e.target_id
              Cache Mode: logical
              ->  Index Scan using segment_pkey on segment s
                    Index Cond: (id = e.target_id)
                    Filter: (kind = 'paragraph'::text)
```

### partial hnsw per target_type, iterative_scan relaxed_order, HNSW forced (enable_seqscan, enable_sort off)

build 3091 ms, 27344896 bytes; median 1.60 ms, p95 2.13 ms; recall@10 0.840; results short of 10 in 46 of 50 queries.

```
Limit
  ->  Nested Loop
        ->  Index Scan using embedding_hnsw_segment on embedding e
              Order By: (vec <=> '[query vector]'::halfvec)
              Filter: (model_config_id = '26'::smallint)
        ->  Memoize
              Cache Key: e.target_id
              Cache Mode: logical
              ->  Index Scan using segment_pkey on segment s
                    Index Cond: (id = e.target_id)
                    Filter: (kind = 'paragraph'::text)
```

### partial hnsw per target_type, iterative_scan strict_order, HNSW forced (enable_seqscan, enable_sort off)

build 3091 ms, 27344896 bytes; median 1.88 ms, p95 2.44 ms; recall@10 0.466; results short of 10 in 50 of 50 queries.

```
Limit
  ->  Nested Loop
        ->  Index Scan using embedding_hnsw_segment on embedding e
              Order By: (vec <=> '[query vector]'::halfvec)
              Filter: (model_config_id = '26'::smallint)
        ->  Memoize
              Cache Key: e.target_id
              Cache Mode: logical
              ->  Index Scan using segment_pkey on segment s
                    Index Cond: (id = e.target_id)
                    Filter: (kind = 'paragraph'::text)
```

## 2048 dimensions

COPY of 10000 rows: 194 ms; table 56606720 bytes. Half-precision round trip, max abs error over 3 rows: 3.01e-05.

### global hnsw (D3), iterative_scan off, planner's choice

build 7191 ms, 81928192 bytes; median 0.79 ms, p95 1.21 ms; recall@10 1.000; results short of 10 in 0 of 50 queries.

```
Limit
  ->  Sort
        Sort Key: ((e.vec <=> '[query vector]'::halfvec))
        ->  Hash Join
              Hash Cond: (e.target_id = s.id)
              ->  Seq Scan on embedding_2048 e
                    Filter: ((target_type = 'segment'::text) AND (model_config_id = '26'::smallint))
              ->  Hash
                    ->  Bitmap Heap Scan on segment s
                          Recheck Cond: (kind = 'paragraph'::text)
                          ->  Bitmap Index Scan on segment_kind
                                Index Cond: (kind = 'paragraph'::text)
```

### global hnsw (D3), iterative_scan relaxed_order, planner's choice

build 7191 ms, 81928192 bytes; median 0.76 ms, p95 0.88 ms; recall@10 1.000; results short of 10 in 0 of 50 queries.

```
Limit
  ->  Sort
        Sort Key: ((e.vec <=> '[query vector]'::halfvec))
        ->  Hash Join
              Hash Cond: (e.target_id = s.id)
              ->  Seq Scan on embedding_2048 e
                    Filter: ((target_type = 'segment'::text) AND (model_config_id = '26'::smallint))
              ->  Hash
                    ->  Bitmap Heap Scan on segment s
                          Recheck Cond: (kind = 'paragraph'::text)
                          ->  Bitmap Index Scan on segment_kind
                                Index Cond: (kind = 'paragraph'::text)
```

### global hnsw (D3), iterative_scan strict_order, planner's choice

build 7191 ms, 81928192 bytes; median 0.75 ms, p95 0.88 ms; recall@10 1.000; results short of 10 in 0 of 50 queries.

```
Limit
  ->  Sort
        Sort Key: ((e.vec <=> '[query vector]'::halfvec))
        ->  Hash Join
              Hash Cond: (e.target_id = s.id)
              ->  Seq Scan on embedding_2048 e
                    Filter: ((target_type = 'segment'::text) AND (model_config_id = '26'::smallint))
              ->  Hash
                    ->  Bitmap Heap Scan on segment s
                          Recheck Cond: (kind = 'paragraph'::text)
                          ->  Bitmap Index Scan on segment_kind
                                Index Cond: (kind = 'paragraph'::text)
```

### global hnsw (D3), iterative_scan off, HNSW forced (enable_seqscan, enable_sort off)

build 7191 ms, 81928192 bytes; median 0.75 ms, p95 1.03 ms; recall@10 0.146; results short of 10 in 50 of 50 queries.

```
Limit
  ->  Nested Loop
        ->  Index Scan using embedding_2048_hnsw on embedding_2048 e
              Order By: (vec <=> '[query vector]'::halfvec)
              Filter: ((target_type = 'segment'::text) AND (model_config_id = '26'::smallint))
        ->  Index Scan using segment_pkey on segment s
              Index Cond: (id = e.target_id)
              Filter: (kind = 'paragraph'::text)
```

### global hnsw (D3), iterative_scan relaxed_order, HNSW forced (enable_seqscan, enable_sort off)

build 7191 ms, 81928192 bytes; median 3.43 ms, p95 4.73 ms; recall@10 0.842; results short of 10 in 39 of 50 queries.

```
Limit
  ->  Nested Loop
        ->  Index Scan using embedding_2048_hnsw on embedding_2048 e
              Order By: (vec <=> '[query vector]'::halfvec)
              Filter: ((target_type = 'segment'::text) AND (model_config_id = '26'::smallint))
        ->  Index Scan using segment_pkey on segment s
              Index Cond: (id = e.target_id)
              Filter: (kind = 'paragraph'::text)
```

### global hnsw (D3), iterative_scan strict_order, HNSW forced (enable_seqscan, enable_sort off)

build 7191 ms, 81928192 bytes; median 4.49 ms, p95 5.37 ms; recall@10 0.406; results short of 10 in 50 of 50 queries.

```
Limit
  ->  Nested Loop
        ->  Index Scan using embedding_2048_hnsw on embedding_2048 e
              Order By: (vec <=> '[query vector]'::halfvec)
              Filter: ((target_type = 'segment'::text) AND (model_config_id = '26'::smallint))
        ->  Index Scan using segment_pkey on segment s
              Index Cond: (id = e.target_id)
              Filter: (kind = 'paragraph'::text)
```

### partial hnsw per target_type, iterative_scan off, planner's choice

build 6144 ms, 81944576 bytes; median 0.75 ms, p95 0.83 ms; recall@10 1.000; results short of 10 in 0 of 50 queries.

```
Limit
  ->  Sort
        Sort Key: ((e.vec <=> '[query vector]'::halfvec))
        ->  Hash Join
              Hash Cond: (e.target_id = s.id)
              ->  Seq Scan on embedding_2048 e
                    Filter: ((target_type = 'segment'::text) AND (model_config_id = '26'::smallint))
              ->  Hash
                    ->  Bitmap Heap Scan on segment s
                          Recheck Cond: (kind = 'paragraph'::text)
                          ->  Bitmap Index Scan on segment_kind
                                Index Cond: (kind = 'paragraph'::text)
```

### partial hnsw per target_type, iterative_scan relaxed_order, planner's choice

build 6144 ms, 81944576 bytes; median 0.75 ms, p95 0.82 ms; recall@10 1.000; results short of 10 in 0 of 50 queries.

```
Limit
  ->  Sort
        Sort Key: ((e.vec <=> '[query vector]'::halfvec))
        ->  Hash Join
              Hash Cond: (e.target_id = s.id)
              ->  Seq Scan on embedding_2048 e
                    Filter: ((target_type = 'segment'::text) AND (model_config_id = '26'::smallint))
              ->  Hash
                    ->  Bitmap Heap Scan on segment s
                          Recheck Cond: (kind = 'paragraph'::text)
                          ->  Bitmap Index Scan on segment_kind
                                Index Cond: (kind = 'paragraph'::text)
```

### partial hnsw per target_type, iterative_scan strict_order, planner's choice

build 6144 ms, 81944576 bytes; median 0.76 ms, p95 0.81 ms; recall@10 1.000; results short of 10 in 0 of 50 queries.

```
Limit
  ->  Sort
        Sort Key: ((e.vec <=> '[query vector]'::halfvec))
        ->  Hash Join
              Hash Cond: (e.target_id = s.id)
              ->  Seq Scan on embedding_2048 e
                    Filter: ((target_type = 'segment'::text) AND (model_config_id = '26'::smallint))
              ->  Hash
                    ->  Bitmap Heap Scan on segment s
                          Recheck Cond: (kind = 'paragraph'::text)
                          ->  Bitmap Index Scan on segment_kind
                                Index Cond: (kind = 'paragraph'::text)
```

### partial hnsw per target_type, iterative_scan off, HNSW forced (enable_seqscan, enable_sort off)

build 6144 ms, 81944576 bytes; median 0.77 ms, p95 0.98 ms; recall@10 0.224; results short of 10 in 50 of 50 queries.

```
Limit
  ->  Nested Loop
        ->  Index Scan using embedding_2048_hnsw_segment on embedding_2048 e
              Order By: (vec <=> '[query vector]'::halfvec)
              Filter: (model_config_id = '26'::smallint)
        ->  Index Scan using segment_pkey on segment s
              Index Cond: (id = e.target_id)
              Filter: (kind = 'paragraph'::text)
```

### partial hnsw per target_type, iterative_scan relaxed_order, HNSW forced (enable_seqscan, enable_sort off)

build 6144 ms, 81944576 bytes; median 2.62 ms, p95 3.52 ms; recall@10 0.802; results short of 10 in 46 of 50 queries.

```
Limit
  ->  Nested Loop
        ->  Index Scan using embedding_2048_hnsw_segment on embedding_2048 e
              Order By: (vec <=> '[query vector]'::halfvec)
              Filter: (model_config_id = '26'::smallint)
        ->  Index Scan using segment_pkey on segment s
              Index Cond: (id = e.target_id)
              Filter: (kind = 'paragraph'::text)
```

### partial hnsw per target_type, iterative_scan strict_order, HNSW forced (enable_seqscan, enable_sort off)

build 6144 ms, 81944576 bytes; median 3.19 ms, p95 4.02 ms; recall@10 0.448; results short of 10 in 50 of 50 queries.

```
Limit
  ->  Nested Loop
        ->  Index Scan using embedding_2048_hnsw_segment on embedding_2048 e
              Order By: (vec <=> '[query vector]'::halfvec)
              Filter: (model_config_id = '26'::smallint)
        ->  Index Scan using segment_pkey on segment s
              Index Cond: (id = e.target_id)
              Filter: (kind = 'paragraph'::text)
```

