"""Alembic 1.20.0 offline probe for the semantic MetaData; opens no database connection.

Questions:
  A. Which properties of the shared semantic MetaData fall outside Alembic 1.20's
     autogenerate comparison (partial-index predicates, SQL-only tables)?
  B. Can Alembic's Operations, in offline (as_sql) mode with only a dialect name, render
     a MetaData table's CREATE TABLE as SQL text, and how close is that text to the
     frozen revision SQL for the same table?

Run from the repository root:
  uv run --no-sync python docs/design_review/evidence/2026-10-29_library-leverage-postgres-migrations/alembic_offline_probe.py
"""

from __future__ import annotations

import io
import re
import sys
from importlib.metadata import version
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations, ops

from corpus_structure.semantic.metadata import SCHEMAS, metadata

ROOT = Path(__file__).resolve().parents[4]
VERSIONS = ROOT / "python/corpus-structure/semantic_alembic/versions"


def norm(sql: str) -> str:
    return re.sub(r"\s+", " ", sql).strip().rstrip(";").strip()


def main() -> int:
    print("alembic", version("alembic"), "sqlalchemy", version("sqlalchemy"), sys.version.split()[0])

    # A. MetaData census relevant to Alembic comparison coverage.
    names = set(metadata.tables)
    print("metadata tables:", len(names), "schemas:", sorted({t.schema for t in metadata.tables.values()}))
    print("SCHEMAS filter:", sorted(SCHEMAS))
    sql_tables = set()
    for f in sorted(VERSIONS.glob("*.sql")):
        sql_tables |= set(re.findall(r"CREATE TABLE ([a-z_]+\.[a-z_]+)", f.read_text()))
    print("tables created by frozen SQL:", len(sql_tables))
    print("SQL-created tables absent from MetaData:", sorted(sql_tables - names))
    partial = []
    expr = []
    checks = 0
    defaults = 0
    for t in metadata.tables.values():
        for ix in t.indexes:
            if ix.dialect_options["postgresql"].get("where") is not None:
                partial.append(f"{t.fullname}:{ix.name}")
            if any(not hasattr(e, "name") or e.__class__.__name__ != "Column" for e in ix.expressions):
                expr.append(f"{t.fullname}:{ix.name}")
        checks += sum(1 for c in t.constraints if c.__class__.__name__ == "CheckConstraint")
        defaults += sum(1 for c in t.columns if c.server_default is not None)
    print("partial indexes (postgresql_where):", len(partial), partial[:6])
    print("expression indexes:", len(expr), expr[:6])
    print("check constraints:", checks, "server defaults:", defaults)

    # B. Offline rendering through Alembic Operations: no connection, dialect name only.
    buf = io.StringIO()
    ctx = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": buf}
    )
    op = Operations(ctx)
    target = metadata.tables["data.identity_exclusion"]
    op.invoke(ops.CreateTableOp.from_table(target))
    for ix in sorted(target.indexes, key=lambda i: i.name or ""):
        op.invoke(ops.CreateIndexOp.from_index(ix))
    rendered = buf.getvalue()
    print("--- offline rendered SQL (data.identity_exclusion) ---")
    print(rendered.strip())
    frozen_src = (VERSIONS / "semantic_0027_exclusions.sql").read_text()
    m = re.search(r"CREATE TABLE data\.identity_exclusion \(.*?\n\)\s*\n\s*;", frozen_src, re.S)
    frozen = m.group(0) if m else ""
    first = re.search(r"CREATE TABLE data\.identity_exclusion \(.*?\n\)", rendered, re.S)
    print("--- comparison ---")
    print("frozen CREATE TABLE found:", bool(m))
    print(
        "whitespace-normalized CREATE TABLE equal:",
        bool(first) and norm(first.group(0)) == norm(frozen),
    )

    def lines(sql: str) -> list[str]:
        return sorted(x.strip().rstrip(",").strip() for x in sql.splitlines() if x.strip())

    print(
        "same element lines ignoring order:",
        bool(first) and lines(first.group(0)) == lines(frozen.rstrip().rstrip(";")),
    )
    rendered_constraints = re.findall(r"CONSTRAINT (\S+)", first.group(0)) if first else []
    print("rendered constraint order:", rendered_constraints)
    # Reference only: SQLAlchemy's own CreateTable ordering (DDL compiler is another cluster's topic).
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.schema import CreateTable

    direct = str(CreateTable(target).compile(dialect=postgresql.dialect()))
    print(
        "SQLAlchemy CreateTable whitespace-normalized equal to frozen:",
        norm(direct) == norm(frozen),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
