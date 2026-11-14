# PostgreSQL domain alignment across declared data operations

**Proposed recommendations · 2026-11-14.** This independent plan-improvement review examines the
whole Python PostgreSQL layer against the [DDO coordinator](../plans/declared-data-operations_2026-11-12.md)
and its ten supporting plans. Inspected source baseline: `75afc15e5f78e9604f4d9aea61f1d4a317b0101f`,
initially clean. Review publication changes only documentation. The current coordinator and STATUS,
not older review summaries or intermediate receipts, own implementation and qualification state.
DDO-03–05 have bounded foundation evidence; DDO-06–12 remain open. The stopped increment's three
unresolved journeys remain unresolved. No database, native candidate, provider, or product test was run.

The inquiry uses core 3.3, efficient-architecture heuristics, code-intelligence 1.4, test-assessment
1.2 and the repository binding. It initiates neither a diagnostic audit nor a completion audit.
Source observations below are **Interface-checked, 2026-11-14**; recommendations and benefits are
**Proposed**, unmeasured. Existing F01–F14/C1–C7, DDO-CA identities, and source-qualified review
recommendations keep their existing disposition owners. Publishing this review does not adopt its
recommendations or change accepted scope or progress.

**Planning adoption · 2026-11-14:** the operator subsequently selected all actionable I01–I08
portions, preserving conditional triggers, in the
[DDO coordinator amendment](../plans/declared-data-operations_2026-11-12.md#postgresql-domain-alignment-amendment--accepted-2026-11-14).
That coordinator now owns scheduled disposition and investigation readiness; the
[PostgreSQL companion](../plans/declared-data-operations/postgresql-realization-and-retirement.md)
retains the implementation design and deletion boundaries. This source review retains its dated
assessment and evidence limits. Selection and plan publication establish no implementation or
new qualification.

Code references below are relative to `python/corpus-structure/src/corpus_structure/`, unless
otherwise specified. Symbol names and line locations refer to the inspected baseline.

## Combined judgment

The principal remaining opportunity is **complete replacement of application-level PostgreSQL
semantics and their consumers**, rather than broader deployment of database libraries. The system
already uses Core metadata, generated native calls, protected native operations, Alembic plugins,
Psycopg pooling, typed COPY and snapshot-bound Arrow reads. Those foundations should carry more of
the replacement. Their presence does not establish that callers use one typed governing model.

Three coherent changes deserve priority: carry the closed native protocol through useful typed
Python call/result surfaces; finish the semantic selection/read/reuse replacement through its public
and protected consumers; remove obsolete compiler and run-based pathways with their actual consumers.
Connection/failure ownership and selective native binding access are complementary infrastructure
corrections. They should accompany the affected vertical replacements rather than become a second
platform project.

This is broader than the earlier [PostgreSQL client-library review](declared-data-operations-postgresql-libraries_2026-11-14.md),
whose limits explicitly included spot-checked legacy maps and partial companion reading. It also
builds on the [SQLAlchemy/Alembic review](declared-data-operations-sqlalchemy-alembic_2026-11-14.md)
without rescheduling its implemented foundation changes. Much of the desired end behavior is already
accepted in DDO. The improvement is to make its PostgreSQL replacement and deletion obligations
concrete enough that implementing the named packages cannot leave the old application model active.

A JSON wire envelope, a security-definer function or explicit SQL is not itself misalignment.
Semantic product membership, complete context, authentic production evidence, current permission and
support checks must survive every lowering. Physical tasks still supply real attempt/lease fences;
removing run-based semantic authority does not authorize deleting that physical custody.

## Target and responsibility coverage

The review considers all ten companions: contracts/compilation, implementation contracts/fingerprints,
products/support, demand execution, operation cutover, reuse/consolidation, interfaces/evaluation,
graph projections, source evolution and preservation/qualification. Their substantive targets supply
requirements beyond their package/status tables. Architectural owners are D1–D8, especially D3's
unified operation realization, D6's physical custody, and D8's pinned query/effect boundaries.

| Responsibility | Current realization and evidence entry | Disposition in this review |
|---|---|---|
| Effective semantics and native wire | `data_operation_wire.py`, `data_operation_storage.py:327–411`; captured closed Draft7 plus generic JSON invocation | Retain wire authority; derive useful typed consumers, I01 |
| Physical metadata and row shape | `metadata.py`, `data_operation_projections.py:269–326`, `typed_generation.py` | Retain implemented Core/shared row derivation; extend only to real consumers, I01/I02 |
| Binding, hydration and selected admission | `data_operation_storage.py:891`, `data_operation_consumers.py`, `sql/data_operation_bindings.sql` | Preserve independent candidate/native semantics; narrow acquisition where valid, I04 |
| Demand lifecycle, intent and publication | `data_operation_demands.py`, `orchestrate/data_operations.py`, `sql/data_operations.sql` | Retain fenced native protocol and recoverable intents; migrate callers, I01/I03 |
| Legacy run/task storage and reuse | `operations.py:322–346,1217,1809,2339`, `domain_operations.py` | Replace semantic grouping/reuse/read authority through I02/I03; retain authentic episodes and physical fences |
| Connections, transactions and errors | `core/db/store.py`, `runtime.py`, `query.py`, `claim_lifetime.py` | Retain purpose/snapshot ownership; consolidate scoped capacity/failure interpretation, I05 |
| Publication, Arrow and JSON | `publication.py`, `arrow_transfer.py`, `data_operation_json.py`, `core/db/adbc_lifetime.py` | Retain distinct justified transports; remove legacy producers with I03; conditional Arrow read extension, I07 |
| Serving, export and detached replay | `serve/`, `contribution_queries.py`, `intervene/semantic_server.py`, CLI export/records | Complete one selected read owner and pinned journey, I02 |
| Consolidation and evaluation | `domain_operations.py`, `evaluate/`, CLI golden/eval | Declare consumed cut bindings; preserve reference/prediction separation, I02/I03 |
| Schema compilation and interchange | `schema/relational.py:596`, `schema/interchange.py:236`, `serve/native_source.py:1028` | Retire legacy target after extracting live transfer helpers, I06 |
| Native SQL and schema evolution | `native_candidate.py`, `alembic_native.py`, `alembic_privileges.py`, `native_sql_body.py` | Retain implemented lifecycle/privilege/data-step ownership; focused structural cleanup, I08 |
| Migration history and operations | `semantic_alembic/`, separate `alembic/`, `cli/db.py` | Preserve frozen supported chains; retire unsupported live routes only on actual custody evidence, I06/I08 |
| Affected tests and operational tooling | semantic fixtures, compiler tests, source/export/reference tooling | Migrate scenario inputs with replacements; retain independent expectations; no general test-system redesign |

The map covers responsibility families, not an exhaustive proof that every dynamic or external caller
has been found. Consumer closure must include supported CLI/MCP entrypoints and configuration, not
only import counts. No live preservation census or protected answer inspection was needed or done.

<a id="I01"></a>
## I01 — Derive useful typed native call and result surfaces

**Alignment improvement; DDO-03/04, integrated with DDO-05/06/10. FP-02/04/05/06, DP-01/02/06/08/24.**

`DataOperationStorage.invoke` accepts an operation string and `dict[str, Any]`, and returns another
dictionary. Closed wire validation is real runtime protection. Nevertheless, `native_operation_calls`
collapses every signature to `OperationFieldType('json_payload')`; `DemandPlanner`, the executor,
`data_operation_service` and external/authoring consumers reconstruct field access through strings.
For example, `create_native_demand` returns `dict[str, Any]` and extracts `demand['demand_id']`.
This loses useful static correspondence after validation; it is not evidence that malformed wire is
currently accepted.

Extend the existing call-generation responsibility with captured protocol definitions and explicit
nominal correspondence. Generate named operation request/result surfaces, nested records and the
supported discriminated alternatives. Keep open semantic bodies as exact JSON values where their
kind genuinely varies. Required, optional and nullable remain distinct; product/member/context and
receipt/attempt references must not become interchangeable strings. Immutable internal structures
must not promise deep immutability while exposing mutable nested dictionaries.

This requires generator work: the current emitter's generic `JsonValue` treatment and schema-bearing
result wrappers do not recursively turn Draft7 `$ref`/union structure into useful Python types.
Provide useful static structural projections for the constructs actually present and retain the
captured schema as runtime authority. Recursive tagged semantic values and conditional
`if/then/else`, `allOf` and `dependencies` constraints need explicit treatment: retain a named exact
value type and runtime constraints where Python types cannot express them. Reject unsupported new
generation deliberately, but rejecting valid current protocol operations is not completion. Do not invent a second handwritten DTO catalog or
infer nominal meaning from suffixes. Existing model-owned source correspondence is the place to
state non-derivable distinctions. The existing schema-property flattening helper is not a union
decoder: preserve alternatives before deriving their static shape. The generic validated invocation
can remain private transport.

Migrate planner, executor, service, external receipt and public read consumers together. Generated
native symbol selection remains closed. Preserve exact numeric encoding, historical captured
interpretation and native permission/admission checks. A new release must not decode old results
using current defaults. Typed Python results confer no publication authority.

**Alternative:** retain validated mappings everywhere. This is functional, but leaves the broad
consumer migration repeating request/result knowledge. Merely annotating dictionaries with `Any`
or wrapping them in an unvalidated dataclass does not deliver the proposed correction.
**Closure:** a protocol-only field/union change reaches generated interfaces and real consumers;
independent malformed/unknown-field and qualified-ID cases retain their boundary behavior. Test the
actual decoder and callers, not only generated source text. Wire identity changes, if any, need
explicit versioning; do not change the wire solely to improve Python ergonomics.

<a id="I02"></a>
## I02 — Deliver the pinned read and cut model through every PostgreSQL consumer

**Missing accepted obligations made concrete; DDO-09/10 with DDO-07/08/11. FP-01/03/04, DP-04/08/09/18,
CI-02/04/11/12/13.**

The interface companion already requires replacing task/run-origin joins. Existing
`operations.py` still resolves copied reuse through `coalesce(reused_task_id,id)` in result and view
queries; the public export, replay and reference paths have real run/task-shaped contracts.
A successful `ci demands read` is not their migration. Historical structural replay deliberately
refuses target references rather than fabricating legacy task/view identifiers; preserve that honest
boundary until the target journey exists.

Implement the new DemandResult/CutSelection projection over exact fulfillment, product/member,
source, producing episode, support and trust pins through the existing protected Core/native route.
Derive eligible row/return types from that definition. Shared projection fragments may compose source,
member and support selection; they cannot introduce a second latest/current classifier. Keep native
read-acquisition effects separate from pure row projection.

Migrate serving/characterization/contextual navigation, definition/assertion queries, all three
contextual recipes, CLI records/export, actual MCP resources and continuations, review bundles,
detached verification/replay, and protected evaluation consumers. Requests and cursors carry the same
selection and interpretation through their whole lifetime. Zero output, pending/failed fates,
partial coverage and unknown support stay observable. Bounded output cannot silently narrow the
examined graph or evidence closure.

Consolidation consumes declared exact cut bindings and policies, retaining per-run knowledge where
that accepted output requires it. Reference authoring and grading retain separate source/prediction
releases and protected labels. Do not replace them with a generic demand read that exposes answers.

**Alternative:** add a DDO reader beside old serving joins. That leaves two current selection
models and export/replay incompatibility; restrict the old reader to identified sealed historical
obligations instead. **Closure:** one target selection travels native → CLI/MCP pagination → export
→ detached replay with independent member/source/relationship expectations and wrong-pin refusals;
protected references remain inaccessible to ordinary discovery. Remove superseded current joins,
codecs, defaults and fallback selection in that same consumer migration.

<a id="I03"></a>
## I03 — Retire run-based semantic mechanisms as complete vertical slices

**Accepted retirement strengthened; DDO-06–11. FP-01/03/04/07, DP-05/09/19, H1/H25/H27.**

Remaining `operations.py` paths combine run preparation, task selection, `task_dependency_scope`,
copied reuse, completion envelopes and task-qualified reads. Run commands and supervision still have
callers. Grouping all these as 'historical' would preserve current mutation paths; deleting the
module wholesale would lose useful readers, algorithms and physical ownership.

Replace semantic reuse with the declared recipe/value/support mechanism and reverse lineage owned
by DDO-09. Retire copied `reused_task_id` meaning, runtime/freshness salts and determinant lists after
their producer, consolidation and read consumers migrate. Replace legacy run finalization and
supervision only where native demand settlement now supplies their required behavior. Actual
`ops.task` attempt/lease/holder custody remains until a replacement supplies those physical fences.

Treat legacy `complete_task` publishers, vector JSON/text-cast storage, visual/external requests,
source-progress reporting and cancellation/task-list commands as consumer-bearing slices. Preserve
specialized algorithms and source custody; redirect current effects to their declared operations,
and make historical inspection explicitly read-only where that is the remaining contract.

Delete obsolete Python methods, registrations, payload builders, native entrypoints/grants,
configuration, generated vocabulary and mechanism-only tests only within the proven retired scope.
Frozen migrations and retained historical bytes are not rewritten. DDO-11 performs final physical
retirement after preserving selected original/reference/evidence closure; earlier code migration
must not wait for a destructive cutover.

**Alternative:** indefinite compatibility dispatch retains precisely the competing authority the
plan replaces. **Closure:** ordinary supported frontdoors use native demands; reuse and consolidation
explain exact consumed bindings; no live current producer/read path falls back to run-keyed meaning.
Historical readers demonstrate their actual retained obligations separately from current execution.

<a id="I04"></a>
## I04 — Keep native binding verification selective without changing its meaning

**Focused infrastructure improvement; DDO-04/05/06. FP-07, DP-10/20, H5/H7/H8/H10.**

The earlier PostgreSQL I01 distinguishes implemented set-based executor hydration from native
validation that aggregates the complete subject/source/analyzed-scope binding-row population,
including bodies, before checking selected inputs (`sql/data_operation_bindings.sql:658`).
The current bound-row successor has already supplied those scope predicates; this is not an
unqualified whole-demand scan claim. Retain the existing typed pin relation/server-side cursor route. For native selected
verification, derive the smallest sufficient keyed relation and project only fields required by
selected comparison, support and population predicates. Keep semantically necessary complete-population
work for all-members, absence and closed-discovery checks; a selected-key filter cannot replace it.

Separate selected-value access from population-witness evaluation when their required scopes differ,
using Core joins/EXISTS/lateral composition under the same authenticated read/trust pins. The
native half must independently verify selected inputs; do not call native raising comparators from
candidate filtering or share one implementation as both result and oracle.

**Alternative:** retaining the current aggregate is acceptable if the actual predicate requires its
whole scope and bounded representation. Do not replace it merely with a loop hidden behind a bulk
API. **Closure:** independent same-role/context/cardinality, empty versus partial population, wrong
support and revocation cases remain correct; selected hydration does not load unrelated bodies where
no governing predicate needs them. Source/query reasoning can establish eliminated work; no timing
claim or benchmark obligation follows. Author a forward native successor for changed bodies.

<a id="I05"></a>
## I05 — Align database capacity and failure ownership with the invocation

**Infrastructure correction and alignment; DDO-06 and shared retained consumers. FP-01/05/07,
DP-15/19/20/21, H18/H21/H24.**

Retain one physical connection manager per opened purpose, with SQLAlchemy borrowing from Psycopg's
pool through `NullPool` and `close_returns=True`. Purpose-specific credentials, maintenance/admission
sessions, snapshot readers and session advisory-lock owners are distinct responsibilities; merging
them into one universal pool would weaken their contracts.

Make the executor's database acquisition fit the shared invocation's actual maximum simultaneous
borrowers and renewal needs. Account for claim admission, active groups, publication, per-port database
work, renewal and other admitted borrowers. Four worker threads do not prove four simultaneous
claims: current execution also caps active groups by capacity, two at defaults. Prefer short checkout
lifetimes and bounded admission with a demonstrable renewal route; choose reserved renewal capacity
or a separately bounded renewal pool only if the actual shared-pool envelope needs it. Do not build a
scheduler, capacity estimator or permanently duplicated pool merely to satisfy an arithmetic rule.

Fix repeated dialect connection initialization at the owning pool/SQLAlchemy integration boundary.
Installed source shows SQLAlchemy's Psycopg on-connect callback appends a notice handler, while the
externally pooled physical connection can return through another SQLAlchemy connection event.
Treat this as a source-supported accumulation defect, not a reproduced production incident. Ensure
physical initialization occurs once per physical connection and checkout/session reset retains the
correct responsibility. Preserve extension checks, JSON adapters, exceptions and cleanup ordering.

Keep generic SQLSTATE/pool/ADBC physical classification in `core/db/store.py`, native invariant
meaning in declared diagnostic bindings, and retry/reconciliation policy with the operation. Remove
duplicated physical decoding where present, not every local SQLSTATE branch. Known catalog refusals
and SERIALIZABLE release retries have legitimate local meaning. A DDO refusal envelope is not the
same outcome as an exception or an uncertain commit.

`claim_lifetime._retryable_renewal_timeout` compares English server messages. Replace locale-based
inference with an explicit operation policy over trustworthy error/effect facts. SQLSTATE `57014`
means query cancellation; absence of a client cancellation request does not prove a server deadline
rather than administrative cancellation. If renewal permits a bounded retry after rollback-confirmed
query cancellation, state that policy honestly and recheck lease coverage. Do not relabel every such
error as timeout. Preserve unknown-effect reconciliation and do not make non-idempotent publication
automatically retryable.

**Closure:** targeted future controls cover repeated physical checkout, saturated acquisition with
renewal, rollback-confirmed cancellation, connection loss, exact uncertain receipt replay and cleanup
failure attribution. Broad benchmarking or global error registries add no required value.

<a id="I06"></a>
## I06 — Remove the obsolete relational target while preserving live Arrow conversion

**Additional reduction opportunity already noted by DDO; DDO-01/10/11. FP-01/04/06,
DP-01/06/16/17, H1/H27.**

`schema.relational.compile_metadata` defaults to `target='legacy'`, with a separate `_Compiler` from
fixed semantic/read physical compilation. `schema.interchange.compile_interchange` constructs legacy
table/payload Arrow schemas from that default; `installed()` caches them. In the inspected source,
production has no discovered call to `compile_interchange` or `installed()`.
`compile_metadata` itself remains live through `schema/physical.py` for semantic targets. Schema tests still exercise them and
`schema/model.py` includes their compiler revision markers. This is bounded search evidence, not
proof about external scripts.

Extract the useful SQLAlchemy-type-to-Arrow conversion from `interchange._sql_arrow` into the current
transfer/type owner: `serve/native_source.py:1028` still imports it. Inventory record/payload encode
helpers before removing adjacent functions. Remove the legacy table-projection compiler/default,
unconsumed installed interchange/schema generation, stale type mappings and revision contributions
once their finite consumers are migrated. Keep semantic physical/read compilation, typed-column
emission, current pgvector types and independent null/numeric/type expectations. CLI schema release
compilation already uses semantic regeneration; native-candidate authoring is not a legacy-target
consumer merely because it imports `Vector` from the same module.

Check `HalfVec` at the actual model and frozen migration imports before removal. A deleted current
model element does not prove no retained revision needs its Python symbol. Do not remove supported
`Vector` because Arrow has no generic vector mapping: choose a declared vector representation only
for a real Arrow consumer, otherwise retain explicit unsupported-type refusal.

The separate earlier `alembic/versions` tree has no discovered current migration route; `ci db migrate`
uses semantic migrations and refuses the legacy database shape. Preserve the immutable active
`semantic_alembic` chain. For the old tree, establish real reader/restore/import obligations before
choosing archival retention or removal of unsupported executable artifacts. Do not add a new
legacy-upgrade adapter simply to justify keeping that target alive.

**Alternative:** isolate a legacy compiler only if an identified supported consumer requires it.
Compatibility for tests alone is insufficient. **Closure:** current native/source Arrow export and
semantic metadata/generation retain independently expected types; current CLI compile/authoring
works without the legacy projection. Retained migration imports and actual historical readers stay
resolvable. No migration file or artifact is rewritten as part of this proposal.

<a id="I07"></a>
## I07 — Preserve transport distinctions and record the target vector contract

**Retain strengths; conditional extension and explicit retirement, DDO-07/08/10/11.
FP-02/04/07, DP-11/15/18/19, H15/H16/H23.**

DDO product identity includes canonical member bodies and uncertain completion can be replayed in a
later transaction. Keep exact JSON transport for these bodies unless a concrete new requirement
justifies redesigning identity, intent durability and publication together. Typed COPY already has
real owners for PDF staging and release archives. Reintroducing transient staged member payloads
would recreate the withdrawn proposal's recovery hole.

Retain Psycopg/pgpq COPY on the borrowed publication transaction, explicit columns and declared
schema/type checks. pgpq encodes Arrow; its emitted DDL is not model authority. Retain a separate ADBC
session only for its actual Arrow read contract, importing the established SQLAlchemy snapshot and
owning cancellation/cursor/reader lifetime. ADBC ingestion is not a drop-in replacement for a COPY
that must share an existing transaction. Global replacement of JSON adapters also risks changing
exact DDO decimal/context semantics or legacy float payload interpretation.

Record contextual retrieval's implemented vector-member contract in the affected DDO/D3 owners:
product members carry vectors and retrieval binds typed `VECTOR(d)` values in a transient relation
for exact cosine/lexical ranking. This differs from legacy task-keyed stored vectors and repeated
JSON/text casts. Retire that legacy storage/search route with its I03 callers; do not introduce a
second persistent vector index to unify appearances. Preserve dimension, finite/numerical and selected
inventory contracts. Approximate search requires an actual changed retrieval requirement.

Arrow transport for DDO-10 remains conditional on a real large tabular reader. Derive the row shape
from the same pinned projection, preserving type fidelity and limits. `read_demand_result` records
read/trust state and locks: it must not be treated as a pure COPY-exportable query. Acquire native
read authority first, then qualify the chosen pure projection/snapshot path. Atomic JSON pages remain
valid for consumers needing closed page semantics.

**Closure:** actual publication rollback/cancellation and exact-intent replay retain their guarantees;
source/export values preserve independently expected numeric/null/time/ordering meaning. An Arrow
extension requires its actual security-definer/COPY and snapshot behavior qualified before adoption,
not an unconditional extra backend or campaign.

There is a concrete obstacle to simply reusing the current ADBC snapshot wrapper:
`sql/data_operations.sql` inserts `ops.data_demand_read` in `read_demand_result`, and
`data_binding_rows` reads that row using `SELECT INTO STRICT`. A separate session importing the
exporter's snapshot cannot see the exporter's own uncommitted insertion. PostgreSQL 18's
[snapshot synchronization contract](https://www.postgresql.org/docs/18/functions-admin.html#FUNCTIONS-SNAPSHOT-SYNCHRONIZATION)
explicitly preserves that transaction boundary. Therefore acquisition plus snapshot import in the
same exporting transaction is insufficient. Compare same-session Psycopg streaming, a separately
committed pin followed by fresh authenticated snapshot/revalidation, or a protected projection over
explicit authenticated immutable pin values. Each must preserve selected boundary/owner-XID and trust
semantics; committing acquisition is not an automatically equivalent fix. Until qualified, retain the
existing bounded native/Psycopg read route. This makes the prior conditional Arrow recommendation more
specific, rather than scheduling a second read authority.

<a id="I08"></a>
## I08 — Finish structural SQL cleanup inside the existing authoring lifecycle

**Carries forward PostgreSQL review I05; DDO-03/04 with DDO-09/10 projections. FP-01/03/04, DP-06/13/14/15/24.**

The accepted SQLAlchemy/Alembic amendment has already delivered captured fate-set derivation, shared
Core binding/read shapes, governed privilege operations and frozen named data steps at its bounded
foundation. Keep that implementation rather than propose the same rewrite again. Alembic comparison,
registered operations/rendering and frozen before/after policy remain the schema/native lifecycle.
Global retirement ordering, owned role restoration and cross-owner authorization still have real
consumers; no new migration engine or speculative branch arrangement is needed.

Use pglast declaration transformations for actual structural header edits instead of string function
renaming in `data_operation_storage.native_sql`. Preserve procedural body bytes and dollar quoting;
AST deparsing is not guaranteed lossless for every PostgreSQL declaration. Consolidate duplicate
native descriptor extraction and trigger interpretation where they mean the same fact, using the
existing native owner rather than a new parser abstraction.

Keep SQLGlot qualification/type/lineage analysis scoped to the checked projection recipe. It is not
PostgreSQL authorization or an alternative execution representation. A compiled-SQL dependency
cross-check is conditional on a concrete DDO-09/10 consumer that can use it; declared dependencies
remain authoritative. Unresolved PostgreSQL syntax must remain unknown, never proof of no dependency.
Do not replace complete support or population semantics with syntactic table extraction.

**Closure:** actual changed declarations retain independently expected identity, owner/ACL and body
meaning; compare against real catalogs when authoring verification is later authorized. Retained
parser limitations need bounded unsupported cases or a deliberately chosen upstream correction,
not broad handwritten parser work. A native-body change uses an immutable forward successor.

## Whole intervention, order and acceptance

Prioritize I01/I02/I03 as the coherent domain/consumer replacement. Define their shared selected
read and result contracts before extending family consumers; develop supported typed generation and
consumer migration together. I04/I05 accompany the executor/read slices that exercise them. I06 can
proceed independently after the live Arrow helper and retained imports are separated. I08 fits the
next actual authoring change. I07 preserves existing transfer responsibilities; its conditional Arrow
extension is not a prerequisite to the semantic replacement.

| Package group | Amendment and integration boundary |
|---|---|
| DDO-01–04 | Derived typed protocol surfaces; retained model/Core authority; selective native verification; scoped structural cleanup; legacy compiler reduction |
| DDO-05/06 | Consume typed native results, maintain exact read/claim pins, bound actual DB borrowers and renewal; preserve physical settlement/replay |
| DDO-07/08 | Migrate producer/immediate-reader families and legacy publishers/vectors/external requests; retain genuine kernels and custody |
| DDO-09 | One declared reuse/change/cut-currentness mechanism; remove copied-task meaning and run-specific invalidation with callers |
| DDO-10 | Complete public read/query/MCP/export/replay and protected assessment journeys; remove current runtime-binding/address fallbacks |
| DDO-11 | Verify preserved closure and actual historical readers, coordinate adoption, perform final obsolete physical/API/grant retirement |
| DDO-12 | Qualify the assembled replacement and preservation behavior under the existing required union; no separate PostgreSQL campaign |

These are proposed amendments to existing owners, not DDO-13 or a parallel execution ledger. I02/I03
mostly expose missing accepted obligations, whereas I01/I05/I06/I08 add or sharpen implementation
mechanisms. Substantial restructuring is justified where it removes competing meaning; a generic
repository facade, ORM conversion, universal error taxonomy or transport rewrite would add burden
without closing the identified consumer gaps.

Key future discriminating cases are protocol-only changes with actual caller adaptation; complete
qualified identities and exact values across native/Python/Arrow boundaries; concurrent demands with
renewal/cancellation and unknown publication outcomes; pinned pagination through detached replay;
reference/prediction isolation; and retirement while a genuine historical reader still works. Reuse
existing invariant enforcement for consumer tests while retaining independently specified expected
values and selected memberships. Emitted SQL agreeing with its generator is derivation evidence,
not semantic/native correctness.

No automatic rule change follows from this review. Any selected amendment that changes a binding
decision, authority, preservation or pool ownership commitment must use the existing ADR/architectural
owner route before dependent adoption. Ordinary refactoring under an accepted contract needs no new
ADR solely for code movement. The DDO coordinator remains the sole owner of selected scope and
finding disposition.

Independent challenge narrowed I01 to structural static projections plus runtime conditional
constraints; complete Draft7-to-Python equivalence is not claimed. It also independently confirmed
I07's cross-session own-write visibility obstacle and clarified I06's live compiler boundary. Both corrections are integrated above.

## Library capability coverage and selection

The eight references, including addenda/corrections, were investigated in two library-research
contributions. References are orientation; installed source establishes the consequential integration
facts named here. This table groups capability families rather than requiring a feature quota.

| Reference and capability families | Contextual disposition |
|---|---|
| [SQLAlchemy](../libraries/postgresql/sqlalchemy.md): Core expressions, typed rows/types, metadata/reflection, dialect-native operations, execution/transactions, caching/events/extensions; ORM and loading | Core, model-bound type/row generation and native projection compilation carry I01/I02/I04. Retain transaction and dialect integration, repair repeated physical initialization. ORM/session identity maps, routing and distributed extensions have no demonstrated replacement consumer here; adding them would not fix semantic selection. No new SQL expression DSL. |
| [Alembic](../libraries/postgresql/alembic.md): revision graph/state, autogeneration, structured plugins/rewriters, operations/renderers, online/offline execution, data steps, testing and dialect extensions | Existing programmatic produce/compare/render/upgrade with caller connection, custom native/privilege operations and frozen data steps already fits. Retain global dependency ordering. Revision branching, batch rebuild and offline deployment do not solve the current gap; use them only for a concrete future migration need. |
| [pglast](../libraries/postgresql/pglast.md): PG18 AST, visitors/mutation, lexer/source locations, deparsing/printers, fingerprints, procedural inspection | Structural native edits and shared fact extraction support I08; retain actual procedural enforcement. Parse trees do not resolve catalogs/types/privileges, procedural JSON inspection is not a PL/pgSQL compiler, and normalized fingerprints omit distinctions needed by custody identities. Deparse limitations prevent unconditional whole-body regeneration. |
| [SQLGlot](../libraries/postgresql/sqlglot.md): typed/dialect AST, qualification, lineage, optimization, diff/serialization, JSONPath, templates, DDL/privileges, execution/extensions | Retain checked-recipe analysis and located explanations. Conditional compiled-SQL cross-check remains secondary. DDL/Grant nodes do not establish effective database privileges; AST similarity is not semantic compatibility or complete dependencies. Python SQL execution, transpilation or a second authoring AST would not replace Core/native authority. |
| [Psycopg](../libraries/postgresql/psycopg.md): binding/composition, adaptation, row factories, streaming/cursors, COPY, prepared statements/pipelines, transactions, async/cancellation/notifications/diagnostics | Retain selected driver and transaction-aware COPY; use typed SQLAlchemy results at SQLAlchemy-owned cursor boundaries rather than imposing a second row-factory system. Exact DDO JSON stays scoped. Prepared/pipeline/async/notification features require actual independent batching or wakeup needs; none is a prerequisite for this replacement. |
| [psycopg-pool](../libraries/postgresql/psycopg-pool.md): ownership/close_returns, configure/check/reset, elastic/zero-min/null pools, capacity, health/reconnect, retirement/resizing/stats | Existing real pool plus SQLAlchemy NullPool is intentional. I05 aligns aggregate borrowers and renewal with lifecycle hooks. Reset/reconnect/observability additions need actual uncontained state or operational consumers; do not duplicate the pool's rollback/discard behavior. Capacity bounds alone do not reserve renewal availability. |
| [pgpq](../libraries/postgresql/pgpq.md): encoder lifecycle, Arrow/PG types, arrays/composites, JSON encoders, schema fidelity, stream errors, Python/Rust boundaries | Retain schema-checked per-COPY encoding on the publication transaction. Current adapter rejects unsupported precision/type conversions; do not bypass those guards or use encoder DDL as authority. No revived generic staged-member protocol or bespoke binary encoder. |
| [ADBC PostgreSQL](../libraries/postgresql/adbc-driver-postgresql.md): Arrow reads/parameters, ingestion, OID/type discovery, metadata, transactions/cancellation/diagnostics, direct Arrow interoperability and connection profiles | Retain current snapshot-bound analytics/export lifetime. I07's new DDO read requires resolution of native read-row visibility first. Ingest on another session cannot inherit publication transaction custody. Metadata discovery does not replace model/custody authority; DuckDB integration and new connection-profile machinery have no current DDO consumer. |

Selected versions are SQLAlchemy 2.1.6, Alembic 1.20.1, Psycopg 3.3.6, psycopg-pool 3.3.3,
pglast 8.7, SQLGlot 30.27.0, pgpq 0.12.0 and ADBC PostgreSQL 1.13.0. No version change is proposed.
The SQLAlchemy/Alembic reference main headings describe earlier patch versions; their corrections
and the selected installed sources, not those headings, inform the recommendations. Adjacent
pgvector 0.5.1 and PyArrow 26.0.0 supply actual current vector/columnar contracts; neither broadens
this into a separate library-family review.

## Reconciliation with the earlier reviews

| Source recommendation | Independent disposition at this baseline |
|---|---|
| PostgreSQL I01 | Executor set hydration is implemented. Carry native selected-verification improvement as I04, retaining complete-population obligations rather than blindly applying selected-key filtering. |
| PostgreSQL I02 | Carry I05 with a tighter actual-borrower/renewal analysis; worker thread count and configured pool size alone do not prove availability or starvation. |
| PostgreSQL I03 | Qualify through I05: share physical classification, retain operation-owned policies and declared invariant bindings. SQLSTATE alone cannot distinguish all causes of query cancellation. |
| PostgreSQL I04 | Implemented transient typed vector retrieval; record its contract and retire legacy storage through I03/I07. No new persistent vector representation selected. |
| PostgreSQL I05 | Carry explicitly through I08; structural edits and helper consolidation remain low-priority parts of an actual native-authoring change. |
| PostgreSQL I06 | Still conditional, with the newly explicit uncommitted read-pin visibility obstacle and alternatives in I07. Existing ADBC snapshot infrastructure alone is insufficient. |
| PostgreSQL I07 | Remains conditional in I08. Recipe/declared semantics stay authoritative; syntax analysis is supporting evidence. |
| Withdrawn staged-member proposal | Keep withdrawn. JSON identity/intent semantics, PDF staging and release archive staging have different owned purposes. |
| PostgreSQL defect 1: notice handlers | Source-confirmed integration issue retained in I05, without claiming a live reproduction. |
| Defect 2: renewal message locale | Observation retained; remedy qualified because cancellation classification needs contextual policy, not simply removing the English comparison. |
| Defect 3: HalfVec mapping | Current mappings remain; I06 requires retained import/consumer analysis before deletion. Missing current model use does not prove historical irrelevance. |
| Defect 4: stale design text | Update affected D3/D9 ownership/version/transport descriptions with selected amendments; do not let older text override the implemented source or coordinator. |
| Defect 5: parser/deparser hazards | Retain as version-specific limitations for actual affected constructs, not evidence all SQL authoring is unsafe or a reason for a parser replacement project. |
| SQLAlchemy/Alembic I01–I05 | Captured fates, shared Core reads, independent binding cases, compared privileges and frozen data steps are implemented foundation contributions. I01/I02 here extend consumer/type coverage; they do not relabel that prior work unimplemented. New public projections and qualification remain open at their existing owners. |

The earlier PostgreSQL review's 'small remaining set' judgment was relative to its library lens and
limited consumer coverage. It does not settle the broader domain/consumer replacement selected here.
Conversely, discovering the broader remaining footprint does not invalidate its sound transport or
native-authority decisions.

## Evidence, independent challenge and limits

Root synthesis combines a read-only consumer/retirement map, two library/source investigations and
a fresh independent design challenge. Code mapping covered Python source, both migration trees and
affected schema/semantic/serve/evaluation/test tools. The principal new type-boundary observation
was read directly in storage, wire generation, planner/service/executor consumers and shared row
projection code. The native binding aggregate, read acquisition and row lookup were inspected
without executing them. Library sources include installed SQLAlchemy engine/dialect callbacks,
Psycopg notice-handler and pool transaction-return behavior, plus PostgreSQL's documented snapshot
visibility. These are source/documentation observations, not passing functional tests.

Coverage follows all ten companion responsibilities and all eight library capability families.
It does not claim every native function body, test, schema instance, external invocation or possible
dynamic import was exhaustively assessed. Parser scans and prior offline experiments were not
replayed and receive no new evidence credit. The review makes no new table counts, workload-size,
throughput, speedup or complete consumer-absence claim. Retained historical migration imports,
exact preservation bytes and real restored historical reading require the existing DDO-11 work.

**not_run:** `uv run ci test`, native/provider controls, database status/census, native authoring,
benchmarks, broad `uv run ci check` and health campaigns. Standing cancellation remains in force.
Only documentation publication validation and root turn-end maintenance are run for this review;
their dated outcomes are recorded in STATUS. No diagnostic baseline, accepted ADR, architectural
owner, implementation plan, dependency, product code or test implementation is amended.
