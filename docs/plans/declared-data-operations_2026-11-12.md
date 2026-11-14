# Declared data operations — total governing model

**Status: Reassessed 2026-11-14. DDO-00–02 retain bounded foundation completion.
DDO-03/04 have reopened native implementation obligations (DDO-CA-08/09); DDO-05 dependency-complete readiness is not certified until those contracts work. Earlier scoped qualification remains dated evidence.
DDO-06–08 remain open; the current increment is concluded and its remaining tests were cancelled by the operator, 2026-11-14. DDO-09–12 retain their broader open scope. No deployment, activation or production cutover.**
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

### Source evolution and model-update amendment · 2026-11-13

Consumes [ast-grep/LibCST review I01–I06](../plan_improvement_reviews/declared-data-operations-ast-grep_2026-11-13.md)
at `2e88d02db`. The operator selected full integration on 2026-11-13: owned regeneration,
programmatic Python migrations and the bounded ongoing `ci model change preview/apply` capability
are required planned scope. Ast-grep discovery remains conditional per actual consumer; adding its
Python binding is not a prerequisite. The [source-evolution companion](declared-data-operations/source-evolution-and-migrations.md)
owns technical contracts, detailed library references, conditional dispositions and settling cases.

DDO-03 supplies explicit source-migration intent, proposed-source compilation and exact effect
preparation. DDO-06/07 supply authentic binding/read/trust context and the first actual M1 caller
migration; DDO-07/08 complete their full ordinary-consumer populations. DDO-10 exposes those same
supported transformations as recurring operator preview/apply behavior. DDO-09 retains semantic
change/reuse meaning; DDO-11/12 retain adoption, immutable history, retirement and qualification.
No new DDO stage or second semantic/effect authority is introduced.

Authored inputs change only through explicit owner-specific intent. Regenerate checkout-derived
products through their owners; retain release-only calls/IDs/schemas in archive preparation.
Required unresolved consumers prevent a coherent migration from becoming applicable. Existing apply
remains retryable per-file publication, not multi-file atomicity. Bind source-universe membership,
eligibility facts, transformation implementation/options and selected library identity alongside
existing exact-byte/toolchain premises. Initial scope is finite named UTF-8 Python transformations.

LibCST's programmatic codemod results, rename/import coordination, matcher/template construction
and an explicitly qualified annotation stage are selected mechanisms for applicable migrations.
Current Griffe/Astroid/conditional ty responsibilities and pyrefly remain unchanged. Ast-grep matches
are syntax/candidate evidence; they cannot establish complete semantic dependency or caller closure.
The complete capability catalogue keeps triggers and limits rather than scheduling every feature.
No rule impact is presently selected; a real authority/publication change follows the existing
confirmation/decision route. This is plan adoption, not implementation or renewed qualification.

## Reading and work-package ownership

| Supporting plan | Owns design detail |
|---|---|
| [Source evolution and migrations](declared-data-operations/source-evolution-and-migrations.md) | Source-effect preparation, migration eligibility/results, library composition and ongoing preview/apply; DDO-03/07/08/10 with DDO-09/11/12 boundaries |
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

DDO-00 is **complete at its scoped preparation boundary**. DDO-01/02 retain **bounded foundation completion**. DDO-03/04 are **incomplete at the required native contract boundary** (CA-08/09); DDO-05 retains its delivered resolver but its dependency-complete native readiness claim is **open**. Earlier CA-01/05/06/07 scoped repairs remain implemented; they do not discharge the new obligations. The completion-audit findings table and the resumed execution receipt below own current disposition and source/context-qualified evidence. DDO-06–12 remain **open**. The current DDO-06–08 increment is concluded at the operator's integration/closeout boundary, 2026-11-14; remaining targeted qualification is cancelled, not passed. The current execution account below owns the residual work and efficiency follow-up. Neither cancelled campaign is restarted.
Rows describe dependencies, not mandatory stage-wide
barriers or separate agent assignments. Interface agreement permits design, not a claim of usable
native behavior. Product-family slices carry immediate consumers; no late consumer repair phase.

| Package | Prerequisite capability | Delivered behavior and completion boundary |
|---|---|---|
| DDO-00 | Accepted RC01–09 and current code/data | Durable decisions/owner updates, complete operation/consumer inventory and preservation root classification; no destructive action before concrete closure |
| DDO-01 | DDO-00 accepted mixed ownership | Both closed source/declaration frontends and one normalized operation/kind model; source/aggregate/effectful profiles represented |
| DDO-02 | DDO-01 effective IR | Versioned canonical kind/subject/product/recipe/binding and admitted implementation-slice identities, independent expected examples |
| DDO-03 | DDO-01/02 | Direct suitable typed invocation plus generated native/wire correspondence, fixed relational bindings and equivalent native/explanation semantics; explicit source-migration effect preparation; no hidden selector authority |
| DDO-04 | DDO-01–03 implemented contracts | Native products/support/request/attempt/intent/fulfillment operations and purpose permissions work under real transactional controls |
| DDO-05 | DDO-03/04 | Native frozen demand, declared discovery/aggregate closure, explicit producer selection and dependency-derived frontier |
| DDO-06 | DDO-04 and DDO-05 resolved requests | Cross-demand coalescing, owned execution, fenced publication, exact uncertain replay, bounded drain and resume |
| DDO-07 | DDO-01–06 usable vertical primitives | Capture/recognition/source and primary providers publish new products with their immediate consumers migrated |
| DDO-08 | Same primitives + required DDO-07 products | Every downstream/structural/authored/external operation and effectful action realizes its declared profile; bypasses removed |
| DDO-09 | DDO-02–04; integration with DDO-05–08 | Complete declared reuse, support-aware revocation/impact and modeled consolidation; remove conservative old mechanisms only after replacement works |
| DDO-10 | DDO-04 selection; DDO-07–09 products | Pinned read/export/replay, protected assessment and supported operator model-update preview/apply; no hidden inference or cross-snapshot meaning |
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

### Ast-grep/model-update review disposition · 2026-11-13

Source-qualified IDs refer to review `2e88d02db`; they do not replace Python or NetworkX I01–I07.
Required portions below are accepted planning amendments, **open for implementation**. Conditional
rows retain their triggers in the source-evolution companion; no dependency or investigation quota
follows from catalogue inclusion. This table alone owns scheduled disposition.

