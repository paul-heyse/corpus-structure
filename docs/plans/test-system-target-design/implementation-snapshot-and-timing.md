# Implementation snapshot and timing controls

**Status:** Proposed plan; nothing implemented. **Created:** 2026-11-13.

This companion owns the design of packages TS-03 and TS-16: the one bounded production change of
the series, which reads the implementation inputs once per process and gives tests an explicit
override, and the CPU lifecycle controls, which stop waiting out production grace periods and
stop writing executor internals. The
[coordinator](../test-system-target-design_2026-11-13.md) owns package state and finding
disposition; nothing here restates them.

**Baseline and evidence.** Source was read at `main` `683e9a955` on 2026-11-13; another session
was committing during authoring, so line citations are as read. Design statements are
**Proposed**. Source facts are **Interface-checked by source inspection, 2026-11-13**. Durations
quoted from the audit are **Measured** from stored results and are orders of magnitude; the
share of any test's time explained by the repeated reads is a source reading, not a profile.
Paths `tests/…` and `src/…` are relative to `python/corpus-structure/`; root paths are written
as root `tests/…`. Section references are to the
[design review](../../design_review/reviews/design_review_test-system-target-design_2026-11-13.md)
(§4.6 for the three production seams, §6.1 for DTA-032, §6.4 for DTA-026).

## Current baseline and what is reused

**Implementation inputs.** Two public readers in `src/corpus_structure/semantic/contracts.py`
acquire the determinants from disk on every call, and nothing on that path is cached:

- `analysis_implementation_inputs()` (`:1180`) reads about a hundred named files, digests every
  file of the `en_core_web_sm` package (`:1394–1397`), reads every `.py` and `.sql` file of the
  package (`:1441`), asks for about nineteen distribution versions and parses the physical YAML
  closure (`:1193–1196`).
- `trusted_execution_inputs()` (`:1166–1177`) wraps it and adds the schema and
  `execution-model.yaml`. Its docstring states the intended lifetime: "Read bundled code-owned
  definitions once at an explicit application entry boundary."

`prepare_interpretation_context` (`src/corpus_structure/semantic/analysis_contracts.py:638`)
reaches those readers through three consumers on every call:

| Consumer | Lines | Reads per call |
|---|---|---|
| `_standalone_model()` | `:409–412` | One, on the standalone branch only (`_profile`, `:425–426`) |
| `_semantic_implementation_digests()` | `:466–469`, compared at `:454–462` | One, on both branches |
| `_analysis_runtime(prepared)` | `:472–485` | One, on both branches: `runtime_implementation_digests()` falls back to the reader (`src/corpus_structure/semantic/runtime_bindings.py:25–38`) on the standalone branch, and `analysis_implementation_inputs()` is called directly at `:484` on the prepared branch |

So a standalone call reads everything three times and a prepared call twice. `grammar.parse`
without a context prepares a standalone context before it consults its memo
(`src/corpus_structure/methods/math/grammar.py:982–993`), so a memo hit pays too.

What is reused: `compile_execution_model` is already cached on its inputs (`contracts.py:1813`),
`_boundary()` is cached once per process (`analysis_contracts.py:488–495`), and the comparison
at `analysis_contracts.py:454–462` is a real admission check that stays.

**CPU lifecycle.** The grace constants are module attributes read at call time in parent-side
code only: `_COOPERATIVE_CLOSE_SECONDS` and `_WORKER_EXIT_SECONDS`, both `5.0`
(`src/corpus_structure/semantic/cpu_execution.py:545–546`), read at `:634`, `:965–966` and
`:1025`. The only factory seam is the module-global name `ProcessPoolExecutor`, constructed in
`_executor()` at `:725–735`. Both seams are already used by tests: the grace constants are
shortened in `tests/semantic/test_data_operation_cpu.py:191–192`, and the first lifecycle test
replaces the module global with a wrapping factory (`tests/semantic/test_cpu_lifecycle.py:59–68`).
No production change is needed for TS-16.

## Target design and contracts

| Operation | Consumes | Decides | Produces |
|---|---|---|---|
| `current_implementation()` | The installed package on first use | Nothing; it is a read | One frozen snapshot per process: the trusted execution inputs, the analysis implementation inputs, the semantic and runtime digest tuples, and the standalone runtime fingerprint |
| `implementation_override(snapshot)` | A snapshot built from explicit inputs, or the refusal marker | Nothing | A context in which `current_implementation()` returns that snapshot, or raises under the refusal marker; the previous state is restored on exit |
| `implementation_overridden()` | — | — | Whether an override is installed; the seed operation (TS-08) uses it to refuse to build |

