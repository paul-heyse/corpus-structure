# DuckDB 2.0 scoped binding and export metadata probe

**Purpose.** This probe settles four DuckDB 2.0.0 capability questions raised by the
[library assessment](../../../library_leverage/libraries/duckdb/README.md):
- scoped relation names that need no SQL-text rewriting;
- export metadata;
- Arrow metadata survival.

Context7 does not yet cover DuckDB 2.0, released 2026-10-21. These facts come from the installed
package.

## Environment

- DuckDB 2.0.0 and pyarrow 26.0.0, as installed in the repository `.venv`.
- Python 3.14.10.
- An in-memory database only. No database server or network was used, and nothing was installed.
- Run on 2026-10-29 from the repository root at source commit `d739b88`.

## Command

```
uv run --no-sync python docs/design_review/evidence/2026-10-29_library-leverage-duckdb/probe_duckdb.py
```

[output.json](output.json) is the unedited output.

## Outcome (passed; all four questions answered)

1. **`DuckDBPyRelation.query(name, sql)` scopes the name to the call.** The relation can be
   re-read lazily with the same result. The catalog is unchanged afterwards, and a later reference
   to the name raises `CatalogException`. The installed docstring states that the name is "a common
   table expression over the relation, and a catalog entry for the length of the call … Nothing of
   it is left afterwards."
2. **A `TEMP MACRO … AS TABLE` can bind several per-operation inputs by value.** The macro's
   parameters are relation names passed to `query_table(...)`. Inputs registered from Arrow tables
   and inputs created as views from relations both bind. The result re-reads identically. The macro
   text stays constant, and only name strings vary.
3. **`COPY (…) TO '…' (FORMAT parquet, KV_METADATA {…})` writes file-level key-value metadata.**
   DuckDB `parquet_kv_metadata()` and pyarrow `read_metadata` both read the same pairs back.
   `DuckDBPyRelation.write_parquet` in 2.0.0 has no key-value metadata parameter, according to its
   installed signature.
4. **Arrow schema-level and field-level metadata do not survive a DuckDB round trip.**
   `register(…)` followed by `to_arrow_table()` returns `None` for both.

## Limits

- These are small synthetic relations; nothing about performance is measured.
- The macro route was checked for binding and re-reading only. It was not checked under
  concurrent use from one connection, which DuckDB 2.0 refuses with `ResourceInUseException`.
- Field-level Parquet metadata through DuckDB `COPY` was not examined. Only file-level
  `KV_METADATA` was examined.
