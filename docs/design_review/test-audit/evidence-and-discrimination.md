# Evidence independence and discrimination

Findings about which production mistakes the tests would still detect: refusal reach, expected sets, independence
from the code under test, reference data, generated cases and quantifiers. FP-02, FP-04, FP-05, DP-03, DP-23, H20,
CI-04 and CI-12 by analogy, and [companion](../design_principles/core/test-assessment.md) §1, §3, §4 and §7. Baseline,
scope and method are in the [README](README.md). Paths are relative to `python/corpus-structure/` unless they start at
the repository root.

Much of the evidence is deliberately independent, and that bounds the findings below:
- **Hand-written exact expectations against production paths:** closure sets with cycles and non-composition
  (`tests/semantic/test_inference.py:185-229`, `:355-367`), exact view rows on both engines (`test_analytics.py`),
  `test_query.py`, `test_occurrence_context.py:60-107`, `test_statistics_cut.py:255-264`.
- **A two-principal refusal pattern that separates privilege from the guard behind it:** the writer gets `42501`, then
  `SET LOCAL ROLE corpus_sem_publisher` reaches a per-mutation message (`test_execution_native.py:124-144`, `:437-498`;
  `test_operations.py:1041-1057`, `:1111-1139`; `test_native_source_selection.py:84-109`).
- **Real races that prove they raced:** `"40001" in states` on both transports (`test_publication.py:417`,
  `test_arrow_publication.py:226`).
- **Exact wire fidelity through real binary COPY** (`test_arrow_publication.py:309-347`), and a server-side content oracle
  that recomputes canonical bytes from staged rows (`semantic_0040_kernels.sql:937`, `:954`).
- **Independent encodings and authoring:** `test_alternative_groups.py:29-37` (explicitly avoiding the production helper),
  independently authored references (`test_reference_evaluation.py:80-99`), `test_canonical.py` (hand-written bytes,
  `hashlib`, code-point order), `test_conformance.py`, `test_tex.py` with a code-disjoint 918-row parity set, and
  `test_locators.py` with generator controls.
- **Genuine archives with a recorded production route** (`tests/fixtures/semantic/README.md`): `reader-v10*`, `v11` and `v12`
  are not regenerated, and their expectations are independent.
- **Reference data that cannot launder a regression.** Every frozen JSON file in `tests/math/data`, `ingest/data`, `llm/data` and
  `data/locators` re-derives exactly from its frozen sources by stdlib generators (computed 2026-10-30), and none regenerates
  from production. `fixtures/tex` is byte-identical to its source.

<a id="dta-001"></a>

## DTA-001 — Refusal tests can pass for a reason other than the guard they name

**Principles:** FP-05, DP-03, DP-23, H20; companion §4 (a negative case "reaches the intended boundary and fails for the intended
reason"), §1. **Subject:** implemented (`tests/semantic/test_publication.py`, `test_arrow_publication.py`, `test_operations.py`,
`test_analysis_contracts.py`).

**Diagnosis.** A recount over `tests/semantic` by AST finds **32 bare `pytest.raises(DBAPIError)`** with no match and no use of the bound
exception, one of them a tuple with `ActivationConflict`, across 10 modules (`test_publication` 14, `test_operations` 4, `test_native_closure` 4, `test_arrow_publication` 3,
`test_reference_evaluation_native` 2, and one each in `test_native_agent_hold`, `test_reference_evaluation`, `test_query`,
`test_interruption`, `test_native_fixtures`). A further 71 match a message and 11 assert the reason afterwards. The stronger form has grown,
and the weak form now clusters. Several bare cases build an input that also violates an independent constraint, so they pass through it if
the intended guard is removed.

