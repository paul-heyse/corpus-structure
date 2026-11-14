"""Project-aware bootstrap inside one owned PostgreSQL18 pg_virtualenv cohort."""

from __future__ import annotations

import json
import os
import secrets
import shutil
import sys
import time
from pathlib import Path

import psycopg
from psycopg import sql
from sqlalchemy.engine import URL

from corpus_structure.core.db.extensions import expected_extensions
from corpus_structure.settings import DatabaseSettings, Settings
from native_test_support import semantic_principals
from test_receipts import (
    _cancelled,
    _group_present,
    read_json,
    run_python,
    run_rust,
    supervision,
    write_json,
)


def provision(request, control):
    """Build explicit role Settings on the actual private endpoint; never use shared provisioning."""
    connection = psycopg.connect(
        host=os.environ["PGHOST"],
        port=int(os.environ["PGPORT"]),
        dbname="postgres",
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        autocommit=True,
        connect_timeout=10,
    )
    with connection:
        row = connection.execute(
            "SELECT host(inet_server_addr()),current_setting('port')::int,current_user,"
            "current_setting('data_directory'),current_setting('server_version_num')::int,"
            "pg_postmaster_start_time()::text,system_identifier::text FROM pg_control_system()"
        ).fetchone()
        assert row is not None
        host, port, owner, directory, server_version, started, identifier = row
        work = Path(os.environ["PG_CLUSTER_CONF_ROOT"]).parent.resolve()
        if port != request["port"] or port in {5432, 5434} or not 180000 <= server_version < 190000:
            raise ValueError("acquired private PostgreSQL endpoint/version differs")
        if not Path(directory).resolve().is_relative_to(work):
            raise ValueError("acquired data directory is outside pg_virtualenv ownership")
        principals = semantic_principals()
        passwords = {
            purpose: secrets.token_urlsafe(24) for purpose in principals if purpose != "publisher"
        }
        for purpose, principal in principals.items():
            if control.interruption:
                raise InterruptedError(control.interruption)
            login = sql.SQL("NOLOGIN") if purpose == "publisher" else sql.SQL("LOGIN")
            inherit = sql.SQL("NOINHERIT") if purpose == "fit" else sql.SQL("INHERIT")
            connection.execute(
                sql.SQL(
                    "CREATE ROLE {} {} {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS"
                ).format(sql.Identifier(principal), login, inherit)
            )
            if purpose != "publisher":
                connection.execute(
                    sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                        sql.Identifier(principal), sql.Literal(passwords[purpose])
                    )
                )
        connection.execute(
            sql.SQL("GRANT {} TO {} WITH INHERIT FALSE, SET TRUE").format(
                sql.Identifier(principals["publisher"]), sql.Identifier(owner)
            )
        )
        connection.execute(
            sql.SQL("CREATE DATABASE cs_template OWNER {} TEMPLATE template0").format(
                sql.Identifier(owner)
            )
        )
        connection.execute("ALTER DATABASE cs_template IS_TEMPLATE true")
        admin_password = os.environ["PGPASSWORD"]
        admin = URL.create(
            "postgresql",
            username=owner,
            password=admin_password,
            host=host,
            port=port,
            database="postgres",
            query={"connect_timeout": "10"},
        )
    with psycopg.connect(
        admin.set(database="cs_template").render_as_string(hide_password=False), autocommit=True
    ) as template:
        for name, version in expected_extensions().items():
            if control.interruption:
                raise InterruptedError(control.interruption)
            template.execute(
                sql.SQL("CREATE EXTENSION {} VERSION {}").format(
                    sql.Identifier(name), sql.Literal(version)
                )
            )
        actual = dict(template.execute("SELECT extname,extversion FROM pg_extension").fetchall())
        if any(actual.get(name) != version for name, version in expected_extensions().items()):
            raise ValueError("private infrastructure extension versions differ")

    def purpose_url(purpose):
        return admin.set(
            username=principals[purpose], password=passwords[purpose]
        ).render_as_string(hide_password=False)

    settings = Settings(
        database=DatabaseSettings(
            url=purpose_url("write"),
            maintenance_url=admin.render_as_string(hide_password=False),
            reader_url=purpose_url("read"),
            admission_url=purpose_url("admit"),
            evaluator_url=purpose_url("evaluate"),
            fitter_url=purpose_url("fit"),
            template="cs_template",
        )
    )
    acquired = {
        "mode": "private",
        "host": host,
        "port": port,
        "server_version": server_version,
        "server_started": started,
        "system_identifier": identifier,
        "maintenance_user": owner,
        "template": "cs_template",
        "principals": principals,
        "fast_functional_host": True,
    }
    return settings, acquired


