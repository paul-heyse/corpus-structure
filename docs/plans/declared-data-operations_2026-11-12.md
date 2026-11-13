# Declared data operations — total governing model

**Status: Completion reassessment found remaining implementation and qualification gaps · 2026-11-13.
DDO-00 preparation is complete. DDO-01/02 and DDO-03–05 remain partially implemented;
DDO-CA-01/05 have residual defects, CA-06/07 record missing projection/retirement obligations.
DDO-06–12 retain their broader open scope. Implementation remains paused at the operator's request.**
Owns DDO-00–12, the full audited F01–F14/C1–C7 scope, RC01–RC09 adoption and assembled
qualification. The operator selected this as a dramatic standalone redesign: other plans supply
no product scope or acceptance limits. Later operator-accepted test-system dependencies are
recorded in the execution queue. Current code/data remain the implementation baseline.

## Basis, objective and decisions

Consumes the [integrated review](../design_review/reviews/design_review_declared-data-operations_2026-11-12.md)
and all4supporting pages at64dc6c3e6; the audit companion explains changes, not additional scope.
Product source8c0f4f951, diagnostic reconciliationf6ce5d086. Actual starting tree64dc6c3e6 was clean.
The NetworkX amendment consumes [its review](../plan_improvement_reviews/declared-data-operations-networkx_2026-11-12.md)
at `7c5368faa`. Operator authorization selects I01–I07 required portions and preserves conditional
capabilities with explicit triggers, not mandatory investigations. The Python-introspection amendment
consumes [its review](../plan_improvement_reviews/declared-data-operations-python-introspection_2026-11-12.md)
at `0907dcc23`; its source-qualified RC01–03 were explicitly accepted on 2026-11-12.
The [execution receipt](#ddo-0002-execution-receipt--2026-11-12) distinguishes implemented foundations
and actual checks from the remaining **Proposed** target. The
[DDO-03–05 checkpoint](#ddo-0305-partial-implementation-checkpoint--2026-11-13) records the integrated
implementation and remaining scope. Native candidate installation is exercised in isolated test
databases; no production deployment, activation or provider inference was run.
Apply core3.3/heuristics/code-intelligence1.4/test-assessment1.2/binding. No new broad diagnostic audit
is initiated by authoring. This coordinator is the single owner of scheduled finding/package state.

The target is a total explicit domain model governing supported products, subjects, operations,
input/output bindings, applicability, lifecycle/effects/outcomes, demand fulfillment, provenance,
reuse and change. Specialized algorithms implement its contracts. The PostgreSQL kernel remains
transactional authority; authoritative typed ports and generated physical/wire projections consume one
effective semantic definition compiled from its appropriate authored owner.
A semantic operation does not automatically create a task/process/table/transaction. Pure reads do
not schedule recomputation. Explicit selection and original evidence survive every physical lowering.

### Operator-confirmed rule changes ·2026-11-12

The operator explicitly accepted RC01–RC09 during plan preparation. Do not request confirmation again.
DDO-00 records the affected scoped target successors and updates D1–D8 before dependent production
cutover. ADR-0092–0095 establish those accepted target rules. The predecessor records still govern
selected legacy/archived consumers; full-record/reference retirement belongs to DDO-11 when those
actual consumers switch. This preserves their unrelated operational and custody decisions rather
than retiring them prematurely. Accepted predecessor bodies remain immutable.

| Review impact | Accepted direction and architectural route |
|---|---|
| RC01 | Runtime provenance/revocation, never reuse equality; supersede affected ADR0063 clause, D3/D6 |
| RC02 | Complete declared dependencies replace broad defaults; supersede affected ADR0060 scope, D4/D6 |
| RC03 | Compatible cross-release inputs with full custody/support/permissions; revise ADR0027 target through successor, D2/D3 |
| RC04 | Semantic product/member references plus explicit support selection; successors to affected ADR0081/82 identity, D1/D3 |
| RC05 | Native demand and fulfillment replace stage-run sequence/grouping; successors to affected ADR0084/90 clauses, D3/D6/D8 |
| RC06 | Fixed model-derived operation/binding/eligibility relations; extend ADR0033 through successor, D2/D3 |
| RC07 | Retain per-run materialization with exact consumed bindings/currentness; successor extending ADR0014, D5 |
| RC08 | Semantic inference recipe separated from full execution profile; successors to affected ADR0085/91 fingerprint meaning, D4; CUDA/dtype guarantees preserved |
| RC09 | Preservation-aware reference/custody cutover; successors to affected ADR0050/64/67 clauses, D3/D7/D8 |

### Python-introspection rule changes · accepted 2026-11-12

These are source-qualified impacts from review `0907dcc23`, distinct from original RC01–09.
Do not request confirmation again. DDO-00 integrates them into coherent architecture/ADR successors
before dependent production adoption; accepted historical records remain immutable.

| Review impact | Accepted direction and route |
|---|---|
| Python RC01 | Admit closed implementation-owned definitions beside externally authored operations into one effective model; D2/D4/D6 ownership and DDO-01 frontend contract |
| Python RC02 | Admit conservative normalized implementation-slice revisions as selected recipe determinants; preserve whole-runtime custody separately; DDO-00 integrates affected ADR0063/0060 successor wording, D2/D4/D5/D6 |
| Python RC03 | Use suitable authoritative typed Python ports directly; generate needed native/wire projections without duplicated signatures; D2/D3/D8 and DDO-03 correspondence |

## Combined target and authoring decisions

One OperationDefinitionRevision owns complete typed contracts and specialized profiles. The compiler
produces a ResultRecipeIdentity, binding/eligibility specification and admitted execution projection.
Kind contracts close over effective semantic definitions rather than the whole release or fields
current readers happen to inspect. Canonical graph encoding uses stable semantic references to avoid
release/recipe/product hash cycles. Definition revision and eligibility-only widening can change
without changing result meaning; changed analyzed scope/input/support cannot be hidden as provenance.

Semantic product identity is kind-contract+immutable subject/context+canonical semantic body.
Exact blobs, logical requests and authentic execution episodes remain separate. Role-qualified
value/population/support binding drives reuse; equal bytes alone cannot establish source identity,
trust or an independent evidence vote. Revocation retains products/history and invalidates the
relevant required support. Rebinding equivalent support is an explicit admitted fact, not a fake
new inference episode. Runtime artifacts and release-bound attestations remain independently named.

Native Demand/DemandUse owns requested scope, explicit selection and every obligation's fate.
Discovery publishes a closed/partial/empty population witness; typed relational bindings drive
sufficiency and the ready frontier. One logical request has one live fenced producer, while several
demands can share its result. Existing task leases/attempts are physical ownership, not a second
semantic scheduler. Exact completion intent and receipt distinguish uncertain commit from rollback;
uncertain physical submission retains authenticated ownership until bounded settlement/termination.

Current foundations include composed LinkML/execution contracts, generated calls/metadata, native
claim settlement, source custody, pinned products and scoped provider sessions. They are reused
where their guarantees fit. Name-based graphs, broad Reader/config identity, copied task reuse,
private selectors and task-keyed product meaning are replaced with their consumers, not wrapped as
an unchanged second authority. Existing source/evaluation separation and native protection remain
preservation requirements even where their representation changes substantially.

### Concrete mechanisms and execution fit

Use selected LinkML1.12.1 effective-schema APIs, Pydantic2.14.1 strict generated boundaries,
SQLAlchemy2.1.6 Core/fixed PostgreSQL18 relations and the existing Alembic1.20.1 migration owner.
Supporting plans name pivotal APIs/current source references. No dependency upgrade or workflow
engine is needed by this series. PostgreSQL uniqueness/row locks and generated publication calls
supply request coalescing and coherent visibility; old run-scoped locking alone is insufficient.

Prepare immutable effective contracts once. Resolve demand-scoped bindings through indexed set
queries, keep compact manifests through planning, hydrate bodies under coordinated capacity and
preserve provider batching/shared residency. Aggregate fan-in uses population closure, not repeated
whole-book scans. No global operation×subject table, all-path expansion, per-kind process or long
publication transaction follows from total modeling. This is a credible qualitative route for the
retained316-view/518-page book, skewed sections, cross-page groups and concurrent independent demands;
no numerical speed/capacity claim is made. A bounded refusal alone does not establish workload fit.


### NetworkX amendments and package dependencies

The [graph companion](declared-data-operations/graph-projections-and-analysis.md) owns faithful
projection families, selected NetworkX 3.7 APIs/source links, execution policy and complete feature
selection. Both authoring routes compile into the single effective semantic model; PostgreSQL remains transactional authority.
Replace compile-time-only wording with derived computations over effective declarations or pinned
runtime selections. This is a plan mechanism amendment, not a new rule change; RC01–09 remain accepted.

DDO-01–03 supply projection definitions, canonical typed records and pure topology kernels first.
DDO-04 supplies actual coherent native acquisition before runtime graph consumers integrate.
DDO-05/06 readiness still uses selected relational sufficiency and native claims, with no generation
barriers. DDO-08 repairs cycle-member versus downstream-blocked authored claims. DDO-09 distinguishes
potential impact from stale bindings and preserves substitution cutoffs. DDO-10 supplies bounded typed
member/path/SCC/boundary explanations and preserved matching; DDO-11 retains authenticated closure.
DDO-12 incorporates adopted cases into the same final union. These are additions to existing packages,
not new stages or DDO-13. Companion-level design agreement alone does not establish working prerequisites.

Graph snapshots preserve roles/order/multiplicity, source/selection/trust pins, isolates, original
witnesses and examined completeness. Canonical identities use typed semantic records, not graph class,
component numbers, insertion order or fingerprints of structural similarity. Core dispatch is explicit;
optional accelerators and analytics neither block core delivery nor become new required investigations.


### Implementation-owned contracts and recipe dependencies

The [implementation companion](declared-data-operations/implementation-contracts-and-fingerprints.md)
owns mixed authoring, closed source extraction, detailed selected APIs/sources and conservative
slice identity. Coupled Python definitions own their typed invocation plus colocated non-derivable
domain facts; external protocols retain declaration authority. Both produce the same immutable
effective operation IR with authored/extracted/inferred/modeled origins. No second editable registry.

DDO-01 acquires admitted source/stub/environment context and extracts effective facts with Griffe,
LibCST and supported Astroid refinement only where needed. DDO-02 compiles finite implementation
slices as explicit recipe determinants under qualified profiles. Successful inference alone does
not prove exhaustive targets; explicit boundaries or refusal handle unsupported dynamic behavior.
DDO-03 uses direct suitable typed ports and generates required native/wire correspondences. No
ambient import, provider execution or per-request source parsing follows from derivation.

Contract identity, implementation revision and exact runtime custody remain separate. In-slice
repairs/refactors can conservatively change recipes without a manual version increment; unrelated
runtime changes do not salt them. DDO-09 retains equal-value/support cutoff after requested
recomputation. DDO-10 derives documentation and comprehensive drift from effective records, not
Griffe breakages alone. ty navigation is conditional; pyrefly remains checker. DDO-07/08 retire
actual duplicated mappings/lists with consumers, while DDO-11 preserves archived interpretations.

## Reading and work-package ownership

| Supporting plan | Owns design detail |
|---|---|
| [Implementation contracts and fingerprints](declared-data-operations/implementation-contracts-and-fingerprints.md) | Shared Python/declaration authoring, extraction APIs, slice identities, derived contracts/drift and profile qualification |
| [Graph projections and analysis](declared-data-operations/graph-projections-and-analysis.md) | Shared projection/algorithm/lifecycle contracts across DDO-01–12; complete capability selection and conditional triggers |
| [Contracts and compilation](declared-data-operations/contracts-and-compilation.md) | DDO-01–03, semantic authority/IR, canonical identity and generated binding/port semantics |
| [Products and support](declared-data-operations/products-and-support.md) | DDO-04, native storage/admission, request/attempt/derivation/fulfillment/receipt protocol |
| [Demand planning and execution](declared-data-operations/demand-planning-and-execution.md) | DDO-05/06, discovery, readiness, scheduling, physical ownership/recovery |
| [Operations and adapter cutover](declared-data-operations/operations-and-adapter-cutover.md) | DDO-07/08, complete source/primary/downstream/external operation replacements |
| [Change, reuse and consolidation](declared-data-operations/change-reuse-and-consolidation.md) | DDO-09, common substitutability/currentness, revocation and cut materialization |
| [Interfaces and evaluation](declared-data-operations/interfaces-and-evaluation.md) | DDO-10, native/ci/MCP/export/replay and protected assessment |
| [Preservation/adoption/qualification](declared-data-operations/preservation-adoption-and-qualification.md) | DDO-00 preparation, DDO-11/12 preservation/cutover and final required union |

## Execution queue and readiness

DDO-00 is **complete at its scoped preparation boundary**. DDO-01/02 and DDO-03–05 are
**partially implemented**, with remaining source closure, scoped discovery, projection-definition
and retirement obligations (CA-01/05/06/07), as well as incomplete final qualification. The completion-audit table
below owns all five findings' current disposition, and [Audit repair execution](#audit-repair-execution--2026-11-13)
owns implementation and remaining acceptance. DDO-06–12 remain **open**. Execution is paused;
no automatic test restart or continuation is scheduled.
Rows describe dependencies, not mandatory stage-wide
barriers or separate agent assignments. Interface agreement permits design, not a claim of usable
native behavior. Product-family slices carry immediate consumers; no late consumer repair phase.

| Package | Prerequisite capability | Delivered behavior and completion boundary |
|---|---|---|
| DDO-00 | Accepted RC01–09 and current code/data | Durable decisions/owner updates, complete operation/consumer inventory and preservation root classification; no destructive action before concrete closure |
| DDO-01 | DDO-00 accepted mixed ownership | Both closed source/declaration frontends and one normalized operation/kind model; source/aggregate/effectful profiles represented |
| DDO-02 | DDO-01 effective IR | Versioned canonical kind/subject/product/recipe/binding and admitted implementation-slice identities, independent expected examples |
| DDO-03 | DDO-01/02 | Direct suitable typed invocation plus generated native/wire correspondence, fixed relational bindings and equivalent native/explanation semantics; no hidden selector authority |
| DDO-04 | DDO-01–03 implemented contracts | Native products/support/request/attempt/intent/fulfillment operations and purpose permissions work under real transactional controls |
| DDO-05 | DDO-03/04 | Native frozen demand, declared discovery/aggregate closure, explicit producer selection and dependency-derived frontier |
| DDO-06 | DDO-04 and DDO-05 resolved requests | Cross-demand coalescing, owned execution, fenced publication, exact uncertain replay, bounded drain and resume |
| DDO-07 | DDO-01–06 usable vertical primitives | Capture/recognition/source and primary providers publish new products with their immediate consumers migrated |
| DDO-08 | Same primitives + required DDO-07 products | Every downstream/structural/authored/external operation and effectful action realizes its declared profile; bypasses removed |
| DDO-09 | DDO-02–04; integration with DDO-05–08 | Complete declared reuse, support-aware revocation/impact and modeled consolidation; remove conservative old mechanisms only after replacement works |
| DDO-10 | DDO-04 selection; DDO-07–09 products | Pinned read/export/replay and protected assessment migrated together; no hidden inference or cross-snapshot meaning |
| DDO-11 | DDO-00 preserved closure + all target callers/native behavior | Coordinated forward adoption, disposable regeneration, verified source/reference custody and obsolete authority retirement |
| DDO-12 | Complete functional DDO-00–11/frozen source | Series-owned applicable functional/native/fault/provider/nonfunctional union and retained-book/consumer qualification covered |

DDO-09's admission/reuse contract design precedes first reuse-capable callers; the full package can
finish after their integrations. DDO-10 defines public selection needs alongside DDO-04/07.
DDO-11 preservation constraints apply from DDO-00 onward, not after storage is destroyed.
Independent family adapters may proceed once shared contracts and actual native prerequisites are
available. Shared compiler/physical/native files need explicit editing ownership despite logical
independence. The coordinator integrates contributions and reconciles revealed shared decisions.

The operator-accepted [test-system target](test-system-target-design_2026-11-13.md)
supplies the next native-test foundations: TS-05/06/17 precede new DDO-06 native tests.
DDO-06–12 consume TS-21 when retiring their respective mechanisms; DDO-12 also consumes
TS-22's discriminating evidence mapping and actual-provider outcomes in its own qualification
table. These are future dependency obligations, not claims that the test-system target is
implemented or prerequisites to the current DDO-03–05 corrections. DDO-06 owns retirement of
stage-run admission including `max_active_stage_runs`; DDO-09 owns removal of copied
`reused_task_id` meaning once its DDO-07/08/10 callers use semantic fulfillment, with DDO-11
performing final physical retirement. The contracts companion incorporates test-system RC03.

## Finding and recommendation disposition

Each multi-package finding remains **open**. DDO-00–02 contributions are recorded below; closure
requires the complete contributing package behavior, not acceptance or a foundation-only pass.
Preserve original source IDs; do not relabel prior plan findings.

| Source finding | Component/correction and package owner | Closure evidence |
|---|---|---|
| F01 | Composed operation authority and complete ports, DDO-01/03/07/08 | All supported operations map to owned contracts, no descriptor/selector second authority |
| F02 | Qualified sufficiency, DDO-03/05/10 | Actual supported cardinality/coverage/source cases explained and enforced |
| F03 | Declared dependencies, DDO-05–08 | New operation composition works without hidden name/order maps |
| F04 | Complete fine-grained declared reuse, DDO-02/09 | Unchanged admitted determinants/new custody reused; changed admitted slice yields new recipe with equal-output cutoff; relevant input/policy change not reused |
| F05 | Parameters/population/analyzed scope/input split, DDO-01–03/07/08 | Distinct analyzed scope cannot collide; independent subjects share recipe |
| F06 | Semantic products vs execution evidence, DDO-02/04/07/10 | Equal semantic body survives producer revision without merging occurrences/episodes |
| F07 | Uniform derivation/support/fulfillment, DDO-04/06/10 | Demand selection and original lineage observable including zero-output/reuse |
| F08 | Subject-relative change, DDO-09 | New/unseen subjects and actual downstream stop points independently checked |
| F09 | Modeled cut currentness, DDO-09 | Exact consumed bindings/policy and explicit target explain current/stale/unknown |
| F10 | Relational discovery/coverage binding, DDO-03/05 | Same-base, exact-one, two-distinct, optional/alternative and closed-population controls |
| F11 | Support-aware substitution/admission, DDO-04/09/10 | Scope mismatch and revoked required support refuse despite equal bytes/contracts |
| F12 | Definition/recipe/eligibility split and canonical closure, DDO-01/02/09 | Eligibility-only widening and semantic changes have independently expected propagation |
| F13 | Demand fate/population and request fulfillment, DDO-04–06/09 | Shared requests, discovery additions/deletions and every obligation's fate survive resume |
| F14 | Preservation/build adoption, DDO-00/06/11 | Original/reference/evidence closure and exact fenced PDF adoption retained |

C1 maps to DDO-02/04/09 and every migrated producer, C2 to DDO-01–03/07/08, C3 to DDO-04/07/10/11,
C4 to DDO-03/05/06, C5 to DDO-04/09/10, C6 to DDO-09/10 and C7 to DDO-09/10.
Embedded obligations are carried explicitly: population versus analyzed scope; complete canonical
semantic closure; profile split; no-product/multi-output effects; original source/coverage/choices;
explicit replicate/retry/revocation; cross-demand ownership; uncertain completion; PDF custody;
authored/external work; zero-output reporting; protected assessment and full pinned evidence closure.
Review §7 scenarios belong to DDO-02/05/06/09/10/12 as detailed by their independent checks.


### NetworkX review disposition · 2026-11-12

Source-qualified IDs below refer to the NetworkX review at `7c5368faa`, not new diagnostic findings.
All recommendations remain **open at series scope**; pure foundation contributions are recorded
in the execution receipt. Conditional subfeatures retain their source judgments
and triggers in the graph companion; mentioning them does not schedule execution or qualification.

| Source recommendation | Selected correction and package owners | Closure evidence |
|---|---|---|
| [NetworkX I01](../plan_improvement_reviews/declared-data-operations-networkx_2026-11-12.md#I01) | Typed snapshot projection families and faithful representation, DDO-01–04/09/10 | Independent roles/multiplicity/isolate/endpoint/canonical and coherent snapshot checks |
| [NetworkX I02](../plan_improvement_reviews/declared-data-operations-networkx_2026-11-12.md#I02) | Shared authenticated topology/closure kernels, DDO-02/05/09–11 | Exact root-inclusive memberships, all required edges, missing/partial scope and custody |
| [NetworkX I03](../plan_improvement_reviews/declared-data-operations-networkx_2026-11-12.md#I03) | Potential versus bound graphs, SCC diagnostics/nonbarrier readiness, DDO-01/02/05/06/08/09/10 | Cycle member versus blocked tail; unselected alternative; B admits C while unrelated A runs |
| [NetworkX I04](../plan_improvement_reviews/declared-data-operations-networkx_2026-11-12.md#I04) | Preserve explicit rooted attributed comparison modes and mappings, DDO-02/08/10/12 | Independent multiplicity/shared-binder/asymmetric-field/joint-choice matching outcomes |
| [NetworkX I05](../plan_improvement_reviews/declared-data-operations-networkx_2026-11-12.md#I05) | Typed paths/member/SCC/boundary inspection and faithful containment, DDO-05/09–11 | Exact witness/source hierarchy and pinned partial scope; optional advanced summaries remain conditional |
| [NetworkX I06](../plan_improvement_reviews/declared-data-operations-networkx_2026-11-12.md#I06) | Explicit core backend, ownership/cache and conversion contracts, DDO-03/06/09/10 | Adopted-call dispatch/refusal, immutable lifetime and actual numeric/index fidelity checks |
| [NetworkX I07](../plan_improvement_reviews/declared-data-operations-networkx_2026-11-12.md#I07) | Independent topology fixtures and existing public qualification, DDO-01–12 | Independently expected semantics and adopted native/ci/MCP/export cases in final union |


### Python-introspection review disposition · 2026-11-12

All recommendations remain **open at series scope**; implemented foundation contributions are
recorded in the execution receipt. IDs below refer to review `0907dcc23`, not
NetworkX recommendations. Conditional catalogue entries are not scheduled investigations or required
qualification unless selected for a concrete consumer. The shared companion owns their technical detail.

| Source recommendation | Package responsibility | Closure evidence |
|---|---|---|
| [Python I01](../plan_improvement_reviews/declared-data-operations-python-introspection_2026-11-12.md#I01) | DDO-00/01/03/07/08 mixed ownership and author-once definitions | Actual simple/inherited operations yield effective contracts/invocation without duplicate authoring |
| [Python I02](../plan_improvement_reviews/declared-data-operations-python-introspection_2026-11-12.md#I02) | DDO-01–03/07/08/10 closed source facts/resolution | Independent origins, alias/metadata completeness, supported coverage and cache isolation |
| [Python I03](../plan_improvement_reviews/declared-data-operations-python-introspection_2026-11-12.md#I03) | DDO-01/02/09 admitted implementation-slice recipe dependency | Independent source-change matrix, unknown refusal, opaque boundaries and equal-value cutoff |
| [Python I04](../plan_improvement_reviews/declared-data-operations-python-introspection_2026-11-12.md#I04) | DDO-03/08/10 direct ports, derived docs/full drift | Nominal/native correspondence and explicit extension metadata retained; breakages not equality |
| [Python I05](../plan_improvement_reviews/declared-data-operations-python-introspection_2026-11-12.md#I05) | DDO-00/01/03/07/08/11 consumer migration/removal | Duplicate signature/owner/version/dependency lists retired with real consumers; custody preserved |
| [Python I06](../plan_improvement_reviews/declared-data-operations-python-introspection_2026-11-12.md#I06) | DDO-03/10/12 checker/public tooling boundary | pyrefly obligations preserved; any adopted ty inspection negotiates public supported API |
| [Python I07](../plan_improvement_reviews/declared-data-operations-python-introspection_2026-11-12.md#I07) | DDO-01–12 preparation/profile/lifecycle qualification | Independent effective facts/slices, archived interpretation and adopted native/provider/consumer union |

## DDO-00–02 execution receipt · 2026-11-12

Implementation baseline `31427a080383fad70c73b98851ad8f312cdb8429`; the earlier product design
baseline remains `8c0f4f951`. This increment supplies unused target preparation/identity foundations.
Current selected native ABI, producers, task reuse and archived interpretations retain their
original contracts until their owning cutover packages replace the actual consumers.

- **DDO-00:** accepted scoped target ADR-0092–0095 and D1–D8 owner updates; the
  [operation/consumer reconciliation](../design_review/evidence/2026-11-12_ddo-operation-inventory/consumer-reconciliation.md)
  accounts for 101 declared protocol operations, both repository registries (34 phase0 / 17 M1),
  all three local pack configurations, inherited dispatch, six descriptor selectors, explicit
  interpretation authoring and immediate publisher/read consumers. New record
  `ddo.operation-consumer-reconciliation` passes this bounded metadata inquiry; the original
  partial record remains unchanged. Unconfigured external plugins are not an asserted population.
- **DDO-00 preservation:** the [root census and follow-up](../design_review/evidence/2026-11-12_ddo-preservation-closure/README.md)
  retain exact acquired database identity/revision, 58 metadata projections and 357 FKs.
  All 41,949 artifact links and 3,726 selected source/input product links resolve. The follow-up
  classifies all 417 pending manifests preserve-sealed and all 73 historical ID occurrences as
  retained provenance within their original scope. There is no discovered missing required root
  or remaining metadata-classification blocker in that declared universe. DDO-11 still reacquires
  and freezes the actual target, verifies bytes/readers/recovery, fences writers and resolves
  actual correspondence before adoption. The old unsettled `0a78…` result remains protected.
- **DDO-01:** frozen effective kind/operation/binding/source/identity products and one shared
  pre-hash `effective_class_definitions` phase; closed declaration and captured Python frontends.
  Griffe owns callable/declaration/C3 facts, LibCST owns lexical/normalized source facts, and
  preparation-local Astroid structural bindings refine source aliases without inference,
  transforms, runtime bootstrap or ambient import discovery. Typed binding fields/literals,
  complete conditional/policy/vocabulary facts, duplicate identities, unsupported dispatch,
  mutable/global/alias cycles and unmodeled transformations receive explicit refusal/unknowns.
  Explicit target manifests archive effective products and reopen pinned version1 products
  without consulting current source; mixed legacy/target admission inputs refuse.
- **DDO-02:** versioned typed canonical values, root-inclusive finite semantic graphs and
  independent kind/definition/recipe/eligibility/slice/subject/body/product identities. Compiled
  role policies drive request/admission projections including exact versus substitutable support,
  required episodes/providers/alternatives, analyzed scope, population witnesses and replicates.
  Unknown required kind/slice closure withholds reusable identity. Runtime artifact identity is
  separate from release-bound attestation; the actual unbound runtime cache consumer uses it.
  PostgreSQL parity covers framing of already normalized tagged values in rollback-only temporary
  helpers, not native normalization, product admission or a new installed ABI.
- **Actual provider projections:** `NativeProfile.identity_projections` reads positive identity
  roles from its actual typed constructor and nested `GlinerProfile` declarations. Explicit
  supplied released authentic-observation policy qualifies D1/GLiNER, separating runtime/threads/
  refusal bounds from semantic model/options/device/dtype/math policy. Missing/unsupported provider
  policy refuses; no installed fallback qualifies the other providers. Shared GLiNER validation
  rejects historical CPU/unknown nested profiles under CUDA; artifact-map reordering preserves
  target identities. Existing wire/defaults/fingerprints remain exact. DDO-07/09 owns actual
  request/reuse adoption; the foundation does not claim broad runtime salts have already disappeared
  from selected production stage keys.

**Real-source qualification boundary:** the existing `semantic.identity.claim_source_item` now
owns its colocated typed/domain contract and supplies a successful captured-source recipe case.
Actual operation-event scoring and the inherited authored-interpretation family supply real
effective fields, supplying/exposed ownership, callable shapes and origins, with explicit unknown
dependencies and no reusable recipe when their framework/context closure is unavailable. Closed
inherited/alias profiles have separate independent controls. This does not claim that the inherited
production pipeline is reusable or fully admitted. Its Pydantic/generated behavior and selected
reader/context/output bindings must receive supported complete profiles before DDO-03/07/08
adoption; missing capture or interpretation cannot become an identity fallback. Optional general
framework inference remains conditional, not a new universal Python modeling project.

**Tested · 2026-11-12 local / 13 UTC:** the final 18-path union passed **436 selected / 436 passed**,
managed `9d485175a11e44018135cf84b59c7a29`. Its exact receipt is
[retained durably](../design_review/evidence/2026-11-13_cli-9d485175a11e44018135cf84b59c7a29/README.md)
under record `cli.9d485175a11e44018135cf84b59c7a29`. The named opt-in actual GLiNER diagnostic
was excluded because provider execution is outside this foundation qualification. This union
covers the new compiler/identity/source/profile cases, actual rollback-only PostgreSQL framing and
existing preparation/contracts/archive/runtime/value/call/interpretation/GLiNER/host regressions:

```sh
uv run ci test --json -- \
  python/corpus-structure/tests/semantic/test_data_operation_compilation.py \
  python/corpus-structure/tests/semantic/test_data_operation_identity.py \
  python/corpus-structure/tests/semantic/test_data_operation_identity_native.py \
  python/corpus-structure/tests/semantic/test_prepare.py \
  python/corpus-structure/tests/semantic/test_contracts.py \
  python/corpus-structure/tests/semantic/test_execution_release.py \
  python/corpus-structure/tests/semantic/test_release_compatibility.py \
  python/corpus-structure/tests/semantic/test_release_wire_payload.py \
  python/corpus-structure/tests/semantic/test_runtime_identity.py \
  python/corpus-structure/tests/semantic/test_analysis_contracts.py \
  python/corpus-structure/tests/semantic/test_value_codec.py \
  python/corpus-structure/tests/semantic/test_identity_vectors.py \
  python/corpus-structure/tests/semantic/test_operation_call_generation.py \
  python/corpus-structure/tests/semantic/test_interpretations.py \
  python/corpus-structure/tests/methods/test_native_profile_identities.py \
  python/corpus-structure/tests/methods/test_native_host.py \
  python/corpus-structure/tests/methods/test_gliner.py \
  python/corpus-structure/tests/methods/test_pm2_gliner_classification.py \
  -k 'not native_boundary_diagnostic_observes_and_rescores_exact_occurrence'
```

Final `uv run ci check --only types --json` passed `1b8c525eba5b41c2913a867ab6b19f4f`;
`--only lint` passed `cf5aabe7d74744cc8712ee9fb7c2ef21`; `--only deps` passed
`8003758619af4e119fe238957f7dd217`. `uv run ci doctor --json` passed
`a2d46c5105b34811b9d768231877fbd7` after dependency placement. Final source was formatted before
this union; commits `0de179fc7` / `d1c25aa4a` preserve those tested source/test bytes. Independent
read-only implementation review found no remaining material finding within the bounded compiler
and selected D1/GLiNER projection scope; reviewer tests were not_run. Existing 221-case and
intermediate focused passes retain their original scope, not an additional qualification claim.
Initial typing failure `47eed05be9e044ffaea1cfd0599c56ee` and transient visitor failures
`1b6dc49e7a3f428fba594413ce48b010` / `cba8775412fe4becae6b8c415d114055` remain recorded;
the owning repairs and affected cases are included in the final passing union.

`uv run ci docs check --json` passed `2c36be942c6b4dac9c920a0ea4dfc52e` (948 canonical pages,
zero link errors; existing phase0 descriptor-tag warnings). `uv run ci evidence check --json`
passed `df6182ace4a14d71ba25685c68920458` (402 records / 217 folders, zero errors and 42 existing
historical warnings). Root `just turn-end` passed; subsequent receipt-only documentation additions
do not alter qualified source/test bytes. Broad `uv run ci test` / `uv run ci check`,
provider execution, book processing, permanent database writes/migration, activation and protected
answer reads are **not_run** for this increment. DDO-12 remains the assembled final qualification
owner; passing this foundation does not qualify the redesigned production pipeline.

## DDO-03–05 partial implementation checkpoint · 2026-11-13

**Historical incremental account; current execution is recorded under [Audit repair execution](#audit-repair-execution--2026-11-13).**
The following receipts retain their original source and scope; their then-open obligations do not
override that current account. The earlier foundation worktrees were merged
and removed. Current execution has three active isolated implementation worktrees; their source
and retained receipts are integrating on main. This checkpoint does not change the accepted
target or close multi-package findings from source reviews.

### Integrated capability and present boundary

- **DDO-03:** the versioned effective model carries typed operands, literal/parameter/population
  facts, kind-universe/projection-family policies and selected versus potential dependencies.
  `data_operation_bindings.py` lowers the admitted form through SQLAlchemy Core and produces one
  immutable binding/explanation result. `data_operation_binding_native.py` and its captured SQL
  enforce that same archived binding AST at native attach/publication boundaries. Literal/range/
  membership, optional input, alternatives and closed-population predicates retain explicit
  unknown/refusal states. Unsupported nested aggregate/choice under absence refuses.
- Direct original-callable ports use captured source, exact runtime alias/global correspondence,
  nominal JSON/Python ingress, defaults and immutable results. Their currently admitted invocation
  profiles include **scalar pure, original tuple-native batch, closed plain receivers and
  explicit atomic mapping outputs**; this does not admit arbitrary adapter profiles. The actual `claim_source_item` is covered by direct-port checks;
  this is not admission of every production adapter. Necessary native/wire calls, nominal IDs and
  closed Draft7 schemas are generated from one captured fixed protocol through the existing shared
  renderer. Generic JSONSchema local nominal references outside the owned wire namespace refuse
  rather than acquiring an invented kind identity.
- **DDO-04:** fixed physical declarations and captured native SQL supply demand/request/product/
  member/support/population/read/intent/derivation relations, guarded calls and purpose grants.
  Existing task/attempt/lease ownership is reused. Native checks authenticate typed canonical
  bodies, nominal container/member contracts and explicit member context; family projections are
  governed by the **member** kind. Local endpoints explicitly name local scope without a product
  self-hash cycle. Unbacked artifact hashes and unsupported provider identity profiles refuse.
- Exact retained intent/adoption/publication distinguishes producer attribution, current fenced
  publisher and committed replay. Append-only revocation and authenticated support rebinding
  preserve historical evidence. Pinned native reads carry an immutable transaction visibility cut
  and continuation; frontier reads defer full bodies. These are tested bounded primitives;
  the remaining package obligations below and production adoption are not complete.
- Explicit target preparation archives manifest, effective model, source closure, generated ports/
  schemas, native definitions and runtime inputs. Release/archive/runtime-binding paths recognize
  this explicit target separately from selected legacy inputs; normal target admission checks the
  actual frozen native catalog. Forward revision `semantic_ddo_kernel_v1` is now registered;
  targeted native tests use the real frozen migration and normal `admit_data_operation_release` catalog admission. The earlier
  test-only acquired-candidate bypass was removed. The persistent development database remains at
  `semantic_bep_located_v2`; deployment and activation were not performed.
- **DDO-05:** frozen demands retain roots, explicit producer/discovery selections, dependency
  closure, parameters including exact tagged meaning, inference/execution profiles and replicates.
  `DemandPlanner` registers/expands/resumes native obligations and performs bounded Core binding
  selection against pinned source/subject scope, retaining native attachment and common binding
  results. Population receipt/support identity is distinct from stable semantic membership.
  This is a planner foundation, not the migrated production book driver or DDO-06 execution owner.
- Legacy generated calls were regenerated from the current trusted physical contract after task
  nullability changed. Their public legacy result fields stay required and use explicit native-row
  refusal for missing legacy fields. Selected legacy producers/readers remain until their actual
  coordinated replacement; this regeneration is not production migration or activation.

### DDO-03/06 execution increment · 2026-11-13

**Implemented foundations; integrated native qualification in progress. Execution continues.**
DDO-03–05 and DDO-06 remain partial/open; DDO-07 remains open. This checkpoint does not end
execution of the approved remaining DDO-03–05, DDO-06 and DDO-07 scope.

- Direct ports now support exact closed receivers, original tuple-native batch calls and
  atomic typed-mapping output bundles. The acquired execution boundary retains original
  source names separately from explicit runtime locations, validates exact native/runtime
  correspondence and carries canonical typed output meaning. Generated records, streams and effects still need their concrete applicable profiles. Prepared
  formal and learned spaCy capabilities now have explicit acquired profiles; their actual native
  publication and subsequent family consumers remain in qualification/integration.
- Four actual colocated consumer contracts cover shared-document source views, optional
  exact-one M1 projection, distinct structural passage/reading associations and retained
  contextual occurrences. Explicit subject fields preserve member identity. Frozen source
  sets preserve exact foreign product/member/source/reference custody. Requested-ID coverage
  is explicit. Closed membership is qualified by its product, preventing local-ID collisions.
- Native cancellation detaches demand interest, preserves shared work and increments an
  orphaned generation's fence; a later demand cannot revive that old attempt. Read-derived
  populations retain exact obligation/filter/parameter/producer context and complete/partial
  standing. The planner consumes them only through a fresh pinned read, refuses ambiguous
  parents and exposes reuse/selection progress. Managed `ci demands create/read/cancel`
  routes delegate to the same native service.
- The runless execution owner connects admitted source calls to native claims, separate
  intent retention/publication, exact reconciliation, bounded hydration and physical work.
  It scans pinned continuation pages and replenishes from fresh native sweeps. Dynamic
  claim admission and injected native renewal preserve independent uncertain-claim custody.
  Prepared plans share one schema-free CPU owner, predeclared native host group and transferable
  byte reservation. Exact typed renewal loss affects one claim; known-retired infrastructure failures
  retain immutable native attempt records. Bounded failure results retain successful sibling receipts
  and distinguish their total count from the displayed subset. Generic pure-call CPU dispatch and
  actual callable-to-publication/exceptional-exit controls remain in qualification; source alone is
  not verified closure.
- The first native source/publication qualification failed 39/62 cases, with 23 passes,
  `2031b6142f4d4f61b8f30a746b80eb8c`. Thirty-four failures share a request-attachment
  SQL alias ambiguity, four expose a fixture's overbroad request construction and one
  exposes a scalar/collection declaration mismatch. The receipt is retained; source fixes
  and the combined follow-up successor must be tested before any native closure claim.
- Original-source handoff requires typed factual support, rather than a synthetic computational
  derivation. [ADR-0096](../adr/0096-original-source-admission.md) accepts the target detail;
  existing document/native/cut/view custody and frozen selectors authenticate the source. The
  generic source receipt, separately typed support/trust/revocation branch and exact-scope binding
  projection are integrated in source; admission never fabricates a computational episode. Their
  native source-to-publication/revocation control awaits the combined successor. Pending/expired
  request invalidation now considers current support/runtime before any intent exists, preserving
  active leases and historical generations. These remain active DDO-03/04/05/07 obligations until
  actual native qualification, rather than closing on DTO/provider tests.
- Host/provider replies now retain original host-generation/request/profile/digests and
  logical-member correspondence. The common captured execution envelope retains actual CPU process/native-thread facts and
  provider receipts separately from product meaning. Native envelope publication remains open.
  Formal and learned spaCy target families share the original-source model and exact nominal
  four-field member packets. The spaCy product retains available language columns from the same
  inference; a separate declared canonical-sentence projection excludes native-label-only changes
  from canonical downstream input identity. Actual CUDA profile controls passed 67/67,
  `8bf9402cc7a7458281a5a1fcc6e4df78`, with retained source/context. Full ancestry/table context
  is integrated. Independent HanLP, constructions/context/composition and the other DDO-07
  families remain active.

- **Continuing execution · 2026-11-13.** The scalar CPU path and prepared kernels share the
  actual owned CPU process scope, including cooperative cancellation. Native callback concurrency
  uses its configured provider limit independently of CPU worker count. Reversible NLP residency
  drains real host generations before a PDF GPU borrower and allows later generations; unproven
  PDF retirement cannot be cleared by successful NLP teardown. Actual process/capacity handoff
  controls **passed 2/2**, `801e7e0c939c4014a4edea45aaa13871`; byte-credit controls **passed 2/2**,
  `15940a8fe8e14ff5bc894b7c30583bc9`. Neither establishes complete GPU/provider qualification.
- Native admission projection now preserves the exact archived role representation, including
  modern default support origins; historical v1 keeps its original omission. Actual isolated
  execution exposed the omission (`612d252855234670a3200e9a470efd69`) after a callable fixture's
  nominal integer mismatch was corrected. These are retained failures, not native closure.
- Complete original-source target publication also exposed a whole-archive JSONB transport object
  exceeding PostgreSQL's aggregate limit (`7aec18be673345d1b3804674864fc53e`). The model remains
  complete. [ADR-0098](../adr/0098-typed-release-archive.md) owns model-declared binary COPY staging
  and atomic native finalization; the existing durable archive and reader meaning are preserved.
  The [combined successor](../design_review/evidence/2026-11-13_ddo-archive-composition/README.md)
  owns normal authoring and affected native retesting. Generated call/column outputs were derived
  through their actual owning generators; model-change preview owns the canonical model outputs,
  not those separate call wrappers.
- [ADR-0097](../adr/0097-ddo-native-composition.md) supplies concrete nominal input refinement
  from captured inheritance and owned identifier paths such as `/source/document`. Queries,
  request identities and native population selection retain actual concrete kind contracts.
  Pure binding/identity/source/consumer union **passed 78/78**, `e01d3b0e4212488b9417349bbe5dbf1f`;
  nested owned-path controls **passed 6/6**, `fdf1c487d0574f1e8769ae91456dd63a`. Native refusal and
  actual heterogeneous multi-source composition remain open.
- Learned native spaCy columns and cheap canonical token/sentence products now have separate
  nominal member contracts. Normalized family coverage remains distinct from native block/column
  availability. The acquired CUDA/spawned canonical CPU union **passed 20/20**,
  `1e17a92561984ec894654aa577290276`. The common prepared verifier checks the expected qualified
  callable owner before code/source correspondence; substituted functions cannot authenticate
  against themselves. Source profiling reuses one interval/layout algorithm in its target and
  existing immediate consumer. These integrations do not close all DDO-07 families.
- [ADR-0099](../adr/0099-runless-pdf-source-ownership.md) accepts actual raw-asset factual support,
  genuine runless PDF claim context and sealed publisher custody separate from later admission.
  Typed original-asset/context foundations and the completion envelope are integrated in source.
  Native retention/publication must validate actual sealed PDF proof using the original intent
  producer fence on adoption. The PDF-domain contract facet, actual raw-source-to-capture pipeline,
  recognition and source discovery remain active; no legacy execution model or run is fabricated.

Frozen `semantic_ddo_original_v1` follows `semantic_ddo_population_v1` through the normal
rollback-only chain; [authoring custody](../design_review/evidence/2026-11-13_ddo-original-source-and-execution/README.md).
The persistent database remains at `semantic_bep_located_v2`, unchanged until DDO-11.
Candidate registration is not adoption, and later source changes require fresh adoption custody.

Bounded checks **passed**: 33 source-port/runtime cases, root receipt
`71134795644b4381911e4180b17b1793`; 52 port/demand/consumer/source-set cases,
`0e8a7c76606449eeaf858641294ba77f`; 122 ClassVar/acquisition cases,
`4116b0d1cc1a44e3936aff7f99e21c8a`; 41 Python/PostgreSQL product-local population cases,
`dbe5a22e71eb49f883efbd0a6d8f1339`; five CLI routing cases,
`71480333f47f4d9cbae7b124d1aaec32`. Receipts are retained with their original source/context.
Integrated Pyrefly **passed** `b857ccb5dcb84c3ca0f26f195235428d` before the subsequent CLI/context
merges; those changes receive their affected checks. Failed/intermediate receipts are preserved.
The integrated wire/original-support/demand/formal selection **passed 81/81**,
`d1ebcf88a5ca47db8ac6848c84d374c9`, using `uv run ci test --workers 2 --json --` with
`test_data_operation_wire.py`, `test_data_operation_original_support.py`,
`test_data_operation_demands.py` and `test_formal_products.py`. Physical owner/evidence controls
**passed 55/55**, `c1cbfa4e9a0e41769eab8843ed2b0a1f`; explicit retirement-uncertainty control
**passed 1/1**, `22674cb4c2d04575bfb1e62ac63c5fb1`. Each is targeted native-process or functional
evidence for its stated boundary, not complete DDO-06/07 qualification. Pyrefly **passed**
`9dac405c780d4ccc8473601c28c9b34c`; Ruff **passed** `0948567ba4ff43e781722e5f24482599`,
before subsequent worker merges. Reassess affected checks after integration.

Full provider/book/series qualification remains **not_run**, with functional scope still open.

### Remaining functional scope and next execution

These are concrete unfinished obligations, not merely a request to run a final test suite:

**Execution resumed · 2026-11-13.** The operator approved execution of all remaining scope,
including DDO-12. Preserve the persistent database until coordinated DDO-11 cutover; native
successors are authored by temporarily replaying the registered forward chain in a rollback-only
transaction. Registration and isolated native tests do not deploy that chain to the working database.
The prior 442-case receipt retains its original source and scope.

Current increments retain the sufficient binding through the ready-to-port handoff, apply frozen
semantic parameters to the original callable, refuse stale definition/eligibility bindings, expose
native compute/reconcile disposition and retain exact request/generation completion observations
separately from the pinned frontier. Explicit core NetworkX dispatch now also covers demand closure.
Closed source profiles can opt into Griffe postcollection dataclass/TypedDict enrichment; their
selection is archived, generated constructor/default-factory/type facts remain modeled, and actual
Python signatures remain distinct from expanded wire boundaries. Bounded plain receivers and tuple-native batch invocation are implemented. Runtime generated-constructor,
resource/stream/effectful capability admission and actual consumer qualification remain unfinished.

Invalid retained-intent recovery now has a native source implementation: validated replacement
bindings can advance a pending/expired generation while preserving the old intent and task;
an active lease refuses takeover. Fencing does not establish physical child retirement. The frozen
`semantic_ddo_recovery_v1` successor is registered and its scoped native controls pass; integrated
consumer qualification is required before this obligation can close. The [authoring receipt](../design_review/evidence/2026-11-13_ddo-intent-recovery/README.md)
records exact artifacts, pending-chain rollback and the unchanged persistent database.

New worker-local test reports were removed with worktree cleanup before durable retention. Their
reported results are not accepted as durable qualification evidence. Root receipt
`ba0f1c0e4370468c934da63ce2e16df3` (170/171 passed, one corrected deployment expectation) is
[retained](../design_review/evidence/2026-11-13_cli-ba0f1c0e4370468c934da63ce2e16df3/README.md),
and root qualification supplies the accepted replacement scope.

1. **DDO-03:** close the required adapter-capability profiles against real immediate consumers.
   Bounded tuple-native batch, plain receivers and explicit atomic mapping outputs are implemented;
   stream, preparation/resource ownership, effectful and generated-constructor forms still need
   their suitable adapters and conformance checks before use. DDO-CA-03 tracks the batch-loss seam. Complete the real consumer
   forms named in contracts/demand plans (shared-base source views, exact selected projection,
   distinct passages/readings and retained occurrence population), native/explanation parity and
   typed nominal member-family integration. Preserve unsupported-profile refusal in the meantime.
2. **DDO-04:** deploy the already registered forward revision only at the authorized adoption
   boundary, reacquiring its target/predecessor and exact source/release bindings. Normal frozen
   catalog admission is tested in isolated databases; the actual captured-source execution/publication
   vertical journey remains. Production adoption effects still require DDO-11 preservation/cutover custody.
   Finish **invalidated retained-intent generation recovery** across real support-substitution
   consumers: native runtime-invalidation generation/active-lease controls now pass, while
   invalidated upstream support with an admitted equivalent replacement and DDO-06 physical
   retirement still require integrated consumer qualification.
   Do not permit a replacement answer in the old generation or rewrite original producer evidence.
3. **DDO-05:** qualify actual discovery expansion, closed aggregate fan-in, explicit producer
   alternatives and dependency-derived frontier with the native implementation and real consumer
   shapes, including resume/continuation and typed downstream handoff. A frozen Python declaration
   or synthetic planner storage double alone does not establish these native journeys.
4. Keep DDO-06 execution ownership/drain and native stream item/terminal-to-completion mapping,
   DDO-07 staged artifacts/provider identity, DDO-08 remaining
   adapters/effects, DDO-09/10 independent-strength grouping and selected reuse/read policy,
   DDO-11 adoption/retirement and DDO-12 assembled qualification with their existing owners.
   Refused generic-schema/member or provider features need admission before a dependent consumer;
   no implicit fallback supplies them. No package or source-review finding is closed by these
   foundations alone.

### Resumed execution verification · 2026-11-13

**Tested:** the final frozen-head native union **passed, 61/61**, managed
`780320d32c3f4cb7a519230f4b322045`. It covers the registered recovery successor, runtime-invalidated
retained-intent generation replacement, active-lease refusal, immutable historical inspection,
stale producer fencing, binding/identity controls and acquired-start chained deployment recovery.

```sh
uv run ci test --workers 2 --json -- \
  python/corpus-structure/tests/semantic/test_data_operation_storage.py \
  python/corpus-structure/tests/semantic/test_data_operation_binding_native.py \
  python/corpus-structure/tests/semantic/test_data_operation_identity_native.py \
  python/corpus-structure/tests/semantic/test_model_deployment.py \
  python/corpus-structure/tests/semantic/test_migration_chain.py \
  python/corpus-structure/tests/semantic/test_native_candidate_cli.py
```

The [durable native receipt](../design_review/evidence/2026-11-13_cli-780320d32c3f4cb7a519230f4b322045/README.md)
retains exact scope/source. The earlier five-path source/preparation/port/demand union passed
121/121 (`21cc20694c554d8aa4308f4e402c7498`,
[receipt](../design_review/evidence/2026-11-13_cli-21cc20694c554d8aa4308f4e402c7498/README.md)); subsequent
changes include formatting and native authoring repairs. These are bounded results, not DDO-12.
The ten-path intermediate run passed 170/171; its corrected acquired-start assertion is covered
by the final native union. No claim of a final all-series union follows.

`uv run ci check --only types --json` **passed** `9e1e3818cdd1456e85673920ba817e2b`;
`uv run ci check --only lint --json` **passed** `548f68db067f4d6dbeda980f69d455f9`.
`uv run ci db status --maintenance --json` confirms the persistent working database remains at
`semantic_bep_located_v2`, with repository head `semantic_ddo_recovery_v1`.
Final `uv run ci docs check --json` **passed** `cfa6a73093e043c78b2e9f0883742f44`
(959 canonical pages, zero link errors). `uv run ci evidence check --json` **passed**
`69e35f78aebc49ed807f8a3cf5abc9a0` (zero errors, 42 historical warnings; subsequent native
receipt retained through the same owner). Root `just turn-end` passed with no source changes.
Only isolated qualification databases installed the successor. All worker edits are merged,
conflicts reconciled, and implementation worktrees/branches removed. Operator reference edits
remain untouched. DDO-03–05 and every multi-package finding remain open at the stated consumer
boundaries; DDO-06–12 remain open, including all final provider/book/fault qualification.

### Closeout verification

**Tested · 2026-11-13:** final targeted union **passed, 442 selected / 442 passed**,
managed `e332a3ef0884454988beaad5af1166b7`. Its
[durable receipt](../design_review/evidence/2026-11-13_cli-e332a3ef0884454988beaad5af1166b7/README.md)
preserves the exact selection, actual six-worker context, reports and source observations. No
provider execution is selected. This is the closeout union for this partial implementation, not
DDO-12 qualification or a claim that all DDO-03–05 functional scope is complete.

```sh
uv run ci test --workers 6 --json -- \
  python/corpus-structure/tests/semantic/test_data_operation_compilation.py \
  python/corpus-structure/tests/semantic/test_data_operation_identity.py \
  python/corpus-structure/tests/semantic/test_data_operation_identity_native.py \
  python/corpus-structure/tests/semantic/test_data_operation_bindings.py \
  python/corpus-structure/tests/semantic/test_data_operation_binding_native.py \
  python/corpus-structure/tests/semantic/test_data_operation_ports.py \
  python/corpus-structure/tests/semantic/test_data_operation_artifacts.py \
  python/corpus-structure/tests/semantic/test_data_operation_wire.py \
  python/corpus-structure/tests/semantic/test_data_operation_member_contracts.py \
  python/corpus-structure/tests/semantic/test_data_operation_preparation.py \
  python/corpus-structure/tests/semantic/test_data_operation_runtime.py \
  python/corpus-structure/tests/semantic/test_data_operation_demands.py \
  python/corpus-structure/tests/semantic/test_data_operation_storage.py \
  python/corpus-structure/tests/semantic/test_operation_call_generation.py \
  python/corpus-structure/tests/schema/test_model_change_preview.py \
  python/corpus-structure/tests/semantic/test_model_deployment.py \
  python/corpus-structure/tests/semantic/test_archive_reader.py \
  python/corpus-structure/tests/semantic/test_archive_wire.py \
  python/corpus-structure/tests/semantic/test_runtime_bindings_native.py \
  python/corpus-structure/tests/semantic/test_core_operation_calls.py \
  python/corpus-structure/tests/semantic/test_operations.py \
  python/corpus-structure/tests/semantic/test_domain_operations.py \
  python/corpus-structure/tests/semantic/test_consolidation.py \
  python/corpus-structure/tests/semantic/test_statement_anchors.py \
  python/corpus-structure/tests/semantic/test_source_frame_admission.py \
  python/corpus-structure/tests/semantic/test_proposals.py \
  python/corpus-structure/tests/intervene/test_automated_receipts.py \
  python/corpus-structure/tests/semantic/test_native_candidate_cli.py
```

`uv run ci check --only types --json` **passed** `4648e4089fc842c7a111ddb8ada13753`;
`uv run ci check --only lint --json` **passed** `237f6a6ef87d444a8d646becaffdb335`. Both
recipe outputs were retained durably with `ci evidence retain`. Final source was formatted before
this union. Subsequent registration refresh reproduced identical frozen migration bytes; receipt/
plan/status changes do not alter the qualified production or test source. Source/test commit `c2da716c6` preserves the qualified bytes. Root `just turn-end` passed with
1189 Python files unchanged and no safe-fix source changes. `uv run ci docs check --json`
**passed** `9e7cd45393344cf59db1defeb34545e3` (955 canonical pages, zero link errors; existing
phase0 descriptor-tag warnings). `uv run ci evidence check --json` **passed**
`f236f0e888dc4099bff1d3bb92cc3d95` (408 records / 224 folders, zero errors, 42 historical warnings).
Final receipt-only updates leave qualified product/test bytes unchanged.

**Repaired failures and preserved limits:**

- Initial native installation/publication failures `cbcecbae334546c0ab70cc6847d6c4fa`,
  `0e5c2a69fdb04421ac3f7157821715b8`, `01b82773168144acb4583578589ef777`,
  `76f2eb3b3b0641f88ac5e69389f4da15`, `ad314ba96f4448a9ba2443f005fa824d`,
  `bb865ac90a634ad89abc754df6fb2ae2`, `a0d3bf2c2909430aa579957bee1168a6`,
  `f2147b8173234711807ff158917430b6` and `7223e14847e64677b2ca8e47da19c9a1`
  exposed trigger dependency/ownership, native type normalization, fixture migration recursion,
  SQL precedence/alias and composite-row shape defects. The final union exercises the repaired
  native installation, exact publication/replay, permissions, takeover, revocation, snapshots,
  immutable content, invalid bodies and direct-writer predicate refusal.
- Existing-consumer regressions `7a1193b8bfc94c3892c078a5f914d9cc`,
  `55303ce073194f1ab49a31b1380ecb3e`, `36b1e3091f074f9c9c81fcad26e10350` and
  `0acef7d328ad4f3cafc142b044895bd4` prompted generated-call refresh, adaptation of the CLI
  preparation stub, explicit consumed task columns throughout affected completion/consolidation/
  source-frame/agent consumers, and the frozen forward migration required to align compiled and
  deployed physical descriptors. Intermediate runtime-pin drift occurred while source files were
  still being edited; the final union ran against stable source. It does not establish a cause
  for unrelated earlier process failures.
- Failed union `4b41695a2bdf45048ad369df7c4948f7` (308 passed / 8 failed) is
  [retained](../design_review/evidence/2026-11-13_cli-4b41695a2bdf45048ad369df7c4948f7/README.md).
  Native `3862aa550f3b45f6b76f970ff6fb0c04` (23 passed / 3 failed) is
  [retained](../design_review/evidence/2026-11-13_cli-3862aa550f3b45f6b76f970ff6fb0c04/README.md).
  Repairs preserve typed parameter encoding and require fresh pinned reads after revocation;
  deliberately invalid inputs still reach native enforcement. The final union covers all their
  selected identities on the final source.
- Worker crash `8faf0c6270ff448aba560dfe137d5fcc` is
  [retained with incomplete worker reporting](../design_review/evidence/2026-11-13_cli-8faf0c6270ff448aba560dfe137d5fcc/README.md).
  Its exact node passed in single-worker `6a6894c840374e0fa649d9168808ca7d` and the final union.
  Cause remains **unknown**; no memory or migration-cause claim is made.
- Managed candidate `8ed280dd74a24ebeb3e26574a1517257` refused because the CLI rebuilt native
  definitions after rolling back the new row-type scaffolding. `authored_admission_sql` now reuses
  the exact normalized admission from production authoring; it does not generate another answer.
  `1bb2a8f541704c9ca18d5643d0d80ca6` then correctly refused a stale preview after that repair.
  Fresh authoring/registration passed, and the actual CLI plus its 14 targeted regression cases
  are covered. Typing/lint failures encountered during integration were repaired; their original
  managed receipts retain their original scope, not qualification credit.

### Frozen migration and handoff boundary

The [native request and receipt](../design_review/evidence/2026-11-13_ddo-native-kernel/README.md)
record rollback-only authoring against the acquired `corpus_structure_dev` on PostgreSQL18/corpus,
port5434, OID25921445/system7701811359771751232. Final preview `f500ce98465a4260845d5772d2e0db53`,
apply `12ea0387dc004636842dd284a8d88062`, candidate `b0a0b07c907144eab227f891ba28caab` and
registration `2ae5b1b7cd7e420fb21d700cb03f0c25` **passed**. Candidate and preview are held while
DDO-04/11 still consume them. `ci model change inspect-candidate` reports registration verified
and dependency available; a future effect must reacquire its prerequisites and exact source binding.
No deployment authorization is inferred from an inspection's suggested command.

Revision `semantic_ddo_kernel_v1` adds 26 tables, two task columns, five nullable task fields under
the explicit legacy/target task constraint, two indexes and guarded native transitions. Inspection
found no table or column drops. Frozen upgrade/state/admission artifacts are stored through Git LFS;
registration refresh after formatting reproduced their hashes exactly. The native test fixture now
uses this normal frozen head and real catalog admission, removing its former acquired-candidate bypass.
`uv run ci db status --maintenance --json` confirms the persistent database still at
`semantic_bep_located_v2`, with repository head `semantic_ddo_kernel_v1`; it was not migrated or activated.

Broad series/provider/book/fault qualification is **not_run** at this partial checkpoint; DDO-12
retains the assembled qualification obligation. Original source/reference/evidence and held result
`0a78c71ce1a949e38e906c9c5392c1f3` remain protected. All worker assignments are concluded; only the
main worktree remains. Operator library-reference edits remain untouched and uncommitted.

## Investigations, risks and evidence boundaries

Authoring resolved compiler ordering through effective IR/stable references, typed relational forms,
native Demand authority, request ownership under existing tasks, and a short atomic publication /
trust protocol. The graph companion additionally owns bounded effective-model fidelity, coherent acquisition,
topology-policy separation, matching and selected-call typing questions with named dependent packages.
Optional features have revisit conditions and no mandatory investigation task. The implementation companion additionally assigns supported-profile coverage, source-only acquisition,
metadata export, cache isolation and slice-locality investigations before dependent reuse/migrations.
Remaining bounded execution investigations have outcomes, not a license to weaken
contracts: DDO-00's scoped metadata classification is complete; DDO-11 reacquires/freezes it before
adoption effects. DDO-01/02 qualifies semantic closure on actual effective schemas and its admitted
source profiles, preserving explicit unknowns for unsupported production profiles. DDO-04 qualifies native catalog/permission /
transaction behavior; DDO-07 qualifies actual provider mappings; DDO-12 resolves any material final
workload regression uncertainty. Failure blocks the dependent capability until corrected; no
field-only digest, hidden callback, CPU provider fallback or narrowed source universe is substituted.

The planning [census](../design_review/evidence/2026-11-12_declared-data-operations-planning/README.md)
was a metadata-only read on2026-11-12local/13UTC;329FKs/12table counts. It establishes why preservation
must precede destructive adoption, not a complete root inventory. No reference answers were read.
Future probes, if needed, follow the existing evidence route; expected improvements require no
measurement campaign. Useful independent semantic/reference expectations survive implementation-test
retirement. Full qualification belongs to this series, never inherited from an old plan.

## Completion audit · 2026-11-13

**Reassessed / source-inspected; one bounded defect reproduction Tested · 2026-11-13.**
This reassessment covers every complete/delivered claim in this coordinator and all nine
companions, including increments inside open packages. It also traces legacy/compatibility
machinery through their immediate execution, admission, selector, CPU, PDF and read consumers.
Inspected coordinator baseline `b1b4a4de0`, production/test source `561634814`; later checkout
`08dfd8d83` contains concurrent documentation changes, with no production/test change.
Three fresh read-only reviewers independently assessed compiler/identity/ports/projections,
native product/demand/purpose/recovery, and execution/prepared-family/consumer boundaries.
The coordinator separately checked decisions, metadata preservation and adjacent runtime readers.
Concurrent test-system planning and agent-reference edits are preserved.
Test-infrastructure implementation that started after this baseline is outside this semantic audit;
its eventual harness changes must be included in later qualification-context reconciliation.

**Conclusion: incomplete implementation, not only incomplete qualification.** DDO-00 meets its
bounded preparation boundary. Much of DDO-01–05 and the delivered DDO-06/07 increments exists,
but DDO-CA-01 still permits an unsound reusable recipe, DDO-CA-05 still loses a valid discovery
case, the accepted compiled projection-definition prerequisite is missing (DDO-CA-06), and
avoidable compatibility remains (DDO-CA-07). The earlier source-position repair and other passing
controls remain valid within their stated scope; they did not establish universal closure.
No production repair, migration, provider run or cancelled campaign was resumed by this audit.

### Claimed capability and bounded judgment

| Claimed scope | Current assessment |
|---|---|
| DDO-00 decisions, operation/consumer inventory and metadata preservation classification | **Complete at the dated preparation boundary.** ADR-0092–0095 and D1–D8 carry accepted targets. The inventory accounts for its 101-protocol, 34-phase0/17-M1 and declared local-owner universe; all 417 pending manifests and 73 historical-ID occurrences have conservative sealed dispositions. This is neither universal plugin discovery nor byte/replay/adoption verification. DDO-11 retains those operational obligations. |
| DDO-01/02 effective facts, identities and source-sensitive recipes | **Partially implemented.** The common IR, typed canonical codec and finite semantic graph/kernel exist. The customized captured-builtin counterexample reopens closure/runtime authentication under DDO-CA-01; compiled projection interpretation and obsolete compatibility remain CA-06/07. |
| DDO-03 binding, suitable direct/prepared/stream/command ports and four native consumer forms | **Implemented bounded capabilities, not complete package acceptance.** Strict ingress, typed pull ordinals/terminal standing, prepared ownership, acquired receipt-bearing publication commands and exact native hydration exist. Source authentication remains incomplete under CA-01 and projection declarations under CA-06. Native stream settlement and general effectful execution remain DDO-06/08; ordinary caller migration remains DDO-07/08. |
| DDO-04 native products, support, exact intent/replay, purpose and pinned reads | **Substantial native implementation; qualification incomplete.** CA-02's post-lock receipt reread and CA-04's affected-universe enforcement are present. Actual bounded native controls exist; the final required union was interrupted. Registration is not deployment or adoption. |
| DDO-05 frozen demand, discovery, selected dependencies, support rebind/recovery and fan-in | **Partially implemented.** Pinned planning/expansion/recovery mechanisms exist, but population closure incorrectly requires unique local subject strings (CA-05). A valid same-local-subject/different-scope population cannot reach child attachment. |
| Delivered DDO-06/07 execution and family increments | **Bounded APIs/foundations, broader packages open.** Claim/intent/publication execution, CPU custody and prepared family kernels exist; ordinary production execution has not switched to these target routes. CA-03's batch-loss repair is present. Native stream execution and complete provider/cutover work remain open. |
| NetworkX amendment | **Pure kernels delivered; projection-definition prerequisite incomplete.** Canonical typed edge occurrences, root-inclusive closure, SCC distinction, faithful multiplicity and explicit core dispatch remain useful. They do not supply the absent owned projection interpretation required by I01/DDO-01–03. Later runtime/serving integration retains its existing owners. |
| DDO-06–12 wider replacement, reuse, serving, preservation/adoption and assembled qualification | **Open; no enclosing completion certified.** Existing migration/retirement obligations remain required. APIs or tests calling target helpers do not establish that ordinary entry points migrated. |

### Finding disposition

This table owns current disposition. DDO-CA-01–05 retain their original identities and source-review
mapping; the original [reflection probe](../design_review/evidence/2026-11-13_ddo-completion-audit/README.md)
and all earlier receipts remain unchanged. New findings are plan-local CA-06/07, not new broad
design-audit findings.

| Audit finding | Current source evidence and consequence | Required closure and package owner |
|---|---|---|
| DDO-CA-01 (F04/F12) | **Still implementation-incomplete.** `python_operation_sources.py:1851–1856` excludes builtin references from captured dependencies. `data_operation_ports.py:1069–1073,1135–1141,1716–1723` authenticates code/module globals or assumes the standard builtin, without checking the callable's actual captured `function.__builtins__`. The [bounded probe](../design_review/evidence/2026-11-13_ddo-completion-reassessment/README.md) receives complete slices/no unknowns and the same recipe for results `7`/`8`; isolated post-acquisition builtin-map mutation changes both admitted results to `9`. The original source-position case is repaired, but this residual invalidates the general closure claim. | **Open; DDO-01/02/03.** Refuse unsupported customized builtin environments or model their actual determinants; authenticate each consumed captured builtin binding at runtime. Independent helper-change and isolated mapping-mutation controls must distinguish irrelevant edits from behavior changes. Do not substitute a broad runtime salt for a complete semantic recipe. |
| DDO-CA-02 (F07/F13) | **Repair present; final acceptance open.** `sql/data_operations.sql:1054–1069` rereads the exact committed receipt after support/request serialization, before requiring a live claim. Atomic/overlapping exact publication passed in `78a4a3930af741adb9f2e40f51043418`; differing same-attempt intents retain immutable refusal. | DDO-04 retains final-source/context qualification and exact differing-intent/attribution protection. The interrupted union is not a complete replacement receipt. |
| DDO-CA-03 (F13/F14) | **Repair present; scoped Tested; acceptance open.** `_check_batch_active`, `orchestrate/data_operations.py:98–111,688–690`, retains useful siblings and cancels/drains when none has confirmed authority. `8efecb9296e1459ca10a66fdd2191bcb` passed three batch-activity controls: two ownership-state controls and **one actual hung spawned-process retirement case**, not three physical cases. Broader CPU/activity passed 9/9, `515f429636594afe8aa5cf6c99b64675`. | DDO-06 retains assembled qualification and its other execution/stream obligations. No source evidence found that reopens the original batch defect; do not overstate the physical-case count. |
| DDO-CA-04 (F11/F13) | **Repair present; final acceptance open.** Native fate/expansion/revocation/pending read branches enforce affected kind universes (`sql/data_operations.sql:483–487,512–516,1159–1172,1184–1188`). Valid typed writer/evaluator probes reached the guards in native 10/10, `8dc2c54a9a8f44cfa38f40302d5eec15`; broad selector authorization remains explicit. | DDO-04 retains actual principal, unchanged-fate/trust and final-source qualification. No additional purpose defect was established in this inspection. |
| DDO-CA-05 (F05) | **Still implementation-incomplete in discovery.** Request/product context and exact numeric/null controls are implemented under ADR-0100, but `close_data_population`, `sql/data_operations.sql:543–544`, groups only by `member->>'subject'`. Publication accepts distinct member IDs/full contexts (`:917–942`); closure rejects members named `local` with scopes page1/page2. Native expansion (`:493–503`) and planner forwarding (`data_operation_demands.py:402–413`) already retain complete context. | **Open; DDO-02/03/04/05.** Qualify ambiguity by complete authenticated context with JSONB scope meaning; retain refusal of truly duplicate complete contexts. Exercise native publish→close→expand→attach→publish for both scopes. Use normal forward native authoring; leave frozen v5 unchanged. |
| DDO-CA-06 (NetworkX I01; F01/F02) | **Missing accepted projection-definition prerequisite.** Graph companion §I01 requires compiled source/selection, node/relationship/orientation, unresolved-reference/completeness and analysis interpretation. `EffectiveDataOperationModel`, `data_operation_model.py:378–387`, has no equivalent projection definition. Kind `projection_families` validates packet access, while `SemanticGraph`, `data_operation_identity.py:194–337`, supplies pure authenticated topology kernels. `freeze_demand`, `data_operation_demands.py:107–118,177`, chooses dependency connectivity directly. Those useful subsets do not supply the governing projection contract. | **Open; DDO-01/03.** Compile/admit/archive the named projection interpretation in the effective model and have graph construction/analysis consume it, with independent fidelity/completeness controls. This does not pull later DDO-04/08/09/10 consumers forward or require a separate graph registry/service. |
| DDO-CA-07 (hard-target retirement; Python I05) | **Avoidable compatibility remains.** Current authoring accepts `ARCHIVED_MODEL_VERSION` then emits current v2 (`data_operation_compilation.py:770,1480`). Context-incomplete `subject_identity`/`product_identity` (`data_operation_identity.py:407–434`) have only mechanism tests, and `trusted_data_operation_calls = native_operation_calls` (`data_operation_storage.py:303`) has no repository caller. No concrete retained v1-model instance was identified in the inspected authored-source/preservation owners; synthetic v1 tests are not such a consumer. | **Open; DDO-01/02/03 retirement.** Move declaration fixtures/examples to the current version; remove old-version authoring acceptance, obsolete helpers/alias and mechanism-only controls while preserving useful independent expectations against current identities. Reconcile TS-19's existing helper-deletion handover without duplicating status. Retain a historical decoder only for a specifically identified retained reader/recovery obligation; otherwise retire it too. Frozen migration/evidence bytes stay immutable. |

### Hard-target retirement and closely related adjacent code

Actual old consumers explain what must migrate; they do not grant permanent compatibility.
The completed replacement must have one current authority, with obsolete routes and their
mechanism-only tests removed. Shared useful algorithms, protected native fences and preserved
historical bytes are not obsolete merely because the former route also uses them. The following
is the concrete remaining footprint within the inspected DDO/immediate-adjacent boundary, owned
by existing packages rather than a second retirement plan.

| Remaining mechanism and ordinary consumer | Source evidence | Existing owner / completion requirement |
|---|---|---|
| Registry/method selection and former four selectors | `orchestrate/phase0.py:122–130`; `orchestrate/semantic.py:805,1744`; old selector/digest paths in `methods/native_evidence.py:408–423`, `m1_source.py:496–510`, `structural_products.py:1625–1631`, `contextual_candidates.py:969–1005`. The target hydration APIs are real, but no production caller of those four APIs or `NativeDemandExecutor` was found in the searched Python tree. | DDO-06/07/08: migrate ordinary callers, then remove private selector/digest and registry authority. Preserve conformance kernels, not the old routing. |
| Handwritten dependencies, stage sequencing and freshness recovery | `orchestrate/characterization.py:354–379,527–546,780–817`; `characterization_recovery.py:38–88`; `orchestrate/semantic.py:715–744`. | DDO-06/07: native Demand and compiled declarations replace name maps, first-stage anchors, freshness salts and `SourceOperationLink`; replacement reporting must carry required lineage first. |
| Legacy CPU packets/Reader facade/dispatch default | `semantic/cpu_execution.py:164–175,299–340,395–428,834–859`; actual callers `methods/formal_evidence.py:114–132`, `construction_characterization.py:134–159`. | DDO-06/07: switch callers to acquired target plans; retain shared process/capacity custody and remove the legacy packet, fake Reader/run facade and default branch. |
| Dynamic capability discovery and stage permits | `orchestrate/semantic.py:197–202,1876–1884`; `orchestrate/ready.py:39–42,167–172`. | DDO-06/08: admitted typed ownership replaces `getattr(plan/close)` and stage-run capacity mechanisms. |
| Combined former spaCy/HanLP producer | `methods/native_evidence.py:428–491,670–710` still conditionally invokes HanLP inside the former combined layer route. Separate target family declarations/kernels do not remove that caller. | DDO-07: migrate independent native producers and immediate consumers, then remove combined compatibility routing. |
| Dual admission/task/PDF runtime branches | `semantic/execution_admission.py:52–91`; `sql/execution_guards.sql:4–24` and old lifecycle branches; `pdf_staging_native.py:55–74,87–103,114–139`. | DDO-06/07/08/11: authenticate transition of actual live task/build custody, migrate callers and remove executable legacy branches. They are not frozen historical artifacts. |
| Task/run-origin serving, reuse and fallback projections | `runtime_binding_store.py:56–84` is reached by `serve/selected_source.py:338–384`; DDO-09/10 already name copied reuse/task-dependency/currentness and pinned-reader/export migration. | DDO-09/10/11: move actual readers and durable references, then retire current runtime fallback paths. Archive-only `legacy_runtime_binding` refuses current execution compilers (`runtime_bindings.py:259–277`); preserve necessary original interpretation through concrete frozen custody/import, not a second current execution authority. |
| Authored graph cycle misclassification | `semantic/domain_operations.py:1646–1658` labels every unprocessed `TopologicalSorter` node cyclic, including a tail blocked by a cycle. | Existing DDO-08 / NetworkX I02–I03: SCC/condensation distinguishes actual cycle members, blocked descendants, self-loops and unrelated work. This known open obligation is not renamed as a new finding. |
| Dead current helpers and v1 authoring compatibility | CA-07 above. Historical v1 reader/re-export branches are `data_operation_model.py:423–440,583–640`; no concrete retained target-v1 consumer was established in this bounded search. | CA-07 owns immediate retirement; identify an actual historical interpretation need before retaining decoder machinery. TS-19's proposed deletion work is a handover, not proof of completion. |
| Frozen native revisions / rejected never-deployed archive-v1 evidence | The registered v2–v5 wrappers and payloads implement exact predecessor custody; rejected v1 is preserved outside active Alembic discovery. | Keep immutable historical bytes and required retained evidence. Their retention does not justify a current fallback API, and audit authorization does not permit rewriting migrations or dropping preserved data. |

### Verification, qualification and benefit limits

The new synthetic builtin probe **passed as a defect reproduction**, record
`ddo.captured-builtins-collision`, using
`uv run python docs/design_review/evidence/2026-11-13_ddo-completion-reassessment/builtins_probe.py`.
It performs no provider/database work and does not resume the cancelled campaign. Source
inspection establishes the population/projection/retirement findings without a new test campaign.

The retained final attempted union remains **failed due to operator-requested interruption**:
`2a1fdebfd77749378ce7d4598cba5d68`, 651 selected, 452 passed, 195 not_run, 4 incomplete,
with settled/drained custody. It does not establish full qualification. Earlier receipts preserve
their actual source, scope and context; none covers the new builtin counterexample or same-local-
subject members in one scoped discovery population. The successful repository check
`ef31917fa4ae44cca9aad5b7ae96d0f1` is not proof that the intended semantic scope is complete.

Two evidence descriptions are corrected: batch activity has **one actual hung-process case among
three controls**; the 57-case prepared-family receipt `bfe48e3b290748e091f3cf2b296bdf13`
also includes **bounded actual CUDA HanLP head retention**, not only controlled HanLP behavior.
The real test reaches `hanlp.load` through the default native host. This is neither native family
publication nor complete provider/production-cutover qualification. Authentic execution, retained
fidelity and linguistic correctness remain distinct.

Expected reuse/preparation/work-reduction benefits remain qualitative; no quantitative performance
improvement is established. Missing benchmarks alone are not an incompleteness finding. The audit
has not certified unrelated legacy code outside the named subsystem/adjacent routes. No production
repair or adoption is authorized by these corrections. Implementation remains paused.

## Audit repair execution · 2026-11-13

**Partial implementation / qualification paused · 2026-11-13.** The operator-selected execution is to close
DDO-CA-01–05 and remaining DDO-03–05. It does not imply completion of DDO-06–12. ADR-0100
owns complete subject context through binding, request and product identity: project, local
subject, original source and analyzed scope. Scope JSON numbers retain JSONB decimal value
meaning; bool, string and null remain distinct. Typed semantic parameters and result bodies
retain their existing tagged meanings and encoding version.

The assembled implementation now includes:

- Source-reference and escape classification using captured LibCST/Astroid/Griffe facts refuses
  the inspected function/class-reflection cases. Captured builtin namespaces remain unsound
  under CA-01; the frontend is not generally complete. Known data fields
  and explicit opaque provider bridges retain their appropriate profiles. Generated dataclass
  invocation preserves the real signature, keyword-only/default/factory facts and strict ingress;
  runtime acquisition must authenticate the generated constructor and its admitted methods.
- Explicit context in resolved bindings and all migrated product families. Native request and
  product keys use that same qualified context; discovery association uses typed JSON meaning,
  but population closure still rejects distinct scoped members sharing a local subject (CA-05).
  Local subject headers and original producer/support evidence remain independently retained.
- Native post-lock exact-receipt replay, protected-purpose checks for fate/expansion/revocation
  and pending/zero-output reads, and complete target checks for broad revocation selectors.
- Batch activity checks that retain useful siblings, distinguish uncertain completion custody
  and retire/drain physical work when every claim is lost. The batch-activity selection
  **passed 3/3 controls, including one actual hung-process case**,
  `8efecb9296e1459ca10a66fdd2191bcb`; broader CPU/activity **passed 9/9**,
  `515f429636594afe8aa5cf6c99b64675`.
- Pull-stream closure, prepared-resource ownership, receipt-bearing native command acquisition,
  and exact native hydration for the four required immediate consumer forms. Python normal
  returns and prepared-family completions select the declared unambiguous successful outcome;
  `claim_source_item` keeps its actual `addressed`/`invalid-index` contract.
  DDO-03's pull-stream port is delivered; native owned stream pulling, bounded physical retirement
  and declared item/terminal settlement remain DDO-06. No current production stream declaration
  or native publication-per-item behavior is claimed.
- Native admitted discovery, child expansion, closed fan-in, explicit dependency selection,
  support substitution/invalid-intent generation recovery and pinned continuation controls.
  Runtime/native evidence is required before their package obligations close.

**Current assembled checks · 2026-11-13:** source/compiler/identity/binding/ports/planner/CPU
checks **passed 296/296**, `b0a886ec084441fab287c5b2644f0786`. Prepared product families
**passed 57/57**, `bfe48e3b290748e091f3cf2b296bdf13`, including actual spaCy and canonical
CPU controls and bounded actual CUDA HanLP native-head retention. Controlled adapter tests
within that suite do not gain actual-provider status; native family publication remains open. Wire,
parameters, source-set, preparation and consumer checks **passed 50/50**,
`dfac6b0e387049d19d0629fc0a71fc4c`. Current binding, null-context, command/authoring and
checker controls **passed 73/73**, `f7fe163768034b33ba2ae3014652b2ec`. Full repository
`uv run ci check --json` **passed**, `0b4fd0a8679b442287303c34e89a7ee4`. Later documentation
changes require their publication check; these receipts preserve their actual source and scope.

The [authoring evidence](../design_review/evidence/2026-11-13_ddo-archive-composition/README.md)
owns frozen revisions and all failed/superseded attempts. Invalid never-deployed archive-v1 bytes
remain unchanged outside active Alembic discovery. Corrected v2 and ordinary v3 remain frozen;
actual runtime checks exposed two deferred SQL precedence errors and a fixture kind-shadowing
error. Source repairs also distinguish population variables from support aliases and project
computational episode IDs from mixed-origin support without discarding original references.

Final desired DDO functions now receive active PostgreSQL embedded-SQL type checking through
plpgsql_check during rollback-only authoring. Explicit inventory selection preserves frozen
predecessor meaning, native ACLs and extension lifetime; bounded diagnostics expose unexamined
scope. This catches static typing errors, not arbitrary runtime dynamic SQL or semantic truth.
[The database owner](../design/D3-database.md#postgresql-capability-realization) records the
mechanism and limits. The scope binder uses SQLAlchemy `JSON.NULL` to distinguish explicit
JSON-null context from an omitted SQL-NULL projection parameter, leaving typed body/parameter
null meanings unchanged.

Archive-v4 preview `ad0a9ebb043b4e2aa6f034819c87956b`, rollback-only candidate
`b725cb7122424cdc8bc6bb0e458f3849` and registration `aa6793ea4ce64363b768d699fe0d2180`
**passed**. The critical native/production selection **passed 7/7** (six native journeys and
one independent production-preparation control), `78a4a3930af741adb9f2e40f51043418`: atomic/exact overlapping publication, precise fractional
context, genuine JSON-null product binding, discovery/closed fan-in/pinned resume and unchanged
production `claim_source_item` execution with settled resume. The complete native union
`0aaa980a87bc415f8c6c682ebacd2214` **failed**, 129 passed / 13 failed. Its trust-map,
PDF-stage SQL, contextual uniqueness and retired-attempt defects are being corrected through
a normal successor after frozen v4; test inputs are repaired to reach their intended guards.
Package and audit-finding acceptance remain open until replacement qualification and final
disposition are reconciled. The persistent development database
remains `semantic_bep_located_v2`; plpgsql_check was not left installed there. DDO-11 owns
persistent deployment/adoption/activation.

### V5 qualification baseline

**Frozen native baseline; final qualification interrupted; implementation remains incomplete · 2026-11-13.** Ordinary forward archive-v5
preview `f85b42104df544b68c292fc3e9e0c9b7`, rollback-only candidate
`fa5eaba6351647c581bfec47520baac5` and registration `140d3537f7014c2786f42815cb9ba27e`
**passed**. The [authoring account](../design_review/evidence/2026-11-13_ddo-archive-composition/README.md#accepted-v5-authoring)
records all fourteen native transitions and four ordinary statements. The only physical removal
is the obsolete product uniqueness constraint missing analyzed scope; the contextual primary key
remains authoritative. Frozen v2–v5 artifacts are unchanged after registration.

Trust-map comparison now treats explicit numeric zero as the model's absent-scope default;
unknown/null epochs refuse and positive revocation stays exact. Attachment checks concrete locked
support against the full stored pinned read, and Python consumes the native reader's canonical
answer. Immutable support/publication attribution retains concrete zero epochs. The PDF owner
guard keeps its legacy/runless locks and fences with qualified SQL aliases. Retired physical
attempts retain their holder evidence and need a new attempt fence on the next claim.

Bounded controls **passed**: trust SQL 19/19, `cdbe882e2f2547c9873dd82ab6ea6b27`;
PDF checking/restoration 1/1, `b452c14cf5cd439f8f8e4b3afe7b1720`; repaired native
planner/population/selected-graph/purpose inputs 10/10, `8dc2c54a9a8f44cfa38f40302d5eec15`.
Read-only independent reviews found no material issue in the assembled trust and PDF/checker
corrections; those reviews do not replace the actual native journeys.

The required final union is all `test_data_operation_*` modules under semantic/orchestrate,
the source frontend, five prepared-family suites, native candidate/checker controls and the PDF
guard control: 51 files, exact argv captured by managed
`2a1fdebfd77749378ce7d4598cba5d68`, using `uv run ci test --workers 4 --json -- …`.
Source `561634814` remained frozen for this union. At the operator's request the owned pytest
controller received SIGINT, and its supervisor settled/drained the invocation. The managed outcome
is **failed due to interruption**, with **651 selected / 452 passed / 195 not_run / 4 incomplete**;
there are no assertion-failure counts in that classification. Its held
[durable receipt](../design_review/evidence/2026-11-13_cli-2a1fdebfd77749378ce7d4598cba5d68/README.md)
preserves partial outcomes; this is not complete qualification. No replacement is running.
`uv run ci check --json` **passed**,
`ef31917fa4ae44cca9aad5b7ae96d0f1`, including typing, lint, docs, dependency checks and Clippy;
Rust `rustc 1.102.0-nightly (9c5648833 2026-11-10)`. Later documentation/receipt changes receive
their publication/evidence checks. Finding/package closure awaits the remaining required identities
and reconciliation of source/context applicability.

**Pause publication checks · 2026-11-13:** `uv run ci docs check --json` **passed**,
`26378fcaf892417c81f899044ed6d6c1` (1,244 canonical pages, zero link errors).
`uv run ci evidence check --json` **passed**, `39ad27ce735449d38b59a5849a235286`
(675 records / 497 folders, zero errors, 42 existing historical warnings).
Root `just turn-end` **passed** without changing production or test source. These checks
validate the updated account and retained interrupted receipt; functional qualification remains incomplete.

## Completion and current next action

Complete means one target authority, all supported operations/consumers migrated, no obsolete
semantic fallback, preservation/adoption verified and applicable series qualification covered.
The acceptance details and commands are in the qualification companion. Record enduring meaning in
D1–D8 and accepted decision records, preserving exact old review/evidence history. Never delete plan
or evidence files. Authoring publication checks are separate from product qualification.

**Implementation remains paused.** The current audit records outstanding work; it does not restart
repairs or the cancelled campaign. On the operator's resumption, address CA-01's captured builtin
closure/authentication, CA-05's complete-context discovery, CA-06's compiled projection prerequisite
and CA-07's avoidable compatibility. Native changes require normal successor authoring after frozen
v5. Migrate ordinary consumers and remove the adjacent legacy footprint under their existing
DDO-06–11 owners before claiming those replacements complete.

After repairs, reassess affected evidence against final source/context and qualify the required
union; do not merely retry 199 unresolved identities while assuming the 452 old passes cover changed
semantics. Preserve `2a1fdebfd77749378ce7d4598cba5d68` and earlier failed receipts. Use `ci test coverage`
for explicit selection/source/context reconciliation. No finding/package closes from source presence,
a generic recipe name, a test count or this audit alone.
DDO-07/08 production profiles must close their
required kind/implementation/context facts before invoking or reusing target results. DDO-11
preservation remains a prerequisite for adoption effects; DDO-12 owns the final required union.
