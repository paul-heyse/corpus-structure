# Retained semantic test inputs

`retained-html-inputs.json` contains historical source products, markup and token layouts captured on 2026-10-31 from an isolated export of `7e6289a`. They replace
runtime calls to the retired HTML writer in archived-reader controls. Expected assertions were
not regenerated. They are not PDF expectations or evidence of a current HTML entry point.

`populate_abi10_source.py` deliberately runs only in its asserted historical compiler-10 export
against a caller-owned test database. Its historical producer import belongs to that migration
fixture, not to current application execution.
