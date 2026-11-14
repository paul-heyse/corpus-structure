"""Finite SQL families executed once by pg_prove, with native TAP interpretation."""

from __future__ import annotations

import json
import os
import re
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, literal, text
from sqlalchemy.dialects import postgresql

_ADAPTER = Path(__file__).with_name("pgtap")
_NAME = re.compile(r"[a-z][a-z0-9_]*\Z")


def sql_literal(value: str) -> str:
    return str(
        literal(value).compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    )


@dataclass(frozen=True)
class SqlCase:
    name: str
    assertions: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if not _NAME.fullmatch(self.name):
            raise ValueError("SQL case names must be simple lowercase identifiers")


@dataclass(frozen=True)
class SqlRecipe:
    family: str
    cases: tuple[SqlCase, ...]
    # Hash the actual adapter content into the sealed seed recipe as well as SQL.
    adapter: tuple[tuple[str, bytes], ...]

    @classmethod
    def create(cls, family: str, cases: tuple[SqlCase, ...]) -> SqlRecipe:
        if not _NAME.fullmatch(family) or len({case.name for case in cases}) != len(cases):
            raise ValueError("SQL family and case names must be finite and unique")
        return cls(
            family,
            cases,
            tuple(
                (str(p.relative_to(_ADAPTER)), p.read_bytes())
                for p in sorted(_ADAPTER.rglob("*.pm"))
            ),
        )


@dataclass(frozen=True)
class SqlStage:
    family: str
    cases: tuple[str, ...]
    adapter: Path
    seed_files: tuple[Path, ...]

    def validate_clone(self, admin: Engine) -> None:
        with admin.connect() as connection:
            version = connection.execute(
                text("SELECT extversion FROM pg_extension WHERE extname='pgtap'")
            ).scalar_one()
            if version != "1.3.4":
                raise RuntimeError("SQL family requires pgTAP 1.3.4")
            functions = (
                connection.execute(
                    text(
                        "SELECT p.proname FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname=:schema"
                    ),
                    {"schema": self.family},
                )
                .scalars()
                .all()
            )
            if set(functions) != set(self.cases):
                raise RuntimeError("SQL seed case function membership changed")


def build_sql_seed(
    recipe: SqlRecipe, admin: Engine, writer: Engine, directory: Path, *, purpose_engine=None
) -> SqlStage:
    """Only called inside the verified-head seed owner; never on the deployed head."""
    adapter = directory / "adapter"
    files = []
    for relative, content in recipe.adapter:
        target = adapter / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        files.append(target)
    statements = [
        "CREATE SCHEMA pgtap",
        "CREATE EXTENSION pgtap WITH SCHEMA pgtap",
        f"CREATE SCHEMA {recipe.family}",
    ]
    for case in recipe.cases:
        body = (
            "BEGIN\n"
            + "\n".join(
                f"RETURN NEXT pgtap.ok(({expression}), {sql_literal(description)});"
                for expression, description in case.assertions
            )
            + "\nEND"
        )
        statements.append(
            f"CREATE FUNCTION {recipe.family}.{case.name}() RETURNS SETOF text LANGUAGE plpgsql AS {sql_literal(body)}"
        )
    source = directory / "recipe.sql"
    source.write_text(";\n".join(statements) + ";\n")
    files.append(source)
    with admin.begin() as connection:
        for statement in statements:
            connection.exec_driver_sql(statement)
    stage = SqlStage(recipe.family, tuple(c.name for c in recipe.cases), adapter, tuple(files))
    stage.validate_clone(admin)
    return stage


@dataclass(frozen=True)
class SelectedCase:
    nodeid: str
    name: str
    assertions: int


