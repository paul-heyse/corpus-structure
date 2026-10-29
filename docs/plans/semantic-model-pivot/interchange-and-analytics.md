# Interchange and analytical execution

**Status:** Planned · **Created:** 2026-10-29 · **Proposed.** [Coordinator](../semantic-model-pivot_2026-10-29.md) owns state. Realizes O06; supplies SP-07 consolidation and SP-08 exports/evaluation. Depends on [semantic contracts](semantic-model-and-releases.md) and [PostgreSQL/Core](postgresql-and-publication.md).

## Foundation and target

Current `schema/interchange.py` compiles table/payload schemas; `pool/contract.py` lifts stored batches; `load.py` reads a coherent REPEATABLE READ transaction then materializes; `duckdb_engine.py` scopes registration lifetime; `write.py` performs COPY through the repository. Reuse those coherent boundaries, not their assumption that installed schemas and legacy upcasting define every payload.

Compile operation-shaped Arrow relations from the same release/type mappings that produce relational metadata. Carry release, projection/compiler, data snapshot and qualification identity. Use typed columns for filters/joins; retain lossless structure/JSON only where a faithful native lowering is unavailable. No second editable Arrow schema or DuckDB semantic catalog. SQLAlchemy Table/expression objects define the selected PostgreSQL source relations and typed selection, not independently authored string joins.

<a id="SP-05"></a>
## SP-05 — Typed projections, loading and local set kernels

**Input:** SP-01; SP-02 for actual DB loading; SP-03 for publication integration and package acceptance. Pure schema/loader/kernel work may begin before the publisher is ready. **Owner:** interchange/pool integration.

Compile datatype mappings explicitly for integer bounds, exact numeric/decimal, timestamp precision/timezone, quantities/units, entity references, ordered roles and missing states. Canonical storage can retain an exact value while a bounded Arrow/DuckDB projection refuses it. Never silently cast to float or interpret Arrow null as every missing/unknown state. Preserve nested references and assertion occurrence identity even when grouping uses separate semantic fact keys.

Load mutually dependent relations from one coherent PostgreSQL transaction through the owned connection route. Immutable interpretation may be prepared outside that transaction; mutable facts cannot be combined from separate live connections using only a timestamp. Use an explicit shared snapshot if genuinely required across connections. Keep existing materialization where an operation needs it; introduce RecordBatchReader streaming only with an actual consumer and correct lifetime.

Retain per-operation DuckDB connections and try/finally input registrations. A reader keeps connection and registrations alive through consumption, closure or cancellation. Avoid global mutable connections or retaining Arrow buffers after their last consumer. Apply semantic filters before transfer where they preserve inference/coverage context; global aggregations still require their complete universe.

Use DuckDB relations for candidate set algebra, grouping, fusion and evaluation joins. Reuse declared policy and preserve deterministic ordering/tie behavior where observable. Metadata may be stripped by an engine/operator: restore it only from a known compiled output projection after checking actual shape and meaning. A copied metadata tag is not semantic enforcement.

All admitted writes go through SP-03. Retire `write_arrow` access to arbitrary admitted base tables; Arrow results stage into the publisher under the same SQLAlchemy-owned transaction with psycopg typed COPY. This does not prohibit bulk writes to ordinary evidence tables through their proper repository boundary.

**Acceptance:** independently specified rows for decimals outside columnar bounds, units, timestamp precision, absent/null/unknown, nested references and repeated occurrences. Native PostgreSQL→Arrow→DuckDB→publication journey verifies qualified meaning, not merely serializer agreement. Include metadata loss, wrong release/snapshot, empty relation, shuffled rows, cancelled stream and exception cleanup. Kernel differential checks retain independent expected semantic sets so two implementations cannot share an unnoticed collapse.

## Scope and source references

SP-05 does not create a lakehouse, federation service or new durable catalog. Arrow/DuckDB serve selected operations under one semantic authority; they do not replace PostgreSQL transactional admission. Ordinary projection/schema code stays a bounded compiler using library types, not a generic engine-neutral optimizer.

Mechanisms: `pyarrow.Schema`, `RecordBatchReader`, explicit decimal types, safe casts; DuckDB registered Arrow relations and relation operators; SQLAlchemy Core selection/joins; psycopg typed COPY. Sources: [PyArrow overview](../../libraries/pyarrow.md), [DuckDB overview](../../libraries/duckdb_2.md), [Arrow reader](https://arrow.apache.org/docs/python/generated/pyarrow.RecordBatchReader.html), [decimal256](https://arrow.apache.org/docs/python/generated/pyarrow.decimal256.html), [DuckDB relation source](https://github.com/duckdb/duckdb-python/blob/main/duckdb/_relation.py). Exact-pin compatibility and bounded precision remain native acceptance obligations, not documentation-derived pass claims.
