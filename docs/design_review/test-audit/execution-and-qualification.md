# Execution and qualification

**Interface-checked by source inspection, 2026-11-12, and re-checked 2026-11-13** where a
finding says so. Baseline and limits are in the [account](README.md#baseline). The 2026-11-13
refresh ran no test; it read durations from stored `uv run ci test` results. Those figures are
labelled **Measured** with a run id, are collected under [Measurements](#measurements), and were
taken on a workstation shared with other sessions. A measured duration shows where time went.
Why it went there is established from source, and no speedup is measured anywhere on this page.

<a id="dta-024"></a>

## DTA-024 — Each xdist worker rebuilds the same sealed head deployment

**FP-06/07, DP-10/20; A4; H5/H12/H21; companion §6/8.** The frozen semantic deployment that
every database-backed test clones from is prepared once per pytest process, and the ordinary
route now starts one process per core whatever the selection.

`tests/conftest.py:255–260` defines `semantic_head_template` as a session fixture whose database
name embeds `os.getpid()`. `scripts/native_test_support.py:612–630` builds it by creating a
database from the server template, running Alembic `upgrade(conn)` to head and sealing it; the
chain currently holds 240 revisions. The session fixture `native_server` (`tests/conftest.py:
242–252`) additionally checks roles, sweeps leftovers and records server context per process.
Under xdist each worker is its own session, so each worker that receives a database-backed test
replays the whole migration chain to produce the same sealed template and drops it at session
end. Root `pyproject.toml:46–55` sets `-n auto --dist=loadgroup`; the managed ordinary lane
passes `auto` unless `--workers` is given (`scripts/test_receipts.py:1586–1593`), also for a
narrowed selection.

[ADR-0032](../../adr/0032-native-test-deployment-equivalence.md) owns this design. On 2026-10-29
it selected a session-local native template with fresh clones and explicit policy replay, and
rejected a persistent semantic template cache as unnecessary for that session-local contract.
Parallel workers arrived afterwards (2026-11-06), which turned one session per run into one
session per worker. The sealed head is a pure function of the migration chain and server
template, so the ADR's own validity premise for sharing holds across the workers of one run,
and the ADR names its revisit trigger as session preparation ceasing to fit the supported test
workload. The diagnosis is that the workload the decision was fitted to has changed under it:
a focused selection of a few native tests can now deploy the head once per participating
worker, and the only lever is the manual `--workers N`. That is unnecessary total server work
and contention established from source; workers prepare concurrently, so no added latency is
claimed, and how xdist distributes a small selection across workers was not observed. Nothing
here attributes the BEP-E05 memory interruption, whose cause remains unknown at its owner.

Counterevidence and limits. Clone-per-test from a sealed template is the right amortizer for
mutable native state and is preserved; fresh committed clones are essential to the many tests
that commit, seal or redefine functions (142 package test files mention `semantic_db_engine`).
Per-worker isolation is simple and safe. The older keyed `cs_tpl_` template cache was part of
the legacy test engine and was removed with it; it was not a rejected way of sharing the
semantic head ([DTA-030](retirement-transfer.md#dta-030)). A per-run shared template and a
narrower default worker count for narrowed selections are solution leads only; either reopens
the ownership and invalidation questions ADR-0032 deliberately avoided.

**Measured, 2026-11-13 — the premise about latency changes.** None of the files this finding
cites changed after the 2026-11-12 baseline, so the structure stands as written. Stored results
now put figures on it:

- In the full run `2e2a0e30…` the largest single setup on every one of the 16 workers is 48–95 s;
  a contributor's reading of the per-connection event files puts the head build itself at 47–55 s
  on each worker it could read.
- In the 442-test union `e332a3ef…` (6 workers) the largest setup per worker is 43–68 s, and the
  head build is the largest single item in that run's 670 s of setup.
- A focused run pays it before its first database test. Run `6a6894c8…` is one test on one
  worker: 104.5 s wall, 93.3 s of it setup. Among the last 60 passed narrowed runs, every run
  whose tests touch the database shows the same first-setup step on each participating worker.
- Worker count changes the wait. A contributor's reading of event timestamps gives 37–41 s from
  template creation to the next native event with one or two workers, and 87–92 s each when 16
  workers build at once (run `55303ce0…`). The coordinator did not recompute that gap; run
  `b8ccd2c7…` shows the same direction, with four workers each spending 105–107 s in their first
  storage-test setup against 57 s each with two workers in `780320d3…`.

The earlier text said no added latency was claimed because workers prepare concurrently. On
these receipts that no longer holds: concurrent builds slow each other, so a narrowed run on the
default worker count can wait longer than the same run on one worker. Two consequences follow
for anyone weighing remedies. Sharing one head per run and sizing workers to the selection
remove the duplication and the contention, and leave a floor of roughly 40 s for any run that
touches the database. Only reuse across runs removes that floor, which is the persistent
template cache ADR-0032 rejected. The semantic migration chain is about 250 revision files today and grows with
each native change, so the floor rises over time. ADR-0032's revisit trigger (session
preparation ceasing to fit the supported test workload) now has measured support; the decision
remains its owner's.

**Related, lower weight — maintenance connection lifecycle.** ADR-0032 establishes that
PostgreSQL clones omit database ACLs and database and role defaults, so capturing, replaying
and comparing policy for every clone (`scripts/native_test_support.py:306–371`) is required
work, not waste. What is incidental is how it is carried: `PgAdmin.connect()` (`:165–179`)
creates a `NullPool` engine, attaches observation and disposes it on every call, so one clone
acquisition (`:443–470`) opens and closes several maintenance connections for lease, existence,
creation, ownership, settings and policy reads. Some are inherently separate, because
role-self replay authenticates as another login (`:389–415`). This is a different cause from
the per-worker template and is recorded here only as an observation for whoever revisits the
ADR. Measured 2026-11-13 by a contributor from connection timestamps in `e332a3ef…`: creating a
test's clone takes about 0.2–0.7 s, nearly all of it `CREATE DATABASE`, and the other
maintenance connections including policy replay total about 0.02 s. Consolidating those
connections would tidy observation records and would not noticeably shorten a run.

<a id="dta-025"></a>

## DTA-025 — Rollback-only refusal families rebuild an identical committed scenario per case

**FP-06/07, DP-10/23; A4; H5/H12/H19; companion §6/8.** Many native refusal controls are
parametrized over forged or mutated inputs. Each case builds the full committed scenario on a
fresh clone and submits one mutated copy inside a savepoint or transaction that the database
refuses and rolls back; most then assert that nothing durable remained. The committed state
after the test is by construction the state before it, yet the next case rebuilds it.

Representative sites:

- `tests/semantic/test_private_records.py:131–176`: twelve forged-custody cases. Each requests
  function-scoped `private_source` (`tests/semantic/native_record_fixtures.py:791–819`), whose
  `build_record_source` (`:292–646`) persists a release, creates a run, registers a document,
  stores a PDF original, publishes the native record product, stores two source views and
  creates the task and claim in separate transactions. The test deep-copies one candidate,
  runs the positive control and the refusal in rolled-back savepoints, and asserts no
  `ops.task_result` or `kb.observation` row exists.
- `tests/semantic/test_runtime_bindings_native.py:100–148`: eight mutations. Each calls
  `prepare_operation_scenario` and `prepare_runtime_binding`, mutates a JSON copy and expects
  one refusal.
- `tests/semantic/test_local_semantic_admission_native.py:505–660`: ten corruptions, each after
  `private_source`, a completed relationship case, a finalized run, a reference set with three
  passes and two grades, a new run and `seal_cut`; the forged publication is rolled back and
  absence is asserted (`:637–660`).
- `tests/semantic/test_local_admission_native.py` (seven witness refusals),
  `tests/semantic/test_arrow_publication.py:456–493` (six) and
  `tests/semantic/test_contextual_enrichment_native.py:65–157` (thirteen).

Two families first listed here are not in this footprint as written (refined by the
[design review](../reviews/design_review_test-architecture-and-efficiency_2026-11-12.md),
2026-11-12, and confirmed in source). `tests/semantic/test_witnessed_applicability_native.py:172–197`
commits a new run, task and claim in each case before its refusal, so it is rollback-only only
if those rows move inside the rolled-back transaction.
`tests/semantic/test_structural_native_replay.py:147–217` gives each of its fourteen cases its
own source text through the committed source view (`:57–70`), so its scenarios genuinely differ.

**Changed footprint, 2026-11-13 — families that build the scenario inside the test body.** The
sites above request an expensive fixture, so their cost shows as setup. Four more families have
the same rollback-only shape and build the whole committed scenario in the test body, where it
is recorded as call time and is easy to mistake for the behavior under test:

| Family | Cases | Call time in `2e2a0e30…` |
|---|---|---|
| `tests/semantic/test_identity_exclusions_native.py:21–52` exclusion tampering; each case calls `exclusion_result` and then refuses inside a `SERIALIZABLE` transaction (`:205–220`) | 18 | 477 s |
| `tests/semantic/test_imported_declaration_membership.py:231–291` imported membership lineage | 6, one of which commits | 253 s |
| `tests/semantic/test_occurrence_context.py:143–199` fabricated or omitted context | 8 | 205 s |
| `tests/semantic/test_domain_operations.py:867–992` declared membership lineage | 6, one of which commits | 144 s |

Together these are about 1,080 worker-seconds of call time (Measured, run `2e2a0e30…`; the
shape is Interface-checked 2026-11-13, the coordinator having read the first and third family
and a contributor all four). For scale, the families already listed above measure as follows in
the same run: forged judged rows in `test_local_semantic_admission_native.py`, ten cases, 471 s
of setup; `test_contextual_enrichment_native.py` atomic refusal, thirteen cases, 280 s;
forged custody in `test_private_records.py`, twelve cases, 226 s. A contributor's split of a
warm `private_source` setup gives about 10–11 s, of which the clone is about 0.25 s and pure
preparation about 1 s; the rest builds the committed scenario. So the repeated cost is the
committed build, not the clone.

More generally, `tests/semantic/test_domain_operations.py` calls `build_domain_case` in the body
of 22 tests (`tests/semantic/domain_scenarios.py:65`), and in the 442-test union `e332a3ef…` that
file is the largest single cost: 864 s of call time over 35 tests, with a contributor reporting
a flat median of 27 s per test. Most of those tests commit and consolidate, so they are not in
this rollback-only footprint; they are the F03 shape in the
[design review](../reviews/design_review_test-architecture-and-efficiency_2026-11-12.md)
(identical committed scenarios rebuilt through producers) and are noted here because the cost
is otherwise invisible to a reading of setup times.

Pure native-function checks show the same shape at smaller scale:
`tests/semantic/test_local_semantic_admission.py:121–147` gives seventeen parametrized JSON cases
of one SQL function a clone each, and `tests/semantic/test_contextual_workflow_native.py:29–87,
104–135` does the same for ten literal-argument calls; neither writes state. The package
already offers a rollback connection on a shared session clone for exactly this kind of check
(`db`, `tests/conftest.py:280–291`).

Release preparation itself is not the repeated cost: `prepare_release` memoizes hashable inputs
(`src/corpus_structure/semantic/prepare.py:544–580`, `lru_cache(maxsize=8)`), and
`PreparedRelease` is frozen. What repeats is the clone with its policy replay
([DTA-024](#dta-024)), persistence, native publication and task setup, plus input assembly and
hashing ahead of the cache lookup. The repository already contains the contrasting design:
`tests/semantic/serving_scenarios.py:218–344` builds one session-scoped sealed seed, validates
its identity, policy and recipe, and clones it per test.

Counterevidence. Tests that complete, seal, consolidate or commit need fresh state and are not
in this footprint. The positive control inside each refusal test is valuable and depends on
real committed state. Sharing has real validity premises to establish: `case` objects are
mutable namespaces and some tests assign to them; a claimed task holds a five-minute lease
taken from the server clock (`src/corpus_structure/semantic/sql/execution_projection.sql:86,103`),
which matters only for refused operations that reach a lease-checking guard, since
`ops.complete_task` refuses on status, attempt, holder and sealed run rather than lease expiry
(`src/corpus_structure/semantic/sql/native_task_completion.sql:15–16`); and whether every helper in these
families is read-only on the committed database was not verified for all sites. Under
`--dist=loadgroup` without a group mark, the cases of one family spread across workers, so
any shared scenario is still per worker and its benefit is bounded by [DTA-024](#dta-024). The
diagnosis is the mismatch between a rollback-only claim and a per-case committed rebuild, not
that fixtures are function-scoped in general.

<a id="dta-018"></a>

## DTA-018 — Focused controls construct scenario preparation they do not use

**FP-03/06/07, DP-10/23; A4; H5/H6/H12; companion §8.** The two manifestations recorded on
2026-11-05 are corrected in source. `tests/math/conftest.py:25–61` now stages session fixtures
by consumer (`spike_content` → `spike_readings` → `spike_extraction` → `spike_scoped`);
`tests/math/test_property.py:92` and `tests/math/test_spans.py:158` request only the stage they
read, and `tests/math/test_workers.py` asserts that coverage and early stages omit downstream
work. The schema/projection control in `tests/semantic/test_private_records.py:266` now takes
`private_preparation` rather than the full native scenario.

The same cause has current manifestations elsewhere:

- `tests/evaluate/test_record_policy_native.py:15–47` and the test at `:49` request
  `private_source` but use it only for candidate identifiers and `prepared.release_id`, then
  call `eval.record_policy_full_correct`. That function
  (`src/corpus_structure/semantic/sql/record_policy.sql:103–131`) reads its arguments and one
  `sem.artifact` row of the release; no run, task, source view, PDF or claim is consulted. The
  second test describes itself as comparison mechanics only.
- `tests/semantic/test_cli_failures.py:228–239` builds `build_resubmission_case` — a composed
  release, controlled PDF views, a run, a queued agent task and real primary, formal and
  construction producers — and keeps only the prepared release for a `db check` diagnostic.
- Provider opt-in tests decide to skip inside the body after fixtures have built a clone,
  release, PDF and published source: `tests/semantic/test_characterization_native.py:1727–1729`
  and `:2112–2114`, `tests/semantic/test_native_documents.py:93,97`,
  `tests/semantic/test_pdf_json_publication.py:211`. `tests/semantic/test_pm2_parser_stage_native.py:42–44`
  shows the marker form that skips before preparation.
- `tests/ingest/test_pdf_recognition.py:381–417` replaces the recognition call and starts no
  parser, but obtains its owner through a helper that skips when the isolated parser environment
  is absent (`:166–172`), so a scheduling control loses coverage for an unrelated prerequisite.

Added 2026-11-13:

- `tests/semantic/test_release_compatibility.py:91–123` needs a second database to show that the
  release read cache is scoped per database. It obtains one through `semantic_database_at("head")`,
  which creates a database from the bare server template and replays the whole migration chain
  (`tests/semantic/conftest.py:48–57`). A second clone of the sealed head would be the same
  deployment. The test's call phase is 43.5 s in `2e2a0e30…` (Measured, reported by a
  contributor). The other users of `semantic_database_at` target real historical revisions and
  need the replay.
- The declared-data-operations kernel has its own instances, recorded under
  [DTA-031](#dta-031).

These consumers inherit the cost and the failure coupling of preparation their claim does not
observe. Integrated siblings need the complete scenarios, and shared realistic setup avoids
divergent stand-ins; the concern is these focused consumers only. The 32 other
`build_resubmission_case` and 44 `prepare_operation_scenario` call sites were not individually
assessed.

<a id="dta-026"></a>

## DTA-026 — CPU teardown controls wait out production grace periods and reach into executor internals

**FP-02/06/07, DP-23; A1/A4; companion §5/6/8.** `tests/semantic/test_cpu_lifecycle.py` proves
close, kill and admission behavior against real spawned children that ignore termination, exit
abruptly or hold locks. That fidelity is valuable. Two structural costs come with how it is
obtained.

The production grace constants are module attributes read at call time
(`src/corpus_structure/semantic/cpu_execution.py:456–457`, five seconds each; used at
`:545,819–820,879`). The tests assert wall-clock windows that restate them:
`4.5 <= elapsed < 12` (`:78`) and `9.5 <= … < 12` (`:376`), with upper bounds of twelve seconds
at `:161,282`. Those tests wait out the real grace period serially. The literals couple the
tests to the current values: lowering a constant fails them, while raising one within the
upper bound weakens the lower-bound check without a failure. The `< 1` bounds at `:355,367`
are different and sound; they assert that logical cancellation does not wait. The tests already
monkeypatch the same module for the executor, so the wait length is a choice rather than a
requirement of the claim that grace is honoured before a kill. The BEP plan fixes five seconds
as the selected policy, so one control at the real value may be deliberate, and shortening
grace for real spawned children has its own flakiness trade-off.

`test_close_unblocks_third_submission_behind_broken_pool_lock` (`:201–305`) and its siblings
construct their interleavings by writing CPython `ProcessPoolExecutor` private state:
`_initargs`, `_initializer`, `_executor_manager_thread_wakeup`, `_broken`, `_shutdown_lock` and
`_executor_manager_thread` (`:92–94,144–145,208–209,261–265,326–327`). The protected contract is the scope's
close behavior; the observation depends on one interpreter's executor implementation. The
interpreter is pinned, which bounds the exposure. Production's own pool-ownership adapter also
depends on executor internals and says so (`cpu_execution.py:461–467,508–513`), so the
test-specific part of this concern is the writing of private attributes to inject an
initializer, for which the module's factory seam already exists (`:62–68` uses it). A toolchain
move would break these
controls for reasons unrelated to the product.

A suspected, unobserved weakness: `test_packet_limit_and_real_inflight_cancellation_…`
(`tests/semantic/test_cpu_execution.py:110–139`) cancels on the third `check_active` call.
`execute` polls at 0.1 s (`cpu_execution.py:802–807`), so cancellation can arrive before a
freshly spawned worker has begun the request. The test would fail if the request completed
first, so it establishes cancellation before completion, not cancellation of work in flight
as its name says. Sibling tests in the same module gate the worker with manager events to
establish that; this one does not. Strengths to
preserve: `_assert_retired` checks no live process, a dead manager, zero budget and closed
admission, and the lock tests assert credits at kill and exact exception-group content.

Checked 2026-11-13 and not added to this finding: the four `time.sleep(1.05)` waits in
`tests/semantic/test_data_operation_storage.py:468,549,1280,1729`. Production takes
`lease_seconds` as a whole number of at least one and compares expiry with `clock_timestamp()`
(`src/corpus_structure/semantic/sql/data_operations.sql:734–780`), so a real expiry needs a real
second. The waits total about four seconds and are the claim. The observation that there is no
time seam is production's, and the cost is small.

<a id="dta-031"></a>

## DTA-031 — Declared-data-operation native tests rebuild one identical admitted kernel per case

**FP-06/07, DP-10/23; A4; H5/H6/H12/H19; companion §2/6/8. Interface-checked by source
inspection, 2026-11-13; durations Measured, runs named.** The native tests of the
declared-data-operations work default to the most expensive preparation available, whatever the
case needs.

`kernel` (`tests/semantic/test_data_operation_storage.py:170–252`) is function-scoped. For
every case it writes the same schema, declarations and target file to `tmp_path`, runs
`prepare_data_operation_inputs`, `bound_data_operation_model` and
`prepare_data_operation_runtime`, and then in one transaction persists the release, admits it
through the real `admit_data_operation_release`, persists the runtime binding and inserts one
project row (`:223–232`). Nothing in that state depends on the case: it holds no claim, lease or
clock value. It sits on `ddo_kernel_engine` (`:162–168`), a fresh clone per test. About sixty
cases in this module use it; `tests/semantic/test_data_operation_service.py` and
`tests/semantic/test_data_operation_population_native.py` import it, and the population module
and `tests/orchestrate/test_data_operation_execution.py` each write out the same
persist–admit–bind sequence again in their own fixtures (`test_data_operation_population_native.py:137–151`,
`orchestrate/test_data_operation_execution.py:76–80`).

Measured: in `e332a3ef…` the storage module's 26 tests spend 416 s in setup and 44 s in their
bodies. A contributor's split of one warm case gives about 0.65 s for the clone, about 3.4 s of
Python before the first write and about 8 s inside the persist-and-admit transaction, for a body
of about 1 s. `test_data_operation_binding_native.py` spends 181 s of setup for eight tests with
no measurable call time, and `test_data_operation_identity_native.py` 44 s for one; both figures
include a worker's first head build ([DTA-024](#dta-024)).

Three kinds of consumer are treated alike:

- **Tests that need fresh committed state.** Most of the module: attach, claim, retain and
  publish commit in separate transactions, and the concurrency, visibility and purpose-principal
  controls need real sessions (`:427–449`, `:1822`, `:1862`, `:1898`). A fresh database per case
  is the claim here. What these cases do not need is to produce the kernel again; it is the same
  committed state every time.
- **Rollback-only refusal families.** Invalid output (`:610`), fence renewal (`:1266`) and forged
  graph (`:1972`), four cases each, rebuild the kernel and then refuse. Each still commits an
  attach or claim first, the caveat recorded for witnessed applicability under
  [DTA-025](#dta-025).
- **Checks that write nothing.** `:738` takes the full kernel to call `data.ddo_normalize`.
  `:2150–2177` clones to call `data.ddo_json_meaning`. `binding_native_connection`
  (`tests/semantic/test_data_operation_binding_native.py:42–72`, also used by the parameter and
  population-selection modules) and both identity-native tests take a clone to run function
  definitions and calls inside a transaction they roll back. The shared rollback connection `db`
  (`tests/conftest.py:280–291`) exists for this; nine test files use it and 155 use clone
  fixtures. The per-case saving here is under a second; the weight is that these checks do not
  say they write nothing, and each still triggers a head build on whichever worker receives it.

The plan does not help the tests choose. The contracts companion says native checks use the
working database and need no disposable database
(`docs/plans/declared-data-operations/contracts-and-compilation.md:359–361`), while the
coordinator records isolated test databases and a working database that is behind the head. The
code follows the coordinator. With no stated line between "needs a fresh admitted kernel" and
"reads installed functions", every native check takes the former. That inconsistency is the
plan owner's to settle; it is listed in the [account](README.md#observations-for-the-ddo-plan).

Lineage and counterevidence. The cause is the one the design review named F03 and this account
names [DTA-025](#dta-025): identical committed scenarios rebuilt per consumer. It has its own
identity here because the review predates these tests and the footprint is the fastest-growing
part of the suite. `tests/semantic/serving_scenarios.py:218–344` already shows the contrasting
shape, a sealed seed that is validated once and cloned per test. Whether a seed of the kernel
is valid to share rests on premises not all checked here: the contributor could not split the
eight-second transaction between release persistence, catalog verification and runtime binding,
and whether `prepare_data_operation_inputs` is memoized was not established. A sealed kernel
seed is a solution lead only.

<a id="dta-032"></a>

## DTA-032 — Standalone interpretation contexts recompute implementation determinants on every call

**FP-07, DP-10; A4; H12/H14/H26; companion §8. Interface-checked by source inspection,
2026-11-13; the share of test time it explains is suspected, not measured.** The cause is in
production and is reported here because tests are where it is paid most often.

`grammar.parse` prepares an interpretation context whenever the caller passes none, and does so
before it consults its memo (`src/corpus_structure/methods/math/grammar.py:982–992`), so a memo
hit pays for the context too. `prepare_interpretation_context`
(`src/corpus_structure/semantic/analysis_contracts.py:638–659`) always calls `_analysis_runtime`
(`:472–485`) and, with no release, `_standalone_model` (`:409–412`), which compiles the execution
model from `trusted_execution_inputs()`. A contributor traced that path to an uncached read of
about a hundred package files, distribution version lookups and a pure-Python parse of the
physical model's YAML closure (`src/corpus_structure/semantic/contracts.py:1180–1300`,
`src/corpus_structure/schema/physical.py:28–52`); the coordinator read the call chain and not the
bodies of those two functions.

In tests, `tests/math/test_property.py:120–132` calls `G.parse(latex, "any_value", macros)` once
per generated example with no context, 300 examples under the profile that managed runs select,
and the grammar tests call it through a helper in the same way. Measured in `2e2a0e30…`:
`test_generated_layer` takes 198 s, about 0.66 s per example. That one property is most of the
time spent in Hypothesis tests, which is why the example count is not the first thing to look
at. The inputs are fixed for the life of the process, so the preparation is stable work repeated
per call.

**Refined by the [design review](../reviews/design_review_test-system-target-design_2026-11-13.md),
2026-11-13, and confirmed by the coordinator.** The footprint is wider than the standalone
route. With a prepared release, `_profile` still compares the model's digests with
`_semantic_implementation_digests()`, which calls `trusted_execution_inputs()`, and
`_analysis_runtime` calls `analysis_implementation_inputs()`
(`src/corpus_structure/semantic/analysis_contracts.py:454–485`); neither is cached, so every
interpretation context re-reads the determinants at least twice. `trusted_execution_inputs`
documents the intended lifetime as one read at an application entry boundary
(`src/corpus_structure/semantic/contracts.py:1166–1169`). A contributor's reading puts
production callers inside per-span and per-item loops (`methods/math/source_context.py:238`,
`methods/math/native.py:285,948,1261`); that production consequence is noted for the broad audit
and not assessed here.

Uncertainty. Nothing was profiled. That context preparation dominates the 0.66 s is a reading of
source; the generated formulas also do real parsing. Whether the same path inflates the 352 s
`test_coverage_beside_s5` or the staged-worker controls was not traced. Production callers that
compose a prepared projection pass their own context and do not take this path, so the
production cost may be small; the adapter's own comment describes the standalone route as the
explicit trusted base profile.

<a id="dta-002"></a>

## DTA-002 — Interrupted shared authentication effects have an owned recovery path

**FP-05/07, DP-19/20/21; companion §6/8.** Still holds as written. Root
`tests/scripts/test_native_auth.py` keeps independent fake-state controls, a real `flock`
subprocess and opt-in native crash controls gated on `CORPUS_TEST_NATIVE_AUTH_CRASH`; the
ordinary lane deselects them by marker and a skip becomes `blocked`, not success
(`scripts/test_receipts.py:480–482`). Lines 700–1084 were not reread this refresh. Existence of
the controls is not a fresh run.

<a id="dta-003"></a>

## DTA-003 — Acquired identity is corrected; deployment completeness remains consumer-specific

**FP-05/06, DP-21/22; companion §6.** Holds with moved locations. Provenance is still marked
complete while `deployment_status` may be unavailable (`scripts/native_test_support.py:747–752`);
the classifier and its tests now state that explicitly (`scripts/test_receipts.py:492–540`, root
`tests/scripts/test_test_receipts.py:600–640,904`). Item-bound maintenance connections made
during fixture setup count as acquisition, so "complete" attests acquisition for the item, which
matches the marker's meaning. Revisit when a qualification consumer relies on the flag for full
deployment or policy reproducibility. No incorrect qualification is established.

<a id="dta-017"></a>

## DTA-017 — The default application target refuses accidental acquisition

**FP-02/05/06, DP-19/20; companion §5/6.** Holds; locations moved. The autouse fence is
`tests/conftest.py:189–200` with its sentinel at `:60–63`; the control is
`tests/test_semantic_runtime_settings.py:117–139`. The root `tests/` tree has no equivalent
fence; no misrouted write is inferred from that.

<a id="measurements"></a>

## Qualification limits

The 2026-11-05 limit is corrected: `classify_rust` now applies the shared group-cleanup check
and downgrades to `incomplete` with no functional coverage (`scripts/test_receipts.py:893–903`),
with a control at root `tests/scripts/test_test_receipts.py:775–794`. The empty Rust selection
still establishes no functional coverage.

## Measurements

**Measured, 2026-11-13, from stored results; no test was run.** Method, conditions and the full
tables are in the [evidence folder](../evidence/2026-11-13_test-audit-refresh/README.md). The
workstation was shared with other sessions during every run read, so these are ordinary
development conditions and not a benchmark.

Full run `2e2a0e30…` (2026-11-10, 16 workers, 6,025 tests; predates the declared-data-operations
tests):

- 1,503 s wall. Workers are busy for 96% of the span of test phases, so the full run is bound by
  total work. Rebalancing tests across workers would recover at most the last minute, where one
  worker finishes 31–67 s after the others.
- Setup is 36% of worker time (7,833 of 21,977 worker-seconds), call 61%, teardown 3%.
- Setup is concentrated in few tests: 4,922 tests set up in under 0.05 s, while 335 tests with a
  setup over 5 s account for 7,425 s.
- `tests/semantic/` holds 75% of worker time.
- Collection costs about 30 s before the first test phase on 16 workers, and 16 s pass between
  the last phase and process exit. The fault lane adds about 27 s and the empty Rust workspace
  under a second.

Narrowed runs (the last 60 that passed, 2026-11-12 and 13):

- A run has about 7.5 s of fixed overhead at the median (4.9–17.3 s), split roughly evenly between
  startup and collection before the first phase and reporting after the last. A contributor
  observed the tail after the last worker finishes varying from 2 to 11 s, close to xdist's
  ten-second gateway timeout in one run; its cause was not established.
- A run that touches the database adds the head build on each participating worker
  ([DTA-024](#dta-024)).

The 442-test union `e332a3ef…` (2026-11-13, 6 workers): 504 s wall. Three files tied to
machinery the declared-data-operations plan removes take 41% of its worker time, almost all of
it `test_domain_operations.py`; the `test_data_operation_*.py` files take 29%, of which 85% is
setup.

Inspected with no shortfall established, 2026-11-13: the one-second sleeps in
`tests/math/test_grammar.py` and `tests/math/test_stages.py` are interrupted by sub-second
deadlines; the long child sleeps end on an event or a kill; the database drop retry waits only
on SQLSTATE 55006 for at most two seconds; `ci test retry` reruns unresolved identities only, so
a failed union need not be repeated whole; the fault lane is serial by design. No ADR or skill
adopts or rejects selecting tests by changed path. The identities under test depend on SQL, YAML
and about a hundred implementation files beyond Python imports, so an automatic selection would
need a complete dependency key to be safe; no shortfall is asserted.

<a id="dta-021"></a>

## DTA-021 — Fixture self-tests no longer depend on another test

**FP-05/06, DP-23; companion §4/6.** Corrected in source. `tests/test_db_fixtures.py:35–54` is
one parametrized test that performs the write, observes it inside the transaction and checks
absence through a fresh connection, for both normal and exceptional exit; `:57–66` is
self-contained with no module global. The former cross-test evidence dependency is gone. The
earlier diagnosis is recoverable in Git under this identity.

<a id="dta-022"></a>

## DTA-022 — Native observation now returns before work when no receipt consumer is live

**FP-06/07, DP-10/14/21; A4; companion §8.** Corrected in source. `observe_connection`
(`scripts/native_test_support.py:677–688`) asks the plugin for a live sink before any query,
hash or rollback; `database()` skips its extra checkout on the same predicate (`:463–468`);
`scripts/qualification_plugin.py:37–39` supplies it. Root
`tests/scripts/test_test_receipts.py:797–831` forbids cursor, hash and connect calls without a
sink; that control covers `observe_connection` and the server-context record, not the skipped
checkout in `database()`. Observation per physical connection remains in receipt-enabled runs
by design.
