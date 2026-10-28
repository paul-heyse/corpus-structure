"""S6 shared database helpers (throwaway spike code).

The cluster is the project-local PG18 cluster (``just db-up``; ``bash scripts/local_pg.sh url``:
socket under ``build/pg/run``, port 5440, ``shared_preload_libraries = pg_textsearch``, peer
authentication, the developer its superuser); the system cluster is never touched. Connection
defaults come from ``PGHOST``/``PGPORT`` when set, else that socket. Roles:

- the superuser of that environment (``PGUSER``) creates the template database ``cs_template``
  with ``vector`` and ``pg_textsearch`` (D3 §3 provisioning, done once by the operator);
- ``cs_s6_app``, a NOLOGIN non-superuser with CREATEDB, owns ``cs_spike_s6`` and applies the DDL,
  as the product's role would. Peer authentication admits only the OS user's role, so the
  application connection logs in as the superuser and runs ``SET ROLE cs_s6_app``; from then on
  every privilege check is the application role's (``current_user``).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path

import psycopg

CODE = Path(__file__).resolve().parent
EVIDENCE = CODE.parent
RESULTS = EVIDENCE / "results" / "s6"
DB = "cs_spike_s6"
TEMPLATE = "cs_template"
APP_ROLE = "cs_s6_app"
REPO = EVIDENCE.parents[3]
os.environ.setdefault("PGHOST", str(REPO / "build" / "pg" / "run"))
os.environ.setdefault("PGPORT", "5440")


def admin(dbname: str = "postgres", **kw) -> psycopg.Connection:
    return psycopg.connect(dbname=dbname, autocommit=True, **kw)


def app(dbname: str = DB, autocommit: bool = False, **kw) -> psycopg.Connection:
    c = psycopg.connect(dbname=dbname, autocommit=True, **kw)
    c.execute(f"SET ROLE {APP_ROLE}")
    c.autocommit = autocommit
    return c


def ensure_role() -> None:
    with admin() as c:
        if not c.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (APP_ROLE,)).fetchone():
            c.execute(f"CREATE ROLE {APP_ROLE} NOLOGIN CREATEDB NOSUPERUSER")


def ensure_template() -> dict:
    """D3 §3: the template database with both extensions, created by the superuser."""
    ensure_role()
    with admin() as c:
        if not c.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TEMPLATE,)).fetchone():
            c.execute(f"CREATE DATABASE {TEMPLATE} OWNER {APP_ROLE}")
            with admin(TEMPLATE) as t:
                t.execute("CREATE EXTENSION vector")
                t.execute("CREATE EXTENSION pg_textsearch")
            c.execute(f"ALTER DATABASE {TEMPLATE} IS_TEMPLATE true")
    with admin(TEMPLATE) as t:
        return dict(t.execute("SELECT extname, extversion FROM pg_extension ORDER BY 1").fetchall())


def recreate_db(name: str = DB) -> None:
    """A fresh database cloned from the template, owned by the application role (as `ci db init`)."""
    ensure_template()
    with admin() as c:
        c.execute(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)")
    # cloned by the application role itself: a CREATEDB role may clone an IS_TEMPLATE database
    with app("postgres", autocommit=True) as c:
        c.execute(f"CREATE DATABASE {name} TEMPLATE {TEMPLATE}")


def drop_db(name: str) -> None:
    with admin() as c:
        c.execute(f"DROP DATABASE IF EXISTS {name} WITH (FORCE)")


def split_sql(sql: str) -> list[str]:
    """Split a script into statements, respecting quotes, dollar quotes and comments."""
    out, buf, i, n = [], [], 0, len(sql)
    while i < n:
        ch = sql[i]
        if sql.startswith("--", i):
            j = sql.find("\n", i)
            j = n if j < 0 else j
            buf.append(sql[i:j])
            i = j
            continue
        if ch == "'":
            j = i + 1
            while j < n:
                if sql[j] == "'" and (j + 1 >= n or sql[j + 1] != "'"):
                    break
                j += 2 if sql[j] == "'" else 1
            buf.append(sql[i : j + 1])
            i = j + 1
            continue
        m = re.match(r"\$[A-Za-z_]*\$", sql[i:])
        if m:
            tag = m.group(0)
            j = sql.find(tag, i + len(tag))
            buf.append(sql[i : j + len(tag)])
            i = j + len(tag)
            continue
        if ch == ";":
            stmt = "".join(buf).strip()
            if re.sub(r"--[^\n]*", "", stmt).strip():
                out.append(stmt)
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    tail = re.sub(r"--[^\n]*", "", "".join(buf)).strip()
    if tail:
        out.append("".join(buf).strip())
    return out


def server_facts() -> dict:
    with admin() as c:
        facts = {
            "version": c.execute("SELECT version()").fetchone()[0],
            "settings": dict(
                c.execute(
                    "SELECT name, setting || coalesce(unit, '') FROM pg_settings WHERE name = ANY(%s) ORDER BY 1",
                    (["shared_preload_libraries", "maintenance_work_mem", "work_mem", "shared_buffers", "max_wal_size",
                      "io_method", "default_text_search_config", "port", "data_directory", "max_parallel_maintenance_workers",
                      "jit"],),
                ).fetchall()
            ),
            "available_extensions": dict(
                c.execute("SELECT name, default_version FROM pg_available_extensions WHERE name IN ('vector','pg_textsearch')").fetchall()
            ),
        }
    facts["cluster"] = "project-local PG18 cluster (just db-up, scripts/local_pg.sh; socket build/pg/run, port 5440; pg_textsearch preloaded; developer superuser); system cluster on 5432 untouched"
    facts["df_root"] = subprocess.run(["df", "-h", "/"], capture_output=True, text=True).stdout.strip().splitlines()[-1]
    facts["at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    return facts


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=str) + "\n")


def env_note() -> str:
    return f"PGHOST={os.environ.get('PGHOST')} PGPORT={os.environ.get('PGPORT')}"
