"""Bounded TA-01 real-clone controls; private setup is confined to pg_virtualenv."""

from __future__ import annotations

import json
import os
import pwd
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import psycopg
from sqlalchemy import text

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "scripts"))

from native_test_support import PgAdmin, SemanticTemplate, principal_engine, server_url
from corpus_structure.settings import Settings


def private_setup() -> Settings:
    port = os.environ["PGPORT"]
    socket = os.environ["TA_SOCKET"]
    operator = pwd.getpwuid(os.getuid()).pw_name
    endpoint = dict(host=socket, port=port, user=operator, dbname="postgres")
    with psycopg.connect(**endpoint, autocommit=True) as conn:
        for role in ("publisher", "writer", "reader", "evaluator", "admitter"):
            name = "corpus_sem_" + role
            conn.execute(
                f"CREATE ROLE {name} {'NOLOGIN' if role == 'publisher' else 'LOGIN'} "
                "NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS"
            )
        conn.execute(f'GRANT corpus_sem_publisher TO "{operator}" WITH INHERIT FALSE, SET TRUE')
        conf = Path(os.environ["PG_CLUSTER_CONF_ROOT"]) / "18/regress"
        ident = conf / "pg_ident.conf"
        with ident.open("a") as stream:
            for role in ("writer", "reader", "evaluator", "admitter"):
                stream.write(f"\nta_native {operator} corpus_sem_{role}\n")
        hba = conf / "pg_hba.conf"
        original = hba.read_text()
        hba.write_text(
            "local all corpus_sem_writer,corpus_sem_reader,corpus_sem_evaluator,corpus_sem_admitter peer map=ta_native\n"
            + original
        )
        conn.execute("SELECT pg_reload_conf()")
        assert conn.execute("SELECT count(*) FROM pg_hba_file_rules WHERE error IS NOT NULL").fetchone() == (0,)
        conn.execute("CREATE DATABASE cs_template")
    with psycopg.connect(**dict(endpoint, dbname="cs_template"), autocommit=True) as conn:
        for line in (REPO / "ops/postgresql/extensions.txt").read_text().splitlines():
            if line and not line.startswith("#"):
                name, version = line.split()
                conn.execute(f"CREATE EXTENSION {name} VERSION '{version}'")
    return Settings(database={
        "url": f"postgresql://corpus_sem_writer@/postgres?host={socket}&port={port}",
        "maintenance_url": f"postgresql://{operator}@",
    })


@contextmanager
def policy_source(server, name):
    with server.database(name, server.template) as engine:
        with engine.begin() as conn:
            conn.exec_driver_sql("CREATE TABLE public.ta_prepared(value integer)")
            conn.exec_driver_sql("INSERT INTO public.ta_prepared VALUES(19)")
        engine.dispose()
        policy = server.policy(name)
        with server.connect() as conn:
            conn.exec_driver_sql(f'ALTER DATABASE "{name}" ALLOW_CONNECTIONS false IS_TEMPLATE false')
        yield SemanticTemplate(name, policy)


