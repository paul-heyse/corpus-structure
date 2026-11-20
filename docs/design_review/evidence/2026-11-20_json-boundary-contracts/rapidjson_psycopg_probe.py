"""psycopg 3.3.6 JSON adapters fed by the rapidjson exact codec: no connection, no database.

Uses AdaptersMap/Transformer contexts only. Run from the repository root:

    uv run python -I docs/design_review/evidence/2026-11-20_json-boundary-contracts/rapidjson_psycopg_probe.py
"""

from decimal import Decimal

import psycopg
import rapidjson
from psycopg.adapt import AdaptersMap, PyFormat, Transformer
from psycopg.pq import Format
from psycopg.types.json import Json, Jsonb, set_json_dumps, set_json_loads


def json_bytes(value):
    return rapidjson.dumps(value, number_mode=rapidjson.NM_DECIMAL, allow_nan=False, sort_keys=True,
                           ensure_ascii=False, bytes_mode=rapidjson.BM_NONE).encode()


def json_loads(content):
    return rapidjson.loads(content, number_mode=rapidjson.NM_DECIMAL, allow_nan=False)


print("psycopg", psycopg.__version__, "| impl", psycopg.pq.__impl__)
scoped = AdaptersMap(psycopg.adapters)


class Context:
    adapters = scoped
    connection = None


set_json_dumps(json_bytes, context=Context)
set_json_loads(json_loads, context=Context)
tx = Transformer(Context)
value = {"b": Decimal("1.10"), "a": [1, 10**30]}
for wrapper in (Jsonb, Json):
    for fmt in (PyFormat.BINARY, PyFormat.TEXT):
        dumper = tx.get_dumper(wrapper(value), fmt)
        print(f"  {wrapper.__name__:5} {fmt.name:6} {type(dumper).__name__:24} -> {bytes(dumper.dump(wrapper(value)))!r}")
for oid_name, fmt in (("jsonb", Format.BINARY), ("jsonb", Format.TEXT), ("json", Format.TEXT)):
    oid = psycopg.adapters.types[oid_name].oid
    loader = tx.get_loader(oid, fmt)
    payload = (b"\x01" if (oid_name, fmt) == ("jsonb", Format.BINARY) else b"") + b'{"n":1.10,"i":100000000000000000000000000000}'
    print(f"  load {oid_name:5} {fmt.name:6} {type(loader).__name__:28} -> {loader.load(payload)!r}")
print("  global default untouched:", type(Transformer(psycopg.adapters).get_loader(
    psycopg.adapters.types["jsonb"].oid, Format.TEXT).load(b'{"n":1.10}')["n"]).__name__)
print("  Jsonb(value, dumps=...) per-value override:", bytes(
    tx.get_dumper(Jsonb(value), PyFormat.TEXT).dump(Jsonb(value, dumps=lambda v: "{}"))))
print("  plain dict without wrapper:", end=" ")
try:
    tx.get_dumper(value, PyFormat.AUTO)
    print("dumper found")
except Exception as exc:  # noqa: BLE001
    print(f"{type(exc).__name__}: {exc}")
