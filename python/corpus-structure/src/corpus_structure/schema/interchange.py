"""The interchange projections (model and projections §3.5; ADR-0020, ADR-0021): Arrow and DuckDB.

`compile_interchange(model)` is a pure function of the model: one Arrow schema per table (from the
relational projection, so the two agree by construction) and one per payload class (`ci:payload`),
plus their DuckDB column types and, per payload kind, the VARIANT `SHREDDING` spec that pool and
interchange's exports write. `encode` and `decode` carry records across, applying the null policy.

**Metadata.** Every schema carries `cs.model_revision` (the content hash) and `cs.class` (the
prefixed class, `core:` or `sys:`); a table schema also `cs.table`, a payload schema `cs.payload`
(its kind). A JSON-valued field carries `cs.class`, the class its value instantiates, when the
model names one. `cs.payload_schema_id` is the registry's id of a payload schema, known only once
the registry holds it (its row stores these very bytes), so `with_payload_schema_id` stamps it on a
copy for an export.

**Payload fields.** A scalar slot is typed (`integer` int64, a float float64, `boolean`, a timestamp
`timestamp[us, UTC]`, strings and enums `string`, `Bytes` binary); multivalued, a list of that. A
slot ranged over a class travels as `arrow.json` text, as does `Json`: condition trees and nested
values are recursive or carry the core shapes' forms and aliases, which only their JSON keeps
(§3.5). So does a slot whose `any_of` alternatives include a class (`ClaimItem.object`: an entity
or a value); its field carries `cs.any_of`, the alternatives, instead of `cs.class`.
A class with one attribute that is `Json` or a keyed inlined collection stands for that value, a
root (`TriggerMetrics`, `FrameEntries`): its record is `{<attribute>: <the value>}`. No Arrow
extension type is used beyond the canonical `arrow.json`, which DuckDB reads as `JSON`.

**The null policy** (`ci:null`; Arrow has only null, so absent and null would collapse). A field is
nullable unless its slot is required or declares `ci:null: never`; null then stands for absent. A
`json` field holds the value's JSON text (compact, in the dump's key order; not canonical JSON,
which refuses the floats payloads hold), so a JSON `null` is the text `null` and Arrow
null is absent. `encode` refuses a null where the schema forbids one (`NullPolicyError`), at any
depth.

**Table fields** follow the generated `MetaData`'s column types (bigint int64, integer int32,
smallint int16, real float32, double precision float64, timestamptz `timestamp[us, UTC]`, text and
regconfig string, bytea binary, jsonb `arrow.json`, `halfvec` a list of float32, arrays lists) and
nullability.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import cache
from typing import Any

import pyarrow as pa
from sqlalchemy import BigInteger, Boolean, Double, Integer, SmallInteger, Table, Text
from sqlalchemy.dialects.postgresql import ARRAY, BYTEA, JSONB, REAL, REGCONFIG, TIMESTAMP
from sqlalchemy.types import TypeEngine

from corpus_structure.schema import relational
from corpus_structure.schema.model import Model, ModelError, ci_annotations, revision

# Bump on any change to what the compiler produces for the same model.
COMPILER_VERSION = "1"
COMPILER = "corpus_structure.schema.interchange"

JSON = pa.json_(pa.string())
TIMESTAMP_TYPE = pa.timestamp("us", tz="UTC")
URI_TYPES: Mapping[str, pa.DataType] = {
    "xsd:long": pa.int64(),
    "xsd:short": pa.int16(),
    "xsd:integer": pa.int64(),
    "xsd:int": pa.int64(),
    "xsd:float": pa.float64(),
    "xsd:double": pa.float64(),
    "xsd:boolean": pa.bool_(),
    "xsd:dateTime": TIMESTAMP_TYPE,
    "xsd:string": pa.string(),
}
SQL_TYPES: Mapping[str, pa.DataType] = {
    "bytea": pa.binary(),
    "jsonb": JSON,
    "regconfig": pa.string(),
    "halfvec": pa.list_(pa.float32()),
}


class NullPolicyError(ValueError):
    """A record has a null where its schema forbids one (`ci:null: never`, or a required slot)."""


@dataclass(frozen=True)
class Interchange:
    """The model's Arrow schemas, by table full name and by prefixed payload class."""

    model_revision: str
    tables: Mapping[str, pa.Schema]
    payloads: Mapping[str, pa.Schema]
    kinds: Mapping[str, str]  # payload kind -> prefixed class

    def payload(self, kind: str) -> pa.Schema:
        return self.payloads[self.kinds[kind]]

    def shredding(self, kind: str) -> str:
        """The VARIANT `SHREDDING` type of the payload kind's column (pool and interchange)."""
        return shredding_type(self.payload(kind))


def _meta(items: Mapping[str, str]) -> dict[bytes, bytes]:
    return {k.encode(): v.encode() for k, v in items.items()}


def prefixed(model: Model, cls: str) -> str:
    """A class's prefixed name: `core:` for the core module's, `sys:` for the system module's."""
    return f"core:{cls}" if cls in model.core.schema.classes else f"sys:{cls}"


