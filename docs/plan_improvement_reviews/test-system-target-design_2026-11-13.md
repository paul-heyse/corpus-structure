# Test-system target design: remove repeated work while preserving evidence

**Plan-improvement review · 2026-11-13.** Subject: the
[coordinator](../plans/test-system-target-design_2026-11-13.md) and all seven companions.
The operator emphasized efficiency and shorter focused and full test runs. This assessment
recommends amendments; it changes no plan, ADR, implementation or finding disposition.

## Baseline, method and combined judgment

Source was inspected at `2687fa1f8b5d5f6aa55341c8c01e3e602861ac68`, initially clean.
Concurrent documentation commit `c76a7fa9d` changed D3 and the DDO checkpoint during review;
its current native-test ownership text was reconciled before publication. No concurrent
production or test changes were included. Plan authoring baselines and historical receipts
keep their original dates and applicability. TS-00–23 remain unstarted or DDO-gated.

All recommendations and expected benefits below are **Proposed**. Source observations are
**Interface-checked by source inspection, 2026-11-13**. No test, provider, database operation,
probe or benchmark was run for the assessment. No speedup is measured or claimed.

The root and three independent read-only design reviewers covered lifecycle/isolation,
support/preparation/scheduling, and evidence/DDO integration. We read the coordinator and
seven companions, the source review and supporting classifications, relevant audit findings,
architectural owners and governing decisions, and decisive implementation/consumer paths.
The selected standard was core 3.3, heuristics 1.0, test-assessment 1.2 and the repository
binding, with code-intelligence 1.4 applied to source/identity/evidence fidelity questions.
This is an improvement review, not a refreshed diagnostic audit or formal acceptance review.

**Retain the target direction and amend its preparation boundaries.** The largest opportunities
identified by structure remove work before adding concurrency: avoid a dedicated verification
clone, avoid parsing historical artifacts to answer a one-revision question, share pure
preparation at its actual input boundary, and stop rebuilding stable SQL/setup per refusal case.
The target's existing worker sizing, staged builders and general seed mechanism are suitable
foundations. Several proposed details would otherwise forfeit their intended savings.

The domain distinctions are useful: deployment, preparation, population, isolation and evidence
class have different validity premises. FP-01–06/A1–A3 favor keeping those premises with their
owners, explicit scenario values and narrow composition. FP-07/A4 and H5/H12/H14/H20/H28 favor
eliminating unrelated acquisition and preparation. Reuse remains conditional on isolation and
independent observations; the assurance amendments below enable the efficiency changes rather
than establish a new test framework. No blanket architectural acceptance or completion is given.

Preserve one authenticated lifecycle owner, policy replay, real purpose logins, fresh committed
clones for concurrency/publication claims, cold deployment controls and authored expectations.
Retain TS-09's reach/reason/effect contract, TS-14's asymmetric preservation and redaction
examples, TS-15's explicit digest policy, TS-16's real spawned-process controls and shortened
grace windows, TS-19's literal identity vectors, and unchanged Hypothesis evidence. Their
assurance purpose earns their work.

Paths below beginning `tests/` or `src/` are relative to `python/corpus-structure/`;
`scripts/`, root `conftest.py` and `docs/` are repository-root paths. Line citations locate
the inspected source, not a promise that later lines stay fixed.

## Amendments with the strongest direct efficiency value

<a id="I01"></a>
### I01 — Verify the first useful clone and resolve only its requested expectation

