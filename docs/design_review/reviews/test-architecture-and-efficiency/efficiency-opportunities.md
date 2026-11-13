# Efficiency opportunities in the test system

> **Superseded, 2026-11-13.** The current assessment is the
> [design review of the test system target design](../design_review_test-system-target-design_2026-11-13.md),
> which carries F01–F03 and RC01–RC02 forward by identity and states what becomes of each option
> here ([options and classification](../test-system-target-design/options-and-classification.md)). This document is retained as that review's input.

**Supporting document to the [design review of test architecture and efficiency](../design_review_test-architecture-and-efficiency_2026-11-12.md),
2026-11-12.** Written by the same delegated reviewer.

**Role.** This is Part B of that review: an inventory of ways to reduce the computational demand of
the test system while keeping, and where possible raising, fidelity and coverage. It carries no
separate verdict and no disposition ledger; the principal review owns the overall judgment, the
finding identities, the rule impacts (RC01, RC02) and the Deferred rows. Where an opportunity is the
same remedy as a Part A correction, it is designed once in the principal review and only ranked and
cross-referenced here.

**Baseline and consumed context.** `main` `784d86f11`, clean tree; test audit publication
`cf24c0e80`; the four evidence maps and the receipt summary prepared for the review
([retained evidence](../../evidence/2026-11-12_test-architecture-review/README.md)). Paths follow
the principal review's convention: `tests/` and `src/` are relative to `python/corpus-structure/`;
repository-root test paths are written as root `tests/…`; other root paths begin with `scripts/`,
`ops/`, `conftest.py` or `pyproject.toml`. Source facts are **Interface-checked by source inspection,
2026-11-12**; every opportunity is **Proposed**.

**Evidence rule and ranking.** Under the operator's rule an opportunity qualifies without measurement
when a gain is very plausible from structure and a slowdown is very unlikely or impossible; each entry
says why both hold. Nothing was run or timed. The tiers below are my structural judgment of how much
repeated or unnecessary work each removes and how safe it is. **The ranking is not measured.** The
retained receipt of 2026-11-07 (`docs/design_review/evidence/2026-11-06_wce-completion-repair/qualification/test-receipts/ordinary-001`,
source `2b11a881` dirty, 5,070 nodes, 16 workers; phase time 56 % call, 33 % setup, 11 % teardown) is
cited only as orientation.

**Entry fields.** Avoidable work and why it arises · simpler conforming realization · guarantees
preserved · validity premise · why a slowdown is very unlikely · fidelity or coverage gain ·
mechanism (named capability, conditions and limits, reference, and whether selected, candidate or
unresolved).

---

## Summary

| ID | Opportunity | Tier | Designed in |
|---|---|---|---|
| D1 | One head deployment per run, shared by its workers | 1 | Principal §6.1, DTA-024 |
| D2 | Rollback-only refusal families share one committed scenario | 1 | Principal §6.1, DTA-025 (with DTA-001) |
| D3 | Pure SQL-function checks on a read-only, rolled-back head rung | 1 | Principal §6.1, DTA-025 |
| D5 | Sealed scenario seeds cloned per committing consumer | 1 | Principal §6.1, F03 |
| G1 | Fixture-closure groups for expensive module and session preparation | 1 | Principal §6.1, F02 |
| S1 | Staged builders; focused consumers stop at the stage they read | 1 | Principal §6.1, DTA-018 |
| W1 | Workers sized to explicit node-id selections | 2 | Principal RC02 |
| D4 | One maintenance session per clone acquisition | 2 | Here |
| S2 | Memoized scenario input assembly by recipe value | 2 | Here (rides on DTA-009) |
| P1 | Independent cold-process controls run their children concurrently | 2 | Here |
| T1 | CPU lifecycle controls use short grace and pin the production value | 2 | Principal §6.5, DTA-026 |
| D6 | Serving-seed clone validation without exact duplicates | 3 | Here (rides on F03) |
| D8 | One sweep per run instead of one per worker | 3 | Here |
| S3 | Load the controlled PDF builder once per process | 3 | Here |
| W2 | Import the CLI application lazily in the package conftest | 3 | Here |
| W3 | Screen managed pytest arguments without a second interpreter | 3 | Here |
| G3 | Dispatch structurally long single tests first | 3 | Here |
| C1 | Defer collection-time file loads to first use | 3 | Here |
| D7 | Scenario seeds shared across a run's workers | Deferred | Principal §6.1, F03 |
| D9 | Head reused across runs under a conservative content key | Unresolved | Principal §7, §8 |

