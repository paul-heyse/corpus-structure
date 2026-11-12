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
| Date | 2026-11-12 |
| Audited source | `56f8d309b0b8aaad72a2205ea54a926eaf5a8d89` plus the live working tree at capture |
| Included dirty source | 15 modified and 3 untracked test files of the in-progress BEP repair increment, read as they stood: `tests/orchestrate/` (`test_characterization_demand`, `test_characterization_recovery`, `test_execution_preparation`, `test_policy`, `test_ready_coordination`, `test_source_configurations`, `test_whole_document`, and untracked `test_source_operation`, `test_source_progress`, `test_work_context`), `tests/semantic/` (`test_characterization_native`, `test_method_dimensions`, `test_runtime_identity`), `tests/methods/` (`test_m1_cli`, `test_m1_review_repairs`), `tests/acceptance/test_regeneration.py`, `tests/core/test_method.py`, root `tests/test_native_run_scope.py`. 21 modified or untracked production files under `src/` were present and read only as contracts |
| Excluded | The GPU worktree `corpus-structure-bep-batching`; any edit made to dirty files after their reading |
| Standard | core 3.3; heuristics 1.0; test-assessment 1.2; code-intelligence 1.4 where applicable; repository binding |
| Previous account | 2026-11-05, source `bc2208f9`, publication `1e42a6e5`; superseded as a current baseline, retained in Git |
| Kind | Change-led refresh; static architectural assessment |
| Publication | The commit publishing this account, distinct from the audited source |

Paths in topic pages beginning `tests/` or `src/` are relative to `python/corpus-structure/`.
Repository-root paths are written as root `tests/…` or begin with `scripts/`, `docs/` or
`pyproject.toml`. All current source observations are **Interface-checked by source inspection,
2026-11-12**; no product behavior is freshly labelled Tested or Measured by this audit.

The working tree was under concurrent edit during reading (operator decision: read live, do
not chase drift). One documentation-only commit landed on `main` during the audit; no committed
test-scope change intervened. Findings citing the dirty files describe the state at capture.

## Scope and method

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
| [Execution and qualification](execution-and-qualification.md) | New DTA-024, 025, 026; DTA-018 with a changed footprint; DTA-021, 022 and the qualification limit corrected; 002, 003, 017 reconciled |
| [Evidence and discrimination](evidence-and-discrimination.md) | DTA-001 and 006 with changed footprints; new DTA-027; DTA-023 corrected with a narrow residue; 007, 010, 011, 013, 015, 019, 020 reconciled |
| [Support structure](support-structure.md) | DTA-009 with a changed footprint; new DTA-028, 029; 005, 008, 012, 016 reconciled |
| [Retirement and transfer](retirement-transfer.md) | New DTA-030; 004 and 014 reconciled |

Thirty DTA identities exist; none is retired or reused. The
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
