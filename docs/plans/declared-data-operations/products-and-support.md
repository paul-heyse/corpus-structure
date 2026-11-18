# Products, support and the native kernel

**Proposed implementation plan ·2026-11-12.** Develops DDO-04; the
[coordinator](../declared-data-operations_2026-11-12.md) owns state and finding disposition.
Consumes DDO-01–03 contracts and provides the actual native interfaces for DDO-05–11.
No native objects described below exist merely because this document names them.

**Execution owner · 2026-11-13:** the
[coordinator execution account](../declared-data-operations_2026-11-12.md#audit-repair-execution--2026-11-13)
owns delivered behavior, dated qualification and remaining package scope. This companion keeps
the governing contracts; it does not maintain a second completion ledger.

The [completion audit](../declared-data-operations_2026-11-12.md#completion-audit--2026-11-13)
introduced DDO-CA-02/04 for overlapping publication replay and purpose enforcement.
Their current disposition belongs to the coordinator's findings table.
CA-05 also retains the complete-context discovery closure gap. Successful member/product admission
does not establish that native population closure accepts every valid distinct scoped member.

## Target and representation

Extend the trusted physical LinkML model and its SQLAlchemy metadata. Candidate semantic releases
supply definition rows, not arbitrary tables. Keep `sem` for immutable declarations, `kb` for
products, `ops` for demands/execution and `eval` for protected assessment. Physical layout need
not mirror every semantic concept; indexed common headers plus existing kind-specific projections
preserve useful bulk access. `semantic/metadata.py:1–44` and `schema/relational.py` own this route.

| Relation / representation | Meaning and key |
|---|---|
| Released operation/kind projections | Definition revision, recipe, binding and kind-contract fingerprints from DDO-01–03; immutable registry ordinals name fingerprints |
| kb.data_product | Unique kind-contract fingerprint, complete qualified subject context and canonical semantic-body digest; exact encoded artifact is separately authenticated |
| kb.data_product_member | Product-qualified stable local member ID; typed family projections preserve endpoints, occurrence multiplicity, source coordinates, coverage and choices |
| ops.data_demand | Immutable native demand identity, definition/release, target strength and frozen root/discovery/selection binding |
| ops.data_request | Unique recipe+complete qualified subject context+ordered/role-qualified inputs/support/population+replicate logical key; current execution generation/live task association |
| ops.task | Existing physical queue/attempt/lease/holder owner, extended with request/generation binding; do not add a second independent attempt state machine |
| ops.data_derivation | Append-only authentic execution ID, request/generation, exact completion/outcome and definition/runtime attestation; distinct episodes remain distinct |
| ops.derivation_input/output/support | Role-qualified product/member and support/selection references; order/multiplicity explicitly retained; canonical manifest identity matches rows |
| ops.demand_use | Demand obligation plus append-only selection/fate transitions; exact selected product/support or outstanding request, including zero-output and reused fulfillment |
| ops.data_completion_intent | Immutable request/generation/attempt-bound canonical completion intent, digest and publication receipt identity |
| ops.data_revocation | Append-only distrust selector/reason and monotonic trust epoch under the declared authority scope |

Common product headers do not replace typed semantic rows with EAV. Family-specific native readers
and endpoint constraints remain. Exact blobs/archive envelopes may share storage without collapsing
different semantic contexts. Choose composite unique/FK constraints for qualified references; a digest
alone never authenticates source custody or permits cross-project access.

## Complete lifecycle realization · Domain-model I03

The captured protocol owns recordable, historical and visible fate vocabularies, with distinct meanings.
Production records use the generated Literal types; bind-status conversion is an explicit typed mapping,
not a cast or duplicated spelling. Generate the data-task trigger's state/transition literals from the
same admitted protocol while preserving guards, holder/generation fences and transactional authority.
Every supported operation outcome has an explicit terminal mapping or a deliberate refusal. Remove
`ddo_completion_state`'s unmapped-outcome fallback with generated definitions and actual consumers;
previously admitted definitions are conversion/regeneration inputs, not a compatibility exception.

The protocol/compiler owner settles the outcome/state correspondence from actual definitions and the
native guard before changing generation. DDO-03/04 generate and consume it; DDO-05/06 use typed facts;
DDO-09 owns their impact interpretation. Verify protocol-only changes reach Python, SQL CHECK/trigger
and real claim/publication/read callers, with independently expected invalid transition/outcome cases.
A Literal-keyed dictionary alone does not prove totality. Use an exhaustive discriminator or exact-key
conformance against the authoritative vocabulary, retaining independently specified semantic expectations.


## DDO-04 implementation

First implement the fixed relational declarations, generated typed native calls and protected
publication operations together. Reuse `compile_metadata` and generated operation-call types.
Use PostgreSQL18 unique constraints and INSERT…ON CONFLICT for logical request coalescing, then
row locks on the existing task owner for attempt takeover. SQLAlchemy2.1.6 Core supplies set joins,
EXISTS, ordered aggregates and typed bind parameters; no Python item-loop readiness scans.

The native call contract has these fixed operation names; generated signatures expose the typed
fields described here rather than generic caller-supplied SQL:

| Native operation | Inputs → result/effect |
|---|---|
| register_data_demand | Authenticated compiled demand/root/selection → immutable demand ID or exact replay |
| attach_data_request | Demand obligation, resolved binding manifest, recipe/replicate → selected admissible fulfillment or unique request/generation |
| claim_data_request | Demand/request, holder and lease → exact existing-task claim/attempt fence or typed no-work/refusal |
| retain_data_completion_intent | Exact claim, canonical typed result and support closure → immutable intent digest; conflicting same attempt refuses |
| adopt_data_completion_intent | New exact claim+old immutable intent digest for same unresolved request/generation → native adoption binding on current task fence; retain original producer attribution |
| publish_data_derivation | Current claim+original or adopted intent binding+trust epoch → atomically installed products/projections/derivation/receipt/fulfillment or exact committed replay |
| inspect_data_completion | Exact request/generation/intent → committed receipt, known uncommitted or explicit uncertain/unavailable |
| revoke_data_support | Authorized scoped selector+reason → append-only revocation/epoch; no product deletion |
| read_demand_result | Pinned demand/selection revision, role/scope/page bounds → qualified result, fates, support/coverage and exact continuation |

Publish input/output/support rows, family projections, authentic derivation and demand fulfillment
in one short transaction after private computation. Different demands can attach to one successful
request; that does not fabricate independent derivations. A revoked success advances the request's
execution generation while appending new authentic evidence. Terminal old attempts stay terminal.
No request reassignment can publish under an earlier task/attempt/holder.

For publication/revocation ordering, resolve every required transitive support authority scope
and lock its trust epoch in sorted scope-key order first, then request,
then task fence in stable key order. Revocation advances that epoch under the same first lock.
Re-evaluate relevant support on epoch change; publication either precedes revocation and becomes
historically affected or observes it and refuses. Do not hold these locks during inference.
A demand read names its selection/trust snapshot; historical evidence is never rewritten.

Intent retention occurs before the potentially uncertain publication commit. A process-independent
resume inspects the exact intent and receipt; it cannot rerun stochastic inference to guess whether
publication committed. An intent does not itself authorize publication after lease loss: new fenced
ownership must authenticate adoption/replay. Existing ClaimOwner.settle and PreparedUnitCompletion
(semantic/claim_lifetime.py:29–112; operations.py:721–786) provide useful exact-replay semantics.

Indexes cover demand+subject+target obligations, request uniqueness, unsettled tasks, product identity,
input/support reverse lineage and revocation selectors. Query only the affected demand/population;
do not build a global all-subject/all-operation materialization. Purpose roles protect source,
ordinary read/write and evaluator universes separately.

## Migration, retirement and checks

Generate one forward native revision from trusted physical declarations and native operation owners.
Existing `semantic/migrations.py:39–78` owns advisory migration serialization, exact predecessor
checks and the caller's transaction. Use Alembic1.20.1 command.upgrade through that owner; version
stamping is not migration or catalog reconciliation. Freeze candidate artifacts through the existing
model-authoring/deployment route. Do not edit frozen old revisions.

Add targeted native controls: duplicate concurrent attach yields one logical request; member/role
and source mismatch refuse; two distinct derivations can support one product without adding a vote;
stale owner cannot publish; revoked required support cannot be laundered through equal bytes;
commit-ack loss replays one receipt; known rollback remains retryable. Deliberate malformed wire
must reach native enforcement. Generated types alone are not an oracle.

Retire old task-dependent product publication, copied reused-task fulfillment and task_dependency
semantics only with their DDO-07/08/10 callers moved. DDO-11 target-native adoption and writer fencing are prerequisites for any
destructive instance operation. DDO-04 finishes when native interfaces and permissions work, not
when a table/type draft compiles. It does not claim the complete series qualified.


### Logical key versus selected support episode

Canonical request identity includes semantic value inputs, population witnesses, declared support
requirements and any explicitly required episode/provider/alternative selection. An arbitrary
currently available support episode is not automatically a determinant for a value-only consumer.
The actual selected episodes remain authentic derivation inputs and DemandUse admission evidence.
An explicit support-rebinding operation may append an admissibility receipt proving equivalent
trusted inputs under that contract; it never rewrites historical lineage or fabricates a new
inference episode. Episode-specific and independent-evidence requirements cannot use this shortcut.


### Takeover and historical receipt semantics

The immutable intent retains its original producer attempt and runtime evidence. On unresolved
same-request/generation takeover, adopt_data_completion_intent authenticates the old intent,
its payload/source closure and the new claim, then associates its digest with the current task
attempt. publish_data_derivation verifies that adoption plus the new publication fence; it does
not rewrite the old producer fields or pretend the new holder performed inference. A settled
old generation is inspected/replayed as historical receipt, not adopted for another publication.
Inspection of an already committed receipt remains available under read permissions after terminal
status, lease expiry or revocation. Satisfying a new/current DemandUse is a separate live admission
and may refuse that historical support. Test takeover of uncommitted and already committed intent,
expired adoption fences and receipt availability after revocation.

Support rebinding is the explicitly modeled value-substitution variant of attach_data_request:
it accepts the equal-value binding and required support contract, authenticates alternative support
under the same epoch protocol and appends a DemandUse/admission receipt. It creates no new authentic
derivation, preserves original computation lineage and refuses episode-specific requirements.


Support substitution must independently establish that the authentic producing execution remains
trusted for its own recipe/runtime/behavior. Alternative upstream evidence cannot rehabilitate an
execution directly revoked for its own defect. Such a product needs a separate trusted producing
derivation (or recomputation), even when its bytes match. Preserve this refusal as an independent
native/admission test, alongside allowed substitution of equal-value upstream support.


## Coherent graph acquisition — I01/I02/I06

Consumes the [shared projection and physical-route contract](graph-projections-and-analysis.md#projection-contract-and-physical-route--i01).
DDO-04 supplies compact typed rows/adjacency through the same pinned native read owner used by
DDO-10. Bind source/contracts, selection and trust assessment for the acquisition lifetime; pagination
must retain the exact scope and required intermediates. Authenticate endpoints, occurrence roles and
support before exposing adjacency. Use indexed product/input/support lineage; no graph mirror table,
unrestricted reference crawler or independent trust cache is introduced.

[`MultiDiGraph`](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/classes/multidigraph.py)
can preserve keyed support occurrences for an analysis, while native typed rows remain authoritative.
[`reverse_view`](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/classes/graphviews.py)
can reuse owned immutable adjacency for reverse lineage; it is a live view, not a historical snapshot.
Run pure graph computation outside publication/trust locks. Retain selective SQL instead of first
hydrating the entire history. A read/result budget does not establish complete examined closure;
partial/unavailable acquisition remains explicit. Re-admit live effects under existing native fences.

Before runtime consumers integrate, qualify independent expected selected edges/members, isolates,
wrong source/trust scope, omitted intermediate and continuation across incompatible snapshots.
Bounds/custody failure must not become empty/complete support. Existing native race/publication and
revocation checks remain required; NetworkX reachability does not prove admissibility.


## Source-derived contract and recipe admission — Python I01–I04

Consumes the [shared contract](implementation-contracts-and-fingerprints.md). DDO-04 authenticates
compiled effective definitions and admitted implementation-revision manifests under the same native
request/publication owner. Input/support/value key projections consume the resulting recipe identity;
raw runtime archives remain provenance and never become hidden equality salts. Changed code cannot
publish under stale admitted recipe/correspondence merely because its Python signature matches.

Griffe [`visit` and alias resolution](https://mkdocstrings.github.io/griffe/reference/api/loaders/)
can identify callable structure and origins; this supplies no effect permission, trust or native
admission. Direct typed Python ports retain strict wire and native validation. Purpose roles, exact
source custody, unknown completeness and trust-serialized publication remain unchanged. Return pinned
source/contract/revision witnesses through existing reads; no mutable source-graph authority is added.

Native integration checks include mismatched manifest/recipe/call correspondence, unauthorized
implementation discovered by static analysis, nominal-role confusion and retained historical producing
runtime. Python extraction success cannot substitute for the deliberate invalid native-input cases.

The [source-evolution amendment](source-evolution-and-migrations.md#preparation-coverage-and-publication)
preserves this boundary. Proposed-source compilation prepares candidate effective facts and archive
products through `data_operation_artifacts.py` and normal release verification; source file effects
are not native admission receipts. Do not duplicate archive-only calls/IDs/schemas in the checkout
or patch generated bytes with a codemod. Current source updates use existing preview/apply; frozen
native revisions require immutable successors and existing registration/adoption custody.

## Native foundation completion correction · 2026-11-14

The [current audit](../declared-data-operations_2026-11-12.md#completion-audit--2026-11-14)
identified CA-08/09 under DDO-03/04; their current repair disposition is in the coordinator.
Native candidates must materialize contract-selected provider
identity from authentic producing custody instead of unconditionally refusing every such input.
Pinned acquisition/continuation must cover relevant transitive computational and original-source
trust scopes, consistently with recursive support validity and publication locking. Do not weaken
the complete-support containment guard to accommodate an incomplete read pin. Existing replay,
purpose-principal and qualified-context closures retain their narrow scope. The coordinator alone
owns repair state and positive/forgery/revocation verification under the operator-authorized
focused scope in the coordinator receipt.


## SQLAlchemy/Alembic native authoring and read alignment · 2026-11-14

**Accepted foundation contract; implemented state and bounded verification belong to the coordinator.** The
[coordinator amendment](../declared-data-operations_2026-11-12.md#sqlalchemyalembic-alignment-amendment--accepted-2026-11-14)
owns disposition and sequencing. DDO-04 delivers these foundation changes with the reopened
DDO-03/05 work. They are not postponed until later table-role changes or public reader migration.
Selected versions remain SQLAlchemy 2.1.6 and Alembic 1.20.1; no upgrade, ORM, native ENUM,
Alembic Utils, revision branch or second migration engine is required.

### Protected Core reads and explicit effects — I02

**Domain PG I02/I04/I08 additions · accepted 2026-11-14.** Existing SQLA/Alembic foundation is
retained. DDO-04 now also supplies the early selected-read contract consumed by public interfaces,
and PG-Q2's [predicate-shaped selected verification](postgresql-realization-and-retirement.md#reads).
The existing binding aggregate is already scoped by operation/subject/source/analyzed scope; narrow
body acquisition only where actual predicates permit it. Preserve product-qualified member/grouped
witnesses, population universals/absence, provider/trust identity and independent native selected
verification. DDO-05 consumes usable native premises, not merely an agreed select shape.

[Native structural cleanup](postgresql-realization-and-retirement.md#transfers) joins the next
affected authoring change: selected pglast headers/shared descriptor extraction preserve body bytes,
ACL/owner custody, Core placeholders and specialized effects. Changed bodies use immutable successors
under one chain owner. No duplicate privilege/data-step rewrite or new migration framework is needed.


Revise current `ops.data_binding_rows` and the read part of `ops.read_demand_result` with CA-08/09
and the existing binding repair. Derive eligible body/row shape from Core selects over the shared
`MetaData`, using the existing `projection_recipe`, `companion_projection_native` and
`native_sql_body` route. Direct application-owned Core expressions may compose CTEs, lateral joins,
table-valued functions and ordered aggregates; do not grow the closed ProjectionRecipe AST into a
new query language merely to express these selects. Extend the emitter only for the actual
multi-branch return requirements of binding rows. Reuse named selectables for visibility, latest
use and admitted product/member facts where current consumers repeat the same responsibility.

Acquiring sorted trust-epoch shares and inserting `data_demand_read` is an effect and stays inside
an authenticated native operation. Projection under its returned pins is a separate responsibility;
this need not add a caller round trip. Preserve a single atomic closed JSON page where planner/ci
consumers need it, composing acquisition and projection inside the existing native call as needed.
Do not label all JSON wire contracts obsolete. Keep guarded SECURITY DEFINER and fixed search_path,
empty runtime table-read roles and modeled EXECUTE grants. Such functions are not inlined: scope,
cursor and limit must enter as function parameters, not rely on outer predicates pushing down.

Provider-sensitive computed candidates must carry identity derived from authenticated producing
custody through row, request and native validation (CA-08). Read acquisition, continuation and
binding must use the same relevant recursive computational/original support scope closure (CA-09).
Keep publication locking and complete-support containment; Core conversion alone fixes neither
semantic gap. Use keyed, demand-scoped joins and bounded pages, without all-history expansion.
For new/revised effect INSERTs, compile explicit target columns from `Table` metadata and embed
the resulting SQL; avoid positional column-order dependence. Attach/claim/publish/revoke locks,
fences and effects otherwise remain specialized PL/pgSQL.

Compiled SQL is frozen in successors under existing custody and the selected library determinant.
The review's same-version deterministic compilation observations are not a cross-release byte
stability guarantee. JSONB path meaning remains a semantic responsibility even in a typed Core tree.
Future acceptance covers independently expected rows/pins, provider forgery and recursive revocation,
including three-source/two-hop continuation and fresh acquisition after a nonzero upstream epoch.
Wrong scope/contract/trust/cursor pins refuse. Text derivation checks supplement, not replace, those
independent expectations. New DDO-09/10 public projections consume this route in their own packages.

### Governed privilege operations and complete authoring integration — I04

Represent desired table owner/ACL and schema-usage policy explicitly in the existing trusted physical /
native authoring model. Before comparing operations, decide and record the governed privilege
universe: table and column grants, grant options and grantees, schema usage, PUBLIC and purpose
roles, and treatment of privileges outside that universe. Verification must enforce that declared
boundary rather than assume the existing read-role check covers every ACL detail. Share default
role policy with generated admission SQL instead of repeating role strings.

The I04 review baseline recorded table owner and read roles. Its admission guarded those roles
and PUBLIC. The current model generates complete schema and table ACL expectations and compares
them to typed PostgreSQL catalog observations. The older no-baseline argument applies to the
existing normalized table-read policy. Define deterministic interpretation of older frozen
declarations for the additional governed facts, or an explicit declared baseline through the normal
successor route where those facts cannot be derived. Do not infer desired/before policy from stray
live grants. Any unavailable predecessor fact must be resolved or refused explicitly, not called an
empty ACL. Frozen predecessor bytes remain unchanged.

Use the existing Alembic plugin's `Operations.register_operation`, `implementation_for`,
`renderers.dispatch_for` and comparator APIs for compared before/after privilege operations with
renderer/reverse behavior. Table comparison can own table deltas; schema usage needs its own shared
schema-level owner rather than a per-table duplicate. Execution verifies stale-before catalog facts
and applies the declared transition under correct owner authorization, followed by independent
after-state admission. A changed read_roles declaration on an existing table must yield an operation
rather than just a deployment refusal; an unchanged declared policy must yield none.

Integrate the new operation kind through frozen payload versioning, `cli/schema.py` serialization
(currently NativeTransitionOp-only), candidate loading/execution, `schema/model_explanation.py`
explanation/counting, ordering and managed receipts. Preserve reading/execution of frozen old
payload versions where actual registered revisions require it. Do not leave new operations outside
inspection or reported counts. Add nonempty diff-reporting (`to_diff_tuple`) support only for an
actual consumer; the current empty-diff test is not that consumer or a reason for a new gate.

Move role/privilege strings and role-restoration AST repair out only after the replacement owns
their effects. Ordinary table ALTER authorization and cross-owner FK creation still require valid
role context: moving GRANTs into an operation does not remove these obligations. Express special FK
authorization from declared constraint/ownership facts instead of matching one table/column name.
Retain explicit global physical-retirement ordering where needed. Qualify ADR-0074's retained-walk
rationale through the existing architectural owner/ADR route before dependent adoption; accepted
ADR bodies remain immutable. No automatic public Rewriter conversion follows.

Future focused acceptance covers existing-table role change, unchanged policy, schema usage,
column/grant-option cases within the selected policy, stale-before refusal, after-state mismatch,
operation serialization/explanation/receipt fidelity and required ordinary/FK ownership ordering.

### Revision-owned data steps and supported predecessor preparation — I05

Implement the bounded authoring cleanup with I04, not as a later generic migration framework.
For actual revision data moves, extend the closed frozen ChangeRequest DTO with a finite
repository-owned builder name. Resolve only a closed first-party mapping at authoring; never accept
arbitrary dotted Python imports or SQL in a request. Capture relevant builder implementation identity
in preview/staleness premises. A builder returns a Core statement, for example Insert.from_select;
authoring freezes its compiled named-column SQL in the revision's ExecuteSQLOp. Applying a frozen
revision never resolves or imports a current builder.

Registered forward-base replay applies frozen older revisions before current authoring, supporting
removal of old pdf_visual_index/characterization_source_scope backfill branches from the normal
head-successor route. Standalone authoring can still use an older migrated predecessor: determine
which predecessor routes are supported and preserve their behavior through explicit revision-owned
steps, or deliberately bound that route with a truthful refusal before removing branches. Do not
claim all historical branches are unreachable merely because the main chain is ahead.

Replace hardcoded task/run temporary columns only with prerequisite preparation derived from actual
target/catalog differences and authoring needs. Account for defaults, types, dependencies and
rollback-only lifetime; blindly adding every missing target column is not sufficient. Remove
revision-specific branches/scaffolding once their replacement and supported callers are accounted
for. Future focused acceptance covers one frozen named step exactly once, an unrelated successor
without table-specific work, captured-builder staleness, supported older predecessors and rollback.

All successors serialize through the coordinator's single chain owner after
`semantic_ddo_origeps_v1`. No persistent deployment or activation is authorized here. Tests remain
cancelled. Pivotal APIs, source references and alternatives are in
[review I02](../../plan_improvement_reviews/declared-data-operations-sqlalchemy-alembic_2026-11-14.md#I02),
[I04](../../plan_improvement_reviews/declared-data-operations-sqlalchemy-alembic_2026-11-14.md#I04) and
[I05](../../plan_improvement_reviews/declared-data-operations-sqlalchemy-alembic_2026-11-14.md#I05).

## Realized bounded graph acquisition · 2026-11-15

The graph reader now owns acquisition separately from pure analysis. It retains one bounded temporary
SQLite witness index after the reader transaction closes; snapshot construction, source/assessment
projection and NetworkX analysis run without publication/trust locks. Budget refusals retain the
authentic committed native read/cut/trust pins. No persistent mirror or connection compatibility
wrapper remains. Ordinary selected queries do not capture the extra graph frontier.

Native implementation capture includes the actual delegated graph helpers and NetworkX execution
profile; archived nominal source without those imports retains its original requirements. The DDO
coordinator and native evidence own qualification, not this contract description.

## Native validity, pinned reads, release facts and settlement — production-efficiency · 2026-11-17

**Accepted scope; implementation Proposed.** The coordinator owns status. The
[integration companion](production-efficiency-integration.md) owns the slice order and shared
mechanisms. This section owns the native contracts for PE-S16–S21, the native half of PE-S26 and
the SQL half of PE-S27. They deliver in two frozen successors: N1 (no wire change) and N2.
Paths: `sql/` = `python/corpus-structure/src/corpus_structure/semantic/sql/`.

### PE-S16 — indexes and the exact-pin union (PE-F08)

The sentence above, "Indexes cover demand+subject+target obligations, request uniqueness,
unsettled tasks, product identity, input/support reverse lineage and revocation selectors", is
the intent. At `2cc4e4d9d` the physical model declares only keys on the most-probed tables.
Declare through `ph:indexes` (`schema/relational.py` already supports list and dict forms):

| Table | Index | Serves |
|---|---|---|
| `ops.demand_use` | `(obligation_id, created_at, id)` | latest and later use per obligation |
| | `(demand_id, fate)` including `obligation_id, derivation_id, created_at` | demand-scoped scans, fulfilled filter |
| | `(request_id, generation)` | attach, claim, publish fan-out, request usefulness |
| | `(derivation_id)` where not null | support walk, read seeds |
| `ops.data_derivation` | `(request_id, generation)` | attach, read-page joins |
| `ops.data_obligation` | `(demand_id, id)` | frontier keyset page |
| `ops.data_derivation_output` | `(product_id, member_id)` | exact-pin arm, revocation by product |
| `ops.data_revocation` | `(scope, selector_kind, selector)` | direct validity, renewal, publish |
| `ops.data_population` | add a stored `context_key` (digest of the population scope, fixed at insert) to the existing index as `(demand_id, name, context_key, created_at, id)` | supersession probe |

Reverse-lineage indexes on `ops.data_derivation_support` are declared only when a
reverse-impact consumer lands (DDO-09); the forward walk is served by the primary key.

The binding universe's `(demand OR exact pin)` predicate is emitted as two arms joined by
`UNION`: demand-owned fulfilled uses, and uses reached from the declared pins through
`data_derivation_output(product_id, member_id)`. The existing distinct key removes a use that is
both. Acceptance checks index presence in the catalog and index use per listed predicate with
sequential scans disabled. That is usability evidence, not timing.

### PE-S17 — release facts lowered at admission (PE-F09 b)

`sem.admit_data_operation_definitions` already authenticates the release artifacts. The same
call writes immutable rows, and native readers use them instead of parsing and re-hashing
artifacts per call:

- `sem.data_operation_release(release_id, model_digest, native_definitions_digest,
  native_kernel_digest, lowering_digest)`;
- `sem.data_subject_scope(release_id, subject_definition) → scope`;
- on `sem.data_operation_definition`: `binding_expression`, `definition_identity`,
  `eligibility_identity`, `quantified`, `validity_family` (null when no per-kind validator
  applies), `command_class`, `dependencies`;
- `sem.pdf_operation_contract(release_id, operation_id, contract_id)`, written by PDF admission
  after its single digest verification;
- `execution_profile` on `sem.runtime_binding`.

Changed native code is still detected. Validity compares `native_kernel_digest` with the
installed source digest. A successor that changes the lowering re-lowers every admitted release
from its immutable artifacts in its data step, and readers refuse a release whose
`lowering_digest` differs from the installed constant. Removed: per-call
`convert_from(...)::jsonb`, the per-call `sha256` re-hashes, the JSON command-eligibility tests
and the four parses in `require_pdf_operation`.

### PE-S18 — set-wise support validity (PE-F05)

**Rule change PE-RC02, part 1** (ADR-A, superseding ADR-0093). Current support is evaluated
once per statement over the distinct support closure of the candidates.

Contract `ops.ddo_valid_closure(seed_uses, seed_episodes, boundary)`: a stable set-returning
function, called once per statement in a materialized CTE, returning `(kind, id, valid)` for
every distinct node reached.

1. **Closure.** The existing deduplicating `_support_walk` edge set, extended to emit an edge
   kind. AND-edges: episode to support episode, to support use and to original; use to producing
   episode and to population; population to source use and to parent. OR-groups: a use's
   recorded support, and its selected support when the producing definition's provenance is
   value substitution under a value-strength demand.
2. **Direct validity, once per distinct node, by set joins.** An episode is valid when its
   outcome is success or empty and no revocation row matches its scope and selectors; its
   per-kind check runs only when its lowered `validity_family` is non-null and checks only
   mutable premises (kernel digest, and cut trust for grade, fit and event episodes). An
   original admission is valid when visible under the boundary and unrevoked. A population is
   valid when no newer same-name, same-context population is visible. A use is valid when
   fulfilled.
3. **Propagation.** A recursive CTE marks nodes reaching an invalid node through AND-edges. A
   bounded loop resolves OR-groups: a substitutable use is invalid only when both groups are.
   Arrays and `unnest` joins are used; no temporary table (the statement-local rule of
   DDO-SI-23 stands).
4. **Termination.** Support is acyclic by construction. A node on a malformed cycle is invalid.

Boundary-relative facts (seed choice, original visibility, population supersession) use
`ddo_read_visible`. Revocation is always current, as today. Direct episode invalidity is an
AND-edge outside the OR-group, so a directly revoked producer is never rehabilitated.

The immutable `_require_*_producer` replays inside the `*_dependencies_valid` functions leave
validity. Their correspondence is established by the completion battery at retention today;
PE-S21 later records it under the kernel digest. PE-S00 confirms each helper reads only
immutable rows before that is relied on.

Removed: recursive `ddo_support_valid`, `ddo_use_valid`, `ddo_population_valid`,
`ddo_direct_support_valid`, and the seven unconditional per-kind calls.

Rejected: a maintained invalidation record. A transitive one puts a reverse-lineage walk inside
the revocation lock and duplicates the value-substitution semantics in a second authority; a
direct-only one adds nothing to a keyed join; boundary-relative parts would still be per read.

In the binding universe, role, kind, subject and source reduction now precede validity, and
validity is computed once on the distinct reduced candidates. The access check keeps its place
before subject and source, so the refusal surface is unchanged. Quantified operators still
receive the full role-filtered universe.

### PE-S19 — pinned read as acquisition evidence (PE-F07)

**Rule change PE-RC02, part 2.** At acquisition, the only write, the read records its complete
trust-scope closure as immutable `ops.data_demand_read_scope(read_id, scope, epoch, ordinary,
domain)` rows (zero epochs included; the flags keep the census subset used by grade cuts), its
distinct access universes, and the native kernel digest.

`ops.ddo_require_read_current(read)` then: locks the recorded scopes in shared mode in scope
order; refuses on any epoch difference; refuses on a kernel difference; authorizes the live
caller for each recorded universe. It recomputes no closure and performs no insert. Callers:
the pinned `read_demand_result` path, both binding functions, attach, population selection, the
grade, fit and event cut checks, which compare the cut read's recorded ordinary scopes, and the
selected-acquisition checks `ddo_require_source_set_acquisitions` and
`ddo_require_selected_output`, which today run a pinned page read per cut and per use.

This is acquisition evidence, not a cached authority result: every call re-locks, re-compares
live epochs and re-authorizes against live role membership, so ADR-0121's "no authenticated cut
or authority result is cached across invocations" stands. No session marker records "already
checked"; a caller could forge one. Reads acquired before N1 have no scope rows and refuse with
"reacquire".

By reading, the visible closure under a fixed boundary cannot gain scopes, because every walk
edge comes from a row immutable after insert. One tie remains open (PE-D03); PE-S00 decides
between strict owner-row visibility and forbidding writes in the acquiring transaction after
acquisition.

PE-S00 confirms that every binding candidate, including exact-pin uses from other demands, lies
inside the recorded closure; if not, pin scopes are added at acquisition.

### PE-S20 — settlement lock mode (PE-F30)

**Rule change PE-RC02, part 3.** Every settlement, cancellation, renewal and pinned read takes
the canonical closure in shared mode, in sorted scope order, before demand, request and task
row locks. Only `revoke_data_support` takes scopes exclusively and bumps the epoch. One
share-mode function replaces the separate renewal variant.

By reading, exclusivity among settlements protects nothing: epoch stability needs only the
single writer excluded; publication–revocation ordering holds under share because each
settlement statement takes a new snapshot; coalescing and attempt fences use request and task
locks; population creation is serialized by the demand lock. Share mode also removes the
inferred upgrade deadlock (PE-D07). This replaces the sentence in the demand-planning companion
that completion and publication retain exclusive authority.

### PE-S21 — kernel-sealed completion intent (PE-F09 c)

The intent records the installed kernel digest, which covers every completion-validator body,
and the complete locked trust snapshot. At publish, when the intent's digest equals the
installed digest, the immutable correspondence battery is skipped. Publish always runs: the
fence and adoption check; request authorization and the caller-purpose checks now inside the
policy, structural and rich validators; runtime and recipe revocation; set-wise support
validity over the intent's support, which also covers population supersession; and the per-kind
mutable premises. A differing or absent digest runs the full battery as today.

Classification of completion validators, read 2026-11-17 and confirmed in PE-S00
(I immutable only, M mutable trust state, A caller authority):

| Validator | Class |
|---|---|
| PDF, external, artifact, definition, contextual, rich preparation, structural dossier completion | I |
| Record grade, record fit, operation event completion | M (cut trust epochs) |
| Policy authorization, rich admission, structural admission completion | M + A |
| Output witnesses | I + A (body access authorizes the caller) |
| Support assertion | M |

Retain and publish remain two transactions. The retained intent is the durable recovery point
that distinguishes a lost acknowledgement from a rollback (ADR-0094); a savepoint inside one
transaction would lose it when the commit fails, and recomputing provider or GPU work is the
cost that point exists to avoid. With the battery sealed, the second transaction is short.

### PE-S26 — set-form native operations and member installation (PE-F10, PE-F12)

1. `register_data_demand` inserts the roots × root-operation obligations in the same call.
2. `close_data_population` inserts the population and the obligations for its members × the
   native discovery closure atomically and returns the count inserted. `expand_data_obligation`
   becomes internal. Items derived natively from authenticated members fail only on a broken
   invariant, so whole-call failure is correct here.
3. `attach_data_requests(read_id, items[])` returns, per item, `attached`, `fulfilled` or
   `refused` with its result or refusal. The union of support scopes is locked once, in shared
   mode, outside the per-item exception blocks; the narrow read check runs once; each item runs
   in its own subtransaction. Authorization failure aborts the call. Repeated request keys are
   deduplicated. Use keys stay deterministic, so replaying the call returns the same per-item
   results and inserts nothing.
4. `claim_data_requests(holder, lease, items[])` returns per item a fence, `no-work` or a
   refusal. Each item keeps its own task, attempt and lease fence.
5. Publication installs members with one `INSERT … SELECT` over the member array with
   ordinality, one insert per family table, and one anti-join collision check that raises on the
   first mismatching ordinal. When the product row already existed under an identical key,
   installation inserts nothing, and the anti-join check still runs against the existing
   members. Members are extracted from the body by native code, so a key match alone does not
   prove member equality across a kernel change; the check is one statement and keeps that
   detection.
6. The read page returns per obligation an `inputs_watermark`: the latest visible fulfilled use,
   population or original among its prerequisite operations and exact pins.
7. `read_demand_result` gains an `obligation_id` filter so a single pinned obligation is read
   without paging from the start. The request schema is closed, so this is a protocol change
   and ships in N2 with the set forms.

Preserve per-item fates, receipts and fences, idempotent obligation identity and member failure
isolation. Rejected: whole-call atomic attach (one bad obligation would block a page) and
client-side batching over single-item natives (keeps one round trip and one validation per item).

### PE-S27, SQL half — wire validation placement (PE-F04)

**Rule change PE-RC01** (ADR-0128, superseding ADR-0106; the Python half is in the contracts
companion). Each externally callable native entrypoint validates its complete input once per
call against the contract installed with its release, before any effect; a set-form call
validates the whole set once. Native wrappers do not re-validate their own results, and
native-to-native calls do not re-validate an admitted payload. The generated wrapper lowers one
schema constant per operation instead of extracting from the whole-contract constant, and adds
the installed contract's digest to its envelope. Removed: the output `ddo_require_wire` call
and the duplicate in-body input check in `release_data_attempt`. The client result check that
replaces the native one completes before the calling transaction commits; a call path that
commits inside the native call keeps its SQL output check.

### Acceptance

Expectations are specified by hand per fixture, under both a null and a pinned boundary.

- **Validity:** a diamond with a revoked shared ancestor; a deep chain revoked at the leaf;
  revocation by each selector kind; value substitution (recorded support revoked with a valid
  replacement is valid; the same under episode strength is invalid; a directly revoked producer
  with a valid replacement is invalid); population supersession inside and after the boundary;
  an original admitted after the boundary; kernel mismatch invalidating only kernel-checked
  families; an epoch bump in a census scope versus a domain-only scope; an injected cycle;
  a revoked evaluator-universe episode invalidating an ordinary consumer while ordinary export
  still stops at the authority leaf.
- **Binding order:** a revoked or malformed candidate of another subject or kind neither raises
  nor refuses this obligation; an unauthorized-universe row of an accepted kind still refuses.
  The union arms: a superseded pinned use from another demand is selected, a superseded demand
  use is not, a use both pinned and owned appears once.
- **Pinned read:** recorded scopes equal the hand-specified scope set of each fixture; a revocation in any recorded
  scope refuses, including a scope with zero epoch at acquisition, a domain scope and an
  evaluator scope; a revocation outside the closure passes; a caller lacking the evaluator role
  is refused on every call; a re-check leaves insert and update counters unchanged; a kernel
  change refuses; a pre-N1 read refuses.
- **Publish:** under the same kernel, publish still refuses after a revocation, after a
  supersession with no epoch change, and for an adopter lacking the evaluator role; a tampered
  intent that only the battery rejects is refused when the digest differs; exact replay returns
  the same receipt.
- **Locks:** two settlements on one scope proceed together; a revocation waits behind a
  settlement's share lock; a settlement queued behind a committed revocation refuses; two
  transactions each holding a pinned read and then attaching on one scope both finish.
- **Set forms:** a mixed batch commits its valid items and leaves no effect for the refused
  one; replay inserts nothing; duplicates within a batch are handled; two overlapping concurrent
  batches do not deadlock; a second run over an unchanged demand issues one frontier read and no
  expansion, binding or attach.
- **Release facts:** lowered rows equal facts parsed independently from the artifact bytes; a
  differing `lowering_digest` refuses.

### Native implementation preservation criteria

Equivalence of set-wise validity including value-substitution OR semantics and boundary
composition; the owner-row visibility tie; coverage of nested member kinds by stored universes;
share-mode correctness under revocation, renewal and cancellation; which SQLSTATEs set forms
trap and lock placement outside savepoints; whether set-form attach keeps ADR-0121's separate
attachment statements and live revalidation (attach stays separate from acquisition and each
item revalidates live); re-lowering in the data step; census-subset
correctness of stored cut checks; and the A4 judgment for register, bind, attach, execute,
publish and for the repeat run after N1 and N2.
