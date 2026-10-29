# Consumer read boundary and interfaces

This page records comparative judgments for:
- CBO-001: the composable semantic read boundary;
- CBO-025: read-only snapshot opening;
- CBO-016: release-typed instance traversal;
- CBO-012: refusal mapping;
- CBO-007: exports;
- CBO-023: the math deadline under FastMCP.

Baseline, inputs and method are in the [README](README.md). Paths are relative to
`python/corpus-structure/src/corpus_structure/` unless they start with `domains/` or `docs/`.
Every recommendation is **Proposed**.

SP-08 has already built much of this surface: `serve/read.py`, `serve/journey.py`,
`serve/export.py`, `cli/{query,explain,export}.py` and `intervene/semantic_server.py`. The judgments
below assess those implementations against the recommended targets.

<a id="cbo-001"></a>

## CBO-001 — One public read route: promote the kernel primitives, keep serve policy in serve

**Premise, at `0350a7a`.** The opportunity is still high value. The refresh is accurate, and the
review adds the following.

**Live defect** (coordinator-verified; this is a defect, not a leverage claim).
- The generic `claims` query's `object=` filter reads `typed_value.c.lexical` (`serve/queries.py:50`),
  a column that does not exist.
- It raises `AttributeError`, which the CLI refusal handler does not catch.
- No test passes `object`.
- Even with the column fixed, lexical equality on decimals is not value equality.