---

## W — Process and worker startup

### W1 — Workers sized to explicit node-id selections (tier 2; principal RC02)

- **Avoidable work.** `-n auto` starts 16 workers whatever the selection (`pyproject.toml:46–55`;
  `scripts/test_receipts.py:1588`), and every worker imports the package conftest and collects the
  selection before surplus workers are shut down (xdist 3.8.0: workers are fixed before collection and
  each performs a full collection). A one-test run pays 16 interpreter starts, plugin autoloads and
  conftest imports (the CLI application, SQLAlchemy, psycopg, LinkML runtime).
- **Realization.** When every selector is an explicit node id, the managed route passes
  `--workers min(auto, count)`; path selectors keep `auto`.
- **Guarantees preserved.** Same tests, same receipts (the plugin already records requested and
  actual workers), same isolation.
- **Premise.** A node-id count is an upper bound on work units, because each ungrouped test is its own
  unit under `loadgroup`.
- **Why no slowdown.** Workers beyond the number of tests can receive no work; removing them removes
  only startup.
- **Gain.** Less CPU and memory contention for focused runs; with D1 the remaining per-worker database
  work is already gone.
- **Mechanism.** Existing `--workers` option of `ci test` (candidate); alternative: a root-conftest
  `pytest_xdist_auto_num_workers(config)` first-result hook, which sees only `config.args` (xdist
  `plugin.py:16–54`). Changes the default named in the completed parallel-execution companion (RC02).

### W2 — Import the CLI application lazily in the package conftest (tier 3)

- **Avoidable work.** `tests/conftest.py:37` imports `corpus_structure.cli.app` (all 22 command modules,
  Rich, Typer) at conftest import in every worker, although only the `cli` fixture uses it
  (`:144–159`).
- **Realization.** Import inside `Cli.__call__` or the fixture.
- **Guarantees preserved.** Unchanged behaviour of CLI tests; the import-hygiene controls in
  `tests/test_cli.py:276–340` run in fresh interpreters and are unaffected.
- **Premise.** Nothing else in the conftest needs `app` at import.
- **Why no slowdown.** The import moves, it does not repeat (module cache).
- **Gain.** Focused non-CLI runs skip the import; small.
- **Mechanism.** Plain deferred import (selected if adopted).

### W3 — Screen managed pytest arguments without a second interpreter (tier 3)

- **Avoidable work.** A narrowed `ci test` spawns `uv run python scripts/test_receipts.py
  validate-pytest` only to call the pure `validate_pytest_args` (`scripts/test_receipts.py:1536–1552`;
  process map §1.1), before the lane spawns `uv` again.
- **Realization.** Screen in the process that already builds the lane arguments
  (`_managed_pytest_args` calls the same function, `:1567`), and report a refusal from there.
- **Guarantees preserved.** The same validation function and refusals.
- **Premise.** The CLI-operations custody boundary (ADR-0069) allows the screening to happen inside the
  lane's own `test_receipts.py` process rather than in a separate pre-check; I did not establish
  whether the separate pre-check exists to fail before a managed result workspace is opened.
- **Why no slowdown.** One process fewer.
- **Gain.** A fixed per-invocation saving on every focused run; small.
- **Mechanism.** None beyond moving a call (candidate).

---

## G — Scheduling

### G1 — Fixture-closure groups for expensive module and session preparation (tier 1; principal F02)

- **Avoidable work.** Under `loadgroup` an ungrouped test is its own work unit, so module- and
  session-scoped preparation is rebuilt on every worker that runs a consumer, and again on one worker
  when its module's tests interleave with others. Example: the full statistics pack prepared at module
  scope in `tests/orchestrate/test_policy.py:36–49` for ten test functions; the receipt shows that
  module as setup time only.
