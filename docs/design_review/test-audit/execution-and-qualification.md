# Execution and qualification

**Interface-checked by source inspection, 2026-11-12, and re-checked 2026-11-13 and 2026-11-17** where a
finding says so. Baseline and limits are in the [account](README.md#baseline). The 2026-11-13
refresh ran no test; it read durations from stored `uv run ci test` results. Those figures are
labelled **Measured** with a run id, are collected under [Measurements](#measurements), and were
taken on a workstation shared with other sessions. A measured duration shows where time went.
Why it went there is established from source, and no speedup is measured anywhere on this page.

<a id="refresh-2026-11-17-execution"></a>

## Refresh of 2026-11-17

**Interface-checked by source inspection, 2026-11-17**, source `fbd3f2a98`
([baseline](README.md#baseline)). The findings in this section are new. Each earlier finding
below carries a dated status line. Durations are **Measured** only where a stored run id is
given ([Measurements](#measurements)); everything else is unnecessary work established by
structure. How these relate to the production account is on the
[joint page](../audit/model-and-execution.md).

| Earlier finding | Status at `fbd3f2a98` |
|---|---|
| DTA-024 | Corrected. Residuals are DTA-038 and DTA-039 |
| DTA-025 | No longer applicable at the cited sites; the data-operation footprint moved to shared rollback bases |
| DTA-018 | No longer applicable at the cited sites; no new oversized consumer established |
| DTA-026 | Changed footprint |
| DTA-031 | Corrected. The residue is DTA-047 |
| DTA-032 | Corrected by a different mechanism than the plan records |
| DTA-002, 003, 017 | Stand (configuration read only) |
| DTA-021, 022 | Corrections stand |

<a id="dta-040"></a>

### DTA-040 — A per-test directory is part of PDF scenario identity, so seed and preparation reuse does not hit

**FP-04 (DP-04), FP-07/A4; DP-09, DP-10; H12, H14; companion §6, §8.**

The scenario-seed registry and the prepared-kernel cache both key on the recipe value
(`scripts/native_scenario_seeds.py:203–209`; `tests/semantic/data_operation_kernel_support.py:161`).
For PDF source scenarios the recipe is built by `current_pdf_recipe(directory)`, which calls
production `pdf_capture_custody`. That writes the resolved asset root and the resolved capture
directory into the `pdf-capture/execution-custody` artifact
(`src/corpus_structure/semantic/pdf_capture.py:86–99`), which becomes part of the recipe's
captured dependencies. The fixtures pass the per-test `tmp_path`
(`tests/semantic/current_pdf_source_support.py:286`, `current_pdf_integration_support.py:247`,
`pdf_staging_support.py:347`, `rich_domain_native_support.py:88`,
`tests/evaluate/declared_record_native_support.py:508`). Nothing normalizes the paths.

**Consequence.** Every such test has a recipe no other test shares, so:

- each seeded scenario clones the head, runs a full uncached release preparation, admits,
  seals and clones again, and the sealed seed stays registered until the session closes
  (`native_scenario_seeds.py:272–273, 347–353`): one extra sealed database per test for the
  rest of that worker's session;
- direct `prepare_kernel(recipe)` callers with per-test recipes miss the unbounded
  prepared-kernel cache every time, and the cache still keeps each prepared release, model,
  runtime and temporary directory for the worker's lifetime
  (`tests/semantic/test_pdf_transform_operations.py:278–279, 335`;
  `test_current_pdf_source_inputs.py:13–15`;
  `tests/evaluate/test_declared_record_native_journey.py:26–29`;
  `test_declared_rich_native_journey.py:31`). The seed path does not use that cache: it
  prepares into a supplied directory, uncached by design;
- production's own preparation cache (eight entries) misses as well. For the roughly fifteen
  `admit_current_target(…, recipe(tmp_path / "recipe"), …)` consumers, which admit into an
  existing clone and create no seed, this is the only cost.

The release identity under test also includes a directory that changes nothing about the
operations being tested.

**Contrary evidence.** The mechanism works when the recipe is stable: the module-scoped recipe
in `tests/semantic/characterization_native_support.py:86–88` is reused within its module, and
`declared_scenarios.py:200–208` seeds once per session. Production may have a reason to bind
the capture directory into custody; whether the directory belongs in release identity is a
question for the production owner. The test-side defect is choosing a per-test directory.

**Footprint.** Established for the keying and the retention; the number of databases that
accumulate was not counted.

<a id="dta-038"></a>

### DTA-038 — The deployment key cannot see imports made by executed upgrade bodies, and includes much that a deployment does not depend on

**Delta, 2026-11-17, source `1afa63f88`.** Stands; revisions `semantic_ddo_pe_n3` and `_n4` have the same shape ([delta](README.md#delta-1afa63f88)).

**FP-04/FP-05, FP-07/A4; DP-10, DP-20; companion §6, §8.**

The reusable head database is keyed by `deployment_key()`. Its module component is a walk over
import statements, outside function bodies, starting from every migration `.py` file
(`scripts/native_deployment_key.py:126–142`).

*What it misses.* The declared-data-operations revisions do not run their DDL in the `.py`
file. They read a hash-pinned `*_upgrade.txt` body and `exec` it. Those bodies enter the key as
artifacts, by size and mtime only (`:130, 146–148`), so their imports are never walked. Twenty
of them import `corpus_structure.semantic.alembic_privileges` at module level; the matching
`.py` files import it only inside `upgrade()`, which the walk skips by design
(`semantic_alembic/versions/semantic_ddo_domain_v9.py:41–42`). Running the snapshot's own
closure function gives 25 package modules, and `alembic_privileges` (which executes grant and
revoke admission) is not among them.

*What it over-includes.* The whole `uv.lock`, the interpreter version, artifact mtimes rather
than the content digests the revisions already pin, and incidental modules in the closure.
Unrelated edits to any of these rebuild the head.

**Consequence.** An edit to `alembic_privileges.py` that changes the privileges a build produces
leaves the key unchanged, and narrowed runs reuse a head built by the old code. First-use
verification bounds this: the head's catalog checks include table, function and schema
privilege predicates and per-actor read checks against the descriptor, and a failure retires
the head (`src/corpus_structure/semantic/execution_admission.py:81–118`). The exposure is
whatever privilege admission produces outside those predicates, and a reused head passing
narrowed runs where a fresh qualification build would differ.

**This is a gap the plan accepted in kind.** The plan chose a narrow key plus verification and
explicitly declined to follow imports inside functions, on the ground that the key "does not
have to be provably complete"
(`docs/plans/test-system-target-design/native-lifecycle-and-deployment.md:295–296`). What it
did not anticipate is the executed body: there the import is at module level, in a file the
walk treats as an opaque artifact.

**Footprint.** The omission is established by source and by running the closure function over
the snapshot. That a stale head has survived verification was not established.

<a id="dta-039"></a>

### DTA-039 — A key miss replays the whole migration chain, and sealed state is re-verified at several boundaries

**FP-07/A4; DP-10, DP-23; H5, H12, H21; companion §8.**

On any key change `_publish_deployment` builds from the server template and replays all 285
revisions (`scripts/native_test_support.py:995–1057`; `scripts/native_deployment_build.py:11–19`),
even when the change is one appended revision and the predecessor head is still retained (three
are kept). The revision graph is linear and every frozen artifact is digest-pinned in its
revision, so the delta is named by data the system already holds. The plan's options compared
key breadths only.

Smaller repetitions of the same kind, each over state that cannot have changed:

- every worker of a narrowed run re-verifies the same sealed head and re-walks the chain to
  compute the same key (`native_test_support.py:366–384, 896–930`);
- the role script is spawned twice per process (`:901, 932–935`);
- the policy is compared twice per clone (`:650–654, 760–762`);
- every seed hit re-validates ownership, policy and drained sessions on new connections
  (`native_scenario_seeds.py:206–209, 277–301`).

**Contrary evidence and what to keep.** A build from base is the strongest equivalence claim,
and qualification runs already build private heads fresh; the cold chain controls keep real
coverage. Per-process verification is a deliberate trust premise and per-clone policy replay is
required (ADR-0032). Only the doubled comparison and doubled subprocess are pure repetition.
The plan's own figure for a head build is about 40 s; it was not re-measured.

**Footprint.** The structure is established. Whether an incremental head is worth its validity
conditions is open.

<a id="dta-047"></a>

### DTA-047 — Pure SQL-expression checks create a database per case and execute production SQL spliced by string offsets

**Delta, 2026-11-17, source `1afa63f88`.** Changed footprint. Three tests now take their SQL from the generator instead of a deleted file. One site is stale: `tests/semantic/test_native_sql_body.py:200–216` still reads `execution_projection_check.sql`, deleted in `708c119a6`. About fourteen test modules still read hand-written production SQL by file path, so each further retirement can orphan a reader ([delta](README.md#delta-1afa63f88)).

**FP-02, FP-07/A4; DP-23; H5, H12; companion §5, §6, §8.** Residue of DTA-031.

`semantic_bare_engine` creates a new database for each test; its stated purpose is bootstrap
and upgrade obligations (`tests/native_fixture_support.py:1–5, 29–38`). Several checks that
need one session with temporary functions in a rolled-back transaction use it:
`tests/semantic/test_data_operation_trust_snapshot_sql.py:17–31` (19 cases),
`test_data_operation_retirement_context_sql.py:21, 102, 144`,
`test_data_operation_null_scope.py:14, 31`, and `cpu_basis_connection`
(`test_data_operation_cpu_basis.py:61–90`), which builds a six-table schema by hand without
foreign keys and is imported by three other modules.

Several of them find production SQL by literal string offsets and execute the slice
(`test_data_operation_trust_snapshot_sql.py:52–62, 126–131`;
`test_data_operation_retirement_context_sql.py:31–41`;
`test_data_operation_identity_native.py:121–124`).

**Consequence.** A database is created per case for checks that write nothing. A
behavior-preserving reformat of the SQL breaks the tests (loudly). And the subject is a
re-spliced fragment on a substitute table, so a test named `_native`, such as
`test_established_validity_native.py:25–123`, runs without the installed function, triggers,
keys or grants: a defect outside the slice, or in how deployment installs it, is invisible.

**Contrary evidence.** These checks test production's own expression text, not a copy, and are
cheap to write. An existing alternative is the rollback-family seed in
`tests/semantic/data_operation_binding_support.py:86–120`. Across the package 35 files use the
bare engine; those outside the data-operation tests were not examined.

<a id="dta-048"></a>

### DTA-048 — One ordinary-lane control takes the operator's real host-wide GPU lock

**FP-06, FP-07; companion §6, §8.**

`test_residency_hands_off_actual_gpu_capacity_and_restarts_real_host`
(`tests/methods/test_native_host.py:716–752`) calls the real `pdf_gpu_slot`, which locks
`/tmp/corpus-structure-pdf-gpu-<uid>.lock`, the lock real PDF captures hold, and polls with a
two-second deadline (`src/corpus_structure/ingest/pdf_capacity.py:51–64`). Every other test
replaces the slot or stubs the lock calls.

**Consequence.** If the suite runs while a book is being captured, which is ordinary for this
workload, the test fails with a message that blames a previous NLP group.

The claim under test, that handoff retires the NLP group before the slot is taken, is genuine.
One site, established.

## Earlier findings

<a id="dta-024"></a>

## DTA-024 — Corrected: the head deployment is keyed and reused across workers and runs

**Corrected (2026-11-17, source `fbd3f2a98`).** The per-process head is gone. Narrowed runs reuse a head database keyed by `deployment_key()` and verified before first use; a qualification run builds one run-private head shared by its workers (`scripts/native_test_support.py:298–313, 937–965`). What remains is the key's coverage ([DTA-038](#dta-038)) and the cost of a key miss ([DTA-039](#dta-039)). The 2026-11-12 and 2026-11-13 text and measurements are in Git at `fbd3f2a98`.

<a id="dta-025"></a>

## DTA-025 — No longer applicable at the cited sites

**No longer applicable (2026-11-17, source `fbd3f2a98`).** The cited modules were deleted. Rollback-only families now share one worker clone under `rollback_family` (`scripts/native_scenario_seeds.py:322–351`), and the forged-graph family moved there (`tests/semantic/test_data_operation_storage.py:2457–2539`). Families that still clone per case commit an attach or claim first, which justifies it. One premise to record, not a finding: shared rollback bases do not stop maintenance connections from advancing sequences, so generated identifiers can depend on case order; no test read asserts literal generated ids there. Earlier text is in Git at `fbd3f2a98`.

<a id="dta-018"></a>

## DTA-018 — No longer applicable at the cited sites

**No longer applicable (2026-11-17, source `fbd3f2a98`).** `build_resubmission_case`, `prepare_operation_scenario` and the cited consumers are gone; `tests/semantic/test_release_compatibility.py:101–118` now uses a committed clone of a seed. No new focused consumer of an oversized scenario was established. Two related observations have their own homes: per-test recipes defeat reuse ([DTA-040](#dta-040)), and `current_pdf_source_factory`, a function-scoped fixture that commits a clone, registers and runs a demand per call, is used by 23 test functions in 17 files (`tests/semantic/current_pdf_source_support.py:350–366`), some of whose subjects need no source run. Earlier text is in Git at `fbd3f2a98`.

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

**Status, 2026-11-17, source `fbd3f2a98`.** Changed footprint. Grace periods are injected short with a separate check of the production value (`tests/semantic/test_cpu_lifecycle.py:24–26, 50–51`). The executor class is replaced by patching the module attribute; production has no factory parameter. One test still drives private executor state (`:298–305`).

<a id="dta-031"></a>

## DTA-031 — Corrected: data-operation native tests clone a sealed kernel seed

**Corrected (2026-11-17, source `fbd3f2a98`).** `ddo_kernel` clones a per-worker sealed seed (`tests/semantic/data_operation_kernel_support.py:288–306`); binding checks use a rollback family; identity and JSON checks use read or rollback connections. Residue: expression checks that still create a database per case ([DTA-047](#dta-047)), and per-worker seed builds without affinity ([DTA-037](retirement-transfer.md#dta-037)). Earlier text is in Git at `fbd3f2a98`.

<a id="dta-032"></a>

## DTA-032 — Corrected by a different mechanism than the plan records

**Corrected (2026-11-17, source `fbd3f2a98`).** The standalone interpretation context is now memoized per macro table and kind (`src/corpus_structure/methods/math/grammar.py:983–993`). The process-snapshot interface the test-system plan cites as the correction no longer exists; it was removed with the legacy compiler (`1f885d9ed`). See the note under [DTA-037](retirement-transfer.md#dta-037). Earlier text is in Git at `fbd3f2a98`.

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

### Measurements of 2026-11-17

**Measured from stored results; no test was run.** Method and tables are in the
[evidence folder](../evidence/2026-11-17_joint-audit-refresh/README.md). The host was shared.

- **No passed full run exists after `2e2a0e30…` (2026-11-10).** The full-run figures above
  therefore predate the declared-data-operations tests, the test-system work and the
  retirements, and should not be read as current.
- **The last 120 passed narrowed runs (2026-11-16 15:19 to 2026-11-17 16:53):** median wall
  29.1 s; median fixed cost outside test phases 7.4 s (0.8–39.9 s), of which collection is a
  median 2.8 s. Runs with no database fixture finish in a few seconds; runs whose setup reaches
  a head or seed build show setup of tens of seconds to minutes.
- **Run `873f904c…` (2026-11-14, 685 tests, 4 workers, passed):** 318 s wall; setup is 42% of
  worker time (473 of 1,115 worker-seconds) and 403 of those seconds sit in 17 tests whose
  setup exceeds 15 s. `tests/semantic/` holds 98.6% of worker time. This run predates most of
  the efficiency slices.
- **Run `42cd4f8b…` (2026-11-17, 5 tests, 1 worker, private host, failed):** three tests of
  `tests/semantic/test_operation_event_native_journey.py` spent 382, 448 and 576 s in setup.
  A failed run shows where time went, not a normal cost; the cause was not examined.

These establish no speedup and no current full-run profile.

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
