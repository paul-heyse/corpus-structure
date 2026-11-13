# Design review — test system target design

**Design / target review · 2026-11-13 · principal reviewer: delegated `design-reviewer` (fresh
context; author of neither the audit, the tests nor the 2026-11-12 review).** Supporting document:
[options and classification](test-system-target-design/options-and-classification.md), which
records what becomes of every option of the superseded review and the per-family planning leads;
it routes back here for every judgment.

This review **supersedes** the
[design review of test architecture and efficiency, 2026-11-12](design_review_test-architecture-and-efficiency_2026-11-12.md)
and its [efficiency opportunities](test-architecture-and-efficiency/efficiency-opportunities.md).
Its findings F01–F03 keep their identities and meanings here; its rule impacts RC01 and RC02 keep
their identities with revised content (§12).

This review is evidence, not authority. Every remedy is **Proposed**. Source facts are
**Interface-checked by source inspection, 2026-11-13**, at `main` `a5ea7c4dc` unless a sentence
names a contributor. Durations are **Measured** from stored `ci test` results read by the test
audit on 2026-11-13 (runs dated 2026-11-10 to 2026-11-13, on a workstation shared with other
sessions); they are orders of magnitude, not a benchmark. No test, build or database operation was
run for this review, and no speedup is claimed anywhere.

**Path convention.** Paths beginning `tests/` or `src/` are relative to `python/corpus-structure/`.
Repository-root test paths are written as root `tests/…`; other root paths begin with `scripts/`,
`ops/`, `docs/`, `conftest.py`, `pyproject.toml` or `uv.lock`. Citations are `path:line` as read at
`a5ea7c4dc`.

---

## 1. Scope, outcome and coverage

| Field | Value |
|---|---|
| Subject | The test system: package `tests/`, root `tests/`, every `conftest.py`, `scripts/native_test_support.py`, `scripts/test_receipts.py`, `scripts/qualification_plugin.py`, `src/corpus_structure/cli/testing.py`, the pytest/xdist configuration in root `pyproject.toml`. Three bounded production seams that test findings depend on: standalone interpretation-context preparation, data-operation lease expiry, CPU lifecycle grace periods. Production is otherwise read only as the contract tests protect |
| Baseline | `main` `a5ea7c4dc` (clean at session start). Between the audit's publication `28b4a53db` and this baseline, seven commits changed six test files, all declared-data-operations tests; the shared infrastructure, the audit pages, ADR-0032 and the declared-data-operations plan are unchanged. Where the footprint moved, this review cites the baseline |
| Audit consumed | Test audit publication `28b4a53db` ([account](../test-audit/README.md)): DTA-001, 006, 009, 018, 024–036, the README's observations for the declared-data-operations plan owner, the [measurements](../evidence/2026-11-13_test-audit-refresh/README.md) and the four contributor reports behind them. The broad production audit is not refreshed; this is a test-scope engagement with three bounded production seams |
| Standard | [`standard.toml`](../design_principles/standard.toml): core principles 3.3, [efficient-architecture heuristics](../design_principles/core/efficient-architecture-heuristics.md) 1.0, [test-assessment companion](../design_principles/core/test-assessment.md) 1.2, review template 3.3, [binding](../design_principles/binding/corpus-structure.md); code-intelligence profile 1.4 for source-capture tests only |
| Tier · purpose | Design · target |
| Focus (operator, 2026-11-13) | Holistic and unconstrained: open library scope, all principles. Pressures named by the operator: the execution time of focused runs and of the full union is hindering development pace; the test architecture should align with the target design of the declared-data-operations plan |
| Outcome wanted | One coherent target design for the test system and the set of changes that fully addresses every open finding, specific enough for plan creation |
| Maturity | Design stage; one operator; agents make the edits; the declared-data-operations (DDO) plan is mid-execution (DDO-03–05 partial, DDO-06–12 open) and is the fastest-growing source of new tests |

### Functional intent and workload premise

The test system gives the operator and agents trustworthy, discriminating and understandable
evidence that the product's guarantees hold: native custody and refusals in PostgreSQL 18,
restricted principals, provenance, served answers, cold determinism, and now the declared
data-operation model and its kernel. It must also be fast enough to sit inside two loops: an
edit–test loop in which an agent reruns a focused selection many times an hour, and a full union run
at each complete scope. Receipts must say truthfully what ran and with what evidence class.

Workload premise, from that intent and the measured runs:

- **Focused runs:** one to a few dozen tests, very often native, through `uv run ci test -- PATH`.
  Today a one-test native run took 104.5 s wall, 93.3 s of it setup (run `6a6894c8…`); a narrowed
  run carries about 7.5 s of fixed overhead at the median (4.9–17.3 s).
- **The full union:** about 6,000 ordinary tests plus the fault lane on 16 xdist workers; run
  `2e2a0e30…` took 1,503 s wall with workers busy 96% of the time, so it is bound by total work.
  Setup is 36% of worker time and is concentrated in about 335 tests.
- **Growth:** the semantic migration chain holds 249 revisions at the baseline and
  `semantic_alembic/versions/` holds about 1.3 GB of frozen native artifacts (about 966 MB JSON,
  221 MB text, 96 MB SQL; `du`, 2026-11-13), and a head build executes that chain; each native
  candidate adds to it. The data-operation tests grew to 35 modules; seven modules now import the
  storage test module and the kernel admission sequence is written out in six.
- **Envelope:** a 16-core, 32-thread workstation shared with GPU work and other agent sessions; the
  dedicated cluster `18/corpus` (`max_connections = 256`, `shared_buffers = 8GB`,
  `synchronous_commit = off`, `ops/postgresql/corpus.conf:6,13,30`) on ext4, which also holds the
  persistent development database.

### Method and coverage

I loaded the standard, the companion and the binding; read all four audit pages, the evidence
README, the four contributor reports and the four prepared input reports; read the superseded review
and its supporting document in full; and opened the decisive sources at the grain cited: the native
lifecycle (`scripts/native_test_support.py` in full), the package and semantic conftests, root
`conftest.py`, the pytest configuration, the managed route's argument building and selection
handling (`scripts/test_receipts.py:320–360,1420–1600`, `cli/testing.py:400–850`), the serving seed
(`tests/semantic/serving_scenarios.py:215–345`), the DDO kernel and its importers, the identity,
binding and wire sites behind DTA-033/034, the interpretation-context call tree
(`analysis_contracts.py:400–500,630–665`, `contracts.py:1147–1182,1380–1446`, `grammar.py:975–1000`),
the data-task guard and lease sites, the CPU constants and lifecycle tests, the migration chain's
imports and frozen-artifact pattern, ADR-0032, ADR-0048, D3's native-test section, D9 §4 and the
DDO plan's qualification text and recorded campaigns. Installed pytest-xdist 3.8.0 source was read
for the run identity; other library behavior is taken from the library-mechanics report with its
labels.

Thin areas, stated as limits: most test bodies outside the DDO modules were not reread; per-family
isolation and seed classifications in the supporting document come from a contributor's AST
heuristic plus partial reads; `domain_scenarios.py` beyond its first 200 lines, `reference_scenarios.py`,
`pdf_integration_support.py` and `witnessed_scenario_support.py` were not read in depth; nothing was
profiled. Where a judgment rests on a contributor, it says so.

---

## 2. Integrated assessment

The assurance core of the test system is strong and constrains every correction. Native tests get
real logins and real commits on fresh clones of a sealed deployment whose database policy is
captured, replayed and compared before exposure (`scripts/native_test_support.py:306–371`; ADR-0032).
Receipts keep passed, failed, blocked, inapplicable and incomplete apart, record native acquisition
context per connection, and route setup prerequisites to `blocked`. Expectations are mostly authored
independently of production: identity vectors, literal Arrow rows, analytic forms, hand-authored gold,
and in the DDO tests hand-authored compiler node ids, graph topologies with a self-loop and a cycle,
literal canonical framing and independent wire bounds. The serving seed
(`tests/semantic/serving_scenarios.py:241–344`) already shows a sealed committed scenario cloned per
consumer. None of the corrections below gives any of that up.

The problems have six structural causes.

**C1 — Preparation lifetimes do not follow what the preparation depends on.** Each preparation in a
native test depends on different things and so stays valid for a different span:

| Preparation | What it depends on | When it changes | Current lifetime |
|---|---|---|---|
| Deployed semantic head | The migration chain, the few product modules the chain imports, library versions, the server, `cs_template` and the semantic roles | When a migration is added or changed; almost never otherwise | One per pytest process, so one per worker per run (`tests/conftest.py:255–260`) |
| Pure prepared release | Bundle, dependencies, profile, compiler stack, and the product code loaded in the process | On a product edit, which never happens inside a process | Per process, eight-entry LRU (`src/corpus_structure/semantic/prepare.py:592`); module fixtures per worker |
| Committed scenario | Head, product code, test support code and the recipe's inputs | On nearly every implementation edit | Per test or per case, often inside the test body |
| Implementation determinants (production) | The installed code and data bytes | Between processes | Re-read on every interpretation-context call (`analysis_contracts.py:409–485`) |

The head is the only large preparation whose validity is independent of ordinary product edits, yet
it has the shortest lifetime of all relative to its validity: every worker of every run rebuilds it
(DTA-024). Committed scenarios that are identical across cases or consumers are rebuilt through real
producers (DTA-025, DTA-031, F03); pure preparation is rebuilt on every worker that touches it
(F02); focused controls build stages they never read (DTA-018); and production re-reads about a
hundred files, a spaCy model directory and the whole package tree per call (DTA-032). These are the
dominant execution-fit defects, and they grow with workers, cases and migrations.

**C2 — A test cannot say what isolation its claim needs, so every native check takes the most
expensive route.** The lifecycle offers a fresh committed clone (`semantic_db_engine`,
`tests/semantic/conftest.py:27–34`) and a rolled-back connection on a shared clone (`db`,
`tests/conftest.py:279–291`), but nothing names the distinction or enforces the cheaper one's premise.
Read-only checks, DDL installed in one transaction, permission refusals on an empty database and
rollback-only refusal families all take fresh clones, and the DDO tests do so through a copy of the
fixture (DTA-025, DTA-031).

**C3 — Negative and absence evidence does not always prove reach and reason.** Some refusal controls
would pass if their guard were removed (DTA-001), one absence control passes under either order
(DTA-027), and some presence and count assertions stand in for preservation (DTA-006). C2 and C3
compose: a rolled-back case on a shared scenario is only safe when each case proves the scenario
still admits the clean input and names the exact refusal.