| Test | Guard under test | What fails instead | State |
|---|---|---|---|
| `test_publication.py:283` writer `INSERT` into `data.entity` | No INSERT privilege | Foreign key (`23503`) | Local confound holds. Bounded: `data.require_runtime_principal` refuses a principal holding such privileges at runtime and `test_native_fixtures.py:163` calls it |
| `test_publication.py:284` reader `SELECT data.begin_stage()` | No EXECUTE | SERIALIZABLE check fires first | Local confound holds. Bounded by `test_native_closure.py:555-561`, which grants this EXECUTE and asserts `match="purpose contract"` |
| `test_arrow_publication.py:176-181` | Writer INSERT | As row one | Same |
| `test_operations.py:215` `kb.observation` insert | `REVOKE INSERT` | NOT NULL | Unchanged |
| `test_publication.py:257-270` null, missing and foreign values | Value guards | The value guard most likely fires first (`validate_state`, `semantic_0040_kernels.sql:1008`), but if it is removed the kept `fact_id` still refuses at `:1017` | **Concealment confirmed.** No test matches `missing scalar` or `invalid fact identity` |
| `test_publication.py:476-489` bad datatype and record with `FactRow("forged")` | Datatype and record guards | Forged identity | **Half closed:** datatype is evidenced at `:933-942`; record shape is not |
| `test_operations.py:496-508` measurement forge loop | `validate_measurement_definition`, for `metric`, `run_id` and `detail` | `guard_measurement_custody` fires first. The loop has no one-factor structure: its `{}` baseline is already refused | **New** |
| `test_arrow_publication.py:429-479` six derived-intent cases | Each of operation, contract, projection, source release, cut, profile | Any database error from a hand-written call, including a `begin_stage` failure | **New** |
| `test_analysis_contracts.py:205-209` `stage_key(name="forged")`, bare `PreparationError` | `analysis_contracts.py:544-547` | `:549-551` also raises, because required components are absent | **New;** the only non-database site traced |

For the measurement loop: same-event row triggers fire in name order, and the catalog of a `semantic_0040` target
(queried 2026-10-30) shows `guard_measurement_custody` before `validate_measurement_definition`, with the writer holding INSERT on
`ops.measurement`. The custody guard refuses a bound-release insert when `current_user <> 'corpus_sem_publisher'`. The run is bound to a release (`test_operations.py:398`). So the `metric`, `run_id`
and `detail` checks are not reached in this loop, and a search of the package tests for their messages finds only a Python-level
`unresolved metric` (`test_metric_contracts.py:63`).

A narrower weakness affects some matched cases. `str(DBAPIError)` carries more than the reason: SQLAlchemy adds `[SQL: …]` and
`[parameters: …]`, and a control on 2026-10-30 shows psycopg's own `str(exc)` includes `CONTEXT: PL/pgSQL function …`. So
`test_execution_release.py:256` `match=r"semantic-2|execution"` can match a function name, and its `sqlstate == "23514"` does not narrow it,
because that code is shared by most guards. A script found no `match=` literal that also occurs in the test's own statement text, so literal
self-echo is not live.

**Consequence.** Concealed defects. A regression in GRANT or REVOKE, a value rule, a derived-intent guard or a measurement definition check
could leave these tests green. A failing case does not say which guard fired.

The evidence matters more than its size suggests. PL/pgSQL bodies are treated as opaque bytes: `native_products.py:98-107`, `:526-534` hash them,
`parse_plpgsql` appears nowhere, and `EXECUTE format` or `EXECUTE '` occurs on 670 lines across the kernels and revisions (counting
redefinitions). Hash custody shows the reviewed bytes are deployed, not that they are correct, so behavioural native tests are the only evidence
for guard logic.

**Footprint.**
- *Known:* the table's rows and the recount.
- *Measured statically, with a wide bound:* how many live guards have any reason-level test. Over `semantic/sql/*.sql` and `semantic_0040_*.sql`, the
  coordinator's method (350 distinct `RAISE EXCEPTION` message heads, against `match=` regexes and literals of 12 or more characters in `tests/semantic`)
  leaves 143 with no reason-level text. The independent reviewer's method (253 messages, excluding physical self-checks) leaves 123. So on the order of
  120–145 guard messages have no test naming their reason. Bare refusals may reach some of them, and a literal is not necessarily an assertion, so this
  bounds reason-level evidence, not reach. Sampled greps find nothing for `undeclared record`, `canonical date`, `live lease` or `undeclared run transition`.
- *Suspected:* other bare sites, not all traced for confounds, and other bare `PreparationError` uses in `test_analysis_contracts.py`.

**Counterevidence.**
- Many bare cases are single-field perturbations of a batch a sibling publishes successfully, which discriminates in effect.
- Closed since the prior account: the composed-guard mutation in `test_execution_native.py`, now asserted through two principals; and
  the staging-impersonation case at `test_publication.py:308-311`, now SERIALIZABLE under the owner and so reaching its guard.

