# Test domain model, execution, and managed test review

**Plan-improvement review · 2026-11-18.** Retain the TDM series and revise its entry,
preparation identity, fixture resolution, and acceptance design. Add a bounded test review
view to `ci`. Build it from managed receipts. The tested behavior of `pytest-json-report`
supports a conditional export use case. Its default session document is unsuitable for
determining managed attempt completion or qualification.

## Baseline and scope

Reviewed the [TDM coordinator](../plans/test-domain-model-and-execution_2026-11-17.md) and all
five companions at plan revision `98f638bc9` and checkout `aea554e5c`. The plan's revised source
baseline is `12f57dc4d`. Relevant subsequent changes include the N13 fixture repairs, contextual
product-cut acquisition, external packet dispatch, predicate interval resolution, and the grammar
comparison controls. Two pre-existing PDF test edits and the supplied, still-untracked
`pytest-json-report.md` guide were visible in the working tree. The PDF edits are context, with
no test evidence attributed to them. The standalone reporting probe used the pinned package
versions directly.

The [source review](../design_review/reviews/design_review_test-domain-model-and-execution_2026-11-17.md),
its dispositions, the test-assessment companion, and the [baseline re-reads](../design_review/evidence/2026-11-17_test-plan-authoring/README.md)
provide the starting judgments. This review traced the package tests, affected root scripts,
native deployment and scenario lifecycle, PDF/executor/host seams, and managed test reports.
It read decisive consumers and explored adverse cases without a fresh full-suite census.
Relevant contracts include [ADR-0101](../adr/0101-verified-test-deployments.md),
[ADR-0102](../adr/0102-reusable-native-scenario-seeds.md),
[ADR-0131](../adr/0131-model-owned-postgresql-programs.md), and
[ADR-0069](../adr/0069-cli-operations-custody.md). RC07–RC11 retain their accepted standing.
Recommendations below are **Proposed**. Source observations are **Interface-checked by source
inspection, 2026-11-18** unless a specific retained run or probe is cited.

<a id="I01"></a>

## I01 — Restore evidence by failure boundary and owner

