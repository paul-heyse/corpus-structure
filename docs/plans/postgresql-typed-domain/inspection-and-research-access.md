# Explicit acquisition, honest inspection and research access

**Status: Complete for selected delivery; investigation decisions retained, combined PTD-11 acceptance recorded · 2026-11-10.** Selected package delivery is Tested at the scope recorded by the coordinator; conditional targets remain Proposed. The
[coordinator](../postgresql-typed-domain_2026-11-09.md) owns all package/decision state, source
correspondence and combined qualification. This companion owns the design and local acceptance
below, not another status table. The coordinator records execution and native delivery separately from original authoring.

## PTD-02 · One ADBC acquisition policy owner

Consumes [O12](../../functional_reviews/postgresql-typed-domain_2026-11-09.md). Move the configured-driver acquisition function from analytics to the
existing core/db boundary. Inputs are explicit purpose-derived connection settings, configured native
driver path, resolver mode and supported operation cancellation. Preserve builtin for ordinary capture
and server discovery for database description; no new pool or second settings authority.

Compose acquisition with owned_adbc_read. Cursor and reader lifetime stays inside the borrowed
physical session; rollback and close are attempted independently while retaining the primary exception
and each cleanup failure. A failure before returning a session owns no returned session. Migrate
analytics capture, companion export, CLI export and database description; remove direct acquisition
and the old analytics factory after all imports move. Cloning type-cache/database objects does not
copy a snapshot or transaction. Verify configured-driver parity, intentional resolver differences,
read-only principals, acquisition failure and original-plus-cleanup failures without a mock-provider
claim of native success. Existing capture snapshot import and literal COPY route remain unchanged.

## PTD-03 · Attributed observed types

Consumes [O10](../../functional_reviews/postgresql-typed-domain_2026-11-09.md); requires working PTD-02. Extend existing DatabaseDescription observations
with the producing metadata interface/source and observed PostgreSQL/Arrow type metadata. Expose
available type identity, numeric typmod and extension facts while retaining unavailable declared
nullability/domain definitions. Use separately observed Inspector constraints when requested; Arrow
nullable is not PostgreSQL NOT NULL. Optional released bindings identify their source/revision and
are not inferred from a display type name. Multiple sessions do not establish one atomic snapshot.

Keep bounded schemas/relations/columns/bytes, principal, observation time and read-only behavior.
Use current ci db describe and JSON materialization; add no general query executor. Change machine
output with an explicit report-version/support decision at its owner, migrating formatters/consumers
and removing blanket metadata discard. A prospective expression schema can legitimately report
more typmod detail than table schema. Missing information remains unknown rather than guessed.

Acceptance covers constrained numeric table field and computed expression output, user-defined or
opaque type, inaccessible relation, unavailable constraints and bounded overflow. Independent catalog
expectations and known Arrow metadata challenge the formatter, not a report generated from itself.

## PTD-I05 · Research and exchange route decisions

Resolve each separately: parameter description/bound read, Arrow capsule/stream consumer, offline
replay, external target-aware ingestion, live federation and alternate query laboratory. The selected
initial research consumer is an independent Arrow reader and detached comparison of the current
four companion families, covered by PTD-08. Prefer that source/pin-bound route for reproducibility.
Live exploratory access must state its different completeness/snapshot guarantees.

For parameters, current D8/admit_sql selects parameter-free SELECTs. Develop a concrete finite
positional-parameter proposal and obtain accept/reject before fixing a changed profile. If accepted,
explicitly declare/infer bounded types, refuse ambiguity, forbid effects and retain release/role
admission. adbc_prepare describes inputs and adbc_execute_schema outputs; neither authorizes execution.
Bound PGresult results may buffer each binding and execute later parameter rows during consumption;
they are not incremental COPY. Preserve existing COPY for large capture unless a complete better
route is established. A rejected profile change closes these branches by retaining the support rule.

Capsule consumers need single ownership and reader close before session reuse, plus schema/pins and
cancellation. Prefer existing Parquet/IPC manifests for offline replay. FileWriter binary COPY needs
a type/schema/version manifest and atomic publication; not a portable self-describing replacement.
An ingestion branch needs a real input contract and the proper observation/publication owner; ADBC
cannot borrow Core's protected session. Select it only when a complete independently owned staged
operation preserves admission; otherwise retain Psycopg/pgpq. create_append does not supply migration.

