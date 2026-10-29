# Evidence independence and discrimination

Findings about which production mistakes the tests would still detect: refusal reach, expected
sets, independence from the code under test, generated cases and quantifiers. FP-02, FP-04,
FP-05, DP-03, DP-23, H20, CI-04 and CI-12 by analogy, and
[companion](../design_principles/core/test-assessment.md) §1, §3, §4 and §7. Baseline, scope
and method are in the [README](README.md). Paths are relative to `python/corpus-structure/`
unless they start at the repository root.

Much of the tier-1 evidence is deliberately independent, and that bounds the findings below:
- **Hand-written exact expectations against production paths:**
  - closure sets, including cycles and negative/context sets, each with a positive sibling built by
    the same setup (`tests/semantic/test_inference.py`);
  - exact analytical view rows checked on both engines against one hand-written list
    (`tests/semantic/test_analytics.py`);
  - `test_query.py`, including `knowledge == "unknown"` and `unanalysed` coverage, which is good
    CI-04 evidence;
  - hand-derived decimal scale and lexical form (`tests/semantic/test_columnar_journey.py`);
  - contract families and lifecycles (`tests/semantic/test_contracts.py`).
- **A real SERIALIZABLE race that proves it raced:** it asserts `"40001" in states`
  (`tests/semantic/test_publication.py`).
- **One-factor perturbations of accepted batches, with no-partial-state checks** (`test_publication.py`).
- **An explicitly independent identity encoding:** "do not use the production identity helper"
  (`tests/semantic/test_alternative_groups.py`).
- **Compiler refusals assert diagnostic codes.**
- **Known-incorrect controls for the cross-engine comparator** (`Skewed`, `NotASet` in
  `tests/pool/test_engines.py`).
- **Locator correctness grounded in hand-built renditions and spike locators**
  (`tests/core/test_locators.py`). So the `fixtures/s0` and `fixtures/trace` keys, though produced
  by the production locator generator (`fixtures/s0/build.py:16-20`), serve only as join keys and
  regression locks. No locator-correctness claim depends on them, and that planning lead is
  **not** a finding.

<a id="dta-001"></a>

## DTA-001 — Refusal tests at the protected native boundary can pass for an unrelated reason

