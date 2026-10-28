"""Copy of S6's ``code/s6a_ddl.py`` (design-spikes, 2026-10-28) for probe Q-4: unchanged; only ``apply`` is used. Original docstring follows.

S6-A (brief steps 1–2): database, extensions, and the extracted D3 DDL applied as a non-superuser.

    uv run python code/s6a_ddl.py   # project-local cluster (just db-up) [--sql code/s6_ddl.sql]

1. Server facts and free disk space; ``cs_template`` with ``vector`` and ``pg_textsearch`` created
   by the superuser (D3 §3); ``cs_spike_s6`` cloned from it by ``cs_s6_app`` (CREATEDB, not superuser).
2. The D3 §3 premises: ``CREATE EXTENSION`` as ``cs_s6_app`` fails (neither extension is trusted), and
   the migration's assertion block raises its instruction in a database cloned from ``template0``.
3. The DDL applied statement by statement as ``cs_s6_app``, each under a savepoint, so every failing
   statement is seen, not only the first. ``--sql`` selects the verbatim extract (to see D3's
   errors) or the applied copy (default).
Writes ``results/s6/ddl_apply.json`` (one file per ``--sql`` choice, suffixed).
"""

from __future__ import annotations

import argparse
import time

import psycopg

from s6_db import CODE, DB, RESULTS, admin, app, drop_db, recreate_db, server_facts, split_sql, write_json


def premises() -> dict:
    out = {}
    noext = "cs_s6_noext"
    drop_db(noext)
    with app("postgres", autocommit=True) as c:
        c.execute(f"CREATE DATABASE {noext} TEMPLATE template0")
    with app(noext, autocommit=True) as c:
        for ext in ("vector", "pg_textsearch"):
            try:
                c.execute(f"CREATE EXTENSION {ext}")
                out[f"create_extension_{ext}_as_app"] = "succeeded (unexpected)"
            except psycopg.Error as e:
                out[f"create_extension_{ext}_as_app"] = f"{e.sqlstate}: {e.diag.message_primary}"
        assertion = split_sql((CODE / "s6_ddl.sql").read_text())[0]
        assert assertion.lstrip().upper().startswith("-- D3") or "DO $$" in assertion
        try:
            c.execute(assertion)
            out["assertion_without_extension"] = "no error (unexpected)"
        except psycopg.Error as e:
            out["assertion_without_extension"] = f"{e.sqlstate}: {e.diag.message_primary}"
    drop_db(noext)
    return out


def apply(sql_path) -> dict:
    stmts = split_sql(sql_path.read_text())
    errors, t0 = [], time.perf_counter()
    with app() as c:
        for i, s in enumerate(stmts):
            try:
                with c.transaction():
                    c.execute(s)
            except psycopg.Error as e:
                first = next((ln for ln in s.splitlines() if ln.strip() and not ln.strip().startswith("--")), "")
                errors.append({"index": i, "statement": first.strip()[:160], "sqlstate": e.sqlstate,
                               "message": e.diag.message_primary, "detail": e.diag.message_detail, "hint": e.diag.message_hint})
        c.commit()
        ms = (time.perf_counter() - t0) * 1000
        cat = {
            "tables": c.execute("SELECT count(*) FROM pg_tables WHERE schemaname IN ('meta','kb','ops','eval')").fetchone()[0],
            "views": c.execute("SELECT count(*) FROM pg_views WHERE schemaname IN ('meta','kb','ops','eval')").fetchone()[0],
            "indexes": c.execute("SELECT count(*) FROM pg_indexes WHERE schemaname IN ('meta','kb','ops','eval')").fetchone()[0],
            "constraints_by_type": dict(c.execute(
                "SELECT contype, count(*) FROM pg_constraint co JOIN pg_namespace n ON n.oid = co.connamespace "
                "WHERE n.nspname IN ('meta','kb','ops','eval') GROUP BY 1 ORDER BY 1").fetchall()),
            "bm25_index": c.execute("SELECT pg_get_indexdef('kb.segment_bm25'::regclass)").fetchone()[0] if not any(
                "segment_bm25" in e["statement"] for e in errors) else None,
            "owner_is_superuser": c.execute("SELECT rolsuper FROM pg_roles WHERE rolname = current_user").fetchone()[0],
        }
    return {"sql": str(sql_path.relative_to(CODE.parent)), "statements": len(stmts), "errors": errors, "ms": round(ms, 1), "catalog": cat}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sql", default="s6_ddl_applied.sql")
    a = ap.parse_args()
    facts = server_facts()
    recreate_db(DB)
    with admin(DB) as c:
        facts["extensions"] = dict(c.execute("SELECT extname, extversion FROM pg_extension ORDER BY 1").fetchall())
    facts["premises"] = premises()
    facts["apply"] = apply(CODE / a.sql)
    suffix = "" if a.sql == "s6_ddl_applied.sql" else "_" + a.sql.removesuffix(".sql")
    write_json(RESULTS / f"ddl_apply{suffix}.json", facts)
    print(facts["apply"]["statements"], "statements;", len(facts["apply"]["errors"]), "errors")
    for e in facts["apply"]["errors"]:
        print(" ", e)
    print(facts["premises"])
    return 0 if not facts["apply"]["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
