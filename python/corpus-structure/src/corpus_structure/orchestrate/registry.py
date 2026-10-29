"""The registry and named configurations (orchestration §3.2; D4 §1; D2 §12.1).

**Loading `methods.yaml`.** `load_methods(path)` reads the file with PyYAML `safe_load` into
`MethodsFile`: its `version`, `configs: {method: {name: params}}` and every other top-level section
(`math`, `binders`, `aliases`, …) kept as data. Nothing else is read: no settings source, no
environment, no `BaseSettings` (coordinator decision 26). A configuration of an unregistered method
is refused when the registry is built.

**The overlay** `defaults ⊕ named params` is whole top-level replacement: the `Config` validated
from the named params alone, so each field the params give replaces the default whole (a nested map
is never merged key by key) and each field they omit takes its declared default. References are
resolved after the overlay, on its result: an `ArtifactRef` to the hash of the schema version's
artifact of that compiler and kind (the installed compiler version's), a `ConfigRef` to the other
method's resolved params (named `<method>/<name>` or `<name>`), a `SourceProfileRef` to the parsed
profile, a `PackSection` to the file's section. A float becomes its canonical decimal string before
hashing (D1 §10.1), and `cfg:` hashes the complete canonical params, defaults included.

**Per run.** `resolve_all` resolves every named configuration of every registered method (a method
the file names nothing for gets `default`, its `Config` defaults); `record` get-or-creates the
`ops.method` rows (with the declared `ConfidenceSource` beside the family) and `ops.method_config`
rows (with the tier). The run stores the map `<method>/<name>` → config hash in its options, and
`RunConfigs` serves every later lookup for the run from that map and the stored rows, so editing
`methods.yaml` never changes what an existing run resolves.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ValidationError
from sqlalchemy import Connection, select

from corpus_structure.core.canonical import decimal_of_float
from corpus_structure.core.evidence import config_key
from corpus_structure.core.method import (
    ArtifactRef,
    ConfigRef,
    Method,
    PackSection,
    ResolvedConfig,
    SourceProfileRef,
    config_references,
)

DEFAULT = "default"


class RegistryError(ValueError):
    """A configuration that cannot be loaded or resolved; `problems` names method, configuration
    and field for each."""

    def __init__(self, problems: Sequence[str]) -> None:
        self.problems = list(problems)
        super().__init__("; ".join(self.problems))


@dataclass(frozen=True)
class MethodsFile:
    """`methods.yaml` as loaded: its version, its named configurations and its other sections."""

    version: str = "0"
    configs: Mapping[str, Mapping[str, Mapping[str, Any]]] = field(default_factory=dict)
    sections: Mapping[str, Any] = field(default_factory=dict)


def load_methods(path: Path) -> MethodsFile:
    """The pack's `methods.yaml`; an absent file is an empty one."""
    if not path.exists():
        return MethodsFile()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise RegistryError([f"{path.name}: the top level is not a mapping"])
    data = dict(data)
    version = str(data.pop("version", "0"))
    configs = data.pop("configs", None) or {}
    problems = []
    if not isinstance(configs, dict):
        problems.append(f"{path.name}: configs is not a mapping")
        configs = {}
    for method, named in configs.items():
        if not isinstance(named, dict) or not all(isinstance(p, dict) for p in named.values()):
            problems.append(f"{path.name}: configs.{method} is not a mapping of named params")
    if problems:
        raise RegistryError(problems)
    return MethodsFile(version, configs, data)


