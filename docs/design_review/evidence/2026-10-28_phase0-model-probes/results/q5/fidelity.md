# Q-5 pool round trip: fidelity

Versions: {'adbc-driver-postgresql': '1.13.0', 'adbc-driver-manager': '1.13.0', 'duckdb': '2.0.0', 'pyarrow': '26.0.0', 'pgpq': '0.12.0', 'psycopg': '3.3.6', 'psycopg-binary': '3.3.6'}; run 2026-10-28T19:36:23-0400.

## ADBC result schema

| column | Arrow type | field metadata |
|---|---|---|
| id | `int64` | {'POSTGRESQL:type': 'int8'} |
| run_id | `int64` | {'POSTGRESQL:type': 'int8'} |
| kind | `string` | {'POSTGRESQL:type': 'text'} |
| payload | `extension<arrow.json>` | {'POSTGRESQL:type': 'jsonb'} |
| payload_json | `extension<arrow.json>` | {'POSTGRESQL:type': 'json'} |
| amount | `extension<arrow.opaque[storage_type=string, type_name=numeric, vendor_name=PostgreSQL]>` | {'ADBC:postgresql:typname': 'numeric', 'POSTGRESQL:type': 'numeric', 'POSTGRESQL:typmod': '-1'} |
| at | `timestamp[us, tz=UTC]` | {'POSTGRESQL:type': 'timestamptz'} |
| label | `string` | {'POSTGRESQL:type': 'text'} |
| note | `string` | {'POSTGRESQL:type': 'text'} |

## Write-back routes compared with `src_obs`

| route | outcome | failing checks (row ids) | error |
|---|---|---|---|
| psycopg_set_types | written | {} |  |
| pgpq_text | refused by the server | — | 08P01: insufficient data left in message |
| pgpq_decimal128 | refused before COPY | — | ArrowInvalid: Rescaling Decimal value would cause data loss |
| pgpq_staging | written | {} |  |

Checks per row: `row_present`, `jsonb_equal`, `b_presence_equal`, `b_value_equal`, `top_type_equal`, `json_text_identical`, `numeric_equal`, `numeric_text_identical`, `timestamptz_equal`, `text_equal`, `dim_numeric_text_identical`.

## DuckDB

Types after `register`: {'id': 'BIGINT', 'run_id': 'BIGINT', 'kind': 'VARCHAR', 'payload': 'JSON', 'payload_json': 'JSON', 'amount': 'VARCHAR', 'at': 'TIMESTAMP WITH TIME ZONE', 'label': 'VARCHAR', 'note': 'VARCHAR'}

Absent versus null (`id, json_exists(payload,'$.b'), payload->'$.b', (payload->'$.b') IS NULL, json_type`): [['1', 'True', 'null', 'False', 'OBJECT'], ['2', 'False', 'None', 'True', 'OBJECT'], ['3', 'False', 'None', 'True', 'OBJECT'], ['4', 'False', 'None', 'True', 'NULL'], ['5', 'None', 'None', 'True', 'None'], ['6', 'False', 'None', 'True', 'OBJECT'], ['7', 'False', 'None', 'True', 'OBJECT'], ['8', 'False', 'None', 'True', 'OBJECT'], ['9', 'True', 'false', 'False', 'OBJECT']]

Group-by: [{'kind': 'mention', 'n': 2, 'n_payload': 2, 'b_exists': Decimal('1'), 'b_json_null': Decimal('1'), 'first_at': 1793170800123456}, {'kind': 'relation', 'n': 2, 'n_payload': 2, 'b_exists': Decimal('0'), 'b_json_null': Decimal('0'), 'first_at': -1}, {'kind': 'scope', 'n': 2, 'n_payload': 2, 'b_exists': Decimal('1'), 'b_json_null': Decimal('0'), 'first_at': 1774744200000000}, {'kind': 'value', 'n': 3, 'n_payload': 2, 'b_exists': Decimal('0'), 'b_json_null': Decimal('0'), 'first_at': -62135596800000000}]

Result lifecycle: {'first_fetchone': (0,), 'second_statement': [(42,)], 'first_after_second': [], 'relation_reevaluated_twice': [9, 9]}

Arrow out of DuckDB: id `int64`, run_id `int64`, kind `string`, payload `string`, payload_json `string`, amount `string`, at `timestamp[us, tz=America/New_York]`, label `string`, note `string`, weight `string`, cls `string`

## Binding

```json
{
 "param_select": {
  "outcome": "accepted",
  "ids": [
   7,
   8,
   9
  ]
 },
 "param_select_record_batch": {
  "outcome": "accepted",
  "ids": [
   3
  ]
 },
 "param_insert_str_into_timestamptz": "ProgrammingError: INVALID_ARGUMENT: Failed to prepare query: ERROR:  column \"cut_at\" is of type timestamp with time zone but expression is of type text",
 "temp_table_cut": {
  "ids": [
   1,
   2,
   3,
   4,
   6,
   8
  ],
  "expected": [
   1,
   2,
   3,
   4,
   6,
   8
  ]
 },
 "server_statements": [
  "COPY (SELECT /*q5-cut*/ o.id FROM src_obs o JOIN q5_cut c ON o.run_id = c.run_id WHERE o.at <= c.cut_at ORDER BY o.id) TO STDOUT (FORMAT binary)",
  "COPY (SELECT /*q5-plain*/ id FROM src_obs ORDER BY id) TO STDOUT (FORMAT binary)",
  "SELECT /*q5-param*/ id, kind FROM src_obs WHERE run_id = $1 AND id > $2 ORDER BY id",
  "SELECT /*q5-param-rb*/ id FROM src_obs WHERE id = $1"
 ]
}
```

## ±infinity timestamps through ADBC

```json
{
 "adbc_int64_us": [
  -9222425352054775809,
  -9222425352054775808
 ],
 "postgres_epoch_us_text": [
  "Infinity",
  "-Infinity"
 ],
 "int64_min": -9223372036854775808,
 "int64_max": 9223372036854775807,
 "pg_epoch_offset_us": 946684800000000
}
```

## psycopg as loader

```json
{
 "equal_to_adbc_by_column": {
  "id": true,
  "run_id": true,
  "kind": true,
  "payload": true,
  "payload_json": true,
  "amount": [
   "NaN",
   "Infinity",
   "-Infinity"
  ],
  "at": true,
  "label": true,
  "note": true
 },
 "timestamptz_load_by_session_zone": {
  "server TimeZone, text": "America/New_York: DataError: timestamp too small (before year 1): '0001-12-31 19:03:58-04:56:02 BC'",
  "server TimeZone, binary": "America/New_York: DataError: timestamp too small (before year 1)"
 },
 "note": "text-format cursor with TextLoader for jsonb/json/numeric; binary jsonb would come back as dicts via json.loads",
 "default_loaders_row6": {
  "payload": "{'i': 0, 't': 1e-30, 'v': 1.2345678901234567e+19}",
  "amount": "Decimal('123456789012345678901234567890.123456789')"
 },
 "binary_text_loader": "TextBinaryLoader"
}
```
