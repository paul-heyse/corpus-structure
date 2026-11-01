# PostgreSQL capabilities: systems leverage and PDF target improvements

**Review date:** 2026-11-01. **Assessment:** Proposed recommendations, grounded in source inspection; this is a blended architectural, capability, library-comparison and plan-improvement review. It is not architectural acceptance or product qualification.

**Original assessment baseline:** `15c9b9e1f8bb49274b4e69db03d3813c417cce8c`, including the uncommitted addenda in the seven PostgreSQL references listed in the coverage appendix. Their previous final lines are the diff boundary: SQLAlchemy1803, Psycopg1458, pool1232, Alembic1377, pglast1248, pgpq723 and ADBC757. The three dirty primary-intake references are preserved; their new content is not this engagement's capability intake. Actual implementation, accepted targets and prior receipts are distinguished below. During publication, concurrent edits appeared in D3 and PDF artifact identity source/tests, then landed with accepted ADR-0043 at `fcfd62a4`; they were preserved and are not reviewed or qualified here. They do not change the inspected connection/transport mechanisms; artifact-identity implementation decisions must be reconciled at adoption. Diagnostic audit documentation was neither consulted nor updated.

**Criteria:** [core3.3 and declared profile/binding](../design_review/design_principles/standard.toml), the [efficient architecture heuristics](../design_review/design_principles/core/efficient-architecture-heuristics.md), relevant code-intelligence fidelity/attribution constraints and the test-assessment companion. These guide judgment within the selected responsibilities; no audit prerequisite, formal verdict matrix or new gate is introduced.

**Operator direction, 2026-11-01:** treat the documented features as available. Updating these dependencies to the latest stable releases is a settled recommendation and ordinary execution judgment now and going forward, not an approval question. Preserve exact declarations and intentional lockfile updates. No dependency was changed by this review, and no newest release number is guessed here. **Design-phase direction:** breaking changes of any scale may be proposed for a better target. Existing APIs, ownership, archived-reader compatibility and current machinery are not target-design constraints. Explain transition/evidence consequences and propose changes to their owning decisions where needed; preserving actual concurrent files and historical receipts during this audit is a separate execution obligation.

**Revised assessment, 2026-11-01:** a fresh independent auditor and bounded schema/transport investigations reassessed the original bodies first, then the addenda against the expanded candidate set. The [audit companion](audits/postgresql-capability-leverage_2026-11-01_audit.md) preserves input `4a38d5a4` and the two-pass net changes. Current-source inspection began at `b283ebf3`, advanced through `7b3488f6` and includes relevant dirty PDF implementation/plan files; conclusions are scoped to inspected paths, not a claim that the moving checkout is qualified.

## Combined judgment

The strongest opportunity is to delegate more of the *mechanical realization* of the model to established library capabilities while preserving application authority over admission, identity, evidence and publication. The code already uses the right broad composition: model-derived SQLAlchemy Core metadata, protected PostgreSQL operations, Psycopg/pgpq on the publisher's connection, and snapshot-bound ADBC capture into Arrow/DuckDB. Retain that composition for current consumers while comparing complete alternative operation owners. No concrete object-editing consumer currently justifies adding ORM state; a future consumer can change that judgment. Existing ownership is context, not a rule excluding ADBC-owned operations or complete native-object library support. Retention recommendations below are comparative judgments for the intended consumers, not compatibility vetoes.

The new content supports improvements across complete systems, rather than seven independent adoptions:

- One failure vocabulary can replace duplicated physical-error interpretation across connection acquisition, publication and orchestration.
- One model-derived wire profile and encoder preparation path can serve both ordinary Arrow publication and PDF staging without merging their domain protocols.
- Core/Alembic/pglast can carry more SQL construction, schema evolution and diagnostics, leaving policy and protected lifecycle operations in their current owners.
- Current Core record readers and streamed exports are implemented; extend them only for a demonstrated gap. Model-derived columnar published-family projections offer a distinct bulk analytical capability (O13).
- Original compilation/type facilities and native-object lifecycle extensions broaden the proposed improvement beyond local helpers (O11/O12). Optional native schema/statistics exploration adds useful operator functionality (O14).
- Pool statistics and native cancellation can improve operation without becoming a new scheduler, lease authority or logging framework.

Current code has advanced beyond the original package descriptions: `semantic/pdf_record_reader.py` implements published keyset-paged reads and ordered streaming exports; `orchestrate/source_reader.py` scopes connection checkout to actual reads; `ingest/pdf_retained_stream.py` implements envelope decomposition and exact-byte checks. Publication orchestration calls freeze/prepare/validate/seal, but its imported `semantic.pdf_publication` module was absent at inspection. Call sites do not establish working publication. The coordinator's older “planned” labels cannot establish absence either. These are source observations, not a completion audit or current provider/deployment acceptance. The [PDF coordinator](../plans/pdf-docling-pipeline_2026-10-31.md) retains execution ownership; no package state is changed here.

## Responsibility and execution model

| Responsibility | Inspected implementation and retained authority | Proposed leverage |
|---|---|---|
| Meaning and physical structure | `model/semantic`, `semantic/metadata.py`, `schema/relational.py`; model defines application operations and generated forms | Core types/expressions/DDL and focused Alembic extensions realize mechanics |
| Physical connections | `core/db/store.py:71–101`, `semantic/runtime.py`; one regular Psycopg pool, Core Engine using `creator=pool.getconn`, `NullPool` | Retain composition; native admission, health, drain and statistics |
| Transactions and private admission | `semantic/pdf_staging.py:159–213`, `pdf_staging_native.py`; caller-owned Core transaction plus protected scratch/adopt | Same checked driver for COPY; library encoding, set operations, explicit recovery |
| Publication and identity | `semantic/publication.py`, native functions and immutable receipt identities | Share physical failure classification; retain operation-specific replay/fences |
| Analytics and reads | `semantic/analytics.py:795–938`, `CapturedPacket.iter_batches`; exported/imported snapshot and Arrow/spool ownership | Retain implemented bounded Core rows and native exports; O13 adds typed analytical families where useful |
| SQL meaning and admission | `semantic/authored_sql.py:118–188`, native generators | Library AST traversal/printing and source locations; application allowlists and catalog validation survive |
| Schema delivery | `semantic/migrations.py`, `semantic_alembic/env.py`, frozen revisions | Public extension hooks and structured new migration operations; immutable history remains |

Paths in code references are relative to `python/corpus-structure/src/corpus_structure/` unless another root is given. Line locations describe this baseline, not permanent identities. Prior leverage accounts were used only as challengeable leads; the present claims come from current implementation and the documentation delta. No current disposition is copied from those accounts.

<a id="O01"></a>
## O01 — Update the library family and retire superseded workarounds

**Proposed; direction selected by the operator.** Update the seven libraries to their latest stable releases as part of the ensuing implementation. Move declarations and locks deliberately, inspecting the affected family rather than resolving the entire environment wholesale. This is a default execution step, not a research gate or a request for further permission.

The useful consequence is removal of old accommodations where the current upstream behavior discharges their actual contract. In particular, `semantic/alembic_defaults.py:1–40` exists to route Identity comparison around callable-default ordering and imports the private `_compare_identity_default`. Re-exercise that concrete case after updating; remove the adapter and its registration if the upstream path now handles it. Retain it only on a reproduced remaining semantic defect, not on pin preservation. Release corrections in the SQLAlchemy, Psycopg and pool addenda inform regression selection; they are not seven separate upgrade investigations.

**Why:** FP-02/06, DP-13–16, H4/H27. Less dependence on private behavior, fewer stale branches and a supported base for later changes. An upgrade alone establishes no runtime acceptance. Relevant controls: Identity/default comparison, pool return, cancellation, exact COPY types, ADBC snapshot capture and parser admission. Existing historical products remain recoverable evidence; a target redesign may deliberately replace compatibility or reproduction mechanisms when its changed meaning and transition are stated. New compiler outputs carry their own provenance.

<a id="O02"></a>
## O02 — Give acquisition, execution and ambiguous publication distinct outcomes

