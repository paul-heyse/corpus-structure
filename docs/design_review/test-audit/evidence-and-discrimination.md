# Evidence and discrimination

**Interface-checked by source inspection, 2026-11-12; additions dated 2026-11-13 and 2026-11-17.** These observations use the source
baseline in the [account](README.md#baseline). Prior qualification receipts retain their original
dates and applicability; nothing here is a fresh native execution or an observed production
defect.

Positive evidence in the changed scope is substantial and bounds the findings below:
hand-authored identity preimages and digests, literal Arrow rows with hand-derived results,
analytic closed forms for table interpretation, asymmetric rendering fixtures, hand-authored
gold with deliberately wrong predictions in scoring tests, native refusals pinned to SQLSTATE
plus message or constraint with a positive control in a rolled-back savepoint, and
unknown/absent/empty distinctions in serving and gap tests. Sharing production validators for
downstream setup does not invalidate those tests; judging the validator itself still needs a
separate expected result.

<a id="refresh-2026-11-17-evidence"></a>

## Refresh of 2026-11-17

**Interface-checked by source inspection, 2026-11-17**, source `fbd3f2a98`
([baseline](README.md#baseline)). No test was run; this section judges whether the evidence
would detect a wrong implementation, not whether it currently passes. The production side
gained many mechanisms that reuse work or skip a check, and several of the commits that added
them record `runtime not_run`. The question asked of each was: if the reuse were wrong (stale,
wrongly keyed, too broad, racing), which test would fail?

| Earlier finding | Status at `fbd3f2a98` |
|---|---|
| DTA-001 | Standing, changed footprint (new sites below the finding) |
| DTA-033 | Corrected on 2026-11-13, then regressed in its native half |
| DTA-027 | Corrected |
| DTA-006 | Corrected at its one surviving site |
| DTA-007 | Stands as sound |
| DTA-010, 011, 013, 015, 019, 020, 023 | Not re-examined |

Much of the new machinery is well tested, and that bounds the findings: the archive open cache
(cold race, eviction order, header change mid-open), the preparation caches (each determinant
perturbed, a colliding-hash subclass refused), file and query custody (content confirms
metadata; reload refused), the CPU worker cache (a tampered digest refused on a warm worker),
native residency (a stale timer replayed deterministically), the prepared grammar against an
independent test-only oracle, shared PDF streams (tamper refusal, cross-project isolation,
reclaim races), and the encoder and GLiNER provider panels (singleton reference under mixed,
reversed and regrouped cohorts).

<a id="dta-044"></a>

### DTA-044 — Mechanisms that skip a check or carry a result forward are tested only where the reuse is correct

**FP-02, FP-04, FP-05, FP-06; DP-23; A4; companion §1, §4.**

Each item below is a production mechanism whose purpose is to avoid repeating work that was
already established. In each, the tests exercise the path where skipping is right and not the
path where it must not happen.

- **PDF round-trip oracle skip.** A build may skip the reconstruction oracle when a passed
  receipt exists for the same lowering identity and kind, bound to a published revision
  (`src/corpus_structure/semantic/pdf_certification_native.py:62–90`;
  `semantic/pdf_publication.py:851–900`). No test asserts that decision, although the skip
  very likely executes unobserved wherever one test publishes several builds with the same
  lowering (`tests/semantic/test_pdf_publication_identity.py:390–405`). A search of both
  test trees for the certification basis, the oracle begin and finish calls and the force flag
  finds only a key declaration and literal values fed to doubles. The lowering-identity test
  compares the identity with the digest of the artifact the same function returns
  (`tests/semantic/test_pdf_producer_certification.py:135–146`); no test perturbs a lowering
  input or reaches the drift refusals (`semantic/pdf_lowering.py:284–292`). Accepting a failed
  or unpublished receipt, matching across kinds, or a manifest that omits an input would all
  pass. This is the one mechanism here that removes an established check rather than reusing a
  computed value.
- **Kernel-sealed completion.** The publish-time battery runs only when the receipt's kernel
  digest differs from the installed one (`semantic/sql/data_operations.sql:1476–1482`). Every
  test publishes under the installed kernel, so the fallback never executes
  (`tests/semantic/test_data_operation_storage.py:2860–2880` checks the equal path).
- **Lowered release facts.** Readers refuse a release whose lowering digest differs and
  re-admission re-lowers (`:460–466, 2424–2431`). Tests check that the column exists
  (`tests/semantic/test_data_operation_lowering.py:6–28`).
- **Set-wise validity.** The scalar check now delegates to the set evaluator
  (`:391–434`), so scalar tests are no independent reference. One test addresses the closure
  directly, with duplicate seeds of one episode and a self-loop
  (`test_data_operation_storage.py:2815–2840`). None has several distinct seeds sharing
  descendants, mixed valid and invalid seeds, a two-node cycle or population supersession. A
  scalar journey does show revocation through a shared ancestor invalidating two dependents
  (`tests/semantic/test_structural_admission_native.py:689–730`).
- **Query cache budgets.** The demand key includes `max_bytes` so that an entry filled under a
  larger budget cannot bypass a smaller one (`semantic/demand_queries.py:196–212`). No test
  varies it against a warm entry, and rich graph-budget refusals run only cold because an
  autouse fixture clears the cache per test
  (`tests/semantic/selected_query_cache_support.py:13–17`). Eviction by byte capacity is tested
  (`tests/semantic/test_selected_query_cache.py:25–46`); the entry-count bound is never
  exceeded. Consumer tests replace the native recheck with a double that re-implements its
  refusals (`:27–43`).
- **Change scope.** An unrelated source edit is shown to change no operation
  (`tests/semantic/test_change_impact.py:118–127`), but no model with several operations
  asserts that an unrelated operation stays outside the affected set (the one assertion on it
  is in a two-operation model, `:136`). By search, no native test shows that a revocation in
  one source scope leaves a read pinned only to another scope current; the expression-level
  check covers an added zero-epoch scope only
  (`tests/semantic/test_data_operation_trust_snapshot_sql.py:46–53`).
- **Smaller instances.** The racily-clean window of file custody is never derived as true
  (every fixture advances the clock ten seconds; `tests/semantic/test_file_custody.py:16–21,
  66–78`). The execution-basis cache key names the source root and run determinants, and
  neither is varied, although the test's name claims root exactness
  (`tests/orchestrate/test_execution_host.py:68–125`). As a hypothesis only: the "no
  re-recognition" guards patch `grammar.syntax`, which production's prepared path calls, so a
  regression that reached recognition through `grammar.parse` instead would bypass them; no
  such consumer was shown.

**Consequence.** For each item there is a plausible regression (always skip; drop the refusal;
validity depends on what else was seeded; a budget dropped from the key) that changes what is
published or served and fails no test.

**Contrary evidence.** The oracle itself discriminates (it refuses a lossy but callback-valid
lowering, `test_pdf_producer_certification.py:156–235`); the retention-time battery runs in
every publishing test; production rechecks native authority before every cached use and that
ordering is asserted (`tests/semantic/test_demand_results.py:150–163`); the native validity
journeys have hand-designed expectations and real revocation.

**Limits.** Absence is by search of both test trees with the terms named. Evidence records
outside the tests (for example the qualification behind ADR-0130) were not examined, so for the
oracle the finding may narrow to "no repeatable test".

<a id="dta-045"></a>

### DTA-045 — The native host's frozen-profile refusal is asserted against a rule the test double invents

**FP-02, FP-05, FP-06; DP-23; companion §1, §4, §5.**

`test_frozen_artifact_mismatch_refuses_before_starting`
(`tests/methods/test_characterization_resources.py:243–252`) expects a refusal matching "frozen
selection". The only source of that message is the test's own `Group.startup` (`:59–61`), which
refuses before creating a worker, so the accompanying "nothing was opened" assertion holds by
construction. Production has no such check before startup. The real checks run after spawn: the
child refuses when shared host artifacts differ from the frozen profile
(`src/corpus_structure/methods/native_host_adapters.py:42–44`) and the parent refuses when the
host reports a different profile (`methods/native_host.py:197–213`). Neither message, nor
`_validate_startup`, appears in a test; the real-process peer always echoes the declared
profile (`tests/methods/native_host_cases.py:25–39`).

**Consequence.** If the parent comparison lost a field or the child comparison were removed, a
host running a different checkpoint, dtype or thread policy would serve results under the
frozen identity that receipts and warm reuse depend on, and no test would fail.

**Contrary evidence.** The runtime-identity refusal has a real control
(`tests/methods/test_native_host.py:291–296`), and the parser's startup observation is tested
field by field (`:602–680`). Established.

<a id="dta-046"></a>

### DTA-046 — No controlled encoder-batch test has two surviving members with distinct outputs after a member is dropped

**FP-05, FP-06; DP-23; companion §4, §5.**

The controlled batch tests replace the model with one that returns the same vector for every
text, with one exception that returns a different, invalid vector at one index
(`tests/semantic/test_contextual_encoder_batch.py:104–127`;
`test_contextual_owned_encoder.py:23–31`). That exception does check attribution in a batch
where nothing is dropped: the failure lands on the right member and the other succeeds
(`:243–249`). With one member dropped from a two-member batch, the single survivor's slot is
checked (`:167–178`). The risky step in the batch form is realignment after a drop when
several members survive, and no controlled test has two or more survivors with distinct
outputs; an off-by-one there would pass. Attribution across cohorts is otherwise checked by
the provider panel, which needs provider evidence and model snapshots
(`test_actual_encoder_batch_semantics.py:19, 148`).

**Consequence.** In the ordinary lanes a realignment regression after a dropped member could
publish vectors under the wrong occurrence undetected.

**Contrary evidence.** The GLiNER coalescing double keys its reports by context id and does not
share this blind spot (`tests/methods/test_characterization_resources.py:353–386`). A small
real encoder with a distinct vocabulary exists in test support
(`tests/semantic/current_contextual_support.py:12–52`) and drives native workflows over several
targets (`test_contextual_workflow_native.py:137–140`); whether any of those drops a member and
asserts per-member vectors was not established.

## Earlier findings

<a id="dta-001"></a>

## DTA-001 — Some refusal assertions do not distinguish the intended outcome

**FP-05, DP-03/14/15/23; companion §1/4/5.** The cause persists with a changed footprint. Every
manifestation named on 2026-11-05 is corrected in source; different sites now carry it.

Corrected since the last account:

- LinkML: `tests/schema/lint_support.py:9–39` asserts the exact return code, parses the JSON
  report and requires errors exactly when the code is 2; `tests/schema/test_lint_support.py`
  holds negative controls for invocation failure. Warnings remain suppressed by
  `--ignore-warnings`, which is the stated policy.
- `tests/semantic/test_pdf_publication.py:150–171` pins `P0004` and its message for late append
  with a canonical payload. The seal control at `:363–369` is only partly corrected: after
  asserting state it pins `P0002` "query returned no rows", the generic strict-lookup error that
  any missing row in the seal path would raise.
- `tests/semantic/test_local_semantic_admission_native.py:505–660` now stages each forged batch
  through the publication route after a clean baseline and asserts a per-corruption SQLSTATE
  with message or constraint (`:597–621`); the direct status update is its own test asserting
  `42501` (`:696–711`).
- `tests/semantic/test_native_fixtures.py:192–199` asserts `42501` per denied statement.
- `tests/semantic/test_private_records.py:131–176` asserts SQLSTATE and exact message after a
  positive control.

Current manifestations:

**A refusal that would occur without the guard under test.**
`tests/semantic/test_publication.py:225–231` and `tests/semantic/test_arrow_publication.py:180–185`
claim a restricted writer cannot bypass staged publication. Both insert a `data.entity` row whose
realization does not exist and accept any `DBAPIError`. `data.entity` declares a foreign key on
`(realization_id, release_id)` to `data.realization` and admitted immutability
(`src/corpus_structure/model/semantic/physical.yaml:499–521`). With the fence in place
PostgreSQL reports the privilege error first; the point is that without it the insert would
still raise a database error, so these controls cannot fail for the regression they name. The
same shape appears in `tests/semantic/test_native_closure.py:66–75`: four of its five statements
would still be refused by the immutability triggers that the next block of the same test
matches by message (`:76–90`); only the `SELECT` discriminates, because a granted read would
succeed. In `tests/evaluate/test_record_references_native.py:99` the refused pass B had already
been recorded at `:86`, so a uniqueness refusal alone satisfies the check. The exposure is
bounded: `tests/semantic/test_native_fixtures.py:155–199` pins `42501` for every restricted
role on representative statements, so a schema-wide privilege regression is caught; what is
unpinned is the privilege on the specific tables these tests name.

**Mutation families asserted under one undifferentiated refusal.** Each builds several
deliberately different corruptions and accepts the same exception class with no reason:

- `tests/evaluate/test_operation_fitting_native.py:279–307`: twelve labelled mutations; the
  label is bound as `_label` and discarded.
- `tests/semantic/test_contextual_enrichment_native.py:65–157` (thirteen corruptions; atomicity
  is asserted afterwards), `tests/semantic/test_interpretations_native.py:162` (eight),
  `tests/semantic/test_arrow_publication.py:456–493` (six),
  `tests/evaluate/test_record_references_native.py:97–108`.
- `tests/semantic/test_runtime_bindings_native.py:136–148`: eight mutations under SQLSTATE
  `23514` alone, a class shared by several checks.
- `tests/semantic/test_review_bundle.py:673–773`: sixteen bundle corruptions ending in bare
  `pytest.raises(ValueError)` (`:771`).

A corruption rejected by a neighbouring check, or a mutation that breaks row shape rather than
custody, satisfies these controls, so removal of one specific guard can go unnoticed while the
others still refuse.

**CLI refusals asserted by exit class or a shared substring.**
`tests/methods/test_m1_cli.py:9–35` checks five different pin refusals with `exit_code == 2`
and any of four words including `configuration`, which is part of the option name the parser
echoes for unrelated usage errors. `tests/test_source_cli.py:356–357` asserts only a nonzero
exit for a retired positional form. The first test's guard that no database is opened is real
and unaffected.

**A scoring expectation with a neutral parameter.** The 2026-11-05 limit in
`tests/semantic/test_record_reading_closure_native.py:179–192` is corrected: changing center or
scale now changes the expected native score. A narrower sibling remains in
`tests/methods/test_m1_readings.py:200–209`, which recomputes a score from `fitted()` parameters;
the training values in `tests/semantic/test_record_policy.py:76–91` are symmetric about zero, so
`center` is exactly zero and an implementation that dropped centering produces the same
expectation. Scale is non-unit and is detected. Independent sklearn evidence in the same policy
module challenges the fit itself.

Counterevidence. The same files and their neighbours contain many controls that pin SQLSTATE,
constraint or message, often with an honest note on which layer owns the refusal
(`tests/semantic/test_pdf_integrated.py`, `tests/semantic/test_execution_native.py`,
`tests/evaluate/test_characterization_assessment_native.py:420–581`,
`tests/semantic/test_contextual_query_replay.py:289–296`). Many pure-Python `ValueError`
matrices mutate one field of a validated positive in the same test, which limits confounding. A
generic exception assertion alone is not a diagnosis; the sites above are those where the input
or the shared class makes a different refusal a plausible pass. Counts for files that were
sampled rather than read in full come from targeted search and may be incomplete.

**Status, 2026-11-17, source `fbd3f2a98`.** Standing, changed footprint. Corrected sites: the forged-graph family pins an exact SQLSTATE and message per mutation (`tests/semantic/test_data_operation_storage.py:2529–2538`), and `tests/semantic/test_native_closure.py:47–53` pins `42501` per statement. New sites that accept an undifferentiated refusal, each a place where a neighbouring check could refuse in place of the named one:

- bare `DBAPIError`: `tests/semantic/test_established_validity_native.py:122` (six premise perturbations), `test_data_operation_context_fanin_native.py:158`, `test_data_operation_binding_native.py:714`, `test_data_operation_external_native.py:169`, `test_data_operation_authored.py:212`, `test_data_operation_population_selection.py:168`, `test_current_pdf_integration_native.py:107–167` (five forged receipt fields and four reader variants);
- bare `ValueError`: `test_record_publication_native.py:167–200, 304, 363` (the serving scope gate), `test_definition_model_native.py:132–164` (fourteen cases across two tests);
- one exception class for twelve distinct corruptions: `test_execution_admission_expectations.py:81–136`;
- SQLSTATE `23514` alone, a class several checks share: `test_pdf_shared_streams.py:143, 224`.

A positive control precedes most of these. `tests/test_source_cli.py:231, 274, 367` still assert only a nonzero exit.

<a id="dta-033"></a>

## DTA-033 — The product identity production uses is checked only against itself

**FP-04/06, DP-04/23; A2; companion §1/4. Interface-checked by source inspection, 2026-11-13.**
ADR-0100 made the full subject context part of product identity. Production now computes product
keys with `contextual_product_identity`
(`src/corpus_structure/semantic/data_operation_identity.py:471`), called from the construction,
sentence, formal, canonical-sentence and enriched-document producers.

Its only test derives the expectation from the function under test:
`tests/semantic/test_data_operation_storage.py:1791–1817` reads the stored request context,
calls `contextual_product_identity` and compares the result with the key the native side
stored. The pure identity module does not mention the function. It tests `product_identity` and
`subject_identity` (`tests/semantic/test_data_operation_identity.py:297–317`), which no longer
have a caller under `src/`.

What the existing checks still catch: a context component being dropped, since the same test
varies scope, source and project and asserts distinct products; and a disagreement between the
Python and SQL implementations. What would pass: a framing or field-shape mistake made the same
way on both sides, such as a wrong domain tag or the wrong nesting of the context, and any
regression in how the local subject is qualified, which no pure test varies. The plan asks for
exactly the missing control: expected canonical values and identities that are not derived from
production (`docs/plans/declared-data-operations/contracts-and-compilation.md:354`), and
ADR-0100 says independent vectors migrate with the identity.

Counterevidence. Canonical framing and JSON meaning do have hand-authored literal vectors
(`tests/semantic/test_data_operation_identity.py:36–76`,
`tests/semantic/test_data_operation_identity_native.py:21–116`), and the semantic identity
vectors recorded under [DTA-011](#dta-011) still hold. The gap is this one identity, which is
the one products are now keyed by. The tests of the two superseded helpers are a small instance
of [DTA-035](retirement-transfer.md#dta-035).

Two lower-weight discrimination notes from the same modules, in the footprint of
[DTA-001](#dta-001): the forged-graph family accepts any of three reasons for each of its four
mutations (`match="graph|closure|discovery"`, `tests/semantic/test_data_operation_storage.py:2000`),
where the plan asks that a refusal name the unmet obligation; and two tests restate a registry
size (`len(...) == 18` at `test_data_operation_storage.py:39` and
`test_data_operation_wire.py:111`).

**Inspected with no shortfall established, 2026-11-13** (a contributor's reading of about 60% of
the declared-data-operation test lines): compilation and source-capture expectations are
hand-authored node ids, surfaces and refusals, with recipe sensitivity tested by controlled
perturbation and unknown kept distinct from absent; graph cases use hand-authored topologies
including a self-loop and a two-node cycle; wire bounds are independent and generated types are
exercised by behavior, not compared with a regeneration; equal bodies under different contexts
are shown to give distinct products; and concurrency controls use real transactions.

**Status, 2026-11-17, source `fbd3f2a98`.** Corrected on 2026-11-13, then regressed in its native half. The shared literal product vector gained `subject_definition` on 2026-11-15 (commit `9256dfd94`; `tests/semantic/data_operation_identity_vectors.py:18–24`). The Python consumer builds its input through production's subject context and followed the change. The native consumer builds its input by hand without that field (`tests/semantic/test_data_operation_identity_native.py:25–35`) and compares the native identity with the digest of the literal (`:37–41`). The native function cannot add a missing key (`src/corpus_structure/semantic/sql/data_operations.sql:122–147`), so the five parametrized cases cannot pass as written. Production's own product key includes the field (`:1601`), so the literal is right and the test input is stale. No stored result has run them since 2026-11-15, so this is established from source and not observed. The commit message says "291 focused controls passed"; whether this test was among them is not recorded.

The structural cause: the vector file shares only the expected bytes, and each consumer rebuilds the input. Until the native half is restored, the only native check of the identity that keys products is the storage test that compares the Python and native implementations with each other (`tests/semantic/test_data_operation_storage.py:2289–2294`). The request identity has no literal vector at all, and its completeness test does not vary `subject_definition` (`tests/semantic/test_data_operation_identity.py:407–430`). A related instance on the new search cursor: the expected selection digest is recomputed by running the production projection (`tests/semantic/test_source_search.py:141–185, 222–227`).

<a id="dta-027"></a>

## DTA-027 — Corrected

**Corrected (2026-11-17, source `fbd3f2a98`).** `tests/test_cli.py:162–192` covers stdout and stderr with the secret placed at the clip boundary and checks the exact output. Earlier text is in Git at `fbd3f2a98`.

<a id="dta-006"></a>

## DTA-006 — Corrected at its surviving site

**Corrected (2026-11-17, source `fbd3f2a98`).** The one surviving cited site now asserts exact edge sets and witness lists (`tests/semantic/test_contextual_workflow_native.py:360–369`); the other cited files were deleted. Earlier text is in Git at `fbd3f2a98`.

<a id="dta-023"></a>

## DTA-023 — Rendering fixtures now discriminate crop location

**FP-02/05, DP-08/15/23; companion §1/4/7.** Corrected in source. Root
`tests/test_native_region_render.py:12–42` renders `asymmetric_pdf()` (root
`tests/pdf_region_support.py`) and asserts specific red, green and white pixels, origin
equivalence, and a blue pixel after a translated crop.
`tests/semantic/test_published_region_artifact.py:178–182` checks the same landmarks on the
direct renderer call.

A narrower residue remains in that file: the tool-driven path renders at another scale and
asserts content type, disposition, digest equality between deliveries and artifact existence
(`:283–335`), not pixels. A wrong pointer, region index or page resolved inside the tool path
would pass; rasterization itself is covered by the direct call. Revisit if the tool path gains
its own address resolution.

<a id="dta-007"></a>

## DTA-007 — Cold compilation has independent controls

**FP-06, DP-09/23; companion §1/3/6.** Still holds. `tests/semantic/test_prepare.py:524–620` is
unchanged since the previous baseline, and `tests/schema/test_packs.py:67–82` adds a
two-process, two-seed, two-path control for pack hashes.
`tests/semantic/test_execution_release.py:77–122` and `test_prepare.py:528,559` clear the
process-wide preparation cache; whether an entry prepared under a monkeypatched constant can
outlive its test was not established and is recorded as an open question, not a finding.

<a id="dta-010"></a>

## DTA-010 — Selected catalog mutations identify stable subjects and expected diagnostics

**FP-02/06, DP-24; companion §4/5.** Still holds; `tests/semantic/test_contracts.py:210–360` and
`tests/semantic/test_execution_projection.py` are unchanged for the cited controls. The
truthiness-only diagnostic fields are noted under [DTA-006](#dta-006).

<a id="dta-011"></a>

## DTA-011 — Independent full semantic identity vectors challenge assembly

**FP-04, DP-04/23; CI-12 where applicable; companion §1.** Still holds;
`tests/semantic/test_identity_vectors.py` is unchanged since the previous baseline.

<a id="dta-013"></a>

## DTA-013 — Selected vacuous work assertions corrected; restricted properties retain their meaning

**FP-05, DP-23; companion §4/6.** Still holds. `tests/math/test_property.py:99–104,138` keeps
its reading floor and the explicitly restricted generated property. The workset and hydration
observations in `test_statistics_model.py` and `test_domain_operations.py` were not reread.

<a id="dta-015"></a>

## DTA-015 — Released alias policy and composed product controls correct the spelling mismatch

**FP-02/04, DP-01/23; companion §1/4.** Still holds; `tests/semantic/test_alias_policy.py` and
the identity vectors are unchanged since the previous baseline. The wider phase 0 obligation
remains at its owner.

<a id="dta-019"></a>

## DTA-019 — Retained references declare authority and deliberate evolution

**FP-04/05, DP-22/24; companion §4/6/7.** Holds for what was read:
`tests/semantic/reference_scenarios.py:1–5` and `tests/semantic/test_reference_split_authority.py`
state authored ownership, independence claims and ABI-refusal behavior; `tests/math_support.py:
10–13` and `tests/llm/conftest.py:7–10` keep their frozen-oracle statements. Reference identities
are built with production identity helpers over hand-authored content.

<a id="dta-020"></a>

## DTA-020 — Historical relabelling diagnosis remains superseded; supported archives keep their meaning

**FP-04/05, DP-23/24; companion §1/4/6.** Still holds;
`tests/semantic/test_archive_reader.py:464–490` loads the supported compiler fixtures, forbids
recompilation and checks Decimal value and exponent. `test_release_compatibility.py` was not
reread.
