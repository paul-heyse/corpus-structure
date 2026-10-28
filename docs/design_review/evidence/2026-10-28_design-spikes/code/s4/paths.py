"""Inputs and outputs of S4, and batch loading."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

CODE = Path(__file__).resolve().parent.parent
EV = CODE.parent
REPO = EV.parents[3]
RES = EV / "results" / "s4"
SCHEMA_ROOT = RES / "schema"
DOMAINS = SCHEMA_ROOT / "domains"
CORE_YAML = DOMAINS / "core" / "schema" / "core.yaml"
CORE_RULES = DOMAINS / "core" / "schema" / "rules.yaml"
PACK = DOMAINS / "statistics"
PACK_YAML = PACK / "schema" / "statistics.yaml"
PACK_RULES = PACK / "schema" / "rules.yaml"
PACK_REFERENCE = PACK / "reference"
LINT_CONFIG = SCHEMA_ROOT / ".linkmllint.yaml"
COMPILED = RES / "compiled"

R2 = EV / "results" / "s0r2"
S0 = EV / "results" / "s0"
SR_REFERENCE_MD = R2 / "inputs" / "packet_v1" / "reference.md"
EXAMPLE_PACKETS = R2 / "inputs" / "example_packets"

QWEN = Path.home() / ".cache/huggingface/hub/models--Qwen--Qwen3.5-9B/snapshots/c202236235762e1c871ad0ccb60c8ee5ba337b9a"
GLINER = Path.home() / ".cache/huggingface/hub/models--fastino--gliner2.5-base-v1/snapshots/54785d51df8d86a0d8f2eb212fec15871aad2c4d"


def rel(p: Path) -> str:
    return str(p.relative_to(EV))


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def load_batch(path: Path) -> tuple[dict, dict | None]:
    """(batch, envelope) from a batch file; the spike envelope is outside the D2 contract."""
    d = json.loads(path.read_text(encoding="utf-8"))
    if set(d) == {"envelope", "batch"}:
        return d["batch"], d["envelope"]
    env = d.pop("envelope", None)
    return d, env


def batch_sets() -> list[tuple[str, str, list[Path]]]:
    """(set name, form, files) for every batch S4 validates (brief step 5)."""
    units = lambda d: sorted(p for p in d.glob("*.json") if p.stem[0] in "TUEH" and p.stem[1:].isdigit())  # noqa: E731
    out = [
        ("v1.model", "model", units(R2 / "reference_model_v1")),
        ("examples", "model", units(R2 / "examples")),
        ("v1.stored", "stored", units(R2 / "reference_v1")),
        ("s0.reference", "stored", units(S0 / "reference")),
    ]
    for d in sorted((S0 / "stored").iterdir()):
        if d.is_dir():
            out.append((f"s0.stored.{d.name}", "stored", units(d)))
    return out
