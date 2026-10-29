# Test code design principle audit

This is the separate living diagnostic account for test code, test evidence and shared test
infrastructure. The [skill](../../../.claude/skills/design-principle-audit-tests/SKILL.md) owns
the audit method; the [repository binding](../design_principles/binding/corpus-structure.md#test-code-design-principle-audit)
owns invocation, finding identity and follow-up routes. The
[test-assessment companion](../design_principles/core/test-assessment.md) supplies the test-specific
interpretation of the selected core and applicable domain profiles.

<a id="baseline"></a>

## Baseline

| | |
|---|---|
| Audited source | commit `c6f8d16` (T0, 2026-10-29T13:22-04:00) plus one dirty file, a one-line change to `tests/semantic/test_execution_release.py` |
| Reconciled through | commit `c50a747` (2026-10-29T13:40-04:00). Concurrent SP-C03/SP-C05 integration landed during the audit. Between T0 and this commit: no test module was added or removed, there were no harness or configuration changes, and 28 test files were modified (mostly reformatting). Every cited claim was rechecked at this commit, and line numbers cite it |
| Date | 2026-10-29 |
| Standard | core 3.3 (principles; efficient-architecture heuristics 1.0); test-assessment companion 1.2; code-intelligence profile 1.4, applied by analogy (CI-04, CI-06, CI-10, CI-11, CI-12); [binding](../design_principles/binding/corpus-structure.md) |
| Kind | First test audit; there is no preceding baseline. The [broad audit](../audit/README.md) (`024bb33`) examined tests only for oracle independence, and its observations keep their own baseline |
| Inventory | `uv run --no-sync pytest --collect-only -q`: **passed**. 144 modules and 2,017 tests at T0, 2,028 at reconciliation; no collection errors |
| Publishing commit | The commit that adds this account, distinct from the source baseline |

Paths in this account are relative to `python/corpus-structure/` unless they start at the
repository root (`docs/`, `domains/`, `fixtures/`, `sources/`, `justfile`, `pyproject.toml`).

## Scope

The operator approved the following scope on 2026-10-29. The semantic-model pivot is
mid-execution and phase 0 will be re-scoped after it, so depth follows what survives the pivot.

- **Tier 1, deep (survives and carries SP-10):**
  - shared infrastructure: `tests/conftest.py`, `tests/semantic/conftest.py`, root
    `tests/conftest.py`, the pytest configuration and the `justfile` test routes;
  - the production caches and harness modules that tests depend on;
  - all of `tests/semantic` (46 modules);
  - the data they consume.
- **Tier 2, representative (foundations the pivot reuses):**
  - core evidence, locator, TeX, canonical, frame and method tests;
  - math, ingest and llm;
  - `pool/test_engines`, `schema/test_relational` and `test_rules`, `evaluate/test_equivalence`,
    `test_settings`;
  - their frozen reference data (`tests/data`, `math/data`, `llm/data`, `ingest/data`,
    `fixtures/s0`, `fixtures/trace`, `fixtures/tex`).
- **Tier 3, transfer lens only (pivot SP-08/SP-09 migrate or retire these):**
  - legacy `db`, most of `orchestrate`, `consolidate`, `acceptance`, `evaluate/golden`, `agent`,
    `validate`;
  - the core key/candidate/shape/dispatch tests, the schema pack/stage tests and `pool/test_pool`.
  - These were examined only for assurance that must survive retirement and for causes that recur
    in surviving code ([retirement transfer](retirement-transfer.md)). No per-test findings are
    made on code slated for deletion.
- **Light:** `tests/scripts` and `tests/evidence` (process tooling).
- **Rust:** the crate has no tests.
- **Excluded:** spike code and its instruments under `docs/design_review/evidence/` (tests that
  read evidence folders directly stay in scope as a dependency); `build/` environments.

Production contracts and dependencies were read as context for judging the claims. This account
does not imply that the enclosing production system was audited or qualified.

## Method

- **Contributors.** Three read-only contributors assessed the subject through cross-cutting lenses
  under the audit skill, so that causes shared across directories would surface:
  - evidence independence and discrimination;
  - structure, composition, coupling and domain meaning;
  - execution fit, isolation, lifecycle and the qualification route.

  Each considered FP-01–FP-07 and reported material observations outside its lens. Leads from
  three planning explorations were handed over explicitly as unverified.
- **Coordinator verification.** The coordinator read every decisive source cited by a finding,
  including the DDL and SQL behind [DTA-001](evidence-and-discrimination.md#dta-001), and merged
  candidates by structural cause. Execution-fit and authority views of one cause became one finding
  with both sets of criteria. Each finding was mapped against existing owners and reconciled against
  the concurrent commits.
- **Change scenarios.** Used where they exposed coupling or blind spots:
  - SC1: add a `semantic_alembic` migration;
  - SC2: bump the compiler version or profile;
  - SC3: a lifecycle guard changes;
  - SC4: retire `core.keys` or the old store;
  - SC5: add a dynamic class or a second pack;
  - SC6: upgrade an ontology or library pin.
- **Execution.** Only the collection inventory above and one read-only catalog query on the 5434
  cluster (2026-10-29T13:36-04:00, reported in
  [DTA-002](execution-and-qualification.md#dta-002)).
  - No test, timing, benchmark or mutation campaign was run.
  - Contributors ran small read-only checks (an AST count of native items, comparing a macro table
    with its owner, resolving catalog indexes). Their outputs are cited as observations and were
    not retained as evidence.
- **Leads examined and rejected:**
  - *Locator keys in `fixtures/s0`/`fixtures/trace` come from the production generator.* Locator
    correctness has independent grounding, so the keys act only as join keys.
  - *Siegrist profile compilation cost and spaCy loading.* Immaterial.
  - *Test-database name collisions.* Names are pid/uuid-qualified, and fixed-suffix legacy clones
    fall under the lease.
  - *The `trusted_execution_inputs` monkeypatch beside a cache.* Sound, because callers look the
    name up at call time and the cache is keyed on content.

## How the foundations were assessed

- **FP-01 (separation of concerns) and FP-03 (composition).**
  - Responsibility boundaries in test support were examined: where builders live, what each fixture
    fuses, how support is shared.
  - Findings: [DTA-009](support-structure.md#dta-009) (builders hosted in test modules),
    [DTA-002](execution-and-qualification.md#dta-002) (isolation, bootstrap and migration-as-subject
    fused in one fixture), [DTA-005](support-structure.md#dta-005) (no composable release
    capability).
- **FP-02 (stable contracts).**
  - The contracts tests protect were examined: refusal reasons, catalog addressing, descriptor
    shapes, observation through internal names.
  - Findings: [DTA-001](evidence-and-discrimination.md#dta-001),
    [DTA-010](evidence-and-discrimination.md#dta-010), [DTA-008](support-structure.md#dta-008) and
    the second half of [DTA-007](evidence-and-discrimination.md#dta-007).
- **FP-04 (explicit domain model and scoped semantic authority).**
  - Whether tests consume the model's authority or restate it, and whether expectations are
    independent of the code under test.
  - Findings: [DTA-005](support-structure.md#dta-005), [DTA-008](support-structure.md#dta-008),
    [DTA-011](evidence-and-discrimination.md#dta-011), [DTA-012](support-structure.md#dta-012) and
    the transfer obligation [DTA-004](retirement-transfer.md#dta-004).
  - Much tier-1 evidence is deliberately independent; see
    [strengths](evidence-and-discrimination.md).
- **FP-05 (explicit structure and constraints).**
  - Whether enforcement points are actually discriminated, and whether outcomes are explicit.
  - Findings: [DTA-001](evidence-and-discrimination.md#dta-001),
    [DTA-003](execution-and-qualification.md#dta-003),
    [DTA-013](evidence-and-discrimination.md#dta-013).
- **FP-06 (local reasoning).**
  - Hidden defaults, magic expected values, order dependence and diagnosis.
  - Findings: [DTA-009](support-structure.md#dta-009),
    [DTA-007](evidence-and-discrimination.md#dta-007), and the reason-blind refusals in
    [DTA-001](evidence-and-discrimination.md#dta-001).
- **FP-07/A4 (execution fit), the governing efficiency criterion.**
  - Assessed statically through H2 and H12 (preparation lifetime versus isolation unit), H13, H14
    and H19 (reuse and its validity premises), H20 (repeated unchanged conclusions), H24 and H25
    (cleanup and recovery scaled to parallel sessions) and H27 (full lifecycle, including growth
    under SC1).
  - One material shortfall was established: [DTA-002](execution-and-qualification.md#dta-002),
    repeated head bootstrap per native test, growing as revisions × native tests. It is demonstrated
    repeated work, not a measured bottleneck.
  - Other repetition was judged immaterial: profile compilation, uncached `schema/model.load()` in
    tier 3, spaCy.
- **Domain profile.** The code-intelligence profile applied by analogy, not as a direct subject:
  - CI-04 unknown is not absent: skips folded into success ([DTA-003](execution-and-qualification.md#dta-003));
  - CI-10 hermetic inputs: an unselected Hypothesis profile and ambient provider context;
  - CI-12 non-circular evaluation: self-comparisons and agreement-only identity evidence
    ([DTA-007](evidence-and-discrimination.md#dta-007),
    [DTA-011](evidence-and-discrimination.md#dta-011)).

## Synthesis

What matters most for the remaining pivot work (consumer migration, retirement and regeneration,
assembled qualification) and for the phase-0 rescoping:

1. **The strongest SP-10 rows rely on tests that do not discriminate what they name.**
   - Refusal tests at the protected boundary pass through foreign-key, NOT NULL,
     SERIALIZABLE-first and fact-identity backstops even if the intended guard is gone
     ([DTA-001](evidence-and-discrimination.md#dta-001)).
   - The composed journey checks presence where the plan asks for expected sets
     ([DTA-006](evidence-and-discrimination.md#dta-006)).
2. **SP-10 accounting would happen in the harness and route as they stand.**
   - The native harness pays a full head bootstrap per test and cannot express a controlled
     revision ([DTA-002](execution-and-qualification.md#dta-002)).
   - The `just test-all` route turns skips, empty Rust suites and hangs into success or silence, and
     runs randomized generated cases ([DTA-003](execution-and-qualification.md#dta-003)).
3. **Tier-1 tests compose releases and catalog rows themselves, inside test modules.**
   - Consumer migration (SC5), migrations (SC1) and compiler changes (SC2) therefore fan out across
     many modules.
   - Stand-ins hide mismatches between the writer and the native kernel
     ([DTA-005](support-structure.md#dta-005), [DTA-008](support-structure.md#dta-008),
     [DTA-009](support-structure.md#dta-009)).
4. **Retirement must carry assurance across.** The toy ownership outcomes, trace targets and
   label-normalization expectations live only in tests slated for deletion
   ([DTA-004](retirement-transfer.md#dta-004)).
5. **Some claims read stronger than their observation supports:**
   - determinism and reload compare a cached object with itself, and work-avoidance spies depend on
     cache state and name lookup ([DTA-007](evidence-and-discrimination.md#dta-007));
   - identity evidence is two implementations agreeing
     ([DTA-011](evidence-and-discrimination.md#dta-011));
   - compiler refusals are addressed by position ([DTA-010](evidence-and-discrimination.md#dta-010));
   - a generated layer and a quantifier can pass vacuously
     ([DTA-013](evidence-and-discrimination.md#dta-013)).

No plan has adopted these findings. Scheduling them into the pivot coordinator or the phase-0
rescoping is a separate, instructed step.

<a id="findings"></a>

## Findings

| ID | Finding | Subject | Pivot relevance | Page |
|---|---|---|---|---|
| [DTA-001](evidence-and-discrimination.md#dta-001) | Refusal tests at the protected native boundary can pass for an unrelated reason | implemented | survives | evidence |
| [DTA-002](execution-and-qualification.md#dta-002) | Native semantic harness fuses isolation, head bootstrap and migration-as-subject | implemented | survives | execution |
| [DTA-003](execution-and-qualification.md#dta-003) | Qualification route cannot separate required passes from skipped, blocked, hung or unreplayable outcomes | implemented | survives | execution |
| [DTA-004](retirement-transfer.md#dta-004) | Independent oracles for surviving behaviour live only in tests slated for retirement | implemented | transfer | transfer |
| [DTA-005](support-structure.md#dta-005) | Each native journey assembles its own release; no shared or product composition is exercised | implemented | survives | structure |
| [DTA-006](evidence-and-discrimination.md#dta-006) | Composed journeys assert presence or lower bounds where the claim is an expected set | implemented | survives | evidence |
| [DTA-007](evidence-and-discrimination.md#dta-007) | Determinism, reload and work-avoidance claims observed through uncontrolled process state | implemented | survives | evidence |
| [DTA-008](support-structure.md#dta-008) | Hand-written release, catalog and descriptor stand-ins not tied to what production writes | implemented | survives | structure |
| [DTA-009](support-structure.md#dta-009) | Shared scenario builders live inside test modules; flags and defaults shape other modules' claims | implemented | survives | structure |
| [DTA-010](evidence-and-discrimination.md#dta-010) | Compiler refusal cases target catalog entries by position and observe only the first diagnostic | implemented | survives | evidence |
| [DTA-011](evidence-and-discrimination.md#dta-011) | Semantic identity evidence is only cross-implementation agreement | implemented | survives | evidence |
| [DTA-012](support-structure.md#dta-012) | Tier-2 support restates source and pack declarations across directories | implemented | survives (tier 2) | structure |
| [DTA-013](evidence-and-discrimination.md#dta-013) | Some generated and quantified assertions can pass vacuously | implemented | survives | evidence |

IDs are ordered by consequence for the pivot's remaining consumers at this baseline. They are
stable and are never reused.

## Existing findings linked, not rediagnosed

| Finding | Owner | Reexamined here |
|---|---|---|
| [DA-018](../audit/boundaries-and-composition.md#da-018), [DA-019](../audit/boundaries-and-composition.md#da-019) | Broad audit | Legacy template key premises and sweep races, as precedent and hazard for any semantic template reuse ([DTA-002](execution-and-qualification.md#dta-002)); not refreshed |
| [DA-002](../audit/semantic-model-and-authority.md#da-002), [DA-009](../audit/semantic-model-and-authority.md#da-009) | Broad audit | Legacy mirror and key-pinning test observations; the semantic-identity analogue is the separate component in [DTA-011](evidence-and-discrimination.md#dta-011) |
| [DA-014](../audit/structure-and-invariants.md#da-014), [DA-021](../audit/local-reasoning-and-assurance.md#da-021), [DA-022](../audit/local-reasoning-and-assurance.md#da-022) | Broad audit | Not reexamined beyond confirming that they concern distinct causes |
| F01, F02, F03 | [Phase 0 §11](../../plans/phase-0_2026-10-28.md#11-findings-disposition) (alignment review, operator exception) | F02's test-scope wording is met at `tests/core/test_shapes.py:4-7`; two of its named controls are retiring ([DTA-004](retirement-transfer.md#dta-004)). F01 is a sibling of [DTA-001](evidence-and-discrimination.md#dta-001) |
| Q4-01, I2A-01 | [Phase 0 §11](../../plans/phase-0_2026-10-28.md#11-findings-disposition) | The legacy harness still uses `DROP … WITH (FORCE)`, which the semantic harness avoids; the math pool hang is the route gap's example in [DTA-003](execution-and-qualification.md#dta-003) |

## Strengths to keep

Each page opens with the strengths that bound its findings. In summary:
- real restricted principals and fail-not-skip infrastructure checks;
- deliberately independent, hand-written expected sets in the component tests;
- a genuine SERIALIZABLE race with proof that it raced;
- one-factor batch perturbations with no-partial-state checks;
- known-incorrect controls for the cross-engine comparator;
- content-keyed, version-complete preparation caches returning frozen products;
- schema conformance checked against declared physical metadata without pinning revision ids.

## Coverage limits and open questions

- **Tier 3** was examined through the transfer lens only.
- **Tier-1 modules not read in depth:** most of `tests/semantic/test_operations.py`;
  `test_semantic_mcp`, `test_known_reference_mcp`, `test_agent_resubmission`,
  `test_consolidation`, `test_proposals` and `test_conditional_rules` bodies; `test_analytics`,
  `test_releases`, `test_ontology` beyond cited parts; the fidelity of the in-process MCP client
  harness.
- **Tier-2 data provenance** was checked only to the extent findings needed it.
- **Absence claims and their search scopes:**
  - no production release composer: a search of `src` for the semantic `core.yaml` and pack paths;
  - no pinned semantic key literals: 40–64-hex literals in semantic, core, pool, schema and
    evaluate tests;
  - no intermediate-revision upgrade in tests: revision ids and targeted `upgrade` calls in `tests/`;
  - no `HYPOTHESIS_PROFILE` in recipes: `justfile`, `pyproject.toml`, `.envrc*`;
  - no skips, environment reads or `@given` in `tests/semantic`.

  None of these settles the question beyond its stated paths.
- **Open questions:**
  - whether a fresh clone of a template built by the frozen deployment satisfies the plan's "fresh
    extension-only" requirement ([DTA-002](execution-and-qualification.md#dta-002));
  - whether release preparation has any input outside its cache key
    ([DTA-007](evidence-and-discrimination.md#dta-007));
  - whether a product release composer is planned ([DTA-005](support-structure.md#dta-005));
  - whether the 8-entry preparation cache thrashes across a full run.
- **Concurrency limit:** changes after `c50a747` are not reconciled.

## Reading the account

| Page | Main concerns |
|---|---|
| [evidence-and-discrimination.md](evidence-and-discrimination.md) | Refusal reach, expected sets, independence from the code under test, generated cases |
| [execution-and-qualification.md](execution-and-qualification.md) | Native harness lifecycle, repeated preparation, replay, the qualification route |
| [support-structure.md](support-structure.md) | Where support lives, what it restates, coupling to production artifacts and to other tests |
| [retirement-transfer.md](retirement-transfer.md) | Assurance in tier-3 tests that surviving paths still need |

Findings explain:
- what claim is at risk and why the structural cause matters;
- the inspected footprint (Known, Suspected, Inferred);
- the decisive sources, contrary evidence and material uncertainty.

They use the standard's evidence vocabulary and cite core and profile principles plus companion
sections. Source reasoning can establish a structural weakness without running the suite; a passing
suite does not establish its evidential quality.

## Finding ownership and history

New test findings use stable DTA-nnn identities. Each finding has one primary home, and the
index above is for navigation only. Identity and lineage are kept as explanations or topic
boundaries change, and retired IDs are never reused.

**Relation to the broad account.** The broad and test accounts examine related paths at different
baselines. Where a structural cause is already a finding in the broad account, its identity and
home are kept and it is linked here, with a statement of what was reexamined; this account does not
claim to refresh the other. A new, distinct cause gets its own finding, but sharing a component or
principle is not reason enough to merge diagnoses. A move records its lineage and leaves a route
from the former home.

**Who owns what.**
- The account owns diagnosis at its stated baseline.
- Reviews own correction alternatives and judgment.
- Implementation plans own scheduled disposition, progress and closure evidence; link those owners
  without copying mutable status.

**Removal and history.** Resolved material is removed only on evidence, with closure recoverable
through the removal commit. Git holds earlier accounts; there is no separate audit archive or
execution register.

**Refreshing.** Ordinary implementation does not maintain this collection as a recurring gate. A
test-scope audit or a subsequent review uses the binding's deliberate invocation and freshness
rules. A refresh uses intervening test, production-contract, dependency and configuration changes
as leads, and revisits findings whose premises changed. This account performs no repairs and
establishes no scientific or product qualification.
