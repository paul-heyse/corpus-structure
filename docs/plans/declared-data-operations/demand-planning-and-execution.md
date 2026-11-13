# Declared data operations — demand planning and execution

**Implementation plan · Proposed · 2026-11-12.** This supporting plan develops DDO-05 and
DDO-06 of the [standalone coordinator](../declared-data-operations_2026-11-12.md). The coordinator
alone owns package state, findings disposition, the shared native contract and assembled
qualification. This document contains no independent progress ledger.

The input is the [audited review](../../design_review/reviews/design_review_declared-data-operations_2026-11-12.md)
and its four supporting documents at `64dc6c3e6`; RC01–RC09 were explicitly accepted by the
operator on 2026-11-12. The total governing domain model is fixed. Implementation choices below
realize it; adapter callbacks and method-name cases cannot become alternative semantic authorities.
Other implementation plans impose no prerequisites or scope limits on this standalone series.

**Evidence:** Interface-checked by source inspection, 2026-11-12, against product source
`8c0f4f951` and the current tree at review revision `64dc6c3e6`. The following design is Proposed.
No database access, provider execution, tests or protected reference-answer reads were performed
to author this document. Paths below beginning with a package name are relative to
`python/corpus-structure/src/corpus_structure/`.

## Outcome and foundation assessment

A native Demand is the authoritative immutable request. It selects target contracts and explicit
producer/replicate choices over a frozen root universe, permits declared subject discovery, and
records each obligation's fate and exact selected support. The planner evaluates compiled
relations rather than reproducing domain policy in stage order. Execution coalesces equivalent
requests under one native producer owner, prepares privately, and publishes or replays an exact
retained completion. A resumed invocation consumes the same native Demand and settled evidence;
it does not reconstruct intent from current defaults, run options or expired CLI delivery files.

Useful existing foundations and required changes are specific:

| Current source | Preserve or replace |
|---|---|
| `orchestrate/semantic.py:1236–1315` | Preserve registration after actual immutable predecessors and update local state only after commit; replace configuration/name-based prerequisite cases. |
| `orchestrate/ready.py:78–145`; `core/work.py:32–49` | Preserve bounded replenishment and explicit exhaustion; remove method-specific admission and semantic readiness decisions from the physical driver. |
| `semantic/sql/execution_projection.sql:72–109` | Preserve native claim/lease/attempt fencing and `SKIP LOCKED`; run-scoped claims alone cannot deduplicate work across demands. |
| `semantic/claim_lifetime.py:29–112`; `semantic/operations.py:721–786` | Preserve separate renewal, private completion preparation and exact uncertain-commit replay; replace process-local-only recovery authority with DDO-04's retained immutable intent. |
| `orchestrate/characterization_recovery.py:38–126` | Replace the first-stage-run demand anchor/freshness salt with native Demand authority. Historical runs remain terminal. |
| `methods/native_host.py:43–73,253–364` | Reuse request/profile/host-generation association and owned host teardown; make submission uncertainty and retirement outcomes explicit. |
| `semantic/pdf_staging.py:42–73,223–235`; `orchestrate/pdf_streaming.py:1130–1165` | Preserve exact frozen-union replay premises; replace original-task-only adoption with authenticated native custody transfer. |

The existing resource mechanisms are candidates for reuse, not permanent physical boundaries.
DDO-06 may simplify them where one invocation-wide owner can replace overlapping capacity or
lifetime accounting. A semantic operation does not require a separate process, service request,
model instance, stage run or transaction.

## Consumed and delivered contracts

DDO-01–03 supply compiled operation definitions, canonical identities, generated typed ports,
recipe/eligibility/execution projections and capability admission. DDO-04 supplies the following
fixed trusted-model relations and native operations. Its owning definition decides exact
signatures, locks, schemas and privilege grants; this document specifies their execution use.

