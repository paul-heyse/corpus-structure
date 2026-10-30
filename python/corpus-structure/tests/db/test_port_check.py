"""The port check (model and projections §3.4; probe Q-3): the generated `MetaData` and the overlay
against D3's DDL, through a normalized pglast 8.7 projection, and D3's queries against `MetaData`.

- **Reference.** `data/d3_ddl.sql`, D3 §3-§8's DDL blocks as of 34cd2a8 (D3 is to cite the generated
  rendering instead), for every table D3 renders. Its `IN (/* generated … */)` placeholders leave a
  closed set's members to the model: such a CHECK matches a generated `IN` CHECK on the same column.
  S6's applied DDL (`s6.ddl`), the tested form D3 grew from, is compared too: each difference from
  S6 is either a D3 revision the generated form follows, or a recorded D3 residue item.
- **Projection.** Per table: columns (type, NOT NULL, default, order); the set of constraints, names
  ignored and `IN` lists as sets; indexes by name (unique, `USING`, parameters with `DESC`, `WITH`,
  `WHERE`). Raw AST equality is not used: the generated DDL names every constraint and writes it
  at table level, D3 inline and unnamed.
- **Residue.** `data/port_residue.json` lists every difference from D3 with its reason; the check
  fails on an unlisted difference and on a listed one that no longer occurs.
- **Queries.** `pglast.visitors.referenced_relations` over D3 §5's and §9's queries
  (`data/d3_queries.sql`) names only tables and views of `MetaData`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pglast
import pytest
from pglast import ast, enums
from pglast.stream import RawStream
from pglast.visitors import Visitor, referenced_relations
from sqlalchemy import MetaData, create_mock_engine

from corpus_structure.core.db import legacy_metadata as db

DATA = Path(__file__).resolve().parent / "data"
REPO = Path(__file__).resolve().parents[4]
S6_DDL = REPO / "docs/design_review/evidence/2026-10-28_design-spikes/code/s6_ddl_applied.sql"
GENERATED = "'<generated>'"
PLACEHOLDER = re.compile(r"IN\s*\(\s*/\*.*?\*/\s*\)", re.S)


# --- Normalized projection --------------------------------------------------------------------


class _SortIn(Visitor):
    """IN lists are sets: sort their items so member order is not a difference."""

    def visit_A_Expr(self, ancestors: Any, node: Any) -> Any:
        if node.kind == enums.A_Expr_Kind.AEXPR_IN and isinstance(node.rexpr, tuple):
            items = tuple(sorted(node.rexpr, key=lambda n: RawStream()(n)))
            return ast.A_Expr(kind=node.kind, name=node.name, lexpr=node.lexpr, rexpr=items)
        return None


def dep(node: Any) -> str | None:
    if node is None:
        return None
    new = _SortIn()(node)
    return RawStream()(new if new is not None else node)


def relname(rv: Any) -> str:
    return f"{rv.schemaname}.{rv.relname}" if rv.schemaname else rv.relname


def typename(tn: Any) -> str:
    names = [n.sval for n in tn.names if n.sval != "pg_catalog"]
    mods = f"({','.join(str(dep(m)) for m in tn.typmods)})" if tn.typmods else ""
    return ".".join(names) + mods + ("[]" * len(tn.arrayBounds or ()))


FK_ACTION = {"a": None, "c": "CASCADE", "r": "RESTRICT", "n": "SET NULL", "d": "SET DEFAULT"}


def constraint(c: Any, colname: str | None) -> tuple | None:
    """A table-level normalized constraint, or None for a column attribute (NOT NULL, DEFAULT)."""
    ct = c.contype

    def cols(keys: Any) -> tuple:
        return tuple(k.sval for k in keys) if keys else ((colname,) if colname else ())

    if ct == enums.ConstrType.CONSTR_PRIMARY:
        return ("primary key", cols(c.keys))
    if ct == enums.ConstrType.CONSTR_UNIQUE:
        return ("unique", cols(c.keys))
    if ct == enums.ConstrType.CONSTR_CHECK:
        return ("check", dep(c.raw_expr))
    if ct == enums.ConstrType.CONSTR_FOREIGN:
        ref = tuple(k.sval for k in c.pk_attrs) if c.pk_attrs else ("id",)  # every bare target: id
        return (
            "foreign key",
            cols(c.fk_attrs),
            relname(c.pktable),
            ref,
            FK_ACTION[c.fk_del_action],
        )
    return None


def project(sql: str) -> dict[str, dict]:
    tables: dict[str, dict] = {}
    for raw in pglast.parse_sql(sql):
        s: Any = raw.stmt  # pglast's node fields are optional in its stubs: branch by name
        kind = type(s).__name__
        if kind == "CreateStmt":
            cols: dict[str, dict] = {}
            cons: set[tuple] = set()
            order: list[str] = []
            pk_cols: set[str] = set()
            for el in s.tableElts:
                if isinstance(el, ast.ColumnDef):
                    name = str(el.colname)
                    order.append(name)
                    notnull, default = False, None
                    for c in el.constraints or ():
                        if c.contype == enums.ConstrType.CONSTR_NOTNULL:
                            notnull = True
                        elif c.contype == enums.ConstrType.CONSTR_DEFAULT:
                            default = dep(c.raw_expr)
                        elif c.contype == enums.ConstrType.CONSTR_IDENTITY:
                            default = (
                                f"identity {'always' if c.generated_when == 'a' else 'by default'}"
                            )
                        elif (n := constraint(c, name)) is not None:
                            cons.add(n)
                            if n[0] == "primary key":
                                pk_cols |= set(n[1])
                    cols[name] = {
                        "type": typename(el.typeName),
                        "not_null": notnull,
                        "default": default,
                    }
                elif isinstance(el, ast.Constraint) and (n := constraint(el, None)) is not None:
                    cons.add(n)
                    if n[0] == "primary key":
                        pk_cols |= set(n[1])
            for name in pk_cols:  # a primary key column is NOT NULL
                cols[name]["not_null"] = True
            tables[relname(s.relation)] = {
                "columns": cols,
                "order": order,
                "constraints": cons,
                "indexes": {},
            }
        elif kind == "AlterTableStmt":
            for cmd in s.cmds:
                if cmd.subtype == enums.AlterTableType.AT_AddConstraint:
                    n = constraint(cmd.def_, None)
                    if n is not None:
                        tables[relname(s.relation)]["constraints"].add(n)
        elif kind == "IndexStmt":
            params = []
            for p in s.indexParams:
                e = str(p.name or dep(p.expr))
                if p.opclass:
                    e += " " + ".".join(n.sval for n in p.opclass)
                if p.ordering == enums.SortByDir.SORTBY_DESC:
                    e += " DESC"
                params.append(e)
            tables[relname(s.relation)]["indexes"][s.idxname] = {
                "unique": bool(s.unique),
                "using": s.accessMethod or "btree",
                "params": params,
                "with": {o.defname: dep(o.arg) for o in s.options or ()},
                "where": dep(s.whereClause),
            }
    return tables


def _placeholder_matches(generated: tuple, reference: tuple) -> bool:
    """A reference `col IN ('<generated>')` CHECK matches a generated `col IN (…)` CHECK."""
    if generated[0] != "check" or reference[0] != "check" or generated[1] is None:
        return False
    m = re.fullmatch(rf"(\w+) IN \({re.escape(GENERATED)}\)", reference[1] or "")
    return m is not None and re.fullmatch(rf"{m.group(1)} IN \(.*\)", generated[1]) is not None


def diff(gen: dict, ref: dict, tables: list[str]) -> list[dict]:
    """Every difference of the generated projection from the reference, one item each."""
    out: list[dict] = []
    for t in tables:
        ta, tb = gen.get(t), ref.get(t)
        if ta is None or tb is None:
            out.append(
                {"key": f"{t} table", "generated": ta is not None, "reference": tb is not None}
            )
            continue
        for c in sorted(set(ta["columns"]) | set(tb["columns"])):
            ca, cb = ta["columns"].get(c), tb["columns"].get(c)
            if ca is None or cb is None:
                out.append({"key": f"{t} column {c}", "generated": ca, "reference": cb})
                continue
            for f in ("type", "not_null", "default"):
                if ca[f] != cb[f]:
                    out.append(
                        {"key": f"{t} column {c} {f}", "generated": ca[f], "reference": cb[f]}
                    )
        common = [c for c in ta["order"] if c in tb["columns"]]
        if common != [c for c in tb["order"] if c in ta["columns"]]:
            out.append(
                {"key": f"{t} column order", "generated": ta["order"], "reference": tb["order"]}
            )
        only_a, only_b = (
            ta["constraints"] - tb["constraints"],
            tb["constraints"] - ta["constraints"],
        )
        for b in list(only_b):
            match = next((a for a in only_a if _placeholder_matches(a, b)), None)
            if match is not None:
                only_a.discard(match)
                only_b.discard(b)
        for k in sorted(only_a, key=str):
            out.append({"key": f"{t} only generated {k[0]} {k[1]}", "generated": list(k)})
        for k in sorted(only_b, key=str):
            out.append({"key": f"{t} only reference {k[0]} {k[1]}", "reference": list(k)})
        for i in sorted(set(ta["indexes"]) | set(tb["indexes"])):
            ia, ib = ta["indexes"].get(i), tb["indexes"].get(i)
            if ia is None or ib is None:
                out.append({"key": f"{t} index {i}", "generated": ia, "reference": ib})
                continue
            for f in ("unique", "using", "params", "with", "where"):
                if ia[f] != ib[f]:
                    out.append(
                        {"key": f"{t} index {i} {f}", "generated": ia[f], "reference": ib[f]}
                    )
    return out


# --- The generated and reference DDL ----------------------------------------------------------


def generated_ddl(metadata: MetaData = db.metadata) -> str:
    """Every statement `create_all` emits for the dialect, views and events included."""
    out: list[str] = []

    def dump(sql: Any, *args: Any, **kw: Any) -> None:
        out.append(str(sql.compile(dialect=engine.dialect)).strip().rstrip(";") + ";")

    engine = create_mock_engine("postgresql+psycopg://", dump)
    metadata.create_all(engine, checkfirst=False)
    return "\n\n".join(out) + "\n"


def d3_ddl() -> str:
    return PLACEHOLDER.sub(f"IN ({GENERATED})", (DATA / "d3_ddl.sql").read_text(encoding="utf-8"))


def table_names(sql: str) -> list[str]:
    return [
        relname(r.stmt.relation)
        for r in pglast.parse_sql(sql)
        if isinstance(r.stmt, ast.CreateStmt)
    ]


def residue_fixture() -> dict[str, str]:
    return json.loads((DATA / "port_residue.json").read_text(encoding="utf-8"))["residue"]


@pytest.fixture(scope="module")
def projections() -> tuple[dict, dict, list[str]]:
    ref_sql = d3_ddl()
    return project(generated_ddl()), project(ref_sql), table_names(ref_sql)


# --- Tests ------------------------------------------------------------------------------------


def test_every_d3_table_is_generated(projections: tuple[dict, dict, list[str]]) -> None:
    gen, _, tables = projections
    assert len(tables) == 48  # every table D3 renders (§3-§8), kb.embedding included
    tables_only = set(gen) - {v.fullname for v in db.OVERLAY.views}
    assert sorted(tables_only ^ set(tables)) == []


def test_the_residue_against_d3_is_the_recorded_one(
    projections: tuple[dict, dict, list[str]],
) -> None:
    gen, ref, tables = projections
    found = {item["key"]: item for item in diff(gen, ref, tables)}
    recorded = residue_fixture()
    unrecorded = {k: v for k, v in found.items() if k not in recorded}
    stale = sorted(set(recorded) - set(found))
    assert unrecorded == {}, json.dumps(unrecorded, indent=1, default=str)
    assert stale == []
    assert all(reason.strip() for reason in recorded.values())


def _as_placeholder(key: str) -> str:
    """A generated-only `IN` CHECK's key as D3's placeholder CHECK on the same column."""
    return re.sub(r"(only generated check \w+ IN )\(.*\)$", rf"\1({GENERATED})", key)


def test_s6_differences_are_d3_revisions_or_recorded_residue(
    projections: tuple[dict, dict, list[str]],
) -> None:
    """S6's tested DDL carries over: where the generated form differs from S6, D3 differs from S6
    in the same way (a revision D3 made after S6, which the generated form follows), or the item is
    recorded D3 residue."""
    gen, d3, _ = projections
    s6 = project(S6_DDL.read_text(encoding="utf-8"))
    common = [t for t in s6 if t in d3]
    assert len(common) >= 40
    revised = {i["key"]: i for i in diff(d3, s6, common)}
    recorded = set(residue_fixture())
    unexplained = []
    for item in diff(gen, s6, common):
        d3_item = revised.get(item["key"]) or revised.get(_as_placeholder(item["key"]))
        same_revision = d3_item is not None and (
            d3_item.get("generated") == item.get("generated") or d3_item["key"] != item["key"]
        )
        if not same_revision and item["key"] not in recorded:
            unexplained.append(item)
    assert unexplained == [], json.dumps(unexplained, indent=1, default=str)


SEEDED = {
    "column type": ("depth INTEGER NOT NULL", "depth BIGINT NOT NULL"),
    "nullability": ("corpus_hash TEXT NOT NULL", "corpus_hash TEXT"),
    "default": ("DEFAULT 3 NOT NULL", "DEFAULT 4 NOT NULL"),
    "check member": ("'agent_asserted'", "'agent'"),
    "fk action": (
        "REFERENCES kb.rendition (id) ON DELETE CASCADE",
        "REFERENCES kb.rendition (id)",
    ),
    "index using": ("USING bm25", "USING gin"),
    "index with": ("text_config = 'english'", "text_config = 'simple'"),
    "index where": ("WHERE status = 'running'", "WHERE status = 'pending'"),
    "index desc": (
        "priority DESC, id) WHERE status = 'awaiting_agent'",
        "priority, id) WHERE status = 'awaiting_agent'",
    ),
}


@pytest.mark.parametrize("name", sorted(SEEDED))
def test_the_comparator_sees_each_dimension(
    name: str, projections: tuple[dict, dict, list[str]]
) -> None:
    gen_sql = generated_ddl()
    old, new = SEEDED[name]
    assert gen_sql.count(old) >= 1, f"seed {name!r} does not apply"
    _, ref, tables = projections
    base = {i["key"] for i in diff(project(gen_sql), ref, tables)}
    seeded = {i["key"] for i in diff(project(gen_sql.replace(old, new, 1)), ref, tables)}
    assert seeded - base


def test_d3_queries_name_only_metadata_tables() -> None:
    known = set(db.metadata.tables)
    text = (DATA / "d3_queries.sql").read_text(encoding="utf-8")
    text = re.sub(r"(?<!:):([a-z_]+)", "$1", text)  # bind parameters, not casts
    statements = [s for s in pglast.split(text) if s.strip()]
    assert len(statements) == 7
    named: set[str] = set()
    for statement in statements:
        named |= set(referenced_relations(statement))
    assert named
    assert sorted(named - known) == []
