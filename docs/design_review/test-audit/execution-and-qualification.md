# Execution, isolation and qualification

Findings about test resource lifecycle, repeated preparation, ambient state and the route that turns
test results into qualification evidence: FP-05, FP-06, FP-07/A4, DP-09/10/19/20/21, CI-04 and
CI-10 by analogy, and [companion](../design_principles/core/test-assessment.md) §6 and §8.
Baseline, scope and method are in the [README](README.md). Paths are relative to
`python/corpus-structure/` unless they start at the repository root (`docs/`, `domains/`,
`fixtures/`, `ops/`, `scripts/`, `justfile`, `pyproject.toml`).

The native harness has solid foundations, and they bound any remedy:
- Real restricted logins through purpose credentials, with no `SET ROLE` substitution
  (`tests/semantic/conftest.py:60-101`).
- A fresh committed clone per consumer test, with database ACLs and settings captured, replayed and
  compared before exposure (`scripts/native_test_support.py:271-422`). Non-owner grant graphs refuse
  explicitly rather than replaying loosely.
- Independent, real controls for that replay: lost replay is required to fail
  (`tests/semantic/test_native_fixtures.py:112`), non-owner graphs refuse (`:131`), real logins prove
  TEMP denial on a head clone (`:154-183`), a real restricted leak produces a real 55006 (`:228-255`)
  and fault injection never adopts another's database (`:311-410`).