**Two contracts side by side** ([LOP-X010](../assessment-patterns.md#lop-x010)).
- `serve/read.py` builds on private kernel internals: `_scope`, `_same_scope`, `session._values`,
  `_entities` and `_occurrence_contexts`.
- The pack plugins `domains/{statistics,toy}/queries.py` also import `_same_scope`, and one of them
  calls `ctx.session._entities`. The private API is therefore already an external authoring
  surface.
- The kernel's public `ReadSession.query`/`QuerySpec` and its token scheme have only test callers.
- There are two name resolvers. Only `Reader.iri` refuses ambiguity.
- There are two adapter caches, and they choose adapters differently.

**Unbounded explanation.**
- `explain` returns whole-realization coverage in every explanation, against D8 §3's 6,000-character
  bound and its "top 10 supports".
- The `Evidence` query builds a full explanation only to return the evidence.

**Weaker demand than the opportunity assumed.**
- No current consumer explains many facts at once.
- Evaluation deliberately grades authored payloads, which is CBO-006's territory, not a read-boundary
  consumer.

**Phase tension.** D8 §2 (Proposed) puts MCP query/explain in phase 1, while SP-08 acceptance asks
for "real CLI/MCP dispatch".

**Options.**
- **A. Keep the split.**
- **B. Promote kernel primitives.** Make them public, keep the Reader in serve on top of them, and
  make the journey token the only continuation scheme.
- **C. Move the Reader into `semantic`.** The kernel would then own serving conventions such as
  label properties, modality exclusion and casefold policy.
- **D. A wire-level predicate DSL.**

**Shared decisions.**
- **Is a closed predicate vocabulary inside SP-08's "no query language"? Yes, while it stays closed.**
  - Named, versioned queries with flat, closed Pydantic parameter models are not a query language.
  - A query language begins when callers can compose: boolean combinators, nesting, property paths,
    or arbitrary operators over arbitrary properties.
  - Composition is written as plugin Core.
- **Predicates without an exact lowering are refused, not answered "unknown".**
  - Static gaps are refused at parameter validation. Examples: float ordering over hexadecimal text,
    and value-meaning equality where the reader lacks EXECUTE on `data.value_matches`.
  - Data-dependent gaps, such as `NULL` `numeric_value`, get an exact residual check over
    `decimal_lexical` during hydration, or are refused.
  - `unknown` stays a coverage state (CI-04).

**Revealing case.**
- SP-04's independent expectations run through `QuerySpec` in seven test files; one of them uses it
  12 times as an independent read path for domain outputs. They check wrong-release refusal,
  `StaleSnapshot` versus `WrongRelease`, and class-scoped selection that includes subclasses.
- Retiring `query` wholesale would lose the `StaleSnapshot`/`WrongRelease` distinction, because the
  journey collapses everything into `StaleToken`. It would also tie domain tests to serving policy.

**Recommendation: recommended target B.**

*Kernel* (`semantic/query.py`):
- Public `scope`/`same_scope`.
- Public `values(roots, subjects)`, `entities(ids)` and `occurrence_contexts(ids)`, accepting either
  a set or a Core subquery ([LOP-X005](../assessment-patterns.md#lop-x005)).
- `hydrate(rows)`, moved from `serve/read.py`: decode, adapter chosen through the release index
  ([CBO-013](release-lifecycle.md#cbo-013)), strict validation, attached qualification, reachable
  node closure. One adapter cache.
- Public `selection(class_handle, property_handle, projection, subject_ids)`, without limit or token.
- Binders by realization and by completed run, both over the [CBO-025](#cbo-025) opener.
- `explain` scopes coverage to the fact's family and gets an evidence-only mode. `explain_many`
  waits for a multi-fact consumer. Decide a bounded shape before any MCP `explain`.

*Serve:*
- The Reader keeps the label, modality and casefold policy, built only on the public API. It is the
  documented plugin surface, together with `T`, `scope` and `same_scope`.
- The journey token is the only continuation. `StaleToken` carries a reason code:
  release, revision, projection, query or params.
- `context()` moves from `cli/query.py` into serve, alongside an `open_read(settings, …)` that
  composes engine, snapshot, run selection and registry. The engine comes from
  [G5](engineering-workflows.md#cbo-004).
- Fix the `object` filter under the exact-or-refuse rule.
- The Reader raises `QueryRefused` for caller faults.

*MCP*, only if SP-08 overrides D8's phase placement:
- Thin `query`/`explain` tools over the same functions, using the reader principal and one snapshot
  per call.
- `ResponseLimitingMiddleware` only as the lossy backstop D8 already describes.

*What disappears:* the second token scheme, the second resolver, the second adapter cache, and
private imports in serve and in plugins.

*Transition:* incremental. Public aliases first, then the `hydrate` move, then retiring the token.
The seven test files move to the public `selection` plus `hydrate`.

**Rule impacts.**
- The SP-04 boundary text in `queries-and-consumers.md`: the continuation owner moves to the serve
  journey.
- The exact-or-refuse predicate rule belongs in SP-08 / D8 §5.
- MCP read-tool phase placement: D8 §2 versus SP-08 acceptance.
- No change to a §B decision.

<a id="cbo-025"></a>

## CBO-025 — One owner for read-only snapshot opening

**Premise corrected: six openers, not seven.**
- The openers are `query.py` (`read_session`), two in `domain_operations.py`, and `cli/query.py`,
  `cli/explain.py` and `cli/export.py`.
- `authored_sql.py` is a read-only catalog admission at default isolation, so it is excluded.
- The ADBC import in `analytics.py` is raw DBAPI and must stay hand-written.

**Options.**
- **A.** Keep as is.
- **B.** Swap in `postgresql_readonly=True` at each site.
- **C.** One opener, `snapshot(engine)`, using
  `execution_options(isolation_level="REPEATABLE READ", postgresql_readonly=True)` and owning
  `begin()`, with the realization and run binders on top.
- **D.** A read-purpose engine preconfigured with these options.

**Revealing case.** With `NullPool` over a psycopg pool using `close_returns=True`, SQLAlchemy's
checkin reset writes an explicit `read_only=False`. Later transactions then emit `READ WRITE`,
overriding any role-level `default_transaction_read_only`. No role sets one today, so this is
harmless. Do not adopt role-default read-only as a guarantee without revisiting it.

**Recommendation: recommended target C.**
- It realizes ADR-0026's "SQLAlchemy owns a read-only REPEATABLE READ snapshot" literally. The
  invariant holds by construction, and the journey's server-side check becomes local.
- D is an optional addition owned by G5. On its own it would miss `domain_operations`, which reads
  through the writer engine.
- SQLAlchemy 2.1.5 behaviour was confirmed in installed source: `postgresql_readonly` sets psycopg's
  `read_only`, and psycopg composes `BEGIN … READ ONLY`
  ([sqlalchemy](../libraries/sqlalchemy/README.md#sqlalchemy-transaction-characteristics)).

<a id="cbo-016"></a>

## CBO-016 — One reference-position classifier and visitor over validated models

**Premise: drift is now observed, not hypothetical.** Comparing `evaluate/semantic_values.py` with
the domain walkers:

1. **Subtype resolution.** The domain walkers validate through the release. The evaluation walker
   infers subtypes from key sets on raw dicts.
2. **What counts as an entity reference.** The domain uses any non-inlined property whose range is a
   release class. Evaluation uses only `Entity` and its descendants.
3. **Collision policy.** The domain refuses distinct collisions. Evaluation refuses any collision.
4. **Sequence type.** The two use different sequence types.
5. **Multivalued fact-role references.** `_claim_references` would add a whole tuple. This is latent:
   the current fact references are single-valued.
6. **`_known_input`'s key-name heuristic** is still present.

**Options.**
- **A.** Parity tests only.
- **B.** A release-owned classifier plus a collect/rewrite visitor over validated models, with the
  plain projection done by `model_dump(exclude_unset=True)`.
- **C.** Compiler-attached `Annotated` markers. Ruled out by the library assessment.
- **D.** Share only the classifier.

**Revealing case.** Strict validation could refuse goldens that the dict walker tolerates, or goldens
stored under another release. The condition: validate under the release the payload was admitted
under. Golden storage was not checked.

**Recommendation: recommended target B, built on D.**
- `positions(class)` returns entity, fact, inlined, keyed or scalar.
- `references(range, model)` and `rewrite(range, model, entities, facts, *, sequence, collisions)`
  take the sequence type and collision policy as explicit parameters.
- The domain walkers become wrappers. Evaluation validates `AgentStoredBatch` before walking.
  `FactValueLowerer` keeps its own traversal but consumes the classifier.
- Remove the `_known_input` heuristic.
- The position index lives on the product as non-identity state ([CBO-013](release-lifecycle.md#cbo-013)).
- The rule that only descriptors make references then holds by construction.

<a id="cbo-012"></a>

## CBO-012 — One refusal registry, with a decorator rather than middleware

**Premise, partly changed.**
- *MCP:* four tools map `(ProposalRefused, OperationConflict)`. `queue_status` and
  `record_direction` have no mapping. `propose_claims` returns typed dispositions.
- *FastMCP 4.1.3 behaviour.* Under the default `mask_error_details=False`, an unmapped exception
  already becomes `ToolError`, but with a logged traceback. The core layer logs and wraps *before*
  middleware sees the exception.
- *CLI:*
  - The shared `refusal()` in `cli/query.py` catches broad `ValueError`, `LookupError` and
    `OSError`, but not `DBAPIError`.
  - `golden` catches `DBAPIError`.
  - `regenerate` now catches `SQLAlchemyError` in the uncommitted tree, which conflates retryable
    database errors with refusals.

**Options.**
- **A.** Per-site handling, as now.
- **B.** A FastMCP custom middleware plus a Typer root `cls=` group.
- **C.** One refusal registry: domain refusal classes plus `DBAPIError` classified by the existing
  `core/db/store.classify_error`. A shared CLI `refusal(json)` lives in `cli/output.py`, and an MCP
  `@refusing` decorator is applied through a local tool wrapper, so new tools are covered by
  construction.
- **D.** The built-in `ErrorHandlingMiddleware`. Rejected: it turns tool errors into protocol
  errors.

**Comparison.**
- Middleware cannot suppress the traceback, because logging happens before it runs, so it would
  have to unwrap `__cause__`.
- A decorator works. A scratch check by the G1 reviewer (FastMCP 4.1.3, in-process `Client`) showed
  that a `functools.wraps` decorator under `@mcp.tool` keeps `Context` injection and the advertised
  schema, and returns `isError` with the plain message and no traceback.
- The Typer root group cannot see the per-command `--json` flag.

**Revealing case.**
- Narrowing the CLI catch to typed refusals would turn caller-input `ValueError`s into tracebacks
  unless the Reader first raises `QueryRefused`.
- `propose_claims`' internal typed handling must stay first, so that schema and packet errors keep
  not consuming the one correction.

**Recommendation: recommended target C.**
- `DBAPIError` is classified as RETRY ("transient; retry"), FENCING (conflict) or DEFECT (refusal,
  no traceback). The exit code stays 1.
- Keep the pages-plus-hash protocol rather than a release-bound input schema.
- Retire `intervene/testing.py` with SP-09.

<a id="cbo-007"></a>

## CBO-007 — Retain the physical export; semantic exports wait for demand

**Premise.** `ci export` is a complete *physical* export:
- a run-bound snapshot;
- an ADBC import;
- Arrow with `cs.*` metadata, written as Parquet (`store_schema=True`) or JSONL
  (`allow_nan=False`, decimals as strings);
- a manifest;
- an atomic rename.

`AnalysisScope` settings are not on this path, because no DuckDB is used.

What the physical export does not cover:
- `capture_packet` is still uncalled.
- Relations are held in memory.
- Each export embeds a fresh capture uuid.
- D8 §6 (Proposed, phase 1) names *semantic-answer* exports, which the physical export does not
  serve.

**Options.**
- **A.** Keep the pyarrow whole-spine export.
- **B.** DuckDB `COPY … KV_METADATA` for everything.
- **C.** Subset capture.
- **D.** Answer exports from the query path.

**Comparison.**
- B adds a hop that drops `cs.*` ([DuckDB applicability](../libraries/duckdb/README.md#applicability-cbo-007)).
  It is the right writer only for tables DuckDB itself computes.
- C breaks semantic closure: a `fact` subset without its value closure, evidence and coverage scope
  is unreadable, or turns unknown into absent.

**Recommendation: retain current, with three adjustments.**
- Route through `open_read` / the [CBO-025](#cbo-025) opener.
- Delete `capture_packet` or re-point it at the shared binder.
- Stream through `pq.ParquetWriter` only if memory becomes binding.

Subset and semantic exports stay **unsettled until demand exists**. When a consumer is accepted, use
D, not C. Use B only for derived analytical Parquet built inside `AnalysisScope`. D8 §6's "Parquet
through DuckDB" should read as "derived analytical tables only".

<a id="cbo-023"></a>

## CBO-023 — Math deadline under FastMCP

**Recommendation: retain current.**
- No MCP or serve path imports the grammar, and `require_main_thread()` fails loudly.
- If a future MCP tool must run the grammar, use `run_in_thread=False`: the deadline bounds the
  blocking, and stdio has a single client.
- Adopt a process-pool deadline only together with an HTTP or multi-client transport.

See [fastmcp](../libraries/fastmcp/README.md#applicability-cbo-023) for the threading facts.