def configure_children(settings, execution_path):
    # Creation credentials and libpq defaults must not leak into purpose acquisition.
    for name in list(os.environ):
        if name in {"CORPUS_DATABASE", "CORPUS_DEPLOYMENT_DATABASE"} or name.startswith(
            ("PG", "_PG_", "CORPUS_DATABASE__", "CORPUS_DEPLOYMENT_DATABASE__")
        ):
            os.environ.pop(name)
    for name, value in settings.database.model_dump(mode="json").items():
        if value is not None:
            os.environ["CORPUS_DATABASE__" + name.upper()] = str(value)
    os.environ["PATH"] = execution_path
    os.environ["CORPUS_CI_NATIVE_HOST"] = "private"


def copy_logs(configuration, directory):
    logs = directory / "private-host-logs"
    logs.mkdir(exist_ok=True)
    for source in (configuration.parent / "log").glob("*.log"):
        shutil.copyfile(source, logs / source.name)


def await_owned_children(configuration, directory):
    """The host cannot exit while any existing Python or Rust owner still has children."""
    prefixes = ("pytest", "rustc", "nextest-version", "nextest-list", "nextest")
    groups = {}
    for prefix in prefixes:
        path = directory / f"{prefix}.process.json"
        if path.is_file():
            cleanup = read_json(path).get("owned_group_cleanup") or {}
            if cleanup.get("group") is not None:
                groups[prefix] = cleanup["group"]
    while True:
        pending = {prefix: group for prefix, group in groups.items() if _group_present(group)}
        write_json(
            directory / "private-host-child-settlement.json",
            {
                "state": "waiting" if pending else "settled",
                "owned_groups": groups,
                "pending": pending,
            },
        )
        if not pending:
            return
        copy_logs(configuration, directory)
        time.sleep(0.1)


def main():
    request = json.loads(Path(sys.argv[1]).read_text())
    directory = Path(request["directory"])
    configuration = Path(os.environ["PG_CLUSTER_CONF_ROOT"])
    write_json(
        directory / "private-cohort.inner.json", {"pid": os.getpid(), "parent_pid": os.getppid()}
    )
    outcome = 1
    with supervision(directory) as control:
        try:
            settings, acquired = provision(request, control)
            configure_children(settings, request["execution_path"])
            write_json(directory / "private-host.json", acquired)
            invocation = json.loads((directory / "invocation.json").read_text())
            write_json(
                directory / "invocation.json", {**invocation, "native_host_context": acquired}
            )
            if control.interruption:
                raise InterruptedError(control.interruption)
            process = run_python(
                directory,
                request["pytest_args"],
                timeout=request["timeout"],
                test_timeout=request["test_timeout"],
                cwd=Path(request["cwd"]),
                managed=request["managed"],
                evidence_selection=request["evidence_selection"],
            )
            if not request["python_only"] and not _cancelled(process):
                run_rust(directory, timeout=request["timeout"])
            outcome = (
                130
                if _cancelled(process)
                else (process["returncode"] if process.get("returncode") is not None else 1)
            )
        except (Exception, KeyboardInterrupt) as error:
            write_json(
                directory / "private-host-failure.json",
                {
                    "phase": "bootstrap_or_execution",
                    "type": type(error).__name__,
                    "message": str(error),
                },
            )
            outcome = 130 if control.interruption else 1
        finally:
            await_owned_children(configuration, directory)
            copy_logs(configuration, directory)
    return outcome


if __name__ == "__main__":
    raise SystemExit(main())