- Bounded normal-exit retries, with no forced drop and no backend termination
  (`scripts/native_test_support.py:222-249`). A search of the tests and that module for `WITH (FORCE)`
  finds nothing, so the earlier [Q4-01](../../plans/phase-0_2026-10-28.md#11-findings-disposition)
  observation no longer holds at this path.
- A classifier that is conservative by construction: a pass requires setup, call, teardown and
  `logfinish`, and any skip is `blocked` unless explicitly optional (`scripts/test_receipts.py:356-366`).

<a id="measurements"></a>

## What the one retained receipt measures

Measurements below come from one retained receipt and bind only to its conditions:
`build/test-receipts/qualification/20261030T115507Z-472803`, recorded at `2869e6e` with a tree dirty
in docs and evidence only (not this account's baseline; 2,428 nodes against 2,429), through `just
test-all`, one serial pytest process, Hypothesis profile `ci`, cluster `18/corpus` on PostgreSQL 18.6,
one run, host load unrecorded. It reports `3 failed, 2425 passed`. Totals were recomputed from
`reportlog.jsonl` by the coordinator: setup 136.64 s, call 861.66 s, teardown 17.06 s. They support
the statements on this page and establish no capacity, speedup or dominance claim beyond it.

| Route (by fixture closure, contributor's classification over the receipt) | Nodes | Setup s | Call s | Teardown s |
|---|---:|---:|---:|---:|
| No database | 1,984 | 72.51 | 596.62 | 0.45 |
| Semantic clone | 331 | 21.92 (median 0.064) | 229.03 | 15.94 (median 0.047) |
| Legacy rollback `db` | 59 | 37.82 (median 0.69) | 18.03 | 0.02 |
| Legacy committing clone | 6 | 3.81 | 2.29 | 0.32 |
| Other native and legacy server routes | 48 | 0.59 | 15.69 | 0.31 |

Single expensive items, same conditions:
- `tests/math/test_coverage.py::test_coverage_beside_s5` 176.91 s, about 17% of recorded phases;
- `tests/schema/test_packs.py::test_what_pydantic_accepts_of_schema_draws_satisfies_the_schema` 89.41 s, of which setup 10.29 s;
- these two and `test_generated_layer` (36.17 s) are the three costliest nodes, 29.8% together, and all three carry the weak assertions of
  [DTA-013](evidence-and-discrimination.md#dta-013);
- four setups account for 66.3 s of the 72.5 s non-database setup: `math/test_scope` 22.55 s,
  `math/test_property` 18.18 s, `ingest/test_corpus` 15.30 s, `schema/test_packs` 10.29 s;
- `tests/ingest/test_html.py:198-207` 21.27 s for one delimiter-timeout branch;
- the first head consumer's setup, which includes the complete head build, 0.396 s. The cold
  bootstrap test `test_native_bootstrap_and_subsequent_projection` independently recorded 0.307 s
  of call time.

So semantic clones cost about 3.7% of recorded phase time, and database routes in total about a
third. Modules challenging code with no execution route cost about 20%
([DTA-014](retirement-transfer.md#dta-014)). Non-database preparation and a few long nodes account for more than repeated clones do.

<a id="dta-018"></a>

## DTA-018 — Read-only and rollback cases rebuild a complete write journey per case

**Principles:** FP-07/A4, FP-03, FP-06, DP-10; H5, H12, H19, H20, H27; companion §8, §6.
**Subject:** implemented (`tests/semantic/test_serving.py`, `test_occurrence_context.py`,
`test_identity_exclusions_native.py`, `test_identity_exclusions.py`, `test_cli_failures.py`).

**Diagnosis.** [ADR-0032](../../adr/0032-native-test-deployment-equivalence.md) removed repeated
migration. It did not address scenario preparation above the clone, and several parametrized
matrices rebuild a complete write journey for a case that only reads, or that rolls back:
- `test_identity_exclusions_native.py:16-41` has 10 cases. Each calls `exclusion_result`
  (`test_identity_exclusions.py:16-102`): `source_task` with preparation and HTML ingest, `anyio.run`
  and a FastMCP `Client`, lease, read, `propose_claims`, sealing a cut and `_cut_input`. Only then does
  the case perturb an in-memory batch and attempt a publication that rolls back. The claim needs a
  sealed cut with genuine custody. It does not exercise leasing, packet reading or MCP transport.
- `test_occurrence_context.py:110-193` has eight parameters, each a full `fixture(duplicate=True)` plus
  `_cut_input`, and the damage is an in-memory edit whose attempt rolls back.
- `test_serving.py` `completed()` performs the same default journey three times
  (`test_named_semantic_pages…`, `test_full_projection…`, `test_real_cli…`) for reads and exports.
- `test_cli_failures.py:194-251` has eight cases with one `stage` each, for a read-only CLI route.

**Consequence.**
- The work grows with each new consumer of `completed()`, `fixture()` or `exclusion_result`.
- Focused iteration on a serving read or a native guard pays for submission and consolidation, and
  a narrow native selection imports `fastmcp`, `anyio` and other test modules.
- An MCP, lease or ingest defect fails every case in these matrices. The failure identifies the
  shared cause well, so this is friction rather than concealment.

This is demonstrated repeated work. It is not a measured bottleneck: the semantic clone route's
229 s of call time is not attributed between journeys and assertions, and the modules cited total at
most about 55 s, about 5.5%, including nodes outside these matrices. The structural diagnosis stands; its
weight is smaller than [DTA-013](evidence-and-discrimination.md#dta-013)'s and [DTA-014](retirement-transfer.md#dta-014)'s.

**Footprint.**
- *Known:* the matrices cited. `test_execution_native.py` also repeats a 25–35-line setup block five
  times (`:92-119`, `:191-225`, `:325-359`, `:407-434`, `:540-564`).
- *Inferred:* the cost grows with DTA-009's hubs, and consumers reach them by import.
- *Suspected:* none beyond the above.

**Counterevidence.**
- Building through the real route keeps custody evidence honest, and that is what closed the
  stand-ins of [DTA-008](support-structure.md#dta-008). The finding is the repetition, not the realism.
- `prepare_release` is cached, so compilation is not what repeats.
- Fresh isolation is the accepted premise. ADR-0032 rejected persistent caches, though not session
  reuse of a read-mostly scenario; sharing a sealed scenario would carry its own validity premises.
- `test_operations.py:951` (nine parameters) genuinely needs per-case state.
- `test_consolidation`, `test_analytics` and most of `test_proposals` avoid the database where they can.

**Uncertainty.** The relative weight of journey construction against clone and assertion. The receipt
does not attribute it; a per-fixture split would settle it if a change to these tests is contemplated.

**Leads (optional).** A session-scoped sealed scenario for read-only matrices. Not a default, and only
where a case does not need to own the writes.

**Bears on:** every package adding native semantic tests; focused developer iteration.

<a id="dta-017"></a>

## DTA-017 — The harness leaves a real target as the ambient connection, and only names separate targets from sweepable databases

**Principles:** FP-05, FP-06, FP-02, DP-19, DP-20; H18, H25; companion §5, §6.
**Subject:** implemented (`src/corpus_structure/settings.py:35`, `:87`; `tests/conftest.py:118-128`;
`scripts/native_test_support.py:217-243`, `:559-618`; `tests/test_semantic_runtime_settings.py:30-40`).

**Diagnosis.** Test isolation rests on routing every native test to a clone, but nothing fences the
default route.
- `settings.py:35` defaults the URL to `corpus_sem_writer@/corpus_efficiency_20261030`, a real selected
  target, and `:87` defaults the project to `production-efficiency`. No `CORPUS_` variable is set in the
  audit environment or in `.envrc`.
- The `Cli` fixture (`tests/conftest.py:118-128`) passes `obj=None` unless given `settings=`, and
  `CliState` then falls back to `Settings` (`src/corpus_structure/cli/output.py:29`). An AST count finds
  native CLI calls without `settings=` or `obj=` in `test_source_routing` (8), `test_runtime_entrypoints`
  (2), `test_operations` (1), `test_known_reference_mcp` (1) and `test_native_closure` (1, which
  correctly sets the URL in its environment).
- Those rely on patching `orchestrate.ENGINE`, a documented seam (`src/corpus_structure/cli/orchestrate.py:6`).
  There is no autouse fixture or sentinel URL for anything that bypasses it. A command that reaches
  `open_runtime_engine` directly would connect as the real writer to the real target.

The disposal side has the same shape. `sweep` requires owner, stamp and name, but real targets carry
the same stamp form: a read-only catalog query on 2026-10-30 shows
`corpus_efficiency_20261030` and `corpus_semantic_pivot_20261030` with the comment
`corpus-structure owned database <hex> oid <n>`. So owner and comment do not distinguish a test database
from a target, and the prefix list and `fullmatch` do (`scripts/native_test_support.py:572-603`).
`PgAdmin.drop(name)` (`:217`) would drop a target if handed its name.

The coupling has already had an effect: one of the receipt's three failures is
`test_restricted_defaults_and_purpose_credentials`, `'production-efficiency' == 'semantic-pivot'`, because
a commit moved the defaults to the next dated target. Each retargeting edits a test.

**Claim at risk.** The "dedicated server" premise in ADR-0032 option 4 is qualified: the cluster is
dedicated against other projects (`main`), not between tests and real targets. Native hermeticity is
also at risk. A test could depend on target state or write to it before failing.

**Consequence.** Under the operator rule that data is regenerable, permanent loss is not the concern.
What remains is that a long regeneration or measured run can be disturbed or contaminated, and that a
misrouted test may commit before its assertion fails.

**Footprint.**
- *Known:* the sites cited.
- *Inferred:* the writer has CONNECT on targets.
- *Suspected:* an actual misrouted test. None was found; subcommand paths were traced only as far as the
  `ENGINE` patch.

**Counterevidence.**
- What protects targets today is real: `starts_with` rather than `LIKE`, so
  `cs_semantic_20261029_0f70052` does not match `cs_sem_`; clones only from `cs_template` or a session
  head; `principal_engine` always substitutes the clone name; the restricted writer cannot drop databases.
- Journeys assert data they seeded, so misrouting most likely fails loudly.
- One operator controls concurrency.

**Uncertainty.** Whether any route is actually unfenced. Pointing `CORPUS_DATABASE__URL` at a refused
socket does not settle it directly, because `native_settings` resolves through the same `Settings`;
a control would need to separate the harness's coordinates from the ambient default.

**Leads (optional).** A harness-level sentinel default, or moving dated targets out of code defaults.

**Bears on:** every run on the shared cluster; retargeting; [SC8](README.md#method).

<a id="dta-002"></a>

## DTA-002 — The lifecycle owner covers databases only; killed runs and cluster-level test effects leave what it cannot see

**Lineage.** Formerly "The native semantic harness fuses isolation, head bootstrap and
migration-as-subject in one per-test fixture". [DA-019](../audit/boundaries-and-composition.md#da-019)
routes residue here.

**Closed, with positive evidence.**
- *Repeated head bootstrap per test.* `semantic_head_template` is session scoped
  (`tests/conftest.py:176-196`) and `semantic_db_engine` clones it (`tests/semantic/conftest.py:27-34`).
  `pytest --setup-plan` on `test_query.py` shows one `SETUP S semantic_head_template` and `SETUP F
  semantic_db_engine` per test. A revision now adds one session-build increment, not revisions × tests.
  ADR-0032 records the accepted interpretation, which also settles the prior open question about
  "fresh" clones.
- *No controlled-revision route.* `semantic_database_at` exists (`tests/semantic/conftest.py:48-57`) and
  carries data (`test_execution_projection.py:220`, `test_native_closure.py:336-498`). Its limits are
  in [DTA-020](evidence-and-discrimination.md#dta-020).

Static fan-out at this baseline: 332 nodes clone the head, 7 use `semantic_database_at`, 1
`semantic_bare_engine`, 3 `semantic_absent_database`, 83 the legacy `db_server` closure, and 448 are
marked `db`.

**Principles:** FP-05, DP-19, DP-21; H25; companion §6. **Subject:** implemented
(`scripts/native_test_support.py`; `tests/semantic/test_alternate_principal.py:15-90`).

**Diagnosis (what remains).** ADR-0032 says one test lifecycle "owns leased names, creation, cleanup and
residue". `PgAdmin` scope is databases, and two exposures fall outside it.
- *Killed runs.* The controller handles signals and forwards them to the pytest group, SIGTERM then SIGKILL
  (`scripts/test_receipts.py:77-87`, `:212`, `:220`), but the pytest process has no handler. So the route's own drain, like
  `faulthandler_exit_on_timeout`, skips fixture `finally` blocks. Stamped residue goes at the next session's
  sweep (`tests/conftest.py:171`, `:218`). A kill between `CREATE DATABASE` and the stamp
  (`scripts/native_test_support.py:207-209`) leaves an unstamped database that sweep correctly never
  adopts and that needs manual removal.
- *Cluster-level effects.* `test_alternate_principal.py` creates a role, appends to
  `/etc/postgresql/18/corpus/semantic_hba.conf` and `pg_ident.conf` through `sudo -n`, and reloads the
  cluster shared with real targets. Its careful `finally` does not run on a kill, and the sweep cannot
  see roles or auth rows. A missing non-interactive sudo raises `CalledProcessError`, which classifies as
  `failed`, not `blocked` ([DTA-003](#dta-003)).

**Consequence.** A killed run leaves a role and two auth rows on the shared cluster, and possibly an
unstamped database. These are small and bounded, but no owner would notice them.

**Footprint.**
- *Known:* the sites above. A search of the tests for `CREATE ROLE|DROP ROLE|ALTER SYSTEM|pg_reload_conf`
  finds only this module.
- *Observed:* a read-only query on 2026-10-30T09:42:21-04:00 found no `cs_sem_*` or `ci_test_*` database,
  and a later query found zero `cs_reader_%` roles, so there is no current accumulation. The two auth
  files are not readable by the operator, so their rows were not inspected.

**Counterevidence.**
- A real alternate login is the right claim, and a double would not establish it (companion §5).
- Values are regex-validated, and an invalid reload keeps the prior configuration.
- Any residue is an unprivileged role tied to a dropped database.

**Bears on:** runs interrupted by the hang watchdog; SC7.

<a id="dta-003"></a>

## DTA-003 — The qualification route records context it did not use and misclassifies undeclared prerequisites

**Lineage.** Formerly "The qualification route cannot separate required passes from skipped, blocked,
hung or unreplayable outcomes".

**Closed, with positive evidence** (`just test-all` now runs `scripts/test_receipts.py`, not `just check`;
`justfile:18-19`).

| Prior loss | State at this baseline |
|---|---|
| Zero Rust tests report as a pass | Closed. `--no-tests=warn`; `classify_rust` returns `not_run`, `empty-selection`, `functional_coverage: False`, which the receipt shows |
| Skips fold into a count | Closed. `-rA`, and any skip is `blocked` unless `qualification_optional`. No test emits that property, so every skip is blocked, which is conservative. Corpus skips carry a recorded prerequisite (`tests/conftest.py:105-112`) |
| A hang yields no outcome | Closed. `faulthandler_timeout=900` with exit, a parent deadline covering collection, `phase_start` events, and real-child controls |
| Generated cases are not replayable | Closed. Environment and flag both select `ci`; the receipt records `derandomize=True`, `database=None`, `print_blob=True`, `max_examples=300`. `just py-test` stays `dev` by declared design |
| No selection unit for the native union | Capability exists, unconsumed. `DB_FIXTURES` (`tests/conftest.py:65-82`) covers every native route, and no recipe uses the marker |

**Principles:** FP-05, DP-21, DP-22, CI-04 and CI-10 by analogy; companion §6.
**Subject:** implemented (`scripts/native_test_support.py:665-688`; `tests/llm/test_cascade.py:232-235`;
`tests/semantic/test_alternate_principal.py`).

**Diagnosis (what remains).** The sixth prior loss, ambient provider context, is only partly closed, and a related gap has appeared.
- *Context names what was not used.* `record_server_context` reports resolved `Settings()`, so the
  receipt's `database.url` names `corpus_efficiency_20261030`, which no fixture test used. Only native
  fixtures record context, `ImportError` is swallowed (`:677-680`), and zero `native_contexts` on a native
  run is not flagged. Head revision and role state are unrecorded.
- *A prerequisite the route cannot see becomes a product failure.* `test_the_s0r2_sets_on_the_spike_pages`
  has no `corpus` marker. Its name and `tests/llm/conftest.py:4-6` imply vendored pages only, but
  `located_sets` builds a view for every unit first (`tests/llm/test_cascade.py:200`). Computed from
  `llm/data/units.json`, H1–H3 and H6 are on `special/Pareto.html` and H4–H5 on `special/ChiSquare.html`,
  and neither is vendored. So without the corpus it raises `FileNotFoundError` before its filter runs,
  and the route reports `failed` where 14 marked nodes report `blocked`. With the corpus it is a strict
  subset of `test_the_s0r2_sets_on_every_page`. The sudo prerequisite in [DTA-002](#dta-002) behaves the same.

**Consequence.** A fresh checkout reports a false product failure. A receipt reader could take the recorded
URL for the tested target.

**Footprint.**
- *Known:* the sites above.
- *Inferred:* the C5-2 failure, from source and the computed page map. It was not executed, because the
  corpus exists here. That is exactly the condition that hides it.

**Counterevidence.** The failures are conservative rather than silent, and they never manufacture a pass.
`run` passes no required manifest, so `just test-all -k x` reports `passed` scoped to its recorded argv;
AGENTS.md already warns that a bounded pass establishes only that scope.

**Bears on:** receipts read later; fresh checkouts and worktrees.

## Observations recorded without a finding

- **Serial execution (H21, H22).** The suite is serial, and no plan asks otherwise. By the receipt, 66% of
  recorded time is not database time, and one node takes 17%, which bounds any speedup unless restructured.
  Real obstacles exist: order-dependent pairs on module state in `tests/test_db_fixtures.py:17`, `:50-55`, a
  shared `max_connections = 100`, and a clone needing several admin connections. No speedup is claimed.
- **Unattributed exit time.** The receipt shows 53.7 s between the last `logfinish` and process exit: about
  12.5 s of `-rA` output, then about 41 s with no output, presumably interpreter shutdown. That is about 5% of
  wall time, unprofiled.
- **`CREATE DATABASE` strategy.** `scripts/native_test_support.py:207` names none. PostgreSQL 18 documents
  `WAL_LOG` as the default and as suited to small templates, and it avoids `FILE_COPY`'s checkpoints. No finding.
- **`NullPool` clones.** Measured clone setup and teardown are small. Connection establishment per clone
  (about eight administrative connections) is not separated from it. No material shortfall established.
- **One focused cost.** `tests/ingest/test_html.py:198-207` pays 21.27 s, 99.8% of its module, for one
  branch, because an 800 KB input continues through the complete rendition after the delimiting decision.
  Its 100 µs deadline also governs the "fine" block, a suspected spurious failure under contention, not
  observed. Part of the claim is that the rendition survives, so some end-to-end run is legitimate.
- **Worker identity.** The plugin and classifier carry a few lines for worker identity with no participant
  today (`scripts/qualification_plugin.py:37`, `scripts/test_receipts.py:408`).
- **Process-script boundary.** `AGENTS.md:98` says process scripts are stdlib-only, while
  `scripts/native_test_support.py` imports SQLAlchemy and the package, and `scripts/qualification_plugin.py`
  imports pytest and Hypothesis. Their placement is coherent; the sentence is stale.
- **[I2A-01](../../plans/phase-0_2026-10-28.md#11-findings-disposition).** The forked `cpu_count` pool no
  longer exists at this path: the worker lifecycle moved to `tests/math_support.py:152-213` with a `spawn`
  context, at most eight workers, per-submission deadlines and real controls in `tests/math/test_workers.py`.
  The phase-0 row still reads open. Its disposition is that owner's.
