"""The pool loader (pool and interchange §3.1; probe Q-5, record `p0q.pool-roundtrip`): one run's
pool from PostgreSQL as of its cut.

`load(conn, run_id, cut, kinds)` reads, on one ADBC connection (the DBAPI's default, not autocommit)
in one `REPEATABLE READ, READ ONLY` transaction that it rolls back, so every read sees one snapshot:
1. the run row; `cut` is the cut the caller consolidates as of (None before the seal), and a run
   row whose `cut_at` differs is refused (`CutMismatch`);
2. the registry's rows (`meta.payload_schema`), for reading payloads under their recorded schemas;
3. the run's effective observations of the selected kinds from `kb.run_observation`, whose view
   carries the cut predicate (`core/db/overlay.py`; D3 §8): a task finished after `cut_at` is not
   in it;
4. with a reference run, its global entities and their aliases;
and hands them to `contract.build`, which owns everything after the read.

**Route** (Q-5): ADBC's `fetch_record_batch()` (binary `COPY … TO STDOUT`), each reader consumed
once. The run id and the kinds are bound as literals (an int and members of `ObservationKind`),
because a `$1` parameter leaves the COPY transport. JSONB arrives as `arrow.json`; nothing loaded is
NUMERIC or an infinite timestamp. `connect(url)` opens a connection on a libpq URL
(`Settings().database.url`).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime
from typing import Any

import adbc_driver_postgresql.dbapi as adbc
import pyarrow as pa

from corpus_structure.core.payload_schemas import PayloadSchemaRow
from corpus_structure.core.vocab import ObservationKind
from corpus_structure.pool import contract
from corpus_structure.pool.contract import ALL_KINDS, Pool, RunRow
from corpus_structure.schema import interchange


class RunNotFound(LookupError):
    """No `ops.run` row has the id."""


class CutMismatch(ValueError):
    """The run row's `cut_at` is not the cut the caller loads as of."""


@contextmanager
def connect(url: str) -> Iterator[adbc.Connection]:
    """An ADBC connection on a libpq URL, closed afterwards."""
    with adbc.connect(url) as conn:
        yield conn


def _read(cur: Any, sql: str) -> pa.Table:
    cur.execute(sql)
    return cur.fetch_record_batch().read_all()


def _columns(schema: pa.Schema, alias: str) -> str:
    return ", ".join(f'{alias}."{f.name}"' for f in schema)


def _run(cur: Any, run_id: int) -> RunRow:
    rows = _read(
        cur,
        "SELECT id, cut_at, schema_version_id, model_revision_id, key_scheme, reference_run_id "
        f"FROM ops.run WHERE id = {run_id}",
    ).to_pylist()
    if not rows:
        raise RunNotFound(f"no run {run_id}")
    return RunRow(**rows[0])


def _registry(cur: Any) -> list[PayloadSchemaRow]:
    sql = 'SELECT id, "class", kind, version, parent_id, upcaster FROM meta.payload_schema'
    rows = _read(cur, sql).to_pylist()
    columns = ("id", "class", "kind", "version", "parent_id", "upcaster")
    return [PayloadSchemaRow(*(r[c] for c in columns)) for r in rows]


def load(
    conn: adbc.Connection,
    run_id: int,
    cut: datetime | None,
    kinds: Iterable[str] = ALL_KINDS,
) -> Pool:
    """The pool of run `run_id` as of `cut` (module doc)."""
    run_id = int(run_id)
    selected = sorted({ObservationKind(k).value for k in kinds})
    cur = conn.cursor()
    try:
        cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        run = _run(cur, run_id)
        if run.cut_at != cut:
            raise CutMismatch(f"run {run_id} is cut at {run.cut_at}, not at {cut}")
        registry = _registry(cur)
        raw = contract.raw_schema()
        kind_list = ", ".join(f"'{k}'" for k in selected) or "NULL"
        observations = _read(
            cur,
            f"SELECT {_columns(raw, 'o')} FROM kb.run_observation o "
            f"WHERE o.run_id = {run_id} AND o.kind IN ({kind_list})",
        )
        entities = aliases = None
        if run.reference_run_id is not None:
            ref = int(run.reference_run_id)
            where = f"e.run_id = {ref} AND e.scope = 'global'"
            entity = contract.reference_schema(contract.REFERENCE_ENTITIES)
            alias = contract.reference_schema(contract.REFERENCE_ALIASES)
            entities = _read(cur, f"SELECT {_columns(entity, 'e')} FROM kb.entity e WHERE {where}")
            aliases = _read(
                cur,
                f"SELECT {_columns(alias, 'a')} FROM kb.entity_alias a "
                f"JOIN kb.entity e ON e.id = a.entity_id WHERE {where}",
            )
    finally:
        cur.close()
        conn.rollback()
    return contract.build(run, registry, observations, entities, aliases, selected)


def read_tables(
    conn: adbc.Connection, queries: Mapping[str, tuple[str, str]]
) -> dict[str, pa.Table]:
    """Generated tables' rows, each `name -> (from_and_where, order_by)` read as
    `SELECT <the table's columns> FROM <from_and_where> ORDER BY <order_by>` with the table
    aliased `t`, in one `REPEATABLE READ, READ ONLY` snapshot, and conformed to M3's schema of the
    table (`cs.table` names it)."""
    tables = interchange.installed().tables
    out = {}
    cur = conn.cursor()
    try:
        cur.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        for name, (source, order) in queries.items():
            schema = tables[name]
            rows = _read(cur, f"SELECT {_columns(schema, 't')} FROM {source} ORDER BY {order}")
            meta = {**(schema.metadata or {}), b"cs.relation": name.encode()}
            target = schema.with_metadata(meta)
            # ADBC's array items are nullable where M3's are not; the values cast unchanged
            rows = pa.Table.from_arrays(
                [
                    c.cast(f.type) if c.type != f.type and pa.types.is_list(f.type) else c
                    for c, f in zip(rows.columns, target, strict=True)
                ],
                names=target.names,
            )
            out[name] = contract.conform(rows, target)
    finally:
        cur.close()
        conn.rollback()
    return out
