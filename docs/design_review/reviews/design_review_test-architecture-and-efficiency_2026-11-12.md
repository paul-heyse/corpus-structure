# Design review — test architecture and efficiency

> **Superseded, 2026-11-13.** The current assessment is the
> [design review of the test system target design](design_review_test-system-target-design_2026-11-13.md),
> which carries F01–F03 and RC01–RC02 forward by identity and states what becomes of each option
> here. This document is retained as that review's input.

**Design / target review · 2026-11-12 · principal reviewer: delegated `design-reviewer` (fresh
context; author of neither the audit nor the tests); published by the coordinator without change
to the judgment.** Supporting document: [efficiency opportunities](test-architecture-and-efficiency/efficiency-opportunities.md),
which inventories Part B and routes back here for every remedy shared with Part A.

This review is evidence, not authority. Every remedy below is **Proposed**. Source facts are
**Interface-checked by source inspection, 2026-11-12**, at `main` `784d86f11`. Nothing was run.

**Path convention.** Paths beginning `tests/` or `src/` are relative to `python/corpus-structure/`.
Repository-root test paths are written as root `tests/…`; other root paths begin with `scripts/`,
`ops/`, `docs/`, `conftest.py` or `pyproject.toml`. Citations are `path:line` at the baseline.

---

## 1. Scope, outcome and coverage

| Field | Value |
|---|---|
| Subject | Test code, test evidence and shared test infrastructure: `tests/` (package), root `tests/`, `scripts/native_test_support.py`, `scripts/qualification_plugin.py`, `scripts/test_receipts.py`, root `conftest.py`, pytest/xdist configuration in `pyproject.toml`, and the `ci test` route as it prepares and runs selections. Production is read only as the contract the tests protect |
| Baseline | `main` `784d86f118c5dcd061e22901abaf6032c3ffe6b5`, clean tree apart from one untracked library overview outside scope |
| Audit consumed | Test audit publication `cf24c0e80` ([account](../test-audit/README.md)), audited source `56f8d309` plus the then-dirty tree, DTA-001 … DTA-030. The coordinator reconciled the 21 test-scope files changed between that capture and this baseline; every site the audit cites in them is unchanged. The broad production audit is not refreshed; this is a test-only engagement |
| Standard | Core principles 3.3 with efficient-architecture heuristics 1.0, test-assessment companion 1.2, review template 3.3, repository binding; code-intelligence profile 1.4 only for served or agent-facing test claims |
| Tier · purpose | Design · target |
| Focus (operator, 2026-11-12) | Part A: every audit finding, all foundations. Part B: principle-focused on execution fit (FP-07/A4, DP-10/20, the heuristics, test-assessment §8). Library scope open; libraries are hypotheses |
| Remedy latitude (operator) | Same assurance, less work. Every existing claim keeps at least its present evidence strength. Fixtures, scheduling, preparation lifetimes, composition and assertions may be restructured and assertions strengthened. No dropped cases, weakened oracles, doubles replacing real boundaries, lane or tier moves, or merged or removed cases. Ideas outside this are listed as "recorded, not developed" in the supporting document |
| Evidence rule (operator) | No benchmarking, test runs or database operations. An efficiency opportunity needs no measurement when a gain is very plausible from structure and a slowdown is very unlikely or impossible; each says why. No speed figure is asserted. One retained receipt is cited as historical orientation with its attribution |
| Maturity and outcome | Design stage, one operator, Codex and Claude agents as developers. This review should let plan creation choose a coherent target for preparation lifetimes, negative-evidence contracts, scenario ownership and evidence-class identity, and retire the superseded support it found |

### Functional intent of the test system and workload premise

The product's functional target (DESIGN §1.1) is an evidence-backed representation of what
documents state, held in PostgreSQL 18 under a declared semantic release, with restricted
principals, native custody guards and agent-facing served answers. The test system exists to
give the operator and agents three things: discriminating evidence that each of those guarantees
holds (native refusals, provenance, served answers, cold determinism); truthful qualification
receipts that say for every node whether it passed, failed, was blocked or was inapplicable, and
never present controlled evidence as provider evidence; and feedback fast enough to sit inside a
development iteration.

Workload premise, drawn from that intent and the current tree:

- **Focused selections** of one to a few dozen tests, very often native, run many times per
  iteration by the operator and agents through `uv run ci test -- PATH` or plain pytest.
- **The full ordinary lane** at scope end: about 4,100 test functions by grep (3,841 package,
  288 root) expanding through 852 `parametrize` decorators; the retained 2026-11-07 receipt had
  5,070 nodes. It runs as `-n auto` (16 workers on a 16-core, 32-thread host shared with GPU work)
  against the dedicated cluster `18/corpus`, which also hosts the persistent development database
  (`ops/postgresql/corpus.conf:6`, `max_connections = 256`).
- **Growth**: the authored test scope grew from 418 to 567 files between audit baselines a week
  apart; the semantic migration chain has 240 revisions and grows with each native change;
  scenarios grow with the BEP and full-book work. Any cost multiplied by worker count, by
  parametrized case or by migration count grows with all three.

### Method and coverage

I loaded the standard and the binding sections the brief names, read all five audit pages, and
used the four evidence maps and the receipt summary
([retained evidence](../evidence/2026-11-12_test-architecture-review/README.md)) as leads. I opened the decisive sources at the
grain relied on: the native lifecycle (`scripts/native_test_support.py` acquisition, replay,
lease, sweep, drop and template code; `tests/conftest.py`; `tests/semantic/serving_scenarios.py`;
ADR-0032), the eight DTA-025 families and the two pure-function families, the completion SQL's
lease handling, the xdist 3.8.0 `loadgroup` scope split and auto worker count, pytest 9.1.1's
`import_path`, the managed-route argument builder and receipt status derivation, and every
DTA-018, DTA-026, DTA-027 and DTA-028 site. DTA-001, 006, 009, 029 and 030 were checked at
representative sites. I did not reread the reading union; areas the audit marks thin (most of
`tests/methods/`, some semantic modules, root `tests/scripts/test_native_auth.py` 700–1084) stay
thin. Where I rely on an evidence map without reopening the source, I say so.

---

## 2. Integrated assessment

The test system's assurance core is strong and should constrain every correction. Fresh committed
clones of a sealed head, with the database policy captured, replayed and compared before a clone
is exposed (`scripts/native_test_support.py:306–371`), give native tests real logins, real commits
and isolation. Receipts classify setup prerequisites as `blocked` rather than success
(`scripts/test_receipts.py:466–490`), refuse to call a native node passed without item-bound
acquisition context, and keep failed and interrupted records. Expectations are mostly authored
independently: identity vectors, literal Arrow rows, analytic forms and hand-authored gold. Many
native refusals already pin SQLSTATE and message after a positive control in a rolled-back
savepoint, and the forged-judged family pins a per-case reason table
(`tests/semantic/test_local_semantic_admission_native.py:597–621`). The serving seed
(`tests/semantic/serving_scenarios.py:241–344`) shows the repository already knows how to seal a
committed scenario and clone it.

The problems have five structural causes. They are not one redesign, but the first two depend on
each other in a way that decides the target.

**C1 — Preparation lifetimes do not follow validity.** The sealed head is a pure function of the
migration chain and cluster template, yet it is deployed once per pytest process, which under
`-n auto` means once per participating worker (DTA-024). Identical committed scenarios are rebuilt
through real producers for every case of rollback-only refusal families (DTA-025) and, beyond the
audit's footprint, for every committing consumer of a default recipe, although a clone of a sealed
seed would give the same fresh committed state (F03). Module- and session-scoped preparation is
rebuilt on every worker that runs one consumer, because `--dist=loadgroup` makes each ungrouped
test its own work unit (F02). Focused controls build preparation their claim never reads, and
inherit its failures (DTA-018). These are avoidable repeated work established from structure (H5,
H12, H19, DP-10), and they grow with workers, cases and migrations. They are the dominant
efficiency story; the historical receipt's split of 56 % call, 33 % setup and 11 % teardown is
orientation only.

