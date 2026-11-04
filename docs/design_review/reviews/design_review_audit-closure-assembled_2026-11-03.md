# Audit-closure assembled design review

**Implemented source / Proposed deployment, 2026-11-03. Tier:** design. **Purpose:** target.
**Focus:** holistic, informed by targeted library research.

**Decision: Revise for F01, the producer/required-coverage composition gap.** The other inspected
responsibilities compose coherently at source level. This judgment neither freezes native102
nor establishes complete AC14 qualification. The audit-closure coordinator owns disposition,
integration and acceptance.

## 1. Scope, baseline and evidence

This is the planned assembled continuation of the audit-closure engagement, consuming the
[broad audit](../audit/README.md) at
`90ed25c46ca452b0183b5fd9c6ddb1693dfd83ac` and the
[original target review](design_review_audit-closure-target_2026-11-03.md), subsequently consumed
by the [accepted plan](../../plans/audit-closure_2026-11-03.md). It reconciles intervening AC
implementation rather than initiating another broad audit or treating every historical DA
identity as an open defect.

The assignment began at `2fcbdea2`. The inspected assembled baseline includes the subsequent
source retirement commit `31ea1dad421848365aaf1648c76cd8c47ed087b4`, plus the coordinator's
identified working changes to interactive read budgets, Unicode custody/admission, split chapter
admission and protected split publication. Native102 and its inventory/admission companions
remain an unfrozen candidate. Later source changes require affected conclusions to be reconciled;
this review is not a certificate for an arbitrary subsequent working tree.

The standard is core/template3.3, heuristics1.0, code-intelligence1.4 and test-assessment1.2,
selected through standard.toml and the repository binding. The functional target is DESIGN §1.1:
typed, qualified, evidence-backed document knowledge, inspectable through queries and exports.
D2/D5/D6/D7/D8 and ADR-0054 describe the subject; they do not replace the standard as criteria.

The workload premise is the local operator deployment with concurrent source work, renewal,
publication and readers; intact documents; growing candidate/evidence populations; and skewed
relation degree. No latency, capacity, memory or speedup measurement is claimed.

Method: read-only inspection of the relevant owners, declarations, executing source and selected
independent tests; Context7 inspection of SQLAlchemy transaction characteristics and PostgreSQL
recursive-query behavior. No tests, database operations, providers, probes or mutations were
performed by this reviewer.

## 2. Responsibility and fidelity model

The increment has a sound central separation: released meaning governs specialized preparation;
owned lifetimes govern effects; pinned readers derive answers; evaluator custody governs
reference effects.

| Responsibility | Meaning and authoritative owner | Executing realization and consumers |
|---|---|---|
| Released contracts | Effective enum subsets, property roles, method dimensions, value/rule ABI and source assertion shape | `semantic/types.py`, `prepare.py`, `statement_types.py`, `property_roles.py`, generated boundaries and native lowering |
| Source assertions and identity | Attribute-specific qualification/support; source-local versus resolved identity; explicit resolution outcomes | `proposals.py`, `domain_operations.py`, `consolidation.py`; original occurrences remain retained |
| Prepared interpretation | Candidate context, scientific evidence, representative policy and finite rule closure | `CandidateContextIndex`, scientific operations and delta inference; orchestration does not choose scientific truth |
| Source effects | Executable policy applicability, compatible producer binding, claim custody and terminal settlement | `orchestrate/policy.py`, `methods/llm/producer.py`, `claim_lifetime.py`, protected native operations |
| Answers and evidence | Selection, assessment and establishment remain independent; coverage describes the required universe | `semantic/query.py`, `serve/read.py`, `serve/journey.py`, CLI/MCP/export adapters |
| Evaluation | Frozen actual policy, seed origin, population, prior basis and assignment reasons | `evaluate/split_decisions.py`, `evaluate/semantic.py`, protected `eval.assign_document_split_decision` |

The principal dependency direction is appropriate: adapters and orchestration consume domain
operations and immutable bindings; persisted evidence does not authorize itself; query products
derive standing from canonical relations rather than maintain a second writable status.