**C4 — Scenario and support ownership is decided by where a name was first written.** Scenario
choice depends on fixture-name overrides resolved by import; test modules serve as libraries for
other test modules, including across non-package directories where the file loads twice; production
assembly sequences are hand-copied; superseded lifecycle machinery survives and three database
names escape the sweep (DTA-009, DTA-029, DTA-030, F01, F04). For the DDO tests the storage test
module is the de facto support library for seven others (DTA-031's support footprint).

**C5 — Evidence class and prerequisites are decided in test bodies.** One provider identity passes
on a controlled branch when an asset variable is unset (DTA-028); provider skips run after
expensive fixtures (DTA-018).

**C6 — The DDO transition has no test-side plan of its own.** Required behavior is asserted
through machinery the target removes (DTA-035); the current product identity is checked only
against itself and two doubles sit below wire validation (DTA-033, DTA-034); and the DDO-12 union is
defined by obligation rows with no evidence mapping (DTA-036, refined). The plan's own statements
about where native checks run disagree.

Two further timing couplings are independent: CPU teardown controls wait out real five-second grace
periods and write interpreter-private executor state (DTA-026), and four DDO lease tests sleep a
second each (no finding; §4.6).

**Overall judgment: Revise.** The assurance architecture is right; its physical realization does
not fit either loop the workload premise names, and parts of the evidence contracts are not yet
honest enough to carry the sharing that would fix it. The target (§4) is one coherent lifecycle with
four named isolation classes, a deployment reused under a complete content key, per-worker sealed
scenario seeds keyed by recipe values, owned support modules that use the DDO target's own
concepts, one refusal contract, evidence class in test identity, and one bounded production change
(an implementation snapshot read once per process). A1–A4 are violated for the current system and
satisfied by the proposed route (§15).

---

## 3. Responsibilities and semantic ownership

The test system has its own domain: preparations with validity premises, scenarios defined by
recipes, isolation classes, refusal reasons, evidence classes, prerequisites and qualification
obligations. Today most of these are implicit.

| Concept | Current owner and how it is decided | Target owner and representation |
|---|---|---|
| Deployed head | `PgAdmin.semantic_template` plus a session fixture named per process id (`scripts/native_test_support.py:612–630`, `tests/conftest.py:255–260`) | The same owner, one operation keyed by a computed deployment key; reused across runs for narrowed runs, run-private for qualification (§4.1) |
| Database names, leases and sweep recognition | Ad hoc names in five places (`ci_test_<pid>[_n]`, `cs_sem_<kind>_<pid>_<hex12>`, `cs_ddo_case_<hex12>`, `cs_sem_m1_attributed_<hex12>`, `cs_sem_test_<hex20>`); a sweep with its own patterns and a lock key that differs from the lease key (F01) | One naming function in `native_test_support.py` that yields name, lease key and sweep rule for every kind |
| Isolation need | Implicit in which fixture happens to be requested | Four named classes: pure, read, rollback, commit (§4.2) |
| Scenario recipe | `private_source_options` fixture overrides resolved by import, indirect parameters, a `callspec` read | A frozen recipe value at the call site; it keys seeds and memoized preparation |
| Scenario seed | One bespoke serving seed in a test-support module | One seed operation in the lifecycle owner, per worker, keyed by recipe; the serving seed migrates to it |
| Pure preparation | Production LRU per process; module fixtures per worker | The same production cache, plus a recipe-keyed memo in support; affinity groups for designated expensive preparation |
| Scenario builders and doubles | Support modules for some families; for others `test_*` modules imported by other test modules | Support modules only, imported by canonical absolute name |
| DDO test support | `tests/semantic/test_data_operation_storage.py` and four other test modules | DDO support modules named for the target's concepts: compiled model, admitted kernel, subject context, demand and attachment, purpose principal, wire-checked double, binding case table |
| Refusal reason | Inline idioms from a bare exception class to per-case reason tables | One contract — reach, reason, effect — with expectations at the call site |
| Evidence class and prerequisite | An environment variable in one body; body-level skips | Test identity plus a prerequisite marker decided before setup and recorded in receipts |
| Implementation determinants (production) | Re-read per call by three helpers | One process snapshot read at the entry boundary `trusted_execution_inputs` already names, with an explicit override seam |
| DDO-12 union | Prose path lists of bounded campaigns (accurate receipts) and an obligation table without evidence | The full ordinary and fault lanes on frozen source, a prerequisite-satisfied provider run, and an evidence column in the plan's obligation table |

---

## 4. Target design

### 4.1 Preparation lifetimes and their owners

#### Options compared

| Option | What it removes | What it keeps | Ownership, invalidation and recovery | Verdict |
|---|---|---|---|---|
| (a) Run-scoped head: one per run, built by the first worker under an exclusive lease, shared by the run's workers, dropped at run end | Duplicate and concurrent builds within a run (16× in a full run) | A full build in every run, about 40 s even on one worker, rising with the chain | Needs a run identity in every worker and a run-end owner; a killed controller leaves residue for the sweep | Subsumed by (b) |
| (b) Content-keyed head: one per deployment key, reused by any run whose key matches | The build from every run after the first that shares a key, including focused runs during product-only edits | One build after each migration change | The key must be complete; retention and sweep replace run-end cleanup; publish by rename makes a partial build invisible | **Selected**, with run-private builds for qualification |
| (c) Per-worker heads with less work inside | Nothing structural | The build per worker per run and its contention | Simplest; no new ownership | Rejected: it cannot reach either loop's target |

Option (b) is the only one that removes the floor a focused run pays before its first database test,
which ADR-0032 rejected as a persistent cache "unnecessary for this session-local contract". The
workload that judgment fitted has changed: workers arrived after it, the build is measured at
37–41 s on one or two workers and 87–92 s each when 16 build at once (contributor reading of event
timestamps, runs `cbcecbae…`, `43dfffb3…`, `55303ce0…`), and the chain it executes grows with every
native candidate. ADR-0032's own revisit trigger — session preparation ceasing to fit the supported
test workload — is met (RC01).

Scenario seeds and pure preparation have the opposite validity profile: they depend on the product
code and test support, which change on nearly every implementation edit. A complete cross-run key
for them would almost never hit in the edit–test loop, and an incomplete one would be a G6 failure.
They therefore stay inside a process: seeds per worker, pure preparation in the production cache.

#### Selected design

```
cs_template (provisioned)
  │  build once per deployment key, publish by rename, seal
  ▼
cs_sem_head_<key16>           reused by narrowed runs with the same key (shared usage lease)
cs_sem_head_<key16>_<run8>    run-private, for unnarrowed (qualification) runs
  │
  ├─► commit class:   fresh clone per test (today's contract)
  ├─► read/rollback:  one per-worker session clone, rolled-back transactions per test
  └─► cs_sem_seed_<pid>_<hex12>   per worker, per recipe value, built lazily by real producers,
        │                          sealed, files read-only, dropped at worker end
        ├─► commit class:   fresh clone per consumer
        └─► rollback class: one family clone, rolled-back transaction per case
```

**The deployment operation.** `PgAdmin` gains one operation, `deployment(key, *, reuse)`, which the
session head fixture calls instead of `semantic_template(name)`:

1. Compute the name: `cs_sem_head_<key[:16]>` when reusing; `cs_sem_head_<key[:16]>_<run[:8]>`
   when a run-private head is required, where `run` is xdist's run identity (`testrun_uid`,
   `.venv/…/xdist/plugin.py:400–407`; generated locally under `-n 0`).
2. Take the shared usage lease on the name (`pg_advisory_lock_shared` through `PgAdmin.lease`), held
   for the process's session. Then take an exclusive build lock on a second key derived from the
   name. Two keys are necessary: a builder must not wait for other runs' usage leases to end, and a
   sweep must not drop a head any process is using or about to use.
3. If an owned, sealed database with that name exists, release the build lock and use it; read its
   policy from the catalog as today.
4. Otherwise create `cs_sem_build_<pid>_<hex12>` from `cs_template` through the acknowledged
   creation path, run the existing extension and namespace checks and `upgrade(conn)`, capture the
   policy, seal (`ALLOW_CONNECTIONS false`), dispose every connection, and publish with
   `ALTER DATABASE … RENAME TO` the final name. The ownership stamp is keyed by database OID
   (`src/corpus_structure/core/db/ownership.py:87–89`), so the rename keeps disposal authority.
   A crash at any point leaves only a `cs_sem_build_*` database, never a partial head under the key
   name; the next waiter builds afresh. Release the build lock.
5. Never drop the head from a worker. Retention belongs to the sweep (below).

**The deployment key.** A SHA-256 over a canonical JSON of:

| Component | Why | How |
|---|---|---|
| The chain directory | Every revision, its frozen artifacts and `env.py` | Content digest of every file under `semantic_alembic/` (about 1.3 GB today). If computing it becomes material, the frozen artifacts can be represented by the SHA-256 digests their revision files already pin (for example `NATIVE_UPGRADE_SHA256` in `semantic_ddo_renewal_v1.py`) plus size and mtime for unpinned files; a fresh build verifies the pins either way |
| The chain's machinery | Revisions import `corpus_structure.semantic.native_objects` (183 files), `alembic_native` (73), and singly `alembic_defaults`, `alembic_indexes`, `metadata`, `migrations` and `corpus_structure.schema.relational` (`0134_local_enrichment.py`); these import further package modules | Content digests of the static import closure within `corpus_structure`, computed by an AST walk of import statements (module and function level) from every chain file, resolved with `importlib.util.find_spec`; plus `scripts/native_test_support.py`, which holds the build procedure |
| Libraries and interpreter | Alembic, SQLAlchemy, psycopg and pglast execute the chain | Digest of `uv.lock`; `sys.version` |
| Server and cluster | A re-provisioned template or recreated role changes what a build produces | `server_version_num`, `pg_control_system().system_identifier`, the OID and extension versions of `cs_template` (`PgAdmin.installed()`), the OIDs of the semantic principals |

Computing the closure rather than listing it is what makes the key complete as the chain evolves: a
revision that begins importing another product module enters the key automatically. A cheap control
can check that the computed closure contains the modules above, so a broken walk fails loudly.

**Reuse and qualification.** Narrowed managed runs and plain pytest reuse; the unnarrowed managed
route (`narrowed is False` in `cli/testing.py:586–618`) builds a run-private head, so evidence of
record never rests on cross-run reuse. Its cost is one build in a run that already takes about 25
minutes. Cold deployment controls (`test_migration_chain.py`, `test_model_deployment.py`,
`semantic_bare_engine`, `semantic_database_at`, CLI initialization) keep executing the real chain in
every run, as ADR-0032 requires. Receipts record the head name and whether this run built it.

**Sweep and retention.** One naming function gives every kind its name pattern, lease key and sweep
rule. The sweep drops: unleased `ci_test_<pid>` and `cs_sem_<kind>_<pid>_<hex12>` residue, including
seeds and build residue; unleased run-private heads; and unleased reusable heads beyond the newest
three by database OID, which keeps the current key, a sibling worktree's key and one predecessor.
Head retention runs inside the deployment operation after it holds its own usage lease, so a process
never evicts the head it is about to use. Residue still connected by a dead client's backend is skipped and reported, not raised (F04). The
`cs_tpl_` scheme and its comment stamp are removed (DTA-030); the ownership stamp stays the only
comment, so retention is by count, not last use.

**Scenario seeds.** One seed operation in the lifecycle owner replaces the serving seed's bespoke
lifecycle and generalizes it (F03, DTA-025, DTA-031):

- **Key.** A frozen, hashable recipe value (§4.3), plus the head it was cloned from.
- **Build.** Lazily on first use per worker: `database("cs_sem_seed_…", head)`, then the real
  builder through actual purpose engines, then the existing posture checks the serving seed applies
  (`serving_scenarios.py:259–291`): policy equals the head's, client-free, sealed. Files the seed's
  rows reference go under `tmp_path_factory.mktemp("seed-…")` and are made read-only.
- **What a seed may contain.** Committed state before the claim boundary only: no claimed task, live
  lease or attempt (`build_record_source` claims at `native_record_fixtures.py:499`; `pdf13_db` stores
  its original under a live lease); no session-level state; nothing produced under a process-global
  override that the recipe does not name. A builder that patches a provider must declare the patch
  in its recipe value and scope it to the build with `pytest.MonkeyPatch.context()`; a builder never
  runs under an implementation override (§4.6). Consumers that assert a time relation between seeded
  stamps and their own clock, or absolute generated identifiers not recorded in the descriptor, are
  not seed consumers.
- **Consumers.** A commit-class consumer receives a fresh clone with policy replay, then takes its
  own claims, so lease freshness and attempt numbering are as today. A rollback-class family
  receives one family clone of the seed and a rolled-back transaction per case.
- **Lifetime.** Per worker. Each worker's descriptor (prepared release, identifiers, paths) stays in
  its own process, so nothing needs to be serializable. Seeds shared across a run's workers remain a
  candidate (old D7), with the trigger that full-run receipts show per-worker seed builds as a
  material share of setup after this lands.

**Pure preparation.** It stays in the process, where `PreparedRelease` lives (it holds pydantic
adapters, an `RLock` and caches, so it is not plainly picklable). Three changes reduce its repetition:
a recipe-keyed memo in support for input assembly ahead of `prepare_release` (old S2); fixture-closure
affinity groups for designated expensive module or session preparation, keyed by the preparation
value so cross-module consumers share one worker's cache (F02); and the implementation snapshot,
which removes per-call disk reads from every interpretation context (DTA-032). A seed's consumers
could reopen its persisted release through the production archive reader (`releases.open_release`,
database-scoped cache) instead of re-preparing; that remains a candidate, because archive-opened
releases are read-only and some consumers admit or bind.

**What consumers stop doing.** Naming databases, choosing lifetimes by fixture accident, rebuilding
identical kernels and scenarios, importing fixtures from test modules, and patching implementation
readers.

**Preserved guarantees.** Fresh committed clones with real logins for every claim that needs them;
policy capture, replay and comparison for every clone, seed and seed clone; authenticated, unforced
drops; refusal of setup when replay authority is unavailable; real-chain cold deployment controls;
a sealed, client-free source for every clone (`CREATE DATABASE … TEMPLATE` refuses a connected
source); receipts that distinguish seed origin from clone context.

**Cases that could go wrong.** *A run during a migration edit:* workers starting after the edit
compute a new key and build another head, so one run can use two heads, as today two workers can
deploy two chains; frozen source at qualification excludes it. *Two concurrent runs with one key:*
the second waits on the build lock, then shares; neither waits for the other's usage lease.
*A crash mid-build:* the build lock ends with its session; the residue is swept; the head name
never existed. *An incomplete key:* bounded to development feedback, because qualification builds
run-private heads and cold deployment controls run every time. *A sweep while a builder waits:* the
waiter holds a shared usage lease, so the sweep's try-exclusive fails and it skips.

**Settling evidence.** None is needed before planning. During implementation, the first receipts
show each worker naming one head and a later run reusing it; the head's on-disk size, observed once,
settles whether three retained heads are acceptable.

### 4.2 Isolation classes

The fixture a test requests states the isolation its claim needs. Names are illustrative.

