# Design review — declared data operations

**Design / target inquiry · 2026-11-12 · author: the root Claude session, at the operator's
request, with delegated read-only mapping of design authority, operation code and identity
storage and one delegated planning pass that tested the target against the code.** This is not
an independent `design-reviewer` engagement. It consumes no refreshed audit and does not count
toward the binding's review cadence.

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
| Operator directions (2026-11-12) | Section 9 records the four scoping answers given during the inquiry |
| Standard | [Design principles](../design_principles/core/design-principles.md) DP-04, DP-08, DP-09, DP-19, DP-21 and FP-02/03/05; [heuristics](../design_principles/core/efficient-architecture-heuristics.md) H13, H22, H25, H26 |
| Tier · purpose | Design · target |
| Evidence rule | Source inspection only. No test runs, benchmarks or database changes. No speed or capacity figure is asserted |
| Outcome sought | A target model and an ordered change set that plan creation can adopt, with the rule impacts it would need confirmed |

**Coverage.** The author read directly: the `Method` protocol, `OperationContract`, one released
contract, `CharacterizationOperation`, the task hash construction and its salts, the reuse rule
in SQL, the characterization inputs map, the declared demands and parsing adapters, and
ADR-0060, ADR-0063 and ADR-0090. The operation inventory, the identity table, the schema
inventory and the per-finding ADR and design-section readings come from the delegated sweeps and
were not all re-read. Not covered: evaluation and grading, the serving read side beyond the
tools named, and the Rust crate, which is a placeholder.

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
- **Change impact is already computed from declarations.** `compare_semantic_releases` diffs
  two releases member by member and computes the consumer closure
  (`semantic/operation_reporting.py:763`).

The operator already directed, in ADR-0063, that a code change must not manufacture new data
meaning. One retained clause of that record, that task reuse respects runtime identity, is the
largest single cause of lost reuse today.

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

## 4. Target state

All of section 4 is **Proposed**.

### 4.1 Concepts

| Concept | Definition | Replaces |
|---|---|---|
| **Product** | Immutable, of a declared kind, about a subject, identified by kind, subject key and content digest. Task, run and release are provenance columns | Task-keyed product references and primary keys |
| **Data operation** | One declaration form in the release execution model: subject; consumed kinds with required outcomes; one produced kind; applicability; effect class (`derive`, `augment`, `author`); executor; behaviour version; result determinants | `Method` identity attributes, `OperationDescriptor`, result dimensions under `configure_method`, `source_dependencies` literals |
| **Adapter** | The implementation bound to exactly one data operation through a generated typed port. Keeps `select` and `run` | The protocol's identity fields and `input_digest`; `getattr` discovery of `plan` and `close` |
| **Operation version** | A registered ordinal naming the fingerprint of the declaration: identity, behaviour version, parameters, model and grammar asset digests, provider profile (ADR-0091), numerical policy (ADR-0085), and the contract digests of consumed and produced kinds | `ops.method`, `ops.method_config`, the run dependency manifest as identity |
| **Derivation** | Append-only record: operation version and exact input products, to an output product and outcome. Its key is built from the version and the input identities. It records runtime identity, task and demand as provenance. Several derivations may name one product | `input_hash`, `reused_task_id`, the `reused` status, `ops.task_dependency` |
| **Demand** | Target kinds requested over a subject set under one release | The run as an identity scope; one-stage characterization runs; `SourceOperationLink` |
| **Revocation** | A recorded statement that derivations of an operation version made under named runtimes are distrusted | `fresh` and the `characterization_freshness` hash salt |

**Not determinants.** Executable bytes, runtime identity, thread counts, batching, device
placement, resources and library versions that an operation does not declare are recorded and
never compared.

**Granularity.** Version granularity equals product granularity. Where determinants separate
inside one product, the operation is split. `text.native_evidence` bundles spaCy and HanLP
evidence and would become two operations.

### 4.2 State and eligibility

For an operation and a subject, state is derived from declarations and derivations relative to
one release: not applicable, awaiting inputs, eligible, applied, superseded or revoked. Nothing
stores a mutable latest selection, which keeps ADR-0082.

Applicability is a conjunction of two row forms, so that SQL and Python evaluate the same
declared rows: a consumed kind is present with an outcome in a declared set, or a declared facet
of the subject equals a literal. These project to fixed release-scoped relations in the style
of ADR-0033.

*Example.* `annotate.spacy` consumes a source view's text with outcome complete and produces a
spaCy native-evidence layer. A source view is eligible once recognition has produced its text
and no derivation exists for the current `annotate.spacy` version over that text. After it runs
the view is applied and no longer eligible. If the spaCy model asset changes, the operation
gets a new version: every source view is eligible for it again, the old layers and their
derivations remain, and a consumer of the layer needs updating only where the new layer's
content differs.

