"""`ci db init` and `ci db migrate` (P0-F-4) on throwaway databases under the session's lease."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url

from corpus_structure.core.db import extensions
from corpus_structure.core.db.ownership import DatabaseReservation
from corpus_structure.semantic.metadata import PHYSICAL_MODEL_ID
from corpus_structure.semantic.migrations import head_revision
from corpus_structure.settings import Settings


def settings(native_server: Any, name: str, template: str | None = None) -> Settings:
    url = make_url(native_server.url_of(name)).set(drivername="postgresql")
    database = {
        "url": url.render_as_string(hide_password=False),
        "template": template or native_server.template,
        "maintenance_url": url.render_as_string(hide_password=False),
    }
    return Settings(database=database)


def test_init_creates_and_migrates_then_migrate_reports(
    cli: Any, native_server: Any, semantic_absent_database: DatabaseReservation
) -> None:
    name = semantic_absent_database.name
    made = cli(
        "db",
        "init",
        "--creation-token",
        semantic_absent_database.token,
        "--json",
        settings=lambda: settings(native_server, name),
    )
    assert made.exit_code == 0, made.stderr
    report = json.loads(made.stdout)
    assert report["database"] == name and report["created"] is True
    assert report["revision"] == report["head"] == head_revision()
    assert report["model_revision"] == PHYSICAL_MODEL_ID
    assert report["applied"][0] == "semantic_0001"
    assert report["applied"][-1] == head_revision()
    again = cli("db", "migrate", "--json", settings=lambda: settings(native_server, name))
    assert again.exit_code == 0, again.stderr
    assert json.loads(again.stdout)["applied"] == []
    rerun = cli("db", "init", "--json", settings=lambda: settings(native_server, name))
    assert json.loads(rerun.stdout)["created"] is False


def test_init_refuses_a_missing_template(
    cli: Any, native_server: Any, semantic_absent_database: DatabaseReservation
) -> None:
    name = semantic_absent_database.name
    result = cli("db", "init", settings=lambda: settings(native_server, name, "no_such_template"))
    assert result.exit_code == 1
    assert "the template 'no_such_template' is missing" in result.stderr
    assert not native_server.exists(name)


def test_init_refuses_extensions_at_other_versions(
    cli: Any,
    native_server: Any,
    semantic_absent_database: DatabaseReservation,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    name = semantic_absent_database.name
    wrong = {**extensions.expected_extensions(), "vector": "0.0.1"}
    monkeypatch.setattr(extensions, "expected_extensions", lambda path=None: wrong)
    result = cli("db", "init", settings=lambda: settings(native_server, name))
    assert result.exit_code == 1
    error = " ".join(result.stderr.split())
    assert "vector 0.8.7 (expected 0.0.1)" in error and "just db-provision" in error
    assert not native_server.exists(name)


@pytest.mark.parametrize("cancel", [False, True])
def test_reserved_cli_never_adopts_or_drops_an_intervening_database(
    cli: Any, native_server: Any, cancel: bool
) -> None:
    name = f"cs_sem_init_{os.getpid()}_{uuid4().hex[:12]}"
    expected = BaseExceptionGroup if cancel else RuntimeError
    try:
        with (
            pytest.raises(expected, match="cleanup failures" if cancel else "unauthenticated"),
            native_server.reserved(name) as reservation,
        ):
            # A different, noncooperating connection owns the actual CREATE.
            with native_server.connect() as actor:
                actor.exec_driver_sql(f'CREATE DATABASE "{name}" TEMPLATE template0')
                oid = actor.execute(
                    text("SELECT oid FROM pg_database WHERE datname=:name"), {"name": name}
                ).scalar_one()
            with native_server.connect(name) as actor:
                actor.exec_driver_sql("CREATE TABLE public.intervening(value int)")
                actor.exec_driver_sql("INSERT INTO public.intervening VALUES (73)")
            if cancel:
                raise KeyboardInterrupt("cancel before CLI creation")
            result = cli(
                "db",
                "init",
                "--creation-token",
                reservation.token,
                settings=lambda: settings(native_server, name),
            )
            assert result.exit_code == 1
            assert "creation-only database already exists" in result.stderr
        with native_server.connect() as actor:
            assert (
                actor.execute(
                    text("SELECT oid FROM pg_database WHERE datname=:name"), {"name": name}
                ).scalar_one()
                == oid
            )
        with native_server.connect(name) as actor:
            assert actor.exec_driver_sql("SELECT value FROM public.intervening").scalar_one() == 73
            assert actor.exec_driver_sql("SELECT to_regnamespace('sem')").scalar_one() is None
    finally:
        with native_server.connect() as actor:
            actor.exec_driver_sql(f'DROP DATABASE IF EXISTS "{name}"')


def test_cli_subprocess_acknowledges_creation_before_failed_migration(native_server: Any) -> None:
    name = f"cs_sem_init_{os.getpid()}_{uuid4().hex[:12]}"
    template = f"cs_sem_test_{os.getpid()}_{uuid4().hex[:12]}"
    with native_server.database(template, native_server.template) as engine:
        with engine.begin() as connection:
            connection.exec_driver_sql("CREATE TABLE public.alembic_version(version_num text)")
        engine.dispose()
        with native_server.reserved(name) as reservation:
            configured = settings(native_server, name, template)
            env = {
                **os.environ,
                "CORPUS_DATABASE__URL": configured.database.url,
                "CORPUS_DATABASE__MAINTENANCE_URL": configured.database.maintenance_url,
                "CORPUS_DATABASE__TEMPLATE": template,
            }
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "from corpus_structure.cli.app import main; main()",
                    "db",
                    "init",
                    "--creation-token",
                    reservation.token,
                    "--json",
                ],
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            assert result.returncode == 1, result.stderr
            refusal = json.loads(result.stdout)
            assert refusal["error"]["code"] == "DbRefused"
            assert "legacy database refused" in refusal["error"]["message"]
            with native_server.connect() as connection:
                oid, comment = connection.execute(
                    text(
                        "SELECT oid,shobj_description(oid,'pg_database') "
                        "FROM pg_database WHERE datname=:name"
                    ),
                    {"name": name},
                ).one()
            assert comment == f"corpus-structure owned database {reservation.token} oid {oid}"
        assert not native_server.exists(name)
