# Retirement and transfer

**Interface-checked by source inspection, 2026-11-12; additions dated 2026-11-13.** Use the
[account baseline](README.md#baseline).
ADR-0047 retires obsolete formats without retiring current scientific meaning, source evidence
or independent expectations. Historical test deletion alone establishes no assurance loss.

<a id="dta-030"></a>

## DTA-030 — Superseded fixture machinery remains in shared test support

**FP-01/03, DP-16; A3; companion §2/6.** Two pieces of test support no longer have a live
producer or reachable path but are still maintained and, in one case, tested.

The keyed cross-session template cache of the legacy test engine: that engine and its
template creation were removed on 2026-11-02 (`1351e3c35`), but
`scripts/native_test_support.py:46–49` keeps `TEMPLATE_PREFIX = "cs_tpl_"`, `TEMPLATE_RETENTION`
and the `STAMP` pattern, `PgAdmin.stamp()` (`:547–552`) and the stamp branch of the ownership
comment check (`:248`) serve only that scheme, `sweep` (`:555–586`) still selects and ages
`cs_tpl_*` databases, and `tests/conftest.py:43,170` re-exports the retention constant. Nothing
in `scripts/`, either test tree, `justfile`, `ops/` or the package source creates a database
with that prefix; current templates are named `cs_sem_head_<pid>_…`
(`tests/conftest.py:255–260`). The only exercise is
`tests/test_db_fixtures.py:124–152`, which fabricates `cs_tpl_` names to test the sweep branch.
The `committing_db` fixture (`tests/conftest.py:295–303`) likewise has one consumer, its own
self-test (`tests/test_db_fixtures.py:57–66`).

A candidate-migration replay branch:
`tests/semantic/test_native_attributed_evidence.py:50–72` shadows the shared
`semantic_db_engine` fixture. Its only difference from `tests/semantic/conftest.py:28–35` is a
branch that replays candidate operations from a dated evidence folder when the deployed
revision equals `semantic_m1_private_20261103`. That revision is an interior node of the
migration chain; the single head is `semantic_bep_capacity`, and the fixture always clones the
head template, so the branch cannot run. Its own comment says it should give way once a forward
migration owns the objects. The module still imports the migration machinery and names a path
under `docs/design_review/evidence/` that only the unreachable branch would read. The copy
also names its databases `cs_sem_m1_attributed_<hex>` with no process id (`:53`), which falls
outside the names `sweep` recognises (`scripts/native_test_support.py:587–595`): residue from
an interrupted run of this module would not be reclaimed. A second name escapes the sweep in
the same way (added by the [design review](../reviews/design_review_test-architecture-and-efficiency_2026-11-12.md),
2026-11-12): `tests/semantic/test_serving_scenario_lifecycle.py:39` names its second clone
`cs_sem_test_<hex20>` with no process id. `tests/semantic/snapshot_restore.py` has no importer
or reference outside retained evidence.

A third name escapes it (2026-11-13): `ddo_kernel_engine`
(`tests/semantic/test_data_operation_storage.py:162–168`) names its clones `cs_ddo_case_<hex12>`.
The sweep selects only names beginning `ci_test_`, `cs_tpl_` or `cs_sem_`
(`scripts/native_test_support.py:569–583`), so residue from an interrupted data-operation test
run is never reclaimed. The fixture is otherwise a copy of `semantic_db_engine`
(`tests/semantic/conftest.py:27–34`) under another name.

The consequence is maintained and tested surface for behavior with no producer, and a divergent
copy of a shared fixture that will not follow changes to the original. The design-stage
guidance in AGENTS.md treats removal of superseded machinery as part of delivering its
replacement. Uncertainty: databases with the old prefix may still exist on the development
cluster, which would give the sweep branch a remaining cleanup purpose until they are gone.
A lead outside test scope, not assessed here: the legacy `python/corpus-structure/alembic/`
chain lost its reader in the same commit and no current reference to it was found.
Evidence folders themselves are retained by standing
operator rule and are not in question.

<a id="dta-035"></a>

## DTA-035 — Required behavior is asserted through machinery the target design removes

**FP-02/03, DP-16; A1/A3; companion §5. Interface-checked by source inspection, 2026-11-13;
classification by a contributor, sampled by the coordinator.** The declared-data-operations plan
removes copied task reuse, `ops.valid_reuse`, `ops.task_dependency`, freshness seeds,
`source_dependencies`, `OperationDescriptor` bypasses, stage-run sequencing and
`SourceOperationLink` grouping, and says to retire tests that only restate those mechanisms
while keeping independent semantic expectations
(`docs/plans/declared-data-operations/preservation-adoption-and-qualification.md:53–55`,
`change-reuse-and-consolidation.md:74–77`).

Read against that rule, few tests are mechanism-only and most are mixed:

| File (`tests/`) | Mostly mechanism | Required behavior carried on removed machinery |
|---|---|---|
| `semantic/test_operations.py` | About eleven collected cases: reuse status and `reused_task_id` (`:415`, `:465`), nine forged-reuse cases (`:562`), freshness as invocation salt (`:827`) | Terminal fence, exact replay and sealed cut (`:30`), wrong attempt (`:126`), cancel drains claims (`:897`), stale lease refused (`:950`) |
| `semantic/test_runtime_bindings_native.py` | One test asserting `ops.valid_reuse` and `reused_task_id` (`:180–246`) | Runtime pins, eight altered-binding refusals (`:113`), immutability, changed runtime cannot claim |
| `semantic/test_source_jit_native.py` | Two of three tests assert `ops.task_dependency` rows (`:342`, `:432`, `:636`) | Stale completion refused after reclaim |
| `orchestrate/test_characterization_recovery.py` | About five: anchor run, run-option link, freshness seed (`:45`, `:89`, `:128`, `:172`, `:185`) | Capacity-policy change, receipt failure cannot replace recovery, provider identity |
| `orchestrate/test_source_progress.py` | One reused-count assertion (`:151`) | Readiness semantics in about eight tests, all built through a helper that constructs `SourceOperationLink` (`:71`) |
| `orchestrate/test_ready_coordination.py` | None wholly | Claim and byte-budget behavior, with `max_active_stage_runs` as a parameter in three tests |
| `semantic/test_characterization_native.py` | None wholly | Publication, sealing and size limits; `OperationDescriptor` (`:1421`), `freshness_seed` (`:2061`) and `source_dependencies` (`:1249`) appear as inputs |
| `semantic/test_domain_operations.py` | None | Consolidation semantics; one cyclic-reference expectation (`:498`) is tied to the classification the plan's DDO-08 repairs |

The same names appear in fixtures of at least eight further files, including
`test_retained_source_reuse_native.py`, `test_source_views.py`, `test_coverage_comparison.py`,
`tests/evaluate/test_operation_assessment.py` and `tests/acceptance/test_regeneration.py`.

The diagnosis is not that these tests are obsolete. It is that the behavior the plan must
preserve is expressed in fixtures and assertions that name the machinery being removed, so at
cutover each test needs a judgment (delete, or re-express on the new surface) that the plan
states as a rule and nowhere records per test. Until then the expectations cannot fail for the
new implementation, and a deletion by file would lose required behavior. Equivalents on the new
surface exist for part of it (publication and exact receipt replay, expired owner, cancellation,
immutability and binding refusals in `test_data_operation_storage.py`). No counterpart was found
for source-view batching, readiness progress or characterization recovery.

These files are also not cheap to keep. In the 442-test union `e332a3ef…`,
`test_domain_operations.py`, `test_operations.py` and `test_runtime_bindings_native.py` take
1,087 of 2,636 worker-seconds (Measured; see
[Measurements](execution-and-qualification.md#measurements)), nearly all of it scenario
construction in `test_domain_operations.py`, which is behavior that stays.

Counts are a contributor's approximations from reading, and the further files were found by
search and not classified. The old run and task path is live until cutover, so its tests are
current evidence for current code.

<a id="dta-036"></a>

## DTA-036 — The declared-data-operations test union exists only as prose path lists

**FP-05/06, DP-21/22; G7; companion §6. Interface-checked by source inspection, 2026-11-13.**
The plan's final package requires that the declared union of tests be covered on frozen source
and says no earlier campaign substitutes for it. That union is recorded as shell path lists
inside the coordinator plan (`docs/plans/declared-data-operations_2026-11-12.md`, four lists of
18, 6, 28 and 3 paths). Nothing else names it: the registered markers are `db` and
`shared_cluster_fault` (root `pyproject.toml:70–73`), `ci test` takes pass-through pytest
arguments, and no path-list file or option exists in `cli/testing.py`, `scripts/test_receipts.py`
or the `justfile` (searched for `ddo` and `data_operation`).

**Refined by the [design review](../reviews/design_review_test-system-target-design_2026-11-13.md),
2026-11-13, and confirmed by the coordinator.** The four lists are receipts of bounded campaigns,
and the plan says they are not the DDO-12 union. The path described as stale in the next
paragraph existed when its campaign ran: that campaign's commit `0de179fc7` precedes the deletion
in `9d996b32d`. So the lists are accurate history, and rerunning one is not their purpose. What
remains of this finding is narrower: DDO-12's union is defined by an obligation table that names
no test identities, and nineteen data-operation modules appear in none of the recorded campaigns
(a contributor's comparison), so nothing yet maps each obligation to the tests that discriminate
it. The paragraphs below are kept as first written.

One list is already stale: it names `tests/semantic/test_release_wire_payload.py`
(`docs/plans/declared-data-operations_2026-11-12.md:353`), deleted in `9d996b32d` when the archive
transport tests replaced it. A run of that list as written fails at collection or, if the path
is dropped by hand, silently covers less than the record says. Thirty-two data-operation test
modules exist and the largest recorded union names 28 paths of mixed old and new files, so
which new modules the union omits is a matter of comparing prose with the tree.

The consequence is for qualification, and for pace: each focused run during this work is an
ad hoc selection typed from the plan, and whether a given run covered the required set is
established by reading argument lists. The repository's process rule is to add no register
without a consumer; the plan's final package is one. No remedy is selected here.

<a id="dta-004"></a>

## DTA-004 — Selected independent reference counterparts are explicit

**FP-04/05, DP-23; CI-12 where applicable; companion §1/4/7.** Still holds, narrowly checked:
`tests/semantic/test_reference_counterparts.py` and `test_trace_counterparts.py` are unchanged
since the previous baseline. `tests/semantic/test_reference_evaluation.py` authors its
reference answers by hand with identifiers distinct from the prediction and submits a
hand-authored batch through the real proposal tool, so its grading is not circular; its
discrimination limit is recorded under
[DTA-006](evidence-and-discrimination.md#dta-006). No reference authoring, provider call or
corpus evaluation was performed by this audit.

<a id="dta-014"></a>

## DTA-014 — The broad dormancy diagnosis remains withdrawn

**FP-01/03/04/07, DP-16/22/23; companion §1/2/8.** Still holds. `tests/core/test_conformance.py`
and `tests/evaluate/test_equivalence.py` are unchanged and keep their independent expectations.
Absence of an additional runtime caller does not make those contract tests waste. DTA-030 above
is a different matter: it names support code and a branch with no producer, not tests of a
supported contract.
