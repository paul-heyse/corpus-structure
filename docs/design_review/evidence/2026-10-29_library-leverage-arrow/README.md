# Library-leverage cluster R5 (columnar interchange): pyarrow probes

Date: 2026-10-29. Written by a `library-research` worker for the first
`leverage-library-assessment` pass. Pure Python against the installed environment: no database
connection, no network service, no installs.

## Questions

1. **Metadata (P1, P4).** Do pyarrow's Parquet writers (`pq.write_table`, `pq.ParquetWriter`,
   `ds.write_dataset`) and IPC streams carry schema-level and field-level key-value metadata end to
   end, so that a read-back schema still satisfies `Schema.equals(..., check_metadata=True)`?
   Which keys reach the Parquet footer where non-Arrow readers can see them?
2. **Exact decimals (P2 and follow-ups).** What can pyarrow casts and `pc.round` do for an exact
   HALF_EVEN quantization of lexical decimals to `decimal128(38, 12)` with overflow refusal, and
   where does a vectorized route disagree with an independent stdlib `Decimal.quantize` oracle?
3. **Float hexadecimal (P3).** Can an Arrow cast or kernel parse Python's `float.hex()` spelling?

## Environment

- Python 3.14.10, pyarrow 26.0.0 (installed `.venv`, matching `uv.lock`).
- Command form, from the repository root: `uv run --no-sync python <script>`.
- Source baseline: `d739b883e322adef7a3202e2896766ff71bcac5d`.

## Files

| Script | Output | Purpose |
|---|---|---|
| `probe_arrow.py` | `probe_arrow.out` | P1 Parquet/dataset metadata, P2 decimal casts and a vectorized candidate, P3 float hex, P4 IPC |
| `probe_round_carry.py` | `probe_round_carry.out` | `pc.round` on decimals vs stdlib for 7 round modes, decimal128/decimal256, input scales 13–63 |
| `probe_round_magnitude.py` | `probe_round_magnitude.out` | Bisects the decimal256 discrepancy by integer-digit count |
| `probe_round_random.py` | `probe_round_random.out` | Seeded random differential (2000 values per scale) of decimal256 HALF_EVEN rounding |
| `probe_round_carry_sweep.py` | `probe_round_carry_sweep.out` | Targeted carry-through-9s sweep, decimal128 and decimal256 |

## Outcomes

**P1/P4 metadata — passed.**
- `pq.write_table` (default `store_schema=True`), `pq.ParquetWriter` fed batch by batch, and
  `ds.write_dataset` fed a `Table` or a `RecordBatchReader` all round-trip schema-level and
  field-level metadata, nullability, `decimal128(38,12)` and `timestamp[ns, UTC]`;
  `equals(check_metadata=True)` holds after `pq.read_table` and `ds.dataset(...).to_table()`.
- Footer key-value metadata holds `ARROW:schema` plus each schema-level `cs.*` key as a plain
  entry. Field-level metadata exists only inside the serialized `ARROW:schema`.
- `store_schema=False` drops **all** footer key-value metadata, schema-level keys included, as
  well as field metadata.
- `ds.write_dataset(schema=<metadata-free schema>)` writes no schema metadata. Hive partitioning
  removes the partition column from each file, but the files keep schema metadata.
  `file_visitor` exposes each written file's footer keys.
- Projected or filtered dataset scans keep schema and field metadata. `Table.select` keeps
  schema metadata; `Table.cast` to a metadata-free target drops it.
- IPC stream round trip keeps all metadata. `BufferOutputStream.getvalue()` returns a Buffer
  that reports `is_mutable=True`.

**P2 decimals — partial (vectorized route not exact).**
- A safe cast refuses lossy rescale ("Rescaling Decimal value would cause data loss"), both from
  string and decimal-to-decimal. `safe=False` **truncates** (1.0000000000015 → 1.000000000001;
  −1.0000000000019 → −1.000000000001); it does not round.
- `pc.round(decimal, ndigits=12, round_mode="half_to_even")` rounds decimals while keeping the
  input type and scale. A carry past the type's precision raises `ArrowInvalid`.
- The string→decimal cast accepts exponent forms (`1E+5`, `1.5e-3`), `+1.5` and `.5`. It
  refuses `NaN`, `Infinity` and leading whitespace. A whole-array cast fails on the first bad
  element, with no per-row result.
- Candidate route: string → `decimal256(76, 40)` → `pc.round` → safe cast to
  `decimal128(38, 12)`, with the flag computed as `not_equal(rounded, wide)`. It agreed with the
  stdlib oracle on 20 of 23 vectors and differed on 3:
  - It refused `1e-41` and a value with 46 fractional digits, both beyond the intermediate scale.
    The oracle accepts both and rounds them to 0 / 1.
  - It returned a **wrong value** for `99999999999999999999999999.9999999999995`: …999998 with
    the flag set. The oracle refuses this value because the carry overflows.
- Follow-ups isolate a **decimal256 rounding defect** in 26.0.0. When the round-up carries
  through runs of nines and the integer part has at least 20 digits, `pc.round` on
  `decimal256(76, s)` returns silently wrong values, rounding down or below:
  - Affected input scales: s ∈ {32, 39, 40, 50}. Scales {13, 18, 20, 25, 28, 30, 35, 38, 45, 60}
    showed no wrong values in the targeted sweep.
  - All round modes are affected, including `towards_zero`.
  - The inputs themselves round-trip exactly.
  - Seeded random values (2000 per scale, 30% forced ties) showed no discrepancies, so the defect
    hides from ordinary random testing.
  - `decimal128` showed no wrong values in any sweep (scales 13–35).
  - An issue search of apache/arrow ("decimal256 round") found only closed Go issues. No C++
    report was found; this is a limited search, not proof of absence.
- Decimal128 has no negative zero: `-0` and `-0.0000000000005` become `0E-12`. The stdlib
  produces `-0E-12`, but materializing that into an Arrow decimal also loses the sign.

**P3 float hex — passed (negative capability confirmed).** Casting a `float.hex()` string
(`0x1.8000000000000p+0`, `-0x0.0p+0`) to float64 raises `ArrowInvalid`. No compute function name
contains `hex`. Decimal-text casts do handle subnormals (`5e-324`).

## Limits

- Parquet results cover pyarrow writing and reading only. Visibility of footer keys to other
  engines, such as DuckDB `parquet_kv_metadata`, was not exercised.
- The decimal256 defect is characterized by observation, not root-caused. The affected-scale set
  is from a targeted sweep and is not exhaustive. Any decimal256 rounding at other scales stays
  unverified for carry patterns.
- In `probe_round_carry.out`, rows for `decimal128(38, 39|40)` (scale > precision) fail in
  `as_py()` with `decimal.InvalidOperation`. That is a harness artifact of an invalid type
  choice, not evidence about rounding.
- No timing or memory measurements were taken; nothing here supports a performance claim.
- No evidence record has been finalized. Acceptance and `records/<id>.json` belong to the
  coordinator.
