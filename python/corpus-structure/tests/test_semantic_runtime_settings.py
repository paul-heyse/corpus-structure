"""Credential purpose and operator selection are resolved once at the entry point."""

import pytest
from sqlalchemy.engine import make_url

from corpus_structure.semantic.runtime import Purpose, connection_settings
from corpus_structure.settings import Settings, settings_report


def test_runtime_credentials_do_not_replace_constructor_or_environment(monkeypatch):
    monkeypatch.setenv("CORPUS_DATABASE__URL", "postgresql:///from_env")
    monkeypatch.setenv("CORPUS_RUNTIME__DEFAULT_PROJECT", "configured-project")
    settings = Settings(database={"url": "postgresql:///constructor"})
    assert settings.runtime.default_project == "configured-project"
    assert connection_settings(settings).database.url == "postgresql:///constructor"
    assert (
        make_url(connection_settings(settings, "read").database.url).username == "corpus_sem_reader"
    )
    assert (
        make_url(connection_settings(settings, "maintenance").database.url).database
        == "constructor"
    )
    assert "corpus_sem_evaluator@" in connection_settings(settings, "evaluate").database.url


def test_restricted_defaults_and_purpose_credentials(monkeypatch):
    monkeypatch.delenv("CORPUS_DATABASE__URL", raising=False)
    monkeypatch.delenv("CORPUS_RUNTIME__DEFAULT_PROJECT", raising=False)
    settings = Settings()
    assert settings.runtime.default_project == "siegrist-pdf"
    assert "corpus_sem_writer@/corpus_pdf_20261102" in settings.database.url
    assert (
        "corpus_sem_reader@/corpus_pdf_20261102"
        in connection_settings(settings, "read").database.url
    )
    assert connection_settings(settings).database.url == settings.database.url
    explicit = Settings(database={"evaluator_url": "postgresql://evaluator:password@"})
    evaluator = make_url(connection_settings(explicit, "evaluate").database.url)
    assert evaluator.username == "evaluator" and evaluator.password == "password"
    assert evaluator.database == "corpus_pdf_20261102" and evaluator.host is None
    assert evaluator.query == {"host": "/var/run/postgresql", "port": "5434"}
    report = settings_report(explicit, {})
    assert "password" not in report.model_dump_json()


@pytest.mark.parametrize(
    "application",
    [
        "postgresql://corpus_sem_writer:writer-secret@runtime.example:5440/owned_temporary?sslmode=require&application_name=fixture",
        "postgresql://corpus_sem_writer@/owned_temporary?host=/other/socket&port=5441",
    ],
)
def test_constructor_target_is_identical_for_every_credential_purpose(application, monkeypatch):
    monkeypatch.setenv("CORPUS_DATABASE__URL", "postgresql:///environment_database")
    settings = Settings(
        database={
            "url": application,
            "maintenance_url": "postgresql://admin:admin-secret@",
            "evaluator_url": "postgresql://independent-evaluator:eval-secret@",
        }
    )
    source = make_url(application)
    expected_target = (source.host, source.port, source.database, source.query)
    expected_credentials: dict[Purpose, tuple[str, str | None]] = {
        "write": ("corpus_sem_writer", source.password),
        "read": ("corpus_sem_reader", None),
        "maintenance": ("admin", "admin-secret"),
        "evaluate": ("independent-evaluator", "eval-secret"),
    }
    for purpose, credentials in expected_credentials.items():
        selected = make_url(connection_settings(settings, purpose).database.url)
        assert (selected.host, selected.port, selected.database, selected.query) == expected_target
        assert (selected.username, selected.password) == credentials
    assert settings.database.url == application


def test_peer_maintenance_clears_writer_credentials_and_keeps_target():
    settings = Settings(
        database={
            "url": "postgresql://corpus_sem_writer:writer-secret@runtime.example:5440/owned_temporary?sslmode=require",
            "maintenance_url": "postgresql:///",
        }
    )
    selected = make_url(connection_settings(settings, "maintenance").database.url)
    assert selected.username is None and selected.password is None
    assert (selected.host, selected.port, selected.database) == (
        "runtime.example",
        5440,
        "owned_temporary",
    )
    assert selected.query == {"sslmode": "require"}


def test_query_credentials_cannot_override_selected_purpose_credentials():
    settings = Settings(
        database={
            "url": "postgresql://corpus_sem_writer:writer@runtime.example:5440/owned_temporary?user=other&password=other-secret&passfile=/unrelated/credentials&sslmode=require",
            "maintenance_url": "postgresql:///",
        }
    )
    purposes: tuple[Purpose, ...] = ("read", "evaluate", "maintenance")
    for purpose in purposes:
        selected = make_url(connection_settings(settings, purpose).database.url)
        assert selected.query == {"sslmode": "require"}
        assert selected.database == "owned_temporary" and selected.host == "runtime.example"
        assert (
            selected.username
            == {
                "read": "corpus_sem_reader",
                "evaluate": "corpus_sem_evaluator",
                "maintenance": None,
            }[purpose]
        )
    assert connection_settings(settings, "write").database.url == settings.database.url


def test_unbound_application_settings_use_refused_sentinel():
    import psycopg
    from psycopg_pool import PoolTimeout

    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.settings import Settings

    # The package fixture installed a test-only target after capturing native_settings.
    selected = Settings()
    assert selected.database.url == (
        "postgresql://corpus_test_unbound@/unbound"
        "?host=/__corpus_structure_refused_application_target__&port=5434"
    )
    with (
        pytest.raises((PoolTimeout, psycopg.OperationalError)),
        open_runtime_engine(
            selected, "unbound-application-control", purpose="write", timeout=0.1, max_size=1
        ),
    ):
        pytest.fail("an unbound application target unexpectedly connected")


@pytest.mark.parametrize("purpose", ["read", "evaluate", "admit"])
def test_owner_credentials_are_not_inherited_by_restricted_purpose(purpose):
    settings = Settings(database={"url": "postgresql://owner:secret@/owned"})
    selected = make_url(connection_settings(settings, purpose).database.url)
    assert selected.username != "owner" and selected.password is None
    assert selected.database == "owned"


@pytest.mark.parametrize(
    "field,purpose",
    [("reader_url", "read"), ("evaluator_url", "evaluate"), ("admission_url", "admit")],
)
@pytest.mark.parametrize(
    "credential,conflict",
    [
        ("postgresql://restricted@/another", "database"),
        ("postgresql://restricted@other.example/owned", "host"),
        ("postgresql://restricted@:5440/owned", "port"),
        ("postgresql://restricted@/owned?sslmode=disable", "option sslmode"),
    ],
)
def test_conflicting_purpose_endpoint_refuses(field, purpose, credential, conflict):
    settings = Settings(
        database={
            "url": "postgresql://writer@declared.example:5434/owned?sslmode=require",
            field: credential,
        }
    )
    with pytest.raises(ValueError, match=f"contradict target {conflict}"):
        connection_settings(settings, purpose)


def test_new_purpose_passwords_are_masked():
    settings = Settings(
        database={
            "reader_url": "postgresql://reader:reader-secret@",
            "admission_url": "postgresql://admitter:admitter-secret@",
        }
    )
    report = settings_report(settings, {}).model_dump_json()
    assert "reader-secret" not in report and "admitter-secret" not in report


@pytest.mark.parametrize("url", ["postgresql:///t", "postgresql:///t?host=%2Ftmp&port=5434"])
def test_report_preserves_explicit_socket_url_authority(url):
    settings = Settings(database={"url": url})
    assert settings_report(settings, {}).resolved["database.url"] == url