**Priority: high. TS-02/05/08 and the directly consumed production checker.**
The [lifecycle design](../plans/test-system-target-design/native-lifecycle-and-deployment.md#verification)
forces a per-worker session clone for reused-head verification. A focused commit-only or
seed-only selection otherwise needs no such clone. Production's checker accepts an arbitrary
maintenance `Connection` and rolls back its catalog-check savepoint
(`src/corpus_structure/semantic/execution_admission.py:149–187`).

Let the deployment acquisition owner track pending/completed verification per process and
perform it on the first actual head clone, before exposing that clone or running a seed builder.
That can be a session clone, commit clone or seed-build clone. On a stale head, discard that
clone, obtain the replacement through the same lifecycle and retry before consumer effects.
Preserve the operator's once-per-process verification, stale-head diagnostics and receipts.
Retaining a dedicated verification clone is locally simpler but adds a creation/drop to precisely
the focused loop the target is intended to improve.

There is a second preparation boundary to correct. `_revision_expectation` calls `_expectations`,
whose first-process `_frozen_expectations` reads revision declarations and reads, hashes and
parses every declared admission artifact before returning one requested revision
(`execution_admission.py:104–110,357–463`). Provide revision-targeted expectation resolution:
reuse the artifact parser, follow predecessors when an expectation is inherited, and load the
selected artifacts. Keep whole-history discovery for callers whose contract needs it. A bounded
revision metadata index may still be needed; the saving is avoiding unrelated artifact processing,
not assuming revision discovery has no cost.

This deliberately extends the plan's production-change boundary to the checker it newly places
on every reused-head process. It completes the same reuse intervention, not a production audit.
Preserve selected-artifact digests, unsafe-path/ambiguous-revision refusals and inheritance.
Prefer this correction to the coordinator's once-per-day verification fallback, which would
weaken the accepted assurance instead of removing unrelated work. FP-07, DP-09/10/23, H5/12/20.

**Closure:** commit-only and seed-only runs verify without creating `ci_test_<pid>`; mixed
consumers verify once; a stale head fails before consumer effects. Current and inherited revision
expectations remain equivalent, selected malformed artifacts refuse, and unrelated admission
artifacts are not loaded for an explicit revision. These are functional observations, not timing targets.

<a id="I02"></a>
### I02 — Give driver-only controls an infrastructure database

**Priority: high for focused infrastructure runs; requires a rule proposal. TS-00/01/05.**
TS-05 retains three connection-lifecycle modules on the complete semantic head through
`shared_clone_engine`, then introduces a post-test durable-state comparison. Inspected claims in
`tests/db/test_store.py:24`, `test_lifetime_native.py:112,162` and
`test_adbc_lifetime.py:94,300` concern pools, scalar SQL, JSON, notices, cancellation and backend
settlement. The durable-write case creates an ordinary table; it does not need semantic schema.

Use an explicitly named infrastructure clone from provisioned `cs_template`, through existing
acknowledged creation, leases and authenticated cleanup. Give durable-write cases an isolated
infrastructure clone; preserve extension checks, real drivers and actual authentication. Inspect
the remaining consumers before migration and keep semantic-head fixtures for tests that call
semantic guards. A small base distinction suffices; no plugin or parallel lifecycle is needed.

Compared with retaining the semantic base, this removes head-key construction, semantic
verification and possible migration build from backend-only focused runs. It also avoids inventing
a semantic durable-state comparator for these connection exercises. This reconsiders the recorded
shared-clone choice and belongs in TS-00's decision route if adopted. FP-01/06/07, H5/12/25.

**Closure:** backend-only selections acquire no semantic head; real cancellation/reuse still runs;
durable writes stay isolated; an actual semantic consumer explicitly requests its semantic fixture.

<a id="I03"></a>
### I03 — Key each pure preparation by its own inputs

**Priority: high. TS-03/06/07/08.**
The [support design](../plans/test-system-target-design/scenario-and-support-ownership.md#ts-07--staged-builders-focused-consumers-and-the-recipe-memo)
memoizes by the whole scenario recipe. That recipe includes later publication text, blank cells,
task method and configuration. `prepare_record_source` consumes composition transforms and
`additional_methods` (`tests/semantic/native_record_fixtures.py:208–277`); structural replay
varies text after preparation (`test_structural_native_replay.py:57–70`). Whole-recipe keys retain
correctness but repeatedly assemble/hash identical preparation and keep duplicate results.

Project a small `RecordPreparationRecipe` from the scenario recipe and key the pure-stage memo
by it. Keep full scenario recipe plus head as the seed key. Apply the same distinction elsewhere
only where a meaningful shared prefix exists. Production's eight-entry cache alone does not
remove input assembly before its lookup. No general dependency-tracking framework is needed.
FP-04/07, DP-09/10, H12/14.

**Closure:** recipes differing only in later-stage text reuse one prepared acquisition; changed
composition or methods acquire another. Fresh effectful stages and independently authored
expectations remain. Coordinate the override policy in I04 before allowing memo reuse.

<a id="I04"></a>
### I04 — Define the override lifetime across all affected caches

**Priority: assurance prerequisite for I03. TS-03/07.**
The snapshot companion leaves parser-result cache identity unresolved. Source resolves the
premise: `MathContext.key()` has symbols/profile/rules/conventions, without implementation
digests or runtime identity (`src/corpus_structure/methods/math/grammar.py:366`). Its result
memo uses that key (`:989`); `analysis_contracts.py:533` does not transfer runtime identity into
the grammar context. An implementation override can therefore share a context key with an
ordinary cached result.

Choose one explicit scope rule. Prefer bypassing reads and writes of snapshot-dependent
support/context/result caches while an override is active, preserving the ordinary warm cache.
Separate snapshot-keyed namespaces are a credible alternative if overridden preparation itself
needs reuse. Merely clearing on exit leaves ordinary entries readable inside an override.
Keep the affected cache set bounded to actual snapshot dependencies. FP-05/06, DP-09/18, H19.

**Closure:** nested overrides with unchanged profile ids cannot consume ordinary cached answers
contrary to their override scope or poison later ordinary preparation; exceptional exit restores
ordinary behavior. This strengthens the snapshot seam without disabling normal caching.

<a id="I05"></a>
### I05 — Match affinity to the fixture actually shared

**Priority: high. TS-06/12 and TS-10 families.**
The [affinity design](../plans/test-system-target-design/run-shape-and-scheduling.md#ts-12--affinity-groups-for-designated-preparation)
says a qualifier names the fixture's defining module, but its algorithm compares that qualifier
with the test item's module. After TS-06 merges statistics setup into a support module, its
proposed single support-qualified row matches no consumer item. The intended sharing would fail.

Prefer distinctive shared fixture names for merged statistics preparation and rollback families.
Keep consumer-module qualifiers for genuinely module-local generic fixtures. Resolving actual
fixture-definition ownership is an alternative, but carries pytest-internal coupling unnecessary
for these explicitly owned fixtures. Deduplicate matches by group value before detecting
conflicts: `prepared` and dependent `policy` may legitimately designate the same group.
Preserve xdist's existing scheduler and logical receipt identity mapping. FP-01/07, DP-10/20, H12/22.

**Closure:** imported shared fixtures receive the intended group, unrelated same-name fixtures
do not, repeated matches for one group succeed, distinct groups refuse, and retry identities survive.

<a id="I06"></a>
### I06 — Remove unconditional CLI registration from package collection

**Priority: early, low integration burden. TS-06, alongside TS-04.**
Promote the existing W2 candidate without requiring a benchmark first. Package conftest imports
both `corpus_structure.cli.app` and `cli.output` at module load (`tests/conftest.py:37–38`).
`src/corpus_structure/cli/__init__.py` eagerly imports the command registry, so moving only
the app import would leave that activation intact.

Defer both imports until the `Cli` invocation that consumes them; keep the same runner,
settings factory and output contract. This removes an unconditional collection dependency from
non-CLI selections with a small local change. Other test imports may still activate the CLI;
no claim is made that every non-CLI run will avoid it or that its duration dominates. Retaining
eager imports has no demonstrated semantic requirement here. FP-01/07, H5/6/12.

**Closure:** a cold non-CLI collection can load package conftest without that path importing
the command registry; existing CLI fixture consumers retain their behavior. Keep the separate
second-interpreter argument-screening candidate conditional until its custody contract is resolved.

<a id="I07"></a>
### I07 — Reuse stable DDO refusal and binding setup through the planned seed operation

**Priority: high once seed/isolation contracts exist. TS-09/17/18/20, consuming TS-05/08.**
Two concrete consumer amendments give the existing machinery more useful work to amortize.

The forged-graph family remains commit-class in TS-18 because `attach` commits first. Source
then reads the authentic selection, mutates it and calls `register_data_demand`
(`tests/semantic/test_data_operation_storage.py:1998–2035`). Its generated request/task is
unrelated to the refusal. Use the STORAGE rollback family, connection-oriented demand setup,
a same-state valid-registration control in a rolled-back savepoint, and the four forged cases
with exact diagnostics/effects. This removes repeated clone and unused task setup. Retain commit
isolation if a required cross-session/post-commit effect is discovered; none was identified in
the exercised path. Do not generalize that classification to every DDO refusal.

The binding-native fixture reparses source SQL and installs the same functions for each case
(`test_data_operation_binding_native.py:43–72`). A source-function binding recipe can install
them once in a sealed per-worker seed, then lend rollback-family connections. Include source
bytes in the recipe's preparation dependencies. Keep source-installation controls and actual
deployed-function checks distinct. Temporary identity helpers in `pg_temp` are connection-local
and must not be assumed to survive a clone (`test_data_operation_identity_native.py:59–136`).

Compared with retaining per-case builds, these amendments reuse TS-08 rather than add another
cache. Their burden is narrow helper adaptation and one recipe; TS-20 gains a seed dependency
for this optimization. FP-03/06/07, DP-09/10/23, H5/12/19/23.

**Closure:** authentic inputs reach the same guards, all four mutations discriminate, case
effects roll back, stable function installation builds once per worker, and mutations cannot
affect later cases. Preserve separate real concurrency/publication controls and item provenance.

## Assurance and lifecycle details needed by the combined intervention

<a id="I08"></a>
### I08 — Match binding parity evidence to the observed boundary

**Priority: required clarification before claiming TS-20's promised parity. TS-17/18/20.**
TS-20 promises independently authored members, roles, positions, support and witnesses through
compiled and native paths. The named native fixture omits `ddo_require_binding` and its evaluator
returns a Boolean from `ops.ddo_binding_test` (`test_data_operation_binding_native.py:66,183–188`);
the compiled path returns a full `BindingResult` (`src/corpus_structure/semantic/data_operation_bindings.py:1291`).
Boolean agreement alone cannot establish that full result contract.

Retain cheap expression/codec controls. Use authored full expected bindings for the compiled
executor and a bounded native-admission executor checking independently authored accepted and
refused envelopes through the protected boundary. Share admitted seed/rollback setup from I07;
do not turn every helper case into a full demand journey. Feeding only the compiler's output to
native admission could preserve the same selection error and is insufficient as the oracle.
FP-02/04/06/07, DP-23, test-assessment §§1/4/5; DDO-03 still owns production semantics.

**Closure:** changed member/position/source/context/witness can fail even if the expression
remains true; unknown and present-empty stay distinct. Keep useful path-specific controls.

<a id="I09"></a>
### I09 — Carry applicability and native provenance through the existing receipt consumer

**Priority: before TS-13's first managed run and fixture migration acceptance. TS-05/13/18/22/23.**
TS-13 says no receipt change is needed. `_node_status` can label an optional skip inapplicable,
but `classify` adds every selected identity to the required union and treats it as missing
unless some applicable receipt passes (`scripts/test_receipts.py:457–489,931–943`). A policy
declaration/property alone therefore cannot make the promised ordinary scope qualify.

Prefer an explicit ordinary selection policy that excludes opt-in provider identities from
its required selection, while an explicit provider-required selection includes them. If retaining
observed optional nodes in ordinary runs is useful, instead carry a required-versus-observed
projection through manifest, classifier and CLI. Choose one mechanism through the policy owner;
do not count inapplicability as a pass or silently weaken DDO-12's required-provider obligation.
Missing prerequisites must be decided before scenario setup. Preserve multiple missing reasons
as an aggregate value: `_properties` currently flattens duplicate property names into a dictionary.

Also migrate native fixture classification and item-bound observations with the fixture names.
Package conftest derives `db` from fixture closure; `qualification_plugin.py:125` derives
`native_required` from it; `_union_node_status` requires item-bound acquisition
(`test_receipts.py:1391`). Current transitive fixtures often preserve classification, so an
existing bypass is not established. This is an explicit migration obligation: a shared seed/session
record alone cannot attest every consumer. Use existing connection observation where needed,
without another registry. FP-04/05/06, DP-21/23, CI-04/11.

**Closure:** ordinary controlled scope can qualify without provider setup; explicitly required
provider scope stays blocked when assets are absent; multiple missing reasons survive; teardown
defects remain failed. Representative read/rollback/commit/seed/cold consumers remain native-required
with item-bound context, while pure support consumers acquire no native fixtures.

<a id="I10"></a>
### I10 — Keep deployment construction's dependencies and publication lease explicit

**Priority: fold into lifecycle work; key extraction is a lower-priority enhancement. TS-01/02/08.**
TS-02 hashes all of `scripts/native_test_support.py` as the build procedure while TS-08 adds
seed orchestration there. Seed/sweep/receipt edits would invalidate the head despite unchanged
deployment construction. Prefer a small deployment-construction module whose actual inputs
are included by the key, keeping `PgAdmin` as the single lifecycle authority. Avoid source-fragment
hashing or manual version tokens. Retaining the whole-file key is conservative and correct,
but makes reuse less effective during this undertaking. FP-01/04/07, H13/14.

Independently, make the build database's own lease explicit through sealing and rename.
The failure table assumes that lease, while acquisition step 4 states acknowledged creation
without naming it. The final head's lease cannot protect a differently named build residue
from the sweep. Preserve OID/nonce disposal authority through publication and failure cleanup.

**Closure:** seed/sweep-only changes need not rebuild a head; actual deployment-construction
changes invalidate it. A sweep cannot retire a live build, and failed publication disposes only
the acknowledged owned database. This completes existing custody, not a new recovery framework.

<a id="I11"></a>
### I11 — Keep optional registry machinery local to its scenario owner

**Priority: optional simplification within TS-06.**
The recipe-type builder association serves generic seeding. The additional global composition
and provider-patch registry has no demonstrated need for independently supplied extensions in
the inspected consumers. Keep those named choices and patch application beside the relevant
builder using ordinary values/functions; retain minimal recipe-type dispatch if it remains useful.
Compare this with the proposed common registry by import-order knowledge, extension edits and
diagnosis, not line count. Revisit if independently supplied scenarios need registration.
FP-01/03/06, DP-16/17, H25/27. No duration benefit is asserted for this simplification.

## Interactions, adoption and evidence limits

Recommend adopting I01, I03, I05, I06 and I07 as the main efficiency amendments. I04, I08 and
I09 preserve the meaning of the resulting reuse/evidence and should travel with their consuming
packages. I02 is worthwhile for the focused infrastructure loop but explicitly reopens the
shared-semantic-clone choice through TS-00. I10's lease clarification belongs with publication;
its module extraction and I11 should not delay the principal work if their local burden grows.
The whole intervention remains the same test-system undertaking; no extra audit, process gate,
performance service or bespoke scheduler is recommended.

Prerequisite order differs from value: define the snapshot/override validity before memo reuse;
establish recipe, seed and transaction contracts before migrating families. Correct fixture
affinity in the same change as shared support moves. Add the targeted checker route before
judging reused-head verification too expensive. Preserve TS-05/06/17 readiness for new DDO-06
native tests, and the existing TS-21/22 package gates. No recommendation reduces the final
required functional/provider/nonfunctional obligations or substitutes a bounded pass for them.

The coordinator's DTA and F identities remain with its findings table; this review's I references
are proposals, not new execution dispositions. Current DDO coordinator text at lines 209–217
already records RC03, TS dependencies and retirement ownership; its contracts companion at
366–370 incorporates RC03. The test plan's corresponding handover text is stale. The old direct
lease-update premise also no longer describes storage lines 2116–2147, which now use protected
`release_data_attempt`. Reconcile these facts during plan revision without duplicating DDO status.

The review inspected representative decisive consumers, not every one of the many fixture
migrations or TS-21 retirement candidates. Their classifications require package-time semantic
inspection; token searches are navigation and closure aids, not proof that behavior transferred.
No deployed catalog, actual provider or live thread/transaction behavior was exercised. Historical
duration figures were not refreshed. Improvement magnitude, bottleneck ranking and combined
runtime remain unmeasured; the recommendations identify concrete work removed by structure.

After implementation, existing focused receipts can establish acquisition/build counts and
retained behavior. Timing investigation is warranted if a material duration uncertainty remains
and would change the next decision; it is not a prerequisite to removing established redundant work.
Formal assembled review and final-source qualification remain TS-23's obligations.

## Publication checks

- **passed, 2026-11-13:** `just turn-end` (ADR index and formatting).
- **passed, 2026-11-13:** `uv run ci docs check`, initial publication result
  `2152cd9ac598460caa45712fe1d4454c`: 1,243 canonical pages, zero link errors.
- **passed, 2026-11-13:** `git diff --check` for publication edits.
- **not_run:** `uv run ci test`, `uv run ci check`, provider/native execution and benchmarks;
  this assessment changes documentation only and makes no product qualification claim.
