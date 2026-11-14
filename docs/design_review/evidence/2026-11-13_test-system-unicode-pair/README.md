# PostgreSQL 18.7 Unicode identity qualification

**Tested, 2026-11-13:** the installed CPython3.14.10/UCD16.0.0 and PostgreSQL18.7
UTF8 builtin `pg_unicode_fast` version1 pair agree over every supported Unicode scalar.
The 1557 changed mappings retain digest
`97b00ff02d8ab202d343184b422f25c8ea8e0b30db3f9334ed3b2d909a615d02`.

The test-system campaign `087abdd3b95d49409c305105165fa6cb` exposed two integrated acceptance
failures because the exact qualified pair still named PostgreSQL18.6. The admission guard
correctly refused the updated host. This investigation qualifies the actual pair before any
metadata repair; it changes no folding algorithm, runtime guard, schema or deployment.

Command, **passed**:

```sh
uv run python docs/design_review/evidence/2026-11-13_test-system-unicode-pair/code/qualify.py
```

The existing production qualification compares the complete scalar relation, excluding NUL and
surrogates. Six independent sequence expectations additionally cover expansion, sigma, Turkish
I, ligatures and composed/decomposed accents. No normalization occurs. Exact observed-pair
admission passes; both the previous18.6 pair and a corrupted collation determinant are refused.
The connection uses the configured maintenance template in a read-only transaction. No database,
schema, extension, deployment or activation is created. The previous qualification evidence is
preserved unchanged.

`inputs/unicode_identity.before.py` captures the implementation used by the original campaign
and probe. `results/qualified-pair.json` retains exact runtime determinants, independent cases,
refusals and implementation digest. The [record](records/test-system.unicode-pg18-7.json) owns
the qualification conclusion. Integrated test repair and exact failing-ID retries remain with
the [test-system coordinator](../../../plans/test-system-target-design_2026-11-13.md).
