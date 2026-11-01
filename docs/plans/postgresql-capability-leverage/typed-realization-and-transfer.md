# Typed relational realization and directional transfer

**Proposed target, 2026-11-01.** [Coordinator](../postgresql-capability-leverage_2026-11-01.md) owns PG-03/04/06 and PG-I02. Source O04/O05/O06/O11/O13 inform this design.

## Shared source facts, distinct execution contracts

Extend the existing physical model/Core metadata rather than add a second schema. Derive static typed column surfaces and stable relational operation shapes from the same declarations that govern native enforcement. `schema/relational.py`, `semantic/metadata.py`, `pdf_record_model.py` and `analytics.py::compile_projection` identify the actual current consumers.

Separate:

1. Semantic projection: family/field meanings, visibility, permitted filters, ordering, exactness and published pin.
2. Prepared realization: Core expressions, Arrow field descriptions, decoder/encoder requirements and dependencies.
3. Per-operation binding: product/project/run/filter values, actual snapshot and session state.
4. Directional transport: source representation → target wire representation with explicit supported layouts and loss/refusal rules.

These can be ordinary functions and immutable prepared values; no generic query DSL, universal adapter or durable preparation store is selected. Use SQLAlchemy `TypedColumns`, generic tables/selectables and `with_cols` for generated static surfaces where they improve real callers. Static typing is not runtime admission.

## PG-03 — Prepare the stable part once

Reuse structure at the semantic/physical/compiler/profile lifetime. Bind changing values through parameters. Engine statement caching covers eligible execution; direct `.compile(literal_binds=True)` for ADBC COPY SQL does not acquire that cache automatically. Reuse its construction only where stable structure actually warrants it; render values with the dialect rather than interpolate arbitrary strings. `lambda_stmt` is optional when Python-side statement construction is material, not a compulsory second cache.

Session OIDs, prepared statements and adapters follow physical-session/catalog-generation lifetime. Do not cache a live privilege/admission conclusion solely by release ID. TypeDecorator/result processors do not cover raw pgpq or ADBC; put required normalization in the directional profile's actual execution path. Preserve SQL NULL, JSON null, missing, exact lexical numeric, timestamps and metadata distinctions.

For Python-owned relational construction, use Core set operations, CTEs, table-valued functions, LATERAL/window operations, `Insert.from_select`, explicit defaults/RETURNING and ordered aggregation where they preserve complete intent. Keep effective native set SQL where changing notation removes no work. Correlate generated results through explicit keys or documented order support; never zip arbitrary RETURNING order to input records. A default evaluated once per INSERT SELECT is not a per-row domain function.

**Closure:** two pins reuse eligible structure while returning different correct rows; changed model/type/profile invalidates the affected shape; static wrong-column/type cases fail typing; raw and Core paths preserve independent exact-value expectations. Do not test cache correctness only through identity of the cache object.

## PG-04 — Shared preparation for actual writers

Select the existing Core transaction → checked Psycopg borrower → pgpq stream → protected adoption route for ordinary Arrow publication and private batch writers. Share ordered field/type/JSON builder preparation and output-schema checking, with a fresh stateful encoder for every COPY stream. Check semantic names and metadata, not just positional physical compatibility: swapped same-typed columns must refuse. Keep batch limits, replay identity, current claim fences and durable admission at each operation's owner.

Preserve `publication.stage_batch` row COPY using `Copy.set_types`/`write_row`; converting domain rows to Arrow solely for helper uniformity is counterproductive. pgpq's generated DDL is not the model's full constraint contract. Handle matching string/large-string/view JSONB builders when a selected profile needs them. Failed native encoding requires a fresh encoder; DB rollback alone does not reset it. Input size, encoded buffers and total live working set are different; an encoder flush threshold is not a memory ceiling.

**PG-I02:** source already in PostgreSQL should normally move through server-native SQL rather than leave and return. A standalone Arrow/Parquet import is not automatically added to scope. If a required operation encounters such an input, compare a full ADBC-owned temporary ingest + protected SQL + explicit commit/rollback against the selected Psycopg route. ADBC target-aware name/OID lookup can remove actual reorder/type work, but opening another connection cannot inherit another owner's transaction/temp tables. Record the complete choice before implementing it; do not maintain two writers for hypothetical replaceability.

**Closure:** independent expected rows for empty/reordered/conflicting batches, numeric extremes, SQL versus JSON null, oversized individual values, failure during encoding and failed native adoption. Check fresh encoder after failure and no partial public visibility. Reuse production validators when testing their consumers, but retain independent expectations for the validator's own semantic contract.

## PG-06 — Typed published-family analytical port

Deliver model-derived projections for published input, relation, coverage and mapping-report families. Include publication identity and the modeled fields used for actual inventory/coverage comparison. Relations expose their model-defined kind, ordered/multiple occurrence identity, source and target product-qualified endpoint/address, and unresolved-target state where meaningful; a local record ID alone is not an endpoint. Inputs carry qualified source bindings; coverage carries scope and outcome; mapping reports carry source/target scope and status. Derive field names and physical encodings from the current model rather than infer semantics from JSON spelling. Expose bounded JSON only where the model genuinely owns opaque extensions; do not flatten every native field merely to claim a columnar API. ADBC table/query introspection does not supply full typmods, nullability or domain meaning and is not the schema owner.

Use protected native projections/functions or an equivalent authorized Core relation so ordinary callers cannot bypass published visibility. Reuse the same semantic projection for compatible row and batch consumers; do not grant raw table access to avoid JSON. An ADBC read operation owns its session/cursor/reader. Import the exporting Core snapshot where mutable selection/authorization premises participate; immutable product content does not alone make the mutable selection step consistent. Release both sessions after capture, before long local computation. A clone shares metadata state, not session/snapshot/temp tables.

For bulk projection use ADBC COPY-result batches and existing capture/spool lifetimes. Keep Core bounded rows for small inspection. Native `$n` bound ADBC queries remain an option for result-sized Arrow consumers, not the default large transfer: their result buffering and lazy multi-parameter effects differ from COPY hints. Never infer all writes executed from partial returned-stream consumption.

The completed operation streams each selected family to Parquet and supplies an owned manifest naming product/release/projection/schema, actual row counts and file byte identities. Reuse existing capture/artifact representations where they provide those meanings; no second certificate system. DuckDB consumes those files to produce a pinned input/relation/coverage inventory, preserving partial/unknown outcomes. [Consumer owner](consumer-capabilities.md) specifies entry points and acceptance.

## Library basis and execution fit

[SQLAlchemy original §§2–4/8/11 and addendum §§1/2/7](../../libraries/postgresql/sqlalchemy.md), [pgpq original §§2–8 and full addendum](../../libraries/postgresql/pgpq.md), [ADBC original §§3–9 and addendum §§1–8](../../libraries/postgresql/adbc-driver-postgresql.md), and [Psycopg COPY/adaptation](../../libraries/postgresql/psycopg.md). Filter/project before expensive movement where meaning permits; preserve needed context and exact negative/completeness semantics. FP-04/07, DP-06/09/10/15, H5–8/H12/H15–17 favor operation-shaped batches without making zero-copy or one representation an objective. Benefits remain qualitative until measured.
