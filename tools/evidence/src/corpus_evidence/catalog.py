"""The evidence catalog: a DuckDB database rebuilt from the records (never an authority).

Its tables are derived from the `Record` model, which is their only schema owner:
- `records` holds one row per record: `gid` (`<folder>/<id>`), `folder` and `record_path`, then
  every `Record` field under its own name, with Arrow types derived from the field annotations
  (a list is a LIST, a nested model a STRUCT, a number-or-text union a STRUCT of `num` and `text`);
- every list field `f` also gets a table `record_<f>` with one row per element: `gid`, `ord`
  (1-based) and the element's columns (nested STRUCT fields flattened as `<field>_<sub>`, so a
  result's value reads as `value_num` and `value_text`), or `item` for a list of scalars;
- `record_links` lists every record reference field (`supersedes`, `depends_on`, …) resolved to
  the target's gid.
Macros: `records_for(item)` (current records that answer an item) and `result(gid, name)`.

A folder may add its own tables and views over its result files in `catalog.sql` (a Jinja template;
`folder` is the folder's absolute path and `schema` its DuckDB schema name), so analyses of a
folder's data live beside that data.
"""

from __future__ import annotations

import datetime as dt
import functools
import operator
import re
import types
from pathlib import Path
from typing import Annotated, Any, Literal, Union, get_args, get_origin

import duckdb
import pyarrow as pa
from jinja2 import Environment, StrictUndefined
from pydantic import BaseModel

from .model import Record, RecordRef
from .store import Folder, Store

# Catalog columns that precede the model's own fields in `records`.
KEY_FIELDS = [
    pa.field("gid", pa.string(), nullable=False),
    pa.field("folder", pa.string(), nullable=False),
    pa.field("record_path", pa.string(), nullable=False),
]
_SCALARS: dict[type, pa.DataType] = {
    str: pa.string(),
    bool: pa.bool_(),
    int: pa.int64(),
    float: pa.float64(),
    dt.date: pa.date32(),
}
# A number-or-text union (`Result.value`) keeps both readings apart.
_NUM_TEXT = pa.struct([pa.field("num", pa.float64()), pa.field("text", pa.string())])

MACROS = """
CREATE MACRO records_for(answered) AS TABLE
    SELECT * FROM records WHERE list_contains(answers, answered) AND status = 'current';
CREATE MACRO result(record_gid, result_name) AS
    (SELECT coalesce(CAST(value_num AS VARCHAR), value_text) FROM record_results
     WHERE gid = record_gid AND name = result_name);
"""


def _strip(ann: Any) -> tuple[Any, bool]:
    """The annotation without `Annotated` metadata or `None`, and whether it was optional."""
    if get_origin(ann) is Annotated:
        return _strip(get_args(ann)[0])
    if get_origin(ann) in (Union, types.UnionType):
        args = [a for a in get_args(ann) if a is not type(None)]
        if len(args) == len(get_args(ann)):
            return ann, False
        inner = functools.reduce(operator.or_, args)
        return _strip(inner)[0], True
    return ann, False


def _is_num_text(ann: Any) -> bool:
    args = set(get_args(ann)) if get_origin(ann) in (Union, types.UnionType) else set()
    return (
        bool(args) and args <= {int, float, str, bool} and str in args and bool(args & {int, float})
    )


def arrow_type(ann: Any) -> pa.DataType:
    """The Arrow type of a model field annotation."""
    ann, _ = _strip(ann)
    if _is_num_text(ann):
        return _NUM_TEXT
    if get_origin(ann) is Literal:
        kinds = {type(v) for v in get_args(ann)}
        if len(kinds) != 1:
            raise TypeError(f"mixed Literal {ann!r} has no Arrow type")
        return _SCALARS[kinds.pop()]
    if get_origin(ann) is list:
        return pa.list_(arrow_type(get_args(ann)[0]))
    if isinstance(ann, type) and issubclass(ann, BaseModel):
        return pa.struct(model_fields(ann))
    if ann in _SCALARS:
        return _SCALARS[ann]
    raise TypeError(f"no Arrow type for {ann!r}; extend corpus_evidence.catalog")


def model_fields(model: type[BaseModel]) -> list[pa.Field]:
    return [
        pa.field(
            name, arrow_type(f.annotation), nullable=not f.is_required() or _strip(f.annotation)[1]
        )
        for name, f in model.model_fields.items()
    ]


def arrow_schema(model: type[BaseModel] = Record) -> pa.Schema:
    """The `records` table's schema: the catalog keys, then the model's fields."""
    return pa.schema(KEY_FIELDS + model_fields(model))