- **Realization, guarantees, premise, gain.** Principal F02.
- **Why no slowdown.** Grouping is restricted to preparation that clearly dominates cheap bodies, so
  serialising the bodies costs little; modules with expensive bodies are excluded by the criterion.
- **Mechanism.** `xdist_group` assigned by fixture closure in root `conftest.py:21–37` (selected;
  existing math pattern). Limit: two group marks on one item form a combined group, so each item gets
  at most one.

### D2's family groups

Rollback-only families sharing a scenario use the same mechanism; see D2.

### G3 — Dispatch structurally long single tests first (tier 3)

- **Avoidable work.** Not work but idle tail: a few single tests are structurally long
  (`tests/math/test_coverage.py::test_coverage_beside_s5`, `tests/math/test_property.py::test_generated_layer`,
  `tests/acceptance/test_regeneration.py` lifecycle cases, `tests/schema/test_packs.py` hash control,
  `tests/db/test_cli_db.py` subprocess migration). Under `loadscope`-family scheduling, units are
  sorted by test count, then kept in collection order, so a long single test is dispatched wherever it
  happens to be collected and can start late.
- **Realization.** A short designated list moved to the front of collection in the root conftest hook,
  so those units are dispatched first among single-test units.
- **Guarantees preserved.** Same tests and assertions; collection stays deterministic and identical on
  every worker.
- **Premise.** `loadscope` keeps collection order among equal-size units (stable sort of the work
  queue; library map §2).
- **Why a slowdown is very unlikely.** Reordering adds no work; starting the longest independent jobs
  first is the standard way to shorten a list schedule's tail. It cannot change any result.
- **Gain.** Shorter wall time of full runs when a long test would otherwise start late; none for focused
  runs.
- **Mechanism.** `pytest_collection_modifyitems` reorder (candidate). The completed parallel companion's
  "no custom scheduler" is respected, since the built-in scheduler is unchanged.

---

## D — Database layer

### D1 — One head deployment per run (tier 1; principal DTA-024)

- **Avoidable work.** The 240-revision head is deployed by every worker that needs it, and by up to
  *k* workers for a *k*-test focused run. The concurrency of those deployments is why the cluster's
  `max_locks_per_transaction` was raised (`ops/postgresql/corpus.conf:7–9`).
- **Realization and guarantees.** Principal §6.1.
- **Why no slowdown.** Waiting workers block on an exclusive advisory lease while one deployment runs
  without the contention of fifteen others; waiting cannot exceed building under contention.
- **Gain.** One deployment per run; a consistent chain for the whole run.
- **Mechanism.** Session advisory locks, `pytest_configure_node` / `workerinput`, controller
  `pytest_sessionfinish` (selected; principal §7).

### D2 — Rollback-only refusal families share one committed scenario (tier 1; principal DTA-025)

- **Avoidable work.** Each case of six families rebuilds an identical committed scenario on a fresh
  clone (12 + 8 + 10 + 7 + 13 + 6 cases), then clones, replays policy and drops (each drop forcing a
  cluster checkpoint). The forged-judged family's per-case setup is the largest in the receipt.
- **Realization and guarantees.** Principal §6.1, with the refusal contract of §6.2.
- **Why no slowdown.** The family's cases run serially on one worker, but each case becomes a rolled-back
  transaction on prepared state instead of a full build; the family is one larger unit that `loadgroup`
  dispatches early (largest first).
- **Gain.** Fidelity rises: every case gains a minimal-pair positive control and an exact reason.
- **Mechanism.** SQLAlchemy Core rollback and savepoints; `xdist_group` by fixture closure (selected).

### D3 — Pure SQL-function checks on a read-only head rung (tier 1; principal DTA-025)

- **Avoidable work.** A clone, policy replay and drop per case for calls to STABLE functions with
  literal arguments (`tests/semantic/test_local_semantic_admission.py:121–147`,
  `tests/semantic/test_contextual_workflow_native.py:29–135`).
- **Realization.** Principal §6.1: READ ONLY, rolled-back transactions on the per-worker `db` session
  clone, which no consumer commits to after one DDL-committing utility moves to its own clone.
- **Why no slowdown.** One clone per worker instead of one per case.
- **Gain.** "Writes nothing" becomes enforced: a hidden write fails with SQLSTATE `25006`.
- **Mechanism.** `SET TRANSACTION READ ONLY` (selected).

