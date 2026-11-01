# pg_textsearch 1.5.1 — PostgreSQL BM25 Full-Text Search Extension

Technical capability reference | October 28, 2026 | PostgreSQL 18 | Upstream release v1.5.1

## 1. Executive orientation

`pg_textsearch` is a native PostgreSQL extension, not a Python library. The Debian/Ubuntu package `postgresql-18-pg-textsearch` installs the extension for PostgreSQL 18. Python applications access its functionality through SQL using database clients such as Psycopg 3, SQLAlchemy, or asyncpg.

Developed by Timescale, `pg_textsearch` adds relevance-ranked full-text retrieval using BM25 scoring, a custom PostgreSQL index access method, and Block-Max WAND query optimization. Its purpose is to make sophisticated lexical search available directly within PostgreSQL, without requiring a separate search engine and synchronization pipeline.

Upstream repository: [https://github.com/timescale/pg_textsearch](https://github.com/timescale/pg_textsearch?utm_source=chatgpt.com)

Version-specific reference: [https://github.com/timescale/pg_textsearch/tree/v1.5.1](https://github.com/timescale/pg_textsearch/tree/v1.5.1?utm_source=chatgpt.com)

Release notes: [https://github.com/timescale/pg_textsearch/releases/tag/v1.5.1](https://github.com/timescale/pg_textsearch/releases/tag/v1.5.1?utm_source=chatgpt.com)

Version 1.5.1, released October 2, 2026, is the latest verified stable release. It fixes concurrency-related index corruption, expression-index insertion and array/domain handling, and maintenance behavior. The preceding 1.5.0 release introduced substantial Boolean search, compaction, and storage improvements.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### Core capability map

| Capability                | Native mechanism                                          | Architectural significance                                                              |
| ------------------------- | --------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Relevance ranking         | Corpus-aware BM25 with tunable `k1` and `b`               | More expressive ranking than simple lexical matching                                    |
| Fast top-K retrieval      | Block-Max WAND and ordered index scans                    | Avoids evaluating every candidate when retrieving highly ranked documents               |
| Boolean search            | PostgreSQL `tsquery` and `@@`                             | Deterministic AND, OR, NOT, phrase, prefix, and weight predicates                       |
| Language processing       | PostgreSQL text search configurations                     | Reuses PostgreSQL tokenization, stop-word handling, and stemming                        |
| Flexible indexing         | Expression, partial, array, and partitioned indexes       | Applies search to derived content and scoped datasets                                   |
| Transactional integration | PostgreSQL index access method, WAL, and MVCC integration | Search indexes participate in database transactions, recovery, and physical replication |
| Incremental indexing      | On-disk memtable, immutable segments, compaction          | Accommodates mutable, continuously updated document collections                         |
| Operational controls      | Shared-memory cache, VACUUM integration, diagnostics      | Manages indexing memory, space reclamation, and maintenance                             |
| Background maintenance    | Optional `pg_durable` integration, introduced in 1.5.0    | Separates index compaction from foreground write paths                                  |

The most important architectural distinction is that pg_textsearch combines search-engine-style ranked retrieval with PostgreSQL's relational execution environment. Search results can participate in SQL joins, filters, aggregations, access control, and application transactions without independently maintaining a second document store.

However, its BM25 access method does not automatically optimize every SQL expression containing BM25 scores. Efficient top-K scans, Boolean filtering, and filtered ranking have materially different execution characteristics.

## 2. Search and ranking semantics

### 2.1 BM25 relevance scoring

BM25 is a probabilistic information-retrieval ranking function. It scores documents using corpus statistics rather than merely counting matching words.

Its important inputs are:

| Component                        | Behavior                                                              |
| -------------------------------- | --------------------------------------------------------------------- |
| Term frequency (TF)              | Repeated query terms increase relevance, subject to saturation        |
| Inverse document frequency (IDF) | Rare terms contribute more than common terms                          |
| Document length                  | Longer documents can receive a normalization adjustment               |
| Average corpus length            | Establishes the baseline against which document lengths are evaluated |
| Query terms                      | A document's score combines contributions from normalized query terms |

Two configurable parameters govern ranking:

- `k1` — default 1.2, range 0.1–10.0: Controls term-frequency saturation. Larger values allow repeated occurrences to contribute more before their marginal effect diminishes.
- `b` — default 0.75, range 0–1: Controls document-length normalization. Zero disables this normalization; one applies the full configured length adjustment.

These are per-index parameters rather than options independently specified for every query.

### 2.2 Scoring operators and query types

| Interface                  | Function                                                      |
| -------------------------- | ------------------------------------------------------------- |
| `text <@> 'query text'`    | Calculate relevance with automatically inferred index context |
| `text <@> bm25query`       | Score using an explicit query object                          |
| `to_bm25query(text)`       | Construct a BM25 query without explicit index context         |
| `to_bm25query(text, text)` | Construct a BM25 query with an explicit index name            |
| `bm25query = bm25query`    | Equality comparison for BM25 query objects                    |

The ranking operator returns a `double precision` value, with negative scores and ascending order: more relevant documents have lower numerical scores.

A representative indexed ranking expression is `ORDER BY content <@> 'database optimization' LIMIT 10`.

The distinction between an index scan and an ordinary scalar score evaluation is consequential:

Indexed scoring: PostgreSQL selects the `bm25` access method and requests relevance-ordered results. Block-Max WAND can prune uncompetitive candidates before computing their complete scores.

Standalone scoring: `<@>` calculates a relevance score for an individual row outside an ordered BM25 index scan, using statistics from the selected index. This allows composition with arbitrary SQL expressions but can require evaluating and sorting many rows.

Explicit `to_bm25query('terms', 'index_name')` references are particularly important for prepared statements, stored procedures, partial indexes, ambiguous expressions, and query contexts where the planner cannot reliably infer the index.

A BM25 score is a corpus-dependent ranking measure, not a calibrated probability. Scores should not be interpreted as fixed relevance percentages or assumed comparable across independently indexed collections.

Source: [https://github.com/timescale/pg_textsearch/blob/v1.5.1/README.md](https://github.com/timescale/pg_textsearch/blob/v1.5.1/README.md?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 2.3 Boolean, phrase, prefix, and negative search

Version 1.5.0 added a significant second query family: index-assisted Boolean retrieval using PostgreSQL's native `tsquery` representation.

| Feature             | `tsquery` syntax  | Semantics                                    |
| ------------------- | ----------------- | -------------------------------------------- |
| Conjunction         | `term1 & term2`   | Both conditions must match                   |
| Disjunction         | `term1 \\| term2` | Either condition can match                   |
| Negation            | `!term`           | Excludes a matching term                     |
| Pure-negative query | `!term`           | Supports queries with no positive term       |
| Phrase matching     | `term1 <-> term2` | Terms must appear consecutively in order     |
| Positional distance | `term1 <N> term2` | Terms occur at a specified lexeme distance   |
| Prefix matching     | `term:*`          | Matches lexemes with the specified prefix    |
| Weight restriction  | `term:A`          | Applies PostgreSQL lexeme-weight constraints |

The `@@` operator provides Boolean matching, such as `content @@ to_tsquery('english', 'database & !mysql')`.

Several distinctions matter:

Phrase search is now available in v1.5.1, contrary to older documentation describing its absence. Phrase and weight predicates may require a conservative heap recheck, because the BM25 index does not necessarily retain enough positional or weight information to determine every match independently.

Boolean matching and BM25 ranking are separate operations. They can be combined in SQL, but the current planner does not execute the combination as one integrated ranked Boolean index scan. It may first find Boolean matches, then calculate standalone BM25 scores and sort them. This can be efficient for selective filters but considerably less efficient when a Boolean predicate matches much of the corpus.

Text search configuration consistency is essential. For Boolean matching, the configuration used to parse the text operand must correspond to the indexed configuration. Changes to `default_text_search_config` can invalidate cached generic prepared-statement assumptions; the extension explicitly handles the mismatch rather than silently returning incorrect index results.

PostgreSQL's `tsquery` ecosystem also provides query constructors and transformations such as `plainto_tsquery`, `phraseto_tsquery`, `websearch_to_tsquery`, and `ts_rewrite`. Those functions belong to PostgreSQL; they are not separate pg_textsearch implementations. Their results can be useful in constructing Boolean retrieval expressions, subject to the extension's supported operations and planner behavior.

Sources:

[https://github.com/timescale/pg_textsearch/releases/tag/v1.5.0](https://github.com/timescale/pg_textsearch/releases/tag/v1.5.0?utm_source=chatgpt.com)

[https://www.postgresql.org/docs/18/functions-textsearch.html](https://www.postgresql.org/docs/18/functions-textsearch.html?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2

## 3. Indexing capabilities

### 3.1 Custom `bm25` index access method

`pg_textsearch` registers a PostgreSQL index access method named `bm25`.

The primary form is `CREATE INDEX index_name ON table_name USING bm25 (content) WITH (text_config='english')`.

Its index parameters are:

| Parameter             | Default         | Function                                        |
| --------------------- | --------------- | ----------------------------------------------- |
| `text_config`         | Required        | PostgreSQL configuration for text normalization |
| `k1`                  | `1.2`           | BM25 term-frequency saturation                  |
| `b`                   | `0.75`          | BM25 length normalization                       |
| `compaction`          | `inline`        | Index maintenance policy                        |
| `compaction_schedule` | Global schedule | Optional per-index maintenance schedule         |

Unlike a standard PostgreSQL GIN index over `tsvector`, the BM25 index maintains the statistical and posting information needed for relevance-ordered retrieval. This makes the index itself a ranking execution mechanism, not merely a structure for identifying documents satisfying a search predicate.

### 3.2 Expression indexing and structured data

The extension can index immutable expressions producing text-like values.

| Input shape      | Supported approach                                            | Important implication                                               |
| ---------------- | ------------------------------------------------------------- | ------------------------------------------------------------------- |
| Plain text       | Index a `text`, `varchar`, or `char` column                   | Straightforward document retrieval                                  |
| JSONB text field | Index an expression such as `data->>'description'`            | No separate extracted column is necessary                           |
| Multiple columns | Concatenate or combine fields through an immutable expression | A searchable document can be constructed from relational attributes |
| Transformed text | Index `lower(content)` or another immutable expression        | Search operates on the expression's result                          |
| Text arrays      | Index `text[]`, `varchar[]`, or `char[]`                      | Elements contribute to one searchable document                      |
| Derived arrays   | Index an immutable array-producing expression                 | Supports searching a constructed collection of text fields          |

The indexed expression must match the query's scoring expression sufficiently for PostgreSQL to recognize the index.

Multi-column aggregation is not the same as independently weighted fields. Combining title and body in a single expression produces one BM25 document. The extension's documented options do not provide separate native BM25 field boosts or BM25F-style field-specific statistics.

Text arrays are flattened with spaces before tokenization. Consequently, array element boundaries are not preserved as separate relevance or positional domains.

This is useful for indexing structured or semi-structured relational content without duplicating a full document into a separate search system, but it does not turn `pg_textsearch` into a general-purpose JSONB search index.

### 3.3 Partial indexes and multilingual collections

Partial indexes allow a BM25 index to cover only rows satisfying a SQL predicate.

Examples include one index for publicly visible documents, one per content category, or one per language.

A particularly useful composition is:

`CREATE INDEX docs_en_idx ON documents USING bm25(content) WITH (text_config='english') WHERE lang='en'`

Such an index combines a row-selection predicate with an appropriate language analyzer.

The planner has an important limitation: partial BM25 indexes require explicit index naming through `to_bm25query()`; the implicit string-query form skips them. The query must also contain a predicate establishing that the partial index is applicable.

Partition-local and partial-index corpus statistics introduce ranking-scope differences, discussed below.

### 3.4 PostgreSQL language-processing integration

`pg_textsearch` reuses PostgreSQL's text search configurations, allowing lexical retrieval to benefit from its established text-processing infrastructure.

This includes language-specific stemming, stop-word dictionaries, token classification, normalization, and configurable dictionaries.

PostgreSQL can also support custom parsers, synonym dictionaries, thesaurus dictionaries, and other domain-specific normalization rules. Their applicability depends on how the chosen text search configuration transforms indexed content and queries.

Chinese-language support, added in v1.4, illustrates the extension boundary: `pg_textsearch` can use a Chinese-aware text search configuration, but segmentation is supplied by a separate PostgreSQL parser extension such as `zhparser`. It does not implement its own Chinese tokenizer.

Source: [https://github.com/timescale/pg_textsearch/blob/v1.5.1/README.md](https://github.com/timescale/pg_textsearch/blob/v1.5.1/README.md?utm_source=chatgpt.com)

PostgreSQL text configuration reference: [https://www.postgresql.org/docs/18/textsearch-configuration.html](https://www.postgresql.org/docs/18/textsearch-configuration.html?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2

## 4. Query planning and top-K retrieval

### 4.1 Block-Max WAND

Block-Max WAND (BMW) is among the extension's most important advanced mechanisms.

Conventional relevance ranking can require computing scores for a large number of matching documents and sorting the results.

BMW uses posting-list organization and precomputed upper bounds to avoid fully scoring blocks that cannot enter the current top-K result set.

Its operating model is:

Candidate generation → upper-bound evaluation → selective scoring → top-K maintenance.

The mechanism depends on term postings, bounded block-level scores, and efficient skipping among candidate documents.

As the result threshold becomes more competitive, additional blocks can be rejected without fully processing their contents.

This makes BMW particularly well suited to relatively small result limits against substantial document corpora. It is not equivalent to a guarantee that all scoring queries have sublinear execution complexity; highly selective Boolean conditions, broad retrieval, different SQL plans, and scoring many rows can produce different costs.

### 4.2 SQL planner interactions

`pg_textsearch` includes PostgreSQL planner hooks and cost-estimation logic to support relevance-ordered index scans.

The main execution distinctions are:

| Query shape                                    | Potential execution strategy                                        | Consequence                                      |
| ---------------------------------------------- | ------------------------------------------------------------------- | ------------------------------------------------ |
| `ORDER BY score LIMIT K`                       | Ordered BM25 index scan                                             | BMW can accelerate top-K retrieval               |
| Highly selective ordinary `WHERE` condition    | Relational pre-filter, standalone scoring, sort                     | Can avoid ranking most of the corpus             |
| Broad `WHERE` condition plus ordered BM25 scan | BM25 candidate scoring followed by post-filter                      | May need deeper retrieval to fill results        |
| Boolean `@@` plus BM25 score ordering          | Boolean match evaluation, standalone scoring, sort                  | Not fused into one ranked index scan in v1.5.1   |
| No pushed-down SQL limit                       | Initial batch controlled by `default_limit`, expanded when required | Different work profile from explicit small top-K |

Filtered ranking has a noteworthy optimization: the engine can seed its initial scoring depth based on planner selectivity estimates, rather than blindly retrieving exactly K candidates and repeating the search. This was improved in v1.4.

Post-filtered scans also support iterative growth. If many high-ranking candidates fail a relational predicate, the extension can increase the internal scoring batch to seek additional qualifying rows.

Nevertheless, filter selectivity, predicate placement, and the selected plan can matter as much as BM25 scoring performance. A separate B-tree index may be better for highly selective structured filtering, with standalone BM25 scoring applied afterward. Conversely, broad filters may favor a ranked BM25 scan.

`EXPLAIN (ANALYZE, BUFFERS)` is therefore more informative than assuming the presence of a BM25 index guarantees BMW execution.

Source: [https://github.com/timescale/pg_textsearch/blob/v1.5.1/README.md](https://github.com/timescale/pg_textsearch/blob/v1.5.1/README.md?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



## 5. Storage engine and indexing architecture

The storage architecture is more sophisticated than the SQL interface suggests. It combines a durable append-oriented write path with immutable posting segments, shared-memory acceleration, and PostgreSQL-native recovery.

Architecture reference: [https://github.com/timescale/pg_textsearch/blob/v1.5.1/ARCHITECTURE.md](https://github.com/timescale/pg_textsearch/blob/v1.5.1/ARCHITECTURE.md?utm_source=chatgpt.com)

### 5.1 LSM-like index organization

`pg_textsearch` uses a log-structured-merge-like organization inside PostgreSQL index storage.

| Layer               | Responsibility                                              | Important properties                                      |
| ------------------- | ----------------------------------------------------------- | --------------------------------------------------------- |
| Index metapage      | Root metadata and published segment topology                | Tracks the authoritative storage generation               |
| L0 memtable         | Receives incremental index writes                           | Durable, on-disk, WAL-logged                              |
| Shared-memory cache | Accelerates access to memtable contents                     | Derived, disposable, rebuilt on demand                    |
| Immutable segments  | Store compact postings, dictionaries, and document metadata | Efficient ranked retrieval and compression                |
| Compaction levels   | Organize and consolidate segments                           | Bound segment proliferation and reclaim deleted documents |
| Deferred-free chain | Retains displaced pages until safe reuse                    | Protects concurrent and standby readers                   |

A critical architectural change arrived in v1.3: the memtable's authoritative representation moved to WAL-logged PostgreSQL pages, with shared memory serving as an optional read cache.

This distinction improves crash recovery and replication behavior. Shared-memory state can be discarded or reconstructed without losing indexed writes.

Writes are appended to the durable memtable. Spills transform accumulated records into immutable segments; queries combine the active memtable with published segments.

A live heap tuple identifier occurs in at most one published segment, reducing the need for cross-segment document deduplication during retrieval.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 5.2 Block storage and compression

Segments contain the components needed for ranked retrieval, including term dictionaries, postings, document identifiers, field-length information, and skip structures.

The extension uses compressed posting blocks, delta encoding, and bitpacking. Its implementation also incorporates optimized block decompression and SIMD-accelerated decoding paths.

The important interaction is between compression and retrieval algorithms: compressed blocks reduce memory and I/O requirements, while skip structures and score upper bounds enable BMW to avoid decoding postings unlikely to improve the result set.

The `pg_textsearch.compress_segments` setting governs compression of newly created segments and defaults to enabled.

Compression reduces storage and I/O costs but introduces decompression work; changing it is primarily a performance tradeoff, not a change in search semantics.

### 5.3 Parallel index construction

Large initial builds can use PostgreSQL parallel maintenance workers.

The v1.5 architecture distributes disjoint heap ranges among workers. Each worker creates temporary segment streams, and the leader merges these directly into the published index representation.

Several advanced implementation details are consequential:

Streaming metadata: Worker segment directories and large intermediate metadata are stored in temporary files rather than retained in large shared-memory structures.

Bounded leader merge: The leader performs term-oriented merging with bounded working buffers, avoiding a complete corpus-sized document-remapping structure.

PostgreSQL bulk-read buffer strategy: Workers use buffer-ring behavior for large heap scans to avoid unnecessarily filling shared buffers with one-pass indexing data.

Shared maintenance memory: `maintenance_work_mem` is a total budget distributed among launched workers, not a separate full allocation for every worker.

`max_parallel_maintenance_workers` influences available build parallelism; PostgreSQL can choose fewer workers according to the table and execution environment.

For workloads dominated by initial ingestion, bulk loading before constructing the BM25 index can avoid substantial incremental indexing work.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2



## 6. Mutation, compaction, and concurrency

### 6.1 Incremental writes and memtable spilling

New and updated indexed documents are incorporated into the active memtable. When the memtable exceeds configured thresholds, the engine can spill its contents into an immutable segment.

Automatic spill triggers include the memtable page threshold, bulk-load term threshold, and VACUUM processing.

The storage design distinguishes durability from query acceleration: even if the shared cache is evicted, the on-disk memtable retains authoritative data.

### 6.2 Compaction mechanics

Compaction consolidates immutable segments and removes dead-document information.

Version 1.5 substantially improves concurrency by dividing maintenance into selection, construction, validation, and publication phases.

The long-running output build does not hold the per-index exclusive lightweight lock throughout. Exclusive publication is brief, allowing readers and other writers to make progress during much of the work.

Compaction is nevertheless a physical index-maintenance operation, not a fully transactional logical rewrite. Once published, the segment replacement is not undone merely because the calling SQL transaction later rolls back.

The compaction planner handles count-triggered merges, similarly sized segments, and segments with substantial deletion. Segments with at least 50% dead documents can become eligible for rewriting even when the normal segment-count threshold has not been reached.

The engine also enforces limits on segment size and count. Under sufficiently constrained maintenance conditions, a full L0 level can prevent further spills; a manual-compaction policy therefore introduces an operational responsibility rather than providing unlimited deferred maintenance.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 6.3 Three compaction modes

| Mode         | Behavior                                                                  | Principal tradeoff                                                           |
| ------------ | ------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `inline`     | Opportunistic compaction during spills and certain maintenance operations | No companion scheduler, but triggering writes can incur maintenance latency  |
| `background` | Dispatches index-specific maintenance to `pg_durable` workflows           | Moves much work off the foreground path, but adds orchestration dependencies |
| `manual`     | Leaves eligible work to explicit maintenance                              | Greater scheduling control, but requires reliable external maintenance       |

The default is `inline`.

Managed background compaction, introduced in v1.5.0, remains explicitly described as beta functionality.

It is not simply a built-in worker activated by one configuration flag.

It requires `pg_durable` 0.2.8 or later, preloading and initialization, appropriate privileges, and the required workflow infrastructure. The index owner must have `LOGIN`, and superuser-owned workflows require an additional `pg_durable` configuration setting.

Each physical BM25 index receives a separately managed workflow. Spill events can signal it, while a scheduled wake-up provides recovery from missed or deferred work.

The currently documented integration also requires `pg_durable` to be available in the same database as the index.

Source: [https://github.com/timescale/pg_textsearch/blob/v1.5.1/ARCHITECTURE.md](https://github.com/timescale/pg_textsearch/blob/v1.5.1/ARCHITECTURE.md?utm_source=chatgpt.com)

Companion extension: [https://github.com/microsoft/pg_durable](https://github.com/microsoft/pg_durable?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2

### 6.4 Maintenance functions

The extension exposes useful SQL maintenance interfaces.

| Function                       | Capability                                         |
| ------------------------------ | -------------------------------------------------- |
| `bm25_needs_compaction(index)` | Check whether a compaction pass is eligible        |
| `bm25_level_counts(index)`     | Inspect segment counts across the eight LSM levels |
| `bm25_compact_step(index)`     | Execute at most one eligible compaction pass       |
| `bm25_compact(index)`          | Process eligible compaction passes across levels   |
| `bm25_force_merge(index_name)` | Attempt one bounded best-effort merge              |
| `bm25_spill_index(index_name)` | Force a memtable spill                             |

The first four are documented in the compaction reference; `bm25_force_merge` and `bm25_spill_index` are explicitly categorized as development interfaces that may change.

`bm25_needs_compaction()` and `bm25_compact_step()` are particularly useful together because they expose maintenance readiness and incremental execution without requiring an all-at-once consolidation operation.

Mutating maintenance functions require appropriate index ownership. They do not operate on partitioned parent indexes or during recovery.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



## 7. PostgreSQL configuration and observability

### 7.1 Runtime configuration

The significant runtime parameters in v1.5.1 are:

| Parameter                                      | Default       | Function                                                     |
| ---------------------------------------------- | ------------- | ------------------------------------------------------------ |
| `pg_textsearch.default_limit`                  | `1000`        | Initial ranked scoring batch without a pushed-down SQL limit |
| `pg_textsearch.compress_segments`              | `on`          | Compression of new segment posting blocks                    |
| `pg_textsearch.segments_per_level`             | `8`           | Compaction threshold and bounded merge fan-in                |
| `pg_textsearch.max_segment_size`               | `4095MB`      | Conservative upper budget for new merged segments            |
| `pg_textsearch.bulk_load_threshold`            | `100000`      | Terms per transaction before automatic spill                 |
| `pg_textsearch.memtable_pages_threshold`       | `64`          | Memtable chain page threshold                                |
| `pg_textsearch.memtable_cache_enabled`         | `on`          | Enable derived shared-memory memtable cache                  |
| `pg_textsearch.memory_limit`                   | `2GB`         | Approximate global memtable-cache memory budget              |
| `pg_textsearch.background_compaction_schedule` | `*/5 * * * *` | Default managed-compaction schedule                          |
| `pg_textsearch.allow_rls`                      | `on`          | Permit BM25 indexes on RLS-protected tables                  |

An important refinement to older descriptions is that `memory_limit` is not a strict hard ceiling on total server memory.

It governs approximate shared-memory cache admission, eviction, and fallback behavior. Its thresholds include a per-index growth guard at one-eighth of the configured limit and a global best-effort eviction threshold at one-half.

Concurrent work can temporarily exceed the estimated limit. Index-building memory is controlled separately through PostgreSQL maintenance settings.

This distinction matters for capacity reasoning: cache admission and index construction are separate resource-management domains.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 7.2 Index usage and diagnostics

Because BM25 is a PostgreSQL index access method, ordinary PostgreSQL instrumentation remains applicable.

`pg_stat_user_indexes`, `pg_class`, and `pg_am` can identify BM25 indexes and expose index-scan activity. `pg_relation_size` provides physical index size. `EXPLAIN (ANALYZE, BUFFERS)` exposes the selected execution plan and its buffer activity.

Additional development interfaces include:

| Function                              | Diagnostic value                           |
| ------------------------------------- | ------------------------------------------ |
| `bm25_pending_free_pages(index_name)` | Pages awaiting standby-safe reclamation    |
| `bm25_dump_index(index_name)`         | Truncated index-structure inspection       |
| `bm25_summarize_index(index_name)`    | Index statistics without document contents |

These are superuser-only development interfaces and should not be treated as permanently stable observability contracts.

Together, PostgreSQL-native metrics and extension diagnostics can distinguish planner choices, accumulated segment maintenance, index growth, and delayed page reclamation.

Source: [https://github.com/timescale/pg_textsearch/blob/v1.5.1/README.md](https://github.com/timescale/pg_textsearch/blob/v1.5.1/README.md?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



## 8. Correctness, replication, and security boundaries

### 8.1 WAL, recovery, and replication

The index uses PostgreSQL's WAL mechanisms rather than defining a completely independent storage log.

It uses `GenericXLog` for relevant page mutations, WAL logging for newly written segment pages, and PostgreSQL recovery-conflict mechanisms for safe page reuse.

The authoritative on-disk state allows reconstruction across crash recovery and physical replication.

Physical replication is supported, with important standby considerations.

Queries against hot standbys require careful handling of segment-page generations. The project documents `hot_standby_feedback = on` for continuity of queries referencing older segment generations. If a disconnected standby retains an old snapshot, PostgreSQL recovery-conflict records provide a correctness fallback by canceling the conflicting snapshot before page reuse.

This protects storage correctness but is not a promise that every long-running standby query will complete without interruption.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



### 8.2 MVCC and corpus-statistics scope

The extension integrates with PostgreSQL's tuple visibility and transactional storage machinery, but its BM25 statistics are based on physical index statistics rather than statistics filtered individually for the current MVCC snapshot.

That distinction affects score interpretation.

A ranked result set may be visibility-correct while its IDF and corpus-length statistics reflect the physical index's broader population. Index updates, deletions, and maintenance can therefore affect statistical interpretation independently of the visible row set.

The v1.5 storage architecture captures a consistent physical index generation for an execution, including retries and cursor fetches, to avoid mixing incompatible segment and corpus-statistic states.

### 8.3 Row-level security

One of the extension's most consequential security limitations is that corpus statistics include indexed rows hidden by PostgreSQL row-level security.

A user who already knows a term may infer information about its distribution from relevance scores affected by inaccessible documents. This does not directly expose the text of unknown hidden documents, but it is a statistical information channel.

The `pg_textsearch.allow_rls` setting provides a superuser-controlled restriction. Setting it to `off` prevents certain operations that would establish combinations of RLS-protected tables and BM25 indexes.

Changing the setting does not retroactively eliminate existing combinations.

For strong cross-tenant or cross-security-domain isolation, this limitation deserves attention independently of whether normal SQL row visibility is enforced.

Source: [https://github.com/timescale/pg_textsearch/blob/v1.5.1/README.md](https://github.com/timescale/pg_textsearch/blob/v1.5.1/README.md?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



### 8.4 Other material boundaries

| Area                       | Limitation or behavior                                                                                                       |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Partitioned tables         | Each physical partition maintains separate BM25 statistics                                                                   |
| Cross-partition scoring    | IDF scales can differ, so scores are not inherently globally comparable                                                      |
| Very long tokens           | PostgreSQL ignores lexemes exceeding 2047 bytes                                                                              |
| Large raw documents        | Inputs over 256 KB are split at safe boundaries before tokenization and term-frequency merging                               |
| Text arrays                | Elements are flattened; element boundaries do not remain independently searchable                                            |
| PL/pgSQL                   | Implicit index inference is unreliable; explicit index context is required                                                   |
| Two-phase commit           | `PREPARE TRANSACTION` is unsupported after certain BM25 index create/drop operations until that DDL transaction is completed |
| Extension interoperability | Fixed LWLock tranche identifiers can conflict with other extensions' wait-event naming                                       |
| Background compaction      | Beta integration with a separately installed companion extension                                                             |

The partition-local statistics issue is particularly relevant to Timescale hypertables and other partitioned collections. Independent BM25 statistics mean that simply merging score-sorted results from partitions is not equivalent to ranking all documents against one global corpus.

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2

## 9. Python integration and companion technologies

### 9.1 Python application boundary

There is no special Python API required to use `pg_textsearch`.

The extension runs inside the PostgreSQL server and is accessed through the usual PostgreSQL wire protocol.

| Python interface | Integration role                                                                     |
| ---------------- | ------------------------------------------------------------------------------------ |
| `psycopg` 3      | Synchronous and asynchronous SQL execution, connection management, parameter binding |
| `psycopg_pool`   | Connection pooling for repeated search workloads                                     |
| `asyncpg`        | Asynchronous PostgreSQL queries and prepared statements                              |
| `SQLAlchemy`     | SQL expression construction, application query composition, ORM/Core integration     |
| `Alembic`        | Versioned migration management for extension and index DDL                           |

These are independent client-side libraries. None supplies BM25 ranking; the server extension supplies it.

Parameterized SQL can pass query text to `to_bm25query()`, while table and index identifiers remain SQL schema objects requiring controlled handling.

Explicit index selection is especially relevant to Python clients because prepared statements and dynamically generated SQL can encounter the extension's implicit-index-inference limitations.

The integration boundary is therefore straightforward: Python manages application orchestration and SQL execution; PostgreSQL manages indexing, retrieval, ranking, and transaction semantics.

### 9.2 Hybrid semantic and lexical retrieval

A useful composition is `pg_textsearch` plus pgvector.

| Retrieval component | Responsibility                                                           |
| ------------------- | ------------------------------------------------------------------------ |
| `pg_textsearch`     | Lexical BM25 retrieval                                                   |
| `pgvector`          | Vector storage and similarity search                                     |
| PostgreSQL SQL      | Candidate combination, filtering, joins, and reranking                   |
| Python application  | Query preparation, embedding generation, and optional external reranking |

The two retrieval methods address different signals.

BM25 favors terms with meaningful corpus frequency and document-frequency characteristics. Vector retrieval uses proximity in an embedding space.

Their result sets can be combined using relational operations and ranking fusion, including Reciprocal Rank Fusion (RRF).

A particularly important distinction is that raw BM25 and vector-distance scores are not directly comparable. RRF combines rank positions rather than assuming equivalent numerical scales.

Hybrid search does not eliminate the costs of two retrieval pipelines or automatically provide globally optimal candidate generation. Each method may independently retrieve a bounded candidate set before fusion, which introduces recall-versus-cost tradeoffs.

The advantage is that both result sets can be generated inside PostgreSQL without duplicating the relational record store.

Relevant reference:

[https://github.com/timescale/pg-aiguide/blob/main/skills/postgres-hybrid-text-search/SKILL.md](https://github.com/timescale/pg-aiguide/blob/main/skills/postgres-hybrid-text-search/SKILL.md?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub

### 9.3 Comparison with PostgreSQL native full-text search

PostgreSQL already provides substantial native search functionality through `tsvector`, `tsquery`, GIN/GiST indexes, and functions such as `ts_rank` and `ts_rank_cd`.

| Dimension                     | Native PostgreSQL FTS                                      | `pg_textsearch`                              |
| ----------------------------- | ---------------------------------------------------------- | -------------------------------------------- |
| Principal index types         | GIN/GiST                                                   | Custom BM25                                  |
| Query matching                | `tsquery` and `@@`                                         | Supports `tsquery` Boolean matching          |
| Ranking                       | `ts_rank`, `ts_rank_cd`                                    | Corpus-aware BM25                            |
| Top-K optimization            | Generally relies on conventional match and sort strategies | Specialized Block-Max WAND                   |
| Language processing           | Native configurations                                      | Reuses native configurations                 |
| Corpus statistics for scoring | Native rank functions do not use global corpus IDF         | Built into BM25 index statistics             |
| Operational dependencies      | PostgreSQL core                                            | Extension installation and shared preloading |

Native full-text search remains a strong option for deterministic lexical filtering and relatively simple ranking requirements.

The primary distinction of `pg_textsearch` is its integrated corpus-aware ranking index and efficient relevance-ordered retrieval, rather than a replacement for PostgreSQL's entire text-search subsystem.

PostgreSQL reference: [https://www.postgresql.org/docs/18/textsearch-indexes.html](https://www.postgresql.org/docs/18/textsearch-indexes.html?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.postgresql.org\&sz=32)

postgresql.org



### 9.4 Comparison with ParadeDB

ParadeDB's `pg_search` is another PostgreSQL-native approach to ranked search.

Its current architecture integrates Tantivy and supports a broader search-and-analytics feature family, including BM25, filters, facets, aggregations, and highlighting.

By contrast, `pg_textsearch` has a narrower documented functional emphasis: PostgreSQL-native BM25 relevance retrieval, integrated text configurations, Boolean `tsquery` support, and an explicitly managed LSM-like index implementation.

This is an architectural distinction rather than a definitive performance ranking. Query planning, supported SQL operations, compaction behavior, and extension compatibility matter in addition to the scoring algorithm.

ParadeDB source: [https://github.com/paradedb/paradedb](https://github.com/paradedb/paradedb?utm_source=chatgpt.com)&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub



## 10. Performance characteristics and evidence

`pg_textsearch` maintains an upstream benchmark suite covering ranked retrieval, index construction, and concurrent insertion.

The key mechanisms responsible for potential performance advantages are:

Retrieval: Block-Max WAND prunes candidates and posting blocks that cannot improve a top-K result.

Storage: Posting compression and skip structures reduce data movement and help query execution avoid unnecessary decoding.

Index construction: Parallel workers and bounded streaming merges reduce build time and memory pressure for larger collections.

Maintenance: Immutable segment construction outside long exclusive index-lock periods improves concurrency during compaction and spilling.

Upstream benchmarks use MS MARCO, MS MARCO v2, Wikipedia abstracts, and smaller regression datasets. The primary MS MARCO dataset contains approximately 8.8 million passages; v2 exceeds 138 million passages.

The documented query methodology uses warm-cache `LIMIT 10` searches, grouping query lengths and collecting latency distributions.

Its standard GitHub Actions environment is PostgreSQL 17 on a two-core AMD EPYC runner with 7 GB RAM. The published methodology explicitly excludes network latency and measures single-threaded query execution for that benchmark family.

Consequently, upstream latency or speedup figures should not be generalized to arbitrary concurrent PostgreSQL 18 workloads, heavily filtered searches, long-document collections, or hybrid retrieval.

Benchmark dashboard: [https://timescale.github.io/pg_textsearch/benchmarks/](https://timescale.github.io/pg_textsearch/benchmarks/?utm_source=chatgpt.com)

Methodology: [https://timescale.github.io/pg_textsearch/benchmarks/methodology.html](https://timescale.github.io/pg_textsearch/benchmarks/methodology.html?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://timescale.github.io\&sz=32)

pg_textsearch

## 11. Installation, version compatibility, and maturity

### 11.1 Package and server versions

The names refer to distinct layers:

| Name                          | Meaning                                              |
| ----------------------------- | ---------------------------------------------------- |
| `pg_textsearch`               | PostgreSQL extension name used by `CREATE EXTENSION` |
| `bm25`                        | Index access method created by the extension         |
| `postgresql-18-pg-textsearch` | Debian-family operating-system package               |
| `1.5.1`                       | Upstream extension release                           |
| PostgreSQL 18                 | Database-server major version                        |

The supported stable PostgreSQL majors are 17 and 18. Upstream v1.5.1 also documents best-effort PostgreSQL 19 prerelease compatibility, without published prebuilt binaries for PostgreSQL 19.

Linux amd64 and arm64 binaries are available from upstream releases. Source builds are documented for Linux, macOS, and Windows, with Windows support newly introduced in v1.5.

Debian package documentation:

[https://packages.debian.org/en/forky/postgresql-18-pg-textsearch](https://packages.debian.org/en/forky/postgresql-18-pg-textsearch?utm_source=chatgpt.com)

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1

### 11.2 Activation and upgrade lifecycle

Installing the system package makes the extension's files available to PostgreSQL but does not, by itself, enable the SQL extension in every database.

The operational lifecycle requires adding `pg_textsearch` to `shared_preload_libraries`, restarting the PostgreSQL server, and executing `CREATE EXTENSION pg_textsearch` in each target database.

Upgrades require compatibility between the loaded server binary and SQL extension version. Release-specific upgrade instructions should be checked for index-format changes and any `REINDEX` requirement; not every earlier version necessarily has identical upgrade conditions.

The system-package name should also be distinguished from the actual files installed. Different packaging repositories can distribute the same extension under different package names, so independently installing multiple variants that own the same PostgreSQL extension binaries is not a valid method of combining capabilities.

### 11.3 Version development and documentation accuracy

The release history illustrates how quickly the extension's operational model has changed:

| Version | Significant addition                                                                                 |
| ------- | ---------------------------------------------------------------------------------------------------- |
| 1.0     | First generally available release                                                                    |
| 1.1     | Better concurrent writes, memory controls, arrays, expressions, partial indexes, alive-bitset VACUUM |
| 1.2     | Physical replication correctness                                                                     |
| 1.3     | Durable on-disk memtable and derived shared-memory cache                                             |
| 1.4     | Improved filtered top-K retrieval and Chinese text-search support                                    |
| 1.5.0   | Boolean/phrase queries, beta background compaction, major concurrency improvements                   |
| 1.5.1   | Concurrent spill/merge, expression-index, and maintenance correctness fixes                          |

A source-verification caveat is important: some public documentation continues to describe older limitations such as unavailable phrase search, unsupported expression indexes, or exclusively synchronous compaction. Those statements no longer fully describe 1.5.1.

For version-sensitive implementation decisions, the tagged upstream README, architecture document, and release notes take precedence over older product documentation or development-branch descriptions.

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+2

## 12. Architectural implications

The most significant capability combinations are:

| Combination                          | What it enables                                                          | Important boundary                                                   |
| ------------------------------------ | ------------------------------------------------------------------------ | -------------------------------------------------------------------- |
| BM25 + Block-Max WAND                | Efficient ranked retrieval without an external search service            | Depends on an appropriate ordered index plan                         |
| BM25 + native text configurations    | Custom tokenization and language-aware relevance ranking                 | Tokenization quality and language configuration remain consequential |
| Expression + partial indexes         | Searchable projections over structured data and selected row populations | Explicit index references and expression matching matter             |
| `tsquery` + BM25                     | Deterministic Boolean eligibility with relevance ordering                | Not yet one fused optimized scan                                     |
| BM25 + PostgreSQL relational indexes | Choose structured pre-filtering or ranked candidate generation           | Planner selectivity and score-evaluation costs determine efficiency  |
| On-disk memtable + WAL               | Durable incremental indexing with recoverable read caches                | Requires storage-generation and page-reuse coordination              |
| Segments + compaction                | Mutable search collections with controlled index maintenance             | Write latency and maintenance scheduling remain operational concerns |
| BM25 + pgvector                      | Lexical/semantic hybrid retrieval within one database                    | Independent retrieval and score-fusion logic                         |
| BM25 + RLS                           | Search within PostgreSQL's access-control environment                    | Global corpus statistics create a possible inference channel         |

### Overall characterization

`pg_textsearch` 1.5.1 is best understood as a specialized, deeply integrated PostgreSQL relevance-ranking engine, not a general Python text-search library or a full replacement for every search-engine feature.

Its strongest native capabilities are BM25 ranking, efficient top-K retrieval, reuse of PostgreSQL text processing, flexible expression/partial indexing, and a sophisticated durable storage architecture.

The advanced distinctions worth preserving are the separation of ranked index scans from standalone scoring, the lack of fused Boolean/BM25 optimization, per-partition corpus statistics, RLS-related statistical disclosure, and the operational consequences of compaction and physical replication.

For programming agents, recognizing those boundaries is essential to choosing between native relational operations, specialized BM25 execution, and companion technologies without inventing unnecessary application-side search machinery.

Primary technical references

- Version 1.5.1 SQL interface and operations: [https://github.com/timescale/pg_textsearch/blob/v1.5.1/README.md](https://github.com/timescale/pg_textsearch/blob/v1.5.1/README.md?utm_source=chatgpt.com)
- Storage, concurrency, WAL, and compaction architecture: [https://github.com/timescale/pg_textsearch/blob/v1.5.1/ARCHITECTURE.md](https://github.com/timescale/pg_textsearch/blob/v1.5.1/ARCHITECTURE.md?utm_source=chatgpt.com)
- Version 1.5.1 release: [https://github.com/timescale/pg_textsearch/releases/tag/v1.5.1](https://github.com/timescale/pg_textsearch/releases/tag/v1.5.1?utm_source=chatgpt.com)
- Version 1.5.0 feature changes: [https://github.com/timescale/pg_textsearch/releases/tag/v1.5.0](https://github.com/timescale/pg_textsearch/releases/tag/v1.5.0?utm_source=chatgpt.com)
- PostgreSQL 18 text-search functions: [https://www.postgresql.org/docs/18/functions-textsearch.html](https://www.postgresql.org/docs/18/functions-textsearch.html?utm_source=chatgpt.com)
- PostgreSQL 18 text-search configuration: [https://www.postgresql.org/docs/18/textsearch-configuration.html](https://www.postgresql.org/docs/18/textsearch-configuration.html?utm_source=chatgpt.com)
- Benchmark methodology: [https://timescale.github.io/pg_textsearch/benchmarks/methodology.html](https://timescale.github.io/pg_textsearch/benchmarks/methodology.html?utm_source=chatgpt.com)