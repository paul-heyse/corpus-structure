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


def test_deployment_profile_is_independent_and_redacted(monkeypatch: pytest.MonkeyPatch) -> None:
    development = "postgresql:///authoring"
    deployment = "postgresql://deployer:deployment-secret@remote.example/corpus"
    maintenance = "postgresql://migrator:maintenance-secret@remote.example"
    environ = {
        "CORPUS_DATABASE__URL": development,
        "CORPUS_DEPLOYMENT__URL": deployment,
        "CORPUS_DEPLOYMENT__MAINTENANCE_URL": maintenance,
    }
    for key, value in environ.items():
        monkeypatch.setenv(key, value)
    settings = Settings()
    assert settings.database.url == development
    assert settings.deployment is not None
    assert settings.deployment.url == deployment
    assert settings.deployment.maintenance_url == maintenance
    report = settings_report(settings, environ)
    assert report.unknown_env == ()
    assert report.resolved["deployment.url"] == (
        f"postgresql://deployer:{MASK}@remote.example/corpus"
    )
    assert "maintenance-secret" not in report.model_dump_json()
    monkeypatch.delenv("CORPUS_DEPLOYMENT__URL")
    with pytest.raises(ValidationError, match=r"deployment\.url"):
        Settings()


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


@pytest.mark.parametrize(
    "field", ("url", "maintenance_url", "reader_url", "evaluator_url", "admission_url")
)
def test_report_masks_query_credentials_and_preserves_endpoint(field: str) -> None:
    from urllib.parse import parse_qs, urlsplit

    url = (
        "postgresql://operator:login-secret@[::1]:5434/owned?host=/srv/pg&port=5434"
        "&password=query-secret&passfile=/private/auth&sslpassword=ssl-secret"
        "&custom_token=unknown-secret&sslmode=require"
    )
    settings = Settings(database={field: url})
    report = settings_report(settings, {})
    rendered = report.resolved[f"database.{field}"]
    parts = urlsplit(rendered)
    assert parts.hostname == "::1" and parts.port == 5434
    query = parse_qs(parts.query)
    assert query["host"] == ["/srv/pg"] and query["port"] == ["5434"]
    assert query["sslmode"] == ["require"]
    for key in ("password", "passfile", "sslpassword", "custom_token"):
        assert query[key] == [MASK]
    assert all(
        secret not in report.model_dump_json()
        for secret in (
            "login-secret",
            "query-secret",
            "/private/auth",
            "ssl-secret",
            "unknown-secret",
        )
    )


def test_report_masks_endpoint_url_credentials() -> None:
    settings = Settings(llm={"endpoint": "https://user:secret@example.org/v1?token=opaque"})
    rendered = settings_report(settings, {}).resolved["llm.endpoint"]
    assert "secret" not in rendered and "opaque" not in rendered


def test_report_uses_acquired_names_after_environment_changes(monkeypatch):
    monkeypatch.setenv("corpus_database__url", "postgresql:///captured")
    monkeypatch.setenv("corpus_unknown_field", "value-must-not-be-retained")
    settings = Settings()
    monkeypatch.delenv("corpus_database__url")
    monkeypatch.delenv("corpus_unknown_field")
    monkeypatch.setenv("CORPUS_GPU__MODE", "exclusive")
    report = settings_report(settings)
    assert report.resolved["database.url"] == "postgresql:///captured"
    assert report.environment_fields == ("CORPUS_DATABASE__URL",)
    assert report.unknown_env == ("CORPUS_UNKNOWN_FIELD",)
    assert report.origins["database.url"] == "environment"
    assert report.origins["gpu.mode"] == "default"
    assert "value-must-not-be-retained" not in repr(settings.__pydantic_private__)
    assert report.source_policy == {"prefix": "CORPUS_", "delimiter": "__", "case_sensitive": False}


def test_report_uses_actual_instance_source_policy(monkeypatch):
    monkeypatch.setenv("CUSTOM_database--url", "postgresql:///custom")
    monkeypatch.setenv("CORPUS_DATABASE__URL", "postgresql:///ignored")
    settings = Settings(_env_prefix="CUSTOM_", _env_nested_delimiter="--", _case_sensitive=True)
    report = settings_report(settings)
    assert report.resolved["database.url"] == "postgresql:///custom"
    assert report.environment_fields == ("CUSTOM_database--url",)
    assert report.unknown_env == ()
    assert report.source_policy["case_sensitive"] is True


def test_report_nested_json_and_override_have_independent_contributions(monkeypatch):
    monkeypatch.setenv("CORPUS_DATABASE", '{"pool_min_size": 0, "pool_max_size": 6}')
    monkeypatch.setenv("CORPUS_DATABASE__POOL_MAX_SIZE", "7")
    settings = Settings(database={"pool_max_size": 8})
    report = settings_report(settings)
    assert report.resolved["database.pool_min_size"] == "0"
    assert report.resolved["database.pool_max_size"] == "8"
    assert report.origins["database.pool_min_size"] == "environment"
    assert report.origins["database.pool_max_size"] == "constructor"
    assert set(report.environment_fields) == {"CORPUS_DATABASE", "CORPUS_DATABASE__POOL_MAX_SIZE"}