### D4 — One maintenance session per clone acquisition (tier 2)

- **Avoidable work.** `PgAdmin.connect()` builds a `NullPool` engine, opens one connection and disposes
  it on every call (`scripts/native_test_support.py:166–179`), so one acquisition opens about seven
  backends (lease, existence, creation, replay, two policy reads, transactional replay) and the drop one
  more, each a fork and authentication on the server and, in receipt-enabled runs, an observation with
  two to four extra statements and a JSON event (`:677–755`). This multiplies by every clone in the run.
- **Realization.** Keep the lease on its own long-lived connection and role-self replay on its own
  login. Run existence, creation, tagging, replay steps and policy reads on one maintenance connection,
  switching its isolation level between `AUTOCOMMIT` (for `CREATE DATABASE`, which cannot run in a
  transaction block) and `READ COMMITTED` (for the `SET LOCAL ROLE … FROM CURRENT` replay) between
  transactions; read policy on that same connection rather than through nested `connect()` calls
  (`:321,367`).
- **Guarantees preserved.** The same statements, the same comparison of replayed and source policy,
  the same authenticated creation and drop, the same failure on unavailable replay authority. Replay
  still runs on `postgres`, never on the clone source.
- **Premise.** Session state set during replay is transaction-local (`SET LOCAL`) or explicitly reset
  (`RESET ROLE`), which holds at `:322–352`.
- **Why no slowdown.** Fewer backends for the same statements.
- **Gain.** Fewer observation events per clone, so receipts carry less noise.
- **Mechanism.** SQLAlchemy `Connection.execution_options(isolation_level=…)` between transactions
  (SQLAlchemy 2.1 documents that isolation can only change outside a transaction; library map §6)
  (candidate).

### D5 — Sealed scenario seeds cloned per committing consumer (tier 1; principal F03)

- **Avoidable work.** Identical committed scenarios rebuilt through producers for every committing
  consumer of a default recipe (`private_source`, default `build_domain_case`,
  `build_resubmission_case`, `exclusion_result`, `pdf13_db`).
- **Realization and guarantees.** Principal F03: per-worker seeds keyed by recipe value, sealed,
  time-independent, files read-only, a fresh clone per consumer, claims taken after cloning.
- **Why no slowdown.** A `WAL_LOG` clone of a sealed database copies blocks; a build writes the same rows
  through many transactions, Arrow batches and Python producers, and also writes WAL.
- **Gain.** Shorter setup for every focused native run that uses a seeded recipe; DTA-006's changed-run
  comparison becomes a cheap clone plus one change.
- **Mechanism.** Existing `database()` acquisition from a sealed source (selected; the serving seed is
  the precedent and migrates into the same operation).

### D6 — Serving-seed clone validation without exact duplicates (tier 3)

- **Avoidable work.** Each serving clone revalidates the seed (`_validate_serving_seed`: OID, policy,
  recipe recomputed from `inspect.getsource` of three functions and SHA-256, and a sealed/client-free
  check; `tests/semantic/serving_scenarios.py:218–238,307`), then re-reads the clone's policy
  (`:310`) although `replay_policy` has just compared it (`scripts/native_test_support.py:367–371`).
- **Realization.** Keep the cheap checks the seal does not cover (OID unchanged; still sealed and
  client-free); drop the duplicate policy read and recompute the recipe only when the seed is sealed.
- **Guarantees preserved.** The seed cannot be connected to (sealed) or dropped while leased; the
  replay comparison remains.
- **Premise.** Code cannot change inside a running interpreter except by monkeypatching, which seeds
  must not be built under (principal F03).
- **Why no slowdown.** Fewer connections and less hashing.
- **Gain.** Small; it matters more once D5 makes seed clones common.
- **Mechanism.** None (candidate, rides on F03).

### D7 — Scenario seeds shared across a run's workers (deferred)

Per-worker seeds rebuild each recipe up to once per worker. A run-scoped seed would use D1's
operation, but each worker also needs the seed's Python descriptor (prepared release, identifiers) and
access to its files, so seed descriptors must be serialisable and files placed under the run's shared
temporary root. Revisit only if per-worker seed builds still dominate after D5 (principal F03).

