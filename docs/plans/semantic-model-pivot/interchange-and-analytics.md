# Interchange and analytical execution

**Status:** SP-05 implemented within its declared profile; SP-C05 graph/model correspondence and assembled qualification remain open (completion audit below) · **Created/Revised:** 2026-10-29.

## Completeness contracts and current obligations

The scoped SP-05 implementation and receipts below remain the baseline. Added work is owned by
[SP-C05](domain-model-realization.md#SP-C05), using [SP-C01/SP-C02](domain-model-completeness.md)
projection contracts and SP-C03 protected effects. The
[coordinator §10](../semantic-model-pivot_2026-10-29.md#10-domain-model-completeness-integration)
owns its state and completeness-review dispositions.

Name the source universe, relation kinds, context, multiplicity/order, precision, omission,
completeness and lifetime of each normalized relation. Distinguish a captured PostgreSQL packet
from cut/candidate input using the same AnalysisScope; copied schema metadata cannot establish
capture provenance. Separate scope-borrowed readers/relations from detached materialized results.
Keep idempotent cleanup that attempts every owned resource and settles failures/cancellation.

Replace implicit publication intent with append versus snapshot-derived contracts. A derived
result requires its exact source binding/revision and operation/projection identity; stale input
requires recomputation. Preserve one captured snapshot, existing ADBC/Core cooperation and
protected pgpq COPY on the existing caller-owned transaction.

Retain the admitted DECIMAL(38,scale) HALF_EVEN policy, explicit rounding/overflow and exact original
lexical values. Neither Arrow decimal256 nor Oxigraph literal transport widens that contract.
SP-C05 owns bounded graph/mapping candidates and their decision conditions; a new backend is not
necessary to deliver these analytical distinctions. Existing current consumers adopt the new
input/result contracts within SP-C05; SP-08 later consumes them for exports/evaluation.

## Current execution contract (2026-10-29)

SP-05 starts at `903a2ff`, under [ADR-0026](../../adr/0026-columnar-semantic-operations.md).
The operator selected foundation plus existing set kernels, not full SP-07/SP-08 migration.
DuckDB remains the one local relational engine; DataFusion was considered and deferred. A
normalized Arrow spine preserves value/role, occurrence/fact and evidence/support identity;
bounded nested views are operation projections, not another catalog.

The explicit analytical default is DECIMAL(38,12), HALF_EVEN. Original lexical values and keys
remain unchanged; rounded values are identified as analytical products. An explicit release-bound
profile governs this transformation. Resource settings are operational only. Overflow refuses;
floating-point statistics cannot be relabelled as exact decimal results.

ADBC imports the SQLAlchemy read snapshot before data reads. The bulk bridge uses plain
PostgreSQL literal compilation (not psycopg percent escaping), fixed built-in types and owned
readers. Materialize replayable inputs before ending the source transactions, then compose
DuckDB relations in one operation scope. The pinned driver is the default. The operator's dbc
manifest at `~/.config/adbc/drivers/postgresql.toml` selects a separately installed 1.13.0 driver;
an explicit driver path is qualified independently and must not silently fall back.

pgpq 0.12 encodes fixed Arrow staging schemas to psycopg binary COPY on the existing enforcing
transaction. It never creates DDL or writes admitted tables directly. Exact SP-03 receipts and
whole-batch replay remain authoritative; a final canonical serialization pass is retained.
Operations requiring current state fence the source revision inside protected publication.
Stale analytical inputs require recomputation outside the write transaction.

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

## SP-05 implementation boundary (2026-10-29)

**Implemented/Tested; scoped receipts in the coordinator.** `semantic.analytical_profile` and
`semantic.analytics` compile explicit release profiles, Core selections and Arrow schemas, import
the control snapshot into ADBC and materialize a complete normalized realization packet. Narrower
consumer-specific universes remain with their owners; no selective-load performance claim is made.
`capture_packet` owns both database scopes; `AnalysisScope` owns one DuckDB connection, input
registrations, readers and a unique scratch child. Shape, metadata and actual row scopes are
checked. Native scalar fields coexist with original lexical values, roles and references.

Profile artifacts select scale 0–38 at precision 38, with default 12, HALF_EVEN and overflow
refusal. Half-even quantization and rational quotient avoid implicit float/cast rounding.
Canonical hexadecimal floats retain subnormals and signed zero. Fusion retains distinct
support/evidence and candidate counts; aliases retain match counts; disagreement groups use
canonical meaning-bearing qualification, not physical value IDs. Full declared-view set kernels
reuse existing ViewSpec semantics over operation-shaped relations. Independent expected rows and
Python differential controls cover those operations; producing all business projections and
migrating current consumers stay SP-07/SP-08.

`semantic.arrow_publication` freezes readonly bytes-backed Arrow buffers, verifies pgpq wire
schemas, caches exact canonical content and streams binary COPY through protected staging.
Migration 0004 grants application reads and adds protected source-revision fencing; 0005 grants
only the existing pure read helpers needed for canonical qualification projections. Earlier
migrations are unchanged. Generic `pool.write.write_arrow` was retired; ordinary row publication
remains supported. The final canonical serialization pass remains an explicit cost.

Native integration covers PostgreSQL → imported ADBC snapshot → Arrow → DuckDB → pgpq →
protected selection publication, exact replay and stale-analysis refusal. Both bundled and
explicit dbc-installed driver paths are exercised. Source snapshots close before local computation.
Earlier invalid numeric-only-integer fixtures were rejected by existing native constraints;
those constraints were preserved. Initial formatting/typing and boundary failures were corrected
and affected checks rerun, without giving failed results acceptance credit.

## Completion audit (2026-10-29)

**SP-05 implemented within its declared profile at `ad4593f`; whole-series and SP-C05 graph
closure remain open.** The [series audit](../semantic-model-pivot_2026-10-29.md#13-completion-audit-2026-10-29)
owns CA-03/CA-05/CA-06 and qualification. Handwritten kernels remain valid implementations when
their actual semantics are connected to the model; no disconnected exception is adopted.

| Accepted item | Current determination and evidence |
|---|---|
| Compiled operation-shaped Arrow relations and paired Core selections | Implemented shared physical/release/profile mappings in `semantic/analytics.py`; no separately editable Arrow semantic catalog. |
| Integers/decimals/units/time/missing states, nested references and ordered roles | Implemented exact lexical/kind/role columns beside explicit bounded native projections. DECIMAL(38,scale), HALF_EVEN, exact quotient and overflow/refusal behavior remain the admitted profile, not silent float conversion. |
| One coherent PostgreSQL snapshot across Core/ADBC | Implemented exported/imported snapshot and owned capture; actual mutable rows do not cross unrelated timestamp-only reads. Both bundled and explicit dbc-driver paths have scoped native receipts. |
| Materialization or streaming with real lifetime ownership | Implemented capture materialization before source close and an owned operation scope for readers/registrations/child cursors/scratch. No promise of universal streaming was made. |
| Filters/joins, complete analysis universe and set kernels | Implemented selected fusion/disagreement/alias/ViewSpec kernels and deterministic observable behavior. Full-realization capture is the documented initial route; it preserves context but makes no selective-load performance claim. |
| Metadata-loss normalization and actual row-scope checks | Implemented known compiled output restoration with schema/nullability/row identity validation; copied tags cannot authorize a different result. |
| Protected Arrow publication, pgpq schema and one transaction/retry owner | Implemented fixed publisher staging and same-driver COPY; arbitrary admitted-table Arrow writes are retired. Ordinary evidence persistence retains its proper owner. |
| Append/derived intent, exact source fence, stale analysis and immutable replay | Implemented explicit types and protected native checks; stale computation requires recomputation while matching completed replay returns its original receipt. |
| Borrowed/detached coexistence, cancellation and cleanup failures | Implemented owned connections/readers, borrowed-handle refusal after close, detached survival, all-resource teardown and preserved cancellation/failures. |
| Independent exact-boundary/native/DuckDB/publication controls | Existing analytics/Arrow tests and native snapshot/pgpq/replay/cancel receipts retain scope. Round trips alone are not treated as semantic correctness evidence. |
| Graph/read/analytical projection contracts reach current consumers | Analytical types and compilation consume named contracts; graph ID resolution and named-query coverage remain CA-05/CA-03. Maintained model/implementation correspondence is CA-06. |

Catalog `compile_projection` consumes the archived execution projection and release arithmetic;
`capture_analytics` consumes that mapping and an actual shared snapshot; `open_analysis` checks
captured/candidate provenance/schema/rows; `close_analysis` owns the actual lifetime; and
`publish_arrow` consumes explicit intent and native fences. These routes are substantively
connected. Hashing descriptive contract fields alone does not independently establish every
lowering property. `graph_project`/`graph_validate` implement qualified closure/conformance but
currently accept an unresolved caller-supplied projection ID (CA-05).

The full normalized capture and retained pure scientific algorithms are reasoned bounded choices,
not missing federation/DataFusion capabilities. DataFusion, alternative graph stores and
linkml-map have no unfulfilled installation mandate. No throughput/capacity benefit was measured
by this audit.
