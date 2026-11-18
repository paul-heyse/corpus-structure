# Reuse and refusal evidence

**Status:** Proposed companion of the
[test domain-model and execution plan](../test-domain-model-and-execution_2026-11-17.md); not started.
**Created:** 2026-11-17. Writing this plan authorizes no implementation.

This companion owns the designs of TDM-13 (a perturbation table for every production mechanism
that reuses work or skips a check, and one fixture that owns the isolation of the selected-query
cache) and TDM-14 (the existing refusal contract applied to the sites that still accept an
undifferentiated refusal). The findings are
[DTA-044](../../design_review/test-audit/evidence-and-discrimination.md#dta-044) and
[DTA-001](../../design_review/test-audit/evidence-and-discrimination.md#dta-001), with the evidence
half of [DTA-038](../../design_review/test-audit/execution-and-qualification.md#dta-038). Package
state, the queue, finding dispositions, shared contracts, rejected options and external context are the
[coordinator's](../test-domain-model-and-execution_2026-11-17.md).

**Baseline and evidence.** Section references written `§n` point to the
[source review](../../design_review/reviews/design_review_test-domain-model-and-execution_2026-11-17.md),
which read source at `1afa63f88` and the audit at `fbd3f2a98`; this companion develops its §4.4,
the cache row of §4.8 and §5.4. Every design statement here is **Proposed**. The plan was
authored against commit `50827eb9f` (the authoring baseline, 2026-11-17) and revised against
commit `12f57dc4d` (the revision baseline, 2026-11-18), after the model-owned SQL conversion
([ADR-0131](../../adr/0131-model-owned-postgresql-programs.md)) was completed. The conversion is
under validation, so source may still move a little; TDM-00 re-reads what changed since
`12f57dc4d`. Source facts re-read at the revision baseline are **Interface-checked by source
inspection, 2026-11-18**, and line citations are to that commit. Facts that were not re-read keep
their 2026-11-17 label: in this document those are the internals of mechanisms 5 to 8, whose
production and test files are unchanged since the authoring baseline, and the count of cases at
the two bare-`ValueError` tests of TDM-14. Nothing was run, and a statement about what a test
would observe is made "by reading, not run". No speedup is claimed. The investigation reports
this companion draws on are in the evidence folder
`docs/design_review/evidence/2026-11-17_test-plan-authoring/`: the
[current-state map](../../design_review/evidence/2026-11-17_test-plan-authoring/state.md), whose part B lists what a test can observe for each
mechanism, the [library capability notes](../../design_review/evidence/2026-11-17_test-plan-authoring/library-capabilities.md), and the
[identity re-baseline](../../design_review/evidence/2026-11-17_test-plan-authoring/rebaseline-identity.md), which re-read every mechanism and
refusal site at `12f57dc4d`. `tests/…` and `src/…` are relative to `python/corpus-structure/`;
repository-root paths are written as root `scripts/…` or root `tests/…`. The hand-written
`data_operations.sql` that this page used to cite was deleted by the conversion; mechanisms 2, 3
and 4 now live in generator modules under `src/corpus_structure/semantic/`, named where each is
described.

## Review integration · 2026-11-18

**Proposed.** I01, I02 and I05 from the
[November 18 improvement review](../../plan_improvement_reviews/test-domain-model-and-execution_2026-11-18.md)
refine the identity determinants and refusal evidence below. The review inspected `aea554e5c`.
Existing counts retain their stated baseline. Its retained mixed-source N13 attempts establish
observed coverage for particular identities and contexts, with unresolved obligations retained
by their product owner. They provide examples for test guidance and managed review.

## Why this work exists

Production has gained many mechanisms whose purpose is to avoid repeating work that was already
established: a check is skipped because an earlier receipt covers it, a result is served from a
cache, a prepared state is kept because its key did not change. Each such mechanism makes a
decision, "reuse" or "do the work", from a set of facts. This page calls those facts the
mechanism's **determinants**.

The audit asked one question of each mechanism: if the reuse were wrong (stale, wrongly keyed, too
broad), which test would fail? For ten mechanisms the answer was none (DTA-044, and DTA-045 and
DTA-038 for two of them). Their tests exercise the path where reusing is correct. No test changes a
determinant and shows that the mechanism stops reusing. A regression that always skips, or that
drops one determinant from a key, changes what is published or served and fails nothing.

A second, older gap has the same character. Some tests assert that an operation is refused but not
*why*; a refusal by a neighbouring guard satisfies them, so removing the guard the test is named
for can go unnoticed (DTA-001). The refusal contract that fixes this exists
(`tests/native_refusals.py`); sites written since do not use it, and none of the 26 test files
the conversion added does.

**What this companion consumes.** The public observation points each mechanism already exposes
(listed per mechanism below); the head-key function as TDM-06 leaves it; the public profile
comparison as TDM-11 leaves it; the two lowering refusal tests TDM-05 writes; the refusal helper;
the isolation-class fixtures of ADR-0101.

**What it produces.** For each mechanism, a table of cases a wrong reuse would fail; one fixture
that owns cache isolation for every test; refusal assertions that name the guard.

**Where its responsibility ends.** It selects no production change. Where a case cannot be written
until production decides something, the case is recorded with its trigger and not written. It does
not own the production seams that make two mechanisms testable (TDM-06, TDM-11), the double that
replaces the native recheck in cache consumers (`control_frontier`, TDM-12), or the independence
corrections at the lowering-identity test and the validity closure (TDM-05 in
`model-binding-and-independence.md`).

## The perturbation table

The coordinator's contract *perturbation table* names the parts every table below has: how the
decision is observed, a hit control, safety cases that distinguish consequential determinants,
and a completeness case
where the mechanism declares its determinants as data (accepted by the operator on 2026-11-17 as
a test of one mechanism, not a lint). Three working rules add to it.

**Observation.** A table uses what the mechanism exposes: a returned field, a row, a refusal, an
object's identity. Where nothing is exposed, it wraps the expensive production step in a counting
spy. A spy records that work happened; it supplies no expected value.

**The author's list (rule 3).** For each determinant the test author judges should matter, the
case changes its *source* (a receipt's state, a file's bytes, a budget) and asserts the literal
outcome: recomputed, checked, or refused with a named reason. The author decides the list from
what the mechanism is for, not by reading the key's code and copying its fields. A determinant
the code forgot is exactly what the author's list is there to find.

**Two directions.** A safety case says reuse must *not* happen; it holds whatever grain the
identity has, and is written now. A precision case says reuse must *still* happen after an
irrelevant change, and is written now only where production has already decided the grain;
otherwise it is recorded with its trigger.

**Discrimination.** Perturb the determinants whose omission or misinterpretation could change
reuse safety or the stated precision claim. Exercise shared comparators at their owning boundary.
A separate implementation mutation for every row or consumer is needed only when it resolves a
different plausible failure. Preserve deliberate invalid inputs and independently authored
expected outcomes. Compare collected logical identities when consumer migration could drop cases,
and retain existing native receipts where the database class or source/context matters.

**Form.** A table is a module-level tuple of cases beside the test that consumes it, each case a
name, a perturbation and a literal expected outcome, run through `pytest.mark.parametrize`. There
is no shared perturbation framework: the ten mechanisms observe different things, and the
test-assessment companion's §2 warns against forcing superficially similar cases into one
configurable helper. The only shared piece is the small counting-spy idiom, which stays a local
function where it is used.

## Pivotal library capabilities

**Plain pytest and the standard library are sufficient for every table.** Each mechanism has a
small, closed set of determinants. `pytest.mark.parametrize` with `pytest.param(..., id=…)` gives
one named result per case; `dataclasses.replace` perturbs one field of a frozen value;
`dataclasses.fields`, or the keys of a declared mapping, supply the declared set for a completeness
case. These are selected. Reference: the
[library capability notes](../../design_review/evidence/2026-11-17_test-plan-authoring/library-capabilities.md), section D on determinant-perturbation
testing (pinned pytest 9.1.1), which also states the limit that shapes rule 3 above: perturbing a key's *fields*
and recomputing the expectation with the key function is circular, while perturbing a
determinant's *source* and asserting an observable outcome also catches a determinant that is
missing from the key entirely.

**Hypothesis `RuleBasedStateMachine` is a candidate, for cache lifecycle order only.** A state
machine with rules such as warm, perturb, restore and query, and an invariant "a hit happens only
when the current determinants equal a warmed set", explores orders of operations a fixed table does
not, and shrinks a failing sequence (Hypothesis 6.170.12, `hypothesis.stateful`; the same section
D of the library capability notes). It adds nothing for completeness or for single-step safety cases. It is not selected. It would
apply to the in-process caches only: the selected-query cache, the execution-basis cache and the
kernel memo TDM-07 introduces. The trigger, as the coordinator records it, is an order-dependent
defect that plain parametrized cases leave uncovered, or the query cache becoming shared across
processes ([DA-075](../../design_review/audit/execution-fit.md#da-075)), which adds invalidation
order as a real determinant. The history concern is already answered: the `ci` profile registered
at `tests/conftest.py:95–97` sets `database=None` and `derandomize=True`, so no failure history is
kept. One caution for whoever adopts it: the same file loads the profile named by
`HYPOTHESIS_PROFILE` and defaults to `dev` (`:98–99`), which keeps Hypothesis' defaults, so a state
machine must run under the `ci` profile or carry `database=None` in its own settings.

## TDM-13 — Perturbation tables and the cache-scope fixture

**Needs.** TDM-06 for the head key's table, and TDM-11 for the check of form of the profile table
(mechanism 9), each stated below by the capability it supplies. The other eight tables need
nothing from this series and can be written once TDM-00 has confirmed that their mechanism has
not moved since `12f57dc4d`. Two tables build on tests TDM-05 writes; that is an ordering
convenience, not a barrier.

**Delivered by the conversion; remaining scope below.** The conversion moved mechanisms 1 to 4
into generated programs without changing what they decide, and it left the caches, file custody,
the execution host, the native host and the head key untouched. Its new tests supply part of one
table: three tests of the release-fact compiler cover the admission side of mechanism 3 (see
there). They supply no case for the oracle skip, the kernel seal, the validity closure or any
cache, and none of them has the hit-control and perturbation form. Every other table remains in
full, and the cache-scope fixture is as it was.

**Implementation vision.** Each table is added to the test module that already holds the
mechanism's equal-path test, so the hit control and the safety cases sit together. The package
owns, per mechanism, the author's list of determinants and each literal outcome. Where a setup
needs a state production's own programs can produce (a failed oracle receipt), the test produces it
through those programs. Where no program produces the state (a receipt recorded under another
kernel), the test's owner role writes it directly inside a rolled-back transaction; that is
deliberate tampering with a determinant's source, which is what a safety case is.

**Failure behaviour.** A safety case that fails on first run is a finding, not a literal to
adjust. Either the mechanism reuses where it should not (a product defect, reported to the
coordinator with the case as its reproduction) or the author's judgment about the determinant was
wrong (the case is removed with its reason recorded in the table). The expected outcome is never
rewritten to match what the mechanism did.

### 1. PDF round-trip oracle skip

*Mechanism.* Validation of a PDF build runs a reconstruction oracle unless a passed oracle receipt
already covers the same lowering identity and kind and is bound to a published, validated revision
(the generated program `ops.read_pdf_certification_requirement`,
`src/corpus_structure/semantic/pdf_certification_native.py:363–403, 456–462`; the Python decision
in `validate_pdf_build`, `src/corpus_structure/semantic/pdf_publication.py:783–824`). It is the
one mechanism here that removes an established check instead of reusing a computed value.

*Observation.* `ops.read_pdf_certification_requirement(build, task, attempt, holder, frozen)`
returns `oracle_receipt_id` and `certification_basis`. The Python side runs the oracle exactly when
`force_oracle` is set or `oracle_receipt_id` is null (`pdf_publication.py:824`). The rows of
`ops.pdf_roundtrip_oracle` show whether an oracle began for a build. After publication,
`inspect_pdf_execution_receipt(…).certification.basis` (`pdf_publication.py:1045` onward) reports
the basis. No production change is needed. One reading matters for what to assert: the requirement
program sets the basis to `'producer-certified'` whenever the build has no passed oracle of its
own, before it knows whether a prior receipt qualifies (`:456–462`, by reading, not run). The basis
alone therefore does not show the decision; the table asserts `oracle_receipt_id` and the oracle
rows.

| Case | Change to the determinant's source | Literal outcome |
|---|---|---|
| Hit | Build A is validated by a passed oracle and published. Build B has the same lowering identity and kind | B's requirement returns A's receipt id and `producer-certified`; validating B adds no oracle row for B |
| Failed receipt | A's oracle finished in a failing state | B's requirement returns a null receipt id; validating B adds one oracle row for B in state `passed`; B's published basis is `round-trip-verified` |
| Unpublished | A's oracle passed but A was never published | As "failed receipt" |
| Unvalidated | A is published but has no validation record | As "failed receipt" |
| Other kind | A's passed, published receipt is for a different kind | As "failed receipt" |
| Other lowering | A's passed, published receipt carries a different lowering identity | As "failed receipt" |
| Forced | Hit conditions, with `force_oracle=True` | An oracle row for B is added although a receipt qualifies |

*Declared inputs.* The lowering identity declares its inputs as data: the retained contract lists
each input with its digest, built from `LOWERING_FILES` and `LOWERING_LIBRARIES`
(`src/corpus_structure/semantic/pdf_lowering.py:15–106`; the file list is about seventy entries
after the conversion). TDM-05 writes the two refusal tests (a
captured source that differs; a contract that differs). This table adds the enumerated form: for
every input the retained contract lists, altered captured bytes are refused with "captured PDF
lowering source differs from its contract". Enumerating from the contract is right here because
the set only generates cases. What it cannot show is that the list is *complete*; that is the
`LOWERING_FILES` row of the coordinator's [production context](../test-domain-model-and-execution_2026-11-17.md#handovers).

*A wrong implementation each row fails.* Dropping the `state == "passed"` condition fails "failed
receipt"; dropping the join to published revisions fails "unpublished"; dropping the validation
join fails "unvalidated"; matching without kind or lowering identity fails those rows; ignoring the
force flag fails "forced"; never reusing fails the hit.

*What exists at `12f57dc4d`.* No test supplies a row. `tests/semantic/test_pdf_certification_programs.py:56–76`
calls the requirement program for an unknown build and pins `P0002`, with no positive control and
no message; it is a TDM-14 site. `tests/semantic/test_pdf_validation_read_native.py:200` checks a
"no passed round-trip oracle" refusal of the frozen-check dispatch against a stubbed table, which
is a different decision.

### 2. Kernel-sealed completion

*Mechanism.* When an episode is re-read, `ops.ddo_require_episode_correspondence` runs the full
completion battery only if the receipt's `validating_kernel_digest` differs from the installed
kernel's digest. The routine is generated in
`src/corpus_structure/semantic/data_completion_settlement_native.py` (declared at `:625`, the
comparison at `:661`, the refusal message at `:667`); seven generated admission and completion
programs call it. Every existing test publishes under the installed kernel, so the battery branch
never runs: `tests/semantic/test_data_operation_storage.py:2864–2887` checks the equal path by
reading the receipt's digest and comparing it with the seal's, and
`tests/semantic/test_data_completion_settlement_programs.py` checks the routine's signature
statically and adds no case.

*Observation.* A refusal with SQLSTATE `23514`, or its absence. Nothing else is exposed.

| Case | Change | Literal outcome |
|---|---|---|
| Hit | Receipt under the installed digest; the retained intent's payload altered so its recorded digest no longer matches | No refusal: the seal is accepted as the evidence. Without the altered payload a skip and a re-check are indistinguishable, so the alteration is part of the hit control |
| Other kernel | The same altered payload; the receipt's digest set to a different value | `23514`, "historical intent payload digest differs" |
| Absent seal | The same altered payload; the receipt's digest null | The same refusal |
| Battery reached | Receipt under a different digest; payload digest consistent, payload content violating one named completion check | That check's own refusal, asserted through the refusal contract |

*Precision, gated.* "A kernel change that cannot affect completion checking still skips the
battery" fails today, because the digest covers the whole kernel source. Trigger:
[DA-068](../../design_review/audit/execution-fit.md#da-068) decides the grain of kernel identity.

*Open at entry.* Whether the test's owner role can set `validating_kernel_digest` inside a
rolled-back transaction, or an immutability guard prevents it. If it is prevented, the case needs a
receipt recorded by a head built from a different kernel source, which is expensive, and the choice
returns to the coordinator.

### 3. Lowered release facts

*Mechanism.* `sem.data_operation_release.lowering_digest` records the lowering under which a
release's facts were admitted. Readers and demand admission require it to equal the installed
digest (`src/corpus_structure/semantic/data_operation_read_native.py:207–212`,
`demand_registration_native.py:602`, `demand_authority_native.py:137`). Admission is the generated
routine `sem.ddo_lower_data_operation_definitions`
(`src/corpus_structure/semantic/data_operation_compiler_native.py`, declared at `:1108`):
re-admission of an existing release re-lowers and updates the column (`:1073–1078`), and a
mismatch that survives is refused (`:1094–1099`). One older test checks that the column exists
(`tests/semantic/test_data_operation_lowering.py:6–28`).

*Observation.* The column's value before and after; the readers' refusals.

*Supplied by the conversion.* `tests/semantic/test_data_operation_compiler_native.py` has three
tests on the admission side, and they are not written again. Admitting a release twice returns
the same literal result and leaves the column equal to the digest of the program the test itself
installed (`:181`). Five mutations of the admitted evidence are each refused with a literal
message and leave no partial facts (`:219`). Re-lowering requires finalization, keeps the
admitted immutable facts, and leaves the column equal to the digest (`:367`). These are
independent expectations of what admission writes. None of them makes the column stale, so none
is a safety case of the reuse decision, and neither of the two refusal messages in the table
below appears in any test.

| Case | Change | Literal outcome | State at `12f57dc4d` |
|---|---|---|---|
| Hit | Admitted release, column equal to the installed digest | A demand on the release is admitted | The column's value is covered (`:181`); the admitted demand is missing |
| Stale digest refuses a read | Column set to another value by the owner role | Demand admission refuses; read-only inspection refuses with `23514`, "read-only inspection native source correspondence differs" | Missing |
| Re-admission re-lowers | Stale column; the release is admitted again as an existing release | The column equals the installed digest again and the demand is admitted | Missing: the existing replay starts from an equal column |
| A new-release admission does not repair | Stale column; admission flagged as a new release | Refusal, "release facts changed under admitted release" | Missing |

*Precision, gated.* "A lowering change that cannot affect this release's facts leaves it readable"
fails today because the digest is one digest of the whole native source. Trigger:
[DA-069](../../design_review/audit/execution-fit.md#da-069).

### 4. Set-wise validity closure

*Mechanism.* `ops.ddo_valid_closure` evaluates validity for a set of seeds; the scalar
`ops.ddo_node_valid` delegates to it (both generated in
`src/corpus_structure/semantic/data_validity_native.py`, at about `:578` and `:643`).

This mechanism makes no reuse decision to observe. Its gap is an independent reference, and TDM-05
supplies that: hand-authored graphs with literal expected rows (shared descendants, mixed seeds, a
two-node cycle, population supersession) and the property that a node's validity does not depend on
what else was seeded. This table adds nothing of its own and exists so the mechanism is not lost
from the list of ten. The undeclared-member case is under "Gated cases" below.

### 5. Selected-query cache

*Mechanism.* Served queries keep bounded derived rows in a process-global cache
(`src/corpus_structure/semantic/selected_query_cache.py:60–86`; 32 MiB, 128 entries). The demand
query's key includes the request's `max_bytes`, so an entry filled under a larger budget cannot
answer a request with a smaller one (`src/corpus_structure/semantic/demand_queries.py:196–212`).
Five serving modules use the same cache with their own keys (`src/corpus_structure/serve/`:
`rich_queries.py:226`, `identity_exclusion_comparison.py:156`, `contribution_facets.py:264`,
`structural_products.py:283`, `interpretations.py:208`).

*Observation.* The return value does not say whether the cache answered. This is the one mechanism
where a counting spy is the only option: the cold path calls `read_demand_result` for the whole
result (`demand_queries.py:215–226`), and a spy on that call counts recomputations. The bounds of
the cache itself are observable through its public `get` and `put` on an instance the test
constructs.

| Case | Change | Literal outcome |
|---|---|---|
| Hit | The same request twice | One whole-result read; equal rows |
| Smaller budget against a warm entry | Warm with a large `max_bytes`; repeat with a `max_bytes` the body exceeds | A second whole-result read, and the budget refusal the cold path gives. Not the warm rows |
| Different cut | Warm; repeat after the trust assessment changes the cut identity | A second whole-result read |
| Different page | Warm; repeat for a page whose content differs | A second whole-result read |
| Authority on a hit | Warm; repeat with the native recheck refusing | The refusal; the cached rows are not returned (the existing ordering test at `tests/semantic/test_demand_results.py:150–163` is the base) |
| Entry bound | An instance with `max_entries=2`; three distinct keys stored | `get` of the first key returns `None`; the other two return their entries |
| Oversized entry | An entry larger than the instance's byte bound | `put` returns `False` and `get` returns `None` |

The key is assembled inline, not declared as data, so there is no completeness case; the table is
the specification. For the five serving modules, the package's first step reads each key and
authors that module's determinant list from what its request means. Each module that has a budget
gets the "smaller budget against a warm entry" case, which is the regression the audit names; rich
graph-budget refusals currently run only cold.

### 6. Change scope

*Mechanism.* `changed_operations(before, target)` reports the operations whose recipe changed and
every operation that depends on them (`src/corpus_structure/semantic/change_impact.py:157–200`). On
the native side, a read is pinned to source scopes, and validity under a read boundary depends on
revocations in those scopes.

*Observation.* The returned roots and affected mapping, which are plain sets; the boolean from
`ops.ddo_node_valid` with a boundary.

| Case | Change | Literal outcome |
|---|---|---|
| Affected set, several operations | A hand-authored model with four operations: B depends on A, D depends on C. A's recipe changes | Roots are exactly `{A}`; the affected names are exactly `{A, B}`; C and D are absent. The expected sets are written by hand |
| Revocation in a pinned scope | A read pinned to scope S1; a revocation in S1 | The node is no longer valid under that read |
| Revocation in another scope | A read pinned only to scope S2; the same revocation in S1 | The node stays valid under that read |

The existing two-operation assertion (`tests/semantic/test_change_impact.py:130–136`) stays. The
last row is a precision case and is written now: the source scope is a grain production has
already decided, so the case is expected to hold at entry (by reading, not run). If it fails, that
is a finding.

### 7. File custody's racy window

*Mechanism.* A file whose modification time lies within two seconds of the moment it was acquired
is marked racily clean and is re-read at every check, because its metadata cannot prove it is
unchanged (`src/corpus_structure/semantic/file_custody.py:17, 36–56`). The test fixture advances
the clock ten seconds (`tests/semantic/test_file_custody.py:16–21`), so the flag is never derived
as true.

*Observation.* The `racily_clean` field; whether a check reads the file, by the read-forbidding
patch the module already uses (`:24–32`) or a count of reads.

| Case | Change | Literal outcome |
|---|---|---|
| Hit | Acquired ten seconds after the file's modification time | `racily_clean` is false; a check does not read the file |
| Inside the window | Acquired one second after | `racily_clean` is true; each check reads the file once |
| At the boundary | Acquired exactly two seconds after, and two seconds plus one nanosecond after | True, then false. The two seconds is a literal in the test, not production's constant |
| Future timestamp | Modification time later than the acquiring clock | True |
| Changed bytes inside the window | Same size and restored timestamps, different bytes | `FileCustodyError` |

### 8. Execution-basis cache key

*Mechanism.* `ProcessExecutionHost.acquire_basis` keeps a verified basis keyed by engine, release,
runtime, source root and the run's determinants: the installed version of each library in
`BYTE_LIBRARIES` and `DEPLOYMENT_LIBRARIES`, and the semantic compiler version
(`src/corpus_structure/orchestrate/execution_host.py:74–82, 198`). The existing test varies the
engine and a runtime marker; its name claims root exactness, and the root is never varied
(`tests/orchestrate/test_execution_host.py:68–125`).

*Observation.* Object identity of the returned basis, and the count of calls to
`acquire_data_execution_basis` through the spy the test already installs.

| Case | Change | Literal outcome |
|---|---|---|
| Hit | Same engine, release, runtime and root | The same object; one acquisition |
| Other root | A different `source_root` | A different object; two acquisitions |
| Library version | The version lookup returns a different value for one library, in a new run | A different object; two acquisitions |
| Compiler version | A different semantic compiler version, in a new run | A different object; two acquisitions |
| Changed archive or runtime row under a cached basis | The stored header or runtime row differs | `SemanticRefusal`, "verified execution archive/runtime changed; restart required" (existing, kept) |

*Completeness.* The library set is declared as data. The "library version" case is parametrized
over a hand-written list of library names, and one test asserts that list equals the union of the
two declared tuples. A library added to the run determinants without a case fails that test.

*Precision, gated.* "A version change of a library this basis does not use still reuses" fails
today. Trigger: DA-069.

### 9. Native host frozen profile

*What TDM-11 supplies.* A public production comparison of a selection's profile with a host's
startup observation, callable without starting a process; its compared fields declared as data;
a refusal that names the mismatching field; and a mode of the test peer that misreports one named
field. The baseline, with its eleven inline comparisons and the invented refusal of DTA-045, is in
[controlled boundaries and seams](controlled-boundaries-and-seams.md).

*Division with TDM-11.* The coordinator gives the per-field cases and the real-peer reach
control to TDM-11 as the acceptance of its seam, and gives TDM-13 the check of their form. This companion
therefore writes no second profile table. TDM-13 checks that TDM-11's table has the form above (a
hit control; one case per field with the field named in the refusal; an absent-key case; the
`cuda:1` device accepted for a `cuda` profile; the completeness case against the declared field
set) and adds whatever of that list is missing. If nothing is missing, TDM-13 records the mechanism
as covered by TDM-11 and adds no test.

### 10. Deployment key and seed origin

*What TDM-06 supplies.* A key function over what the build actually runs: the deployed migration
chain, located by production's own constant; the executed upgrade bodies and their bounded import
closure; verified declarations for pinned artifacts and content for unpinned inputs; and the observed server facts
provisioning produces. Provisioning does not enter the key as source: steps that shape the head
at build time are reached from `construct_deployment`, whose closure the key covers, and earlier
host provisioning enters as observed server and role facts. The baseline key reads the wrong
tree, records artifacts by size and modification time, and does not walk the executed bodies
(see the baseline of [preparation identity](preparation-identity.md)). A table written against that
function would pin its defects, so this table waits for TDM-06.

*Observation.* `deployment_key(…)` is a pure function that returns the digest and its components
(root `scripts/native_deployment_key.py:109–158`); it runs on a temporary tree with no database.
Whether a deployment was built or reused is already recorded
(`SemanticDeployment.built`, and `acquisition` in the receipt, root
`scripts/native_test_support.py:305–306, 325`).

| Case | Change on a temporary tree | Literal outcome |
|---|---|---|
| Hit | The same tree twice | Equal digests |
| Touched, unchanged | Every artifact's modification time changed, bytes equal; and the tree copied to another directory | Equal digests. This is the precision case RC07 decides, so it is written with TDM-06 |
| Revision changed | One deployed revision's bytes | Different digest |
| Executed body changed | One upgrade body's bytes | Different digest |
| Import added to an executed body | A body gains an import of a package module; then that module's bytes change | The digest changes at each step |
| Unpinned artifact content changed | Bytes differ; size and modification time restored | Different digest |
| Pinned artifact altered | Bytes differ from the declared digest, with the declaration fixed | Equal key and a loader refusal for the wrong digest |
| Imported module changed | A module in the chain's import closure | Different digest |
| Construction closure changed | The construction entry, or a module it imports | Different digest |
| Server role capability | Change one selected role-policy flag in the typed observation, including BYPASSRLS with name, OID and other determinants fixed | Different digest |
| Effective membership option | Change a relevant membership identity or SET, INHERIT or admin option, with other facts fixed | Different digest |
| Provisioning source alone | A provisioning module that the construction closure does not reach is edited, with the observed server facts unchanged | Equal digests. An edit to provisioning reaches no server until the operator provisions again |
| Lockfile, server principals | Each in turn | Different digest |
| Frozen tree changed | A file under the chain the build does not run | Equal digests |
| The key follows the build | A built head's recorded revision, read from its version table (`public.semantic_alembic_version`) | The file that declares that revision is listed in the key's chain component |

Use the existing catalog observation and provisioning policy for these determinants. Exercise
policy drift on an owned clone or through the typed observation in a unit case. Verify replay
against frozen installed expectations and preserve failed-key replacement. Ordinary host role
mutation is unnecessary for these cases.

The last row is the control for the defect found during authoring. Its expected value comes from
the built database, which is an independent system, not from the key's arguments.

*Completeness.* The components are declared as data (the keys of the returned components mapping).
A hand-written list of component names equals that set, and each name has at least one row above.

*Where it lives.* The pure rows sit beside the existing key tests in root
`tests/scripts/test_native_deployment_key.py`. The re-baseline read that file at `12f57dc4d`: it
has eight tests, unchanged since the authoring baseline, seven on a temporary tree and one on the
real tree. TDM-06 rewrites two of them (the real-tree case and the case that keeps a revision's
function-level import outside the key), and this table is written against the result. The one
related test the conversion added is the principal inventory case in root
`tests/scripts/test_private_cohort.py:600–612`, which is not a key case. The last row reads a
built head's version table, and the root script tests have no database fixtures; it sits in the
package's `tests/test_db_fixtures.py`, which already builds and reuses a head.

*Seeds.* A seed is reused when its recipe key is already present in the worker's registry, visible
as an equal `source_database_oid` in two clones' origins (root
`scripts/native_scenario_seeds.py:83–105, 206`). Recipe sensitivity already has tests
(`tests/test_scenario_recipes.py`), and TDM-07 changes what a recipe contains. TDM-13 adds a seed
table only if TDM-00's re-read finds a recipe field with no perturbation case after TDM-07.

### Gated cases, with their triggers

| Case | Why it is not written now | Trigger |
|---|---|---|
| Precision for kernel-sealed completion | One digest covers the whole kernel; the case fails today | DA-068 decides kernel identity's grain |
| Precision for lowered release facts and for the execution-basis key | One digest, or one version tuple, covers everything; the cases fail today | DA-069 decides implementation identity's grain |
| The undeclared-member case for validity families: a hand-authored expected family that includes a member the declaration lacks, so a derivation that accepts it silently fails | The derivation accepts it today | [DA-070](../../design_review/audit/semantic-model-and-authority.md#da-070) is corrected in production |

Each gated case is written by the change that fires its trigger, in the table that already exists
for its mechanism.

### The cache-scope fixture

*Baseline.* Isolation of the process-global cache is an autouse fixture defined in a support module
(`tests/semantic/selected_query_cache_support.py:13–17`). An autouse fixture defined in a module is
active only in modules that import it; six do. Any other test that reaches one of the six
production callers shares entries with whatever ran before it in the same worker process.

*Target.* One function-scoped autouse fixture in the package `tests/conftest.py` owns isolation
for every test: the cache is cold when a test starts and is cleared when it ends. A test that needs
a warm cache warms it itself, in its body, which is what the tables above do. To avoid importing a
production module into every test, including the many that never touch serving, the fixture clears
the cache only if the cache's module has already been imported in the process; a test that has not
caused that import cannot have filled it. The module-level fixture and its six imports are removed.
`control_frontier` stays in the support module; its correction is TDM-12's.

*Why one owner.* Two production changes are plausible (§4.8): the cache keyed by request content,
under which identical seed clones would share entries, and the cache shared across processes
(DA-075). In either case the one fixture changes, to scope the cache to the test's clone, and no
test module does.

*Rejected.* Keeping the fixture importable and adding the import where it is missing repeats the
cause: the next serving test forgets it. A session-scoped clear is cheaper and wrong, because the
tests in question differ by what is warm.

**Complete consumer scope of TDM-13.** The ten mechanisms above, with tables written for eight,
one inherited from TDM-11 and one deferred to TDM-05's reference cases; the six modules that import
the cache fixture; the five serving modules' keys. Test modules that gain tables:
`tests/semantic/test_pdf_certification_programs.py` or the staging support's consumers (mechanism
1), `test_data_operation_storage.py` (2), `test_data_operation_compiler_native.py`, beside the
conversion's three admission tests (3),
`test_selected_query_cache.py` and `test_demand_results.py` (5), `test_change_impact.py` (6),
`test_file_custody.py` (7), `tests/orchestrate/test_execution_host.py` (8), root
`tests/scripts/test_native_deployment_key.py` and `tests/test_db_fixtures.py` (10). These are the expected homes, not a
requirement.

**Superseded machinery removed.** The module-level autouse fixture and its imports; the fixture
clock shift as the only clock in the custody tests; the claim of root exactness in a test name that
does not vary the root (the test is renamed or gains the case).

**Acceptance evidence.** Record the meaningful failure each selected determinant or shared
comparator case distinguishes. Use a deliberate wrong implementation only when assertion content
and existing independent expectations leave that question unresolved. Prefer one check at the
shared comparator boundary where it covers the same failure across consumers. Retain authored
outcomes and deliberate invalid inputs. The cache-scope fixture is accepted by a `pytester` run
of an inner module containing two tests, run with `-p no:xdist` and in file order, in which the first fills the process-global cache
and the second asserts it empty; the inner module imports nothing from the cache support. A
control run with the fixture disabled shows the second test failing.
Targeted runs with `uv run ci test -- PATH` per mechanism.

**Independence from where the text lives.** The tables call installed functions by name and
assert refusals by SQLSTATE and message, so they did not change when mechanisms 1 to 4 became
generated programs and will not change if validation moves them again. A safety case that
TDM-00's re-read finds added after `12f57dc4d` is recorded, and the table keeps only the missing
rows, as it does for mechanism 3.

## TDM-14 — The refusal contract applied to the new sites

**Needs.** Nothing from this series. The earlier need for TDM-09 at the nine sites of the PDF
integration module is gone; see "Order" below.

**Delivered by the conversion.** No site of the audit's list was converted to the contract, and
the helper is unused in every file the conversion added. The conversion removed the one ordering
constraint, and it added refusal assertions of its own, which are classified below: some already
meet the contract inline, and the rest join the scope.

**The contract.** A refusal assertion establishes three things: a positive control shows the
unaltered case succeeds, so the refusal is caused by the alteration; the assertion names the exact
SQLSTATE; and it names the message or the constraint, so a refusal by a neighbouring guard does not
satisfy it. The helper is `native_refusal(sqlstate, constraint=…, message=…, context=…)` in
`tests/native_refusals.py:13–49`, with its own controls in `tests/test_native_refusals.py`
(four of whose tests request an undefined fixture and are repaired by TDM-01). Six test modules
call it at `12f57dc4d`: `tests/semantic/test_data_operation_storage.py`, `test_native_closure.py`,
`test_pdf_spool_native.py`, `test_pdf_stage_context.py`, `test_pdf_staging.py` and
`tests/test_db_fixtures.py`. For a refusal raised in Python the same contract is met with
`pytest.raises(Type, match=…)` on the specific reason, and for a command-line refusal with the exit
code and the reported reason. No new mechanism is added.

**Reach, effect and retained receipts.** Pair the authored invalid attachment with a valid entry
that reaches the intended guard, then pin the literal refusal and the expected rollback or absence
of committed effects. Use the N13 cardinality and population-witness examples in
[I01](../../plan_improvement_reviews/test-domain-model-and-execution_2026-11-18.md#I01) to compare
predecessor and current guard before changing a SQLSTATE expectation. Retain each attempt's
source/context and failure phase. Successful collection establishes identities and imports.
Only actual setup/body execution establishes those boundaries. Product disposition stays with
its existing owner.

**Implementation vision.** For each site the implementer first decides, from what the case alters,
which obligation should refuse it. Only then is that guard's SQLSTATE and message found in its
owner and written into the assertion. If the observed refusal comes from a different guard, there
are two honest outcomes: the case does not reach the boundary it claims to test and is repaired so
that it does, or guard order is itself a product question and goes to the coordinator. Copying
whatever the run reports into the assertion is the one outcome the package excludes, because it
would pin the neighbouring guard and call the result discriminating.

Two SQLSTATEs need more than the code. `23514` is shared by many checks and always needs the
message or constraint. `P0002` is PostgreSQL's generic "query returned no rows" from a strict
lookup, which any missing row raises; there the helper's `context` argument, which matches the
PL/pgSQL context naming the function, is what separates one lookup from another.

**Complete consumer scope.** The audit's list at `fbd3f2a98`, with lines as they stand at
`12f57dc4d`:

- Bare `DBAPIError`: `tests/semantic/test_established_validity_native.py:224` (six premise
  perturbations; the audit cited `:122`), `test_data_operation_context_fanin_native.py:158`,
  `test_data_operation_binding_native.py:726` (the neighbouring `:713` matches the message
  "checked project" and lacks the SQLSTATE), `test_data_operation_external_native.py:169`,
  `test_data_operation_authored.py:212`, `test_data_operation_population_selection.py:164`, and
  `test_current_pdf_integration_native.py:119, 136, 165, 298` (five forged receipt fields and four
  reader variants).
- Bare `ValueError`: `test_record_publication_native.py:167, 192, 304, 363` and
  `test_definition_model_native.py:156, 163`. Two further sites in the first file raise a specific
  class with no reason: `InvalidContinuation` at `:156` and `RichQueryRefused` at `:203`. The
  class names the refusing component; the first step decides whether the class alone separates
  the intended guard from its neighbours, and adds the reason where it does not. The audit counted
  fourteen cases in the two tests; that count was not re-derived.
- One exception class for many corruptions: `test_execution_admission_expectations.py:103, 122,
  135`.
- SQLSTATE `23514` alone: `test_pdf_shared_streams.py:155–157, 231–233`;
  `test_current_pdf_integration_native.py:354–362`; and two tests added since the authoring
  baseline in `test_data_operation_binding_native.py` (`:848–850`, `:954–958`).
- Exit code only: `tests/test_source_cli.py:231, 274, 367`.

**The conversion's refusal assertions, classified.** The 26 test files added since the authoring
baseline hold more than forty `pytest.raises(DBAPIError)` sites, all written inline. The
re-baseline classified them by the shape of the assertion (a search, not a reading of each
test), so the first step confirms each file's class and whether a positive control precedes each
refusal.

| Shape | Files | Disposition |
|---|---|---|
| SQLSTATE and message both pinned | `tests/semantic/test_native_refusal_detail.py` (exact SQLSTATE, primary message and detail); the claim and release tests (`test_data_claim_native.py`, `test_data_claim_batch_native.py`, `test_data_attempt_release_native.py`), which combine `match=` with the SQLSTATE; the two `23514` sites of `test_closure_native.py` (`:86–100`), which add a message substring | Meets the contract inline. Not in scope; the helper form is adopted only when the file is edited for another reason |
| SQLSTATE only | `test_pdf_access_correspondence_programs.py:54–61` (`22023`, `42501`); `test_data_completion_settlement_programs.py:41–43` (`P0001`); `test_pdf_certification_programs.py:56–76` (seven calls expecting `P0002`, `P0004` or `42501`, with no positive control); `test_closure_native.py:80–85` (`23505`, `P0001`) | In scope. Each gains the message, constraint or context that names its guard, through the helper |
| Message only (`match=`, no SQLSTATE) | `test_data_operation_compiler_native.py`, `test_pdf_companion_read_native.py`, `test_record_policy_native_access.py`, `test_support_trust_native.py` | The message names the guard, so a neighbouring guard does not satisfy the assertion and the discriminating part of the contract is met. In scope for the missing SQLSTATE only, which the helper adds |
| Mixed within one file | `test_pdf_stage_lifecycle.py` (for example `:41–43` with the SQLSTATE alone and `:80–82` with both), `test_data_read_boundary_native.py`, `test_data_product_admission_programs.py`, `test_pdf_validation_read_native.py`, `test_native_release_guards.py`, `test_pdf_companion_adoption_programs.py`, `test_operation_event_programs.py`, `test_pdf_freeze_programs.py`, `test_pdf_inventory_programs.py`, `test_pdf_publication_controls.py` | The first step classifies each site by the rows above; the SQLSTATE-only and bare sites are in scope |

Older sites the audit lists under DTA-001's earlier manifestations have recorded dispositions in
the earlier plan and are not in this package. TDM-00's re-read of changes since `12f57dc4d` is
the scope at entry, because validation may still add tests of this kind.

**Superseded machinery removed.** The inline `getattr(refused.value.orig, "sqlstate", None)`
comparisons at the sites in scope, replaced by the helper.

**Order.** None is imposed. `test_current_pdf_integration_native.py` builds its scenario behind a
controlled converter double (`tests/semantic/current_pdf_integration_support.py:286–302`) that
now returns a reply certified by production's shared emitter, so by reading, not run, its
scenario sets up, and its sites are converted with the others. If a targeted run shows that it
does not set up, the cause is reported to the coordinator and those sites wait for it; they are
not skipped.

**Failure behaviour.** A site where the intended guard cannot be identified from the case is
reported, not guessed.

**Acceptance evidence.**

- For each family of mutations, each case names a distinct reason. Where two cases would name the
  same message, the test says in a comment why they are the same obligation, or the cases are
  merged.
- For each site, the assertion fails when the intended guard is removed and a neighbouring guard
  still refuses. This is established by the assertion's content, a message or constraint that
  belongs to one guard. Try a local wrong edit only where a concrete ambiguity remains, following
  TDM-13's discrimination rule. Assert the expected rollback or absence of committed effects.
- A positive control precedes each refusal in the same test.
- Targeted runs with `uv run ci test -- PATH` for each file touched.

**Literals come from the guard as it stands.** The guards are now generated programs, and some
have a new message or SQLSTATE; each assertion takes its literal from the guard's owner at entry,
after the implementer has decided which guard should refuse.

## Open questions

| Question | Evidence that settles it | Work it constrains |
|---|---|---|
| Can the owner role set a receipt's `validating_kernel_digest` in a rolled-back transaction? | Read the guards on `ops.data_publication_receipt` at entry | Mechanism 2's safety cases |
| What does the requirement read return as the basis when no receipt qualifies? | Run the hit and "failed receipt" rows; by reading the generated program at `12f57dc4d` (`pdf_certification_native.py:456–462`) it is `producer-certified` with a null receipt | Which column mechanism 1 asserts |
| Which determinants do the five serving cache keys carry, and which have a budget? | Read each key | Mechanism 5's per-module cases |
| Does any pure test rely on the cache module being imported by the fixture? | Search for uses of the cache with no import of serving code | The fixture's import-free clear |
| Is the profile table written by TDM-11 complete in the sense of "The perturbation table"? | Read TDM-11's delivered tests | Whether TDM-13 adds anything for mechanism 9 |

**Production observations** this companion raised are rows of the coordinator's
[production context](../test-domain-model-and-execution_2026-11-17.md#handovers): the requirement program reporting `producer-certified`
before it knows a prior receipt qualifies; the cache not reporting whether it answered; and
`LOWERING_FILES` as a hand-kept list. None is a remedy this series selects.

## State

| Package | State |
|---|---|
| TDM-13 | Not started |
| TDM-14 | Not started |
