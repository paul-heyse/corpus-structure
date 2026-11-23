"""DuckDB 2.0.0 canonical-JSON and digest fidelity against the repository's canonical_json.

Run: uv run python docs/design_review/evidence/2026-11-22_sbx-columnar-basis/duckdb/probe_canonical.py
Synthetic values only; no repository data, no database connection.
Each line prints SAME or DIFF with the two byte strings where they differ.
"""

import hashlib
import json
import sys

import duckdb
import pyarrow as pa

from corpus_structure.core.canonical import canonical_json

con = duckdb.connect(config={"TimeZone": "UTC", "threads": 1})
print("duckdb", duckdb.__version__, "pyarrow", pa.__version__, "python", sys.version.split()[0])


def report(label, duck, expected):
    status = "SAME" if duck == expected else "DIFF"
    line = f"{status}  {label}"
    if status == "DIFF":
        line += f"\n      duckdb  : {duck!r}\n      python  : {expected!r}"
    print(line)
    return status == "SAME"


def one(sql, params=None):
    return con.execute(sql, params or []).fetchall()[0][0]


# C1 flat struct, fields declared in sorted order, strings/ints/bools/null
v = {"a": 1, "b": "x", "c": True, "d": None, "e": -9223372036854775808}
duck = one("SELECT to_json({'a': 1, 'b': 'x', 'c': true, 'd': NULL::INTEGER, 'e': (-9223372036854775808)::BIGINT})::VARCHAR")
report("C1 flat struct sorted fields, int/str/bool/null/min-bigint", duck.encode(), canonical_json(v))

# C2 struct fields declared out of order: to_json follows declaration order, not sorted
duck = one("SELECT to_json({'b': 1, 'a': 2})::VARCHAR")
report("C2 struct declared unsorted (b,a)", duck.encode(), canonical_json({"b": 1, "a": 2}))

# C3 json_normalize: does it sort keys?
duck = one("SELECT json_normalize('{\"b\":1,\"a\":{\"d\":2,\"c\":3}}')::VARCHAR")
report("C3 json_normalize sorts keys recursively?", duck.encode(), canonical_json({"b": 1, "a": {"d": 2, "c": 3}}))

# C4 string escapes, one per character, each compared individually
chars = [chr(i) for i in range(0x00, 0x20)] + ['"', "\\", "/", "\x7f", "\u0080", "é", " ", " ", "﻿", "\U0001f986", "中"]
diffs = []
for ch in chars:
    duck = con.execute("SELECT to_json(?::VARCHAR)::VARCHAR", [ch]).fetchall()[0][0]
    exp = canonical_json(ch).decode()
    if duck != exp:
        diffs.append((hex(ord(ch)), duck, exp))
print(("SAME" if not diffs else "DIFF") + f"  C4 single-character string escapes over {len(chars)} characters")
for d in diffs:
    print(f"      U+{d[0][2:].zfill(4)}  duckdb {d[1]!r}  python {d[2]!r}")

# C5 NFC: canonical_json NFC-normalizes; DuckDB to_json does not unless nfc_normalize is applied
decomposed = "é"
duck = con.execute("SELECT to_json(?::VARCHAR)::VARCHAR", [decomposed]).fetchall()[0][0]
report("C5 decomposed e+U+0301 without nfc_normalize", duck.encode(), canonical_json(decomposed))
duck = con.execute("SELECT to_json(nfc_normalize(?::VARCHAR))::VARCHAR", [decomposed]).fetchall()[0][0]
report("C5b with nfc_normalize()", duck.encode(), canonical_json(decomposed))

# C6 integers beyond 64 bits (HUGEINT) and UBIGINT
big = 2**100
duck = one(f"SELECT to_json({big}::HUGEINT)::VARCHAR")
report("C6 HUGEINT 2^100", duck.encode(), canonical_json(big))
duck = one("SELECT to_json(18446744073709551615::UBIGINT)::VARCHAR")
report("C6b UBIGINT max", duck.encode(), canonical_json(18446744073709551615))