def _value(ann: Any, v: Any) -> Any:
    """A model value in the shape `arrow_type(ann)` describes."""
    ann, _ = _strip(ann)
    if v is None:
        return None
    if _is_num_text(ann):
        numeric = isinstance(v, int | float) and not isinstance(v, bool)
        return {"num": float(v) if numeric else None, "text": None if numeric else str(v)}
    if get_origin(ann) is list:
        (elem,) = get_args(ann)
        return [_value(elem, x) for x in v]
    if isinstance(v, BaseModel):
        return {n: _value(f.annotation, getattr(v, n)) for n, f in type(v).model_fields.items()}
    return v


def _row(store: Store, folder: Folder, rec: Record) -> dict:
    keys = {
        "gid": f"{folder.name}/{rec.id}",
        "folder": folder.name,
        "record_path": str(folder.record_paths[rec.id].relative_to(store.root)),
    }
    return keys | {
        n: _value(f.annotation, getattr(rec, n)) for n, f in type(rec).model_fields.items()
    }


def _columns(prefix: str, t: pa.DataType, name: str) -> list[str]:
    """Select-list items flattening a STRUCT expression into `<name>_<sub>` columns."""
    if pa.types.is_struct(t):
        out = []
        for f in t:
            sub = f"{prefix}.{_q(f.name)}"
            out += _columns(sub, f.type, f"{name}_{f.name}" if name else f.name)
        return out
    return [f"{prefix} AS {_q(name or 'item')}"]


def _q(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def element_tables(model: type[BaseModel] = Record) -> dict[str, str]:
    """`record_<field>` → its `CREATE TABLE … AS` statement, for every list field of the model."""
    out = {}
    for f in model_fields(model):
        if not pa.types.is_list(f.type):
            continue
        cols = ", ".join(["gid", "ord", *_columns("e", f.type.value_type, "")])
        out[f"record_{f.name}"] = (
            f"CREATE TABLE record_{f.name} AS SELECT {cols} FROM ("
            f"SELECT gid, generate_subscripts({_q(f.name)}, 1) AS ord, unnest({_q(f.name)}) AS e "
            f"FROM records) ORDER BY gid, ord"
        )
    return out


def ref_fields(model: type[BaseModel] = Record) -> list[str]:
    """Fields holding record references (`RecordRef` or a list of them)."""
    out = []
    for name, f in model.model_fields.items():
        ann = f.annotation
        inner = get_args(ann)[0] if get_origin(ann) is list else ann
        if inner == RecordRef or RecordRef in get_args(inner):
            out.append(name)
    return out


_LINKS = pa.schema(
    [
        pa.field("gid", pa.string()),
        pa.field("kind", pa.string()),
        pa.field("target_gid", pa.string()),
    ]
)


def _links(store: Store) -> pa.Table:
    rows = []
    for folder, rec in store.all_records():
        for kind in ref_fields(type(rec)):
            v = getattr(rec, kind)
            for ref in v if isinstance(v, list) else [v] if v else []:
                hit = store.resolve(folder, ref)
                target = f"{hit[0].name}/{hit[1].id}" if hit else None
                rows.append({"gid": f"{folder.name}/{rec.id}", "kind": kind, "target_gid": target})
    return pa.Table.from_pylist(rows, schema=_LINKS)


def schema_name(folder: Folder) -> str:
    return "f_" + re.sub(r"[^a-z0-9]+", "_", folder.name.lower()).strip("_")


def build(store: Store, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    records = pa.Table.from_pylist(
        [_row(store, f, r) for f, r in store.all_records()], schema=arrow_schema()
    )
    links = _links(store)
    con = duckdb.connect(str(path))
    try:
        con.from_arrow(records).create("records")
        con.execute("ALTER TABLE records ADD PRIMARY KEY (gid)")
        for sql in element_tables().values():
            con.execute(sql)
        con.from_arrow(links).create("record_links")
        con.execute(MACROS)
        env = Environment(undefined=StrictUndefined, keep_trailing_newline=True, autoescape=False)
        for folder in store.folders.values():
            sql_path = folder.path / "catalog.sql"
            if not sql_path.exists():
                continue
            schema = schema_name(folder)
            con.execute(f"CREATE SCHEMA {schema}")
            sql = env.from_string(sql_path.read_text(encoding="utf-8")).render(
                folder=str(folder.path), schema=schema
            )
            con.execute(f"SET schema = '{schema}'")
            con.execute(sql)
            con.execute("SET schema = 'main'")
        con.execute("CHECKPOINT")
    finally:
        con.close()
    return path
