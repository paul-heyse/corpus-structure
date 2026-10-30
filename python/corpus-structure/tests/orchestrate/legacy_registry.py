"""Historical installed-model registry oracle, excluded from product execution."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import replace
from typing import Any

from sqlalchemy import Connection, select

from corpus_structure.core.method import Method, ResolvedConfig
from corpus_structure.orchestrate.registry import MethodRegistry, RegistryError


def record(
    registry: MethodRegistry, conn: Connection, resolved: Mapping[str, ResolvedConfig]
) -> dict[str, ResolvedConfig]:
    """Get or create each configuration's `ops.method` and `ops.method_config` rows."""
    import legacy_db_repo as repo

    from corpus_structure.core.db.legacy_metadata import metadata

    method_rows: dict[str, int] = {}
    out = {}
    for key, rc in resolved.items():
        m = registry.method(rc.method)
        if rc.method not in method_rows:
            method_rows[rc.method], _ = repo.get_or_create(
                conn,
                metadata.tables["ops.method"],
                {
                    "name": m.name,
                    "version": m.version,
                    "family": m.family.value,
                    "confidence_source": m.confidence_source.value if m.confidence_source else None,
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


class RunConfigs:
    """A run's configurations, from its recorded map and the stored rows: every lookup for the run
    after creation (a policy action, a pass-C task days later) reads these."""

    def __init__(self, registry: MethodRegistry, conn: Connection, configs: Mapping[str, str]):
        from corpus_structure.core.db.legacy_metadata import metadata

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
