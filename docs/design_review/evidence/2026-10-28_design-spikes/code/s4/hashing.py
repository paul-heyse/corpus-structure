"""Canonical JSON (D1 §10.1) and the schema version hash (D2 §2; schema-rules note L-07)."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from pathlib import Path

import yaml

from . import paths


def _nfc(o):
    if isinstance(o, str):
        return unicodedata.normalize("NFC", o)
    if isinstance(o, float):
        raise TypeError(f"float {o!r} refused in canonical JSON (D1 §10.1)")
    if isinstance(o, list | tuple):
        return [_nfc(v) for v in o]
    if isinstance(o, dict):
        out = {}
        for k, v in o.items():
            nk = _nfc(str(k))
            if nk in out:
                raise ValueError(f"keys equal after NFC: {k!r}")
            out[nk] = _nfc(v)
        return out
    return o


def canonical_json(o) -> bytes:
    return json.dumps(_nfc(o), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_canonical(o) -> str:
    return hashlib.sha256(canonical_json(o)).hexdigest()


def schema_sources(domains: Path = paths.DOMAINS, pack: str = "statistics") -> dict:
    """Parsed hash inputs keyed by their path under domains/: the pack schema, the pack and core rules
    files, the imported core schema, and the worked examples (packet text as a string, batch parsed)."""
    files = [
        f"core/schema/core.yaml",
        f"core/schema/rules.yaml",
        f"{pack}/schema/{pack}.yaml",
        f"{pack}/schema/rules.yaml",
    ]
    out = {f: yaml.safe_load((domains / f).read_text(encoding="utf-8")) for f in files}
    ref = domains / pack / "reference"
    for d in sorted(p for p in ref.iterdir() if p.is_dir()) if ref.exists() else []:
        out[f"{pack}/reference/{d.name}/packet.md"] = (d / "packet.md").read_text(encoding="utf-8")
        out[f"{pack}/reference/{d.name}/batch.json"] = json.loads((d / "batch.json").read_text(encoding="utf-8"))
    return out


def schema_version_hash(domains: Path = paths.DOMAINS, pack: str = "statistics") -> str:
    return sha256_canonical(schema_sources(domains, pack))