**Implemented evidence:** `store.py:108–121` classifies a Psycopg `OperationalError` without SQLSTATE as retryable lost connection. `_publish` in `semantic/publication.py:649–659` independently repeats that interpretation and attempts receipt lookup. The pool's `PoolClosed`, `PoolTimeout` and `TooManyRequests` taxonomy describes materially different circumstances; treating all as transport loss can repeat acquisition pressure, attempt recovery against a deliberately closed pool, or obscure the action the operator needs.

**Proposed:** one shared physical failure classification **plus operation-phase knowledge** (before checkout, executing, committing, resolving acknowledgement), consumed by existing transaction/publication/orchestration owners. Distinguish admission pressure, acquisition timeout, closed lifecycle, disconnect/invalidated connection, serialization/deadlock, explicit cancellation and domain fencing. Use native exception types, SQLSTATE and SQLAlchemy invalidation information; do not infer physical loss solely from absent SQLSTATE. Preserve structured ADBC details when present, without assuming every pathway populates them.

Keep retries with the domain operation. A failure before acquiring a connection does not by itself justify ambiguous-commit receipt recovery. A failure during commit may require lookup under the original immutable identity. A retry of serialization/deadlock repeats the complete transaction with its original input; stale holder/fence refusal is not permission to reacquire authority. Native pool reconnect backoff maintains connection inventory; it does not retry a publication.

This replaces two independently maintained interpretations of the same premise, not the existing idempotency protocol. A universal retry decorator is the weaker alternative because it cannot know whether effects occurred. FP-04/05, DP-02/08/19, H18/H24 apply. **PDF fit:** integrate before PDF-21 seal recovery and reuse in PDF-24 read cancellation. Independent controls must distinguish failure before acquisition, after write/before acknowledgement, changed duplicate content, closed shutdown and stale attempt. No measured retry reduction is claimed.

<a id="O03"></a>
## O03 — Preserve one pool and make transaction ownership explicit

**Implemented evidence:** `open_store` has one regular `ConnectionPool(open=False, close_returns=True, check=check_connection)`; Core borrows it through `NullPool`. `semantic/runtime.py` opens this store. The [PDF staging target](../plans/pdf-docling-pipeline/staged-publication-and-validation.md) says to keep SQLAlchemy pooling and use Psycopg pooling only for separately owned traffic. That prose does not describe the current supported composition.

**Proposed PDF amendment:** state separately that Psycopg-pool owns physical inventory, Core Connection/Transaction owns the publication transaction, and pgpq writes through its checked Psycopg driver. Retain `close_returns=True`, explicit open/wait and idle configuration. Preserve configure's scoped JSON adapters; moving serialization solely into `create_engine(json_serializer=...)` does not cover direct driver COPY/adaptation. The application's `pool/` package is analytical processing, not a second connection pool.

Switching to SQLAlchemy's retaining pool would be a possible complete alternative only with a concrete benefit and migration of all direct borrowers; the addenda supply no reason to do that here. A NullConnectionPool is not a drop-in substitution for the regular pool's SQLAlchemy return contract. `getconn/putconn` ownership, `close`, `drain`, health checks and reset callbacks have distinct meanings; library lifecycle does not replace task/attempt ownership.

**Benefit:** FP-01–03, DP-14/19/20, H4/H21/H23. The correction avoids building a second inventory or holding a connection during inference. **PDF fit:** PDF-20/21 and I18 wording; no §B change. Preserve actual interop tests and add a slow/abandoned borrower case when changing lifecycle behavior.

<a id="O04"></a>
## O04 — Share the exact wire profile and encoder preparation, not publication policy

**Implemented evidence:** `semantic/arrow_publication.py:37–88` derives stage Arrow fields, chooses JSONB string encoders and checks encoder schema against the expected PostgreSQL shape. `semantic/pdf_staging.py:159–213` separately assembles builders from generated metadata, verifies each batch's full schema, writes header/batches/footer and then calls protected adoption on the same connection. Both already delegate serialization to pgpq; neither is a bespoke COPY encoder.

**Proposed:** derive one reusable, **directional** wire-profile/encoder-preparation capability from the existing model and Core metadata. It should own field order, PostgreSQL type selection, nullability, JSON wire choice and the encoder/output-schema compatibility check. Each transfer still obtains a fresh stateful encoder and writes one valid stream. Batch limits, receipt identity, task fences and the ordinary versus PDF publication protocols remain with their current owners. Do not introduce a new persistence service or copy the whole `AppendPublication` constructor into PDF staging.

Retain existing Python-row COPY in `publication.py::stage_batch` (`set_types`/`write_row`); converting those rows to Arrow solely to share a helper adds work. A shared profile must distinguish source encoding and destination semantics: pgpq write types, ADBC read types, normalization and exact canonical values are not universally symmetric.

Use pgpq for its established binary encoding; do not treat its inferred schema or `CREATE TYPE` output as the authority for model DDL. Decimal precision/scale, list element rules, JSON string interpretation and generated composite-type lifetime are not all established by successful encoding. ADBC target-aware `adbc_ingest` is valuable for an independently owned existing-table import, but cannot replace the current publisher's same-session temporary scratch/adoption transaction by opening another connection.

**Complete alternatives:** compare the current Core/Psycopg/pgpq operation with an ADBC-owned begin → scratch/ingest → protected adopt → explicit commit/rollback operation, and with server-native `INSERT … SELECT` when inputs already reside in PostgreSQL. ADBC target-aware name/OID resolution can remove real wire adaptation; opening a second session cannot share the existing transaction, but moving the complete operation is possible. Retain the present integrated writer because its guarantees and integration are already supplied, unless that complete comparison demonstrates a benefit. Native encoder failure requires a new encoder as well as DB rollback.

**Why:** FP-03–05, DP-06/10/13–16, H4/H12/H15. Removes repeated schema-to-wire decisions and makes PDF's transport receive the same explicit compatibility protection as ordinary publication. **PDF fit:** PDF-20 and I18, then PDF-24 interchange. Controls need independent expected bytes/rows for JSON null versus SQL NULL, decimal extremes, empty/reordered batches, schema mismatch, large values, encoder failure and failed adoption. Independent native checks remain essential.

<a id="O05"></a>
## O05 — Use operation-shaped reads: Core rows, COPY capture and bound ADBC queries

**Implemented evidence:** `analytics.py:698–704` compiles literal Core SQL for the COPY capture path. `load_packet:824–889` exports/imports one snapshot, toggles COPY for transaction setup, consumes `fetch_record_batch`, normalizes typed values and stores bounded batches. `CapturedPacket.iter_batches:205–227` retains owner lifetime and closes it after the last borrower. PDF-24 already selects this route and closed streaming Core Results.

**Proposed:** retain bounded Core rows for current item/cell/relationship reads. `PublishedPdfReader.iter_rows` already uses bound Core SQL, keyset pages and closed Results before yielding. Its ordered export event cursor avoids per-record lookup reconstruction. A second bound ADBC path is conditional on an actual Arrow consumer benefit, not the default way to improve those reads. Psycopg row factories are useful for a direct-driver typed-row consumer, but do not justify replacing an adequate Core mapping/validation boundary.

Retain COPY-result ADBC capture for bulk columnar work; use O13 to expose model-derived published families without the JSON/dict/hex round trip. If native `$n` bindings and `adbc_prepare` are selected for a result-sized Arrow query, preserve their different buffering/effect contract: bound results use a result-based reader rather than the COPY size-hint pathway, and consuming only part of a parameter stream may leave later executions undone. Parameter rows are repeated executions, not inherently one set operation. [Native reader source](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/result_reader.cc).

Keep explicit imported snapshots for mutable captures, stable published pins for immutable reads, and deterministic reader/connection ownership. Clones do not inherit session state. Complete native JSON serialization, exact retained-byte replay and typed Arrow projections are distinct outputs with independent completeness contracts. Add no duplicate export engine merely to use a new API.

**Why:** FP-02/06/07, DP-08/10/15, H5–8/H16/H17. **PDF fit:** refine current PDF-24 consumers and remaining PDF-25 adoption. Test wrong pin, slow/abandoned reader, snapshot consistency, exact numbers/nulls, ordering/multiplicity and complete companion inventories. Full-model hydration remains an explicit requested operation. Benefits are structural; no memory or throughput measurement was performed.

<a id="O06"></a>
## O06 — Express model lowering and validation as relational operations

