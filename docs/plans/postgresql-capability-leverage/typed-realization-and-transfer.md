# Typed relational realization and directional transfer

**Implemented and targeted Tested,2026-11-01.** [Coordinator](../postgresql-capability-leverage_2026-11-01.md) owns PG-03/04/06 and PG-I02. Source [O04/O05/O06/O11/O13](../../functional_reviews/postgresql-capability-leverage_2026-11-01.md#O04) informs this design. This document selects the realization of prepared queries, write profiles and published-family transfer; [consumer capabilities](consumer-capabilities.md) owns the delivered Parquet/DuckDB interaction. The coordinator records the final selected functional/native qualification; quantitative benefits remain unmeasured.

## Current seams and the intended change

The inspected source already delegates binary encoding and transport. `semantic/arrow_publication.py::stage_schema/_encoder/stage_arrow` derives fields from `STAGE_TYPES`, constructs pgpq builders, checks the encoder's PostgreSQL schema, and streams through the caller's Psycopg driver. `semantic/pdf_staging.py::stage_schema/adopt_pdf_batch` separately derives fields through `pdf_record_model.record_arrow_schema`, constructs JSONB builders, checks incoming batch metadata and performs same-session scratch COPY/adoption. Neither is a bespoke COPY encoder. Their repeated model-to-wire decisions, not the library calls themselves, are the PG-04 consolidation target.

`semantic/analytics.py::compile_projection/load_packet` already prepares relational projection shapes, exports a Core snapshot, imports it into a fresh ADBC session and consumes columnar results. `semantic/pdf_record_reader.py::iter_rows` instead supplies bounded JSON/dict pages to small-item consumers; it reserializes selected JSON fields and decodes artifact hex. PG-06 adds an authorized typed companion route rather than sending that JSON-row function through another driver. The current bounded row reader and ordered native JSON event exporter retain their distinct uses.

During implementation, refresh these seams against the final PDF source. Migrate existing callers of these capabilities; do not import another series' publication, inference or adoption queue. The model and current native authorization contracts remain the source of meanings to realize, not frozen physical interfaces that prevent a better design.

## PG-03 — Model-derived static surfaces and reusable runtime preparation

### One declaration, three derived products

Extend the existing model compiler and Core metadata, not a separately authored transfer schema. For each selected operation/family derive:

| Product | Contents and owner | What it does not establish |
| --- | --- | --- |
| Static column surface | Generated `TypedColumns` declaration associated with the existing Core table/selectable; field names and Python value types come from the model | Live table existence, current privileges, row validity or native constraint enforcement |
| Prepared operation | Core expression tree, bound-parameter definitions, selected field order, directional profile and dependency identity | A live transaction, caller authorization or the result for a specific product pin |
| Native/transport realization | Generated protected typed function return columns, Arrow fields, supported PostgreSQL wire types and explicit normalization instructions | A second writable semantic definition or a reversible universal SQL/Arrow conversion |

SQLAlchemy's `FromClause.with_cols(GeneratedColumns)` associates a typed surface with a table-valued function, CTE or other selectable. It returns the same object without runtime validation. Generate the `TypedColumns` subclasses and their use from model declarations; do not maintain handwritten parallel column classes. Generic `Table`/selectable typing provides static column attributes without introducing an ORM identity map. The exact generated Python annotation syntax follows the latest stable SQLAlchemy API adopted in PG-00; its semantics are fixed here: absent column access and incompatible typed operation usage should be visible to Pyrefly, while native constraints and runtime profile validation remain separate.

**Worked shape:** the published relation projection has model-derived columns for relation identity/kind and product-qualified endpoint rows. Its generated `RelationColumns` surface is attached to the function's Core selectable with `with_cols`. An inventory query selects `relation_kind`, counts distinct relation identity separately from endpoint rows, and groups over explicit projected keys. Changing the product pin supplies new bind values to the prepared expression; it does not regenerate the model or add a new query class. A newly modeled endpoint role changes generated fields/profile and the consumers selecting that role. It does not silently acquire meaning from a JSON key. This is a target example, not a claim that these generated identifiers already exist.

The following **unexecuted generated-target sketch** uses the installed SQLAlchemy 2.1 annotation form, rather than a new typed-table wrapper. `generated_pin_parameters` is the generated tuple of typed `bindparam` arguments for the six pin fields specified under PG-06; `pin_values` supplies their invocation values. This abbreviated column surface selects only the fields needed by the illustrated consumer; generation also describes the remaining return columns. It does not create or execute the protected function.

```python
from sqlalchemy import BigInteger, Named, Text, TypedColumns, bindparam, column, func, select

class RelationColumns(TypedColumns):
    relation_id: Named[str]
    relation_kind: Named[str]
    endpoint_ordinal: Named[int]
    target_occurrence_id: Named[str]

rows = func.ops.read_published_relation_batch(*generated_pin_parameters).table_valued(
    column("relation_id", Text),
    column("relation_kind", Text),
    column("endpoint_ordinal", BigInteger),
    column("target_occurrence_id", Text),
).with_cols(RelationColumns)

stmt = (
    select(rows.c.relation_id, rows.c.endpoint_ordinal, rows.c.target_occurrence_id)
    .where(rows.c.relation_kind == bindparam("relation_kind", type_=Text))
    .order_by(rows.c.relation_id, rows.c.endpoint_ordinal)
)
# Core row consumer: conn.execute(stmt, {**pin_values, "relation_kind": selected_kind})
# Bulk consumer: bind these values, then dialect-render stmt for ADBC COPY SELECT.
```

`Named[str]` reflects the required occurrence identity in the current endpoint model; optional model fields use `Named[T | None]` where actually declared. `.with_cols` neither adds columns nor checks that the live function returns them. Generation and native/catalog admission must make those actual columns agree. The example's final ordering deliberately retains multiple endpoints instead of reducing them to one target per relation.

Use Core `select`, joins, CTEs, `lateral`, window operations, `Insert.from_select` and ordered aggregation where the actual operation benefits. For a relational staging-to-destination operation, express the population as `INSERT ... SELECT`; do not fetch rows to Python and reinsert them merely because the authority is declared in Python. Preserve existing effective native set SQL where changing notation removes no decisions or work. `Insert.from_select(include_defaults=True)` includes eligible client defaults; a Python callable default runs once for that statement, not once per selected row. Domain per-row derivation must therefore be explicit SQL or a different owned operation. Correlate `RETURNING` rows through explicit keys; do not zip unspecified result order with input order. [SQLAlchemy addendum §§1.1–1.7](../../libraries/postgresql/sqlalchemy.md).

### Reuse at the lifetime that actually applies

Prepare Core expression shape and ordered profile descriptions once per existing release/prepared-operation lifetime. The preparation identity includes the governing semantic release, physical realization/compiler revision and directional profile definition. Put reuse in that existing owner; no global query registry or durable preparation store is selected. Product/project/run/filter values and the exported snapshot are per invocation. A retained prepared value contains no connection, cursor, transaction, result reader or live privilege conclusion.

Engine compiled-statement caching handles eligible Core execution. Do not add another compiled SQL cache beside it. Custom SQL constructs use `inherit_cache` only when their SQL-affecting state really follows the parent cache contract; custom types use `cache_ok` only with stable, complete configuration. Start with ordinary reusable Core expressions. `lambda_stmt` is unnecessary for the selected fixed family operations; reconsider it only if a real changing composition repeatedly performs material Python construction work.

ADBC bulk COPY SQL uses direct dialect compilation, not Engine execution. Reuse the prepared Core shape, bind invocation values and render through PostgreSQL's dialect with `literal_binds=True` and named paramstyle, as `analytics.compile_sql` currently does. This preserves COPY-compatible unparameterized result execution and percent characters. Never interpolate caller text into SQL; identifiers/function names are generated from the selected model operation, while values use dialect literal rendering. Do not cache that rendered text as if a different product pin were the same invocation.

Psycopg prepared statements, registered adapters and ADBC custom-type resolution have physical-session/catalog-generation lifetimes. An execution shaped by an unchanged release may still require fresh session preparation after a native type or adapter configuration changes. Current fixed primitive companion projections use ADBC `type_resolver_mode="builtin"`; no shared custom OID cache or cloned-session pool is needed. If a selected future field requires custom types, its profile must state the new resolver/session lifetime before adoption. `TypeDecorator` and Core result processors do not run over raw pgpq bytes or ADBC batches; required normalization belongs in the actual directional execution path.

**Closure:** generate one real family surface and exercise a consumer selecting its columns; a modeled field change updates the static/native/Arrow products together. Check wrong-column and supported incompatible-type examples through the repository's typing route, not by asserting annotations exist. Two product pins reuse eligible shape while yielding independently correct rows; a changed governing profile invalidates affected preparation. Native runtime refusal still catches deliberately invalid raw values. No cache-object identity assertion substitutes for correct changed-input results.

## PG-04 — Exact write profiles and same-session COPY/adoption

### Prepared profile contract

Use an ordinary immutable prepared value containing an ordered field specification and a builder factory, derived from current model/Core metadata. Its contract contains:

- Governing release/physical/profile identity and operation/family identity.
- Exact ordered Arrow fields, nullability and required schema/field metadata.
- Expected PostgreSQL **wire** type per field, including supported aliases; this is distinct from the final destination/domain type and its constraints.
- Per-field encoding instruction: default inferred encoder, selected text-to-JSONB builder, or an explicitly supported exact numeric/temporal route.
- The source-to-wire normalization/refusal rule, including presence/null and bounded extension encoding.

Store these facts once in the existing prepared realization. Construct builders and a new encoder for each COPY stream; do not share native mutable encoder state or assume native builders can be safely mutated concurrently. The small factory construction is preferable to introducing a global builder cache whose validity is harder to establish.

Derive both current writer profiles through that capability. Ordinary `AppendPublication` presently permits all-nullable scratch columns and selected Decimal128 scale; private PDF staging uses the nullability/metadata of `record_arrow_schema`. Preserve these deliberate profile differences rather than make their schemas identical. Profile construction compares `encoder.schema().columns` against the expected wire order/type/nullability, normalizing only documented equivalent spellings such as `bool`/`boolean` and `int8`/`bigint`. For each actual batch, separately require complete schema equality, including metadata. pgpq's column-count/physical-type checks cannot detect swapped same-typed semantic columns.

**Worked JSONB field:** a modeled bounded JSON extension represented by Arrow `string` uses `StringEncoderBuilder.new_with_output(field, Jsonb())`; `large_string` uses `LargeStringEncoderBuilder`, and string-view uses `StringViewEncoderBuilder`. Supply a concrete dictionary containing a builder for **every** top-level field to `new_with_encoders`, with `infer_encoder` for the others. A null Arrow slot produces SQL NULL; the non-null string `"null"` produces JSON null. The profile does not parse arbitrary Python objects or collapse missing into either value. PostgreSQL still validates JSONB syntax/value restrictions. The supported Arrow physical representation is part of the profile, not an incidental choice discovered halfway through transfer.

Decimal128 is encoded exactly to PostgreSQL NUMERIC where selected; lexical arbitrary-precision values remain lexical when that is their declared representation. No float intermediary or unselected timestamp nanosecond truncation is permitted. ADBC read NUMERIC may arrive as text even when write NUMERIC uses decimal encoding. Preserve directional contracts rather than create a universal inverse type map. Do not introduce generated composites: current flat staging/model child relations avoid composite namespace/OID lifecycle, and pgpq DDL does not express the complete model constraints. [pgpq original §§3–5 and addendum §§1/2/3/4.4](../../libraries/postgresql/pgpq.md).

### Transfer sequence and ownership

Select Core transaction → checked existing Psycopg driver → pgpq stream → protected native adoption. The enclosing application operation owns checkout, transaction and retry. The shared transfer primitive consumes the explicit prepared profile, authenticated scratch target and batch iterator; it does not commit, renew task claims or decide publication visibility.

1. In the caller's current transaction invoke the operation's protected scratch-preparation function. Authenticate shape/owner as the current operation requires; do not issue arbitrary pgpq-generated persistent DDL.
2. Obtain `conn.connection.driver_connection`; require the supported Psycopg connection. A new driver connection would lose the transaction and session-local scratch.
3. Create a fresh encoder and check its output schema. Compose `COPY` with `psycopg.sql.Identifier(schema, table)` and an explicit ordered column list. Never pass a dotted name as one identifier.
4. Enter `cursor.copy(... FROM STDIN (FORMAT BINARY))`, write `encoder.write_header()`, then validate/count each incoming batch before `encoder.write_batch(batch)` and `Copy.write(bytes)`. Empty emitted chunks are valid buffering behavior. End with `encoder.finish()` before leaving the COPY context.
5. After successful COPY invoke the caller's protected adoption operation on the **same Core connection**. It independently checks actual scratch values, immutable source/replay identity and current fences before recording durable private membership or ordinary publication effects.
6. The outer transaction commits only after adoption succeeds. Commit acknowledgment/recovery follows PG-02's phase-aware outcome contract. A returned COPY count or footer is not a publication receipt.

Input rows/bytes and encoded working set are different. Enforce existing operation upload limits before encoding, retain oversized-scalar part handling and do not assume pgpq's roughly 1 MiB emission threshold caps memory. pgpq serializes a whole incoming batch before deciding to flush. Do not copy/retain every encoded batch merely to collect progress metrics.

If batch validation, encoding, COPY or adoption fails, propagate the error through COPY/transaction cleanup; discard the encoder and settle rollback before returning the connection. A Python encoder may contain partial native bytes after an error. Appending a footer or retrying another batch on it is invalid recovery. Replays obtain the caller's immutable replay source, create a new stream and use the existing adoption identity/conflict contract. The transfer helper never fabricates a retry policy or treats database rollback as encoder reset.

### Actual migration and PG-I02 decision

Migrate `arrow_publication._encoder/stage_arrow` and `pdf_staging.adopt_pdf_batch` to the profile factory/transfer mechanics while preserving their separate receipt, batch-limit and adoption owners. The ordinary publication constructor's whole-table canonicalization is not copied into the streaming path; eliminating unrelated constructors is not prerequisite to this consolidation.

Keep `publication.stage_batch` using Psycopg `Copy.set_types` and `write_row` for existing Python domain rows. These rows are already adapted through a suitable library; converting them to Arrow merely to call the new helper adds work. [Psycopg original COPY section and addendum §5](../../libraries/postgresql/psycopg.md) distinguish driver adaptation of rows from pre-encoded `Copy.write` blocks.

PG-I02 selects server-native relational operations for inputs already resident in PostgreSQL, and the current Core/Psycopg/pgpq owner for the two integrated writers. A standalone external Arrow import is not introduced as an additional consumer. ADBC `adbc_ingest(mode="append", temporary=True)` can instead own an entire temporary-ingest → protected SQL → explicit commit/rollback operation and adapt encodings to target names/OIDs. It is a credible complete alternative, but moving both integrated callers adds transaction/session integration while their native type profiles and protected adoption are already supplied. Target-aware ingest alone supplies no present reason for that migration. Do not open an extra ADBC writer to share another session's scratch, and do not retain parallel writers for hypothetical substitution. [ADBC addendum §§2/7](../../libraries/postgresql/adbc-driver-postgresql.md).

**Closure:** both actual Arrow writers use the shared preparation with independent expected rows/bytes for SQL versus JSON null, decimal extremes, empty/reordered batches, metadata mismatch and large individual values. Refuse a swapped same-typed column before native adoption. Force encoder failure and a later fresh-stream replay; verify no partial public visibility and no reuse of failed encoder state. Preserve independent native enforcement tests and the Python-row route's behavior. Shared production validators can test consumers, but expectations for the validators' semantic correctness must remain independent.

## PG-06 — Authorized typed companion projections

### Selected SQL and model realization

Generate four family-specific protected PostgreSQL set-returning functions under the existing `ops` native authoring route, with stable typed `RETURNS TABLE` columns. The selected target names are `ops.read_published_input_batch`, `ops.read_published_relation_batch`, `ops.read_published_coverage_batch` and `ops.read_published_mapping_report_batch`. These are proposed new operations, not descriptions of installed functions. The shared application entry is `CompanionExportRequest(pin, families, destination) -> CompanionExportManifest`, using `PublishedSourcePin(project_id, run_id, release_id, task_id, product_key, content_digest)` as defined by the consumer owner. Each function accepts those explicit pin fields (with types derived from their model), not only an unqualified document ID; it resolves the existing published revision authority before reading corresponding immutable modeled rows. A wrong/hidden pin refuses rather than looking like an empty legitimate family.

Use fixed safe search paths, ordinary read-principal EXECUTE grants and existing ownership discipline. Do not grant raw staging/authoritative-table access. Generate return fields and decoding from the semantic model, including JSON expansion/casts only where the current companion realization requires them; PostgreSQL performs that expansion once as a set, rather than returning JSON row objects for Python to reinterpret. New SQL is forward-generated and receives native admission/catalog checks through this series' object-evolution route. Do not edit frozen migrations or make unrelated object-lifecycle replacement a dependency.

| Family | Required projected meaning and row granularity |
| --- | --- |
| input | One modeled source-input binding with ordinal/role, provider product-qualified pin and source/frame/recipe distinctions actually owned by that input |
| relation | One modeled relation endpoint row, retaining relation identity/kind, endpoint ordinal/role, occurrence identity and qualified target product/address; do not collapse repeated endpoints or count endpoint rows as distinct relations |
| coverage | One modeled coverage assertion with its input/selected scope, outcome and declared completeness/uncertainty distinctions; zero rows is not an invented successful coverage assertion |
| mapping_report | One modeled mapping result with source and target qualification, status and reason/diagnostic distinctions; opaque extension payload remains bounded JSON where it is not interpreted by the inventory |

**Representative relation-endpoint projection.** The following is the selected mapping example to realize through the current model, not a new manually authoritative schema. It fixes the important columnar distinctions now; generation must carry actual modeled names and constraints into its concrete SQL/Arrow products and consumer schema.

| Illustrative column | PostgreSQL / Arrow export type | Null and multiplicity meaning |
| --- | --- | --- |
| `relation_id`, `relation_kind` | `text` / non-null `string` | Relation identity and modeled kind repeat for each endpoint; inventory counts distinct relation identity separately |
| `endpoint_ordinal` | `bigint` / non-null `int64` | Ordered endpoint occurrence within this relation; equal target values do not remove separate ordinals |
| `endpoint_role` | `text` / non-null `string` | The model's source/output/input/other declared role, not a role inferred from column position |
| `target_task_id` | `bigint` / non-null `int64` for a resolved endpoint | Qualified target task, not a local record identifier |
| `target_product_key`, `target_content_digest` | `text` / non-null `string` for a resolved endpoint | Target product and immutable revision; carry the qualifying input binding when an endpoint targets an input product |
| `target_occurrence_id` | `text` / non-null `string` | Required current modeled occurrence identity, resolved under the qualified target product |
| `extension_json` | bounded JSON value / nullable string with declared JSON metadata | Only genuinely opaque modeled extension detail; SQL NULL differs from serialized JSON `null` |

The v1 endpoint projection selects the existing `PdfRelationEndpoint`/`PdfRecordEndpoint` contract: required occurrence identity and resolved target product binding. There is no new native-pointer/unresolved union or nullable target identity. Resolve `input_index` to the exact input product; absent input_index means the output product. Expose an occurrence's native pointer only through its modeled occurrence/address projection when needed, not as an alternative endpoint identity. Outside-selection status describes the analytical selection boundary of an already resolved endpoint; it never weakens publication reference admission. Each row also carries source pin/projection provenance. A future need for unresolved published endpoints would require an explicit model change with its own value and admission design, not permissive transport nullability.

Common provenance columns bind the published product, release and projection contract. Derive exact physical field names, types, nullability and keys from the current model and retain those concrete generated products in the implementation. The granularity above determines the contract; no duplicated handwritten field registry is selected. Endpoint qualification is not replaced by an unscoped local ID. Missing, failed, unknown, unrequested and partial are preserved according to their actual model definitions rather than invented for all families.

The prepared Core query uses each generated function as a table-valued selectable with explicit typed columns, bind arguments and final `ORDER BY` over the model-defined logical key. Return typing does not require a general SQL parser. Ordering at the outer query, not assumed function execution order, governs deterministic export. SQLAlchemy's function/typed-column constructs express optimizer-visible relational intent; ADBC sees a COPY-compatible SELECT, not a whole JSON result requiring Python dict expansion. Keep bounded Core item access and native JSON event serialization unchanged in meaning.

### Snapshot, driver and detached artifact lifecycle

Use one exported Core read snapshot for the entire selected-family export. Mutable selection/authorization premises participate even when product contents are immutable; use the existing actual read-session authority rather than invent a second snapshot token protocol. The ADBC operation uses the same database/read principal as the authorized source session.

1. Validate the request and resolve the published binding in the Core read session; export its PostgreSQL snapshot while that transaction remains open.
2. Open one fresh, nonpooled ADBC connection with builtin type resolution and autocommit disabled. With `adbc.postgresql.use_copy="false"`, establish repeatable-read/read-only mode and import the exported snapshot before any data query. Render the server-produced snapshot identifier as a dialect SQL literal, as existing `load_packet` does.
3. Enable `adbc.postgresql.use_copy="true"` and the operation's explicit byte-size hint. For each requested family compile its prepared Core SELECT with this invocation's values through the PostgreSQL dialect. Use unbound COPY-result execution for this bulk operation.
4. Consume `cursor.fetch_record_batch()` exactly once within the cursor/session scope. Validate actual raw types, then apply the profile's explicit model-to-export normalization per batch: NUMERIC lexical preservation or declared exact decimal conversion, UTC/temporal interpretation and JSON/extension metadata handling. Attach the declared model schema; do not infer domain meaning from the driver's physical field types alone.
5. Open one `pyarrow.parquet.ParquetWriter` per selected family using its fixed export schema and write validated batches incrementally. Reuse existing capture/spool ownership and hashing machinery; a Parquet file hash is computed over the closed file, whose footer must be complete. A valid empty family still gets a schema-bearing empty Parquet file and an actual count of zero.
6. Close each reader before another statement reuses its cursor; close each Parquet writer before recording its file byte identity. After every family is complete, explicitly roll back/close the read-only ADBC session, then release the exporting Core read transaction. Neither session remains open during DuckDB inventory or comparison.
7. Finalize the detached manifest only after all files and binding checks succeed, using the existing export/artifact ownership route. Failed output never receives a completed manifest. Cleanup handles only this operation's temporary output; a cancelled consumer closes its native reader before transaction/connection teardown.

ADBC's connection context manager closes resources; it does not commit on successful exit. `adbc_clone` shares database/type-resolution state but creates a different PostgreSQL session, so it cannot import another session's transaction or scratch state implicitly. `fetch_arrow()` is an optional one-shot native stream transfer for another concrete compatible consumer; this selected Parquet path uses the already-supported PyArrow reader. A reader interface or batch hint alone is not a memory proof. [ADBC original §§3/5/8/9 and addendum §§1/5/7](../../libraries/postgresql/adbc-driver-postgresql.md).

Native parameter-bound result queries remain available for a result-sized Arrow consumer; they are not selected for these bulk exports. Their PostgreSQL `PGresult` pathway does not obey the COPY batch-size hint, and multiple parameter rows are repeated potentially lazy executions. Do not replace the bulk query with one binding per endpoint or infer all bound side effects occurred after partial stream consumption. [Tagged ADBC result reader](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/result_reader.cc).

The manifest binds product/release/projection/profile identity, each family's schema/actual row count, closed file identity and export completeness. Reuse the existing logical-row and file-custody distinctions; physical batch boundaries do not redefine product identity. DuckDB reads detached files through that manifest, as detailed by the [consumer owner](consumer-capabilities.md); no backend handle or mutable latest selection escapes the export operation.

**Closure:** a real published fixture with multiple/repeated endpoints, partial and unknown coverage, mapping statuses and independently expected typed values passes PostgreSQL → ADBC → Parquet → DuckDB through the shared public operation. Check distinct relation counts separately from endpoint counts. During capture, change mutable selection in another transaction and show all four families retain the source snapshot's coherent binding. Refuse wrong project/product/digest, hidden staging and unsupported families distinctly from an empty legitimate family. Include SQL/JSON null, lexical numeric extremes, JSON metadata, schema mismatch, early sink failure, reader cancellation and mismatched file/manifest identity. Inspect final outputs independently; calling the producer's normalization for both actual and expected would not establish fidelity. Existing full-document export and bounded row-reader contracts retain their tests.

## Research basis and execution fit

This proposal consumes the original and added capabilities together: [SQLAlchemy original §§2–4/8/11 and addendum §§1/2/7](../../libraries/postgresql/sqlalchemy.md), [pgpq original §§2–8 and addendum](../../libraries/postgresql/pgpq.md), [ADBC original §§3–9 and addendum §§1–8](../../libraries/postgresql/adbc-driver-postgresql.md), and [Psycopg COPY/adaptation](../../libraries/postgresql/psycopg.md). Latest-stable upgrades remain settled direction, not a new availability investigation.

During expansion, Context7 returned SQLAlchemy Core column/typed-query material but not precise 2.1 `with_cols` semantics. Installed `FromClause.with_cols` source explicitly states that it returns self without validation; that is the static/runtime boundary used above. [SQLAlchemy typed Core documentation](https://docs.sqlalchemy.org/en/21/core/metadata.html) and the repository reference supply the broader source route. Tagged [pgpq core encoder](https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/lib.rs) and [Python binding](https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/py/src/lib.rs) qualify positional checking, native mutable state and buffering; their role is mechanism semantics, not a requirement to retain that release.

Filter/project before expensive movement, retain required context, and move server-resident populations inside PostgreSQL. Preserve exactness and negative/completeness meanings while avoiding JSON/dict/hex intermediates for the selected analytical consumer. FP-04/07, DP-06/09/10/15 and H5–8/H12/H15–17 support these choices without making zero-copy, one physical representation or a new generic framework an objective. Benefits are qualitative; no throughput or bounded-memory measurement follows from this document expansion.