# C7 doubles and decimals (canonical_json refuses both; compare to the canonical decimal *string* policy)
duck = one("SELECT to_json([1.0::DOUBLE, 0.1::DOUBLE, 1e-7::DOUBLE, 1e16::DOUBLE, 2.5e-05::DOUBLE])::VARCHAR")
print(f"INFO  C7 doubles to_json -> {duck}   python json.dumps -> {json.dumps([1.0, 0.1, 1e-7, 1e16, 2.5e-05], separators=(',', ':'))}")
duck = one("SELECT to_json([1.500::DECIMAL(10,3), 0.10::DECIMAL(4,2), -0.0::DECIMAL(4,2)])::VARCHAR")
print(f"INFO  C7b decimals to_json -> {duck}   (canonical policy: decimal travels as canonical string, e.g. \"1.5\", \"0.1\", \"0\")")
duck = one("SELECT to_json([1.500::DECIMAL(10,3)::VARCHAR, (1.500::DECIMAL(10,3))::DOUBLE::VARCHAR])::VARCHAR")
print(f"INFO  C7c decimal ::VARCHAR -> {duck}")

# C8 null vs absent: struct always emits key; json_strip_nulls drops explicit nulls too
duck = one("SELECT to_json({'a': 1, 'b': NULL::INTEGER})::VARCHAR")
report("C8 struct null field emits \"b\":null (explicit null)", duck.encode(), canonical_json({"a": 1, "b": None}))
duck = one("SELECT json_strip_nulls(to_json({'a': 1, 'b': NULL::INTEGER}))::VARCHAR")
report("C8b json_strip_nulls gives absent", duck.encode(), canonical_json({"a": 1}))
# presence-driven emission: MAP built from present entries (keys sorted), values as JSON
duck = one(
    """
    WITH r AS (SELECT 1 AS a, NULL::INTEGER AS b, true AS b_present, NULL::INTEGER AS c, false AS c_present)
    SELECT to_json(map_from_entries(list_filter([
        {'k': 'a', 'v': to_json(a)},
        {'k': 'b', 'v': to_json(b)},
        {'k': 'c', 'v': to_json(c)}],
        lambda e: e.k = 'a' OR (e.k = 'b' AND b_present) OR (e.k = 'c' AND c_present))))::VARCHAR FROM r
    """
)
report("C8c MAP of present entries (b explicit null, c absent)", duck.encode(), canonical_json({"a": 1, "b": None}))

# C9 nested: list of structs with nested list and struct
duck = one(
    "SELECT to_json([{'k': [1, 2], 'n': {'x': 'é', 'y': NULL::VARCHAR}}, {'k': [], 'n': {'x': '\"', 'y': 'z'}}])::VARCHAR"
)
report(
    "C9 nested list/struct, empty list",
    duck.encode(),
    canonical_json([{"k": [1, 2], "n": {"x": "é", "y": None}}, {"k": [], "n": {"x": '"', "y": "z"}}]),
)
duck = one("SELECT to_json(MAP {}::MAP(VARCHAR, INTEGER))::VARCHAR")
report("C9b empty MAP -> {}", duck.encode(), canonical_json({}))

# C10 Arrow-sourced struct: field order comes from the Arrow schema
t = pa.table({"row": pa.array([{"z": 1, "a": "q"}], type=pa.struct([("z", pa.int64()), ("a", pa.string())]))})
duck = con.sql("SELECT to_json(row)::VARCHAR FROM t").fetchall()[0][0]
report("C10 Arrow struct (z,a) -> declaration order", duck.encode(), canonical_json({"z": 1, "a": "q"}))

# C11 ordered group digest: sha256 over to_json(list(struct ORDER BY ord)) vs python digest
rows = pa.table(
    {
        "block": [1, 1, 1, 2, 2],
        "ord": [2, 0, 1, 0, 1],
        "text": ["c", "a", "bé", "x", "y\n"],
    }
)
duck_rows = con.sql(
    """
    SELECT block,
           sha256(to_json(list({'ord': ord, 'text': text} ORDER BY ord))::VARCHAR) AS d_list,
           sha256('[' || string_agg(to_json({'ord': ord, 'text': text})::VARCHAR, ',' ORDER BY ord) || ']') AS d_agg
    FROM rows GROUP BY block ORDER BY block
    """
).fetchall()
ok = True
for block, d_list, d_agg in duck_rows:
    items = sorted(
        [{"ord": o, "text": s} for b, o, s in zip(rows["block"].to_pylist(), rows["ord"].to_pylist(), rows["text"].to_pylist()) if b == block],
        key=lambda r: r["ord"],
    )
    exp = hashlib.sha256(canonical_json(items)).hexdigest()
    ok &= d_list == exp and d_agg == exp
print(("SAME" if ok else "DIFF") + "  C11 per-group sha256 of ordered list (list(... ORDER BY) and string_agg forms)")

