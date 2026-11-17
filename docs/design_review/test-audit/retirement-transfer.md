# Retirement and transfer

**Interface-checked by source inspection, 2026-11-12; additions dated 2026-11-13 and 2026-11-17.** Use the
[account baseline](README.md#baseline).
ADR-0047 retires obsolete formats without retiring current scientific meaning, source evidence
or independent expectations. Historical test deletion alone establishes no assurance loss.

<a id="refresh-2026-11-17-retirement"></a>

## Refresh of 2026-11-17

**Interface-checked by source inspection, 2026-11-17**, source `fbd3f2a98`
([baseline](README.md#baseline)). No test was run.

| Earlier finding | Status at `fbd3f2a98` |
|---|---|
| DTA-030 | Corrected for the machinery it cited; the same cause recurs as DTA-037 |
| DTA-035 | No longer applicable in the cited files; related production cause is DA-080 |
| DTA-036 | Standing, changed footprint |
| DTA-004, 014 | Not re-examined |

<a id="dta-037"></a>

### DTA-037 — Hand-kept fixture-name lists have drifted from the fixtures that exist, and one test requests a fixture that was deleted

**FP-01, FP-03, FP-06, FP-07; DP-16; A3; companion §2, §6, §8.** Same cause as DTA-030: when
machinery is retired, the lists that named it are not.

Two decisions are keyed on hand-maintained lists of fixture names, and nothing checks that the
names exist:

- `PREPARATION_AFFINITY` (root `conftest.py:10–57`) assigns tests to xdist groups so that tests
  sharing an expensive preparation run on one worker;
- `DB_FIXTURES` (`tests/conftest.py:101–142`) adds the `db` mark, which the qualification
  plugin turns into "native required" (`scripts/qualification_plugin.py:241–243`).

The only guard rejects conflicting groups (`conftest.py:72–75`). After the retirements of
2026-11-14 to 2026-11-16 (`37b8552c1`, `c3f39ba15`, `da32889ae`, `7faa99d40`, `0ba50554b`), a
scan of every fixture definition in the snapshot shows:

- 23 of 37 affinity entries and 11 of 38 `DB_FIXTURES` entries name fixtures defined nowhere;
- six live fixtures (`record_source_*`, `tests/conftest.py:532–567`) depend on `private_source`,
  which no longer exists, and have no consumer. They are themselves `DB_FIXTURES` entries, so
  17 of the 38 are dead in effect;
- `tests/semantic/test_source_routing.py:9–12` requests `domain_default_case`, which is defined
  nowhere. That test cannot set up. No stored result has run it since 2026-11-15.

The converse gap matters more for execution: the fixtures that now hold shared preparation have
no affinity entry. `ddo_kernel` is requested in 35 test modules, the declared serving seed and
case in four each, and none carries a group mark. Every worker that receives one of their consumers builds its own seed per recipe.
The plan defers seed sharing, so that repetition is known; what is new is that the mechanism
meant to limit it does not follow the current fixture graph.

Also from the same cause:

- four support modules have no importer anywhere in the snapshot
  (`tests/semantic/scenario_preparation_support.py`, `primary_formal_fixture.py`,
  `method_dimensions_native_support.py`, `characterization_construction_support.py`);
- the test-system plan's shared-contract row for the implementation snapshot, and its closure
  evidence for DTA-032, describe an interface that was removed with the legacy compiler
  (`1f885d9ed`). This is a note for the plan owner, not a test defect.

**Contrary evidence and what to keep.** Grouping by fixture closure is sound, and because the
`db` mark works through the transitive fixture closure, live roots such as `native_server`
already catch most consumers; the dead names misclassify nothing by themselves.

**Footprint.** Established by a scan of the snapshot. The setup error is shown by source, not
by a run.

## Earlier findings

<a id="dta-030"></a>

## DTA-030 — Corrected for the machinery it cited

**Corrected (2026-11-17, source `fbd3f2a98`).** The template stamp scheme, the committing fixture and the attributed database are gone, and naming, leasing and sweeping share one table (`scripts/native_test_support.py:72–126, 852–894`). The cause, lists and support that outlive what they name, recurs as [DTA-037](#dta-037). Earlier text is in Git at `fbd3f2a98`.

<a id="dta-035"></a>

## DTA-035 — No longer applicable in the cited files

**No longer applicable in the cited files (2026-11-17, source `fbd3f2a98`).** Every cited test file was deleted and no test names the retired run, task-dependency or descriptor vocabulary. Whether each behavior those tests carried was re-expressed was not examined; the plan's transfer item is still open. A related cause now has its primary home in the production account: superseded production code whose only consumers are tests ([DA-080](../audit/boundaries-and-composition.md#da-080)). Its test-side footprint is six files under `tests/core/` (about 3,300 lines) that exercise rendition keying and translation, `tests/ingest/test_renditions.py` and `test_corpus.py`, and the tests of evaluation modules with no production importer. Earlier text is in Git at `fbd3f2a98`.

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

**Status, 2026-11-17, source `fbd3f2a98`.** Standing, changed footprint. An eight-row mapping skeleton from obligations to tests now exists (`docs/plans/test-system-target-design/data-operations-test-alignment.md:617–660`); its completion is gated on the final qualification package. Two points for that mapping: expression checks on spliced SQL and substitute schemas ([DTA-047](execution-and-qualification.md#dta-047)) are expression-level evidence, not native evidence; and a claim that needs no provider, empty-population closure of a source demand, runs only where provider assets are present (`tests/orchestrate/test_source_demand_native.py:188–270`).

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