**What consumers stop doing.** Production call sites stop reading the package from disk per
call. Tests stop monkeypatching the readers and the digest consumer.

**Preserved guarantees.**

- The admission refusal stays: a prepared release whose recorded `implementation_digests`
  differ from the running implementation is refused with `unsupported_analysis_implementation`
  (`analysis_contracts.py:454–462`).
- The runtime fingerprint has the same inputs: `sys.version` and the sorted name and digest
  pairs (`runtime_bindings.py:41–53`). Its value for an unchanged installation is unchanged.
- The standalone route remains the explicit trusted base profile.
- A call that passes explicit `physical_sources` computes as now and never touches the snapshot
  (`src/corpus_structure/cli/model.py:1048`, `src/corpus_structure/semantic/native_candidate.py:1615`).

**The one intentional behavior change.** A process no longer notices installed files that are
edited after its first read. The per-call reads described bytes on disk, which are not
necessarily the code the process had already imported, so the snapshot describes the running
implementation at least as faithfully. The operator decided on 2026-11-13 that a long-lived
process is expected to restart after a code change, so the stat-keyed alternative is not built.

## Pivotal library mechanisms

| Mechanism | Use | Reference |
|---|---|---|
| `functools.cache` on a zero-argument function | One snapshot per process, with `cache_clear()` as the explicit refresh | §7, "Implementation snapshot"; existing idiom at `src/corpus_structure/core/batch.py:119` |
| A context manager that installs and restores a module-level value | The override; it nests, and restores on exceptional exit | Python standard library |
| `pytest.MonkeyPatch.setattr` on a module attribute | Shortened grace; the wrapping executor factory | Existing precedents cited above |
| `multiprocessing` manager events | Gating a spawned worker from the parent; they can cross a spawn as task arguments | Existing precedent, `tests/semantic/test_cpu_execution.py:228–229,283–284,386–387` |

## TS-03 — Implementation snapshot with an explicit override

**Required input.** None. It is independent of the lifecycle packages and scheduled early
because every interpretation context pays the reads, and because the seed operation needs the
override query.

**Implementation vision.** `contracts.py` gains one owner of the implementation inputs.

- A frozen snapshot value holds two primaries, the trusted execution inputs and the analysis
  implementation inputs, and three derived values: the semantic digest tuple that
  `_semantic_implementation_digests` returns today, the runtime digest tuple, and the standalone
  runtime fingerprint. One constructor computes the derived values from the primaries, so a
  snapshot built for a test is consistent by construction.
- `current_implementation()` returns the installed snapshot, read once per process on first use.
  The single disk acquisition sits in one private function that it calls.
- Called without `physical_sources`, `trusted_execution_inputs()` and
  `analysis_implementation_inputs()` return the snapshot's primaries. About a dozen production
  callers of the no-argument form (for example `semantic/composed.py:28`,
  `semantic/regeneration.py:105`, `semantic/pdf_contracts.py:108`) therefore stop reading too,
  with no change to what they receive.
- The three consumers in `analysis_contracts.py` read the snapshot: `_standalone_model` compiles
  from its execution inputs; `_semantic_implementation_digests` returns its semantic digests;
  `_analysis_runtime` takes the runtime digests and standalone fingerprint on the standalone
  branch, and on the prepared branch passes the snapshot's analysis inputs to
  `installed_runtime_id(prepared, inputs)` as it passes the fresh read today.
- `grammar.parse` without a context obtains its standalone grammar context from a memo keyed by
  `(_table_key(table), kind)` before the `_MEMO` lookup at `grammar.py:989–993`.
- `implementation_override(...)` installs a snapshot for the duration of a `with` block. It is
  process-wide, not thread-local, because consumers run on worker threads that must see it. It
  does not cross a process spawn; a spawned CPU worker reads its own installed snapshot, which
  is also what a monkeypatch did.
- Anything memoized from the snapshot must not outlive an override. `_boundary()` and the new
  standalone grammar-context memo are bypassed while an override is installed, or keyed by the
  snapshot's identity; the implementer chooses, and the counting control below fixes the
  behavior for the ordinary case.
- The refusal marker replaces the tests that patch a reader with a failing function to prove
  that a path does not acquire installed inputs.

**Consumers migrated.** The review named the fixture and four reader patches. Source shows one
of those four and five further sites that patch the digest consumer, all of which move:

