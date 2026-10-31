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
libpq URL and token succeeded.

Actual configured `claude-opus-5-5` returned `READY` through Claude CLI authentication.
This establishes provider availability only, not source extraction or grading.
