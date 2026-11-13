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
semantics only with their DDO-07/08/10 callers moved. DDO-11 preservation is a prerequisite for any
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