def selected_sql_cases(session: Any, family: str) -> tuple[SelectedCase, ...]:
    from qualification_plugin import logical_nodeid

    selected = []
    groups = set()
    for item in session.items:
        marker = item.get_closest_marker("sql_family")
        if marker is None or marker.args[0] != family:
            continue
        name = marker.args[1]
        count = marker.kwargs.get("assertions")
        if (
            not _NAME.fullmatch(name)
            or not isinstance(count, int)
            or isinstance(count, bool)
            or count < 1
        ):
            raise ValueError("SQL family requires a case name and independent assertion count")
        selected.append(SelectedCase(logical_nodeid(item), name, count))
        groups.add(
            tuple(
                sorted(
                    {
                        str(m.args[0] if m.args else m.kwargs.get("name", "default"))
                        for m in item.iter_markers("xdist_group")
                    }
                )
            )
        )
    if (
        not selected
        or len({c.nodeid for c in selected}) != len(selected)
        or len({c.name for c in selected}) != len(selected)
    ):
        raise ValueError("SQL family selection must have unique logical IDs and case names")
    if len(groups) != 1 or len(next(iter(groups))) != 1:
        raise ValueError("all selected SQL family members require one equal final affinity group")
    return tuple(selected)


def controlled_environment(parent: dict[str, str], url: Any) -> dict[str, str]:
    # No ambient Perl preloads, prove settings, harness spooling or libpq selectors.
    env = {
        key: value
        for key, value in parent.items()
        if not key.startswith(("PERL", "PROVE", "HARNESS", "TAP_", "PG")) and key != "TEST_VERBOSE"
    }
    host, port = endpoint(url)
    env.update(PGHOST=host, PGPORT=port, PGDATABASE=url.database, PGUSER=url.username)
    if url.password is not None:
        env["PGPASSWORD"] = url.password
    env["PGCONNECT_TIMEOUT"] = "15"
    return env


def endpoint(url: Any) -> tuple[str, str]:
    host = url.query.get("host", url.host)
    port = url.query.get("port", url.port)
    if not host or not port or not url.database or not url.username:
        raise ValueError("SQL family requires an explicit owned endpoint, database and login")
    return str(host), str(port)


@dataclass
class SqlBatch:
    report: dict[str, Any]
    directory: Path

    def require_pass(self, name: str) -> None:
        observation = self.report.get("observed", {}).get(name)
        assert self.report.get("valid") is True, (
            f"invalid pgTAP batch ({self.directory}): {self.report.get('errors')}"
        )
        assert observation is not None and observation["status"] == "passed", (
            f"SQL case did not pass: {name} ({self.directory})"
        )