| Site | Today | Target |
|---|---|---|
| `tests/semantic/native_record_fixtures.py:384–396` | Patches `contracts.analysis_implementation_inputs` to substitute one authored policy asset, for the rest of the test | Builds a snapshot from the installed analysis inputs with that artifact replaced and holds the override for the fixture's lifetime. An override is never a recipe field and never seedable, so this `sibling_originals` path stays on a per-test commit-class build, outside TS-11. The module is also touched by TS-06, TS-07 and TS-11 |
| `tests/semantic/test_execution_release.py:244` | Patches `contracts.trusted_execution_inputs` to return inputs with a comment-only catalog change | Override with a snapshot built from the changed inputs |
| `tests/semantic/test_typed_realization.py:363` | Patches the same reader to return inputs with a changed correspondence | Override; the generators read the no-argument form (`semantic/typed_generation.py:30`, `semantic/companion_projection.py:560`) |
| `tests/semantic/test_execution_release.py:115–118`, `tests/semantic/test_contracts.py:452–455` | Patch the reader with a function that fails the test, to show that archive reconstruction and explicit compilation do not acquire installed inputs | Override with the refusal marker |
| `tests/semantic/test_analysis_contracts.py:483,501`; root `tests/test_native_render_preparation.py:51,132`; root `tests/test_native_retained_reads.py:33` | Patch `analysis_contracts._semantic_implementation_digests` to return `()`, to make the running implementation differ from an admitted release | Override with a snapshot whose analysis inputs differ in one artifact. The refusal is then reached through the real comparison with real digests |

`tests/semantic/test_analysis_contracts.py:468–472` patches `_analysis_runtime` to simulate a
runtime change with an unchanged model. It patches a consumer, not a reader, and may stay or
move to an override at the implementer's judgment.

**Superseded machinery removed.** The per-call acquisition in the three consumers; the reader
and digest-consumer monkeypatches above. No compatibility path is kept.

**The counting control.** One test wraps the single private acquisition function with a call
counter, clears the snapshot cache, then calls `prepare_interpretation_context` several times on
the standalone branch and on a prepared release, and `grammar.parse` without a context for a
repeated and a new input. It asserts exactly one acquisition, and clears the cache again on
exit so later tests read the real installation. Wrapping the acquisition function to count it
is the one place a test touches the read path; it substitutes nothing.

**The admission control.** `test_analysis_support_checks_current_semantic_determinants`
(`tests/semantic/test_analysis_contracts.py:480–485`) and
`test_archived_snapshot_read_uses_unchanged_owned_contract` (`:488–503`) keep their assertions
and reach them through the override. They are the closure evidence that the refusal survives.

**A revealing failure case.** A fixture that still monkeypatched
`contracts.analysis_implementation_inputs` after this change would be ignored by every consumer
that reads the snapshot, and its test would silently run against the installed asset. That is
why the patches are removed in the same package and why a bare cache on the readers was
rejected (§6.1, DTA-032 alternatives).

**Acceptance and closure.** `prepare_interpretation_context` performs no acquisition after the
first in a process, shown by the counting control; no test monkeypatches
`trusted_execution_inputs`, `analysis_implementation_inputs` or
`_semantic_implementation_digests`; the admission refusal keeps its controls;
`implementation_overridden()` exists for TS-08.

**Targeted verification.** `uv run ci test -- python/corpus-structure/tests/semantic/test_analysis_contracts.py
python/corpus-structure/tests/semantic/test_execution_release.py
python/corpus-structure/tests/semantic/test_typed_realization.py
python/corpus-structure/tests/semantic/test_contracts.py
python/corpus-structure/tests/math/test_grammar.py
python/corpus-structure/tests/math/test_property.py`, root
`tests/test_native_render_preparation.py` and `tests/test_native_retained_reads.py`, and one
consumer of the authored policy asset fixture.

**Open premises.**

| Premise | What settles it | If it fails |
|---|---|---|
| No single process writes a determinant file and then expects a fresh no-argument read. Every `.py` and `.sql` file of the package is a determinant, and generators write such files: the script entry at `src/corpus_structure/semantic/typed_generation.py:78` writes `_typed_columns.py`, though it reads first and then exits | Reading the generation and model commands in `src/corpus_structure/cli/model.py` and their callers while implementing | The writing command clears the snapshot cache at the write. That is a refresh at an entry boundary, not a per-call read |
| `MathContext.key()` carries the digests or runtime identity, so a `_MEMO` entry made under an override cannot be returned outside it | Reading `key()` | Clear `_MEMO` when an override exits |
| No test depends on the digests changing in the middle of one process without an override | The targeted run above | Convert that test to an override |

**Handover, not scope.** Production prepares a context per span in
`src/corpus_structure/methods/math/source_context.py:238` and in item loops in
`src/corpus_structure/methods/math/native.py:285,948,1261` (and at `:407,541`, whose loop
nesting was not read). This package removes the repeated reads from those loops. Whether the
loop shape itself fits the workload is production's question and is listed under the
coordinator's handovers to the broad audit.

## TS-16 — CPU lifecycle controls