# C12 sha256 over BLOB vs VARCHAR of same UTF-8 bytes
duck_v = one("SELECT sha256('é')")
duck_b = one("SELECT sha256(encode('é'))")
report("C12 sha256(VARCHAR) == sha256(BLOB of UTF-8)", (duck_v == duck_b), True)
report("C12b sha256 hex equals hashlib", duck_v, hashlib.sha256("é".encode()).hexdigest())

# C13 hash() order-independence building block: bit_xor(hash(row)) is order independent but 64-bit, non-cryptographic
a = one("SELECT bit_xor(hash(x)) FROM (VALUES (1),(2),(3)) v(x)")
b = one("SELECT bit_xor(hash(x)) FROM (VALUES (3),(1),(2)) v(x)")
c = one("SELECT bit_xor(hash(x)) FROM (VALUES (1),(1),(2)) v(x)")
d = one("SELECT bit_xor(hash(x)) FROM (VALUES (2)) v(x)")
print(f"INFO  C13 bit_xor(hash()) order-independent: {a == b}; bag (1,1,2) collides with (2): {c == d}")

# C14 VARIANT: does JSON->VARIANT->JSON keep key order, and does variant_normalize sort keys?
try:
    kept = one("SELECT to_json('{\"b\":1,\"a\":2}'::JSON::VARIANT)::VARCHAR")
    norm = one("SELECT to_json(variant_normalize('{\"b\":1,\"a\":2}'::JSON::VARIANT))::VARCHAR")
    print(f"INFO  C14 VARIANT round trip -> {kept}; variant_normalize -> {norm}")
    s = one("SELECT to_json(variant_normalize({'b': 1, 'a': {'d': 1.5::DECIMAL(4,2), 'c': 'é'}}::VARIANT))::VARCHAR")
    print(f"INFO  C14b variant_normalize of struct -> {s}")
except Exception as e:  # noqa: BLE001
    print(f"INFO  C14 VARIANT error: {type(e).__name__}: {e}")

# C15 json_normalize on a richer document: key sort by code point at every depth, separators, escapes, numbers
doc = {"é": 1, "z": [{"b": None, "a": "\u0001\n"}], "A": True, "aa": {"y": [], "x": {}}, "\U0001f986": "q"}
src = json.dumps(doc, ensure_ascii=True, indent=2)  # ASCII-escaped, pretty, insertion order
duck = con.execute("SELECT json_normalize(?::JSON)::VARCHAR", [src]).fetchall()[0][0]
report("C15 json_normalize(pretty, ascii-escaped, unsorted) == canonical_json", duck.encode(), canonical_json(doc))
duck = con.execute("SELECT json_normalize(?::JSON)::VARCHAR", ['{"a":1.50,"b":1e2,"c":-0,"d":10000000000000000000000}']).fetchall()[0][0]
print(f"INFO  C15b json_normalize numbers -> {duck}")
duck = con.execute("SELECT json_normalize(?::JSON)::VARCHAR", ['{"a":1,"a":2}']).fetchall()[0][0]
print(f"INFO  C15c json_normalize duplicate keys -> {duck}  (canonical_json refuses duplicates after NFC)")
duck = con.execute("SELECT json_normalize(to_json({'b': 1, 'a': {'d': [1, 2], 'c': 'é'}}))::VARCHAR").fetchall()[0][0]
report("C15d json_normalize(to_json(unsorted struct)) (no NFC applied)", duck.encode(), canonical_json({"b": 1, "a": {"d": [1, 2], "c": "é"}}))

# L1 lifecycle note: execute().fetchone() leaves the result open; a following execute() replaces it silently,
# but con.sql(...) on the same connection raises ResourceInUseException.
con2 = duckdb.connect()
con2.execute("SELECT * FROM range(10)").fetchone()
con2.execute("SELECT 1").fetchall()
print("INFO  L1 execute().fetchone() then execute(): allowed (open result replaced)")
con2.execute("SELECT * FROM range(10)").fetchone()
try:
    con2.sql("SELECT 1").fetchall()
    print("INFO  L1b execute().fetchone() then sql(): allowed")
except duckdb.Error as e:
    print(f"INFO  L1b execute().fetchone() then sql(): {type(e).__name__}")

duck = con.execute("SELECT json_normalize(?::JSON)::VARCHAR", ['["\\u001f\\u000b"]']).fetchall()[0][0]
print(f"INFO  C15e json_normalize control escapes -> {duck}  python -> {canonical_json(['\x1f\x0b']).decode()}")
