"""`ci db init` and `ci db migrate` (P0-F-4) on throwaway databases under the session's lease."""

from __future__ import annotations

import json
from typing import Any

import pytest
from sqlalchemy.engine import make_url

from corpus_structure.core.db import extensions
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
    cli: Any, native_server: Any, semantic_absent_database: str
) -> None:
    name = semantic_absent_database
    made = cli("db", "init", "--json", settings=lambda: settings(native_server, name))
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
    cli: Any, native_server: Any, semantic_absent_database: str
) -> None:
    name = semantic_absent_database
    result = cli("db", "init", settings=lambda: settings(native_server, name, "no_such_template"))
    assert result.exit_code == 1
    assert "the template 'no_such_template' is missing" in result.stderr
    assert not native_server.exists(name)


def test_init_refuses_extensions_at_other_versions(
    cli: Any, native_server: Any, semantic_absent_database: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    name = semantic_absent_database
    wrong = {**extensions.expected_extensions(), "vector": "0.0.1"}
    monkeypatch.setattr(extensions, "expected_extensions", lambda path=None: wrong)
    result = cli("db", "init", settings=lambda: settings(native_server, name))
    assert result.exit_code == 1
    assert "vector 0.8.7 (expected 0.0.1)" in result.stderr and "just db-provision" in result.stderr
    assert not native_server.exists(name)