def canonical_numbers(value: Any) -> Any:
    """Floats as their canonical decimal strings, so a configuration hashes (D1 §10.1)."""
    if isinstance(value, bool) or value is None or isinstance(value, int | str):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"a non-finite float {value!r}")
        return decimal_of_float(value)
    if isinstance(value, Mapping):
        return {str(k): canonical_numbers(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [canonical_numbers(v) for v in value]
    return value


def _get(data: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    for part in path:
        if not isinstance(data, Mapping) or part not in data:
            return None
        data = data[part]
    return data


def _set(data: dict[str, Any], path: tuple[str, ...], value: Any) -> None:
    for part in path[:-1]:
        data = data.setdefault(part, {})
    data[path[-1]] = value


class MethodRegistry:
    """The registered methods and the pack's named configurations (module doc); implements
    `core.method.Registry` for resolution outside a run (`config` resolves without artifacts)."""

    def __init__(
        self,
        methods: Iterable[Method[Any]],
        file: MethodsFile | None = None,
        sources: Path | None = None,
    ) -> None:
        self._methods = {m.name: m for m in methods}
        self.file = file = file or MethodsFile()
        self.sources = sources
        unregistered = sorted(set(file.configs) - set(self._methods))
        if unregistered:
            raise RegistryError([f"configs.{m}: no registered method {m!r}" for m in unregistered])

    def method(self, name: str) -> Method[Any]:
        if name not in self._methods:
            raise RegistryError([f"no registered method {name!r}"])
        return self._methods[name]

    def methods(self) -> Sequence[Method[Any]]:
        return list(self._methods.values())

    def named(self) -> list[tuple[str, str]]:
        """Every (method, configuration name): the file's, and `default` for a method it omits."""
        out = []
        for name in self._methods:
            names = list(self.file.configs.get(name, {})) or [DEFAULT]
            out += [(name, n) for n in names]
        return out

    def overlay(self, method: str, name: str) -> BaseModel:
        """The method's `Config` validated from the named params alone (whole replacement)."""
        cls = self.method(method).Config
        named = self.file.configs.get(method, {})
        if name not in named and not (name == DEFAULT and not named):
            raise RegistryError([f"{method}/{name}: no such configuration"])
        params = dict(named.get(name, {}))
        try:
            return cls.model_validate(params)
        except ValidationError as error:
            raise RegistryError(
                [
                    f"{method}/{name}: {'.'.join(map(str, e['loc']))}: {e['msg']}"
                    for e in error.errors()
                ]
            ) from None

    def resolve(
        self,
        method: str,
        name: str,
        artifacts: Mapping[tuple[str, str], str] | None = None,
        _seen: tuple[str, ...] = (),
    ) -> ResolvedConfig:
        """The named configuration with its references resolved, its canonical params and hash."""
        key = f"{method}/{name}"
        if key in _seen:
            raise RegistryError([f"{key}: a configuration reference cycle {' -> '.join(_seen)}"])
        m = self.method(method)
        config = self.overlay(method, name)
        dump = config.model_dump(mode="json")
        problems = []
        for path, marker in config_references(type(config)).items():
            where = f"{key}: {'.'.join(path)}"
            value = _get(dump, path)
            match marker:
                case ArtifactRef(compiler=compiler, kind=kind):
                    found = (artifacts or {}).get((compiler, kind))
                    if found is None:
                        problems.append(
                            f"{where}: no {compiler} {kind} artifact in the schema version"
                        )
                        continue
                    _set(dump, path, found)
                case ConfigRef(method=other):
                    ref = str(value or DEFAULT)
                    other_name = ref.split("/", 1)[1] if ref.startswith(f"{other}/") else ref
                    inner = self.resolve(other, other_name, artifacts, (*_seen, key))
                    _set(dump, path, dict(inner.params))
                case SourceProfileRef():
                    _set(dump, path, self._profile(str(value), where))
                case PackSection(name=section):
                    if section not in self.file.sections:
                        problems.append(f"{where}: methods.yaml has no section {section!r}")
                        continue
                    _set(dump, path, self.file.sections[section])
        if problems:
            raise RegistryError(problems)
        try:
            resolved = type(config).model_validate(dump)
            params = canonical_numbers(resolved.model_dump(mode="json"))
        except (ValidationError, ValueError) as error:
            raise RegistryError([f"{key}: {error}"]) from None
        return ResolvedConfig(method, name, resolved, params, config_key(m.name, m.version, params))

    def config(self, method: str, name: str) -> ResolvedConfig:
        return self.resolve(method, name)

    def profiles(self, method: str, name: str) -> list[tuple[str, str]]:
        """(field, profile name) of each `SourceProfileRef` the configuration names."""
        config = self.overlay(method, name)
        dump = config.model_dump(mode="json")
        return [
            (".".join(path), str(_get(dump, path)))
            for path, marker in config_references(type(config)).items()
            if isinstance(marker, SourceProfileRef)
        ]

    def _profile(self, name: str, where: str) -> Any:
        from corpus_structure.ingest.profile import SOURCES_DIR, ProfileError, load_profile

        try:
            profile = load_profile(name, self.sources or SOURCES_DIR)
        except (ProfileError, FileNotFoundError) as error:
            raise RegistryError([f"{where}: source profile {name!r}: {error}"]) from None
        return profile.model_dump(mode="json")

    def resolve_all(self, artifacts: Mapping[tuple[str, str], str]) -> dict[str, ResolvedConfig]:
        """Every named configuration of every registered method, by `<method>/<name>`."""
        out, problems = {}, []
        for method, name in self.named():
            try:
                out[f"{method}/{name}"] = self.resolve(method, name, artifacts)
            except RegistryError as error:
                problems += error.problems
        if problems:
            raise RegistryError(problems)
        return out

    def record(
        self, conn: Connection, resolved: Mapping[str, ResolvedConfig]
    ) -> dict[str, ResolvedConfig]:
        """Get or create each configuration's `ops.method` and `ops.method_config` rows."""
        from corpus_structure.core.db import metadata, repo

        method_rows: dict[str, int] = {}
        out = {}
        for key, rc in resolved.items():
            m = self.method(rc.method)
            if rc.method not in method_rows:
                method_rows[rc.method], _ = repo.get_or_create(
                    conn,
                    metadata.tables["ops.method"],
                    {
                        "name": m.name,
                        "version": m.version,
                        "family": m.family.value,
                        "confidence_source": m.confidence_source.value
                        if m.confidence_source
                        else None,
                    },
                    ["name", "version"],
                )
            config_id, _ = repo.get_or_create(
                conn,
                metadata.tables["ops.method_config"],
                {
                    "method_id": method_rows[rc.method],
                    "name": rc.name,
                    "params": dict(rc.params),
                    "config_hash": rc.config_hash,
                    "tier": m.tier.value,
                },
                ["config_hash"],
            )
            out[key] = replace(rc, method_config_id=config_id)
        return out


def artifact_hashes(conn: Connection, schema_version_id: int) -> dict[tuple[str, str], str]:
    """The schema version's artifacts by (compiler, kind), at the installed compiler versions."""
    from corpus_structure.core.db import metadata
    from corpus_structure.schema.compile import COMPILERS, compiler_version

    table = metadata.tables["meta.compiled_artifact"]
    rows = conn.execute(
        select(table.c.compiler, table.c.compiler_version, table.c.kind, table.c.hash).where(
            table.c.schema_version_id == schema_version_id
        )
    )
    installed = {c: compiler_version(c) for c in COMPILERS}
    return {(r[0], r[2]): r[3] for r in rows if installed.get(r[0]) == r[1]}


class RunConfigs:
    """A run's configurations, from its recorded map and the stored rows: every lookup for the run
    after creation (a policy action, a pass-C task days later) reads these."""

    def __init__(self, registry: MethodRegistry, conn: Connection, configs: Mapping[str, str]):
        from corpus_structure.core.db import metadata

        table = metadata.tables["ops.method_config"]
        hashes = sorted(set(configs.values()))
        rows = {
            r.config_hash: r
            for r in conn.execute(
                select(table.c.id, table.c.config_hash, table.c.params).where(
                    table.c.config_hash.in_(hashes)
                )
            )
        }
        self.registry = registry
        self._by_key: dict[str, ResolvedConfig] = {}
        for key, config_hash in configs.items():
            method, name = key.split("/", 1)
            row = rows[config_hash]
            cfg = registry.method(method).Config.model_validate(row.params)
            self._by_key[key] = ResolvedConfig(method, name, cfg, row.params, config_hash, row.id)

    def config(self, method: str, name: str) -> ResolvedConfig:
        key = f"{method}/{name}"
        if key not in self._by_key:
            raise RegistryError([f"{key}: not a configuration this run recorded"])
        return self._by_key[key]

    def method(self, name: str) -> Method[Any]:
        return self.registry.method(name)

    def methods(self) -> Sequence[Method[Any]]:
        return self.registry.methods()

    def items(self) -> Iterable[tuple[str, ResolvedConfig]]:
        return self._by_key.items()
