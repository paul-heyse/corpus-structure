# Scenario composition and preparation

**Status:** Implemented; operator-selected verification accepted2026-11-02. The
[coordinator](../test-architecture-and-evidence_2026-11-02.md) owns TA-05/06 and DTA-005/007/009/018 state.

## Target and foundation

Keep independent examples readable and shared mechanics deep enough to hide volatile setup.
Current useful foundations include acquire_pack→compose_pack_inputs→prepare_packs, sealed native
schema deployment, `native_record_fixtures.py`, explicit invalid-input controls and existing cache
compatibility checks. `test_domain_operations.fixture`, `test_agent_resubmission.source_task`,
`test_pdf_integrated.pdf13_db`, `test_pdf_staging.private_build` and serving install_pack/completed
are the initial cross-module hubs; follow all their maintained consumers before moving them.

A public product composition claim should exercise the real composer; a local kernel test can
keep a minimal synthetic model. Do not move hand-written expected values into the production model.
No generic scenario registry, class hierarchy or flag-driven universal builder is selected.

## TA-05 — Coherent scenario support and reusable preparation

Inventory each hub's inputs, hidden defaults, effects and consumers. Extract shared mechanics into
ordinary importable test support organized around assurance responsibility, not files named test_*.
Expose meaningful alternatives explicitly: for example two reports and Person identity scope are
independent inputs rather than an implicit coupling. Use narrow builders/pytest fixture dependencies
and parametrization; keep exact expected outcomes at the case that owns them. Constructor validation
must not repair deliberately invalid inputs before the intended boundary.

Keep immutable acquisition and preparation separate from mutable database setup. Acquired bytes,
compiled release products and expected fixed references have distinct authority/dependencies. Reuse
only under complete input/model/profile/library dependencies and immutable lifetime. Preserve
acquire/compose no-I/O/no-compile and prepare_packs single-root-compilation controls. Avoid expensive
preparation at import time when focused consumers do not require it.

For read-mostly matrices, prefer reuse of immutable compiled products first. A sealed seeded scenario
template may remove repeated publication when TA-01 establishes its policy and isolation contract;
it must produce fresh clone state, preserve actual purpose commits, and retain its validity inputs.
Do not share mutable database state or a rollback-only transaction across tests needing committed
cross-session effects. Deployment/publication/race/cancellation tests keep the behavior they assess.
Do not introduce persistent preparation caches without a demonstrated reuse requirement.

Migrate each extracted hub and all its consumers in one coherent slice. Remove replaced helper
implementations/imports once callers move; retain independent reference material. Do not make setup
changes solely by regex or rename case semantics to force existing assertions through.

Acceptance: a focused case imports only needed support; changing an unrelated scenario default does
not change its meaning; two users of reused preparation have isolated effects; changed model/profile/
input membership cannot reuse stale products; a genuine publication/cleanup failure remains visible.
Controls for case-construction semantics are warranted where a shared consequential builder can
silently change many claims; no test for every trivial fixture is required.

## TA-06 — Independent cold evidence alongside warm reuse

`prepare.py` caching and full verification through releases.py mean load==already-prepared does
not independently exercise cold compilation. Preserve warm read reuse and explicit runtime/custody
refusals; this is not authorization to disable production caching. Use existing fresh-interpreter
controls as a model: controlled acquired bytes/profile/dependencies enter a fresh process and the
result is compared with independently specified artifact/content obligations. Separate cross-process
cold determinism from cache-identity/warm-read assertions in names and observations.

Run cold construction once for each materially different promised contract, not redundantly for
every downstream assertion. Keep negative changed-runtime and corrupted-source controls so a warm
hit cannot become an admission receipt. Compare real semantic contents/artifact identity under the
promised equivalence; a source-hash match alone cannot establish compiler correctness.

Acceptance includes a cold positive with independent obligations that reject materially wrong
compiler output, changed input/profile,
and a warm repeated read with positive acquisition/compile call observation where that work claim
is the subject. A deliberately cold deployment/migration test must remain cold after TA-05 changes.
No parser-admission floor or runtime target follows from these requirements.

## Mechanisms, alternatives and sources

Pytest9.2.0 fixture dependencies and scoped fixtures compose resource lifetimes; yield cleanup and
request.addfinalizer protect different partial-setup points. Register a finalizer after successful
acquisition when it must survive later setup failure. Neither protects SIGKILL; TA-02 owns that scope.
Use ordinary immutable values/functions and existing production preparation rather than a bespoke
fixture orchestration engine. Hypothesis/composite strategies remain candidates for meaningful
structural variation, not default replacements for small hand-written examples.

- [Pytest9.2.0 fixtures](https://github.com/pytest-dev/pytest/blob/9.2.0/doc/en/how-to/fixtures.rst)
- [Hypothesis capability reference](../../libraries/analytical_infrastructure/hypothesis.md)
- [Test assessment](../../design_review/design_principles/core/test-assessment.md)
- [Production warm-opening contract](../production-efficiency/runtime-preparation-and-adoption.md)

TA-01's selected native mechanism constrains only database reuse, not extraction of pure support.
Quantified speed benefit remains unmeasured. Source-established removal of repeated preparation
must name what was removed and which independent guarantees remain.

## Implementation boundary — 2026-11-02

`agent_scenarios`, `domain_scenarios`, `operation_scenario_support`, `pdf_staging_support`,
`pdf_integration_support` and `serving_scenarios` now own the shared mechanics. Maintained
consumers no longer import the selected initial test hosts for those builders. Report count and
Person identity scope are separate
`build_domain_case` inputs. Pack-serving scenarios use production `prepare_packs`; isolated
synthetic scenarios retain their declared scope.

[ADR-0048](../../adr/0048-populated-native-scenarios.md) selects only the repeated default completed
serving population for session-local reuse. Three read consumers clone its sealed source instead
of repeating proposals/finalization. OID, policy, client absence, recipe and prepared manifest are
checked before cloning; purpose connections observe the actual fresh clone. Existing receipt
events carry seed origin separately. Query-pack/coverage variants and producer/lifecycle tests
remain cold. Isolation, changed-recipe refusal and partial-build cleanup have dedicated native
controls; no persistent cache, shared mutable result, second janitor or performance claim follows.

Cold semantic artifact obligations run in a fresh interpreter in `test_prepare.py`; warm identity,
archive custody and changed-runtime refusals remain separate controls. The coordinator records
final-source qualification and any unavailable required obligations.