### D8 — One sweep per run instead of one per worker (tier 3)

- **Avoidable work.** Every worker's `native_server` sweeps the cluster at its first native test
  (`tests/conftest.py:242–252`; `scripts/native_test_support.py:554–610`): sixteen scans per full run,
  each try-locking candidates that other sweeps are also examining.
- **Realization.** With D1 the first worker to take the run's exclusive lease sweeps; later workers skip
  the sweep. A controller-side sweep is not proposed because it would give pure-Python selections a
  database dependency.
- **Guarantees preserved.** The same recognition rule, ownership check and lease respect.
- **Premise.** Residue from earlier runs does not appear during a run, apart from the run's own names,
  which sweeps already skip.
- **Why no slowdown.** Fewer scans.
- **Gain.** Small.
- **Mechanism.** The run lease from D1 (candidate).

### D9 — Head reused across runs under a conservative content key (unresolved)

Focused reruns after test-only edits would skip head deployment entirely. The key must be a superset
of what deployment depends on: migrations import product code (`corpus_structure.semantic.native_objects`
in 168 revision files), so the key covers the migration directory, the product source tree, the
installed Alembic, SQLAlchemy and psycopg versions, the server version and the `cs_template` identity.
ADR-0032 rejects a persistent key, and an incomplete key would silently test an old schema (G6). Not
selected; principal §7 and §8 state the revisit trigger.

---

## S — Scenario preparation

### S1 — Staged builders; focused consumers stop at the stage they read (tier 1; principal DTA-018)

Designed in the principal review. Avoidable work: full scenario builds behind controls that read only
a persisted release or nothing at all, and provider skips after preparation. Gain: lower cost and no
failure coupling to unrelated stages.

### S2 — Memoized scenario input assembly by recipe value (tier 2)

- **Avoidable work.** Every `private_source` instantiation calls `prepare_record_source`, which builds
  the schema bundle, derives dependencies (including fixture execution inputs) and only then reaches
  `prepare_release`'s content-keyed cache (`tests/semantic/native_record_fixtures.py:208–286`;
  `src/corpus_structure/semantic/prepare.py:544–580`). The cache absorbs the compile, not the assembly
  and hashing ahead of it.
- **Realization.** With recipe values (principal DTA-009), memoize the `RecordPreparation` per process by
  recipe value.
- **Guarantees preserved.** The same prepared release object reaches consumers (the cache already
  returns one shared object, `tests/semantic/test_prepare.py:539`).
- **Premise.** Recipe transforms are pure and keyed by identity; consumers do not mutate the bundle,
  dependencies or prepared release (no new exposure, since the release object is already shared).
- **Why no slowdown.** A dictionary hit replaces an assembly.
- **Gain.** Fewer collisions with the eight-entry release cache.
- **Mechanism.** `functools.cache` on a function of the frozen recipe (selected with DTA-009).

### S3 — Load the controlled PDF builder once per process (tier 3)

- **Avoidable work.** `write_controlled_pdf` re-executes `fixtures/toy/build_pdf.py` through
  `runpy.run_path` on every call (`tests/pdf_acceptance_support.py:385–391`), and `publish_controlled_pdf_views`
  runs inside every resubmission and domain case.
- **Realization.** Cache the loaded namespace per process; keep writing the PDF per call.
- **Guarantees preserved.** The same builder function writes the same file.
- **Premise.** The script has no per-call module-level side effects and nothing mutates its namespace.
- **Why no slowdown.** One script execution instead of many.
- **Gain.** Small per call, multiplied by every scenario build that remains after D5.
- **Mechanism.** `functools.cache` around `runpy.run_path` (candidate). Caching the PDF bytes is not
  proposed: determinism of `write_pdf` output was not established.

---

## P — Process boundaries

### P1 — Independent cold-process controls run their children concurrently (tier 2)

- **Avoidable wall time.** `tests/schema/test_packs.py:68–83` runs two cold interpreters one after the
  other, each preparing the full statistics pack under a different hash seed and path. Similar
  sequential pairs or triples exist in `tests/semantic/test_prepare.py` (two cold children),
  `tests/semantic/test_statistics_model.py`, `tests/schema/test_model_explanation.py`,
  `tests/semantic/test_terminology.py` and `tests/semantic/test_interpretations.py` (process map §4.2).
