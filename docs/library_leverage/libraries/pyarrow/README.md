# pyarrow

**Realization assessed:** pyarrow 26.0.0.

**Researched:** 2026-10-29 by the R5 columnar cluster.
- The [overview](../../../libraries/pyarrow.md) was read end to end.
- Context7 was consulted on `pc.round`/`RoundOptions` and the `store_schema` option.
- Several pure-Python probes were run
  ([evidence](../../../design_review/evidence/2026-10-29_library-leverage-arrow/README.md)).

## Reusable opportunity types

<a id="pyarrow-parquet-metadata-carriage"></a>

### `pyarrow/parquet-metadata-carriage`

**Need.** Carry schema-level and field-level identity metadata through a columnar file export, so a
reader can re-validate it.

**Mechanism.**
- `pq.write_table`, or `pq.ParquetWriter` fed batch by batch.
- `ds.write_dataset(Table | RecordBatchReader | iterable)`, where `file_visitor` exposes each file's
  footer.
- `ParquetWriter.add_key_value_metadata(...)` adds keys after the data has been written.

**What survives (probe-observed, 26.0.0).** Schema metadata, field metadata, nullability,
`decimal128(38,12)` and `timestamp[ns, UTC]` all survive these reads:
- `read_table`;
- `ds.dataset().to_table()`;
- projected or filtered scans.

Schema-level keys also appear as plain footer entries alongside `ARROW:schema`.

**Conditions and limits.**
- Field-level metadata lives only inside the base64 `ARROW:schema` blob, so non-Arrow readers see
  only schema-level keys.
- `store_schema=False` silently drops *all* footer metadata.
- `write_dataset(schema=<schema without metadata>)` writes none.
- Hive partitioning removes the partition column from each file.
- Casting to a target schema without metadata drops it; `Table.select` keeps it.
- `write_dataset` does not commit atomically.

**Residual for the caller.**
- Re-attach metadata after any engine hop that drops it. DuckDB drops it
  ([duckdb](../duckdb/README.md#duckdb-parquet-export-with-metadata)).
- Publish the output atomically.
- Own the meaning of the keys.

<a id="pyarrow-exact-numeric-boundary"></a>

### `pyarrow/exact-numeric-boundary` (mostly limits and negative results)

**Need.** Convert lexical decimals to a bounded decimal type under a declared rounding mode, with
refusal on overflow; parse lexical float spellings.

**Mechanisms.**
- String→decimal casts. They accept exponent forms, `+1.5` and `.5`. They refuse `NaN`, `Infinity`
  and leading whitespace.
- `pc.round(decimal, ndigits, round_mode=...)` offers ten modes. The default is `half_to_even`, and
  it keeps the type and scale.
- `pc.not_equal(rounded, original)` flags values that were rounded.

**Semantics (probe-observed).**
- A safe cast refuses a lossy rescale. With `safe=False` it **truncates**; it does not round.
- A carry past the type's precision raises `ArrowInvalid`.
- Errors are all-or-nothing for the whole array.
- Decimal128 has no negative zero.

**Limits.**
- **Bounded intermediate scale.** Exact rounding of lexical input of arbitrary length needs an
  intermediate type wide enough for the input's scale. Input beyond it is refused, even where the
  policy would round it.
- **decimal256 rounding defect in 26.0.0.** `pc.round` on `decimal256(76, s)` returns *silently wrong
  values* when the round-up carries through runs of nines and the integer part has at least 20
  digits. For example, `99999999999999999999.9999999999995` rounded to 12 places came back as
  `…99.999999999999`; it should be `100000000000000000000.000000000000`.
  - Affected scales: 32, 39, 40 and 50.
  - All modes are affected.
  - Seeded random tests (2000 values per scale) did not find it.
  - decimal128 produced no wrong values.
  - The finding comes from a targeted sweep. No upstream report was found, but that search was
    limited.
- **No hex-float parsing.** `float.hex()` spellings fail to cast, and no compute function parses
  them.

**Residual for the caller.** Any exact policy over unbounded input, per-row refusal or diagnostics,
and signed zero.

<a id="pyarrow-ipc-owned-copy"></a>

### `pyarrow/ipc-owned-copy` (small)

**Mechanism.** Write with `ipc.new_stream` into a `BufferOutputStream`, then read back with
`open_stream(...).read_all()`. This detaches the table from memory the caller owns, and metadata
survives (probe).

**Condition.** `getvalue()` returns a Buffer flagged `is_mutable=True`. Copying it into Python
`bytes` yields buffers flagged immutable, at the cost of one more copy.

## Applicability at source `d739b88` (re-checked at `3d97504`, plus concurrent `7cfd7f8`)

<a id="applicability-cbo-007"></a>

### CBO-007 — export writer with `cs.*` metadata: **fits with conditions; adopted concurrently**

**Opportunity:** [CBO-007](../../codebase/consumers-and-operations.md#cbo-007). **Type:**
[parquet-metadata-carriage](#pyarrow-parquet-metadata-carriage).

**Fit.**
- A writer can stream batches into `pq.ParquetWriter(schema=<compiled schema with cs.* metadata>)`,
  or pass a reader to `ds.write_dataset`. Both preserve `cs.*` exactly (probe P1).
- Conditions: keep `store_schema=True`, never pass a schema stripped of metadata, re-attach metadata
  after any DuckDB hop, and own atomic publication.
- Streaming would need per-batch normalization, because `load_packet` currently calls
  `reader.read_all()`.

**Concurrent evidence.** SP-08 commit `7cfd7f8`, which landed during this assessment, added
`serve/export.py`:
- it writes each spine relation with `pq.write_table(relation, path, store_schema=True)`;
- it checks every `cs.*` key before writing;
- it publishes through a temporary directory and a rename.

That is this type's route. The comparative review should judge it against the
[DuckDB route](../duckdb/README.md#applicability-cbo-007).

**Subset capture: fits.** It means fewer or narrower COPY statements inside the same snapshot. What
remains is local: subset identity in `projection_id`, and the scope's complete-spine check.

<a id="applicability-cbo-015"></a>

### CBO-015 — Arrow side of the typed-value codec: **vectorized normalization ruled out; per-row loops confirmed**

**Opportunity:** [CBO-015](../../codebase/storage-and-analytics.md#cbo-015). **Type:**
[exact-numeric-boundary](#pyarrow-exact-numeric-boundary).

**Premise correction.** The stated reason, "Arrow refuses to rescale", holds only for casts.
`pc.round(…, "half_to_even")` *does* round decimals. The real reasons are:
- unbounded fractional length in the analytical profile's lexical decimals;
- carry overflow at the decimal128 intermediate's precision;
- silently wrong values with a decimal256 intermediate;
- whole-array errors, which lose per-row refusal.

**Float-hex loop.** Required: Arrow cannot parse `float.hex()` output.

**Possible fast path.** A guarded decimal128 fast path with a per-row fallback is possible. It would
add another application-side mirror of the policy ([LOP-X003](../../assessment-patterns.md#lop-x003)).

**Answer to codec question 1.** On the Arrow side, the single codec must be the Python function that
works one value at a time. Arrow's cast accepts the exponent forms that `str(raw)` produces, so Arrow
would not catch that divergence.

<a id="applicability-ipc"></a>

### Arrow IPC freeze in `arrow_publication.py`: **sound, no opportunity**

This is the [ipc-owned-copy](#pyarrow-ipc-owned-copy) idiom. The `to_pybytes()` copy is what makes
the buffers immutable by flag.

## Coverage limits

- The decimal256 defect has no root cause or upstream status yet.
- The set of affected scales comes from a targeted sweep, not an exhaustive one.
