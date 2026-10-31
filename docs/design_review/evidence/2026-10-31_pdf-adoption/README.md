# PDF operational adoption — in progress

This folder retains independent source reference preparation and the forthcoming actual
PDF adoption journeys. It does not claim completed full-book conversion or qualification.

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