- **Realization.** Start the independent children together and compare their outputs after both finish.
- **Guarantees preserved.** Separate processes, separate seeds and paths, the same comparison; the claim
  is that independent cold runs agree, which concurrency does not weaken.
- **Premise.** The children share no writable files; this must be checked for `prepare_packs` and each
  script (an on-disk cache shared by both children would make concurrency a race).
- **Why a slowdown is very unlikely.** Total work is unchanged; under full contention the pair takes no
  longer than in sequence.
- **Gain.** Shorter wall time of the longest of these tests in a full run and in focused runs.
- **Mechanism.** `subprocess.Popen` and `communicate()`, or a thread pool around `subprocess.run`
  (selected if adopted).

### Other process boundaries examined

Installed `ci` invocations (`tests/test_cli_test_evidence.py`, `tests/semantic/test_review_cli_native.py`
and others), fresh-interpreter import-hygiene and determinism controls, stdio MCP children
(`tests/semantic/test_runtime_entrypoints.py:463–609`), real spawn pools in the math and CPU lifecycle
controls, and nested pytest sessions in root `tests/scripts/test_parallel_harness.py` and
`test_test_receipts.py` each exercise the boundary their claim names. I found no cheaper realization
that keeps the boundary real; see "Recorded, not developed".

---

## T — Real-time waits

### T1 — CPU lifecycle controls use short grace and pin the production value (tier 2; principal DTA-026)

Designed in the principal review. Avoidable work: serial waits of the five-second production grace
periods in `tests/semantic/test_cpu_lifecycle.py`. Why no slowdown: shorter waits. Gain: bounds derive
from the constants, so a policy change no longer fails or silently weakens the controls.

Other waits examined (process map §5) already inject small budgets (`grammar.deadline`,
`SearchLimits(max_seconds=0)`, `open_pm2_worker(startup_timeout_seconds=0.05)`, claim-owner timeouts)
or are bounded by the event they wait for. No further opportunity was found.

---

## C — Collection

### C1 — Defer collection-time file loads to first use (tier 3)

- **Avoidable work.** Every worker collects the full selection, so module-level loads run sixteen times
  in a full run: `tests/ingest/test_renditions.py:32` parses a retained JSON at import,
  `tests/semantic/test_pdf_records.py:575` loads a schema at import. Duplicate module objects for test
  modules imported by absolute name (principal DTA-009) execute their files twice per worker.
- **Realization.** Load inside a cached function or module fixture where the value is not needed to
  build parametrization; remove the duplicate imports through DTA-009.
- **Guarantees preserved.** Same values.
- **Premise.** The loaded value is not used in decorator arguments at collection
  (`tests/core/test_shapes.py:197–199` is, and stays).
- **Why no slowdown.** Work moves to the workers that run the tests, once each.
- **Gain.** Small.
- **Mechanism.** `functools.cache` (selected if adopted).

---

## Hypothesis

The managed `ci` profile runs 300 derandomized examples per property without a database
(`tests/conftest.py:65–69`). Twenty-six of the 27 `@given` tests (process map §6, grep) touch no
database or process; the database-backed property
(`tests/semantic/test_native_closure.py:530–575`) already limits itself to 16 examples, each a
rolled-back transaction on one prepared clone. No opportunity within the latitude was found; fewer
examples would weaken exploration (recorded below).

---

## Structurally heavy single tests

What each needs for its claim, and what is incidental. Durations are not asserted; the receipt only
identified candidates.

