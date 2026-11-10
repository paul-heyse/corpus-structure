# Explicit acquisition, honest inspection and research access

**Status: Planned; execution not started · 2026-11-09.** Target design is Proposed. The
[coordinator](../postgresql-typed-domain_2026-11-09.md) owns all package/decision state, source
correspondence and combined qualification. This companion owns the design and local acceptance
below, not another status table. No product or database changes were made while authoring.

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