| Shared native contract | Consumption here |
|---|---|
| `ops.data_demand`, `ops.demand_use` | Immutable request registration; obligation discovery, selected fulfillment/support and explicit fate. Native demand registration and transitions use modeled operations, never unrestricted row insertion. |
| `ops.data_request` | Unique logical request including replicate, native generation and live physical task owner. |
| `ops.task` | Physical attempt/lease/holder fence; no independent replacement task engine. |
| `kb.data_product/member` and typed family projections | Admitted products, member/population discovery and exact input resolution without full-body hydration. |
| `ops.data_derivation`, `ops.derivation_input/output/support` | Authentic execution, role-qualified consumed inputs and selected support; earlier executions remain immutable. |
| `ops.data_completion_intent`, `ops.data_revocation` | Recoverable immutable completion and scoped current distrust. |
| `attach_data_request`, `claim_data_request` | Attach a demand obligation to settled work or one shared live producer; acquire a fenced attempt. |
| `retain_data_completion_intent`, `publish_data_derivation`, `inspect_data_completion` | Persist exact replay authority before publication, atomically settle it, and inspect/recover its result. |
| `adopt_data_completion_intent` | Authenticate a new exact claim against a retained immutable intent and return a native adoption binding without changing original producer attribution. |
| `revoke_data_support`, `read_demand_result` | Serialized trust changes; pinned coverage/selection/result reads for execution and downstream consumers. |

DDO-05 delivers resolved typed bindings, candidate logical requests, domain sufficiency reasons,
population closure and resumable demand obligations. DDO-06 consumes them and delivers actual
derivations/receipts, selected fulfillment and explicit failure/uncertainty outcomes. Product-family
packages replace actual adapter reads and writers against these interfaces. Public read/evaluation
packages consume the same pinned demand result; they do not derive a second completion algorithm.

## DDO-05 — demand, discovery and eligibility

### Selected relational semantics

Use one compiled, typed relational normal form. A binding rule declares its subject relation,
named input roles, typed equality/range/membership comparisons, required outcomes/coverage and
cardinality. Conjunction is a joined requirement; alternatives are explicitly declared branches
whose producer choice is fixed by the demand or an admitted selection policy. A role declares
set, multiset or sequence semantics; a sequence carries declared ordinal identity. Distinctness
and permitted repetition are explicit. No relation name, SQL body or Python callback can be authored as a hidden
predicate in a candidate release.

Lower role existence and absence to indexed `EXISTS`/`NOT EXISTS`; qualified cardinalities to
bounded grouped selection; alternatives to branch selection over the same admitted universe.
Retain literal type, comparison semantics and unknown state through both Python and SQL lowering.
SQL `NULL`, an empty result and an incomplete population cannot collapse into the same boolean.
Negation, universal conditions and aggregate completion require an immutable population product
whose contract establishes closure. Otherwise the result is awaiting discovery or unknown
sufficiency, as appropriate. A required role's partial or failed output satisfies only an
explicitly weaker consuming contract.

The initial supported forms must express these real consumers:

- A nonempty selection of source views sharing one base product and one document
  (`methods/native_evidence.py:283–290`).
- Exactly one selected eligible projection (`methods/m1_source.py:318–328`).
- Two distinct passages and readings with qualified membership and complete input closure
  (`methods/structural_products.py:1280–1313`).
- A selected retained occurrence population, with optional exact occurrence/type filters
  (`methods/contextual_candidates.py:745–769`).

Specialized predicates outside the normal form are named domain operations with typed inputs,
meaning, output and failure contracts. Their products enter ordinary bindings. They cannot reach
an ambient reader or make unrecorded selections on the planner's behalf. The compiler rejects
structurally incomplete/unresolved declarations; independent adapter conformance checks remain
necessary because compilation cannot infer every undeclared dependency from arbitrary code.

### Demand creation, subject expansion and binding

Demand registration freezes its project/authorization scope, governing release and definition
bindings, requested target kinds/strength, root subject selection, allowed discovery relations,
producer/recipe parameters, retained-product selections and replicate choices. Execution capacity
and acquired device/process details are separately recorded execution policy. Their classification
must follow DDO-01–03's semantic recipe rather than a blanket rule that resources never matter.

Resolve only the transitive operation/binding closure of the requested targets. For each selected
subject, create its target obligation and resolve declared prerequisite roles. The planner can
represent a blocked obligation before inputs exist, but it registers no executable dependent
task with placeholder product identity. A discovery operation itself has an ordinary subject,
inputs and request; its coherent product publishes discovered member identities, coverage and
population closure. The planner expands only the declared member relation. A complete-empty
population closes expansion; partial output remains useful under its declared scope but cannot
prove there are no more subjects.

