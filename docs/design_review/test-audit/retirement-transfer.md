# Retirement and transfer

**Interface-checked by source inspection, 2026-11-12.** Use the [account baseline](README.md#baseline).
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

The consequence is maintained and tested surface for behavior with no producer, and a divergent
copy of a shared fixture that will not follow changes to the original. The design-stage
guidance in AGENTS.md treats removal of superseded machinery as part of delivering its
replacement. Uncertainty: databases with the old prefix may still exist on the development
cluster, which would give the sweep branch a remaining cleanup purpose until they are gone.
A lead outside test scope, not assessed here: the legacy `python/corpus-structure/alembic/`
chain lost its reader in the same commit and no current reference to it was found.
Evidence folders themselves are retained by standing
operator rule and are not in question.

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
