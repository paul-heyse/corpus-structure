# Evidence and discrimination

**Interface-checked by source inspection, 2026-11-12; additions dated 2026-11-13.** These observations use the source
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

<a id="dta-027"></a>

## DTA-027 — The redact-before-clip control passes under either order

**FP-05/06, DP-21/23; companion §1/4.** `tests/test_cli.py:93–106` is named for redaction
before clipping. Production applies `safe_text` and then keeps the last 12,000 characters of
standard output (`src/corpus_structure/cli/operations.py:161,186`). The test's child output is
a 45-character credential-bearing URL, 11,960 filler characters and a 63-character tail holding
two further secrets, 12,068 characters in all. Redaction shortens it to 12,038, of which the
production clip drops the first 38 and keeps only the path end of the already redacted URL.
Clipping first would drop the first 68 raw characters, which is the whole URL and some filler.
Either way the URL credential is gone, and the two tail secrets lie wholly inside the kept
window, where they are redacted under either order. The test asserts only that the three
secrets are absent, so clip-then-redact passes. No secret straddles the boundary.

Redaction of standard error has its own controls through the recipe-reporting route
(`tests/test_cli_recipe_reporting.py:61–64,249–250`); what has no control is ordering at the
6,000-character diagnostic clip (`operations.py:187`).

No leak is observed. The weak observation is an absence on a success path rather than an
undifferentiated refusal, which is why this is kept apart from DTA-001. A related, minor
limit: `tests/test_settings.py:151–154,197–202` assert only that secret substrings are absent
from rendered endpoints. Both fields pass through one masking function whose preservation of
host and port is pinned by sibling tests (`tests/test_settings.py:112,118–148`), so only the
per-field wiring is unpinned there.

<a id="dta-006"></a>

## DTA-006 — Some assertions establish presence or count where the claim is preservation

**FP-04/05, DP-23; companion §4.** The site named on 2026-11-05 is corrected:
`tests/semantic/test_composed_journey.py:109–158` now spells occurrence and evidence identities
independently and compares multisets of supports, evidence and reports. Other current sites
carry the same limit:

- `tests/semantic/test_identity_exclusions.py:127–142` supports a test about grounded
  memberships with row counts and one distinct `establishment` value; which entities were
  grounded is not asserted.
- `tests/semantic/test_exclusion_comparison.py:108–119` compares a run with itself and requires
  no changes and equal examined counts. A comparison that examined rows but always reported no
  change would pass; changed cases are covered at dictionary level in the same file, not
  through the native read.
- `tests/semantic/test_reference_evaluation.py:127–163` submits the same content as passes A, B
  and C (B differs only in whitespace, deliberately), so every score is perfect. The flipped-polarity and duplicate-premise cases later in
  the file can fail a wrong matcher; no case has an unmatched extra or missing claim or a
  partial precision or recall.
- `tests/semantic/test_execution_projection.py:127–133` checks diagnostic fields only for
  truthiness, and `tests/semantic/test_contextual_workflow_native.py:189,198,202` uses substring
  and non-empty checks for a claim about retained compatible edges.

These bound what the named tests establish; none shows a wrong served result. Exact list and
tuple assertions are the norm in the surrounding files.

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
