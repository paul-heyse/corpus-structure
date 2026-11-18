# Test domain model and execution

**Status:** In execution; scoped verification recorded and integrated qualification open. **Created:** 2026-11-17. **Revised:** 2026-11-18.
This coordinator owns the series' combined target, shared contracts, package queue, rule-change
record and the scheduled disposition of every finding it lists. Companion plans own the detailed
designs and package descriptions. Architecture pages and accepted ADRs remain the authority. The operator authorized
implementation on 2026-11-18.

## Outcome and source baseline

Give the test system one rule for what a test may take from the product's domain model and what
it must keep independent, and make the test system's own concepts explicit enough that
preparation is reused exactly, doubles replace only what is external, reuse mechanisms have
evidence that can fail, and test machinery retires with what it serves. The tests that source
shows cannot set up or pass get their evidence back first. The result should also keep the
production changes that are now likely (finer implementation identities, facts moving from code
lists into declarations, further generated SQL) local when they reach the tests.
Add a bounded managed CLI view for reviewing one test selection across its attempts, using the
same result custody and evidence as execution and retry.

**Source.** The [design review of the test domain model and execution](../design_review/reviews/design_review_test-domain-model-and-execution_2026-11-17.md)
(publication `caa841b01`, read at `main` `1afa63f88`, judgment Revise) and its
[dispositions](../design_review/reviews/test-domain-model-and-execution/dispositions.md). The
review consumed the [test audit](../design_review/test-audit/README.md) and the
[joint model-and-execution page](../design_review/audit/model-and-execution.md) at `aca50eeea`,
and superseded the 2026-11-13 test-system review. Section references below (§4.2 and so on) are
to the principal review unless a companion is named.