**Implemented evidence:** `pdf_staging_native.py:178–203` already uses `INSERT … SELECT`, conflict handling and set difference for replay/content checking. It also derives scratch tables from declared relations and authenticates actual scratch shape/ownership. These are strengths, not candidates for replacement by client-side lists. The prior correlated child guard is already replaced by a set join in frozen0061; its whole-book acceptance remains open.

**Proposed:** carry that set-shaped route into PDF-21 frozen-union validation and promote reusable relational fragments through Core expressions: `Insert.from_select`, explicit `RETURNING`, CTE composition and `with_for_update` where Python owns the statement. Keep database-internal locks and protected guard semantics in native operations. Use explicit result/input correlation or stable domain keys when generated identifiers are returned; never zip unspecified returned order to input rows. Ordered aggregates need an explicit order and a result-size purpose, not a book-wide JSON reconstruction.

The system-level displacement is client read/reshape/write coordination and repeatedly hand-built mechanical SQL across generators. It is not removal of all SQL strings: PL/pgSQL lifecycle bodies and native privilege/fence logic remain genuine application behavior. Core and pglast should realize their respective relational-expression and PostgreSQL-AST jobs rather than become two competing semantic compilers. SQL NULL, JSON null, missing values and generated-default ownership must stay explicit in the model and lowering.

**Why:** FP-04/07, DP-01/03/08/10, H2–4/H7–10/H23. **PDF fit:** PDF-21 indexed closure and PDF-18 declaration consumers. A disconnected or stale writer must still fail native admission; local shape checks cannot certify frozen global inventories or endpoints. Closure controls require reordered inputs, duplicate/missing endpoints, permitted cross-reference cycles versus prohibited containment cycles, and concurrent freeze/append. An implementation limited to renaming string builders would not discharge this opportunity.

<a id="O07"></a>
## O07 — Make schema evolution a library operation pipeline

**Implemented evidence:** the semantic migration wrapper supplies `Config.attributes['connection']` and invokes Alembic on the caller's transaction; `semantic_alembic/env.py` scopes schemas, installs comparison plugins and records `on_version_apply`. The Identity workaround reaches a private comparator, and `compare_default` normalizes a known volatile expression textually. This is already an integrated migration system, not a need for a second one.

**Proposed:** apply O01's upstream corrections and use Alembic `produce_migrations`, `UpgradeOps`/`DowngradeOps`, `render_python_code`, public comparator/plugin, `Rewriter`, operation and renderer interfaces for ordinary candidate schema changes. For recurring functions/views/triggers/policies, compare O12's complete lifecycle options before implementing custom comparators/operation renderers. Do not preselect homegrown object management merely because Alembic permits it. Use SQLAlchemy dependency-aware metadata and DDL compilation for mechanical ordering and rendering; attach real prerequisites such as extensions/roles explicitly. Keep autogeneration a candidate producer requiring substantive review, not authoritative evidence that function bodies, grants, CHECK semantics, index opclasses or partial predicates agree.

Retain database-catalog/native descriptor checks and historical-chain tests. Reflection hooks can normalize catalog representations for comparison but cannot write inferred meaning back into LinkML. Conditional DDL/`ddl_if`, generated defaults, DOMAIN and exclusion support are available where an actual modeled invariant needs them; adopting every native object family would enlarge migration/admission burden without present value. Transaction-sensitive concurrent indexes or `autocommit_block` need an explicitly separate deployment phase: they must not accidentally commit PDF seal work.

**Benefit:** FP-01/04/06, DP-06/13–16/24, H12/H27. Displaces repeated operation rendering and scattered comparison workarounds while preserving independent drift protection. **PDF fit:** PDF-21 new operations and PDF-25 forward deployment. Frozen migrations remain untouched; no new generic migration framework or mandatory offline mode is needed. Controls cover modeled declaration changes reaching the new operation, no-change autogeneration, wrong catalog body/privileges and fresh versus retained upgrade equivalence.

<a id="O08"></a>
## O08 — Use pglast for transformations and precise diagnostics, retain admission policy

**Implemented evidence:** `authored_sql.py:118–175` uses `Visitor`, `parse_sql`, `referenced_relations` and `RawStream`, handles CTE lexical scope and rejects unsupported syntax/functions/types. Its admission contract explicitly refuses parser fingerprints as identity. Native syntax, context, function-signature and PDF generators also use ASTs. This already replaces a general SQL scanner.

**Proposed:** factor repeated mechanical AST traversal, node replacement and rendering through pglast's public Visitor/ancestor/stream primitives, preserving explicit transformation contracts. Concrete duplication appears in `native_context_native.py:116–134`, `native_consumer_native.py:89–100` and `native_syntax_native.py:40–52`: parse, omit trigger/physical-contract statements, serialize and replace migration-owner text. These generators emit version-specific0050/0052/0053 products. Establish a current forward-authoring consumer before consolidating their mechanics; do not refactor frozen products or their required reproduction solely for visual duplication. For live consumers, a narrow shared structural transformation can remove repeated mechanics while retaining inclusion policy. Procedural function bodies remain strings in the SQL AST; pglast's raw PL/pgSQL dictionaries do not supply a typed rewrite engine for their internals. Use original `split(only_slices=True)`, token/displacement APIs and original source text for exact diagnostic excerpts; use AST printers for intentionally regenerated SQL. Add qualified source positions, statement spans and relevant comment locations to authored-SQL diagnostics so a compiler refusal can identify the offending declaration instead of forcing inspection of generated SQL. Use diagnostic fingerprint grouping only for operator query-shape exploration; never substitute it for authored bytes, semantic equivalence, model revision or publication identity.

Share prepared syntactic facts across actual native inventory, object-lifecycle and authored-SQL diagnostic consumers when they repeatedly parse the same immutable source. Bind those facts to original statement/source locations; never substitute them for server catalog resolution. Resolve O12 before building parsing/comparison machinery its selected library would supersede. The value is common, auditable syntax mechanics and better authoring feedback. A general AST framework or automatic rewrite of every valid PostgreSQL construct is not warranted. Maintain application-owned allowlists, dependency rules, schema qualification, volatility/privilege policy and live catalog admission; the parser does not establish those. AST mutation/printing can normalize or lose source layout, so source text and rendered products have distinct provenance. PL/pgSQL CLI inspection is an explicit developer investigation, not a replacement for native function-body verification.

**Why:** FP-02/04/06, DP-04/08/13–16/21, H4/H12/H26. **PDF fit:** PDF-21 guard generation and PDF-25 deployment diagnostics. Controls include nested CTE shadowing, forbidden constructs below allowed ancestors, mutation preserving intended dependencies, Unicode positions and comments; compare against independent expected meaning, not a printer/parser round trip alone.

<a id="O09"></a>
## O09 — Native operational control with application-owned outcomes

**Proposed:** use `get_stats`/`pop_stats` as the pool's source for checkout/queue/connection telemetry and route structured Psycopg SQLSTATE/diagnostic and ADBC details into the existing logging direction. Keep unavailable fields unavailable. Original Psycopg `add_notice_handler`/`Diagnostic` can supply constraint/schema/table/column, SQLSTATE and hints for actionable migration/admission diagnostics. Copy selected fields during the callback; the Diagnostic is invalid afterward. Preserve absence and avoid indiscriminate payload/internal-query logging. Native notices are diagnostics, not durable outcomes. [Psycopg messages](https://www.psycopg.org/psycopg3/docs/advanced/async.html#server-messages). In this manual `getconn` integration, `usage_ms` does not measure ordinary Core checkout occupancy; it is measured by `pool.connection()`. Only add checkout timing at the actual borrower boundary if a real diagnostic needs it. Bound native waiting admission through existing settings when concurrency needs it; the current default queue is not a complete-operation capacity bound. Do not add per-query payload copies, a separate metric registry or a bespoke connection-health monitor. Pool counters cover their documented lifecycle intervals; they do not directly measure end-to-end task success or all wait time.