### 4.3 Sequencing

Ready work is planned from eligibility. Dependent work is registered only after its input
identities exist, which keeps ADR-0084's late registration. The existing claim, lease and
attempt fences and the in-process ready frontier (`core/work.py`) execute it. No durable general
graph is stored: the durable facts are derivations.

### 4.4 Change determination

Reads do not re-verify or recompute. Change need is determined when a declaration changes.
Extending the existing release comparison, a changed declaration yields the affected operation
versions and their consumer closure; the affected subjects are reported from the derivations.
The declaration change and revocations are stored. Per-subject update need is a query at
planning or reporting time, not a stored table.

### 4.5 Record of actions and prior state

Derivations and revocations are append-only, and superseded products are retained, so a step
can be re-derived from its recorded inputs without redoing upstream work. An operation with
effect `augment` produces a layer over a base product, so the state after it is the base plus
the layer; characterization layers and `data.batch` already have this form. Operations such as
PDF conversion and recognition stay `derive`. Lease and claim changes are not recorded as
history (H26).

### 4.6 Reach

All derived products: ingest, recognition, language evidence, characterization, extraction,
structure and M1. Claim consolidation and the published `data.*` graph stay materialized per
run (ADR-0014), and a cut records the derivations it consumed so that its staleness is known.

## 5. Finding index

| ID | Finding | Principle | Correction |
|---|---|---|---|
| F01 | Data operations have no uniform declared contract. Three meanings of "operation" are unconnected, most methods have no released contract, and six sites bypass `Method` with an ad hoc `OperationDescriptor` (`semantic/operations.py:180`, `orchestrate/pm2_stage.py:410/632/674`, `semantic/native_requests.py:370`, `semantic/visual_requests.py:129`, `orchestrate/semantic.py:1597`) | DP-08, FP-02 | C1, C2 |
| F02 | Applicability is declared but not evaluable. `explain_operation` reports every applicability invariant as unresolved (`semantic/operation_reporting.py:193-202`), so nothing checks that an object is sufficient for an operation | DP-08, DP-19 | C4 |
| F03 | Sequencing is hand-written and restated. `Step.upstream` is read only by two tests; characterization order and its inputs map are literals; adjacent methods are paired by name (`orchestrate/semantic.py:1835-1865`); method names and pinned versions recur in SQL; 28 test files restate graphs or stage order | DP-19, H22 | C4 |
| F04 | Reuse is gated by identities far wider than the operation. Any change to the owned executable package changes `runtime_id` and disables all reuse. For every method except two, any other operation's configuration or any listed library version changes the scoped manifest. Thread profile enters the hash for primary producers (`orchestrate/semantic.py:729-730`). The development database held 45 reused tasks of 2,409 | DP-09, H13 | C1 |
| F05 | `Config` mixes result-affecting parameters with subject selection and input pins (`methods/native_evidence.py:45-47`, `methods/structural_products.py:1328-1334`), so a configuration hash cannot serve as an operation's identity | DP-04 | C2 |
| F06 | Derived identities include execution identities. Product references and primary keys carry the producing task; the source-view key includes the consuming release and native task; observation keys include a random invocation key (`semantic/observations.py:224-239`); layer payloads embed runtime and the task hash, so their content digests change with code | DP-04 | C3 |
| F07 | Lineage is partial and reuse is not a fact about data. `kb.observation_input` holds no rows and `ops.task_dependency` holds one edge kind in the development database; reuse is a task status copied per run; a fresh result is requested by salting the hash | DP-21 | C3 |
| F08 | Change impact is computed and then unused. The release comparison yields affected operations and their consumers but determines no affected subjects, and reuse never crosses releases, so an unrelated release change recomputes everything | DP-09, H13 | C5, C6 |
| F09 | A consolidation cut records its origin tasks, not the operation versions and products it consumed, so whether a published realization is stale relative to current declarations cannot be derived | DP-21 | C7 |

## 6. Corrective arguments

C1 and C2 each leave one model in force. C3 is a single cutover. C4 to C7 follow C3; C5, C6
and C7 are independent of one another.

### 6.1 C1 — Declared determinants own reuse

Add a `data_operations` section to the execution model, compiled beside `OperationContract`,
generalizing the three existing declared forms in section 2. Build the task hash from the
operation's declared determinants.

Remove: `ops.task_dependency_scope`; the runtime-equality condition in `ops.valid_reuse`; the
manifest's hand-listed libraries and operations as identity; the thread-profile and
producer-origin salts; and `runtime` inside layer result determinants
(`methods/native_evidence_layers.py:107`).

