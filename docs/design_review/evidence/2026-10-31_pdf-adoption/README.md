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
| Independent references/grading | Six frozen original-source facts across two sections; independent automated A/B/C authors with their own pinned source frames; immutable evaluator pass/grade storage after completed extraction. This is a bounded fidelity universe, not complete section truth. |
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