| Class | The test receives | Base | Premise enforced by | Valid for | Not valid for |
|---|---|---|---|---|---|
| **pure** | No native resource | — | Absence of any native fixture | Compiler, codec, wire, preparation and routing claims | — |
| **read** | A `Connection` in a `READ ONLY` transaction that is always rolled back | One per-worker session clone of the head (or of a seed) | PostgreSQL refuses every write, DDL and temporary-table creation with SQLSTATE `25006` | Literal-argument calls of installed functions, catalog reads, identity vectors | Privilege refusals of writes: the read-only check runs before the privilege check, so `25006` masks `42501` |
| **rollback** | `Connection` objects only, never an `Engine`: a writable outer transaction always rolled back, savepoints for positive controls, and restricted-principal connections each inside its own rolled-back transaction | The same per-worker clone, or a family clone of a seed | The fixture asserts its outer transaction is still active before rolling back, so a commit through it fails the test; each case proves reach and reason (§4.4) | DDL installed and used in one transaction; refusal families whose every write rolls back; permission refusals on an otherwise empty database; single-session refusals at `SERIALIZABLE`, with isolation set per case before `begin()` | Separate-login visibility, commits, races, cancellation, `NOTIFY`, session-level advisory locks or settings, assertions on absolute generated identifiers, product code that opens its own connections |
| **commit** | An `Engine` on a fresh committed clone, with purpose engines | The head, or a seed | Its own database (today's contract) | Everything else | — |

There is no implicit default. Today's `semantic_db_engine` becomes the commit class under a name that
says so, and the per-worker clone behind `db` becomes the base of the read and rollback classes. A
misclassified test fails loudly rather than passing vacuously: a hidden write in the read class
raises `25006`; a commit through a rollback-class connection fails the active-transaction check;
a leaked effect from a production path that opened its own connection is exposed by the next case's
positive control and absence checks, and the case passes alone.

The challenge cases the inquiry named resolve as follows. *Refusal tests that commit a claim before
the refused step* (the DDO invalid-output, fence-renewal and forged-graph families, and
`test_witnessed_applicability_native.py:172–197`) stay in the commit class, now on a seed clone, so
the expensive build disappears while the committed claim stays real; they join the rollback class only
if every pre-step moves inside the case transaction. *`SERIALIZABLE` refusals* fit the rollback
class when the refusal is a guard's and the isolation level is set on the case connection; a refusal
that is a serialization failure between two sessions needs the commit class. *Tests that redefine
functions* fit the rollback class when the redefinition need not be visible to another login,
because PostgreSQL DDL is transactional and each case connection is new; otherwise the commit class.
*Permission tests on an otherwise empty clone* (`test_identity_exclusions_native.py:240`,
`test_domain_operations.py:246,254`, `test_occurrence_context.py:315`, by a contributor's reading) fit
the rollback class with principal connections, not the read class, and pin `42501`.

One existing consumer commits DDL to the shared clone (`tests/db/test_lifetime_native.py:162–164`);
it moves to the commit class so the shared clone's base state equals the head by construction.

### 4.3 Scenario and support ownership

**Placement and import rules.**

1. Shared builders, fixtures, recipe values and doubles live in support modules whose names do not
   start with `test_`, imported by their canonical absolute name: modules in the `semantic` and
   `methods` packages (`tests/semantic/__init__.py`, `tests/methods/__init__.py`) or package-root
   modules on the configured `pythonpath` (`pyproject.toml:74`), as `domain_scenarios.py`,
   `serving_scenarios.py` and `pdf_acceptance_support.py` already are. Support modules are never
   collected, so they load once.
2. No test module imports from another `test_*` module, and no module in a non-package directory
   uses a relative import. Under `--import-mode=importlib` (`pyproject.toml:63`) a file in a
   non-package directory is named from its rootdir-relative path, so `..semantic.X` from
   `tests/orchestrate/` or `tests/acceptance/` loads `semantic/X.py` a second time under another
   name (reproduced by the library-mechanics contributor for `tests/acceptance/conftest.py:3–4`).
   Making every test directory a package is not a safe alternative: `tests/math/` would become a
   top-level package named `math`, colliding with the standard library module.
3. Fixtures needed across directories — the lifecycle, the isolation classes and the purpose
   engines — live in the package `tests/conftest.py`. The acceptance conftest's re-export of
   `semantic_db_engine` and `semantic_writer_engine` then disappears.
4. A scenario is selected by a frozen recipe value visible where the case is declared, passed by
   indirect parametrization or a factory fixture. The eleven `private_source_options` overrides and
   the `callspec` read go (`native_record_fixtures.py:782–819`, `test_structural_native_replay.py:57–70`).
   The recipe value is also the seed key and the memo key.
5. Large builders become staged compositions with frozen stage outputs — release persisted; views
   published; run and task created; claimed; completed or sealed — and the full builder is their
   composition, as the math session fixtures already are (`tests/math/conftest.py:25–61`). The seed
   boundary is the last stage before a claim. Builders that are the subject of a test (native record
   publication, PDF build) keep building, because the build is their claim.
6. A double that disables production verification (`synthetic_source_projection`,
   `test_review_bundle.py:202–208`) lives in a named support module that states what it disables.

**DDO support.** The DDO tests need support for the units the target design itself names; the
modules follow assurance needs, not production's file layout (companion §2).

| Unit | Support it needs | Replaces |
|---|---|---|
| Declarations | Builders for each declaration family with the case-defining fields as explicit parameters: subject kind, context shape, coverage, outcomes, ownership, transaction or call boundary. Where two families model the same thing they merge; where compile-only tests vary vocabulary on purpose, the recipe states it | `_declaration` and five variants in the storage test module, `contract()` in the compilation module, `operation()` in demands, `declaration()` in bindings, the parameters module's own |
| Compiled effective model | `compiled(recipe)`, memoized by recipe value | Some sixteen modules compiling their own |
| Admitted kernel | `KernelRecipe` (schema text, declarations, kinds, execution profile, project) and `admit_kernel(connection, recipe)`: the one persist release → admit → persist runtime binding → insert project sequence. If production gains an activation operation for data-operation releases, `admit_kernel` calls it | The sequence in `test_data_operation_storage.py:229–233`, `test_data_operation_population_native.py`, `test_data_operation_consumer_native.py:365–368`, `test_data_operation_original_native.py`, `orchestrate/test_data_operation_execution.py` and `orchestrate/test_data_operation_claim_source_native.py` |
| Kernel seeds | Seeds keyed by `KernelRecipe`: the storage kernel (also used by the service test), the population kernel, the four consumer releases, the execution release with a fixed module name, and the two original-fact profiles over a pre-claim `private_source` stage (a contributor's count of nine) | The function-scoped `kernel` fixture and `ddo_kernel_engine` |
| Subject context and root | `subject_context(...)` and `root_subject(...)` builders with explicit fields | Literals in fourteen modules |
| Demand and attachment | `attach`, `claim`, `retain`, `publish`, `cancel_demand`, and `expire_lease` (§4.6) | Helpers private to the storage test module |
| Purpose principals | Principal engines and rollback-class principal connections from the lifecycle fixtures | Direct `principal_engine` calls |
| Native boundary doubles | `WireCheckedStorage`: validates input and output with the production `validate_native_wire` around hand-written replies | The doubles in `test_data_operation_demands.py:216–221` and `test_data_operation_service.py:16–27` |
| Binding cases | One independently authored case table of members, roles, positions, support and witnesses, consumed by the compiled path on PostgreSQL and by the native binding functions | The SQLite matrices and the separate native vectors (§4.9) |

### 4.4 Negative and absence evidence

A negative control states three things at its call site. **Reach:** a minimal-pair positive control
on the same prepared state in the same transaction, rolled back in a savepoint, so the case is known
to reach the guarded boundary. **Reason:** the boundary's own diagnostic identity — SQLSTATE plus
constraint name or primary message, and a context field where several guards share a message; for
Python and CLI refusals the exception type plus message or error code. **Effect:** absence of what
the guarded operation would have left. An absence assertion has a presence premise in the same
output and an input that the wrong implementation would mishandle visibly. Expected values stay at
the call site; a narrow support helper unwraps the driver error and compares the diagnostic tuple,
with its own accept and reject controls.

### 4.5 Evidence class and prerequisites

A provider-backed claim and a controlled claim have different test identities. A prerequisite is a
marker decided before setup, routed exactly as the `corpus` marker is today
(`tests/conftest.py:122–138`): `qualification_prerequisite` and its reason enter the item's user
properties, and the skip happens before any fixture. Whether a missing provider prerequisite is
`blocked` or `inapplicable` is the qualification policy owner's declaration, not the body's. The DDO-12
provider obligation depends on this.

### 4.6 The three production seams

**A — Implementation determinants are read once per process (DTA-032).** Every
`prepare_interpretation_context` call reads all implementation determinants from disk at least twice:
`_profile` compares `model.implementation_digests` with `_semantic_implementation_digests()`, which
calls `trusted_execution_inputs()` (`analysis_contracts.py:454–469`); `_analysis_runtime` calls
`runtime_implementation_digests()` or `analysis_implementation_inputs()` (`:472–485`); and the standalone
branch adds `_standalone_model()` → `trusted_execution_inputs()` (`:409–412`). One read covers about a
hundred named files, a digest of every file in the `en_core_web_sm` package (`contracts.py:1388–1399`),
every `.py` and `.sql` file in the package (`:1437–1446`), about nineteen distribution versions and a
pure-Python parse of the physical YAML closure. Nothing on that path is cached. `grammar.parse`
prepares a standalone context before consulting its memo (`grammar.py:984–990`), so a memo hit pays
too. `trusted_execution_inputs` documents the intended lifetime itself: "Read bundled code-owned
definitions once at an explicit application entry boundary" (`contracts.py:1169`). The call sites
do not honor it.

The bounded change:

- `contracts.py` gains one owner, `current_implementation()`, returning a frozen snapshot of the
  trusted execution inputs, the analysis implementation inputs, their digests and the standalone
  runtime fingerprint, read once per process on first use (`functools.cache`). Without
  `physical_sources`, `trusted_execution_inputs()` and `analysis_implementation_inputs()` return the
  snapshot's values; with explicit `physical_sources` they compute as now.
- `_standalone_model`, `_semantic_implementation_digests` and `_analysis_runtime` consume the snapshot.
- `grammar.parse` without a context obtains its standalone grammar context from a memo keyed by
  `(_table_key(table), kind)` before its `_MEMO` lookup.
- One explicit override, `implementation_override(snapshot)`, a context manager that installs a
  snapshot and restores the previous one on exit. The fixture that installs an authored policy asset
  (`native_record_fixtures.py:386–396`) and the four sites that patch `contracts.trusted_execution_inputs`
  (`test_execution_release.py:118,244`, `test_typed_realization.py:363`, `test_contracts.py:453`, by a
  contributor's search) move to it where their path reaches the snapshot. Seed builders refuse to run
  under an override, which also settles DTA-007's open question for seeds.

Preserved: the admission check for prepared releases still refuses a release whose recorded
implementation digests differ from the running implementation; the runtime fingerprint has the same
inputs; the standalone route remains the explicit trusted base profile. One behavior changes on
purpose: a process no longer notices installed files edited after its first read. The per-call reads
described bytes on disk, not necessarily the Python code the process had already imported, so the
snapshot describes the running implementation at least as faithfully. **Premise to confirm with the
owner:** no long-lived process (for example the MCP server) relies on per-call rereads to refuse after
an on-disk upgrade without restarting. If one does, the alternative is a stat-keyed cache, as the
frozen-expectation parser already uses, at the cost of a stat walk per call.

The production consequence is broader than tests: by a contributor's reading,
`methods/math/source_context.py:238` prepares a context per span and `methods/math/native.py:285,948,1261`
do so in item loops. That is returned to the
broad audit as an observation; this review does not assess production execution fit.

**B — Data-operation lease expiry needs no production change.** Production validates `lease_seconds`
as an integer from 1 to 86,400 and compares every expiry with `clock_timestamp()`
(`src/corpus_structure/semantic/sql/data_operations.sql`, contributor reading at `:735,745,773,780`); there
is no time parameter. A fractional or injectable clock would widen the production surface only to
shorten tests, which the companion cautions against (§5). The existing idiom expires a lease without
waiting: `SET LOCAL ROLE corpus_sem_publisher` then `UPDATE ops.task SET lease_until =
clock_timestamp() - interval '1 second'` (`test_operations.py:991`, `test_claim_owner_native.py:159`,
`test_pdf_visual_requests.py:681`; its comment there calls time expiry "fixture setup, not a write
capability granted to the worker"). The data-task guard accepts it, because attempt, status and
holder are unchanged and the role is the protected publisher (`execution_guards.sql:4–20`). Keep one
real-clock control — `test_native_request_renewal_cannot_revive_an_expired_attempt`
(`test_data_operation_storage.py:1277–1286`) — which establishes that expiry follows the advancing
clock and that one second is an admitted lease; expire the other three
(`:468`, `:549`, `:1729`) through `expire_lease` in DDO support. This is low priority. One site to
settle first: `:2099` updates `lease_until` on a data task through the admin engine with no
`SET LOCAL ROLE`, which the source guard would refuse; either the deployed guard differs from
`src/…/execution_guards.sql` or that branch does not run as read.

**C — CPU grace periods need no production change.** The constants are module attributes read at call
time in parent-side code only (`cpu_execution.py:545–546`, read at `:634,965–966,1025`), and the suite
already shortens them in `test_data_operation_cpu.py:191–192`. The module-global `ProcessPoolExecutor`
constructed at `:725` is the factory seam the first lifecycle test already replaces
(`test_cpu_lifecycle.py:59–68`); there is no other production seam and none is needed. The change is
test-side (DTA-026).

### 4.7 Focused-run startup and scheduling

- **Worker count (F05, RC02).** The managed route passes `-n auto` for any narrowed selection
  (`scripts/test_receipts.py:1586–1593`), so a one-test run starts sixteen workers, each importing the
  package conftest and collecting the selection, and ends through xdist's gateway shutdown with a
  ten-second exit timeout. With explicit node ids: one id runs with `-n 0`; *k* ids run with
  `-n min(auto, k)`; path selectors keep `auto`. Because each ungrouped test is its own work unit
  under `loadgroup`, *k* is an upper bound on useful workers. Path selectors are not sized: a file
  can hold many independent tests, and the worker count is fixed before collection
  (`pytest_xdist_auto_num_workers` runs in `pytest_cmdline_main`).
- **Affinity groups (F02).** The root hook that already assigns `xdist_group("math_preparation")` by
  fixture closure (`conftest.py:21–37`) assigns one group per designated expensive preparation value,
  for consumers whose bodies are cheap: the statistics pack module fixtures (`orchestrate/test_policy.py`,
  `semantic/test_interpretations.py`, `schema/test_rules.py`, `semantic/test_rule_literal_bindings.py`),
  the HanLP profile and the trusted execution-model compile in root `tests/test_native_run_scope.py`.
  Each item carries at most one group; xdist combines two marks into a new group. Rollback-class
  families are grouped by family, so a family is one work unit: its cases are cheap once the family
  clone exists, and without the group every worker that received one case would build the seed.
  Commit-class consumers of a recipe are not grouped by default: grouping would remove per-worker seed
  builds in full runs but serialize a focused module's real bodies onto one worker; revisit with
  receipts.
- **Hypothesis.** Keep the managed `ci` profile (300 derandomized examples) for focused and full runs,
  so focused and qualification runs explore the same examples. The one property that dominated
  (`test_generated_layer`, 198 s, about 0.66 s per example in `2e2a0e30…`) is a DTA-032 consequence by
  source reading; the example count is not the lever.
- **Dependency-based selection.** Rejected. Test identities depend on SQL, YAML, frozen migration
  artifacts and about a hundred implementation files hashed into runtime fingerprints, none of which a
  Python coverage map such as pytest-testmon records; an incomplete dependency key would silently skip
  affected tests (G6). Selection stays a developer judgment; `-k data_operation` already selects the DDO
  modules by name through the managed route, which admits `-k` (`test_receipts.py:1536–1552`).
- **Smaller items, kept as candidates** in the supporting document: lazy CLI import in the package
  conftest (`tests/conftest.py:37`), argument screening without a second interpreter
  (`cli/testing.py:447–465`), deferred collection-time loads, the controlled PDF builder loaded once per
  process, concurrent cold-process children, structurally long tests dispatched first.

### 4.8 The DDO transition: cutover and the qualification union

**Cutover (DTA-035).** Each DDO package that retires a mechanism owns the transfer of the tests that
name it, as part of delivering that package:

1. A test whose every assertion restates the removed mechanism is deleted in the package's commit,
   which names it and cites the surviving-surface control that covers the same behavior (for example
   `test_data_operation_storage.py` publication and exact replay, expired owner, cancellation,
   immutability and binding refusals).
2. A mixed test is re-expressed on the surviving surface before the mechanism goes. The cheapest route
   is through support: staged builders and recipes are re-pointed once (for example `build_domain_case`,
   `build_resubmission_case`, `projection()` in `orchestrate/test_source_progress.py:71`), and the tests
   on them follow.
3. Behavior without a counterpart on the new surface gets one before the mechanism is removed: the
   audit found none for source-view batching, readiness progress or characterization recovery.
4. Closure for the package: no test source names a retired mechanism (`reused_task_id`, `valid_reuse`,
   `task_dependency`, `freshness_seed`, `source_dependencies`, `OperationDescriptor`,
   `SourceOperationLink`, `max_active_stage_runs`, as the plan retires each), and each deletion is named
   in a commit.

No per-test register is needed; the package commit and the plan package's closure evidence are the
record. The supporting document carries the contributors' per-file classification as planning input,
labelled by how it was obtained.

**The union (DTA-036, refined).** The four path lists in the coordinator plan are receipts of bounded
campaigns, each with a durable receipt that preserves its exact selection, and each states that it is
not DDO-12. The "stale" path in the first list existed when that campaign ran: `0de179fc7` (2026-11-12)
precedes its deletion in `9d996b32d` (2026-11-13). DDO-12 itself already says what the union is: after
all functional scope and retirement, freeze final source and run `uv run ci test` and `uv run ci check`,
with native fault and provider lanes explicitly covered and missing providers kept open
(`preservation-adoption-and-qualification.md`, DDO-12). The target form is therefore:

- the full ordinary and fault lanes on frozen final source, with a run-private head (§4.1);
- one provider run with the provider prerequisites present, in which provider-gated identities
  (after DTA-028's split) either pass or resolve `blocked`;
- an evidence column added to DDO-12's obligation table at DDO-12 time, naming the test identities
  that discriminate each row and the rows still without evidence. That table already exists and DDO-12
  consumes it, so this adds no register.

The gaps the audit observed belong in that column until closed: overlapping publication with differing
intents; one case set through both native and compiled bindings (§4.9); helper-body and
inherited-value change locality; invalidated support recovered through a real consumer; graph example
sets.

### 4.9 Independent evidence for the DDO model

**Identity (DTA-033).** Products are keyed by `contextual_product_identity`
(`data_operation_identity.py:471–483`), whose only test derives the expected key from the function
under test (`test_data_operation_storage.py:1788–1820`). Add literal vectors: hand-authored canonical
input bytes and the expected SHA-256 computed with the standard library, varying the domain tag, the
nesting of `subject_context` and the local-subject qualification; run the same literal context through
the native function in the read class. Delete `product_identity` and `subject_identity`
(`:407–434`), which have no caller under `src/`, with their tests, in the DDO package that owns
identity. Keep one copy of the JSON-meaning vector table (a contributor reports
`test_data_operation_storage.py:2150` repeats `test_data_operation_identity_native.py:96–105`).

**Bindings (DTA-034).** One case table, authored independently, executed by the compiled SQLAlchemy
path on PostgreSQL and by the native binding functions, both in the rollback class. The SQLite runs
(`test_data_operation_bindings.py:130`, `test_data_operation_consumer_bindings.py:88`) go unless a
supported consumer executes bindings on SQLite; production executes them on the planner's PostgreSQL
connection, and SQLite's null and ordering semantics differ.

**Doubles.** `WireCheckedStorage` in support wraps hand-written replies with the production wire
validator on both sides, so a routing test fails when the planner or service emits or accepts a shape
the wire forbids. Payloads the wire would reject get fixed rather than tolerated.

**Preserved strengths** (contributor reading of about 60% of the DDO test lines, sampled by me):
hand-authored compiler node ids and refusals, recipe sensitivity by controlled perturbation, unknown
kept distinct from absent in source capture, literal canonical framing, hand-authored graph topologies,
independent wire bounds, behavioral tests of generated types, equal bodies under different contexts
giving distinct products, and real-transaction concurrency controls.

---

## 5. Finding index

Audit identities are those of publication `28b4a53db`. F01–F03 are the 2026-11-12 review's findings,
carried with their meaning; F04 and F05 are new. "Retain", "Refine" and "Extend" judge the diagnosis.
Disposition for every row is in §14.

| ID | Diagnosis | Selected correction (one line) | Cause | Priority |
|---|---|---|---|---|
| [DTA-001](../test-audit/evidence-and-discrimination.md#dta-001) | Retain; DDO forged-graph and registry-count sites added | Refusal contract with reach, reason and effect at each site | C3 | High; prerequisite of rollback families |
| [DTA-006](../test-audit/evidence-and-discrimination.md#dta-006) | Retain | Assert preserved content; compare against a known difference | C3 | Medium |
| [DTA-009](../test-audit/support-structure.md#dta-009) | Extend: seven importers of the storage test module; relative imports from two non-package directories | Support modules imported by canonical name; recipe values; shared fixtures in the package conftest | C4 | Medium; prerequisite of seeds and cutover |
| [DTA-018](../test-audit/execution-and-qualification.md#dta-018) | Retain; one DDO instance added | Staged builders; second database by clone; prerequisites before setup | C1, C5 | Medium |
| [DTA-024](../test-audit/execution-and-qualification.md#dta-024) | Refine: the build executes a chain of about 1.3 GB of frozen artifacts that grows with each candidate | Content-keyed deployment reused across narrowed runs; run-private for qualification | C1 | High |
| [DTA-025](../test-audit/execution-and-qualification.md#dta-025) | Retain with the 2026-11-13 footprint | Seeds plus the rollback class, gated on DTA-001's contract | C1, C2 | High |
| [DTA-026](../test-audit/execution-and-qualification.md#dta-026) | Retain; production seam corrected (no factory seam beyond the module global) | Shortened grace with derived windows, one pin of the policy value, initializer injection through the module seam | — | Low–medium |
| [DTA-027](../test-audit/evidence-and-discrimination.md#dta-027) | Retain | A secret placed across the clip boundary with a presence premise | C3 | Low–medium |
| [DTA-028](../test-audit/support-structure.md#dta-028) | Retain | Two identities; prerequisite marker before setup | C5 | High |
| [DTA-029](../test-audit/support-structure.md#dta-029) | Retain | One owner of the native half with an explicit digest policy | C4 | Low |
| [DTA-030](../test-audit/retirement-transfer.md#dta-030) | Retain | Remove the dead scheme and fixtures; one naming function covers every created name | C4 | Medium-low; prerequisite of §4.1 |
| [DTA-031](../test-audit/execution-and-qualification.md#dta-031) | Extend: admission sequence in six modules at the baseline | Kernel recipes and seeds; read and rollback classes; DDO support | C1, C2, C4 | High |
| [DTA-032](../test-audit/execution-and-qualification.md#dta-032) | Refine: both branches re-read; not only standalone | Implementation snapshot with an explicit override | C1 | High (small change, broad effect) |
| [DTA-033](../test-audit/evidence-and-discrimination.md#dta-033) | Retain | Literal vectors for the contextual identity; delete the uncalled helpers | C6 | High |
| [DTA-034](../test-audit/support-structure.md#dta-034) | Retain | Wire-checked double; one binding case table through compiled-on-PostgreSQL and native | C6 | Medium-low |
| [DTA-035](../test-audit/retirement-transfer.md#dta-035) | Retain | Per-package transfer rule through re-pointed support; closure by name search and named deletions | C6 | Medium |
| [DTA-036](../test-audit/retirement-transfer.md#dta-036) | Refine: the lists are accurate receipts; the residue is DDO-12's evidence mapping | Full lanes plus a provider run; evidence column in DDO-12's table | C6 | Low–medium |
| F01 | Retain | One function derives lease key and sweep key; `committing_db` removed | C4 | Medium-low |
| F02 | Extend: function-scoped consumers also pay cold preparation once per worker | Affinity groups by preparation value; recipe memo; DTA-032 | C1 | Medium |
| F03 | Extend: DDO kernels and domain-case prefixes | Per-worker seeds keyed by recipe value, one lifecycle | C1 | High |
| F04 | New | Sweep skips residue still in use instead of failing setup | C4 | Low |
| F05 | New | Size workers to explicit node-id selections; `-n 0` for one | C1 | Medium |

The 2026-11-12 review's DTA-016 residue (exact task state for the three non-complete stdio modes,
`test_runtime_entrypoints.py:608`) carries forward unchanged as a deferred row.

---

## 6. Corrective arguments

Each argument separates the diagnosis's evidence from the remedy's maturity. Diagnoses are
Interface-checked (2026-11-13) unless noted; remedies are Proposed.

### 6.1 Preparation lifetimes (C1)

#### DTA-024 — Each worker rebuilds the same sealed head

**Diagnosis: retain, refined.** The head fixture is session-scoped and named with `os.getpid()`
(`tests/conftest.py:255–260`); `semantic_template` creates it from `cs_template`, upgrades it in one
transaction and seals it (`scripts/native_test_support.py:612–630`); the managed route passes `auto`
for narrowed selections (`scripts/test_receipts.py:1588`). The refinement concerns growth: the build
executes the whole frozen chain, whose newer revisions each read and verify their own frozen native
state (for example `semantic_ddo_renewal_v1.py` reads `_native.json`, `_upgrade.txt` and `_admission.sql`
against pinned digests), and that directory is about 1.3 GB. The measured build of 37–55 s therefore
rises with each candidate. Concurrent builds contend (87–92 s each with sixteen).

**Correction.** The content-keyed deployment of §4.1. It consumes the deployment key and the cluster's
template; it decides reuse or build under the build lock; it produces a sealed head under a stable name,
a usage lease and its policy. Consumers keep reading `.name` and `.policy`. Change set:
`scripts/native_test_support.py` (deployment operation, key computation, naming function, sweep
rules), `tests/conftest.py` (head fixture, qualification mode from the managed environment), the
receipt context (head name and built-in-run flag), the controls in `tests/test_db_fixtures.py` and
`tests/semantic/test_native_fixtures.py`. The per-process head path goes.

**Alternatives.** Run-scoped heads (a) and per-worker heads (c), compared in §4.1. A key over the chain
directory alone was rejected because revisions execute product modules. A hand-listed module set was
rejected in favor of a computed closure, which cannot lag a new import.

**Challenge.** A worktree with a different chain on the same cluster gets its own key and head; three
retained heads cover it. A developer who changes a migration mid-run gets a second head for later
workers, as today. A key component missed by the closure walk could serve a stale head to a focused
run; qualification builds run-private heads and cold deployment controls always run the real chain.

**Evidence.** Diagnosis Interface-checked; build durations Measured from stored results; the remedy's
benefit is structural. **Closure:** receipts of two consecutive narrowed runs name the same head and
the second reports it reused; an unnarrowed run's receipt names a run-private head; no per-process head
creation remains. **Owner:** the test-system plan created from this review. **Rule impact:** RC01.

#### DTA-025 — Rollback-only refusal families rebuild an identical committed scenario per case

**Diagnosis: retain, with the audit's 2026-11-13 footprint.** The six setup families confirmed by the
2026-11-12 review stand; the four families that build in the body add about 1,080 worker-seconds of call
time in `2e2a0e30…` (identity-exclusion tampering 477 s, imported membership 253 s, occurrence context
205 s, declared membership 144 s). A warm `private_source` case spends about 10–11 s in setup, of which
the clone is about 0.25 s and pure preparation about 1 s (contributor, `e332a3ef…`): the repeated cost
is the committed build.

**Correction.** Each member family builds its scenario once as a seed (§4.1) and runs its cases in the
rollback class on one family clone, as one xdist work unit (a family group assigned by the root hook,
§4.7): each case opens a new connection (isolation set before `begin()`
where the product uses `SERIALIZABLE`), runs the positive control in a savepoint, then the refusal,
and asserts the exact reason and absence (§4.4). Identical per-case setup that commits today
(`local_cut`, `curated_case`) moves into the seed. A family's committing positive case ("valid" in the
two membership-lineage families) takes the commit class from the same seed. The identity-exclusion
tampering cases use two `exclusion_result` recipes (with and without attribute assertions), so two
seeds. Pure SQL-function families (`test_local_semantic_admission.py:121–147`,
`test_contextual_workflow_native.py:29–135`) take the read class.

**Membership criterion** for further families: an identical committed scenario across cases; every case
write inside the rolled-back transaction; no live lease unless renewed inside the case; no
session-level effects; no assertion on absolute generated ids. A family failing it stays commit-class
on a seed, which still removes the rebuild.

**Strengths preserved.** Positive controls, per-case reason tables (`test_local_semantic_admission_native.py:597–621`),
atomicity assertions, `SERIALIZABLE` where the product uses it, the transaction-local `plan_cache_mode`
replays.

**Challenge.** A refused operation that checks a task lease, run on a scenario older than five minutes,
would refuse for the lease: the positive control fails first and the reason differs, which is why
DTA-001's contract is a prerequisite. A production path that commits on its own connection would leak
into later cases; the next case's positive control and absence check expose it.

**Evidence.** Diagnosis Interface-checked with Measured costs; remedy Proposed. **Closure:** each migrated
family's receipt shows one seed and one family clone per worker; every case asserts positive control,
exact reason and absence; no case body commits. **Owner:** test-system plan; DDO plan for DDO families.
**Rule impacts:** RC01, RC04.

#### F03 — Committing consumers rebuild identical committed scenarios through producers

**Diagnosis: retain, extended.** Carried from the 2026-11-12 review: committing consumers need fresh
state, not a fresh build. Extended to the DDO kernels (DTA-031) and to the shared prefixes of
`build_domain_case`. A contributor counts 116 test functions using `private_source` across about ten
option sets, 36 `build_domain_case` sites of which eleven use default arguments, and 24
`build_resubmission_case` sites.

**Correction.** Per-worker seeds keyed by recipe value (§4.1), with builders split at the claim
boundary (§4.3). Candidates by structure: default `private_source` and its common option sets at the
pre-claim stage, `build_domain_case` at the release-and-views stage keyed by its schema-affecting
options, `build_resubmission_case` (no lease until `queue_next`), `exclusion_result` before finalize,
the DDO kernels. `pdf13_db` gains little: its original is stored under a live lease, so its seed stops
before most of its work. `completed_*_case` and `judged_source` patch providers during the build; they
seed only once their patches are declared in the recipe and scoped to the build.

`tests/semantic/test_domain_operations.py` is the largest single cost in the 442-test union (864 s of
call time over 35 tests, flat median about 27 s), and twenty-one argument sets serve its 24 tests, so
seeding pays only where tests share a prefix. Which stage of `build_domain_case` dominates is not
established; one profile of a single build inside the consuming package would settle whether the
release stage or the publication stage carries the time.

**Evidence.** Diagnosis Interface-checked with counts from a contributor's AST pass; remedy Proposed.
**Closure:** each chosen recipe's builder runs once per worker; consumers obtain clones; the serving seed
uses the common operation. **Owner:** test-system plan. **Rule impact:** RC04.

#### DTA-031 — DDO native tests rebuild one identical admitted kernel per case

**Diagnosis: retain, extended.** At the baseline the kernel fixture is unchanged
(`test_data_operation_storage.py:162–252`, function-scoped, fresh clone `cs_ddo_case_<hex12>`), seven
modules import from the storage test module, and the persist → admit → bind → project sequence appears in
six modules. A warm case spends about 0.65 s cloning, 3.4 s in Python and 8 s in the admission transaction
for a body of about 1 s (contributor, `e332a3ef…`). The kernel holds no claim, lease or clock value; its
runtime id depends on `sys.version`, stable for every worker on one interpreter.

**Correction.** Kernel recipes and seeds, DDO support (§4.3), and the isolation classes: `:738` and
`:2150` and both identity-native tests take the read class; `binding_native_connection` and the
source-builder connection, which install functions inside a rolled-back transaction, take the rollback
class; committing tests and the refusal families that commit an attach or claim first take the commit
class from the kernel seed. The forged-graph family builds only the demand it reads (a DTA-018
instance). The execution fixture uses a fixed module name so its release identity is stable.

**Challenge.** Rows of a sealed kernel referring to the database name or role names would differ in a
clone; a contributor found no time or process dependence in committed kernel rows but did not inspect
for database or role names — the first seed clone's tests settle it.

**Observation for the DDO plan owner.** `admit_data_operation_release` verifies the native deployment
twice in one transaction: it calls `require_data_operation_native` and then
`admit_data_operation_definitions`, which calls it again (`data_operation_admission.py:64–74`,
`data_operation_storage.py:736–740`). Each call runs the catalog verification. This is production, not
a test finding (H20).

**Evidence.** Diagnosis Interface-checked; costs Measured; remedy Proposed. **Closure:** no DDO module
imports from a test module; one `admit_kernel`; DDO native tests request a named isolation class; the
storage module's receipt shows one kernel seed per worker. **Owner:** DDO plan if it adopts the
finding, otherwise the test-system plan. **Rule impacts:** RC03, RC04.

#### F02 — Module- and session-scoped preparation is rebuilt on every worker

**Diagnosis: retain, extended.** Carried from 2026-11-12, now measured (contributor, `2e2a0e30…`): the
statistics pack module fixture behind `orchestrate/test_policy.py:36–38` spent 28–37 s on each of ten
workers while every other test in that module spent none; `test_interpretations.py` 25–34 s on eight;
root `tests/test_native_run_scope.py` 16–21 s on seven; the HanLP profile about 19 s on both workers of a
two-worker run (`ea623a16…`). Extended: function-scoped consumers pay cold preparation once per worker
too — the first `private_preparation` consumer per worker spent 11–35 s in pure Python against about 1 s
warm. About twenty distinct prepared values have more than forty build sites (contributor).

**Correction.** Affinity groups by preparation value for designated preparations with cheap bodies
(§4.7), the recipe memo, and DTA-032. The designation is a short list beside the math one.

**Challenge.** Grouping a module with expensive bodies would serialize them; the criterion excludes it.

**Closure:** receipts' affinity groups show each designated preparation on one worker. **Owner:**
test-system plan.

#### DTA-018 — Focused controls construct preparation they do not use

**Diagnosis: retain.** Confirmed sites as the audit lists them, plus `test_release_compatibility.py:91–123`,
which obtains its second database by replaying the whole chain through `semantic_database_at("head")`
(`tests/semantic/conftest.py:48–57`) to show a cache keyed by engine (43.5 s of call in `2e2a0e30…`,
contributor).

**Correction.** Staged builders; the record-policy controls take a persisted release and authored
candidates; the CLI diagnostic takes a persisted composed release; provider and asset prerequisites
become markers decided before setup (§4.5); the second database is a second clone of the head; the
recognition scheduling control constructs its owner without the isolated runtime, once implementation
confirms construction does not validate it.

**Closure:** the named consumers request only what they read; no body-level provider skip follows
scenario fixtures. **Owner:** test-system plan.

#### DTA-032 — Interpretation contexts re-read implementation determinants on every call

**Diagnosis: refined.** The audit framed it as standalone-only. Source shows the prepared branch also
reads all determinants twice per call (§4.6 A), so every caller pays it, standalone or not. The share of
`test_generated_layer`'s 0.66 s per example it explains is a source reading, not a profile.

**Correction.** The implementation snapshot, the standalone context memo in `grammar.parse`, and the
explicit override (§4.6 A).

**Alternatives.** Changing the tests to pass a prepared context would leave production's public adapter
paying per call and would stop the property test exercising that adapter. A bare `lru_cache` on the
reader would silently ignore the monkeypatches fixtures use today. A stat-keyed cache keeps mid-process
change detection at the cost of a stat walk per call; it is the fallback if the premise in §4.6 fails.

**Evidence.** Call tree Interface-checked; attribution suspected; remedy Proposed. **Closure:**
`prepare_interpretation_context` performs no file reads after the first in a process (a counting control
over the readers); no test monkeypatches the determinant readers; the admission refusal for a release
with different implementation digests still has its control. **Owner:** test-system plan, with the
production owner of `semantic/contracts.py`.

#### F05 — Narrowed managed runs start one worker per core whatever the selection

**Finding.** `_managed_pytest_args` passes `-n auto` unless `--workers` is given
(`scripts/test_receipts.py:1586–1593`), and `pyproject.toml:64` sets the same default for plain pytest.
A one-test run therefore starts sixteen workers, each importing the package conftest (which imports the
CLI application, `tests/conftest.py:37`) and collecting, and then waits on xdist's gateway shutdown,
whose exit timeout is ten seconds. Measured (contributor, 2026-11-13): trivial two-worker runs took
5.7–6.1 s wall; a three-test run on sixteen workers reached its first phase at 7.7 s and took 15.4 s;
the tail after the last worker varied from 2 to 11 s. FP-07, H21, H26; A4. Consequence: a fixed cost on
every focused run, unrelated to the claim.

**Correction.** Size workers to explicit node-id selections (§4.7). **Challenge.** A path selector with
many slow independent tests still gets `auto`. **Closure:** a one-node managed run records zero workers.
**Owner:** test-system plan. **Rule impact:** RC02.

### 6.2 Isolation and negative evidence (C2, C3)

#### DTA-001 — Some refusal assertions do not distinguish the intended outcome

**Diagnosis: retain.** The audit's sites stand. Added from the DDO modules: the forged-graph family
accepts any of three reasons for each of four mutations (`match=r"graph|closure|discovery"`,
`test_data_operation_storage.py:2001`), and two tests restate a registry size (`len(calls) == 18` at
`test_data_operation_storage.py:39`, `len(contracts) == 18` at `test_data_operation_wire.py:111`).

**Correction.** The contract of §4.4. Privilege controls pin `42501` per statement, which closes the
writer-bypass sites without new inputs, because the missing realization would raise `23503`, not
`42501`. Mutation families bind each label to its expected diagnostic tuple, as the forged-judged table
does. The generic `P0002` cases also pin the diagnostic context naming the guarding function. The
forged-graph family names one reason per mutation. Registry counts become an authored set where the set
is the claim, or go. CLI refusals pin error code and message.

**Challenge.** Two mutations may legitimately reach one guard; the table may repeat a reason, and the
minimal pair proves reach. Message text is product wording; where it churns, prefer constraint names or
SQLSTATE with context.

**Closure:** removing one guard makes exactly its case fail, by reasoning over the guard conditions.
**Owner:** test-system plan; DDO plan for DDO sites.

#### DTA-006 — Some assertions establish presence or count where the claim is preservation

**Diagnosis and correction: retain the 2026-11-12 remedy.** Assert which entities were grounded; compare
two runs with a known difference and assert the exact change list (the changed run is a clone of the
exclusion seed plus one change); give the reference evaluation one submission with an unmatched extra
and a missing claim; assert exact diagnostic fields and retained edges. **Closure:** each named test
fails for a plausible wrong implementation it now accepts. **Owner:** test-system plan.

#### DTA-027 — The redact-before-clip control passes under either order

**Diagnosis and correction: retain the 2026-11-12 remedy.** Place a credential so that clipping first
would cut it mid-token and leave a fragment redaction no longer recognizes; assert the fragment's
absence and the mask token at the expected place; add the same control for the 6,000-character
diagnostic clip (`src/corpus_structure/cli/operations.py:187`). **Closure:** a clip-first implementation
fails by construction. **Owner:** test-system plan.

### 6.3 Ownership and lifecycle authority (C4)

#### DTA-009 — Scenario ownership sits in test modules and fixture-name bindings

**Diagnosis: extend.** The three forms the audit records hold. At the baseline seven modules import from
`test_data_operation_storage.py`, among them the new `orchestrate/test_data_operation_claim_source_native.py:27–33`;
`tests/orchestrate/` and `tests/acceptance/` use relative imports into `semantic` from non-package
directories (`orchestrate/test_data_operation_execution.py:29–30`, `test_data_operation_batch_activity.py:67–68`,
`acceptance/conftest.py:3–4`), which load the target a second time.

**Correction.** §4.3's rules and DDO support. Change set: `native_record_fixtures.py` and the eleven
overriding modules; the test-module owners imported elsewhere, moved by consumer cluster; the
verification-disabling double; the DDO support modules; the package conftest.

**Challenge.** The structural-replay family's per-case text becomes a per-case recipe parameter, which
states the same thing directly.

**Closure:** no `from …test_…` import and no relative import from a non-package directory; no
`private_source_options` override or `callspec` read. **Owner:** test-system plan; DDO plan for DDO
support if it adopts DTA-031.

#### DTA-029 — The primary-layer assembly scaffold is hand-copied

**Diagnosis and correction: retain.** One owner of the native half, taking configuration text, digest
policy (pipeline or derived), products and reference numbers as explicit arguments; the digest choice
becomes visible at each call site. The DDO admission sequence is the same shape and gets the same
treatment through `admit_kernel`. **Closure:** the copies call the owner. **Owner:** test-system plan.

#### DTA-030 — Superseded fixture machinery remains in shared support

**Diagnosis: retain.** Confirmed at the baseline: `TEMPLATE_PREFIX`, `TEMPLATE_RETENTION`, `STAMP`
(`scripts/native_test_support.py:46–49`), `stamp()` (`:547–552`), the stamp branch of `owned_comment`
(`:248`) and the `cs_tpl_` sweep branch (`:580–586`); `committing_db` (`tests/conftest.py:295–303`) with
only its self-test; the shadowing fixture with an unreachable candidate branch and a sweep-escaping name
(`test_native_attributed_evidence.py:51–53`); the second sweep-escaping name
(`test_serving_scenario_lifecycle.py:39`); the third (`cs_ddo_case_`, `test_data_operation_storage.py:162–168`).

**Correction.** Remove the `cs_tpl_` scheme, its retention constant and re-export, `committing_db` and its
self-test, the shadowing fixture with its migration imports and evidence path, and the unreferenced
`tests/semantic/snapshot_restore.py`; route every created name through the naming function. Before
removing the `cs_tpl_` branch, check the cluster once for owned `cs_tpl_*` residue and drop it through
the authenticated drop.

**Relation to §4.1.** The content-keyed head is not a revival of `cs_tpl_`: it uses the ownership stamp
as the only comment, retention by count, and the one recognition rule.

**Closure:** no source names `cs_tpl_` or `STAMP`; every name the tests create matches a sweep rule.
**Owner:** test-system plan; prerequisite of DTA-024.

#### F01 — The sweep's lock key for `ci_test_<pid>_<n>` differs from the lease key

**Diagnosis: retain.** `database()` leases the full name (`:452`); the sweep reduces such names to
`ci_test_<pid>` before try-locking (`:45,591–596`). **Correction:** the naming function derives both keys;
with `committing_db` gone the optional suffix goes. **Closure:** one derivation used by lease and sweep;
the sweep control protects a live name by that name's own lease. **Owner:** test-system plan.

#### F04 — The sweep turns residue still in use into a setup failure

**Finding.** `native_server` sweeps at session setup (`tests/conftest.py:250`). For each unleased owned
candidate it calls `drop`, which retries SQLSTATE `55006` for two seconds and then raises
(`scripts/native_test_support.py:213–242`); the sweep collects the failure and raises a
`BaseExceptionGroup` (`:596–609`). A database left by a killed process whose backend is still executing —
a head build interrupted mid-migration is the natural case — therefore fails the setup of every native
test in an unrelated run until that backend ends. DP-19, DP-20; G5; H24. Consequence: one failure
amplified into spurious failures of other runs.

**Correction.** The sweep skips residue that is still connected, records it, and leaves it for a later
sweep; it keeps raising for authentication and ownership defects. **Closure:** a sweep control with a
connected owned residue completes and reports the skip. **Owner:** test-system plan.

### 6.4 Evidence class and timing (C5)

#### DTA-028 — One provider test identity passes on a controlled branch

**Diagnosis and correction: retain.** `test_pm2_result_native.py` reads `CORPUS_PM2_NATIVE_TEST_ASSETS`
in the body (`:325`) and completes through hand-written replies when it is unset. Split into a provider
identity gated by a prerequisite marker decided before setup and a controlled identity named as such
(§4.5). The ordinary lane on a host without assets then reports the provider node blocked, which is the
truthful outcome. **Closure:** no body reads an asset variable to choose its evidence class; receipts
record the prerequisite. **Owner:** test-system plan; before any qualification that counts PM2 provider
evidence, and before DDO-12.

#### DTA-026 — CPU teardown controls wait out production grace and write executor internals

**Diagnosis: retain; the production-seam premise corrected.** The constants and literal windows stand
(`test_cpu_lifecycle.py:78,111,161,282,376`). The only factory seam is the module-global
`ProcessPoolExecutor` (`cpu_execution.py:725`); the tests that write `_initializer` and `_initargs` on a
live pool (`:92–94,144–145,208–209,326–327`) can inject the same `started` event through that seam with a
wrapping factory that composes the production initializer, as the first test does (`:59–68`).

**Correction.** Windows derive from the constants read at test time; behavioral controls shorten them with
`monkeypatch` (precedent `test_data_operation_cpu.py:191–192`); one cheap assertion pins the selected five
seconds so the policy is protected without waiting it out; initializer injection uses the module seam;
reads and writes of manager state that build the broken-pool interleaving (`:261–265`) stay, tied to the
adapter's documented dependency on executor internals (`cpu_execution.py:568–573,595–602`). The in-flight
cancellation control in `test_cpu_execution.py:110–139` gates its worker with a manager event as its
siblings do.

**Challenge.** A grace shorter than child readiness could race; the tests already wait for `started`
before closing and keep an absolute upper bound. **Closure:** no literal tied to five seconds; one value
assertion; no writes of `_initializer` or `_initargs`. **Owner:** test-system plan.

### 6.5 The DDO transition (C6)

#### DTA-033 — The product identity production uses is checked only against itself

**Diagnosis: retain.** Confirmed: `contextual_product_identity` is the current key
(`data_operation_identity.py:471–483`, its docstring: "the pure legacy helper does not authorize it");
the storage test compares the native key with that function's own output
(`test_data_operation_storage.py:1788–1820`); `product_identity` and `subject_identity` (`:407–434`) have no
caller under `src/`. **Correction:** §4.9. **Challenge:** literal vectors churn on a deliberate identity
change; that is the point, and ADR-0100 says vectors migrate with the identity. **Closure:** a vector test
fails for a changed domain tag, nesting or local qualification; the uncalled helpers and their tests are
gone. **Owner:** DDO plan (identity package), else the test-system plan.

#### DTA-034 — Two DDO claims are checked on a substitute below the boundary they reach

**Diagnosis: retain.** `DataOperationStorage.invoke` validates input and output against the closed wire
(`data_operation_storage.py:320–333`); the planner and service doubles replace the whole object
(`test_data_operation_demands.py:216–221`, `test_data_operation_service.py:16–27`); compiled bindings run
on `sqlite://` (`test_data_operation_bindings.py:130`, `test_data_operation_consumer_bindings.py:88`).
**Correction:** §4.9. **Closure:** routing tests use the wire-checked double; one case table runs through
compiled-on-PostgreSQL and native bindings. **Owner:** DDO plan (DDO-03 parity obligation), else the
test-system plan.

#### DTA-035 — Required behavior is asserted through machinery the target removes

**Diagnosis: retain.** The audit's classification stands as a planning lead; a second contributor's
per-test dispositions are by token match except where read. **Correction:** §4.8. **Prerequisite:**
DTA-009's support and staged builders make re-expression a single re-pointing per builder.
**Closure:** per package, as §4.8 states. **Owner:** DDO plan (DDO-06–11).

#### DTA-036 — The DDO test union exists only as prose path lists

**Diagnosis: refined, partly returned.** The lists are receipts of bounded campaigns, each with a durable
receipt and an explicit statement that it is not DDO-12; the path called stale existed when its campaign
ran. The audit's consequence — that running the list as written fails or silently covers less — applies
only if someone treats a receipt as a union. What remains is that DDO-12's union is defined by
obligation rows with no evidence mapping and no named provider selection. **Correction:** §4.8.
**Closure:** at DDO-12 the obligation table names discriminating identities per row or states the gap;
the provider run's receipt shows provider identities passed or blocked. **Owner:** DDO plan.

---

## 7. Library and system mechanisms

| Capability and use | Mechanism and API | Conditions and limits | Reference and strength | Status |
|---|---|---|---|---|
| Cloning a sealed head or seed (§4.1) | `CREATE DATABASE … TEMPLATE` with the default `STRATEGY WAL_LOG`; `ALTER DATABASE … ALLOW_CONNECTIONS false` | The source takes a `ShareLock`, so concurrent clones of one source proceed; creation fails if another session is connected to the source, after waiting up to five seconds; `FILE_COPY` forces two checkpoints and `file_copy_method = clone` needs reflinks, which ext4 lacks | PostgreSQL 18 `sql-createdatabase` [doc]; `dbcommands.c` REL_18_STABLE [src], library-mechanics report | Selected (existing) |
| Publishing a build atomically | `ALTER DATABASE build RENAME TO head` | Refused while another session is connected to it; requires ownership and `CREATEDB`; the OID, and so the ownership stamp, is kept | PostgreSQL 18 `sql-alterdatabase` [doc]; not exercised here | Selected |
| Drop cost | `DROP DATABASE` requests an immediate, forced, waited checkpoint (`RequestCheckpoint(CHECKPOINT_IMMEDIATE|CHECKPOINT_FORCE|CHECKPOINT_WAIT)`) | Every clone drop flushes the whole cluster, including the development database; fewer clones and fewer head drops are the safe lever | `dbcommands.c` REL_18_STABLE ~1873 [src], library-mechanics report | Premise for priority |
| What clones carry | Objects and in-database grants; not `datacl`, database or role-in-database settings, or the database comment | Policy replay stays per clone; the comment-held ownership stamp stays on the source and is written anew per clone by acknowledged creation | PostgreSQL docs and source [doc/src]; ADR-0032 Context | Selected (existing) |
| Usage leases and build lock | Session advisory locks `pg_advisory_lock_shared`, `pg_advisory_lock`, `pg_try_advisory_lock`, `pg_advisory_unlock` through `PgAdmin.lease` and `lock_sql` | Lock tags include the current database OID, so every lease is taken on `postgres` (as `PgAdmin.connect()` does); session locks survive rollback and end with the session, including a dead client's idle session | PostgreSQL 18 functions-admin [doc]; `lockfuncs.c` [src] | Selected |
| Run identity for run-private heads | xdist `testrun_uid` session fixture / `config.workerinput["testrunuid"]` | Shared by a run's workers; generated locally without xdist | `xdist/plugin.py:400–407` (installed 3.8.0, read 2026-11-13) | Selected |
| Read class | `SET TRANSACTION READ ONLY`, or SQLAlchemy `execution_options(postgresql_readonly=True)` | Writes, DDL and temporary tables fail with `25006`; the read-only check runs at executor start, before privilege checks, so it masks `42501` | PostgreSQL 18 `sql-set-transaction` [doc]; the ordering is the reviewer's reading of executor start, not re-read at the 18 tag | Selected |
| Rollback class | SQLAlchemy Core `Connection.begin()` / `rollback()`, `begin_nested()` savepoints; isolation level set on the connection before `begin()` | Sequences do not roll back; `NOTIFY` is delivered only on commit; `now()` is fixed per transaction while `clock_timestamp()` advances | SQLAlchemy 2.1.6 Core transactions [doc]; existing `rollback_connection` | Selected |
| Affinity groups | `xdist_group` marks assigned in `pytest_collection_modifyitems` by fixture closure, under `--dist=loadgroup` | Two marks on one item form a combined group; group suffixes appear in node ids | xdist `remote.py` [src]; existing math pattern | Selected |
| Prerequisites before setup | Markers whose skip is added at collection (existing `corpus` route) | String `skipif` conditions evaluate at setup, booleans at import | pytest 9.1.1 `_pytest/skipping.py` [src] | Selected |
| Worker sizing | Managed `--workers` / `-n 0` from explicit node ids | Worker count is fixed before collection; `pytest_xdist_auto_num_workers` sees only arguments | xdist `plugin.py:16` [src] | Selected (RC02) |
| Import identity | Canonical absolute imports of support modules on `pythonpath` | Importlib mode names non-package files from the rootdir path, so relative imports from them load twice | pytest 9.1.1 `_pytest/pathlib.py` [src]; reproduced by the library-mechanics contributor [obs] | Selected |
| Deployment key closure | Standard library `ast`, `importlib.util.find_spec`, `hashlib.sha256` | A static walk sees module- and function-level imports; dynamic imports by string would escape it (none found in the chain) | Python 3.14 standard library | Selected |
| Implementation snapshot | `functools.cache` with an explicit override context manager | One snapshot per process; overrides restore on exit | Python standard library | Selected |
| Library lifecycle alternative | `pytest-postgresql` template janitor | No policy replay, leases or authenticated drops; a second owner | Earlier assessment, carried | Not adopted |
| Change-based selection | `pytest-testmon` | Records Python line coverage only; misses SQL, YAML, frozen artifacts and package-data reads | Library behavior as documented | Rejected (G6) |

---

## 8. Alternatives

| Alternative | Change propagation and local reasoning | Semantic authority and composition | Test and substitution boundary | Total machinery and operational risk | Decision |
|---|---|---|---|---|---|
| Current baseline | Consumers pick fixtures by accident; helpers move by import | One lifecycle owner; a bespoke serving seed; copies of the DDO admission sequence | Committed isolation everywhere, including where only rollback or read is needed | Head × workers × runs; scenario × cases × consumers; one forced checkpoint per drop | Revise |
| Proposed (§4) | Consumers state a recipe and an isolation class | One owner for names, leases, deployments and seeds; support modules; one refusal contract | Committed isolation where claimed; rollback and read where sufficient, each self-enforcing or proven per case | Adds a deployment key, a build lock, retention and a seed operation; removes the `cs_tpl_` scheme, a shadow fixture, dead fixtures and duplicated support | Selected |
| Library-owned (`pytest-postgresql`) | Moves lifecycle into a plugin | Loses replay, leases and authenticated drops | Same isolation | Integration gaps | Rejected |
| Simplest viable (run-scoped head, groups, worker sizing) | Small | Unchanged | Unchanged | Removes in-run duplication; keeps the focused-run floor and every per-case rebuild | Insufficient for either loop |
| Cross-run seeds and pure-preparation caches | Adds keys over the whole product and support code | Two reuse mechanisms over production's own cache | Unchanged | Rarely hit during implementation; an incomplete key is a G6 failure | Rejected now |

What becomes harder: the lifecycle owner gains a key computation and a second lock; test authors must
choose an isolation class. What becomes easier: a focused native run pays only for its own scenario; a
new DDO test composes support instead of copying a fixture; the cutover re-points builders once.

---

## 9. Change and failure scenarios

| Scenario and kind | Today | Target | Evidence |
|---|---|---|---|
| Add a native candidate migration (mechanism change) | Every worker of every run redeploys the grown chain | One build on the next run, then reuse | §4.1 |
| Edit product code in the edit–test loop (instance) | Head rebuilt per run per worker | Head reused; seeds rebuilt once per worker, as they must be | §4.1 |
| Add a DDO native test (domain extension) | Import the storage test module or copy the admission sequence; a full kernel per case | Request a kernel-recipe seed clone or the read class from DDO support | §4.3 |
| Add a refusal mutation to a family (instance) | One more full scenario build, clone and drop; may pass on a neighbouring guard | One more rolled-back case with its own reason and positive control | §4.2, §4.4 |
| Cut over from runs and tasks to demands (mechanism substitution) | Mixed tests name the removed machinery | Builders re-pointed once; mechanism-only tests deleted by name | §4.8 |
| A process is killed mid-head-build (failure) | Per-process head residue; another run's sweep can fail on it | Build residue skipped while connected, swept later; the head name never existed | §4.1, F04 |
| Two runs with one key; a sibling worktree on the cluster (concurrency) | Each builds its own heads | Shared head, or separate keys retained side by side | §4.1 |
| Provider assets absent on the qualifying host | Provider node passes through a controlled branch | Provider node blocked; controlled node passes | §4.5 |
| Interpreter upgrade (mechanism substitution) | Tests writing executor internals and the adapter both break | Only the adapter's documented reads break | DTA-026 |
| An installed file is edited while a process runs | Later calls notice | The process keeps its snapshot until restart | §4.6 A |
| Growth to 32 workers | Head builds double; module preparation doubles | One head; designated preparation once per group; seeds per worker (candidate per-run seeds) | §4.1 |

---

## 10. Gates and foundations

| Gate | Verdict | Evidence or scope reason | Required action |
|---|---|---|---|
| G1 Authority | Fail | The DDO admission sequence in six modules; the primary-layer scaffold in seven (DTA-029); names created in five places with sweep rules of their own, and a sweep key that differs from the lease key (DTA-030, F01) | §4.1, §4.3 |
| G2 Semantic fidelity | Pass, narrowly | Receipts keep outcome classes distinct; the provider/controlled loss is judged under G7 | — |
| G3 Validity | Fail | Refusal controls that cannot fail for their named regression (DTA-001); an absence control without a presence premise (DTA-027); doubles that admit payloads the wire forbids (DTA-034) | §4.4, §4.9 |
| G4 Hidden behavior | Pass | The verification-disabling double is opted into by name | Ownership move (DTA-009) |
| G5 Consistency and recovery | Fail, narrowly | Three names escape the sweep; a sweep that can target a live clone (F01); a sweep that fails unrelated runs on in-use residue (F04) | §4.1 |
| G6 Transformation and reuse | Pass, with premises | Current reuse is content-keyed; the proposed deployment key, seed premises and snapshot override state their validity conditions; dependency-based selection is rejected on this gate | Keep the premises with each mechanism |
| G7 Truthful capability claims | Fail | A controlled branch passes under a provider identity (DTA-028) | §4.5 |
| G8 Library leverage | Pass | PostgreSQL, pytest and xdist mechanisms are used; the bespoke parts (policy replay, authenticated drop, deployment key) have stated reasons | — |
| CI-G1 Fidelity (profile) | Pass for what was read | Source-capture tests keep unknown distinct from absent and use hand-authored node ids | — |
| CI-G2 Evidence closure (profile) | Unresolved, inherited | Which boundary covers the size-preflight query and structural-tool registration was not examined | Out of this review's scope |
| CI-G3 Evaluation integrity (profile) | Pass | Reference answers hand-authored and submitted through the real tool | — |

Foundations, for the test system as software. **FP-01** violated: support lives in test modules and
import bindings. **FP-02** violated: evidence class is not part of the test contract; doubles stand below
the boundary they claim; private executor state is written. **FP-03** violated: copied admission and
assembly sequences, divergent declaration families, superseded machinery. **FP-04** satisfied for oracle
independence across most of the suite, which is its strength, and violated for the contextual product
identity (DTA-033) and for scenario authority (DTA-009). **FP-05** violated: isolation need, refusal
reason and prerequisites are implicit. **FP-06** violated: focused controls bootstrap unrelated
preparation and ambient variables decide evidence class. **FP-07** violated (C1, C2, F05). Supporting
rules used: DP-01, DP-03, DP-09, DP-10, DP-16, DP-18, DP-19, DP-20, DP-22, DP-23. Heuristics used: H5,
H12, H13, H14, H19, H20, H21, H23, H24, H25, H26, H27, H28.

---

## 11. Relationships, prerequisite order and priority

**Shared causes.** DTA-024, DTA-025, DTA-031, DTA-018, DTA-032, F02, F03 and F05 share C1; they are
distinct defects with one design. DTA-025 and DTA-031 also depend on C2's classes. DTA-009, DTA-029,
DTA-030, F01, F04 share C4. DTA-033, 034, 035, 036 are the DDO transition's own concerns.

**Prerequisite order, by the capability each needs.**

1. **One naming and sweep authority** (DTA-030, F01, F04) before the deployment and seed operations, so
   one rule recognizes every name the lifecycle creates.
2. **The implementation snapshot** (DTA-032) early: it is small, it removes work everywhere, and its
   override is what lets seeds refuse to build under patched implementation inputs.
3. **The content-keyed deployment** (DTA-024) and **worker sizing** (F05): together they remove the
   focused-run floor. Independent of everything after.
4. **Isolation-class fixtures** in the package conftest, including the principal rollback connections and
   moving the DDL-committing consumer off the shared clone.
5. **Support modules and recipe values** (DTA-009, DDO support for DTA-031): the seed key and the
   cutover's re-pointing need them.
6. **The seed operation** (F03), migrating the serving seed onto it.
7. **The refusal contract** (DTA-001) per family, then **families onto seeds and the rollback class**
   (DTA-025, DTA-031). A family moves only with its contract.
8. **Evidence class** (DTA-028, DTA-018's skips) independently, before DDO-12.
9. **DDO evidence** (DTA-033, DTA-034) independently, before DDO-11 cutover and DDO-12.
10. **Cutover transfer** (DTA-035) inside DDO-06–11; **the union** (DTA-036) at DDO-12.
11. DTA-006, DTA-026, DTA-027, DTA-029, F02 groups, the lease idiom: independent.

**Sequencing with the DDO plan.** The DDO native tests are the fastest-growing footprint, and DDO-06–12
will add more. Steps 1–5 for the DDO modules — naming, deployment, isolation classes and DDO support with
kernel recipes — should land before DDO-06 adds native tests, so new tests start in the target shape
rather than in another copy of the kernel fixture.

**Priority by consequence.**

| Priority | Change and responsible component | Source findings | Closure evidence or revisit trigger |
|---|---|---|---|
| 1 | Evidence class split and prerequisite markers (test support, receipts) | DTA-028, DTA-018 (skips) | Provider identity blocked without assets |
| 1 | Content-keyed deployment and worker sizing (`native_test_support.py`, package conftest, managed route) | DTA-024, F05 | Reuse recorded across narrowed runs; one-node run with zero workers |
| 1 | Seeds, isolation classes, DDO support (lifecycle owner, package conftest, support modules) | F03, DTA-025, DTA-031, DTA-009 | Families and kernels built once per worker |
| 1 | Refusal contract (test sites) | DTA-001 | Each named site pins its reason |
| 1 | Literal identity vectors (DDO identity tests) | DTA-033 | Vector fails on changed framing |
| 2 | Implementation snapshot (production `contracts.py`, `analysis_contracts.py`, `grammar.py`) | DTA-032 | No reads after first per process |
| 2 | Affinity groups, staged builders (root conftest, builders) | F02, DTA-018 | Designated preparation once per group |
| 2 | Cutover transfer (DDO packages) | DTA-035 | Per-package closure |
| 3 | Naming and sweep authority (prerequisite of priority 1 lifecycle work) | DTA-030, F01, F04 | Every name swept by one rule |
| 3 | Wire-checked double, binding parity | DTA-034 | Case table through both paths |
| 3 | DDO-12 evidence column and provider run | DTA-036 | At DDO-12 |
| 4 | CPU timing; redaction order; preservation assertions; assembly owner; lease idiom | DTA-026, DTA-027, DTA-006, DTA-029 | As stated per finding |

**Conflicts between remedies, and how they resolve.** *Grouping against focused parallelism:* groups
cut total work in work-bound full runs but serialize a focused run; the target groups only where bodies
are cheap (designated preparations, rollback families) and leaves commit-class recipe consumers
parallel. *A keyed head against DTA-030's removal of a keyed template cache:* the removed scheme had no
producer and kept retention in a comment that is now the ownership stamp; the new head is designed in
the same owner with one recognition rule, so there is still one retention mechanism. *Seeds against
implementation overrides:* a seed built under a patched implementation would carry the patch into
every clone; seed builders refuse to run under an override. *Rollback sharing against ADR-0048's
rejection of rollback-only transactions:* resolved by restricting the class to claims that need no
committed cross-session isolation (RC04). *Run-private qualification heads against reuse:* qualification
pays one build, so evidence of record never depends on the deployment key's completeness.

**Fit of the corrections.** One lifecycle owner gains a deployment operation, a seed operation and one
naming function, all built on the existing `database()` acquisition; the serving seed moves onto the
seed operation, so there is one seed lifecycle. The read and rollback classes reuse the existing
per-worker clone instead of adding a rung. Affinity groups use the existing root hook, one group per
item. Committed isolation is kept for every claim that commits, races, cancels, notifies or uses a
second login. No double replaces a real boundary; the wire-checked double moves an existing double up to
the boundary. No case is merged and no lane changes. The 2026-11-12 recommendation of one maintenance
session per clone is withdrawn: those connections measure about 0.02 s per clone (contributor), so it has
no time rationale left.

---

## 12. Rule impacts

**RC01 (revised) — ADR-0032, "Fresh native tests clone a session deployment with explicit database
policy replay"** ([ADR-0032](../../adr/0032-native-test-deployment-equivalence.md); D3
[Native test deployment equivalence](../../design/D3-database.md#native-test-deployment-equivalence),
"Semantic templates expire with the session"; [D9](../../design/D9-repository-and-phase0.md) §4 Tests,
Database row). Proposed change: the head is built once per complete deployment key and reused by
narrowed runs across sessions, published atomically, retained by count and swept by the one lifecycle
owner; unnarrowed (qualification) runs build a run-private head; Option 3 is narrowed so that claims not
involving separate-login commits, races, cancellation or notification may use a read-only or
rolled-back transaction on a shared clone, with the premises of §4.2. Unchanged: policy capture, replay
and comparison per clone; authenticated, unforced drops; real-chain cold deployment controls; refusal on
unavailable replay authority. Dependent: DTA-024, DTA-025, DTA-031, F05's effect. If kept: DTA-024 stays
open and the focused-run floor remains; run-scoped sharing (option a) is still available within the
rule's "once per session" only if a run counts as a session, which needs the same wording change;
rollback-only families stay in the commit class on seeds.

**RC02 (revised) — Default worker count for narrowed runs** (`pyproject.toml:64`;
`scripts/test_receipts.py:1586–1593`; the completed
[parallel execution companion](../../plans/test-audit-resolution/parallel-execution-and-harness.md),
"Retain auto as initial default", `:113`). Proposed change: one explicit node id runs with `-n 0`; *k*
node ids with `-n min(auto, k)`; path selectors keep `auto`. Dependent: F05. If kept: each focused run
keeps its worker startup and gateway shutdown; with the content-keyed head, idle workers at least no
longer build anything.

**RC03 — Where DDO native checks run**
([contracts and compilation companion](../../plans/declared-data-operations/contracts-and-compilation.md),
`:359–361`: "Native checks use the project's working database under its ordinary custody; this plan does
not require disposable databases"). Proposed change: DDO native checks run on clones and seeds of the
deployed head under the named isolation classes; the working database is not a test lane. The coordinator
plan already records isolated test databases and a working database behind the head; AGENTS.md's
development-database section keeps isolated test databases where a test requires isolation. Dependent:
DTA-031. If kept: the statement remains unrealizable — the working database lags the head and
coalescing, revocation and concurrency claims need isolation — and the plan stays self-contradictory;
the design here does not change.

**RC04 — ADR-0048, "Read-only serving scenarios clone a session-local populated seed"**
([ADR-0048](../../adr/0048-populated-native-scenarios.md); D3 native-test section, "Accepted target"
paragraph). Proposed change: seeds become the general mechanism for any recipe meeting the seed premises
of §4.1, per worker; "deployment/publication/write-lifecycle tests remain independently prepared"
narrows to tests whose claim includes the seeded stages; Option 2's rejection of a rollback-only
transaction narrows to claims that need committed cross-session isolation. Unchanged: no persistent
scenario cache, no shared mutable database (nothing commits to a shared clone), every reader a fresh
clone with replay, seed origin and clone context distinct in receipts, expected results authored at each
test. Dependent: F03, DTA-025, DTA-031. If kept: seeds stay limited to the serving scenario; the kernel,
private-source and domain rebuilds remain per test.

No other rule changes. The reporting rule that a mocked provider is never passed is implemented by
DTA-028's correction, not changed. The BEP selection of five-second grace is kept and pinned (DTA-026).
The parallel companion's "no custom scheduler" holds: grouping uses marks under the built-in scheduler.
No ADR or design section requires per-call reading of implementation determinants; DTA-032 implements
`trusted_execution_inputs`' documented lifetime. `ops/postgresql/corpus.conf:7–9` keeps its lock capacity;
its comment's rationale (concurrent bootstrap across all workers) weakens but nothing needs changing.

---

## 13. Verification and uncertainty

| Claim | Label and date | Basis | Gap |
|---|---|---|---|
| Per-process head, per-worker build, `auto` for narrowed runs | Interface-checked 2026-11-13 | `tests/conftest.py:255–260`, `native_test_support.py:612–630`, `test_receipts.py:1586–1593` | — |
| Build and overhead durations | Measured, read 2026-11-13 from stored results (runs 2026-11-10 to 13), shared host | Audit evidence README and contributor readings | Orders of magnitude; nothing profiled |
| The chain's machinery imports and frozen-artifact pattern | Interface-checked 2026-11-13 | `grep` over `semantic_alembic/versions/*.py`; `semantic_ddo_renewal_v1.py`; `du` | Transitive closure not computed here |
| Every interpretation context re-reads determinants | Interface-checked 2026-11-13 | `analysis_contracts.py:409–485,638–659`, `contracts.py:1166–1182,1380–1446` | Share of test time not profiled; `MathContext.key()` not read |
| Lease idiom accepted by the data-task guard | Interface-checked 2026-11-13 against `src/…/execution_guards.sql` | Guard conditions | The deployed head's guard not read; `:2099` premise open |
| DTA-036's list is a receipt that predates the deletion | Interface-checked 2026-11-13 | `git merge-base --is-ancestor 0de179fc7 9d996b32d` | — |
| Isolation and seed classification of families | Contributor AST heuristic plus partial reads, 2026-11-13 | Supporting document | Per family confirmation is planning work |
| Double loading through relative imports from non-package directories | Observed by a contributor's probe (pytest 9.1.1) | Library-mechanics report | Whether any test's result changes: not established |
| Every remedy | Proposed | — | Not implemented |

Material premises that could change a remedy, and how to settle them during implementation:

- **No long-lived process relies on per-call determinant rereads** (DTA-032). Settled by the production
  owner; if false, use the stat-keyed alternative.
- **Seeded kernel rows contain no database or role names** (DTA-031). Settled by the first seed clone's
  tests.
- **`build_domain_case`'s dominant stage** (F03 priority for the domain family). Settled by one profile of
  one build inside the consuming package; it changes how much seeding helps that file, not the design.
- **Head size on disk** (retention count). Observed once after the first build.
- **Whether a family's refused operation checks a lease** (DTA-025 membership). Settled by reading its
  guard.
- **Whether recipe consumers assert time relations or write into scenario files** (F03). Settled by reading
  consumers; excludes a recipe from seeding.
- **Whether the deployed guard matches `src/…/execution_guards.sql` for data tasks** (lease idiom; the
  `:2099` site). Settled by reading the head or running that test.

None of these needs a probe before planning. Unexamined breadth is not a finding; the audit's thin areas
remain thin.

**Disagreements with the inputs.** DTA-036's "stale union" is an accurate historical receipt (§6.5).
DTA-032 is not standalone-only (§6.1). The production-seams report is right that no pool factory seam
exists beyond the module global, which corrects the 2026-11-12 review's wording. The DDO cutover
contributor's dispositions are mostly token matches and are carried only as leads. The 2026-11-12
review's D1 (controller hooks and run-end cleanup) is replaced: content-keyed names need no controller
owner.

---

## 14. Dispositions and supersession

No plan owns these findings. Each has a Deferred row here until plan creation selects it; the
reopening event for every row is plan creation from this review, or adoption by the
[declared-data-operations coordinator](../../plans/declared-data-operations_2026-11-12.md) for the rows
it names, whose findings table then owns current status. DTA-001–023 as they stood on 2026-11-05 remain
with the [test audit resolution coordinator](../../plans/test-audit-resolution_2026-11-05.md); the rows
below cover current-source manifestations. These rows replace the 2026-11-12 review's Deferred rows.

| Finding | Disposition | Scope consequence while deferred | Reopening event |
|---|---|---|---|
| DTA-001 | Deferred | Named refusal controls can pass with their guard removed | Plan creation; earlier if a named guard changes |
| DTA-006 | Deferred | Named tests establish presence, not preservation | Plan creation |
| DTA-009 | Deferred | Support decided by import; double loading across non-package directories | Plan creation; earlier with any seed or DDO support work |
| DTA-016 residue | Deferred | Non-complete stdio modes do not pin task state | Plan creation |
| DTA-018 | Deferred | Focused controls pay for and fail on unused preparation | Plan creation |
| DTA-024 | Deferred | Every worker of every run builds the head; the focused floor remains | Plan creation; requires RC01 |
| DTA-025 | Deferred | Refusal families rebuild per case | Plan creation; requires RC01/RC04 for the rollback class |
| DTA-026 | Deferred | Real grace waits; private executor writes | Plan creation; earlier on a CPython change |
| DTA-027 | Deferred | Redaction-order control passes under either order | Plan creation; earlier if clipping changes |
| DTA-028 | Deferred | A passing provider node may not have run the provider | Plan creation; before any qualification counting PM2 provider evidence |
| DTA-029 | Deferred | An assembly change must be mirrored in seven copies | Plan creation |
| DTA-030 | Deferred | Dead branches maintained; three names escape the sweep | Plan creation; with any DTA-024 work |
| DTA-031 | Deferred | Each DDO native case rebuilds the kernel; support owned by a test module | DDO coordinator adoption or plan creation; before DDO-06 adds native tests |
| DTA-032 | Deferred | Per-call determinant reads in tests and production | Plan creation |
| DTA-033 | Deferred | Product identity unchallenged by independent vectors | DDO coordinator adoption or plan creation; before DDO-11 |
| DTA-034 | Deferred | Routing doubles below the wire; binding semantics on SQLite only | DDO coordinator adoption or plan creation; with DDO-03's parity obligation |
| DTA-035 | Deferred | Cutover could delete required behavior with its test | DDO coordinator adoption; at each retiring package |
| DTA-036 | Deferred | DDO-12 obligations without an evidence mapping | DDO coordinator adoption; at DDO-12 |
| F01 | Deferred | Sweep could target a live `committing_db` clone | Plan creation; closed by DTA-030 |
| F02 | Deferred | Designated preparation repeated per worker | Plan creation |
| F03 | Deferred | Identical committed scenarios rebuilt per consumer | Plan creation; requires DTA-009, RC04 |
| F04 | Deferred | A killed run can fail other runs' native setup | Plan creation; with DTA-024 |
| F05 | Deferred | Every focused run starts sixteen workers | Plan creation; requires RC02 |
| RC01–RC04 | For operator confirmation in plan creation | — | Plan creation |

**Supersession.** This review replaces the 2026-11-12 review and its supporting document as the current
assessment of the test system. F01–F03 keep their identities with the same meaning; RC01 and RC02 keep
their identities with revised content; the supporting document of this review states what becomes of
each 2026-11-12 option. The 2026-11-12 review stays recoverable in Git; whether it leaves the working
set is the coordinator's decision under ADR-0001 once nothing cites it. Two items return to the test
audit as refinements: DTA-032's footprint covers the prepared branch, and DTA-036's lists are receipts.
One observation goes to the broad audit: per-span and per-item interpretation-context preparation in
production pays the same per-call reads. Observations for the DDO plan owner: the findings table rows
for DDO-CA-01, 02 and 04 predate tests that now exist (audit observation, agreed); the database-lane
statements disagree (RC03); admission verifies the native deployment twice per release (§6.1, DTA-031);
the `:2099` lease update premise.

---

## 15. Architectural judgment and decision

| Judgment | Verdict | Scenario evidence and scope | Required action |
|---|---|---|---|
| A1 Localize change | Violated | A helper edit in the storage test module changes what seven modules exercise; an admission or assembly change must be mirrored in six or seven copies; a grace-constant change fails timing literals | §4.3, DTA-026 |
| A2 Encode domain meaning explicitly | Violated, scoped | The test system's consequential distinctions — isolation need, scenario recipe, preparation validity, refusal reason, evidence class — are implicit; the current product identity has no independent challenge. Receipts' outcome classes and native context are explicit strengths | §4.2–§4.5, §4.9 |
| A3 Extend through composition | Violated | A new DDO native test copies a fixture or imports a test module; a new variant needs a fixture-name override; superseded machinery is maintained | §4.3 |
| A4 Fit execution to the supported workload | Violated | Focused runs pay a head build that grows with every candidate, sixteen worker start-ups and a full scenario build per case; the full union repeats head builds per worker, scenarios per case and consumer, preparation per worker, and determinant reads per call. A credible route exists (§4.1–§4.7) that removes that work while keeping committed isolation wherever a claim needs it | §4 |

**Bounded decision: Revise.** The assurance architecture — sealed deployments, fresh committed clones with
policy replay, truthful receipts, independent expectations — is accepted as the base to preserve. The
preparation lifetimes, isolation contract, negative-evidence contract, support ownership, evidence-class
identity and the DDO transition need the corrections above. Evidence strength: Interface-checked source,
Measured durations read from stored results, every remedy Proposed.

**Enclosing architecture:** the test system needs revision in the named areas. The product architecture
is not assessed beyond the three seams; DTA-032's production consequence is returned to the broad audit.
Nothing here is release qualification.

**Next decision and owner.** The operator, in plan creation, decides RC01–RC04 and where the DDO-related
findings live. The first steps that unblock the most are the naming and sweep authority with the
content-keyed deployment and worker sizing — which remove the focused-run floor — and, for the DDO
modules, the isolation classes and DDO support with kernel recipes, landed before DDO-06 adds native
tests. The refusal contract, the evidence-class split and the identity vectors proceed independently.

---

## Coordinator publication note — 2026-11-13

Published by the coordinator without change to the reviewer's judgment or text. Before
publication the coordinator opened these cited sources at `main` `196145357` and found them as
described: the ancestry of `0de179fc7` and `9d996b32d` and the plan's statement that its recorded
campaigns are not DDO-12 (DTA-036); the OID-keyed ownership stamp
(`src/corpus_structure/core/db/ownership.py:87–89`); the absent `__init__.py` in `tests/math/` and
`tests/acceptance/` and the relative import in `tests/acceptance/conftest.py:3–4`; the committed DDL
on the shared clone (`tests/db/test_lifetime_native.py:163–164`); the digest comparison and
`trusted_execution_inputs` docstring behind DTA-032 (`analysis_contracts.py:454–469`,
`contracts.py:1166–1169`); the `auto` worker default for narrowed runs
(`scripts/test_receipts.py:1586–1593`); and the 1.3 GB chain directory (`du`). Not re-verified by the
coordinator: the library behaviors taken from the library-mechanics report, the per-family
classifications in the supporting document, and line citations inside the DDO test modules, which
were under concurrent edit.

The two refinements this review returns to the test audit (DTA-032 covers the prepared branch;
DTA-036's lists are accurate receipts) are recorded in the
[account](../test-audit/README.md#refinements-returned-2026-11-13) with this attribution.

