# Test system target design

**Status:** Execution in progress; qualification remains open. **Created:** 2026-11-13. **Revised:** 2026-11-13.
This coordinator owns the series' combined target, shared contracts, package queue, rule-change
record and the scheduled disposition of every finding it lists. Companion plans own the detailed
designs and package descriptions. Architecture pages and accepted ADRs remain the authority;
writing this plan authorizes no implementation.

## Outcome and source baseline

Make the test system fit the two loops development depends on, without giving up what makes its
evidence trustworthy. A focused run should pay only for its own scenario. A full run should stop
repeating identical preparation per worker, per case and per call. Every native test should say
what isolation its claim needs, every refusal should prove it reached its guard for the stated
reason, test support should have owners, and the tests of the declared-data-operations (DDO) work
should be shaped by that design's own concepts and survive its cutover.

**Source.** The [design review of the test system target design](../design_review/reviews/design_review_test-system-target-design_2026-11-13.md)
(publication `89440372a`, read at `main` `a5ea7c4dc`, judgment Revise) and its
[supporting document](../design_review/reviews/test-system-target-design/options-and-classification.md).
The review consumed the [test audit](../design_review/test-audit/README.md) at `28b4a53db` and
superseded the 2026-11-12 test review. Section references below (§4.1 and so on) are to the
principal review unless a companion is named.

**Authoring baseline.** `main` `f03170a89`, 2026-11-13. Another session was committing DDO work
during authoring; line citations are as read and may have moved. Companions cite the review for
design reasoning and this baseline for locations that changed after it.

**Evidence status.** Every design statement here is **Proposed**. Source facts are
**Interface-checked by source inspection, 2026-11-13**. Durations quoted from the audit are
**Measured** from stored results on a shared workstation and are orders of magnitude. No package
has a speed target, and no measured speedup is a completion criterion.

**Scope.** Package and root tests, every `conftest.py`, `scripts/native_test_support.py`,
`scripts/test_receipts.py`, `scripts/qualification_plugin.py`, `cli/testing.py`, the pytest
configuration, and two bounded production changes (implementation inputs read once per process and requested-revision expectation loading). Test-only SQL/TAP and private-cohort integration are included.
TS-19 also deletes two production identity helpers that have no caller, unless the DDO identity
package has already removed them; the deletion is coordinated with the DDO session.
Out of scope: a production audit, changes to the DDO plan's own packages, and edits to other
existing plans (operator direction, 2026-11-13).

**Revision input.** The [improvement review](../plan_improvement_reviews/test-system-target-design_2026-11-13.md)
at `823c7fac0` supplies I01–I11. Revision baseline `b1b4a4de0`, source inspected
2026-11-13; nothing in the series is implemented by this revision. The operator selected all
recommendations for integration and directed adoption of pgTAP/pg_prove/pg_virtualenv where
native batching and cohort reuse make infrastructure effective. Shorter focused and full runs
are a major priority; independent evidence and required qualification remain intact.

## Rule changes confirmed by the operator

The review proposed four rule impacts. The operator decided each on 2026-11-13.

| Item | Rule | Decision | Route and timing |
|---|---|---|---|
| RC01 | [ADR-0032](../adr/0032-native-test-deployment-equivalence.md): the head is built once per session with no persistent reuse key; rollback reset rejected | **Accepted.** Narrowed runs reuse a head across sessions under a deployment key; qualification runs build a run-private head; read-only and rolled-back transactions on a shared clone are allowed for claims that need no separate-login commit | A superseding ADR in TS-00, amending D3 (`docs/design/D3-database.md`, native test deployment equivalence), `DESIGN.md` and D9 §4 Tests in the same change. Precedes TS-02 and TS-05 |
| RC02 | Default worker count for narrowed runs (`pyproject.toml`, `scripts/test_receipts.py`, the completed parallel-execution companion's "Retain auto as initial default", the `ci` skill's testing reference) | **Accepted.** One explicit test id runs without xdist workers; *k* ids with at most *k*; path selections keep `auto` | Implemented by TS-04, which also updates the `ci` skill reference. The completed companion is history and is not edited |
| RC03 | DDO contracts companion: "Native checks use the project's working database under its ordinary custody; this plan does not require disposable databases" | **Accepted.** DDO native checks run on clones and seeds of the deployed head under the named isolation classes | An edit owed to the DDO plan's owner. This series does not edit that plan; TS-17 designs to the accepted rule and the item stays listed under [handovers](#handovers-to-other-owners) |
| RC04 | [ADR-0048](../adr/0048-populated-native-scenarios.md): a session-local seed for the serving scenario only; rollback-only transactions rejected | **Accepted.** Seeds become the general mechanism for any recipe that meets the seed premises; the rollback-only rejection narrows to claims that need committed cross-session isolation | A superseding ADR in TS-00 with D3 and `DESIGN.md` amended. Precedes TS-08 |

Additional operator decisions, confirmed 2026-11-13:

