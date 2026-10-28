"""Q-3 (P0-M-Q3): generated MetaData plus overlay against S6's applied DDL, through a normalized pglast
projection; then Alembic 1.20 autogenerate with a SQLAlchemy 2.1 CreateView table.

    UV_PROJECT_ENVIRONMENT=$PWD/build/probe-venv uv run --project \
        docs/design_review/evidence/2026-10-28_phase0-model-probes \
        python docs/design_review/evidence/2026-10-28_phase0-model-probes/code/q3_port_check.py

Inputs: code/q3/system_sketch.yaml (LinkML sketch), code/q3/compiler.py, code/q3/overlay.py, and a copy
of S6's applied DDL (results/q3/s6_ddl_applied.sql, copied from the design spikes' code/; S6's own
file is read, never written). Outputs under results/q3/. The database part creates p0q_portcheck on
the 18/corpus cluster (port 5434) from cs_template, and drops it at the end.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pglast
from pglast import ast, enums
from pglast.stream import RawStream
from pglast.visitors import Visitor
from linkml_runtime.utils.schemaview import SchemaView
from sqlalchemy import create_engine, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "q3"))
from compiler import Compiler, search_block_kinds  # noqa: E402
import overlay  # noqa: E402

FOLDER = HERE.parent
REPO = FOLDER.parents[3]
S6_SRC = REPO / "docs/design_review/evidence/2026-10-28_design-spikes/code/s6_ddl_applied.sql"
OUT = FOLDER / "results/q3"
FIVE = ["ops.run", "ops.task", "kb.segment", "kb.claim", "meta.schema_slot"]
ADMIN = "postgresql+psycopg:///postgres?host=/var/run/postgresql&port=5434"
DBNAME = "p0q_portcheck"
DB = f"postgresql+psycopg:///{DBNAME}?host=/var/run/postgresql&port=5434"

# Residue classification, written after reading the first diff (results/q3/residue.json lists every
# item; an item without an entry here is "unclassified" and fails the probe).
CLASSIFY: dict[str, tuple[str, str]] = {
    "kb.segment index segment_bm25 where": (
        "S6 DDL differs by design",
        "D3 revised the BM25 kind list after S6 (D3 §5: caption replaces math_display); the overlay "
        "reads SEARCH_BLOCK from the search_block member property, which follows current D3"),
}

# Strict compile (TM §4 vocabulary only): what the proposed declarations carry. Matched by substring.
NEEDS_DECL = "compiler should carry (declaration missing from TM §4)"
CLASSIFY_STRICT: list[tuple[str, tuple[str, str]]] = [
    ("column created_at default", (NEEDS_DECL,
     "DEFAULT now(): LinkML ifabsent has no now(); the sketch's proposed ci:generated: insert_time carries it")),
    ("column ts_config type", (NEEDS_DECL,
     "regconfig: TM §4 says types carry a projection type but names no annotation; proposed ci:sql_type on the type")),
    ("foreign key ('rendition_id',)", (NEEDS_DECL,
     "ON DELETE CASCADE is deletion semantics (D3 §8 delete order); proposed ci:on_delete on the reference slot")),
    ("foreign key ('run_id',)", (NEEDS_DECL, "ON DELETE CASCADE; proposed ci:on_delete")),
    ("foreign key ('schema_version_id',)", (NEEDS_DECL, "ON DELETE CASCADE; proposed ci:on_delete")),
    ("check (parse_status = 'ok') = (parse_reason IS NULL)", (NEEDS_DECL,
     "TM §4's iff_present(x, y = v) states 'x present iff y = v'; 'absent iff' needs a template "
     "(proposed iff_absent) or negation in the condition")),
]


def classify(key: str, strict: bool) -> tuple[str, str]:
    if key in CLASSIFY:
        return CLASSIFY[key]
    if strict:
        for sub, v in CLASSIFY_STRICT:
            if sub in key:
                return v
    return ("unclassified", "")


# ---------------------------------------------------------------------------------------------
# normalized projection
# ---------------------------------------------------------------------------------------------
class _SortIn(Visitor):
    """IN lists are sets: sort their items so member order is not a difference."""

    def visit_A_Expr(self, ancestors, node):
        if node.kind == enums.A_Expr_Kind.AEXPR_IN and isinstance(node.rexpr, tuple):
            return ast.A_Expr(kind=node.kind, name=node.name, lexpr=node.lexpr,
                              rexpr=tuple(sorted(node.rexpr, key=lambda n: RawStream()(n))))
        return None


def dep(node) -> str | None:
    if node is None:
        return None
    new = _SortIn()(node)
    return RawStream()(new if new is not None else node)


def relname(rv: ast.RangeVar) -> str:
    return f"{rv.schemaname}.{rv.relname}" if rv.schemaname else rv.relname


def typename(tn: ast.TypeName) -> str:
    names = [n.sval for n in tn.names if n.sval != "pg_catalog"]
    mods = f"({','.join(dep(m) for m in tn.typmods)})" if tn.typmods else ""
    return ".".join(names) + mods + ("[]" * len(tn.arrayBounds or ()))


FK_ACTION = {"a": None, "c": "CASCADE", "r": "RESTRICT", "n": "SET NULL", "d": "SET DEFAULT"}


def constraint(c: ast.Constraint, colname: str | None):
    """A table-level normalized constraint, or None for column attributes (NOT NULL, DEFAULT, …)."""
    ct = c.contype
    cols = lambda keys: tuple(k.sval for k in keys) if keys else ((colname,) if colname else ())  # noqa: E731
    if ct == enums.ConstrType.CONSTR_PRIMARY:
        return ("primary key", cols(c.keys))
    if ct == enums.ConstrType.CONSTR_UNIQUE:
        return ("unique", cols(c.keys))
    if ct == enums.ConstrType.CONSTR_CHECK:
        return ("check", dep(c.raw_expr))
    if ct == enums.ConstrType.CONSTR_FOREIGN:
        ref = tuple(k.sval for k in c.pk_attrs) if c.pk_attrs else ("id",)  # every target here has PK id
        return ("foreign key", cols(c.fk_attrs), relname(c.pktable), ref, FK_ACTION[c.fk_del_action],
                FK_ACTION[c.fk_upd_action])
    return None


def project(stmts) -> dict:
    tables: dict[str, dict] = {}
    names: dict[str, list] = {}
    for raw in stmts:
        s = raw.stmt
        if isinstance(s, ast.CreateStmt):
            name = relname(s.relation)
            if name not in FIVE:
                continue
            cols, cons, order, pk_cols, cnames = {}, set(), [], set(), []
            for el in s.tableElts:
                if isinstance(el, ast.ColumnDef):
                    order.append(el.colname)
                    notnull, default = False, None
                    for c in el.constraints or ():
                        if c.contype == enums.ConstrType.CONSTR_NOTNULL:
                            notnull = True
                        elif c.contype == enums.ConstrType.CONSTR_DEFAULT:
                            default = dep(c.raw_expr)
                        elif c.contype == enums.ConstrType.CONSTR_IDENTITY:
                            default = f"identity {'always' if c.generated_when == 'a' else 'by default'}"
                        else:
                            n = constraint(c, el.colname)
                            if n:
                                cons.add(n)
                                cnames.append(c.conname)
                                if n[0] == "primary key":
                                    pk_cols |= set(n[1])
                    cols[el.colname] = {"type": typename(el.typeName), "not_null": notnull, "default": default}
                elif isinstance(el, ast.Constraint):
                    n = constraint(el, None)
                    if n:
                        cons.add(n)
                        cnames.append(el.conname)
                        if n[0] == "primary key":
                            pk_cols |= set(n[1])
            for cn in pk_cols:  # a primary key column is NOT NULL
                cols[cn]["not_null"] = True
            tables[name] = {"columns": cols, "order": order, "constraints": cons, "indexes": {}}
            names[name] = cnames
        elif isinstance(s, ast.AlterTableStmt) and relname(s.relation) in FIVE:
            for cmd in s.cmds:
                if cmd.subtype == enums.AlterTableType.AT_AddConstraint:
                    tables[relname(s.relation)]["constraints"].add(constraint(cmd.def_, None))
        elif isinstance(s, ast.IndexStmt) and relname(s.relation) in FIVE:
            params = []
            for p in s.indexParams:
                e = p.name or dep(p.expr)
                if p.ordering == enums.SortByDir.SORTBY_DESC:
                    e += " DESC"
                params.append(e)
            tables[relname(s.relation)]["indexes"][s.idxname] = {
                "unique": bool(s.unique), "using": s.accessMethod or "btree", "params": params,
                "with": {o.defname: dep(o.arg) for o in s.options or ()}, "where": dep(s.whereClause)}
    return {"tables": tables, "constraint_names": names}


def diff(a: dict, b: dict, strict: bool = False) -> list[dict]:
    """Residue of generated (a) against S6 (b), one item per difference."""
    out = []
    for t in FIVE:
        ta, tb = a["tables"].get(t), b["tables"].get(t)
        if ta is None or tb is None:
            out.append({"key": f"{t} table", "generated": bool(ta), "s6": bool(tb)})
            continue
        for c in sorted(set(ta["columns"]) | set(tb["columns"])):
            ca, cb = ta["columns"].get(c), tb["columns"].get(c)
            if ca is None or cb is None:
                out.append({"key": f"{t} column {c}", "generated": ca, "s6": cb})
                continue
            for f in ("type", "not_null", "default"):
                if ca[f] != cb[f]:
                    out.append({"key": f"{t} column {c} {f}", "generated": ca[f], "s6": cb[f]})
        if ta["order"] != tb["order"]:
            out.append({"key": f"{t} column order", "generated": ta["order"], "s6": tb["order"]})
        for k in sorted(ta["constraints"] - tb["constraints"], key=str):
            out.append({"key": f"{t} constraint only generated {k[0]} {k[1]}", "generated": list(k), "s6": None})
        for k in sorted(tb["constraints"] - ta["constraints"], key=str):
            out.append({"key": f"{t} constraint only s6 {k[0]} {k[1]}", "generated": None, "s6": list(k)})
        for i in sorted(set(ta["indexes"]) | set(tb["indexes"])):
            ia, ib = ta["indexes"].get(i), tb["indexes"].get(i)
            if ia is None or ib is None:
                out.append({"key": f"{t} index {i}", "generated": ia, "s6": ib})
                continue
            for f in ("unique", "using", "params", "with", "where"):
                if ia[f] != ib[f]:
                    out.append({"key": f"{t} index {i} {f}", "generated": ia[f], "s6": ib[f]})
    for it in out:
        cls, why = classify(it["key"], strict)
        it["class"], it["reason"] = cls, why
    return out


def jsonable(p: dict) -> dict:
    return {t: {**v, "constraints": sorted([list(x) for x in v["constraints"]], key=str)} for t, v in p["tables"].items()}


# ---------------------------------------------------------------------------------------------
# generation
# ---------------------------------------------------------------------------------------------
def generate(mark_info: bool = False, with_view: bool = False, strict: bool = False):
    sv = SchemaView(str(HERE / "q3/system_sketch.yaml"))
    comp = Compiler(sv, strict=strict)
    md = comp.compile()
    sb = search_block_kinds(sv)
    idx = overlay.apply(md, sb)
    view = overlay.add_view(md, mark_info) if with_view else None
    generate.skipped = comp.skipped
    return sv, md, idx, sb, view


# Seeded differences: each must produce at least one residue item (the comparator is not blind).
CONTROLS = {
    "column type": ("depth INTEGER NOT NULL", "depth BIGINT NOT NULL"),
    "nullability": ("corpus_hash TEXT NOT NULL", "corpus_hash TEXT"),
    "default": ("iteration_limit INTEGER DEFAULT 3 NOT NULL", "iteration_limit INTEGER DEFAULT 4 NOT NULL"),
    "check member": ("'agent_asserted'", "'agent'"),
    "fk action": ("REFERENCES ops.run (id) ON DELETE CASCADE", "REFERENCES ops.run (id)"),
    "unique": ("CONSTRAINT uq_segment_key UNIQUE (key), ", ""),
    "index using": ("USING bm25", "USING gin"),
    "index with": ("text_config = 'english'", "text_config = 'simple'"),
    "index where": ("WHERE status = 'running'", "WHERE status = 'pending'"),
    "index desc": ("priority DESC, id) WHERE status = 'awaiting_agent'", "priority, id) WHERE status = 'awaiting_agent'"),
}


def controls(gen_sql: str, s6: dict, baseline: list[dict]) -> dict:
    base = {x["key"] for x in baseline}
    out = {}
    for name, (old, new) in CONTROLS.items():
        if gen_sql.count(old) != 1:
            out[name] = {"applied": False, "occurrences": gen_sql.count(old)}
            continue
        r = diff(project(pglast.parse_sql(gen_sql.replace(old, new))), s6)
        new_keys = sorted({x["key"] for x in r} - base)
        out[name] = {"applied": True, "detected": bool(new_keys), "new_items": new_keys}
    return out


def ddl_text(md, idx, tables) -> str:
    d = postgresql.dialect()
    parts = [str(CreateTable(md.tables[t]).compile(dialect=d)).strip() + ";" for t in tables]
    parts += [str(CreateIndex(i).compile(dialect=d)).strip() + ";" for i in idx if i.table.fullname in tables]
    return "\n\n".join(parts) + "\n"


# ---------------------------------------------------------------------------------------------
# database: apply, then Alembic autogenerate with a view
# ---------------------------------------------------------------------------------------------
def database() -> dict:
    from alembic.autogenerate import compare_metadata, produce_migrations, render_python_code
    from alembic.migration import MigrationContext

    admin = create_engine(ADMIN, isolation_level="AUTOCOMMIT")
    res: dict = {}
    with admin.connect() as c:
        c.execute(text(f"DROP DATABASE IF EXISTS {DBNAME}"))
        c.execute(text(f"CREATE DATABASE {DBNAME} TEMPLATE cs_template"))
    eng = None
    try:
        eng = create_engine(DB)
        sv, md, idx, sb, view = generate(with_view=True)
        with eng.begin() as conn:
            for s in ("meta", "ops", "kb"):
                conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {s}"))
        md.create_all(eng)
        with eng.connect() as conn:
            res["server_version"] = conn.execute(text("SHOW server_version")).scalar()
            res["extensions"] = dict(conn.execute(text("SELECT extname, extversion FROM pg_extension")).all())
            res["views_in_db"] = [r[0] for r in conn.execute(text(
                "SELECT schemaname||'.'||viewname FROM pg_views WHERE schemaname='ops'"))]
            res["bm25_index_def"] = conn.execute(text(
                "SELECT indexdef FROM pg_indexes WHERE indexname='segment_bm25'")).scalar()
            res["applied_tables"] = sorted(r[0] for r in conn.execute(text(
                "SELECT schemaname||'.'||tablename FROM pg_tables WHERE schemaname IN ('meta','ops','kb')")))
        res["view_table_is_view"] = view.is_view
        res["view_table_info"] = dict(view.info)

        def run(md_, include_object=None, server_default=False) -> dict:
            with eng.connect() as conn:
                opts = {"compare_type": True, "compare_server_default": server_default, "include_schemas": True}
                if include_object:
                    opts["include_object"] = include_object
                mc = MigrationContext.configure(conn, opts=opts)
                diffs = compare_metadata(mc, md_)
                mig = produce_migrations(mc, md_)
                code = render_python_code(mig.upgrade_ops)
            return {"diffs": [repr(d)[:300] for d in diffs], "upgrade_code": code}

        def excl_native(obj, name, type_, reflected, compare_to):
            return not (type_ == "table" and getattr(obj, "is_view", False))

        def excl_info(obj, name, type_, reflected, compare_to):
            return not (type_ == "table" and obj.info.get("is_view"))

        # compare_server_default=True: Alembic compares defaults on the server (SELECT reflected = metadata);
        # recorded separately because the regconfig default makes that comparison fail.
        import warnings
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                res["compare_server_default_true"] = {"result": run(md, server_default=True)}
            except Exception as ex:  # noqa: BLE001
                res["compare_server_default_true"] = {"error": f"{type(ex).__name__}: {str(ex).splitlines()[0]}",
                                                      "sql": str(getattr(ex, "statement", ""))}
        res["reflection_warnings"] = sorted({str(x.message) for x in w})
        res["autogen"] = {
            "no_filter": run(md),
            "include_object_native_is_view": run(md, excl_native),
            "include_object_info_unmarked": run(md, excl_info),
        }
        _, md2, _, _, _ = generate(mark_info=True, with_view=True)
        res["autogen"]["include_object_info_marked"] = run(md2, excl_info)
        # Without the view in the database at all (a first revision): what does autogenerate emit?
        with eng.begin() as conn:
            conn.execute(text("DROP VIEW ops.finished_run"))
        res["autogen"]["view_absent_no_filter"] = run(md)
        res["autogen"]["view_absent_native_is_view"] = run(md, excl_native)
    finally:
        if eng is not None:
            eng.dispose()
        with admin.connect() as c:
            c.execute(text(f"DROP DATABASE IF EXISTS {DBNAME} WITH (FORCE)"))
            res["dropped"] = c.execute(text("SELECT count(*) FROM pg_database WHERE datname=:n"), {"n": DBNAME}).scalar() == 0
        admin.dispose()
    return res


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    s6_copy = OUT / "s6_ddl_applied.sql"
    shutil.copy(S6_SRC, s6_copy)
    sv, md, idx, sb, _ = generate()
    gen_sql = ddl_text(md, idx, FIVE)
    (OUT / "generated.sql").write_text(gen_sql)
    gen = project(pglast.parse_sql(gen_sql))
    s6 = project(pglast.parse_sql(s6_copy.read_text()))
    (OUT / "projection_generated.json").write_text(json.dumps(jsonable(gen), indent=1) + "\n")
    (OUT / "projection_s6.json").write_text(json.dumps(jsonable(s6), indent=1) + "\n")
    residue = diff(gen, s6)
    (OUT / "residue.json").write_text(json.dumps(residue, indent=1, default=str) + "\n")
    ctl = controls(gen_sql, s6, residue)
    _, mds, idxs, _, _ = generate(strict=True)
    strict_sql = ddl_text(mds, idxs, FIVE)
    (OUT / "generated_strict.sql").write_text(strict_sql)
    strict_res = diff(project(pglast.parse_sql(strict_sql)), s6, strict=True)
    (OUT / "residue_strict.json").write_text(json.dumps(strict_res, indent=1, default=str) + "\n")
    counts = {}
    for t in FIVE:
        g = gen["tables"][t]
        counts[t] = {"columns": len(g["columns"]), "constraints": len(g["constraints"]), "indexes": len(g["indexes"])}
    raw_equal = {t: None for t in FIVE}
    summary = {"search_block": sb, "counts": counts, "residue_items": len(residue),
               "by_class": {}, "generated_constraint_names": gen["constraint_names"],
               "raw_ast_equal_note": "raw pglast AST equality is not used: generated DDL names every constraint and "
                                     "writes them table-level, S6 writes them inline and unnamed"}
    del raw_equal
    for r in residue:
        summary["by_class"][r["class"]] = summary["by_class"].get(r["class"], 0) + 1
    summary["controls"] = ctl
    summary["controls_all_detected"] = all(v.get("applied") and v.get("detected") for v in ctl.values())
    summary["strict"] = {"residue_items": len(strict_res), "skipped_invariants": generate.skipped,
                         "by_class": {}}
    for r in strict_res:
        summary["strict"]["by_class"][r["class"]] = summary["strict"]["by_class"].get(r["class"], 0) + 1
    summary["database"] = database()
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, default=str) + "\n")
    for r in residue:
        print(f"[{r['class']}] {r['key']}: generated={r['generated']!r} s6={r['s6']!r}")
    print("strict residue:")
    for r in strict_res:
        print(f"  [{r['class']}] {r['key']}: generated={r['generated']!r} s6={r['s6']!r}")
    print("controls:", {k: v.get("detected") for k, v in ctl.items()})
    print(json.dumps({k: v for k, v in summary.items() if k != "database"}, indent=1, default=str)[:1500])
    db = summary["database"]
    print("db:", db.get("server_version"), "views", db.get("views_in_db"), "dropped", db.get("dropped"))
    for k, v in db["autogen"].items():
        print("autogen", k, v["diffs"])
    ok = ("unclassified" not in summary["by_class"] and "unclassified" not in summary["strict"]["by_class"]
          and summary["controls_all_detected"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
