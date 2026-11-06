# Assertions and independent evidence

**Status:** Original TR-03–05 Implemented; TR-13 amendments Proposed; full qualification stopped. Revised2026-11-06. [Coordinator](../test-audit-resolution_2026-11-05.md)
owns TR-03/04/05 and DTA disposition. Paths below are package-relative unless marked root.

## Target and invariants

Use real production entrypoints and validators for consumer enforcement, independently authored
expected meanings for the responsibility under assessment, and native errors whose intended
cause is observable. Reuse pytest assertions/parametrization, Psycopg diagnostics and current
publication operations. Do not add a second production validation framework or universal test DSL.
Each negative case starts from a positive accepted premise, changes the intended property and
observes the rejection boundary plus preserved state. Setup is outside its expected-error block.

The audit establishes local discrimination defects, not demonstrated production bypasses. Tests
that accept a generic error for a genuinely generic failure remain valid; migrate the identified
claim families and their maintained equivalents rather than imposing a mechanical catch ban.

## TR-03 — Reach and identify native guards

**Inputs:** current source/native contracts; explicit scenario products from TR-01 where used.
**Output:** native refusal evidence that distinguishes authorization, identity, custody, lifecycle
and publication guards. Owner: semantic native test consumers and their source-fixture support.

For `test_local_semantic_admission_native.py:443–514`, replace the forbidden direct writer status
update with the sanctioned execution/consolidation preparation path. Setup must produce the
legitimate output workspace/cut before entering the assertion. Retain actual writer credentials
for staging/publication. Pair each of the ten mutations with successful unchanged input; observe
the expected native SQLSTATE plus stable constraint/primary diagnostic and absence of partial
published rows. Independent boundary observations must establish staging/publication was reached;
permission denial in setup cannot discharge the case. Keep the separate direct-status-update
SQLSTATE42501 control; do not grant writer UPDATE(status) or bypass protected publication.

For private custody/standing controls, recompute ordinary derived IDs when a changed record is
intended to remain otherwise valid. Identity-corruption cases deliberately keep invalid IDs and
expect identity refusal instead. Keep source-derived expected custody and standing independent
of producer `candidate()` values. For actual privilege controls in `test_native_fixtures.py`, use
otherwise valid operations or discriminate SQLSTATE42501 so NOT NULL/FK errors cannot satisfy
an authorization assertion. Observe actual session_user/current_user as appropriate.

For late append/seal controls in `test_pdf_publication.py`, use a valid current-shaped body and
change only finalized/validation state. Establish validation receipt and product lifecycle
premises before the negative action. Follow the same claim through decomposed JSON/integrated
publication callers where they name a native guard; distinguish Python preparation refusal from
native enforcement, retaining useful separate controls for each boundary.

Prefer independent `(sqlstate, constraint_name)` assertions via DBAPIError.orig diagnostics;
use stable primary messages when a named native rule lacks a constraint identity. Sorting or
normalization must not erase the difference under test. Valid siblings, one-fault inputs and
rollback/committed-state observations are acceptance evidence. If corrected tests expose a real
product defect, repair its owning contract and append native migrations as needed, qualify those
consumers, and preserve frozen migration/evidence bytes. A looser test is not a fallback.

## TR-04 — Exact semantic and numerical expectations

For `test_composed_journey.py`, derive expected support/evidence/source-report membership from
its hand-authored source/scenario. Assert exact semantic identities, multiplicity and relevant
relationships under the contract's ordering semantics, not merely nonempty arrays. Keep the
existing exact Alice fact assertion. Exercise wrong member, omitted member and extra member
controls where the shared comparison could otherwise hide them; do not sort away multiplicity
or require incidental row order. Independent full identity vectors remain the authority for key
assembly; reuse production keys only for downstream setup with that distinction explicit.

For the native predictor in `test_record_reading_closure_native.py`, retain the eight independently
specified raw signals and pinned weighted baseline. Add separately revealing valid centering and
scaling inputs. For raw first signal0.5, coefficient1, changing only center to0.25 changes48.75
to48.50; changing only scale to0.5 changes48.75 to49.25. Also check combined parameters whose
result is not raw0.5. Derive arithmetic by hand from the stated linear score contract; do not
compute the expected score through Python production scoring or SQL under test. Keep unknown,
misordered and zero-scale refusal tests and Python/sklearn comparison as separate guarantees.
The introduced cases target native standardization, not a broader statistical-quality claim.

TR-04 consumes only the migrated source contract it needs; numerical vectors can land without
waiting for all scenario work. Preserve exact numeric kinds, negative zero, Decimal exponent,
absence/null, qualification, direction and endpoint multiplicity wherever those define meaning.

## TR-05 — Real CLI outcomes and native crop location

### LinkML

Retain CLI coverage for the pinned LinkML1.12.1 and repository lint configuration. Select
`linkml-lint --ignore-warnings --format json` with captured stdout/stderr and require successful
exit before accepting the report. Warning allowance matches the current error-only policy.
Decode the installed formatter's JSON array and reject error-level problems; malformed/missing
reports are failures, not clean lint. A valid clean report is an empty array; warnings remain
available in diagnostics. Use one narrow test-support function for the two existing lint callers,
not a generic CLI runner. Seeded metamodel rejection still exercises the real CLI.

Acceptance separates clean, warning-only, error-level, configuration/argument failure with empty
stdout, and malformed report. Exception assertions cannot substitute for real CLI positive and
negative controls. Test the interpreter of a failed subprocess result with an independent canned
result if needed; do not replace the actual lint contract with a mocked provider pass.

