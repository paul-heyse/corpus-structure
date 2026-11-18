# Design review — test domain model and execution

**Design / target review · 2026-11-17 · principal reviewer: delegated `design-reviewer` (fresh
context; author of neither the audits, the tests nor the earlier reviews).** Supporting document:
[dispositions](test-domain-model-and-execution/dispositions.md), which holds the per-finding
disposition table and routes back here for every judgment.

This review **supersedes** the
[test system target design review of 2026-11-13](design_review_test-system-target-design_2026-11-13.md)
and its supporting document. Its findings F01–F05 and rule impacts RC01–RC04 keep their identities;
§11 says what carries and what no longer applies. New findings start at F06 and new rule impacts at
RC07 (RC05 and RC06 are identities the test-system plan already uses).

**Evidence labels.** Every remedy is **Proposed**. Source facts are **Interface-checked by source
inspection, 2026-11-17**, in a frozen export of `main` at
`1afa63f883f07873c8b4d3cccb9fc6622b558d50` unless a sentence attributes them to the audit or a
contributor. One analysis ran a pure function of the snapshot (the deployment key's own
`import_closure`, §4.2); it executed no test, database, build or provider. Durations are
**Measured** only as read from stored results in the
[cost map](../evidence/2026-11-17_joint-audit-refresh/README.md) (shared workstation, ordinary
development conditions). No speedup is claimed anywhere.

**Path convention.** `tests/…` and `src/…` are relative to `python/corpus-structure/`;
repository-root paths are written as root `conftest.py`, `scripts/…`, `docs/…`.

---

## 1. Scope, outcome and coverage