def controls(settings: Settings, *, deployed=True) -> dict:
    server = PgAdmin(server_url(settings), settings.database.template, settings=settings)
    extensions = server.check()
    server.check_roles({p: "corpus_sem_" + p for p in ("writer", "reader", "evaluator", "admitter")})
    token = uuid4().hex[:12]
    names = [f"cs_sem_{kind}_{os.getpid()}_{token}" for kind in ("head", "test", "bare")]
    results = {"extensions": extensions, "owned_names": names, "full_current_deployment": deployed}
    source = server.semantic_template(names[0]) if deployed else policy_source(server, names[0])
    with source as template:
        with server.connect() as conn:
            results["head_posture"] = list(conn.execute(text("SELECT datallowconn,datistemplate FROM pg_database WHERE datname=:n"), {"n": names[0]}).one())
        assert results["head_posture"] == [False, False]
        with (
            server.database(names[1], template.name, policy=template.policy) as left,
            server.database(names[2], template.name, policy=template.policy) as right,
        ):
            assert server.policy(names[1]) == server.policy(names[2]) == template.policy
            with left.begin() as conn:
                conn.exec_driver_sql("CREATE TABLE public.ta_isolation(value integer)")
                conn.exec_driver_sql("INSERT INTO public.ta_isolation VALUES(73)")
            with left.connect() as conn:
                assert conn.exec_driver_sql("SELECT value FROM public.ta_isolation").scalar_one() == 73
            with right.connect() as conn:
                assert conn.exec_driver_sql("SELECT to_regclass('public.ta_isolation')").scalar_one() is None
            results["committed_clone_isolation"] = True
            results["purpose_sessions"] = {}
            for purpose, expected in (("write", "writer"), ("read", "reader"), ("evaluate", "evaluator"), ("admit", "admitter")):
                engine = principal_engine(settings, purpose, names[1])
                try:
                    with engine.connect() as conn:
                        actual = list(conn.execute(text("SELECT current_user,session_user")).one())
                        assert actual == ["corpus_sem_" + expected] * 2
                        assert conn.exec_driver_sql("SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolbypassrls FROM pg_roles WHERE rolname=current_user").scalar_one() is False
                        results["purpose_sessions"][purpose] = actual
                finally:
                    engine.dispose()
            with left.connect() as conn:
                if deployed:
                    results["deployment_revision"] = conn.exec_driver_sql("SELECT version_num FROM semantic_alembic_version").scalar_one()
                else:
                    assert conn.exec_driver_sql("SELECT value FROM public.ta_prepared").scalar_one() == 19
            results["policy_replay_equal"] = True
    assert not any(server.exists(name) for name in names)
    results["owned_databases_removed"] = True
    return results


def pgtap(settings: Settings) -> dict:
    url = settings.database.url.replace("corpus_sem_writer@", pwd.getpwuid(os.getuid()).pw_name + "@")
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("CREATE EXTENSION pgtap VERSION '1.3.4'")
        expected = conn.execute("SELECT rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolbypassrls FROM pg_roles WHERE rolname='corpus_sem_reader'").fetchone()
        assert expected == (True, False, False, False, False)
        conn.execute("SELECT plan(2)")
        posture = conn.execute("SELECT results_eq($$SELECT rolcanlogin,rolsuper,rolcreatedb,rolcreaterole,rolbypassrls FROM pg_roles WHERE rolname='corpus_sem_reader'$$,$$SELECT true,false,false,false,false$$,'independent reader posture')").fetchone()[0]
        refusal = conn.execute("SELECT throws_ok('SELECT 1/0','22012','division by zero','exact native rejection')").fetchone()[0]
        assert posture.startswith("ok 1") and refusal.startswith("ok 2")
        assert conn.execute("SELECT * FROM finish()").fetchall() == []
        # Deliberately wrong expected SQLSTATE must yield TAP failure, not a SQL exception.
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("SELECT plan(1)")
        wrong = conn.execute("SELECT throws_ok('SELECT 1/0','23505','division by zero','wrong expected rejection')").fetchone()[0]
        assert wrong.startswith("not ok 1")
    proofs = {}
    for label, state in (("positive", "22012"), ("negative", "23505")):
        path = Path(os.environ["TMPDIR"]) / (label + ".sql")
        path.write_text("BEGIN; SELECT plan(1); SELECT throws_ok('SELECT 1/0','" + state + "','division by zero','native state'); SELECT * FROM finish(); ROLLBACK;\n")
        completed = subprocess.run(["pg_prove", "--norc", "-h", os.environ["TA_SOCKET"], "-p", os.environ["PGPORT"], "-U", pwd.getpwuid(os.getuid()).pw_name, "-d", "postgres", str(path)], text=True, capture_output=True)
        assert (completed.returncode == 0) is (label == "positive")
        proofs[label] = {"returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}
    return {"python_posture": list(expected), "tap_posture": posture, "tap_refusal": refusal, "negative_control": wrong, "pg_prove": proofs}


if __name__ == "__main__":
    private = sys.argv[1].startswith("private")
    settings = private_setup() if private else Settings()
    result = {} if sys.argv[1] == "private-pgtap" else controls(settings, deployed=sys.argv[1] != "shared-policy")
    print(json.dumps({"native_controls": result}, sort_keys=True), flush=True)
    if private:
        result["pgtap"] = pgtap(settings)
    print(json.dumps(result, indent=2, sort_keys=True))