For federation, compare explicit remote SQL/read_adbc with ATTACH and existing detached capture;
qualify filter pushdown, autocommit/concurrency and cache semantics before choosing the community
extension. No second instance authority. Each selected route becomes a bounded PTD-10 slice with an
actual consumer, exact support limits, producer/consumer migration and independent failure/success
cases; each other route closes with a reason and revisit condition.

Sources: [description](../../../python/corpus-structure/src/corpus_structure/serve/database_description.py),
[owned cleanup](../../../python/corpus-structure/src/corpus_structure/core/db/adbc_lifetime.py),
[ADBC25 APIs](https://arrow.apache.org/adbc/25/python/api/adbc_driver_manager.html),
[selected result reader](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/result_reader.cc),
[exchange review](../../functional_reviews/postgresql-typed-domain/analytical-exchange.md).

## PTD-02 concrete execution mechanisms · 2026-11-09

The existing core/db/adbc_lifetime owner exposes open_adbc_connection(uri, *, driver_path,
resolver_mode). URI is already purpose-derived; resolver is explicitly builtin or server and
validated before driver invocation. Installed acquisition uses postgres dbapi.connect with
adbc.postgresql.type_resolver_mode; configured acquisition uses manager dbapi.connect with
AdbcDriverPostgresqlInit and URI/resolver database options. No new settings authority/pool/cache.

Capture/export retain builtin, COPY-disabled snapshot setup then literal bulk COPY; description
uses server and the configured driver with owned_adbc_read, preserving its current metadata.
CLI export retains configuration forwarding. The existing ownership helper retains the primary
exception reaching it, independently attempts rollback/close, attaches cleanup failures and
synchronizes cancellation retirement. Reader/cursor cleanup can replace an earlier body error
before reaching that owner; CA02 identified this incomplete original-error preservation, now repaired below. No separate
operator authorization for narrowing the accepted requirement was established. Synchronous connect
cannot be interrupted through a borrower registered afterward. Native manager partial-acquisition
cleanup does not guarantee preserving every acquiring exception. Type-cache clone is not a snapshot.

Focused checks include actual configured-driver parity, server custom-type resolution, read-only
roles, session isolation, snapshot/COPY controls, cancellation and no surviving owned sessions.
Mock factory checks establish unit behavior only. ADBC1.13.0 contracts are checked against installed
sources and the [selected upstream implementation](https://github.com/apache/arrow-adbc/tree/apache-arrow-adbc-25).

## PTD-03 execution contract · 2026-11-09

Emit database-description-v2. Attribute Inspector/GetObjects/GetTableSchema/ExecuteSchema/
GetStatistics observations to their interfaces and separate sessions. Retain recursive Arrow
storage/extension fields, arrow_nullable and arbitrary metadata as base64; interpret recognized
POSTGRESQL:type/typmod and Arrow extension keys without synthesizing unavailable native identity,
constraints or domain meaning. Preserve signed numeric typmod; no new decoder or parameter profile.
Count children/metadata under existing object/byte bounds. Selected ADBC1.13 sources add metadata
independently of Arrow storage and can expose different table/expression facts. Reader-purpose
ownership, server resolver, parameter-free admission and actual CLI JSON remain acceptance boundaries.

<a id="ptd-i05-decisions"></a>
## PTD-I05 decision account · 2026-11-09

**Source-inspected at `baea0ed8e`; design judgments Proposed.** The inquiry traced actual database
description, snapshot capture, AnalysisScope readers/Polars access, companion inventory/comparison,
source-bound annotations and PDF visual inputs. PTD-08 has already delivered the independent detached
consumer; that remains the selected research route. The review's suggested capsule/bound-query/import
journeys are alternatives to assess under the coordinator's conditional scope, not mandatory new
APIs after this consumer is delivered. No additional PTD-10 research/input slice is selected.

| Branch | Decision and comparison against the actual consumer | Specific revisit condition |
| --- | --- | --- |
| Parameter description | **Retain parameter-free authored query description.** `DatabaseDescriptionRequest`/`describe_database` bind a release, admit SQL, then describe its output without executing the query. Existing generated native calls already provide typed bound parameters for supported operations; adding a parallel authored parameter schema would not simplify that contract. The current description caller supplies no parameter values/type declaration. ADBC `adbc_prepare` could describe a finite positional profile, but this is an added D8 capability, not a current type-inspection defect. | An operator-facing query requiring independent typed parameters that cannot be expressed by existing generated calls or the admitted parameter-free query. Then present a concrete bounded positional profile, ambiguity refusal, input/output schema attribution and conforming current alternative under the coordinator's rule-decision route before fixing its target. I02 owns any changed language/analysis semantics. |
| Bound analytical reads and preparation reuse | **Retain typed Core calls for ordinary bound reads and snapshot-bound literal COPY for bulk capture.** `analytics.capture` sets repeatable-read/read-only, imports its source snapshot, enables COPY and consumes RecordBatchReader results through owned cleanup. Bound ADBC PGresults would introduce different buffering/execution behavior without replacing this custody. Installed DBAPI preparation reuse is on the same cursor for the same query, not a portable prepared object or general cache. | A selected small parameter-bearing research read whose complete bounds and snapshot/role/release admission make PGresult buffering appropriate. Declare consumption-driven later bindings and early-close behavior; do not describe this route as incremental COPY. Couple its profile decision to the row above and its preparation lifetime to I03. |
| Arrow capsule transfer | **Retain owned RecordBatchReader access.** Current capture already reads batches without compulsory whole-result PyArrow-table hydration; `AnalysisScope.reader` provides an explicitly scoped downstream reader. `BorrowedHandle` deliberately refuses an unowned `__arrow_c_stream__`; direct transfer would remove this lifetime guard while adding no required current consumer. Installed `fetch_arrow` supports one transfer before consumption, with subsequent data inspection forbidden. | A named external Arrow-compatible consumer that cannot use the current reader/detached package and benefits from the C Stream boundary. Specify one owner, retained schema/pins, close/cancel, early termination and closure before cursor/session reuse. |
| Ordinary Arrow/Polars streams | **Retain current AnalysisScope behavior.** DuckDB handles/readers borrow the scope; materialized Arrow/Python values detach; lazy Polars access is explicitly refused. The existing scope tracks readers and closes them before backing connections/capture leases. A second stream wrapper would duplicate that responsibility. | A real asynchronous/lazy or non-PyArrow consumer requiring a different lifetime. Its contract must extend the current owner rather than bypass it; cancellation and use-after-close cases become delivery obligations. |
| Offline replay and binary COPY files | **Retain manifest-bound Parquet with IPC schema.** Companion export verifies family files, six-part pins, logical/file identities and independent schemas; inventory and comparison read after disconnection. `FileWriter` binary COPY would add PostgreSQL type/version dependence and a separate replay importer while leaving the manifest/custody work necessary. | A selected PostgreSQL restore/replay consumer that needs COPY bytes rather than independent analytical reading. Deliver type/schema/server compatibility, atomic publication and admitted restoration then; a binary stream alone is not a self-describing dataset. |
| Target-aware ADBC ingestion | **Retain existing protected Psycopg/pgpq routes for current annotations/publication.** The source-bound annotation and same-session publication inquiry is recorded in the [input-family decisions](released-types-and-exchange.md#i05-input-decisions). ADBC `adbc_ingest` supports target modes, but an independently acquired session cannot borrow the current Core transaction. Creating/replacing tables would also add schema authority that the selected route does not need. | A real external structured dataset with an identified observation owner and one complete independently owned admitted staging transaction. Judge `append`, `create`, `create_append`, `replace` and temporary targets against that operation; generated DDL does not supply migration/admission. |
| Nested input, arrow-json, spatial and Rust | **Resolved separately in the input-family decisions.** Preserve current JSON directions and typed source geometry; defer nested native fields and Rust transport to their named missing-consumer triggers. These are investigated decisions, not pending unbounded probes. | Triggers and fidelity/lifecycle obligations remain in that one owning input section. |
| Live federation | **Retain explicit captured inputs and detached comparison.** Current analytical input contracts bind source snapshot, release, policy and declared universe; AnalysisScope can compose those inputs without a live remote table authority. `read_adbc`/remote SQL or community `ATTACH TYPE adbc` could supply interactive remote access, but none of the inspected companion/run-comparison journeys needs a continuously changing remote source. | An actual exploratory join across a live external data source for which fresh remote reads are the desired meaning. Compare explicit remote SQL first, then inspect selected extension pushdown, autocommit/concurrency, metadata cache and snapshot/freshness guarantees before choosing ATTACH. No extension compatibility or native parity is claimed here. |
| Alternate query laboratory | **Retain Core/Arrow/DuckDB for current released coverage, declared property views and companion comparison.** These workflows already combine bounded captured relations and detach results. SQLFrame or SQLGlot PythonExecutor/optimizer/acceleration would add another semantics/execution surface without a selected destination-specific question. | A concrete notebook or destination-comparison query beyond those facilities. I02 owns language/parity, I05 owns acquisition and result custody; use independently expected destination values and pin dialect/schema/transforms. Performance evidence is needed only if it changes the choice. |
| Metadata/statistics, driver profiles, resolver and clone extensions | **Retain PTD-02/03's explicit acquisition and attributed observations.** The current describer already requests native objects, Arrow query/table schemas and optional statistics, with unavailable freshness/constraints preserved. A second manifest/profile system would duplicate settings authority; cloning does not copy a snapshot and can share driver database/type caches. | A named missing inspection fact, independent driver deployment or type-generation lifecycle. Add the specific observation/loader at its existing owner; do not expand metadata merely because an API exists. I06 owns any selected long-lived cache-generation replacement. |

### Decisive sources and acceptance boundary

Repository source references above are relative to
`python/corpus-structure/src/corpus_structure/`. Key paths and inspected responsibilities:

- [Database description](../../../python/corpus-structure/src/corpus_structure/serve/database_description.py),
  lines29ff,164–190,350–445: explicit request, release/admission, statistics and output schema.
- [Analytics](../../../python/corpus-structure/src/corpus_structure/semantic/analytics.py),
  lines421–504,896–935,1199–1245,1457–1470: borrowing, snapshot/COPY capture, cleanup and reader scope.
- [Capture storage](../../../python/corpus-structure/src/corpus_structure/semantic/capture_storage.py),
  lines137–220: resident/spooled batching and retained ownership.
- [Companion export](../../../python/corpus-structure/src/corpus_structure/serve/companion_export.py),
  lines275–452ff: verified manifest/file/schema inventory and independent detached comparison.
- [Directional writes](../../../python/corpus-structure/src/corpus_structure/semantic/arrow_transfer.py),
  lines49–166: profile-derived schema checks, fresh encoder and same-session COPY.

Installed ADBC manager/PostgreSQL1.13.0 (upstream ADBC25) and Psycopg3.3.6 APIs were inspected on
2026-11-09 using `uv run --no-sync python -B` with `inspect.signature`, `inspect.getdoc` and selected
source locations. `adbc_prepare` documents same-query cursor-local reuse; `fetch_arrow` documents
single-use consumption; `adbc_ingest` documents destination modes. Their primary references remain
the [selected Python APIs](https://arrow.apache.org/adbc/25/python/api/adbc_driver_manager.html) and
[PostgreSQL result reader](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/result_reader.cc).
These source contracts settle the comparisons above without a new native or performance probe.

**Checks:** source/API inspection **passed** at the stated boundary. Product/native tests and
benchmarks **not_run** because this investigation selects no changed executable path. No native,
release, dependency or D8 support change is requested. The coordinator owns publication checks and
combined I disposition; historical PTD-02/03/08 verification remains historical scoped evidence.


## Completion audit · 2026-11-09

Shared acquisition is integrated, but child cursor/reader context exit can replace a body failure
before the connection owner observes it. The later source-mechanism description did not establish
an authorized exception to the original primary-error requirement. The repair requirement was to preserve the body
error and all child/connection cleanup failures through actual analytics/export/description callers.
PTD-03 metadata implementation was delivered; its outstanding control was to exercise an existing inaccessible
relation under the actual reader through ordinary JSON reporting. The coordinator's
[completion audit](../postgresql-typed-domain_2026-11-09.md#completion-audit) owns CA02/04 and required
closure evidence. Parameter/capsule/input/lab investigations remain excluded from this audit.


## Repair execution · 2026-11-10

The [coordinator delivery receipt](../postgresql-typed-domain_2026-11-09.md#completion-repairs-and-ptd-10-delivery--2026-11-10)
closes the local audit obligations at the scoped boundary and owns current disposition. Historical
audit descriptions above identify the inspected baseline, not an unrepaired current claim.
owned_adbc_child now retains body identity across reader/cursor/writer retirement and appends
nested cleanup errors before existing rollback/close settlement. Description metadata readers are
lexically owned; _rows no longer owns generator cleanup. The actual reader/CLI denied-version-table
control passed, distinguishing refused Arrow shape, available catalog facts and a missing literal.


## Final selected-scope adoption · 2026-11-10

The [PTD-11 closure](../postgresql-typed-domain_2026-11-09.md#final-qualification-and-series-closure--2026-11-10)
owns the final applicable functional/provider/native/nonfunctional union and adoption handoff.
Selected delivery is complete; conditional branches retain their recorded decisions and revisit
premises. Earlier receipts remain dated evidence, not new qualification by republication.