The [plan-improvement review](../plan_improvement_reviews/test-domain-model-and-execution_2026-11-18.md)
(`105048abf`, source inspected at `aea554e5c`) refines the package designs and adds TDM-19.
The [review disposition](#improvement-disposition) links each recommendation to its owner.
The review re-read affected paths and used retained receipts and an isolated reporting probe;
these supplement the baseline below within their stated scope.

**Authoring baseline.** `main` `50827eb9f`, 2026-11-17, 37 commits after the review's baseline.
Another session was converting maintained PostgreSQL SQL to generated SQL
([ADR-0131](../adr/0131-model-owned-postgresql-programs.md)) throughout authoring.

**Revision baseline.** `main` `12f57dc4d`, 2026-11-18, 104 commits after the authoring baseline.
The conversion is complete and its full validation is under way (operator, 2026-11-18), so the
series was re-baselined at that commit: every package's cited sites were re-read in a frozen
export of it, line citations are as of it, and what the conversion delivered was taken out of
scope. The two re-baseline reports are the
[boundaries re-baseline](../design_review/evidence/2026-11-17_test-plan-authoring/rebaseline-boundaries.md)
(TDM-01, TDM-09 to TDM-12, TDM-15 to TDM-17) and the
[identity re-baseline](../design_review/evidence/2026-11-17_test-plan-authoring/rebaseline-identity.md)
(TDM-03 to TDM-08, TDM-13, TDM-14); [Revision · 2026-11-18](#revision-2026-11-18) summarizes the
change. The investigation reports written during authoring are kept in the evidence folder
`docs/design_review/evidence/2026-11-17_test-plan-authoring/`: the
[current-state map](../design_review/evidence/2026-11-17_test-plan-authoring/state.md), the
[PDF source consumer map](../design_review/evidence/2026-11-17_test-plan-authoring/pdf-source-consumers.md),
the [seam advice](../design_review/evidence/2026-11-17_test-plan-authoring/seams.md), the
[library capability notes](../design_review/evidence/2026-11-17_test-plan-authoring/library-capabilities.md)
and the earlier [test map](../design_review/evidence/2026-11-17_test-plan-authoring/test-map.md).

**Execution premise (operator, 2026-11-18).** The ADR-0131 conversion is complete and under
validation, and this series executes after it. Packages are written against `12f57dc4d`. Each
package that the conversion touched carries a short "Delivered by the conversion" note naming
the delivering commit and states only its remaining scope. Because validation is still running,
source may move further; [TDM-00](#tdm-00) re-reads relevant changes after `12f57dc4d`, their
affected test consumers, and relevant retained failure receipts. The review's §13 column
"coordinate with the conversion" no longer applies: the
conversion certified the converter copies (DTA-041) itself, TDM-01 and TDM-16 take the readers
its SQL retirements left behind, and TDM-06 covers provisioning. The conversion's remaining
production work is [context for this series](#handovers). Updates to the DDO plan follow
completion of TDM.

<a id="glossary"></a>

**Terms used across the series.** The *conversion* is the ADR-0131 work, and its numbered steps
are cited as the review cites them: step 3 moves controlled PDF fixtures through the certified
producer, step 4 converts the kernel SQL, step 5 routes host bootstrap and test provisioning
through shared administration builders, and step 6 turns analytical SQL into DuckDB relations.
The *head* is the sealed, keyed and verified database that the migration chain builds and from
which test databases are cloned ([ADR-0133](../adr/0133-native-test-deployment-inputs.md)). A *seed*
is a sealed, worker-local database that holds one prepared scenario on top of the head
([ADR-0134](../adr/0134-native-test-scenario-bindings.md)). A *commit clone* is a fresh database
cloned from a seed or the head for one consumer that commits. A *rollback family* is a group of
tests that share one clone, each inside a transaction that is rolled back. The *read class* is a
read-only, rolled-back transaction on a worker's session clone of the head. *DDO* is the
identifier of the plan series that owns the data-operation work (its packages are DDO-nn, and
`ddo_` prefixes the native data-operation functions). *PM2* appears only in the names of existing
support modules and production error types, such as `current_pm2_native_support.py` and
`Pm2WorkerError`, and is used here only to name them.

**Evidence status.** Every design statement here is **Proposed**. Source facts re-read at the
revision baseline are **Interface-checked by source inspection, 2026-11-18**; a fact that was not
re-read keeps its 2026-11-17 label and is marked where it appears. Where the series says a test
cannot set
up or pass, that is read from source and was not run. Durations are quoted only from the
review, which read them from stored results. No package has a speed target and no measured
speedup is a completion criterion.

**Scope.** Package tests under `python/corpus-structure/tests/`, every `conftest.py`, the root
scripts the tests use (`scripts/native_test_support.py`, `native_deployment_key.py`,
`native_deployment_build.py`, `native_scenario_seeds.py`, `qualification_plugin.py`, and the
`--principals` mode of `scripts/pg_semantic_roles.sh`, which has no caller left and which TDM-06
removes),
the tests under root `tests/scripts/` for the scripts this series changes (the deployment key,
the lifecycle support, the seed registry and the qualification plugin, including
`tests/scripts/test_native_deployment_key.py` and `tests/scripts/test_native_scenario_seeds.py`),
the test-assessment companion of the design standard, two superseding ADRs, and three bounded
production changes that give test doubles a production owner to delegate to
([the seams](#shared-contracts)). Production code kept alive only by tests retires with those
tests, inside the package that owns them. TDM-19 covers the managed test review command,
its directly affected CLI and receipt readers, the command reference, and targeted CLI tests
([managed test review](test-domain-model-and-execution/managed-test-review.md)). See
[retirement rule 4](test-domain-model-and-execution/declarations-retirement-and-execution.md#retirement-rules).
Out of scope: any other production remedy, including every correction of the production findings
DA-068 to DA-081; edits to other plan series; the DDO-12 qualification union, which stays with its
owner; and the rest of the repository-root `tests/` tree. The original review did not read the root
`tests/` tree. The revision scanned it for fixture definitions and list names and read the
deployment key's tests; TDM-00 reads the other in-scope files under `tests/scripts/` before any
package relies on a statement about them.

<a id="rule-changes"></a>

## Rule changes confirmed by the operator

The operator accepted all four rule impacts of the review on 2026-11-17, and one further rule
change that authoring revealed (RC11). Accepted ADRs are
immutable, so each ADR change is a superseding record written in [TDM-00](#tdm-00), with the
owning design section amended in the same commit.

| Item | Decision | What changes | Route | Needed by |
|---|---|---|---|---|
| RC07 | Accepted 2026-11-17 | The deployment key covers what the build runs: the migration chain production deploys, located by production's own constant; the native bodies its revisions execute and their module-level imports; artifacts by content instead of size and modification time. Steps executed during a build are reached from the construction entry, whose closure is keyed; provisioning applied to the server beforehand enters as observed server facts (role names, attributes and memberships), not as source | [ADR-0133](../adr/0133-native-test-deployment-inputs.md) supersedes ADR-0101 | TDM-06 |
| RC08 | Accepted 2026-11-17 | A seed recipe is content only. A workspace or asset location is a binding the builder supplies. A recipe that needs a per-consumer binding is built in the consumer's clone and never sealed | [ADR-0134](../adr/0134-native-test-scenario-bindings.md) supersedes ADR-0102 | TDM-07, TDM-08 |
| RC09 | Accepted 2026-11-17 | The `db` mark derives from the native root fixture and worker groups are declared where a fixture is defined. The two hand-kept name lists are removed | Recorded here; the earlier series' TS-12 mechanism is replaced. No ADR | TDM-15 |
| RC10 | Accepted 2026-11-17 | Infrastructure clones may serve rolled-back connections for SQL expression checks that install only temporary objects | ADR-0133 | TDM-16 |
| RC11 | Accepted 2026-11-17 (revealed by authoring) | ADR-0102 says nothing built under an implementation override is seedable. A seed may now be built behind a controlled boundary double when the double's content is part of the recipe, and so of the seed's identity, and production's own protocol and checks still run. Seeds built under any other implementation override stay forbidden | ADR-0134 | TDM-08 |

Two further confirmations from the same decision. The completeness case of a perturbation
table (a test that fails when a mechanism declares a determinant no case covers) is a test of
one mechanism's behaviour, not a design-alignment lint. The model-binding rule becomes part of
the design standard: it is added to the
[test-assessment companion](../design_review/design_principles/core/test-assessment.md), which
moves from 1.2 to 1.3 ([TDM-02](test-domain-model-and-execution/model-binding-and-independence.md)).
That edition change needs no ADR of its own: the operator's decision recorded here is its route,
and the standard's manifest and binding are unchanged.

Rule changes RC01 to RC04 of the 2026-11-13 review carry unchanged (review §11). RC09 replaces
the mechanism of the earlier series' TS-12, and RC08 refines RC04.

## Target and foundation assessment

The test architecture delivered by the earlier series holds and is the base: a sealed, keyed
and verified deployment head; worker-local sealed scenario seeds; isolation chosen by what a
claim needs; a refusal contract; support modules for the data-operation tests; a wire-checked
storage double; literal identity vectors. The review found three places where the test
system's own model is thinner than the work it governs, and this series corrects them.

**Tests have no rule for what they may take from the product model.** Support modules retype
how a domain pack is composed, one scenario pairs a compiled model with a release that does
not contain it, a test copies a production formula to compute its expectation, a double
invents a refusal production does not have, and tests read production SQL files by path and
cut text out of them. Each is a different answer to the same unasked question. The series
states the answer once, as [the model-binding rule](#shared-contracts), and applies it.

**Preparation identity mixes content with where things run, and its largest key looks at the
wrong input.** The PDF scenario recipe embeds the per-test directory, so every PDF scenario is
unique and is sealed as a seed nobody can reuse. Authoring found a larger defect than the
review recorded: the deployment key hashes the frozen `semantic_alembic` tree, while the build
it keys runs `target_alembic` (`scripts/native_test_support.py:912`;
`src/corpus_structure/semantic/migrations.py:14`). An edit to a deployed revision does not move
the key; only the per-process verification of revision and catalog stands between such an edit
and a stale head. The conversion left this unchanged while the deployed tree grew from 22 to 29
revisions.

**Machinery is declared away from what it names.** Two lists of fixture names drifted from the
fixtures that exist; nine PDF converter doubles each restate how a stream request is assembled
and write a preparation entry production would not accept, although the conversion now sends
their replies through production certification; mechanisms that reuse work or skip a check are
tested only where reusing is correct.

The target adds no framework. It adds a small number of named concepts and removes the copies
and lists they replace.

| Area | Target in one sentence | Companion |
|---|---|---|
| Model binding | Scenario construction comes from the model's owner; expectations stay independently authored; a claim that a realization follows its declaration is tested by changing the declaration in the test | [Model binding and independence](test-domain-model-and-execution/model-binding-and-independence.md) |
| Preparation identity | A preparation is keyed by its content and lives as long as the implementation that built it is fixed; where it runs is a separate binding | [Preparation identity](test-domain-model-and-execution/preparation-identity.md) |
| Controlled boundaries | A double replaces one external computation, production's protocol and refusals still run, and each boundary has one owner that delegates to a production seam | [Controlled boundaries and seams](test-domain-model-and-execution/controlled-boundaries-and-seams.md) |
| Reuse evidence | Each reuse or skip decision has cases that distinguish the determinants that can change its result | [Reuse and refusal evidence](test-domain-model-and-execution/reuse-and-refusal-evidence.md) |
| Declarations and retirement | Preparation follows each item's resolved fixture definitions, and a test obtains its subject from the subject's owner, so a retirement breaks its dependents visibly | [Declarations, retirement and suite execution](test-domain-model-and-execution/declarations-retirement-and-execution.md) |
| Managed test review | One read-only view combines the required selection, attempt coverage, failure boundaries, and custody using existing managed receipts | [Managed test review](test-domain-model-and-execution/managed-test-review.md) |

**Foundations assessed during authoring** (read-only, at `50827eb9f`; each still holds at
`12f57dc4d`, with the conversion's effect noted):

- *The seed registry can express a second stage* (RC11 permits building it behind the
  controlled converter). A recipe type wrapping another already
  exists, and the builder receives its own directory. The builder runs outside any test, so it
  cannot use a test's monkeypatch; the controlled converter a PDF seed needs must be named by
  recipe data. The conversion made the controlled converters certify through production but
  left each a function installed by `monkeypatch`, so TDM-08 still depends on TDM-09.
- *The capture workspace is part of release custody.* Production binds the capture directory
  and asset root into the release's custody artifact and later uses that directory as the
  spool workspace. A shared writable workspace would be unsafe. TDM-08 exposes a sealed-capture
  route only for consumers that need the published result. Consumers that can capture or
  transform use a writable binding. Check eligibility at the fixture boundary before relying on
  shared custody. A capture may attempt per-request directory creation before it finds a
  published build, so a downstream filesystem error is too late to classify the consumer.
- *The stream protocol cannot be split after conversion.* Production writes and acknowledges
  its preparation entry before converting, because recovery identifies pages from it. The
  production seam therefore takes the request and a producer, not a finished result. The
  emitter the conversion added, `StreamingPdfResult.certified_reply`, takes a finished result;
  it is the seam's last step, and TDM-09 builds the rest in front of it.
- *The demand executor has a public constructor that computes what tests copy.* It touches
  native state in eight ways, which reduce to one collaborator with three surfaces.
- *pytest and xdist supply what grouping needs,* with two limits that shape the design:
  fixtures requested at run time are invisible to the collected closure, and marks on fixtures
  are an error in pytest 9. The resolved definitions distinguish local overrides and parent
  requests. TDM-15 confines this version-sensitive access to one adapter.
- *Managed receipts support a composed review.* Coverage, failures, and inspection already
  own the selected identities, observed outcomes, and custody. TDM-19 composes their typed reads
  and uses incremental events for managed evidence, including when an attempt is interrupted.

**Credible changes the target should absorb**, each traced in the owning companion: a modeled
field is added; a data operation is added; a production mechanism retires; a cache key gains a
determinant; the PDF worker boundary is replaced; kernel identity becomes finer than one
digest; validity families and guard membership move from code lists into declarations; the
query cache becomes content-keyed or shared across processes.

**Two readiness premises of the review's §4.8 that need a route of their own.** *Analytical SQL
becomes DuckDB relations (step 6).* The converted relational modules (the rich evaluator, the
companion export, the PDF derived analysis and artifact identity) already existed at the
authoring baseline and are unchanged since. The tests of them read for the revision, a sample,
author their expected rows by hand or compute them by a different and simpler method; none takes
them from the relation. TDM-05 therefore confirms this at entry over the tests not yet read and
replaces expected rows only where a test is found to compute them by running the relation.
*Release admission as one production operation
([DA-033](../design_review/audit/execution-fit.md#da-033)).* Production does not offer it, so
the test helper `admit_kernel` restates the order persist, admit, bind. TDM-03 makes that helper
the single test-side owner of the order, so a future production operation is adopted in one
place; the observation is [production context](#handovers).

<a id="shared-contracts"></a>

## Shared contracts

Each contract has one owner. Companions use these names and do not redefine them.

| Contract | Meaning | Owner |
|---|---|---|
| The model-binding rule | For each value a test uses, its role decides its source. An *expectation* is authored by hand, computed by a different and simpler method, or taken from a real independent system. A *correspondence* claim is tested by changing the declaration inside the test and expecting the realization to follow. Everything else is *scenario construction* and comes from the model's owner. A name used to select a subject stays literal; a set whose correctness is the claim is authored by hand and includes a member the declaration lacks | TDM-02; durable home is the test-assessment companion |
| Recipe | The content of a prepared scenario: inputs, declarations, captured sources, and the content of any controlled converter. No filesystem path or other per-consumer fact | TDM-07 |
| Binding | Where a recipe's preparation executes: its workspace and asset root. Supplied by the builder. Per worker when it is the seed's own directory; per consumer otherwise | TDM-07 |
| Preparation lifetime | A preparation may be reused for as long as the implementation that built it is fixed: the head across sessions under its key; seeds and prepared kernels within one worker process; anything bound to one consumer for that test | TDM-06, TDM-07 |
| Controlled boundary | The one place a test replaces an external computation. Production's protocol, encoding, identity and refusals still run; the double's output carries the identity of its input; one support owner; one contract control against the real boundary | TDM-09 to TDM-12 |
| Production seam | A production function or collaborator that owns a protocol tests would otherwise restate: the PDF stream function, the executor's native-I/O collaborator, the public host profile comparison | TDM-09, TDM-10, TDM-11 |
| Perturbation table | For one reuse or skip mechanism: how the decision is observed, a hit control, distinguishing determinant changes with literal outcomes, and a completeness case where the mechanism declares its determinants as data | TDM-13 |
| Preparation declaration | Native database use follows the native root; worker affinity is derived from the fixture definitions applicable to the item and reconciled with explicit groups | TDM-15 |
| Capture eligibility | A published-capture clone carries read access to a reserved sealed workspace; a consumer that can produce new capture or transform claims uses its own writable binding | TDM-08 |
| Review authority | The original attempt supplies the required selection; incremental receipts and existing managed reports supply observations, scope and custody | TDM-19 |
| Subject from its owner | A test obtains production SQL by importing its generator or naming the installed function, never by reading a file or cutting text | TDM-16 |

## Package queue

The table owns execution state. Row order is one useful route; the "Needs" column is what
binds. A package is not automatically one worker's assignment.

| Package | Delivers | Needs | Findings | State |
|---|---|---|---|---|
| <a id="tdm-00"></a>TDM-00 | Re-read changed code, affected consumers and relevant failure receipts; superseding ADRs for RC07, RC08, RC10 and RC11 with their owning design sections; RC09 recorded | — (the conversion is complete) | RC07–RC11, I01 | Implemented. RC07, RC08, RC10 and RC11 in ADR-0133/0134; RC09 recorded in the rule-change table. |
| <a id="tdm-01"></a>TDM-01 | Evidence restored at the baseline repair sites and newly confirmed impacted sites; collection and actual setup accounted for separately | TDM-00 | DTA-037 (dangling request), DTA-047 (two stale readers), I01 | Setup and test-body repairs implemented. Composition and public structural acquisition are blocked on production contracts. |
| TDM-02 | The model-binding rule in the test-assessment companion, version 1.3 | — | §3 | Implemented. Test assessment 1.3 published. |
| TDM-03 | Scenarios bound to production acquisition and the release's model; one PDF recipe composer, which still takes the directory it takes today; one recipe-extension helper; `admit_kernel` as the single test-side owner of the persist, admit and bind order | TDM-02 | DTA-042 | Implemented. Scoped model, pack and admission controls passed. |
| TDM-04 | Identity vector records carry every authored input, so neither consumer supplies a constant and the native consumer keeps the authored number spelling (`1.2500`); a request-identity vector against the generated `data.ddo_identity` | TDM-02 | DTA-033 | Implemented. Python and installed native identity controls passed. |
| TDM-05 | Generated-program tests assert meaning, including two spelling assertions the conversion added; circular expectations corrected; the DuckDB relational tests confirmed to author their expected rows, with replacement only where one is found not to | TDM-02 | F07, DTA-044 (two sites), DTA-033 (search selection site) | Implemented. Representative generated and installed semantic controls passed; source-search evidence below. |
| TDM-06 | Head key over the production migration chain and actual construction inputs, with observed effective role policy; frozen replay and failed-key repair; redundant policy comparison and dead `--principals` mode removed | TDM-00 | DTA-038/039, RC07, I02 | Implemented. Key, policy replay and stale-head replacement controls passed. |
| TDM-07 | Recipe and binding split: TDM-03's one composer changes to take content and a binding separately, and recipes become location-free; binding-aware bounded memo; per-consumer recipes never sealed | TDM-00; TDM-03 for the one composer | DTA-040, RC08 | Implemented. Direct writable acquisition and worker binding memo integrated. |
| TDM-08 | Piloted sealed-capture and writable routes; eligible consumers moved to completed-capture clones under the workspace reservation | TDM-07; TDM-09; TDM-01 for the three repaired factory and seed-directory consumers | F06, RC11, I03 | Sealed and writable capture verified. Consumer evidence includes production blocks and separately recorded provider attempts. |
| TDM-09 | Seam 1 completed in front of the conversion's `certified_reply`: one production owner of the sequence from preparation to reply, and a request-taking `PdfWorker.stream`; one controlled converter owner whose content is recipe data; every hand-written preparation entry and copy of request assembly removed; contract control | TDM-00 | DTA-041 | Production and controlled seams implemented. Generated successor registered; native composition acceptance is blocked. |
| TDM-10 | Public executor construction; real and controlled packet custody and settlement comparisons; reservation pinned by literals | The production seam needs nothing; the test migration needs TDM-07's memoized kernel recipe | DTA-043; DTA-034 (claim double); DTA-009 (`controlled_executor`); I03 | Public executor and typed native I/O implemented. Controlled cases and real prepared-batch path passed. |
| TDM-11 | Profile determinant and completeness cases, real-peer reach and cleanup, test-only startup matcher retirement | — | DTA-045, I05 | Implemented. Pure compatibility matrix and real-peer refusal controls passed. |
| TDM-12 | Remaining substitutes wire-checked and owned by support modules; identity-bearing encoder fake; test modules no longer imported from another test directory | TDM-10 for the population-close double only | DTA-034, DTA-046, DTA-009 (each with TDM-10) | Implemented. Wire, paging and encoder controls passed. |
| TDM-13 | The perturbation-table contract and safety cases for every reuse and skip mechanism, built on the cases the conversion added for lowered release facts and not repeating them; one cache-scope fixture | TDM-06 for the key's table; TDM-11 for the check of form of the host profile's table, which TDM-11 writes to this contract | DTA-044, DTA-038 (evidence) | Implemented safety controls; see scoped evidence and production-gated precision cases below. |
| TDM-14 | Refusal contract applied to the newer sites, and to the conversion's new tests that pin only SQLSTATE or only a message; new tests that already pin both inline after a positive control meet the contract and are left as they are | — | DTA-001 | Implemented. Scoped installed, CLI and stale-trust controls passed. |
| TDM-15 | Preparation declarations resolved per item; native-root `db` mark; retired lists, dead fixtures and unimported modules | TDM-01 for the shared conftest edits | DTA-037, RC09, I04 | Implemented. Fixture resolution, collection and worker affinity controls passed. |
| TDM-16 | The ten remaining path readers of production SQL moved to the subject's owner; every check that does not claim a bare database, including sixteen conversion test files, moved off a database per case | TDM-00; TDM-01 for the two broken readers | DTA-047, RC10 | Implemented. Installed, rollback and bare-database allocations verified in scoped cohorts. |
| TDM-17 | Ordinary-lane host test without the real GPU lock | — | DTA-048 | Implemented. Ordinary-lane private-path lock and wait controls passed. |
| <a id="tdm-19"></a>TDM-19 | [Read-only review of a managed selection and its attempts](test-domain-model-and-execution/managed-test-review.md) | Existing managed receipts and TDM-00 baseline read | I06, I07 | Implemented. Managed review, retries, paging and CLI controls passed. |
| <a id="tdm-18"></a>TDM-18 | Integrated qualification, findings returned to the test audit, and handoff | All other scheduled packages, including TDM-19 | I01 | Open. Reconcile final-source coverage when functional dependencies clear. |

Every package needs TDM-00's re-read of its sites; the "Needs" column lists only further
capabilities.

**Why this order.** TDM-00 comes first because validation of the conversion may still move the
revision baseline a little, and because three packages depend on its ADRs. TDM-01 follows at once:
a test that cannot set up gives no evidence for the claim behind it, and that is worse than
any inefficiency. TDM-02 has no prerequisite and shapes how every later package writes its own
acceptance, so it should land early. After that there are five largely independent lines:

- TDM-03, TDM-07, TDM-08 (scenario composition, then location-free recipes, then the new seed
  stage), with TDM-09 joining before TDM-08 because the seed builder needs the controlled
  converter as data. TDM-09 no longer restores setup for any group of tests, since the conversion
  certified the converter copies. Its priority now rests on two things: it is TDM-08's
  prerequisite, and it removes the hand-written preparation entry, which is not a valid report
  and would be refused the first time a controlled path resumes a spool. TDM-03 before TDM-07 is a real dependency: TDM-03 puts PDF recipe composition in
  one place, still taking a directory, and TDM-07 then changes that one composer instead of two
  functions and their call patterns;
- TDM-09, TDM-10, TDM-11, TDM-12 (the boundaries);
- TDM-06 (the head key), which should land before interpreting reuse evidence;
- TDM-15, TDM-16, TDM-17 (declarations, SQL subjects, the GPU test), with TDM-15 after the
  shared conftest repair;
- TDM-19 (managed review), which can use existing receipts in parallel with harness changes
  and must reach acceptance before TDM-18.

TDM-13 can begin as soon as the mechanism each table covers is observable, which for most is
today; only the key's table waits for TDM-06. TDM-14 has no prerequisite: the nine sites in the
PDF integration module no longer wait for TDM-09, because their converter now certifies and, by
reading, their setup holds. Two packages share a mechanism with
a neighbour, and the split is fixed here: TDM-11 writes the host profile's cases and TDM-13
only checks their form; TDM-05 writes the set-wise validity reference cases and the two
lowering refusal tests, and TDM-13 checks the distinguishing lowering inputs and their
declared completeness.

**TDM-09 and the conversion.** The conversion retired the fixture-only occurrence writer and
moved all nine converter doubles onto production certification (`1d22c41cb`, `8a5c074f0`). TDM-09
owns what that left on the consumer side: the two certifying test helpers, which copy request
assembly and place a preparation entry by hand, and the nine doubles, which move to the one
owner as content values.

**Shared editing surfaces.** Independent packages still meet in a few files:
`tests/semantic/current_pdf_source_support.py` (TDM-03, TDM-07, TDM-08, TDM-09),
`tests/conftest.py` and root `conftest.py` (TDM-01 first, then TDM-15),
`scripts/native_test_support.py` (TDM-06, TDM-16),
`tests/semantic/data_operation_kernel_support.py` (TDM-03, TDM-07, TDM-10),
`tests/semantic/native_program_support.py` (TDM-04, TDM-16). Sequence edits to
these or give them one owner at a time.

### TDM-00 — entry

*Purpose.* Establish what is true when execution begins, and put the accepted rule changes
into their authorities before dependent work starts.

*Baseline re-read.* Start with changes from `12f57dc4d` through the entry commit. Trace changes
in fixture, helper, and generated-program owners to impacted test consumers even when the tests
did not change. Reconcile retained failure receipts against their source and execution context.
Classify gaps at entry by collection or import, fixture resolution, setup or call, refusal
expectation, and product behavior. Record affected package state and route in-series prerequisites
before dependent packages start. A package already delivered by a later commit needs a source
reference and acceptance evidence for its actual scope.

The N13 chain beginning `be66da57a0a44cf3b6aa420cb7e77c37` reports 146 observed identities of
148 selected across mixed source and context. Use the two unresolved refusals from
`5008e8bb6809433ab620a80dea585857` as authoring and review cases. Compare the invalid attachment
with the valid entry and the predecessor and current guards before judging whether the asserted
denial is stale. DDO owns product disposition and its qualifying union. [I01 evidence](../plan_improvement_reviews/test-domain-model-and-execution_2026-11-18.md#I01)

*Root script tests.* The revision read the deployment key's tests
(`tests/scripts/test_native_deployment_key.py`, whose real-tree case at `:137–159` names the
frozen chain and must change with TDM-06) and the test of in-process principals
(`tests/scripts/test_private_cohort.py:600–612`). TDM-00 reads the other in-scope files under
root `tests/scripts/` (the tests of the lifecycle support, the seed registry and the
qualification plugin) and records, for TDM-06, TDM-07, TDM-13 and TDM-15, what each asserts
today and which chain, recipe or list it names.

*Decision records.* One ADR supersedes ADR-0101 and carries RC07 and RC10. One supersedes
ADR-0102 and carries RC08 and RC11: a recipe is content only, and a seed may be built behind a
controlled boundary double when the double's content is part of the recipe, and so of the seed's
identity, and production's own protocol and checks still run, while seeds built under any other
implementation override stay forbidden. Each restates the decision it replaces with the change, names what
is preserved (verification as the authority on safety; process-scoped seeds; isolation by
claim), and amends its design section in the same commit. The
[preparation-identity companion](test-domain-model-and-execution/preparation-identity.md#what-the-superseding-records-must-say)
and the
[declarations companion](test-domain-model-and-execution/declarations-retirement-and-execution.md#what-the-rule-change-records-must-say)
state what each must say. RC09 needs no ADR; the record above and TDM-15's change are its
route.

*Acceptance.* `uv run ci adr lint` passes; the superseded ADRs name their successors; each
successor record contains every statement those two companion sections require, checked item by
item by a reader who did not write the record; each companion's state table reflects source at
the entry commit; any package closed as already delivered cites the commit.

### TDM-01 — evidence restored

*Purpose.* Some tests cannot set up or pass by reading, and the claims behind them have no
evidence until they do. Those that a later package rewrites wholesale are left to that
package. The rest are repaired here, in the smallest way that restores a real assertion.

*Known at the revision baseline* (by reading at `12f57dc4d`, not run):

| Site | Defect | Repair here or elsewhere |
|---|---|---|
| `tests/semantic/test_source_routing.py:9–12` | Requests the fixture `domain_default_case`, defined nowhere | Here: rewrite onto a current scenario, or delete with a transfer note naming the surviving control |
| `tests/semantic/test_native_sql_body.py:202–217` | Reads `execution_projection_check.sql`, deleted in `708c119a6` | Here: take the program from its generator, as the sibling test already does |
| `tests/semantic/test_native_closure.py:268–290` | New since authoring. Replaces the file read of `pdf_record_context.sql`, deleted in `5341e93dd`; production now builds that program from a generator, so the replacement never fires and the assertion on the changed text fails | Here: make the change through the generator's input, or delete with a transfer note |
| `tests/semantic/test_witnessed_publication_native.py:29–31`, `tests/semantic/test_condition_publication_native.py:54–56` | Call the PDF source factory, which returns a context manager, without `with` | Here |
| `tests/semantic/test_source_discovery_native.py:52` (cases without views) | Writes into a frozen seed directory. Unchanged since authoring; not re-verified in depth | Here, after confirming the failure |
| `tests/test_native_refusals.py` | Four tests request a `db` fixture that the package tests, the root `tests/` tree, the root scripts and the root conftest do not define | Here |
| `tests/semantic/test_current_pdf_source_inputs.py:58–68` | Calls a converter double without options it reads | TDM-09, which rewrites it; TDM-01 leaves it alone |

*Delivered by the conversion.* Three rows of the authoring table are gone. The two tests whose
slice anchors were absent were rewritten onto generators (`d422c48e7`, `a727a9878`). The seven
converter copies that production refused now certify through production (`1d22c41cb`,
`8a5c074f0`), so their consumers set up by reading. The native identity cases received the field
their input lacked (`d422c48e7`) and can pass; what TDM-04 still corrects is not a setup defect.

*What bounds this package.* An exhaustive comparison of requested fixture names with defined
fixtures, over 930 files of the package tests, the root `tests/` tree, the root scripts and the
root conftest, found exactly two undefined names: `domain_default_case` and `db`, both in the
table. The same scan found no unresolved import of the package or of a test module and no
missing path named in a test. A test whose body calls a production signature that has since
changed cannot be found by reading; the collection and targeted runs below are how such a test
would show.

Run `uv run ci test collect` for package identities and import or collection errors. A bounded
pytest `--setup-plan` inspection may help diagnose static dependency resolution if the targeted
hooks are safe in that mode. Run the affected fixtures and test bodies on the managed route to
exercise real setup, including dynamic requests and context-managed entry and exit. Record the
outcome at each boundary separately.

*Acceptance.* Account for missing fixture names, stale generated-program references, and
context-managed fixtures through targeted execution or a named remaining obligation with its
package owner. Check a meaningful counterexample where a repair could otherwise lose the claim.
For a deleted test, identify the surviving control or the retired behavior. Collection confirms
identities and collection behavior; setup and body success require their own receipts.

<a id="implementation-evidence"></a>

## Implementation and scoped evidence · 2026-11-18

The receipt IDs point to the commands' managed results. These observations establish the
named selections and observed contexts. TDM-18 owns their final-source applicability and
the required lane union.

| Package | Observation |
|---|---|
| 00, 02 | The changed conversion sources, affected tests and retained N13 receipts informed the entry decisions. ADR-0133/0134 and test assessment 1.3 passed `uv run ci adr lint` (`57f9113a721840cfa2cf78e242fe48a2`) and `uv run ci docs check` (`15c0c93147dc4e53b23b10646b6e2987`). |
| 01, 03 | Removed the unreachable source-routing fixture test. Current native source capture and governed discovery own the surviving custody and routing claims. Repaired the stale generated SQL readers, context-manager entry, direct temporary storage, authored read/write transaction boundaries and retained source fixture. Grading and rich-domain preparation passed a scoped selection (`e2fcf5e565fc43d8b579a4f3a9af8ad9`). Public construction and cross-release setup use the admitted release model. The native formal bounded read and the deliberately incomplete construction/replay cases passed (`b76eef68213c42c8afe03f38b6fab4bc`, `cafc10b98cb4440a8064ddb5fc50f613`). |
| 04 | Authored contextual product and request vectors passed 51 Python controls (`f3414c988f044012a582791c989def86`) and nine installed native controls (`7b10d0b6b27d4380a3b9ffef768fbfd4`). The native consumer preserves decimal spelling. |
| 05 | Generated grammar and semantic controls passed (`e6ffd880b71e4ad5864d78bd2ae7e514`), as did installed lock, cast and configuration cases (`684d65316d524444bb6e6e1075f19d22`, `9401dfc9971749b0a9614a815c725433`, `6e5205edf8e042dc81d013c4d11c4487`) and independent closure cases (`a434e6e534cc44758b7e0335eea5bb2a`). Source-search cursor checks with authored scope and independently perturbed candidates passed in the same retained mixed attempt as all three discovery cases (`adb098f282cf47f1b9977fd342a87a21`). |
| 06, 13 | Key and policy controls passed (`80e45f44d30c4d0baf09880e8bf462a2`), with actual clones (`ccec880737b14cdfa572b0b585fec3e9`) and stale-key replacement (`0776e7884f8d48bfa21c24fc60a022ad`). Equal-size content, relocated checkout, interpreter, observed facts and role identity controls passed (`976fbbba198c4e2f96731d3af1840f20`). Oracle receipt and row evidence, lowering determinant changes, completion seals, and lowered stale-read and repair paths passed (`e4fff3c720e442eab8fd47521c742130`, `1c235faca12f4ce993eded4eff6dd792`, `b4bcf85f3c1b44e2abb1dfa62f76dab1`, `a64fd500265445cabe3d6495c5517c18`). Production-gated precision cases retain the companion's triggers. |
| 07, 08 | The registry's direct acquisition uses one writable clone with no retained seed. Worker preparation uses a 16-entry content/binding memo. Independent bindings, invalidation and eviction while a caller retains resources passed (`47bc03d12a2d47f1afcd3af6c27e42f8`). Native pilot receipt `ccc148b0ccc14a268ddd17db16f1c70f` includes passing sealed export, distinct clones sharing a single conversion, graph read and writable materialization profiles. A bound PDF recipe refused sealing, and one different content row produced a new capture identity and selected text in `aba5da0bd9d04767a3ab90a6fa76d75d`. The migrated table, structural, operation-event and primary-source fixtures share a published capture with a converter-entry guard. The clone requires both fulfilled source operations and their stored receipts. The native export passed with independently derived document identity (`004af6ed90524f18a5b466e03fbd3666`). |
| 09 | The single typed PDF stream protocol and its controls passed (`4b38f8fa68b34ef3b9b68feb78069e09`). The source change required a frozen native successor for fresh admission. Typed preview, rollback candidate check and registration passed (`66969ed415bf449392d7e4d0d6f811ac`, `6dd9a2773df04c9094694d616bd29772`, `9dac312f26c44c43aa93327fbfeeee1b`). The test head uses `semantic_tdm_pdf_stream_protocol`. Existing stage and development deployment remain at their recorded DDO head. |
| 10 | Public scheduling and host controls passed (`c3815a1615344db39bc46c0e4a855e79`). External packet and uncertain-publication controls passed (`8a3adade2557487db3459580ba74400c`), including ordered replies and missing-lease refusal (`5f7982b310ad4224b2224ec0865ae01f`). The collaborator returns whole admission records to preserve release, runtime and implementation checks. The prepared-batch native path passed (`118f4565f6524642950d0e2add0b3667`), including detached verification after comparing the exact exported operation fields against the captured archive. |
| 11, 17 | Pure frozen profile, actual peer refusal, cleanup and private lock controls passed (`31a26e1f2d624a03b439db1b454df785`). |
| 12 | Wire and bounded projection controls passed (`46cdce4cf2404e558d6e8acd8ba203be`, `ad982167a4a3474280cdf65acf4a9e37`). Distinct surviving encoder responses after a drop passed (`c38ab2714518452d949e18ebcf9157a7`, `71869b9ec9144bed827281d9cd7c5186`). A one-off in-memory rotation of returned member positions under `uv run python` failed at the independent `alpha`, `gamma` output assertion. The production module was loaded normally for the managed rerun. |
| 14 | Fan-in, authored relabel and source CLI tests passed (`d32409eecea2473da757571df51ddad9`). The external cancellation and population guards passed in the mixed original (`a62c3753e7014ac08a6c592706fa412b`). The formerly unreached authored stale-trust case passed (`ab102a30cbb843e595ea666381bc2204`). The installed certification matrix reached its seven valid boundaries and discriminated exact stale-holder, role and missing-oracle refusals (`976fbbba198c4e2f96731d3af1840f20`). |
| 15 | Item-resolved fixture metadata and xdist affinity passed (`fff8a27fcf734a4eb855953211649a1d`, `31bac1dbc9d147ddb047a4d7f0855659`, `b74d59e4e7e64d8f9dab81ea1a601c81`). `uv run ci test collect` passed for 8,824 selected identities (`9a077ce482bb4da18faefcd8718b25fb`). The receipt establishes collection only. The two affinity controls that failed in the 169-node execution selection passed its exact retry (`3686bc7c85e4442cac2d0dd4817db0af`). |
| 16 | Installed, reusable rollback and narrow bare-database cohorts passed (`83905f5eb7b84ef891639c65be560ee2`, `c37a616b63144c488f0477a243db247b`, `0cf30e4d8d3c4fd3b7e0def8183e7e58`, `460925a1d94643248f1870e34499b965`). The remaining bare databases cover empty, forward migration or era-specific claims. |
| 19 | Managed review passed the existing classifier/CLI suite (`d37d367332814fcbb18d9472501e2c07`) and six final controls (`514502f63bee4f2e9b9384abfb2a170c`). The public command and generated reference are available. |

**Open native composition boundary.** The migrated analytical tests register a real selected
source cut through the declared discovery path. The composition control still stops at
`text.compose_view/source-native` awaiting inputs in `132a35c400974ee7b2e82cd6966bedf5`.
Its [document-level operation](../../python/corpus-structure/src/corpus_structure/methods/characterization.py)
omits the discovery dependency, so completed discovery cannot advance its readiness watermark. Its optional analytical roles also lack an explicit acquisition
path for products retained by earlier demands. The production declaration and acquisition owners
need to settle those contracts. The native composition test retains its independent expected
result. This is an open prerequisite to verifying that consumer.

**Open rich admission boundary.** The four-original record-publication stage now builds in one
controlled capture sequence per seed. Those synthetic originals share stream parts, so the test
builder admits one capture at a time before testing record publication. The authored publication
case completed `rich.consolidate` and left `rich.admit` awaiting inputs
(`24d7b2fa63a84dbd8120bd0893a41869`). The latter requires the consolidation input but declares
no dependency on that producer, so the readiness watermark cannot observe its completion.
The current declaration and readiness owners are
[`methods/rich_knowledge.py`](../../python/corpus-structure/src/corpus_structure/methods/rich_knowledge.py)
and [`semantic/data_operation_projections.py`](../../python/corpus-structure/src/corpus_structure/semantic/data_operation_projections.py).
The test keeps its independent publication assertions and reports the two fates.

**PM2 provider evidence.** The selected source-demand and table cases initially reported
`blocked` because `CORPUS_PM2_NATIVE_TEST_ASSETS` was unset
(`e3f3845e51b049fcb57a4db32384d999`). The provider selection was repeated with the
documented local `build/models/pm2` asset root (`1a2dfbc649724fffb723c8c4d8ab1c06`).
The two-region full-native demand reached execution and exceeded the harness's 15-minute
limit. At the deadline its main thread was validating an interpreted product and computing
the product's semantic identity in `construction_products.py` and
`data_operation_identity.py`. That retained stack identifies where execution was interrupted.
Cleanup settled. Two cases remained `not_run`. Both passed when selected separately
(`149a296834074df48871df92edc498d8`): the empty-source control and the actual literal native model answer.

**Other native consumer boundaries.** The seven-module capture selection recorded 23 passes
and two failures (`e3ceec079cab49c785f7b742c2897f6f`). The render fixture supplies explicit capacity for its temporary unmanaged engine and points
to the paragraph that owns the authored region. The exact render control passed
(`557f4f737a70405ab92327754b82ee76`).
The visual observation completed capture, render, claim and packet read. Its controlled
submission stopped when the captured output schema reached the external result port's
closed local-reference check. The [external packet compiler](../../python/corpus-structure/src/corpus_structure/semantic/external_execution_native.py)
uses the installed nominal body schema as the result contract. That schema and packet
validation must agree on dialect and local references before the visual consumer can finish.

The witnessed admission and condition cases reached protected issue in
`b99fa9ca2efe4d228596172c575ee6d9`. The fixture opens that issuer result with evaluator
purpose. Its public result still requires ordinary reader authority. The installed
[`read_demand_result`](../../python/corpus-structure/src/corpus_structure/semantic/demand_result_native.py)
authorizes all declared operation roles before explicit output acquisition. The witness
retry reached that public boundary and returned SQLSTATE `42501`
(`cd73d47f019646cc98a1650efc3a1328`). Its public output must be readable while evaluator
inputs retain their existing custody.

The structural representative using the shared capture passed (`ce02672c2aa148068b1734f68f54cd5f`).
The controlled PM2 result then passed against the restored native descriptor
(`3ff3f89fa4b1433395e65ed728a5e3eb`). That case validates the real selected mapping, resolves
and discovers the resulting publication, and asserts the exact stale-read `P0001` refusal.
The event fixture declares its prepared capsule and nominal CPU reply. Its native frame still
reaches `inspect._empty` while constructing the strict adapter for a production kernel with
no return type (`e019dc222e394f50afd1da7e8bc37aa4`). Adding the production reply annotations
changed the global native source digest and caused fresh admission to refuse the installed
descriptor (`04e277393dea4554a20c520fbade633a`). The production edit was reverted to keep
the registered head usable. The production event reply type and its frozen native descriptor
must be updated together.

**Scoped execution.** The actual Docling spool-resume provider selection passed
(`5fc23c205c7f406599ba81df4c1c1a26`). Native PDF worker retirement, complete export,
sealed capture and writable materialization passed in the mixed native attempt
`24d7b2fa63a84dbd8120bd0893a41869`. `uv run ci check` passed
(`3b9a6705cafb44a4a3232d36e3fb0d20`). The
[test audit refresh](../design_review/test-audit/README.md#tdm-refresh-2026-11-18)
covers the changed test architecture and retains the historical audit baseline.
`ci test review 10735b0bdc8e434b8a17c67d572baa37 3686bc7c85e4442cac2d0dd4817db0af`
accounts for all 169 identities in that selection across the original and exact retry.
It retains the failed original and both attempts' settled custody.

### TDM-18 — closing

After all functional scope is implemented, run `uv run ci test` for the applicable lanes and
`uv run ci check`. Reconcile the required union by test identity, source/context, and receipt.
Use the implemented TDM-19 review where a chain includes retries or interruptions. Preserve
the separate standing of collection, setup, functional observations, and result custody. Keep
out-of-scope failures visible in the closure account with their current owners. Update the test
audit through its own refresh route and run the handoff skill. DDO plan updates follow this
series.

**Current qualification.** Repository checks passed. The full `uv run ci test` ordinary and
Rust union and the exclusive fault lane are `not_run` at this boundary while the native
consumers above lack production prerequisites. Retain their failed results and the narrower passing evidence.
The final qualification requires the exact ordinary, applicable provider and fault selections
on the accepted source and its required native context. The two-region provider timeout remains
open even though the narrower real provider case passed.

## Finding disposition

This table is the single scheduled-disposition owner for the findings it lists. Diagnoses stay
in the [test audit](../design_review/test-audit/README.md) and corrective reasoning in the
review; neither is copied here. "Closure evidence" is what must be observed, not a claim that
it has been.

| Finding | Package | Closure evidence | State |
|---|---|---|---|
| [DTA-041](../design_review/test-audit/support-structure.md#dta-041) converter copies | TDM-09 | Partly corrected by the conversion: every controlled reply is now emitted and certified by production. Remaining to observe: no test writes a preparation entry or assembles a stream request by hand; controlled content is a recipe value; the contract control passes; the consumers of the nine doubles pass in a run | Implemented; PDF protocol and capture controls passed. Native composition remains open. |
| [DTA-037](../design_review/test-audit/retirement-transfer.md#dta-037) fixture lists | TDM-01 (dangling request), TDM-15 | Every native item carries `db`; resolved overrides and parent requests give the correct group under xdist; global lists are retired | Fixture declarations and collection controls passed. |
| [DTA-033](../design_review/test-audit/evidence-and-discrimination.md#dta-033) vector inputs | TDM-04 (TDM-05 for the search selection site) | The native cases take every input from the vector record and pass, including the case whose number spelling the consumer loses today; a framing change made on both sides fails a vector; the search selection test no longer recomputes its expected digest with the production projection. The conversion supplied the missing field as a constant in the consumer, which makes the cases passable and leaves the finding open | Authored identity vectors and independent native cursor controls passed. |
| [DTA-047](../design_review/test-audit/execution-and-qualification.md#dta-047) SQL readers, per-case databases | TDM-01 (stale readers), TDM-16 | Partly corrected by the conversion: ten readers now import their generator and the absent anchors are gone. Remaining to observe: none of the ten remaining modules reads production SQL by path or cuts text from it; no check that does not claim a bare database creates a database per case, which 61 files do at the revision baseline against 45 at authoring | The scheduled SQL subjects and isolation routes were migrated. Scoped native results passed. |
| [DTA-045](../design_review/test-audit/evidence-and-discrimination.md#dta-045) invented refusal | TDM-11 | Removing a field from the comparison fails a test; the real peer reaches the refusal | The profile comparator and actual peer refusal passed. |
| [DTA-044](../design_review/test-audit/evidence-and-discrimination.md#dta-044) reuse tested only where correct | TDM-13 (TDM-05 for two circular sites) | Each listed mechanism has a case where reuse must not happen, asserted by literal outcome | Scoped safety evidence passed. Production-gated precision controls retain their triggers. |
| [DTA-042](../design_review/test-audit/support-structure.md#dta-042) composition restated | TDM-03 | No support module types the statistics bundle; the grading scenario's model is its release's | Scenarios use the release model and maintained pack factories. Scoped checks passed. |
| [DTA-038](../design_review/test-audit/execution-and-qualification.md#dta-038) head key coverage | TDM-06, evidence in TDM-13 | Executed revision bodies, unpinned content and effective role-policy changes move the key; a content-neutral touch preserves it, and a wrong pinned artifact is refused | Production-chain key and observed-role perturbations passed. |
| [DTA-039](../design_review/test-audit/execution-and-qualification.md#dta-039) replay and repeated verification | TDM-06 | One policy comparison per clone. The repeated role-script process is already gone: the conversion made principals an in-process read (`781350991`) | Redundant policy comparison retired; observed replay and repair passed. Incremental head remains deferred. |
| [DTA-040](../design_review/test-audit/execution-and-qualification.md#dta-040) location in recipe identity | TDM-07 | No seed sealed for a per-consumer recipe; equal content gives equal recipe identity in any directory | Content recipes, independent bindings and memo eviction passed. |
| F06 capture per consumer | TDM-08 | Two eligible clones share a reserved published capture without another converter call; the sealed route explicitly refuses write use, and the writable pilot has its own binding | Pilot passed. See the scoped capture and consumer evidence. |
| [DTA-043](../design_review/test-audit/support-structure.md#dta-043) executor from private fields | TDM-10 | Public construction preserves reservation, packet custody and settlement behavior across real and controlled cases | Public executor, controlled packet settlement and prepared-batch controls passed. |
| [DTA-046](../design_review/test-audit/evidence-and-discrimination.md#dta-046) encoder realignment | TDM-12 | An off-by-one realignment after a drop fails a controlled test | Independent surviving identities and drop realignment passed. |
| [DTA-048](../design_review/test-audit/execution-and-qualification.md#dta-048) real GPU lock | TDM-17 | No ordinary-lane test opens the host lock | Private path lock and actual wait controls passed. |
| [DTA-034](../design_review/test-audit/support-structure.md#dta-034) remaining substitutes | TDM-12; TDM-10 for the claim double | Each substitute passes the wire validator on both sides | Scoped wire validation, ordered replies and missing-lease refusal passed. |
| [DTA-001](../design_review/test-audit/evidence-and-discrimination.md#dta-001) newer refusal sites | TDM-14 | A valid control reaches the boundary; the invalid case asserts literal SQLSTATE and message or constraint and the expected effect or rollback | Scheduled installed refusal and positive reach controls passed in scoped selections. |
| [DTA-009](../design_review/test-audit/support-structure.md#dta-009) test modules as support | TDM-12 (`_page`, `_complete_ready`, cross-directory imports of test modules); TDM-10 (`controlled_executor`) | No test imports `_page`, `_complete_ready` or `controlled_executor` from a test module; no test module imports a name from a test module in another test directory; no relative import in a test directory that is not a package | Obsolete support imports and executor constructor retired. Scoped checks passed. |
| F07 renderer spelling | TDM-05 | A renderer change that keeps meaning passes; one that changes meaning fails | Structural and installed semantic controls passed. |
| [DTA-026](../design_review/test-audit/execution-and-qualification.md#dta-026) private interpreter state | — | — | Deferred; trigger: an interpreter change |
| [DTA-036](../design_review/test-audit/retirement-transfer.md#dta-036) DDO-12 union | — | — | Not owned here; stays with its existing owner |

A package finishing does not close a finding with other contributors: DTA-009, DTA-033,
DTA-034, DTA-037, DTA-038, DTA-044 and DTA-047 each need all of their packages.

<a id="improvement-disposition"></a>

## Plan-improvement disposition

This table routes the November 18 recommendations to their packages. The existing findings
table retains closure state for the underlying audit and design findings.

| Review | Package owner | Disposition |
|---|---|---|
| [I01](../plan_improvement_reviews/test-domain-model-and-execution_2026-11-18.md#I01) | TDM-00/01/14/18 | Entry review and targeted repairs completed in scope; integrated qualification remains open. |
| [I02](../plan_improvement_reviews/test-domain-model-and-execution_2026-11-18.md#I02) | TDM-06/13 | Implemented production-chain and observed-policy identity. Scoped clone and perturbation evidence passed. |
| [I03](../plan_improvement_reviews/test-domain-model-and-execution_2026-11-18.md#I03) | TDM-03/07–10/12 | Implemented PDF and executor seams and both capture routes. See the open native consumer evidence. |
| [I04](../plan_improvement_reviews/test-domain-model-and-execution_2026-11-18.md#I04) | TDM-15 | Implemented per-item fixture resolution under RC09. Scoped xdist controls passed. |
| [I05](../plan_improvement_reviews/test-domain-model-and-execution_2026-11-18.md#I05) | TDM-02/04/05/11/13/14/16/17 | Implemented independent semantic and refusal controls and retired the superseded test machinery. See production-gated precision cases. |
| [I06](../plan_improvement_reviews/test-domain-model-and-execution_2026-11-18.md#I06) | [TDM-19](#tdm-19) | Managed review implemented and tested. Timing, live progress and completion are conditional. |
| [I07](../plan_improvement_reviews/test-domain-model-and-execution_2026-11-18.md#I07) | [TDM-19](#tdm-19) | Incremental reporting remains the evidence source. External JSON exchange is conditional. |

<a id="candidates-and-deferrals"></a>

## Candidates, deferrals, rejected options and open premises

**Candidates** (not scheduled; each names what would settle it):

- *The deployment key computed once on the xdist controller and sent to workers*
  (`pytest_configure_node`, `workerinput`). Saves repeated walking and hashing per worker.
  Settled by reading stored setup phases after TDM-06; adopt only if key computation is a
  visible share of focused-run startup.
- *Hypothesis state machines for cache lifecycle order* (warm, perturb, restore, query). Adds
  value only for in-process caches whose order of operations matters. Settled when TDM-13
  writes the query-cache table: adopt if plain parametrized cases leave an order-dependent
  defect uncovered, or if the query cache becomes shared across processes (DA-075), which makes
  invalidation order a real determinant.

- *Managed review phase timing, live progress and completion.* Consider phase timing after
  TDM-19 if reviewing retained phase and scheduling data still requires repeated extraction.
  Consider progress when `ci results watch` leaves a specific diagnostic gap, and completion
  when repeatedly entering result IDs warrants bounded metadata lookup. The
  [managed-review companion](test-domain-model-and-execution/managed-test-review.md#reporting-foundation-and-conditional-extensions)
  owns their design limits. TDM-18 can close without these extensions.

**Deferred with a trigger:**

- *Incremental head built from its predecessor* (DTA-039). Valid only when every key component
  except appended revisions is unchanged. Trigger: stored results show head builds recurring on
  appended-only changes. The conversion appended seven revisions, which is the pattern the
  trigger names, but no stored result was read for the revision.
- *Precision cases of perturbation tables* (reuse must survive an irrelevant change). Trigger:
  the production owner decides the grain of kernel and implementation identity (DA-068,
  DA-069).
- *The undeclared-member case for validity families.* It fails today by design of the current
  code. Trigger: the production change that corrects DA-070.
- *A seedable admitted-release stage for PDF consumers that capture.* Trigger: production moves
  the capture workspace out of release custody.
- *A completed-journey seed for the declared-record scenario* (operator, 2026-11-17). It has the
  same shape as F06 (thirteen consuming functions on one recipe) but was not in the review. Trigger: TDM-08
  is delivered and its stage holds; then extend by the same rules.
- *Grouping commit-class consumers of a seed by recipe.* Trigger: a stored full run shows seed
  builds per worker dominating setup (review §14).
- *External pytest JSON exchange.* Trigger: a named consumer needs a field the retained
  receipt cannot provide economically. Compare an allowlisted settled export with an opt-in
  plugin supplement under the TDM-19 reporting contract. Managed reporting and exact retry
  continue to use incremental evidence.

**Rejected, with the reason, so they are not proposed again:**

- *Seeds reused across sessions.* A cross-session key must fingerprint the product code a
  builder runs, which is nearly the whole package; it would miss on almost every edit, and
  anything narrower would admit stale seeds.
- *Model-driven or change-based test selection (including pytest-testmon).* A test's identity depends on Python modules, generators,
  migrations and test support that the model's change-impact comparison does not see; an
  incomplete dependency key skips affected tests silently.
- *Test keys built with production identity functions.* Test infrastructure must keep working
  while the code under test is broken.
- *A library-owned database lifecycle (pytest-postgresql).* It has no policy replay, leases,
  authenticated drops or key-addressed reuse across sessions.
- *Fixing the copies and lists in place.* The same drift already recurred once for each
  (DTA-029 to DTA-041, DTA-030 to DTA-037).
- *Every PDF test through the real worker child.* Strongest fidelity, but a process per
  scenario; kept for the one contract control.
- *Default duplicate pytest JSON session snapshot.* The isolated reporting probe showed
  incomplete standing under interruption and distributed execution. It would retain additional
  output without taking over an existing reporting responsibility.

**Open premises** (each is the first step of the package it constrains):

| Premise | Settled by | Constrains |
|---|---|---|
| Publication's logical digest is independent of the build, so the contract control can compare it across routes | Reading the digest's inputs | TDM-09 |
| Today's authored claim replies pass wire validation | Running them through the validator | TDM-10 |
| The consumers of the nine certified converter doubles set up, which is established only by reading | The first targeted run of those modules | TDM-09, TDM-14 |
| A completed-capture consumer can use the sealed route under the existing reservation | Trace consumers and pilot a post-capture reader and writable consumer before broad migration | TDM-08 |
| Resolved fixture definitions and mark ordering represent local overrides under the pinned pytest and xdist versions | Inspect the adapter contract, then check root/package parity and two-worker placement | TDM-15 |
| Existing review reads can be composed without rereading or reclassifying the same receipt unnecessarily | Trace typed projections, descriptor custody and shared limits before fixing the CLI implementation | TDM-19 |

All 87 deployed artifacts at the revision baseline were digest-pinned. TDM-06 also specifies
content identity for any unpinned construction input found at entry or added later.

<a id="handovers"></a>

## Production context owned outside this series

These observations explain the boundaries of the test packages. The coordinator records new
external causes here when they affect interpretation of TDM evidence. This table creates no
handoff obligation and calls for no edits to other plans at TDM-18. Any DDO plan updates take
place after this series completes.

| Observation | Owner | What the tests do meanwhile |
|---|---|---|
| The capture workspace and asset root are part of release custody, so release identity depends on a filesystem location | Production (broad audit, identity broader than its premise) | Recipe and binding split (TDM-07); post-capture seed only (TDM-08) |
| `LOWERING_FILES` is a hand-kept list whose completeness nothing establishes. The conversion grew it to about seventy entries (seventeen generator modules added, five SQL files removed) and no test refers to it | Production (DA-068, DA-069 family) | A perturbation case per listed input (TDM-13) |
| Kernel digest grain and implementation identity; validity-family membership, support closures and read identities; pack composition and guard and grant membership in the model; query-cache keying | Production (DA-068, DA-069, DA-070, DA-071, DA-073, DA-074, DA-075, DA-076) | Seams of §4.8, carried in the owning companions: safety cases now and gated precision cases (TDM-13); reference cases independent of the production encoding (TDM-05); scenarios bound to acquisition and hand-authored posture expectations (TDM-03) |
| Release admission is not one production operation, so the test helper `admit_kernel` restates the order persist, admit, bind | Production (DA-033) | `admit_kernel` is the single test-side owner of that order (TDM-03); when production offers the operation, the helper calls it and the restated order goes |
| Superseded production machinery other than code kept alive only by tests | Production (the remaining DA-080 items) | None. Code whose last caller is a test retires inside the package that owns that test. One such item is known and is scope, not handover: the `--principals` mode of `scripts/pg_semantic_roles.sh`, which has no caller and goes in TDM-06. The conversion already deleted the fixture-only occurrence writer, and `function_bodies` has four production callers and stays |
| Six files in `src/corpus_structure/semantic/sql/` have no loader in `src/`: `exclusions.sql`, `fact.sql`, `selection.sql`, `validation.sql`, `source_record_graph.sql` and `data_operation_identity.sql` | Production (the conversion's owner, ADR-0131; DA-080 family) | None, beyond TDM-16 moving the two tests that read `source_record_graph.sql` and `data_operation_identity.sql` by path |
| Production exposes a decoder for packaged data-operation inputs. Its package owner does not replace previously captured artifacts | Production (data-operation composition) | The recipe-extension helper holds the `"data-operations/"` prefix in one place (TDM-03) |
| The search selection digest has no pure production function (none found in `src/corpus_structure/semantic/pdf_source_search.py` at `12f57dc4d`) | Production (PDF source search) | Perturbation cases on the cursor's selection; no literal vector for that digest (TDM-05) |
| The certification-requirement program reports `producer-certified` before it knows that a prior receipt qualifies | Production (PDF certification) | The oracle-skip table asserts the receipt id and the oracle rows, not the basis alone (TDM-13) |
| The selected-query cache does not report whether it answered | Production (serving) | A counting spy on the whole-result read (TDM-13) |
| The host-wide GPU lock path is a literal inside `_locked_gpu_slot` | Production (ingest capacity) | The waiting control replaces the module-level `Path` name of `corpus_structure.ingest.pdf_capacity` for its duration (TDM-17) |
| Each SQL retirement of the conversion should move its own path readers in the same commit | The conversion's owner (ADR-0131) | TDM-01 repairs the two tests found broken by a retirement at the revision baseline; TDM-16 moves the remaining path readers |
| `tests/native_private_bootstrap.py:30–106` still provisions a private server with hand-written role, template and extension SQL, so the conversion's step 5 reached the shell scripts and not the private-host test path | The conversion's owner (ADR-0131) | None; the key observes what that provisioning creates as server facts (TDM-06) |
| The deployment key hashes the wrong migration tree, unchanged by the conversion | Test audit (refines DTA-038) | Corrected by TDM-06 |
| No full run has passed since 2026-11-10 | Qualification owner | TDM-18 produces the first current profile |

<a id="revision-2026-11-18"></a>

## Revision · 2026-11-18

Re-baselined from `50827eb9f` to `12f57dc4d` after the ADR-0131 conversion completed, while its
validation was running. Facts are by reading, from the
[boundaries](../design_review/evidence/2026-11-17_test-plan-authoring/rebaseline-boundaries.md) and
[identity](../design_review/evidence/2026-11-17_test-plan-authoring/rebaseline-identity.md)
re-baseline reports. No package was added or deleted and every state stays `Not started`.

| Package | Delivered by the conversion | Removed from scope |
|---|---|---|
| TDM-01 | Absent anchors rewritten; converter copies certified; native identity input completed | Three table rows |
| TDM-04 | `subject_definition` added to the native input (`d422c48e7`) | The claim that the native cases cannot pass |
| TDM-06 | Principals read in-process (`781350991`), with a test | The doubled role-script process |
| TDM-09 | Production emitter `certified_reply`; all nine doubles certified; occurrence writer deleted (`1d22c41cb`, `8a5c074f0`) | Restoring setup, replacing five-field replies, deleting the writer |
| TDM-13 | Part of the safety cases for lowered release facts (`test_data_operation_compiler_native.py`) | Those cases only |
| TDM-14 | Converter certification, so the integration sites set up | The dependency on TDM-09 |
| TDM-16 | Ten path readers moved to generator imports; `routine_declaration` helper | Those readers' sources; any deletion of `function_bodies` |

The other nine packages received nothing; their citations and counts were corrected.

*What got larger.* Test files that create a database per case rose from 45 to 61, all sixteen
additions being conversion tests (TDM-16). The deployment key still hashes the wrong tree, which
grew from 22 to 29 revisions (TDM-06). TDM-01 gained one test broken by a retirement, TDM-05 two
spelling assertions, and TDM-14 the conversion tests that pin only SQLSTATE or only a message.

*Not refreshed.* The test audit's own statuses for DTA-041, DTA-047, DTA-033 and DTA-038 were not
refreshed by this revision; the audit's own route refreshes them in [TDM-18](#tdm-18).

## Completion

The series is complete when every package's acceptance holds on final source, the disposition
table's closure evidence has been observed for every scheduled finding, the broad
`uv run ci test` and `uv run ci check` routes have run on final source with the required union
accounted for, both superseding ADRs are accepted with their design sections amended, the
test-assessment companion is at 1.3, `uv run ci docs check` passes, and TDM-19 preserves
attempt and custody standing in its human and typed views. Conditional extensions remain
triggered work. Record implementation and qualification separately and describe expected
benefits qualitatively.