# --- Payload classes ---------------------------------------------------------------------------


def _scalar(model: Model, rng: str) -> pa.DataType:
    view = model.system
    if view.get_enum(rng) is not None:
        return pa.string()
    sql_type = ci_annotations(view.get_type(rng)).get("ci:sql_type")
    if sql_type is not None:
        if sql_type not in SQL_TYPES:
            raise ModelError([f"type {rng}: ci:sql_type {sql_type!r} has no Arrow type"])
        return SQL_TYPES[sql_type]
    for name in (rng, *view.type_ancestors(rng)):
        uri = view.get_type(name).uri
        if uri in URI_TYPES:
            return URI_TYPES[uri]
    raise ModelError([f"type {rng}: no Arrow type for its uri"])


def root_attribute(model: Model, cls: str) -> str | None:
    """The attribute a root class stands for (module doc), or None."""
    slots = list(model.system.class_induced_slots(cls))
    if len(slots) != 1:
        return None
    slot = slots[0]
    rng = str(slot.range or model.system.schema.default_range)
    if rng == "Json":
        return str(slot.name)
    target = model.system.get_class(rng)
    keyed = target is not None and any(s.identifier for s in model.system.class_induced_slots(rng))
    if slot.multivalued and slot.inlined and not slot.inlined_as_list and keyed:
        return str(slot.name)
    return None


def _payload_field(model: Model, cls: str, slot: Any) -> pa.Field:
    view = model.system
    name, rng = str(slot.name), str(slot.range or view.schema.default_range)
    ann = ci_annotations(slot)
    meta: dict[str, str] = {}
    # a slot ranged over several alternatives (`any_of`), one of them a class, is a class value
    alternatives = [str(x.range) for x in slot.any_of or () if x.range is not None]
    classes = [r for r in alternatives if view.get_class(r) is not None]
    if view.get_class(rng) is not None or classes or rng == "Json" or ann.get("ci:null") == "json":
        typ = JSON
        if classes:
            meta["cs.any_of"] = " ".join(prefixed(model, r) for r in alternatives)
        elif view.get_class(rng) is not None:
            meta["cs.class"] = prefixed(model, rng)
        if ann.get("ci:null") is not None:
            meta["cs.null"] = str(ann["ci:null"])
    else:
        typ = _scalar(model, rng)
        if slot.multivalued:
            typ = pa.list_(pa.field("item", typ, nullable=False))
        if ann.get("ci:null") is not None:
            meta["cs.null"] = str(ann["ci:null"])
    nullable = not slot.required and ann.get("ci:null") != "never"
    return pa.field(name, typ, nullable=nullable, metadata=_meta(meta) if meta else None)


def payload_schema(model: Model, cls: str, model_revision: str) -> pa.Schema:
    fields = [_payload_field(model, cls, s) for s in model.system.class_induced_slots(cls)]
    kind = ci_annotations(model.system.get_class(cls)).get("ci:payload")
    meta = {"cs.model_revision": model_revision, "cs.class": prefixed(model, cls)}
    if kind is not None:
        meta["cs.payload"] = str(kind)
    root = root_attribute(model, cls)
    if root is not None:
        meta["cs.root"] = root
    return pa.schema(fields, metadata=_meta(meta))


# --- Tables ------------------------------------------------------------------------------------


def _sql_arrow(typ: TypeEngine) -> pa.DataType:
    if isinstance(typ, ARRAY):
        return pa.list_(pa.field("item", _sql_arrow(typ.item_type), nullable=False))
    if isinstance(typ, relational.HalfVec):
        return SQL_TYPES["halfvec"]
    by_class: list[tuple[type, pa.DataType]] = [
        (BigInteger, pa.int64()),
        (SmallInteger, pa.int16()),
        (Integer, pa.int32()),
        (REAL, pa.float32()),
        (Double, pa.float64()),
        (Boolean, pa.bool_()),
        (TIMESTAMP, TIMESTAMP_TYPE),
        (JSONB, JSON),
        (BYTEA, pa.binary()),
        (REGCONFIG, pa.string()),
        (Text, pa.string()),
    ]
    for cls, arrow in by_class:
        if isinstance(typ, cls):
            return arrow
    raise ModelError([f"no Arrow type for SQL type {typ!r}"])


def table_schema(model: Model, table: Table, model_revision: str) -> pa.Schema:
    view = model.system
    cls = table.info.get("model_class")
    fields = []
    for column in table.columns:
        meta = {}
        if cls is not None and isinstance(column.type, JSONB):
            rng = view.induced_slot(column.name, cls).range
            if rng is not None and view.get_class(rng) is not None:
                meta["cs.class"] = prefixed(model, str(rng))
        fields.append(
            pa.field(
                column.name,
                _sql_arrow(column.type),
                nullable=bool(column.nullable),
                metadata=_meta(meta) if meta else None,
            )
        )
    meta = {"cs.model_revision": model_revision, "cs.table": table.fullname}
    if cls is not None:
        meta["cs.class"] = prefixed(model, cls)
    else:
        enum = str(table.info["model_enum"])
        meta["cs.class"] = f"core:{enum}" if enum in model.core.schema.enums else f"sys:{enum}"
    return pa.schema(fields, metadata=_meta(meta))