| Fact family | Fidelity, identity and unknowns | Consumers |
|---|---|---|
| Source attributes | Individually qualified and located assertions; entity labels and generated IDs do not borrow a neighboring claim's support | Consolidation, fact/occurrence reads, explanation |
| Identity resolution | Declared-key/global-label/source-local basis; resolved, ambiguous, incomplete and cyclic outcomes remain explicit | Consolidation and identity inspection |
| Rule values and scientific assessments | Declared range, enum, expression form/language, reading status and unavailable interpretation remain distinct | Rule evaluation and scientific policy |
| Inferred relations | Versioned rule and direct premise identities; original source occurrences remain distinct | Accepted facts and derivation inventories |
| Fact standing | Selection membership, each assessment and establishment references; unassessed/unavailable remain explicit | Primitive/named answers, premises and export |
| Coverage | Complete relative to the archived required producer/unit universe; paging does not establish knowledge absence | Answer knowledge state; F01 affects this boundary |
| Split assignments | Immutable decision provenance for new effects; legacy unavailable provenance is not reconstructed | Reference creation and evaluator inspection |

## 3. Contracts and enforcement

**Implemented, source-inspected, 2026-11-03:** `SourceAttributeAssertion` in
`model/semantic/agent.yaml` requires its own value, qualification, source establishment and evidence.
Proposal placement includes entity attributes (`semantic/proposals.py:845` onward);
`domain_operations.py:1686` onward lowers each attribute independently and retains a partial
coverage outcome when located support is unavailable. `consolidation.py:224` onward rejects
non-source establishment before assembly. These operations govern behavior rather than merely
standardize output records.

Rule translation has one `project_rule_value` owner (`semantic/rule_views.py:248` onward).
Declared binding supplies range and enum identity; expression language/form, missing reason and
reading availability survive projection. Released member behaviors govern symbol-definition and
binding roles. A new semantic operation still needs its own algorithm; adding an ordinary member
does not justify another registry.

`admit_source_policy` (`orchestrate/policy.py:208` onward) distinguishes authored language from
the executable source context. Unavailable judgment/budget symbols cannot enter this context as
fabricated values. Producer compatibility is checked before effects.

The public source-method reader exposes owned operations rather than a raw connection.
`ScopedSourceReader._read` borrows the shared read-only REPEATABLE READ owner for a coherent read,
then returns detached values. This is a trusted method boundary, not a sandbox against arbitrary
Python execution.

`ClaimOwner.settle` (`semantic/claim_lifetime.py:54` onward) serializes renewal and terminal
settlement under one owner-local lock, retires a claim only after durable completion or exact
replay, and retains uncertain completion intent. The source scheduler claims one ready bounded
batch before establishing that owner (`orchestrate/semantic.py:529` onward). Custody and unit
preparation occur inside its lifetime. Per-task durability is preserved.

**Proposed deployment:** the inspected SQL defines protected split publication with explicit
input validation, current-basis comparison, independent assignment reconstruction, atomic
decision/assignment effects and exact replay. The new chapter boundary accepts string, null or
absent metadata and explicitly refuses other JSON types. This avoids treating Python `str()`
as a portable grouping definition. D7 accurately records that unsupported historical chapter
metadata can block a new split/reference invocation; existing stored assignments remain readable
with their actual provenance limits.

## 4. Composition and physical route

| Operation | Declared model and method | Work, limits and failure | Evidence linkage |
|---|---|---|---|
| Candidate interpretation | Pinned cut/release; indexed statement premises and occurrence-sensitive symbol ownership | Preparation shared within its owned lifetime; self-exclusion retained | Candidate occurrence and assessment references |
| Finite inference | Complete accepted seed universe; unary and transitive delta processing | Accumulated workspace, newly inserted frontier, empty-frontier termination; atomic publication retained | Versioned direct witnesses produced from the fixed point |
| Ordinary fact answer | Requested projection plus independent standing and required coverage | Batched hydration; scoped coverage aggregate/detail selection | Pinned fact, occurrence, assessment and establishment references |
| Evidence detail | Fact-rooted named collection | Identity/keyset selection before hydration; row/byte limits; source bodies retrieved explicitly | Binding, run/cut, answer selection and query binding continue across calls |
| Relation query | Directed bounded walks, cycles and parallel-edge identity; default depth four | Indexed adjacency, bounded batches/frontier/state, deterministic replay; unfinished work refuses | Ordered fact-ID witnesses with each premise's own standing |
| Split publication | Frozen policy/seed/population/prior basis under chapter/URI/hash algorithm | Project-owned atomic effect and exact replay; conflicting basis refuses | Immutable decision referenced by new assignments |

