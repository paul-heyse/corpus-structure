# Consumers and domain operations

Opportunities in the semantic read surface used by SP-08 consumers, exports, domain decisions,
scientific comparison, the CLI and MCP surfaces, and the instance traversal those consumers repeat.
Baseline, scope and labels are in the [README](README.md). Paths are relative to
`python/corpus-structure/src/corpus_structure/` unless they start with `python/` or `docs/`.
Line numbers cite the reconciled tree at `f697233`.

Strengths that bound these opportunities:
- `query.py` uses release-, revision- and fingerprint-pinned keyset tokens, and reconstructs values
  with one recursive CTE plus two bulk reads instead of per-row queries.
- `consolidate_cut` runs fusion and views in one DuckDB `AnalysisScope` over Arrow.
- Exact-replay `_completed_result` refuses any change of policy or version.
- `align.py` and `equivalence.py` are strong library users: SciPy `linear_sum_assignment`,
  RapidFuzz, SymPy and seeded NumPy.
- Claim premises are ordered with stdlib `graphlib`, and union-find over scientific decisions is
  small and appropriate. No graph library is warranted.
- The CLI `emit` writes the same `model_dump_json` shape the MCP returns.
- `Planned` stub commands exit 1 honestly.
- Semantic MCP tests drive FastMCP's in-process `Client`.

<a id="cbo-001"></a>

## CBO-001 — SP-08 consumers have no composable semantic read boundary

**Label:** accepted planned (SP-08). **Altitude:** subsystem, shared by every consumer.

**Operation and consumer.** These consumers must each select a release-bound projection, filter it,
page or stream it under a response budget, reconstruct typed values, explain facts and emit a
surface-specific format:
- CLI `query`, `explain` and `export`;
- MCP query/explain tools;
- evaluation readers;
- exports.