| Item | Decision | Route |
|---|---|---|
| RC05 / I02 | **Accepted:** driver-only controls use an infrastructure base; durable-write cases have isolated infrastructure clones. The shared semantic-engine exception and its comparator are removed | TS-00's ADR-0032 successor and D3/DESIGN/D9 changes precede TS-05 |
| RC06 / I09 | **Accepted:** ordinary required selection excludes opt-in provider identities; explicit `ci test --providers-only` requires actual providers and blocks on missing prerequisites | TS-13 updates selection/receipt contracts and the ci testing reference; TS-22/23 preserve separate required provider evidence |
| Tooling direction | **Selected:** pgTAP/pg_prove SQL-family execution and a supported pg_virtualenv private cohort, using existing lifecycle and result custody | TS-24/25; [tooling companion](test-system-target-design/postgresql-tooling.md). Test-only installation changes no production extension prerequisite |

Earlier operator decisions, with their current amended meaning:

- **The deployment key is narrow and verified** (2026-11-13). The review keyed the reusable
  head on the migration chain plus the chain's whole import closure inside the package. At the
  authoring baseline that closure is 531 of the package's 566 modules once imports inside
  functions are followed, because `semantic/contracts.py` is in it and reaches nearly
  everything. Such a key changes on most product commits. The selected key covers the chain,
  the 28 modules it imports at module level, `uv.lock` and the server, and a reused head is
  verified with production's own deployment check once per process that did not build the
  head. The check compares the deployed catalog with the frozen expectations of the head
  revision; it is not equality with a fresh build. The
  [lifecycle companion](test-system-target-design/native-lifecycle-and-deployment.md#deployment-key)
  owns the design.
- **A long-lived process is expected to restart after a code change** (2026-11-13). The
  implementation snapshot is therefore a plain once-per-process read with an explicit override;
  the stat-keyed alternative is not built.
- **A seed holds no unfinished task** (2026-11-13). A seed may hold completed attempts, but no
  task in a claimed or running state, whether or not its lease has expired. The seed build
  checks task status, not only `lease_until`. The ADR-0048 successor (TS-00) states the rule;
  the [isolation companion](test-system-target-design/isolation-and-seeds.md) owns the design.
- **Shared semantic clones** (amended by RC05). Rollback cases expose connections and a
  reader engine forced read-only. Driver connection-lifecycle controls use the infrastructure
  base rather than a writable semantic engine. Tests that actually commit receive an isolated
  clone of the appropriate base. No writable shared-semantic-engine exception remains.

A rule change that execution reveals follows the same confirmation before dependent work.

## Target and foundation assessment

The review's assessment of the foundations stands and is not repeated. What the series reuses,
and must not weaken:

- **The native lifecycle owner.** `PgAdmin` in `scripts/native_test_support.py`: acknowledged
  creation, leases, authenticated unforced drops, policy capture, replay and comparison for
  every clone, and refusal of setup when replay authority is missing.
- **Fresh committed clones with real logins** for every claim that commits, races, cancels,
  notifies or needs a second login.
- **The sealed serving seed** (`tests/semantic/serving_scenarios.py`) as the pattern for a
  committed scenario cloned per consumer.
- **Truthful receipts.** Outcome classes stay distinct, native acquisition context is recorded
  per connection, and a missing prerequisite is `blocked`, never `passed`.
- **Independent expectations.** Identity vectors, hand-authored gold, literal framing and the
  DDO compiler and graph expectations the audit found sound.
- **Cold deployment controls** that execute the real migration chain in every run.

The target, in one view (§4 of the review develops it):

| Responsibility | Target | Companion |
|---|---|---|
| Names, leases, sweep | One naming function yields the name, lease key and sweep rule for every database the tests create | [Native lifecycle and deployment](test-system-target-design/native-lifecycle-and-deployment.md) |
| Deployed head | Built once per deployment key, published by rename, reused by narrowed runs and verified once per process that did not build it; run-private for qualification | same |
| Isolation | Four named classes a test requests: pure, read, rollback, commit; cold deployment fixtures are a separate named kind | [Isolation classes and scenario seeds](test-system-target-design/isolation-and-seeds.md) |
| Committed scenarios | Per-worker sealed seeds keyed by a recipe value and the head; fixtures clone them for consumers | same |
| Support and scenarios | Support modules imported by canonical name; recipe values at the call site; staged builders | [Scenario and support ownership](test-system-target-design/scenario-and-support-ownership.md) |
| Negative and absence evidence | One contract: reach, reason, effect | [Evidence contracts](test-system-target-design/evidence-contracts.md) |
| Evidence class | Provider and controlled claims have different test identities; prerequisites are decided before setup | same |
| Implementation inputs (production) | One snapshot per process with an explicit override | [Implementation snapshot and timing controls](test-system-target-design/implementation-snapshot-and-timing.md) |
| Timing-coupled controls | CPU lifecycle windows derived from constants (timing companion); DDO leases expired through the publisher role (data-operations companion, TS-17 and TS-18) | same; [Data-operations test alignment](test-system-target-design/data-operations-test-alignment.md) |
| Run shape | Workers sized to explicit selections; affinity groups for designated preparation | [Run shape and scheduling](test-system-target-design/run-shape-and-scheduling.md) |
| DDO tests | Support named for the design's concepts; kernel seeds; independent identity and binding evidence; cutover transfer; DDO-12 evidence mapping | [Data-operations test alignment](test-system-target-design/data-operations-test-alignment.md) |

Three credible changes the target is meant to absorb. A new native migration costs one head
build on the next run, then reuse. A new DDO native test requests a kernel seed clone or the
rollback class from support instead of copying a fixture. A new refusal mutation is one more
rolled-back case with its own reason and positive control.

## Shared contracts

These are consumed across companions. Each has one owning package; consumers link to it.

| Contract | What it is | Owner |
|---|---|---|
| Database naming | A function returning, for each kind of test database, its name, lease key and sweep rule. Kinds include the head, build residue, a stale head set aside after failed verification, the session clone, commit clones and seeds, and today's per-process head as an interim kind that TS-02 removes | TS-01; TS-02 and TS-08 add their kinds through it |
| Run scope | `CORPUS_CI_RUN_SCOPE`, set by the managed route to `qualification` or `narrowed`; absent means narrowed. Receipts record the head name and whether it was built, reused and verified | TS-02 |
| Head acquisition | Replacement-aware handle whose clone operation verifies the first useful clone before effects; no dependency on a session-clone fixture | TS-02 early acquisition slice |
| Implementation snapshot and override | `current_implementation()`, `implementation_override(...)` and `implementation_overridden()` in production; the last lets a seed build refuse to run under an override | TS-03 |
| Isolation-class fixtures | In the package `tests/conftest.py`: `native_read`; `native_rollback` (case connections, principal connections, and a reader engine whose sessions are forced read-only); the `commit_*_engine` fixtures that replace the `semantic_*_engine` family; and infrastructure engine/rollback/isolated fixtures for driver-only consumers; no writable shared-semantic-engine exception. The session clone (`ci_test_<pid>`) is owned here and created lazily. Cold deployment fixtures (`semantic_bare_engine`, `semantic_database_at`) are a separate named kind outside the four classes | TS-05 |
| Recipe value | A frozen, hashable, data-only description of a scenario, visible at the call site; the key for seeds (with the head). Pure preparation uses its preparation-stage projection instead of the whole scenario recipe. Each recipe type registers exactly one builder in a support-level registry, while compositions and patches are resolved locally by that builder, not a global registry. An implementation override is never a recipe field | TS-06 |
| Stage outputs | Frozen results of each builder stage; the seed boundary is the last stage before a claim | TS-07 |
| Seed operation | In the lifecycle owner: build once per worker with the recipe type's registered builder, check, seal, clone. A seed may hold completed attempts but no unfinished task (none claimed or running, whatever its lease). Seeds are requested only through fixtures, which reach the operation as `scenario_seeds.commit_clone(recipe)` and `scenario_seeds.rollback_family(recipe)`; no test body calls it. `database()` gains an optional seed origin for receipts | TS-08 |
| Refusal contract | Reach, reason and effect, with a small helper that compares the driver's diagnostic tuple | TS-09 |
| Provider selection and prerequisites | Separate opt-in provider marker and prerequisite checks; persisted provider-only selection through retry/coverage; aggregated missing reasons and item-bound native observations | TS-13 |
| DDO support | Declaration builders, `KernelRecipe`, `admit_kernel`, demand helpers and an interim per-test kernel fixture (TS-17); the `ddo_kernel(recipe)` fixture, which is `scenario_seeds.commit_clone(recipe)` exposing the purpose engines of that clone, and `expire_lease` (TS-18); `WireCheckedStorage` and the binding case table (TS-20) | TS-17, TS-18, TS-20 |

SQL/TAP family selection, host acquisition and result custody are owned in the
[tooling companion](test-system-target-design/postgresql-tooling.md#shared-contracts).
They compose these contracts; they do not replace actual-purpose observations or lifecycle ownership.

## Package queue

The table owns execution state. Row order is one useful route; the dependency column is what
binds. A package is not automatically one worker's assignment.

| Package | Delivers | Needs | Findings | State |
|---|---|---|---|---|
| TS-00 | Baseline reconciliation; superseding ADRs including infrastructure RC05, with design sections amended | Operator decisions above | RC01, RC04, RC05 | Delivered; ADR lint passed |
| TS-01 | One naming, lease and sweep authority; superseded lifecycle machinery removed; sweep skips residue still in use | — | DTA-030, F01, F04 | In progress |
| TS-02 | Keyed, verified head deployment; run-private heads for qualification; receipts record the head | TS-00, TS-01 | DTA-024 | Not started |
| TS-03 | Implementation snapshot with override; fixtures moved off monkeypatched readers | — | DTA-032 | In progress |
| TS-04 | Workers sized to explicit selections | — | F05, RC02 | Delivered; targeted checks passed |
| TS-05 | Isolation classes, infrastructure base and commit fixture migration | TS-00, TS-01, TS-02 acquisition slice | (enables DTA-025, DTA-031) | Not started |
| TS-06 | Support modules and import rules; recipe values and their builder registry replace fixture-name overrides; the statistics-pack fixtures merged into one support owner | — | DTA-009 | In progress |
| TS-07 | Staged builders; focused consumers request only what they read; preparation-specific recipe memo | TS-03 override scope, TS-05, TS-06 | DTA-018 | Not started |
| TS-08 | The seed operation; the serving seed migrated onto it | TS-00, TS-01, TS-02 acquisition slice, TS-03, TS-06 | F03 | Not started |
| TS-09 | Refusal contract helper and the named weak sites | — | DTA-001 | In progress |
| TS-10 | Rollback families on seeds; pure SQL checks in the read class | TS-05, TS-07, TS-08, TS-09 per family | DTA-025 | Not started |
| TS-11 | Commit-class consumers clone recipe seeds | TS-07, TS-08 | F03 | Not started |
| TS-12 | Affinity by distinctive shared fixture names and consumer-qualified local fixtures; deduplicate equal groups | — | F02 | In progress |
| TS-13 | Provider-only selection, controlled identities and aggregated prerequisites before setup; complete receipt/retry projection | — | DTA-028, DTA-018 (skips) | Not started |
| TS-14 | Preservation assertions, redaction-order control, exact task state for stdio modes | TS-08 for the two-run comparison | DTA-006, DTA-027, DTA-016 residue | Not started |
| TS-15 | One owner of the primary-layer assembly | — | DTA-029 | In progress |
| TS-16 | CPU lifecycle controls without real grace waits or private initializer writes | — | DTA-026 | Delivered; targeted checks passed |
| TS-17 | DDO support modules, declaration builders, kernel recipes, `admit_kernel`, an interim per-test kernel fixture | TS-06 | DTA-031, DTA-009 (DDO) | In progress |
| TS-18 | Kernel/source-function seeds, forged-graph rollback family and deterministic lease expiry | TS-05, TS-08, TS-09 per refusal family, TS-17; TS-07 for the two original recipes | DTA-031, DTA-018 (forged graph) | Not started |
| TS-19 | Literal vectors for the contextual product identity; uncalled helpers removed | — | DTA-033 | In progress |
| TS-20 | Wire-checked double; authored compiled results and bounded protected native admission | TS-05, TS-08, TS-17, TS-18 binding seed slice | DTA-034 | Not started |
| TS-21 | Cutover transfer of tests tied to retired machinery | TS-07, TS-17, and each retiring DDO package | DTA-035 | Gated on DDO |
| TS-22 | DDO-12 evidence mapping, as a table in this series' companion, and the provider run | TS-13, DDO-12 | DTA-036 | Gated on DDO |
| TS-24 | SQL-family batching with pgTAP/pg_prove, stable case identities and receipt integration | TS-04, TS-05, TS-08, TS-13 selection/provenance slice | Tooling direction, I07/I09 | Not started |
| TS-25 | Supported private PostgreSQL cohort through pg_virtualenv; explicit endpoint and host context | TS-01, TS-05, TS-13 context slice; TS-24 for SQL consumers | Tooling direction, I02 | Not started |
| TS-23 | Assembled review, final-source qualification, handoff | All non-DDO-gated packages including TS-24/25 | — | Not started |

**What depends on what, by capability.**

- TS-01 comes before any new kind of test database, so one rule recognizes every name. TS-02 and
  TS-08 both add kinds.
- TS-03 is small and independent. It is scheduled early because it removes work from every
  interpretation context, and because its override is what lets a seed builder refuse to run
  under patched implementation inputs.
- TS-02 with TS-04 removes the fixed floor of a focused native run. TS-05/08 consume TS-02's acquisition slice; the full head-reuse consumer work need not block that slice.
- TS-05, TS-06 and TS-17 are the foundation the DDO tests need. They should land before DDO-06
  adds more native tests, so those start in the target shape.
- A family moves in TS-10 only together with its refusal contract from TS-09. The two packages
  proceed family by family.
- TS-09, TS-13, TS-15, TS-16 and TS-19 are independent of the lifecycle work and of each other.
- TS-21 and TS-22 close inside the DDO work. Their gates name DDO package ids; current DDO state
  is read from the [DDO coordinator](declared-data-operations_2026-11-12.md), never copied here.

**Shared editing surfaces.** `scripts/native_test_support.py` and the package `tests/conftest.py`
are touched by TS-01, TS-02, TS-05 and TS-08; one owner should hold them in sequence.
`tests/semantic/native_record_fixtures.py` is touched by TS-03, TS-06, TS-07 and TS-11.
`tests/semantic/test_data_operation_storage.py` belongs to the paused DDO execution; TS-17
and TS-18 coordinate with it before moving helpers out.

## Finding disposition

This table is the single owner of scheduled disposition for these findings. The review's
Deferred rows and the audit link here. Dispositions use the binding's vocabulary.

| Finding | Package | Disposition | Closure evidence |
|---|---|---|---|
| [DTA-001](../design_review/test-audit/evidence-and-discrimination.md#dta-001) | TS-09 | Open | Each named site pins reach, reason and effect; removing one guard fails exactly its case, by reasoning over the guard |
| [DTA-006](../design_review/test-audit/evidence-and-discrimination.md#dta-006) | TS-14 | Open | Each named test fails for a wrong implementation it accepts today |
| [DTA-009](../design_review/test-audit/support-structure.md#dta-009) | TS-06, TS-17 | Open | No import from a `test_*` module; no relative import from a non-package directory; no `private_source_options` override or `callspec` read |
| DTA-016 residue | TS-14 | Open | The three non-complete stdio modes assert their exact task state |
| [DTA-018](../design_review/test-audit/execution-and-qualification.md#dta-018) | TS-07, TS-13, TS-18 | Open | Named consumers request only what they read; no body-level provider skip follows scenario fixtures; the DDO forged-graph family registers only the demand it reads |
| [DTA-024](../design_review/test-audit/execution-and-qualification.md#dta-024) | TS-02 | Open | Two consecutive narrowed runs name one head and the second records reuse and verification; an unnarrowed run names a run-private head; no per-process head remains |
| [DTA-025](../design_review/test-audit/execution-and-qualification.md#dta-025) | TS-10 | Open | Every family in TS-10's scope list is migrated or holds the disposition stated there; each migrated family shows one seed and one family clone per worker; every case asserts positive control, exact reason and absence; no case body commits |
| [DTA-026](../design_review/test-audit/execution-and-qualification.md#dta-026) | TS-16 | Closed, 2026-11-13: 9af8d67168a94b3b866715acdde07d42 (28/28), post-type affected controls 0afe6c7e8901433b922ca8d1dff7ba66 (4/4) | No literal tied to five seconds; one value assertion; no writes of `_initializer` or `_initargs` |
| [DTA-027](../design_review/test-audit/evidence-and-discrimination.md#dta-027) | TS-14 | Closed, 2026-11-13: 7a25573b85bb4579b46aef1695a9fb88 (2/2) | Independently sized stdout/diagnostic windows start inside the raw credential; exact masked output distinguishes redact-before-clip |
| [DTA-028](../design_review/test-audit/support-structure.md#dta-028) | TS-13 | Open | No body reads an asset variable to choose its evidence class; receipts record the prerequisite |
| [DTA-029](../design_review/test-audit/support-structure.md#dta-029) | TS-15 | Open | The seven copies call one owner with an explicit digest policy |
| [DTA-030](../design_review/test-audit/retirement-transfer.md#dta-030) | TS-01 | Open | No source names `cs_tpl_` or `STAMP`; every created name matches a sweep rule |
| [DTA-031](../design_review/test-audit/execution-and-qualification.md#dta-031) | TS-17, TS-18 | Open | One `admit_kernel`; DDO native tests request a named class or a cold deployment fixture; one kernel seed per recipe per worker |
| [DTA-032](../design_review/test-audit/execution-and-qualification.md#dta-032) | TS-03 | Open | No file read after the first per process in context preparation; no test monkeypatches the readers or `_semantic_implementation_digests` (one counting control wraps the single acquisition function); the admission refusal keeps its control |
| [DTA-033](../design_review/test-audit/evidence-and-discrimination.md#dta-033) | TS-19 | Open | A literal vector fails for a changed domain tag, nesting or local qualification; the uncalled helpers are gone |
| [DTA-034](../design_review/test-audit/support-structure.md#dta-034) | TS-20 | Open | Routing tests use the wire-checked double; one case table runs through both binding paths on PostgreSQL |
| [DTA-035](../design_review/test-audit/retirement-transfer.md#dta-035) | TS-21 | Open, gated | Per retiring DDO package: no test source names the retired mechanism; each deletion is named in a commit |
| [DTA-036](../design_review/test-audit/retirement-transfer.md#dta-036) | TS-22 | Open, gated | The companion's mapping table names discriminating identities, or states the gap, for each DDO-12 obligation row and is handed to the DDO owner; the provider run shows provider identities passed or blocked |
| F01 (review) | TS-01 | Open | One derivation serves lease and sweep; `committing_db` removed |
| F02 (review) | TS-12 | Open | Each designated preparation runs on one worker per run |
| F03 (review) | TS-08, TS-11 | Open | The builder of each recipe TS-11 lists runs once per worker; the serving seed uses the common operation |
| F04 (review) | TS-01 | Open | A sweep that meets connected residue completes and reports the skip |
| [PostgreSQL review F01](../design_review/reviews/design_review_postgresql-tooling_2026-11-13.md#f01--ambient-proveharness-inputs-can-alter-execution) | TS-24 | Open; target amended 2026-11-13 | Explicit prove/harness inputs ignore conflicting ambient configuration; unexpected psql exit cannot qualify selected cases |
| F05 (review) | TS-04 | Closed, 2026-11-13 | Real one-ID receipt fd2b0feb1cea417cb05b5ce4cbf81198 requested/actual zero; capped three-ID receipt 7e09a210f721489e90d3972044ca2c67; root CLI integration f725721fa9624957973caccff0a6176c passed 18/18 |

DTA-001–023 as they stood on 2026-11-05 remain with the completed
[test audit resolution](test-audit-resolution_2026-11-05.md); the rows above cover current-source
manifestations.

## Improvement-review integration

All recommendations from [the review](../plan_improvement_reviews/test-system-target-design_2026-11-13.md)
are selected for planned implementation; each remains **Open**, not verified closure. This table
is their single scheduled disposition owner, alongside the existing DTA/F table.

| Review item | Packages | Closure behavior (Open) |
|---|---|---|
| [I01](../plan_improvement_reviews/test-system-target-design_2026-11-13.md#I01) | TS-02, TS-05, TS-08 | First useful clone verified once; selected inherited artifact resolution avoids unrelated payload reads |
| [I02](../plan_improvement_reviews/test-system-target-design_2026-11-13.md#I02) | TS-00, TS-01, TS-05 | Infrastructure-only selections acquire no semantic head; durable writes isolated |
| [I03](../plan_improvement_reviews/test-system-target-design_2026-11-13.md#I03) | TS-06, TS-07 | Later-stage variations share pure preparation; true preparation changes invalidate |
| [I04](../plan_improvement_reviews/test-system-target-design_2026-11-13.md#I04) | TS-03, TS-07 | Nested overrides bypass affected cache reads/writes and preserve ordinary warm state |
| [I05](../plan_improvement_reviews/test-system-target-design_2026-11-13.md#I05) | TS-06, TS-12 | Imported shared fixtures grouped correctly; duplicate equal groups accepted |
| [I06](../plan_improvement_reviews/test-system-target-design_2026-11-13.md#I06) | TS-06 | Both CLI imports deferred; cold non-CLI collection avoids registry activation through conftest |
| [I07](../plan_improvement_reviews/test-system-target-design_2026-11-13.md#I07) | TS-09, TS-17, TS-18, TS-20 | Authentic forged-graph rollback controls; stable binding source functions installed once per worker |
| [I08](../plan_improvement_reviews/test-system-target-design_2026-11-13.md#I08) | TS-20 | Independent full results and native accepted/refused envelopes discriminate selection errors |
| [I09](../plan_improvement_reviews/test-system-target-design_2026-11-13.md#I09) | TS-05, TS-13, TS-18, TS-22, TS-23 | Provider-only scope survives retry/coverage; aggregated reasons and item native evidence retained |
| [I10](../plan_improvement_reviews/test-system-target-design_2026-11-13.md#I10) | TS-01, TS-02 | Construction-key dependencies exclude unrelated orchestration; build-name lease protects publication |
| [I11](../plan_improvement_reviews/test-system-target-design_2026-11-13.md#I11) | TS-06 | Minimal type dispatch; compositions and patches owned locally |

TS-24/25 carry the later tooling direction. Preserve the source review's evidence limits;
no benchmark quota or numerical speedup claim follows. Existing receipts can show eliminated
acquisitions and reused setup. Investigate duration only where it would change a consequential
remaining choice. TS-23 still owns final-source functional/provider/nonfunctional coverage and
assembled review. Its position after appended IDs is dependency order, not renumbering.

## Candidates, rejected options and open premises

**Candidates kept, not scheduled.** Each has a trigger; none is a completion obligation.

| Candidate | Trigger to schedule |
|---|---|
| Seeds shared across a run's workers (old D7) | Full-run receipts after TS-11 show per-worker seed builds as a material share of setup |
| Seed consumers reopen the persisted release through the archive reader instead of re-preparing | A read-only consumer family whose setup is dominated by preparation after TS-11 |
| Commit-class consumers of one recipe seed grouped onto one worker | Full-run receipts after TS-11 show per-worker builds of one recipe's seed as a material share of setup |
| Math and CPU process pools coordinated with xdist's worker count. This is a real shared-capacity concern, not a rejection, and it needs measurement before any design | A full run showing oversubscription |
| Long single tests dispatched first (G3) | A full run whose tail is one late long test |
| Argument screening without a second interpreter (W3); deferred collection-time loads (C1); controlled PDF builder loaded once (S3); concurrent cold-process children (P1) | Any of them, when a focused run's fixed overhead matters after TS-04 |

**Rejected, with the review's reasons** (supporting document, Part A): dependency-based test
selection; a disk cache of prepared releases; fewer Hypothesis examples for focused runs;
subtests in place of parametrized cases; in-process substitutes for the installed CLI;
`pytest-postgresql` as lifecycle owner; one maintenance session per clone (about 0.02 s per
clone, so no time rationale); a run-scoped head with controller-owned cleanup (replaced by the
keyed head).

Every other Part A option keeps the disposition the supporting document gives it; this plan
does not restate or change them.

**Open premises.** Each is settled inside the package that consumes it, not by a probe now.

| Premise | Settled in | If it fails |
|---|---|---|
| `ALTER DATABASE … RENAME` publishes a build and keeps the OID-keyed ownership stamp | TS-02, first build | Build under the final name behind the build lock and seal last; the lifecycle companion states the rule for an unsealed database found under a head name |
| No command writes implementation files and then re-reads them in the same process | TS-03 | A generator that does clears the snapshot after writing |
| A read-only transaction refuses `CREATE FUNCTION`, including into `pg_temp` | TS-18 | If it does not, the identity-native checks may use the read class instead of rollback |
| Sealed kernel rows carry no database or role names | TS-18, first kernel seed clone | The affected recipe stays on a per-test build |
| Which domain-case prefix is reusable | TS-11, inspect consumed stages and dependencies; profile only if it changes the boundary | Use the smallest sufficient stable prefix without making benefit measurement a gate |
| A family's refused operation does not check a task lease | TS-10, per family | The family stays commit-class on a seed |

## Handovers to other owners

Not this series' work; listed so they are not lost.

- **DDO plan owner:**
  - RC03 and TS-05/06/17 readiness, TS-21/22 consumption and retirement owners are already
    recorded by the DDO coordinator and contracts companion. Link their package obligations;
    do not copy status or resume that paused execution.
  - The edit to the DDO-12 obligation table. TS-22 delivers the evidence mapping as a table in
    the [data-operations companion](test-system-target-design/data-operations-test-alignment.md);
    adding it to the DDO plan's table is the DDO owner's edit at DDO-12 time.
  - Deletion of the uncalled identity helpers `product_identity` and `subject_identity`. TS-19
    deletes them unless the DDO identity package has already done so; the two sessions agree
    which commit carries it. DTA-033 closes only when they are gone.
  - Its findings-table rows for DDO-CA-01, 02 and 04 predate tests that now exist.
  - `admit_data_operation_release` verifies the native deployment twice per release.
  - DDO-06 owns `max_active_stage_runs`; DDO-09 removes copied `reused_task_id` meaning and
    DDO-11 retires the physical storage. TS-21 consumes those owners rather than requesting new ones.
  - Assurance gaps against its own verification text: overlapping publication with differing
    intents, helper-body and inherited-value change locality, invalidated support recovered
    through a real consumer, graph example sets.
- **Broad audit:** production prepares an interpretation context per span and per item
  (`methods/math/source_context.py`, `methods/math/native.py`); TS-03 removes the repeated reads
  but the loop shape is production's to assess.

## Completion

The series is complete when every non-gated package is delivered with its consumers migrated
and its superseded machinery removed; the final source passes `uv run ci test` and
`uv run ci check` with a run-private head and explicit provider-required selections covering applicable provider obligations separately; missing selected providers remain blocked; an assembled design review of the changed lifecycle
has been held (TS-23); and the gated packages are either delivered or carried, with their
gates, into the DDO work. Targeted checks run per package during implementation; the integrated
run happens once at complete scope (AGENTS.md). Receipts that show a head reused or one seed per
worker are functional closure evidence. They are not speed claims.

**Current work:** TS-01 native validation and TS-03 final consumer checks, plus the operator-authorized native PDF prerequisite repair. Next: TS-02 acquisition foundation, then TS-05/08 consumers as their other prerequisites become available.

## Revision publication · 2026-11-13

This revision integrates I01–I11 and the selected PostgreSQL tooling direction; it implements
no package and closed no DTA/F/I finding at publication `08dfd8d83`; the execution checkpoint below owns subsequent progress.

- **passed:** `just turn-end`, `git diff --check`.
- **passed:** `uv run ci docs check`, initial publication result
  `c4768dba59644b45ba16964d7bcd5402`, 1,245 canonical pages and zero link errors.
- **not_run:** `uv run ci test`, `uv run ci check`, native/provider probes and benchmarks;
  only plan/review navigation and checkpoint documentation changed.

## Execution checkpoint · 2026-11-13

TS-00 delivered ADR-0101/0102 and governing D3/DESIGN/D9 target updates. The one-time legacy
authentication query found no legacy candidates; the baseline PgAdmin sweep returned no drops.
ADR lint passed `709f24d15cd147ecbb2fc493a357e60a`; initial stale-index refusal
`248547f59d57400886694bca4b5f774a` is retained and resolved by index regeneration.
Doctor passed `5f17c96c61d14541aed2d3e43624222d`. No deployment, activation or frozen archive edit.

TS-04 supervisor controls passed 49 targeted tests, `c53a42bca53644149afa32d60cdf4c1d`.
A real single-ID run recorded requested/actual zero (`fd2b0feb1cea417cb05b5ce4cbf81198`);
a real three-ID run recorded auto/cap-three/actual-three (`7e09a210f721489e90d3972044ca2c67`).
Root CLI provisional facts/help integration passed 18/18 affected checks, `f725721fa9624957973caccff0a6176c`.
Other packages remain open; these bounded results are not TS-23 qualification.

TS-16 passed 28 controls (`9af8d67168a94b3b866715acdde07d42`) and four post-typing affected
controls (`0afe6c7e8901433b922ca8d1dff7ba66`). Typing initially failed
`7525c9df9b314dc488b50d65b3f5993a`; owning fixes passed
`8b1df76ece564c60935d2d9317822dc8`. This is not the final repository gate.

**Authorized prerequisite repair, operator 2026-11-13:** fix the native
`ops.retain_pdf_original` recipe-digest ambiguity and qualify a normal forward successor, without
resuming DDO execution or deploying to the persistent working database. Failed guard-family
run `36b9f71e784440c8be83ef6d0f68ecf6` retained: 18 passed, 50 setup failures at that guard.
[Repair evidence](../design_review/evidence/2026-11-13_test-system-pdf-guard-repair/README.md)
owns preview/candidate/registration custody; no existing frozen migration bytes are edited.
The first successor passed preview/candidate/registration and three exact guard/forward-deployment
controls (`e0b76cad67e1435199d8009c1147d9a3`). The next native batch
`e67fcd551fcc4a138b2d3d0ec24b6cdd` failed with 3 passed and 22 setup failures at
`check_pdf_build`'s reference to removed `data_derivation.task_id`; its adjacent repair uses
the current `producer_task_id` in a separate forward successor.

**DDO alignment, operator 2026-11-13; Interface-checked by source inspection.** The DDO
transition remains the baseline. Repairs and test migrations must follow its current model,
not restore the prior architecture to satisfy callers. The PDF reuse query selects the original
published task and associates it with the derivation's immutable producer task. Adoption's
current publication fence remains separately authenticated by retain/adopt/publish. Current
reuse still requires `ddo_support_valid`; readable historical receipts do not imply currently
admissible support. Request/generation/intent and custody checks remain with those production
owners. TS-21/22 remain gated; this repair resumes no DDO package or cutover.

TS-01's pure naming/sweep controls passed 28 tests (`201bb6d3dac94f6cba93b63f97197b08`);
native affected-consumer qualification remains open behind the PDF prerequisite. TS-03's
snapshot controls, including concurrent cold acquisition and nested override/cache behavior,
passed (`962c709485484712afd08df5c0faa649`); affected native consumer qualification remains
open. The generated typed-column IDs were reconciled through their generator after confirming
preexisting source/ID drift; no physical model change was made. Types passed
`a23e8d279d0f467fa778242b4f893e2d` and scoped lint passed
`017d334e34e6432d96f5ab8390e0454f`; these are bounded checks.

An assigned-work CLI defect in evidence finalization is repaired at its owning layer: invalid
or missing requested records now refuse diagnostically before any record is rewritten. Three
targeted controls passed (`a130b37bfaed44b6b9740ce7634bd5d5`); failed original invocation
`51102baee5474ef1af78229b6d8e8078` is retained. TS-06/15 support integration is in progress.

TS-12's table now covers shared statistics preparation, consumer-qualified HanLP/run-scope
preparation and the existing math closure. Actual isolated two-worker controls established
shared imported preparation once, unrelated same-name exclusion and unchanged math grouping.
Result `74551fe43d8b44708710e63db9bf211d` passed three and failed one diagnostic-stream
assertion; the correction reads both pytest streams and passed its exact retry
`8d36fdb1d6e44ccb99b8e6d96c53be7b`. Actual designated-consumer receipts and final integration
remain open. TS-19's pure contextual literal vectors passed the full identity module,
48/48 (`244f50becd69430793b5e485a9d5f179`); deployed-function/source-text controls and helper
retirement remain open. TS-17 DDO support extraction is underway against the current model.

TS-14's stdout/diagnostic redaction-order controls passed two identities
(`7a25573b85bb4579b46aef1695a9fb88`). Initial test-authoring arithmetic failure
`fc06ad71376a430d99c3ed1c2f706d8a` is retained (1 passed, 2 failed) and corrected using
the explicit raw clipping offset. Other TS-14 preservation/task-state work remains open.
The scoped PostgreSQL target review is published with a bounded diagnostic reconciliation;
its F01 is scheduled in TS-24, not a replacement test-system qualification.
