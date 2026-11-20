"""Contract probe: pydantic-settings 2.16.1 sources, origins, nesting, layering, env decoding.

Run from the repository root:
    uv run python docs/design_review/evidence/2026-11-20_json-boundary-contracts/schema_models_settings_probe.py

Environment variables are set inside this process only (os.environ), never exported.
"""

from __future__ import annotations

import json
import os
import tempfile
from contextvars import ContextVar
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError
from pydantic_settings import (
    BaseSettings,
    JsonConfigSettingsSource,
    NoDecode,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    SettingsError,
)

print("pydantic-settings", version("pydantic-settings"))
for name in list(os.environ):
    if name.startswith("CORPUS_") or name.startswith("PROBE_"):
        del os.environ[name]


def outcome(fn):
    try:
        return repr(fn())[:160]
    except ValidationError as exc:
        return "ValidationError:" + ";".join(f"{e['type']}@{'.'.join(map(str, e['loc']))}" for e in exc.errors())
    except SettingsError as exc:
        return f"SettingsError: {exc}"[:200]
    except Exception as exc:  # noqa: BLE001
        return f"{type(exc).__name__}: {exc}"[:200]


class Database(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    url: str = "postgresql:///default"
    pool_max_size: int = Field(default=4, ge=1)
    password: SecretStr | None = None


@dataclass(frozen=True)
class Policy:
    workers: Annotated[int, Field(strict=True, ge=1)] = 1
    enabled: Annotated[bool, Field(strict=True)] = False


_observed: ContextVar[dict[str, dict[str, Any]] | None] = ContextVar("_observed", default=None)


class OriginObserver(PydanticBaseSettingsSource):
    """Last-before-default source: reads earlier sources' outputs through the public property."""

    def get_field_value(self, field, field_name):  # required abstract method; unused
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        sink = _observed.get()
        if sink is not None:
            sink.update({name: data for name, data in self.settings_sources_data.items()})
        return {}


class Probe(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PROBE_", env_nested_delimiter="__", frozen=True, extra="forbid")
    database: Database = Database()
    policy: Policy = Field(default_factory=Policy)
    numbers: list[int] = []
    name: str = "n"

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings):
        return (init_settings, env_settings, OriginObserver(settings_cls))


def build(**kwargs):
    sink: dict[str, dict[str, Any]] = {}
    token = _observed.set(sink)
    try:
        return Probe(**kwargs), sink
    finally:
        _observed.reset(token)


print("\n[D18] origins through public settings_sources_data")
os.environ["PROBE_DATABASE__POOL_MAX_SIZE"] = "8"
settings, seen = build(name="from-init")
print("  settings:", settings.database.pool_max_size, settings.name)
print("  observer saw:", seen)
print("  model_fields_set:", settings.model_fields_set, "| database.model_fields_set:", settings.database.model_fields_set)
del os.environ["PROBE_DATABASE__POOL_MAX_SIZE"]

print("\n[D19] nested section built alone ignores the environment")
os.environ["PROBE_DATABASE__URL"] = "postgresql:///from-env"
print("  Database().url:", Database().url, "| Probe().database.url:", Probe().database.url)
from corpus_structure.settings import DatabaseSettings, Settings, settings_report  # noqa: E402

os.environ["CORPUS_DATABASE__POOL_MAX_SIZE"] = "7"
os.environ["CORPUS_DATA_DIRR"] = "typo"
print("  project DatabaseSettings().pool_max_size:", DatabaseSettings().pool_max_size, "| Settings().database.pool_max_size:", Settings().database.pool_max_size)
print("  project Settings() with CORPUS_DATA_DIRR (prefix-sharing unknown name):", outcome(lambda: Settings().paths.data_dir), "| report unknown_env:", settings_report(Settings()).unknown_env)
os.environ["CORPUS_PATHS__DATA_DIRR"] = "typo"
print("  project Settings() with CORPUS_PATHS__DATA_DIRR (unknown inside a section):", outcome(lambda: Settings()))
for n in ("CORPUS_DATABASE__POOL_MAX_SIZE", "CORPUS_DATA_DIRR", "CORPUS_PATHS__DATA_DIRR", "PROBE_DATABASE__URL"):
    del os.environ[n]


class Partial(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PROBE_", env_nested_delimiter="__")
    database: Database = Database(url="postgresql:///instance-default", pool_max_size=9)


class PartialOn(Partial):
    model_config = SettingsConfigDict(env_prefix="PROBE_", env_nested_delimiter="__", nested_model_default_partial_update=True)


os.environ["PROBE_DATABASE__POOL_MAX_SIZE"] = "2"
print("  default-instance + env partial, flag off:", Partial().database)
print("  default-instance + env partial, flag on: ", PartialOn().database)
del os.environ["PROBE_DATABASE__POOL_MAX_SIZE"]

print("\n[D20] file source with a per-instance path, deep merge with env and init")
_policy_file: ContextVar[Path | None] = ContextVar("_policy_file", default=None)


class Layered(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PROBE_", env_nested_delimiter="__", extra="forbid")
    database: Database = Database()
    policy: Policy = Field(default_factory=Policy)

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings):
        path = _policy_file.get()
        file_sources = (JsonConfigSettingsSource(settings_cls, json_file=path),) if path else ()
        return (init_settings, env_settings, *file_sources)


with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp, "policy.json")
    path.write_text(json.dumps({"database": {"url": "postgresql:///from-file", "pool_max_size": 3}, "policy": {"workers": 5}}))
    os.environ["PROBE_DATABASE__POOL_MAX_SIZE"] = "6"
    token = _policy_file.set(path)
    try:
        layered = Layered(database={"url": "postgresql:///from-init"})
        print("  init url + env pool + file policy:", layered.database.url, layered.database.pool_max_size, layered.policy)
    finally:
        _policy_file.reset(token)
    del os.environ["PROBE_DATABASE__POOL_MAX_SIZE"]
print("  file source JSON numbers are validated in python mode (strict int from file 5 -> ok above); strings would fail strict")

print("\n[D21] env decoding and strict leaves")
os.environ["PROBE_POLICY__WORKERS"] = "4"
print("  strict dataclass leaf from env '4':", outcome(lambda: Probe().policy))
del os.environ["PROBE_POLICY__WORKERS"]
os.environ["PROBE_POLICY"] = '{"workers": 4, "enabled": true}'
print("  whole complex value as JSON:", outcome(lambda: Probe().policy))
del os.environ["PROBE_POLICY"]
os.environ["PROBE_NUMBERS"] = "[1,"
print("  malformed JSON for complex field:", outcome(lambda: Probe()))
os.environ["PROBE_NUMBERS"] = '["x"]'
print("  decodable JSON, invalid value:", outcome(lambda: Probe()))
del os.environ["PROBE_NUMBERS"]


class NoDec(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PROBE_")
    numbers: Annotated[list[int], NoDecode] = []


os.environ["PROBE_NUMBERS"] = "[1,2]"
print("  NoDecode list from env:", outcome(lambda: NoDec().numbers))
del os.environ["PROBE_NUMBERS"]

print("\n[D22] extra='forbid' with env_prefix")
os.environ["PROBE_UNKNOWN"] = "1"
print("  unknown PROBE_UNKNOWN:", outcome(lambda: Probe().name))
del os.environ["PROBE_UNKNOWN"]
os.environ["PROBE_DATABASE__URLX"] = "1"
print("  unknown nested PROBE_DATABASE__URLX:", outcome(lambda: Probe()))
del os.environ["PROBE_DATABASE__URLX"]

print("\n[D23] misc")
s, _ = build(database={"password": "pw"})
print("  SecretStr in model_dump(mode='json'):", s.model_dump(mode="json")["database"]["password"], "| python:", s.model_dump()["database"]["password"])
print("  settings_cached exists:", hasattr(Probe, "settings_cached"), "| same object twice:", Probe.settings_cached() is Probe.settings_cached())
import pydantic_settings  # noqa: E402

print("  exported sources:", sorted(n for n in dir(pydantic_settings) if n.endswith("Source")))
