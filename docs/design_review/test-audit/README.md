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
| Date | 2026-11-17 (refresh of the 2026-11-13 account) |
| Audited source | `fbd3f2a98362da44d9c9bdb9f59bab1ff305bd36`, committed `main`, clean tree. Contributors read a frozen export of that commit, so cited lines are exact for it. The operator stated during the audit that production edits were in progress; later source is outside this refresh |
| Standard | Core 3.3; heuristics 1.0; test-assessment 1.2; code-intelligence 1.4 where applicable; repository binding |
| Previous accounts | 2026-11-13, source `main` between `64cd3d6fa` and `7458fd879`; 2026-11-12, source `56f8d309b`; 2026-11-05, source `bc2208f9`. All retained in Git; the previous publication of this collection is at `fbd3f2a98` |
| Kind | Change-led refresh by static reading, run jointly with the [broad account](../audit/README.md) at the same commit. Durations are read from stored results. No test was run |
| Emphasis (operator, 2026-11-17) | The comprehensive domain data model, and efficiency of execution, including the caching recently added to production |
| Publication | The commit publishing this account, distinct from the audited source |

Paths in topic pages beginning `tests/` or `src/` are relative to `python/corpus-structure/`.
Repository-root paths are written as root `tests/…` or begin with `scripts/`, `docs/`,
`conftest.py` or `pyproject.toml`. Observations dated 2026-11-17 are **Interface-checked by
source inspection**. Earlier findings keep the date they state. Durations are **Measured**
from stored results with their run id
([evidence](../evidence/2026-11-17_joint-audit-refresh/README.md)). No product behavior is
labelled Tested by this audit, and no speedup is measured.

<a id="refresh-2026-11-17"></a>

## Refresh of 2026-11-17: what changed and what was found

**What changed since 2026-11-13.** 421 test files were added, 177 deleted and 341 modified.
The package tests are now about 212,000 lines in 698 test modules and about 135 other support files;
`tests/semantic/` holds 147,000 of them and 84 files test declared data operations. The
test-system work (keyed head reuse, sealed scenario seeds, isolation classes, worker sizing)
landed, the legacy execution compiler and its tests were retired on 2026-11-16, and the
production side gained the efficiency mechanisms of the
[production-efficiency integration](../../plans/declared-data-operations/production-efficiency-integration.md).