Cancellation needs both native protocol action and owned settlement. `semantic/claim_lifetime.py` renews claims in a thread and joins it; pool shutdown alone does not cancel checked-out operations. For PDF-21 long validation and PDF-24 abandoned reads, scope Psycopg `cancel_safe(timeout=...)` to a Psycopg connection actually owned by that operation (use ADBC’s native cancellation for ADBC-owned work), settle/rollback before reuse and close the reader/borrower deterministically. Preserve task fencing and bounded cleanup semantics; `Rollback` suppression, a cursor context exit or `pool.close()` is not evidence of successful publication or worker termination.

If an operator-facing ingestion diagnostic is selected, join the owned backend PID to `pg_stat_progress_copy` to separate server ingestion from client encoding/backpressure. Rows processed do not establish durable adoption or publication, and unknown totals remain unknown; do not add default polling or progress percentages.

For intermittent long-lived MCP traffic, a zero-minimum regular pool is a useful optional setting: retain the same return contract while releasing idle inventory. Explicit connectivity checks are still needed when minimum zero makes readiness vacuous. Dynamic connection parameters plus `drain()` can support credential/endpoint rotation if a real operational need appears; this is independent of PDF completion. LISTEN/NOTIFY may later improve operator progress wakeups but durable task state remains authoritative and polling/reconnect semantics still need a consumer case.

**Why:** FP-05–07, DP-19–21, H21/H23–27. **PDF fit:** cancellation/settlement within PDF-21/24; broader telemetry integrates with the existing logging undertaking, without accepting new scope there. Controls must cover cancellation during active work, connection return after settlement, no callback outcome masquerading as completion, absent diagnostics and repeated cleanup. No new hard cleanup deadline or operational readiness is claimed by this static assessment.

<a id="O10"></a>
## O10 — Choose the native retained-data migration shape before PDF-25 cutover

**Proposed:** choose migration mechanics from the actual source representation. Existing PostgreSQL rows favor server-native set transforms; Arrow/Parquet replay favors projected scanners → typed batch admission; historical JSON envelopes use the now-implemented streaming `ijson` decomposition and companion journal in `ingest/pdf_retained_stream.py`. That parser preserves a selected numeric profile and checks exact serialized identity, so it is not replaceable by an Arrow encoder merely because both stream data. Adoption call sites exist, but missing publication prerequisites must be reconciled before crediting delivered migration.

Reuse compatible admission/completion semantics, not one universal input format. Retain separate schema change, data movement, validation and activation steps where their effects differ. `postgresql_using`, eligible NOT VALID plus VALIDATE and native index options remain useful for actual relational schema changes; they do not describe the entire envelope migration. `autocommit_block` commits prior work, concurrent indexes can remain invalid and NOT VALID leaves old rows unvalidated. Prefer ordinary transactional/rebuild work unless live-write requirements justify added online machinery.

**PDF fit:** PDF-25 retained-data adoption and O07/O12 forward artifacts. Verify exact old byte pins, independent new record values, interrupted migration/retry, failed native admission and unchanged public selection until completion. Source/test existence is not operational cutover. FP-05/07, DP-08/19/24 and H23–27 apply.

<a id="O11"></a>
## O11 — Prepare typed relational realizations at their actual stable lifetime

**Proposed:** extend model-derived metadata to reusable typed expression/transport preparation where it eliminates repeated decisions. `analytics.py::compile_projection` reconstructs column expressions and Arrow fields per capture; `published_native_table` checks availability and copies metadata per call. Original SQLAlchemy `TypedColumns`, generic Table/selectable typing and `with_cols` for generated/static surfaces, compiler/expression extension points, structural statement caching and `lambda_stmt` are alternatives to ad hoc preparation caches. Bind changing pins/values separately from reusable statement shape. Engine execution caching does not automatically cover direct `.compile(literal_binds=True)` used for COPY SQL; reuse that stable construction explicitly only where it removes material work. Retain per-capture schema metadata and current authority checks.

Psycopg preparation, adapter registration and ADBC type-resolver caches have physical-session/type-generation lifetimes. A model-only cache key is insufficient if deployed custom OIDs or adapter configuration changes. `TypeDecorator` and SQLAlchemy result processors do not affect raw COPY or ADBC. Declare directional profiles with O04 and use a session/deployment invalidation boundary before sharing custom type preparation. Keep builtin ADBC resolution for current fixed primitive captures; enable broader discovery only for an actual custom-type consumer.

Compare retaining cheap construction, public compiler caching and narrow prepared artifacts; do not build a new global query registry or cache results. Closure requires changed parameters without changed prepared shape, changed physical/model profile invalidating preparation, and exact value/null semantics across raw and Core routes. FP-04/06/07, DP-01/09/10/15, H12/H14.

<a id="O12"></a>
## O12 — Compare complete native-object lifecycle delegation