Context7 and installed `linkml/linter/{cli.py,formatters/json_formatter.py}` establish exit0/1/2,
warning policy and JSON shape. [Upstream contract](https://linkml.io/linkml/schemas/linter.html).

### PDF rendering

Replace the uniform-page oracle in root `tests/test_native_region_render.py` with a small
asymmetric native PDF, using installed PDFium/Pillow creation capabilities rather than a new
rendering service. For example embed a hand-specified unequal color pattern through
`PdfImage.new`, `set_bitmap`, explicit matrix placement, `PdfPage.insert_obj` and `gen_content`.
Close document/page/bitmap/image handles through their real lifetimes.

Author expected interior color/location samples from source coordinates, avoiding anti-aliased
edges and text/font variability. Assert dimensions, expected interior features and exclusion of
features outside the requested region for both top-left and bottom-left forms. Two same-sized
translated crops must have different expected content. Do not derive expected locations from
production crop formulas or use its full-page output as the sole oracle. Keep invalid geometry
and retained-page-dimension refusals. Extend the real published-region artifact journey to retain
an independently identified feature, while preserving byte custody/metadata as distinct claims.

PDFium render crops are `(left,bottom,right,top)` amounts in canvas units; rendering and cropbox
editing are different operations. Installed helper source and [PDFium Python API](https://pypdfium2.readthedocs.io/en/stable/python_api.html)
qualify the mechanism. No GPU/model or external rendering provider is required for this control.

## Preservation and completion

Relevant existing native guards, full-key vectors, reference source meanings, stable diagnostic
IDs, real SDK transport and production serializer tests remain. TR-09 reconciles their final
applicability. Each capability gets focused functional checks and appropriate typing/lint at its
coherent endpoint. The coordinator's TR-10 owns final integration; no full campaign per assertion
or helper, automatic mutation suite, snapshot regeneration or reference rewriting is required.

## Encountered qualification repair — 2026-11-06

The initial serial broad attempt found one stale assertion in root test_native_render_preparation:
it expected runtime_id in the renderer provenance payload. Current PdfRendererProvenance has exact
implementation_digest/pypdfium2/Pillow fields; runtime binding is qualified separately. Independent
focused review accepted the test-only correction. The explicit qualifier call assertion remains,
and the expected renderer fields come from the qualified archive. Only that failed node was rerun;
it passed in build/test-receipts/qualification/test-audit-renderer-failure-repair-20261106.
Successful cases were not rerun. Full attempt and interruption remain retained; coordinator owns
remaining1390-node scope and the operator stop. No full qualification claim follows.


## TR-13 — Independent question matrices and diagnostics

**Proposed,2026-11-06; review I07/I08.** Extend current independent operation-assessment controls
and native component custody tests with the scenario inputs from the preparation companion.
The assurance owner authors expected endpoints, roles, multiplicity, state and numeric boundaries;
production validators may enforce setup but do not compute both actual and expected meaning.
Stable pytest.param IDs identify question/facet and distinction. Required outcomes remain separate
collected cases; runtime subtests are optional diagnostics inside a case, not new union obligations.

Required current-contract cases distinguish right location/wrong role (the WCE-R01 regression),
right role/wrong endpoint, compatible overlap/exclusive alternatives, missing/extra/duplicate exact
outputs, repeated windows/physical occurrences, missing reference/missing output, ambiguous/unresolved,
unstated/uninspected and local component support/unsupported whole statement. Exposure/partition
controls retain original origin family (WCE-R02); parameter/header/note examples (WCE-R03) enter
only with suitable actual source and question. No synthetic case establishes authentic source
quality or independent author agreement. Protected A/B/C reference services remain semantic owners;
pytest gains no second reference ledger. Later threshold/unit/revision/cohort cases enter with their
actual WCE producers, without expanding this test series into those product algorithms.

Reuse assert rewriting for shared assertion modules before import, narrow pytest_assertrepr_compare
where useful, and Item.add_report_section for phase diagnostics. Show frozen frame/question/source
identifiers, facet, expected/actual endpoint-role members and missing versus uninspected. Do not
dump protected answers, normalize away duplicates or build a new assertion engine. Exact row sets,
Counter-style bags and independently specified numeric tolerances remain credible simple choices.
Native errors retain intended SQLSTATE/constraint/message identity, positive premises and valid siblings.

TR-15 compares the same current located-component custody/basis case in Python and SQL before
selecting pgTAP. SQL expectations use results_eq only for contractual order, bag_eq for multiplicity,
set_eq only for true sets; schema/signature-qualified catalog assertions protect promised properties,
not every installed object. Name inventory is not overload inventory; generated body checksums do
not replace independent behavior or existing native_sql_body/source_frame_admission attestation.

Acceptance includes deliberate wrong answers for each changed comparator, exact required case
membership and phase-attributable distributed diagnostics. Native/read/CLI/MCP/export variants
establish only their exercised boundaries. Existing frozen archive meanings and original failed
attempts retain their own historical scope; current-only cutover determines executable counterparts.
TR-09 reconciles consumer/retirement coverage; TR-10 qualifies the selected final source.

Mechanisms and versions: pytest9.1.1 rewriting/parametrization/public reports and the existing
Psycopg diagnostics, from the [pytest reference](../../libraries/analytical_infrastructure/pytest.md)
§5/6/9/10. No9.2-only public types or automatic snapshot updates are selected. The [WCE assessment
owner](../witnessed-corpus-enrichment/assessment-source-expansion-and-qualification.md) retains
source quality, fitting eligibility and later producer-specific requirements. WCE plan files are unchanged.
