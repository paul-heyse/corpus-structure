# Execution resources, ownership and directional transport

**Status:** Planned; implementation and verification not_run. **Created:** 2026-11-01.
**Target maturity:** Proposed. The [coordinator](../unified-domain-model_2026-11-01.md) owns
package state, source disposition and assembled acceptance. This companion owns UM-09/UM-10
and realizes review [R04](../../design_review/reviews/design_review_unified-domain-model_2026-11-01.md#R04)
and [R09](../../design_review/reviews/design_review_unified-domain-model_2026-11-01.md#R09).
It does not change existing plans or claim their provider/deployment work complete.

## 1. Baseline and foundation assessment

Source inspection uses `370f0643` plus identified concurrent PDF/native work as context. Source
paths below are relative to `python/corpus-structure/src/corpus_structure/`. The review's
original research has older source baselines; implementation must reconcile changed callers
before treating their evidence as current.

`settings.py:98–143` already supplies validated, frozen analytics settings from one process root.
`semantic/domain_operations.py:2050–2075` still constructs `AnalysisScope(packet)` with its own
resource defaults. `semantic/analytics.py:1018–1061` owns the actual DuckDB connection and scratch
workspace. Export already consumes capture settings, so the missing propagation is a bounded
consolidation/invocation correction, not justification for another settings system.

`analytics.py:419–462,1170–1217` tracks borrowed relations, connections and Arrow readers and
settles independent teardown actions before propagating errors. Python generators are not
wrapped. DuckDB `iter_rows` submits when iteration starts; passing the initial method guard
does not establish guarded later consumption. No successful post-close escape has been observed.

The current `semantic/arrow_transfer.py:41–171` derives explicit directional profiles, checks the
pgpq wire schema and creates a fresh encoder for each stream inside the caller's Core/Psycopg
transaction. `analytics.py:860–908` and `serve/companion_export.py:73–168` own a separate ADBC
read session with an imported snapshot. Preserve these existing boundaries.

## 2. Target contracts and selected library composition

### Resources are invocation inputs

The entry point resolves the existing `Settings` once. Its validated `AnalyticsSettings` snapshot
(or an immutable subset containing the selected resource fields) is passed explicitly through
the operation composition boundary into consolidation, capture and `AnalysisScope` construction.
Do not read the environment inside scientific policy or an analytical kernel. Threads, memory,
scratch parent, batch sizing and driver selection are process execution choices; arithmetic,
comparison, completeness and precision profiles remain release-owned semantic inputs.

Use pydantic-settings 2.16.1 `BaseSettings`/`settings_customise_sources` and nested Pydantic 2.14.1
models already in use. Constructor-over-environment acquisition remains selected. More cloud/file
sources, settings caches or a resource registry are not needed to propagate existing values.
Keep the scope's own argument validation and native-engine resource configuration.

### Borrowed versus detached results

The selected public analytical boundary supports owned relations and guarded Arrow batch readers.
A lazy Python result is borrowed whenever consumption can submit or continue native execution.
Add an owner-bound iterator adapter for the supported `iter_rows` route: check the scope before
first and every subsequent consumption, retain its underlying iterator for settlement, and reject
consumption after scope closure with the same deterministic closed-scope failure as readers.
Unsupported delayed interfaces must refuse at the boundary until their lifetime is qualified.
Do not infer every iterator is detached merely because its Python wrapper is materialized.

Already detached Arrow tables and Python values remain usable after closing the scope. Scope
closure remains idempotent, cancels/drains owned work as appropriate and attempts every independent
closer. A cleanup failure cannot transfer ownership silently or erase cancellation.

DuckDB 2.0 `DuckDBPyRelation`, `to_arrow_reader` and Arrow `RecordBatchReader` provide native
relational execution and batch delivery. They do not make blocking joins/sorts constant-memory.
Keep schema, release, snapshot and projection checks before registration; keep the input owner
alive until the last borrower closes. The adapter extends the current owner instead of creating
another lifetime framework.

### Directional profiles and execution

A domain operation supplies its admitted projection/signature and bound request. UM-03/UM-05
produce its typed parameter/result and relational products. UM-10 derives or selects the exact
wire profile: fields, order, nullability, encoding, model/release/compiler identity and normalization.
The transport owns movement; it does not redefine domain values or authorize publication.

For writes, retain SQLAlchemy 2.1.6 `Connection` → underlying Psycopg 3.3.6 connection → quoted
`psycopg.sql.Identifier` COPY target/columns → `pgpq.ArrowToPostgresBinaryEncoder` → existing
protected adoption/seal. `new_with_encoders`, `infer_encoder`, JSONB encoder builders and fresh
header/batch/footer state realize the known wire profile. Check each batch against the profile.
Discard an encoder after failure; do not finish/reuse partial encoder state. pgpq 0.12.0's schema
DDL helper is not the authoritative application schema.

For reads, retain ADBC PostgreSQL 1.13.0's separate transaction and imported PostgreSQL snapshot.
Core-produced COPY-compatible SQL is generated output. The ADBC `use_copy` and batch hint options
belong to that read path. Normalization checks against the model-derived Arrow schema preserve
exact lexical values alongside declared bounded numeric projections. Arrow metadata and physical
validation alone do not establish semantic validity.

Keep directional support explicit for temporal, array and composite/custom values as well as
numeric/JSON values. Preserve timezone and temporal precision; array/list layout, dimensionality
and element nulls; and composite/custom-type field and OID resolution under the correct schema.
A type supported in one direction is not automatically supported by another driver or direction.
Unsupported representations refuse explicitly rather than silently coercing or adding new support.

ADBC `$n` result binding/`adbc_prepare` is a candidate for a named parameterized consumer, not an
automatic replacement: bound results bypass COPY, use PGresult conversion, do not honor COPY's
batch hint and may execute per parameter set as the reader is consumed. A separate ADBC session
cannot see or participate in uncommitted publisher staging. `adbc_ingest` is similarly not a
same-session publication substitute. Psycopg row factories/custom adapters are candidates only
for a demonstrated conversion gap; custom PG types add OID and schema-lifecycle obligations.

## 3. UM-09 — Resources and supported lazy-result ownership

**Required working input:** current validated settings and existing `AnalysisScope` owner; no
whole-document dependency on native generation or SQLGlot. A settled UM-03 invocation boundary
must carry resources when that boundary is introduced, but this correction can precede it.

**Delivered behavior:** a non-default resource choice reaches actual consolidation/capture scope
creation. Supported lazy results cannot submit or continue after their scope closes. Detached
outputs retain their existing usability and semantics.

Migrate `consolidate_cut`, its orchestration/service callers, analytical capture/export entry points
and tests that construct scopes. Inventory all maintained `AnalysisScope` constructions; explicit
local defaults may remain for deliberately isolated library use, but application entry points must
not silently ignore selected resources. Remove duplicated application default choices after callers
use the shared settings snapshot. Do not remove the kernel's independently useful validation.

**UM-I09:** exercise delayed `iter_rows` before consumption, after partial consumption and during
close/cancellation. The decision is which interfaces the existing owner can guard/settle honestly.
An unsupported interface must explicitly refuse; it cannot be advertised as safe by annotations.
This investigation gates that lazy interface, not resource propagation or detached outputs.

**Acceptance:** independently choose non-default thread/memory/scratch values and observe them at
actual scope creation without changing release arithmetic identity. Check first/resumed iteration
after close, normal exhaustion, partial-reader cancellation, double close and independent cleanup
failures. Retain an Arrow-reader case and a detached-output case as contrary controls.

## 4. UM-10 — Domain-to-wire continuity and actual consumers

**Required working input:** UM-03's typed signatures/materializers and UM-05's projection shape for
each migrated operation; existing transfer/adoption primitives remain working foundations.

**Delivered behavior:** maintained row and batch consumers receive a projection derived from the
same operation meaning, with explicit parameter binding, exact codecs and a typed result boundary.
No caller chooses SQL identifiers or reconstructs the meaning of a wire value independently.

Migrate publication/Arrow staging and companion/capture exports together with their actual
consumers. Preserve same-session rollback/receipt behavior for writes and repeatable-read/read-only
snapshot import for analytical reads. New static result adapters must not hydrate bulk datasets
row by row merely to produce Python domain objects. Use batch operations where the contract is
relational; retain exact lossless source representations when analytical projections are bounded.

**UM-I10:** for a named conversion gap only, compare an ADBC bound-result path or Psycopg adapter
with the current route. Record exact type/OID/null/precision, buffering, lazy-effect and cancellation
behavior and the consumer benefiting from a change. If no gap is established, retain the existing
route and record the reason; UM-10 still delivers model-owned codecs and consumer continuity.

**Acceptance:** row/batch equivalent meaning against independently specified values; SQL NULL,
JSON null, absent fields, exact numeric lexical values and refused lossy conversions; profile/order/
nullability mismatch; multiple product pins; rollback before adoption; uncertain publication outcome;
partial ADBC consumption/cancellation and snapshot coherence. Do not add overlapping counts as a
qualification total. Required provider/native obligations remain open if unavailable.
For supported temporal/array/composite profiles, independently check timezone/precision, empty and
null elements/layout, and custom-type OID/schema resolution in each actual direction; retain
explicit refusal controls for unsupported directions without extending the supported type set.

## 5. Integration, references and completion

[Typed operations](typed-domain-operations.md) own request/result meaning;
[relational projections](relational-implementations-and-projections.md) own selected expressions;
[native evolution](native-authoring-and-evolution.md) owns protected definitions/deployment.
This document owns resource/lifetime composition and directional execution, not another source of
semantic policy. [Integration](integration-adoption-and-qualification.md) owns assembled journeys.

Concrete source/feature evidence is in the [boundary assessment](../../library_leverage/libraries/unified-model-boundaries_2026-11-01.md)
and [PostgreSQL assessment](../../library_leverage/libraries/unified-model-postgresql_2026-11-01.md),
with guide details in [settings](../../libraries/data_model/pydantic-settings.md),
[DuckDB](../../libraries/analytical_infrastructure/duckdb_2.md),
[PyArrow](../../libraries/analytical_infrastructure/pyarrow.md),
[pgpq](../../libraries/postgresql/pgpq.md), [Psycopg](../../libraries/postgresql/psycopg.md) and
[ADBC](../../libraries/postgresql/adbc-driver-postgresql.md). Exact-source inspection establishes
interfaces, not the future implementation's memory/performance or native correctness.

Completion requires current maintained callers migrated, obsolete independent resource/codec paths
retired, the selected success/failure controls applicable to final source, and no unsupported lazy
interface advertised. Targeted checks occur during implementation; full functional/hygiene routes
follow complete series scope under the coordinator. No benchmark or new capacity claim is required.
