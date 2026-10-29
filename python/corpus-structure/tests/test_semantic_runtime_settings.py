"""Credential purpose and operator selection are resolved once at the entry point."""

from corpus_structure.settings import Settings, settings_report
from corpus_structure.semantic.runtime import connection_settings


def test_runtime_credentials_do_not_replace_constructor_or_environment(monkeypatch):
    monkeypatch.setenv("CORPUS_DATABASE__URL", "postgresql:///from_env")
    monkeypatch.setenv("CORPUS_RUNTIME__DEFAULT_PROJECT", "configured-project")
    settings = Settings(database={"url": "postgresql:///constructor"})
    assert settings.runtime.default_project == "configured-project"
    assert connection_settings(settings).database.url == "postgresql:///constructor"
    assert connection_settings(settings, "read").database.url == "postgresql:///constructor"
    assert connection_settings(settings, "maintenance").database.url == settings.database.maintenance_url
    assert "corpus_sem_evaluator@" in connection_settings(settings, "evaluate").database.url


def test_restricted_defaults_and_purpose_credentials(monkeypatch):
    monkeypatch.delenv("CORPUS_DATABASE__URL", raising=False)
    monkeypatch.delenv("CORPUS_RUNTIME__DEFAULT_PROJECT", raising=False)
    settings = Settings()
    assert settings.runtime.default_project == "semantic-pivot"
    assert "corpus_sem_writer@/corpus_semantic" in settings.database.url
    assert "corpus_sem_reader@/corpus_semantic" in connection_settings(settings, "read").database.url
    assert connection_settings(settings).database.url == settings.database.url
    explicit = Settings(database={"evaluator_url": "postgresql://evaluator:password@host/eval"})
    assert connection_settings(explicit, "evaluate").database.url == explicit.database.evaluator_url
    report = settings_report(explicit, {})
    assert "password" not in report.model_dump_json()