**Method.** Five read-only contributors worked in parallel against the same ten questions used
for the production account (what is declared in the model and what is restated by hand; what
repeats while its inputs are unchanged; the facts of every cache and prepared holder; whether
identities are complete for what they key): shared execution infrastructure; the
data-operation tests; scenario and support modules; evidence for the new reuse and caching
mechanisms and the model compiler; and the remaining trees, sampled. The coordinator read the
decisive source behind each published finding, checked stored results where a finding said a
test could not pass, built the cost map, and reconciled candidates by structural cause across
both accounts. A fresh reviewer challenged the draft before publication
([Independent challenge](#independent-challenge)).

**New findings.**

| Finding | Summary |
|---|---|
| [DTA-037](retirement-transfer.md#dta-037) | Hand-kept fixture-name lists have drifted from the fixtures that exist; one test requests a deleted fixture |
| [DTA-038](execution-and-qualification.md#dta-038) | The deployment key cannot see imports made by executed upgrade bodies, and includes much a deployment does not depend on |
| [DTA-039](execution-and-qualification.md#dta-039) | A key miss replays the whole migration chain; sealed state is re-verified at several boundaries |
| [DTA-040](execution-and-qualification.md#dta-040) | A per-test directory is part of PDF scenario identity, so seed and preparation reuse does not hit |
| [DTA-041](support-structure.md#dta-041) | The controlled PDF converter is copied nine times and no longer produces what production requires |
| [DTA-042](support-structure.md#dta-042) | Support modules restate pack and recipe composition; one pairs a model with a release that does not contain it |
| [DTA-043](support-structure.md#dta-043) | Admission tests assemble the executor from private fields and copy the reservation formula |
| [DTA-044](evidence-and-discrimination.md#dta-044) | Mechanisms that skip a check or carry a result forward are tested only where the reuse is correct |
| [DTA-045](evidence-and-discrimination.md#dta-045) | The native host's frozen-profile refusal is asserted against a rule the test double invents |
| [DTA-046](evidence-and-discrimination.md#dta-046) | No controlled encoder-batch test has two surviving members with distinct outputs after a drop |
| [DTA-047](execution-and-qualification.md#dta-047) | Pure SQL-expression checks create a database per case and execute spliced production SQL |
| [DTA-048](execution-and-qualification.md#dta-048) | One ordinary-lane control takes the operator's real host-wide GPU lock |

**Tests that source shows cannot currently pass or set up.** Three were found by reading, and
none has a stored result since the change that affected it, so none is observed:

- the five native identity-vector cases ([DTA-033](evidence-and-discrimination.md#dta-033));
- `tests/semantic/test_source_routing.py`, which requests a deleted fixture
  ([DTA-037](retirement-transfer.md#dta-037));
- every consumer of the copied PDF converter, through two unconditional refusals added on
  2026-11-17 ([DTA-041](support-structure.md#dta-041)).

**Earlier findings.** Corrected: DTA-024, 027, 028, 030 (for the machinery it cited), 031, 032,
and 006 at its surviving site. No longer applicable at their cited sites: DTA-008, 018, 025,
029, 035. Changed footprint: DTA-001, 005, 009, 016, 026, 034, 036. Regressed: DTA-033.
Standing: DTA-002, 003, 007, 012, 017, and the earlier corrections of 021 and 022. Not re-examined: DTA-004, 010, 011, 013, 014,
015, 019, 020, 023. Each topic page carries a status table and a dated status line on the
finding.

**Where the time goes (Measured, with limits).** No passed full run exists after 2026-11-10,
so there is no current full-run profile. From narrowed runs: a run has a median 7.4 s of fixed
cost outside test phases; database-free runs finish in seconds; and setup is concentrated in a
few tests that reach a head or seed build
([Measurements](execution-and-qualification.md#measurements)).

## How the foundations were assessed

- **FP-04, domain model and identity (priority).** By asking which test scenarios and
  expectations follow the declared model and which restate it. The tests' own declared
  operation inventories are compiled by the production compiler and are appropriately
  independent of the production model. Restatement that is not independence: DTA-037, 041, 042,
  043, and the vector input of DTA-033. Identity of test preparation: DTA-038, 040.
- **FP-07 / A4, execution fit (priority).** By static reading of preparation lifetimes and keys
  (H5, H12, H14, H19, H21): DTA-039, 040, 047. The sealed-seed and keyed-head designs are
  strengths. Dependency-based test selection was rejected in the test-system plan and was not
  reopened; keying of preparation is a different question and is what these findings concern.
- **FP-02, FP-05, FP-06, evidence.** By asking, for each production mechanism that reuses or
  skips work, which test fails if the reuse is wrong: DTA-044, 045, 046, and the changed
  footprints of DTA-001, 033 and 034.
- **FP-01, FP-03, ownership.** By following imports and copies: DTA-041, 042, 043 and the
  changed footprint of DTA-009.
- **Profile.** Unknown-versus-absent and non-circular evaluation were read where served
  results are tested; no new finding.

The integrated argument with the production account, including the cache inventory for both
sides, is on the [joint page](../audit/model-and-execution.md).

## Current diagnostic navigation

| Topic | Current concerns and retained identities |
|---|---|
| [Execution and qualification](execution-and-qualification.md) | Open: DTA-038, 039, 040, 047, 048, and DTA-026 (changed). Measurements. Corrected: DTA-024, 031, 032; earlier corrections standing: 021, 022; no longer applicable: 018, 025; standing: 002, 003, 017 |
| [Evidence and discrimination](evidence-and-discrimination.md) | Open: DTA-044, 045, 046, DTA-001 (changed), DTA-033 (regressed). Corrected: 006, 027. Standing: 007. Not re-examined: 010, 011, 013, 015, 019, 020, 023 |
| [Support structure](support-structure.md) | Open: DTA-041, 042, 043, DTA-009 and 034 (changed). Corrected: 028. No longer applicable: 008, 029. Changed: 005, 016. Standing: 012 |
| [Retirement and transfer](retirement-transfer.md) | Open: DTA-037, DTA-036 (changed). Corrected: 030. No longer applicable: 035. Not re-examined: 004, 014 |

Forty-eight DTA identities exist; none is retired or reused. DTA-037–048 are unscheduled. The
[test system target design plan](../../plans/test-system-target-design_2026-11-13.md) owns the
recorded disposition of DTA-001–036 and of its review findings; this refresh does not amend
it. Where this account describes one of those as corrected or regressed, that is a diagnostic
reading of current source, and the plan's findings table remains the owner of status. Revisit
trigger for the new findings: the next diagnostic review of test architecture, or the update
the operator has said will follow the production edits now in progress.

One primary home per cause holds across both accounts. Tests whose only subject is production
code with no other consumer are footprint of
[DA-080](../audit/boundaries-and-composition.md#da-080), not a separate test finding.

<a id="independent-challenge"></a>

## Independent challenge

A fresh reviewer, given the criteria and the drafted pages but not the contributors' reports,
opened the cited sources and tried to refute each new finding, each changed footprint and each
correction claim. Its effect on the published account:

- **Withdrawn:** from DTA-044, the claim that the ready-frontier window is untested (its
  bounds are asserted in the byte-admission and execution tests) and the stated citation for
  the grammar guards, now a hypothesis; from DTA-048, the claim that a failure could set the
  GPU quarantine.
- **Strengthened:** DTA-041. The challenger read the capture function in full and found an
  earlier unconditional refusal at spool completion, so setup failure is established from
  source rather than likely.
- **Narrowed:** DTA-038 (the plan knowingly left function-level imports to verification, and
  the catalog checks do test privileges; the new point is the executed body); DTA-046 (one
  batch test does use distinct outputs; the gap is two or more survivors after a drop); DTA-040
  (the seed path does not use the prepared-kernel cache, and consumers that admit into an
  existing clone create no seed).
- **Corrected:** counts and attributions in DTA-037 (deletion dates and commits; 17 of 38
  database-fixture entries dead in effect; consumer counts), DTA-039 (285 revisions), DTA-043
  (eight stubs, sixteen tests, a third importing module, and production's constructor as
  contrary evidence), DTA-009 (91 importing files, not 64) and several line references.
- **Added contrary evidence:** to DTA-044, four existing tests that partly cover the listed
  gaps.
- **Confirmed as drafted:** DTA-033's regression, DTA-042, DTA-045, DTA-047 and the correction
  and no-longer-applicable statements.

## Limits

- **Sampled or not read.** Most of `tests/semantic/` outside the data-operation, PDF, cache and
  support files named in the findings (rich, formal, constructions, characterization and record
  bodies); `tests/llm/`, `tests/db/` and `tests/schema/` bodies; about sixty support modules
  with three or fewer importers; the bodies of about twenty data-operation test modules; root
  `tests/scripts/`; the receipt classifier beyond its reuse key. Absence of a finding there
  means not examined.
- **Not established.** Whether the tests named above actually fail (none was run); whether a
  stale head can survive verification; whether evidence records outside the tests already
  exercise the oracle skip; whether cross-directory test imports load a module twice.
- **Not run.** Product tests, collection, provider calls, database operations and benchmarks.
  Source-established unnecessary work is not a measured bottleneck. Existing failed and
  interrupted receipts keep their original dates and scope.
- Production causes were followed only far enough to judge test evidence; the production
  account, refreshed at the same commit, owns them.

<a id="observations-for-the-ddo-plan"></a>

## Observations for plan owners

Not test findings; the plans own them.

- The test-system plan's contract row for the implementation snapshot, and its closure
  evidence for DTA-032, describe an interface removed on 2026-11-16.
- The plan records DTA-033 closed on 2026-11-13; its native half regressed two days later.
- For the final qualification mapping: spliced-SQL and substitute-schema checks are
  expression-level evidence, and several efficiency mechanisms have no failing-path test
  ([DTA-044](evidence-and-discrimination.md#dta-044)).

## Earlier refreshes

The accounts of 2026-11-12 and 2026-11-13, their scoped reconciliations for the PostgreSQL
tooling and assembled test-system reviews, the refinements returned by three design reviews,
the library and tooling assessment and the publication checks of those dates are in Git at
`fbd3f2a98`. The anchors below preserve links to them.

<a id="refresh-2026-11-13"></a>
<a id="postgresql-tooling-reconciliation"></a>
<a id="assembled-test-system-reconciliation"></a>
<a id="refinements-returned-2026-11-13"></a>

## Publication checks — 2026-11-17

- **passed:** `uv run ci docs check` (result `d2e8ef51bca54f089433faedfa1ef9eb`; 1,310 canonical pages, no link errors),
  after two earlier anchors that reviews still link to were restored to the broad README.
- **passed:** identity check by search over both collections: DA-001–080 and DTA-001–048 each
  have one anchor, none reused.
- **not_run:** product tests, collection, provider and native controls, benchmarks,
  `uv run ci test` and `uv run ci check`. Durations were read from stored results; this
  publication changes no product behavior.
- No design-alignment checker, process gate, library catalog or dependency was added.
