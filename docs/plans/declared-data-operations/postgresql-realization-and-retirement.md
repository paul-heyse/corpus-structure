# PostgreSQL realization and retirement

**Accepted scope; integrated implementation in progress · 2026-11-14.** Consumes all actionable portions
of [PostgreSQL domain alignment I01–I08](../../plan_improvement_reviews/declared-data-operations-postgresql-domain-alignment_2026-11-14.md)
at `a1b9cc73a`, selected by the operator with conditions preserved. The
[coordinator amendment](../declared-data-operations_2026-11-12.md#postgresql-domain-alignment-amendment--accepted-2026-11-14)
owns scope, question/recommendation disposition and completion. This companion owns shared technical
realization and planned migration boundaries, not another progress ledger or DDO stage.

## Baseline, authority and integration boundary

**Source-inspected, 2026-11-14 at `a1b9cc73a`.** Product source is unchanged from the review's
`75afc15e5` baseline. Existing SQLAlchemy/Alembic alignment, fate derivation, Core binding/read
products, privilege operations, frozen data steps and typed-column unsupported-type refusal are
implemented foundations with the coordinator's bounded evidence. They are not new missing work.
The additional typed native consumer interfaces and wider read/reuse/retirement integration below
remain planned. Existing failures, scoped completion and historical evidence limits remain intact.

Use core 3.3, efficient-architecture heuristics, code-intelligence 1.4 and test-assessment 1.2.
FP-04/DP-01/02 require governing meanings and qualified distinctions at actual consumers;
FP-01/03/06 support one owner and local composition; FP-07/H5/H8/H18/H21/H27 favor scoped sets,
useful preparation and removal of duplicate runtime machinery. None requires a new registry,
benchmark, cost model or alignment lint.

Semantic definitions stay with [contracts and compilation](contracts-and-compilation.md), instance
admission/publication with [products and support](products-and-support.md), execution with
[demand planning](demand-planning-and-execution.md), selection/currentness with
[reuse and consolidation](change-reuse-and-consolidation.md), public contracts with
[interfaces and evaluation](interfaces-and-evaluation.md), and historical custody with
[preservation/adoption](preservation-adoption-and-qualification.md). The designs here realize those
contracts. One semantic operation need not create another task, transaction or stored intermediate.

Retain PostgreSQL transactional authority, purpose-restricted native effects, exact semantic identity
and authentic producing episodes. Raw SQL, JSON and physical task fences are not removal targets
by category. DDO-11's final physical retirement follows actual preserved closure; current caller
migration and safe dead-code removal need not wait for deployment.

<a id="typed-native"></a>
## Typed native realization — I01

DDO-03 extends `semantic/data_operation_wire.py` and the shared
`semantic/operation_call_generation.py:render_call_bindings` using captured closed protocol bytes.
Currently `native_operation_calls` maps every request/result to `json_payload`; embedded schema bytes
protect runtime admission but do not give planner/executor consumers a useful static record shape.
Do not introduce a parallel handwritten DTO or signature catalog.

The selected realization generates operation-specific structural TypedDict views through captured
schema/correspondence generation and the named typed call surface (ADR-0106). Draft7 and the exact
codec remain the runtime boundary; no second runtime object/decoder layer is introduced.
Return values are detached mutable snapshots. See the coordinator for implementation and evidence.
The planned record-emitter alternative is superseded by this consumed structural representation. Preserve fixed symbol selection; the validated generic
`DataOperationStorage.invoke` remains private transport. Model-owned explicit field correspondence
supplies nominal product, member, demand, request, attempt, receipt and contextual identities;
shared `identifier: string` or field spelling cannot infer them. Contracts owns that correspondence;
DDO-02 consumes it under existing identity rules without changing identity merely for ergonomics.

Generate nested records, literal/discriminated variants, collection/map element types and named
recursive exact semantic values. Required, absent and present-null fields remain distinct. Omitted
fields serialize by omission, never by injecting schema defaults or converting absence to null.
Use owned immutable collections or detached mutable transport copies; a frozen outer record does
not establish deep immutability. Keep genuinely varying semantic bodies governed by their kind and
exact value codec instead of widening every enclosing record to `Any`.

Runtime Draft7 remains authoritative for `if/then/else`, `allOf`, cross-field dependencies and union
constraints not expressible statically. Do not flatten alternatives with `json_schema_properties`
and then treat the flattened object as the union decoder. Validate wire ingress with its captured
schema before structuring; serialize through the exact Decimal/context codec. Unsupported new
generation has a located refusal, but rejecting today's valid protocol is not completion.

**Preparation PG-Q1:** before generator implementation, inventory protocol constructs and nominal
field bindings, then specify the supported structural representation and omission/union decoder
contract using actual representative operations. Compare extending current record emission with a
schema-owned structural annotation where it avoids redundant wrappers; select one consumed route.
Include `data_operation_artifacts._validate_native_correspondence`, which currently rejects nested
`call.records`, and its finite native primitive/kind lowering in the design. Emitter changes alone
cannot pass current correspondence validation. Preserve `compile_data_operation_artifacts`' captured
generator sources and artifact/digest route, without another editable checkout DTO catalogue.
The output is an implementable correspondence/decoder design covering the current operation set,
not a general JSON Schema compiler. Archive preparation owns captured generated products; checkout
artifacts use their existing generator. No per-request source/schema generation or provider import.

Migrate `DemandPlanner`, executor claim/publication/recovery, `data_operation_service`, admission,
external receipts, interpretation authoring and new public readers in coherent slices. Remove
manual request/result field reconstruction in migrated paths. A generated type grants neither
native permission nor publication custody. Retained archives decode from their original schema,
not current installed definitions; no wire change is required solely for better Python types.

<a id="reads"></a>
## Selected reads and selective native access — I02/I04

DDO-04 supplies acquisition and protected projection primitives; DDO-09 owns currentness/cut meaning;
DDO-10 owns the full public journey. Produce Core selects over shared fixed metadata and derive
eligible row/native return shapes from the same definition. Reuse current projection fragments for
visibility, product/member and finite support traversal; no second query DSL or latest classifier.
Scope, continuation and limits enter the protected function, since outer predicates cannot be
assumed to push through SECURITY DEFINER PL/pgSQL.

Read acquisition has effects: authorization, sorted trust locks, pinned selection/boundary and a
`data_demand_read` row. Keep it native. Projection under those pins may share its transaction and
atomic JSON page; separating responsibilities does not require an extra round trip. Cursors and
resources bind demand/selection, interpreted contracts, project/source and trust assessment for
all pages. Historical selected trust and a current trust assessment are distinct named facts.
Unknown/incomplete, absent under a closed witness, empty completed and failed remain distinguishable.

`ddo_require_binding` already restricts `data_binding_rows` by subject, original source and analyzed
scope, but aggregates all returned rows/bodies before selected validation. **PG-Q2:** classify actual
binding predicates by necessary scope: selected member bodies versus complete role/population facts.
Separate those acquisitions using keyed joins, EXISTS/lateral set composition and compact witness
rows where semantics allow. All-members/negative/coverage predicates keep their full required
population; membership does not automatically prove the required values. The outcome chooses a
selective route or explains why the current scoped aggregate is necessary for a named case. No
whole-demand scan allegation, selected-only shortcut or benchmark prerequisite follows.

Candidate filtering and protected selected-binding verification stay independently implemented.
Raising native comparison helpers cannot replace filtering nonmatches/unknowns. Preserve provider
identity, same-role/full-context association, complete transitive support and trust lock ordering.
Changed native bodies need a frozen forward successor through the existing authoring owner.

Public migration must cover reader/query and source-only/partial/full results, definition/assertion
and all three contextual recipes, actual MCP tools/resources, CLI records/export, review bundles,
verification and detached replay. Preserve necessary intermediate nodes even for filtered output.
Reference authoring/grading keeps purpose roles and separate source/prediction releases; generic
DDO read access never exposes protected answers. Consolidation retains exact consumed cut bindings
and policies plus authentic producing episodes; it does not infer currentness from a run ID.

<a id="lifecycle"></a>
## Database lifecycle and failure meaning — I05

Retain `ConnectionPool(close_returns=True)` with SQLAlchemy `NullPool` borrowing through
`creator=pool.getconn`. This avoids two physical inventories. Purpose-specific roles,
maintenance/admission sessions and dedicated advisory-lock lifetimes remain distinct contracts.
Psycopg pool return already sanitizes transaction state; add a reset hook only for concrete
surviving session state beyond SET LOCAL/transaction-scoped staging.

**PG-Q3:** `NativeDemandExecutor.run` delegates to `maintained_claims`, which currently retains one
borrowed connection across active-claim renewal transactions; settlement shares `owner.lock`.
Inspect that existing residency first, alongside admission/port borrowers, rather than adding
another reservation without a consumer. Reconcile D3's one-foreground-operation wording too.
Inspect the actual phase/borrower paths, active-group limits, renewal and port work to
choose the minimum sufficient capacity owner. Four worker threads are not proof of four active
claims; current default claim/byte capacity is two. Inference and capacity-waiting ports retain no foreground DB checkout; independently owned
renewal residency follows PG-Q3. An adequate `max_size` does not guarantee renewal availability during elastic growth,
reconnect or health checks. If the existing no-wait-behind-port requirement requires reserved
capacity, compare one invocation-owned renewal borrower with a separately bounded renewal pool;
record aggregate ownership, timeout/reconnect and cleanup, not a new scheduler or estimator.

Fix notice callback accumulation at `core/db/store.py`'s physical connection integration. Installed
SQLAlchemy dialect setup adds a notice handler each time its NullPool creates a connection record,
while the external pool may return the same physical session. Ensure physical initialization once
per physical session, preserve ordinary dialect setup and checkout checks, and verify reconnect
receives new initialization. Choose the supported event/pool hook after inspecting its lifetime;
do not silently disable all dialect initialization or duplicate the pool's sanitation.

Keep physical SQLSTATE/pool/ADBC facts in `classify_error`, invariant meaning in declared
`NativeDiagnosticBinding`, and retry/reconciliation with the operation. Known admission refusal
and SERIALIZABLE retry branches can remain contextual. Replace English-message-dependent renewal
classification with a policy over trustworthy physical/effect facts. Plan the bounded retry of
rollback-confirmed query cancellation/lock unavailability under existing lease-coverage checks;
retain its actual cause, and do not claim `57014` proves deadline expiry or `55P03` universally
proves lock timeout. Client-requested cancellation, invalidation, insufficient lease and unknown
effects do not enter this rollback-confirmed retry. Non-idempotent publication keeps exact intent
inspection/reconciliation rather than automatic retry.

The review introduced no new automatic rule change. PG-Q3 must reconcile D3/D9's older one-pool
wording with actual purpose/renewal ownership. If a selected design changes an architectural rule,
record its concrete impact for operator decision and route an ADR/owner update before dependent
implementation; this planning amendment does not pre-approve an unspecified pool topology.

<a id="transfers"></a>
## Typed transfers and conditional capabilities — I07/I08

Retain exact DDO JSON member bodies: they participate in product identity and durable replayable
completion intent. PDF staging and release archives retain typed COPY on the caller-owned
transaction. `pgpq.ArrowToPostgresBinaryEncoder` is encoding, not schema authority; retain explicit
columns, full schema checks, exact precision refusals, fresh stream encoder and no footer on error.
A batch flush threshold is not a hard native memory bound; actual producer batch admission remains
with the transfer owner. Ordinary row COPY can remain for a real row producer.

Psycopg supports the existing same-session transaction/COPY ownership; ADBC owns another session
and cannot replace that staging transaction. Exact `ContextJSONB` and ordinary pool JSON retain
their explicit scopes, including Decimal and SQL NULL versus JSON null distinctions. Typed result
rows should follow SQLAlchemy's cursor ownership rather than layering another row factory over it.

Record the implemented vector contract alongside operation migration: vector product members bind
as typed `VECTOR(d)` in a transient selected relation for exact cosine/lexical ranking. Preserve
finite values, dimension, numerical policy and exact candidate inventory. Retire legacy task-keyed
vector columns/JSON casts with their actual I03 readers/writers; no second persistent vector
representation or approximate search follows from this amendment.

**Conditional Arrow reads:** trigger only for a real DDO-10 tabular consumer whose transfer needs
justify Arrow. Until then use bounded existing native/Psycopg reads. If triggered, **PG-Q5** compares
same-session streaming plus Arrow conversion; committed acquisition plus a fresh authenticated
snapshot/lock revalidation; or a protected projection over authenticated immutable pins. ADBC
snapshot import cannot see the exporter's newly inserted uncommitted `data_demand_read` row, and
owner-XID facts visible to the acquiring transaction must not disappear. Commit-before-export is
not automatically equivalent. Preserve boundary/frontier, source/trust, continuations, concurrent
publication/revocation and cancellation lifetime before selecting that alternative. No separate
Arrow authority, effectful COPY shortcut or unconditional backend implementation is scheduled.

**Required bounded native cleanup:** use pglast's prepared private tree and selected
`CreateFunctionStmt.funcname` transformations for declaration renames instead of literal SQL
replacement; preserve body bytes/dollar quoting. Consolidate identical descriptor-literal
extraction and trigger interpretation in their native owner. Keep Core placeholder composition
and specialized PL/pgSQL effects. Refuse unsupported deparse cases explicitly or preserve their untouched text rather than
inventing a procedural compiler. Prior PostgreSQL review I05 remains the source of this I08 cleanup.

**Conditional SQL cross-check:** trigger only when an actual DDO-09/10 declared-input consumer
needs a compiled-SQL consistency diagnostic. SQLGlot checked-recipe qualification/type/lineage
remains supporting analysis, not PostgreSQL authorization or complete support provenance. Unresolved
syntax is unknown. A table name scan or AST similarity cannot establish semantic dependencies,
currentness, privileges or compatibility.

<a id="retirement"></a>
## Consumer replacement and retirement boundaries — I03/I06

The following is the planned consumer coverage, not evidence all dynamic callers are enumerated.
Reacquire imports, entrypoints, registrations, configuration and retained artifacts before each
replacement. Current callers must migrate; they do not justify indefinite compatibility dispatch.
Preserve independent expectations when removing mechanism tests. Partial transfer does not close
the enclosing coordinator finding.

| Current responsibility / entrypoints | Target and whole removal boundary | Package / preservation prerequisite |
|---|---|---|
| `operations.create_task`, task_dependency_scope, reused_task_id and execution guards | Declared semantic request/value/support reuse and reverse lineage; remove twin lookup, copied reuse, broad runtime/freshness salts and their current readers | DDO-09 with 06–08/10; keep original producing episode and independent nonreuse controls |
| Run preparation/finalization and consolidation | Native demand settlement plus exact cut bindings/currentness; remove current run-group semantic scheduler and competing stale-cut classifier | DDO-06/09; preserve accepted per-run published knowledge and genuine algorithms |
| `complete_task` envelopes and family publishers | Declared publication/receipts, exact source/support and uncertain replay; retire obsolete payload builders, native APIs/grants and configurations with each migrated family | DDO-07/08; physical task/attempt/holder fences remain real custody |
| `orchestrate.commands`, liveness, source_progress; status/result/task-list CLI | Native demand reporting/cancellation/resume; sealed historical inspection where still required; remove session/run supervision only when no current obligation remains | DDO-06/10; retain authentic physical status and advisory ownership still consumed |
| Visual/external request and result paths | Declared external/effect operations and receipt reconciliation; remove bypass writers and old request routing | DDO-08/10; no packet delivery relabelled fulfillment |
| Legacy vector write/search and JSON cast readers | Selected typed vector-member retrieval; remove task-vector native/storage branches and current cached-vector codecs | DDO-08/10/11; preserve historical selected evidence and numerical contracts |
| `serve/journey`, contribution_queries, characterization/contextual and definition/assertion consumers | Pinned shared selected read owner across every recipe; remove current run/task-origin and latest/default joins | DDO-09/10; keep examined evidence closure and partial/zero-output standing |
| CLI records/export, MCP resources/cursors, selected_source and review bundles | Same pinned production owner and exact exported source/support/contract closure | DDO-10; cursor interpretation survives new release/defaults |
| Characterization/model observation replay and detached verification | Target semantic references, exact runtime/source pins; remove current dual-address/fabricated-task fallbacks | DDO-10/11; preserve required sealed original interpretation |
| `runtime_binding_store` missing-runtime run fallback and archive dispatch | Explicit pinned current exports; retain only identified sealed interpretation and recovery | DDO-10/11; classify genuine runtime-less historical data before destructive removal |
| Evaluation, golden/reference authoring, legacy pair/singleton/frame adapters and original-grade comparison | Explicit source/prediction applicability and reviewed address correspondence; remove superseded current adapters | DDO-10/11; protected answers and genuine original-grade comparison remain unchanged |
| Legacy `_Compiler`, `compile_metadata(target='legacy')`, `compile_interchange`, `installed()` | Retain semantic/read physical compiler; extract live `_sql_arrow` and used record helpers, then remove obsolete projection/default/installed routes | DDO-01/10; current native_source Arrow consumer, generators and schema tests migrated |
| HalfVec/type maps and model compiler revision markers | Remove only retired current mappings/identity contributions; keep used Vector and semantic generated DTO/vocabulary | DDO-01/10; inspect frozen migration imports and actual format readers |
| Earlier `alembic/versions` versus active `semantic_alembic` | No new legacy upgrade adapter; choose retained archival/import support or removal of unsupported executable route | DDO-11 after PG-Q4; never rewrite frozen active history or assume file retention preserves instances |

**PG-Q4:** resolve bounded residual consumer/custody questions before compiler/import/old-frame
retirement: live payload encoders, `_sql_arrow` type coverage, compiler markers, HalfVec imports,
old Alembic restore paths and reference-frame applicability. Use existing census classifications,
source and named reader/recovery consumers; no speculative live scan or protected-answer read.
Missing actual custody keeps only the affected destructive step open. Do not delete mixed-use
modules wholesale or retain a whole old platform solely for a synthetic test.

<a id="work-and-evidence"></a>
## Work slices, prerequisites and evidence

| Slice in existing package | Consumes / produces / integration boundary |
|---|---|
| DDO-01/02/03 typed preparation | PG-Q1 and captured schemas/correspondence → useful generated records/calls and archive products; actual planner/service consumer included |
| DDO-04/05 protected selection | Existing Core/native foundations + PG-Q2 → scoped projection/verification; retains independent binding and trust/provider controls |
| DDO-06 lifecycle | PG-Q3 + typed claim/recovery results → actual bounded borrowers, notice initialization and honest contextual retry; no inference-held connections |
| DDO-07/08 family replacement | Available typed native/read primitives → producers plus immediate consumers and superseded effect/vector/publisher removal |
| DDO-09/10 shared cut/read contract | Define selected contract early alongside DDO-04; integrate full reuse/currentness/consolidation and public/reference journeys as prerequisites become usable |
| DDO-01/10 compiler reduction | PG-Q4 finite consumer findings + extracted live helpers → one current physical/interchange route; independent of unrelated provider completion |
| DDO-04 native cleanup | Next actual affected authoring change → pglast edits/shared descriptor decoder under one successor chain owner |
| DDO-11/12 adoption and qualification | Actual current consumer replacement + preserved closure → coordinated physical retirement and complete applicable final-source union |

Questions' current disposition is solely in the coordinator. These slices are not new stages,
mandatory agent assignments or whole-document synchronization barriers. Shared generators, native
SQL and migration chain need a named integration writer. New scoped extensions do not erase prior
foundation evidence or certify larger package completion.

Future focused acceptance must independently distinguish protocol union/field changes and nominal
IDs at real callers; absent/null/exact Decimal and recursive values; wrong same-context role and
closed/partial/empty populations; actual borrower saturation and reconnect/notice behavior;
rollback-confirmed cancellation versus unknown commit; support revocation and exact receipt replay;
all public pagination/export/replay memberships and protected references; and compiler/helper
retirement while a genuine historical reader still works. Source/body-only generator agreement is
not a native or semantic oracle. No benchmark is required for expected qualitative reductions.

Implementation checks remain targeted; full `uv run ci test`/`uv run ci check` and native/provider
union belong to DDO-12 after complete scope and final maintenance. **not_run for this amendment:**
product/native/provider checks, DB operations, authoring/deployment/activation, benchmarks and health
campaigns. Existing cancellation remains in force; future acceptance descriptions do not restart it.

## Library mechanisms and explicit non-adoptions

Pinned versions remain SQLAlchemy 2.1.6, Alembic 1.20.1, Psycopg 3.3.6, psycopg-pool 3.3.3,
pglast 8.7, SQLGlot 30.27.0, pgpq 0.12.0 and ADBC PostgreSQL 1.13.0. The
[review capability account](../../plan_improvement_reviews/declared-data-operations-postgresql-domain-alignment_2026-11-14.md#library-capability-coverage-and-selection)
retains the complete family dispositions, addendum corrections and version limits.

- [SQLAlchemy Core/types and execution](../../libraries/postgresql/sqlalchemy.md) supplies
  select/CTE/lateral/EXISTS and typed native row derivation; `TypedColumns`/`Named` are static
  correspondence, not runtime admission. The [2.1.6 selectables reference](https://github.com/sqlalchemy/sqlalchemy/blob/rel_2_1_6/doc/build/core/selectable.rst)
  supports the set route. Do not introduce an ORM identity map/session lifecycle for immutable
  products, a generic query DSL, or native ENUM solely to duplicate protocol value sets.
- [Alembic structured operations](../../libraries/postgresql/alembic.md) supplies existing
  `produce_migrations`, registered operations/comparators/renderers and caller-connection upgrade.
  Keep implemented frozen privilege/data-step custody, global ordering and predecessor checks;
  branches, Rewriter replacement, offline deploy and another migration framework have no selected need.
- [Psycopg](../../libraries/postgresql/psycopg.md) and
  [pool ownership/lifecycle](../../libraries/postgresql/psycopg-pool.md) supply driver COPY,
  adaptation, bounded acquisition and sanitation. No bespoke pool/queue, blanket reset or global
  JSON change. Async, pipelines, notifications, prepared-statement tuning and new credentials
  machinery require actual consumers, not catalogue presence.
- [pgpq](../../libraries/postgresql/pgpq.md) supplies binary encoding only. Keep schema/lifetime
  guards; no encoder-derived DDL authority or revived staged-member route.
- [ADBC](../../libraries/postgresql/adbc-driver-postgresql.md) supplies current columnar reads
  with owned child/reader cancellation and snapshot lifetime. The
  [PostgreSQL18 snapshot contract](https://www.postgresql.org/docs/18/functions-admin.html#FUNCTIONS-SNAPSHOT-SYNCHRONIZATION)
  forbids assuming uncommitted acquisition visibility. No ADBC ingest substitution, DuckDB extension
  or generic ADBC pool is selected by this amendment.
- [pglast AST/printer boundaries](../../libraries/postgresql/pglast.md) supports selected
  declaration edits; its normalized fingerprint is not custody identity. Preserve known deparse
  hazards with qualified cases, not a new parser/procedural compiler.
- [SQLGlot qualification/lineage](../../libraries/postgresql/sqlglot.md) supports checked recipe
  analysis with attributed value/membership/ordering/unknown facts. Keep compiled-SQL cross-checks
  conditional; no transpiler/optimizer/DDL privilege authority or AST-based compatibility claim.

D3/D9 pool/version/transfer wording must be corrected with the owning selected implementation/decision,
including the implemented transient vector contract. Distinguish stale descriptions from supported
historical behavior. Parser/deparser hazards from prior PostgreSQL defect 5 remain limits for actual
constructs; an affected case can justify a deliberate upstream correction under dependency policy,
but no wholesale upgrade or parser audit is scheduled.