**Uncertainty.** A library limit bounds any remedy. SQLSTATE resolves the declarative confounds, but `ERRCODE='23514'` occurs 1,923 times across
the kernels and revisions, so it does not separate RAISE guards. `constraint_name` is declarative-only (no RAISE sets it), and for RAISE guards the
message is the only discriminator. `orig.diag.message_primary` is available and narrower than matching `str(DBAPIError)`; a search finds `diag`
unused in `tests/semantic` outside stubs.

A control for the measurement loop, if wanted: on a disposable clone, drop `validate_measurement_definition` and run
`test_recognizer_terminal_source_boundary_and_coverage`. It is expected to still pass.

**Leads (optional).** Assert the reason per refusal, in the two-principal form that already exists, and build negative inputs as one-factor changes
to an accepted input.

**Related.** [F01](../../plans/phase-0_2026-10-28.md#11-findings-disposition) concerns missing cases on the legacy store. This finding concerns
cases that exist but do not discriminate.

**Bears on:** SP-10 strong-publication and refusal rows; every later protected writer.

<a id="dta-015"></a>

## DTA-015 — The surviving label route supplies head-word keys the normalizer cannot match, and the only oracle uses the other form

**Principles:** FP-02, FP-04, DP-01, DP-23; CI-12 by analogy; companion §1, §4. A production cause is reported here, and repair is not authorized by
this account.
**Subject:** implemented (`src/corpus_structure/core/keys.py:187`, `:205`; `domains/statistics/methods.yaml:33-39`;
`src/corpus_structure/semantic/regeneration.py:99-106`; `src/corpus_structure/semantic/domain_operations.py:113-114`, `:760`, `:767-773`, `:834`).

**Diagnosis.** `LabelRules.head_words` is keyed by prefixed class (`core/keys.py:187`), but the pack writes a local name
(`head_words: {DistributionFamily: [distribution, distributions]}`). The retired route translated it (`consolidate/pass_.py:39-45`, "the pack writes
local names"). The surviving route does not: `regeneration.py` passes `methods.get("aliases", {})`, `domain_rule_inputs` stores it unchanged,
`_entity_mappings` validates it directly and calls `normalize_label(label, compact(definition.iri), aliases, case)`, and `compact` yields `stat:DistributionFamily`.
`rules.head_words.get(type_, ())` then finds nothing. `evaluate/semantic_alignment.py:444` consumes the same function.

A pure control on 2026-10-30 used the real pack section through `LabelRules.model_validate`:

| Type passed | `"The normal distribution"` | `"normally distributed"` |
|---|---|---|
| `stat:DistributionFamily` (what the route passes) | `normal distribution` | `normal` |
| `DistributionFamily` (what the pack declares) | `normal` | `normal` |

D5 specifies that these should agree (`docs/design/D5-consolidation-identity-confidence.md:202-203`), and `DistributionFamily` declares `cs:scope: global`
(`domains/statistics/semantic.yaml:52`), so it takes this label route.

**Why the tests do not see it.** `tests/core/test_keys.py:75-82`, `tests/evaluate/conftest.py:69` and `tests/core/test_conformance.py:108` hand-write
`stat:DistributionFamily`, `tests/consolidate/conftest.py:68` uses the translating config, and `test_semantic_alignment.py:141` uses articles only. A search
for `head_words` finds no use in `tests/semantic`, `tests/acceptance` or `tests/orchestrate`. A sound unit oracle hard-codes one key form, so it cannot meet the
composition mistake, and no journey composes the real pack's aliases with a head-word case ([DTA-005](support-structure.md#dta-005)).

**Consequence.** Label-based global identity silently fails to fuse the forms the pack declares for that class. Retiring `consolidate/pass_.py` also removes the
only translation (SC4). Articles and rewrites still apply.

**Footprint.**
- *Known:* the sites above, and two controls. Besides the function-level table, `_entity_mappings` on the composed `prepare_pack(domains/statistics)` (pure, no
  database, 2026-10-30; `DistributionFamily` has `identity_groups == (('id',),)`) keeps `The normal distribution` and `normally distributed` **split**, `The gamma
  distribution` and `gamma distributed` **split**, `normal` and `normal distribution` **split**, and merges `The normal distribution` with `normal distribution`.
  `head_words` appears only at `core/keys.py:187`, `:205` and `consolidate/pass_.py:43-45`, so no other route translates it.
- *Observed:* in `corpus_efficiency_20261030` (read-only, 2026-10-30), the `DistributionFamily` labels in `kb.observation` are `normal distribution` (4),
  `lognormal distribution` (2), `standard lognormal distribution` (2) and `standard normal distribution` (2). All carry the head word, so **no split is
  visible in this small target**. The defect is real and latent there.

**Counterevidence.** The no-match argument holds for any prefix set. `prepared.entity_keys` handles identity-slot entities separately, so `FamilyParameter` is
unaffected. The route is conservative: non-fusion leaves two entities rather than merging different things.

**Bears on:** statistics entity identity on any corpus using adjectival forms; `evaluate/semantic_alignment.py` label comparison.

<a id="dta-006"></a>

## DTA-006 — Composed journeys assert presence or lower bounds where the claim is an expected set

**Principles:** DP-23, FP-04; companion §4. **Subject:** implemented (`tests/semantic/test_domain_operations.py`, `test_composed_journey.py`,
`test_agent_resubmission.py`, `test_serving.py`).

**Diagnosis.** The idiom survives and has now been surveyed. It concentrates in top-level consolidation and explanation checks rather than being universal.

| Site | Observation | What would still pass |
|---|---|---|
| `test_domain_operations.py:601-606` | Occurrences and `evidence_source` non-empty | Extra or duplicate occurrences; evidence for the wrong source |
| `:631-632` | `"rejected" in outcomes and "refuted" in outcomes`, `len(occurrence) >= 2` | Spurious assessments, extra occurrences |
| `:672-674` | `parent` picked by `next`, inverse is a member, `derivation` non-empty | Extra inferred facts and derivations (receipts at `:657-660` are exact) |
| `:969` | `entity_source` non-empty | Wrong or extra source rows |
| `:1013` | `consolidate_cut` with no read-back | Persisted premise references could differ |
| `test_composed_journey.py:72`, `:78` | `source_receipts` truthy; `supports and evidence and source_observations` | Wrong span, wrong source, extra supports. This is the module's stated source-to-read claim |
| `test_agent_resubmission.py:286`, `:296`, `:330`, `:374` | `rejected` or `issues` truthy | Any issue satisfies a test about a specific uncertainty or refusal |
| `test_agent_resubmission.py:365` | `outcome in ("unlocated","coarse")` | Two outcomes accepted for a quotation sharing no text with the source |
| `test_serving.py:187` | `include_candidates` asserts only `projection == "fact"` | The flag could have no effect on rows |
| `test_serving.py:239-247`, `:475`, `:485`, `:500` | Non-empty, `any`, superset, truthy | Extra or wrong served rows |

**Consequence.** Extra, duplicated or spurious facts, derivations, assessments or source rows on the composed path would pass, though SP-10 asks for "independent
expected sets" there.

**Footprint.**
- *Known:* the sites cited.
- *Inferred:* a regex over assert lines in `test_reference_evaluation`, `test_identity_exclusions`, `test_statement_anchors` and `test_columnar_journey` finds only
  `test_known_reference_mcp.py:283`, which is not a reading.

**Counterevidence.** Components underneath assert exact sets, and exact checks exist in the same journeys: `test_runtime_entrypoints.py:76-82`, `:102`,
`test_serving.py:167`, `:178`, `:467-473`, `:494`, `:502-507`, and `test_domain_operations.py:829-836`, `:861-885`, `:901-913`, `:1081-1097`. The gap is at composition.

**Bears on:** SP-10 occurrence, fact and conflict-scope rows.

<a id="dta-011"></a>

## DTA-011 — Semantic key assembly is evidenced only by cross-implementation agreement

**Lineage.** Formerly "Semantic identity evidence is only cross-implementation agreement; no vector is pinned".

**Principles:** DP-04, DP-23, CI-12 by analogy; companion §1. **Subject:** implemented (`src/corpus_structure/semantic/identity.py:33-66`;
`tests/semantic/test_value_codec.py`, `test_native_closure.py:572-633`).

**Diagnosis.** "No vector is pinned" is no longer accurate. `test_value_codec.py` hand-pins `value_meaning` vectors (`:11-24`), canonical bytes `b'{"decimal":"1.23"}'`
(`:31`) and key relations (`:32-33`), so a shared misreading of value meaning has an anchor. The assembly above it remains differential: a search for 40–64-hex literals
in `tests/semantic/*.py` finds only a `release:` digest (`test_archive_reader.py:54`), with no `fact:` or `occ:` literal. Field order, participants and prefix in
`identity.py` are checked only by Python and SQL agreeing, so a coordinated reorder on both sides passes.

**Consequence.** Silent re-keying of semantic facts and occurrences passes the suite.

**Counterevidence.** `test_identity_resolution.py:139-157` covers arrival and id independence, `test_alternative_groups.py` uses an independent canonical encoding, and
`release_id` versions the compiler stack. Under the regenerable-data rule, re-keying is recoverable, though an undetected one would still mislead comparison across runs.

**Related.** [DA-009](../audit/semantic-model-and-authority.md#da-009) keeps the pre-pivot key scheme's observation. [DTA-020](#dta-020) records a further limit: the
historical answer in `test_release_compatibility.py` is built with the current `fact_key`.

**Bears on:** any compiler-version change; identity rows.

<a id="dta-007"></a>

## DTA-007 — Determinism, reload and work-avoidance claims are observed through process state the tests do not control

**Principles:** DP-09, DP-23, FP-06, H14, H19, H20; companion §1, §3, §5, §6. **Subject:** implemented
(`src/corpus_structure/semantic/prepare.py:528`; `src/corpus_structure/semantic/releases.py:558-560`; the tests cited).

**Diagnosis.**

*Self-comparison, narrowed.* `prepare_release` still returns an `lru_cache(maxsize=8)` entry and `load_release` still re-prepares through it. Eight positive
`load_release(...) == prepared` comparisons remain (`test_execution_release.py:118`, `:179`, `:212`; `test_inference.py:352`; `test_release_publication.py:76`;
`test_releases.py:162`, `:429`, `:455`), plus `test_prepare.py:57` and `test_rule_products.py:44`. `test_execution_release.py:114-118` patches
`contracts.trusted_execution_inputs` around a `load_release` whose compile body does not run on a cache hit, so the patch cannot fire on the path it protects.

Ordinary reads no longer take this route. `open_release` (`archive_reader.py:152-296`) never calls `prepare_release`, so `test_releases.py:115` `opened == prepared` is a real
non-cache equality of decoded against compiled products, and genuine v10–v12 fixtures challenge it. `load_release` byte-compares the derivation and each projection row against
the archive, so tamper detection is real. The residual concealment is narrow: a cold `_prepare_release_uncached` on decoded inputs is never compared with an earlier compile,
except `test_statistics_model.py:100-125` for one toy schema's registry rows. The prior open question about unkeyed inputs narrows accordingly: searches of the preparation modules
for ambient reads find only explicit paths (`ontology.py:278`, `:813`), and the key covers bundle, dependencies, profile, compiler version, `sys.version` and library versions
(`prepare.py:382-388`). Remaining candidates are third-party generator internals and hash-randomized iteration order (*Suspected*). `test_prepare.py:524`, `:551` also
clear the compile cache, a second mechanism alongside eviction.

*Work avoidance, split by mechanism.* Wrap-and-count with a positive assertion is sound against route removal, and only an added route under another name escapes it. Patch-to-raise
with no positive control is weaker:
- `test_proposals.py:297-309` patches `ontology.build_graph_artifacts`. A regression through a cached `prepare_release` would hit an entry `test_observations.py:21-25` prepared, if
  still among the last eight (*Inferred:* evicted at default order, masked under a narrow selection). `test_release_compatibility.py:551` prepares nine bundles and so flushes the
  cache, which makes eviction a concrete mechanism.
- `test_archive_reader.py:43`, `:203` patch only `prepare.prepare_release`, while `_boundary` and `scientific_model` reach it behind `lru_cache(maxsize=1)`. `test_capture_policy.py:140-141`
  clears the cache first; `test_archive_reader.py:203` does not. Whether that makes its outcome order-dependent is *Suspected*.
- `test_domain_operations.py:1252-1260` is vacuous as written. See [DTA-013](#dta-013).

**Consequence.** Determinism and reload claims are weaker than they read for the full-verification route only. Work-avoidance claims can depend on test order.

**Counterevidence.** The cache key is complete by inspection, and products are frozen, so there is no stale-evidence risk for correctness claims while premises are unchanged. The read cache
has better evidence than the compile cache (`test_release_compatibility.py:422-450`, `:514-542`).

**Uncertainty.** Whether the 8-entry cache thrashes: module locality is high and test-side `@cache` sits above it, so ordinary misses are expected and eviction costs a re-preparation, not
correctness. `_prepare_release_cached.cache_info()` at session end would settle it.

**Bears on:** release-compatibility and archive claims.

<a id="dta-010"></a>

## DTA-010 — Compiler refusal cases target catalog entries by position and observe only the first, often generic, diagnostic

**Principles:** FP-02, FP-06, DP-24; companion §4, §5. **Subject:** implemented (`tests/semantic/test_contracts.py:213-227`, `:246`, `:251`, `:273-285`, `:392-394`;
`tests/semantic/test_analysis_contracts.py:135`, `:215`; `tests/semantic/test_execution_projection.py:105-123`; `src/corpus_structure/semantic/contracts.py:675-676`).

**Diagnosis.** Fourteen of 15 refusal cases at `test_contracts.py:213-227` mutate the live catalog by list position, and `_fail` raises a single diagnostic. Positions today resolve to
`relationships[19]` `entity_membership`, `concepts[0]` `IdentityExclusion`, `transitions[0]` `run_start_source` and `operations[0]` `resolve_identity`, and nothing in the test names them.

**The predicted failure happened.** Between baselines `("outcome_domains", 13, …, "outcome_authority")` became `("outcome_domains", "scientific", …, "outcome_implementation")`. Only that case
moved to an id.

A sibling has the same cause: `test_execution_projection.py:105-123` runs eight contract changes against `codes & {five codes}`, so a `version` change refused as `duplicate_definition` passes, and
four of them check only the truthiness of `contract_id`, `consumer`, `expected`, `actual` and `remedy`. `test_effective_bindings.py:105` `match=r"statement|locator"` spans seven defects.

**Consequence.** A reorder or insertion silently retargets a mutation, and the case may then refuse for another reason with the same generic code (concealment) or fail spuriously.

**Counterevidence.** Expectations are hand-written, and coverage is broad. `test_effective_bindings.py:145-155` asserts a full diagnostic by value, so the stronger form exists.

**Uncertainty.** Which check produces each code. Printing `diagnostics[0]` per case, with no database, would settle it.

**Bears on:** contract-catalog evolution.

<a id="dta-019"></a>

## DTA-019 — Frozen oracles and genuine archives have no declared basis for accepting a deliberate change

**Principles:** FP-04, FP-05, DP-22, DP-24; companion §4, §6, §7; AGENTS.md ("Holds go in `docs/pins.md`"). **Subject:** implemented (`tests/{ingest,llm,math}/data`, `fixtures/s0`, `tests/fixtures/semantic`;
`tests/semantic/test_release_compatibility.py:43`, `:65`, `:217-293`; `src/corpus_structure/semantic/determinants.py:30-41`; `docs/pins.md`).

**Diagnosis.** The positive result comes first: the frozen data cannot launder a regression. The other side of that strength is that when production should legitimately change, the data has no route.
- Build docstrings say "written once" and "the committed JSON is the fixture's authority", so rerunning reproduces the old values. Only `fixtures/tex/README.md` states a rule: "A disagreement is
  decided by D1 §6.2, and the side that changes is recorded." Corrections so far are local, well-documented overlays (`tests/math/test_scope.py:39`).
- Library behaviour determines the data. `spike_renditions.json` pins sentence offsets from spaCy and `en_core_web_sm`, and `llm/data/units.json`, `fixtures/s0` frames and `s0r2_contexts.json` depend on those
  offsets. `test_sentences.py:58-60` refuses other versions, so the coupling is recognized.
- `determinants.boundary_compatible` hard-codes `pydantic-core == 2.50.1` and `python == 3.14.10` for compilers 10 and 11, and requires recorded equal to installed for 12 and 13. So a routine bump of `pydantic`,
  `pydantic-core`, `jsonschema`, `cattrs` or Python fails the archive tests by design.
- AGENTS.md requires a `docs/pins.md` hold for "a parity oracle, golden output or a known breakage". The table has rows for sympy, pylatexenc, duckdb and server extensions, and none for spaCy, `en-core-web-sm`,
  html5lib, lark, pydantic or the others above. Python has a toolchain row with an unrelated reason.

**Claim at risk.** That a failure in these tests means a regression, and that a later edit to a frozen file is still evidence.

**Consequence.** SC6: a sentence-model or html5lib bump fails tests across ingest, llm, math and evaluate at once, with no recorded reason or revisit trigger. The natural wrong repair is hand-editing a 251 KB offset
table or regenerating a fixture from current code, either of which removes the independence.

**Footprint.** *Known:* the sites above. *Inferred:* the fan-out of an offset change, from reading tests, not probed.

**Counterevidence.** Failure is loud, pins are exact, so nothing moves by accident, and `test_release_compatibility.py:46-80` tests the negative per library. The fixture README documents the archive contract. For one
operator, a light rule may be enough.

**Uncertainty.** Whether offset parity with S1 is a lasting obligation or a finished port check. If finished, these fixtures' future is retirement, not update.

**Bears on:** any dependency bump in these families; [pin-check](../../pins.md).

<a id="dta-013"></a>

## DTA-013 — Some generated and quantified assertions can pass vacuously

**Principles:** DP-23, FP-05; companion §4, §6. **Subject:** implemented (`tests/math/test_property.py:96-113`; `tests/math/test_coverage.py:79-80`; `tests/evaluate/test_parity.py:133`;
`tests/core/test_shapes.py:192-205`; `tests/schema/test_packs.py:412-424`; `tests/semantic/test_statistics_model.py:57-66`; `tests/semantic/test_domain_operations.py:1252-1260`).

**Diagnosis.**
- **`test_generated_layer`.** Draws from `from_lark` over the grammar under test, suppresses every health check, and returns early for examples whose parse yields no tree. An early `return` counts as a valid example,
  whereas `assume` would feed Hypothesis's own discard accounting. Its only gate is `counts["read"] > 0`. The receipt prints `{'generated': 300, 'read': 283}`, unasserted, so a regression rejecting 282 of 283 passes.
- **`test_coverage`.** Asserts no `internal` failure and no disagreement, and status is print-only by declared design (`:4-5`). A regression turning most of 74 non-vendored pages to `failed` with a parse category passes, because such
  spans have `agrees is None`. Only the four vendored pages have a floor.
- **`test_parity`.** `:133` asserts only `got["core"] <= 0.933 + 1e-9`, so zero passes.
- **Schema draws.** `test_shapes.py:192-205` and `test_packs.py:412-424` discard refused instances with `except ValidationError: return` and count nothing, the latter with `suppress_health_check=list(HealthCheck)` over a hand-rolled draft-7
  rewrite. A model tightened until every draw is refused passes.
- **`test_statistics_model.py:57-66`.** `all(p.multivalued …)` over a generator filtered on class and IRI, with no count guard.
- **`test_domain_operations.py:1252-1260`.** Patches `ReadSession.load_values` and asserts `not noise_ids & loaded`, with no assertion that `loaded` is non-empty. If production hydrates by another route, `loaded` is empty and the assertion
  passes. The production call is `semantic/domain_operations.py:483`.

**Consequence.** Concealed regressions in grammar acceptance, reading coverage, parity, draw coverage, multivalue metadata and input-noise hydration.

The weak assertions also sit on the most expensive nodes. Under [the receipt's conditions](execution-and-qualification.md#measurements) the three costliest nodes
in the suite are all here: `test_coverage_beside_s5` 176.91 s, `test_what_pydantic_accepts_of_schema_draws_satisfies_the_schema` 89.41 s (15 examples, refusals
discarded, dormant target) and `test_generated_layer` 36.17 s, together 302.49 s, 29.8% of recorded phases. This is a judgment about what the expense buys (companion §8),
not a claim that they are wasted: `test_coverage` also establishes its tree and token property and the absence of crashes over 28,956 spans.

**Footprint.** *Known:* the sites cited. *Suspected:* actual vacuity. Draw acceptance rates are unmeasured, and the statistics filters almost certainly match today.

**Counterevidence.**
- The no-gate choice in `test_coverage` has a stated reason: timeout flips near the 2 s limit (16 status changes in the receipt, 14 with a timeout on one side).
- Other floors are tight: `test_cascade.py:277` (`>= 523`, actual 527), `test_scope.py:129` (exactly 18), `test_parity.py:123`.
- `test_canonical.py` pairs its generated cases with hand-written byte vectors, and the hand-written strategies at `test_shapes.py:158-178` have no discard path.
- The `test_packs.py` draw targets code under [DTA-014](retirement-transfer.md#dta-014).

**Bears on:** math foundations; statistics metadata.

<a id="dta-020"></a>

## DTA-020 — "Historical" test inputs are built by the current producers

**Principles:** FP-04, FP-05, DP-23, DP-24; companion §1, §4; SC2, SC6. **Subject:** implemented (`tests/semantic/test_capture_policy.py:24-160`; `tests/semantic/test_release_compatibility.py:124-143`;
`tests/semantic/test_execution_projection.py:220-300`).

**Diagnosis.** Several tests of retained readers and upgrades construct their era input with today's code, so the input tracks every shape change.
- `test_capture_policy.py:24-62`, `:65-160` build a "compiler 7/8" payload from `compile_execution_model(trusted_execution_inputs())`, then edit version fields and pop keys. The docstring is honest: "not provenance of a genuine archived-8 store"
  (`:69-74`). None of the `reader-v*` fixtures carries an `execution_model` row, and a search finds no other use of `compiler_version` "8".
- `test_release_compatibility.py:124`, `:136-143` builds the historical answer with the current `fact_key` and publishes through the current kernel, so `session.explain(fact)` compares current to current and cannot observe re-keying.
- `test_execution_projection.py:220-300` starts from a retained archive but uses current `_projection_rows` and `_archive_bytes`. A change to `_projection_rows` changes the "historical" input. The old kernel probably refuses impossible shapes (*Inferred*).
- Data-bearing upgrades stop at `semantic_0033`: a search of the tests for `upgrade(conn, "semantic_` finds only targets 0031, 0032 and 0033. Revisions 0034–0040 run only on empty databases.

**Consequence.** A decoder that starts reading a key only today's model has stays green while a genuine payload would fail. An upgrade that breaks on populated data after 0033 fails first in operation.

**Footprint.** *Known:* the sites cited.

**Counterevidence.**
- Real routes are exercised: snapshot, ADBC and export are real, and the read-only refusals are real.
- `tests/fixtures/semantic/README.md:4-14` records a route for genuine fixtures (`git archive` of the unmodified commit), which v10–v12 follow.
- **Weight:** the operator rule that data is regenerable lowers what depends on this. No retained pre-9 store was established to exist, and if none has a consumer, the obligation itself may be overstated, which would be a different correction.

**Uncertainty.** Whether retained pre-9 decoders have any consumer.

**Bears on:** SC2; archive-reader retention decisions.

## Observations recorded without a finding

- **Authored-SQL catalog stage.** `authored_sql.py`'s catalog half has happy-path evidence, one wrong column and one wrong login. A search of the package tests for `unsupported or writable catalog dependency`, `unsupported catalog function`,
  `catalog admission requires restricted`, `analyzed SQL input set differs` and `catalog admission changed` finds nothing, and no test admits any function. This would be a finding if the route were live, but no production authored-SQL input
  exists at this baseline (search of `domains` and `src`), so it is latent. Expected values are hand-written, and nothing in `tests/semantic` imports pglast, so companion §1 is satisfied. Trigger: the first real authored input.
- **Relational compiler target.** `tests/schema/test_relational.py` exercises only the legacy target over `system.yaml`, while runtime uses `target="semantic"` on `physical.yaml` (`semantic/metadata.py:22`). The legacy target is still live for
  Stage A, and `tests/semantic` challenges the physical tables at integration level, so the tests are not dead; the file simply reads as more than it covers.
- **Domain-pack queries.** `test_serving.py:453-462`, `:545-556` install a session into a `cached_property` slot and call `query.rows` directly, so `family_profile`, `parameter_mapping` and others skip binding, paging and size limits. This isolates
  algorithm semantics with exact rows. The CLI `query` route was not surveyed.
- **Aggregated journeys.** `test_reference_evaluation.py:31-452` runs about a dozen obligations in one test, so a first failure withholds the rest. The state is costly and really shared, and messages are specific. No net loss shown.
- **pgpq buffering.** A control on the installed 0.12.0 shows a 2.1 MiB batch emits from `write_batch` and a small one emits only from `finish`, so `test_arrow_publication.py` never exercises the multi-chunk path. No plausible mistake was found: the
  loop writes in order, psycopg skips empty writes, and the server oracle would refuse reordering. Timezone loss, rejected Arrow types and JSONB validation are not reachable from production's stage types.