The root universe is frozen by membership identity, not a future re-execution of a mutable query.
Newly discovered descendants belong to that demand only through its declared discovery products.
A later changed root population is a new demand/binding. A resumed demand does not import unrelated
subjects that appeared meanwhile. Closed fan-in binds the exact complete member set; optional
absence binds its qualified closed-population witness. Additions, deletions, ordering and optional
presence therefore affect identity where they can affect the answer.

Input resolution returns an admitted immutable manifest: subject, role-qualified values and exact
selected support, ordering/multiplicity, outcome/coverage, membership/population witnesses and
definition/eligibility revisions. DDO-01–03 derive its request-identity projection from semantic
values, population witnesses and declared support requirements. Particular episode/provider/alternative
selections enter that identity only where the consuming contract requires them. All actually selected
episodes remain authenticated admission and lineage evidence; a currently available episode is not
automatically a determinant for a value-only consumer. There is no adapter-owned `input_digest` or
second hash assembled from run options.

### Obligation state and resume

The governing model distinguishes not applicable, awaiting inputs/discovery, unknown sufficiency,
ready, executing, fulfilled, partial, failed and cancelled. Currentness/revocation, shared-producer
availability and physical capacity remain separate dimensions. Native `demand_use` transitions
record meaningful selection/fate facts; frontier polling and lock activity need no event stream.

`read_demand_result` pins the demand/selection and evidence boundary and includes zero-output
operation outcomes. A fulfilled no-product result is distinguishable from an unattempted producer.
Successful product reuse attaches exact admissible support and records fulfillment without copying
a producing task or creating a new authentic derivation.

Where the consumer permits equivalent trusted support, the explicitly modeled support-rebinding
variant of `attach_data_request` consumes the equivalent-value manifest and required support
constraints. It checks current admission under DDO-04's trust protocol and appends a DemandUse
admission receipt. It preserves the original authentic derivation and its actual consumed episodes;
it cannot satisfy an episode-specific or independent-evidence requirement by relabeling provenance.

Resume opens the native Demand, verifies its retained release/contracts and authorization, resolves
settled selections and outstanding obligations, inspects uncertain completions first, then advances
only remaining work. Current support admission is explicit: a new revocation may require a new
generation or an allowed alternative support selection; it does not rewrite historical fulfillment.
Runtime/process profiles may change only within the demand's admitted execution/numerical contract.
Changed semantic intent creates a new demand. Current defaults, stage-run anchors, freshness seeds
and delivered artifacts cannot silently supply missing intent.

### Physical route and exhaustion

Prepare compiled rules once per verified release/execution context. Use set-oriented selection
rooted in the demand's obligations and member identities, indexed by demand/subject/kind and exact
input role. Publication/discovery advances the affected kind/subject frontier; reconnect/resume
reconstructs it from native facts. Keep only a bounded page of compact identities/manifests live,
then hydrate bodies after admission. Aggregate queries may examine their required closed population
but cannot repeatedly decode all historical products to discover readiness.

`SKIP LOCKED` is a queue coordination tool, not a completeness oracle: no returned claim may mean
another owner holds the work. Frontier completion checks native outstanding obligations, live shared
requests and unresolved discovery. Capacity backpressure remains temporary, dependency failure has
a domain reason, and an externally assigned request remains awaiting that executor. Cyclic ordinary
bindings refuse with a located cycle; supported iterative algorithms are single declared operations
with explicit convergence/partial-result semantics, not accidental planner recursion.

## DDO-06 — request ownership, execution and recovery

### Native request and attempt ownership

`attach_data_request` authenticates the demand obligation and exact request manifest. A unique
native logical key includes the requested replicate. Equal demands attach to the same admissible
settled execution or one shared live request. `ops.data_request` names its current generation and
physical `ops.task` owner. Ordinary fenced retries remain in the unsettled generation; re-execution
after revoked success appends a new generation/authentic derivation without changing prior success.
An intentional rival uses an explicit replicate, not a freshness salt or an extra implicit producer.

DDO-04 implements unique insertion/conflict handling and row locking in the native call. It must
return attached fulfillment, waiting-on-owner, or newly reservable work explicitly; a local lookup
followed by an unguarded insert is insufficient. `claim_data_request` checks current generation,
lease and live holder, advances the existing task attempt fence and returns an exact typed claim.
Different demands cannot acquire independent producers for one generation. A task lease timeout
does not prove a process has physically stopped: stale work loses publication rights, while its
own supervisor retains physical custody until authenticated retirement.

