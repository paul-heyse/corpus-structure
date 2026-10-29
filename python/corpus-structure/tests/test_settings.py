"""The settings contract (foundations §3.1, D9 §3)."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from corpus_structure.settings import MASK, Settings, settings_report


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    for name in list(os.environ):
        if name.upper().startswith("CORPUS_"):
            monkeypatch.delenv(name)


def test_prefix_and_nesting(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORPUS_DATABASE__URL", "postgresql:///other")
    monkeypatch.setenv("CORPUS_GPU__MODE", "exclusive")
    monkeypatch.setenv("CI_GPU__MODE", "co-resident")  # CI systems' prefix is not ours
    settings = Settings()
    assert settings.database.url == "postgresql:///other"
    assert settings.database.template == "cs_template"
    assert settings.gpu.mode == "exclusive"


def test_init_beats_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CORPUS_DATABASE__URL", "postgresql:///from_env")
    settings = Settings(database={"url": "postgresql:///from_init"})
    assert settings.database.url == "postgresql:///from_init"


def test_two_settings_do_not_leak() -> None:
    a = Settings(database={"url": "postgresql:///a"}, gpu={"mode": "exclusive"})
    b = Settings(database={"url": "postgresql:///b"})
    assert (a.database.url, a.gpu.mode) == ("postgresql:///a", "exclusive")
    assert (b.database.url, b.gpu.mode) == ("postgresql:///b", "auto")


def test_frozen_and_forbidding() -> None:
    settings = Settings()
    with pytest.raises(ValidationError):
        settings.database = settings.database
    with pytest.raises(ValidationError):
        Settings(databse={"url": "x"})
    with pytest.raises(ValidationError):
        Settings(database={"url": "x", "pasword": "y"})


def test_no_dotenv_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".env").write_text("CORPUS_GPU__MODE=exclusive\n")
    monkeypatch.chdir(tmp_path)
    assert Settings().gpu.mode == "auto"


def test_sqlalchemy_url() -> None:
    url = "postgresql:///corpus?host=/srv/pg/run&port=5440"
    expected = "postgresql+psycopg:///corpus?host=/srv/pg/run&port=5440"
    assert Settings(database={"url": url}).database.sqlalchemy_url == expected
    with pytest.raises(ValueError, match="libpq URL"):
        _ = Settings(database={"url": "mysql://x/y"}).database.sqlalchemy_url


def test_report_lists_unknown_names_and_masks_secrets() -> None:
    settings = Settings(
        database={"url": "postgresql://paul:hunter2@db.local:5440/corpus"},
        llm={"api_key": "sk-secret"},
    )
    environ = {
        "CORPUS_DATA_DIRR": "/x",  # mistyped: sets nothing
        "corpus_databse__url": "x",  # case-insensitive; no section `databse`
        "CORPUS_DATABASE__URL": "postgresql:///corpus",
        "CORPUS_PATHS": "{}",  # a whole section as JSON is known
        "CI_JOB": "1",
        "HOME": "/home/x",
    }
    report = settings_report(settings, environ)
    assert report.unknown_env == ("CORPUS_DATA_DIRR", "corpus_databse__url")
    assert report.resolved["llm.api_key"] == MASK
    assert report.resolved["database.url"] == f"postgresql://paul:{MASK}@db.local:5440/corpus"
    assert "hunter2" not in report.model_dump_json()
    assert "sk-secret" not in report.model_dump_json()
    assert report.resolved["gpu.mode"] == "auto"
