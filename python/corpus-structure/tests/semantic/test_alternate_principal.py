"""A real alternate reader login on the dedicated local test cluster; owned auth rows unwind."""

import os
import pwd
import re
import subprocess
from uuid import uuid4

from sqlalchemy import text

from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings


def test_alternate_reader_login_and_owner_base(semantic_db_engine):
    endpoint = semantic_db_engine.url
    assert endpoint.host is None and endpoint.query.get("port") == "5434"
    assert endpoint.query.get("host") == "/var/run/postgresql"
    role = "cs_reader_" + uuid4().hex
    database = endpoint.database
    operator = pwd.getpwuid(os.getuid()).pw_name
    assert database is not None
    assert all(re.fullmatch(r"[a-z_][a-z0-9_-]*", name) for name in (role, database, operator))
    conf = "/etc/postgresql/18/corpus/"
    hba = f"local {database} {role} peer map=corpus_semantic"
    ident = f"corpus_semantic {operator} {role}"

    def pg(sql):
        subprocess.run(
            [
                "sudo",
                "-n",
                "-u",
                "postgres",
                "psql",
                "-Xq",
                "-p",
                "5434",
                "-d",
                "postgres",
                "-v",
                "ON_ERROR_STOP=1",
            ],
            input=sql,
            text=True,
            check=True,
            capture_output=True,
        )

    pg(
        f"CREATE ROLE {role} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS; "
        f"GRANT corpus_sem_reader TO {role};"
    )
    try:
        for path, line in ((conf + "semantic_hba.conf", hba), (conf + "pg_ident.conf", ident)):
            subprocess.run(
                ["sudo", "-n", "tee", "-a", path],
                input=line + "\n",
                text=True,
                stdout=subprocess.DEVNULL,
                check=True,
            )
        pg("SELECT pg_reload_conf();")
        base = endpoint.set(drivername="postgresql").render_as_string(hide_password=False)
        settings = Settings(database={"url": base, "reader_url": f"postgresql://{role}@"})
        with (
            open_runtime_engine(settings, purpose="read", timeout=5, max_size=1) as engine,
            engine.connect() as conn,
        ):
            assert conn.execute(text("SELECT current_user,session_user")).one() == (role, role)
        with (
            open_runtime_engine(
                Settings(database={"url": base}), purpose="read", timeout=5, max_size=1
            ) as engine,
            engine.connect() as conn,
        ):
            assert conn.scalar(text("SELECT current_user")) == "corpus_sem_reader"
    finally:
        failures = []
        for path, line in ((conf + "semantic_hba.conf", hba), (conf + "pg_ident.conf", ident)):
            result = subprocess.run(
                ["sudo", "-n", "sed", "-i", f"/^{line}$/d", path], capture_output=True
            )
            if result.returncode:
                failures.append(path)
        try:
            pg("SELECT pg_reload_conf();")
        finally:
            pg(f"DROP ROLE {role};")
        assert not failures, f"owned authentication rows need cleanup: {failures}"