[SP-08](../../plans/semantic-model-pivot/queries-and-consumers.md#SP-08) requires real CLI and MCP
dispatch, continuation across active-release changes, stale-token refusal and context-identified
exports.

**Current mechanism.**
- **Semantic queries are narrow.** `ReadSession.query` takes a stdlib dataclass `QuerySpec`
  (`semantic/query.py:67-80`) that expresses one class handle, one property handle, a projection,
  `subject_ids` and `page_size`. It loads the page with `.all()` (`:1036`). Its continuation scheme
  lives in `_selection` and the token checks (`:398-476`). `explain(fact_id)` handles one fact
  (`:1097`) through a dozen statements.
- **Value reconstruction is reached privately.** `domain_operations.py:521` calls the private
  `session._values(…)`. Reconstructing typed values by id under a snapshot is needed by more than
  queries, but it is not public.
- **The CLI still serves through the legacy layer.** `cli/query.py:16-18` imports `serve.journey`,
  `serve.queries` and `serve.registry`. That layer has its own capabilities: object, subject and
  label filters, BM25 search with a composite keyset (`serve/queries.py`), a run-based continuation
  scheme, and `max_rows`/`max_chars` response budgets (`serve/journey.py`). Two token schemes
  therefore coexist.
- **The semantic MCP server offers no query or explain tool.** Its six tools are queue, read,
  propose and release operations (`intervene/semantic_server.py:221-361`).
- **There is no export command** (search of `cli/` and `serve/` for "export").

**Why it matters.** Without one boundary, each SP-08 surface rebuilds request validation,
predicates, continuation, size bounds, value decoding and explanation. That repeats the legacy
pattern on the new model.
- Domain queries need predicates over `typed_value` and `value_role`, and label lookup, beyond a
  single class/property slot.
- Exports and evaluation need explanation over many facts. Calling `explain` per fact multiplies
  round trips.

**Patterns.** LOP-05 (consumer intent cannot reach the Core expression), LOP-04 (one-fact
explanation), LOP-09 (two token schemes; consumer-local decoding), LOP-12.

**Footprint.**
- *Known:* the sites cited.
- *Suspected:* evaluation readers (legacy text SQL in `evaluate/sets.py`) and golden storage will
  need the same primitives.

**Preservation constraints.**
- Continuation pins release, realization, revision and query fingerprint, and refuses on change.
- Active-pointer changes never rebind a token.
- `knowledge` stays observed / absent / unknown, and coverage stays unknown versus absent.
- Strict release-derived validation (a wrong projection cannot be relabeled).
- REPEATABLE READ, read-only snapshots, and evidence closure over the same snapshot.
- C-collated ordering.
- [ADR-0026](../../adr/0026-columnar-semantic-operations.md): Arrow/DuckDB derived only.
- The SP-08 text forbids a generic introspection service or a new query language.

**Counterevidence.**
- SP-04 was deliberately minimal.
- Request schemas depend on the release, so static Typer options cannot express them. The
  `NAME=VALUE` plus Pydantic validation in `cli/query.py` is a reasonable reason for some custom
  work.
- Rich, JSON and Arrow rendering legitimately differ.

**Research leads.** [sqlalchemy](../../libraries/sqlalchemy.md): Core composition,
`yield_per`/`stream_results`, lateral and `table_valued`. [psycopg](../../libraries/psycopg.md):
server-side cursors. [pydantic](../../libraries/pydantic.md): `TypeAdapter` over `QuerySpec` for
wire validation and JSON Schema. [fastmcp](../../libraries/fastmcp.md): `ResponseLimitingMiddleware`.

**Questions for library research.**
1. Can a release-checked predicate builder over `typed_value`/`value_role` express current domain
   filters while staying visible to the planner?
2. Can one validated request/continuation/size-bounded envelope serve CLI, MCP and export?
3. Can explanation become set-oriented (`fact_id = ANY(…)`) and value reconstruction a public batched
   operation, reusing the same statements and envelopes?

**Related.** [CBO-003](release-preparation.md#cbo-003) (every session reloads the release);
[CBO-007](#cbo-007) (exports).

**Library assessment (2026-10-29).** Core fits with conditions ([applicability](../libraries/sqlalchemy/README.md#applicability-cbo-001)). Three exact-lowering gaps were not recorded above: floats stored as hex text, decimals with `NULL` `numeric_value` beyond NUMERIC bounds, and the reader lacking EXECUTE on native value functions. `_values`/`_entities` use expanding `.in_()` ([LOP-X005](../assessment-patterns.md#lop-x005)). Concurrent SP-08 commit `7cfd7f8` added `serve/read.py` and migrated serving; refresh this premise before review.

<a id="cbo-005"></a>

## CBO-005 — The released rule policy evaluates semantic candidates through the retiring rule environment

**Label:** current; SP-09 retirement is accepted planned. **Altitude:** subsystem, the domain
decision operation.

**Operation and consumer.** `consolidate_cut` calls `ReleasedRulesPolicy.evaluate` to decide
selection, warnings and errors over release-bound candidates. The CLI consumer is `ci run finalize`.

**Current mechanism.**
- **The rule type environment is assembled by hand from two sources:**
  - the legacy string-typed dicts `BINDING, CLAIM, ENTITY, NODE, STATEMENT, VALUE`, imported from
    `schema.rules` (`domain_operations.py:2253`);
  - a hand map from LinkML range to rulelang type notation (`"number?"`, `"string?"`, `:2303-2307`).
- **Candidates are projected into legacy shapes:**
  - legacy view dataclasses from `validate.views` (`:2894`);
  - legacy view specs from `pool.steps` (`:2408`, `:2986`);
  - `consolidate.finalize.GRAMMAR_KINDS` (`:2892`);
  - `core.keys.LabelRules` (`:798`).
- **It calls a private comparator method:** `comparator._constraints` (`:2765`).
- **The rule language relies on rule-engine internals.** `schema/rulelang.py` reads
  `rule.statement.expression` (`:242`) and the private `_object_type` (`:309`). It also uses a hand
  string type notation that the policy builds from LinkML ranges, a round trip.

**Why it matters.** SP-09 must retire "replaced model projections, dispatch paths" and legacy
modules. Surviving decision code depends on at least six of them, so retiring them breaks the
policy unless it is rebased first. Each new LinkML range or qualifier shape also needs parallel
edits to the hand type map and the legacy dicts.

**Patterns.** [LOP-X001](../assessment-patterns.md#lop-x001), LOP-02, LOP-10 (private
rule-engine and comparator access).

**Footprint.**
- *Known:* `domain_operations.py` policy region (about `:2246-3170`), `schema/rules.py`,
  `schema/rulelang.py`.
- *Suspected:* authored domain rule text refers to legacy field names.

**Preservation constraints.**
- [ADR-0018](../../adr/0018-policy-routed-escalation.md) (rule-engine `Chain` policies; revisit if
  rule-engine cannot express a condition). Pin `rule-engine==5.1.0`.
- The archived rule artifact is part of release identity.
- The result binding `VERSION` refuses mismatch, so any change to the view shape needs a version
  bump.
- Undecided must not become a rule pass or a refutation.
- The vocabulary and literal checks in rulelang are domain policy.

**Counterevidence.**
- Projecting into the legacy views keeps existing authored rule text running unchanged. Rule-text
  compatibility may be the real contract.

**Research leads.** [rule-engine](../../libraries/rule-engine.md): `type_resolver_from_dict`,
dataclass resolvers, `DataType.from_type`, public AST traversal.
[pydantic](../../libraries/pydantic.md): release-generated models as the typed subject.

**Questions for library research.**
1. Can a rule-engine object schema be derived from release-generated types (optional, nested, map
   and list shapes) while keeping vocabulary admission?
2. Does rule-engine expose a public typed traversal or resolved attribute type that replaces
   `_object_type`?
3. What smallest stable "rule view" keeps archived rule text meaningful after legacy retirement?

**Library assessment (2026-10-29).** `ReleasedRulesPolicy` evaluates `when`/`check` `Rule` pairs, not a `Chain`. `type_resolver_from_dict` is already used. Deriving rule types from the release's Pydantic models is ruled out at rule-engine 5.1.0; a logical view (OBJECT plus accessor) fits with conditions, and its nullability is part of the archived contract ([applicability](../libraries/rule-engine/README.md#applicability-cbo-005)).

<a id="cbo-006"></a>

## CBO-006 — Scientific comparison and alignment kernels take the retiring value and batch model

**Label:** current for domain decisions; accepted planned (SP-08) for evaluation migration.
**Altitude:** boundary of a domain algorithm.

**Operation and consumer.** Value equivalence, condition comparison and set alignment serve domain
decisions today and evaluation scoring in SP-08.

**Current mechanism.**
- `ValueComparator` and `align` import `core.values`, `core.batch`, `core.keys` and
  `schema.lookup` (`evaluate/equivalence.py:43-48`, `evaluate/align.py:46-59`).
- The semantic decision path translates release records into those legacy types before comparing.
  It also reaches the comparator's private `_constraints` (see [CBO-005](#cbo-005)).
- Evaluation readers query legacy tables with text SQL (16 `text(` sites in `evaluate/sets.py`).

**Why it matters.** SP-08 must migrate align, equivalence and the readers. A second consumer would
otherwise write a second translator into a model that SP-09 retires.

**Patterns.** [LOP-X001](../assessment-patterns.md#lop-x001), LOP-06, LOP-09.

**Preservation constraints.**
- Tier semantics, with undecided distinct from unequal.
- Seeded numeric sampling.
- The SymPy 1.14.0 hold (`docs/pins.md`) and [ADR-0012](../../adr/0012-math-grammar-token-keys.md).
- Ontology mappings, corpus identity, string equality and symbolic/numeric equivalence stay
  distinct operations.
- Gold references stay out of extraction and consolidation inputs.

**Counterevidence.** The kernels are sound library users. Only their operand model is the issue.

**Research leads.** [pydantic](../../libraries/pydantic.md): one adapter from release-validated
values. [PostgreSQL system tooling](../../libraries/PostgreSQL_System_Tooling_for_Ubuntu.md):
role/schema separation, if goldens become a separate realization whose isolation is enforced by
privileges.

**Questions for library research.**
1. Should the comparator own one adapter from release-validated values, used by every consumer?
2. Can gold isolation be enforced by database privileges rather than by convention?

**Library assessment (2026-10-29).** `model_copy(update=…)` in the comparison path writes without validation. Gold isolation by privileges is being implemented concurrently (`4de601c`) ([applicability](../libraries/postgresql/README.md#applicability-cbo-006)).

<a id="cbo-007"></a>

## CBO-007 — Exports and analytical capture cannot be composed from the application store

**Label:** accepted planned (SP-08 exports and evaluation readers). **Altitude:** workflow.

**Operation and consumer.** SP-08 exports "consume SP-05 projections" and must identify their
semantic and data context. Evaluation readers may consume the same captures.

**Current mechanism.**
- `capture_packet` and `load_packet` (`semantic/analytics.py:407`, `:458`) have no production
  caller. Apart from tests, the only reference is the implementation registry entry
  (`semantic/contracts.py:94`).
- Capture needs a separate libpq URI and a driver path.
- The production engine from `open_store` has an empty URL
  (`core/db/store.py:98`, `create_engine("postgresql+psycopg://", creator=pool.getconn, …)`), so the
  test-side derivation of the URI from `engine.url` does not transfer.
- `AnalysisScope` resources (threads, memory, scratch) are passed by hand rather than taken from
  `AnalyticsSettings`.
- Capture always copies the whole 26-relation `SPINE` (`analytics.py:51`, `:274`). Nothing pushes a
  narrow export's selection or projection down.
- No export writer exists.

**Why it matters.** The first export consumer would otherwise assemble connection derivation,
driver selection, resource settings, scope and output format by itself.

**Patterns.** LOP-12, LOP-05, LOP-08.

**Preservation constraints.**
- [ADR-0026](../../adr/0026-columnar-semantic-operations.md): one DuckDB scope; ADBC imports the
  snapshot read-only; DataFusion rejected (revisit trigger: an inspected operation requires it).
- Exact lexical decimals.
- `cs.*` Arrow schema metadata.
- The duckdb 2.0.0 hold.

**Counterevidence.**
- A whole-spine packet may be deliberate, for replayability.
- Some exports may belong on the query path ([CBO-001](#cbo-001)) instead.

**Research leads.** [duckdb_2](../../libraries/duckdb_2.md): `COPY … TO` Parquet with key-value
metadata. [pyarrow](../../libraries/pyarrow.md): Parquet and dataset writers that keep schema
metadata. [adbc-driver-postgresql](../../libraries/adbc-driver-postgresql.md).

**Questions for library research.**
1. Does a DuckDB or pyarrow writer carry `cs.*` identity metadata end to end?
2. Can `compile_projection` take a declared relation or property subset without breaking replay
   identity?
3. Who owns ADBC connection construction from `Settings` and the restricted principals?

**Library assessment (2026-10-29).** Premise corrected. Settings already held the libpq URL and driver path, and since `3d97504` `connection_settings(settings, "read")` derives the reader URL. Concurrent SP-08 commit `7cfd7f8` added `ci export` using that route plus pyarrow `write_table(store_schema=True)`. DuckDB drops Arrow metadata, so a DuckDB export must restate identity as `KV_METADATA` ([duckdb](../libraries/duckdb/README.md#applicability-cbo-007), [pyarrow](../libraries/pyarrow/README.md#applicability-cbo-007), [adbc](../libraries/adbc-driver-postgresql/README.md#applicability-cbo-007)).

<a id="cbo-012"></a>

## CBO-012 — Refusal mapping and MCP conventions are re-decided per surface

**Label:** current (semantic MCP); SP-08 extension accepted planned. **Altitude:** interface.

**Operation and consumer.** CLI commands and MCP tools translate semantic refusals into user-facing
outcomes. Refusals include `OperationConflict`, `DomainOperationRefused`, `WrongRelease`,
`StaleSnapshot` and `ProposalRefused`; outcomes are exit codes, JSON error shapes and MCP errors.

**Current mechanism.**
- The semantic MCP server repeats `try/except → ToolError` inside its tools
  (`intervene/semantic_server.py`, seven handlers). It does not translate database errors and has no
  response-size backstop.
- The legacy server has both: `DBAPIError → ToolError` and
  `ResponseLimitingMiddleware(max_size=BACKSTOP_BYTES)` (`intervene/server.py:40-52`, `:89`).
- `propose_claims` advertises an untyped dict input. The release schema arrives through instruction
  pages and a schema hash instead.
- CLI refusal mapping is rewritten in several modules (`cli/orchestrate.py`, `cli/query.py`,
  `cli/mcp.py`, `cli/db.py`).
- The harness `intervene/testing.py` reads the legacy part shape, so it cannot drive the semantic
  server.

**Why it matters.** SP-08 adds query, explain and intervention tools, and stale-submission handling.
Mapping refusals consistently is one decision that is currently made in many places.

**Patterns.** LOP-09, LOP-03 (middleware available but unused), LOP-12.

**Preservation constraints.**
- Packet-hash pinning and lease renewal.
- The one-correction retry semantics, where schema or packet errors do not consume the retry.

**Counterevidence.** A per-release tool input schema would need tools registered per run, and
listings the agent reads would grow. Serving the schema through pages may be deliberate.

**Research leads.** [fastmcp](../../libraries/fastmcp.md): error-translation and response-limiting
middleware; providers and tool transforms for schemas bound to a release.
[typer](../../libraries/typer.md): mapping exceptions to exit codes.

**Questions for library research.**
1. Can FastMCP middleware own error translation and size bounds for both servers?
2. Is a per-run input schema worth its cost compared with the pages-plus-hash protocol?

**Library assessment (2026-10-29).** Premise partly stale at `3d97504`: `intervene/server.py` now delegates to the semantic server, the legacy response backstop and `DBAPIError` mapping no longer exist, and a new `record_direction` tool has no refusal mapping. The built-in `ErrorHandlingMiddleware` would turn every tool error into a protocol error; a custom middleware or decorator fits ([fastmcp](../libraries/fastmcp/README.md#applicability-cbo-012)).

<a id="cbo-016"></a>

## CBO-016 — Release-typed instance traversal is reimplemented per consumer

**Label:** current; SP-08 consumers inherit it. **Altitude:** module, repeated.

**Operation and consumer.** Consumers walk instance values under release descriptors to collect
references, rewrite identities, lower values to typed rows or produce plain data. The consumers are
cut materialization, consolidation and lowering.

**Current mechanism.**
- `_plain` and `_native` (`domain_operations.py:271`, `:283`) and `consolidation.plain` re-derive
  roughly `model_dump(exclude_unset=True)`.
- Three descriptor-driven walkers: `_reference`, `_entity_references` and `_claim_references`
  (`:298`, `:343`, `:371`).
- `FactValueLowerer.lower` in `consolidation.py`.
- `_known_input` defines a key-name heuristic walker (`refs()` over `target`/`entity`/`subject`,
  `:456-465`). Its `references` and `classes` results are never read in the rest of the function
  (searched to `:640`). That contradicts the descriptor-only rule that plain strings never become
  references.

**Why it matters.** Each new consumer adds another walk with slightly different policy. This is
where reference semantics can drift.

**Patterns.** [LOP-X004](../assessment-patterns.md#lop-x004), LOP-03, LOP-09.

**Preservation constraints.**
- Inlined versus referenced, and fact-role references.
- Refusal on keyed-member collision.
- Tuple versus list shape. Whether canonical bytes distinguish them was not verified.

**Counterevidence.** The walkers carry domain policy. A library can discharge the traversal, not
the policy.

**Research leads.** [pydantic](../../libraries/pydantic.md): `model_dump` and core-schema
traversal. A descriptor visitor exposed by the prepared release
([CBO-013](release-preparation.md#cbo-013)).

**Question for library research.** Can one descriptor-directed visitor (collect, rewrite, lower)
serve all consumers?

**Library assessment (2026-10-29).** `model_dump(exclude_unset=True)` equals `_native` exactly on compiler output (probe); the walkers' policy stays owned. `conditional_rules.validate_rules` is a further shallow projection site ([pydantic](../libraries/pydantic/README.md#applicability-cbo-016)).

<a id="cbo-020"></a>

## CBO-020 — Each cut loads and decodes the whole input realization, then narrows in Python

**Label:** current. **Altitude:** operation. The execution-fit point is qualitative, not measured.

**Operation and consumer.** Cut materialization reads known inputs (prior entities and facts) from
an input realization.

**Current mechanism.** `_known_input` (`domain_operations.py:446-600`) does three things:
- loads every membership of the input realization;
- loads every selected fact for those entities;
- decodes every value through the private `session._values`.

Only the references reachable from entities actually used are carried forward later. The narrowing
set computed at the start is unused ([CBO-016](#cbo-016)).

**Why it matters.** The work scales with the size of the known-input realization, not with the
cut's reference set. That matters for SP-09 regeneration runs that reuse prior known inputs.

**Patterns.** LOP-05, LOP-04.

**Counterevidence.**
- Label-based identity resolution needs every known global-label entity, so labels and keys must
  stay global. Only the full fact and value decoding is questionable.
- Known-input realizations may be small reference catalogs.

**Research leads.** A PostgreSQL recursive CTE over value roles, the pattern `query.py` already
uses. [sqlalchemy](../../libraries/sqlalchemy.md).

**Question for library research.** Which attributes does identity resolution need globally, and can
the rest be fetched by reachability inside the database?

**Library assessment (2026-10-29).** Premise corrected. Identity resolution needs memberships plus decoded identity-group and display-label values for every known entity. The reachable set is seeded from Python resolution output, so a database closure is a second phase. The known-entity `.in_(ids)` sets would hit the 65,535-parameter ceiling regardless ([sqlalchemy](../libraries/sqlalchemy/README.md#applicability-cbo-020)).

<a id="cbo-023"></a>

## CBO-023 — The math deadline confines comparison and domain decisions to the main thread

**Label:** current constraint; possible SP-08 risk. **Altitude:** function with system reach.

**Operation and consumer.** Grammar reads are bounded by a deadline. Consumers are evaluation
comparison and released-rule evaluation.

**Current mechanism.**
- One `SIGALRM` timer bounds each read (`methods/math/grammar.py:37`, `:405-412`).
- Consumers call `grammar.require_main_thread()` (for example `evaluate/equivalence.py:129`).

**Why it matters.** Any SP-08 path that runs comparison or finalize off the main thread raises
`OffMainThread`. Examples are an MCP worker thread or a threaded reader.

**Patterns.** LOP-08.

**Uncertainty.** Whether any SP-08 path will actually run off the main thread. How FastMCP 4.1.3
executes synchronous tools was not examined.

**Preservation constraints.** [ADR-0012](../../adr/0012-math-grammar-token-keys.md) governs the
grammar. Bounded parse time is a real protection.

**Research leads.** A process-based deadline (`concurrent.futures` process pool);
[fastmcp](../../libraries/fastmcp.md) execution model.

**Question for library research.** How does FastMCP execute synchronous tools, and which SP-08
paths would run the grammar off the main thread?

**Library assessment (2026-10-29).** Settled by probe: default synchronous FastMCP tools run on a worker thread (`OffMainThread`), while `async def` or `run_in_thread=False` tools run on the main thread under `ci mcp serve` ([fastmcp](../libraries/fastmcp/README.md#applicability-cbo-023)).
