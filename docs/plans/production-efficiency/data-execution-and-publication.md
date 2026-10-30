# Data execution and publication efficiency

**Status:** Planned; no implementation or new performance qualification is claimed.  
**Created:** 2026-10-30. **Packages:** PE-08–PE-09.  
**Disposition owner:** [production-efficiency coordinator](../production-efficiency_2026-10-30.md).

## Target and prerequisites

This document realizes [F07](../../design_review/reviews/production-efficiency_2026-10-30.md#F07)
and [F11](../../design_review/reviews/production-efficiency_2026-10-30.md#F11). Semantic definitions
remain authoritative while publication ownership and analytical placement change. PE-00 supplies
accepted rule changes and their decision routes; PE-01 owns the shared model contracts for
interpretation, source identity, dependencies, exact values, effects and resource lifetimes.
A declaration being accepted does not establish that a runtime consumer has adopted it.

The target has one ownership boundary for each publication transport. A snapshot-derived intent
composes that owned transport instead of copying it again. Analytical capture preserves one logical
spine and snapshot contract with resident and spooled physical realizations. These are physical alternatives under one semantic authority,
not independent data models or a general storage abstraction.

Current source anchors are `semantic/arrow_publication.py`, `semantic/analytics.py`,
`semantic/domain_operations.py`, `serve/export.py` and `semantic/ontology.py` under
`python/corpus-structure/src/corpus_structure/`. Relevant owners are D3/D5/D8 and ADR-0031/0033.
Existing bulk COPY, exact decimal/lexical boundaries, snapshot imports, native operation lookup,
borrowed-handle checks and cleanup are preserved strengths.

<a id="PE-08"></a>
## PE-08 — Freeze publication transport once and reuse it across attempts

**Input:** existing implemented ownership/receipt contracts, including immutable transport content
and scoped source binding, reconciled with PE-01. Local duplicate-freeze removal need not wait
for the entire analysis-contract expansion. **Output:** all current row and Arrow publication producers use one owned
transport; a derived intent neither recreates its buffers nor recanonicalizes its content.

### Ownership and execution

`AppendPublication.from_rows` currently freezes its Arrow relations through IPC and builds canonical
content, then `SnapshotDerivedPublication.from_rows` passes those relations through another
`AppendPublication` constructor. Consolidation performs this inside the SERIALIZABLE retry
callback. Remove this duplication by composing an already-owned append transport with the derived
operation intent. The trusted internal constructor accepts the actual owned product, not a caller
assertion that arbitrary input is immutable. Ordinary external Arrow/NumPy-backed input still
crosses the existing ownership/validation boundary once.

Keep the current canonical publication bytes and receipt identity for supported replay. Preserve
row sorting, decimal spellings, signed-zero meaning, null/missing distinctions, field order and
exact lexical fallback. Replacing these bytes with an IPC fingerprint would change the protocol
and is not part of this correction. Do not add a serialized certificate, new ownership table or
parallel transport registry to avoid calling the existing owner twice.

In `consolidate_cut`, resolve span sequence IDs and finalize the source batch first. Construct the
owned derived publication before entering the retry owner, then reuse it for each attempt. Only
local preparation moves: admission, source-revision checks, staging, SERIALIZABLE isolation,
receipt replay, source/proof/result publication and final atomic visibility remain protected.
Inference that depends on the newly published revision stays in that transaction. Moving inference
out requires a separately justified combined-input design and is not inferred from this package.
An ambiguous commit is resolved through the same immutable identity before new work is attempted.

Integrate row publication, Arrow-producing analytical kernels, source consolidation and inference
consumers together. Retire the internal reconstruction path once these consumers compose the
owned product. Do not retain an optimized path and an ordinary duplicate-freeze path with
caller-specific selection flags.

### Library realization and boundaries

| Mechanism | Intended role and conditions |
|---|---|
| `pyarrow.ipc.new_stream`, `BufferOutputStream`, `BufferReader`, `ipc.open_stream` | Establish owned immutable buffers once where inputs may alias mutable memory. Internal composition preserves that ownership; arbitrary Arrow input is not assumed frozen merely because its Python wrapper is immutable. |
| `pgpq.ArrowToPostgresBinaryEncoder` header/batch/finish methods | Continue encoding native RecordBatches for COPY. Retain the declared column/type mapping and exact source lexical columns. |
| Psycopg cursor `copy` on SQLAlchemy's existing driver connection | Stage the owned batches on the transaction already owned by the publication operation. No second pool/transaction or independent commit. |
| Existing `publication._publish` and native publication routines | Remain the single retry/fencing/replay owner. Prepared content is reused; uncertain database effects are not cached as success. |

Sources: [Arrow IPC](https://arrow.apache.org/docs/python/ipc.html),
[Psycopg COPY](https://www.psycopg.org/psycopg3/docs/basic/copy.html),
[pgpq](https://github.com/adriangb/pgpq), and repository capability orientation in
[PyArrow](../../libraries/pyarrow.md), [Psycopg](../../libraries/psycopg.md),
[pgpq](../../libraries/pgpq.md) and [SQLAlchemy](../../libraries/sqlalchemy.md).
Use the pinned APIs and installed sources for consequential details during implementation.

### Completion evidence

Establish that direct Arrow and row producers freeze external mutable buffers once, trusted derived
composition performs no second freeze, and every retry reuses the same content. Independently
challenge mutation of the original buffer, malformed schemas, decimal limits, lexical preservation,
receipt equality, rollback, stale source revisions and ambiguous commit replay. Preserve the
atomic source/inference/result case. These are implementation acceptance needs, not a separate
project to redesign testing infrastructure. Quantified latency or memory improvement needs a
representative publication measurement; removal of duplicate construction alone establishes the
structural correction, not a speedup factor.

<a id="PE-09"></a>
## PE-09 — Bound capture's live state under the same analytical contract

**Input:** PE-01 snapshot/value/lifetime contracts; accepted RC04 from PE-00. **Output:** resident
and spooled capture under that same contract, with an explicit capacity/lifetime decision for
each supported operating mode and no narrowing of the complete spine or long analytics inside
a live database snapshot.
PE-08's owned transport boundary is reused where captured or computed data is published.

### Bounded capacity decision

Implement both resident and detached file capture. Begin with one representative required larger
realization and the present small realization to settle batch sizes, necessary materialization,
resource admission and ownership details. Measure only enough to choose those physical details;
this is not a mandatory scale matrix or a runtime cost model. DuckDB's `memory_limit` does not
bound Arrow tables already retained by Python.

Initially select the realization explicitly through the owning operation/configuration. Do not
add an automatic memory estimator or planner. Document the resident mode's supported envelope
and the spooled mode's disk, reader and cleanup obligations; unsupported inputs refuse honestly.
A bounded refusal alone does not establish fit for an in-scope larger capture. If a required
workload does not fit, correct the physical route before declaring that obligation complete.

RC04 was accepted for planning on 2026-10-30: resident and spooled realizations implement one
representation/ownership/completeness-qualified contract. PE-00 owns the enduring decision and
PE-01 its typed binding. The bounded decision settles how to realize that target, not whether
to defer spooled capture. It does not authorize hot upgrades of historical packets or require
every small query/export to use files.

### Detached file realization

Consume the current ADBC reader batch by batch under its imported REPEATABLE READ snapshot.
Apply the same release-compiled schemas and exact normalization profile to each batch. Write
complete relations into a private owned directory using `pyarrow.parquet.ParquetWriter.write_batch`.
Accumulate row counts, retained Arrow schema metadata and final content digests without loading
all relations back into memory. Publish the directory and complete manifest atomically only after
all required spine relations are closed and verified; missing or cancelled relations never become
a usable packet. Empty relations still have their declared schema and manifest entry.

Keep logical content identity distinct from physical Parquet-file integrity hashes. The capture
contract must specify canonical row/collection ordering and exact encoding across both modes;
a file-byte digest is not a substitute for semantic content. Settle a bounded canonical hashing
route in the capacity decision, using declared source ordering where sufficient or an external
sort over normalized canonical row keys (for example DuckDB over the private detached files).
Close database snapshots before substantial detached sorting/hashing, and publish the manifest
only after it completes. Do not hide whole-relation `to_pylist`, global row sorting or a complete
canonical byte buffer inside an otherwise batched writer. If the content protocol changes,
version it explicitly and retain old-reader meaning rather than compare unlike digest recipes.

Close both database snapshot scopes before long local analysis. DuckDB relations over the detached
Parquet files, or PyArrow dataset scanners, consume the same release/realization/revision/projection/
profile-qualified inputs as the resident realization. Scans may select columns and predicates only
where the operation contract permits; a full export still contains the complete logical spine.
Captured occurrence provenance and private candidate inputs remain distinct products.

The owner retains the capture directory until its last borrowed reader/relation closes. Explicit
exports transfer ownership to the destination; disposable analysis captures are removed by their
owner on close. Readers never outlive a deleted backing directory. Cancellation closes writers,
ADBC readers/connections and owned scratch without exposing a partial manifest. Do not keep a
PostgreSQL transaction open throughout downstream DuckDB computation to obtain lower memory use.

### Local preparation and trusted builders

Address the remaining F11 preparation at its actual ownership boundaries. A trusted candidate
builder should derive and validate occurrence/evidence scope once rather than construct a Python
expected universe and immediately convert its own Arrow result back with `to_pylist` for comparison.
Arbitrary external analytical input retains independent scope/schema/custody enforcement. Reuse
PE-01's owned-input distinction; do not introduce another cache or generic proof framework.

Prepare constant core RDF/SHACL shape data once where its dependencies are unchanged. Preserve
snapshot/release-specific qualified projection and required reference closure. RDFLib `Graph` is
mutable: caching one graph then applying `selected += shapes` would contaminate later validations.
Keep prepared immutable triples/bytes or construct an isolated graph per composition. Evaluate
`Graph.addN` only as a concrete bulk assembly option; it does not authorize a graph-store migration
or loss of qualified occurrences, member positions or multiplicity. SHACL remains validation with
explicit entailment/import/mutation settings.

### Library realization and completion

Use ADBC `fetch_record_batch` iteration, PyArrow `ParquetWriter.write_batch` with schema retention,
`ParquetFile.iter_batches`/dataset scanners, and DuckDB relation scans/`to_arrow_reader` where a
consumer needs incremental output. A reader borrows its analytical connection and inputs until
consumed/closed. `to_arrow_table` intentionally materializes a complete result; use it only where
that ownership is useful. The current exact Decimal rounding/overflow and hexadecimal-float
boundaries are not replaced by an approximate native cast merely to remove Python loops.

Primary references: [Arrow record batches](https://arrow.apache.org/docs/python/data.html),
[ParquetWriter](https://arrow.apache.org/docs/python/generated/pyarrow.parquet.ParquetWriter.html),
[Arrow dataset scanner](https://arrow.apache.org/docs/python/generated/pyarrow.dataset.Scanner.html),
[DuckDB relational API](https://duckdb.org/docs/stable/clients/python/relational_api.html),
[RDFLib Graph](https://rdflib.readthedocs.io/en/stable/apidocs/rdflib.graph.html).
Capability orientation: [ADBC PostgreSQL](../../libraries/adbc-driver-postgresql.md),
[DuckDB](../../libraries/duckdb_2.md), [PyArrow](../../libraries/pyarrow.md),
[RDFLib](../../libraries/rdflib.md) and [PySHACL](../../libraries/pyshacl.md).

Completion requires the capacity decision and both required physical realizations, all actual
capture/analysis/export consumers migrated, and independent equality of logical schema, scope,
exact values, relationship closure and incomplete outcomes across applicable realizations.
Challenge cancellation, empty relations, malformed metadata, signed zero, decimal overflow,
borrowed-reader closure and failed atomic publication. Demonstrate that required spooled capture
releases database scopes before analysis and that resident capture has an honest supported bound.
Measure memory/latency only for the decision or benefit claimed; no default zero-copy claim follows.
