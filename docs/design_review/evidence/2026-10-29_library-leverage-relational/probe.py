"""Pure-Python compile probe (no database connection): relational access route questions.

Q1  IN-list rendering: does Core `col.in_(ids)` expand to one bind per element under the
    psycopg dialect, and does `col == any_(bindparam(ARRAY))` render one array parameter?
Q2  Set-oriented explanation / predicate composition: do release-scoped predicates over
    typed_value/value_role compose into one statement whose filters stay in SQL?
Q3  Reachability closure: can a recursive CTE over a non-recursive UNION ALL edge relation
    (fact -> value, value -> child value, value -> entity, entity -> fact) be expressed in Core
    against the shared MetaData, with a single recursive reference?
Q4  DDL compiler parity: does CreateTable(...) over the shared MetaData reproduce a frozen
    revision's CREATE TABLE text?
Q5  Principal conninfo derivation: does psycopg.conninfo.make_conninfo override `user` on the
    configured libpq URL without network access?

Run from the repository root: uv run --no-sync python <this file>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import psycopg
import sqlalchemy
from psycopg.conninfo import conninfo_to_dict, make_conninfo
from sqlalchemy import ARRAY, Text, and_, any_, bindparam, exists, literal, select, union_all
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "python/corpus-structure/src"))
from corpus_structure.semantic.metadata import table  # noqa: E402

DIALECT = postgresql.psycopg.dialect()
print("sqlalchemy", sqlalchemy.__version__, "psycopg", psycopg.__version__)


def show(title: str, stmt, **kw) -> str:
    compiled = stmt.compile(dialect=DIALECT, **kw)
    text = str(compiled)
    print(f"\n=== {title}\n{text}\nparams={sorted(compiled.params)[:8]}... n={len(compiled.params)}")
    return text


# Q1 -------------------------------------------------------------------------------------
f = table("data.fact")
ids = [f"fact:{i}" for i in range(5)]
expanded = select(f.c.fact_id).where(f.c.fact_id.in_(ids))
compiled = expanded.compile(dialect=DIALECT)
print("\n=== Q1a in_() cached form:", str(compiled))
rendered = expanded.compile(dialect=DIALECT, compile_kwargs={"render_postcompile": True})
print("Q1a in_() post-compile form:", str(rendered), "params:", len(rendered.params))
anyform = select(f.c.fact_id).where(f.c.fact_id == any_(bindparam("ids", type_=ARRAY(Text))))
show("Q1b = ANY(array bind)", anyform)

# Q2 -------------------------------------------------------------------------------------
v, r = table("data.typed_value"), table("data.value_role")
release, realization = "release:x", "realization:y"


def scope(rel):
    return and_(rel.c.release_id == release, rel.c.realization_id == realization)


# A release-checked predicate would be validated in Python against the prepared release,
# then lowered to these expressions; this only checks that the lowering composes.
role_pred = exists(
    select(1).where(
        scope(r),
        r.c.parent_value_id == f.c.object_value_id,
        r.c.role == "unit",
        exists(
            select(1).where(
                scope(v),
                v.c.value_id == r.c.child_value_id,
                v.c.kind == "string",
                v.c.text_value == "mg",
            )
        ),
    )
)
query = (
    select(f.c.fact_id, f.c.subject_id)
    .where(scope(f), f.c.property_id == "prop:dose", role_pred, f.c.fact_id.collate("C") > "after")
    .order_by(f.c.fact_id.collate("C"))
    .limit(101)
)
show("Q2a predicate over value_role/typed_value composed into one SELECT", query)

s, o = table("data.support"), table("data.occurrence")
explain_many = (
    select(s.c.fact_id, o)
    .select_from(s.join(o, and_(s.c.release_id == o.c.release_id,
                                s.c.realization_id == o.c.realization_id,
                                s.c.occurrence_id == o.c.occurrence_id)))
    .where(scope(s), s.c.fact_id == any_(bindparam("fact_ids", type_=ARRAY(Text))))
    .order_by(s.c.fact_id, o.c.occurrence_id)
)
show("Q2b set-oriented support read keyed by fact_id = ANY(:fact_ids)", explain_many)

# Q3 -------------------------------------------------------------------------------------
fact_edges = select(
    literal("e").label("src_kind"), f.c.subject_id.label("src"),
    literal("v").label("dst_kind"), f.c.object_value_id.label("dst"),
).where(scope(f), f.c.property_id.in_(["prop:a", "prop:b"]))
role_edges = select(
    literal("v"), r.c.parent_value_id, literal("v"), r.c.child_value_id
).where(scope(r))
entity_edges = select(
    literal("v"), v.c.value_id, literal("e"), v.c.entity_id
).where(scope(v), v.c.kind == "entity")
edges = union_all(fact_edges, role_edges, entity_edges).subquery("edges")
seed = select(literal("e").label("kind"), literal("entity:root").label("node")).cte(
    "reach", recursive=True
)
reach = seed.union(
    select(edges.c.dst_kind, edges.c.dst).join(
        seed, and_(edges.c.src_kind == seed.c.kind, edges.c.src == seed.c.node)
    )
)
closure_sql = show(
    "Q3 reachability closure over a UNION ALL edge relation",
    select(reach.c.node).where(reach.c.kind == "e"),
)
print("Q3 single recursive reference in the recursive term:",
      closure_sql.count("JOIN reach ON") == 1)

# Q4 -------------------------------------------------------------------------------------
frozen = (
    ROOT / "python/corpus-structure/semantic_alembic/versions/semantic_0027_exclusions.sql"
).read_text()


def norm(sql: str) -> str:
    return re.sub(r"\s+", " ", sql).strip()


for name in ("data.identity_exclusion", "data.identity_exclusion_evidence"):
    generated = str(CreateTable(table(name)).compile(dialect=postgresql.dialect())).strip()
    start = frozen.index(f"CREATE TABLE {name} (")
    end = frozen.index("\n)\n", start) + 2
    frozen_stmt = frozen[start:end].strip()
    print(f"\n=== Q4 {name}: CreateTable text == frozen 0027 text:",
          norm(generated) == norm(frozen_stmt))
    if norm(generated) != norm(frozen_stmt):
        print("generated:\n" + generated + "\nfrozen:\n" + frozen_stmt)

# Q5 -------------------------------------------------------------------------------------
base = "postgresql:///corpus?host=/var/run/postgresql&port=5434"
for principal in ("corpus_sem_writer", "corpus_sem_reader"):
    derived = make_conninfo(base, user=principal, application_name="probe")
    print(f"\n=== Q5 {principal}: {derived}  -> {conninfo_to_dict(derived)}")

# Q6 -------------------------------------------------------------------------------------
# Offline rendering for an authoring-time transport generator: psycopg.sql without a
# connection versus SQLAlchemy's identifier preparer (quotes only when required).
from psycopg import sql  # noqa: E402

temp = sql.SQL("CREATE TEMP TABLE {t}({cols}) ON COMMIT DROP; GRANT INSERT ({names}) ON pg_temp.{t} TO {w}").format(
    t=sql.Identifier("sp_fact"),
    cols=sql.SQL(",").join(
        sql.SQL("{} {}").format(sql.Identifier(c), sql.SQL(t))
        for c, t in [("fact_id", "text"), ("n", "numeric")]
    ),
    names=sql.SQL(",").join(map(sql.Identifier, ["fact_id", "n"])),
    w=sql.Identifier("corpus_sem_writer"),
)
print("\n=== Q6 psycopg.sql offline:", temp.as_string(None))
print("Q6 psycopg.sql Literal offline:", sql.Literal("it's").as_string(None))
quote = postgresql.dialect().identifier_preparer.quote
print("Q6 SQLAlchemy preparer:", quote("sp_fact"), quote("corpus_sem_writer"), quote("Mixed"))