The selected PostgreSQL mechanisms are unique constraints with `INSERT ... ON CONFLICT`,
short row locks and `FOR UPDATE SKIP LOCKED` for eligible claims. These provide race-safe native
coordination, not domain sufficiency or end-to-end completion. Read committed statement boundaries
must correctly observe a competing committed insertion before selecting its owner; use the owned
native operation rather than a caller-built single-snapshot shortcut. See PostgreSQL18
[INSERT](https://www.postgresql.org/docs/18/sql-insert.html),
[SELECT locking clauses](https://www.postgresql.org/docs/18/sql-select.html#SQL-FOR-UPDATE-SHARE)
and [row locks](https://www.postgresql.org/docs/18/explicit-locking.html#LOCKING-ROWS).

### Semantic, attempt and physical states

Keep three related state machines explicit in the governing model:

| Dimension | Selected distinctions |
|---|---|
| Demand obligation | Required/discovered binding and its sufficiency, fulfillment or terminal failure fate from DDO-05. |
| Native producer attempt | Reserved/claimed, active, completion intent retained, publication uncertain, settled, failed/cancelled/fenced. Generation and holder qualify each transition. |
| Owned physical work | Capacity reserved; known not submitted, accepted or submission uncertain; in flight, collected, reduced, drained/terminated and retired. |

No physical state is inferred solely from a task status. No semantic success is inferred from a
future completing. Native terminal result validation and admission establish the published outcome.
Cancellation of one demand detaches its need; a shared producer continues while another authorized
obligation remains useful. Cancellation of the whole physical owner stops admission, fences its
late replies, drains/terminates owned work and leaves native requests recoverable. Collected valid
sibling results retain their exact settlement rights unless their own authority is lost.

### Bounded physical ownership and uncertain submission

One invocation-wide execution owner coordinates shared CPU/provider capacity, bytes and resident
models. Reserve capacity before hydration/serialization/submission; charge queued packets, replies,
reductions and publication drafts through their last owned consumer. Do not hold a DB connection
through inference or a capacity wait. Renewal has its own finite database operation and does not
wait behind provider work. Current byte/count settings are the baseline to evaluate, not a reason
to preserve overlapping per-layer budgets or a stage permit after stage-run semantics disappear.

Each submission has a request identity, admitted provider/profile and supervisor/host generation
before the transport call. A normal capacity refusal returns explicit temporary backpressure.
A transport/pool exception is a failure. If acceptance is uncertain and no future is returned,
retain the request's capacity and generation ownership; stop new work on that failed executor.
Resolve it through an authenticated acceptance/reply/retirement acknowledgement, or bounded drain
followed by terminating and joining the owned generation. If termination cannot be confirmed,
retain unavailable/quarantined ownership and report the failure; do not invent freed capacity.
Native publication remains fenced independently.

Match replies to exact generation, request, provider/profile and attempt. A cancelled member cannot
reassign its ordinal to a new request. Host-generation failure fences all unfinished requests in
that generation; already collected valid results can settle under their native claims. Healthy
unrelated providers and useful siblings remain usable. Record the primary submit/teardown failure
with original cause and explicit uncertain-effect standing. The historical book failure does not
establish a particular `BrokenPipe` cause or prequalify a replacement executor.

### Preparation, publication and revocation ordering

Compute privately through admitted typed ports. The parent validates the typed result bundle,
canonical product/projection agreement, exact source/support/population closure and declared
outcomes before final publication. Provider/native batching can span compatible logical operations,
but actual grouping/numerics remain authentic provenance and cannot erase member failure boundaries.

`retain_data_completion_intent` stores the immutable request/generation/attempt-bound completion
manifest and authenticated durable payload references before `publish_data_derivation`. It creates
replay authority, not visible successful fulfillment. Its own lost acknowledgement is resolved by
inspection under its stable idempotency identity. An intent cannot be replaced with a newly
computed answer after an uncertain outcome.

Publication uses DDO-04's short fenced transaction. It checks exact task/attempt/holder, generation,
live admission, product/support premises and the scoped revocation authority, then atomically
commits product/member/family projections, authentic derivation/input/output/support, completion
receipt and demand fulfillment. Product-body deduplication does not merge authentic episodes or
make an equal untrusted support path admissible. Conflicting output for an already settled exact
intent is a conflict; an exact replay returns its existing receipt.

Final admission and `revoke_data_support` use the same scoped trust-epoch authority and lock order
defined by DDO-04. Recheck the epoch after acquiring that authority; a version sampled before a
concurrent revocation is insufficient. If publication commits first, the subsequent revocation
makes its support affected in current assessments. If revocation commits first, publication refuses
or explicitly resolves an admissible alternative under the consumer contract. Readers pin their
historical selection and report a separately identified present trust assessment. No large payload
preparation, provider call or full-history scan occurs under this trust/publication lock.

### Recovery and effectful execution

| Observed outcome | Required next behavior |
|---|---|
| Known rollback before publication | Revalidate live ownership; replay the retained intent under the native contract, or retry preparation only when no uncertain effect exists. |
| Commit acknowledgement lost | `inspect_data_completion` authenticates the exact intent/request/generation. Historical committed-receipt inspection remains available after terminal task state, lease expiry or later revocation; new current DemandUse admission is checked separately. Return that receipt or replay the same uncommitted intent; never repeat stochastic inference to guess the outcome. |
| Inspection/replay unavailable | Retain publication-uncertain native state and durable intent; surface the prerequisite and resume through the same authority. Do not mark failed-empty or create an unchecked replacement. |
| Owner crashed with retained intent | Native takeover reconciles completion before permitting new computation. `adopt_data_completion_intent` authenticates the new exact claim and old immutable intent digest and stores its validated adoption reference on the existing task/new attempt. Publication consumes that current fence plus adoption binding, preserves original production provenance and never rewrites the old intent's producer fence. |
| Frozen PDF build retained | Authenticate request/source/recipe/schema/profile, exact frozen union and replay receipts; fence the old writer and transfer custody under the new attempt before sealing/publication. |
| Open PDF build retained | Resume authenticated upload/replay under the admitted lifecycle; an unfrozen build cannot take the frozen-publication shortcut. |

External-agent work uses the same request/attempt model with a declared external executor and
immutable packet/input binding. Packet delivery is not fulfillment. Results arrive through an
admitted result port, retain producer attribution and enter the same validation/publication owner.
Protected evaluator labels cannot become packet inputs through planner discovery. Effectful
commands declare their idempotency identity, effect boundary and receipt inspection/reconciliation
operation. Equal output payloads alone cannot establish an external effect. When an executor cannot
resolve an uncertain effect, report uncertainty rather than silently replaying a non-idempotent
command. Authored selections are declared immutable inputs, not provider side effects.

## Integration sequence and retirement

1. Settle DDO-01–03 binding/canonicalization and DDO-04 native call contracts; implement DDO-05
   resolution against the shared compact projections. Independent family examples can establish
   expressiveness before every adapter migrates.
2. Implement native Demand registration/read and request attachment with exact zero/unknown
   outcomes. Add claim/attempt and retained-intent publication/recovery through DDO-04; no reuse
   protection is removed before its target replacement is working.
3. Connect the bounded frontier and typed execution ports, then migrate actual product families
   with their producers and immediate consumers. Native Demand resume replaces stage-run recovery
   in the same replacement, including CLI correlation and cancellation semantics.
4. Replace active stage graphs, characterization order/input maps, method-name pairing,
   `source_dependencies`, private selection/digest decisions and run-anchor/freshness logic.
   Remove old `SourceOperationLink` execution grouping only when native Demand reporting and
   public consumers carry its required lineage. Do not hide equivalent lists behind a new port.
5. Integrate source custody, reference applicability and frozen-build preservation with the
   coordinator's actual-data cutover. Retire superseded runtime/SQL paths and mechanism-only tests
   with their replacement; preserve useful independent semantic expectations and historical
   artifacts required by real consumers. There is no second legacy/new planner fallback.

DDO-05 can deliver declared resolution before every family executes. DDO-06 is usable only when
the native request/publication interfaces, physical retirement and resume path work together.
These readiness distinctions do not create package-status facts outside the coordinator.

## Focused verification and completion boundary

During implementation, use relevant compile checks and focused functional/native controls. Select
cases that challenge different failure classes; generated declarations alone are not an independent
oracle for the binding semantics. The coordinator owns final-source required-union accounting and
the series' assembled functional/provider qualification. Other plans' campaigns are not prerequisites.

DDO-05 checks exact projection/cardinality/distinctness, typed alternatives, ordered/set roles,
complete-empty versus partial discovery, aggregate fan-in, changed optional/negative membership,
newly discovered subjects, explicit producer choice, unsupported cycles, and capacity/locked work
not becoming false completion. A resumed demand must preserve original root membership and intent
despite changed defaults or newly added unrelated subjects. Explain and execute must resolve the
same admitted inputs and missing-reason semantics.

DDO-06 checks two concurrent demands sharing one logical request; explicit replicates; fenced
takeover and revoked-success generation; stale late result refusal; cancellation with useful
siblings; no-future uncertain submission with confirmed termination; bounded backpressure; restart
after retained intent; lost acknowledgement both when commit happened and when it rolled back;
revocation/publication in both serialized orders; exact PDF open/frozen adoption; external packet
and effect-receipt custody. Native race controls use real transactional sessions where their
guarantee depends on PostgreSQL; a mocked provider cannot establish native-provider qualification.

The product-family/public-consumer packages exercise the assembled demand from retained original
source through discovery, selected analysis and pinned result/cut, including zero output and partial
failure. Selected actual native providers establish their execution/admission/numerical boundaries.
Replaying a settled demand creates no new authentic derivations; a meaningful parameter change
updates affected requests and stops at substitutable value/support. No speed/capacity improvement
is asserted or required to be measured merely to qualify these semantics.

Expected execution fit is qualitative: indexed demand-scoped relational work, compact manifests,
bounded hydration/frontiers and shared resident providers avoid per-read inference and repeated
all-history expansion. Large closed populations still require their semantically necessary work;
bounded paging, streaming and backpressure provide the physical route rather than truncating scope.

**Authoring checks:** `not_run` — product tests, database/native controls and providers; this document
defines future verification. The root performs documentation checking and turn-end maintenance
after integrating the series.


## Declared versus selected graphs and execution policy — I01–I03/I06

Consumes [projection families](graph-projections-and-analysis.md#projection-contract-and-physical-route--i01)
and [topology kernels](graph-projections-and-analysis.md#shared-closure-cycles-and-partial-orders--i02i03).
DDO-05 distinguishes potential producer dependencies from actual bound-request precedence. Keep
operation/role occurrence and alternative-group identities: A and B required together is not one
reachable input, and unselected producer alternatives cannot impose mandatory prerequisites/cycles.
DDO-03/04 relational binding and native obligation facts remain readiness authority.

[`lexicographical_topological_sort` and `topological_generations`](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/algorithms/dag.py)
produce stable explanations and dependency levels, not a new scheduler. Execute C when its B input
settles even if unrelated A at B's level is still running. SCC/condensation diagnose genuine selected
cycles; potential alternative cycles alone do not establish unavoidable execution blockage.
`nx.dag.antichain_width` uses transitive closure/matching and is conditional inspection only, never
capacity admission. Longest-path weights likewise do not create an implicit duration estimator.

DDO-06 admits graph algorithms through [explicit execution/cache policy](graph-projections-and-analysis.md#execution-and-interchange--i06).
The [3.7 dispatcher](https://github.com/networkx/networkx/blob/networkx-3.7/networkx/utils/backends.py)
supports `backend="networkx"`; select it for core dispatchable calls instead of ambient priorities.
No request mutates global nx.config. Converted caches belong to immutable projection lifetimes;
direct attribute mutation may bypass invalidation. No optional accelerator installation or nested
pool is required. Future engine adoption shares invocation CPU/device capacity and qualifies the
actual invocation, conversion/result route and explicit fallback/refusal policy.

Add independent cases for A/B/C nonbarrier progress, selected versus unselected cycle, all-of versus
alternative sufficiency, partial discovery, root inclusion and locked/backpressured work not becoming
exhaustion. Runtime projection acquisition requires actual DDO-04 native support, not merely an agreed
interface. No in-memory whole-database graph is needed to replenish the native bounded frontier.