| Source recommendation | Integrated responsibility and package owner | Required closure |
|---|---|---|
| [Ast-grep I01](../plan_improvement_reviews/declared-data-operations-ast-grep_2026-11-13.md#I01) | Required owner-specific propagation and owned generation, DDO-01/03/07/08/10 | Declaration-owned and implementation-owned changes reach derived products and actual handwritten consumers without inverse authority or patched generated artifacts. |
| [Ast-grep I02](../plan_improvement_reviews/declared-data-operations-ast-grep_2026-11-13.md#I02) | Required applicable programmatic LibCST migrations, DDO-03/07/08/10 | Actual M1 first slice, contextual/structural challenge cases, complete required consumer population, qualified adopted rename/import/annotation behavior and retired former routing. |
| [Ast-grep I03](../plan_improvement_reviews/declared-data-operations-ast-grep_2026-11-13.md#I03) | Conditional bounded discovery within DDO-00/07/08/10 | Existing discovery/CLI or embedded binding selected only when it removes concrete work; preserve attribution, coverage and unknowns. No second production frontend, persistent scanner or new lint gate. |
| [Ast-grep I04](../plan_improvement_reviews/declared-data-operations-ast-grep_2026-11-13.md#I04) | Required ongoing explicit source-update preview/apply, DDO-03/10 with DDO-07/08 migration semantics | Proposed-snapshot compilation, typed per-consumer outcomes, exact file effects, complete staleness premises and honest partial-apply recovery; required unresolved sites prevent application. |
| [Ast-grep I05](../plan_improvement_reviews/declared-data-operations-ast-grep_2026-11-13.md#I05) | Required selected-boundary fidelity, DDO-01/03/07/08 | Correct scope/alias/source identity, encoding/coordinates, parse validity, conflict handling and independent source/semantic expectations for the chosen backend. |
| [Ast-grep I06](../plan_improvement_reviews/declared-data-operations-ast-grep_2026-11-13.md#I06) | Required qualitative execution fit, DDO-03/07/08/10 | Shared preparation and scoped file batches; no gratuitous second parse, journal, worker pool or resident index. No quantitative benefit claim without measurement. |

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

<a id="completion-audit--2026-11-13"></a>
## Completion audit · 2026-11-14

**Reassessed / Interface-checked by source inspection, 2026-11-14.** This audit reconstructs all
complete/delivered claims across DDO-00–12 and all ten companions, and searches the entire repository
for retirement opportunities through the implemented DDO target. Production/test baseline is
`a15f2e197cb7da4e16eae9d6e6fbbbe99e5aa5b2`. Concurrent `c940b529e` adds only the SQLAlchemy/Alembic
review and its index; those changes are preserved and its recommendations remain unadopted.
Three fresh independent read-only implementation reviewers examined foundations/native contracts,
execution/producers, and public consumers/preservation. The root reconciled their decisive source
facts and inspected configuration, schema/interchange generation, scripts, services, Rust and documentation.

**Implementation:** DDO-00's declared metadata classification and DDO-01/02's inspected foundation
claims retain their bounded completion. DDO-03/04 require CA-08 provider-selected input identity and
CA-09 transitive trust pinning; DDO-05's dependency-complete native readiness therefore remains open.
These are missing accepted native capabilities, not merely missing provider tests. Safe refusal of
an unimplemented profile does not constitute an operator-approved exclusion. Existing CA-02/04/05
narrow replay, purpose and qualified-context repairs are not reopened by unrelated findings.
DDO-06–12 remain open; ordinary caller, family, serving and adoption gaps were already required work.

**Qualification:** read-only managed inspection confirms cancelled ordinary receipt
`3696eb7a301c4cc1965aefe09b0f1ddb` is failed with1failed/1incomplete and settled custody. The paired
provider receipt and historical diagnostic/passing receipts retain their recorded bounds in the
[current increment account](#verification-and-cancelled-qualification). Lost worker-local raw
receipts remain unavailable. **not_run:** tests, builds, provider execution, database operations,
benchmarks and repository health checks in this audit. No cancelled qualification is resumed.
**Benefits:** reduced duplicate work and smaller maintained code are qualitative expectations;
no measured performance benefit or complete assembled qualification is certified.

The retirement footprint below is an actionable assessment, not authorization to delete production
code or data. Actual public demand read/export replacements are not yet complete: a native demand
inspection API alone cannot replace every Reader/MCP/export contract. Conversely, untouched obsolete
scaffolding need not wait for the whole cutover merely because it sits beside a live Graph or kernel.

### Claimed capability and bounded judgment

| Claimed scope | Current assessment |
|---|---|
| DDO-00 decisions, operation/consumer inventory and metadata preservation classification | **Complete at the dated preparation boundary.** ADR-0092–0095 and D1–D8 carry accepted targets. The inventory accounts for its 101-protocol, 34-phase0/17-M1 and declared local-owner universe; all 417 pending manifests and 73 historical-ID occurrences have conservative sealed dispositions. This is neither universal plugin discovery nor byte/replay/adoption verification. DDO-11 retains those operational obligations. |
| DDO-01/02 effective facts, identities and source-sensitive recipes | **Complete at foundation scope, 2026-11-13.** Captured-builtin closure/authentication, compiled projection interpretation and current-format retirement are repaired. Effective facts and canonical codecs retain explicit unsupported-profile refusal; later family migrations do not become complete here. |
| DDO-03 binding, suitable direct/prepared/stream/command ports and four native consumer forms | **Reopened native profile scope, 2026-11-14 (CA-08/09).** Typed ports, hydration and source-migration preparation have scoped passing evidence; required provider-sensitive native correspondence and coherent transitive trust acquisition are incomplete. Ordinary callers retain DDO-06–08 owners. |
| DDO-04 native products, support, exact intent/replay, purpose and pinned reads | **Incomplete, 2026-11-14 (CA-08/09).** Registered native operations and narrow replay/purpose/support controls remain delivered; provider-selected input identity and transitive-support read pins are not complete. Registration is not deployment/adoption or qualification. |
| DDO-05 frozen demand, discovery, selected dependencies, support rebind/recovery and fan-in | **Delivered resolver; dependency-complete native readiness open, 2026-11-14.** Selected closure, complete-context discovery and fan-in have scoped controls, but CA-08/09 affect native attachment/read premises. Actual selected-view child fulfillment remains the existing DDO-06/07 failure, not a newly closed foundation claim. |
| Delivered DDO-06/07/08 execution and family increments | **Bounded implementation and scoped Tested results, 2026-11-14; broader packages open.** Owned streams, typed CPU coroutines, shared provider custody and explicit retained-demand CLI execution are integrated. The restricted positive CLI route passes. Default source/book/phase0 workflows and complete family/provider population have not switched; current native family qualification is cancelled with residual failures. See the current execution account below. |
| NetworkX amendment | **Required DDO-01–05 contributions complete.** Compiled v3 projection interpretation now governs the delivered kernels/consumers; later impact, comparison, serving and export integrations remain open. |
| DDO-06–12 wider replacement, reuse, serving, preservation/adoption and assembled qualification | **Open; no enclosing completion certified.** Existing migration/retirement obligations remain required. APIs or tests calling target helpers do not establish that ordinary entry points migrated. |

### Finding disposition

This table owns current disposition. DDO-CA-01–05 retain their original identities and source-review
mapping; the original [reflection probe](../design_review/evidence/2026-11-13_ddo-completion-audit/README.md)
and all earlier receipts remain unchanged. CA-06–09 are plan-local completion findings, not new broad
design-audit findings. CA-08/09 are the open implementation gaps added by the 2026-11-14 reassessment.

| Audit finding | Current source evidence and consequence | Required closure and package owner |
|---|---|---|
| DDO-CA-01 (F04/F12) | **Implemented; scoped Tested, 2026-11-13.** Captured slices retain per-function standard builtin references. Ports authenticate actual captured dictionaries and consumed bindings, including helpers/generated methods/stream pulls; nonordinary mapping subclasses and unsupported source namespaces refuse. | DDO-01/02/03 repair covered by source/compiler/ports263 `3a40d30d38934ef189b1c6b1ba547379`, final ports70 `abf6354897214e21b53e908235a24f59` and the final historical/subclass controls in the resumed receipt. No broad runtime recipe salt. |
| DDO-CA-02 (F07/F13) | **Closed at DDO-04 boundary; scoped Tested, 2026-11-13.** Post-lock exact committed-receipt reread retains immutable differing-intent refusal and original attribution. | Exact and overlapping replay, conflicting overlapping intents and publication passed in native `07021252b8464b599428d0d3655957e0`; original failed outcome remains visible for unrelated setup/test-input corrections. Later DDO-06/12 assembled execution is separate. |
| DDO-CA-03 (F13/F14) | **Repair present; scoped Tested; acceptance open.** `_check_batch_active`, `orchestrate/data_operations.py:98–111,688–690`, retains useful siblings and cancels/drains when none has confirmed authority. `8efecb9296e1459ca10a66fdd2191bcb` passed three batch-activity controls: two ownership-state controls and **one actual hung spawned-process retirement case**, not three physical cases. Broader CPU/activity passed 9/9, `515f429636594afe8aa5cf6c99b64675`. | DDO-06 retains assembled qualification and its other execution/stream obligations. No source evidence found that reopens the original batch defect; do not overstate the physical-case count. |
| DDO-CA-04 (F11/F13) | **Closed at DDO-04 boundary; scoped Tested, 2026-11-13.** Actual purpose principals enforce affected kind universes for fate, expansion, revocation and pending/zero-output reads. | Native purpose and unchanged-fate/trust controls passed in `07021252b8464b599428d0d3655957e0`; current-source replacements and inventory reconciliation are below. No new purpose defect remains in this scope. |
| DDO-CA-05 (F05) | **Closed; scoped Tested, 2026-11-13.** Population ambiguity compares complete authenticated subject/original/scope context using JSONB meaning. Distinct page1/page2 members sharing a local subject reach child publication; duplicate complete contexts including equivalent numeric scopes refuse. | Frozen `semantic_ddo_projection_v1`; final native replacements10 `09ecb5f88e5f476a9ed8bcd226e30829` passed, including independent null-scope controls and actual captured-source publication/resume. No frozen predecessor was edited or deployed. |
| DDO-CA-06 (NetworkX I01; F01/F02) | **Closed at DDO-01/03 boundary, 2026-11-13.** Effective v3 archives typed compiled projection definitions. Semantic graph validation and demand freezing consume their interpretation, preserving role occurrences, isolates and selected/potential distinctions. | Independent projection/demand/identity controls plus integrated263 pass. Later support/impact/serving/assessment integrations retain DDO-04/08/09/10 owners; their open scope does not reopen this prerequisite. |
| DDO-CA-07 (hard-target retirement; Python I05) | **Former v1 authoring/decoder/alias retirement remains implemented; reassessed 2026-11-14.** Current format is v4; historical v2/v3 exact reading serves retained archive interpretation, with explicit current admission/projection/Python-port refusal. No current v1 fallback remains. | TS-19 helper removal is retained, not repeated. Preserve frozen migration/evidence bytes and required archive reading; the former remaining-v1 allegation in the retirement inventory is corrected below. This is not universal completion of caller/reader retirement. |
| DDO-CA-08 (F02/F10/F11) | **Open implementation gap; source-inspected, 2026-11-14.** `sql/data_operations.sql:600` unconditionally refuses roles requiring provider identity, and `data_binding_rows` emits NULL provider identity. The compiler/Python identity accepts that contract. `contracts-and-compilation.md` “Shared key/admission projection” and demand identity require selected provider identity when the consuming contract requires it. Earlier unsupported-profile refusal is a limitation, not an accepted exclusion. | DDO-03/04, consumed by DDO-05/07/09: derive provider identity from authenticated producing custody and carry it through candidate, semantic request and native validation. Closure requires independently expected positive native attachment and changed/forged-provider refusals. No such check was run by this audit. |
| DDO-CA-09 (F07/F11/F13) | **Open implementation gap; source-inspected, 2026-11-14.** `sql/data_operations.sql:1320–1334,1585–1591` pins root/direct-SourceSet epochs only, whereas `ddo_lock_support:125–142` locks recursive computational/original support scopes and validity recursively consults revocations. An A output supported transitively by B can change admissibility after B revocation under an unchanged A-only read pin; nonzero B epochs can also fail fresh attachment's complete-support containment check (`:702`). Products/support requires stable transitive scoped trust assessment throughout pinned reads. | DDO-04 with DDO-03/05/09 readers: acquire/validate the relevant transitive support scope closure consistently for reads, continuation and binding. Preserve the stronger publication lock/containment guard. Closure needs a three-source/two-hop case with stable continuation, transitive revocation refusal and fresh acquisition after an upstream nonzero epoch. No live reproduction was run. |

### Hard-target retirement and closely related adjacent code

**Repository-wide static retirement assessment · 2026-11-14.** Dispositions below identify future
implementation work; this audit deletes no code. “Remove now” means no missing target capability
was established for that bounded removal, not permission to delete independent algorithms, records
or generated vocabulary with a similar name. Consumer migration includes imports, registrations,
configuration, wire/generated surfaces, mechanism-only controls and operational instructions.
A former caller's continued existence is a migration obligation, not indefinite compatibility policy.

| Disposition / responsibility | Actual consumers and implemented target | Existing owner / complete removal or settling requirement |
|---|---|---|
| **Remove now — unused pass-runner scaffolding** | `orchestrate/runner.py:15–42,60–62`: local `PassOutcome`, `PassReport`, `PassRunner`, `Evaluate` and `Graph.pass_config/m19_config/evaluate_config` have definitions but no repository consumers in inspected Python/scripts/services/domain sources. | DDO-06/08. Remove those symbols/fields and stale pass descriptions. Preserve live `Graph.stages`, `policy_propose`, `for_kind`, `Step`, `unit_view` and the distinct generated **core.vocab.PassOutcome** enum. Confirm indirect/injected constructor consumers before applying; directly affected graph/default controls are the later verification boundary. |
| **Remove now — inert phase0 method descriptors/config entries** | `phase0.py:93–118,152–154`, `orchestrate/domain_methods.py`: EvaluateStub/ConsolidateMethod/RulesMethod are registration-only descriptors; actual consolidation uses `semantic.domain_operations.consolidate_cut`. Statistics/toy `methods.yaml` still name their three configs. | DDO-06/08. Remove descriptor classes, registrations and only `consolidate.claims`, `validate.rules`, `evaluate.score` dead entries together. Preserve independently consumed aliases/math sections and actual consolidation/rule/evaluation kernels. Check registry/default-source behavior when implementing. |
| **Remove now — HTML-only profiling adapter** | `ingest/profile_segments.py` has only the `tests/ingest/test_renditions.py:23` importer; current `ingest/methods.py:104–113` and declared source profile use `semantic/source_profiles.source_profile_values`. | DDO-07 / PDF-10 retirement. Remove obsolete production measurement/profile adapter and mechanism-only archive test dependency; port any useful independent interval/math expectation to native fixtures. Preserve historical data. |
| **Remove/reduce now — orphan HTML profiles and one-time fixture builders** | `sources/siegrist.yaml`, `sources/toy.yaml` retain DOM selectors; code/test searches find no profile loader and `test_stage_b.py:85` asserts SourceProfile absent. Current pack configs select PDF. `fixtures/s0/build.py`, `fixtures/trace/build_segments.py/build_targets.py` reconstruct old renditions; only documented one-time builder links found. | PDF-10/11, cross-linked DDO-07/11. Remove active orphan profiles and obsolete executable regeneration instructions/builders once their finite fixture inputs are retained; fix toy README's implication of required historical HTML read compatibility. Keep authored fixtures, provenance, plans/evidence and inert records. No protected answers or historical bytes are rewritten. External invocation of these repository scripts is unknown, not a maintained runtime guarantee. |
| **Remove/reduce current HTML synthesis; preserve identity kernel** | `_cut_input`, `semantic/domain_operations.py:902–937`, supplies a native descriptor with `rendition_id=None`, macro-only content, or None. Yet `_project_cut:1457–1530,1554–1587` keeps author_markup/RenditionContent/project_markup and LocatorIndex fallbacks; `_evidence_link:363–376` keeps a rendition tuple. NativeProposalFrame/native_statement_source already supply current native interpretation. | DDO-07/09 with PDF-10/11 and DDO-11 custody reconciliation. Remove obsolete current synthesis/fallbacks, retaining truthful unsupported/partial standing for historical observations. Preserve `source_projection.statement_identity` used by current native statements/PDF journeys; retire `project_markup` and its HTML-only positive test rather than deleting the whole module. Reviewers differ on whether retained rows can reach the old branch; no live-data claim is made and inert rows stay preserved. ADR-0040 withdraws maintained HTML-result interpretation, not original custody. |
| **Reduce now — historical math context chain** | `methods/math/context.py`, `source_context.prepare_source_math`, `spans.math_spans/read_spans` are reached only through the historical/test chain. Current `math/native.py` and `math/prepared.py` still use `_heads`, EarlyFunctionDeclaration, span types and extraction helpers. | DDO-08/PDF retirement. Remove or relocate only historical context/locator adapters and their mechanism tests; preserve native finite math helpers and independent expectations. Do not delete these mixed-use modules wholesale. |
| **Migrate available target, then remove — ordinary drivers/selection/recovery** | Default CLI routes still reach source_operation/phase0/semantic registry and method.select; target DemandPlanner/NativeDemandExecutor and admitted bound/hydrated ports exist. `characterization.py:354–379,527–575,780–840` retains name/dependency/device maps and recovery anchors. | DDO-06/07/08. Migrate source/book/phase0 and reporting/cancellation/resume, including injected registry roots. Remove private selector/digest authority, SourceOperationLink grouping, manual dependency/freshness maps, stage permits and `max_active_stage_runs` only with their actual callers. Current child-binding failure and CA-08/09 are concrete shared prerequisites. |
| **Migrate available target, then remove — legacy CPU facade/dispatch** | `cpu_execution.py:128–175,201–235,299–352,395–449,857–864,1107–1256` retains packets, _KernelReader/_KernelRun/_KernelContext, method dictionary/default legacy dispatch and cpu_method_plan/run_cpu_method. Formal/construction/contextual ordinary callers remain. Target acquired PythonCPUDescriptor calls and formal/construction/context ports exist. | DDO-06/07. Move those callers, remove old packets/Reader facade/dictionary/defaults and mechanism controls together. Retain CPUExecutionScope, real cancellation/retirement, byte reservation and receipts. Separately assess shrinking specialized formal packet dispatch (`:358–393,412–413,866–869`) onto the generic prepared-kernel call while preserving its timeout, kernel and validation: this is an improvement opportunity, not a new completion defect. |
| **Migrate available target, then remove — combined native provider route and dual internal references** | `methods/native_evidence.py:425–710` still combines producers; separate annotation/canonical/HanLP declarations and shared hosting exist. `data_product_reference.py:90–115` accepts both semantic product/member and task refs; model_characterization, constructions, formal/contextual readers and StructuralInput consume the union. Actual semantic DeclaredStructuralSource/product/contribution refs already exist. | DDO-07/08, DDO-10/11 final reference retirement. Move ordinary publication/readers onto distinct target facts and real semantic refs, then remove combined routing and current dual-reference dispatch. Keep semantic conversion algorithms and any explicitly sealed old reader. Never synthesize legacy task/view IDs for target facts. |
| **Blocked on missing target population — learned/M1/math/structural/authored/external** | `ci run parsers/interpret` still reach PM2 stage descriptors; interpretation_authoring builds its own registry/graph; old agent queues remain. Target learned and M1 candidate factories exist, but M1 formal/named rules explicitly refuse without real inputs. Math declared kernel is not full producer acquisition; dossier/predicate/scoped/definition/artifact/clause and finite/contextual/external families remain unfinished. | Existing DDO-07/08 inventory in the current increment account owns these, not new duplicate findings. Preserve exact model questions/raw observations/numerical policy and specialized algorithms. Deliver the missing producer/input/effect contract plus immediate consumers, then remove each old route. Declarations and selector-only APIs do not establish a replacement. |
| **Blocked on missing public target — Reader/MCP/query/export/replay/cursors** | `serve/journey.py:48–137`, read.py, CLI query/export/eval, semantic_server, selected_source exports and review bundles retain run/task-origin selection. No DDO read-owner integration was found in serve/intervene; native CLI demand inspection is narrower than accepted DDO-10 public read/export behavior. | DDO-10 with DDO-09/11. Build pinned public read/resource/query/export/verify/detached replay and cursor contracts first, then migrate all registered tools/query recipes/export readers. Do not remove supported public behavior on the assumption that internal demand inspect is equivalent. |
| **Migrate then remove — copied task reuse/consolidation meaning** | `semantic/operations.py:283–345` create_task twin lookup uses configuration/hash/release/runtime/realization and task_dependency_scope; execution_guards still validates reused_task_id. Cut and public readers dereference old origins. Declared request/product/support machinery exists but full currentness/substitution consumers are incomplete. | DDO-09 with DDO-06–08/10/11 callers. Replace old reuse equality and copied task representation with declared semantic requests, exact consumed bindings and admitted support substitution; retain authentic original execution lineage, current trust and independent nonreuse controls. |
| **Reduce to required sealed reading — archives/runtime/old bundles** | archive_reader common authentication supports releases, CPU/inspection capsules; runtime_binding_store:68–85 has a real missing-runtime run fallback. Legacy runtime binding refuses current execution. Legacy structural source helpers remain used by review_bundle and replay readers and explicitly refuse target refs. | DDO-10/11. Inventory exact retained readers/recovery consumers, migrate current exports to explicit runtime/support pins, then remove current fallback entrypoints and retain only required sealed interpretation. Existing census proves classified roots, not byte integrity or mandatory rich current-reader compatibility. Required unknown custody blocks destructive steps, not removal of unrelated dead scaffolding. |
| **Correct inventory, retain justified archive reading — CA-07** | Current v1 authoring/decoder/alias removal is implemented; `data_operation_model.py:761–800` reads current v4 and historical v2/v3 for archive_reader. Model admission/projection/Python-port checks refuse historical current execution. The previous retirement row cited removed v1 code. | CA-07 remains closed at its scoped boundary; remove the stale remaining-v1 allegation. Consolidate v2/v3 only after identifying actual sealed archive consumers and preserving their interpretation. No current execution fallback is justified by frozen migration retention. |
| **Unresolved — assessment-era adapters/old reference applicability** | characterization_assessment:927–929,1344–1361 uses a legacy_structural_graph for cases without semantic refs; record_gaps:214–280 compares frozen original-side grades; CLI golden passes legacy_split. Protected frames/grades have genuine custody. | DDO-10/11. Map exact reference-frame applicability and reviewed native correspondence before removing old pair/singleton interpretation. Preserve legitimate original-grade comparison and protected-answer boundaries. No automatic regrading or claim that the word legacy proves obsolescence. |
| **Additional reduction opportunity — legacy schema/interchange compiler** | relational.compile_metadata defaults to legacy at schema/relational.py:595; interchange.compile_interchange:236–257 and schema tests still use it. model.compilers:651–656 retains its version marker; current native_source imports interchange._sql_arrow. | DDO-01/10 coordination with schema owner; not a newly failed accepted obligation. Separate genuine current Arrow/type conversion and compiler-custody markers from unused legacy table projections; migrate the finite consumers before shrinking the legacy target. Keep current generated DTO/vocabulary consumers. No whole-module deletion inferred. |
| **Justified retain / not retirement candidates** | Query compatibility is target-required cross-release semantic binding, not archived Python execution. Current sentence/text/math kernels, protected reference comparison, CPU/provider custody, ops/PostgreSQL and scenario seeds have real consumers. Chandra's HTML is PDF-recognizer output; docs HTML is publishing. Nemotron's independent environment/worker preserves vendor/runtime and cancellation custody. Rust is a starter, with no competing DDO engine found. | Keep these capabilities. Do not remove a dependency solely because an obsolete adapter also imports it; check all current uses and regenerate through the owning generator. Frozen migrations, archived artifacts, evidence and plans stay exact. |

**Coverage and limits:** source inspection covered production Python packages, ordinary and explicit
CLI roots, registered MCP/query groups, domain/source configurations, generators, runtime/native SQL
and model declarations, version readers, tests/fixtures/builders, services, ops, scripts, Rust and
publication/plan navigation. Dynamic injected registries, external plugins/script invocations, live
persisted rows and external retained bundles were not exhaustively enumerated; their unresolved
edges are stated in the relevant row. No live database census or protected/source body reads were
necessary for these conclusions. Absence claims are bounded repository searches, not universal proofs.

**Execution order when implementation resumes:** repair CA-08/09 and the existing child-binding
obligation; remove independent dead scaffolding/profile adapters without waiting for full adoption;
migrate ordinary callers onto available target ports/CPU/reference types in coherent slices; deliver
missing family and public read contracts before removing their predecessors; verify exact preserved
custody before the final sealed-reader/cutover retirement. Pure static-extraction reuse retains its
existing Proposed follow-up. Future verification targets the changed consumers and independent
semantic/refusal expectations; this audit does not authorize another test run or new retirement gate.

### Verification, qualification and benefit limits

This audit is source-inspected; it does not claim new functional reproduction. Existing failed,
interrupted and passing receipts remain immutable and keep their original source/context bounds.
The 2026-11-13 builtin collision reproduction and repaired foundation controls remain historical
scoped evidence; they do not exercise CA-08/09. The current cancelled family attempts and lost
worker receipt limitation are recorded in the current increment account. Missing benchmarks alone
are not an implementation defect. No production repair, database adoption or test campaign is
performed by this audit. Remediation and its later qualification remain with the owning packages.

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

**Current boundary, corrected 2026-11-14:** DDO-00–02 retain bounded foundation completion; DDO-03/04 native contracts require CA-08/09 and DDO-05 dependency-complete readiness remains open. DDO-06 owns native
physical/stream execution and production driver integration; DDO-07/08 own actual family/caller
migrations, DDO-09/10 reuse/serving and ongoing interface adoption, DDO-11 preservation/deployment/
cutover and DDO-12 assembled qualification. The latest increment is concluded; this audit does not resume implementation. Their
legacy routes are removed with their actual migrated consumers, not by erasing historical artifacts.
Preserve the interrupted `2a1fdebfd77749378ce7d4598cba5d68` campaign and failed native predecessors;
only the scoped replacements and explicit inventory corrections below establish this closure.

## DDO-00–05 resumed execution and scoped acceptance · 2026-11-13

The operator authorized the detailed remaining-foundation execution after the test-system
handoff at `94539f712`; the operator explicitly waived repeating its interrupted full campaign.
This account owns the resumed scope. DDO-00 preparation remains complete; new changes reconcile
its inventory/contracts without repeating its census. Later DDO-06–12 migrations/adoption are not
pulled forward. The existing failed/interrupted receipts remain retained with their original scope.

Implemented contributions:

- CA-01 source closure and runtime captured-builtin authentication, including exact ordinary
  dictionary semantics, inherited/generated helpers and stream-pull checks.
- CA-06 effective v3 projection interpretation consumed by compiler topology and selected-demand
  closure; canonical body/parameter encoding and JSON context meaning are unchanged.
- CA-07 current v1 authoring/decoding and unused alias retirement; only exact historical v2
  reading remains for retained releases/candidates and cannot gain current execution.
- DDO-03 finite source-migration intent, exact owned before/after inputs, proposed model
  compilation, per-consumer standing, qualified native LibCST composition and existing file-effect
  custody. Unsupported/dynamic/re-export/name-collision sites block apply. Symbol moves preserve
  callable contracts; signature/context migrations remain with their actual DDO-07/08 consumers.
- CA-05 complete-context JSONB population uniqueness; actual native scalar/population consumers
  retain distinct scoped members. Release admission now delegates once to its guarded native
  definition-admission owner rather than verifying the catalog twice.

The [native authoring record](../design_review/evidence/2026-11-13_ddo-projection-context/README.md)
owns exact attempts and frozen successor `semantic_ddo_projection_v1`. Final preview
`10a81274757548a084cad38f26fd10da`, rollback-only candidate `7ccd25c86a534675a5db847dc2d5db27`
and registration `7c5d74466b734072bc47ffe8848516b7` **passed**. Exactly four native body
transitions/zero ordinary schema operations were inspected. Source-only preparation guards added
after registration stale that preview's generator; the four registered files remain exactly verified.
No deployment/activation occurred; the persistent working database retained its acquired identity
and revision. Future adoption reacquires a fresh preview/target under DDO-11.

**Passed, scoped 2026-11-13:** `uv run ci test --json --` the source/compiler/ports/model/projection/
demand/preparation selection263, `3a40d30d38934ef189b1c6b1ba547379`; pure binding/wire/parameters/
source-set/subject/population/consumer selection108, `792326c6afa247acbd2a5e48843b5186`; final
ports70, `abf6354897214e21b53e908235a24f59`; source-migration suite19 including keyword-contract
refusal, `c498044acb2e4fdea7d662f285434c60`. Earlier final preparation/preview source selection32
passed `8c0cba62027143978612d6b1ff149754`; the new guards receive their narrower replacements.
`uv run ci check --only types --json` passed `1aa76272c86f4293a864e4b11012deb6`;
`uv run ci check --only lint --json` passed `b46defb5ea8a4c6395514f274b524e14`.

Independent assembled implementation review **Accept scoped**, by source inspection, including
reinspection of relative-import normalization, destination-scope refusal, semantic preparation
staleness, callable contract preservation and captured mapping-subclass refusal. Source preservation
and model semantics use independent expectations, not generated-output agreement alone.

**Native scoped acceptance complete, 2026-11-13:** initial native selection94
`07021252b8464b599428d0d3655957e0` remains **failed**, with91 observed passes, one seed setup
refusal and two invalid newly authored typed-population inputs. Final replacements10
`09ecb5f88e5f476a9ed8bcd226e30829` **passed**: the failed setup identity, corrected typed
population cases, final-port actual production source publication/resume and four independent
null-scope controls. Existing replay/principal/recovery/consumer passes remain applicable: their
production paths did not change in the replacement. No mocked provider is counted as native evidence.

The raw coverage report correctly remains failed against the original inventory: its sole
unresolved identity `test_discovery_same_local_subject_distinct_contexts_reach_child_publication[scopes1-population]`
was an invalid null/string population body under the explicit `Scope{page: integer}` contract.
It is **removed from the current required inventory**, not relabelled passed; null behavior is
covered by the separate supported null-scope contracts above. Equal-number ambiguity uses an integer
body plus a value-equivalent numeric member header so the actual closure guard is reached.

An assigned-work seed validation race was corrected by reusing the existing bounded backend-exit
waiter, retaining refusal for persistent sessions and never terminating backends. Focused controls6
passed `68fdc68fe1be422191a231671ce8e48d`, and the failed native setup identity passed in the
final replacements. The original backend disappeared before diagnosis; no confirmed connection
leak is claimed. Final pure port historical-format and mapping-subclass refusals2 passed
`564cfbcfb212476cbf9f8def8b6bb939`; authored-input closure/keyword-contract controls2 passed
`2ce0522bf5e94a96835c43ae7338ccf8`.

At the 2026-11-13 acceptance boundary, DDO-00–05 implementation and scoped retirement were reported complete. The current 2026-11-14 audit supersedes that conclusion for CA-08/09 native contracts and DDO-05 dependency readiness; earlier scoped passing evidence remains valid only for its exercised behavior.
This is not DDO-12 assembled qualification. TS-21 retirement controls are transferred only for removed
mechanisms; TS-22 remains DDO-12's complete evidence-mapping obligation. The interrupted651-case
campaign is not blindly retried or promoted to current qualification. No quantitative benefit or
DDO-06–12 completion is claimed.

**Documentation publication:** `uv run ci docs check --json` passed `c5d40d6ecf3e4a3890a4329cb02edb95` (1,256 canonical pages, zero link errors); root `just turn-end` completed without final source mutation. Commits `b5d7c63ce` and `ffea0bd5f` contain the checked implementation; subsequent checkpoint edits change documentation only.

Worktree-local managed stores and integrated patches are preserved, with original namespaces, under `build/ddo-worker-results/{builtins,projections,native}` before removing this execution's temporary worktrees. Read an older worker receipt through the corresponding `CORPUS_CI_RESULTS` store; current qualification uses the root receipts above. Pre-existing non-ancestor worktrees are preserved.

## DDO-06–08 authorized execution · 2026-11-13

Operator-authorized scope is DDO-06–08, starting at `2fbff1797`; DDO-00–05 foundations
remain accepted. Execution is in progress, not completed by this authorization. The operator
selected terminal settlement for owned streams: stage bounded items privately and publish only
one declared completion/population after valid termination. Failed/cancelled prefixes confer no
fulfillment. Effective v4 will carry explicit settlement and captured consumer capabilities;
real historical interpretations stay exact and frozen predecessors are never rewritten.

The shared executor/transport comes first, then authentic ordinary-driver/selection context,
then producer-plus-immediate-consumer vertical migrations and retirement. The first actual M1
migration uses explicit source/call correspondence; generic `method.select` receivers cannot be
rewritten to M1 by spelling. Native Demand, pinned read/trust and bounded hydration supply the
context. Source/primary and downstream/authored families integrate against that common route.
DDO-06 closure includes its actual ordinary callers, not helper-only delivery.

Only focused new/affected checks run. After a repair rerun only failing identities, never the
full selection or an interrupted campaign. No full test campaign or repository health sweep is
scheduled. DDO-09/10 retain broader reuse/serving/model-update interfaces; DDO-11 retains persistent
deployment/adoption/activation; DDO-12 retains assembled book/provider/fault qualification.


### Native execution frontdoor increment · 2026-11-13

`ci demands execute DEMAND --source-root ROOT` now resumes the exact retained intent through
NativeDemandExecutor. Source root selects physical locations only: retained release inputs,
runtime custody and actual callable admission remain authoritative. Release loading returns its
verified bundle/dependencies alongside the prepared release so execution does not reacquire and
recompile the archive twice. The database connection closes before execution/capacity waits.
Managed output retains pinned native state, bounded receipt count/standing and partial results
on execution failure; successful command delivery does not imply all obligations fulfilled.

**passed:** exact retained-source native execution/resume1 `262a9c118abe45b2bcc392c79bf03008`;
CLI pending-fate/correlation1 `3b2b725894f4449e86acac69da0c3b9a`; help-without-settings passed in
initial `80d813cd08344b8a8c61e084faaad6a0`. That initial receipt remains failed: its native setup
observed a worker's premature v4 source edit against the v3 kernel. The edit was moved to the
isolated worker checkout and only the failed identity was rerun. These bounded receipts establish
the new execution frontdoor, not ordinary default-source family migration or DDO-06 closure.
Source/default/registry callers and full family contracts remain active integration work.

### Shared contract, source migration and native successor integration

**Implemented, bounded checks below, 2026-11-13:** current effective v4 carries explicit terminal
settlement, captured consumer-selection and prepared-factory correspondence. Historical v2/v3
reading stays exact; current admission does not reinterpret old stream bytes. Primary factory
methods are colocated with their operation owners and freeze sentence/HanLP configuration into
captured custody; the combined input helper is acquisition, not another producer-selection registry.
Actual family publication/default callers remain in progress.

Finite `call_context` source migration supports explicit old/new owner correspondence, exact source
call expressions and required lexical context. Declaration-owned old selectors retain a source/
Griffe/class-colocation proof without gaining execution authority. Before-owner checks are not
weakened globally. Focused migration5 `ac6100ba6f5e44159fda3487e04d3907`, preview/apply2
`e432b608dbdc464aa7db0f16b127b33c`, old-selector proof1 `3b3b80de70a642cfb831251362779fc8`
**passed** in the worker source context. The actual M1 producer/ordinary-caller migration remains
open; source transformation capability alone is not adoption.

Authored SCC classification uses the existing topology owner: actual cyclic members, blocked
cyclic descendants, unrelated publishable claims and unavailable premises stay distinct. Independent
pure1 `5f55bc36db1b4ee59359eff7e8a68709` and native1 `027015cc4c204c73993a0c9d1825064f`
**passed**, before the v4 guard integration. The repaired claim semantics do not depend on that
archive-version guard. These bounded checks do not qualify all DDO-08 operations.

The [owned-execution native record](../design_review/evidence/2026-11-13_ddo-owned-execution/README.md)
owns preview `7140393ec9e343f8ad0d46b1130f9ede`, rollback-only candidate
`94b54246db1e44768860589106f1a580` and registration `7c84e38e315a42f0b333e0a38545488b`:
**passed**, two body transitions/zero ordinary operations, unchanged owners/ACLs. New frozen
`semantic_ddo_stream_v1` follows `semantic_ddo_projection_v1`; no persistent deployment/activation.

### Producer and physical-owner integration · 2026-11-14

**Current increment concluded by operator; DDO-06–08 remain open.** All current worker edits
are integrated on `main`, merge conflicts are resolved, and all six auxiliary worktrees are removed.
Branch references remain. The three current workers have finished. No further implementation,
tests, full campaign or repository health sweep is part of this closeout. Remaining qualification
was cancelled explicitly by the operator; likely interaction with remaining structural changes is
an investigation, not an established explanation or closure.

#### Integrated behavior and current family boundary

**Implemented / Interface-checked, 2026-11-14; scoped Tested only where identified below.**
Owned streams retain private prefixes until valid terminal settlement. Typed scalar CPU coroutines
use the existing process/capacity owner; uncertain submission retains credit, and physical drain
precedes native failure settlement. The invocation shares borrowed native-host residency, original
parent byte credit, provider coalescing and nested physical-cohort/logical-fence receipts. It does
not create a pool or independently reserve the same work for each family. Actual generation,
request/task/attempt and scatter membership remain authenticated at native retention.

The existing `ci run --demand ID --source-root ROOT` and `ci demands execute` frontdoors share one
retained-demand executor, project checks and exact numeric JSON. Restricted positive execution
now passes. These explicit routes do not establish default source/book/phase0 migration. Original
PDF capture/support uses its actual sealed product/derivation and receipt, with no latest lookup.

Grouped record witnesses match all comparisons against one actual input member. Exact `@product`
and `@member` headers and source sets retain genuine product/member/context pins. Unordered source
positions remain semantic/source positions; dense physical ledger slots are separate. Exact pinned
cross-demand facts require current read/trust/project/kind/producer admission. Execution roots are
not every input context: explicitly frozen source views may be admitted under an authenticated
whole-original-document root of the same document. Declared subject-field association retains each
view's own scope through binding and support checks. Original facts retain authentic source/admission
identity and have no invented computation episode. Current selected-view child fulfillment still fails.

| Family/responsibility | Integrated increment | Remaining obligation |
|---|---|---|
| Source and primary | Original document addressing and selected-view discovery; source profiling; one actual spaCy inference retains full annotations for canonical/construction consumers; compact summaries and separate source-only/full composition profiles | Resolve the two-view child binding failure; complete family/caller population and actual provider/native journeys; migrate ordinary drivers and retire superseded routing |
| Learned primary | Declared Maverick, DiPO, D1 source/candidates and GLiNER cues/function factories; contextual CPU composition consumes their actual facts and retained formal/construction facts | Complete full profiles and authentic provider/native qualification; ordinary registry/default caller cutover |
| M1 | Original resumable candidate kernel, existing GLiNER questions/failure dispositions, actual source/context selectors, shared provider coalescing and CPU coroutine plan; frozen numerical profile has stable typed timeout default | CPU and provider native journeys are incomplete at cancellation. Formula syntax and named rules explicitly refuse until their formal/rule inputs are bound. Finite and contextual interpretation families remain unstarted |
| Structural | Declared comparison/condition factories use actual source, contribution, report and source-set pins; both M1 and structural capture the actual shared prepared-call adapter source | Genuine predicate/dossier/definition/relationship predecessors, ordinary callers and positive native/CPU qualification remain open |
| Math | Shared original reading kernel consumes actual source coordinates and retained syntax; explicit context preparation; clipping/foreign-coordinate controls | Full mathematical producer/context acquisition, normalization, symbol scope, scoped relations and downstream definition/artifact/clause/effectful migration remain open. The standalone pure-kernel context control does not qualify target producer acquisition |
| Compiler and custody | Closed supplied JSON-schema kinds with explicit nominal namespace; real custom validators remain producer assets/runtime code; callable recompile reuses authenticated effective-kind facts; keyword labels are not lexical loads, argument values remain checked | Complete consumer adoption and shared static-preparation efficiency work below; source/body-change refusal stays required |

Historical structural replay explicitly narrows genuine legacy sources and refuses target references
at the old task-based replay/export boundary. No target reference is relabelled with invented legacy
row/view/task identifiers. This preserves the unfinished DDO target rather than reverting its model.

#### Registered native successors

Every row is **passed for preview, rollback-only candidate, typed operation/SQL inspection,
registration and evidence finalization, 2026-11-14**. Authoring is separate from functional/provider
qualification. The chain follows `semantic_ddo_stream_v1`; frozen predecessors remain exact.

| Revision and evidence owner | Native transitions / ordinary schema operations | Purpose |
|---|---|---|
| [`semantic_ddo_context_v1`](../design_review/evidence/2026-11-14_ddo-context-witnesses/README.md) | 29 / 0 | Qualified context and grouped witnesses |
| [`semantic_ddo_inputs_v1`](../design_review/evidence/2026-11-14_ddo-input-custody/README.md) | 15 / 0 | Exact headers/source sets, unordered input custody, pinned reuse and provider receipt fences |
| [`semantic_ddo_admission_v1`](../design_review/evidence/2026-11-14_ddo-target-admission/README.md) | 3 / 0 | Target-v4 projection admission through the common physical/catalog guard, without requiring a fabricated legacy execution model |
| [`semantic_ddo_acquire_v1`](../design_review/evidence/2026-11-14_ddo-execution-admission/README.md) | 5 / 0 | Admission-only selected definition/runtime hashes through `inspect_data_execution`; protected tables remain private; no per-port all-model native re-admission |
| [`semantic_ddo_sources_v1`](../design_review/evidence/2026-11-14_ddo-source-roots/README.md) | 4 / 0 | Authenticated selected views under document roots; EXECUTE on pure immutable JSON field helper for existing read/write/evaluator purposes, without PUBLIC/table grants |
| [`semantic_ddo_viewbind_v1`](../design_review/evidence/2026-11-14_ddo-view-bindings/README.md) | 3 / 0 | Respect declared subject-field association instead of discarding related scoped inputs |
| [`semantic_ddo_rolesup_v1`](../design_review/evidence/2026-11-14_ddo-role-support/README.md) | 3 / 0 | Same role-qualified context contract at selected original support validation |
| [`semantic_ddo_origeps_v1`](../design_review/evidence/2026-11-14_ddo-original-episodes/README.md) | 3 / 0 | Original-only input matching uses an empty computation-episode set; actual computed episodes remain exact and nonempty |

Persistent revision remains `semantic_bep_located_v2`, OID25921445/system7701811359771751232,
PostgreSQL18.7 port5434. No persistent deployment, activation, adoption or cutover occurred.

#### Verification and cancelled qualification

Commands and outcomes below are scoped receipts, not an assembled required-union pass.
Passing identities were not repeated after repairs. Failed root receipts and cancelled replacements
are retained; no mocked provider receives passed credit.

| Command / selected scope | Outcome and receipt |
|---|---|
| `uv run ci check --only types --json` | **passed**, `1a362a87875c4bcb8a4ccf86cfd32b4e`; whole configured project, zero reported errors/warnings after merged typing repairs |
| `uv run ci check --only lint --json` | **passed**, `fd289eb10b2e47fa9fda4c93cd9e8d5b`; Ruff E501 remains excluded |
| `uv run ci test` exact nominal/profile and CLI refusal selections | Earlier scoped **passed**: nominal6 `2fe947c7bfe24f1ab26c3564ef7f3486`, final compile1 `9751471c74fb4e20917cee812f6da793`, M1 producer5 `085bf5449db24044b0c8252f322f9788`, CLI refusal3 `5ef12800b44c48dea9ef44311fa43dfe` |
| `uv run ci test` native grouped-pin/frontdoor/fan-in selection14 and exact replacements | Original `b6ca89acc86b4b8a88799bb0373dd5ad`: **failed**,4passed/10failed. Replacement8 `c7f7988624644fca995a9f2ce27cb97b`:7passed/1failed. Later native8 `d2b37ff859e04575a6fb4ea48c01274e`:7passed/1failed, including positive grouped publication/fan-in, pinned reuse and provider logical-fence cases; native observation complete |
| `uv run ci test` restricted CLI positive plus five new/failing native cases | `cfd68fb63f434e3d91a9c9d7dff2cfe4`:1passed/5failed; the restricted CLI positive passed. `uv run ci test retry cfd68fb63f434e3d91a9c9d7dff2cfe4 --lane ordinary --json`: `e1a5233bcc97452a9ed21c89148964fa`,3passed/2failed; native bounded acquisition read and closed-/partial-empty discovery passed |
| `uv run ci test` exact retained-math controls and failed-only replacements | Existing3 covered by `6a33ea34504d48988c642f6f6615d05f` and `94c04d4e79214bd1a022d173e478d867`, **passed** at their composite scope. New clipped helper passed in `5b62cd272c9a4314acfcc320a8b772a1`; positive helper final replacement **passed**, `9e349159fed843ec83d0e652b0d46507`. These are kernel/coordinate controls, not complete math-family qualification |
| `uv run ci test` installed retry-collection diagnostic | **passed**, `f9926f049e88454fbc33c739c8bb7610`. Failed recollection retains diagnostics and reports functional execution not_run, rather than silently broadening the retry |
| `uv run ci test retry 09524c2757b1455b9a68655d6b2cdd7f --lane ordinary --json` | **Cancelled by operator**: `3696eb7a301c4cc1965aefe09b0f1ddb`,1failed/1incomplete of2selected. Two-view discovery produced two children, but both uses remained `awaiting-inputs` rather than fulfilled; the M1 CPU journey is incomplete |
| `CORPUS_PM2_NATIVE_TEST_ASSETS=/home/paul/corpus-structure/build/models/pm2 uv run ci test retry 1c816055350d4f848acc33988504a0b9 --lane ordinary --json` | **Cancelled by operator**: `ac02513cd05f42a587120c617ee3917e`,1incomplete. Assets prefix supplies the existing prerequisite; this does not establish provider execution or qualification |

Both final cancelled receipts have **settled custody**, retained logs and holds. Their managed top-level
outcome is `failed` with partial reporting (no SessionFinish after interruption), not `passed`.
Earlier root failure chains remain held, including `a5a2ea89cc34449aaefce5b9937214f5`,
`e3b9df8625694ea0b7e1999c91737ba3`, `eebb1bf36cee423ab6e20c8282e1f9f1`,
`09524c2757b1455b9a68655d6b2cdd7f`, and provider chain `9a1e99733b34412ebfede5365b6ea569`
→`4f01e8d48adc452bb83b5e5da53e74c2`→`9071d19fc0ac4ddc9d920a989c89262b`
→`f55bf882f4ee474ab1439ed7596659d4`→`e3e0218e61894202b266085025a377cd`
→`1c816055350d4f848acc33988504a0b9`. Latest source is `56377252f`; diagnostic source differs
only by subsequent SQL correction/immutable generated successors, not Python typing/lint changes.

**Worker evidence limitation:** ignored worktree-local managed stores were removed during cleanup
without copying their raw receipts into the root store. Code and branch references are retained,
but worker-reported controls (including structural3 `67b25da1b01046259680063b0f521ca4`,
structural replay1 `7722fa2ab7e24a28acbe420489430109`, and learned/M1 pure controls) are historical
reports with unavailable raw evidence. They receive no current inspectable qualification credit.
Root-wide types/lint and the root receipts above remain inspectable. Do not rerun passing identities
to repair that historical evidence gap. Retain needed raw managed stores before future worktree removal.

#### Remaining scope and efficiency follow-up

1. **DDO-06/07, current failure:** investigate why actual selected-view discovery children remain
   `awaiting-inputs`, including authentic original/computed candidate selection and complete-context
   binding. Preserve both scoped children and the frozen original selection. Remaining structural
   changes may affect this path; no causal resolution is claimed. M1 CPU/provider journeys remain
   incomplete, and their last fully reported failure was the shared binding-validator query repaired
   by `semantic_ddo_origeps_v1`. No further retry is authorized by this closeout.
2. **DDO-06, efficiency / Proposed:** reuse pure static extraction for identical captured inputs,
   while keeping native permission, source, and trust checks at their required boundaries.
   `data_operation_ports.python_port_identity` currently invokes `compile_data_operations` for
   each port correspondence over the supplied source collection. Share its immutable extraction
   product over its valid lifetime instead of re-parsing/recompiling an unchanged collection for
   adjacent ports. Use the existing pure-preparation pattern; a bounded `functools.lru_cache` over
   immutable inputs is a concrete candidate, not an adopted implementation. Include exact schema,
   declaration bytes, Python sources/filenames/stubs/boundary contracts/interpretation, effective
   nominal definitions/vocabularies and relevant analyzer/implementation context. Honor override
   bypass and source/body/config/context invalidation. Keep database permissions, runtime custody,
   read/trust epochs, native admission and provider outcomes outside that pure cache. Preserve
   independent source/body-change refusal. Address this shared acquisition responsibility before
   restarting wider qualification; expected reduced repeated work is qualitative, unmeasured.
3. **DDO-06/07/08:** migrate default source/book/phase0 callers and complete the supported family
   inventory above, then retire superseded registries, four private selectors/input digests,
   handwritten dependencies/stage permits and legacy CPU/Reader dispatch with their actual consumers.
   Complete source/learned profiles, optional M1 formal/rule inputs, finite/contextual interpretation,
   math/scoped/definition/artifact/clause/dossier and external/effectful paths. Helpers and declarations
   do not close these obligations.
4. **Qualification and adoption:** scoped independent assembled review, complete applicable functional /
   actual-provider / nonfunctional union, serving, preservation and cutover remain with DDO-06–12.
   **not_run**: full `uv run ci test`, broad `uv run ci check`, repository health campaign and independent
   assembled review at this increment. Do not restart cancelled tests or expand validation merely to
   close the checkpoint. No push, deployment or activation follows from this closeout.