This gives the most relief for the least risk, because source edits and other operations'
configurations stop invalidating. It costs one full recompute, since every hash changes once.
*Check:* edit a source file that no declaration names and rerun a demand, and every task
reuses; bump one behaviour version, and only that operation reruns.

### 6.2 C2 — Port, parameter split and version registry

Split each `Config` into parameters, subject selection and input pins. Generate a typed port
per operation, following the generated database-call layer
(`semantic/operation_call_generation.py:675`). Fold the six descriptor sites in and split
`text.native_evidence`. Register operation versions in the release schema.

Remove: `OperationDescriptor`, `Method.version`, `ops.method` and `ops.method_config`.
*Check:* two subjects share one operation-version row; an adapter without a declaration is
refused when the registry loads.

### 6.3 C3 — Content product identity and derivations

Product references become kind, subject key and content digest, and product primary keys
follow. The source-view key drops the consuming release and task; observation keys use the
derivation key. Add derivation, derivation-input, derivation-output and revocation records.
Re-key PDF private builds by derivation key, keeping task, attempt and holder as fences, so a
frozen build survives a new demand (`semantic/pdf_staging.py:43-52`).

Remove: `ops.task_dependency`; `reused_task_id` and the `reused` status; `ops.valid_reuse`;
`ops.select_reused_source_views` and `ops.run_source_view`; `fresh` and the freshness seed. A
wanted rival result becomes an explicit replicate on the derivation, selected explicitly.

This is one cutover across the product, characterization and PDF stores, by forward migrations
that drop and recreate from the physical model, and it regenerates derived products.
*Check:* rerunning an upstream operation with identical content leaves its consumers applied;
a frozen PDF build is adopted by a new demand.

### 6.4 C4 — Planner and sufficiency

Project data operations and their consumed kinds to fixed release relations. Plan ready work
from eligibility. Make `explain_operation` answer whether a given object can be passed to an
operation and what is missing.

Remove: `Graph` and `Step`; name-pair grouping; the characterization inputs map and stage
sequence; one-stage runs; `source_dependencies` literals; `SourceOperationLink`; method-name
literals in SQL; and the tests that restate pipeline order.
*Check:* one demand runs capture through the composed view in declared order and resumes after
a kill without duplicate derivations.

### 6.5 C5 — Cross-release admission

Admit an input product derived under another release when its kind contract digest equals the
consuming release's. Remove the release from the runtime manifest
(`semantic/runtime_bindings.py:107-112`) so that a revocation by runtime can span releases.
*Check:* a release that changes one unrelated concept reuses every derivation.

### 6.6 C6 — Change determination and revocation

Extend the release comparison from affected operations to affected operation versions and
subjects, with a `ci` view and the matching served read.
*Check:* a model-asset change lists exactly that operation's subjects and its consumer closure;
revoking a runtime surfaces its derivations.

### 6.7 C7 — Consolidation staleness

A cut records the derivations it consumed, and a report compares them with current
derivations.

### 6.8 Fit of special cases

| Case | Fit |
|---|---|
| PDF private build lifecycle | Fits as an attempt workspace that is not recorded as history; re-keyed by derivation key |
| External agent tasks | Fit with a declared external executor; awaiting an agent is eligible and externally assigned, and the packet hash is the input pin |
| Run-unit structure methods | Fit once their subject is a content-addressed authored selection in place of inputs carried in configuration |
| `consolidate.claims` | Does not fit and stays per run; its subject is the cut |
| Non-deterministic GPU providers | Fit as they stand under ADR-0085; the determinant is the declared numerical policy and reuse selects a retained observation |

## 7. Change scenarios

| Change | Effect under the target |
|---|---|
| Code refactor with an unchanged declaration | Nothing. Later derivations record the new runtime identity |
| Behaviour version, parameter, model or grammar asset, or numerical policy change on operation X | New version of X. X's subjects become eligible again. A consumer needs updating only where X's new output content differs |
| Threads, batching, device placement, resources | Nothing |
| Applicability widened | Only newly applicable subjects become eligible |
| A new operation, or one inserted between two others | Only the new operation, and consumers whose declared input kind changed |
| A product kind's contract changes | Producers and consumers of that kind |
| Unrelated release change | Nothing |
| Implementation defect found | A revocation; the affected derivations show as needing update |

## 8. Alternatives

1. **Narrow each method's reuse scope by hand**, extending `ops.task_dependency_scope`. The
   smallest change. It restates in SQL what each method depends on, leaves runtime equality in
   force and leaves order hand-written.