def run_sql_batch(clone: Any, selected: tuple[SelectedCase, ...], fallback: Path) -> SqlBatch:
    from qualification_plugin import record_native_context, record_sql_batch

    stage = clone.stage
    if not {case.name for case in selected} <= set(stage.cases):
        raise ValueError("selection contains a case outside the sealed recipe")
    root = Path(os.environ.get("QUALIFICATION_RECEIPT_DIR", str(fallback))) / "sql-batches"
    directory = root / (stage.family + "-" + uuid.uuid4().hex)
    directory.mkdir(parents=True)
    url = clone.admin.url
    with clone.admin.connect() as connection:
        info = connection.connection.driver_connection.info
        if info.dbname != url.database:
            raise RuntimeError("maintenance connection did not acquire the owned clone")
        # Maintenance URLs may intentionally use peer defaults. Resolve those from
        # the authenticated owned connection, never from parent env or guessed ports.
        url = url.set(username=info.user, host=info.host, port=info.port, query={})
        oid, started = connection.execute(
            text(
                "SELECT (SELECT oid FROM pg_database WHERE datname=current_database()), pg_postmaster_start_time()::text"
            )
        ).one()
    host, port = endpoint(url)
    launch = {
        "psql": "/usr/lib/postgresql/18/bin/psql",
        "host": host,
        "port": port,
        "dbname": url.database,
        "username": url.username,
    }
    manifest = {
        "cases": [
            {"name": stage.family + "." + c.name, "nodeid": c.nodeid, "assertions": c.assertions}
            for c in selected
        ],
        "launch": launch,
    }
    (directory / "manifest.json").write_text(json.dumps(manifest))
    context = "json_build_object('database',current_database(),'database_oid',(SELECT oid::bigint FROM pg_database WHERE datname=current_database()),'current_user',current_user,'session_user',session_user,'server_version',current_setting('server_version'),'server_started',pg_postmaster_start_time()::text,'port',current_setting('port')::int,'host',COALESCE(inet_server_addr()::text,current_setting('unix_socket_directories')))"
    pattern = "^(" + "|".join(re.escape(c.name) for c in selected) + ")$"
    source = directory / "selected.pg"
    source.write_text(
        "BEGIN;\nSET LOCAL search_path=pgtap,pg_catalog,public;\nSELECT '# CORPUS_CONTEXT ' || "
        + context
        + "::text;\nSELECT * FROM pgtap.runtests("
        + sql_literal(stage.family)
        + "::name,"
        + sql_literal(pattern)
        + ");\nROLLBACK;\n"
    )
    env = controlled_environment(dict(os.environ), url)
    env.update(
        PERL5LIB=str(stage.adapter),
        CORPUS_PGTAP_RAW=str(directory / "raw.tap"),
        CORPUS_PGTAP_REPORT=str(directory / "report.json"),
        CORPUS_PGTAP_MANIFEST=str(directory / "manifest.json"),
    )
    command = [
        "pg_prove",
        "--norc",
        "--jobs",
        "1",
        "--rules",
        "seq=*",
        "--harness",
        "Corpus::Harness",
        "--formatter",
        "Corpus::Formatter",
        "--nocolor",
        "--psql-bin",
        launch["psql"],
        "--host",
        host,
        "--port",
        port,
        "--dbname",
        str(url.database),
        "--username",
        str(url.username),
        str(source),
    ]
    # The native pgTAP source handler owns psql startup and ON_ERROR_STOP.
    (directory / "invocation.json").write_text(json.dumps({"argv": command}))
    clone.admin.dispose()
    with (directory / "stdout").open("wb") as stdout, (directory / "stderr").open("wb") as stderr:
        process = subprocess.run(command, env=env, stdout=stdout, stderr=stderr, check=False)
    (directory / "process.json").write_text(json.dumps({"returncode": process.returncode}))
    report: dict[str, Any]
    try:
        decoded = json.loads((directory / "report.json").read_text())
        if not isinstance(decoded, dict):
            raise ValueError("native TAP report is not an object")
        report = decoded
    except OSError, ValueError:
        report = {
            "valid": False,
            "errors": ["native TAP report unavailable; cases are incomplete"],
            "observed": {},
        }
    report["expected"] = manifest["cases"]
    report["pg_prove_returncode"] = process.returncode
    if process.returncode:
        report["valid"] = False
        report.setdefault("errors", []).append(f"pg_prove exit {process.returncode}")
    acquired = report.get("context")
    if isinstance(acquired, dict):
        missing = [
            key
            for key in (
                "database",
                "database_oid",
                "current_user",
                "session_user",
                "server_version",
                "server_started",
                "host",
                "port",
            )
            if not acquired.get(key)
        ]
        expected = {
            "database": url.database,
            "database_oid": oid,
            "server_started": started,
            "current_user": url.username,
            "session_user": url.username,
            "port": int(port),
        }
        if missing or any(acquired.get(key) != value for key, value in expected.items()):
            report["valid"] = False
            report.setdefault("errors", []).append(
                "psql acquired context differs from requested database/login/endpoint"
            )
        for case in selected:
            if stage.family + "." + case.name in report.get("observed", {}):
                record_native_context(
                    {
                        "schema": "native-context/v1",
                        "requested": {
                            "database": url.database,
                            "host": host,
                            "port": int(port),
                            "principal": url.username,
                            "purpose": "maintenance",
                        },
                        "acquired": acquired | {"scenario_seed": clone.origin},
                        "provenance": {"complete": not missing, "missing": missing},
                    },
                    nodeid=case.nodeid,
                )
    else:
        report["valid"] = False
    # Public case names stay convenient; artifact report retains fully qualified names.
    (directory / "qualification.json").write_text(json.dumps(report))
    record_sql_batch(report, directory=str(directory), nodeids=[c.nodeid for c in selected])
    report["observed"] = {
        name.removeprefix(stage.family + "."): value
        for name, value in report.get("observed", {}).items()
    }
    return SqlBatch(report, directory)