**Proposed; comparative selection unresolved.** Original Alembic §11.2 and replaceable-object recipes expose a larger opportunity than rendering: model-produced functions/views/triggers/policies can enter a library lifecycle for discovery, canonical definition comparison, dependency order and create/replace/drop/revert operations. Compare Alembic Utils (`PGFunction`, `PGView`, `PGTrigger`, `PGPolicy`, `register_entities`), SQLAlchemy Declarative Extensions (Core-metadata object/role/grant declarations), a focused public Alembic Plugin and current explicit forward native products. [Alembic Utils](https://github.com/olirice/alembic_utils).

Current `native_products.py::closure_products/forward_products`, `source_view_native.py`, `pdf_record_native.py` and staging native products combine authoring, inventories and admission. Delegate only the covered mechanical lifecycle while retaining model semantics, secure role/search_path/grants and native enforcement descriptors. Server-assisted canonicalization may create/simulate objects and needs appropriate privileges/context; its dependency discovery is not a complete semantic or security proof. Alembic Utils simulation belongs in an explicitly owned migration-authoring environment, not an ordinary reader. Declarative Extensions offers broader object/role/grant composition but requires a contract check for all protected function properties and search-path semantics. [Function capability source](https://sqlalchemy-declarative-extensions.readthedocs.io/en/latest/functions.html). Alembic operation trees/rewriters and SQLAlchemy conditional/dependency DDL compose with these libraries; they do not establish its fit automatically.

A revealing new forward product must preserve overloaded function identity, bodies, trigger/policy semantics, dependent object order, role/search_path, wrong-catalog refusal and frozen historical reproduction. Settle the selection on that representative full lifecycle before adding custom lifecycle machinery or adopting the companion wholesale. This is bounded mechanism research, not a new migration framework, and does not block unrelated PDF delivery. FP-01/04/06, DP-06/13–16/24, H4/H27.

<a id="O13"></a>
## O13 — Expose typed published-family batches for analytical consumers

**Proposed:** add a model-derived columnar projection for a selected published record/companion family when a bulk analytical or Parquet consumer needs it. Current `pdf_record_reader.py::iter_rows` receives JSON row values, builds dicts, reserializes selected fields and decodes artifact hex. Those steps fit generic small-item access; a typed family query can avoid them for an Arrow consumer. Reuse published-pin authorization, consistent snapshot/capture and existing batch ownership, with ADBC COPY-result transfer or an explicitly owned compatible reader.

Original ADBC batches/scanner integration plus addendum C Stream support enable direct compatible consumers, but do not imply zero-copy PostgreSQL transport. Derive the schema from the model, not incomplete table/query introspection. Preserve decimal/temporal/null/extension metadata, multiplicity, complete companions and authorization. Keep large native JSON export on its existing ordered event cursor; typed analytical batches are not replacement native serialization or artifact identity.

Select one real consumer and compare its complete current JSON/dict path with typed transfer. Independent wrong-pin/visibility, exact-type, empty/reordered batch, early-exit and companion inventory cases should establish usefulness and fidelity. Until then this is a targeted functional extension, not missing PDF-24 acceptance. FP-03/07, DP-08/10/15, H5/H8/H16/H17.

<a id="O14"></a>
## O14 — Bounded database description for operator and research use

**Proposed optional capability:** expose filtered/depth-bounded ADBC `adbc_get_objects`, result-schema negotiation and supported approximate statistics for operator/agent inspection before choosing a query, projection or import. Original metadata functionality was useful independently of replacing model declarations. A selected-relation description can show physical columns/result shape and approximate population/null/distribution information without a new bespoke catalog model.

Metadata APIs differ: table schema omits parts of the physical contract, query schema describes output, statistics are approximate and may be stale, and driver info is not package provenance. Keep these labels explicit. Preserve exact native catalog/body/privilege checks and domain model authority. Current scoped production search found no use of these metadata APIs, which does not itself establish demand. Revisit when an operator/research consumer is selected; do not add this as a publication prerequisite. FP-02/06, DP-02/15/21, H6/H26.

<a id="O15"></a>
## O15 — Stream selected intact native subtrees with declared context

**Proposed optional functional extension:** a scientific/extraction consumer requesting one intact section could stream that subtree plus its required integrated context rather than hydrate it or export the complete root. Current `PublishedPdfReader` supports selected hydration and whole-root native event export; these do not yet establish a selected-subtree streaming contract.

Reuse the existing recursive native event query and sink serialization, parameterizing the selected root and required context under one published product pin. Preserve ordered membership, source-qualified addresses, evidence/companion reachability and explicit omissions from the full document. A necessary outside reference may require context beyond the output subtree. Partial export is neither a new authoritative product nor progressive publication of an unfinished document, and needs no new database driver.

Compare this complete consumer journey with existing bounded hydration before adoption. Select it for an actual large-section/export consumer; independent expected subtree membership, cross-scope references, repeated occurrences, wrong pins, omitted-companion labels and abandoned sinks establish the intended capability. No new acceptance requirement is imposed on the existing PDF plan. FP-02/03/07, DP-07/08/10/15, H5/H6/H16.

## Proposed integrated target and delivery order

1. O01 latest-stable upgrades remain settled; remove workarounds only when their exact failure is absent.
2. Prioritize O02 phase-aware outcomes, O03 owner clarity and O09 actual cancellation/settlement. Existing scoped source readers and closed export cursors are strengths to preserve, not work to deliver again.
3. Apply O04/O06/O11 where current transport/authoring changes remove real repeated decisions. Preserve working row COPY and bounded Core readers. Resolve missing publication prerequisites through the owning PDF work, without claiming audit implementation.
4. Use O12's representative lifecycle comparison before building custom object extensions under O07. O08 applies only to current forward consumers; historical reproduction remains frozen.
5. Reassess O10 against actual retained-source paths and remaining deployment/adoption obligations. O13 typed analytical families, O14 description tools and O15 selected-subtree exports are separable enhancements with explicit consumers, not PDF acceptance substitutions.

Priority follows outcome risk and value; prerequisite order follows contracts. The PDF coordinator retains all package disposition and assembled journey obligations. Inspection of source/tests does not qualify book publication, actual consumer adoption, provider/reference grading or live deployment.

### Authority and rule impacts

**RC01 — physical connection wording:** amend the staging target to describe the existing Psycopg inventory/Core transaction composition (O03). This aligns it with D3 and current runtime; no §B change is proposed.

**RC02 — new generated interfaces and failures:** O02/O04/O05 may change typed outcomes, compiler products or reader contracts. Carry changed meanings into their model/architectural owners and explicit compatibility/admission versions when implemented. Keep archived meaning intact. If a selected realization alters an accepted ADR, use its existing successor route. The review itself changes none of those authorities.

**Current preservation premises (proposed target changes remain allowed):** PostgreSQL instance authority, one model's structural authority, qualified identity, immutable evidence, task fences, independent native enforcement, one logical integrated document, intact sections and atomic final visibility. No new store, generic scheduler or evidence certificate system currently has a demonstrated benefit. Existing mechanisms may be replaced or removed under the design-phase direction when a stronger complete design is established; doing so requires neither compatibility preservation nor a predetermined change-size limit. PDF-26 progressive scopes remain conditional; new library functionality does not establish their dependency closure.

## Evidence and limits

All recommendation applications above are **Proposed**. Current implementation descriptions are **Implemented (source-inspected, 2026-11-01)**, not fresh runtime qualification. Capability contracts are **Interface-checked** where the linked primary/installed source was examined; the remaining addendum capabilities are documented candidates assessed under the operator's availability assumption. No quantitative performance benefit is claimed.

Research followed Context7 first and primary/installed source for decisive contracts. Static inspection sufficed for the principal choices: same-session staging, pooling composition, shared failure taxonomy, existing capture reuse and library-versus-domain responsibilities. A no-database exception-taxonomy check by the lifecycle contributor observed `PoolClosed`, `PoolTimeout` and `TooManyRequests` all returning `retry` from `store.classify_error`. Its command was `uv run python` importing those three classes and applying `classify_error(cls("synthetic acquisition outcome"))`; this is a reproducer of current classification, not a correctness pass. An earlier exploratory import of nonexistent `classify_database_error` failed; the corrected command removed that unnecessary import. Neither attempt touched the database. O02 is independently supported by the inspected exception/classifier source; no integrated provider or product acceptance is claimed. Further implementation controls are specified with each recommendation. No full PDF/provider run, migration deployment or production change was performed.

The revised inspection followed both the original feature bodies and all seven additions through current store/runtime, publication/staging, analytics/capture, model/SQL/migrations and PDF consumers. It is comprehensive for the added capability families; it is not a claim that every PostgreSQL call in the repository was executed or that all unrelated systems conform to the design standard. Statements that an opportunity is unneeded apply to this inspected target, not to all possible uses of the library.

### Historical validation of the original review

**failed (2026-11-01):** `just docs-check`, before publication, on concurrent ADR-0043 missing its listed DESIGN §B4 decision link and stale generated ADR index. Receipt: `build/postgresql-capability-review-docs-check.log`. This is not a failure in the review's links. **passed (2026-11-01):** scoped Python invocation of existing `scripts/docs.py::rewrite_links`: all25 review links resolved; all10 recommendation anchors are unique. **passed (2026-11-01):** `just turn-end`;632 Python files unchanged, formatting and ADR-index maintenance completed. **failed (2026-11-01):** final `just docs-check` still refuses ADR-0043's missing DESIGN §B4 decision link; the stale-index issue cleared. Receipt: `build/postgresql-capability-review-docs-check-final.log`. The documentation build stops at that unrelated ADR lint, so no full publication pass is claimed. Product tests, provider journeys and performance measurements are **not_run** for this review-only change; their existing obligations remain with the owning plans.

## Coverage of the added capability families

The following appendix accounts for the additions, including corrections and limits. Section numbers refer to each document's **addendum**, not its earlier parent reference. Grouped ranges include all their subordinate sections. “Retain” means current composition is preferable for this target; “conditional” supplies a concrete revisit premise. These are review dispositions, not execution status.

### SQLAlchemy

Reference: [advanced addendum](../libraries/postgresql/sqlalchemy.md).

| Added sections | Assessment and disposition |
|---|---|
| 1.1–1.4 INSERT SELECT, correlated RETURNING/sentinels, heterogeneous NULL/defaults, generated-value retrieval | O06; explicit identity/default contracts survive. Input/output order is not implicit correlation. Included Python defaults in INSERT SELECT are not per-row domain computation. |
| 1.5–1.8 locking, side-effecting CTEs, functions/ordered aggregates, expanding/postcompile parameters/hints | O06; native lock semantics retained; avoid eager lists for database-derived sets. No demonstrated hint need; text shape and parameter limits still matter. |
| 2.1–2.5 conditional DDL, dependency ordering/copy, reflection, mock DDL and defaults/computed values | O07/O11/O12; `sort_tables`, `to_metadata`, `CreateTable`, `CreateIndex`, `AddConstraint` and `CreateView` already used. Mock emission inspects SQL, not server validity. Reflection does not author meaning. Conditional DDL cannot omit required enforcement. |
| 3.1–3.7 deferred reflection, unmapped columns, callable relationships, loader criteria/state, select-in batching, recursive loading, attribute instrumentation | Retain Core/model/Arrow architecture. These ORM facilities would introduce identity-map/mutable-object semantics without replacing native constraints. Revisit for a concrete ORM consumer. |
| 4.1–4.3 ORM execute interception/reentry/frozen results | Retain current pinned release/capture contracts. An ORM result cache cannot establish complete dependencies or publication identity; no new routing/cache layer selected. |
| 5.1–5.3 external Session transactions, scoped Session registries, bind collections | Core already participates in explicit caller-owned transactions. No current Session registry or bind-routing need. |
| 6.1–6.4 engine plugins, independent pools, error interception and event-hook DBAPI failures | O02/O03; `handle_error` may translate physical errors but cannot retry domain operations. No engine-plugin framework needed for existing configuration. |
| 7.1–7.3 SQL NULL/JSON null/missing, typed JSON access, operator classes | O04/O06; `null()`, `JSON.NULL`, `none_as_null` and typed accessors express useful distinctions. COPY must realize the same model policy. Operator warnings do not enforce instance invariants. |
| 8.1–8.3 DOMAIN/exclusion, indexes/transaction-sensitive DDL, BIT/computed/collation/named-type/UUID/HSTORE | O07/O10 where an actual invariant needs the feature. Do not globalize release-scoped meaning into DOMAIN. No current BIT/HSTORE/collation/UUID-identity change justified. |
| 8.4 other dialect enhancements | Contextually inapplicable to PostgreSQL authority; no portability undertaking. |
| 9.1–9.3 released ORM/compiler/URL corrections | O01; select relevant regressions without a version campaign. Blank URL handling belongs explicit connection policy. |
| 10.1–10.4 capability compositions; 11 sources; closing synthesis | O04/O06/O07 compose schema, mutation and integrity; ORM execution composition unselected. Source maps are navigation, not additional demand. |

### Alembic

Reference: [advanced addendum](../libraries/postgresql/alembic.md).

| Added sections | Assessment and disposition |
|---|---|
| 1.1–1.3 detection gaps, normalization and constraint identity | O07; preserve stronger native checks. Digest-bearing CHECK names are meaningful; same-name changed expressions need independent comparison. |
| 2.1–2.5 add-column semantics, USING, NOT VALID, concurrent indexes, dialect options | O10; adding a Column does not automatically realize every unique/index property. Explicitly represent each required operation. |
| 3.1–3.5 programmable environment, revision arguments, CLI x/tag, templates and configuration | Existing env/caller Connection is sufficient. Generation-time template arguments can help when needed. Do not make one immutable revision choose different meaning via runtime flags. |
| 4.1–4.4 operation rendering, dialect implementation, extension selection and version table | O07/O12: `produce_migrations`, operation trees, `render_python_code`, `Rewriter`/directive hooks. `Operations.invoke` does not itself supply history. No custom dialect/version-table implementation needed. |
| 5.1–5.4 resultless execution, literal bulk insert, offline output and callbacks | Explicit live connection retained; exact archived SQL may need direct driver execution because `op.execute` text coercion treats colons as binds. Existing applied callback records steps, not final root commit. Offline emission is not deployment validation. |
| 5.5 SQL Server execution | Inapplicable to this PostgreSQL target. |
| 6.1–6.2 historical migration/schema/data testing and pytest-alembic | Reuse existing migration/native-closure controls; add PDF-25 retained-data cases under O10. No automatic new test dependency or downgrade campaign: base downgrade deliberately refuses destructive rebuild. |
| 7.1–7.3 CreateView/CTAS, named types and computed persistence | CreateView already used. CTAS serves disposable derived tables, not protected schema/grants. Adopt shared DOMAIN/computed forms only with explicit model/lifecycle ownership. |
| 8.1–8.4 release corrections, plugin compatibility, constraint rendering, batch indexes; 9 boundaries | O01/O07. An identity ALTER correction does not establish that the separate identity-comparison workaround is obsolete. |

### pglast

Reference: [advanced addendum](../libraries/postgresql/pglast.md).

| Added sections | Assessment and disposition |
|---|---|
| 1.1–1.2 fingerprint relation/script canonicalization | Retain existing refusal to use fingerprint as identity. Conditional query-shape diagnostics under O08; no cache/admission equivalence claim. |
| 2.1–2.4 visitor action generator, ancestor editing, node reflection and ancestry | O08/O12; use public Visitor/replacement/ancestor operations. `Visitor.iterate()` is not a generic read-only iterator; reconstruct ancestry after mutation. |
| 3.1–3.4 quoting, grammar context, enum printers and reusable streams | O08; ordinary printers/fresh streams replace repeated mechanics. No bespoke pretty-printer or private enum-printer dependency needed. |
| 4.1–4.4 comments, deparsing limits, spans and Unicode/error locations | O08 source diagnostics. Preserve exact authored text separately; printing does not establish exact editing. Existing ParseError position handling is a strength. |
| 5.1 PL/pgSQL CLI inspection | Explicit developer inspection; raw procedural dictionaries are not a typed rewrite or semantic-validation engine. |
| 6.1–6.5 normalize/serialization/version tuple/release/editorial corrections | Constrain correct API use; no substitute for exact admitted SQL identity. O01 settles upgrade direction; editorial artifacts do not justify product changes. |
| 7 primary-source map | Navigation for the above judgments. |

### Psycopg

Reference: [advanced addendum](../libraries/postgresql/psycopg.md).

| Added sections | Assessment and disposition |
|---|---|
| 1.1–1.2 dynamic connection inputs and drain | O09 conditional rotation, with explicit inputs. Not atomic revocation or cancellation of borrowers. |
| 1.3–1.4 lifecycle methods, logging and acquisition exceptions | O02/O03/O09; preserve current open/check integration, native failure taxonomy and diagnostics. |
| 2.1–2.3 Rollback, force_rollback, savepoint names/status | Conditional isolated dry-run/testing and diagnostics; retain Core owner. Suppressed rollback is not successful publication; sequences/external artifacts may escape rollback. |
| 3.1 PostGIS/Shapely | Conditional spatial query/index consumer; PDF pixel frames and provenance are not an earth-coordinate model. No PostGIS adoption for adaptation alone. |
| 3.2 NumPy | Conditional scalar-write simplification; not arbitrary array/Arrow interchange. |
| 3.3,3.5–3.6 value-dependent dumpers, contexts/factories and JSON | Extend existing connection-local adaptation only for real scalar needs. Keep model null policy and strict finite-number JSON. No global registry or parallel wire encoder. |
| 3.4 integer inference | Preserve declared bigint boundaries or explicit casts for actual identifier predicates; not blanket casting of every integer. |
| 3.7 timezone semantics | Preserve instant versus original timezone distinction. Analytical timestamps already use UTC; session timezone remains state. |
| 4.1–4.3 binary controls, PgBouncer preparation/deallocation and native capability checks | Explicit operation/wire policy; native checks at actual required boundaries. PgBouncer conditional on deployment need, not a new local middleware layer. |
| 5.1 offline COPY/FileWriter | Conditional Python-row replay consumer. Existing Arrow IPC replay plus pgpq is preferable for current PDF transport. |
| 5.2 returning executemany | Conditional homogeneous non-COPY writes needing results; compare set SQL first. Preserve per-result distinctions and full execution obligations. |
| 6.1–6.4 incomplete/chunked streams, server/held/adopted cursors | O05/O09. Close and settle transaction; held cursors remain session-bound and cannot implement pooled cross-session public continuations. |
| 7.1–7.2 synchronization versus flush, implicit grouping | Retain COPY/adoption and receipt boundaries. Pipeline only where independent non-COPY work benefits; flush is not transaction completion. |
| 8.1 cancellation | O09: `cancel_safe`, observed outcome and settlement; signal handler not the cancellation implementation. |
| 8.2 notifications | Conditional bounded wakeup consumer; durable task/progress state remains authoritative. |
| 8.3 protocol handles/info | Connection info for targeted diagnostics; raw socket/wrapper integration deferred until a concrete consumer needs it. |
| 8.4 DNS/transform hooks | Conditional remote discovery need; not a local connection-manager replacement. |
| 9 source/editorial qualifications | Availability assumption and O01 apply. No unsolicited rewrite of the library references. |

### psycopg-pool

Reference: [advanced addendum](../libraries/postgresql/psycopg-pool.md).

| Added sections | Assessment and disposition |
|---|---|
| A1/A1.1 zero-minimum regular pool/readiness | O09 optional intermittent MCP setting; preserve actual startup connectivity queries. |
| A2.1–A2.3 population/growth, waiting handoff and reset | Native owner retained; no bespoke queue, fairness promise or max-size-only capacity tuning. Keep callbacks light. |
| A3.1–A3.3 idle contraction, lifetime and resize | Native lifecycle retained; specify both bounds when resizing. No exact idle-revocation deadline promised. |
| A4.1–A4.4 return transaction state, membership, health recovery and null-pool checks | O03/O09; pool membership checks are not exactly-once task lease release. Transaction settlement and actual connection health are distinct. |
| A5/A5.1 close_returns compatibility | O03 regular-pool plus SQLAlchemy NullPool retained; null-pool substitution cannot assume the return contract. |
| A6.1–A6.4 foreground null-pool establishment/configuration/failure/timeout | Do not choose null pool for idle reduction alone. Acquisition timeout does not establish a hard complete-operation deadline. |
| A7.1–A7.6 statistics/measurement interpretation | O09 native metrics; SQLAlchemy getconn integration is outside `pool.connection()` usage timing. Supplement at borrower boundary only for a demanded missing metric. |
| A8.1–A8.3 state inspection, explicit opening and shutdown | Existing explicit opening retained; state flags are not connectivity. Settle borrowed operations before closing owner. |
| A9 editorial corrections | Reference maintenance outside this product/recommendation write scope. |

### pgpq

Reference: [technical addendum](../libraries/postgresql/pgpq.md).

| Added sections | Assessment and disposition |
|---|---|
| 1.1 schema fidelity/constraints | O04 retains model/Core/native authority; encoder DDL is not the persistence contract. |
| 1.2–1.3 generated composite lifetime, naming/OIDs | Current flat modeled staging avoids this machinery. Do not add a type registry for hypothetical nested transfers. |
| 1.4 independent schema constructors | Unneeded alongside generated Core metadata. |
| 2.1 batch validation | O04 retains exact full schema/metadata check; positional encoding cannot detect swapped same-typed semantic fields. |
| 2.2–2.3 stream integrity/error state | Fresh encoder per stream; restart after failure. DB rollback does not reset encoder state. |
| 2.4 buffer/resource behavior | Input bytes, encoded bytes and total live working set differ; flush thresholds are not memory ceilings. |
| 3.1 string/large-string/view JSONB builders | O04 choose matching builder for an actually adopted physical profile; avoid casts solely for a narrow local serializer. |
| 3.2–3.3 SQL NULL/JSON null/text validity | Preserve distinct semantics and native rejection, not catch-and-coerce. |
| 3.4 Char | No current consumer; not a substitute arbitrary integer encoding. |
| 4.1 Rust default construction | No current production consumer in inspected Python transfer path. |
| 4.2–4.3 closed encoder families and struct customization | Explicit modeled child relations/extensions preferable to custom encoder plugin framework. |
| 4.4 builder dictionaries | Current actual dict builder use already fits the API. |
| 5.1 remaining Arrow type limits | Typed nulls/physical-layout obligations remain explicit. No automatic normalization without a consumer. |
| 5.2 operational inspection | O09 conditional backend-PID COPY progress diagnostic; no default polling or authoritative progress percentage. |

### ADBC PostgreSQL

Reference: [addendum](../libraries/postgresql/adbc-driver-postgresql.md).

| Added sections | Assessment and disposition |
|---|---|
| 1.1–1.4 bound queries, non-COPY result path, parameter streams, preparation/schema | O05/O13. `$n` binds/Arrow parameter streams are available where a concrete Arrow consumer beats existing Core rows. Full bound effect execution cannot be inferred from partial result consumption; preparation is not persistent reusable server handle assurance. |
| 2.1–2.3 target-aware ingestion, type behavior and schema/temp APIs | Conditional independently owned imports under O04; not substitution into another session's scratch/adopt transaction. Target OIDs and column names do not replace governed DDL. |
| 3.1–3.4 uncommon types, timestamp precision, nested asymmetry and support matrix | O04/O05 exact model profiles. Domain/enum identity absent from physical Arrow representation; microsecond precision and restricted nested ingestion matter. Branch existence alone does not qualify a full transfer. |
| 4.1–4.2 manifests/profiles | Conditional packaging simplification when manual loader/configuration burden appears. Explicit reproducibility inputs; no ambient latest profile. |
| 5.1–5.2 Arrow C Stream/PyCapsule and backend choices | Existing incremental reader retained. Direct `fetch_arrow`/C stream useful for a new consumer otherwise forced to materialize; no wholesale raw-stream rewrite. |
| 6.1–6.3 metadata APIs, typmods and driver info | Useful inspection; not complete physical-contract verification, nullability/typmod authority or package inventory. |
| 7.1–7.4 close versus transaction, clones, options and concurrency | Explicit transaction/read ownership. Clone/new session does not inherit snapshot/temp state; autocommit options can commit and schema option names one identifier. |
| 8.1 structured error details | O02/O09 preserve available fields without inventing missing values. |
| 8.2 multi-statements/result navigation | Not multiple-result protocol; `executescript` can commit preceding work. No migration/seal shortcut. |
| 8.3 decimal fast-path | Explicit diagnostic only where conversion behavior is in doubt; no blanket throughput claim. |
| 8.4 generic facilities versus PostgreSQL implementation | No inferred partition/Substrait/named-binding/callproc/nextset support from generic interfaces. |
| 9.1–9.2 DuckDB ADBC extension | Conditional disposable operator research convenience. Remote explicit SQL needed for pushdown; independent/autocommit and concurrency boundaries do not replace consistent snapshot capture. |
| 10 inherited libpq | Native URI/services/TLS/passfiles/application name serve concrete configuration needs. Current capture already delegates URI handling; no bespoke auth mechanism to replace was found on that path. |
| 11 cross-capability synthesis | O04/O05/O09; useful compositions retain type, snapshot and stream-lifetime boundaries. |

## Research routes and primary sources

Read-only contributions: schema/SQL/migrations, transport/Arrow and connection/failure lifecycle. One root synthesis reconciled their overlap. No contributor edited files or inspected audit documentation. Context7 sometimes returned general examples rather than the precise PostgreSQL contract; those summaries were not treated as decisive evidence. In particular its drain summary was corrected from installed implementation, and an unrelated pgpq search was not treated as absence.

- [SQLAlchemy Core DDL](https://docs.sqlalchemy.org/en/20/core/ddl.html) and [engines](https://docs.sqlalchemy.org/en/20/core/engines.html): compilation, ordering and inspection orientation; repo addendum supplies the 2.1-specific interfaces.
- [Alembic autogeneration API](https://alembic.sqlalchemy.org/en/latest/api/autogenerate.html) and [cookbook](https://alembic.sqlalchemy.org/en/latest/cookbook.html): candidate operations, rendering and extension boundaries.
- [pglast Visitor source](https://github.com/lelit/pglast/blob/v8/pglast/visitors.py), [streams](https://github.com/lelit/pglast/blob/v8/pglast/stream.py) and [public entry points](https://github.com/lelit/pglast/blob/v8/pglast/__init__.py): AST mechanics and parser/normalization boundaries.
- [Psycopg pool integration](https://www.psycopg.org/psycopg3/docs/advanced/pool.html), [pool API](https://www.psycopg.org/psycopg3/docs/api/pool.html), [connections](https://www.psycopg.org/psycopg3/docs/api/connections.html) and [cursors](https://www.psycopg.org/psycopg3/docs/api/cursors.html): ownership, cancellation and native outcome vocabulary. Contributor inspected installed `ConnectionPool.drain`, `connection`, `close`, return logic and `NullConnectionPool.__init__`.
- [pgpq core encoder](https://github.com/adriangb/pgpq/blob/306cdf8cf2b8450a3162a9cd467422cb0849af5a/core/src/lib.rs): stateful batch encoding and compatibility boundaries.
- [ADBC PostgreSQL bound reader](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/result_reader.cc): bound result construction and consumption. Contributor inspected installed manager context exit and clone implementation; explicit rollback in existing capture is correct.

The addenda's topic-specific source maps retain the deeper references for capability families not selected for adoption. These references establish mechanisms, not tested applications in this codebase.


## Coverage of the original documented feature families

This account complements the addendum tables. Original section numbers below refer to the pre-addendum bodies recovered from `15c9b9e1`. Both bodies inform the resulting recommendations; newly considered functionality is not necessarily newly documented. API availability is assumed as directed. A contextual nonselection is not a claim that the capability is absent.

| Reference and original sections | Combined assessment |
|---|---|
| SQLAlchemy §§1–2: Core/ORM layers, expressions, CTE/LATERAL/window/VALUES, compiler extensions, caching, textual/template SQL | O06/O11; structured construction and stable preparation. Prefer explicit bind parameters and native expression APIs; no global expression registry. |
| SQLAlchemy §§3–4: metadata, naming, reflection, translation, views/CTAS, custom types, typed columns | O04/O07/O11; derive mechanical forms from the model. Reflection inspects deployed structure, processors do not cover raw COPY/ADBC, schema translation does not supply isolation. |
| SQLAlchemy §§5–7: mappings, UOW/identity, relationships, inheritance, dataclasses, hybrids/composites, mutation/versioning, loading and bulk DML | Substantively reconsidered but no concrete consumer justifies adding ORM state to the current immutable/batch architecture. A future object-editing workflow could change that; Core and ORM are composable, not mutually exclusive architectures. |
| SQLAlchemy §§8–10: transactions/isolation/pools, results/async, dialects, events, inspection/sharding | O02/O03/O05/O09. Core rows already suit current selective consumers; events must account for bypassing raw-driver paths. Async/shared binds/sharding/two-phase are conditional on actual participants, not modernization defaults. |
| SQLAlchemy §§11–16: batching/materialization/profiling, ecosystem integrations, corrections and synthesis | O01/O04/O11; separate construction, compilation, execution and hydration. Library/runtime type-sharing semantics constrain composition; no benchmark or upgrade-discovery campaign. |
| Alembic §§1–3: revision graph/heads/bases/dependencies and schema/data operations | O07/O10/O12; history, execution and data transformation are separate responsibilities. A second runner or multiple environment is not needed for ordinary forward changes. |
| Alembic §§4–5: metadata comparison/filtering, type rendering, operation trees, rewriting, custom objects/plugins | O07/O12; compare whole native-object lifecycle, including original replaceable-object recipes. Early filtering/multi-object reflection can avoid repeated discovery; no-change autogeneration is not complete native equivalence. |
| Alembic §§6–8: reconstruction/naming, online/offline/transactions, introspection/stamping/validation | Preserve frozen history and caller-owned transaction; stamp does not validate data/schema. Offline output and direct DDL kernel execution do not establish deployment or supply revision history by themselves. |
| Alembic §§9–10: multi-engine/schema/async, reflection, concurrency, compatibility windows and data transitions | O10/O12: substantial data migration deserves its own operation/recovery boundary. No multi-tenant/multi-engine undertaking or compulsory reversible base downgrade. |
| Alembic §§11–14: Alembic Utils, ENUM/schema companions, capability synthesis/source map | O12 materially broadens the comparison beyond rendering. Evaluate supported objects and simulation privileges against application-specific admission; enum/other companions remain conditional on a selected semantic need. |
| Psycopg §§1–4: protocol/cursor strategies, binding/composition/templates, automatic preparation | O03/O06/O11: retain one authoring owner per operation and session-local prepared-state rules. Raw/client cursors are alternatives for a concrete protocol mismatch, not universal replacements for Core. |
| Psycopg §§5–7: pipeline, typed row/block COPY, scoped adaptation/scalars/JSON/arrays/composites/enums/ranges | O04: existing row-oriented `stage_batch` is already native COPY; do not force rows through Arrow just for uniformity. O11 retains exact type/profile identity across schema changes. Native values are candidates for operation-shaped projections, not compulsory canonical storage changes. |
| Psycopg §§8–10: row factories, cursors/streams/results, transactions/savepoints/isolation/two-phase | O02/O05/O09: model validation and Core mapping already serve existing row consumers. Native row factories can serve a genuine direct-driver consumer; they do not warrant a parallel object layer. Savepoint recovery and full-operation replay require distinct effect knowledge. |
| Psycopg §§11–13: thread/async ownership/cancellation, pools, notifications/notices/errors/info/libpq | O02/O03/O09; copy structured notice fields during callback lifetime. No custom socket loop, two-phase coordinator or durable notification queue is justified by this local single-authority target. |
| Psycopg §§14–19: ecosystem/responsibility combinations, performance/guarantee limits and references | O01/O04/O11. PostgreSQL driver semantics do not automatically generalize to every wire-compatible server. Native preparation and adaptation do not discharge domain outcome/replay obligations. |
| Pool §§1–4: regular/null sync/async, borrow/session lifetime, sizing/admission | O03/O09; distinguish aggregate operation demand from per-pool capacity. Regular zero-minimum and null pooling are alternatives with different return contracts. |
| Pool §§5–8: configure/check/reset, middleware, reconnect/timeouts, open/resize/drain/dynamic inputs/close | O03/O09/O11: reset/prepared-state/type-loader policies must compose. Borrowed cancellation and idle inventory shutdown remain different responsibilities. Reconnection is not operation replay. |
| Pool §§9–11: statistics/logger, SQLAlchemy close_returns, typing/adapters/preparation/COPY/cursor occupancy | O02/O03/O09; native statistics plus actual borrower timing only when useful. Manual return integration and callback scope determine what metrics/configuration actually cover. |
| Pool §§12–14: corrections, limits and full-capability synthesis | O01 and combined failure/ownership constraints; no implied readiness or hard cleanup deadline from a state flag/timeout. |
| pglast §§1–5: raw syntax, native/JSON/Protobuf forms, typed construction/equality, visitors/actions/ancestors | O08; no conversion between serialized forms by shape assumption. Preserve distinctions between structural and catalog-resolved meaning. |
| pglast §§6–10: scanner/split slices/Unicode, fingerprints, precedence/safety-belt/printers, comments and PL/pgSQL/CLI | O08: original-source slices can improve exact diagnostics; parse/print checks establish structure only. Global printer overrides and mutable streams cannot silently shape unrelated product identity. |
| pglast §§11–15: structural/agent/migration tools, adjacent parsers, catalog combination, performance/correctness/packaging/source map | O08/O12: server catalog facts remain decisive. No Rust or cross-dialect AST path without a concrete consumer; licensing is not a rejection reason. |
| pgpq §§1–3: transport-independent stream encoding, schema, numeric/temporal/null profiles | O04/O11; native encoders already discharge binary serialization, not model precision/absence semantics. Correct schema/stream lifetime must survive shared preparation. |
| pgpq §§4–5: lists/composites/OIDs, explicit builders, JSONB/arrow-json | Bounded operation-shaped nested/JSON projections remain candidates when they remove actual Python materialization. Current normalized flat records retain enforcement/querying strengths; no new generic encoder registry. |
| pgpq §§6–8: source scanner pushdown, sync/async transport, staging/SQL, performance/error/RLS constraints | O04/O06/O10: source filtering and database set operations can remove work before transfer. Async transport does not make synchronous encoding concurrent; COPY/encoder/transaction errors remain distinct. |
| pgpq §§9–10: Rust composition, sources and synthesis | Conditional future Rust-owned operation; no reason to port the current Python ownership layer merely because the encoder has Rust internals. |
| ADBC §§1–4: native handle ownership, clone/reader/stream/binds, ingestion modes and staging | O04/O05; compare complete ADBC-owned operations fairly. Preserve existing same-session admission until a whole-operation alternative improves the result. Bound result APIs and COPY buffering differ. |
| ADBC §§5–6: exact lexical numeric, nested/extension metadata, builtin/server OID discovery/cache | O04/O11; exact values and convenient analytical projections remain separate. Type-resolution mode/cache lifetime follows actual custom-type needs and schema evolution, not a global default change. |
| ADBC §§7–8: object/schema/statistics APIs, transactions/options/cancellation and diagnostics | O09 and conditional operator exploration. Approximate catalog statistics cannot certify completeness; metadata APIs do not replace function/privilege/typmod admission checks. |
| ADBC §§9–11: scanner/Polars/pandas/engine integration, boundaries and sources | A direct Arrow-consuming research workflow may justify a dedicated integration; current Core readers and captured Arrow are retained until such a consumer makes the change worthwhile. No universal adapter or second publication engine. |

### Audit validation

Final scoped links/anchors and maintenance outcomes are recorded in the audit companion. Runtime probes, database migrations, provider journeys and measurements were **not_run** during this source-led audit; no inspected historical receipt is promoted to a current pass.