**TDM-00, TDM-01, TDM-14, TDM-18.** TDM-00's changed-file re-read is a useful starting point.
Extend it to affected consumers and retained failure receipts. A helper or generated boundary can
change the result of an untouched test. For example, the post-baseline TDM entry must account for
the later DDO repairs to descriptor, source-proof, binding and authorization fixtures. Managed
coverage across the N13 attempt `be66da57a0a44cf3b6aa420cb7e77c37` and three exact retries
reports 146 observed of 148 selected identities, with two unresolved. The attempts differ in
source and context. The last retry, `5008e8bb6809433ab620a80dea585857`, reached native
admission for both unresolved cases. Compare each authored invalid attachment with its positive
baseline and the predecessor/current guard before concluding that the SQLSTATE is stale or that
behavior regressed. DDO retains disposition of those product obligations. TDM uses them to test
whether its refusal guidance and review workflow preserve the claim. [DDO checkpoint](../plans/declared-data-operations_2026-11-12.md#generated-ddo-acquisition-settlement-and-inspection--2026-11-18)

The TDM-01 claim that collection gives a complete structural setup inventory overstates pytest's
collection boundary. TDM-15's own library analysis says missing named fixtures can fail only
during setup. Use managed collection for identities and import errors. Use targeted setup
execution for known repaired dependency paths and dynamic fixtures. A bounded pytest
`--setup-plan` inspection is an optional aid for static resolution if the repository's
setup hooks remain harmless in that mode. It cannot establish fixture-body success. Keep a
separate qualification outcome for each route. This also lets TDM-00 route prerequisite
handoffs early and reserve TDM-18 for reconciling closure. **Principles:** FP-05, FP-06,
DP-21/22. **Closure:** the two undefined-name patterns, stale generated-program references and
context-managed fixtures are each either verified at the boundary they claim or routed with a
specific remaining obligation. A successful collection cannot be counted as a setup pass.
[Entry and repair packages](../plans/test-domain-model-and-execution_2026-11-17.md#tdm-01)

<a id="I02"></a>

## I02 — Key the deployed program and the effective native role policy

**TDM-06 and TDM-13 · DTA-038/039 · RC07.** Land the correct migration-chain authority in the
first native harness slice, before interpreting reuse data. The build reads
`semantic.migrations.ALEMBIC_DIR` while the key caller still names `semantic_alembic`. Use the
production owner for the selected chain and its declared executed bodies. Follow module-level
package imports and function-level imports of executed revision bodies within the accepted
boundary. A digest-pinned artifact can be represented by its verified declaration, provided the
loader rejects altered bytes and installed-clone equivalence remains the authority on reuse.
Hash unpinned inputs by content. A path, timestamp, or currently installed revision ID alone
cannot express actual construction inputs. [Key caller](../../scripts/native_test_support.py) ·
[Preparation proposal](../plans/test-domain-model-and-execution/preparation-identity.md#tdm-06--the-head-key-covers-what-the-build-runs)

Enlarge the proposed role facts beyond login, inheritance, and direct membership. Use a
structured observation of the capability flags governed by the semantic-principal provisioning
contract, including superuser, database creation, role creation, replication and RLS bypass,
plus effective membership identities and relevant SET/INHERIT/admin options. Use the existing
catalog model and the clone equivalence check where their responsibilities match. A role gaining
`BYPASSRLS` can preserve its OID, name and direct memberships while changing behavior. Hashing
provisioning source would also invalidate heads on edits before any host state changes.
Avoid both an exhaustive transitive package walk and a second mutable list of role semantics.
**Principles:** FP-04, FP-07, DP-09, G5/G6. **Closure:** exercise an executed body change, a
wrong artifact digest, an unpinned change, and role-policy changes with other determinants held
fixed. Validate actual head replay with frozen expectations and preserve failed-key replacement.
Test policy drift on an owned clone or by changing the typed observation in a unit case.
[Provisioning contract](../../python/corpus-structure/src/corpus_structure/core/db/host_bootstrap.py)

<a id="I03"></a>

## I03 — Make published-capture reuse a consumer contract

**TDM-03, TDM-07–10, TDM-12 · F06, DTA-040/041 · RC08/11.** Keep the proposed shared PDF
stream protocol above the existing `certified_reply` emitter. It owns request interpretation,
the preparation entry and acknowledgement, cancellation, results and certification. Put the
controlled producer's content in the recipe and let the builder supply the workspace binding.
Then make the fixture route express whether it consumes a completed capture or may make a new
capture/transform claim. An unexpected write to the sealed directory must expose a fixture
classification error. A `PermissionError` discovered mid-journey is an unreliable way to decide
which route a consumer needed.

Pilot with one post-capture consumer and one consumer that registers a second original or
executes a new demand. Only move the larger consumer list after the two routes prove the
ownership split. Keep preparation memo entries live only for the lifetime of a valid binding,
and keep the completed capture's filesystem reservation live while authenticated clones can
read it. Forcing a writable copy of every frozen workspace would hide misclassification and
reintroduce preparation. Making every consumer run the worker would discard the reuse benefit.
The production custody model continues to own its absolute paths. Changes to that model belong
with its production owner unless the pilot demonstrates a required correction.

The proposed executor collaborator is a coherent boundary if it preserves the order of
transaction, savepoint, claim and settlement effects. Include the N13 external-packet route,
which reaches native packet custody before Python port resolution, and an uncertain settlement
with reconciliation in the selected real/controlled comparisons. Keep existing provider and
live-peer controls responsible for what those boundaries actually observe. **Principles:** FP-01,
FP-02, DP-10/19, H1. **Closure:** two eligible clones share the published capture without a
converter call, while the writable route uses its own binding. The authentic control reaches
preparation acknowledgement and certification on the production protocol, and the capture
fixture has an explicit refusal when a post-capture consumer requests work outside its contract.
[Preparation ownership](../plans/test-domain-model-and-execution/preparation-identity.md#tdm-08--a-seed-stage-for-the-completed-capture) ·
[Boundary design](../plans/test-domain-model-and-execution/controlled-boundaries-and-seams.md#tdm-09--the-pdf-stream-protocol-and-the-controlled-converter)

<a id="I04"></a>

## I04 — Derive preparation from resolved fixtures

**TDM-15 · DTA-037 · RC09.** Put affinity metadata on the defining fixture and derive marks
from the definitions applicable to the collected item. The proposed global registry keyed by
fixture name would reject legitimate same-name fixtures in sibling scopes or select metadata
from the wrong definition. Pytest's resolved fixture sequence represents local overrides and
can also include an override that requests its parent. Use an item-level error for conflicting
preparation requirements. Emit one resolved xdist group for a grouped item and define how an
explicit group interacts with the inferred group. Dynamic `getfixturevalue` is outside the
static closure. When dynamic setup needs affinity, make its prerequisite explicit in the
owning fixture rather than infer from an unresolved name.

The installed pytest 9.1.1 fixture information exposes the applicable definitions but is an
internal boundary. Keep any access to it in one narrow version-checked adapter. Compare with
a fully public route using explicit declarations on tests whose fixture resolution cannot be
represented reliably. Keeping the current name tables leaves the original drift mechanism.
**Principles:** FP-02, FP-05/06, DP-15. **Closure:** sibling names do not collide, overrides and
parent access attach the actual prerequisite, root and package collections agree, and a bounded
two-worker run preserves logical identities and intended placement. This is a refinement of
RC09's mechanism. No new rule decision is needed. [Fixture plan](../plans/test-domain-model-and-execution/declarations-retirement-and-execution.md#tdm-15--preparation-declarations-at-the-fixture) ·
[pytest fixtures](https://docs.pytest.org/en/9.1.x/how-to/fixtures.html)

<a id="I05"></a>

## I05 — Tie verification work to meaningful changes in the claim

**TDM-02/04/05, TDM-11, TDM-13/14/16/17 · DTA-001/033/044/045/047/048.** Keep the model-binding
rule and its distinctions among authored expectations, construction inputs and correspondence.
Replace the TDM-02 repeated delegated classifications and commit-message artifact with an
editorial check of representative examples in the durable companion. In TDM-04, keep the
authored decimal spelling and complete input frame. TDM-05 should test a generated program's
observable meaning or an actual install dependency. Use parser shape when shape is the
contract, PostgreSQL execution when behavior is the contract, and independently expected
DuckDB rows where order, multiplicity or null handling matters.

Retain deliberate perturbations for shared comparators, cache reuse and refusal paths where a
nearby guard could produce the same apparent result. Use a valid reach control plus literal
status and effect expectations for refusals. A wrong implementation edit for every row or
module adds repeated verification work without always adding discrimination. Compare collected
identities when a migration could lose cases. Use existing native provenance receipts to show
which database class was exercised. TDM-16 should keep generated-scratch checks, installed-release
journeys, and bare/bootstrap tests distinct. A rollback connection can serve a temporary
routine check without standing in for current release admission. TDM-17 should keep the real
lock behavior on its private file and observe host retirement separately from GPU ownership.

Apply the existing retirement rule to TDM-11's `admitted_startup_matches`. Its only current
consumers found were tests, while the package hands it away. Remove it and its mechanism-only
tests inside TDM-11 unless a named accepted pending consumer establishes a specific reason to
retain it. Carry forward any necessary independent live thread-policy behavior. **Principles:**
FP-04/06/07, DP-21/23, H1. **Closure:** each migrated cohort still fails for a meaningful
counterexample, keeps the subject and evidence needed for its claim, and stops exercising
retired setup. Peer refusal and process-cleanup evidence remain with the applicable live route.
[Evidence plan](../plans/test-domain-model-and-execution/reuse-and-refusal-evidence.md) ·
[Retirement rule](../plans/test-domain-model-and-execution/declarations-retirement-and-execution.md#retirement-rules)

<a id="I06"></a>

## I06 — Compose a test review directly from managed attempts

**CLI opportunity · useful before TDM-18.** In the retained N13 chain, `ci test failures`
identified two remaining call failures and offered an exact-retry command. `ci test coverage`
gave the original 148-item denominator and reported scope differences. For interrupted
`087abdd3b95d49409c305105165fa6cb`, `ci results inspect` reported interruption and settled
cleanup, while the [test-system coordinator](../plans/test-system-target-design_2026-11-13.md)
preserves the original required lanes and unrun obligations. These views answer different
questions about one investigation. An operator preparing a review must currently correlate
them by hand. The management and reporting owners already hold the data. [Testing CLI](../../python/corpus-structure/src/corpus_structure/cli/testing.py) ·
[Managed-result inspection](../../python/corpus-structure/src/corpus_structure/cli/result_inspection.py)

Add an optional read-only `ci test review ORIGINAL [ATTEMPT...]`. Use the existing lease
and typed report-building paths in process. Do not shell out to sibling commands or parse
terminal text. Return the original selection, each attempt's lanes and source/context identity,
unresolved logical identities with reasons, custody and cleanup, and a recommended existing
command when one is applicable. Keep review success separate from the reported attempt
outcome. Mixed-source results describe observed node coverage only. Preserve paging and
redaction, report absent fields explicitly, and retain the individual commands for narrow
consumers. A wider result warehouse, trend service, or generic review schema has no current
integration need.

After that view answers the basic review workflow, prioritize a bounded phase timing view
over retained reports and scheduling observations if it saves repeated extraction. Separate
test setup, call, teardown, worker affinity and campaign elapsed time. Label metrics based
on incomplete or incomparable attempts accordingly. Summing overlapping worker durations
does not measure end-to-end time. Keep `ci results watch` as the live owner. Use Typer shared
typed options and Rich tables for the compose view. An interactive progress enhancement can
use a dedicated stderr console with automatic stream redirection disabled when the existing
watch format leaves a concrete diagnostic gap. Shell completion may read bounded authorized
local result metadata; command execution remains explicit. **Principles:** FP-01/06/07,
DP-05/13/14/22. **Closure:** a failed chain and an interrupted or running attempt yield the
same underlying standing as the separate commands, machine JSON remains clean, and review
does not retry or claim custody. [Typer guide](../libraries/python_introspection/typer.md) ·
[Rich guide](../libraries/python_introspection/rich.md)

<a id="I07"></a>

## I07 — Use incremental receipts as the basis for analysis and retries

**Library disposition · Tested 2026-11-18.** The supplied `pytest-json-report` guide is
consistent with the decisive published source. Context7 supplied Typer, Rich and pytest
contracts. Its exact-name search did not resolve the JSON plugin, so the versioned upstream
source established its behavior. With pytest 9.1.1, xdist 3.8.0 and Python 3.14.10, the isolated
probe found useful phase details, captured stdout and item metadata in both normal runs.
It also found zero successful collection item entries in the distributed final report and
missing session metadata with pytest-metadata 3.1.1. A SIGINT report with exit 2 labeled an
interrupted item with only passing setup as `passed`. A controller kill left no final JSON.
After worker loss the final result had a failed item with only a setup stage. Incremental
reportlog retained the available phase and synthetic failure events, including completed
phases after controller loss. The separate Typer/Rich probe produced identical JSON and
exit status with piped stdout under both stderr modes. [Published plugin source](https://raw.githubusercontent.com/numirias/pytest-json-report/v1.5.0/pytest_jsonreport/plugin.py) ·
[Probe and exact observations](../design_review/evidence/2026-11-18_tdm-test-reporting/README.md)

**Recommendation.** Build I06 using the existing reportlog, qualification events and managed
manifests. The native context and retry semantics already require these owners. Preserve JUnit
for its existing exchange consumers. A default duplicate JSON snapshot adds aggregation,
captured-output retention and a second shape without eliminating any owner or being dependable
after loss. If a named external consumer needs the plugin's session shape, compare an explicit
allowed-field export from a settled receipt with an opt-in plugin supplement for fields the
receipt cannot supply. Give any adapter a versioned contract. Keep credential-bearing
exceptions, streams and logs under existing redaction and result custody. The metadata hooks
could be useful for such a consumer, but cannot reconstruct source or native deployment
authority from a missing or incomplete report. **Principles:** FP-04/07, DP-05/15/19/22, G5.
**Closure for any later adoption:** a named consumer uses a field the existing route cannot
produce economically, phase and attempt meaning remain intact under serial and xdist
execution, and a missing final artifact leaves live inspection and exact retry usable.

## Integration order and limits

Resolve I01's active evidence gaps and I02's key inputs early. I04 can proceed independently
after the conftest repair. Merge the producer seam and preparation contracts before expanding
completed-capture reuse. Apply I05 as the packages migrate. I06 can begin with existing
receipts alongside these slices, then use their richer preparation observations as available.
I07 selects the reporting boundary for that work. Existing DTA, RC, F and DA dispositions
remain with their current owners. Wider production handovers, incremental head replay,
cross-session scenario reuse, and long-term historical analytics require their own
justification when triggered.

Checked retained receipts and the bounded isolated experiment only. Whole-suite execution,
real provider qualification, and measured speed or memory improvements are `not_run`.
