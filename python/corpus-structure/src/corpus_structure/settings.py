"""Process settings (D9 §3; foundations §3.1).

One `Settings` root with nested plain models, read from constructor arguments and `CORPUS_*`
environment variables only (`__` separates nesting: `CORPUS_DATABASE__URL`). Settings are built
once at an entry point (the `ci` callback, the MCP lifespan) and passed down; no other module reads
the environment.

`extra="forbid"` refuses an unknown constructor argument and an unknown field inside a section
(`CORPUS_PATHS__DATA_DIRR`), but a name that reaches no section (`CORPUS_DATA_DIRR`) is silently
ignored, so `settings_report` lists every `CORPUS_*` name that matches no field.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

ENV_PREFIX = "CORPUS_"
NESTED_DELIMITER = "__"
MASK = "**********"


class _Section(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class DatabaseSettings(_Section):
    """One libpq URL (peer authentication; no password belongs here) and the template database."""

    url: str = "postgresql://corpus_sem_writer@/corpus_semantic?host=/var/run/postgresql&port=5434"
    maintenance_url: str = "postgresql:///"
    reader_url: str | None = None
    admission_url: str | None = None
    evaluator_url: str | None = None
    template: str = "cs_template"

    @property
    def sqlalchemy_url(self) -> str:
        """The URL in SQLAlchemy's psycopg form, derived from the libpq one."""
        scheme, sep, rest = self.url.partition("://")
        if not sep or scheme not in ("postgresql", "postgres"):
            raise ValueError(f"database.url is not a libpq URL: {self.url!r}")
        return f"postgresql+psycopg://{rest}"


class PathSettings(_Section):
    """Where originals and model files live (relative paths resolve from the working directory)."""

    data_dir: Path = Path("build/data")
    model_cache: Path = Path("build/models")


class LlmSettings(_Section):
    """The vLLM endpoint (D2 §12: an endpoint is a setting, not a configuration)."""

    endpoint: str = "http://127.0.0.1:8000/v1"
    api_key: SecretStr | None = None


class GpuSettings(_Section):
    """GPU mode (D6 §5); `auto` chooses per run from the budgets (default open, OPEN-D6-2)."""

    mode: Literal["auto", "co-resident", "exclusive"] = "auto"


class AnalyticsSettings(_Section):
    """Execution resources only; arithmetic policy belongs to the release profile."""

    threads: int = Field(default=4, ge=1)
    memory_limit: str = "2GB"
    scratch_path: Path = Path("build/tmp/analytics")
    adbc_driver_path: Path | None = None


class RuntimeSettings(_Section):
    """Operator selection; semantic meaning stays in the selected admitted release."""

    default_project: str = "semantic-pivot"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix=ENV_PREFIX,
        env_nested_delimiter=NESTED_DELIMITER,
        frozen=True,
        extra="forbid",
    )

    database: DatabaseSettings = DatabaseSettings()
    paths: PathSettings = PathSettings()
    llm: LlmSettings = LlmSettings()
    gpu: GpuSettings = GpuSettings()
    analytics: AnalyticsSettings = AnalyticsSettings()
    runtime: RuntimeSettings = RuntimeSettings()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Constructor over environment; no dotenv or secrets directory (direnv owns the env).
        return (init_settings, env_settings)


class SettingsReport(BaseModel):
    """What a process resolved, secrets masked, and the `CORPUS_*` names that set nothing."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    resolved: dict[str, str]
    unknown_env: tuple[str, ...]


def known_env_names() -> frozenset[str]:
    """Every environment name a field reads: a section as a whole (JSON) or one of its fields."""
    names: set[str] = set()
    for section, info in Settings.model_fields.items():
        names.add(f"{ENV_PREFIX}{section}".upper())
        model = info.annotation
        if isinstance(model, type) and issubclass(model, BaseModel):
            for field in model.model_fields:
                names.add(f"{ENV_PREFIX}{section}{NESTED_DELIMITER}{field}".upper())
    return frozenset(names)


def _mask_url_password(url: str) -> str:
    parts = urlsplit(url)
    if parts.password is None:
        return url
    host = parts.hostname or ""
    if parts.port is not None:
        host = f"{host}:{parts.port}"
    netloc = f"{parts.username or ''}:{MASK}@{host}"
    return urlunsplit(parts._replace(netloc=netloc))


def settings_report(settings: Settings, environ: Mapping[str, str]) -> SettingsReport:
    """Report `settings` with secrets masked, and the unknown `CORPUS_*` names in `environ`.

    The caller passes the environment (an entry point's `os.environ`), so this reads none itself.
    """
    resolved: dict[str, str] = {}
    for section, values in settings.model_dump(mode="json").items():
        for field, value in values.items():
            resolved[f"{section}.{field}"] = "" if value is None else str(value)
    for field in ("url", "maintenance_url", "evaluator_url", "reader_url", "admission_url"):
        value = getattr(settings.database, field)
        resolved[f"database.{field}"] = "" if value is None else _mask_url_password(value)
    known = known_env_names()
    unknown = sorted(
        name
        for name in environ
        if name.upper().startswith(ENV_PREFIX) and name.upper() not in known
    )
    return SettingsReport(resolved=resolved, unknown_env=tuple(unknown))
