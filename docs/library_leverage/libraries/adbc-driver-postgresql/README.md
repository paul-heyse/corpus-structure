# adbc-driver-postgresql

**Realization assessed:** adbc-driver-postgresql 1.13.0 (driver-manager 1.13.0).

**Researched:** 2026-10-29 by the R5 cluster.
- The [overview](../../../libraries/adbc-driver-postgresql.md) was read end to end.
- Context7 documents main; it was cross-checked against the installed `dbapi.py`.
- ADBC `database.cc` was read at tag `apache-arrow-adbc-25`.
- No database connection was made
  ([evidence](../../../design_review/evidence/2026-10-29_library-leverage-arrow/README.md)).

## Reusable opportunity types

<a id="adbc-driver-postgresql-snapshot-consistent-capture"></a>

### `adbc-driver-postgresql/snapshot-consistent-capture`

**Need.** Read several relations into Arrow under one database snapshot that another session
exported.

**Mechanism.**
1. The exporting session runs `pg_export_snapshot()` in a REPEATABLE READ transaction.
2. The bulk session connects with
   `dbapi.connect(uri, db_kwargs={"adbc.postgresql.type_resolver_mode": "builtin"})`.
3. It turns `adbc.postgresql.use_copy` off for the `SET TRANSACTION …` statements, because COPY
   cannot wrap them.
4. It turns it back on and issues one COPY per relation.
5. `cursor.fetch_record_batch()` streams the results. `batch_size_hint_bytes` is a hint only.

**Conditions.**
- Result queries take no bound parameters, so SQL must be rendered with literals.
- NUMERIC arrives as a string carrying `POSTGRESQL:typmod` metadata; JSON and JSONB arrive as
  `arrow.json`. Casting to text in SQL gives PostgreSQL's own lexical form.
- `builtin` mode cannot resolve composite or user-defined types, and `auto` is not implemented.
- `AdbcDatabase.Init` opens and closes a transient session before the connection's session, so each
  `connect()` makes two PostgreSQL sessions (source).

**Residual.**
- Keeping the exporting transaction open until import completes.
- The isolation and READ ONLY statements.
- Rollback and close.
- Mapping to target types.

<a id="adbc-driver-postgresql-conninfo-connection"></a>

### `adbc-driver-postgresql/conninfo-connection`

**Need.** Build the Arrow bulk connection from the same libpq connection authority the main client
uses.

**Mechanism.**
- The `uri` option is passed verbatim to `PQconnectdb`, so both URI and `key=value` conninfo forms
  work.
- `adbc_driver_manager.dbapi.connect(driver=<path>, entrypoint=…, db_kwargs={"uri": …})` loads a
  specific driver library.
- Version 1.13 also offers TOML connection profiles.

**Conditions.**
- The wheel statically links its own libpq. Its version is unverified and may differ from the main
  client's.
- PG* environment variables and `.pgpass` apply to both libpq copies.
- Profiles add a second configuration authority.

## Applicability at source `d739b88` (re-checked at `3d97504`, plus concurrent `7cfd7f8`)

<a id="applicability-cbo-007"></a>

### CBO-007 — analytical capture connection: **fits with conditions; premise corrected; adopted concurrently**

**Opportunity:** [CBO-007](../../codebase/consumers-and-operations.md#cbo-007). **Types:**
snapshot-consistent-capture, conninfo-connection.

**Already correct.** `load_packet` uses snapshot-consistent capture correctly: `builtin` resolver,
`use_copy` toggled, literal SQL, NUMERIC and JSONB cast to text, rollback in `finally`.

**Premise correction.** The claim that "capture needs a separate libpq URI and driver path"
overstated the gap.
- At the baseline, `Settings` already held a libpq URL and `analytics.adbc_driver_path`. The empty
  engine URL from `open_store` is real but irrelevant, because Settings is the source.
- Since `3d97504`, `connection_settings(settings, "read")` derives the restricted reader's URL, which
  libpq parses correctly. `make_conninfo(url, application_name=…)` can add per-capture keywords.

**Concurrent evidence.** SP-08 commit `7cfd7f8` added `ci export`. It calls
`load_packet(session, connection_settings(settings, "read").database.url, driver_path=…)`, which is
exactly this route.

**Residual.**
- Taking `AnalysisScope` resources from `AnalyticsSettings`.
- Ownership of `application_name`.

**Unsettled.**
- Whether the bundled libpq accepts every conninfo keyword in use. Today that is only user, dbname,
  host and port.
- PostgreSQL's role rules for importing a snapshot.

**Ruled out for this context.** Connection profiles, because they would duplicate the
pydantic-settings authority.

<a id="applicability-cbo-004"></a>

### CBO-004 (informs)

ADBC and psycopg both take libpq conninfo, so one purpose-specific URL authority
(`connection_settings`) serves both. The remaining difference is that two libpq builds are in play.

## Coverage limits

- No database connection: snapshot import and COPY behaviour are known from documentation and source
  only.
- The version of the bundled libpq was not established.