| Test | Essential to its claim | Incidental work and applicable opportunity |
|---|---|---|
| `tests/math/test_coverage.py::test_coverage_beside_s5` | 78-page span reading in spawned workers and comparison with S5 | Start time (G3). Each coverage child parses the 11.4 MB retained archive once (`tests/math_support.py:113–118,401–404`); the staged chain already ships page content instead (`:329–360`), but changing the coverage worker's input path is recorded, not developed |
| `tests/math/test_property.py::test_generated_layer` | 300 generated parses | Start time (G3) |
| `tests/acceptance/test_regeneration.py` lifecycle cases | Full CLI lifecycle against a fresh clone | Toy PDF builder executed per setup (S3); head (D1) |
| `tests/schema/test_packs.py::test_hashes_are_equal_across_processes_hash_seeds_and_load_paths` | Two independent cold preparations | Sequential children (P1) |
| `tests/db/test_cli_db.py` failed-migration subprocess | Real migration chain in a child | None: deployment is the subject (ADR-0032 keeps such controls) |
| `tests/semantic/test_runtime_entrypoints.py` stdio journeys | Four modes, each with its own child and settled task | Scenario per mode (D5); exact task state per mode (principal DTA-016 residue) |
| `tests/semantic/test_local_semantic_admission_native.py` forged rows | Ten refusals with exact reasons | Scenario per case (D2) |
| `tests/semantic/test_identity_exclusions.py`, `test_exclusion_comparison.py` | Grounded memberships; comparison | Exclusion scenario per test (D5); comparison of a run with itself (principal DTA-006) |
| `tests/semantic/test_cpu_lifecycle.py` | Close, kill and admission with real children | Real grace waits (T1) |
| `tests/math/test_workers.py` staged parity | Spawn and in-process readings of one page agree | None found |
| Root `tests/scripts/test_parallel_harness.py`, `test_test_receipts.py` | Real nested sessions and worker loss | None within latitude |
| `tests/test_cli_test_evidence.py` | Installed command rendering over retained receipts | None within latitude |

---

## Recorded, not developed

Outside the operator's latitude, or a slowdown cannot be ruled out from structure:

- **Asynchronous or deferred clone drops.** Would take drop waits (each a forced cluster checkpoint) off
  the test path, but adds concurrent checkpoint and I/O pressure and, if deferred, disk for live clones;
  a slowdown cannot be ruled out without measurement.
- **Non-durable cluster settings** (`fsync`, `full_page_writes`, `wal_level = minimal`). Cluster-wide,
  shared with the development database; an operator decision outside test scope. `synchronous_commit`
  is already off (`ops/postgresql/corpus.conf:30`).
- **`STRATEGY FILE_COPY` with `file_copy_method = clone`.** Forces two checkpoints per creation and needs a
  reflink filesystem; the data directory is on ext4.
- **Fewer Hypothesis examples or narrower phases.** Weakens exploration.
- **Subtests in place of parametrized refusal cases.** Merges case identities.
- **In-process `CliRunner` in place of installed `ci` invocations, or in-process orchestration in place of
  nested pytest sessions.** Replaces the boundary the claim names.
- **Disabling plugin autoload in workers or nested sessions.** Changes the environment the route runs in.
- **One shared source for the structural-replay family's fourteen texts.** Merges distinct committed
  scenarios.
- **A disk cache of prepared releases across processes.** A second reuse mechanism over a production
  cache whose key includes compiler identity; an incomplete key would be a G6 failure.
- **Coordinating the math page pool (up to eight spawn children) and CPU execution pools with xdist's
  worker count.** A real DP-20 concern for host contention, but shrinking pools can lengthen the
  critical path; needs measurement.
- **Fewer workers for full runs.** Database contention may favour fewer workers, but the direction of
  the effect is not established structurally.
- **Shipping page content to the coverage worker.** Would remove per-child archive parsing, but changes
  the reading path the coverage control exercises (`read_page`, the "direct reading path").
- **Reusing the receipt's recorded selection for `ci test retry` instead of a fresh collection.** Unsafe
  after source edits, which is when retries usually happen.
- **The legacy `python/corpus-structure/alembic/` chain without a reader** (audit DTA-030 lead). Outside
  test scope.

---

## Limits

Static review only. No test, collection, database operation or timing. Counts marked as coming from the
evidence maps are AST or grep counts, not collected nodes. The PostgreSQL drop-checkpoint behaviour is
from `REL_18_STABLE` source, not the 18.6 tag. Premises named in each entry are the conditions under
which the entry holds; none was executed. Return to the [principal review](../design_review_test-architecture-and-efficiency_2026-11-12.md)
for the judgment, the finding identities, the rule impacts and the dispositions.
