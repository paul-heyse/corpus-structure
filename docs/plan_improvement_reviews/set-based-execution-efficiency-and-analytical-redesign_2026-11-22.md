# Efficiency and analytical redesign through SBX-09

**2026-11-22 · Plan-improvement review.** Inspected clean `main` at `0e9288dd6`,
including the current sole-root registration `881829fd0`. The integrated qualification target
has the preceding registration. Eight managed runs settled as interrupted and their private
clusters exited. The reviewed footprint covers SBX-01–09 and the typed read, replay, PDF and
test infrastructure that materially changes with those packages. Proposed findings below
apply FP-01, FP-04–07, DP-07–11, DP-13–15, DP-19–20 and heuristic H28 from the
[design standard](../design_review/design_principles/standard.toml).
[Coordinator](../plans/set-based-execution_2026-11-21.md) ·
[Qualification checkpoint](../plans/set-based-execution/cutover-and-qualification.md#sbx-09-qualification-pause)

## Combined judgment

**Proposed.** Adopt a target in which a model-derived typed population is the ordinary
working representation for bulk products, selected multi-item reads and certification.
Produce it at the source, carry it until the real consumer boundary, and issue canonical
commitments from that population. Use Arrow to describe and transport the population,
Acero for composable batch transformations that can flow to a reader, and DuckDB for
whole relational computations whose joins, windows, ordering or replay justify an engine.
Keep keyed native access for a genuinely small or sparse request. Keep mutable authority in
PostgreSQL, with bulk projection pushed before packet construction and ADBC for eligible reads.
Make this division explicit in the model and consumers. A separate analytical store is optional
and earns its lifetime through reuse, independent delivery or recovery.

This can replace product and wire interfaces, worker inputs, generated SQL and storage
layout together. The public functional result is the same authenticated products, authorities,
change semantics and independently replayable evidence. Dev data is disposable. A selected
redesign can replace the registered root and retire its predecessor mechanism with its
consumers. Current root history still bounds the applicability of receipts. Treat canonical
commitment format as an explicit design choice. Keep exact equality for routes claiming the
same commitment identity. A deliberate new identity scheme needs a complete cutover of its
producers, native verifiers, references and detached consumers.

| Complete design considered | Judgment |
|---|---|
| Repair the immutable-carrier and native PostgreSQL design | Best immediate finish for the sparse and governed paths. Removes repeated Python work with little new lifecycle. It leaves bulk consumers paying for tagged packet construction and repeated conversion if used as the general target. |
| Typed populations with native PostgreSQL authority and purpose-specific Arrow/DuckDB execution | Recommended target. Makes acquisition, validation, worker handoff and delivery share one representation where they share a population. Distinguish a transient reader, reusable acquired batch, immutable IPC artifact and persistent Parquet projection. Choose the cheapest sufficient one for each lifetime. |
| PostgreSQL executes the entire analytical path | Prefer where input already lives inside an authority cut and reducing it there saves transfer or enables indexed selection. Carrying PDF and worker-owned inputs back to PostgreSQL for all transformations would add acquisition, writes and transaction pressure. |
| Move authority and computation to DuckDB or file snapshots | Coherent for finite, captured, independently analyzed work. Replacing live authority would require a writer and coordination design for rival claims, role-scoped reads, rollback, revocation, wakes, crash recovery and multiple provider processes. A single owner process is conceivable in this project. It would assume these responsibilities now delivered by PostgreSQL and gives no identified reduction there. Revisit only with a simpler concrete ownership model for those semantics. |

The [annotation pilot](../plans/set-based-execution/common-analytical-basis.md#pilot-implementation-and-evidence)
established canonical parity for an alternate carrier that still traversed both conversion
boundaries. Its immutable-carrier decision remains a strong baseline for the current producer.
The trial left typed acquisition, typed consumers and fused publication work open. The
[prior efficiency amendment](../plans/set-based-execution_2026-11-21.md#validation-postgresql-efficiency-amendment)
already owns admitted-page handoff and summary disclosure, bounded obligations, common attachment
preparation, completion sealing, witness handoff, typed candidates and qualification reuse.
The findings below extend those placements where residual work or a larger replacement is visible.

## Recommendations

<a id="I01"></a>
### I01 — Prepare each admitted premise population once per completion

**Proposed · advance for SBX-02/04 and SBX-08.** The Python completion path decodes and
projects the same admitted packet and derives group digests in `successful_rule_attestation()`
for each matching rule. Sentence completion loops over rules and partitions. Formal completion
invokes twelve rule checks. Native settlement already shares matching premise specifications
with materialized CTEs. Prepare the union of required observations once at the completion
owner, project each distinct premise once and derive separate fingerprints and seals. Share
already acquired blocks and interpreted inventories with named constructions that currently
restore and index them again. This works with the existing immutable carrier and becomes
the consumer contract for a typed replacement. Keep the cached values completion-local.
[Python attestation](../../python/corpus-structure/src/corpus_structure/semantic/established_validity.py#L54) ·
[Sentence caller](../../python/corpus-structure/src/corpus_structure/semantic/sentence_products.py#L1458) ·
[Formal caller](../../python/corpus-structure/src/corpus_structure/semantic/formal_products.py#L1187) ·
[Native sharing](../../python/corpus-structure/src/corpus_structure/semantic/rule_establishment_native.py#L260) ·
[Named rules](../../python/corpus-structure/src/corpus_structure/semantic/constructions/declared_named.py#L19)

The accepted premise contract still requires independent rule identities and authenticated
inputs. Exercise shared premises across rules, different observations over the same packet,
a changed observed field, invalid inventory and two reports matching the same construction.
Existing witness checking already builds one candidate-key set per group and should be the
baseline for extending shared grouped validation.

<a id="I02"></a>
### I02 — Make the annotation fork typed from acquisition through publication

**Proposed · first substantial analytical integration for SBX-01–04/07–09.** Partition
assembly encodes canonical items, tags them and independently projects field-group digests.
Canonical processing decodes, derives addresses, tags again and prepares canonical bytes.
Current reuse correctly separates the local template from current placement. Construction
already narrows work to the selected partitions. Change the full responsibility: acquire the
relevant columns and ordered membership once, bind canonical and construction consumers to
that typed population, and derive exact encodings at the commitment and publication
boundary. Scope logical values by release, schema, digest and address declaration. Attach
current placement and support at use. Eliminate tagged-to-Arrow input creation,
worker-to-Python restoration and duplicate per-consumer inventories where the new path owns
them. Keep a deliberate boundary for provider-specific formats and exact encoding.
[Partition encoding](../../python/corpus-structure/src/corpus_structure/semantic/data_operation_partitions.py#L116) ·
[Canonical reuse](../../python/corpus-structure/src/corpus_structure/semantic/canonical_sentences.py#L129) ·
[Construction inputs](../../python/corpus-structure/src/corpus_structure/semantic/construction_products.py#L896)

Compare an Acero `Declaration` from `RecordBatchReaderSourceNodeOptions` through native
project/filter/group or join nodes and `to_reader()`, direct kernels and the existing carrier.
Use one DuckDB computation over `from_arrow()` when windowing, cross-relation folding or
ordering makes that formulation simpler. One graph can share several aggregates; grouping,
joins and global ordering may retain working state. A reusable fork needs an owned compatible
buffer, materialized result or artifact. The bounded control consumed the input reader once
and verified that DuckDB refuses a second scan. Retain a single worker format after selecting
the complete path. Use process-boundary IPC only when needed, and consume C Stream directly
within a process where supported. The producing owner chooses one representation, with
fixed-schema forms for known products and explicit canonical values for any domain distinctions
outside the engine's type range. [Library control](../design_review/evidence/2026-11-22_sbx-analytical-redesign/README.md)

The first end-to-end decision slice is annotation acquisition through canonical publication
and named construction. Use exact digest and output checks for unchanged, moved, renamed,
repeated, split and merged blocks, duplicate ordinals and independent report positions.
Preserve layout meaning, null/presence, adequate numerical range, rule premise and current
address correspondence. Advance the SBX-18/19 mechanism choice for this slice if acquisition
and both consumers can move together. Defer a partial port that temporarily adds a second
normal carrier.

For durable layout, start with purpose-scoped relational members for fields used in live
joins or point reads, and a typed immutable artifact for wide payloads already owned by
workers. Compare those with a typed projection over the present storage. A projected legacy
packet can validate consumer feasibility, but retaining it as the permanent bulk source
would keep the cost of constructing that packet. Co-publish under one owner where both an
addressable relation and an artifact serve real consumers. A projection must be reproducible
or authenticated and retired with the original publication. Choose representation by access
pattern and consistency requirement so that every product does not acquire both forms.

<a id="I03"></a>
### I03 — Separate keyed selected access from finite analytical reads

**Proposed · SBX-05 and an enabling SBX-11/12 slice.** First item resolution currently decodes
and indexes a complete selected partition. It then deep-copies each returned item. A larger
selected native read already materializes bounded obligations and shares selected uses, but
assembles tagged product envelopes before the next consumer can request a projection.
Parquet demand export then reads JSON spool bodies into Python and reconstructs batches.
Add a model-derived keyed read over the guarded relation before envelope construction,
with compact metadata and selective item access for points, and a typed reader for finite
selections. Share the acquired view/index within its validity. Authorize each actual use in
the relevant cut, even after a cache hit. Rework export and detached replay together so the
typed result reaches `ParquetWriter` and the exact verifier without the intermediate JSON
spool for that route. Carry canonical columns where needed for identity, and publish one
authenticated artifact. Compare a single-use reader to Parquet only when a second consumer,
independent replay or recovery has meaning.
[Resolver](../../python/corpus-structure/src/corpus_structure/semantic/reference_resolution.py#L147) ·
[Native selected projection](../../python/corpus-structure/src/corpus_structure/semantic/data_operation_projections.py#L1888) ·
[Demand export](../../python/corpus-structure/src/corpus_structure/serve/demand_export.py#L360)

Use indexed native point access, PostgreSQL bulk reduction, DuckDB semi/anti joins and
`EXCEPT ALL` across an admitted finite population according to request shape. Use keyed
recursion only for a finite closure requirement and include the full role and occurrence
identity in the key. A prior probe shows why a node-only key loses a support arm.
For Parquet, evaluate needed columns, file and row-group pruning, actual scans and
atomic manifest publication. Check missing item inside a valid partition, both independent
producer positions, revoked use, historical scope, digest or range corruption, and fresh
detached replay. Point and empty-answer work should follow the relevant index and proof
scope. Advance the guarded typed interface before SBX-09 only where its actual remaining
reader or validation journey can consume it. Carry the general read program and archive
retirement with SBX-11/12. [Prior boundary control](../design_review/evidence/2026-11-22_sbx09-review/README.md)

<a id="I04"></a>
### I04 — Keep live mutations set-shaped within their transaction

**Proposed · SBX-06 follow-through.** Current attachment prepares support scopes, locks their
ordered union once and slices fresh trust per item. Completion canonicalizes once for both
intent and digest, and settlement uses the retained seal. Preserve these gains. Remaining
attachment work includes per-item JSONB cache and result-array reconstruction. If native
evidence identifies this as material, compare one transaction-owned ordinalized staging
relation with per-item outcomes and a single ordered aggregation. Keep the savepoint or
equivalent isolation where an individual refusal must leave other inputs eligible. Avoid
adding a second engine around native row locks and wake selection. Existing sparse durable
wakes and exact recipient selectors fit their workload.
[Attachment](../../python/corpus-structure/src/corpus_structure/semantic/request_attachment_native.py#L2179) ·
[Completion](../../python/corpus-structure/src/corpus_structure/semantic/data_completion_settlement_native.py#L1144) ·
[Wake owner](../../python/corpus-structure/src/corpus_structure/semantic/obligation_wake_native.py)

Use retained event receipts before creating a new scenario. When additional validation is
authorized, distinguish wait time, guarded reader work, attachment and completion with
the existing exact event journey and an independent refusal case. Exercise both commit
orders, retry, concurrent claim and protected or revoked support. A bound ADBC array of
parameters runs each binding on the server. A single Arrow result stream supplies no
set-shaped execution benefit for that DML.

<a id="I05"></a>
### I05 — Certify PDF streams over their existing typed inputs

**Proposed · SBX-08/09 supporting boundary and SBX-16/17 realization.** PDF certification
expands Arrow into Python rows, inserts each into SQLite, turns artifact bytes into hex and
back, and builds sortable identity frames one at a time. It already has authenticated IPC
and a captured lowering policy. Replace the temporary row store, hex bridge and repeated
passes together with typed projection, joins, ordering and the necessary canonical identity
fold. Compare a native Arrow/Acero path with DuckDB when ordering, membership and verifying
several stream families fit a single relational plan. Keep stable identity-frame ordering and
the exact fold. A smaller immediately usable change is to keep build comparisons and distinct
stream IDs columnar before the existing fresh native verification probe.
[Certification](../../python/corpus-structure/src/corpus_structure/semantic/pdf_certification.py#L142) ·
[Payload conversion](../../python/corpus-structure/src/corpus_structure/semantic/pdf_payload_validation.py#L113) ·
[Shared verification](../../python/corpus-structure/src/corpus_structure/semantic/pdf_shared_streams.py#L431)

Consider one verified immutable file handle or mapping per invocation to replace repeated
whole-file verification only while the exact bytes remain under the same custody owner.
Retain checks at recovery or external transfer. Validate post-encoding tamper controls,
shared and unreferenced streams, empty streams, raw binary payload, exact roots, policy
differences and cancellation/reclaim. Bring forward the columnar omission check or the
custody correction if it directly removes SBX-09 work. Incorporate the complete certification
replacement with SBX-16/17 unless the SBX-09 path can retire its row store in the same slice.
[Replay verification](../../python/corpus-structure/src/corpus_structure/ingest/pdf_stream_types.py#L92) ·
[IPC lifetime](../../python/corpus-structure/src/corpus_structure/orchestrate/pdf_streaming.py#L76)

<a id="I06"></a>
### I06 — Give each typed value one lifetime and each invocation one resource owner

**Proposed · SBX-08/09 and the SBX-18 execution contract.** The sentence partition-body
cache retains a frozen tagged tree and frozen Python rows. Its weight is the length of the
encoded tagged and canonical forms. That is a useful input-size proxy and can substantially
misdescribe retained object memory. Choose one compact owned representation, with views
scoped to the consuming invocation. For Arrow, account for retained backing buffers and
prevent tiny long-lived slices pinning disproportionately large inputs. Keep existing
byte-bound admission and acquired immutable custody. The exact allowance and caches have
separate purposes.
[Partition cache](../../python/corpus-structure/src/corpus_structure/semantic/sentence_partitions.py#L85) ·
[Weight enforcement](../../python/corpus-structure/src/corpus_structure/caches.py#L199)

Put Arrow CPU/I/O pools and scanner readahead, DuckDB threads and spill, provider work and
active worker counts under the existing execution policy. Native threadpool control already
covers compatible BLAS/OpenMP libraries. Establish engine settings at process startup or
invocation ownership as appropriate. DuckDB's buffer-manager limit and Arrow's pool
accounting cover different allocations. Model boot, object graphs, queues, mapped files and
spill need their actual owners to release them. Use a bounded slow-consumer and early-exit
comparison when selecting a streaming path. Inspect blocking state, cancellation drain,
connection and file release, and total process memory across successive invocations.
[Execution policy](../../python/corpus-structure/src/corpus_structure/core/execution_policy.py#L15) ·
[CPU worker limits](../../python/corpus-structure/src/corpus_structure/semantic/cpu_execution.py#L258) ·
[DuckDB owner](../../python/corpus-structure/src/corpus_structure/analytics.py#L131)

<a id="I07"></a>
### I07 — Reuse the exact-snapshot ADBC path and choose write ownership deliberately

**Proposed · early enabler for I03, with SBX-12 and PDF adoption following their consumers.**
Companion export already exports the authorized PostgreSQL snapshot, imports it into an
independent ADBC read transaction, then reads binary COPY into Parquet. Reuse that pattern
for eligible bulk projections, with SQL filter and projection before packet expansion.
Compare a same-session PostgreSQL projection/COPY where uncommitted state is necessary.
An imported snapshot sees the authentic committed cut available to the purpose role.
A separate session cannot borrow temporary relations or uncommitted writes. Pin the
declared schema and release and retain transaction and reader ownership through drain or
cancellation. Start with `fetch_record_batch()`. Consider `fetch_arrow()` where the direct
consumer can take ownership of a C Stream and remove an adapter. Wire decoding allocates
Arrow buffers. Establish actual ownership beyond that boundary before claiming zero-copy.
[Companion exporter](../../python/corpus-structure/src/corpus_structure/serve/companion_export.py#L123) ·
[ADBC cancellation and settlement](../../python/corpus-structure/src/corpus_structure/core/db/adbc_lifetime.py#L116)

Unbound COPY-compatible and bound-result routes have different buffering. The tagged 1.13
driver supports positional bound results and uses `PqResultArrayReader`, potentially with
a full `PGresult` per binding. The COPY byte hint does not apply there. An incompletely
consumed multi-binding `RETURNING` stream may leave bindings unexecuted. Use server-side
set preparation for many selectors. Scope parallel extraction to actual disjoint partitions
over one imported cut if transfer is established as a bottleneck. The PostgreSQL driver
does not implement ADBC's generic partitioned read API.
[Tagged statement](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/statement.cc) ·
[Tagged result reader](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/result_reader.cc)

Compare `adbc_ingest(mode="append", db_schema_name=…)` with pgpq/Psycopg for a complete
staging-and-promotion responsibility. Target-aware ingestion can remove bespoke binary
encoders for supported destination types. The existing COPY path borrows the caller's
transaction so it can see scratch state and authenticate and promote atomically. Keep it
where that ownership yields the simpler design. Adopt ADBC ingestion only for a coherent
ADBC-owned operation and supported schema, with explicit rollback and commit. Verify
exact type mappings, omitted/default columns, constraint errors, failed promotion and retry.
Confirm large binary and nested writes in the installed versions if required. NUMERIC
output is string-backed. JSON/JSONB retains metadata but needs interpretation. Timestamp
precision, arrays, composite write support, and UUID mappings each require an exact
contract at the selected boundary.
[Current COPY profile](../../python/corpus-structure/src/corpus_structure/semantic/arrow_transfer.py#L55) ·
[ADBC reference and addendum](../libraries/postgresql/adbc-driver-postgresql.md)

Builtin resolution already serves export. Server resolution and shared `AdbcDatabase`
with `adbc_clone()` deserve consideration if repeated custom-type discovery is consequential.
Clones share that resolver and establish separate PostgreSQL sessions. Pooling must account
for purpose, transaction state, type generation after relevant DDL and canceled borrowers.
Use query schema negotiation where it removes bespoke metadata inference.
`adbc_get_table_schema()` omits information available on a result schema. Approximate
statistics can guide planning. Native catalog and model authorities establish exact structure
and permissions. Preserve SQLSTATE and cancellation evidence where available.
[ADBC 25 driver documentation](https://arrow.apache.org/adbc/25/driver/postgresql.html)

Compare DuckDB's PostgreSQL extension and community `adbc` only as complete read
placements. `read_adbc()` can run explicit remote SQL. The community extension documents
autocommit-only operation and no automatic attached-table predicate pushdown. The export
transaction, role and pin must stay under the explicit PostgreSQL/ADBC owner unless a
candidate establishes the same contract. Community extension loading and new database
experiments were `not_run`. Native validation should compare exact results while a concurrent
commit occurs after pin acquisition, assert role refusal, and prove end-of-stream and
early-close cleanup before returning or discarding a session.
[Community extension contract](https://duckdb.org/community_extensions/extensions/adbc)

<a id="I08"></a>
### I08 — Reuse current preparation and bound the next qualification campaign

**Proposed · first before a resumed SBX-09 run.** Eight simultaneous managed invocations
each had their own workers and private clusters. Session-scoped preparation is shared
within one session, so concurrent sessions can replicate model preparation, installed
database state and provider processes. Reconcile prior identities and exact source, root
and provider context, then run the outstanding cohort under one managed owner with bounded
native activity. Reuse authenticated preparation and per-test commit clones where they
preserve isolation. Start with one cohort. Raise concurrency only based on observed
headroom and cleanup. Compare a single execution with bounded cohorts using existing
receipts and host/process observations. Preserve native/provider evidence and interrupted
outcomes. The pause and relief establish the operational trigger. The relative memory
contribution of individual libraries, test paths and allocators remains open.
[Session fixtures](../../tests/conftest.py#L377) ·
[Prior I07](set-based-execution-validation-and-postgresql_2026-11-22.md#I07) ·
[Interrupted scope](../plans/set-based-execution/cutover-and-qualification.md#sbx-09-qualification-pause)

## Capability coverage and evidence

Reviewed complete local references and addenda for [PyArrow](../libraries/analytical_infrastructure/pyarrow.md),
[DuckDB](../libraries/analytical_infrastructure/duckdb_2.md), the
[DuckDB CLI](../libraries/analytical_infrastructure/duckdb_2_cli.md) and
[ADBC PostgreSQL](../libraries/postgresql/adbc-driver-postgresql.md). Prior discovery used
Context7 and versioned primary references. The adjudicating baseline is PyArrow 26.0.0,
DuckDB Python and CLI 2.0.0, and ADBC PostgreSQL 1.13.0. The ADBC addendum corrects the
main text about bound results. The tagged implementation resolves that conflict. The
local probe covers installed Arrow and DuckDB behavior. ADBC feasibility uses source
and earlier exact-snapshot receipts.

| Capability families screened | Fit for this footprint |
|---|---|
| Arrow types, schema/extension metadata, dictionaries, compute, Acero, datasets and scanners | Use model-derived schemas, exact casts and projection/grouping for known types. Preserve domain distinctions as explicit columns or canonical values. Dictionary codes are scope-local. Arrow structural validation supports the physical boundary. Accepted domain, attestation and authority checks retain their meaning. |
| Arrow IPC, C interfaces, buffer slicing, NumPy and DLPack, memory pools and runtime control | Favor compatible same-process buffers and IPC for a real process boundary. Consider projected or memory-mapped IPC for immutable shared input. Numerical buffers fit genuinely compatible model input and output. Verify reference lifetimes, nulls, dtype and alignment. |
| Arrow filesystems, remote transport, Flight, Substrait, UDFs, native plugins and encryption | Revisit only where a real remote/cross-runtime consumer or a kernel currently lacks a viable native route. Native expressions and direct local exchange cover the candidate paths. Flight servers, generalized native extensions and new encryption layers have no identified responsibility to remove here. |
| DuckDB nested types, list operators, VARIANT, windows, grouped and ordered aggregates, join forms, macros, keyed recursion, statistics, indexing and profiling | Assess exact nested and relational operations in I02/I03/I05. Use typed forms for known schemas, explicit ordinality and role keys, and keyed recursion for justified closure. Evaluate VARIANT only for genuinely heterogeneous values with parity evidence. Prefer optimizer-visible expressions to Python callbacks. Inspect plans and selected spill metrics where they inform a decision. |
| DuckDB graph, spatial, full-text and vector extensions, asynchronous I/O | Scoped relational closure and direct predicates already cover the identified needs. Revisit graph or spatial facilities for a specific persistent access workload. Exact retrieval and declared ties constrain vector placement. Approximate retrieval or new search capabilities need a separate functional decision. Tune asynchronous I/O when file scans are an established constraint. |
| Parquet, native DuckDB persistence, compression, cataloged snapshots, DuckLake/Delta/Iceberg and remote/Quack execution | Select IPC for a process boundary and Parquet for reusable or independently consumable projections. Check pruning and total lifecycle, including publisher custody. Add a catalog or remote service only for an identified multi-consumer snapshot, recovery or coordination need. Native PostgreSQL retains live transactional authority in the recommended design. |
| CLI inspection, output modes, MCP, extension and remote discovery | Use `-no-init -bail -no-agent`, `DESCRIBE`, catalogs and structured `EXPLAIN` for small exact diagnostics. Agent previews, hashes and compact plans help exploration. Use typed comparison for exact evidence. Python or a native library owns the execution boundary. No production subprocess or new MCP/server surface is required. |
| ADBC DBAPI, low-level Arrow interfaces, COPY, binding, ingestion, schema/metadata and type resolution | Choices and limits are in I04/I07. Read and ingest fidelity differ by type. Generic ADBC facilities do not establish native driver support for Substrait, partitioned queries or named binding. Use observed schema and tagged behavior for the selected driver. |
| ADBC profiles/manifests, alternative dataframe backends, SQLAlchemy pool, libpq and structured errors | Prefer the current explicit driver/purpose contract. Profiles and manifest discovery fit a shared deployment only if it removes configuration duplication. Polars/pandas materialization lacks a scoped consumer. Shared resolver and independently initialized sessions are a plausible startup optimization. Inherit actual libpq connection and credential semantics. |

**Tested · 2026-11-22.** A six-row, two-batch fixture produced the expected compound groups
and two aggregates through both Acero and DuckDB. It detected an invalid span inside a
duplicate group and preserved the two report positions. DuckDB refused consumption of an
exhausted Arrow reader and succeeded twice after explicit materialization. A separate CLI
query exposed the grouped operator through structured `EXPLAIN`. These controls establish
composition and single-use boundaries on the selected versions. They do not qualify
production semantics or establish performance. The earlier Arrow/Parquet probe shows
projection and filter pushdown in the fixture plan. Actual file and row-group reads remain
a question for a selected production layout. The earlier probes also cover exact typed
examples, trust per lookup and multiplicity.
[New probe](../design_review/evidence/2026-11-22_sbx-analytical-redesign/README.md) ·
[Earlier Arrow/Parquet probe](../design_review/evidence/2026-11-22_sbx-common-analytics/README.md) ·
[Earlier selected boundary probe](../design_review/evidence/2026-11-22_sbx09-review/README.md)

## Integration order and open evidence

1. Resolve the SBX-09 execution conditions in I08 during plan revision. Select I01 and
   the narrowly useful parts of I06/I05 where they eliminate current work without building a
   temporary format. Preserve the original acceptance and sole-root correspondence.
2. Make I02 and I03 concrete together at the keyed and bulk acquisition boundaries. The
   annotation fork is the first complete product slice. The exact selected export is the
   first cross-database slice for I07. Change source storage and consumer contracts together
   where that removes a representation. A scope decision should compare total acquisition,
   transformation, custody, final output, cleanup and the migration of all affected consumers.
3. Bring forward the SBX-18/19 choice only for complete slices that improve SBX-09 readiness or
   retire material work. Otherwise complete the existing foundation with I01/I06/I08 and
   place the full rollout with those later owners. Fold I05 into SBX-16/17 and the broad typed
   archive into SBX-11/12. Keep I04 residual mutation optimization conditional on meaningful
   remaining cost. Route a change to authority or identity through its existing design owner.
4. Qualify changed routes with independent expected product, evidence and failure outcomes
   valid for the selected design. Compare time to first and final consumer, retained memory,
   scans, write and transfer volume only where these could change the decision. Per-kernel
   speed alone cannot justify the added boundary or custody.

Native database operations, provider execution, cold installation and product qualification
were `not_run` in this review. There is no production speed or memory attribution claim.
Recommendations are proposals for subsequent plan revision.
