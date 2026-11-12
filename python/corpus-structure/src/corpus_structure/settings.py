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

import inspect
import json
import os
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any, Literal, get_args
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict
from pydantic_settings.sources import EnvSettingsSource, InitSettingsSource

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy

ENV_PREFIX = "CORPUS_"
NESTED_DELIMITER = "__"
MASK = "**********"


def ambient_postgresql_routing() -> frozenset[str]:
    """Return the names of libpq overrides that can redirect an explicit profile."""
    return frozenset(name for name in ("PGHOSTADDR", "PGSERVICE") if os.environ.get(name))


class _Section(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class DatabaseSettings(_Section):
    """One libpq URL (peer authentication; no password belongs here) and the template database."""

    url: str = (
        "postgresql://corpus_sem_writer@/corpus_structure_dev?host=/var/run/postgresql&port=5434"
    )
    maintenance_url: str = "postgresql:///"
    reader_url: str | None = None
    admission_url: str | None = None
    evaluator_url: str | None = None
    fitter_url: str | None = None
    template: str = "cs_template"
    pool_min_size: int = Field(default=1, ge=0)
    pool_max_size: int = Field(default=4, ge=1)
    checkout_timeout_seconds: float = Field(default=30.0, gt=0)
    pool_max_waiting: int = Field(default=4, ge=1)
    cancel_request_timeout_seconds: float = Field(default=5.0, gt=0)
    renewal_statement_timeout_seconds: float = Field(default=10.0, gt=0)
    completion_statement_timeout_seconds: float = Field(default=120.0, gt=0, allow_inf_nan=False)
    renewal_lock_timeout_seconds: float = Field(default=5.0, gt=0)

    @model_validator(mode="after")
    def validate_pool_bounds(self) -> DatabaseSettings:
        if self.pool_min_size > self.pool_max_size:
            raise ValueError("database pool_min_size must not exceed pool_max_size")
        if self.renewal_lock_timeout_seconds > self.renewal_statement_timeout_seconds:
            raise ValueError("renewal lock timeout must not exceed statement timeout")
        return self

    @property
    def sqlalchemy_url(self) -> str:
        """The URL in SQLAlchemy's psycopg form, derived from the libpq one."""
        scheme, sep, rest = self.url.partition("://")
        if not sep or scheme not in ("postgresql", "postgres"):
            raise ValueError(f"database.url is not a libpq URL: {self.url!r}")
        return f"postgresql+psycopg://{rest}"


class DeploymentDatabaseSettings(DatabaseSettings):
    """An explicitly configured deployment endpoint with its own purpose credentials."""

    url: str = Field(...)


DeploymentProfile = Literal["development", "deployment"]


class PathSettings(_Section):
    """Where originals and model files live (relative paths resolve from the working directory)."""

    data_dir: Path = Path("build/data")
    model_cache: Path = Path("build/models")


class LlmSettings(_Section):
    """The vLLM endpoint (D2 §12: an endpoint is a setting, not a configuration)."""

    endpoint: str = "http://127.0.0.1:8000/v1"
    api_key: SecretStr | None = None


class NemotronSettings(_Section):
    """Dedicated isolated recognizer operations; model/decoding identity belongs to its recipe."""

    endpoint: str = "http://127.0.0.1:8035/v1"
    python: Path = Path("services/nemotron-parse/.venv/bin/python")
    worker: Path = Path("services/nemotron-parse/worker.py")
    receipts: Path = Path("build/recognition")
    timeout_seconds: float = Field(default=1800.0, gt=0)


class GpuSettings(_Section):
    """GPU mode (D6 §5); `auto` chooses per run from the budgets (default open, OPEN-D6-2)."""

    mode: Literal["auto", "co-resident", "exclusive"] = "auto"


class AnalyticsSettings(_Section):
    """Execution resources only; arithmetic policy belongs to the release profile."""

    capture_mode: Literal["resident", "spooled"] = "spooled"
    batch_size: int = Field(default=65536, ge=1)
    resident_limit_bytes: int = Field(default=512 * 1024**2, ge=1)
    batch_size_hint_bytes: int = Field(default=8 * 1024**2, ge=1)
    threads: int = Field(default=4, ge=1)
    memory_limit: str = "2GB"
    scratch_path: Path = Path("build/tmp/analytics")
    adbc_driver_path: Path | None = None


class RuntimeSettings(_Section):
    """Operator selection; semantic meaning stays in the selected admitted release."""

    default_project: str = "siegrist-pdf"


def _identity_name(name: str) -> str:
    return name


def _contribution_paths(value, prefix=""):
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="python")
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield from _contribution_paths(child, f"{prefix}.{key}" if prefix else str(key))
    else:
        yield prefix


