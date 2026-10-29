"""`ci db init` and `ci db migrate` (P0-F-4) on throwaway databases under the session's lease."""

from __future__ import annotations

import json
import os
from typing import Any

import pytest
from sqlalchemy.engine import make_url

from corpus_structure.core._model.revision import CONTENT_HASH
from corpus_structure.core.db import extensions
from corpus_structure.settings import Settings


def settings(db_server: Any, name: str, template: str | None = None) -> Settings:
    url = make_url(db_server.url_of(name)).set(drivername="postgresql")
    database = {
        "url": url.render_as_string(hide_password=False),
        "template": template or db_server.template,
    }
    return Settings(database=database)  # type: ignore[arg-type]


def test_init_creates_and_migrates_then_migrate_reports(cli: Any, db_server: Any) -> None:
    name = f"ci_test_{os.getpid()}_9501"
    db_server.drop(name)
    try:
        made = cli("db", "init", "--json", settings=lambda: settings(db_server, name))
        assert made.exit_code == 0, made.stderr
        report = json.loads(made.stdout)
        assert report == {
            "database": name,
            "created": True,
            "revision": "0002",
            "head": "0002",
            "model_revision": CONTENT_HASH,
            "applied": ["0001", "0002"],
        }
        again = cli("db", "migrate", "--json", settings=lambda: settings(db_server, name))
        assert again.exit_code == 0, again.stderr
        assert json.loads(again.stdout)["applied"] == []
        rerun = cli("db", "init", "--json", settings=lambda: settings(db_server, name))
        assert json.loads(rerun.stdout)["created"] is False
    finally:
        db_server.drop(name)


def test_init_refuses_a_missing_template(cli: Any, db_server: Any) -> None:
    name = f"ci_test_{os.getpid()}_9502"
    result = cli("db", "init", settings=lambda: settings(db_server, name, "no_such_template"))
    assert result.exit_code == 1
    assert "the template 'no_such_template' is missing" in result.stderr
    assert not db_server.exists(name)


def test_init_refuses_extensions_at_other_versions(
    cli: Any, db_server: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    name = f"ci_test_{os.getpid()}_9503"
    wrong = {**extensions.expected_extensions(), "vector": "0.0.1"}
    monkeypatch.setattr(extensions, "expected_extensions", lambda path=None: wrong)
    result = cli("db", "init", settings=lambda: settings(db_server, name))
    assert result.exit_code == 1
    assert "vector 0.8.7 (expected 0.0.1)" in result.stderr and "just db-provision" in result.stderr
    assert not db_server.exists(name)
