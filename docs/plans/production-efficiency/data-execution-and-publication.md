# Data execution and publication efficiency

**Status:** Implemented; scoped verification2026-10-30; assembled qualification remains PE-12.
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
[PyArrow](../../libraries/analytical_infrastructure/pyarrow.md), [Psycopg](../../libraries/postgresql/psycopg.md),
[pgpq](../../libraries/postgresql/pgpq.md) and [SQLAlchemy](../../libraries/postgresql/sqlalchemy.md).
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
Capability orientation: [ADBC PostgreSQL](../../libraries/postgresql/adbc-driver-postgresql.md),
[DuckDB](../../libraries/analytical_infrastructure/duckdb_2.md), [PyArrow](../../libraries/analytical_infrastructure/pyarrow.md),
[RDFLib](../../libraries/data_model/rdflib.md) and [PySHACL](../../libraries/data_model/pyshacl.md).

Completion requires the capacity decision and both required physical realizations, all actual
capture/analysis/export consumers migrated, and independent equality of logical schema, scope,
exact values, relationship closure and incomplete outcomes across applicable realizations.
Challenge cancellation, empty relations, malformed metadata, signed zero, decimal overflow,
borrowed-reader closure and failed atomic publication. Demonstrate that required spooled capture
releases database scopes before analysis and that resident capture has an honest supported bound.
Measure memory/latency only for the decision or benefit claimed; no default zero-copy claim follows.


## Execution —2026-10-30

**Implemented; scoped Tested.** PE-08 composes an actual owned AppendPublication into derived
intent through from_transport. Arrow and row producers cross the ownership boundary once; COPY
still uses pgpq header/batch/finish and Psycopg on the existing SQLAlchemy transaction. Canonical
publication bytes, lexical numeric fallback and receipt identity remain the existing protocol.
Consolidation resolves source spans, binds preparation and freezes its source transport before
the retry owner. Every attempt and ambiguous receipt lookup sees that same actual transport.
Inference depending on the source receipt's revision remains inside the atomic transaction.

PE-09 realizes one full 26-relation captured contract with resident Arrow tables or owned Parquet
files. ADBC fetch_record_batch iteration feeds the same exact normalization boundary. Core
queries order by declared primary keys (text COLLATE C, integer positions numerically); canonical
typed rows are length-framed and hashed incrementally. There is no global Python row sort,
whole-relation to_pylist, read_all, or spooled-to-Table rehydration on the ordinary capture path.
Exact scalar conversion still uses bounded Python Decimal/hexfloat handling where native casts
would change meaning. Batched normalization is not a claim of zero-copy or constant process RSS.

CaptureManifest/relations/binding and CapturePolicyDefinition are trusted LinkML definitions,
consumed by generated boundary adapters and finite implementation support. Compiler 8/profile 4,
analytical-6 and native 0038 carry the new contract and explicit implementation/library determinants.
Native derived publication consumes the analytical ABI recorded in the frozen descriptor rather
than a second literal compiler version. Frozen forward products preserve physical tables.
Historical semantic compiler 10/11 keeps analytical-4; retained prior execution archives keep
analytical-5 captured reads, without current-policy admission or new write authority.
Historical exports keep their format meaning; new captured exports use semantic-export-2.

CapturedPacket exposes iter_batches and explicit to_table materialization; FileRelation retains
schema/count/integrity without pretending to be a table. AnalysisScope registers resident Arrow
or creates lazy read_parquet views, preserving borrowed readers/connections. Source batches are
scope/null validated at construction; internally admitted file descriptors carry that result
without another row-scope scan. File integrity is still checked at read boundaries. External
file inputs retain full shape/scope/logical validation. Manifests own immutable canonical bytes,
bind packet identity/schema/count/digests, and separate physical hashes from logical content.
Export streams and compares actual logical content before publishing a complete destination.