This is preferable to introducing one physical stage or lifecycle for every semantic distinction.
Candidate indexes remove repeated premise reconstruction; delta inference removes accumulated
rescans while preserving the existing publication boundary. The architecture does not move
provider/model preparation into publication locks.

The walk implementation in `domains/statistics/queries.py:Relations` preserves the selected
question. Applying PostgreSQL CYCLE automatically, collapsing repeated edges, or substituting a
shortest path would change it. Replay intentionally repeats the prefix and spends the same work
budget; it avoids a durable traversal service. Its cost is explicit and bounded.

Read budgets bound selected transfer, decoded state and returned envelopes; they do not prove
a latency bound for every database plan. In particular, source search still performs relational
full-text selection/ranking over selected source text. That is a credible simple local route,
without a measured growth claim. A sustained larger search workload could justify a prepared
native search vector/index; the present evidence does not establish an architecture defect or
require another indexing lifecycle.

## 5. Revealing changes and failure scenarios

| Scenario and kind of change | Expected owner and propagation | Assessment |
|---|---|---|
| Add a released source attribute and an expression-form/rule variant — domain extension | Attribute meaning/evidence and member behavior are declared once; prepared adapters, rule projection and native products follow. A genuinely new interpretation needs specialized code | Coherent source route. Range/enum/expression distinctions survive; independent extension expectations remain necessary qualification |
| Replace a managed recognition process under the same alias — mechanism substitution | Controlled startup verifies artifacts and creates a process generation; requests and responses carry that generation | The binding changes or the request refuses. An old in-flight response can retain its original generation without relabelling |
| Add another compatible proposal producer — binding extension | Policy, queue, packets, submission, automation and coverage consume the same binding | F01: coverage independently retains the Opus-only selector |
| More than one ready source-method batch, slow custody and competing reclaim — composition/failure | Only the next executing batch is claimed; ownership spans preparation through exact settlement | Synchronization and native attempt/holder/receipt fences fit the lifecycle; no atomic batch completion is introduced |
| Empty answer over missing producer reports — fidelity | Required population includes every eligible required unit; missing coverage keeps knowledge unknown | F01 can select the wrong population before otherwise correct summary logic runs |
| Dense/cyclic relation expansion and continuation — growth | Necessary intermediate nodes remain eligible; bounded frontier/edge work and replay preserve the question | Exact-or-refuse is explicit; a returned page is not a complete traversal |
| New realization/default selection during evidence retrieval — lifecycle | Returned references and continuations retain release/realization/revision/run/cut/query/selection | Inspected journey contracts preserve the original pin or refuse incompatibility |
| Replay a split with changed defaults or unsupported chapter metadata — policy/failure | Frozen intent remains authoritative; new unsupported input refuses; old provenance is not invented | Coherent operation boundary; native102 qualification remains open |

The managed substitution is deliberately scoped trusted local custody, not model authentication.
`services/nemotron-parse/custody.py`, `launch.py` and `worker.py` compose startup verification,
an immutable generation and request/response checks. `admit_service_generation` verifies the
managed artifact claims; unmanaged endpoints retain provider-reported assurance. Replacing that
route must preserve those meanings or declare a weaker contract.

Current compiler16 production and supported immutable compiler14/15 reading are separate
contracts (`semantic/types.py:17–19`, `archive_reader.py:reconstruct_release`). A readable archive
does not authorize current execution or arbitrary named-query compatibility. Query implementation
custody and continuations refuse incompatible reuse. Final old/new reader and actual consumer
applicability remains an AC13/AC14 obligation.

## 6. Independent judgments and gates

These are source-level design judgments, not runtime qualification results.