**Principles:** FP-05, DP-03, DP-23, H20; companion §4 (a negative case "reaches the intended
boundary and fails for the intended reason"), §1.
**Subject:** implemented (`tests/semantic/test_publication.py`, `test_arrow_publication.py`,
`test_operations.py`).

**Diagnosis.** Most refusal tests on the protected write boundary assert only
`pytest.raises(DBAPIError)`, with no SQLSTATE or message. At reconciliation, 29 such bare
assertions remained across nine semantic modules (41 others match a message). Several of these
tests build a negative input that also violates an independent constraint that runs earlier or acts
as a backstop. If the intended guard were removed, the test would still pass through that other
failure. Each case below was checked against the DDL or SQL:

| Test | Guard under test | What fails instead if the guard is removed |
|---|---|---|
| `test_publication.py:186` (writer `INSERT INTO data.entity VALUES ('x','y','z')`) | No INSERT privilege for the writer | Foreign key to `data.realization`, which has no `('x','y')` row (`semantic_alembic/versions/0001_physical_bootstrap.py`): 23503 instead of 42501 |
| Same loop (reader `SELECT data.begin_stage()`) | No EXECUTE for the reader | The call runs in READ COMMITTED; `begin_stage` first raises "publication requires SERIALIZABLE" (`semantic_alembic/versions/semantic_0024_transport.sql:4`) |
| `test_publication.py:191-195` (writer-created `sp_entity` must not impersonate staging) | "preexisting staging relation" check (`:5` of the same SQL) | Also runs non-SERIALIZABLE, so the check is never reached |
| `test_arrow_publication.py:188-193` | Writer INSERT privilege | The same foreign-key confound with `('x','x','x')` |
| `test_operations.py:207` (`kb.observation.insert().values(task_id=task)`) | `REVOKE INSERT` on observations | NOT NULL on `release_id`, `observation_key`, `ordinal`, … (`semantic_alembic/versions/semantic_0006_operations.sql:247-255`) |
| `test_publication.py` null / missing / foreign-entity object cases | Value null/range/foreign-entity guards | Each swaps the object value for `"vb"` but keeps the `fact_id` computed for the original value, so `publish_batch` fails with "invalid fact identity" (`src/corpus_structure/semantic/sql/publication.sql:34`) |
| `test_publication.py` bad datatype/record cases paired with `FactRow("forged", …)` | Datatype/record guards | The same fact-identity backstop |

**Consequence.** Concealed defects.
- A regression in GRANT/REVOKE, staging protection or a value-validation rule would leave these
  tests green.
- A failing case does not say which guard fired, which obstructs diagnosis.
- SP-10's "Strong publication … direct-DML denial" row and the plan's rule that expectations
  challenging a validator stay independent would rely on exactly these tests.

**Footprint.**
- *Known:* the seven cases above.
- *Suspected:* other bare-`DBAPIError` refusals whose confounds were not traced, for example the
  composed-guard status mutation in `tests/semantic/test_execution_native.py`.
- *Inferred:* the idiom lives in the native harness that the SP-10 union will reuse.

**Counterevidence.**
- Several refusals do assert their reason: `tests/semantic/test_releases.py` (sqlstate 42501),
  `tests/semantic/test_occurrence_context.py` (`has_table_privilege` and the message), and
  message matches in `test_execution_native.py`, `test_inference.py` and
  `test_domain_operations.py`.
- Many bare cases are single-field perturbations of a batch that a sibling test publishes
  successfully. Those discriminate in effect even without asserting the reason.

**Uncertainty.** None for the seven Known cases. A cheap control, if wanted: grant INSERT on
`data.entity` to the writer in a scratch database and run
`test_restricted_role_cannot_bypass_or_replace_stage`. It is expected to still pass.

**Leads (optional).** Assert SQLSTATE or message per refusal, and build negative inputs as
one-factor changes to an accepted input.

**Related.** [F01](../../plans/phase-0_2026-10-28.md#11-findings-disposition) (negative store
tests per invariant, legacy store) concerns missing cases. This finding concerns cases that exist
but do not discriminate.

**Bears on:** SP-10 strong-publication and refusal rows; every later protected writer.

<a id="dta-006"></a>

## DTA-006 — Composed journeys assert presence or lower bounds where the claim is an expected set

**Principles:** DP-23, FP-04; companion §4.
**Subject:** implemented (`tests/semantic/test_domain_operations.py`).

**Diagnosis.** The composed cut → consolidation → inference journey often checks only that rows
exist, that a value is a member, or that a count reaches a lower bound:
- evaluated occurrences and `evidence_source` are non-empty (`:508-513`);
- `"rejected" in outcomes and "refuted" in outcomes`, with `len(occurrence) >= 2` (`:538-539`);
- one inverse is present and `derivation` is non-empty (`:575-581`);
- `entity_source` is non-empty (`:797`).

**Consequence.** Extra, duplicated or spurious facts, derivations, assessments or source rows on
the composed path would pass. SP-10 asks for "independent expected sets" for occurrence, fact and
conflict scope and for qualified inference on that path.

**Footprint.**
- *Known:* the sites cited.
- *Inferred:* other composed-journey modules may use the same idiom; they were not surveyed.

**Counterevidence.** The components underneath assert exact sets: `test_inference.py`
(hand-written closure sets), `test_analytics.py`, the counts in `test_publication.py`,
`test_query.py`, `test_statistics_cut.py`, and a nearby exact-length check in
`test_domain_operations.py`. The gap is at composition, which is where the plan's union applies.

**Bears on:** SP-10 occurrence/fact/conflict-scope and qualified-inference rows.

<a id="dta-007"></a>

## DTA-007 — Determinism, reload and work-avoidance claims are observed through process state the tests do not control

**Principles:** DP-09, DP-23 ("stale caches", "incremental against clean recomputation"),
FP-06, H14, H19, H20; companion §1, §3, §5, §6.
**Subject:** implemented (`src/corpus_structure/semantic/prepare.py:553-582`;
`src/corpus_structure/semantic/releases.py:444`; the tests cited below).

**Diagnosis.** `prepare_release` returns the `lru_cache(maxsize=8)` entry keyed on bundle,
dependencies, profile and compiler stack. `load_release` reconstructs a release by calling
`prepare_release` again. The whole suite runs in one process, and nothing clears the cache except
`tests/semantic/test_prepare.py` itself. Claims observed through that process state lose their
discrimination in two ways.

**1. Self-comparison.** An equal bundle hits the cache: `test_prepare.py` asserts the result
`is first`. So the following compare a cached object with itself:
- `first.release_id == prepare_release(bundle()).release_id` (`test_prepare.py:57`);
- the registry-row equality in `tests/semantic/test_rule_products.py`;
- all eight `load_release(conn, id) == prepared` assertions (`test_execution_release.py`
  ×3, `test_inference.py`, `test_release_publication.py`, `test_releases.py` ×3). In each, the
  same inputs were prepared earlier in the process.

`_prepare_release_uncached` is never re-run on archive-decoded inputs. What is still discriminated:
archived bytes decode to equal inputs (`test_releases.py` records the reconstructed call), and the
manifest, digest and tamper refusals hold. What is concealed: any dependence of preparation on
state outside the cache key (ambient files, package data, iteration order) that would make a
cold-process reload differ.

**2. Work avoidance seen through incidental mechanisms.** Tests that assert some work is *not*
done patch an inner name to raise:
- `tests/semantic/test_proposals.py:288-300` patches `ontology.build_graph_artifacts`;
- `test_execution_release.py` patches `contracts.trusted_execution_inputs` around a `load_release`;
- further sites in `test_releases.py`, `test_prepare.py` and `test_query.py`.

Their discrimination depends on two incidental facts:
- **Cache state.** A regression that routed the work through a cached `prepare_release` would be
  hidden whenever an equal bundle was prepared earlier in the run. The core-only bundle in
  `test_proposals` is also prepared by `test_prepare.py`, `test_expression_context.py` and
  `test_source_routing.py`.
- **Name lookup style.** Each patch works today because the production caller looks the name up at
  call time, through a function-local import or a module global. A new caller that binds the name
  at import, or a new route, bypasses the patch, and the absence assertion still passes.

**Consequence.**
- Determinism and archive-reload claims, which SP-10's "immutable archival products persist" and
  "release-sensitive reuse" evidence would cite, are weaker than they read.
- Work-avoidance claims can depend on test order and on another test's cache cleanup.

**Footprint.**
- *Known:* the ten self-comparisons and six patch sites cited.
- *Inferred:* at today's order the `test_proposals` assertion is probably not masked, because
  intervening preparations and `cache_clear` likely evict the entry.
- *Unknown:* whether the 8-entry bound thrashes across a full run.

**Counterevidence.**
- The cache key covers inputs and the compiler, Python and library stack, and products are frozen
  (`src/corpus_structure/semantic/types.py`). So there is no stale-evidence risk for correctness
  claims while premises are unchanged.
- `tests/semantic/test_statistics_model.py` compares registry-row digests from two fresh
  interpreters, for one small schema.
- `test_prepare.py` checks directly that the cache key covers inputs and the stack.

**Uncertainty.** Whether preparation has any unkeyed input is not established. A probe would clear
the cache before `load_release` in an archive test and run it in a fresh process. It is expected to
stay equal; a divergence would be a real defect.

**Related.** The [SP-06 execution-fit evidence](../evidence/2026-10-29_sp06-execution-fit/README.md)
introduced the cache and makes no correctness claim. This finding concerns how tests observe
through it.

**Bears on:** SP-10 evolution/archive and reuse rows; release-compatibility work in later packages.

<a id="dta-010"></a>

## DTA-010 — Compiler refusal cases target catalog entries by position and observe only the first, often generic, diagnostic

**Principles:** FP-02, FP-06, DP-24; companion §4, §5.
**Subject:** implemented (`tests/semantic/test_contracts.py:198-280`;
`src/corpus_structure/semantic/prepare.py:116-117`).

**Diagnosis.**
- The refusal parametrization mutates the live trusted catalog by list position, for example
  `("relationships", 19, "reference_scope", …)`, `("outcome_domains", 13, …)` and
  `relationships[0].endpoints[0]`.
- The fixture is the live `trusted_execution_inputs()`.
- `_fail` raises a single diagnostic, so `diagnostics[0]` is whichever check fails first.
- Several expected codes are generic (`contract_catalog`, `unresolved_contract_reference`), so many
  different defects produce the same code.

**Consequence.**
- A behaviour-preserving reorder or insertion in the catalog, which is likely as packages add
  lifecycles and guards (SC3), silently retargets a mutation.
- The case may then refuse for another reason with the same generic code (concealment), or fail
  spuriously.
- Order dependence has already shown itself: the SP-C02 receipt records "one diagnostic-order
  expectation failed" in this component (coordinator §10).

**Counterevidence.** The expectations are written independently of the compiler, and the refusal
coverage is broad.

**Uncertainty.** Which check produces each code. A probe would assert each case's diagnostic
`location` once.

**Bears on:** contract-catalog evolution in remaining packages; SP-10 admission-refusal rows.

<a id="dta-011"></a>

## DTA-011 — Semantic identity evidence is only cross-implementation agreement; no vector is pinned

**Principles:** DP-04, DP-23 ("agreement between two implementations is evidence, not proof"),
CI-12 by analogy; companion §1.
**Subject:** implemented (`src/corpus_structure/semantic/identity.py`,
`src/corpus_structure/semantic/sql/identity.sql`, `sql/publication.sql`;
`tests/semantic/test_publication.py`).

**Diagnosis.**
- Python computes fact and occurrence keys; SQL recomputes and checks them during publication.
- `test_publication.py` compares `data.canonical_json(data.value_meaning(…))` with
  `canonical_bytes(_meaning(v))`, a private production helper.
- No test in `tests/semantic` pins a literal key or digest. The search covered 40–64-hex literals
  in the semantic, core, pool, schema and evaluate tests.
- So the evidence detects drift *between* the two implementations, which is a real two-language
  differential. It does not detect a coordinated change to both sides, or a shared misreading of
  the canonical form (for example, both emitting the same wrong decimal form).
- Persisted rows are not recomputed when both sides change together within one compiler version.

**Consequence.** Silent re-keying of semantic facts and occurrences, or a shared canonicalization
error, passes the suite.

**Counterevidence.**
- `tests/semantic/test_alternative_groups.py` uses an independent canonical reference encoding.
  That pattern is absent elsewhere.
- `release_id` versions the compiler stack.

**Related.** The pre-pivot key scheme's equivalent observation ("by design no test pins a key
value") is part of [DA-009](../audit/semantic-model-and-authority.md#da-009), whose identity and
home are unchanged. DA-009's primary cause is unversioned contracts. This finding concerns the
separate post-pivot semantic identity component, where the same evidential gap recurs.

**Bears on:** SP-10 identity and replay rows; any compiler-version change.

<a id="dta-013"></a>

## DTA-013 — Some generated and quantified assertions can pass vacuously

**Principles:** DP-23, FP-05; companion §4 (generated cases), §6.
**Subject:** implemented (`tests/math/test_property.py:96-113`;
`tests/semantic/test_statistics_model.py:57-66`).

**Diagnosis.**
- **`test_generated_layer`** draws inputs from `from_lark` over the grammar under test, suppresses
  every health check, and silently returns for examples whose parse yields no tree. Its only gate is
  `counts["read"] > 0`; the printed counts are not asserted. A regression that rejects nearly all
  generated inputs passes if one input is still read.
- **`test_statistics_model.py`** asserts `all(p.multivalued …)` over a generator filtered by
  `p.iri == metadata["property"]`. If the IRIs stopped matching, for example compact versus
  expanded form, the generator would be empty and the assertion would pass.

**Consequence.** Concealed regressions in grammar acceptance and in predicate multivalue metadata.

**Counterevidence.**
- Other `all()` uses that were checked are guarded by exact-length assertions
  (`test_source_routing`, `test_domain_operations`, `test_statistics_cut`).
- `tests/core/test_canonical.py` pairs its generated cases with hand-written byte vectors.

**Bears on:** tier-2 math foundations; statistics-model metadata consumed by later packages.
