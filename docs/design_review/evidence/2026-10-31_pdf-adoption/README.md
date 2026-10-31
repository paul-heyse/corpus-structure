# PDF operational adoption — in progress

This folder retains independent source reference preparation and actual PDF adoption journeys.
Whole-book source publication has passed; assembled adoption and qualification remain in progress.

`source-only-reference-cases.json` was authored from the rendered retained original physical
page85 before any PDF knowledge extraction run. Expected assertions are frozen; native
addresses will be bound separately. `raw/source-page85.png` is a rendering of that original,
not Docling output. Missing mathematical text in `pdftotext` was not used as evidence of absence.

The fresh owned database `corpus_pdf_20261031` was created through `ci db init` with the
creation-only token `e893ff3a9a1544b8b817ebc3f7bf51aa` and migrated to native0047. Historical
operational databases and selection defaults remain unchanged. Initial CLI attempts using
an SQLAlchemy URL and a non-hexadecimal ownership token refused before creation; the corrected
libpq URL and token succeeded. The subsequent `ci db migrate --json` passed through
`semantic_0048`; its physical revision is
`physical:a186c2ad404b1cd82c4f1d6f73951ee466ffea9a78470d40c37aff2c12987e6d`.

Actual configured `claude-opus-5-5` returned `READY` through Claude CLI authentication.
This establishes provider availability only, not source extraction or grading.

The first whole-book source run (`ops.run` 1 / task 1, release
`release:bb3964f422aa9bcdf70cd4587bae13bf59151c2245b33521f695c43052a9abdd`)
**failed** at application-envelope preparation after the converter returned. Its retained
`raw/book-conversion.log` records 30,345 optional `font` null-validation errors; the database
retains the failed run and original, but no native document product. This is not a completed
conversion/publication receipt. The repair omits absent optional application fields and prepares
a minimal validated native capture before optional discovery/report and organization work,
using the existing failed-task native-product retention path.

The integrated producer/consumer endpoint passed warning-inclusive `just types` with zero
diagnostics. `raw/integrated-native-controls.log` retains the subsequent assembled native
selection: its only failure was a lexical-only test still monkeypatching the removed
pylatexenc-3 API. `raw/lexical-boundary-control.log` retains the corrected control passing
with the current structural parser, syntax and macro expansion prohibited. The other passing
results remain applicable; cosmetic maintenance does not invalidate them. The initial selection
named a nonexistent request-test file and collected nothing; that separate refusal is retained
in `raw/integrated-native-controls-selection-refusal.log`. These selections do not establish
complete plan qualification or actual automated extraction.

## Required acceptance union

The applicable production scope is PDF-00–11, not universal recognition fidelity or extraction
of every section in the book. Full-book source custody is separate from the actual five-section
consumer journey. Historical producers, grades and source anchors remain immutable.

| Obligation | Scope and current evidence |
|---|---|
| Full-book source | Original SHA `e98fe358e74d8905b3491654c8db2354c859dcbbcc4cfe096186f25aa4bb63f9`; source-ready run 2/task 2, native + organized products, all 1,589 physical pages. `raw/book-conversion-retry.log`. |
| Final native ownership/OCR | Final spawn-child native/raster/visible-broken/invisible cases and cleanup; actual estimated OCR word inventory + geometry/admission negatives in the sibling `2026-10-31_pdf-child-ocr` evidence. No claim that old book output contains newly added OCR observations. |
| Native enforcement and domain consumers | Focused real PostgreSQL custody/SourceView/frames/ancestor/reference/finalization controls; generic positioned syntax and optional OCR guard controls. Main assembled native-control selection and corrected lexical-boundary receipt retained. |
| Actual consumer adoption | Explicit retained native pin, five maximal intact numbered sections; full selected inline/cell enrichment, M09/M11/M13 and policy/packet consumers. Current run preparation is separate from completed KG publication. |
| Real extraction | Configured authenticated Claude provider through isolated, run-bound external MCP. References/evaluator credentials are absent from its environment/tools. Required for all five selected sections. |
| Independent references/grading | Independent full-section A/B/C references for two intact sections, with their own source frames; six frozen original-PDF facts separately challenge recognition. Run6 inputs prepared; authors, registration and grading not_run. |
| Public interfaces | Actual CLI + external stdio MCP sections/formula/cell/trace/render/digest-refusal/queue calls. Failed attempts and partial call receipts remain separate. |
| Native exports | Actual JSONL/Parquet selected-section exports have 568 equal ordered rows and exact native JSON lexical values. Explicit complete Docling JSON export reloads and validates all 1,589 pages. `raw/book-export-validation.json`. |
| Broad functional/nonfunctional | `just types` before broad testing, complete functional receipt route and applicable hygiene; preserve original failures and rerun only affected scopes after functional repairs. Cosmetic maintenance does not invalidate passing types/tests. |
| Operational selection | Select completed PDF result and update defaults after the actual journeys; preserve prior operational databases and historical grades. |

