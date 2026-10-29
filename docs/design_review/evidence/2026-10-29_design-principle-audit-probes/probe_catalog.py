"""Read-only catalog probe for the design-principle audit (throwaway database on 5434).

P1: at the semantic head revision, what does each restricted principal hold?
  - table privileges per role on every table in the semantic schemas, plus table ownership;
  - functions: SECURITY DEFINER, proconfig (search_path), owner and EXECUTE per role;
  - non-internal triggers per table, and which tables have UPDATE/DELETE/TRUNCATE refusal triggers;
  - database-level TEMP per role, role attributes and memberships (including SET option);
  - default privileges.
P2: can corpus_sem_publisher INSERT into sem.* (the `ci regenerate` persist path sets that role)?
    Answered from P1's has_table_privilege rows, which account for ownership and membership.

The database is created from the configured template, upgraded through the existing
`semantic.migrations.upgrade` route, inspected read-only, then dropped.
"""

from __future__ import annotations

import json
import os
import sys
import time
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.pool import NullPool

from corpus_structure.core.db import extensions
from corpus_structure.semantic.migrations import current_revision, head_revision, upgrade
from corpus_structure.semantic.runtime import connection_settings
from corpus_structure.settings import Settings

ROLES = ("corpus_sem_publisher", "corpus_sem_writer", "corpus_sem_reader", "corpus_sem_evaluator")
SCHEMAS = ("sem", "data", "ops", "eval", "kb")
PRIVS = ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE")
out: dict[str, object] = {}
settings = Settings()
admin = create_engine(connection_settings(settings, "maintenance").database.sqlalchemy_url, poolclass=NullPool)
server = create_engine(admin.url.set(database="postgres"), poolclass=NullPool)
quote = server.dialect.identifier_preparer.quote
db = f"cs_sem_probe_{os.getpid()}_{uuid4().hex[:8]}_a"
created = False


def drop() -> None:
    for attempt in range(40):
        try:
            with server.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                conn.exec_driver_sql(f"DROP DATABASE IF EXISTS {quote(db)}")
            return
        except DBAPIError as exc:
            if getattr(exc.orig, "sqlstate", None) != "55006" or attempt == 39:
                raise
            time.sleep(0.05)


def rows(conn, sql: str, **params) -> list[dict]:
    return [dict(r) for r in conn.execute(text(sql), params).mappings()]


try:
    with server.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        conn.exec_driver_sql(f"CREATE DATABASE {quote(db)} TEMPLATE {quote(settings.database.template)}")
        created = True
    engine = create_engine(admin.url.set(database=db), poolclass=NullPool)
    try:
        with engine.begin() as conn:
            upgrade(conn)
        with engine.connect() as conn:
            out["head"] = head_revision()
            out["current"] = current_revision(conn)
            out["server_version"] = conn.execute(text("SHOW server_version")).scalar_one()
            out["login"] = conn.execute(text("SELECT current_user")).scalar_one()
            tables = rows(conn, """
                SELECT n.nspname AS schema, c.relname AS name, pg_get_userbyid(c.relowner) AS owner
                FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE c.relkind IN ('r','p') AND n.nspname = ANY(:s) ORDER BY 1,2""", s=list(SCHEMAS))
            for t in tables:
                q = f"{t['schema']}.{t['name']}"
                t["privileges"] = {
                    r: [p for p in PRIVS if conn.execute(text("SELECT has_table_privilege(:r,:q,:p)"), {"r": r, "q": q, "p": p}).scalar_one()]
                    for r in ROLES
                }
                t["triggers"] = rows(conn, """
                    SELECT tgname AS name, tgenabled::text AS enabled,
                           (tgtype & 2)>0 AS before, (tgtype & 4)>0 AS ins, (tgtype & 8)>0 AS del,
                           (tgtype & 16)>0 AS upd, (tgtype & 32)>0 AS trunc, tgfoid::regprocedure::text AS function
                    FROM pg_trigger WHERE tgrelid = CAST(:q AS regclass) AND NOT tgisinternal ORDER BY 1""", q=q)
                t["refuses"] = {
                    k: any(tr["before"] and tr[k] for tr in t["triggers"]) for k in ("upd", "del", "trunc")
                }
            out["tables"] = tables
            funcs = rows(conn, """
                SELECT n.nspname AS schema, p.proname AS name, pg_get_function_identity_arguments(p.oid) AS args,
                       p.prosecdef AS security_definer, p.proconfig AS config, pg_get_userbyid(p.proowner) AS owner,
                       p.provolatile::text AS volatility, l.lanname AS language, p.oid::regprocedure::text AS signature
                FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_language l ON l.oid=p.prolang
                WHERE n.nspname = ANY(:s) ORDER BY 1,2,3""", s=list(SCHEMAS))
            for f in funcs:
                f["execute"] = [r for r in ROLES if conn.execute(text("SELECT has_function_privilege(:r,:f,'EXECUTE')"), {"r": r, "f": f["signature"]}).scalar_one()]
                f["public_execute"] = conn.execute(text("SELECT has_function_privilege('public',:f,'EXECUTE')"), {"f": f["signature"]}).scalar_one()
            out["functions"] = funcs
            out["database_temp"] = {r: conn.execute(text("SELECT has_database_privilege(:r, current_database(), 'TEMP')"), {"r": r}).scalar_one() for r in ROLES}
            out["roles"] = rows(conn, """
                SELECT rolname, rolcanlogin, rolsuper, rolinherit, rolbypassrls FROM pg_roles
                WHERE rolname = ANY(:r) OR rolname = current_user ORDER BY 1""", r=list(ROLES))
            out["memberships"] = rows(conn, """
                SELECT r.rolname AS role, m.rolname AS member, am.admin_option, am.inherit_option, am.set_option
                FROM pg_auth_members am JOIN pg_roles r ON r.oid=am.roleid JOIN pg_roles m ON m.oid=am.member
                WHERE r.rolname = ANY(:r) OR m.rolname = ANY(:r) ORDER BY 1,2""", r=list(ROLES))
            out["default_privileges"] = rows(conn, "SELECT pg_get_userbyid(defaclrole) AS role, defaclnamespace::regnamespace::text AS schema, defaclobjtype::text AS objtype, defaclacl::text AS acl FROM pg_default_acl")
            out["schema_privileges"] = {
                s: {r: [p for p in ("USAGE", "CREATE") if conn.execute(text("SELECT has_schema_privilege(:r,:s,:p)"), {"r": r, "s": s, "p": p}).scalar_one()] for r in ROLES}
                for s in SCHEMAS if conn.execute(text("SELECT 1 FROM pg_namespace WHERE nspname=:s"), {"s": s}).first()
            }
    finally:
        engine.dispose()
finally:
    if created:
        drop()
    with server.connect() as conn:
        out["residue"] = conn.execute(text("SELECT count(*) FROM pg_database WHERE datname LIKE 'cs_sem_probe_%'")).scalar_one()
    json.dump(out, sys.stdout, indent=1, default=str)
