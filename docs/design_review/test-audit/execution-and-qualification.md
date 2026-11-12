# Execution and qualification

**Interface-checked by source inspection, 2026-11-12.** Baseline and limits are in the
[account](README.md#baseline). No runtime or timing result was produced by this refresh; every
statement about unnecessary work below is structural, not a measured cost.

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

**Related, lower weight — maintenance connection lifecycle.** ADR-0032 establishes that
PostgreSQL clones omit database ACLs and database and role defaults, so capturing, replaying
and comparing policy for every clone (`scripts/native_test_support.py:306–371`) is required
work, not waste. What is incidental is how it is carried: `PgAdmin.connect()` (`:165–179`)
creates a `NullPool` engine, attaches observation and disposes it on every call, so one clone
acquisition (`:443–470`) opens and closes several maintenance connections for lease, existence,
creation, ownership, settings and policy reads. Some are inherently separate, because
role-self replay authenticates as another login (`:389–415`). This is a different cause from
the per-worker template and is recorded here only as an observation for whoever revisits the
ADR.

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
  `tests/semantic/test_witnessed_applicability_native.py:36–126,172–280` (six corruptions over a
  function-scoped fixture that runs four runs and two finalizations),
  `tests/semantic/test_arrow_publication.py:456–493` (six),
  `tests/semantic/test_structural_native_replay.py:147–217` (fourteen, some with genuinely
  different source text) and `tests/semantic/test_contextual_enrichment_native.py:65–157`
  (thirteen).

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
which a longer-lived scenario would have to keep valid; and whether every helper in these
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
interpreter is pinned, which bounds the exposure, but a toolchain move would break these
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

No timing measurement was taken. Earlier receipts retain their original source and conditions
in Git; none is a current workload claim.

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