| Judgment | Verdict | Reason |
|---|---|---|
| A1 Localize change | violated | F01 makes an ordinary compatible producer addition depend on an independently maintained read-side producer classifier |
| A2 Encode domain meaning explicitly | violated | Most changed behavior consumes explicit authorities, but the required coverage universe does not consume the supported producer contract |
| A3 Extend through composition | violated | Proposal production composes through the binding; its answer/coverage consumer does not yet compose through that boundary |
| A4 Fit execution to workload | satisfied, scoped | Shared preparation, delta inference, demand-shaped hydration, indexed bounded walks and JIT effect lifetimes provide credible physical routes. No quantified benefit is established |

| Gate | Verdict | Evidence |
|---|---|---|
| G1 Authority | fail | F01: producer compatibility and required producer coverage have independently authored selectors |
| G2 Semantic fidelity | fail | F01: a supported producer's required units can be omitted from the coverage interpretation |
| G3 Validity | pass, inspected contracts | Defined admission, source-establishment and split-basis rejection points exist. Installed native102 enforcement is unqualified |
| G4 Hidden behavior | pass, inspected scope | Owned method reads and explicit publication/settlement effects; unavailable policy inputs refuse |
| G5 Consistency/recovery | pass, design scope | Exact intent/receipt fences, synchronized retirement, pinned detail journeys and explicit limit refusal; final native execution remains open |
| G6 Transformation/reuse | fail | F01: the coverage projection can change the required universe independently of the producing binding |
| G7 Truthful claims | pass, with stated maturity | Configured/reported/manual/managed identities remain distinct; draft deployment and incomplete qualification are explicit |
| G8 Library leverage | pass, inspected choices | Adopted relational, transaction, validation and lifecycle capabilities carry their complete responsibilities; retained custom code implements domain gaps |
| CI-G1 Fidelity | fail | F01 can undermine unknown-versus-absent meaning |
| CI-G2 Evidence closure | pass, inspected source | Fact-rooted evidence and source reads retain their pinned realization and selection |
| CI-G3 Evaluation integrity | pass, inspected source | Evaluator-owned split/reference effects remain distinct from production inputs; no leakage path was established |

FP-01/02/03/04 and relevant DP-01/08/24 are violated at F01's boundary. The inspected source
otherwise supports FP-05/06 and the scoped FP-07 judgment. DP-02/03/05/07/09/18–23 and CI-01–13
retain the specific scope and evidence limits above; no broader foundation or profile certification
is implied.

## 7. Finding

<a id="F01"></a>
### F01 — Required property coverage independently selects one producer identity

**Diagnosis: Implemented defect, source-inspected 2026-11-03.**
Related source diagnoses: DA-035, DA-051 and DA-052.

`methods/llm/producer.py:SUPPORTED_PRODUCERS` admits `agent.opus` and `agent.general`.
Policy admission and `propose_agents` queue the selected compatible method.
However, `semantic/coverage_contract.py:16` archives `agent_method: agent.opus`, and
`semantic/query.py:required_coverage` selects that literal for agent property families before
filtering tasks by `method.name`.

A general-only run therefore cannot establish its property coverage. More consequentially,
a mixed policy can route disjoint source units to compatible producers: the Opus subset can be
complete while a general-owned unit is missing/partial. Selecting only the Opus population
omits a required unit before the summary decides whether an empty answer establishes absence.
Correct aggregation cannot repair the wrong required universe.

This is a shared-contract composition defect, not a request to broaden producer support.
It violates FP-01/03/04, DP-01/08/24, A1–A3 and the G1/G2/G6/CI-G1 judgments above.

**Proposed correction:** the coverage owner consumes the immutable run's compatible producer
bindings and effective-origin tasks, including missing-report units. Derive the accepted finite
producer declarations from the existing binding owner; validate persisted protocol/version/unit
and configuration rather than treating any arbitrary agent method as compatible. Preserve the
historical v3 recipe's original meaning through explicit version dispatch; new semantics need a
new recipe. Do not silently reinterpret an old archive or add a second producer registry.

**Required closure evidence:** inspect the corrected ownership and archived version handling;
independent general-only and mixed-producer cases must discriminate complete versus missing/
partial required coverage. Include persisted binding drift/incompatible producer refusal and a
historical-v3 interpretation case. A test expecting “unknown” for all general-only requests
would not establish the correction.

