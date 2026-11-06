# Evidence and discrimination

## Refresh observations — 2026-11-05

**Interface-checked by source inspection.** These observations use the current source baseline
in the account README. The November2 manifestations below are reconciled against their scoped TA corrections;
prior qualification receipts retain their original dates and applicability.

**DTA-001, additional current manifestation — CLI failures can count as clean lint.**
`tests/schema/test_packs.py:131–142` and `tests/schema/test_model.py:43–58` run `linkml-lint`
with `check=False`, inspect only stdout lines beginning with `error`, and ignore process status
and stderr. A failed invocation with stderr-only diagnostics and empty stdout satisfies those
clean-lint predicates. The metamodel-error positive control in test_model lines62–68 challenges
ordinary reported violations, but not an individual invocation failure.

This is a concrete DP-14/15/23 library-boundary weakness under the existing rejection/outcome
discrimination cause. Context7's LinkML linter documentation and installed LinkML1.12.1
`linkml/linter/cli.py:131–152` expose explicit exit outcomes and structured report formats;
terminal-text absence is a weaker observation. Warning-only status has its own policy and must
not be confused with invocation failure. No new linter or generic assertion framework is selected.
[Upstream linter contract](https://linkml.io/linkml/schemas/linter.html).

<a id="dta-023"></a>

## DTA-023 — Uniform PDF rendering fixtures cannot discriminate crop location

**Interface-checked by source inspection, 2026-11-05; FP-02/05, DP-08/15/23;
companion §1/4/7.** Repository-root `tests/test_native_region_render.py:13–40` creates a blank
PDF page, compares two coordinate-origin renderings and checks their dimensions. A same-sized
crop at another position on that page has the same uniform pixels. Thus an incorrect crop
translation can preserve both assertions, despite the test's stated coordinate-origin claim.
Production `serve/native_regions.py:36–45` contains the distinct origin-dependent crop formulas.

`tests/semantic/test_published_region_artifact.py:178–180` exercises the real renderer and checks
dimensions, then tests artifact custody against the bytes just produced. That provides real
provider, size and custody evidence; it does not independently establish which source pixels
were selected. Coordinate-mapping controls elsewhere independently constrain points but do not
by themselves judge the rendered region. No incorrect production image was observed. A patterned
native fixture is a solution lead, not a requirement for every rendering/transport test.

**Interface-checked by source inspection, 2026-11-05.** See the [baseline](README.md#baseline).
Positive evidence includes hand-authored exact native tuples, malformed inputs, explicit
SQL-null/JSON-null/absence distinctions, graph closure and report failures, scientific uncertainty
and definedness controls, independent geometric expectations and actual owned-child cancellation.
Sharing production validators for downstream setup does not invalidate those tests; independently
judging the validator itself requires a separate expected result.

<a id="dta-001"></a>

## DTA-001 — Some rejection and external-tool assertions do not distinguish the intended outcome

**FP-05, DP-03/14/15/23; companion §1/4/5.** TA-07's selected native controls now
assert independent SQLSTATE/constraint identities. For example, `test_pdf_record_native.py:196–221`
corrects the old mismatched-header manifestation. That scoped correction is preserved.

Current source still contains different weak controls. `test_pdf_publication.py:108` submits
`{"conversion_status":"failed"}` to an already finalized product and accepts any DBAPIError;
the payload is also noncanonical, so malformed-input refusal can satisfy the named late-append
claim. Its seal-without-validation control likewise accepts an unspecified database refusal.
`test_native_fixtures.py:154–183` uses constrained `INSERT ... DEFAULT VALUES` statements and
accepts any DBAPIError for actual-purpose denial claims. A privilege regression can expose an
unrelated missing-value/relational error while preserving those assertions. These are local
fault-discrimination gaps, not observations of an existing bypass.

A stronger current reach failure is `test_local_semantic_admission_native.py:477–505`:
all ten forged-witness cases catch DBAPIError around a direct writer `UPDATE ops.run SET
status=...` before `stage_arrow` and protected publication. The fixture's `case.writer` is an
actual write-purpose engine (`test_private_records.py:185,363`), and
`semantic/sql/execution_guards.sql:104` revokes that status update. Independent
`test_execution_native.py:482–490` expects SQLSTATE42501 for direct writer status updates.
Thus setup refusal can satisfy every corruption case before any forged witness reaches the
claimed publication guard. This conclusion follows from current source; it is not a fresh
native execution or a production bypass observation.

`test_private_records.py:548–585` additionally mutates already-identified candidates and accepts
DBAPIError or InvariantViolation without observing the intended custody/standing guard; changing
identity-bearing content can supply a separate identity refusal. Positive controls elsewhere
recompute identities when the changed input is meant to remain valid.

The LinkML manifestation above is another concrete outcome-discrimination weakness: failed
invocation and clean lint can be observationally identical. Existing exact native SQLSTATE42501,
constraint names, successful siblings, malformed controls and rollback/state preservation are
substantial contrary evidence. A generic exception assertion alone is not a diagnosis; the
confounding outcome here is tied to the specific input and claimed refusal.

A separate **local scoring evidence limit** is
`tests/semantic/test_record_reading_closure_native.py:180–189`: changing center to0.25 and
scale to0.5 for raw signal0.5 preserves `(0.5-0.25)/0.5 = 0.5`. Ignoring both operations
preserves all three expected native scores, including the subsequent coefficient change.
The zero-scale negative case tests validation, not normalization. Independent sklearn evidence
in `test_record_policy.py:202–216` challenges Python scoring, while production SQL has separate
arithmetic (`semantic/sql/record_publication.sql:88–98,170–172`). This names the local oracle's
blind spot; it establishes no erroneous production score or suite-wide normalization absence.
FP-04/05 and DP-11/15/23, companion §1/3/4/7 govern this boundary. Revisit with native scoring.

<a id="dta-006"></a>

## DTA-006 — Some assembled support assertions still establish presence rather than preservation

**FP-04/05, DP-23; companion §4.** The TA-07 selected exact support/member assertions
are corrected and retain their scope. `test_composed_journey.py:76–85` still checks truthy
inventory supports, evidence and source-observation reports while claiming composed evidence.
An additional or wrong support member can preserve those predicates. The same case independently
requires exactly one Alice fact, which constrains a different part of the result. This is a
bounded limitation of preservation evidence, not a blanket objection to existence assertions
or a demonstration that the served support is wrong.

<a id="dta-007"></a>

## DTA-007 — Cold compilation now has independent controls

**FP-06, DP-09/23; companion §1/3/6.** The old load/prepare comparisons remain useful
read/agreement checks but no longer stand alone for cold determinism. `test_prepare.py` includes
fresh-interpreter preparation controls alongside warm reuse, archive and changed-runtime cases;
`test_statistics_model.py` independently exercises frozen artifacts. These source corrections
support the scoped TA-06 disposition. This audit executed neither compiler nor qualification
and makes no cache-thrashing or speedup claim.

<a id="dta-010"></a>

## DTA-010 — Selected catalog mutations now identify stable subjects and expected diagnostics

**FP-02/06, DP-24; companion §4/5.** Current `test_contracts.py` and
`test_execution_projection.py` use stable contract identities and independently specified
subject/diagnostic correspondence for the TA-07 cases. The previous positional-mutation cause
is corrected in that scope. It is not retained as a current allegation merely because some
other tests accept several legitimate errors.

<a id="dta-011"></a>

## DTA-011 — Independent full semantic identity vectors now challenge assembly

**FP-04, DP-04/23; CI-12 where applicable; companion §1.**
`test_identity_vectors.py` supplies independently authored full-key preimages/digests and
scope/value/qualification distinctions. Existing value meanings, PDF scalar/record/fold vectors
and native identity journeys retain separate assurance. The former absence claim is corrected;
current producer/native agreement is not presented as the sole identity oracle.

<a id="dta-013"></a>

## DTA-013 — Selected vacuous work assertions corrected; restricted properties retain their meaning

**FP-05, DP-23; companion §4/6.** TA-07 added positive workset and hydration
observations in `test_statistics_model.py` and `test_domain_operations.py`. The generated
math property still checks values successfully read, with `read > 0`; that is its explicitly
restricted equivalence claim, not a promise of parser-admission coverage. Independent fixed
printer cases and a nonempty corpus reading floor provide other protection. This refresh
requires no arbitrary parser floor and does not revive the retired runtime-share allegations.

<a id="dta-015"></a>

## DTA-015 — Released alias policy and composed product controls correct the spelling mismatch

**FP-02/04, DP-01/23; companion §1/4.** Current `test_alias_policy.py`,
`test_identity_vectors.py` and product/native statistics controls challenge the released full-IRI
alias policy, collisions and affected identity. The former local-versus-prefixed lookup mismatch
is corrected in the scoped TA-08 source. The wider phase0 X2-01 obligation remains at its owner;
this source audit does not claim new corpus merges or qualified normalization outcomes.

<a id="dta-019"></a>

## DTA-019 — Retained references now declare authority and deliberate evolution

**FP-04/05, DP-22/24; companion §4/6/7.** Current math/LLM/ingest/locator builders
state frozen source provenance, independent adjudication and selected successor-reference
updates while preserving original witnesses. Math and LLM helpers explicitly name historical
macro ownership. Current semantic reference guidance separates supported current counterparts
from historical evidence. These corrections support the scoped TA-09 disposition; a pin or
builder alone still cannot establish semantic truth or full-corpus coverage.

<a id="dta-020"></a>

## DTA-020 — Historical relabelling diagnosis remains superseded; supported archives keep their meaning

**FP-04/05, DP-23/24; companion §1/4/6.** `test_release_compatibility.py` explicitly refuses unsupported compiler contracts. Current
`test_archive_reader.py:465–496` also exercises genuine supported compiler14/15 fixtures,
forbids recompilation and independently checks Decimal value/exponent and comparison policy.
Those archived successes keep their original meaning; they are not current-output relabelling.
The old historical-success diagnosis remains withdrawn. Current migrations, custody and protected
reference consumers retain their own obligations and evidence; frozen bytes and earlier failed
or interrupted records are not changed or freshly qualified here.
