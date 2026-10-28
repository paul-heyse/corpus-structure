"""The evidence catalog: a DuckDB database rebuilt from the records (never an authority).

Base tables describe every record. A folder may add its own tables and views over its result
files in `catalog.sql` (a Jinja template; `folder` is the folder's absolute path and `schema` its
DuckDB schema name), so analyses of a folder's data live beside that data.
"""

from __future__ import annotations

import re
from pathlib import Path

import duckdb
from jinja2 import Environment, StrictUndefined

from .store import Folder, Store

BASE_DDL = """
CREATE TABLE records (
    gid VARCHAR PRIMARY KEY, folder VARCHAR, id VARCHAR, title VARCHAR, grp VARCHAR,
    package VARCHAR, finalized DATE, status VARCHAR, superseded_by VARCHAR, question VARCHAR,
    method VARCHAR, outcome VARCHAR, conclusion VARCHAR, record_path VARCHAR);
CREATE TABLE record_answers (gid VARCHAR, item VARCHAR);
CREATE TABLE record_consumers (gid VARCHAR, consumer VARCHAR);
CREATE TABLE record_files (
    gid VARCHAR, direction VARCHAR, path VARCHAR, abs_path VARCHAR, role VARCHAR, sha256 VARCHAR);
CREATE TABLE record_results (
    gid VARCHAR, name VARCHAR, value_num DOUBLE, value_text VARCHAR, "of" BIGINT, unit VARCHAR,
    note VARCHAR);
CREATE TABLE record_links (gid VARCHAR, kind VARCHAR, target_gid VARCHAR);
CREATE TABLE record_agents (
    gid VARCHAR, role VARCHAR, model VARCHAR, brief VARCHAR, separation VARCHAR);
CREATE TABLE record_commands (gid VARCHAR, ord INTEGER, command VARCHAR);
CREATE MACRO records_for(item) AS TABLE
    SELECT r.* FROM records r JOIN record_answers a USING (gid)
    WHERE a.item = item AND r.status = 'current';
CREATE MACRO result(record_gid, result_name) AS
    (SELECT coalesce(CAST(value_num AS VARCHAR), value_text) FROM record_results
     WHERE gid = record_gid AND name = result_name);
"""


def schema_name(folder: Folder) -> str:
    return "f_" + re.sub(r"[^a-z0-9]+", "_", folder.name.lower()).strip("_")


def _gid(store: Store, folder: Folder, ref: str) -> str:
    hit = store.resolve(folder, ref)
    return f"{hit[0].name}/{hit[1].id}" if hit else ref


def _many(con: duckdb.DuckDBPyConnection, sql: str, rows: list[list]) -> None:
    if rows:  # DuckDB 2.0 rejects executemany with no parameter sets
        con.executemany(sql, rows)


def build(store: Store, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    con = duckdb.connect(str(path))
    try:
        con.execute(BASE_DDL)
        for folder, rec in store.all_records():
            gid = f"{folder.name}/{rec.id}"
            con.execute(
                "INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [
                    gid,
                    folder.name,
                    rec.id,
                    rec.title,
                    rec.group,
                    rec.package,
                    rec.finalized,
                    rec.status,
                    rec.superseded_by and _gid(store, folder, rec.superseded_by),
                    rec.question,
                    rec.method,
                    rec.outcome,
                    rec.conclusion,
                    str(folder.record_paths[rec.id].relative_to(store.root)),
                ],
            )
            _many(con, "INSERT INTO record_answers VALUES (?,?)", [[gid, a] for a in rec.answers])
            _many(
                con,
                "INSERT INTO record_consumers VALUES (?,?)",
                [[gid, c] for c in rec.consumed_by],
            )
            _many(
                con,
                "INSERT INTO record_files VALUES (?,?,?,?,?,?)",
                [
                    [gid, d, f.path, str(folder.path / f.path), f.role, f.sha256]
                    for d, f in rec.files
                ],
            )
            _many(
                con,
                "INSERT INTO record_results VALUES (?,?,?,?,?,?,?)",
                [
                    [
                        gid,
                        r.name,
                        float(r.value)
                        if isinstance(r.value, int | float) and not isinstance(r.value, bool)
                        else None,
                        None
                        if isinstance(r.value, int | float) and not isinstance(r.value, bool)
                        else str(r.value),
                        r.of,
                        r.unit,
                        r.note,
                    ]
                    for r in rec.results
                ],
            )
            links = [[gid, "depends_on", _gid(store, folder, x)] for x in rec.depends_on]
            links += [[gid, "supersedes", _gid(store, folder, x)] for x in rec.supersedes]
            _many(con, "INSERT INTO record_links VALUES (?,?,?)", links)
            _many(
                con,
                "INSERT INTO record_agents VALUES (?,?,?,?,?)",
                [[gid, a.role, a.model, a.brief, a.separation] for a in rec.agents],
            )
            _many(
                con,
                "INSERT INTO record_commands VALUES (?,?,?)",
                [[gid, i, c] for i, c in enumerate(rec.commands)],
            )
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