The book conversion used the retained producer snapshot recorded in its release. Final native
process ownership and OCR inventory capture have independent actual provider receipts; the
current consumer run adopts the exact original product rather than relabel its provenance or
repeat successful inference. Known formula recognition failures remain explicit: the source
product reports 6,338 succeeded, 1 failed and 3 unknown detected-formula outcomes. These are stage
outcomes, not independent mathematical correctness scores.

## Current source and closeout — 2026-10-31

Native 0055 is deployed. Run5/task7 retained the actual selected math enrichment, digest
`8468df6fb3af853b1d0757b18facc7ecd2ff25fa301e8f4b8e05aa2930b6948d`.
The selected discovery universe has 648 aligned anchors and 36 typed unresolved reports.
The native product remains whole-document; recognition completeness is scoped and partial.
Run6 source preparation reused that exact enriched producer pin without model inference or
new native outputs. Its five analysis views and five direct context views, M09/M11/M13 processing
and five awaiting-agent tasks are retained. The exact input is `enriched-source-pin.json`.

Actual run6 CLI native-products/views passed. `adopted-run6-interface-selection.json` is a
prepared caller selection; the current-run external MCP/render journey is not_run. Source-only
reference preparation in `raw/source-only-references-run6` passed and retained exact source,
schema/guideline and original-page inputs. No author A/B/C, extraction provider, frozen-value
comparison, reference registration or grading was run. PDF defaults remain unchanged.

The original broad receipt is retained at
`build/test-receipts/qualification/20261031T222237Z-2596239`. It failed/incompletely reported:
eight assertion failures preceded a 900-second fatal deadline in the second integral parse.
The eight corrected acceptance/conformance/migration/registration cases all passed in
`raw/closeout-targeted.junit.xml`; the original report is never overwritten or promoted.
Formal relation construction and deadline handling were corrected structurally, with separately
bounded grammar/stage controls. No passing type/test evidence was discarded due to formatting.
Zero listed Rust tests establish no Rust functional coverage.

The final math adapter change follows run6's frozen release. Continuing actual execution needs
a compatible current consumer release prepared from task7, with exact recipe/coverage reuse;
regenerate reference frames for that consumer rather than relabel old IDs. Complete actual
MCP/render, independent A/B/C, five-section extraction, evaluator registration/grading, coherent
result/default selection and full qualification remain the coordinator's next work.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**Other**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Whole-book native custody, enrichment reuse and bounded consumer closeout](records/pdf.native-source-closeout.json) | PDF-11 | partial | PDF-01, PDF-02, PDF-03, PDF-04, PDF-05, PDF-06, PDF-07, PDF-08, PDF-09, PDF-10, PDF-11 | 2026-10-31 |
<!-- evidence-index:end -->

## Closeout checks

- `just types`: **passed**, warning-inclusive global check; no new suppressions.
- Corrected acceptance/legacy conformance/migration/registration selection: **passed**, 8 tests
  in `raw/closeout-targeted.junit.xml`.
- `timeout -k 2s 75s uv run pytest -q python/corpus-structure/tests/math/test_grammar.py python/corpus-structure/tests/math/test_stages.py`:
  **passed**, 90 controls at `9db2e87` in the delegated native command. The earlier root rerun
  exposed an order-dependent test memo; its failure is retained in `raw/closeout-math-*`.
  The isolated memo preserves both timeout attempts and nonmemoization expectations.
- `just ruff`, `just clippy`, `just adr-lint`, `just lint-agents`, `just deps`: **passed**.
  Ruff's local exception-style cleanup did not invalidate the preceding type/test receipts.
- `just docs-check`: **passed** after adding a missing library title and replacing two dead
  active-HTML source links with verified historical Git recovery instructions.
- `just evidence`: **passed** with 0 errors; 38 historical warnings remain in the existing account.
  `just rules-scan` and `just rules-test`: **not_run**, no rules exist.

All owned agent processes settled and no worktrees remain outside the main checkout. The
[finalized partial record](records/pdf.native-source-closeout.json) records the source readiness
boundary and incomplete assembled acceptance; it does not replace the failed broad receipt.
