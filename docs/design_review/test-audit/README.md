# Test code design principle audit

The separate living diagnostic account for test code, test evidence and shared infrastructure.
The [skill](../../../.claude/skills/design-principle-audit-tests/SKILL.md) owns method and the
[binding](../design_principles/binding/corpus-structure.md#test-code-design-principle-audit)
owns applicability and identities. This account diagnoses; reviews compare solutions and plans
own scheduled disposition. Publication authorizes no product repairs or qualification.

<a id="baseline"></a>

## Baseline

| Item | Inspected state |
|---|---|
| Date | 2026-11-13 (refresh of the 2026-11-12 account) |
| Audited source | `main` between `64cd3d6fa` and `7458fd879`, read live on 2026-11-13 while another session committed declared-data-operations work (operator direction: do not chase the latest tree). Contributors read `fc87caa57`; the coordinator verified cited sources at `14f7bdfe3` and `b96898abf`. Cited line numbers are as read and may have moved |
| 2026-11-12 source | `56f8d309b0b8aaad72a2205ea54a926eaf5a8d89` plus the live working tree at that capture; findings dated 2026-11-12 keep that source |
| Included dirty source | 15 modified and 3 untracked test files of the in-progress BEP repair increment, read as they stood: `tests/orchestrate/` (`test_characterization_demand`, `test_characterization_recovery`, `test_execution_preparation`, `test_policy`, `test_ready_coordination`, `test_source_configurations`, `test_whole_document`, and untracked `test_source_operation`, `test_source_progress`, `test_work_context`), `tests/semantic/` (`test_characterization_native`, `test_method_dimensions`, `test_runtime_identity`), `tests/methods/` (`test_m1_cli`, `test_m1_review_repairs`), `tests/acceptance/test_regeneration.py`, `tests/core/test_method.py`, root `tests/test_native_run_scope.py`. 21 modified or untracked production files under `src/` were present and read only as contracts |
| Excluded | The GPU worktree `corpus-structure-bep-batching`; any edit made to dirty files after their reading |
| Standard | core 3.3; heuristics 1.0; test-assessment 1.2; code-intelligence 1.4 where applicable; repository binding |
| Previous accounts | 2026-11-12, source `56f8d309b`, publication `cf24c0e80`; 2026-11-05, source `bc2208f9`, publication `1e42a6e5`; both retained in Git |
| Kind | Change-led refresh; static architectural assessment, with durations read from stored test results. No test was run |
| Emphasis (operator, 2026-11-13) | Execution time of the test scope, and alignment of the test architecture with the [declared-data-operations](../../plans/declared-data-operations_2026-11-12.md) target design |
| Publication | The commit publishing this account, distinct from the audited source |

Paths in topic pages beginning `tests/` or `src/` are relative to `python/corpus-structure/`.
Repository-root paths are written as root `tests/…` or begin with `scripts/`, `docs/` or
`pyproject.toml`. Source observations are **Interface-checked by source inspection** on the date
each finding states, 2026-11-12 or 2026-11-13. Durations are **Measured** from stored results
with their run id and conditions
([evidence](../evidence/2026-11-13_test-audit-refresh/README.md)). No product behavior is
labelled Tested by this audit, and no speedup is measured.

The working tree was under concurrent edit during reading (operator decision: read live, do
not chase drift). One documentation-only commit landed on `main` during the audit; no committed
test-scope change intervened. Findings citing the dirty files describe the state at capture.

<a id="refresh-2026-11-13"></a>

## Refresh of 2026-11-13: what changed and what was found

**What changed since 2026-11-12.** 133 test files changed (about 22,000 lines added), 63 of them
new, nearly all for the declared-data-operations work. The shared execution infrastructure did
not change: both package conftests, root `conftest.py`, `scripts/native_test_support.py`,
`scripts/test_receipts.py`, `scripts/qualification_plugin.py` and `cli/testing.py` are identical
to the previous baseline, and root `pyproject.toml` changed only its dependency list. Every
earlier finding about that infrastructure therefore stands on unchanged source.

**Method.** Four read-only contributors worked in parallel: fixture, database and scenario
lifecycle; scheduling, the managed wrapper, waiting and long tests; alignment of the
data-operation tests with the target design; and a map of tests tied to machinery the plan
removes, the plan's named assurance gaps and the qualification route. The coordinator built the
cost map from stored results, read the decisive source behind each published finding, and
reconciled candidates by structural cause. Unlike the 2026-11-12 refresh, no separate reviewer
challenged the draft before publication.

**Where the time goes (Measured; details under
[Measurements](execution-and-qualification.md#measurements)).**

- The full run is bound by total work. Workers are 96% busy, so there is little to gain from
  rebalancing and the lever is the work itself.
- Setup is 36% of the full run and is concentrated in about 335 tests. Per-test database clones
  are cheap (well under a second). The cost is in three places: the head deployment built once
  per worker ([DTA-024](execution-and-qualification.md#dta-024), now measured at roughly 40–55 s
  and more under contention); identical committed scenarios rebuilt per case
  ([DTA-025](execution-and-qualification.md#dta-025), [DTA-031](execution-and-qualification.md#dta-031)
  and the review's F03); and pure release preparation repeated once per worker (the review's F02,
  below).
- A large share of call time is also scenario construction, performed inside test bodies
  ([DTA-025](execution-and-qualification.md#dta-025), changed footprint).
- A focused run has about 7.5 s of fixed overhead. If it touches the database it also pays the
  head build, which makes a one-test native run take a minute or more.

**New findings.**

| Finding | Summary |
|---|---|
| [DTA-031](execution-and-qualification.md#dta-031) | Data-operation native tests rebuild one identical admitted kernel per case; read-only and rollback-only checks take the same route |
| [DTA-032](execution-and-qualification.md#dta-032) | Standalone interpretation contexts recompute implementation determinants on every call, before the parse memo; suspected main cost of the math property test |
| [DTA-033](evidence-and-discrimination.md#dta-033) | The product identity production now uses is checked only against itself |
| [DTA-034](support-structure.md#dta-034) | Planner and service doubles sit below wire validation; compiled binding semantics run only on SQLite |
| [DTA-035](retirement-transfer.md#dta-035) | Required behavior is asserted through machinery the target design removes, with no per-test record of what survives |
| [DTA-036](retirement-transfer.md#dta-036) | The data-operations test union has no mapping from its obligations to tests (refined 2026-11-13: the recorded path lists are accurate receipts) |

**Changed premises and footprints.** DTA-024 (measured; concurrent builds add latency, and a
floor remains without cross-run reuse); DTA-025 (four families building in the test body);
DTA-018 (a full migration replay to obtain a second database); DTA-009 (no support owner for the
data-operation tests, and a relative import across a non-package directory); DTA-030 (a third
database name the sweep cannot reclaim); DTA-001 (one permissive refusal match).

**Measurements added to review findings, which keep their review identities.** For F02
(preparation rebuilt on every worker): `prepare_release` is cached per process only
(`src/corpus_structure/semantic/prepare.py:592`, eight entries) and module-scoped fixtures live
per worker, while the tests of one module spread across workers. A contributor measured in
`2e2a0e30…` ten workers each spending 28–37 s in setup for the statistics pack behind
`tests/orchestrate/test_policy.py:36–38`, with every other test in that module at zero; the
coordinator's table shows that module at 292 s of setup and no call time. The same pattern
appears for `tests/semantic/test_interpretations.py` and root `tests/test_native_run_scope.py`,
and in a two-worker focused run (`ea623a16…`, about 19 s on each worker for one module fixture).

**Foundations.** FP-07/A4 received the most attention, through H5 (smallest sufficient scope),
H12 (stable preparation separated from changing values), H19 (established state carried through
operations that preserve its premises), H21 (shared capacity), H26 (auxiliary work in
proportion) and H27 (the whole lifecycle including test setup). FP-04/06 were assessed by
tracing where data-operation expectations come from (DTA-033, and the areas found sound there).
FP-01/03 by following helper ownership across the new modules (DTA-009). FP-02 by asking which
boundary each substitute stands below (DTA-034) and which tests are coupled to machinery being
removed (DTA-035). FP-05 by checking that refusals name their reason and that qualification
scope is explicit (DTA-001, DTA-036). The code-intelligence profile applied only to source
capture tests, where unknown is kept distinct from absent.

**Limits of this refresh.**

- Non-data-operation files changed since 2026-11-12 (about 70, among them
  `tests/methods/test_native_host.py`, `test_characterization_resources.py`,
  `test_contextual_query_replay.py` and `test_definition_model_native.py`) were not read. DTA-001,
  006, 026, 027, 028 and 029 were not re-examined beyond confirming that their cited
  infrastructure is unchanged; `test_pm2_result_native.py` changed its provider opening and
  keeps the ambient-variable branch DTA-028 describes.
- About 60% of data-operation test lines were read. Skimmed only: the artifacts, cpu,
  execution-evidence, member-projection, preparation, runtime, source-native and
  consumer-binding modules. Several files were mid-edit by another session at the end of reading.
- `domain_scenarios.py`, `reference_scenarios.py`, `pdf_integration_support.py` and
  `witnessed_scenario_support.py` were not read in depth, so which parts of their scenarios each
  consumer needs is not established beyond the sites named.
- The full-run receipt predates the data-operation tests; their costs come from narrowed runs.
  The host was shared during every run read. Nothing was profiled, so where a finding attributes
  a duration to a cause inside a phase, that attribution is from source.

<a id="observations-for-the-ddo-plan"></a>

**Observations for the declared-data-operations plan owner** (not test findings; the plan owns
them):

- Its findings table still shows DDO-CA-01, 02 and 04 as open and "sequential" or "not covered",
  while tests now exist: overlapping publication at
  `tests/semantic/test_data_operation_storage.py:1822`, purpose-gate refusals with a real writer
  principal at `:1862` and `:1898`, and captured-object and callable-escape refusals at
  `tests/semantic/test_data_operation_compilation.py:1220`. Existence is not a fresh run.
- Gaps against the plan's own verification text, by search: no overlapping publication with
  differing intents; no case set run through both the native and the compiled binding
  implementation; no helper-body or inherited-value case in the source-change matrix; no
  invalidated-support recovery through a real consumer.
- The database-lane statements disagree (see [DTA-031](execution-and-qualification.md#dta-031)).
- Nineteen data-operation test modules appear in none of the recorded campaigns ([DTA-036](retirement-transfer.md#dta-036), as refined).

## Scope and method of the 2026-11-12 refresh

This is a refresh led by change, not a full reread. Since the previous baseline the authored
test scope grew from 418 Python files to 567 (about 183,000 lines), and the shared
qualification scripts changed substantially. The reading union is every Python file under the
package and root test trees and `scripts/` that was added or modified since `bc2208f9`, plus
the dirty and untracked test files: 330 files, about 134,000 lines. Unchanged files were read
only where a changed helper, fixture or production contract led there. Production code was read
far enough to understand the tested contract and what a test shares with it. The Rust workspace
has no test; nextest configuration was read only where the managed route touches it.

Reading was partitioned by testing responsibility among seven read-only contributors: shared
execution, receipt and qualification infrastructure with root tests (22 files); semantic
execution, runtime, characterization, native-operation and orchestration tests (57); semantic
PDF, artifact, publication, projection and reference tests (32); the remaining semantic tests in
two halves (50 and 58); methods, evaluate and math (67); ingest, schema, core, acceptance, db
and package-level CLI tests (44). Four partitions were sent back for files skipped on the first
pass. The root read the decisive source behind each published finding, re-checked every earlier
DTA premise named below, and reconciled contributor candidates by structural cause. A fresh
reviewer then challenged the drafted findings against source before publication; its effect is
recorded under [Independent challenge](#independent-challenge).

Depth achieved, stated as limits rather than as coverage credit: roughly 190 files were read in
full or in their load-bearing substance, roughly 100 were read in part by section, and roughly
40 were examined only through targeted search, diffs and docstrings. The thinnest areas are:

- `tests/methods/`: about two dozen modules were assessed only from docstrings and searches for
  refusal, fixture and import patterns (including `test_pm2_hanlp_products`, `test_pm2_source`,
  the `test_m1_source_*` family, `test_definition_*`, `test_predicate_*`, `test_navigation`,
  `test_nce02_cross_block`, `test_joined_citation_replay`).
- `tests/semantic/`: not reached beyond search were `test_m1_annotation_configuration_native`,
  `test_method_dimensions_native`, `test_occurrence_context`,
  `test_postgresql_capability_adoption`, `test_record_alternative_publication_native`,
  `test_record_compiler15`, `test_private_record_report_absence_native`, `test_statistics_cut`,
  `test_ontology`, `test_record_contracts`, `test_section_heading_replay` and
  `test_observations`; sampled only were `test_source_views`, `test_native_documents`,
  `test_operation_reporting` and its native sibling, `test_model_apply`,
  `test_source_decision_journey`, most of `test_characterization_evidence` and
  `test_characterization_native`.
- Root `tests/scripts/test_native_auth.py` lines 700–1084 and `scripts/native_auth.py`.

Absence of a finding in those files means not examined. Counts of weak refusal sites in sampled
files come from search and may be incomplete. These are source files and physical lines, not
executable-node or pass counts.

Representative scenarios used as inquiry leads: a focused selection of a few native tests; a
behavior-preserving refactor of a helper inside a test module; removal of one specific database
guard while its neighbours remain; a change to a production grace constant; a provider asset
variable being unset on the qualifying host; a secret positioned across an output clip
boundary; a migration head moving past a candidate revision. No exhaustive trace or mutation
campaign was imposed.

## How the foundations were assessed

- **FP-01/03:** followed scenario ownership and change propagation through imports between
  test modules, fixture-name overrides and configurable scenario builders. The private-global
  patching recorded earlier is corrected; ownership still sits in test modules and import
  bindings ([DTA-009](support-structure.md#dta-009)), and a production assembly sequence is
  copied across method tests ([DTA-029](support-structure.md#dta-029)).
- **FP-02:** distinguished the boundary each test actually exercises (in-process runner,
  in-memory client, stdio child, real PostgreSQL, hand-written double) from the one its name or
  identity claims ([DTA-028](support-structure.md#dta-028)), and looked for observations
  coupled to private implementation state ([DTA-026](execution-and-qualification.md#dta-026)).
- **FP-04:** inspected whether expectations are authored independently of the code they judge:
  identity vectors, literal Arrow rows, analytic closed forms, hand-authored gold and reference
  answers are; a few score and comparison expectations have neutral or degenerate inputs
  ([DTA-001](evidence-and-discrimination.md#dta-001),
  [DTA-006](evidence-and-discrimination.md#dta-006)).
- **FP-05:** inspected whether refusals reach the intended boundary for the intended reason and
  whether absence assertions have a presence premise
  ([DTA-001](evidence-and-discrimination.md#dta-001),
  [DTA-027](evidence-and-discrimination.md#dta-027)); and whether support code and branches
  still have a producer ([DTA-030](retirement-transfer.md#dta-030)).
- **FP-06:** examined what a focused test must bootstrap, ambient environment and ContextVar
  handling, process-wide caches touched by tests, and whether evidence class is visible from
  test identity. The autouse refused application target and the per-row context tests are
  strengths. Several long single-scenario tests chain many dependent phases
  (`tests/semantic/test_pdf_visual_requests.py`, `tests/semantic/test_reference_evaluation.py`,
  `tests/acceptance/test_regeneration.py`, `tests/schema/test_model_change_preview.py`); this
  costs diagnosis when an early phase fails, and is left as an observation because sharing one
  prepared scenario across phases is also the economical choice that DTA-025 notes is missing
  elsewhere.
- **FP-07/A4:** this refresh gave execution fit particular attention through static reading of
  fixtures, support infrastructure and the managed route. The judgments rest on preparation
  lifetime versus validity (H12, H19), smallest sufficient scope (H5), demand for results (H6)
  and coordination of shared capacity (H21). Findings: the identical head deployment rebuilt
  per worker ([DTA-024](execution-and-qualification.md#dta-024)); rollback-only refusal families rebuilding
  committed scenarios ([DTA-025](execution-and-qualification.md#dta-025)); focused consumers of
  full scenarios ([DTA-018](execution-and-qualification.md#dta-018)); real-time grace waits
  ([DTA-026](execution-and-qualification.md#dta-026)). Fresh committed clones, real process
  boundaries, cold-interpreter controls and independent expectations remain justified
  assurance. All of this is demonstrated unnecessary work by structure; no elapsed time,
  share or speedup is claimed and none was measured.
- **Profile:** served and agent-facing tests were read for attributed evidence, unknown versus
  absent and non-circular evaluation. Unknown/absent/empty distinctions and hand-authored gold
  are strengths. Served surfaces are exercised at different boundaries in different files
  (in-memory client over a real database, direct function call, mocked connection, real stdio
  child); no single file is wrong, but which boundary covers the size-preflight query and the
  registration of structural tools was not resolved.

## Current diagnostic navigation

| Topic | Current concerns and retained identities |
|---|---|
| [Execution and qualification](execution-and-qualification.md) | Open: DTA-024 (measured 2026-11-13), 025 and 018 (footprints extended 2026-11-13), 026, and new DTA-031, 032. Measurements. Corrected: DTA-021, 022; reconciled: 002, 003, 017 |
| [Evidence and discrimination](evidence-and-discrimination.md) | Open: DTA-001, 006, 027 and new DTA-033. DTA-023 corrected with a narrow residue; 007, 010, 011, 013, 015, 019, 020 reconciled |
| [Support structure](support-structure.md) | Open: DTA-009 (footprint extended 2026-11-13), 028, 029 and new DTA-034. 005, 008, 012, 016 reconciled |
| [Retirement and transfer](retirement-transfer.md) | Open: DTA-030 (footprint extended 2026-11-13) and new DTA-035, 036. 004 and 014 reconciled |

Thirty-six DTA identities exist; none is retired or reused. DTA-031–036 and the footprints
added on 2026-11-13 are unscheduled: no plan has selected them, and the 2026-11-12 design review
left its own dispositions deferred to plan creation. DTA-031, 033, 035 and 036 concern tests of
the declared-data-operations work; if that plan takes them up, its findings table becomes their
disposition owner and this account links to it. The
[test audit resolution coordinator](../../plans/test-audit-resolution_2026-11-05.md) is complete
for its authorized scope and owns the recorded disposition of DTA-001–023 as they stood on
2026-11-05; this refresh does not amend it. The current-source statuses above are diagnostic:
where a finding is described as corrected, the closure evidence is the cited source and that
plan's record, and where a footprint changed, the new manifestations are unscheduled. DTA-024–030
and the changed footprints of DTA-001, 006, 009 and 018 remain here until a review or plan
selects them. Revisit trigger for all of them: the next diagnostic review of test architecture,
or earlier for DTA-024 if ADR-0032 is revisited under its own trigger.

## Independent challenge

A fresh reviewer, given the criteria and the drafted pages, independently opened the cited
sources and attempted to refute each new finding, each changed footprint and each correction
claim. It did not reread the reading union. Its effect on the published account:

- **Withdrawn before publication:** a drafted finding that the managed route does work with no
  reader. The nextest run record is read by the classifier, and `classification.json` is the
  as-run classification retained in evidence folders.
- **Reframed:** DTA-024 now rests on ADR-0032, which owns the session-template decision, and no
  longer cites the current `--workers 1` instruction, which stems from an unattributed memory
  interruption. Per-clone policy replay is recorded as required work, with only its connection
  lifecycle noted.
- **Narrowed:** DTA-027 to the one CLI control, with the length arithmetic redone; DTA-028's
  naming footprint; DTA-029's footprint and its divergence claim; the writer-bypass
  manifestation of DTA-001, bounded by the role-denial controls.
- **Corrected:** several line ranges and counts, and the description of one partly corrected
  control.
- **Added:** the lease and worker-distribution premises under DTA-025, and the sweep-escaping
  database name under DTA-030.
- **Confirmed as drafted:** DTA-018, and the corrections of DTA-021, DTA-022, DTA-023 and the
  qualification limit.

<a id="refinements-returned-2026-11-13"></a>

## Refinements returned by the design review — 2026-11-13

The [design review of the test system target design](../reviews/design_review_test-system-target-design_2026-11-13.md)
consumed this account at publication `28b4a53db`, read `main` at `a5ea7c4dc`, and supersedes the
2026-11-12 review. It challenged each diagnosis. Two refinements are recorded in the topic pages
with that attribution, both confirmed in source by the coordinator:

- **DTA-036:** the plan's path lists are accurate receipts of bounded campaigns, not a stale
  union. The residue is the missing mapping from DDO-12's obligations to tests.
- **DTA-032:** every interpretation context re-reads the determinants, with or without a
  prepared release.

It also extended footprints without changing a diagnosis (seven importers of the storage test
module and the admission sequence in six modules, at its later baseline), found that the lease
waits need no production change because the suite already expires leases through the publisher
role, and added its own findings F04 (the sweep fails unrelated runs on residue still in use)
and F05 (every focused run starts sixteen workers), which keep their review identities. Remedies,
rule impacts RC01–RC04 and dispositions live in the review; all are deferred to plan creation.

## Refinements returned by the design review — 2026-11-12

The [design review of test architecture and efficiency](../reviews/design_review_test-architecture-and-efficiency_2026-11-12.md)
consumed this account at publication `cf24c0e80` and reconciled it to `main` `784d86f11`, where
every site cited in the files that were dirty at capture is unchanged. Its reviewer challenged
each diagnosis; the following refinements are recorded in the topic pages with that attribution
and were confirmed in source by the coordinator:

- **DTA-025:** two listed families leave the footprint as written (one commits per case, one has
  genuinely different scenarios); the lease premise is narrower.
- **DTA-009:** the open duplicate-module question is settled: test modules in non-package
  directories that are imported by absolute name load twice.
- **DTA-029:** seven copies rather than nine; the digest handling splits three to three.
- **DTA-030:** a second sweep-escaping database name and one unreferenced support module.
- **DTA-026:** production's adapter shares the dependency on executor internals; the
  test-specific concern is writing private attributes.

The review's own findings (`F01` sweep and lease keys differ, `F02` module- and session-scoped
preparation rebuilt per worker, `F03` committing consumers rebuild identical scenarios) keep
their review identities and are not copied here. Remedies, rule impacts and current
dispositions live in the review.

## Library and system-tooling assessment

No new library research was needed for this refresh; the 2026-11-05 assessment of pytest,
Hypothesis, LinkML, Arrow, FastMCP/AnyIO/Typer and the SQLAlchemy/Psycopg/Alembic/PostgreSQL
stack is recoverable in Git and nothing read here contradicts it. Mechanisms relevant to the
new findings are already present in the repository: pytest fixture scopes and markers,
xdist group scheduling (`--dist=loadgroup`, used for math preparation in root `conftest.py:37`),
the sealed-seed-and-clone pattern in `tests/semantic/serving_scenarios.py`, and SQLSTATE,
constraint and message assertions through Psycopg diagnostics. No tool was installed and no
library behavior beyond what the cited source shows is relied on; in particular what PostgreSQL
carries through `CREATE DATABASE … TEMPLATE` was not checked against its documentation.

## Limits and follow-through

No product tests, collection, provider calls, database operations or benchmarks were run for
this audit. Source-established unnecessary work is not a measured bottleneck. Existing failed
and interrupted qualification receipts retain their original dates, source and scope; this
audit closes no BEP, PCE, provider or full-union acceptance obligation. Production causes were
followed only to judge test evidence, not to refresh the broad audit's baseline.

Each finding has one primary home; no existing DA finding in the broad audit covers these
causes. Stable identities and anchors remain; removed text and its evidence are recoverable in
Git. A solution lead in a finding is not a selected remedy. DTA-024 meets the revisit trigger
that [ADR-0032](../../adr/0032-native-test-deployment-equivalence.md) states for itself; whether
to revisit that decision is for its owner.

## Publication checks — 2026-11-13

- **passed:** an ephemeral read-only check of every relative link and anchor in this collection
  and the evidence folder README (none broken), and of DTA identities (36 unique: 001–030
  preserved, 031–036 added, none retired); `git diff --check` on the same paths.
- **failed:** `uv run ci docs check` (result `21bc59fd270c45cc927bcb608a6674d1`). It stops at
  `scripts/adr.py lint`, which reports that DESIGN §B1, §B4 and §B5 carry no `> Decision:` line
  naming ADR-0100. That is in-progress declared-data-operations work owned by another session;
  the publisher's own link check did not run because of it.
- **not_run:** product tests, collection, provider and native controls, benchmarks,
  `uv run ci test` and `uv run ci check`. Durations were read from stored results; this
  publication changes no product behavior.
- **not_run:** `just turn-end` and the STATUS handoff. Another root session holds uncommitted
  source and test edits on `main`; formatting the tree or rewriting STATUS would touch its work.
  This is a path-limited commit of this collection, its evidence folder and one corrected
  cross-reference in the broad account.
- No design-alignment checker, process gate, library catalog or dependency was added.

## Publication checks — 2026-11-12

- **passed:** `uv run ci docs check` (911 canonical pages, no link errors; invocation
  `81bbb0b06d8449bb84aa4b64fd4f1675`); documentation publication only.
- **passed:** `git diff --check -- docs/design_review/test-audit`, and an ephemeral read-only
  anchor reconciliation accounting for 30 unique DTA identities: 001–023 preserved, 024–030
  added, none retired.
- **not_run:** product tests, collection, provider and native controls, benchmarks,
  `uv run ci test` and `uv run ci check`; this diagnostic publication changes no product
  behavior.
- **not_run:** `just turn-end` and the STATUS handoff. Another root session owns uncommitted
  BEP source and STATUS.md; this publication is a path-limited commit of this collection only
  (operator decision, 2026-11-12).
- No design-alignment checker, process gate, library catalog or dependency was added.
