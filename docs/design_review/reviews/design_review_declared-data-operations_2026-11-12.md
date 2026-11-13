# Design review — declared data operations

**Original design / target inquiry · 2026-11-12 · author: the root Claude session, at the operator's
request, with delegated read-only mapping of design authority, operation code and identity
storage and one delegated planning pass that tested the target against the code.** This is not
an independent `design-reviewer` engagement. It consumes no refreshed audit and does not count
toward the binding's review cadence.

**Revised judgment · 2026-11-12 · Codex root synthesis with two fresh independent design reviewers.**
Recommendation audit of exact original8f35f1d07e2613400e0a85ed9e40752e344d042c;
product source remains8c0f4f951. The original inquiry attribution above remains historical;
the revised target and judgments are the auditor's, not an endorsement attributed to its author.
[Net changes](audits/design_review_declared-data-operations_2026-11-12_audit.md).
Consumes the bounded diagnostic reconciliation published atf6ce5d086
([account](../audit/README.md#declared-data-operations-entry-refresh)), not a whole-codebase audit.
Core3.3, heuristics, code-intelligence1.4, test-assessment1.2 and binding apply.

This review is evidence, not authority. Every remedy below is **Proposed**. Source facts are
**Interface-checked by source inspection, 2026-11-12**, at product source `8c0f4f951`
(`main` `46b1b3072`). Nothing was run. Counts from the development database were read from its
catalog on the same date and are marked where used.

**Supporting documents.** This principal owns the findings, the target and every remedy. Four
pages hold the detail behind it:

- [Operations and sequencing baseline](declared-data-operations/operations-and-sequencing-baseline.md):
  the operation inventory, the existing abstractions, how order and eligibility are decided,
  and the coupling hot spots.
- [Identity, reuse and provenance baseline](declared-data-operations/identity-and-provenance-baseline.md):
  every identity in use, the fingerprint machinery, what is keyed by run, and what a change
  invalidates today.
- [Design authority map](declared-data-operations/design-authority-map.md): what the standard,
  the architectural sections and accepted decisions already say, the vocabulary to reuse, and
  the decisions the target touches.
- [Target contracts and storage](declared-data-operations/target-contracts-and-storage.md):
  the declaration shape, the configuration split, storage changes and the fit of special cases.

**Path convention.** Paths without a prefix are relative to
`python/corpus-structure/src/corpus_structure/`. Other paths begin with `docs/`. Citations are
`path:line` at the baseline.

---

## 1. Scope, outcome and coverage

| Field | Value |
|---|---|
| Subject | How data operations are specified, sequenced, identified and recorded: the `Method` protocol and its registries, released operation contracts, orchestration and readiness, task reuse, product identity, lineage and change impact |
| Origin | The inquiry the [BEP coordinator](../../plans/book-processing-efficiency-and-parallelism_2026-11-11.md) deferred: "a stronger ports/adapters and dependency-driven design remains a subsequent inquiry" |
| Operator intent (2026-11-12) | Be able to change data operations and their sequencing without surgery across the pipeline. Four properties: uniform ports with contracts; dependencies expressed on object state; versions tied to a fingerprint of the operation instead of run ids; a retained record of actions and prior state |
| Operator directions (2026-11-12) | Fixed: all derived products; declared semantic invalidation; no read-triggered recomputation; extend the existing PostgreSQL kernel |
| Standard | [Design principles](../design_principles/core/design-principles.md) core3.3 and code-intelligence1.4; correctness/domain authority and execution workability emphasis; [heuristics](../design_principles/core/efficient-architecture-heuristics.md) H13, H22, H25, H26 |
| Tier · purpose | Design · target |
| Evidence rule | Source inspection only. No test runs, benchmarks or database changes. No speed or capacity figure is asserted |
| Outcome sought | A target model and an ordered change set that plan creation can adopt, with the rule impacts it would need confirmed |

**Coverage.** The author read directly: the `Method` protocol, `OperationContract`, one released
contract, `CharacterizationOperation`, the task hash construction and its salts, the reuse rule
in SQL, the characterization inputs map, the declared demands and parsing adapters, and
ADR-0060, ADR-0063 and ADR-0090. The operation inventory, the identity table, the schema
inventory and the per-finding ADR and design-section readings come from the delegated sweeps and
were not all re-read. That original inquiry excluded evaluation/grading and much of serving. The audit includes their
source/prediction binding and evidence-closure contracts as affected consumers; it does not certify
every serving/evaluation implementation. Rust remains a placeholder. §§4–11 state fresh coverage.

## 2. Integrated assessment

The domain model is mostly present. The friction comes from where its connections live. An
operation's inputs, its order relative to others, what makes its output reusable, and what its
output is called are each stated more than once, in Python, SQL and tests, and the statements
are kept in agreement by tests and matching names. BEP findings E09 and E15–E19 were each a
repair to one of those restatements.

Four things are already close to the target and should be generalized, not replaced:

- **A declared operation fingerprint exists for one family.** Characterization layers carry an
  `operation` block with key, version, configuration, model, grammar, produced families,
  required layers, preconditions and result determinants
  (`model/semantic/characterization.yaml:66-100`, `orchestrate/semantic.py:1007-1024`).
- **Declared operation-to-operation prerequisites exist for one family.** Analysis demands
  name prerequisites and determinants (`model/semantic/execution-model.yaml:14708`), and
  parsing adapters declare behaviour revisions (`:14766`).
- **Reuse is already by content hash, not task id.** `input_hash` and `config_hash` exist and
  a twin task is reused when they match (`semantic/operations.py:301-363`).
- **Declared change facts already exist.** `compare_semantic_releases` diffs
  two releases member by member and lists directly referenced consumers, retaining unknown closure
  (`semantic/operation_reporting.py:763`).

The operator requires that a code change not manufacture new data meaning. Runtime-equality
reuse is a concrete overly broad dependency for that target; its contribution to total runtime
or lost reuse was not measured. The corrected target separates semantic recipe, input/support
binding and execution provenance rather than dropping validity premises.

## 3. Owners and current contracts

**Three meanings of "operation".**

| Meaning | Definition | What it covers |
|---|---|---|
| Method | `Method[C]` protocol: name, version, family, unit type, `Config`, `select`, `input_digest`, `run` (`core/method.py:981-1011`) | About 33 implementations registered in `orchestrate/phase0.py:121-157` and `orchestrate/m1.py:161-182`. Inputs arrive through a reader port of more than 50 methods; output is one large `UnitResult` union |
| Released contract | `OperationContract`: inputs, results, applicability, effects, outcomes, dependencies, implementation, transitions (`semantic/contracts.py:694-716`) | 101 contracts, mostly database and protocol actions. Data-bearing ones include `convert_pdf` and `publish_characterization`. Language, extraction and structure methods appear only as result dimensions of `configure_method` |
| Invocation | `SourceOperationLink`, run options, managed CLI operations | Grouping of runs for reporting (ADR-0090) |

**Sequencing.** `Graph` and `Step` declare stages (`orchestrate/runner.py:49-68`), and order is
iteration over them (`orchestrate/semantic.py:663-664`). Characterization order is a literal
sequence with a hand-maintained map from each method to the layers it consumes
(`orchestrate/characterization.py:357-379, 527-623`); each stage is a separate run. Task
prerequisites come from a `source_dependencies` literal in each `Config`, limited to three kinds
by a database check. The database claims a task when no prerequisite is unfinished
(`semantic/sql/execution_projection.sql:72-88`).

**Identity and reuse.** The task hash combines the release, input realization and revision, a
scoped run dependency manifest, the method name and version, the config hash and the method's
input digest (`orchestrate/semantic.py:701-745`). `ops.valid_reuse` additionally requires an
equal `ops.run.runtime_id` (`semantic/sql/task_dependency_scope.sql`). The runtime identity is
one hash over the owned executable package (`semantic/runtime_bindings.py:100-150`).

**Products and lineage.** `ProductReference` is a producing task, a product key and a content
digest. About 120 tables are append-only. `data.batch` holds each published revision as an
additive delta. Task, run and project state is updated in place.

## 4. Corrected target state

**Proposed · independent recommendation-audit synthesis, 2026-11-12.** The fixed outcome is a
total domain model for supported data operations. Products, subjects, bindings, applicability,
transitions, effects, outcomes, demands and change determination govern behavior through owned
contracts. Algorithms remain trusted implementations of those contracts. Completeness of the
model does not require a physical task, table, transaction or materialization for each concept.
The target extends PostgreSQL's existing kernel; it does not add a second workflow authority.

### 4.1 One declaration, distinct semantic projections

One released **OperationDefinitionRevision** owns subject types, input roles and bindings,
output roles/cardinality, applicability, invariants, effects, outcomes, lifecycle, executor
capabilities and result determinants. Existing OperationContract and the data-operation facet
compose through this authority: database/protocol calls realize its controlled actions rather
than restating its policies. Specialized domain algorithms retain named contracts and limits.

The compiler derives three distinguishable projections from that declaration:

- **ResultRecipeIdentity:** behavior revision, result-affecting parameters, model/grammar/prompt
  assets, semantic provider/numerical policy and the semantic contracts required for the result.
- **Eligibility and binding specification:** subject population, relational input bindings,
  sufficiency, coverage and policy requirements. Its revision is recorded independently.
- **Execution binding:** admitted implementation, capabilities and resource/lifecycle policy.
  Executable bytes and acquired execution details remain provenance, not automatic reuse fences.

The split is declared and compiled, never guessed from fields a current reader happens to use.
An eligibility-only change can preserve a recipe only if it cannot change result interpretation,
coverage, inputs, required effects or validity. A widened subject predicate can then admit newly
applicable subjects without rerunning existing substitutable products. A changed scope rule or
input selection that affects the answer changes the recipe or exact binding. Unknown dependencies
remain explicit; the compiler refuses structurally incomplete or explicitly unresolved declarations instead of
reverting to a whole runtime hash. Independent adapter conformance must still challenge whether
all answer-affecting dependencies were disclosed; compilation cannot prove that fact. Refactors do not manufacture changed data meaning.

An operation-version ordinal is an immutable display/registry name for a recipe fingerprint,
not another independently authored version. The complete definition revision remains discoverable
and governs eligibility even when the recipe stays unchanged. Contract fingerprints use a
versioned canonical representation and the relevant semantic closure (types, relations, invariants,
coverage and numerical meaning), excluding unrelated authoring layout. They are not shallow field
shape hashes or hand-maintained reader-field allowlists.

### 4.2 Products, evidence and input bindings

A semantic **ProductIdentity** comprises its kind's semantic contract fingerprint, a stable
subject identity and canonical semantic body digest. Kind names without contract identity are
insufficient across releases. The subject preserves original source identity, projection/recipe,
context, scope, order and occurrence distinctions required by the kind; identical text on two
pages does not merge its occurrences. Project authorization is a separate admission boundary.
A content blob can be shared without conflating semantic products or evidence episodes.

Meaning-bearing source coordinates, native label schemes, choices and coverage stay in the body.
Producing task/runtime/recipe identifiers belong in an attributed support envelope unless the
kind explicitly defines an observation about them. Moving runtime out while retaining producing
operation version inside the hashed layer would defeat equal-content cutoff. Local member IDs
must be stable within the body's canonicalization and avoid self-referential digest construction.
References to members use product plus local member identity.

A **Derivation** records recipe, subject, exact role-labeled inputs, selected replicate, outcome
and output members, with task/attempt/runtime and definition revision as provenance. Distinct
observations remain distinct derivations even when they support one product; deduplication adds
no independent vote. No-product failed/empty/withheld outcomes remain representable. A typed
result bundle can contain several roles/kinds and declared cardinalities; do not split a
coherent multi-output operation solely to satisfy a one-kind restriction. Splitting spaCy and
HanLP is justified by their independent recipe/failure/reuse boundaries, not by a universal rule.

Each input binding distinguishes its semantic value projection from its **support requirements**:
selected provenance, source custody, coverage, admissible outcomes and required relationships.
Membership/order and a complete population witness are inputs where additions, removals, optional
presence or absent lookups can affect the answer. Equal output content stops propagation only
when the consumer's value AND support contract remains satisfied. A provenance-sensitive consumer
cannot silently adopt another derivation because the payload bytes match.

**Revocation** is append-only distrust of specified derivations or a precisely scoped recipe /
executable combination, with reason and scope. It does not mutate or erase a shared product.
Current admissibility can use another qualifying support path only where the consumer's contract
permits it; otherwise the consumer is affected. Explicit replicates retain rival evidence and
selection. Historical snapshots retain their original support and assessment; a present trust
assessment names the revocation snapshot it uses. Revocation, retry and a requested rival
observation have different meanings and are modeled separately.

### 4.3 Subject discovery, sufficiency and eligibility

Use a bounded, typed relational binding specification over declared concepts: role joins,
cardinality, ordering/distinctness, alternatives, optional inputs, scoped predicates and coverage /
population requirements. Compile it to fixed release relations and typed Python ports. It is
not arbitrary callback code or an unrestricted effect language. Specialized predicates that
cannot be expressed by these forms remain named, typed domain operations with declared inputs,
outputs and semantics; their results enter the same model.

The original conjunction of kind presence and literal facet equality is insufficient. Actual
contracts require same-document membership, exact one selected projection and two distinct
passages/readings with closure (native_evidence.py:283–293, m1_source.py:318–328,
structural_products.py:1280–1320). These become reusable declared bindings, not copied branches.
Adapters receive admitted bindings; Method.select becomes a mechanical query adapter or a
separately declared subject-discovery operation. A broad ambient Reader cannot supply undeclared
answer-affecting input. Generated operation-shaped ports expose pinned inputs and capabilities,
including batch/stream and cancellation behavior, without forcing scalar service calls.

A **Demand** freezes requested products, subject universe/discovery binding, explicit producer /
replicate selection and governing release. Discovery may yield new subjects in typed products;
its completeness and membership revision are retained. Every demanded binding has a fate:
not applicable, awaiting inputs/discovery, unknown sufficiency, ready, executing, fulfilled,
partial, failed or cancelled. Currentness/revocation and physical capacity are separate dimensions,
not one overloaded applied/superseded enum. Partial or unknown coverage satisfies only contracts
that explicitly accept it. An unregistered dependency is not independence.

### 4.4 Planner, execution and publication

The planner derives required bindings and ready work from that model. Population selection
chooses independent subjects; actual analyzed selectors/context remain immutable subject/input
bindings, never mere demand provenance (native_evidence.py:412–440). It distinguishes AND
requirements, alternative producers and explicit selection; it does not choose an arbitrary
producer by registry order. Ordinary acyclic dependencies are supported; cycles require a
separately declared iteration/convergence contract or an explicit unsupported-cycle result.
Register dependent tasks only after immutable bound inputs exist. Potential planned dependencies
and actual consumed-input lineage remain distinct queryable projections.

Logical computation/request identity is distinct from an authentic derivation execution identity.
A revoked successful execution can be recomputed under the same recipe and exact inputs while
appending a new derivation; old evidence is never overwritten. Explicit replicates are separate
requested rival observations. PostgreSQL coordinates equivalent in-flight derivations with unique logical request/replicate
identity and existing claim/lease/attempt fences. A **DemandUse** records which exact product,
derivation/support binding and outcome each demand selected, including reuse. Removing reused
status therefore removes copied execution, not observability or demand membership. A failed
attempt does not become a successful derivation and does not erase useful siblings.

Admission and execution have explicit ownership transitions: reserved, submission uncertain,
in flight, collected, reduced and physically retired. A submit exception without a returned
future must not masquerade as temporary capacity backpressure or release potentially live work.
The responsible executor becomes failed/unavailable, retains uncertain ownership until drained,
and reports the original failure. Retain authenticated process/host-generation custody, resolve
uncertainty through an acknowledged settlement, bounded drain or termination/fencing of that
owned generation, and retire capacity only after confirmed settlement/physical termination.
This is a target contract; the book BrokenPipe cause remains
unproven. core/work.py and provider/CPU executors are reusable mechanisms subject to these
contracts, not automatically qualified by retention.

Private computation occurs outside publication transactions. One fenced publication atomically
binds output members, semantic body digests, supporting derivation and demand fulfillment after
rechecking mutable admission premises. Revocation and publication admission serialize on
the relevant authority: publication either precedes revocation and becomes affected historical
work, or observes it and refuses. A commit followed by lost acknowledgement replays the exact
immutable completion intent/receipt, not inference or external effects. Retain the useful
ClaimOwner.settle/PreparedUnitCompletion.apply semantics (claim_lifetime.py:29–112;
operations.py:737–786), with native durable recovery authority where process-independent resume
needs it; managed artifact expiry cannot erase that authority. Frozen PDF builds can be adopted only after verifying exact recipe,
source/schema/input bindings, authorized new ownership and old-writer fencing; derivation-key
relabeling alone is insufficient. Coherent batches and prepared resources may span logical
operations where contracts permit; independent failure/reuse boundaries remain independently useful.

External-agent packets/results and authored selections enter the same model with their own
custody and effects. Effectful command fulfillment has an idempotency/receipt contract: possession
of an equal payload does not prove that a required effect occurred. Consolidation remains
materialized per run/cut, but its consumed bindings, policy, outcome and effects are fully modeled.
It is not an exception to domain modeling.

### 4.5 Cross-release admission, change and reads

Admit cross-release products by semantic kind-contract compatibility PLUS exact subject/source
bindings, required support, coverage/outcome, authorization and current selection/revocation
policy. Equality supplies a fast semantic compatibility case; it does not prove those other
premises. A meaning-changing contract requires an explicit admitted transformation, never a
reader-default coercion. Execution still binds one immutable release/runtime attestation.
Separate executable artifact identity from that attestation for cross-release revocation;
removing release_id alone is insufficient while execution_model_id and semantic_inputs remain
in the manifest (runtime_bindings.py:100–123).

The existing member diff provides direct reference/change facts, not a verified transitive
data-operation graph (operation_reporting.py:791–888). Compile typed producer/consumer closure
from the governing model. Change determination combines old/new declared dependencies, the frozen demand subject universe,
subject-discovery/population witnesses and reverse actual derivation lineage. Existing derivations
alone cannot reveal new subjects or newly applicable work. Report potentially affected, awaiting
upstream determination, proven stale, currently substitutable, revoked, inapplicable and unknown
with reasons. A transitive consumer is potentially affected before new upstream output exists;
it is not automatically stale. After recomputation, propagate only changed value/support bindings.
Cuts record exact consumed bindings and policy, permitting this same relative-currentness report.

Reads remain pinned and do not schedule recomputation or repeat upstream NLP. Authorization,
compatibility and mutable trust checks remain necessary at their actual boundaries. Explanation,
update-need and served views use the same model and explicit snapshot. Original-source reference
release, prediction view and grading recipe remain separate evaluation bindings
(operation_assessment.py:1612–1667). CLI/MCP pagination, exports and detached replay retain the
complete selected source/support closure; absent or revoked evidence remains explicit.

## 5. Findings and corrected dispositions

All corrections are Proposed. F01–F09 remain source identities; their diagnoses are narrowed
where the original overstated absence. New IDs identify defects in the proposed target itself.
No finding below is scheduled by this audit; planning selection is its revisit trigger.

| ID | Corrected finding / consequence | Correction | Basis |
|---|---|---|---|
| F01 | Method, released operation and invocation contracts lack one composed data-operation authority; existing protocol contracts are useful, not absent | C2/C4 | §3; contracts.py:694–716 |
| F02 | Operation explanation lacks qualified live sufficiency, not every production validity check | C4 | operation_reporting.py:193–202; §4.3 counterexamples |
| F03 | Handwritten sequencing/input maps duplicate semantic prerequisites; task fences and explicit physical stages are not themselves defects | C4 | §3; operations baseline |
| F04 | Reuse scope is broader than declared result dependencies; the database's reuse count does not establish its cost or largest cause | C1/C2 | task_dependency_scope.sql:3–40 |
| F05 | Config mixes recipe parameters, selection and exact inputs | C2 | target contracts; native_evidence/config and comparison source |
| F06 | Task/runtime-dependent product identity prevents semantic equality cutoff; observation episodes must still stay distinct | C3 | ProductReference; characterization operation body |
| F07 | No uniform derivation/support and demand-use account; empty specialized tables do not prove lineage universally absent | C3 | identity baseline lists existing layer/PDF/fact lineage |
| F08 | Declaration change reporting does not supply subject-relative update determination; explicit pinned reuse already exists on some paths | C5/C6 | operation_reporting.py:763 onward; retained demand contract |
| F09 | Cuts lack the proposed uniform currentness contract; origin tasks do retain traversable provenance | C7 | ops.cut_task and method/config references; D5 |
| F10 | Kind presence alone loses relational/cardinality/coverage requirements and dynamic discovery | C2/C4 | §4.3 actual supported comparisons and scopes |
| F11 | Unqualified content dedup/cross-release equality can erase support, trust or occurrence distinctions | C3/C5 | §4.2/4.5; source and evaluation guards |
| F12 | One declaration fingerprint conflicts with eligibility-only widening and still embeds production identity in content | C1/C2/C6 | original§7 versus fingerprint; §4.1/4.2 |
| F13 | Removing task reuse/membership without replacement loses per-demand selection and fate; derivations alone cannot find new subjects | C3/C4/C6 | §4.3–4.5 |
| F14 | Blanket regeneration/drop-recreate and unqualified build adoption omit durable source/reference/custody obligations | C3 | pdf_staging.py:129–174; original/prediction release separation |

## 6. Corrected change set

1. **C2 — Governing declaration and binding foundation.** Compose contracts, typed roles,
   result bundles, subject discovery, parameter/input split and recipe/eligibility/execution
   projections first. Include every derived-product family, consolidation and affected read /
   evaluation operations. Generate ports and fixed relational projections. Remove independent
   method identity/config definitions only once every consumer realizes this authority.
2. **C3 — Product, derivation and demand-use foundation.** Implement semantic products and
   member references, attributed support, exact population bindings, attempts, explicit replicates,
   revocations and DemandUse together. Replace task-keyed identities across PDF, characterization,
   observations and downstream structural products. Preserve meaningful evidence episodes.
   Cutover must preserve required original custody, protected reference sets/labels, completed
   snapshots, receipts and evidence closure; regenerate disposable derivations only. Actual
   retained consumers keep sealed interpretation or explicit reviewed correspondence.
3. **C1 — Declared reuse cutover.** Enable reuse under complete recipe/value/support binding
   and admission; remove runtime equality, broad manifest salts and copied reused tasks only
   after C2/C3 supply their semantic, custody and reporting replacements. This is not the
   original low-risk first slice. Preserve exact run/runtime execution attestation.
4. **C4 — Dependency-driven demand execution.** Replace name-based stages/input maps and
   private selectors with declared binding/discovery/eligibility. Preserve physical batching,
   claim fences, uncertain-submission ownership, publication receipts and recovery. Remove
   Graph/Step/SourceOperationLink/source_dependencies only after demand and reporting consumers
   have moved; do not preserve hidden equivalent lists behind the generated port.
5. **C5 — Cross-release admission.** Use explicit semantic compatibility and the complete
   admission contract in §4.5; retain original source and evaluation applicability. Split
   executable identity from release attestation without using executable equality as reuse.
6. **C6 — Change and revocation determination.** Query both old/new declarations and selected
   subject/population universe, then actual lineage. Produce the typed update-need explanations
   for native/CLI/MCP reads. Do not perform eager recomputation or label merely affected work stale.
7. **C7 — Consolidation currentness.** Bind each cut to consumed products/support, recipe and
   policy. Explain currentness relative to an explicit target release and trust snapshot using
   the same change mechanism. Per-run materialization remains a realization choice.

C2/C3 are prerequisites to removing identity/reuse protections. C4 depends on their binding and
demand-use contracts; C5–C7 share admission/change semantics and cannot independently invent
compatibility or staleness. Functional delivery includes affected consumers and removal of
superseded machinery. Detailed implementation packages follow planning, not this audit.

## 7. Change and failure cases

| Case | Required target behavior |
|---|---|
| Refactor with unchanged declared meaning | Same recipe; new executable provenance; no incidental invalidation |
| Model/grammar/semantic parameter change | New recipe; affected bindings considered; identical substitutable value/support stops consumer propagation |
| Eligibility widened without changing result meaning | New definition/eligibility revision; only newly admitted subjects need execution |
| Optional input appears, member removed or ordering changes | Population binding changes where answer-affecting; missing/empty/unknown stay distinct |
| Equal text at different locations; conflicting provider observations | Source occurrences and evidence episodes remain distinct; no extra vote from storage dedup |
| One support path revoked | Reassess consumer-required support; retain raw product and historical snapshots; use rival support only if allowed |
| Concurrent equivalent demands | Coalesce logical work under native ownership; each demand records its selected fulfillment |
| Submit fails without future / stale attempt returns | Preserve uncertain physical custody and original error; no permanent capacity None or unfenced publication |
| Commit succeeds but acknowledgement is lost | Exact receipt replay; no repeated external effect |
| New operation/provider or email quotation context | Add/recompose owned contracts and admitted implementation; no statistics/page-specific planner branches |
| Pinned serving/evaluation across releases | Preserve source/prediction/reference identities and full evidence closure; unknown compatibility refuses |

The supported workload includes the retained316SourceViews/518pages, skewed natural sections,
shared resident providers, multi-page groups and concurrent independent demands on one host.
Set-oriented indexed eligibility/lineage queries, bounded frontiers, immutable prepared contracts
and compatible provider batches supply a credible proposed physical route. No full-book scan per
read, per-kind process or Cartesian expansion follows from the semantic model. Actual throughput,
capacity and implementation qualification are not established by this reasoning.

## 8. Alternatives and physical fit

Retain PostgreSQL transactions, constraints, relational joins and indexed demand/derivation
lookups as the coordination substrate. Existing SQLAlchemy Core/generated typed call bindings
(contracts.py:670–692; operation_call_generation.py:675) provide the compilation/port precedent.
Use LinkML's composed contracts and existing canonical_bytes rather than a new generic object
store. These inspected mechanisms establish interfaces, not a tested new planner. A new schema
compiler feature must cover the declared semantics; generating names alone is insufficient.

Retain specialized domain algorithms behind admitted ports. The simplest conforming design is
one declarative semantic model, fixed relational lowerings and a bounded existing executor;
it can group/split/fuse physical work. A second workflow engine, blanket code-closure fingerprint,
untyped generic effect interpreter and full primitive event sourcing remain unselected.
A smaller model with private selection rules is not a conforming alternative. Additional durable
facts here have consumers: derivations for reuse/lineage, DemandUse for fulfillment/reporting,
population witnesses for completeness/change, and revocations for trust. Attempt workspaces need
current ownership and meaningful recovery receipts, not an event for every lock acquisition.

## 9. Rule impacts

All remain Proposed and require operator confirmation through plan creation. Accepted ADRs
are unchanged. Core semantic-model and fidelity requirements are assessment criteria; existing
ADRs describe current design, not a reason to weaken the target.

| ID | Affected rule | Corrected target change; consequence if retained |
|---|---|---|
| RC01 | ADR-0063 reuse/runtime clause | Runtime is provenance/revocation evidence, not reuse equality; retaining equality prevents intended refactor reuse |
| RC02 | ADR-0060 two-method/full-binding defaults | Complete declared recipe/value/support scope for all operations; retaining defaults leaves broad invalidation |
| RC03 | ADR-0027 release-bound execution | Keep one bound execution release; admit compatible original products with source/support/authorization; retaining same-release-only inputs limits cross-release use |
| RC04 | ADR-0081/0082 product pins | Semantic product/member plus selected support bindings; retain explicit selection/no latest; old task-only pins block value cutoff |
| RC05 | ADR-0084 stage runs; ADR-0090 invocation links | DemandUse and modeled bindings replace stage-run sequencing/grouping; late registration/fences/receipts stay; old boundaries otherwise constrain planner |
| RC06 | ADR-0033 fixed projections | Extend model-derived operation/binding/eligibility relations without arbitrary effects or EAV; unchanged projection set cannot realize planner |
| RC07 | ADR-0014 per-run materialization | Retain materialization, add exact consumed bindings/currentness; without extension cut-currentness remains incomplete |
| RC08 | ADR-0085/0091 provider/numerical identity | Declare semantic recipe separately from full execution/acquisition profile; preserve observed numerical/batch evidence and CUDA/dtype policy. Whole-profile hashing otherwise retains runtime/thread invalidation |
| RC09 | ADR-0050/0064/0067 source custody/current-only cutover | Change reference/admission representations with preserved originals, completed snapshots and protected evaluation closure; blanket instance destruction is not authorized regeneration |

D1 owns semantic identity, D2/D4 declaration and typed ports, D3 persistence/admission,
D5 consolidation, D6 planning/change and D7/D8 evaluation/served bindings. These owners change
only through the subsequent decision/implementation route.

## 10. Verification and uncertainty

**Interface-checked by source inspection, 2026-11-12**: decisive contracts, actual cardinality /
source guards, task dependency scope, profiles, runtime manifest, private PDF adoption, release
comparison and evaluation applicability. Versioned canonical encodings must distinguish absent/empty, typed numeric values/defaults,
ordered sequences and declared sets; existing canonical utilities have different contracts
(identity.py:16–31 versus core/method.py:96–125) and are not interchangeable by name.
The original DB counts are historical observations,
not newly queried and not evidence of a measured benefit. No tests, database changes, model calls,
benchmark or protected reference-answer reads were performed for this audit.

Subsequent implementation should independently challenge the cases in §7: canonical identity
under serialization changes; identical bytes with different source/support; deletion/negative
membership changes; eligibility-only changes; revocation and rival support; concurrent fulfillment,
failed submission, stale completion and acknowledgement loss; frozen-build adoption; cross-release
source/reference refusal and retained CLI/MCP/export/replay closure. Generated conformance checks
cannot independently establish the model's adequacy. These are acceptance scenarios, not a new
standing suite, mandatory profiling campaign or proof framework.

The target decisions above replace routine design questions left to planning by the original.
Exact relation/index layouts and port-generation mechanics remain implementation choices under
these contracts. Semantic closure compilation must be qualified against real composed declarations;
if it cannot preserve their constraints it is an implementation blocker, not permission for a
shallow field-only digest. No universal semantic-equivalence inference is promised: substitutability
is exact under the declared value/support contract; other equivalence requires a named operation.

## 11. Judgment and disposition

| Judgment | Revised target assessment |
|---|---|
| A1 Localize change | Satisfied at Proposed design level: owned declarations and compiled bindings replace independent interpretation; all affected consumers included |
| A2 Encode domain meaning | Satisfied at Proposed design level for the corrected contracts; implementation must realize them, including discovery, evidence/support and demand fate |
| A3 Compose capabilities | Satisfied at Proposed design level: operation-shaped ports with explicit multi-input/output bindings and physical grouping |
| A4 Execution fit | Satisfied qualitatively at Proposed design level for the named workload via indexed set operations/preparation/bounded executor; no measured capacity or runtime qualification claim |

Each verdict below assesses the **specified Proposed target by static reasoning**, not existing
production or future implementation. Qualification and adapter conformance remain open.

| Gate | Target verdict and independent basis |
|---|---|
| G1 Authority | Pass: one composed operation authority; compiled projections; product/support/attempt identities separated |
| G2 Fidelity | Pass: typed scope/cardinality/native schemes, distinct coverage and outcomes, explicit contract correspondence |
| G3 Validity | Pass: binding construction and native publication reject invalid relationships/source/support; compiler shape checks do not replace adapter conformance |
| G4 Hidden behavior | Pass: scoped read/effect capabilities, declared dependencies, pure pinned inspections and explicit effect fulfillment |
| G5 Recovery | Pass: fenced producer, atomic publication, exact uncertain-completion replay and bounded authenticated physical retirement |
| G6 Reuse/transformation | Pass: complete recipe/value/support/population bindings and consumer-relative substitutability; no blanket byte equality |
| G7 Claims | Pass: all target benefits Proposed; inspected mechanisms Interface-checked; no implementation/performance certification |
| G8 Library leverage | Pass at selected-design level: existing PostgreSQL/schema/typed-call mechanisms; no new generic engine selected or future bespoke algorithms prequalified |
| CI-G1 Fidelity | Pass: attributed evidence episodes, source/coverage/unknown distinctions and declared numerical semantics survive reuse |
| CI-G2 Evidence closure | Pass: pinned demand-result/cut selection retains source/support/choice closure across resources, exports and continuations |
| CI-G3 Evaluation integrity | Pass: original reference frames, prediction selection and grading recipe bind separately; protected evaluator capabilities cannot enter producer discovery |

**Decision: Accept corrected target for plan creation, at Proposed/static evidence strength.**
The original proposal requires the corrections above; it is not accepted unchanged. Product
implementation, migration and qualification remain open. F01–F14/C1–C7 are now scheduled by the standalone
[DDO coordinator](../../plans/declared-data-operations_2026-11-12.md#finding-and-recommendation-disposition),
which solely owns their current disposition. The operator explicitly accepted RC01–RC09 on
2026-11-12 during plan preparation; that decision is recorded there, not attributed to this audit.
The new series owns its redesign and qualification independently of other plans. No production
repair, deployment or book retry is performed by publishing these documents.
