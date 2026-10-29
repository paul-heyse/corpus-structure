"""The Arrow-native write route (pool and interchange §3.4; ADR-0021; probe Q-5): Arrow relations
under the generated schemas into their tables.

`write_arrow(conn, table, rows)` conforms an Arrow table to M3's schema of a generated table
(`schema/interchange.py`; the columns it holds, in any order) and writes it by binary COPY with
`Copy.set_types` through F4's `repo.copy_rows`, inside the caller's transaction. Values cross as
the null policy reads them: Arrow null is SQL NULL (absent), an `arrow.json` text is parsed and
written as `jsonb` (the text `null` as JSON `null`), a `timestamp[us, UTC]` as `timestamptz`.
Columns the relation lacks take their server defaults.

**pgpq is not adopted** (record `p0q.pool-roundtrip`): with NUMERIC as text it is refused by the
server, with decimal128 by Arrow, and it passes only through a text staging table and a server-side
cast. Psycopg `Copy.set_types` kept absent versus null, JSON text, NUMERIC and `timestamptz` on
every case. pgpq is reconsidered only if a measured writer cost calls for it, then with the
staging step.
"""

from __future__ import annotations

import json
from typing import Any

import pyarrow as pa
from psycopg.types.json import Jsonb
from sqlalchemy import Connection

from corpus_structure.core import db as store
from corpus_structure.core.db import repo
from corpus_structure.schema import interchange


class WriteSchemaError(ValueError):
    """A relation that does not conform to its table's M3 schema."""


def _column(field: pa.Field, column: pa.ChunkedArray) -> list[Any]:
    values = column.to_pylist()
    if field.type == interchange.JSON:
        return [None if v is None else Jsonb(json.loads(v)) for v in values]
    return values


def write_arrow(conn: Connection, table: str, rows: pa.Table) -> int:
    """Write `rows` into the generated table `table` (module doc); the number of rows written."""
    schema = interchange.installed().tables[table]
    columns = []
    for name in rows.column_names:
        if name not in schema.names:
            raise WriteSchemaError(f"{table} has no column {name!r}")
        field = schema.field(name)
        column = rows.column(name)
        if column.type != field.type:
            raise WriteSchemaError(f"{table}.{name} is {column.type}, the model's is {field.type}")
        if not field.nullable and column.null_count:
            raise WriteSchemaError(f"{table}.{name}: a null where the model forbids one")
        columns.append((name, _column(field, column)))
    names = [n for n, _ in columns]
    data = list(zip(*(values for _, values in columns), strict=True)) if columns else []
    return repo.copy_rows(conn, store.metadata.tables[table], names, data)
