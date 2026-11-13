# Declared data operations — total governing model

**Status: Proposed implementation series; authoring revised 2026-11-12 with NetworkX and Python-introspection integration; production not started.**
Owns DDO-00–12, the full audited F01–F14/C1–C7 scope, RC01–RC09 adoption and assembled
qualification. The operator selected this as a dramatic standalone redesign: other plans supply
no scope, prerequisites or acceptance limits. Current code/data remain the implementation baseline.

## Basis, objective and decisions

Consumes the [integrated review](../design_review/reviews/design_review_declared-data-operations_2026-11-12.md)
and all4supporting pages at64dc6c3e6; the audit companion explains changes, not additional scope.
Product source8c0f4f951, diagnostic reconciliationf6ce5d086. Actual starting tree64dc6c3e6 was clean.
The NetworkX amendment consumes [its review](../plan_improvement_reviews/declared-data-operations-networkx_2026-11-12.md)
at `7c5368faa`. Operator authorization selects I01–I07 required portions and preserves conditional
capabilities with explicit triggers, not mandatory investigations. The Python-introspection amendment
consumes [its review](../plan_improvement_reviews/declared-data-operations-python-introspection_2026-11-12.md)
at `0907dcc23`; its source-qualified RC01–03 were explicitly accepted on 2026-11-12. All new mechanisms here are **Proposed**. Source inspection and metadata census are bounded evidence;
no new implementation, migration, deployment, activation, provider inference or product test was run.
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
DDO-00 records/supersedes the affected accepted ADRs and updates D1–D8 owners as target architecture
before dependent production cutover. Group coherent decisions; nine impacts do not require nine
redundant records. Accepted historical ADR bodies remain immutable.

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

All packages are **open/not implemented**. Rows describe dependencies, not mandatory stage-wide
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

## Finding and recommendation disposition

Each row is **open**, with closure determined by the complete contributing package behavior, not
mere acceptance of the target. Preserve original source IDs; do not relabel prior plan findings.

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
All selected work is **open/not implemented**. Conditional subfeatures retain their source judgments
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

All selected work remains **open/not implemented**. IDs below refer to review `0907dcc23`, not
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

## Investigations, risks and evidence boundaries

Authoring resolved compiler ordering through effective IR/stable references, typed relational forms,
native Demand authority, request ownership under existing tasks, and a short atomic publication /
trust protocol. The graph companion additionally owns bounded effective-model fidelity, coherent acquisition,
topology-policy separation, matching and selected-call typing questions with named dependent packages.
Optional features have revisit conditions and no mandatory investigation task. The implementation companion additionally assigns supported-profile coverage, source-only acquisition,
metadata export, cache isolation and slice-locality investigations before dependent reuse/migrations.
Remaining bounded execution investigations have outcomes, not a license to weaken
contracts: DDO-00 completes actual external-reference preservation closure; DDO-01/02 qualifies
semantic closure on all real effective declarations; DDO-04 qualifies native catalog/permission /
transaction behavior; DDO-07 qualifies actual provider mappings; DDO-12 resolves any material final
workload regression uncertainty. Failure blocks the dependent capability until corrected; no
field-only digest, hidden callback, CPU provider fallback or narrowed source universe is substituted.

The planning [census](../design_review/evidence/2026-11-12_declared-data-operations-planning/README.md)
was a metadata-only read on2026-11-12local/13UTC;329FKs/12table counts. It establishes why preservation
must precede destructive adoption, not a complete root inventory. No reference answers were read.
Future probes, if needed, follow the existing evidence route; expected improvements require no
measurement campaign. Useful independent semantic/reference expectations survive implementation-test
retirement. Full qualification belongs to this series, never inherited from an old plan.

## Completion and current next action

Complete means one target authority, all supported operations/consumers migrated, no obsolete
semantic fallback, preservation/adoption verified and applicable series qualification covered.
The acceptance details and commands are in the qualification companion. Record enduring meaning in
D1–D8 and accepted decision records, preserving exact old review/evidence history. Never delete plan
or evidence files. Authoring publication checks are separate from product qualification.

**Next:** execute DDO-00 and the DDO-01–03 compiler/binding foundation when implementation is
requested. This document authorizes no production effect merely by being published.