**Required input.** None.

**Implementation vision.** All changes are in `tests/semantic/test_cpu_lifecycle.py` and
`tests/semantic/test_cpu_execution.py`.

*Windows derive from the constants.* Each elapsed-time assertion is written in terms of
`cpu_execution._COOPERATIVE_CLOSE_SECONDS` and `cpu_execution._WORKER_EXIT_SECONDS` read at test
time, with a stated slack, in place of literals tied to five seconds:

| Line | Today | What it means |
|---|---|---|
| `:78` | `4.5 <= elapsed < 12` | At least the cooperative grace less slack; less than both graces plus slack |
| `:111` | `< 5` | Less than the cooperative grace: the close drained without waiting it out |
| `:161`, `:282` | `< 12` | Less than both graces plus slack |
| `:371` | `< 5` | Less than the cooperative grace |
| `:376` | `9.5 <= … < 12` | At least both graces less slack; less than both plus slack |

The `< 1` bounds at `:355` and `:367` are logical-cancellation checks and are not grace windows;
they stay.

*Behavioral controls shorten the grace.* Each test that waits out a grace sets both constants
with `monkeypatch.setattr` before closing, as `tests/semantic/test_data_operation_cpu.py:191–192`
does, to values well above scheduling noise and well below five seconds. Because the windows
derive from the constants, the assertions follow. The tests already wait for the child's
`started` event before closing and keep an absolute upper bound, so a short grace cannot race
child start-up.

*One assertion pins the policy.* A single cheap test asserts that both constants equal `5.0`
without patching them. The selected five seconds of cooperative grace and five of exit
confirmation are then protected without any test waiting them out.

*Initializer injection uses the module seam.* The four tests that write `_initializer` and
`_initargs` on a live pool (`:92–94`, `:144–145`, `:208–209`, `:326–327`) instead install one
shared wrapping factory before the pool is created, in the manner of `:61–68`:
`monkeypatch.setattr(cpu_execution, "ProcessPoolExecutor", factory)`, where the factory receives
the production keyword arguments and replaces `initializer` with `_initialize_with_event`
(`:120–126`) and `initargs` with the production initializer, the production arguments and the
`started` event. The production initializer therefore still runs in the child, which is what
the private writes achieved. The event must be created before `_executor()` is first called.

*Manager-state access that stays.* `test_close_unblocks_third_submission_behind_broken_pool_lock`
reads `_broken` and `_shutdown_lock` and calls `_executor_manager_thread_wakeup.wakeup()`
(`:261–265`) to construct the broken-pool interleaving. Those stay, with a comment tying them to
the adapter's own documented dependence on the same executor internals
(`cpu_execution.py:568–573,595–602`). `_ownership` (`:44–45`) and the patch of
`_PoolOwnership.shutdown` (`:182`) are the product's types and stay.

*In-flight cancellation is gated.* `test_packet_limit_and_real_inflight_cancellation_release_owned_capacity`
(`tests/semantic/test_cpu_execution.py:110–139`) cancels after its activity callback has been
polled three times, which assumes the worker is still running then. It gates the worker with a
manager event as its siblings do (`:228–233`): the callback raises only after `started` is set,
and the worker is released afterwards, so the cancellation is in flight by construction.

**Successful example.** With the grace patched to a fraction of a second, the non-cooperative
initializer control still shows the close waiting at least the cooperative grace and then
killing the worker, and completes in about that long instead of five to ten seconds.

**Revealing failure case.** If production stopped honoring the cooperative grace and killed at
once, the lower bound derived from the patched constant fails. If someone changed the grace to
two seconds, only the value assertion fails, and no behavioral control changes meaning.

**Acceptance and closure.** No literal in these tests is tied to five seconds; exactly one
assertion pins the value; no test writes `_initializer` or `_initargs`; the in-flight
cancellation control is gated by an event.

**Targeted verification.** `uv run ci test -- python/corpus-structure/tests/semantic/test_cpu_lifecycle.py
python/corpus-structure/tests/semantic/test_cpu_execution.py`.

**Open premise.** Whether the tests at `:137`, `:171` and `:201` wait a real grace today was
not established by reading. Running them once with the shortened constants settles it; a test
that does not wait needs only its derived upper bound.

## Outside this companion

Data-operation lease expiry needs no production change either. Production compares every expiry
with `clock_timestamp()` and has no time parameter, and the suite already expires a lease
without waiting by updating `lease_until` as the publisher role. That change, with the one
real-clock control it keeps, is delivered in TS-18 and designed in the
[data-operations companion](data-operations-test-alignment.md). The seed operation that consumes
`implementation_overridden()` is in the [isolation companion](isolation-and-seeds.md).
