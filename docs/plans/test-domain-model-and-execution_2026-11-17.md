# Test domain model and execution

**Status:** Proposed; not started. **Created:** 2026-11-17.
This coordinator owns the series' combined target, shared contracts, package queue, rule-change
record and the scheduled disposition of every finding it lists. Companion plans own the detailed
designs and package descriptions. Architecture pages and accepted ADRs remain the authority;
writing this plan authorizes no implementation.

## Outcome and source baseline

Give the test system one rule for what a test may take from the product's domain model and what
it must keep independent, and make the test system's own concepts explicit enough that
preparation is reused exactly, doubles replace only what is external, reuse mechanisms have
evidence that can fail, and test machinery retires with what it serves. The tests that source
shows cannot set up or pass get their evidence back first. The result should also keep the
production changes that are now likely (a model that generates its SQL, finer implementation
identities, facts moving from code lists into declarations) local when they reach the tests.

**Source.** The [design review of the test domain model and execution](../design_review/reviews/design_review_test-domain-model-and-execution_2026-11-17.md)
(publication `caa841b01`, read at `main` `1afa63f88`, judgment Revise) and its
[dispositions](../design_review/reviews/test-domain-model-and-execution/dispositions.md). The
review consumed the [test audit](../design_review/test-audit/README.md) and the
[joint model-and-execution page](../design_review/audit/model-and-execution.md) at `aca50eeea`,
and superseded the 2026-11-13 test-system review. Section references below (§4.2 and so on) are
to the principal review unless a companion is named.

**Authoring baseline.** `main` `50827eb9f`, 2026-11-17, 37 commits after the review's baseline.
Another session was converting maintained PostgreSQL SQL to generated SQL
([ADR-0131](../adr/0131-model-owned-postgresql-programs.md)) throughout authoring. Line
citations are as read in a frozen export of that commit and will have moved by execution. The
investigation reports written during authoring are kept in the evidence folder
`docs/design_review/evidence/2026-11-17_test-plan-authoring/`: the
[current-state map](../design_review/evidence/2026-11-17_test-plan-authoring/state.md), the
[PDF source consumer map](../design_review/evidence/2026-11-17_test-plan-authoring/pdf-source-consumers.md),
the [seam advice](../design_review/evidence/2026-11-17_test-plan-authoring/seams.md), the
[library capability notes](../design_review/evidence/2026-11-17_test-plan-authoring/library-capabilities.md)
and the earlier [test map](../design_review/evidence/2026-11-17_test-plan-authoring/test-map.md).