def test_nemotron_endpoint_credentials_and_queries_are_masked():
    settings = Settings(
        nemotron={"endpoint": "https://user:secret@example.test/v1?token=opaque#private"}
    )
    rendered = settings_report(settings).model_dump_json()
    assert all(secret not in rendered for secret in ("secret", "opaque", "private"))


def test_root_validation_alias_is_a_full_environment_name(monkeypatch):
    from pydantic import Field

    class AliasedSettings(Settings):
        operator_label: str = Field(default="unset", validation_alias="CORPUS_ALIAS")

    monkeypatch.setenv("CORPUS_ALIAS", "selected")
    configured = AliasedSettings()
    assert configured.operator_label == "selected"
    report = settings_report(configured)
    assert "CORPUS_ALIAS" in report.environment_fields
    assert "CORPUS_ALIAS" not in report.unknown_env
    assert report.origins["operator_label"] == "environment"
    assert "CORPUS_CORPUS_ALIAS" not in configured._known_names


def test_alias_outside_custom_prefix_is_still_acquired_and_reported(monkeypatch):
    from pydantic import Field

    class AliasedSettings(Settings):
        operator_label: str = Field(default="unset", validation_alias="EXTERNAL_LABEL")

    monkeypatch.setenv("EXTERNAL_LABEL", "selected")
    monkeypatch.setenv("CUSTOM_BAD_NAME", "ignored")
    configured = AliasedSettings(_env_prefix="CUSTOM_")
    assert configured.operator_label == "selected"
    report = settings_report(configured)
    assert report.environment_fields == ("EXTERNAL_LABEL",)
    assert report.origins["operator_label"] == "environment"
    assert report.unknown_env == ("CUSTOM_BAD_NAME",)


def test_nested_alias_stays_relative_and_case_sensitive(monkeypatch):
    from pydantic import BaseModel, ConfigDict, Field

    class Nested(BaseModel):
        model_config = ConfigDict(extra="forbid")
        label: str = Field(default="unset", validation_alias="SelectedLabel")

    class AliasedSettings(Settings):
        nested: Nested = Nested()

    monkeypatch.setenv("CUSTOM_nested__SelectedLabel", "selected")
    configured = AliasedSettings(_env_prefix="CUSTOM_", _case_sensitive=True)
    assert configured.nested.label == "selected"
    report = settings_report(configured)
    assert report.environment_fields == ("CUSTOM_nested__SelectedLabel",)
    assert report.origins["nested.label"] == "environment"
    assert report.unknown_env == ()


def test_root_alias_choices_and_path_keep_canonical_origin(monkeypatch):
    from pydantic import AliasChoices, AliasPath, Field

    class AliasedSettings(Settings):
        operator_label: str = Field(
            default="unset",
            validation_alias=AliasChoices(AliasPath("EXTERNAL_FIELDS", 0), "EXTERNAL_LABEL"),
        )

    monkeypatch.setenv("EXTERNAL_FIELDS", '["selected"]')
    configured = AliasedSettings(_env_prefix="CUSTOM_")
    report = settings_report(configured)
    assert configured.operator_label == "selected"
    assert report.environment_fields == ("EXTERNAL_FIELDS",)
    assert report.origins["operator_label"] == "environment"
    assert "0" not in configured._known_names


@pytest.mark.parametrize("prefix_target,env_name", [("variable", "TOKEN"), ("all", "CORPUS_TOKEN")])
def test_alias_path_head_equal_to_field_name_records_canonical_origin(
    monkeypatch, prefix_target, env_name
):
    from pydantic import AliasPath, Field

    class AliasedSettings(Settings):
        token: int = Field(default=0, validation_alias=AliasPath("token", "value"))

    monkeypatch.setenv(env_name, '{"value":7}')
    configured = AliasedSettings(_env_prefix_target=prefix_target)
    report = settings_report(configured)
    assert configured.token == 7
    assert report.origins["token"] == "environment"
    assert "token.value" not in report.origins
    assert env_name in report.environment_fields


@pytest.mark.parametrize("by_alias,by_name", [(True, True), (False, True)])
def test_alias_path_head_same_name_preserves_native_name_fallback(monkeypatch, by_alias, by_name):
    from pydantic import AliasPath, Field
    from pydantic_settings import SettingsConfigDict

    class AliasedSettings(Settings):
        model_config = SettingsConfigDict(validate_by_alias=by_alias, validate_by_name=by_name)
        token: int = Field(default=0, validation_alias=AliasPath("token", "value"))

    monkeypatch.setenv("CORPUS_TOKEN", "7")
    configured = AliasedSettings()
    report = settings_report(configured)
    assert configured.token == 7
    assert report.origins["token"] == "environment"


def test_alias_choice_same_name_path_retains_ordered_branch_attribution(monkeypatch):
    from pydantic import AliasChoices, AliasPath, Field

    class AliasedSettings(Settings):
        token: int = Field(
            default=0,
            validation_alias=AliasChoices(
                AliasPath("token", "missing"), AliasPath("token", "value"), "OTHER_TOKEN"
            ),
        )

    monkeypatch.setenv("TOKEN", '{"value":7}')
    configured = AliasedSettings()
    assert configured.token == 7
    assert settings_report(configured).origins["token"] == "environment"