| Field | Value |
|---|---|
| Subject | Test code, test evidence and shared test infrastructure of `python/corpus-structure`: `tests/` (including conftest files and support modules), root `conftest.py`, root `scripts/native_test_support.py`, `native_deployment_key.py`, `native_deployment_build.py`, `native_scenario_seeds.py`, `qualification_plugin.py`, `test_receipts.py`, and `src/corpus_structure/cli/testing.py`. Production is read to understand contracts and seams; **no production remedy is selected** |
| Baseline | `1afa63f88` (frozen export). Another session was editing production and test code during the review; the working tree was not read for source facts |
| Audit consumed | Repository commit `aca50eeea`: the [test account](../test-audit/README.md) refreshed at `fbd3f2a98` with its [scoped delta at `1afa63f88`](../test-audit/README.md#delta-1afa63f88) (DTA-001…048), the [joint page](../audit/model-and-execution.md), the [broad account](../audit/README.md) (DA-068…081), and the [cost map](../evidence/2026-11-17_joint-audit-refresh/README.md) |
| Standard | Core principles 3.3, efficient-architecture heuristics 1.0, test-assessment companion 1.2, review template 3.3, code-intelligence profile 1.4 (where served results are tested), repository binding |
| Focus (operator, 2026-11-17) | Principle-focused: explicit domain model and scoped semantic authority (FP-04, A2) and execution fit (FP-07, A4), read through the test-assessment companion. Library scope open. Other guarantees constrain remedies |
| Tier · purpose | Design · target |
| Maturity | Design stage; one operator; agents edit. The 2026-11-13 target was adopted and delivered (test-system plan TS-00…20, 24, 25; TS-21/22 gated on the declared-data-operations plan). A concurrent model-owned SQL conversion ([ADR-0131](../../adr/0131-model-owned-postgresql-programs.md)) is mid-way |
| Outcome wanted | One target for the test system that resolves the open test findings, aligns tests with a domain-model-driven approach and efficient execution as far as is sound, and keeps the likely production changes local in the tests |

### Functional intent and workload premise

Tests exist to give evidence that would fail on a wrong implementation, at a cost that keeps the
working loop short for one operator and several agents sharing one workstation.

- **Focused runs dominate.** The last 120 passed narrowed runs (2026-11-16 15:19 to 2026-11-17
  16:53) had a median wall time of 29.1 s and a median fixed cost outside test phases of 7.4 s
  (0.8–39.9 s); runs with no database fixture finish in a few seconds, and runs whose setup
  reaches a head or seed build show setup of tens of seconds to minutes (Measured, cost map).
- **Preparation is the main cost.** The largest passed narrowed run since 2026-11-13
  (`873f904c…`, 2026-11-14, 685 tests, 4 workers) spent 42% of worker time in setup, 403 s of it
  in 17 tests whose setup exceeded 15 s (Measured). The native head replays 285 revisions; seeds
  run real producers; PDF scenarios run a capture.
- **No current full-run profile.** No full run has passed since 2026-11-10. Full-run statements
  here are qualitative.
- **Concurrency and envelope.** xdist workers (`-n auto` for path selections; `-n 0` for one test
  id), several agents at once, a shared PostgreSQL 18 cluster on ext4, and real GPU work on the
  same host.

### Method and coverage

I loaded the standard, companion, template, profile and binding; read all four test-audit pages,
the joint page, the cost-map README and the 2026-11-13 review in the parts that carry identities
and design; read MAP_TEST, LIB_TEST and DELTA_TEST in full. I opened the decisive sources myself:
the deployment key and lifecycle (`scripts/native_deployment_key.py` in full;
`native_test_support.py:281–396, 896–1117`), the seed registry in full, root `conftest.py` in full,
`tests/conftest.py:90–582`, `tests/scenario_recipes.py`, the kernel support
(`tests/semantic/data_operation_kernel_support.py:50–320`), the PDF source support
(`tests/semantic/current_pdf_source_support.py:1–520`), production PDF custody and streaming
(`src/corpus_structure/semantic/pdf_capture.py:55–140, 440–457`;
`orchestrate/pdf_streaming.py:270–300, 395–540`; `ingest/pdf_worker.py:60–135, 270–300`), the
executor constructor and the byte-admission builder, the native-host doubles and
`_validate_startup`, the GPU slot, the bare-engine fixture and one SQL-splicing test, the stale SQL
reader, the identity-vector test and its literal, the grading support, the query-cache support,
`change_impact.changed_operations`, the production identity primitives, model deployment's
admission sequence, one DDO revision and its executed body, ADR-0101, ADR-0102 and ADR-0131. I
read xdist 3.8.0's group-joining code and pytest 9.1.1's fixture-closure docstring in the
installed environment.

Not examined: most test bodies outside the cited files; `tests/llm`, `tests/db`, `tests/schema`
bodies; root `tests/` (34 files, outside coverage per the coordinator); the T and P contributor
reports beyond their use in the audit. Findings carried without re-inspection say so in the
dispositions. Nothing was run.

---

## 2. Integrated assessment

The 2026-11-13 target is in place and its core holds: a sealed, keyed and verified deployment
head; worker-local sealed seeds keyed by frozen recipe values; isolation classes chosen by claim;
a refusal contract; DDO support modules; a wire-checked routing double; literal identity
vectors; worker sizing for explicit selections. This review keeps all of it.

What the audit found since then is not a failure of that design but three places where the test
system's own model is still thinner than the work it governs, plus the effect of a production
model that is becoming the source of SQL:

1. **The tests do not yet have a rule for what they may take from the product model.** Five
   support modules restate how the statistics pack is composed and one pairs a model with a
   release that does not contain it (DTA-042); identity vectors share expected bytes but each
   consumer rebuilds the input, and the native half drifted (DTA-033); a test copies the executor's
   reservation formula (DTA-043); a double invents a refusal production does not have (DTA-045);
   tests read production SQL by path and splice it by text (DTA-047), so each ADR-0131 retirement
   can orphan a reader. Each of these is a different answer to the same unasked question (§3).
2. **Preparation identity is right in shape but conflates content with where things run.** A
   scenario recipe is meant to be a data-only value; the PDF recipe embeds the per-test directory
   because production binds the capture workspace into release custody, so every PDF scenario is
   unique, is sealed as a seed nobody can reuse, and stays retained for the session (DTA-040). The
   head key misses the module that executed upgrade bodies import and counts file timestamps
   instead of content (DTA-038). A key miss replays the whole chain (DTA-039).
3. **Machinery is declared in lists away from what it names.** The affinity table and the `db`
   fixture list drifted from the fixtures that exist (DTA-037); seven hand copies of the PDF
   converter double stopped producing what production requires (DTA-041); reuse and skip
   mechanisms are tested only where reusing is correct (DTA-044, 046).

The target (§4) adds no new framework. It states one rule for model binding versus independence
(§3), makes the test system's own concepts explicit — recipe content separate from per-consumer
bindings, a lifetime chosen by where a preparation's implementation is fixed, one controlled
boundary per external computation, a perturbation table per reuse mechanism, preparation
declarations at their definition — and removes the hand lists and copies those concepts replace.

**Overall judgment: Revise, second-order.** A1–A4 are violated for the current test system in the
bounded ways named in §16 and satisfied by the proposed route. Several open findings describe tests
that source shows cannot set up or pass (DTA-041, DTA-037, DTA-033, DTA-047); they are first in
priority because the claims behind them currently have no evidence.

---

## 3. What tests take from the model, and what stays independent

This answer comes first because every other recommendation depends on it.

### 3.1 The rule

For each value a test uses, ask what role it plays in the test's claim.

1. **It is the expectation** — the value the test says is correct. It must not be computed by the
   code under test, nor read from the artifact that code produces. Author it by hand, compute it by
   a different and simpler method (a small analytic case; a standard-library digest of authored
   bytes), or take it from the behaviour of a real independent system (PostgreSQL refusing a row).
2. **The claim is a correspondence** — a realization follows its declaration (generated SQL follows
   physical metadata; a key changes with each determinant; grants follow role declarations). Change
   the declaration inside the test and expect the realization to follow. The expected value comes
   from the test's own perturbed declaration, which is the mechanism's *input*, never from the
   mechanism's output or code.
3. **Otherwise it is scenario construction** — which pack, which release, which operations exist,
   the columns setup rows are written through, how a recipe is composed, which fixtures need the
   database. Take it from the model's owner: production acquisition, the release's bound model,
   generated facades, reflection, the fixture's own definition. A hand copy here detects no product
   mistake and drifts with every model change.

Two clarifications keep the rule from being misapplied:

- **A name used to select is a coordinate, not a restatement.** A demand target such as
  `"source.pdf_views/discovery"` names the operation the test is about; keep it literal. If the
  model drops the operation, the test fails loudly, which is correct.
- **A set of names stands for a model fact.** When a set only generates cases (every declared
  operation, every relation with a read role), enumerate it from the model. When the set's
  correctness is the claim (which operations a validity family contains; which operations a change
  affects; which relations a role may write), author the expected set by hand for a small model,
  and include one member the declaration does not have, so a derivation that silently accepts an
  undeclared member fails (the case [DA-070](../audit/semantic-model-and-authority.md#da-070)
  describes).

### 3.2 Examples on each side

| Element | Bind to the model (scenario) | Keep independent (claim) |
|---|---|---|
| Pack composition | Any test that needs the statistics records obtains them through production acquisition (`prepare_packs`, as `tests/statistics_pack_support.py:10–25` does), not a three-file bundle typed again (`tests/semantic/record_contracts_support.py:48–66` and four others, DTA-042) | A test whose subject is pack composition asserts the expected members by hand |
| The model a release runs | `bound_data_operation_model(prepared)` from the release under test (as kernel support does, `data_operation_kernel_support.py:152`) | — Compiling a second model beside the release (`tests/evaluate/declared_record_grading_support.py:34–57`) is neither: it is a second, divergent authority |
| Operation lists | Demand targets; iterating declared operations to generate cases | Expected validity-family membership or affected-operation sets for a hand-authored model, with a missing member ([DTA-044](../test-audit/evidence-and-discrimination.md#dta-044) change scope) |
| Fixture names | The `db` mark and the worker group derive from fixture definitions (§4.5) | — Fixture names carry no domain claim |
| Column lists | Setup rows through generated facades or reflected tables | Hand-authored expected predicates on a throwaway schema (`tests/semantic/test_physical_checks.py`); the posture test's hand list of relations and purpose roles (`test_data_operation_storage_posture_native.py:7–19`) stays hand-written because derived grants are its claim |
| Recipes | Captured inputs composed by production composers (`current_pdf_recipe` already does this) | Recipe-sensitivity tests perturb one input and expect a new identity |
| Identities | Release ids and kind keys used to address rows | Literal vectors: authored input, authored canonical bytes, standard-library digest ([DTA-033](../test-audit/evidence-and-discrimination.md#dta-033)) |
| SQL | The program obtained from its owner by import (the generator) or the installed function by name | Behaviour on PostgreSQL; structural correspondence through pglast (`test_pdf_prepare_model.py:17–51`); never text read from a file |
| Doubles | The reply's shape checked by the production wire validator | The reply's content authored by the test; any refusal a double raises is production's own ([DTA-045](../test-audit/evidence-and-discrimination.md#dta-045)) |

### 3.3 Where binding makes evidence circular

Sites at `1afa63f88` where an expectation comes from the code under test, each judged by the rule:

- the lowering-identity test compares the identity with the digest of the artifact the same
  function returns (DTA-044);
- scalar validity tests now delegate to the set evaluator, so they are no reference for it
  (DTA-044);
- the expected search selection digest is recomputed by running the production projection
  (`tests/semantic/test_source_search.py:141–185`, recorded under DTA-033);
- four generated-SQL literals were rewritten to the new renderer's spelling, and one assertion
  compares two production values (`RETIRED_PARTS`) (DELTA_TEST, §2; recorded here as **F07**);
- `test_native_sql_body.py:200–216` asserts substrings of the same production text it reads, so its
  expectation is spelling only — and the file it reads was deleted (DTA-047).

Two neighbouring faults are not circularity but are cured by the same rule: a test that
*re-implements* production logic to compute an expectation (the reservation formula in
`tests/orchestrate/test_data_operation_byte_admission.py:51–57, 80`, DTA-043), and a double that
*fabricates* an authority production does not have (`tests/methods/test_characterization_resources.py:59–61`,
DTA-045).

### 3.4 What follows for the rest of the design

The rule says the product model is the right source for *what a scenario contains* and the wrong
source for *what a test expects*. It also says what the product model cannot supply: which tests to
run (§4.5), because a test's identity depends on more than the model declares. The test system
therefore needs its own small model for preparation, boundaries and reuse evidence, keyed by the
product model's content where scenarios are concerned (§4).

---

## 4. Target design

### 4.1 The test system's own concepts

| Concept | Meaning | Current owner and representation | Target owner and representation |
|---|---|---|---|
| Recipe | The content of a prepared scenario: inputs, declarations, captured sources | Frozen dataclass values (`KernelRecipe`, `tests/semantic/data_operation_kernel_support.py:63–74`) with a canonical identity (`scripts/native_scenario_seeds.py:34–60`); the PDF recipe also carries the per-test directory | The same values, **location-free**: no filesystem path or other per-consumer fact |
| Binding | Where a recipe's preparation executes: its workspace directory, asset root | Not a concept; embedded in the recipe (`current_pdf_source_support.py:58–59, 325`) | A separate value the builder receives (the seed registry already passes the builder its own directory, `native_scenario_seeds.py:213, 224–226`); a recipe that needs a per-consumer binding is built in the consumer's clone, not sealed as a seed |
| Base | A sealed database other preparations clone | `SemanticDeployment` under a deployment key (`native_test_support.py:281–396`) | Unchanged, with a key that covers what the chain executes (§4.2) |
| Preparation lifetime | How long a preparation may be reused | Chosen per mechanism | Chosen by one principle: a preparation lives as long as the implementation it ran stays fixed (§4.2) |
| Isolation class | What isolation a claim needs | Read, rollback, commit and infrastructure fixtures (ADR-0101) | Unchanged |
| Controlled boundary | Where a test replaces an external computation | Nine PDF converter copies, a bypassed executor constructor, invented host refusals | One owner per boundary; production's protocol and refusals run; one contract control against the real boundary (§4.3) |
| Reuse evidence | What shows a reuse or skip mechanism is safe | Tests of the equal path only | A perturbation table per mechanism (§4.4) |
| Preparation declaration | Which fixtures need the database and which share a worker | Two hand-kept name lists (root `conftest.py:10–57`, `tests/conftest.py:101–142`) | Declared where the fixture is defined, or derived from the fixture graph's root (§4.5) |

### 4.2 One identity for prepared test state

**Principle.** Production keys a result by recipe, content-addressed inputs and implementation
slice (`src/corpus_structure/semantic/data_operation_identity.py:378–413`); its slice fingerprint
refuses when a required dependency is unknown. Applied to tests, the implementation slice decides
the lifetime:

- the head's implementation is frozen migration bytes plus a small module closure, which can be
  content-addressed, so the head may be reused **across sessions**;
- a seed or a prepared kernel is built by live product code, whose only exact and cheap identity
  is "the code loaded in this process", so these live **per worker process**;
- anything bound to one consumer lives **for that test**.

| Preparation | Content key | Implementation it depends on | Lifetime and sharing | Invalidation | Premise check |
|---|---|---|---|---|---|
| Head | Chain sources, executed native bodies and their module-level import closure, construction closure, artifact **content**, lockfile, interpreter, server identity | Frozen bytes and 26 package modules (analysis below) | Across sessions, workers and agents with one key; run-private for qualification | New key, new name; newest three retained | Revision and catalog verification once per process, by production's verifier (`native_test_support.py:351–387`) |
| Seed | Recipe content plus head name (`native_scenario_seeds.py:205`) | Live product code | Per worker process | Process end | Identity, sealing, policy and drained sessions on each hit; `validate_clone` per clone |
| Pure preparation (prepared kernel, compiled model) | Recipe content | Live product code | Per worker process, one bounded memo shared by seed builds and direct callers | Process end; size bound | None needed inside a process |
| Per-consumer build | Recipe content plus binding | Live product code | The test's own clone | Test end | — |

**Head key (DTA-038).** Two changes, both inside the existing key function:

1. *Executed bodies are sources.* Each declared-data-operations revision reads a digest-pinned
   `*_upgrade.txt` and executes it (`semantic_alembic/versions/semantic_ddo_domain_v9.py:15–20,
   30–44`); twenty of those bodies import `alembic_privileges` at module level, while the revision
   files import it only inside `upgrade()`, which the walk skips by design
   (`scripts/native_deployment_key.py:41–47`). The body a revision names in `NATIVE_UPGRADE_FILE`
   joins the closure walk as a source. Running the snapshot's own `import_closure` over the chain
   gives 25 package modules; adding the bodies adds exactly one, `semantic/alembic_privileges.py`
   (analysis of the snapshot, 2026-11-17). The key therefore gains the missing input without
   widening appreciably — the inversion risk DA-068 illustrates does not arise here.
2. *Artifacts by content.* Artifacts enter the key by path, size and modification time
   (`native_deployment_key.py:146–148`). A revision that pins its artifact's SHA-256 already puts
   that content into the key through its own source digest, so its artifacts need no metadata at
   all. Artifacts no revision pins enter by content digest: older revisions execute files without a
   digest (for example `semantic_alembic/versions/0035_analysis_contracts.py:21–25` runs
   `semantic_0035_admission.sql` as read), and 65 of the 285 revision files carry no SHA-256 pin.
   Timestamps leave the key, so a checkout, rebase or sibling worktree with identical content
   shares a head.

Kept as they are: the whole `uv.lock` (dependency moves are deliberate and rare; conservative beats
unsound) and verification as the authority on safety: the key is a hit-rate device, the verifier
decides (ADR-0101).

**Recipes without locations (DTA-040).** Production binds the resolved asset root and capture
directory into the release's custody artifact (`src/corpus_structure/semantic/pdf_capture.py:92–98`)
and later uses that directory as the actual spool workspace (`pdf_capture.py:453`;
`orchestrate/pdf_streaming.py:275–296`). The audit called the test-side defect "choosing a per-test
directory"; reading the execution path refines that: a directory shared across tests would also
share a workspace, which could expose the spool-reuse branch across tests and change what is
tested. The sound test-side design does not depend on that production choice:

- `current_pdf_recipe(directory, …)` becomes a location-free recipe value plus a binding the builder
  supplies;
- when a recipe declares a per-consumer binding, the registry builds it into the consumer's commit
  clone and does not seal or retain a seed — this removes the sealed seed per test that otherwise
  stays registered for the session (`native_scenario_seeds.py:269–274`) and the extra clone;
- when the binding is per worker (the seed's own directory, read-only after sealing), the recipe is
  seedable as any other.

If production later moves the workspace into a runtime binding instead of release content
(a premise returned to the production owner, §15), PDF recipes become seedable without a test
change beyond the builder.

**A seed for the completed PDF source (F06).** `_current_pdf_source` seeds only the admitted
release and then, for every consumer, initializes the project, registers an original, freezes and
registers a demand and runs a full capture execution (`current_pdf_source_support.py:325–379`); 23
test files consume it. The completed capture is committed state with no unfinished task, which
ADR-0102 already allows a seed to hold. With the workspace bound to the seed's directory, the
completed source becomes a second stage of the same recipe, and consumers whose claims start after
the capture clone it. Consumers whose claim is the capture keep building it. This is the largest
structural lever for the PDF family that source shows; its size is not measured.

**One bounded memo.** The seed builder prepares into its own directory without the memo
(`data_operation_kernel_support.py:164–167, 288–292`) while direct callers use an unbounded
`functools.cache` that keeps every prepared release and its temporary directory for the worker's
life (`:161`). One owner — the memo, bounded by entry count (`functools.lru_cache(maxsize=…)`), used
by direct callers and bypassed only for per-consumer recipes — removes the retention without losing
reuse.

**Rejected or deferred.**

- *Cross-session seeds.* A cross-session key must fingerprint the product code the builder runs.
  When the test-system plan was written, the full import closure covered 531 of the package's 566
  modules (plan authoring figure, 2026-11-13, not re-measured), so such a key would miss on nearly
  every edit while any narrower one would let stale seeds through. Rejected again, for the same
  reason the 2026-11-13 review gave.
- *Test keys built with production identity functions* (`canonical_identity`, `recipe_fingerprint`).
  Test infrastructure must keep working while the code under test is broken; a defect in the
  production identity would otherwise fail every seed instead of its own tests. `recipe_id` stays on
  canonical JSON and `hashlib`.
- *An incremental head built from its predecessor (DTA-039).* Valid only when every key component
  except the appended revisions is unchanged. During the SQL conversion the closure modules
  (`native_objects`, `alembic_native`, `alembic_privileges`) are among the files being edited, so
  most key misses would not qualify. **Deferred**; trigger: after the conversion settles, stored
  results show head builds recurring on appended-only changes.
- *Computing the key once on the xdist controller* and shipping it to workers
  (`pytest_configure_node`, `config.workerinput`). A small saving of repeated walking and hashing
  per worker (DTA-039); candidate only, unmeasured.

The doubled role-script spawn and doubled policy comparison DTA-039 names are pure repetition and
go.

### 4.3 Controlled boundaries

**The common shape.** A test replaces an external computation and nothing else: production's
protocol, encoding, identity and refusals still run. The double's output carries the identity of
its input, so misattribution is visible. Each boundary has one owner in a support module, and one
contract control runs the same authored input through the double and through the real boundary.
The wire-checked routing double (`tests/semantic/data_operation_binding_support.py:240–262`) and
the real-process host peer (`tests/methods/native_host_cases.py`) already have this shape.

| Boundary | Real component | What the double replaces | Owner and contract control | Findings |
|---|---|---|---|---|
| PDF converter | The worker child streams the producer's result, writes record batches, acknowledges completion and certifies (`src/corpus_structure/ingest/pdf_worker.py:80–131`) | The converted document and its effective options | One support module replaces the nine copies; a contract control runs one authored document through the real child with the scripted converter (the route of `tests/orchestrate/test_pdf_streaming_integration.py:96–112`) and through the controlled stream, and compares replay families, order and certificate verification | DTA-041 |
| Demand executor | Public constructor (`src/corpus_structure/orchestrate/data_operations.py:634–693`) | Native I/O only | Executors are built by the constructor from a prepared kernel recipe with explicit `database_capacity`; tests read `executor.reservation`; one test pins the formula with literal numbers | DTA-043 |
| Native host startup | Parent comparison `NativeHost._validate_startup` (`src/corpus_structure/methods/native_host.py:196–213`); child asset checks (`native_host_adapters.py:17–48`) | The model inside the peer | The peer gains a mode that reports one perturbed profile field; a per-field perturbation table drives the parent comparison (§4.4); the invented `Group.startup` refusal goes | DTA-045 |
| Native storage | `DataOperationStorage.invoke` validates input and output | Native replies | Wire-checked double (exists) | DTA-034 |
| Read-result page, frontier recheck | `stream_demand_result`; `recheck_selected_frontier` | The native page; the recheck | `_page` (`tests/semantic/test_demand_results.py:20–91`, eleven importers) moves to support and is validated against the generated wire type; `control_frontier` raises only production's refusals | DTA-034, DTA-009 |
| Encoder batch | Contextual encoder | The model | An identity-bearing fake whose vector is derived from its input text, with a multi-survivor drop case | DTA-046 |

**Judging the certified converter helper (`f511833df`).** `_certified_controlled_reply`
(`current_pdf_source_support.py:198–232`) makes the right boundary choice: the fixture authors the
document and production encodes and certifies it. Its weaknesses are fixable inside the target
shape: it restates the child's ordering (preparation, records, completion, certification), imports
the private `_atomic_bytes` and `_ref`, writes preparation bytes that are not a valid preparation
report (`:274`), and builds its spool without the request's payload schema. Only two of nine sites
adopted it, and its new keyword requirement broke `tests/semantic/test_current_pdf_source_inputs.py:58–68`.
The shape fits the executor (replace native I/O, keep the constructor) and the native host (the
real-process peer already replaces only the model). The better owner of the stream protocol is
production: the child's handling of a stream request is inline in `_native_child` and not callable
alone. A production function for it, which both the child and the controlled double call, would
remove the test's restatement; that is returned to the production owner (§15), and the test-side
owner is designed to delegate to it when it exists.

### 4.4 Evidence for reuse and skip mechanisms

One pattern, a **perturbation table**, applies to every mechanism that reuses work or skips a
check, without taking the expectation from the code under test:

1. **Observe the decision.** Use what the mechanism exposes: the PDF certification read returns
   `certification_basis` (`'round-trip-verified'` or `'producer-certified'`,
   `src/corpus_structure/semantic/pdf_certification_native.py:62–90`); the deployment record says
   `built` or `reused`; seeds report their origin. Where nothing is exposed, wrap the expensive
   production step in a counting spy; that observes an effect, not an expectation.
2. **Hit control.** Same inputs, reuse observed.
3. **Perturbation cases.** For each determinant *the test author* judges should matter, from the
   domain rather than from the key's code, perturb its source (an artifact's bytes, a receipt's
   state, a revision's publication, a budget) and assert the literal outcome: recomputed, checked,
   or refused.
4. **Completeness where the mechanism declares its determinants as data.** Assert that the table
   covers the declared set (for example the fields of the native profile type checked by
   `_validate_startup`). A new determinant without a case fails this one test. Where a mechanism
   declares nothing, the table is the specification.
5. **Two directions.** Safety cases (must not reuse) are direction-independent and are written now.
   Precision cases (must still reuse after an irrelevant change) wait until the production owner
   decides an identity's grain (DA-068, DA-069), because today's broad identities would fail them.

Applied to the gaps DTA-044, 045 and 038 name: the oracle skip (failed, unpublished, other-kind and
unvalidated receipts each force the oracle); kernel-sealed completion (a receipt under a different
kernel runs the publish-time battery); lowered release facts (a changed lowering digest refuses and
re-admission re-lowers); query-cache budgets (`max_bytes` varied against a warm entry; the entry
count exceeded); change scope (an unrelated operation stays outside the affected set in a model with
several operations; a revocation in one source scope leaves a read pinned to another current); file
custody's racy window; the execution-basis key (root and run determinants varied); the frozen-profile
comparison (each profile field); the deployment key (an import added to an executed body).

Plain `pytest.mark.parametrize` with `dataclasses.replace` covers fixed determinant sets. Hypothesis'
`RuleBasedStateMachine` adds value only for lifecycle order (warm, perturb, restore, query) of the
in-process caches; the managed `ci` profile already sets `database=None` and `derandomize=True`
(`tests/conftest.py:95–97`), so no failure history is kept.

### 4.5 Model-derived scope and grouping

**Selection.** Dependency-based selection stays rejected. `change_impact` compares two compiled
models and reports operations whose recipe, eligibility or recipe identity changed and their
dependents (`src/corpus_structure/semantic/change_impact.py:157–200`). A test's identity also
depends on Python modules outside any declared slice, on generators, migrations and test support,
none of which that comparison sees, and using it requires compiling both models. An incomplete
dependency key would skip affected tests silently (G6). The earlier reasons therefore still hold.
Revisit if a family's operations have complete implementation slices and its tests declare the
operations they exercise; even then only an advisory listing, never a skip.

**Grouping and the `db` mark (DTA-037).** Grouping derives from the test system's own
declarations, not from change impact:

- the `db` mark derives from the root every native fixture depends on (`native_server`); the
  closure pytest computes per item (`item.fixturenames`) already reaches it, so the 38-name list
  becomes one name and its eleven undefined and six unsatisfiable entries disappear. Dynamic
  requests are invisible to the closure (pytest 9.1.1 `FuncFixtureInfo` docstring), so native
  fixtures requested through `request.getfixturevalue` (for example `tests/conftest.py:498–513`;
  seven calls in four files) become static dependencies;
- a fixture that holds expensive shared preparation declares its worker group where it is defined,
  through a small decorator that wraps `pytest.fixture` and records the group; the root
  collection hook groups an item by the declarations in its closure and keeps today's refusal of
  conflicting groups (root `conftest.py:72–75`). A deleted fixture takes its declaration with it.
  Pytest offers no fixture metadata of its own: marks on fixtures are an error since 9.0;
- rollback families stay grouped by family; commit-class consumers of a recipe stay ungrouped, as
  the 2026-11-13 review decided, because grouping them would serialize real bodies onto one worker.

### 4.6 Retirement without a lint

Machinery retires with what it serves when nothing names it by hand:

1. **Derive, do not list** (§4.5). A derived mark or group cannot outlive its fixture.
2. **Obtain the subject from its owner by import.** A test that imports a generator or names an
   installed function fails at collection or with a missing-object error when the owner retires; a
   test that reads a file by path fails only when run, and only if someone runs it
   (`tests/semantic/test_native_sql_body.py:200–216` reads a file deleted in `708c119a6`).
3. **The retiring change removes its tests and their machinery**, transferring any behaviour
   without a surviving control first: the transfer rule of the 2026-11-13 review, held by TS-21 for
   the DDO cutover, applied to each ADR-0131 retirement. The four unimported support modules and the
   six `record_source_*` fixtures (`tests/conftest.py:532–567`) go now.
4. **Production kept alive only by tests** (DA-080) retires with those tests.

No checker is added; the first two items remove the need for one.

### 4.7 Executing the suite

| Cost | Necessary? | Target |
|---|---|---|
| Head build on a key change | Yes | Key covers what the chain executes and ignores timestamps (§4.2) |
| Head verification once per worker | Yes, a deliberate trust premise (ADR-0101) | Kept |
| Policy replay per clone | Yes (ADR-0101) | Kept; the doubled comparison goes |
| Seed build per recipe per worker | Yes, given process-scoped validity | Kept; per-consumer recipes stop being sealed |
| Full PDF capture per consumer | No, where the claim starts after the capture | Completed-source seed stage (F06) |
| A database per case for expression checks (`tests/native_fixture_support.py:29–38`; `tests/semantic/test_data_operation_trust_snapshot_sql.py:16–31`) | No | Installed functions called in the read class on the head; text splicing ends (DTA-047) |
| The real host-wide GPU lock in an ordinary test (`tests/methods/test_native_host.py:716–752`; lock path fixed in `src/corpus_structure/ingest/pdf_capacity.py:51`) | No for the claim tested | The ordinary test asserts that the previous group is retired inside `external_gpu` (already asserted) without taking the real slot; the slot's lock is covered by stubbed controls (DTA-048) |
| Worker startup for one test | No | Already removed (`-n 0` for one id, F05) |

### 4.8 Readiness for the planned production changes

| Premise | What breaks or goes stale in tests today | Seam that keeps the change local | Holds under both directions? |
|---|---|---|---|
| SQL and Python facades are generated from the model; hand SQL files and substring rewrites retire (ADR-0131) | About seventeen modules read production `.sql` by path, eight splice by anchor text, 52 files assert substrings of SQL or source (MAP_TEST M4); one reader is already orphaned | Subject from its owner (§4.6): programs by import or installed function by name, behaviour on PostgreSQL, structure through pglast; each conversion commit moves its readers. Tests' own control SQL stays, as ADR-0131 states | Yes |
| Controlled PDF fixtures move through the certified producer; the fixture-only occurrence writer is deleted (step 3) | Seven uncertified converter copies; one direct caller | One controlled-converter owner that delegates to a production stream function when one exists (§4.3) | Yes |
| Analytical SQL becomes DuckDB relations (step 6) | Any test that would compute expected rows by running the relation | Expected rows authored for small inputs now, asserted on the evaluator's public result, so the same tests guard the backend switch | Yes |
| Kernel identity becomes finer than one digest (DA-068) | Kernel-sealed completion's fallback never runs in tests (DTA-044) | Perturbation table: safety cases now; precision cases with the production decision (§4.4) | Yes |
| Validity families, support graph and implementation identity derive from declarations (DA-070, 071, 076) | No missing-member case; scalar tests delegate to the set evaluator | Hand-authored small models with expected sets, shared descendants, mixed seeds, a two-node cycle and an undeclared member (§3.1) | Yes for declared members; the undeclared-member case is written with the production change, since it fails today |
| Query cache keyed by request identity, possibly shared across processes (DA-075) | Isolation is an autouse clear in a support module imported by ten modules (`tests/semantic/selected_query_cache_support.py:13–17`); identical seed clones would share entries under a content key | One package-level cache-scope fixture owns isolation (a cold cache by default, warm state built explicitly by the test); if the cache becomes durable, the same fixture scopes it to the clone | Yes |
| Release composition and guard or grant membership move into the model (DA-073, 074) | Five modules hand-list pack bundles; 48 files carry role-name literals | Scenarios obtain releases through production acquisition by name; posture tests keep hand-authored expected relations and roles | Yes |
| *Added:* host bootstrap and test provisioning through shared administration builders (step 5) | The head key's construction component covers only `construct_deployment`'s closure; `PgAdmin` provisioning is outside it | Provisioning that shapes the head's content is called from the construction entry point, whose closure is keyed; policy capture and replay keep comparing actual catalogs | Yes |
| *Added:* release admission as one production operation | `admit_kernel` restates production's persist, admit and bind order (`data_operation_kernel_support.py:228–252`; compare `src/corpus_structure/schema/model_deployment.py:996–1010`) | One test owner (`admit_kernel`) calls the production operation when it exists | Yes |
| *Added:* the capture workspace becomes a runtime binding rather than release content | PDF recipes unique per test | Recipe and binding split (§4.2) | Yes |

---

## 5. Corrective arguments

Diagnoses are Interface-checked (2026-11-17) unless the dispositions say a finding was carried
without re-inspection. Remedies are Proposed.

### 5.1 Model facts restated by hand

**DTA-042 — pack and recipe composition restated; a model paired with the wrong release.**
Confirmed: `declared_record_grading_support.py:34–57` prepares the release from the bundle alone and
compiles the model with reading-resolution declarations and Python sources. *Correction:* scenario
support obtains the release through production acquisition and the model from that release; the
two `current_pdf_recipe` functions become one composer; the twelve recipe-extension sequences call
one helper that is the only user of production's `"data-operations/"` prefix. Hand-authored record
contents stay. *Alternatives:* a shared test copy of the bundle (one place, still a restatement
that drifts from production acquisition); leaving the copies (every pack change edits five
modules). Both lose to binding.

**DTA-033 — identity vectors share expected bytes but not inputs.** Confirmed: the native case
builds its value without `subject_definition` (`tests/semantic/test_data_operation_identity_native.py:21–41`)
while the literal includes it (`tests/semantic/data_operation_identity_vectors.py:17–24`).
*Correction:* each vector record carries its authored input as data, beside the authored canonical
bytes; both consumers use that input; a request-identity vector is added and `subject_definition`
is varied. *Alternative:* build the native input through production's subject context, as the
Python consumer does — that makes the input follow production and hides a framing mistake made on
both sides.

**DTA-043 (formula half).** Covered in §5.3.

**F07 — generated-SQL tests assert renderer spelling copied from new output.** Low weight. The
literals discriminate spelling, not meaning, and each renderer change requires copying output
again. *Correction:* assert the meaning through pglast (the target type of the cast, the index
method) or through PostgreSQL behaviour; replace production-to-production equality with an
authored expected tuple.

### 5.2 Preparation identity

**DTA-038 — head key coverage.** §4.2. *Alternatives considered:* the full nested closure (covers
nearly the whole package; the operator rejected it on 2026-11-13 for that reason, and it would
rebuild the head on almost every edit); trusting verification alone (it checks catalog predicates,
not every effect privilege admission produces). Adding executed bodies costs one module.

**DTA-039 — full replay per key miss; repeated verification.** Remove the doubled spawn and
comparison; keep per-process verification and per-clone replay; defer the incremental head (§4.2).

**DTA-040 — per-test directory in PDF identity.** Diagnosis refined (§4.2): the directory is the
production workspace, so a shared directory is not a safe test-side fix. *Correction:* recipe and
binding split; per-consumer recipes built in the consumer's clone; bounded memo.
*Alternatives:* a stable per-worker directory (risks cross-test workspace reuse); asking
production to drop the directory from custody (a production remedy this review does not select;
returned).

**F06 — the PDF source scenario re-executes its capture per consumer.** §4.2. Depends on
DTA-040's binding concept. Closure: consumers whose claims start after capture clone a
completed-source seed; capture-claim consumers keep building.

**DTA-047 (cost half) — a database per case for checks that need one session.** *Correction:*
call the installed function on the head in the read class (ADR-0101 already provides it), which
also tests what deployment installed — the fidelity gap the audit names for `_native`-named tests
on substitute schemas. Where a check needs a temporary function, obtain the statement from its
generator and install it in a rolled-back transaction. *Alternative:* the infrastructure rollback
connection on a template clone; cheaper still but outside ADR-0101's stated purpose for
infrastructure clones (RC10), and it keeps testing a fragment instead of the deployment.

### 5.3 Controlled boundaries

**DTA-041 — converter copies.** §4.3. Seven copies return the five-field reply without preparation,
completion or certification; both production refusals stand
(`src/corpus_structure/ingest/pdf_build_spool.py:744–748`, `orchestrate/pdf_streaming.py:529–530`), so
by source their consumers cannot set up. *Correction:* one owner, all nine sites, the in-body
copies removed, `test_current_pdf_source_inputs.py` re-pointed, a contract control.
*Alternatives:* every test through the real child with a scripted converter (strongest fidelity, a
process per scenario, kept for the contract control); fixing the seven copies in place (repeats the
cause).

**DTA-043 — executor from private fields.** Confirmed: `NativeDemandExecutor.__new__` and about
fourteen attributes (`tests/orchestrate/test_data_operation_byte_admission.py:69–110`) and four more
`__new__` sites in `test_data_operation_execution_basis.py`. *Correction:* §4.3; the builder moves
to a support module. A native-I/O seam on the executor would be the cleaner owner and is returned
to production. *Alternative:* keep the bypass and import the formula from production (removes the
copy, keeps eighteen private assignments).

**DTA-045 — refusal asserted against an invented rule.** Confirmed: the double's `startup` refuses
"frozen selection" and production has no such pre-start check. *Correction:* §4.3 and §4.4; the
resources test that remains asserts only that `ProviderExecution` propagates a refusal the group
raises, and says so in its name.

**DTA-034 (remaining substitutes) and DTA-046.** §4.3. Carried on the audit's reading.

### 5.4 Reuse and refusal evidence

**DTA-044.** §4.4. Its oracle-skip item has an observable outcome (`certification_basis`), so the
perturbation table needs no production change.

**DTA-001 (changed footprint).** The refusal contract helper exists (TS-09); the new sites adopt it
(exact SQLSTATE plus message or constraint, after a positive control). No new mechanism. Carried on
the audit's reading.

### 5.5 Retirement

**DTA-037.** §4.5 and §4.6; `tests/semantic/test_source_routing.py:9–12` requests a fixture defined
nowhere and is rewritten onto a current scenario or deleted with its transfer note.

**DTA-047 (retirement half).** §4.6; the stale reader is fixed now.

**DTA-036, DTA-009.** DTA-036 stays with the plan's DDO-12 mapping (TS-22). DTA-009's sharper
cases (`_page`, `_complete_ready`, `controlled_executor`, cross-directory imports) move to support
modules with the boundary corrections; cohesive public builders imported from test modules move
when touched, since no assertion depends on them.

### 5.6 Host interference

**DTA-048.** §4.7. **DTA-026 (remaining private-state test).** Deferred to an interpreter change.

---

## 6. Library and system mechanisms

| Capability | Mechanism and API | Conditions and limits | Reference and strength | Status |
|---|---|---|---|---|
| Fixture closure per item | `item.fixturenames` (closure of arguments, `usefixtures` and autouse) in `pytest_collection_modifyitems`; root hook `tryfirst` so xdist sees marks | Dynamic `request.getfixturevalue` requests are not in the closure; conftest fixtures are known only for the collected subtree | pytest 9.1.1 `_pytest/fixtures.py` `FuncFixtureInfo` docstring (installed source, read 2026-11-17) | Selected (existing hook) |
| Fixture-level declarations | A project decorator wrapping `pytest.fixture` that records a group | Pytest 9 refuses marks on fixtures; an alternative is `pytest.param(..., marks=pytest.mark.xdist_group(...))` in fixture params, rejected because it changes every consumer's node id and xdist joins conflicting groups silently | pytest deprecations page "applying a mark to a fixture function"; LIB_TEST A3 (contributor, installed source) | Selected |
| Worker affinity | `--dist=loadgroup`, `xdist_group` marks | Several marks on one item form a joined group (`'_'.join(sorted(...))`); collection must be identical on every worker | xdist 3.8.0 `remote.py:236–254` (read 2026-11-17) | Selected (existing) |
| Shipping a run-wide value to workers | `pytest_configure_node(node)`, `node.workerinput` → `config.workerinput` | Controller never collects | xdist 3.8.0 `workermanage.py`; LIB_TEST B3 (contributor) | Candidate (§4.2) |
| Head publication and reuse | `CREATE DATABASE … TEMPLATE`, `ALTER DATABASE … RENAME TO`, `ALLOW_CONNECTIONS false`, session advisory locks | No other session on a template during a clone; concurrent clones of one template not confirmed here | PostgreSQL 18 docs; existing `native_test_support.py:995–1057` | Selected (existing) |
| Read class for installed functions | `rollback_connection(..., readonly=True)` on the per-worker clone (`tests/conftest.py:436–439`) | Read-only masks privilege refusals of writes (`25006` before `42501`) | ADR-0101; PostgreSQL 18 `SET TRANSACTION` | Selected (existing) |
| Content digests for artifacts | `hashlib.file_digest` | Cost of hashing unpinned artifacts not measured | Python 3.14 standard library | Selected |
| Bounded memo | `functools.lru_cache(maxsize=…)` | Entry bound only; size per entry unbounded | Standard library | Selected |
| Determinant perturbation | `pytest.mark.parametrize`, `dataclasses.replace`, `dataclasses.fields` | Fixed determinant sets | Standard pytest | Selected |
| Cache lifecycle sequences | Hypothesis `RuleBasedStateMachine` (`@rule`, `@invariant`, `Bundle`) | Use the `ci` profile (`database=None`, derandomized) | Hypothesis 6.170.12 stateful docs; LIB_TEST D (contributor) | Candidate |
| SQL structure | pglast `parse_sql` | Parses, does not execute | Existing use (`test_pdf_prepare_model.py`) | Selected (existing) |
| Library-owned database lifecycle | pytest-postgresql template janitor | No policy replay, leases or authenticated drops; no key-addressed cross-session reuse | Earlier assessment, carried | Not adopted |
| Change-based selection | pytest-testmon; production `change_impact` | Neither sees SQL generators, migrations, test support or package data | §4.5 | Rejected |
| In-process cache library | cachetools 7.2.7 (`cached(..., condition=…)`) | Per-process only; no persistence | Joint page library table | Not needed for tests |

---

## 7. Alternatives

| Alternative | Change propagation | Semantic authority | Test boundary | Machinery and risk | Decision |
|---|---|---|---|---|---|
| Current baseline | Pack, recipe, converter and list changes repeat across copies | Five composition copies; nine converters; two name lists; a model compiled beside its release | Doubles below or beside the boundary; invented refusals | Per-test seeds retained; per-case databases; chain replay per miss | Revise |
| Proposed (§3–§4) | One owner per fact; derived lists | Product model for scenarios; independent expectations for claims; test concepts explicit | One controlled boundary per external computation, checked once against the real one | Removes copies, lists and per-test seeds; adds a decorator, a recipe/binding split and perturbation tables | Selected |
| Library-owned lifecycle (pytest-postgresql) | Moves lifecycle into a plugin | Loses replay and authenticated ownership | Same | Integration gaps | Rejected |
| Simplest viable: fix the copies and lists in place | Small | Unchanged | Unchanged | The same drift recurs at the next retirement or protocol change, as DTA-029 → DTA-041 and DTA-030 → DTA-037 already show | Insufficient |
| Model-driven test selection and cross-session seeds | Adds whole-product keys | Two reuse mechanisms over live code | Unchanged | Rarely hits in the edit loop; an incomplete key skips or reuses wrongly (G6) | Rejected |

---

## 8. Change and failure scenarios

| Scenario (kind) | Today | Target |
|---|---|---|
| Add a modeled field (domain extension) | Generated SQL and facades follow; path-reading and splicing tests break; five pack copies unaffected but stale | Scenarios follow through production acquisition; tests whose claim includes the field change deliberately; no text readers remain |
| Add a data operation (instance) | Declaration builders exist (TS-17); a new preparation fixture needs a list edit | Same builders; any new preparation fixture declares its group where defined |
| Retire a production mechanism (mechanism removal) | Path readers orphaned silently; lists keep dead names | Import failures name every dependent test; nothing listed by hand; the retiring change removes its tests |
| Add a determinant to a cache key (policy) | No test fails if it is dropped later | The perturbation table's completeness case fails until a case is added |
| Edit one kernel module (implementation) | Head unaffected unless in the 26-module closure (correct); seeds rebuild per process (correct); kernel-sealed fallback never exercised | Same reuse; the fallback is exercised by a safety case |
| Replace the PDF worker boundary (mechanism substitution) | Nine copies to change; two refusals broke seven | One owner; the contract control shows drift |
| One focused test, cold then warm | Cold: head build if the key moved, then seed and capture; warm: head reused, seed and capture rebuilt per test for PDF scenarios | Warm PDF consumers whose claims follow capture clone a completed-source seed |
| Several workers | Each builds its seeds; per-test PDF seeds accumulate | Per-consumer recipes are not sealed; seeds per recipe per worker |
| Interrupt and resume | Build residue and pid-named clones swept next session; prepared-kernel temporary directories outside the scratch root can leak | Same sweep; memo directories under the scratch root |
| Two agents at once | Head shared under leases; one ordinary test can fail on the other agent's GPU capture | Same sharing; the ordinary test no longer takes the host lock |

---

## 9. Gates and foundations

Verdicts are for the current test system at `1afa63f88` within the focus; the proposed route is
designed to pass each.

| Gate | Verdict | Evidence | Required action |
|---|---|---|---|
| G1 Authority | Fail | Two name lists independent of the fixture graph that now disagree with it (DTA-037); nine converter copies (DTA-041); five pack-composition copies and a second compiled model (DTA-042); a copied reservation formula (DTA-043) | §4.3, §4.5, §5.1 |
| G2 Semantic fidelity | Pass, narrowly | Receipts keep outcome classes distinct; the GPU test's message misattributes cause (DTA-048), judged under G7 | — |
| G3 Validity | Fail | A refusal asserted against a double's invented rule (DTA-045); a native vector whose input cannot match its literal (DTA-033); setup that production now refuses (DTA-041) | §4.3, §5.1 |
| G4 Hidden behaviour | Pass | The cache clear is opted into by import; one dynamic fixture request hides a native dependency from classification (fixed in §4.5) | — |
| G5 Consistency and recovery | Pass | Rename publication, sealing, sweep and retention hold; per-test seed retention is resource, not consistency | — |
| G6 Transformation and reuse | Fail, bounded | The head key omits a module the chain executes (DTA-038), bounded by first-use verification; production reuse mechanisms lack failing-path evidence (DTA-044) | §4.2, §4.4 |
| G7 Truthful capability claims | Fail | `_native`-named tests run on substitute schemas (DTA-047); a test named for root exactness never varies the root (DTA-044); the GPU test blames a previous NLP group when another capture holds the lock (DTA-048) | §4.4, §4.7 |
| G8 Library leverage | Pass | pytest closure and xdist groups are used; the bespoke pieces (policy replay, key, registry decorator) have stated reasons | — |
| CI-G1–G3 (profile) | Not re-assessed | Served-result tests were outside the focus beyond identity vectors, which are judged under G3 | — |

**Foundations.** FP-01 violated (support owned by whichever test module wrote it first, DTA-009);
FP-02 violated (doubles beside the boundary, DTA-041/043/045); FP-03 violated (copied protocols and
sequences); **FP-04 violated** for model restatement and fabricated authority (DTA-033, 042, 045)
and satisfied for most expectations, which remain independently authored; FP-05 violated (recipe
and binding not distinguished; preparation declarations kept apart from definitions); FP-06
violated (a pack change edits five modules; a protocol change breaks seven); **FP-07 violated**
(DTA-040, F06, DTA-047, DTA-048). Supporting rules used: DP-01, DP-04, DP-06, DP-09, DP-10, DP-16,
DP-23. Heuristics used: H1, H4, H12, H13, H14, H18, H19, H20, H21, H27.

---

## 10. Finding index

Audit identities are those of commit `aca50eeea`. "Refine" changes the diagnosis; the
[dispositions](test-domain-model-and-execution/dispositions.md) give every open finding's
disposition and the DA findings the target depends on.

| ID | Diagnosis | Selected correction | Priority |
|---|---|---|---|
| [DTA-041](../test-audit/support-structure.md#dta-041) | Retain (delta) | One controlled-converter owner with a contract control | 1 |
| [DTA-037](../test-audit/retirement-transfer.md#dta-037) | Retain | Derived `db` mark and definition-site groups; dead fixtures and modules removed | 1 (the dangling request), 3 otherwise |
| [DTA-033](../test-audit/evidence-and-discrimination.md#dta-033) | Retain (regressed) | Vector records carry authored inputs | 1 |
| [DTA-047](../test-audit/execution-and-qualification.md#dta-047) | Retain (delta) | Installed functions in the read class; subjects from owners; stale reader fixed | 1 (stale reader), 2 otherwise |
| [DTA-045](../test-audit/evidence-and-discrimination.md#dta-045) | Retain | Per-field perturbation and a real-peer reach control | 2 |
| [DTA-044](../test-audit/evidence-and-discrimination.md#dta-044) | Retain | Perturbation tables | 2 |
| [DTA-042](../test-audit/support-structure.md#dta-042) | Retain | Production acquisition; model from the release | 2 |
| [DTA-038](../test-audit/execution-and-qualification.md#dta-038) | Retain | Executed bodies in the closure; artifacts by content | 2 |
| [DTA-040](../test-audit/execution-and-qualification.md#dta-040) | Refine | Recipe and binding split; bounded memo | 2 |
| F06 | New | Completed-source seed stage | 2 |
| [DTA-043](../test-audit/support-structure.md#dta-043) | Retain | Public constructor; formula pinned once | 3 |
| [DTA-046](../test-audit/evidence-and-discrimination.md#dta-046) | Retain | Identity-bearing fake with several survivors | 3 |
| [DTA-048](../test-audit/execution-and-qualification.md#dta-048) | Retain | Ordinary test without the real lock | 3 |
| [DTA-039](../test-audit/execution-and-qualification.md#dta-039) | Retain | Pure repetitions removed; incremental head deferred | 3 |
| [DTA-034](../test-audit/support-structure.md#dta-034) | Retain | Remaining substitutes wire-checked | 3 |
| [DTA-001](../test-audit/evidence-and-discrimination.md#dta-001) | Retain | Existing refusal contract applied to new sites | 3 |
| [DTA-009](../test-audit/support-structure.md#dta-009) | Retain | Sharp cases to support modules | 4 |
| F07 | New | Meaning asserted through pglast or behaviour | 4 |
| [DTA-026](../test-audit/execution-and-qualification.md#dta-026) | Retain | Deferred to an interpreter change | 4 |
| [DTA-036](../test-audit/retirement-transfer.md#dta-036) | Retain | With TS-22 at DDO-12 | Plan-owned |

---

## 11. The 2026-11-13 review: what carries and what no longer applies

| Identity | 2026-11-13 meaning | Current state (test-system plan at `1afa63f88`) | This review |
|---|---|---|---|
| F01 | Sweep lock key differs from lease key | Closed by TS-01 | No longer applies; one naming and lease authority is a preserved strength |
| F02 | Module and session preparation rebuilt per worker; affinity groups | Closed by TS-12 with a fixture-name table | The table drifted (DTA-037); its mechanism is replaced by definition-site declarations (RC09). The grouping decision itself carries |
| F03 | Identical committed scenarios rebuilt; seeds | Closed by TS-08, TS-11 | Carries; its "frozen recipe value" premise is refined by the recipe and binding split (DTA-040, RC08) and extended by F06 |
| F04 | Sweep fails other runs on in-use residue | Closed by TS-01 | No longer applies; preserved strength |
| F05 | One-test runs start sixteen workers | Closed by TS-04 | No longer applies; preserved strength |
| RC01 | Reusable heads across narrowed runs (ADR-0032) | Accepted; ADR-0101 | Carries; its key inputs are refined by RC07 |
| RC02 | Worker count for narrowed runs | Accepted; implemented | Carries unchanged |
| RC03 | DDO native checks on clones, not the working database | Accepted; the DDO companion now says the working database is not a test lane | Carries unchanged |
| RC04 | General seeds; rollback-only narrowed (ADR-0048) | Accepted; ADR-0102 | Carries; tightened by RC08 |

The 2026-11-13 decisions on dependency-based selection, process-scoped seeds, isolation classes,
the refusal contract and the implementation snapshot all still hold. Its C1–C6 cause grouping is
superseded by §2's three causes, which are what remains after its corrections landed.

---

## 12. Rule impacts

Each is for the operator to confirm or reject in plan creation; none takes effect from this review.

**RC07 — Deployment key inputs** ([ADR-0101](../../adr/0101-verified-test-deployments.md),
Decision: "the key covers migration source, frozen-artifact metadata, module-level package import
closure …"; the test-system plan's operator decision of 2026-11-13 recording the module-level
closure). *Proposed change:* executed native bodies named by a revision are closure sources;
artifacts enter by content (pinned digests through their revision, content digests otherwise),
not by size and modification time. *Depends:* DTA-038. *If kept:* the omitted module stays bounded
only by verification, and identical content in another checkout or after a rebase rebuilds the
head.

**RC08 — Seed recipes carry no execution location**
([ADR-0102](../../adr/0102-reusable-native-scenario-seeds.md), Decision: "keyed by the frozen
data-only recipe and acquired head"). *Proposed change:* a recipe is content only; a workspace
or asset location is a binding the builder supplies; a recipe that needs a per-consumer binding is
built in the consumer's clone and never sealed as a seed. *Depends:* DTA-040, F06. *If kept:* PDF
scenarios keep sealing one unreusable seed per test for the session, and F06 is unavailable.

**RC09 — Where preparation declarations live** (test-system plan TS-12, "affinity by distinctive
shared fixture names and consumer-qualified local fixtures"; `DB_FIXTURES` in `tests/conftest.py`).
*Proposed change:* the `db` mark derives from the native root fixture; worker groups are declared at
the fixture definition; both hand lists are removed. *Depends:* DTA-037. *If kept:* the lists are
corrected by hand and drift again at the next retirement.

**RC10 — Infrastructure clones for SQL expression checks** (ADR-0101: infrastructure clones are
"shared only for connection exercises without durable effects"). *Proposed change, only if the
operator prefers the cheaper route of §5.2:* allow rolled-back infrastructure connections for
expression checks that install only temporary objects. *Depends:* the alternative half of DTA-047.
*If kept:* the selected route (installed functions in the semantic read class) applies unchanged.

**Not rule impacts, stated for confirmation.** The completeness case in a perturbation table is a
test of one mechanism's behaviour, not a repository-wide alignment check; if the operator reads it
as a check under "no new alignment linting", drop that one case and keep the per-determinant cases.
Hypothesis stateful tests use the existing history-free profile. ADR-0131's "preserve independent
control SQL" is consistent with ending text splicing, which concerns production SQL, not tests' own.

---

## 13. Order of work

**Prerequisites, by the capability each needs.**

1. *The rule of §3* needs nothing and shapes every later change.
2. *Restoring setup* (DTA-041's seven copies onto one owner; the stale SQL reader; the dangling
   fixture request; the native vector input). These restore evidence that is currently absent.
3. *The recipe and binding split* precedes F06 and is independent of the key work.
4. *The key changes* (DTA-038) are independent of everything else.
5. *Definition-site declarations* (DTA-037) precede any new preparation fixture.
6. *Perturbation tables* (DTA-044, 045) need only the observable outcomes that already exist.

**During the SQL conversion versus after it.**

| Safe now, independent of the conversion | Coordinate with the conversion | Wait for a production decision |
|---|---|---|
| Head key changes; definition-site declarations and dead-fixture removal; recipe and binding split and bounded memo; DTA-033 inputs; DTA-043, 045, 046, 048; perturbation tables at behaviour level (they guard the conversion); authored expected rows ahead of DuckDB relations | DTA-041 is the same change as the conversion's step 3 fixture move — do it once, now, with that step's owner, because consumers cannot set up today; each SQL retirement moves its path readers in the same commit (step 4); after step 5, confirm provisioning that shapes the head is reached from the construction entry | Precision cases of perturbation tables (DA-068, 069); the undeclared-member case for validity families (DA-070); F06's per-worker variant if production moves the workspace into a runtime binding |

**Priority by consequence** is the finding index's column: tests that cannot set up or pass first,
then evidence that cannot fail (DTA-045, 044) and identity coverage (DTA-038, 042, 040), then
execution and ownership.

---

## 14. Verification and uncertainty

| Claim | Label and date | Basis | Gap |
|---|---|---|---|
| Seven uncertified converter copies; both refusals present | Interface-checked 2026-11-17 | Search for five-field replies; `pdf_build_spool.py:744–748`, `pdf_streaming.py:529–530` | Not run |
| Executed bodies add one module to the key closure | Analysis 2026-11-17 | Snapshot's `import_closure` over the chain with and without bodies (25 → 26) | — |
| The capture directory is the production workspace | Interface-checked 2026-11-17 | `pdf_capture.py:92–98, 453`; `pdf_streaming.py:275–296` | Whether a shared directory would reach the spool-reuse branch was reasoned, not traced |
| The executor constructor computes reservation and capacity | Interface-checked 2026-11-17 | `data_operations.py:634–693` | — |
| `certification_basis` exposes the skip decision | Interface-checked 2026-11-17 | `pdf_certification_native.py:62–90` | Which caller surfaces it to a test not traced |
| Durations | Measured from stored results | Cost map | No current full run; shared host |
| Every remedy | Proposed | — | Not implemented |

**What would change the judgment.**

- If production intends the capture workspace to be release identity permanently, F06 needs the
  seed's own directory as its binding, which the design already allows; nothing else changes.
- If seeding the completed PDF source is invalid for most consumers (their claims include the
  capture), F06 shrinks to a few modules; reading the 23 consumers settles it.
- If hashing unpinned artifacts proves expensive, keep size and timestamp for those files only.
- If the operator treats perturbation-table completeness as a lint, drop that case (§12).
- If a stored full run later shows seed builds per worker dominating setup, grouping commit-class
  consumers by recipe becomes worth its serialization; until then it is not recommended.

---

## 15. Returned to the audit

**Out of focus.**

- Production binds the capture workspace and asset root into release custody
  (`src/corpus_structure/semantic/pdf_capture.py:92–98`), so a release's identity depends on a
  filesystem location (identity broader than its premise; joint page cause 1).
- The worker child's stream protocol is inline in `_native_child` (`ingest/pdf_worker.py:80–131`);
  a callable production function would let tests stop restating it.
- The executor has no native-I/O seam; tests replace private methods.
- `NativeHost._validate_startup` is a private static method; a public profile comparison would be
  the natural test seam.
- `LOWERING_FILES` (`semantic/pdf_lowering.py:33–64`) is a hand-kept list whose completeness no
  mechanism establishes (DA-068/069 family).
- No full run has passed since 2026-11-10, and source shows several tests cannot set up or pass;
  this is a qualification concern for the plan owner.

**Refinements to existing findings.** DTA-040: the directory is the execution workspace, so the
test-side defect is the missing recipe/binding distinction, not the choice of directory. DTA-047:
MAP_TEST counts seventeen modules that read production SQL by path, not about fourteen.
DTA-041: the certified helper's preparation bytes are not a valid report and its spool omits the
payload schema.

---

## 16. Architectural judgment and decision

| Judgment | Verdict | Scenario evidence | Required action |
|---|---|---|---|
| A1 Localize change | Violated | A pack change edits five modules; one protocol change broke seven copies and one test; a SQL retirement orphaned a reader | §4.3, §4.6, §5.1 |
| A2 Encode domain meaning explicitly | Violated, scoped | Recipe content and execution binding are not distinguished; preparation declarations live in lists; tests restate model facts or fabricate authority (DTA-033, 042, 045). Independent expectations across most of the suite are the strength to keep | §3, §4.1, §4.2 |
| A3 Extend through composition | Violated | A new PDF test copies a converter; a new preparation fixture edits two lists | §4.3, §4.5 |
| A4 Fit execution to the supported workload | Violated, bounded | Per-test PDF recipes seal unreusable seeds and retain them with their prepared kernels for the session; full capture per consumer; a database per expression check; one ordinary test contends for the host GPU lock. A credible route removes this work while keeping committed isolation where claims need it | §4.2, §4.7 |

**Bounded decision: Revise.** The 2026-11-13 architecture — keyed and verified heads, worker-local
sealed seeds, isolation by claim, refusal contract, independent expectations — is accepted as the
base. The rule of §3, the recipe and binding split, the head key's coverage, one controlled boundary
per external computation, perturbation tables and definition-site declarations are needed.
Evidence strength: Interface-checked source, one analysis of the snapshot, Measured durations read
from stored results; every remedy Proposed.

**Enclosing architecture:** the test system needs revision in the named areas; production is not
assessed beyond the seams in §4.8 and §15. Nothing here is release qualification.

**Next decision and owner.** The operator, in plan creation, decides RC07–RC10 and where the
findings are scheduled. The first step is restoring setup for the tests that source shows cannot
run, done once with the conversion's step 3 owner for the converter; the rule of §3 and the recipe
and binding split follow.

---

## Coordinator publication note — 2026-11-17

The coordinator, who wrote the audits this review consumes, prepared the brief, the pinned
snapshot and four contributor reports (a test audit delta, a production audit delta, a map of
test preparation and seams, and library research), and did not write the review. Before
placing it the coordinator checked nine cited sites against the snapshot (the Hypothesis
profile, capture custody and workspace, the deployment key's artifact component and function
skip, the kernel memo, the affinity conflict refusal, the native host startup comparison and
the GPU test); all matched. The review text above is the reviewer's, unedited.

**Reconciliation at publication.** `main` was at `23fa183e7`, 24 commits after the baseline
`1afa63f88`, with the SQL conversion continuing. In that range 18 test files and three scripts
changed. None of the sites this review's priority-one findings cite changed: the seven
uncertified converter copies, `tests/semantic/test_native_sql_body.py`, both conftest files and
`scripts/native_deployment_key.py` are as read. `scripts/pg_provision.sh` and
`scripts/pg_semantic_roles.sh` changed, which is the start of the provisioning move §4.8 adds
as a premise; that source was not read for this review. Uncommitted work was not read.