**Execution premise (operator, 2026-11-17).** This series executes after the ADR-0131
conversion is complete. Packages are written against `50827eb9f` and say what they do when the
conversion has already done part of their work; [TDM-00](#tdm-00) re-reads the baseline at
entry and records what remains. Because the series runs after the conversion, the review's §13
column "coordinate with the conversion" is replaced by that re-read: the converter copies
(DTA-041) are not corrected together with the owner of the conversion's step 3, readers orphaned
by each SQL retirement are moved by TDM-16 at entry, and provisioning is checked by TDM-06's
first step. The obligation that each SQL retirement move its own readers stays with the
conversion's owner and is recorded as a [handover](#handovers).

<a id="glossary"></a>

**Terms used across the series.** The *conversion* is the ADR-0131 work, and its numbered steps
are cited as the review cites them: step 3 moves controlled PDF fixtures through the certified
producer, step 4 converts the kernel SQL, step 5 routes host bootstrap and test provisioning
through shared administration builders, and step 6 turns analytical SQL into DuckDB relations.
The *head* is the sealed, keyed and verified database that the migration chain builds and from
which test databases are cloned ([ADR-0101](../adr/0101-verified-test-deployments.md)). A *seed*
is a sealed, worker-local database that holds one prepared scenario on top of the head
([ADR-0102](../adr/0102-reusable-native-scenario-seeds.md)). A *commit clone* is a fresh database
cloned from a seed or the head for one consumer that commits. A *rollback family* is a group of
tests that share one clone, each inside a transaction that is rolled back. The *read class* is a
read-only, rolled-back transaction on a worker's session clone of the head. *DDO* is the
identifier of the plan series that owns the data-operation work (its packages are DDO-nn, and
`ddo_` prefixes the native data-operation functions). *PM2* appears only in the names of existing
support modules and production error types, such as `current_pm2_native_support.py` and
`Pm2WorkerError`, and is used here only to name them.

**Evidence status.** Every design statement here is **Proposed**. Source facts are
**Interface-checked by source inspection, 2026-11-17**. Where the series says a test cannot set
up or pass, that is read from source and was not run. Durations are quoted only from the
review, which read them from stored results. No package has a speed target and no measured
speedup is a completion criterion.

**Scope.** Package tests under `python/corpus-structure/tests/`, every `conftest.py`, the root
scripts the tests use (`scripts/native_test_support.py`, `native_deployment_key.py`,
`native_deployment_build.py`, `native_scenario_seeds.py`, `qualification_plugin.py`, and the
`--principals` mode of `scripts/pg_semantic_roles.sh`, whose only caller is test infrastructure),
the tests under root `tests/scripts/` for the scripts this series changes (the deployment key,
the lifecycle support, the seed registry and the qualification plugin, including
`tests/scripts/test_native_deployment_key.py` and `tests/scripts/test_native_scenario_seeds.py`),
the test-assessment companion of the design standard, two superseding ADRs, and three bounded
production changes that give test doubles a production owner to delegate to
([the seams](#shared-contracts)). Production code kept alive only by tests retires with those
tests, inside the package that owns them
([retirement rule 4](test-domain-model-and-execution/declarations-retirement-and-execution.md#retirement-rules)).
Out of scope: any other production remedy, including every correction of the production findings
DA-068 to DA-081; edits to existing plans; the DDO-12 qualification union, which stays with its
owner; and the rest of the repository-root `tests/` tree. The review did not read the root
`tests/` tree, so TDM-00 re-reads the in-scope files under `tests/scripts/` at entry before any
package relies on a statement about them.

<a id="rule-changes"></a>

## Rule changes confirmed by the operator

The operator accepted all four rule impacts of the review on 2026-11-17, and one further rule
change that authoring revealed (RC11). Accepted ADRs are
immutable, so each ADR change is a superseding record written in [TDM-00](#tdm-00), with the
owning design section amended in the same commit.

| Item | Decision | What changes | Route | Needed by |
|---|---|---|---|---|
| RC07 | Accepted 2026-11-17 | The deployment key covers what the build runs: the migration chain production deploys, located by production's own constant; the native bodies its revisions execute and their module-level imports; artifacts by content instead of size and modification time. Steps executed during a build are reached from the construction entry, whose closure is keyed; provisioning applied to the server beforehand enters as observed server facts (role names, attributes and memberships), not as source | ADR superseding [ADR-0101](../adr/0101-verified-test-deployments.md) | TDM-06 |
| RC08 | Accepted 2026-11-17 | A seed recipe is content only. A workspace or asset location is a binding the builder supplies. A recipe that needs a per-consumer binding is built in the consumer's clone and never sealed | ADR superseding [ADR-0102](../adr/0102-reusable-native-scenario-seeds.md) | TDM-07, TDM-08 |
| RC09 | Accepted 2026-11-17 | The `db` mark derives from the native root fixture and worker groups are declared where a fixture is defined. The two hand-kept name lists are removed | Recorded here; the earlier series' TS-12 mechanism is replaced. No ADR | TDM-15 |
| RC10 | Accepted 2026-11-17 | Infrastructure clones may serve rolled-back connections for SQL expression checks that install only temporary objects | Same ADR that supersedes ADR-0101 | TDM-16 |
| RC11 | Accepted 2026-11-17 (revealed by authoring) | ADR-0102 says nothing built under an implementation override is seedable. A seed may now be built behind a controlled boundary double when the double's content is part of the recipe, and so of the seed's identity, and production's own protocol and checks still run. Seeds built under any other implementation override stay forbidden | Same ADR that supersedes ADR-0102 | TDM-08 |

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
it keys runs `target_alembic` (`scripts/native_test_support.py:917`;
`src/corpus_structure/semantic/migrations.py:14`). An edit to a deployed revision does not move
the key; only the per-process verification of revision and catalog stands between such an edit
and a stale head.

**Machinery is declared away from what it names.** Two lists of fixture names drifted from the
fixtures that exist; seven hand copies of the PDF converter double stopped producing what
production requires; mechanisms that reuse work or skip a check are tested only where reusing
is correct.

The target adds no framework. It adds a small number of named concepts and removes the copies
and lists they replace.

| Area | Target in one sentence | Companion |
|---|---|---|
| Model binding | Scenario construction comes from the model's owner; expectations stay independently authored; a claim that a realization follows its declaration is tested by changing the declaration in the test | [Model binding and independence](test-domain-model-and-execution/model-binding-and-independence.md) |
| Preparation identity | A preparation is keyed by its content and lives as long as the implementation that built it is fixed; where it runs is a separate binding | [Preparation identity](test-domain-model-and-execution/preparation-identity.md) |
| Controlled boundaries | A double replaces one external computation, production's protocol and refusals still run, and each boundary has one owner that delegates to a production seam | [Controlled boundaries and seams](test-domain-model-and-execution/controlled-boundaries-and-seams.md) |
| Reuse evidence | Every mechanism that reuses work or skips a check has a table of cases in which it must not | [Reuse and refusal evidence](test-domain-model-and-execution/reuse-and-refusal-evidence.md) |
| Declarations and retirement | What a fixture needs is declared where the fixture is defined, and a test obtains its subject from the subject's owner, so a retirement breaks its dependents visibly | [Declarations, retirement and suite execution](test-domain-model-and-execution/declarations-retirement-and-execution.md) |

**Foundations assessed during authoring** (read-only, at `50827eb9f`):

- *The seed registry can express a second stage* (RC11 permits building it behind the
  controlled converter). A recipe type wrapping another already
  exists, and the builder receives its own directory. The builder runs outside any test, so it
  cannot use a test's monkeypatch; the controlled converter a PDF seed needs must be named by
  recipe data. This is why TDM-08 depends on TDM-09.
- *The capture workspace is part of release custody.* Production binds the capture directory
  and asset root into the release's custody artifact and later uses that directory as the
  spool workspace. A shared writable workspace would be unsafe. A completed capture whose
  workspace lies inside a frozen seed directory is safe for consumers that run neither capture
  nor a PDF transform. A capture first creates its per-request directory under the workspace and
  only then returns an already published build from the database without further filesystem
  access; on a frozen workspace that creation either finds the directory present and writes
  nothing, or raises `PermissionError`. No other reader of the workspace after publication was
  found. This bounds TDM-08.
- *The stream protocol cannot be split after conversion.* Production writes and acknowledges
  its preparation entry before converting, because recovery identifies pages from it. The
  production seam therefore takes the request and a producer, not a finished result.
- *The demand executor has a public constructor that computes what tests copy.* It touches
  native state in eight ways, which reduce to one collaborator with three surfaces.
- *pytest and xdist supply what grouping needs,* with two limits that shape the design:
  fixtures requested at run time are invisible to the collected closure, and marks on fixtures
  are an error in pytest 9.

**Credible changes the target should absorb**, each traced in the owning companion: a modeled
field is added; a data operation is added; a production mechanism retires; a cache key gains a
determinant; the PDF worker boundary is replaced; kernel identity becomes finer than one
digest; validity families and guard membership move from code lists into declarations; the
query cache becomes content-keyed or shared across processes.

**Two readiness premises of the review's §4.8 that need a route of their own.** *Analytical SQL
becomes DuckDB relations (step 6).* The series executes after the conversion, so the converted
relational modules exist at entry. TDM-05 reads their tests (the rich evaluator, the companion
export and the PDF derived analysis) and, wherever expected rows are computed by running the
relation or copied from its output, replaces them with rows authored for small inputs.
*Release admission as one production operation
([DA-033](../design_review/audit/execution-fit.md#da-033)).* Production does not offer it, so
the test helper `admit_kernel` restates the order persist, admit, bind. TDM-03 makes that helper
the single test-side owner of the order, so a future production operation is adopted in one
place; the observation itself is a [handover](#handovers).

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
| Perturbation table | For one reuse or skip mechanism: how the decision is observed, a hit control, one case per determinant the test author judges should matter with its literal outcome, and a completeness case where the mechanism declares its determinants as data | TDM-13 |
| Preparation declaration | Which fixtures need the database and which share a worker, stated at the fixture's definition or derived from the fixture graph | TDM-15 |
| Subject from its owner | A test obtains production SQL by importing its generator or naming the installed function, never by reading a file or cutting text | TDM-16 |

## Package queue

The table owns execution state. Row order is one useful route; the "Needs" column is what
binds. A package is not automatically one worker's assignment.

| Package | Delivers | Needs | Findings | State |
|---|---|---|---|---|
| <a id="tdm-00"></a>TDM-00 | Entry: baseline re-read after the conversion; ADRs superseding ADR-0101 (RC07, RC10) and ADR-0102 (RC08, RC11) with their design sections; RC09 recorded | Conversion complete | RC07–RC11 | Not started |
| <a id="tdm-01"></a>TDM-01 | Evidence restored for tests that cannot set up or pass at entry and that no later package rewrites | TDM-00 | DTA-037 (dangling request), DTA-047 (stale reader) | Not started |
| TDM-02 | The model-binding rule in the test-assessment companion, version 1.3 | — | §3 | Not started |
| TDM-03 | Scenarios bound to production acquisition and the release's model; one PDF recipe composer, which still takes the directory it takes today; one recipe-extension helper; `admit_kernel` as the single test-side owner of the persist, admit and bind order | TDM-02 | DTA-042 | Not started |
| TDM-04 | Identity vectors carry their authored inputs; a request-identity vector | TDM-02 | DTA-033 | Not started |
| TDM-05 | Generated-program tests assert meaning; circular expectations corrected; authored expected rows for the converted relational modules | TDM-02 | F07, DTA-044 (two sites), DTA-033 (search selection site) | Not started |
| TDM-06 | Head key over what the build runs, starting with the migration tree it actually deploys; repeated role-script and policy work removed | TDM-00 | DTA-038, DTA-039, RC07 | Not started |
| TDM-07 | Recipe and binding split: TDM-03's one composer changes to take content and a binding separately, and recipes become location-free; binding-aware bounded memo; per-consumer recipes never sealed | TDM-00; TDM-03 for the one composer | DTA-040, RC08 | Not started |
| TDM-08 | Completed-capture seed stage; eligible consumers moved | TDM-07; TDM-09; TDM-01 for the three repaired factory and seed-directory consumers | F06, RC11 | Not started |
| TDM-09 | Seam 1 and one controlled converter owner; all copies and the fixture-only occurrence writer removed; contract control | TDM-00 | DTA-041 | Not started |
| TDM-10 | Seam 2; executor tests through the public constructor; reservation pinned once by literals | The production seam needs nothing; the test migration needs TDM-07's memoized kernel recipe | DTA-043; DTA-034 (claim double); DTA-009 (`controlled_executor`) | Not started |
| TDM-11 | Seam 3; the profile's per-field cases and completeness case; real-peer reach control; invented refusal removed | — | DTA-045 | Not started |
| TDM-12 | Remaining substitutes wire-checked and owned by support modules; identity-bearing encoder fake; test modules no longer imported from another test directory | TDM-10 for the population-close double only | DTA-034, DTA-046, DTA-009 (each with TDM-10) | Not started |
| TDM-13 | The perturbation-table contract and safety cases for every reuse and skip mechanism; one cache-scope fixture | TDM-06 for the key's table; TDM-11 for the check of form of the host profile's table, which TDM-11 writes to this contract | DTA-044, DTA-038 (evidence) | Not started |
| TDM-14 | Refusal contract applied to the newer sites | TDM-09 for the nine sites in the PDF integration module, which cannot set up before it | DTA-001 | Not started |
| TDM-15 | Preparation declarations at the fixture; `db` mark from the native root; lists, dead fixtures and unimported modules removed | TDM-01 for the shared conftest edits | DTA-037, RC09 | Not started |
| TDM-16 | Production SQL obtained from its owner; expression checks without a database per case | TDM-00 | DTA-047, RC10 | Not started |
| TDM-17 | Ordinary-lane host test without the real GPU lock | — | DTA-048 | Not started |
| <a id="tdm-18"></a>TDM-18 | Closing: integrated qualification, findings returned to the audit, handoff | All | — | Not started |

Every package needs TDM-00's re-read of its sites; the "Needs" column lists only further
capabilities.

**Why this order.** TDM-00 comes first because everything else is written against a baseline
that will have moved, and because three packages depend on its ADRs. TDM-01 follows at once:
a test that cannot set up gives no evidence for the claim behind it, and that is worse than
any inefficiency. TDM-02 has no prerequisite and shapes how every later package writes its own
acceptance, so it should land early. After that there are four largely independent lines:

- TDM-03, TDM-07, TDM-08 (scenario composition, then location-free recipes, then the new seed
  stage), with TDM-09 joining before TDM-08 because the seed builder needs the controlled
  converter. TDM-03 before TDM-07 is a real dependency: TDM-03 puts PDF recipe composition in
  one place, still taking a directory, and TDM-07 then changes that one composer instead of two
  functions and their call patterns;
- TDM-09, TDM-10, TDM-11, TDM-12 (the boundaries);
- TDM-06 (the head key), which touches only the key and lifecycle scripts;
- TDM-15, TDM-16, TDM-17 (declarations, SQL subjects, the GPU test).

TDM-13 and TDM-14 can begin as soon as the mechanism each table covers is observable, which
for most is today; only the key's table waits for TDM-06. Two packages share a mechanism with
a neighbour, and the split is fixed here: TDM-11 writes the host profile's cases and TDM-13
only checks their form; TDM-05 writes the set-wise validity reference cases and the two
lowering refusal tests, and TDM-13 writes the case per declared lowering input.

**TDM-09 and the conversion.** The conversion schedules retirement of the fixture-only
occurrence writer, whose only callers are the uncertified converter copies. Whichever lands
first, TDM-09 owns the consumer side: every copy moves to the one owner and the writer is gone
when TDM-09 closes.

**Shared editing surfaces.** Independent packages still meet in a few files:
`tests/semantic/current_pdf_source_support.py` (TDM-03, TDM-07, TDM-08, TDM-09),
`tests/conftest.py` and root `conftest.py` (TDM-01 first, then TDM-15),
`scripts/native_test_support.py` (TDM-06, TDM-16),
`tests/semantic/data_operation_kernel_support.py` (TDM-03, TDM-07, TDM-10). Sequence edits to
these or give them one owner at a time.

### TDM-00 — entry

*Purpose.* Establish what is true when execution begins, and put the accepted rule changes
into their authorities before dependent work starts.

*Baseline re-read.* For each package, re-read the sites its companion cites and record, in the
companion's state table, what the conversion already delivered and what remains. Authoring
expects these to have moved: the seven uncertified converter copies and the fixture-only
occurrence writer (the conversion's step 3 moves controlled fixtures through the certified
producer); the remaining readers of `semantic/sql/data_operations.sql` (its step 4 converts the
kernels they read); test provisioning (its step 5 routes it through shared administration
builders, which changes what the head key must cover). A package whose whole subject the
conversion already delivered is closed with a reference to the delivering commit, not
re-implemented.

*Root script tests.* The review did not read the root `tests/` tree. TDM-00 reads the in-scope
files under root `tests/scripts/` (the tests of the deployment key, the lifecycle support, the
seed registry and the qualification plugin) and records, for TDM-06, TDM-07, TDM-13 and TDM-15,
what each asserts today and which chain, recipe or list it names.

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
item by a reader who did not write the record; each companion's state table reflects source at the entry commit; any package closed as already
delivered cites the commit.

### TDM-01 — evidence restored

*Purpose.* Some tests cannot set up or pass by reading, and the claims behind them have no
evidence until they do. Those that a later package rewrites wholesale are left to that
package. The rest are repaired here, in the smallest way that restores a real assertion.

*Known at authoring* (re-confirm in TDM-00; by reading, not run):

| Site | Defect | Repair here or elsewhere |
|---|---|---|
| `tests/semantic/test_source_routing.py:9–12` | Requests the fixture `domain_default_case`, defined nowhere | Here: rewrite onto a current scenario, or delete with a transfer note naming the surviving control |
| `tests/semantic/test_native_sql_body.py:200–216` | Reads `execution_projection_check.sql`, deleted in `708c119a6` | Here: take the program from its generator, as the sibling test already does |
| `tests/semantic/test_data_operation_trust_snapshot_sql.py:53`, `test_data_operation_selected_graph_sql.py:34` | Slice anchors absent from the file they read | Here if TDM-16 has not reached them |
| `tests/semantic/test_witnessed_publication_native.py`, `tests/semantic/test_condition_publication_native.py` | Call the PDF source factory without `with` | Here |
| `tests/semantic/test_source_discovery_native.py` (cases without views) | Writes into a frozen seed directory | Here, after confirming the failure |
| `tests/semantic/test_current_pdf_source_inputs.py:58–68` | Calls the changed converter double without options it now reads | TDM-09, which rewrites it; TDM-01 leaves it alone |
| Seven uncertified converter copies and their consumers | Production refuses their reply | TDM-09 |
| Native identity vectors | Input lacks a field the expected literal has | TDM-04 |
| `tests/test_native_refusals.py` | Requests a `db` fixture that no package test module, root conftest or root script defines (the root `tests/` tree was not searched) | Here |

TDM-01 also runs the collection of the whole package (`uv run ci test` in collect-only form,
or the equivalent the `ci` skill names) and reads the errors: collection is the cheapest
complete inventory of tests that cannot set up for a structural reason, and it executes no
test body.

*Acceptance.* Each repaired test passes in a targeted run and still fails when its subject is
deliberately broken (state the mutation tried). Package collection reports no error, or each
remaining error is assigned in TDM-00's record to the package that rewrites the failing test.
Tests
deleted here have a transfer note naming the control that still covers the behaviour, or
stating that the behaviour was retired.

### TDM-18 — closing

After all functional scope is implemented: `uv run ci test` for the applicable lanes and
`uv run ci check`, with the required union accounted for by test identity and receipt. No full
run has passed since 2026-11-10, so this is the first current full-run profile; failures
outside this series' scope are recorded and routed to their owners, not absorbed. Then: update
the test audit so that each corrected finding's status reflects delivered source (an audit
refresh by its own skill, not an edit made from this plan's claims); record the
[handovers](#handovers) at their owners; run the handoff skill.

## Finding disposition

This table is the single scheduled-disposition owner for the findings it lists. Diagnoses stay
in the [test audit](../design_review/test-audit/README.md) and corrective reasoning in the
review; neither is copied here. "Closure evidence" is what must be observed, not a claim that
it has been.

| Finding | Package | Closure evidence | State |
|---|---|---|---|
| [DTA-041](../design_review/test-audit/support-structure.md#dta-041) converter copies | TDM-09 | No stream reply built by hand outside the owner; the contract control passes; former consumers pass setup | Scheduled |
| [DTA-037](../design_review/test-audit/retirement-transfer.md#dta-037) fixture lists | TDM-01 (dangling request), TDM-15 | No hand list of fixture names; every native item carries `db`; a deleted fixture leaves nothing behind | Scheduled |
| [DTA-033](../design_review/test-audit/evidence-and-discrimination.md#dta-033) vector inputs | TDM-04 (TDM-05 for the search selection site) | Native vector cases pass; a framing change made on both sides fails a vector; the search selection test no longer recomputes its expected digest with the production projection | Scheduled |
| [DTA-047](../design_review/test-audit/execution-and-qualification.md#dta-047) SQL readers, per-case databases | TDM-01 (stale readers), TDM-16 | No test reads production SQL by path or cuts text from it; expression checks create no database per case | Scheduled |
| [DTA-045](../design_review/test-audit/evidence-and-discrimination.md#dta-045) invented refusal | TDM-11 | Removing a field from the comparison fails a test; the real peer reaches the refusal | Scheduled |
| [DTA-044](../design_review/test-audit/evidence-and-discrimination.md#dta-044) reuse tested only where correct | TDM-13 (TDM-05 for two circular sites) | Each listed mechanism has a case where reuse must not happen, asserted by literal outcome | Scheduled; precision cases gated |
| [DTA-042](../design_review/test-audit/support-structure.md#dta-042) composition restated | TDM-03 | No support module types the statistics bundle; the grading scenario's model is its release's | Scheduled |
| [DTA-038](../design_review/test-audit/execution-and-qualification.md#dta-038) head key coverage | TDM-06, evidence in TDM-13 | The key moves when a deployed revision, a native body it executes, or a module in the construction closure changes, and when observed server or role facts change; it does not move when a file is touched without changing | Scheduled; restated against `target_alembic` |
| [DTA-039](../design_review/test-audit/execution-and-qualification.md#dta-039) replay and repeated verification | TDM-06 | One role-script result and one policy comparison per clone | Scheduled in part; incremental head deferred |
| [DTA-040](../design_review/test-audit/execution-and-qualification.md#dta-040) location in recipe identity | TDM-07 | No seed sealed for a per-consumer recipe; equal content gives equal recipe identity in any directory | Scheduled |
| F06 capture per consumer | TDM-08 | Eligible consumers clone the completed-capture stage; capture-claim consumers still build | Scheduled |
| [DTA-043](../design_review/test-audit/support-structure.md#dta-043) executor from private fields | TDM-10 | No `__new__` of the executor in tests; reservation read from the executor and pinned once | Scheduled |
| [DTA-046](../design_review/test-audit/evidence-and-discrimination.md#dta-046) encoder realignment | TDM-12 | An off-by-one realignment after a drop fails a controlled test | Scheduled |
| [DTA-048](../design_review/test-audit/execution-and-qualification.md#dta-048) real GPU lock | TDM-17 | No ordinary-lane test opens the host lock | Scheduled |
| [DTA-034](../design_review/test-audit/support-structure.md#dta-034) remaining substitutes | TDM-12; TDM-10 for the claim double | Each substitute passes the wire validator on both sides | Scheduled |
| [DTA-001](../design_review/test-audit/evidence-and-discrimination.md#dta-001) newer refusal sites | TDM-14 | Each listed site pins SQLSTATE plus message or constraint after a positive control | Scheduled |
| [DTA-009](../design_review/test-audit/support-structure.md#dta-009) test modules as support | TDM-12 (`_page`, `_complete_ready`, cross-directory imports of test modules); TDM-10 (`controlled_executor`) | No test imports `_page`, `_complete_ready` or `controlled_executor` from a test module; no test module imports a name from a test module in another test directory; no relative import in a test directory that is not a package | Scheduled; the remaining same-directory imports of private names move when a package touches the importing module (review §5.5) |
| F07 renderer spelling | TDM-05 | A renderer change that keeps meaning passes; one that changes meaning fails | Scheduled |
| [DTA-026](../design_review/test-audit/execution-and-qualification.md#dta-026) private interpreter state | — | — | Deferred; trigger: an interpreter change |
| [DTA-036](../design_review/test-audit/retirement-transfer.md#dta-036) DDO-12 union | — | — | Not owned here; stays with its existing owner |

A package finishing does not close a finding with other contributors: DTA-009, DTA-033,
DTA-034, DTA-037, DTA-038, DTA-044 and DTA-047 each need all of their packages.

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

**Deferred with a trigger:**

- *Incremental head built from its predecessor* (DTA-039). Valid only when every key component
  except appended revisions is unchanged. Trigger: after the conversion settles, stored results
  show head builds recurring on appended-only changes.
- *Precision cases of perturbation tables* (reuse must survive an irrelevant change). Trigger:
  the production owner decides the grain of kernel and implementation identity (DA-068,
  DA-069).
- *The undeclared-member case for validity families.* It fails today by design of the current
  code. Trigger: the production change that corrects DA-070.
- *A seedable admitted-release stage for PDF consumers that capture.* Trigger: production moves
  the capture workspace out of release custody.
- *A completed-journey seed for the declared-record scenario* (operator, 2026-11-17). It has the
  same shape as F06 (fourteen consumers on one recipe) but was not in the review. Trigger: TDM-08
  is delivered and its stage holds; then extend by the same rules.
- *Grouping commit-class consumers of a seed by recipe.* Trigger: a stored full run shows seed
  builds per worker dominating setup (review §14).

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

**Open premises** (each is the first step of the package it constrains):

| Premise | Settled by | Constrains |
|---|---|---|
| Publication's logical digest is independent of the build, so the contract control can compare it across routes | Reading the digest's inputs | TDM-09 |
| Today's authored claim replies pass wire validation | Running them through the validator | TDM-10 |
| Registering a new demand against a completed capture reuses it without a capture claim | Reading demand reuse; failure is loud if not | TDM-08 |
| A root-conftest hook that adds group marks needs `tryfirst` to run before xdist reads them | A two-worker collection | TDM-15 |
| Hashing artifacts no revision pins is cheap enough to do per key computation | Observation during TDM-06; fall back to size and time for those files only | TDM-06 |

<a id="handovers"></a>

## Handovers to other owners

These are production observations the review returned or the companions raised, and this series
does not act on them. This table is their one list: companions cite it and do not restate it.
TDM-18 records each at its owner; none blocks the series. A product finding that a package's
failing case reveals during execution is added here by the coordinator.

| Observation | Owner | What the tests do meanwhile |
|---|---|---|
| The capture workspace and asset root are part of release custody, so release identity depends on a filesystem location | Production (broad audit, identity broader than its premise) | Recipe and binding split (TDM-07); post-capture seed only (TDM-08) |
| `LOWERING_FILES` is a hand-kept list whose completeness nothing establishes | Production (DA-068, DA-069 family) | A perturbation case per listed input (TDM-13) |
| `admitted_startup_matches` has no production consumer | Production (pending or superseded machinery) | None |
| Kernel digest grain and implementation identity; validity-family membership, support closures and read identities; pack composition and guard and grant membership in the model; query-cache keying | Production (DA-068, DA-069, DA-070, DA-071, DA-073, DA-074, DA-075, DA-076) | Seams of §4.8, carried in the owning companions: safety cases now and gated precision cases (TDM-13); reference cases independent of the production encoding (TDM-05); scenarios bound to acquisition and hand-authored posture expectations (TDM-03) |
| Release admission is not one production operation, so the test helper `admit_kernel` restates the order persist, admit, bind | Production (DA-033) | `admit_kernel` is the single test-side owner of that order (TDM-03); when production offers the operation, the helper calls it and the restated order goes |
| Superseded production machinery other than code kept alive only by tests | Production (the remaining DA-080 items) | None. Code whose last caller is a test retires inside the package that owns that test: the fixture-only occurrence writer in TDM-09, `function_bodies` in TDM-16 if no production caller remains |
| Production has no public operation that reopens packaged data-operation inputs | Production (data-operation composition) | The recipe-extension helper holds the `"data-operations/"` prefix in one place (TDM-03) |
| The search selection digest has no pure production function, if TDM-05's first step confirms it | Production (PDF source search) | Perturbation cases on the cursor's selection; no literal vector for that digest (TDM-05) |
| The certification-requirement program reports `producer-certified` before it knows that a prior receipt qualifies | Production (PDF certification) | The oracle-skip table asserts the receipt id and the oracle rows, not the basis alone (TDM-13) |
| The selected-query cache does not report whether it answered | Production (serving) | A counting spy on the whole-result read (TDM-13) |
| The host-wide GPU lock path is a literal inside `_locked_gpu_slot` | Production (ingest capacity) | The waiting control replaces the module-level `Path` name of `corpus_structure.ingest.pdf_capacity` for its duration (TDM-17) |
| Each SQL retirement of the conversion should move its own path readers in the same commit | The conversion's owner (ADR-0131) | TDM-16 moves the readers found orphaned at entry |
| The deployment key hashed the wrong migration tree | Test audit (refines DTA-038) | Corrected by TDM-06 |
| No full run has passed since 2026-11-10 | Qualification owner | TDM-18 produces the first current profile |

## Completion

The series is complete when every package's acceptance holds on final source, the disposition
table's closure evidence has been observed for every scheduled finding, the broad
`uv run ci test` and `uv run ci check` routes have run on final source with the required union
accounted for, both superseding ADRs are accepted with their design sections amended, the
test-assessment companion is at 1.3 and `uv run ci docs check` passes, and the handovers are
recorded at their owners. Completing implementation, completing qualification and realizing a benefit are
separate statements; the series claims the first two and describes the third qualitatively.
