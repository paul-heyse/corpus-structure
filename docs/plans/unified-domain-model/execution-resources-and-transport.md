# Execution resources, ownership and directional transport

> Current execution (2026-11-02): implementation is integrated under
> [ADR-0047](../../adr/0047-current-only-domain-runtime.md); the
> [coordinator checkpoint](../unified-domain-model_2026-11-01.md#current-execution-checkpoint--2026-11-02)
> owns current disposition and open acceptance. Historical compatibility/repair statements below
> retain their dated baseline; obsolete runtime formats are retired, while current archive custody
> and query compatibility remain supported. Final assembled qualification is open.

**Status:** Implementation integrated; current-only targeted closeout and assembled acceptance remain with the coordinator. **Created:** 2026-11-01. **Updated:** 2026-11-02. **Maturity:** Implemented; focused Tested evidence
is bounded below, with no measured speedup or universal memory claim.
The [coordinator](../unified-domain-model_2026-11-01.md) owns
package state, source disposition and assembled acceptance. This companion owns UM-09/UM-10
and realizes review [R04](../../design_review/reviews/design_review_unified-domain-model_2026-11-01.md#R04)
and [R09](../../design_review/reviews/design_review_unified-domain-model_2026-11-01.md#R09).
It does not change existing plans or claim their provider/deployment work complete.

## 1. Baseline and foundation assessment

Source inspection uses `370f0643` plus identified concurrent PDF/native work as context. Source
paths below are relative to `python/corpus-structure/src/corpus_structure/`. The review's
original research has older source baselines; implementation must reconcile changed callers
before treating their evidence as current.

The original review identified missing resource propagation from the validated process settings
to consolidation and unguarded delayed row generators. Current source passes `Settings.analytics`
through CLI finalization/regeneration and `orchestrate.commands.finalize_bound_run` into
`semantic.domain_operations.consolidate_cut`, which supplies threads, memory and scratch parent to
the actual `AnalysisScope`. Explicit standalone scope defaults remain available. No second settings
system or resource registry was introduced.

`semantic.analytics.BorrowedRows` now owns the supported `iter_rows` generator, checks its scope
before first/resumed consumption and retires it on exhaustion, explicit close or failure. The
existing scope settles row generators, readers, child connections and scratch independently.
Lazy Polars output and unowned Arrow capsules refuse explicitly. Detached Arrow/Python values
remain usable after closure. These are ownership properties, not constant-memory guarantees for
arbitrary native joins or sorts.

The current `semantic/arrow_transfer.py:41–171` derives explicit directional profiles, checks the
pgpq wire schema and creates a fresh encoder for each stream inside the caller's Core/Psycopg
transaction. `semantic/analytics.py` and `serve/companion_export.py` own a separate ADBC
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

### Selected-section preparation and reuse

The [UM-05 section projection](relational-implementations-and-projections.md#published-document-consumers)
is an additional UM-09/10 consumer. Pass the existing validated invocation resource snapshot to its
actual analytical/batch owners. Resolve the exact publication once and obtain selected records,
required ancestry and companion context through set-shaped reads. Reuse the existing snapshot,
cancellation and borrower owners; close database/native borrowers before unrelated local work when
detached immutable selected values suffice. Bound live batches and intermediates across the composed
operation; do not replace row-by-row lookups with a second whole-book copy.

Carry established immutable publication/custody properties through this controlled projection.
Validate changed selection, representation and consumer-contract premises at their own boundaries;
do not rerun whole-book native callbacks or recognition merely because consumer preparation resumes.
Arrow batch output is appropriate where an actual consumer benefits; no batch-to-Python-object loop,
new transfer profile or extra ADBC session is required just to claim columnar integration. Keep
explicit full exports and genuinely global validation distinct. Qualitative work removal is the
claim; no speedup measurement or new benchmark obligation is introduced.

### Current implementation and bounded evidence

The four companion recipes now declare `pdf-companion-projection-v3` and the directional JSON
policy once: Python/Core reads cast JSONB to text (`str | None`), while ADBC statements retain the
JSONB OID and Arrow JSON's separate null bitmap. Generated operation row materializers retain the
text until the shared explicit decoder is requested. Required SQL-null fields refuse; JSON text
`null` remains a distinct value. Source JSON provenance and Python transport type remain separate.
JSON effect inputs still use strict `JsonValue`; this read policy does not widen input coercion.

Coverage's optional `supports` collection permits omission or an array, not explicit null. The
actual native control preserves that domain refusal in both the released Python model and native
adoption, tests admitted omitted/empty-array export, and independently checks SQL NULL/JSON
null/array/object through Core, ADBC and Parquet. A failed earlier null-coverage assumption is
retained; it is not evidence of an accepted nullable coverage value.

| Evidence, checked 2026-11-02 | Outcome and limit |
|---|---|
| `build/test-receipts/um09-functional-attempt-00004.jsonl` | **passed**, 44 recorded DB-free resource/analytics/capture calls. This earlier receipt is component evidence, not final native-consumer qualification. |
| `uv run pytest -x -q python/corpus-structure/tests/semantic/test_analysis_resources.py`; `build/um09-resource-current-adapter-00001.log` | **passed**, 12 current resource/lifetime cases, including actual non-default DuckDB scope configuration, CLI forwarding, delayed consumption and independent cleanup/cancellation. The forwarding fixture now supplies the generated native row shape. |
| `build/test-receipts/um10-json-native-tristate-00002/classification.json` | **passed**, actual protected publication plus Core/ADBC/Parquet domain and transport controls on native85. `...00001` remains **failed** for the invalid test assumption above. Final23/86 source applicability remains part of the coordinator's union. |
| `build/test-receipts/um03-pdf-envelopes-00001/classification.json` | **passed**, scoped native staging/publication envelopes before later Core/backend changes; not an enclosing UM-10 exit. |
| `build/test-receipts/um05-fixed-byte-reader-lifetime-attempt-00001.jsonl` | **passed**, 20 DB-free fixed-byte/cursor lifetime calls; named prepared statements preserve page closure and live event cursor ownership. |

Actual selected-cell/context corrections and final native86 consumer checks remain with their
UM-05/integration owners. Current evidence does not establish new temporal/composite/OID profiles,
global memory bounds, a speedup, provider adoption or current-book acceptance. Unsupported
directions remain refused. Existing native/ADBC cancellation and write rollback obligations still
need the coordinator's final-source applicability assessment; component counts are not summed.

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

## Completion audit — 2026-11-02

**Bounded judgment:** non-default consolidation resources, guarded borrowed rows/delayed
consumption, independent cleanup/cancellation, caller-owned Psycopg/pgpq COPY and separate
ADBC imported snapshots are real mechanisms with retained passing controls. Existing finite
Core/ADBC/Parquet null/presence profiles are substantive; no requirement to add candidate temporal,
composite or custom-OID profiles is inferred. These findings establish neither a universal memory
bound nor a measured speedup.

**UM-CA04:** companion_export unconditionally uses default adbc.connect, ignoring the existing
analytics.adbc_driver_path setting which capture already honors. This is incomplete propagation
of an accepted invocation resource, not an extra backend request. Closing evidence must show
non-default driver acquisition on actual companion export while preserving snapshot import,
batch options, cancellation and lifetime. Earlier native85/86-focused evidence retains its source
limits; native90/product controls do not by themselves close all transport/resource acceptance.
The coordinator owns failed product qualification and final-source required-union reconciliation.