Disposable directories publish their manifest only after every writer closes. CaptureOwner
prevents new leases after close and removes backing files after active leases finish. Database
scopes end before high-level capture returns. Exporting-context exit failures close the packet;
read/write/cancellation failures retain the primary error when teardown also fails. Explicit
exports retain their destination independently of disposable capture cleanup.

CandidateInput.from_admitted_cut derives and validates source scope once; consolidation no longer
creates Arrow merely to compare it with its own reconstructed Python universe. Arbitrary external
from_cut input retains the full expected-universe check. Core SHACL shapes are parsed into cached
immutable triples and copied with Graph.addN into fresh per-validation graphs. Independent blank
nodes are standardized apart. Qualified closure, occurrence identity and position multiplicity
remain; SHACL inference/imports/mutation/advanced rules remain disabled.

### Capacity and concrete defaults

The API keeps resident capture by default; CLI full export selects spooled through AnalyticsSettings
or --capture-mode. Defaults are 65,536 consumer rows, an 8 MiB ADBC byte hint and 512 MiB retained
resident Arrow admission. A driver hint is not a hard maximum; a large variable-width value can
exceed it. DuckDB retains 4 threads/2 GB and its memory limit is not a total-process cap. Resident
admission counts actual normalized retained Arrow bytes and refuses with a spooled-mode remedy;
there is no estimator or automatic switch.

The [native capture investigation](../../design_review/evidence/2026-10-30_data-capture/README.md)
exercises a complete projection with 1,024 evidence rows and 4 MiB source text: a 1 MiB resident limit
refuses, spooled capture/analysis/export succeeds, and a larger resident admission with different
batching has identical logical content. This bounded result settles the representation route;
it does not establish 512 MiB default capacity, whole-process RSS, full-corpus throughput or a
speedup factor. Broader production capacity/nonfunctional adoption remains PE-12.

### Verification and remaining boundary

build/pe89/core-functional.log retains the initial 84-case analytical/publication/model preparation
selection. build/pe89/integration.log retains native source/inference atomicity and export integration.
build/pe89/history-storage-final.log retains 56 passing policy/historical-reader/lifecycle/storage
cases. Independent cases challenge canonical content, external mutable buffers, retry/ambiguous
commit, old-reader meaning, exact scalar values, malformed headers, corruption, cancellation,
cleanup failure and backing-file lifetime. Capacity observations have a finalized evidence record.

Initial native failures include a stale analytical compiler literal; the corrected native guard
uses the descriptor. scoped-functional-final.log is an interrupted run whose cached implementation
bytes crossed a later source freeze; it has no acceptance credit. The earlier broad run at
build/test-receipts/qualification/20261030T104101Z-161695 is incomplete after the retained-reader
gap was identified, and likewise supplies no completion credit.

**passed, 2026-10-30:** `just test-all`, receipt
`build/test-receipts/qualification/20261030T104609Z-191443`: 2,407 Python tests, four dependency/
native warnings, no unresolved required selections and no source/context divergence. Rust selected
zero tests (`not_run`), supplying no Rust functional coverage. `just hygiene`, `just ready`,
`just docs-check` and `just evidence` passed; the evidence check retains 37 historical warnings.
Warning-inclusive Pyrefly reports no errors or warnings, with no new suppressions.

After that broad run, packet context-manager teardown was corrected to preserve a primary error
when disposal also fails. The affected storage/native/archive selection exercised the final
production source; its new regression initially failed because its test import was missing.
That import was corrected, and all eight storage cases passed in
`build/pe89/cleanup-corrected.log`; warning-inclusive typing passed in
`build/pe89/types-closeout-final.log`. The native/archive cases in
`build/pe89/closeout-functional.log` passed. The broad pass remains applicable to unaffected
behavior; it was not repeated after this narrow cleanup correction. Lint maintenance does not
invalidate those functional/type results.

PE-08–PE-09 implementation acceptance is complete. PE-12 retains assembled/provider/nonfunctional
qualification and wider capacity adoption. Operational database migration, historical regrading
and audit-premise changes were outside this execution scope.