def _source_paths(model, values, prefix=""):
    if isinstance(values, BaseModel):
        yield from _contribution_paths(values, prefix)
        return
    for key, value in values.items():
        for name, info in model.model_fields.items():
            paths = _validation_paths(model, info)
            by_name = not paths or model.model_config.get(
                "validate_by_name", model.model_config.get("populate_by_name", False)
            )
            found = False
            field_value = value
            for alias_path in paths:
                if alias_path[0] != key:
                    continue
                candidate = value
                try:
                    for part in alias_path[1:]:
                        candidate = candidate[part]
                except KeyError, IndexError, TypeError:
                    continue
                field_value, found = candidate, True
                break
            if not found and not (key == name and by_name):
                continue
            path = f"{prefix}.{name}" if prefix else name
            children = [
                t
                for t in get_args(info.annotation) or (info.annotation,)
                if isinstance(t, type) and issubclass(t, BaseModel)
            ]
            if children and isinstance(field_value, Mapping):
                yield from _source_paths(children[0], field_value, path)
            else:
                yield from _contribution_paths(field_value, path)


class _ObservedSettingsSource(PydanticBaseSettingsSource):
    """Observe names/paths while native settings owns source execution and merging."""

    def __init__(self, source):
        super().__init__(source.settings_cls, _init_state=source._init_state)
        self.source = source
        self.__name__ = type(source).__name__
        self.paths = ()

    def get_field_value(self, field, field_name):
        return self.source.get_field_value(field, field_name)

    def __call__(self):
        self.source._set_current_state(self.current_state)
        self.source._set_settings_sources_data(self.settings_sources_data)
        values = self.source()
        self.paths = tuple(_source_paths(self.settings_cls, values))
        return values


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix=ENV_PREFIX,
        env_nested_delimiter=NESTED_DELIMITER,
        frozen=True,
        extra="forbid",
    )

    database: DatabaseSettings = DatabaseSettings()
    deployment: DeploymentDatabaseSettings | None = None
    paths: PathSettings = PathSettings()
    llm: LlmSettings = LlmSettings()
    nemotron: NemotronSettings = NemotronSettings()
    gpu: GpuSettings = GpuSettings()
    analytics: AnalyticsSettings = AnalyticsSettings()
    characterization_execution: CharacterizationExecutionPolicy = Field(
        default_factory=CharacterizationExecutionPolicy
    )
    runtime: RuntimeSettings = RuntimeSettings()
    ci_results: Path | None = None
    _origins: dict[str, str] = PrivateAttr(default_factory=dict)
    _environment_names: tuple[str, ...] = PrivateAttr(default=())
    _known_names: frozenset[str] = PrivateAttr(default_factory=frozenset)
    _source_policy: dict[str, str | bool | None] = PrivateAttr(default_factory=dict)

    @field_validator("characterization_execution", mode="before")
    @classmethod
    def decode_execution_environment(cls, value):
        # Environment leaves are strings; the shared policy itself remains strict.
        if isinstance(value, Mapping):
            return {
                key: json.loads(item) if isinstance(item, str) else item
                for key, item in value.items()
            }
        return value

    def __init__(self, **values: Any) -> None:
        # These pinned 2.16.1 native hooks prepare sources once and give them back to
        # BaseSettings; they avoid a second environment read or a parallel merge engine.
        options = inspect.signature(type(self)._settings_init_sources).parameters
        source_options = {key: value for key, value in values.items() if key in options}
        init_values = {key: value for key, value in values.items() if key not in options}
        sources, init_kwargs = type(self)._settings_init_sources(
            _init_kwargs=init_values, **source_options
        )
        observed = tuple(
            _ObservedSettingsSource(source)
            if isinstance(source, (InitSettingsSource, EnvSettingsSource))
            else source
            for source in sources
        )
        super().__init__(_build_sources=(observed, init_kwargs))
        for source in observed:
            if isinstance(source, _ObservedSettingsSource):
                origin = (
                    "constructor"
                    if isinstance(source.source, InitSettingsSource)
                    else "environment"
                )
                for path in source.paths:
                    self._origins.setdefault(path, origin)
                if isinstance(source.source, EnvSettingsSource):
                    env = source.source
                    self._source_policy = dict(
                        prefix=env.env_prefix,
                        delimiter=env.env_nested_delimiter,
                        case_sensitive=env.case_sensitive,
                    )
                    self._known_names = known_env_names(env)
                    normalize = _identity_name if env.case_sensitive else str.casefold
                    prefix = normalize(env.env_prefix)
                    self._environment_names = tuple(
                        sorted(
                            name if env.case_sensitive else name.upper()
                            for name in env.env_vars
                            if normalize(name).startswith(prefix)
                            or normalize(name) in self._known_names
                        )
                    )
        for path in _contribution_paths(self.model_dump(mode="python")):
            self._origins.setdefault(path, "default")

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
    origins: dict[str, str] = Field(default_factory=dict)
    environment_fields: tuple[str, ...] = ()
    source_policy: dict[str, str | bool | None] = Field(default_factory=dict)


def _validation_paths(model, info):
    """Ordered Pydantic alias paths under the model's native validation policy."""
    alias = info.validation_alias
    if not model.model_config.get("validate_by_alias", True) or not alias:
        return []
    converted = alias.convert_to_aliases() if hasattr(alias, "convert_to_aliases") else alias
    if isinstance(converted, str):
        return [[converted]]
    return converted if isinstance(converted[0], list) else [converted]