2. **Fingerprint each operation's code closure.** Rejected by the operator: invalidation must
   follow the operation as declared. A refactor would still invalidate.
3. **A workflow or asset-versioning library.** It would supply staleness and planning but adds
   a second authority over task state beside PostgreSQL and the release, which the design
   rationale declined. The operator chose to extend the existing kernel.
4. **A stored per-object state log, or full event sourcing.** Not selected. Update need is
   derivable from declarations and derivations, a stored copy would need its own consistency
   rule, and delta outputs do not fit conversion and recognition.

## 9. Operator directions and rule impacts

**Directions given during the inquiry, 2026-11-12.**

| Topic | Direction |
|---|---|
| Reach | All derived products. Consolidation and the published graph stay per run and record what they consumed |
| Code and invalidation | Invalidation must not come from hashes of code. Code may change massively; if the operation executed does not change, nothing is invalidated. Contracts and declared state transitions determine invalidation |
| Recomputation | No recomputation as a matter of course when data is called on. The value is characterizing precisely when data needs updating. A constitutive, before-plus-alteration form is useful where expressible and not required |
| Engine | Extend the existing PostgreSQL task kernel |

**Rule impacts.** Each is **Proposed** and needs confirmation and a decision record through
plan creation. Accepted records are unchanged by this review.

| ID | Rule affected | Proposed change |
|---|---|---|
| RC01 | ADR-0063, "task reuse also respects runtime identity" | Runtime identity is provenance and a revocation handle, never a reuse condition. The semantic and runtime split, the run pin and the start and claim comparison stand |
| RC02 | ADR-0060, the two-method dependency projection and full-binding defaults for other methods | Declared determinants supply every operation's scope |
| RC03 | ADR-0027, one pinned release per operation | Execution still binds one release; inputs from another release are admitted by kind contract digest |
| RC04 | ADR-0081 and ADR-0082, product pins | Pins become content identities. Explicit selection and no latest selector stand |
| RC05 | ADR-0084 stage-run boundaries; ADR-0090 run-option operation link | A demand groups the work. Late registration, receipts, no broker or durable general graph, and the reporting obligations stand |
| RC06 | ADR-0033, fixed release relations | Add data operations and their consumed kinds. No effect interpreter or generic store |
| RC07 | ADR-0014, per-run materialization | Kept. A cut records the derivations it consumed |

ADR-0083, ADR-0085 and ADR-0091 are unaffected. Section owners for an adopted target would be
D1 for product identity, D3 for derivation, version and revocation storage, D4 for the
declaration, port and determinants, D5 for cut staleness, D6 for demand, eligibility and change
determination, and D8 for sufficiency and update-need reads.

## 10. Verification and uncertainty

Each correction names a functional check in section 6. An assembled check would run one demand
over the retained book capture to the composed view, confirm that an identical second demand
creates no derivations, and confirm that one declared parameter change reruns only that
operation and the consumers whose input content changed. None of these was run.

Risks, each with what would change the design:

1. **The behaviour version is the only automatic guard against an undeclared behaviour
   change.** Stale products are retained until someone notices, and revocation is the remedy.
   If revocations recur for an operation, declare its library versions as determinants, as
   parsing adapters already do with a frontend revision.
2. **Kind contract digests may be too coarse.** One shared model mixin edit could change every
   kind. If the first real model edit invalidates broadly, digest only the fields a kind's
   readers use. Whether a per-kind digest is derivable from the existing member walk is
   inferred, not verified.
3. **The parameter split touches every method and its tests.** A method that cannot separate
   selection from parameters keeps an authored selection as its subject.
4. **C3 is one cutover** and regenerates the book corpus. It belongs after the BEP/TC
   qualification closes.
5. **Replicates create rival products.** A default among them would need an explicit selection
   decision.

## 11. Dispositions and decision

**Decision: Revise.** The target in section 4 and corrections C1 to C7 are Proposed. F01 to F09
are Deferred until a plan selects them; none is scheduled, and the trigger is the operator
choosing to plan this target. No production change is authorized by this review, and the
BEP/TC qualification in progress is unaffected. Source is frozen during its invocations, so
production work on any correction would start after that qualification's book retry settles.

**Architectural judgment.** On semantic ownership, the target gives each data operation one
declared owner for its contract, determinants and state transition, where today these are
restated across Python, SQL and tests. On execution fit, it removes recomputation caused by
unrelated changes and adds no machinery on the read path; its durable additions are the
derivation and revocation records and the operation-version registry. It keeps PostgreSQL and
the semantic release as the only authorities. The judgment is qualitative and no gain is
measured.