Current execution disposition belongs in the audit-closure coordinator's findings table.
A correction produced during review requires a separately attributed delta assessment; it does
not erase this original diagnosis.

## 8–9. Library mechanisms and alternatives

**Interface-checked, 2026-11-03:** SQLAlchemy's
[`Connection.execution_options`](https://docs.sqlalchemy.org/en/20/core/connections.html) and
[PostgreSQL transaction characteristics](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html)
support setting isolation/read-only characteristics before beginning the owned transaction.
`semantic/query.py:read_snapshot` uses that route. Returning owned values lets the checkout end
before scientific/model computation. A separate generic SQL capability or reader framework adds
no required behavior for the migrated method callers.

SQLAlchemy Core selection, joins, grouped/window aggregates and keyset predicates preserve
set-shaped intent for coverage, standing and detail. Client streaming alone would not bound
server expansion or repair the required coverage universe.

**Interface-checked, 2026-11-03:** PostgreSQL's
[recursive-query documentation](https://www.postgresql.org/docs/18/queries-with.html) explains
that outer sorting/joining can consume recursive output despite an outer LIMIT, and that cycle
handling changes which paths are explored. The selected bounded adjacency route fits the actual
walk contract. A native shortest-witness operation or detached NetworkX execution remains an
alternative for a separately declared consumer question, not a replacement with equivalent
meaning.

The simplest viable assembled design is the selected extension of existing owners: ordinary
domain functions, immutable released products, protected native effects and bounded readers.
A universal mapping/workflow/provenance system would add lifecycle and maintenance responsibilities.
Retaining the old raw connection, eager claims or unbounded explanation materialization would
reintroduce the diagnosed problems. No new dependency or generalized framework is recommended.

For F01, relationally selecting the correct immutable producer-bound task population is sufficient.
No coverage cache, parallel status store or new scheduler is needed.

## 10. Verification and uncertainty

| Claim | Evidence and current limit |
|---|---|
| Governing semantic and lifecycle source exists | Implemented; direct inspection on the stated baseline |
| Library transaction/recursive mechanisms fit the selected contracts | Interface-checked through Context7 and the linked primary documentation |
| Selected tests challenge meaningful semantics | Source inspection of bounded-walk, attributed-source, archive-reader, source-search and split native controls; this reviewer did not execute them |
| Native102 is final, installed and admitted | Not established; candidate is unfrozen |
| Fresh/forward native transitions and final reader bodies agree | Open with the coordinator; draft reauthoring is still being reconciled |
| Complete functional/provider/nonfunctional union | not_run by this reviewer; remains AC14 |
| Quantified performance or capacity benefit | Not claimed |

The reported parallel full-chain setup failures involving PostgreSQL's shared lock table do not,
without a demonstrated source cause, establish an architectural defect. Likewise, investigation
of reflected index collation and intended changed reader bodies is a native-authoring question;
this review does not call either resolved or turn diagnostic failures into qualification success.

No prior failed/interrupted receipt is discarded or promoted. Bounded native/provider receipts
can inform the coordinator's later applicability account, but cannot establish the final union
after further source or native changes.

## 11. Rule impacts and disposition

**New rule impacts: none.** F01 completes the accepted producer/coverage responsibility and versions
its derived recipe; it requires no change to the already accepted RC01–RC12 target directions.
Historical recipe meanings and supported-reader limits remain preservation constraints.

The original audit's DA identities retain their original disposition owners. This review adds
only F01 and points its execution disposition to the audit-closure coordinator. It does not close
the audit collection, change M1 state or authorize unrelated implementation.

## 12. Decision and next boundary

**Assembled decision: Revise.** Resolve F01 at the shared producer/coverage boundary, retain the
original finding, and assess the integrated correction with its independent cases.

The remaining inspected design is coherent at Implemented/Interface-checked strength. Preserve
attribute-specific support, explicit identity uncertainty, scientific-policy separation,
same-snapshot evidence, per-task durability, current-only execution, maintained archive meanings
and honest historical provenance.

The enclosing system remains unqualified. After source and native102 stabilize, the coordinator
must complete the accepted forward-transition and final functional/provider/nonfunctional union,
then prepare the M1 impact handoff. Neither this review nor a corrected local finding establishes
that release boundary.
