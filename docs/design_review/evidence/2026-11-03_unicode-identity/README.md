# Qualified Unicode identity pair

**Tested 2026-11-03.** AC03/I01 compares Python's Unicode default case folding with
PostgreSQL's builtin `pg_unicode_fast` folding. No normalization is performed.
The exact supported pair is retained in `results/qualified-pair.json` and the package's
`semantic.unicode_identity.QUALIFIED_PAIR`.

The comparison queries every Unicode scalar supported by PostgreSQL UTF8 text (NUL and
surrogates excluded), retaining the complete changed-mapping relation digest. Six independently
specified sequence cases cover expansions, Greek sigma variants, dotted/dotless I, ligatures,
and distinct composed/decomposed spellings. They challenge the integration; mapping equality
is established by the complete scalar comparison rather than those examples.

The read-only command used the configured corpus cluster's maintenance template database. It
created no stores, schema objects, extensions or service changes. The result also exercises the
Python admission boundary's refusal of changed collation determinants. Native deployment
adoption/refusal and assembled publication remain separately owned integration obligations.

Run from the repository root with the intended environment:

```bash
uv run python docs/design_review/evidence/2026-11-03_unicode-identity/code/qualify.py
```

The finalized record is `ac03.unicode`. The copied implementation under `inputs/` identifies
qualification source bytes; it is evidence and does not replace the package owner. Current
execution must bind the qualified recipe and check the exact runtime/collation pair at admission.