def _validation_names(model, name, info):
    """Pydantic input keys, including only the head of an alias path."""
    paths = _validation_paths(model, info)
    names = [path[0] for path in paths]
    if not paths or model.model_config.get(
        "validate_by_name", model.model_config.get("populate_by_name", False)
    ):
        names.append(name)
    return names


def known_env_names(source: EnvSettingsSource) -> frozenset[str]:
    """Accepted keys under the actual native environment source's alias/prefix policy."""
    normalize = _identity_name if source.case_sensitive else str.casefold
    names = set()

    def children(model, base):
        for name, info in model.model_fields.items():
            for child_name in _validation_names(model, name, info):
                full = base + source.env_nested_delimiter + child_name
                names.add(normalize(full))
                descend(info, full)

    def descend(info, base):
        if not source.env_nested_delimiter:
            return
        for child in get_args(info.annotation) or (info.annotation,):
            if isinstance(child, type) and issubclass(child, BaseModel):
                children(child, base)
            elif isinstance(child, type) and is_dataclass(child):
                for field in fields(child):
                    if field.init:
                        names.add(normalize(base + source.env_nested_delimiter + field.name))

    for name, info in source.settings_cls.model_fields.items():
        # Native root extraction owns env_prefix_target, AliasChoices/AliasPath,
        # validation-by-name policy and case handling. Root aliases are absolute.
        for _, env_name, _ in source._extract_field_info(info, name):
            names.add(normalize(env_name))
            descend(info, env_name)
    return frozenset(names)


def _mask_url_credentials(url: str) -> str:
    # Retain useful routing context; unknown query values may contain credentials. This is
    # diagnostic rendering only, never a URL used to establish a connection.
    safe_options = {
        "host",
        "hostaddr",
        "port",
        "sslmode",
        "application_name",
        "connect_timeout",
        "target_session_attrs",
        "channel_binding",
        "gssencmode",
    }
    try:
        parts = urlsplit(url)
        netloc = parts.netloc
        if "@" in netloc:
            authentication, _, host = netloc.rpartition("@")
            username, separator, _ = authentication.partition(":")
            if separator:
                netloc = f"{username}:{MASK}@{host}"
        query = urlencode(
            [
                (key, value if key.casefold() in safe_options else MASK)
                for key, value in parse_qsl(parts.query, keep_blank_values=True)
            ]
        )
        rendered = urlunsplit(
            parts._replace(netloc=netloc, query=query, fragment=MASK if parts.fragment else "")
        )
        # urllib drops an explicitly empty authority for schemes outside its registry.
        # Libpq uses that authority for peer/socket URLs; retain the declared delimiter.
        prefix = parts.scheme + "://"
        if not netloc and url.startswith(prefix) and not rendered.startswith(prefix):
            rendered = prefix + rendered[len(parts.scheme) + 1 :]
        return rendered
    except ValueError:
        return MASK


def settings_report(settings: Settings, environ: Mapping[str, str] | None = None) -> SettingsReport:
    """Explain the constructed snapshot; an explicit mapping requests a separate name inventory.

    Only names and contribution paths are retained during acquisition, never provider values.
    Origins describe acquisition contributions, not complete validator/derived-field provenance.
    """
    resolved: dict[str, str] = {}
    for section, values in settings.model_dump(mode="json").items():
        if values is None:
            continue
        if not isinstance(values, dict):
            resolved[section] = str(values)
            continue
        for field, value in values.items():
            resolved[f"{section}.{field}"] = "" if value is None else str(value)
    for section, database in (("database", settings.database), ("deployment", settings.deployment)):
        if database is None:
            continue
        for field in (
            "url",
            "maintenance_url",
            "evaluator_url",
            "reader_url",
            "admission_url",
            "fitter_url",
        ):
            value = getattr(database, field)
            resolved[f"{section}.{field}"] = "" if value is None else _mask_url_credentials(value)
    resolved["llm.endpoint"] = _mask_url_credentials(settings.llm.endpoint)
    resolved["nemotron.endpoint"] = _mask_url_credentials(settings.nemotron.endpoint)
    policy = settings._source_policy
    normalize = _identity_name if policy.get("case_sensitive") else str.casefold
    names = settings._environment_names if environ is None else tuple(environ)
    known = settings._known_names
    policy_prefix = policy.get("prefix", ENV_PREFIX)
    prefix = normalize(policy_prefix if isinstance(policy_prefix, str) else ENV_PREFIX)
    unknown = tuple(
        sorted(
            name
            for name in names
            if normalize(name).startswith(prefix) and normalize(name) not in known
        )
    )
    supplied = tuple(
        sorted(name for name in settings._environment_names if normalize(name) in known)
    )
    return SettingsReport(
        resolved=resolved,
        unknown_env=unknown,
        origins=settings._origins.copy(),
        environment_fields=supplied,
        source_policy=policy.copy(),
    )
