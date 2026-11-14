# Assembled test system — design review

**Date:** 2026-11-13. **Tier / purpose:** design / target. **Reviewer:** independent
TS-23 design-reviewer agent. **Focus:** the original holistic test-system engagement,
emphasizing execution fit, preserved assurance, the selected pgTAP/pg_prove/pg_virtualenv
capabilities and alignment with the current declared-data-operations model.

## 1. Scope, outcome and evidence boundary

The assembled design separates stable preparation from case effects while retaining the
distinctions that make native evidence useful. Keyed deployed heads, worker-owned scenario
seeds, explicit resource binding, staged preparation, selection and receipt ownership now
compose into one credible test route. Independent expected meanings remain outside the
production computations they challenge. No additional architectural correction is established
by this review; the bounded decision is in §12.

**Interface-checked by source inspection, 2026-11-13**, applies to the architectural
observations below. Code existence is **Implemented**; expected efficiency benefits are
**Proposed**, with no speedup or capacity measurement claimed. Attributed managed receipts
retain their own source and execution conditions and do not qualify this final tree.

The source baseline is `dee4342741c896a2b67bdad790dae99ed49c054c` plus the live dirty
test-system implementation read on that date. This includes the shared lifecycle/deployment/key,
seed/isolation, snapshot/override and revision-expectation contracts; package and semantic
fixtures; representative record/domain/resubmission/serving and DDO consumers; canonical
support ownership; provider selection/prerequisites; receipt, retry and CLI projections;
SQL/TAP execution; and private-host supervision/bootstrap. Concurrent implementation was
present. The coordinator owns subsequent formatting, source applicability and qualification.

