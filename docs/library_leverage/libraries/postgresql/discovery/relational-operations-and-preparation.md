# Relational operations and preparation

**Discovery · 2026-11-09.** Local observations are source-inspected at `51b3c28de`;
capability details are Interface-checked only where the cited selected source was inspected.
All candidate benefits and research priorities are **Proposed**. See the
[family briefing](../briefing.md) for environment, scope and evidence limits. These are research
leads, not applicability verdicts or selected replacements.

## Adopted intent

[Projection recipes](../../../../../python/corpus-structure/src/corpus_structure/semantic/projection_recipe.py) already lower model-owned expressions
into Core. [Companion preparation](../../../../../python/corpus-structure/src/corpus_structure/semantic/companion_projection.py) caches stable function
shapes with typed parameters and deterministic ordering. [Analytics](../../../../../python/corpus-structure/src/corpus_structure/semantic/analytics.py)
prepares query structure before value binding. These are used, not missing capabilities.

## Research shortlist

| State | Mechanism and consumer | Proposed value | Countercondition; next distinguishing question |
| --- | --- | --- | --- |
| Candidate underuse | Composable EXISTS/correlated predicates, ANY array binds, joins and database-derived key sets in readers/retrieval | Keep filtering and membership in the planner; avoid key round trips/expanding parameters | Complete global context or absence proofs may require wider input. Which current key set can remain resident without weakening source/release eligibility? |
| Candidate underuse | CTEs/add_cte, lateral(), table_valued(), VALUES, windows and aggregate_order_by() in projection/retrieval | Express the whole operation without intermediate materialization | A shared CTE in separately executed statements is recomputed. Can one composed operation preserve channel evidence, full membership validation and deterministic ties? |
| Conditional | Insert.from_select, UPSERT, DML CTEs, RETURNING correlation/from_dml_column | Avoid client read/write loops where inputs already reside in PostgreSQL | COPY remains appropriate for Python/Arrow producers; conflict semantics and returned identity can differ. Identify an actual resident transformation before replacing transport |
| Conditional | GenericFunction, compiler extensions, typed text/tstring, CreateView/CreateTableAs/Select.into | Delegate repeated SQL structure and expose result types | Procedural kernels remain opaque and native lifecycle is separate. Which structural fragment is duplicated and fully representable by a public construct? |
| Candidate underuse | Structural compiled caches/cache_ok/inherit_cache and lambda_stmt at existing preparation owners | Remove repeated stable construction without overlapping caches | Existing object-lifetime preparation may already suffice. What stable operation is actually rebuilt, and what determinants invalidate it? |
| Conditional | Core partitions/yield_per and server cursors for ordinary row exports | Bound materialization while retaining one snapshot | ADBC owns large analytical reads; streams retain transaction/pool capacity. Which consumer benefits after including ownership and cleanup? |
| Conditional | Psycopg prepare_threshold/prepare/prepared_max, pipeline/sync, executemany(returning=True)/results | Reuse server/session work or batch actual repeated calls | Pipelines exclude COPY/server cursors/streaming and delay errors; native preparation is per physical session. Which repeated workload remains after set-based composition? |
| Conditional | ADBC adbc_prepare/adbc_execute_schema and positional bound results | Discover parameter/result schemas before execution | Parameter description is not durable prepared-handle reuse; result buffering differs from COPY. Does a small Arrow consumer need this without duplicating adequate Core reads? |

## Four preparations, four lifetimes

A released expression recipe, SQLAlchemy's structural compiled cache, a server-session prepared
statement and protocol pipeline batching are distinct. Their reuse keys and failure scopes must
not be collapsed. Bind values change per invocation; declared types, namespaces, native revisions
and profile semantics may invalidate stable preparation.

ADBC1.13 supports result-producing positional `$n` bindings. The overview main text's older
no-parameterized-SELECT claim is corrected by its addendum and tagged source. Bound results use
PqResultArrayReader rather than incremental COPY: batch-size hints do not establish bounded native
buffering, and later parameter rows may execute during consumption. Early stopping result-producing
DML is therefore an effects question. Current literal-compiled snapshot COPY remains a sound baseline.

## Sources and handoff

[sqlalchemy overview](../../../../libraries/postgresql/sqlalchemy.md) Core and advanced relational/DDL sections;
[psycopg overview](../../../../libraries/postgresql/psycopg.md) preparation/pipeline/result sections; [adbc-driver-postgresql overview](../../../../libraries/postgresql/adbc-driver-postgresql.md)
addendum§1. Exact source:
[ADBC25 statement dispatch](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/statement.cc),
[result reader](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/result_reader.cc).

Prioritize the [retrieval operation](typed-retrieval-and-vector-search.md) and one concrete
resident-set consumer before proposing new caching or batch infrastructure. Preserve independent
eligibility/ordering expectations in any later comparison. Benefits remain qualitative.
