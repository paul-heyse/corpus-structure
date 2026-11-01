# PDF-17–19 record/identity foundation — 2026-11-01

**Implemented; targeted Tested.** ADR-0042 and the PDF coordinator own target and disposition.
Source baseline09ef5dff; integrated production through0a3ffd2d, including core/system0.6.3 compiler
bookkeeping, generated schema identities and final test annotation repairs.0060 remains deployed;
0061–0063 are committed and undeployed. No inference,
provider grading, operational data conversion or live migration was run.

## Actual checks

- **passed:** final foundation/schema regression union after the0.6.3 regeneration:
  **394passed/4warnings**,185s (`pdf-foundation-final-model-union.log`), including frozen
  forward-product reproduction. It subsumes the187-case union and five affected controls below;
  counts are not summed. Final global `just types` and `uv run ruff check .` passed
  (`pdf-foundation-final-model-types.log`, `pdf-foundation-final-model-ruff.log`).
- **passed:** warning-inclusive `just types` after integration and test annotation repairs;
  zero Pyrefly diagnostics/suppressions added (`pdf-foundation-main-types.log`).
- **passed:** `uv run pytest` over the eight files below, `-q -o addopts='' --maxfail=3`:
  **187passed/4warnings**,65s (`pdf-foundation-main-union.log`). This is the selected foundation
  regression union, not complete pipeline qualification. It includes native database cases.
- **passed:** final affected rerun of `test_pdf_record_native.py -k 'function_identity or graph_cell'`
  after test-only narrowing/raising-callback repairs: **5passed/9deselected/2warnings**. These overlap
  the187 and are not an additional disjoint count.
- **passed:** `uv run ruff check .`; ADR lint39records. Formatting-only changes do not invalidate
  applicable passed types/tests; exact authored source provenance has separate reproduction controls.
- **failed:** first assembled run113passed/3failed, retained as `pdf-foundation-main-union-initial.log`.
  It exposed owned-function test setup and OUT/TABLE/private-visibility integration errors.
- **failed:** first reconstruction-hardening run89passed/1failed on a changed diagnostic expectation,
  retained as `pdf18-main-controls-initial.log`; corrected90-case pass follows.
- **failed:** full `just docs-check` on existing relocated-library/retired-source links outside the
  updated owning pages (`pdf-foundation-docs.log`). Focused owning-page checks are recorded separately.
- **failed:** final `just model check` exposed compiler3 versus the logged compiler2 revision;
  generation correctly refused an unrecorded revision (`pdf-foundation-model-check-initial.log`,
  `pdf-foundation-model-generate.log`). A parented0.6.3 change record and regenerated projections
  correct that mismatch without rewriting prior revisions or frozen migrations. `just model check`
  then **passed** (`pdf-foundation-model-check-final.log`). Semantic key scheme1 is unchanged.
- **not_run:** `just test-all`, whole-book publication, full native streaming producer, external
  MCP/provider/reference/grading journeys, default cutover and performance qualification.

Selected files under `python/corpus-structure/tests/`:

```
semantic/test_pdf_records.py
semantic/test_pdf_record_identity.py
semantic/test_pdf_record_native.py
semantic/test_native_closure.py
semantic/test_schema_product_cli.py
semantic/test_archive_reader.py
semantic/test_metadata.py
schema/test_relational.py
```

Final command (the schema directory replaces the single relational file above):

```sh
uv run pytest python/corpus-structure/tests/schema \
  python/corpus-structure/tests/semantic/test_pdf_records.py \
  python/corpus-structure/tests/semantic/test_pdf_record_identity.py \
  python/corpus-structure/tests/semantic/test_pdf_record_native.py \
  python/corpus-structure/tests/semantic/test_native_closure.py \
  python/corpus-structure/tests/semantic/test_schema_product_cli.py \
  python/corpus-structure/tests/semantic/test_archive_reader.py \
  python/corpus-structure/tests/semantic/test_metadata.py \
  -q -o addopts='' --maxfail=3
```

Prior worker controls retain their own scope:88codec cases before two root hardening controls;
15identity cases before two root controls;0062native/candidate14 and relational29;0063scope21,
then four affected controls after strengthening column-only read checks. They are not summed
with the integrated union. Worker failures, source/type receipts and root results are archived
in `raw/checks.tar.gz` with a SHA/member manifest `raw/checks.json`. The worker's
`native-foundation-prior-failures.txt` is an attributed summary/excerpt of its early failures,
not an original full command log; subsequent final logs are retained separately.

## What these establish

The pinned native mapping covers64native object classes/declared fields, explicit presence/order,
rich cells, qualified reference indexes and large/NUL values. Logical framing preserves exact
scalar type, decimal representation and binary64 signed zero; raw standard byte identities remain
separate. PostgreSQL scalar/record/fold vectors are independently authored, not copied outputs.
Actual private native tables, artifact verification, graph references, role/column-read refusal,
model counterfactuals and release admission were exercised in disposable fixture databases.

The initial native0062 discrepancy was corrected by forward0063; frozen0061/0062 stay unchanged.
Pglast signatures now exclude OUT/TABLE parameters while preserving real overloads. Private table
SELECT expectations derive from model-owned read_roles; no blanket reader grants were added.

I14 remains partial: installed StandardPdfPipeline still performs global assembly/heading and
post-assembly enrichment. I15/16 have foundation contracts and executable primitives; complete
frozen-union/native-export correspondence and live staging/seal remain PDF-20/21/24. Opaque
extension JSON has explicit encounter-order byte semantics rather than generic unordered JSON
canonical equivalence. These limits are not hidden by passing codec or hash tests.