**C2 — Negative and absence evidence does not prove reach and reason.** Some refusal controls would
pass if the guard they name were removed, because the input also violates a neighbouring guard
or the assertion accepts any database error (DTA-001). Some absence assertions have no presence
premise or a non-discriminating case (DTA-027), and some presence and count assertions stand in
for preservation claims (DTA-006). **C1 and C2 compose, and the composition is the key design
point.** Sharing a committed scenario across refusal cases is only safe when every case proves
reach (a minimal-pair positive control on the same state, in the same transaction) and reason (the
boundary's exact diagnostic identity). Without them, a scenario that drifted, for example a lease
that expired or a commit that leaked from an earlier case, would turn each refusal into a vacuous
pass. With them, the positive control that a shared scenario makes nearly free is also the
per-case proof that the scenario is still valid. Fidelity rises as work falls; neither correction
should land in a shared family without the other.

**C3 — Scenario and support ownership is decided by import binding.** Which release a case runs
under depends on which `private_source_options` fixture name an import resolved
(DTA-009); test modules serve as libraries for other test modules, including a
verification-disabling double, and absolute imports of test modules in non-package directories
load a second copy of the module; a production assembly sequence is hand-copied (DTA-029);
superseded fixture machinery and sweep branches survive (DTA-030), and the sweep's lock key
diverges from the lease key it is meant to respect (F01). C3 is also a prerequisite of C1: a shared
scenario or seed needs an explicit recipe value as its key, and a key that depends on import
resolution cannot be trusted.

**C4 — Evidence class and prerequisites are decided in test bodies.** One provider test identity
passes on a controlled branch when an asset variable is unset, so a passing receipt does not say
whether a provider ran (DTA-028); provider and asset prerequisites are checked in bodies after
expensive fixtures have run (DTA-018). The repository's own marker route (`corpus`, `skipif`)
already decides prerequisites before setup and records them in receipts.

**C5 — Lifecycle controls couple to timing and interpreter internals.** CPU teardown controls wait
out five-second production grace periods with literal bounds and write CPython-private executor
state to build interleavings (DTA-026).

**Overall judgment: Revise.** The architecture of assurance is sound and worth keeping; the
physical realization of preparation and parts of the evidence contracts are not fit for the
focused-iteration workload or for honest qualification. A1–A4 are in §15. The corrections fit
together around one lifecycle owner, one scenario-recipe value and one refusal contract; nothing
here needs a second fixture framework, a double in place of a real boundary, or weaker isolation
for any claim that needs committed isolation.

---

## 3. Responsibilities and semantic ownership in the test system

The test system has its own domain: preparations with validity premises, scenarios with recipes,
evidence classes, prerequisites and refusal reasons. The table names who owns each now and in the
target.

| Concept | Current owner and how it is decided | Target owner and representation |
|---|---|---|
| Native preparation lifetime (head, clone, rollback) | `PgAdmin` in `scripts/native_test_support.py` plus fixtures in `tests/conftest.py`, `tests/semantic/conftest.py`; per-process head; serving seed in a test module | The same lifecycle owner, with five declared lifetimes (§4); serving seed migrates into it |
| Scenario recipe (which release, which source text, which methods) | Overridable `private_source_options` fixture resolved by import (`tests/semantic/native_record_fixtures.py:781–819`), indirect parameters, one `callspec` read | A frozen recipe value at the call site, also the key for shared scenarios and seeds |
| Scenario builders and doubles | Support modules and, for 75 owners, `test_*` modules imported by other test modules | Support modules only; test modules do not import test modules |
| Refusal reason | Inline idioms, from bare exception class to per-case reason tables | One contract (reach, reason, effect) with a narrow helper for the native unwrap and comparison |
| Evidence class (provider or controlled) | An environment variable read inside one body | Test identity plus a prerequisite marker decided before setup and visible in receipts |
| Prerequisite | Session fixtures (`PrerequisiteUnavailable`), the `corpus` marker hook, `skipif`, and body-level `pytest.skip` | Marker or session fixture before any scenario preparation; body-level skips removed |
| Scheduling affinity | Root `conftest.py` assigns `xdist_group("math_preparation")` by fixture closure | The same mechanism assigns family and expensive-preparation groups; one group per item |

---

## 4. Target state

### 4.1 Preparation lifetimes

Five lifetimes, each with one owner, a validity premise, an isolation guarantee and a cleanup
owner. All database objects are created through the existing `PgAdmin.database()` acquisition with
its lease, authenticated creation, policy replay and comparison, and authenticated drop.

```
cluster template cs_template (provisioned)
   │  CREATE DATABASE … TEMPLATE (WAL_LOG) + policy replay/compare
   ▼
L1 run head ─ one per run, shared by every worker; built once under an exclusive
   │          advisory lease, sealed, leased shared by users; dropped by the run controller
   ├──► L2 scenario seed ─ one per worker per recipe value; committed, time-independent,
   │        │              sealed, files read-only; dropped at worker session end
   │        └──► L3 fresh clone per committing test (from the seed)
   ├──► L3 fresh clone per committing test (from the head)            [today's default]
   ├──► L2f family scenario ─ one clone per rollback-only family, on one worker (group mark)
   │        └──► L4 case transaction ─ always rolled back; savepoints for positive control
   └──► L2r read-only head clone ─ the existing per-worker `db` session clone, never committed to
            └──► L4r case transaction ─ READ ONLY, always rolled back (pure SQL-function checks)
```

| Lifetime | Holds | Validity premise | Isolation it gives | Cleanup owner |
|---|---|---|---|---|
| L1 run head | Deployed migration chain, sealed | Pure function of `cs_template` and the chain on disk when the run began; nobody connects | Immutable source for clones | Run controller at session end; next run's sweep after an interrupted run |
| L2 scenario seed | A recipe's committed state, before any claim or lease | Built by real producers once; sealed; no time-bound state; files read-only | Each consumer gets its own fresh clone | Worker session end; sweep |
| L3 fresh clone | Real commits, logins, races, cancellation | Created from L1 or L2 with policy replay | Full committed isolation per test | `database()` exit |
| L2f family scenario | One family's identical committed scenario | Every case confines writes to a rolled-back transaction; per-case positive control proves the scenario still admits the clean input | Rollback isolation per case | Family fixture teardown via `database()` |
| L2r/L4r read-only head | Head schema and functions | No consumer commits to the session clone; each case transaction is READ ONLY | Read-only transaction per case | Worker session end |

What consumers stop knowing: which process built the head, whether a scenario was built for them or
cloned, and how a family's scenario is shared. They state a recipe value and whether their claim
needs committed isolation, a rolled-back transaction or a read-only one.

### 4.2 Negative and absence evidence

A negative control has three parts, kept visible at the call site: **reach** (a minimal-pair
positive control on the same prepared state in the same transaction, rolled back), **reason** (the
boundary's own diagnostic identity: SQLSTATE plus constraint name or primary message, and a
context field where several guards share a message; exception type plus message or code for Python
and CLI refusals), and **effect** (absence of what the guarded operation would have left). An
absence assertion has a **presence premise** in the same output and a **discriminating input**
that the wrong implementation would mishandle visibly.

### 4.3 Scenario ownership

Scenarios are built by support modules from frozen recipe values. Large builders compose stages
(release persisted, views published, run and task created, completed or sealed) that consumers can
stop at. Doubles that disable production verification live in a named support module with their
scope stated. Test modules do not import from test modules.

### 4.4 Evidence-class identity and prerequisites

A provider-backed claim and a controlled claim have different test identities. A prerequisite is a
named marker or a session fixture decided before any scenario preparation, and it reaches the
receipt as `qualification_prerequisite` like the `corpus` marker does today. Whether a missing
provider prerequisite is `blocked` or `inapplicable` is declared by the qualification policy owner,
not by the test body.

### 4.5 Timing-coupled lifecycle controls

Timing windows derive from the constants under test, short values serve behavioural controls, one
cheap assertion pins the selected production values, and fault injection uses the module's factory
seam rather than writing interpreter-private executor state.

---

## 5. Finding index

Audit identities are those of publication `cf24c0e80`. "Retain", "Refine" and "Reject" judge the
diagnosis; "Confirm" means the audit reports the finding as corrected or holding without defect
and I agree. Disposition for every open row is in §14.

| ID | Audit anchor | Judgment of the diagnosis | Cause | Priority |
|---|---|---|---|---|
| DTA-001 | [evidence-and-discrimination#dta-001](../test-audit/evidence-and-discrimination.md#dta-001) | Retain; refined: privilege sites are discriminated by SQLSTATE alone, so pinning `42501` closes them without new inputs | C2 | High |
| DTA-002 | [execution-and-qualification#dta-002](../test-audit/execution-and-qualification.md#dta-002) | Confirm | — | — |
| DTA-003 | [execution-and-qualification#dta-003](../test-audit/execution-and-qualification.md#dta-003) | Confirm | — | — |
| DTA-004 | [retirement-transfer#dta-004](../test-audit/retirement-transfer.md#dta-004) | Confirm | — | — |
| DTA-005 | [support-structure#dta-005](../test-audit/support-structure.md#dta-005) | Confirm | — | — |
| DTA-006 | [evidence-and-discrimination#dta-006](../test-audit/evidence-and-discrimination.md#dta-006) | Retain | C2 | Medium |
| DTA-007 | [evidence-and-discrimination#dta-007](../test-audit/evidence-and-discrimination.md#dta-007) | Confirm; its open question becomes a seed premise (§6.1) | — | — |
| DTA-008 | [support-structure#dta-008](../test-audit/support-structure.md#dta-008) | Confirm | — | — |
| DTA-009 | [support-structure#dta-009](../test-audit/support-structure.md#dta-009) | Retain; refined: the open two-module question is settled (duplicates for eight non-package targets) | C3 | Medium; prerequisite of C1 |
| DTA-010 | [evidence-and-discrimination#dta-010](../test-audit/evidence-and-discrimination.md#dta-010) | Confirm | — | — |
| DTA-011 | [evidence-and-discrimination#dta-011](../test-audit/evidence-and-discrimination.md#dta-011) | Confirm | — | — |
| DTA-012 | [support-structure#dta-012](../test-audit/support-structure.md#dta-012) | Confirm | — | — |
| DTA-013 | [evidence-and-discrimination#dta-013](../test-audit/evidence-and-discrimination.md#dta-013) | Confirm | — | — |
| DTA-014 | [retirement-transfer#dta-014](../test-audit/retirement-transfer.md#dta-014) | Confirm | — | — |
| DTA-015 | [evidence-and-discrimination#dta-015](../test-audit/evidence-and-discrimination.md#dta-015) | Confirm | — | — |
| DTA-016 | [support-structure#dta-016](../test-audit/support-structure.md#dta-016) | Confirm; narrow residue gets a one-line strengthening | C2 | Low |
| DTA-017 | [execution-and-qualification#dta-017](../test-audit/execution-and-qualification.md#dta-017) | Confirm | — | — |
| DTA-018 | [execution-and-qualification#dta-018](../test-audit/execution-and-qualification.md#dta-018) | Retain | C1, C4 | Medium |
| DTA-019 | [evidence-and-discrimination#dta-019](../test-audit/evidence-and-discrimination.md#dta-019) | Confirm | — | — |
| DTA-020 | [evidence-and-discrimination#dta-020](../test-audit/evidence-and-discrimination.md#dta-020) | Confirm | — | — |
| DTA-021 | [execution-and-qualification#dta-021](../test-audit/execution-and-qualification.md#dta-021) | Confirm corrected | — | — |
| DTA-022 | [execution-and-qualification#dta-022](../test-audit/execution-and-qualification.md#dta-022) | Confirm corrected | — | — |
| DTA-023 | [evidence-and-discrimination#dta-023](../test-audit/evidence-and-discrimination.md#dta-023) | Confirm; residue kept with the audit's trigger | — | — |
| DTA-024 | [execution-and-qualification#dta-024](../test-audit/execution-and-qualification.md#dta-024) | Retain; refined with cleanup ownership and the cluster lock-sizing consequence | C1 | High |
| DTA-025 | [execution-and-qualification#dta-025](../test-audit/execution-and-qualification.md#dta-025) | Retain; footprint refined (six members, one conditional, one excluded) and lease premise narrowed | C1 | High |
| DTA-026 | [execution-and-qualification#dta-026](../test-audit/execution-and-qualification.md#dta-026) | Retain the timing part; refine the private-state part | C5 | Medium |
| DTA-027 | [evidence-and-discrimination#dta-027](../test-audit/evidence-and-discrimination.md#dta-027) | Retain | C2 | Medium |
| DTA-028 | [support-structure#dta-028](../test-audit/support-structure.md#dta-028) | Retain | C4 | High |
| DTA-029 | [support-structure#dta-029](../test-audit/support-structure.md#dta-029) | Retain; footprint refined (seven copies; digest handling splits three to three) | C3 | Low–medium |
| DTA-030 | [retirement-transfer#dta-030](../test-audit/retirement-transfer.md#dta-030) | Retain; extended (a second sweep-escaping name; one unreferenced support module) | C3 | Medium |
| F01 | this review | New: the sweep's lock key for `ci_test_<pid>_<n>` differs from the lease key | C3 | Medium |
| F02 | this review | New: module- and session-scoped preparation rebuilt on every worker that runs a consumer | C1 | Medium–high |
| F03 | this review | New: committing consumers rebuild identical committed scenarios through producers | C1 | High |

---

## 6. Corrective arguments

### 6.1 C1 — Preparation lifetimes

#### DTA-024 — Each xdist worker rebuilds the same sealed head deployment

**Diagnosis: retain, refined.** `semantic_head_template` is session-scoped and names its database
with `os.getpid()` (`tests/conftest.py:255–260`); `PgAdmin.semantic_template` creates it from
`cs_template`, runs the full Alembic upgrade in one transaction and seals it
(`scripts/native_test_support.py:613–630`). Under xdist each worker is a session, `-n auto` gives
16 workers (`pyproject.toml:46–55`; xdist 3.8.0 `plugin.py:16–34` uses physical cores), and the
managed lane passes `auto` unless `--workers` is given (`scripts/test_receipts.py:1587–1593`).
Under `loadgroup`, each ungrouped test is its own work unit (`xdist/scheduler/loadgroup.py`, the
scope is the whole node id unless an `@group` suffix is present), so a focused selection of *k*
native tests can deploy the head up to *k* times and a full run deploys it on every worker. Two
refinements. First, the per-worker deployment already shaped cluster configuration: the comment at
`ops/postgresql/corpus.conf:7–9` raises `max_locks_per_transaction` to 1024 because "concurrent
native test bootstrap holds temporary validation relation locks across all auto-selected xdist
workers". Second, the template's cleanup is tied to the process that built it
(`database()` drops at context exit, `scripts/native_test_support.py:477–493`), so sharing needs a
new cleanup owner, not only a new build site. The historical receipt (2026-11-07, older source)
shows small `db/` modules whose only native fixture is a session clone taking 12–24 s of setup per
test; that is consistent with, but does not establish, head deployment on first native use per
worker.

**Target behaviour.** One head per run. The run's name follows the sweepable pattern
`cs_sem_head_<controller pid>_<hex12>` and reaches workers through xdist's `pytest_configure_node`
/ `workerinput` channel (or is generated locally when xdist is off). The first worker to need it
takes an exclusive advisory lease on the name; if the database is absent it builds and seals it,
if it exists unsealed it is partial residue it may drop and rebuild, and if it is sealed it reuses
it. Before releasing the exclusive lease it takes the ordinary shared lease, which it holds for its
session. Other workers block on the exclusive lease and then take shared leases. Workers never drop
the head. The run controller drops it in `pytest_sessionfinish` after the workers are down, under
the same authenticated-drop rule. An interrupted run leaves a lease-free name in the swept pattern,
which the next run's sweep reclaims; each worker's sweep skips its own run's names.

**Responsibility boundary.** `PgAdmin` gains one operation, a run-scoped sealed database (ensure
under exclusive lease, seal, lease shared, never drop from a worker), used by the head fixture and
available to seeds later. The package conftest supplies the run identity and the controller-side
drop. Consumers are unchanged: they read `.name` and `.policy`.

**Change set.** `scripts/native_test_support.py` (run-scoped operation; sweep exclusion of current
run names), `tests/conftest.py` (head fixture, controller hooks), the sweep and head controls in
`tests/test_db_fixtures.py` and `tests/semantic/test_native_fixtures.py`. Remove the per-process
head path. Worker sizing for narrowed selections is a separate rule change (RC02).

**Strengths that constrain it.** The head stays sealed and client-free; every clone still replays
and compares policy; drops stay authenticated and unforced; the extension and namespace checks at
build stay; unavailable replay authority still refuses setup (ADR-0032 Decision).

**A legitimate case it could get wrong.** A worker whose first native test arrives after the worker
that built the head has exited: today it would build its own; under the target it finds the head
leased by any live user, or, if every user has exited, its sweep must not drop the run's own head
(hence the exclusion) and its ensure step reuses it. Two concurrent runs (a focused run during a
full run) have different controller identities and never share. A builder crash leaves an unsealed
database that the next exclusive holder recognises and rebuilds. A run with `-n 0` acts as both
controller and worker. A developer editing a migration mid-run now sees one consistent chain for
the whole run, where today later workers could deploy a different chain from earlier ones.

**Closure evidence.** Source shows no per-process head creation; the item-bound native context of a
parallel run's receipt names one head database across workers; the sweep control shows an
interrupted run's head reclaimed and a live run's head kept.

**Prerequisites.** RC01 (ADR-0032). DTA-030 and F01 should land first or together, so one sweep
authority recognises exactly the names the lifecycle creates.

**Related observation — maintenance connection lifecycle.** The audit's note stands: one clone
acquisition opens seven maintenance connections and one more to drop
(`PgAdmin.connect()` builds and disposes a `NullPool` engine per call,
`scripts/native_test_support.py:166–179`; replay reads policy twice through nested connections,
`:321,367`). Only the lease and role-self replay are inherently separate. Collapsing the rest onto
one maintenance session per acquisition is Part B (supporting document, D4); it does not change
what is replayed or compared.

#### DTA-025 — Rollback-only refusal families rebuild an identical committed scenario per case

**Diagnosis: retain, with the footprint refined.** I read the eight families. Six are rollback-only
on an identical scenario:

| Family | Cases | Scenario | Case writes |
|---|---|---|---|
| `tests/semantic/test_private_records.py:78–176` | 12 | default `private_source` | Positive control and refusal in savepoints; the outer `case.writer.begin()` commits an empty transaction at normal exit (`:134–176`) |
| `tests/semantic/test_runtime_bindings_native.py:100–148` | 8 | `prepare_operation_scenario` defaults | Refusal in a transaction ended by the exception (`:138–146`) |
| `tests/semantic/test_local_semantic_admission_native.py:505–660` | 10 | `private_source` + `judged_source` with fixed parameters | One SERIALIZABLE transaction, explicitly rolled back (`:645`) |
| `tests/semantic/test_local_admission_native.py:73–` | 7 | `private_source`, then `local_cut(case)` committed in each test (`:26–30,78`) | Rolled-back SERIALIZABLE transaction; `local_cut` is identical per case and belongs in the scenario build |
| `tests/semantic/test_contextual_enrichment_native.py:83–157` | 13 | `private_source` (contextual method), then `curated_case` committed in each test (`:87`) | Refusal in a savepoint; `curated_case` is identical per case and belongs in the scenario build |
| `tests/semantic/test_arrow_publication.py:445–495` | 6 | `inference_fixture` (release and one base batch) | Transaction ended by the exception; asserts one batch remains (`:495`) |

`tests/semantic/test_witnessed_applicability_native.py:172–` is **not** rollback-only as written:
each case commits a new run, task and claim in an outer transaction that exits normally
(`:174–197`). It becomes a member only if those per-case rows move inside the rolled-back
transaction, which requires that every step it calls uses the case's connection.
`tests/semantic/test_structural_native_replay.py:147–217` is **excluded**: its module-level
`private_source_options` feeds each case's own text into the committed source view (`:57–70`), so
the scenarios genuinely differ. The pure SQL-function checks are confirmed:
`tests/semantic/test_local_semantic_admission.py:103–147` calls one STABLE function per case with
JSON arguments and a per-case positive control, and `tests/semantic/test_contextual_workflow_native.py:29–135`
makes literal-argument calls; neither writes.

The lease premise is narrower than the audit states. `ops.complete_task` refuses on status,
attempt, holder and sealed run, not on lease expiry (`src/corpus_structure/semantic/sql/native_task_completion.sql:15–16`;
the lease is only cleared at `:97`). Families that complete through that path, as the private-records
family does through `bypass` (`tests/semantic/native_record_fixtures.py:746–777`), do not need a
live lease. Families whose refused operation reaches a lease-checking guard (PDF staging and
publication paths, per the lifecycle map) do; for them the case must renew the lease inside its
own transaction or stay per-case.

**Target behaviour.** Each member family builds its scenario once, on its own clone of the head (or
of a seed, F03), on one worker. Its cases run sequentially there, each in a transaction that always
rolls back, with savepoints for the positive control. Every case states reach, reason and effect
(§4.2). The shared scenario is handed out as a frozen value with engines bound to the family clone;
a case that needs its own object takes a copy. Identical per-case setup (`local_cut`,
`curated_case`) moves into the family build. Pure SQL-function checks move to L4r: a `READ ONLY`,
rolled-back transaction on the per-worker `db` session clone, which no consumer commits to. Today
one `db_engine` consumer commits DDL to that clone
(`tests/db/test_lifetime_native.py:162–167`); it moves to a fresh clone so the rung's base state
equals the sealed head by construction.

**Responsibility boundary.** The lifecycle owner offers a family-scoped acquisition built from the
same `database()` operation; scenario builders already take engines (`build_record_source(admin,
writer, …)`, `tests/semantic/native_record_fixtures.py:292`) and need no scope of their own;
build-time patching uses `pytest.MonkeyPatch.context()` and `tmp_path_factory`. Root `conftest.py`
assigns `xdist_group` by fixture closure, exactly as it does for math preparation
(`conftest.py:21–37`), so a family is one work unit.

**Strengths that constrain it.** The positive control inside each refusal test, the per-case reason
table of the forged-judged family, atomicity assertions after refusal, SERIALIZABLE isolation where
the product uses it, and the `unit` case's eight publish/refuse replays under a transaction-local
`plan_cache_mode` (`tests/semantic/test_local_semantic_admission_native.py:546,633–643`), which stays
inside its own transaction.

**A legitimate case it could get wrong.** A refused operation that checks the task lease, run on a
family scenario older than five minutes, would refuse for the lease rather than the mutation; with
class-only assertions it would still pass. With the §4.2 contract it fails loudly twice: the
positive control is refused, and the reason differs. That is why DTA-001's contract is a
prerequisite here. A second case: a production path inside a case that opens its own connection
and commits would leak into later cases; the always-rollback outer transaction does not stop it,
but the next case's positive control and absence checks expose it, and running the case alone
reproduces the clean result. A third: assertions on absolute generated identifiers become
order-dependent because sequences do not roll back (PostgreSQL §9.17); the private-records family
uses an offset from a stored id (`tests/semantic/test_private_records.py:94`), which is safe, but each
member must be checked for literal ids.

**Membership criterion** for the further parametrized families the lifecycle map lists (61 tests,
at least 244 cases from literal lists): identical committed scenario across cases; every case write
inside a transaction that rolls back; no reliance on a live lease unless renewed inside the case;
no session-level effects (advisory locks, role or database settings, function redefinition)
outside the transaction; no assertion on absolute generated ids. Classifying them is planning work.

**Closure evidence.** Each migrated family's receipt shows one clone per family; every case asserts
positive control, exact reason and absence; no case body contains a committing transaction; pure
checks run under READ ONLY transactions on the `db` rung and the rung's clone receives no commits.

**Prerequisites.** DTA-001 contract for each migrated family (safety); DTA-009 recipe values (the
family's key and group); RC01 (ADR-0032 option 3 is rejected in terms that cover these cases).

#### F03 — Committing consumers rebuild identical committed scenarios through producers

**Finding.** The audit excluded tests that complete, seal, consolidate or commit, because they need
fresh state. They do need fresh *state*; they do not need the state rebuilt by producers. A clone of
a sealed scenario seed is fresh committed state with the same content. Today each consumer of a
default recipe reruns the whole build: `private_source` alone persists a release, creates a run,
registers a document, stores a PDF original, publishes the native record product through several
transactions and Arrow batches, stores two views and creates and claims a task
(`tests/semantic/native_record_fixtures.py:292–646`), and the lifecycle map counts 85 test functions
in 28 files requesting it. `build_domain_case` is called with default options at eleven sites in
`tests/semantic/test_domain_operations.py` and `test_audit_closure_native.py` (by the ownership map's
count, spot-checked at `test_domain_operations.py:22,138,204` and `test_audit_closure_native.py:83`),
inside test bodies, before each test consolidates. The serving seed proves the pattern works here.
FP-07, DP-10, H12, H19; A4. Consequence: the dominant per-test preparation is repeated identical
work that grows with consumers and with builder depth, and it inflates every focused native run.

**Target behaviour.** A per-worker scenario seed per recipe value (L2), built lazily on first use
by the real builder, sealed (`ALLOW_CONNECTIONS false`), validated once (policy equals the head's,
client-free), with its files made read-only. Each consumer receives a fresh clone through
`database()` with policy replay. The seed holds only time-independent committed state: claims,
leases and attempts are taken per test after cloning, so lease freshness and attempt numbering are
the same as today. `tests/semantic/serving_scenarios.py` migrates to the same operation, so there is
one seed lifecycle, and its per-clone revalidation is reduced to what the seal does not already
guarantee (supporting document, D6).

**Change set.** Lifecycle owner (seed operation keyed by recipe value), scenario builders split at
the claim boundary (shared with DTA-018's staging), consumer fixtures for the chosen recipes. Choose
recipes by: one recipe value used by many consumers; build much costlier than a clone; build
deterministic and time-independent before the claim boundary; consumers' claims do not include the
build itself. Candidates by structure: default `private_source`, default `build_domain_case`,
`build_resubmission_case(composed=True)` and its default, `exclusion_result`, `pdf13_db`.

**Strengths that constrain it.** Fresh committed clones per test and real logins (ADR-0032); real
producers build the seed; builder-focused tests (native record publication, PDF build) keep
building because the build is their claim.

**A legitimate case it could get wrong.** A consumer asserting a time relation between scenario
stamps and its own clock would see the seed's earlier stamps; each recipe's consumers must be
checked for this. A consumer writing into the scenario's files would now fail on read-only files
rather than corrupt later consumers, which is the intended loud failure. A builder that monkeypatches
production during the build (`sibling_originals`,
`tests/semantic/native_record_fixtures.py:386–397`) must keep the patch scoped to the build and the
patched input in the recipe value. The source file name passed to `build_domain_case` (`source.html`
versus `source.pdf`) may matter and belongs in the recipe if it does. DTA-007's open question applies:
a seed must not be built under a monkeypatched production constant that the release cache key does
not include.

**Closure evidence.** For each chosen recipe the builder runs once per worker and every consumer
obtains a clone; the serving seed uses the common operation; no consumer takes a claim from the
seed.

**Prerequisites.** DTA-009 recipe values; DTA-018 staged builders (the claim boundary); DTA-024 is
independent but multiplies the benefit. A per-run seed shared across workers is not selected now: it
needs serialisable seed descriptors and cross-process files; revisit if per-worker seed builds still
dominate after this lands (supporting document, D7).

#### F02 — Module- and session-scoped preparation is rebuilt on every worker that runs a consumer

**Finding.** Under `--dist=loadgroup` a test without a group mark is its own work unit
(`xdist/scheduler/loadgroup.py`), so the tests of a module are spread across workers and a
module- or session-scoped fixture is built on every worker that receives one consumer, and rebuilt
on one worker when the module's tests interleave with others there (pytest's `SetupState`). Example:
`tests/orchestrate/test_policy.py:36–49` prepares the full statistics pack at module scope for ten
test functions; the historical receipt shows that module's time as setup only. The math chain
already shows the remedy: a fixture-closure `xdist_group` in root `conftest.py:21–37`. FP-07, DP-10,
H12, H21; A4. Consequence: total preparation scales with the number of workers that happen to run a
consumer, not with the number of distinct preparations.

**Target behaviour.** The root `conftest.py` hook assigns a group, by fixture closure, to consumers of
designated module- or session-scoped preparation whose preparation clearly dominates their bodies;
each item carries at most one group (xdist forms a new combined group from two marks, which would
split sharing). The designation is a short list kept beside the math one.

**Legitimate case it could get wrong.** A module whose test bodies are expensive would be serialized
onto one worker and could lengthen the run; `tests/semantic/test_domain_operations.py` (35 tests,
call-dominated in the historical receipt) must not be grouped. The criterion is structural:
preparation shared and costly, bodies cheap.

**Closure evidence.** Receipt `affinity_groups` shows each designated preparation on one worker;
source shows the designation list and one group per item.

**Prerequisites.** None; it composes with DTA-025 family groups (one group per item).

#### DTA-018 — Focused controls construct scenario preparation they do not use

**Diagnosis: retain.** Confirmed at every site. `tests/evaluate/test_record_policy_native.py:15–47`
calls `eval.record_policy_full_correct`, which reads its arguments and one `sem.artifact` row of the
release (`src/corpus_structure/semantic/sql/record_policy.sql:103–131`), after a full `private_source`
build. `tests/semantic/test_cli_failures.py:228–239` builds a composed resubmission case and keeps
only `prepared`. Provider and asset skips run after fixtures have built clones and scenarios
(`tests/semantic/test_characterization_native.py:1727–1729` and `:2112–2114`;
`tests/semantic/test_native_documents.py:93,97`). `tests/ingest/test_pdf_recognition.py:381–417`
replaces `_recognize_pages` but obtains its owner through `owner()`, which skips when the isolated
parser runtime is absent (`:166–172`).

**Target behaviour.** Builders compose stages (release persisted; views published; run and task
created; completed or sealed), each returning a frozen value, and the full builder is their
composition (the math conftest's staged session fixtures are the precedent). Focused consumers
request the earliest stage their claim reads. The record-policy controls take a persisted release
and authored candidates; the CLI diagnostic takes a persisted composed release. Provider and asset
prerequisites move to markers decided before setup (§6.4). The recognition scheduling control
constructs its owner without the isolated runtime, since the recognition call is replaced; the
premise that `RecognitionWorker` construction does not validate or start the runtime must be
confirmed at implementation.

**A legitimate case it could get wrong.** If `record_policy_full_correct` later consults run or view
state, the focused test would fail rather than pass silently, and would then need the later stage.

**Closure evidence.** The named consumers request only the stage they read; no `pytest.skip` remains
after scenario fixtures for provider or asset prerequisites; the remaining 32 `build_resubmission_case`
and 44 `prepare_operation_scenario` sites are classified against the same criterion during planning.

**Prerequisites.** Shares the staged builders with DTA-009 and F03, and the prerequisite marker with
DTA-028.

### 6.2 C2 — Refusal and absence evidence

#### DTA-001 — Some refusal assertions do not distinguish the intended outcome

**Diagnosis: retain, refined.** Confirmed at the sites read. `tests/semantic/test_publication.py:223–231`
accepts any `DBAPIError` for a writer insert into `data.entity` and a reader call to
`data.begin_stage()`. The refinement: the privilege fence (`REVOKE ALL … FROM corpus_sem_writer`,
`semantic_alembic/versions/semantic_0003_publication.sql:8`, with only `SELECT` granted later) raises
`42501`, while the missing realization would raise a foreign-key `23503`; pinning SQLSTATE alone makes
the control fail if the fence is removed, so no new input is needed (the ownership map traced the
grants; I confirmed the test site). `tests/evaluate/test_operation_fitting_native.py:279–307` loops
twelve labelled mutations under a bare `pytest.raises(DBAPIError)` and discards the label; the
ownership map traces them to six distinct guard messages. `tests/methods/test_m1_cli.py:9–35` accepts
exit code 2 and any of four words, one of which the parser echoes for unrelated usage errors.
`tests/semantic/test_runtime_bindings_native.py:136–148` pins only `23514`.

**Target behaviour.** Every negative control states reach, reason and effect (§4.2). Privilege
controls pin `42501` per statement (`tests/semantic/test_native_closure.py:66–75` included). Mutation
families bind each label to its expected `(sqlstate, message | constraint[, context])`, following the
forged-judged table. The seal control in `tests/semantic/test_pdf_publication.py:363–369` and the
`selected` case that expects the generic `P0002` also pin the diagnostic context naming the guarding
function, as `test_local_semantic_admission_native.py:622–624` already does. `test_record_references_native.py:99`
uses a pass whose only defect is the one under test, or pins the guard's message. The review-bundle
family pins each corruption's `ValueError` message. CLI refusals pin the error code and message, as
`tests/test_cli.py:374–381` does. A narrow support helper unwraps `InvariantViolation.__cause__` and
compares the diagnostic tuple with a full report on mismatch; expected values stay at the call site,
and the helper gets its own accept and reject controls (companion §3).

**Strengths that constrain it.** Existing SQLSTATE and message pins, honest notes about which layer
owns a refusal, and positive controls in savepoints.

**A legitimate case it could get wrong.** Two mutations may deliberately reach one guard (by the map's
reading, `compiler_mismatch` and `model` in the runtime-binding family both reach "runtime binding
belongs to another execution model"). The reason table may repeat a message; the minimal pair proves
reach, and distinct guards are not required where the product shares one. Message text is product
wording; where it churns, prefer constraint names or SQLSTATE with context.

**Closure evidence.** Each named site asserts its specific reason; removing one guard makes exactly its
case fail, by reasoning over the guard conditions (a one-off mutation during implementation is
optional).

#### DTA-027 — The redact-before-clip control passes under either order

**Diagnosis: retain.** `tests/test_cli.py:93–106` builds 12,068 characters with all secrets either
removed by any clip or wholly inside the kept window; production redacts then keeps the last 12,000
characters of standard output (`src/corpus_structure/cli/operations.py:161,186`). Clip-then-redact
passes.

**Target behaviour.** Place a credential so that clipping first would cut it mid-token and leave a
fragment that redaction no longer recognises, then assert the fragment's absence and a presence
premise: the mask token at the expected place and the retained window's exact tail. Add the same
control for the 6,000-character diagnostic clip (`operations.py:187`). The settings tests at
`tests/test_settings.py:151–154,197–202` and `tests/test_semantic_runtime_settings.py:179` assert the
masked rendering of their own field before asserting absence, as `tests/test_settings.py:44–53` does.

**Closure evidence.** By construction a clip-first implementation leaves the fragment and fails.

#### DTA-006 — Some assertions establish presence or count where the claim is preservation

**Diagnosis: retain.** Confirmed at `tests/semantic/test_identity_exclusions.py:127–142`
(counts and one distinct `establishment`), `tests/semantic/test_exclusion_comparison.py:107–119`
(a run compared with itself) and `tests/semantic/test_execution_projection.py:127–133` (truthiness).

**Target behaviour.** Assert which entities were grounded; compare two runs with a known difference
and assert the exact change list (with F03, the changed run is a clone of the exclusion seed plus one
change, not a second full build); give the reference evaluation one submission with an unmatched extra
and a missing claim inside its existing prepared scenario; assert exact diagnostic fields and the
exact retained edges.

**Closure evidence.** Each named test fails for a plausible wrong implementation it now accepts.

#### DTA-016 residue

Agreed as holding. In `tests/semantic/test_runtime_entrypoints.py:608` the three non-complete modes
should assert the exact task state each mode leaves, rather than "not `done`".

### 6.3 C3 — Scenario and support ownership

#### DTA-009 — Scenario ownership sits in test modules and fixture-name bindings

**Diagnosis: retain, refined.** The three forms hold. The audit's open question is settled from
pytest 9.1.1's source. In `importlib` mode `import_path` first resolves a package root through
`__init__.py` files; only `tests/semantic/` and `tests/methods/` are packages. For a file in a
non-package directory it falls back to `module_name_from_path` relative to the root
(`.venv/…/_pytest/pathlib.py:548–575`), so `tests/ingest/test_annotations.py` is collected as
`python.corpus-structure.tests.ingest.test_annotations`, while `from ingest.test_annotations import …`
through the configured `pythonpath` loads the same file again as `ingest.test_annotations`. There are
two module objects, each executing the file, with separate classes and caches. Importers exist:
`tests/methods/test_native_evidence.py:9`, `test_math_scope_primary.py:7`,
`test_construction_named.py:8`, `tests/semantic/test_nce02_native_scope.py:103`,
`tests/evaluate/test_characterization_assessment_native.py:10`, `tests/semantic/test_review_cli_native.py:13`
and others (grep, 2026-11-12). For `semantic.*` and `methods.*` absolute and relative imports resolve
to one key, so the audit's example `semantic.native_record_fixtures` versus `.native_record_fixtures`
is not a duplicate. The ownership map was right on this point; the library map's search for
`from test_…` missed directory-qualified imports.

**Target behaviour.** A scenario is selected by a frozen recipe value visible where the case is
declared, passed by indirect parametrization or a factory fixture; `private_source_options`
overrides and the `callspec` read go. Shared builders, fixtures and doubles live in support modules or
directory conftests; test modules import from those only. `synthetic_source_projection` moves to a
named support module that states it disables `review_bundle._verify_source_projections`. Large
builders become staged compositions (DTA-018). With no test module imported by absolute name, the
duplicate module objects disappear.

**Change set.** `tests/semantic/native_record_fixtures.py` and the eleven overriding modules; the 75
test-module owners imported elsewhere (ownership map, 255 import statements), moved in planning by
consumer clusters; `tests/semantic/test_review_bundle.py` double; re-export chains.

**A legitimate case it could get wrong.** The structural replay family selects text per case; its
recipe becomes a per-case parameter, which expresses the same thing directly. The interpretations and
record-policy-authority overrides use two transforms or a method spec; the recipe value carries them.

**Closure evidence.** No `private_source_options` override or `callspec` read; no test-to-test import;
the verification-disabling double has a named owner.

**Prerequisites.** None. It is a prerequisite of DTA-025 and F03.

#### DTA-029 — The primary-layer assembly scaffold is hand-copied across method tests

**Diagnosis: retain, footprint refined.** Seven files copy the spaCy native-layer sequence: the shared
`tests/methods/primary_reading_fixture.py:84–104`, `navigation_fixture.py:56–75`, root-of-package
`tests/native_math_primary.py:107–118`, `test_math_scope_primary.py:90`, `test_construction_named.py:97`,
`test_m1_producer.py:198` and `test_primary_reading_consumers.py:142`. The digest handling splits three
ways to three: the shared fixture, navigation and `native_math_primary` overwrite
`configuration_digest` with the pipeline digest; math-scope, construction-named and M1-producer do not.
`test_contextual_characterization.py:46–57` only appends provider metadata rows and
`test_definition_declaration_primary.py` uses the HanLP path; neither is a copy of this sequence.

**Target behaviour.** One owner for the native half, taking configuration text, digest policy (pipeline
or derived), products and reference numbers as explicit arguments; the claim-specific construction
halves stay local. The digest choice becomes visible at each call site.

**Closure evidence.** The copies call the owner; each site's digest choice is explicit.

#### DTA-030 — Superseded fixture machinery remains in shared test support

**Diagnosis: retain, extended.** Confirmed: `TEMPLATE_PREFIX`, `TEMPLATE_RETENTION`, `STAMP`,
`stamp()`, the stamp branch of `owned_comment` and the `cs_tpl_` sweep branch
(`scripts/native_test_support.py:46–49,244–250,547–586`) serve a scheme nothing creates;
`committing_db` (`tests/conftest.py:295–303`) has only its self-test; the shadowing
`semantic_db_engine` in `tests/semantic/test_native_attributed_evidence.py:50–69` keeps an unreachable
candidate branch and names its clone `cs_sem_m1_attributed_<hex>`. Two extensions: the audit's claim
that this is the only sweep-escaping name is wrong, because
`tests/semantic/test_serving_scenario_lifecycle.py:39` names its second clone `cs_sem_test_<hex20>`
without a process id, which the sweep pattern at `scripts/native_test_support.py:587–589` does not
match; and `tests/semantic/snapshot_restore.py` has no reference anywhere outside retained evidence
(grep over the repository excluding `.git`, `.venv`, `target`, `build`, plans and evidence, 2026-11-12).
The ownership map's claim that `tests/fixtures/support.py` has no importer is wrong: it is loaded by
path in `tests/fixtures/test_fixtures.py:30–40`.

**Target behaviour.** Remove the `cs_tpl_` scheme and its test, `committing_db` and its self-test, the
shadowing fixture with its migration imports and evidence path, and `snapshot_restore.py`; give the
lifecycle test's second clone a sweepable name. Before removing the `cs_tpl_` branch, check the
cluster once for owned `cs_tpl_*` residue and drop it through the existing authenticated drop, so no
residue is stranded.

**Closure evidence.** No source names `cs_tpl_` or `STAMP`; every database name the tests create
matches the sweep's recognition; the removed fixtures have no consumers.

**Prerequisites.** Lands with or before DTA-024 so one sweep authority covers exactly the names created.

#### F01 — The sweep's lock key for `ci_test_<pid>_<n>` differs from the lease key

**Finding.** `database()` leases the full name it creates (`scripts/native_test_support.py:452`, via
`lease(name)`), so a `committing_db` clone `ci_test_<pid>_<n>` is protected under that full name. The
sweep reduces such names to group 1 of `TEST_DB` and try-locks `ci_test_<pid>` (`:45,592–596`), a key
held only while the same worker also holds the session clone `db_engine`. A worker sweeping while
another worker holds a `committing_db` clone without `db_engine` would obtain the lock and attempt to
drop a live database; the drop either fails after its two-second retry, failing the sweeping worker's
`native_server` setup, or succeeds between statements. The sweep control
(`tests/test_db_fixtures.py:124–152`) encodes the session-key convention by leasing
`ci_test_999999998` to protect `ci_test_999999998_9`, so the test and the fixture disagree. DP-01,
DP-19; G1, G5. Exposure today is narrow, because the only consumer requests both fixtures.

**Correction.** Derive the sweep's lock key from the same function that derives the lease key; with
`committing_db` removed (DTA-030) the optional suffix in `TEST_DB` goes too, and the control protects a
live name by that name's own lease.

**Closure evidence.** One key-derivation function used by lease and sweep; the control fails if they
diverge.

### 6.4 C4 — Evidence-class identity and prerequisites

#### DTA-028 — One provider test identity passes on a controlled branch

**Diagnosis: retain.** `tests/semantic/test_pm2_result_native.py:286–` reads
`CORPUS_PM2_NATIVE_TEST_ASSETS` in the body (`:327`); with it set the test opens real PM2 workers and
runs the reassignment-after-lease-loss control, otherwise the same node completes through hand-written
replies with a `controlled-test` checkpoint (`:366–`). Receipt status derives only from phase outcomes
(`scripts/test_receipts.py:466–490`), so both branches are `passed`. G7, DP-21/22.

**Target behaviour.** Two identities: the provider test, gated by a prerequisite marker decided before
setup, and the controlled test named as controlled. The marker reaches the receipt as
`qualification_prerequisite` and reason, exactly as the `corpus` marker does
(`tests/conftest.py:122–138`). The same mechanism replaces the body-level skips of DTA-018 and the
existing `skipif` at `tests/semantic/test_pm2_parser_stage_native.py:42–44`. A provider-gated node
without assets is then `blocked`, as the parser-stage test already is, unless the qualification policy
owner declares it optional, which yields `inapplicable`.

**A legitimate case it could get wrong.** The ordinary lane on a host without assets will report a
blocked node where it now reports a pass. That is the truthful outcome under the reporting rule that
a mocked provider is never passed; whether such nodes keep the required union open is a policy choice
for its owner, not for the test body.

**Closure evidence.** No test body reads an asset variable to choose its evidence class; provider and
controlled evidence have distinct node ids; receipts record the prerequisite for provider nodes.

### 6.5 C5 — Timing-coupled lifecycle controls

#### DTA-026 — CPU teardown controls wait out production grace and reach into executor internals

**Diagnosis: retain the timing part; refine the private-state part.** The grace constants are module
globals read at call time in parent-side code (`src/corpus_structure/semantic/cpu_execution.py:456–457`,
used at `:545,819–820,879`), and the tests assert literal windows such as `4.5 <= elapsed < 12`
(`tests/semantic/test_cpu_lifecycle.py:78`) and `9.5 <= … < 12` (`:376`). The refinement: production's
`_PoolOwnership` itself depends on CPython 3.14 executor internals and documents it
(`cpu_execution.py:461–467,508–513`), so a toolchain move would break the adapter, not only the tests.
What is test-specific is *writing* private attributes to inject an initializer (`_initializer`,
`_initargs` at `:92–94,144–145,208–209,326–327`). Test 1 already uses the module-attribute factory seam
for the same purpose (`:62–68`).

**Target behaviour.** Windows derive from the constants read at test time; behavioural controls
shorten the constants with `monkeypatch` (premise: only parent-side code reads them, which holds at
the baseline); one cheap assertion pins the selected five-second values, so the policy is protected
without waiting it out. Initializer injection uses the factory seam everywhere. Reads of manager state
(`_broken`, `_shutdown_lock`) remain where an interleaving needs them, explicitly tied to the
adapter's documented dependency. The suspected weakness in
`tests/semantic/test_cpu_execution.py:110–139` is closed by gating the worker with a manager event, as
its siblings do.

**A legitimate case it could get wrong.** A grace shorter than child readiness could make "kill after
grace" race the child; the tests already wait for a `started` event before closing, and the upper
bound keeps an absolute slack for kill and join.

**Closure evidence.** No literal tied to five seconds; one value assertion; no writes to private
executor attributes; the in-flight cancellation control gates its worker.

### 6.6 Confirmations without remedy

- **DTA-002** holds: fault controls are opt-in, serial and skip to `blocked`; lines 700–1084 of root
  `tests/scripts/test_native_auth.py` were not reread by the audit or by me.
- **DTA-003** holds; acquisition-complete provenance matches the marker's meaning.
- **DTA-004, DTA-005, DTA-008, DTA-010, DTA-011, DTA-012, DTA-013, DTA-014, DTA-015, DTA-019, DTA-020**
  hold as the audit states; I found nothing contrary at the sites I opened, and did not reread the
  others.
- **DTA-007** holds; its open question (a cache entry prepared under a monkeypatched constant
  outliving its test) becomes a premise for F03 seeds.
- **DTA-017** holds: the autouse fence is at `tests/conftest.py:189–200`.
- **DTA-021** and **DTA-022** are corrected as the audit states.
- **DTA-023** is corrected; I agree to keep the tool-path residue under the audit's trigger.

---

## 7. Library and system mechanisms

Each mechanism below carries a recommendation; references are to the pinned versions (pytest 9.1.1,
pytest-xdist 3.8.0, SQLAlchemy 2.1.6, PostgreSQL 18.6 on the cluster).

| Capability and owner | Mechanism | Conditions and limits | Status |
|---|---|---|---|
| Run-wide head (DTA-024), lifecycle owner | PostgreSQL session-level `pg_advisory_lock` (exclusive build) and `pg_advisory_lock_shared` (use), both released when the backend's session ends (PostgreSQL 18 §13.3.5); keys from the existing `lock_sql` (`scripts/native_test_support.py:86–88`) | A session already holding a lock can take it again; a crash releases it; session locks ignore transaction rollback | Selected |
| Run identity to workers | xdist `pytest_configure_node(node)` adding to `node.workerinput`, received as `config.workerinput` (`xdist/newhooks.py:74`, `workermanage.py:308–349`); `testrun_uid` also available | Hook runs on the controller per node before start; the controller never collects, so it cannot see the selection | Selected |
| Run-end cleanup | Controller-side `pytest_sessionfinish` after `DSession` tears down nodes (`xdist/dsession.py:94–100`) | A hard kill of the controller leaves the head; the next sweep reclaims it | Selected |
| Concurrent clones of one template | `CREATE DATABASE … TEMPLATE` takes `ShareLock` on the source, so parallel workers can clone one template; it fails if any other connection to the source exists (PostgreSQL 18 `sql-createdatabase`) | The head and seeds must stay client-free; sealing with `ALLOW_CONNECTIONS false` enforces it | Selected (existing) |
| Clone strategy | Default `STRATEGY WAL_LOG` copies block by block through WAL and forces no checkpoint; `FILE_COPY` forces two immediate checkpoints; `file_copy_method = clone` needs a reflink filesystem, and the data directory is on ext4 (library map, `findmnt`) | Keep WAL_LOG | Selected (existing) |
| Drop cost | `dropdb()` requests an immediate, waited, cluster-wide checkpoint after forgetting the database's sync requests (PostgreSQL `REL_18_STABLE` `dbcommands.c`, read by the library map; consistent with my knowledge of earlier releases; not checked at the 18.6 tag) | Every clone drop flushes dirty buffers of every database on the cluster, including the development database; fewer clones is the only safe lever | Premise for C1 priority |
| What clones carry | Objects and in-database grants are copied; `datacl`, database and role-in-database settings are not (PostgreSQL 18 docs; ADR-0032 Context) | Policy replay remains required per clone and per seed clone | Selected (existing) |
| Family rollback (DTA-025) | SQLAlchemy Core `engine.connect()` + `conn.begin()` + `rollback()` (`rollback_connection`, `scripts/native_test_support.py:53–61`); `begin_nested()` savepoints; isolation set before `begin()` | Savepoint rollback releases locks taken after it; sequences are not rolled back; session-level advisory locks ignore rollback; `clock_timestamp()` advances | Selected |
| Read-only rung (L4r) | `SET TRANSACTION READ ONLY` (or `execution_options(postgresql_readonly=True)`) on the rolled-back connection | Writes to non-temporary tables and all DDL, including temporary-table creation, fail with SQLSTATE `25006` (PostgreSQL 18 `SET TRANSACTION`), so a hidden write is a distinct, loud failure when reasons are pinned | Selected |
| Family affinity and expensive preparation (DTA-025, F02) | `xdist_group` marks assigned in root `conftest.py` `pytest_collection_modifyitems` by fixture closure, under `--dist=loadgroup` (existing math pattern) | A group is one unit on one worker, sent largest first; two marks on one item form a new combined group | Selected |
| Higher-scoped scenario fixtures | Module-scoped fixtures with `pytest.MonkeyPatch.context()` and `tmp_path_factory` | Exceptions raised by higher-scoped fixtures are cached for the scope | Selected |
| Prerequisites before setup (DTA-028, DTA-018) | Markers whose skip is added in `pytest_collection_modifyitems` (existing `corpus` route) or `skipif` marks, evaluated in `pytest_runtest_setup` with `tryfirst` before fixture setup (`_pytest/skipping.py`) | String `skipif` conditions are evaluated at setup, booleans at import | Selected |
| Selection-sized workers (RC02) | Managed route computes `--workers` from explicit node-id selectors; alternative is a root-conftest `pytest_xdist_auto_num_workers` hook | Worker count is fixed before collection; path selectors give no count without collecting | Candidate |
| Cross-run head reuse | A head keyed by a conservative digest of `semantic_alembic/`, the `corpus_structure` source tree, installed Alembic/SQLAlchemy/psycopg versions, server version and `cs_template` identity; migrations import product code (`corpus_structure.semantic.native_objects` in 168 revision files), so the chain directory alone is an incomplete key | Not selected; ADR-0032 rejects a persistent key; revisit if focused native reruns after test-only edits remain dominated by head deployment | Unresolved alternative |
| `pytest-postgresql` janitor | Template-and-clone database lifecycle | Does not replay database ACLs or role settings, has no authenticated-drop or lease model; would duplicate the existing owner | Not adopted |

---

## 8. Alternatives for preparation lifetimes

| Alternative | Change propagation and local reasoning | Semantic authority and composition | Test and substitution boundary | Total machinery and operational risk | Decision |
|---|---|---|---|---|---|
| Current: per-process head, per-test clone and build | Consumers know nothing; builders rerun everywhere | One lifecycle owner; serving seed as a side path | Fresh committed isolation for every test, including tests that need only rollback | Head work × workers; scenario work × cases × consumers; one forced checkpoint per drop | Revise |
| Proposed: L1–L4 (§4.1) | Consumers state a recipe and an isolation need | One owner, one seed lifecycle, one refusal contract | Committed isolation where claimed; rollback or read-only where sufficient, with per-case proof | Adds a run-scoped operation and controller cleanup; removes `cs_tpl_` scheme, a shadow fixture and dead fixtures | Selected |
| Library-owned: `pytest-postgresql` with its template janitor | Moves lifecycle into a plugin | Loses policy replay, leases and authenticated drops; second owner | Same isolation | Integration and policy gaps | Rejected |
| Simplest viable: per-run head plus group marks only | Small change | Unchanged | Unchanged | Removes head repetition and per-worker module rebuilds, leaves per-case and per-consumer rebuilds | Insufficient alone; it is the first step of the proposed design |
| Cross-run keyed head | Adds a key and retention | Sound only with a superset key | Unchanged | Removes head deployment from focused reruns after test-only edits; rebuilds on any product edit | Deferred alternative (§7) |
| Clone per case for rollback families (seed per family) | Small change | Unchanged | Committed isolation per case | Still one clone, policy replay and forced checkpoint per case | Use only for committing families (F03), not for rollback-only ones |

---

## 9. Gates and foundations

| Gate | Verdict | Evidence or scope reason | Required action |
|---|---|---|---|
| G1 Authority | Fail | The primary-layer assembly contract is restated in seven copies (DTA-029); the sweep's protection key and the lease key are separate definitions (F01) | §6.3 |
| G2 Semantic fidelity | Pass, narrowly | Receipts keep passed, failed, blocked, inapplicable and incomplete distinct; the provider/controlled loss is judged under G7 | — |
| G3 Validity | Fail | Refusal controls that cannot fail for the regression they name (DTA-001); absence controls without presence premise (DTA-027) | §6.2 |
| G4 Hidden behaviour | Pass | The verification-disabling double is opted into by name; the ambient asset switch is judged under G7 | Ownership move under DTA-009 |
| G5 Consistency and recovery | Fail, narrowly | Residue that escapes the sweep (DTA-030, two names); a sweep that can target a live clone (F01) | §6.3 |
| G6 Transformation and reuse | Pass, with premises | The release cache is content-keyed; the proposed head, seed and family reuse each state validity premises (§4.1, §6.1); DTA-007's open question stays a premise | Keep premises with each recipe |
| G7 Truthful capability claims | Fail | A controlled branch passes under a provider test identity (DTA-028) | §6.4 |
| G8 Library leverage | Pass | Pytest, xdist and PostgreSQL mechanisms are used; the lifecycle's bespoke parts (replay, authenticated drop) have stated reasons (ADR-0032) | — |
| CI-G1 Fidelity (profile) | Pass for what was read | Unknown, absent and empty distinctions are strengths in served and gap tests | — |
| CI-G2 Evidence closure (profile) | Unresolved | Inherited from the audit: which boundary covers the size-preflight query and structural-tool registration was not settled; not examined here | Out of this review's focus |
| CI-G3 Evaluation integrity (profile) | Pass | Reference answers are hand-authored and submitted through the real tool (DTA-004) | — |

Foundations, for the test system as software. **FP-01** violated: scenario policy and shared builders
live in import bindings and test modules (DTA-009). **FP-02** violated: evidence class is not part of
the test contract (DTA-028); interpreter-private writes (DTA-026). **FP-03** violated: parallel copies
and superseded machinery (DTA-029, DTA-030). **FP-04** satisfied for oracle independence, which is the
suite's strength, and violated for scenario authority (DTA-009). **FP-05** violated: refusal reach and
reason, prerequisites and shared-state premises are implicit (DTA-001, DTA-018, the `db` rung's base
state). **FP-06** violated: focused controls bootstrap unrelated preparation and ambient variables
decide evidence class (DTA-018, DTA-028). **FP-07** violated (C1 and DTA-026). Supporting rules most
used: DP-01, DP-10, DP-16, DP-19, DP-20, DP-22, DP-23.

---

## 10. Change and failure scenarios

| Scenario | Today | Target | Evidence |
|---|---|---|---|
| Add one refusal mutation to a native family (domain extension) | One more full scenario build, clone, policy replay, drop and forced checkpoint; the new case may pass on a neighbouring guard | One more rolled-back case on the family scenario with its own reason and positive control | §6.1, §6.2 |
| Add a scenario variant (new bundle transform) | Override `private_source_options` in a module; consumers depend on import resolution | A new recipe value at the call site; shares and seeds key on it | §6.3 |
| Add a migration | Deployed by every participating worker in every run | Deployed once per run | §6.1 |
| Focused run of three native tests | Up to three head deployments, three scenario builds, 16 interpreters collecting | One head deployment, scenario clones from per-worker seeds, workers sized to node-id selections (RC02) | §6.1, RC02 |
| Provider assets absent on the qualifying host | The provider node passes through a controlled branch | The provider node is blocked or inapplicable by policy; the controlled node passes | §6.4 |
| Interpreter upgrade (mechanism substitution) | Tests that write executor internals and the adapter both break | Only the adapter and its reads break, as its documented dependency says | §6.5 |
| Interrupted run | Per-process heads and clones left; one shadow-fixture name and one lifecycle-test name never reclaimed | Run head and all names reclaimed by the next sweep | §6.1, §6.3 |
| Growth to 32 workers | Head deployments and per-worker module rebuilds double | Head once; grouped preparation once per group | §6.1 |

---

## 11. Relationships, prerequisite order and fit

Shared causes and prerequisites, by the capability each needs:

1. **Recipe values (DTA-009)** come first among the scenario corrections: shared family scenarios
   (DTA-025) and seeds (F03) need an explicit key, and group assignment needs a stable fixture closure.
2. **The refusal contract (DTA-001)** must accompany any family moved onto a shared scenario: the
   positive control and exact reason are what make sharing safe.
3. **Sweep authority (DTA-030, F01)** precedes or accompanies the run-scoped head (DTA-024), so that one
   recognition rule covers every name the lifecycle creates and no second retention scheme exists.
4. **Staged builders (DTA-018)** are the same change as the big-builder part of DTA-009 and define the
   seed's claim boundary (F03).
5. **The prerequisite marker** serves DTA-028 and DTA-018's body skips together.
6. DTA-024, F02, DTA-026, DTA-027, DTA-006, DTA-029 are otherwise independent.

Priority by consequence is different from that order: DTA-028 (a false pass), DTA-024, DTA-025 and F03
(the largest repeated work) and DTA-001 (vacuous refusals) lead; F02 and DTA-018 follow; DTA-030, F01,
DTA-026, DTA-027, DTA-006 and DTA-009 next; DTA-029 last. DTA-009 is lower priority but an early
prerequisite.

**Fit check.** One lifecycle owner (`PgAdmin` with its fixtures) gains a run-scoped operation, a family
acquisition and a seed operation, all built on `database()`; the serving seed migrates into the seed
operation, so there is no second seed lifecycle. The `db` rung is reused for pure checks rather than a
new rung. Group marks use the existing root-conftest mechanism, one group per item, so family groups,
preparation groups and the math group do not combine. Committed isolation is kept for every test that
commits, seals, redefines functions, races or cancels; rollback isolation is used only where every
case write rolls back and each case proves reach and reason; read-only isolation is enforced by the
database. No double replaces a real boundary, no case is merged, and no test changes lane.

---

## 12. Rule impacts

**RC01 — ADR-0032, Fresh native tests clone a session deployment with explicit database policy replay**
(`docs/adr/0032-native-test-deployment-equivalence.md`). The Decision says the head is built "once per
session" and "every consumer receives a new database"; Option 3 rejects rollback reset because it
"cannot establish separate-login commits, races or cancellation". Proposed change: the head is built
once per run and shared by the run's workers, its cleanup owned by the run controller within the same
lifecycle; consumers whose claims involve separate-login commits, races or cancellation keep a new
database, while rollback-only refusal families and pure SQL-function checks receive a rolled-back (or
read-only) transaction on a shared committed scenario, with per-case reach and reason; committing
consumers may receive their new database as a clone of a sealed scenario seed. Unchanged: no persistent
reuse key, no forced drops, policy replay and comparison per clone. Dependent findings: DTA-024,
DTA-025, F03 (and the serving-seed migration). If the rule is kept: DTA-024 stays open and A4 stays
violated for focused native runs; DTA-025 can only use a seed per family with a clone per case, which
keeps one clone, replay, drop and forced checkpoint per case; F03 stands, since seed clones already
satisfy "a new database".

**RC02 — Default worker count for narrowed selections** (`pyproject.toml:46–55` addopts `-n auto`;
`scripts/test_receipts.py:1587–1593`; the completed
[parallel execution companion](../../plans/test-audit-resolution/parallel-execution-and-harness.md),
"Retain auto as initial default; a justified explicit cap uses existing CLI/environment settings").
Proposed change: when every selector is an explicit node id, the managed route passes
`--workers min(auto, count)` (one test runs with one worker); path selectors keep `auto`. This uses the
existing CLI setting the companion names, but changes the default for narrowed selections. Dependent:
DTA-024's focused-run part. If kept: with the run-scoped head, idle workers no longer deploy anything,
so the remaining cost is 16 interpreters importing the package conftest and collecting the selected
files for a one-test run; this is accepted as a known overhead.

No other rule is changed. The reporting rule that a mocked provider is never `passed` is implemented,
not changed, by DTA-028's correction. The BEP selection of five-second grace is kept and pinned by one
assertion (DTA-026). The companion's "no custom scheduler" is respected: grouping uses marks under the
built-in `loadgroup`.

---

## 13. Verification and uncertainty

| Claim | Label and date | Basis | Gap |
|---|---|---|---|
| Per-process head and per-worker deployment | Interface-checked 2026-11-12 | `tests/conftest.py:255–260`, `scripts/native_test_support.py:613–630`, xdist `loadgroup.py`, `plugin.py` | Distribution of a small selection across workers not observed |
| DTA-025 membership and lease premise | Interface-checked 2026-11-12 | Eight families read; `native_task_completion.sql:15–16,97` | Lease checks of completion paths other than `ops.complete_task` not read per family |
| F03 recipe candidates and counts | Interface-checked 2026-11-12 (counts from the evidence maps' AST scans, spot-checked) | `native_record_fixtures.py:292–646`, default `build_domain_case` sites | Time-relation assertions and file writes of consumers not searched per recipe |
| Two module objects for non-package imports | Interface-checked 2026-11-12 | pytest 9.1.1 `_pytest/pathlib.py:548–575,624–720,847–880`; importer grep | Not observed at runtime; whether duplicated state matters for any test not established |
| Drop forces a checkpoint | Interface-checked from `REL_18_STABLE` source by the library map, not the 18.6 tag | Library map §4 | Size of its effect unmeasured; used only to rank, never as a figure |
| Historical phase split (56/33/11 %) and per-module setup | Measured, 2026-11-07, retained receipt `docs/design_review/evidence/2026-11-06_wce-completion-repair/qualification/test-receipts/ordinary-001`, source `2b11a881` (dirty), 5,070 nodes, 16 workers | Receipt summary | Older source; orientation only |
| Every remedy | Proposed | — | Not implemented |

Material premises that could change a remedy, and how to settle them during implementation: whether a
family's refused operation checks the task lease (settled by reading its guard; changes membership,
not the design); whether a recipe's consumers assert time relations or write into scenario files
(settled by reading consumers; excludes a recipe from seeding); whether `RecognitionWorker` construction
validates the runtime path; whether controller-side hooks in the package conftest load on the
controller for every selection that contains native tests (they load when the package tests directory is
an initial path; a selection under `tests/scripts/` only needs no head). None of these needs a probe
before planning. Unexamined breadth is not a finding: the audit's thin areas remain thin.

**Disagreements with the evidence maps.** The library map's "no current instance" of duplicate modules
is wrong (§6.3). The process map's statement that the math preparation chain re-parses the 11.4 MB
retained archive in every spawned child is too broad: the staged chain ships `PageContent` payloads
(`tests/math_support.py:329–360`); only the coverage worker re-parses, once per child
(`:401–404,113–118`). The ownership map's "no importer" for `tests/fixtures/support.py` is wrong (loaded
by path). The lifecycle map's sweep-escaping names and key mismatch are right and are taken up as
DTA-030's extension and F01.

---

## 14. Dispositions

No plan owns these findings yet. Each open finding has a Deferred row here until plan creation selects
it; the reopening event for all is the operator's plan creation from this review. DTA-001–023 dispositions
as they stood on 2026-11-05 remain with the
[test audit resolution coordinator](../../plans/test-audit-resolution_2026-11-05.md); the rows below cover
the current-source manifestations only.

| Finding | Disposition | Scope consequence while deferred | Reopening event |
|---|---|---|---|
| DTA-001 | Deferred | Named refusal controls can pass if their guard is removed | Plan creation from this review; earlier if a named guard changes |
| DTA-006 | Deferred | Named tests establish presence, not preservation | Plan creation from this review |
| DTA-009 | Deferred | Scenario selection depends on import binding; eight test modules load twice | Plan creation; earlier if a shared-scenario or seed change is planned (prerequisite) |
| DTA-016 residue | Deferred | Non-complete stdio modes do not pin task state | Plan creation |
| DTA-018 | Deferred | Focused controls pay for and fail on unused preparation | Plan creation |
| DTA-024 | Deferred | Head deployed per worker; focused native runs pay repeatedly | Plan creation; or ADR-0032 revisit under its own trigger |
| DTA-025 | Deferred | Rollback-only families rebuild per case | Plan creation; requires RC01 |
| DTA-026 | Deferred | CPU lifecycle controls wait out real grace; writes to private executor state | Plan creation; earlier on a CPython change |
| DTA-027 | Deferred | Redaction-order control passes under either order | Plan creation; earlier if output clipping changes |
| DTA-028 | Deferred | A passing provider node may not have run the provider | Plan creation; earlier before any qualification that counts PM2 provider evidence |
| DTA-029 | Deferred | Assembly-contract change must be mirrored in seven copies | Plan creation; earlier on a native evidence assembly change |
| DTA-030 | Deferred | Dead branches maintained; two names escape the sweep | Plan creation; earlier with any DTA-024 work |
| F01 | Deferred | Sweep could target a live `committing_db` clone | Plan creation; closed by DTA-030's removal of `committing_db` |
| F02 | Deferred | Module and session preparation repeated per worker | Plan creation |
| F03 | Deferred | Identical committed scenarios rebuilt per consumer | Plan creation; requires DTA-009 |
| RC01, RC02 | For operator confirmation in plan creation | — | Plan creation |

---

## 15. Architectural judgment and decision

| Judgment | Verdict | Scenario evidence and scope | Required action |
|---|---|---|---|
| A1 Localize change | Violated | A scenario variant or helper edit propagates through import bindings and test-module owners (DTA-009); an assembly change must be mirrored in seven copies (DTA-029); a grace-constant change fails timing literals (DTA-026) | §6.3, §6.5 |
| A2 Encode domain meaning explicitly | Violated, scoped | The test system's consequential distinctions (evidence class, refusal reason, prerequisite, scenario recipe, preparation validity) are partly implicit: DTA-028, DTA-001, DTA-018, DTA-009; receipts, prerequisite categories and native context are explicit strengths | §6.2–§6.4 |
| A3 Extend through composition | Violated | A new variant needs a fixture-name override; a new provider-gated test reinvents a body switch; superseded machinery is maintained (DTA-030) | §6.3, §6.4 |
| A4 Fit execution to the supported workload | Violated | For focused native runs and the full lane, head deployment scales with workers, scenario builds with cases and consumers, module preparation with workers, and teardown with clones (each drop forcing a cluster checkpoint); a credible route exists (§4.1) that removes that work while keeping committed isolation where claims need it | §6.1 |

**Bounded decision: Revise.** The assurance architecture (sealed head, fresh committed clones with
policy replay, truthful receipts, independent expectations) is accepted as the base to preserve. The
preparation lifetimes, negative-evidence contracts, scenario ownership and evidence-class identity need
the corrections above. Evidence strength: Interface-checked source and documentation, one attributed
historical receipt; every remedy Proposed.

**Enclosing architecture:** the test system needs revision in the named areas; the product architecture
is not assessed by this review, and nothing here is release qualification.

**Next decision and owner.** The operator, in plan creation, decides RC01 and RC02 and selects findings.
The first architectural step that unblocks the most is the recipe value with staged builders (DTA-009,
DTA-018), alongside the sweep cleanup (DTA-030, F01); the refusal contract (DTA-001) and evidence-class
split (DTA-028) can proceed independently.

---

## Coordinator publication note — 2026-11-12

Added by the coordinator at publication; it is not part of the reviewer's judgment.

- **Text.** The review above is the delegated reviewer's text. The only edits are this note, the
  header's publication clause and the link to the retained evidence maps.
- **Citations opened by the coordinator at the baseline** (the ones the main recommendations rest
  on): `ops.complete_task` not checking lease expiry (`native_task_completion.sql:15–16,97`); the
  DDL-committing `db_engine` consumer (`tests/db/test_lifetime_native.py:162–164`); the second
  sweep-escaping name (`tests/semantic/test_serving_scenario_lifecycle.py:39`); the lock-capacity
  comment and `synchronous_commit = off` (`ops/postgresql/corpus.conf:7–9,30`); xdist's
  `loadgroup` scope split; the absence of `__init__.py` under `tests/ingest/` and
  `tests/evaluate/` with absolute imports of their test modules; the fixture-closure group hook
  (root `conftest.py:21–37`); the per-case commits in the witnessed-applicability family; the
  seven assembly copies and their digest handling; the lease and sweep keys behind F01; and the
  companion plan's "Retain auto as initial default". All matched the review's description.
- **Returned to the audit.** The review's refinements of DTA-009, DTA-025, DTA-026, DTA-029 and
  DTA-030 are recorded in the [test audit account](../test-audit/README.md) in the same commit, so
  the diagnostic source does not disagree with this review. F01–F03 keep their review identities.
- **Checks.** `uv run ci docs check` and `git diff --check`: see the publishing commit. Product
  tests, collection, database operations and benchmarks: not_run, by the operator's evidence rule.