The review consumes test-audit publication `28b4a53db`, its
[PostgreSQL reconciliation](../test-audit/README.md#postgresql-tooling-reconciliation), and
the current [assembled reconciliation](../test-audit/README.md#assembled-test-system-reconciliation)
written for this engagement. Its criteria are core 3.3, heuristics 1.0, test-assessment 1.2,
code-intelligence 1.4 and the repository binding. The functional purpose is dependable,
discriminating verification supporting [DESIGN §1.1](../../design/DESIGN.md#section-1-1).
The [coordinator plan](../../plans/test-system-target-design_2026-11-13.md) and companions
describe the expected change footprint; they do not determine this review's judgments.

This is a test-responsibility engagement under the binding. The production snapshot,
expectation-loading and narrowly authorized PDF guard corrections are examined as affected
contracts. It does not refresh the broad production diagnostic account or assess the whole
DDO production architecture. TS-21 retirement transfer and TS-22 evidence/provider obligations
remain gated by their DDO dependencies. Persistent deployment, activation and production
cutover are outside this review. Those boundaries do not waive a defect in supported tests.

The workload is repeated focused selections and broader qualification on one operator's
workstation, with several pytest workers, large frozen migration artifacts, shared immutable
preparation and cases that genuinely require independent commits, principals or processes.
Growth in recipes, cases and migrations, concurrent acquisition, failed publication, missing
providers and interrupted children are relevant; production corpus throughput is not inferred
from these test fixtures.

## 2. Responsibilities and semantic authority

| Owner | Meaning and consumer contract | Reason to change |
|---|---|---|
| `PgAdmin` / `SemanticDeployment` | Acknowledged database ownership, naming, leases, policy replay, sealed publication and verified usable clones | Database lifecycle or deployment construction |
| Deployment key / expectation resolver | Declared construction inputs and acquired server identity; revision-local frozen expectations | Migration/helper inputs or frozen-contract format |
| Scenario registry / seed owner | One builder per frozen recipe type; sealed worker-owned state with owned files; fresh committing or rollback-family consumers | A new scenario or reusable prefix |
| Scenario support owner | Pure preparation, persisted source, queued/completed stages and explicit resource binding | A changed scenario meaning or consumer stage |
| Snapshot owner | One lazy installed implementation snapshot; explicit process-wide scoped override | Determinant acquisition or controlled alternative implementation |
| Pytest selection / prerequisite owner | Logical identity, selected evidence class, final affinity and external prerequisite reasons | New provider or selection policy |
| Reportlog / receipt owner / CLI | Native outcomes and observations, exact retries, required-node coverage and bounded operator views | New observation or reporting need |
| SQL family / pgTAP bridge | Independently authored SQL/counts and selected logical mapping; actual native TAP execution | A SQL-only case or adapter contract |
| Private cohort / existing supervisor | One explicit PostgreSQL endpoint, canonical purpose Settings, child settlement and artifact custody | Host setup or supervision policy |

The governing sources are
[native lifecycle](../../../scripts/native_test_support.py),
[deployment inputs](../../../scripts/native_deployment_key.py),
[seed operation](../../../scripts/native_scenario_seeds.py),
[recipe registration](../../../python/corpus-structure/tests/scenario_recipes.py),
[package fixtures](../../../python/corpus-structure/tests/conftest.py),
[selection](../../../scripts/qualification_plugin.py) and
[receipt classification](../../../scripts/test_receipts.py).
Semantic identity, acquired physical identity, frozen stage data and live resources are separate.
The model governs operations: construction and disposal require ownership; consumers clone or
borrow a transaction according to their effects; a source claim is acquired after cloning;
provider selection determines required evidence before setup. This is more than common output
columns or domain names on generic records.

The profile applies here to source/evidence fidelity and non-circular evaluation, rather than
requiring a new analyzer or graph system inside test support.

| Fact family | Provider / fidelity | Coverage and unknowns | Identity and consumers |
|---|---|---|---|
| Test outcome | Pytest reportlog / observed | Selected setup/call/teardown; unstarted, blocked and incomplete stay distinct | Canonical logical node ID; retry and coverage |
| Native acquisition | Actual SQLAlchemy/psql session / observed | Item-bound complete acquisition differs from session-only deployment metadata | Database OID, login, endpoint, incarnation; native claim eligibility |
| SQL case result | Native TAP parser / observed | Exact selected cases/counts; malformed or partial batch cannot qualify members | Family/case mapped to logical pytest ID |
| DDO binding meaning | Independently authored expectation / reference | Complete compiled result and bounded protected-admission obligations remain different evidence | Roles/members/source/context/support/witnesses; equality or exact refusal |
| Source/serving reference | Authenticated published source and retained cut / resolved | Scoped reference and continuation controls; no inference of whole-product completeness | Exact source/product/cut identity; retained reader journeys |

## 3–4. Contracts, composition and physical execution

`SemanticDeployment.clone` verifies a reused head on the first useful requested clone, before
consumer effects, and records a stale-key gap before replacement. It does not create an extra
verification-only session clone. Fresh run-private qualification construction avoids cross-run
reuse; concurrent builders share publication locks. Build names remain leased through sealing
and rename, cleanup follows the acknowledged OID, and retention excludes leased heads. The
key deliberately avoids hashing all bulk artifact bytes on every worker; first-use native
catalog verification is a distinct safeguard, not a claim of equality with a new build.

The expectation resolver in
[execution admission](../../../python/corpus-structure/src/corpus_structure/semantic/execution_admission.py)
separates the revision metadata index from selected frozen payload loading. Explicit-revision
lookup follows predecessor inheritance, validates metadata and hashes the selected artifacts;
full-history discovery remains available for the caller that actually needs it. An unrelated
artifact does not become ordinary selected-revision work. Its independent temporary-source
controls retain corruption, unsafe-path, cycle and missing-predecessor refusals.

The TS-10 CaseMatch17 read-class target is coherently realized through TS-24's nineteen-case
SQL family rather than a per-case `native_read` fixture. The deployed
`data.local_semantic_case_matches` consumes literal JSON arguments and is `IMMUTABLE`, with
no DML in its inspected body. The test claim is semantic applicability, not reader privileges.
One family clone supplies deployed state and test-only SQL preparation; pgTAP rolls back
case-local work and the explicit batch transaction rolls back before exit. There is no
per-case database clone. Selected logical identities, independent applicability/statement
expectations, assertion counts and actual maintenance-session context survive this mechanism
substitution. Independent actual-principal controls retain the authorization claim. The
coordinator should record this explicit TS-10/24 disposition; restoring an incidental
per-case launch or read fixture would add work without restoring a missing guarantee.

The seed owner builds through the verified head and registered builder, disposes build engines,
rejects claimed/running tasks even with expired leases, checks policy, seals the database and
freezes owned files. Stage validators retain their consumer-specific custody checks. Frozen
outputs carry source/preparation data; explicit clone adapters supply engines and authenticated
purpose logins. Relevant record/local/judged/interpretation stages refuse retained build handles.
The stage/resource separation prevents a later clone from silently using the seed's disposed
writer. Read and rollback consumers cannot commit shared state through their borrowed outer
transaction; separate readers see committed state. Commit, race, cold construction, migration
and actual-principal claims retain the corresponding native routes.

Record, domain and resubmission preparation keys project the stable inputs they actually use.
Formula capability belongs in the pure preparation key; each expression remains a later input.
Whole default scenarios and source prefixes are both useful physical units. Queuing under a
historical producer patch remains in that actual patch scope instead of acquiring an already
queued seed. DDO original-source composition combines an engine-free authentic record source
with an admitted target kernel and seed-owned runtime files. It does not restore retired DDO
columns or use inference episodes as original-source authority.

The [snapshot contract](../../../python/corpus-structure/src/corpus_structure/semantic/contracts.py)
uses a lock for lazy installed acquisition and a documented, nested process-wide override.
Affected preparation owners bypass ordinary memo reads and writes during overrides, preserving
the warm ordinary entry afterward. Concurrent independent override scopes are expressly outside
this process-wide contract; worker threads within the scope see its chosen implementation.

| Analysis/projection question | Universe, method and model | Bounds, output and evidence |
|---|---|---|
| Did these selected tests complete? | Exact selected manifest and reportlog phases; deterministic classification | Partial streams stay incomplete; receipt keeps native evidence and source/context |
| Did these SQL cases execute? | Exact selected family/case set, pgTAP xUnit, native child/outer TAP parsing and actual psql exit | Finite declared family; invalid framing/count/process/context invalidates qualification while retaining observations |
| Can this receipt cover this requirement? | Logical-ID mapping plus required evidence class and host mode; no suffix guessing | Missing provenance, unknown context and unresolved nodes remain explicit; plan judges final applicability |
| Does the binding preserve meaning? | Complete authored `BindingResult` on PostgreSQL, plus separately authored actual-writer admission cases | No Boolean/full-result equivalence; role/member/source/context/support/witness differences remain observable |

## 5. Revealing change and failure scenarios

| Scenario / kind | Propagation and judgment |
|---|---|
| Change a migration or real constructor helper / mechanism input | The key changes at the construction owner; unrelated seed/sweep work need not rebuild the head. Reused native catalog verification remains before effects. Frozen successor expectations evolve through their existing owner. |
| Add a recipe or source prefix / composition | Frozen input type and one builder belong to its support module; downstream fixtures choose the stage they need. No new lifecycle, database-name convention or generic orchestration branch is required. |
| Add a refusal / instance | Author the mutation and exact expected native reason beside the case; the common helper checks diagnostic shape. Keep a valid reachability premise and absent-effect assertion where the claim needs them. |
| Add or lose a provider / evidence binding | Explicit provider identity and named prerequisites flow through collection, setup reporting, retry and coverage. Missing assets do not change a controlled test into an apparent provider pass. |
| Replace shared host with private cohort / mechanism | Existing fixture/lifecycle contracts consume acquired Settings. One cluster serves the cohort; private mode and a fresh incarnation survive retry. Shared authentication/durability controls are refused rather than reinterpreted. |
| Replace Python SQL-only case execution with pgTAP / mechanism | The independent inputs/counts and logical identities survive; pgTAP owns rollback and TAP syntax. Real-purpose, publication and multi-session claims remain on the appropriate Python/native route. |
| Grow workers/recipes; fail a builder or interrupt a child / growth and failure | Worker affinity avoids repeated designated preparation; one seed per recipe per worker and one private host per cohort bound unnecessary startup. Failed publication cleans acknowledged resources; incomplete batches and unsettled child groups cannot earn complete evidence. |
| New source/evidence family or changed served selection / domain extension | Scenario-specific support composes exact source pins and authored meanings. The continuation consumer retains its completed-cut pin across actual project-selection changes; incomplete or unmaterialized populations remain unknown/refused. This assesses test fidelity, not the entire product extension. |

These scenarios support FP-01–FP-07 rather than relying on file count or passing examples.
The retained costs buy concrete guarantees: fresh commits and purpose logins establish visibility
and authorization; rollback families isolate case effects; deployment checks challenge reused
catalog state; cold controls exercise construction itself. Broader worker sharing or elimination
of those boundaries would need a corresponding claim-preserving contract.

## 6–7. Gates, findings and applicability

Gate judgments below are static **pass** judgments within the reviewed boundary, not test
execution outcomes or claims of complete suite quality.

| Gate | Judgment and decisive basis |
|---|---|
| G1 Authority | Pass: lifecycle, recipe type, selected identity and native outcome have identifiable owners; authored expectations are independent references. |
| G2 Semantic fidelity | Pass: stage/resource, observed/expected, unknown/absent, controlled/provider and logical/physical distinctions survive the inspected consumers. |
| G3 Validity | Pass: owned acquisition, sealed seeds, borrowed transaction enforcement, exact native refusals and independently authored malformed inputs provide explicit rejection boundaries. |
| G4 Hidden behavior | Pass: explicit effects/Settings, snapshot scope, final selection and controlled prove/harness inputs; no ambient provider-class branch in the inspected split consumer. |
| G5 Consistency and recovery | Pass: acknowledged publication, usage/build leases, unforced cleanup, batch validity and existing process settlement protect visibility and failure meaning. |
| G6 Transformation and reuse | Pass: complete recipe dependencies, stage-specific reuse, override memo bypass, exact logical aliases and explicit required host/evidence matching. |
| G7 Truthful capability claims | Pass: bounded receipt observations, native applicability and incomplete/blocked states do not become qualification or speed claims. |
| G8 Library leverage | Pass: PostgreSQL template cloning/transactions/advisory locks, pytest/xdist, pgTAP, native TAP parsing and pg_virtualenv discharge their existing capabilities; adapters own concrete attribution/custody gaps. |
| CI-G1 Fidelity | Pass in applicable evidence paths: unknown stays distinct from absence; native/expression/full-result and controlled/provider evidence are not relabelled. Whole-product extraction/analysis semantics are outside this test engagement. |
| CI-G2 Evidence closure | Pass for receipt and inspected retained-source/continuation journeys: selected identities bind actual observations; session-only metadata cannot attest an item. Whole-product serving closure is not certified. |
| CI-G3 Evaluation integrity | Pass for inspected authored results, literal identity vectors and nonperfect reference controls; shared wire validators are not treated as independent semantic expectations. No claim about unexamined evaluation families. |

No new material finding is established. Existing DTA and source-review findings retain their
identities and [single scheduled disposition owner](../../plans/test-system-target-design_2026-11-13.md#finding-disposition).
This review changes their inspected premises; it does not close every historical footprint.
The earlier [PostgreSQL review F01](design_review_postgresql-tooling_2026-11-13.md#f01--ambient-proveharness-inputs-can-alter-execution)
is addressed at the inspected boundary: `--norc`, explicit harness/formatter/rules/jobs,
normalized environment, launch-option validation and actual psql exit checking. The plan owns
closure evidence. There is no new rule-impact identity or second findings ledger.

## 8–9. Library fit and complete alternatives

The selected [SQL adapter](../../../scripts/pgtap_batch.py) delegates assertion/xUnit
execution to pgTAP and TAP grammar to `TAP::Parser`; its small framing adapter enforces this
finite family's identity/count contract. `Corpus::Harness` validates the native pgTAP source
options rather than replacing psql execution. The selected
[private-host adapter](../../../scripts/native_private_cohort.py) delegates cluster creation
and normal trap cleanup to installed pg_virtualenv, while
[bootstrap](../../../python/corpus-structure/tests/native_private_bootstrap.py) owns project
roles/extensions/Settings and waits for recorded child owners. The
[tooling review](design_review_postgresql-tooling_2026-11-13.md) preserves the library contract
references and alternatives; current adapter source was independently inspected here.

| Complete option | Assessment |
|---|---|
| Per-test/per-worker head and repeated complete scenarios | Simple local acquisition but repeats stable migration/preparation work at incidental case boundaries. Retain it only where construction is the claim. |
| Current keyed head plus worker seeds/stages | Removes repeated stable construction while retaining fresh transaction/commit/principal boundaries. Keys, sealing and explicit binding add justified custody responsibilities. Preferred for the reviewed workload. |
| Shared cluster versus private cohort | Shared acquisition avoids cluster startup; a private cohort isolates host state and supports explicit incarnation custody. Neither proves durability; keep both as explicit modes, with unsupported shared-host controls refused privately. |
| Per-case Python SQL versus finite pgTAP batch | Python is preferable for application/purpose/concurrency cases; one native batch removes repeated SQL crossings for the selected family. Batch-level failure enlarges the retry unit but preserves exact logical observations and refuses partial qualification. |
| Custom deployment/TAP/cluster framework | No concrete benefit justifies replacing established database, parser or cluster capabilities. Further generalized workflow/registry machinery is unnecessary. |

The relevant efficiency reasoning is H5/H8/H12–14/H18–24/H26–28: reuse stable work, preserve
validity premises, cross boundaries at useful granularity and keep auxiliary/recovery machinery
proportionate. Per-seed clone validation and real native acquisition remain because their
premises cross a physical copy/session boundary. No timing claim is needed to distinguish
this from repeated whole-chain construction.

## 10. Verification and remaining uncertainty

**not_run by this reviewer:** functional tests, benchmarks and broad qualification. Static
inspection was sufficient for the architectural decisions; no proof-only probe was added.

**passed read-only inspection, 2026-11-13:**
`uv run ci results show 38db958326b24a66a670e740eb8a0464 --json`,
`uv run ci results show 8bbf9bb6a7fe4c3a97fd12d7f96a3650 --json`, and
`uv run ci test scheduling 8bbf9bb6a7fe4c3a97fd12d7f96a3650 --limit 2 --json`.
The existing first receipt records nine private-host cases passed across two requested/actual
workers. The second records nineteen native SQL identities passed; the scheduling view records
one valid batch, 39 expected/observed assertions, successful pg_prove/psql exits and actual
item-bound acquisition context. These are attributed **Tested** observations of those original
2026-11-13 runs, not newly executed tests or final-source union coverage. The
[private-cohort evidence](../evidence/2026-11-13_test-system-private-cohort/README.md)
retains failed/interrupted attempts and its explicit limits, including Rust-inside-private
execution not_run at that evidence endpoint.

Source controls inspected include native publication/failure/retention, seed cleanup/claims,
pure preparation and nested override restoration, exact SQL/TAP framing/process failures,
provider prerequisites and retry containment, original-source custody, complete PostgreSQL
binding equality and bounded actual-writer substitutions. Test existence is not a fresh pass.
The original-source composition and four TS-18 consumers were reread after their owner declared
source stable. Final TS-20 inspection covers `data_operation_binding_support`, the complete-result
test in `test_data_operation_bindings`, the protected scalar/population sections in
`test_data_operation_storage` (including the added semantic support-episode substitution), and
the canonical `discover` importer in `test_data_operation_population_native`. Shared range-case
metadata supplies both observation boundaries; the expected compiled result and expected native
refusal remain independently authored. Read-only `ci results show` for
`52739ad6d420445e80f70c1cef63f316` and `c02bd2220d2e4d1cab7d6ca758c7f3cd` records their
bounded four- and sixteen-identity selections as passed. The latter receipt predates the added
support-episode substitution. Read-only `uv run ci results show
66926508d9f340b8abeddb12470b5c17 --json` subsequently records that affected native identity
passed with the eleven authored scalar substitutions. These remain bounded attributed receipts,
not final-source union qualification.
The coordinator's final two contract edits were also inspected: release-compatibility's second
database now uses `commit_clone()` while retaining independent database-scoped cache and digest
expectations; domain staging disposal now requires exact `P0001` / `untrusted staging relation
sp_record_report` diagnostics. These fulfill the scheduled preparation/refusal responsibilities
without changing the architectural judgment; their affected test outcomes remain coordinator-owned.
The [PDF repair evidence](../evidence/2026-11-13_test-system-pdf-guard-repair/README.md) and
the actual changed guard expressions were read: the recipe local-variable ambiguity is removed,
and the reuse query follows `producer_task_id` while retaining `ddo_support_valid`; it does not
restore retired machinery. Producer/adopter fencing remains with DDO's production owners.

Coverage is representative and change-led, not a line-by-line reread of every moved test or
all support helpers. No universal oracle-independence claim follows. Full provider availability,
final native/functional/nonfunctional union applicability and source after coordinator maintenance
remain qualification work. New changes that affect a reviewed contract require reconciliation;
an unrelated edit does not automatically reopen the architecture or justify another broad audit.

## 11. Authority changes and disposition

**New rule impacts: none.** The reviewed realization needs no additional waiver, gate, register,
alignment lint or production-DDO decision. Existing confirmed rule changes and successors remain
owned by the coordinator and architectural collection. Review acceptance does not authorize a
persistent database operation or a DDO cutover. Scheduled finding state and the remaining TS-21/22
dependencies stay in the [coordinator](../../plans/test-system-target-design_2026-11-13.md).

## 12. Architectural judgments and decision

| Judgment | Verdict | Independent scenario basis |
|---|---|---|
| A1 Localize change | Satisfied | New recipes/refusals/providers change their coherent support/selection owner; deployment and resource custody remain bounded dependencies. |
| A2 Encode domain meaning explicitly | Satisfied | Recipe/stage/isolation/purpose/outcome/evidence distinctions govern acquisition and observation; complete expectations remain independent of the selected production calculation. |
| A3 Extend through composition | Satisfied | Domain/source/kernel prefixes compose with one seed/lifecycle route; host and SQL mechanism substitutions preserve their actual boundary contracts. |
| A4 Fit execution to the supported workload | Satisfied | Keyed head reuse, first useful verification, stage-specific memo/seed lifetimes, designated affinity and cohort/batch granularity remove repeated stable work while retaining justified fresh effects and recovery units. No unsubstantiated speed claim supports this verdict. |

**Decision: Accept scoped**, at the static Interface-checked strength stated above, for the
assembled implemented test-system responsibilities and selected change/failure scenarios.
No in-scope MUST gap or unresolved gate is established. This is an assembled architectural
judgment, not the accumulation of local passing slices.

**Enclosing status:** the reviewed test architecture is accepted for those scenarios; product
DDO completion/retirement and whole-product fidelity remain unassessed here. TS-21/22 reopen
their excluded obligations when their DDO dependencies are available. The coordinator's next
step is final-source qualification and handoff, retaining blocked/not_run obligations and all
failed/interrupted receipts. This review supplies no complete-qualification or measured-benefit
claim.