def compile_interchange(model: Model) -> Interchange:
    """Every table's and payload class's Arrow schema (module doc)."""
    current = revision(model).content_hash
    metadata = relational.compile_metadata(model.system)
    tables = {name: table_schema(model, t, current) for name, t in metadata.tables.items()}
    payloads, kinds = {}, {}
    for name, element in model.system.schema.classes.items():
        kind = ci_annotations(element).get("ci:payload")
        if kind is None:
            continue
        cls = prefixed(model, str(name))
        payloads[cls] = payload_schema(model, str(name), current)
        kinds[str(kind)] = cls
    return Interchange(current, tables, payloads, kinds)


@cache
def installed() -> Interchange:
    """The installed model's projections, compiled once per process."""
    from corpus_structure.schema.model import load

    return compile_interchange(load())


def with_payload_schema_id(schema: pa.Schema, payload_schema_id: int) -> pa.Schema:
    """A copy of a payload schema stamped with its registry id (`cs.payload_schema_id`)."""
    meta = dict(schema.metadata or {})
    meta[b"cs.payload_schema_id"] = str(payload_schema_id).encode()
    return schema.with_metadata(meta)


# --- Records -----------------------------------------------------------------------------------


_ABSENT = object()


def _encode_value(field: pa.Field, value: Any, where: str) -> Any:
    if value is _ABSENT or (value is None and field.type != JSON):
        if not field.nullable:
            raise NullPolicyError(f"{where}: null where the schema forbids it")
        return None
    if field.type == JSON:  # JSON text; payloads hold floats, which canonical JSON refuses
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    if pa.types.is_list(field.type):
        item = field.type.value_field
        return [_encode_value(item, v, f"{where}[{i}]") for i, v in enumerate(value)]
    return value


def encode(schema: pa.Schema, records: Iterable[Mapping[str, Any]]) -> pa.Table:
    """Records (JSON-mode dumps, absent fields left out) as an Arrow table under `schema`."""
    root = (schema.metadata or {}).get(b"cs.root")
    rows = []
    for n, record in enumerate(records):
        if root is not None:
            record = {root.decode(): record}
        unknown = set(record) - set(schema.names)
        if unknown:
            raise ValueError(f"record {n}: fields {sorted(unknown)} are not in the schema")
        rows.append(
            {
                f.name: _encode_value(f, record.get(f.name, _ABSENT), f"record {n}: {f.name}")
                for f in schema
            }
        )
    return pa.Table.from_pylist(rows, schema=schema)


def _decode_value(field: pa.Field, value: Any) -> Any:
    if value is None:
        return _ABSENT
    if field.type == JSON:
        return json.loads(value)
    if pa.types.is_list(field.type):
        return [_decode_value(field.type.value_field, v) for v in value]
    return value


def decode(table: pa.Table) -> list[Any]:
    """The records of an encoded table, absent fields left out (the inverse of `encode`)."""
    root = (table.schema.metadata or {}).get(b"cs.root")
    out: list[Any] = []
    for row in table.to_pylist():
        record = {}
        for field in table.schema:
            value = _decode_value(field, row[field.name])
            if value is not _ABSENT:
                record[field.name] = value
        out.append(record.get(root.decode()) if root is not None else record)
    return out


# --- DuckDB ------------------------------------------------------------------------------------


def duckdb_type(typ: pa.DataType) -> str:
    """The DuckDB type of an Arrow type (the column types of exports and the pool)."""
    if typ == JSON:
        return "JSON"
    if pa.types.is_list(typ):
        return f"{duckdb_type(typ.value_type)}[]"
    if pa.types.is_struct(typ):
        return "STRUCT(" + ", ".join(f'"{f.name}" {duckdb_type(f.type)}' for f in typ) + ")"
    if pa.types.is_timestamp(typ) and typ.tz is not None:
        return "TIMESTAMPTZ"
    names = {
        pa.int16(): "SMALLINT",
        pa.int32(): "INTEGER",
        pa.int64(): "BIGINT",
        pa.float32(): "FLOAT",
        pa.float64(): "DOUBLE",
        pa.bool_(): "BOOLEAN",
        pa.string(): "VARCHAR",
        pa.binary(): "BLOB",
    }
    if typ not in names:
        raise ModelError([f"no DuckDB type for Arrow type {typ}"])
    return names[typ]


def duckdb_columns(schema: pa.Schema) -> dict[str, str]:
    return {f.name: duckdb_type(f.type) for f in schema}


def shredding_type(schema: pa.Schema) -> str:
    """The `STRUCT(…)` a payload's VARIANT column shreds into: its typed fields, JSON as VARIANT."""

    def shred(typ: pa.DataType) -> str:
        if typ == JSON:
            return "VARIANT"
        if pa.types.is_list(typ):
            return f"{shred(typ.value_type)}[]"
        return duckdb_type(typ)

    return "STRUCT(" + ", ".join(f'"{f.name}" {shred(f.type)}' for f in schema) + ")"
