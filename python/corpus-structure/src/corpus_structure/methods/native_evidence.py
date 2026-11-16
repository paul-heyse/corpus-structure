"""Native linguistic layer metadata and exact shared source/head kernels.

Current producers live in sentence_products, canonical_sentences and hanlp_products.
This module supplies only kernels still consumed by retained layer readers/producers.
"""

from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
from typing import Any

from .native_evidence_layers import NativeEvidenceBuilder, digest

MODEL = "spacy-en_core_web_sm-3.8.0+hanlp-modernbert-large-20250107"


def native_run(
    provider: str,
    profile: str,
    configuration: str,
    *,
    model: str,
    version: str,
    runtime_version: str,
    layout: Any,
    text: Any,
    components=(),
    packages=(),
    artifacts=(),
    limits=(),
    diagnostics=(),
) -> dict[str, Any]:
    return dict(
        local_id=provider,
        provider=provider,
        profile=profile,
        model=model,
        model_version=version,
        runtime_version=runtime_version,
        configuration=configuration,
        configuration_codec="spacy-config-v1" if provider == "spacy" else "hanlp-config-json-v1",
        configuration_digest=sha256(configuration.encode()).hexdigest(),
        layout_recipe="canonical-token-layout-1",
        layout_digest=digest(layout),
        text_digest=digest(text),
        components=list(components),
        availability=[],
        runtime_packages=list(packages),
        artifacts=list(artifacts),
        limits=list(limits),
        diagnostics=list(diagnostics),
    )


def _availability(builder: NativeEvidenceBuilder, provider: str) -> list[dict[str, Any]]:
    rows = []
    for family in builder.families:
        if not family.startswith(provider + "."):
            continue
        covered = builder.covered[family]
        statuses = {status for _, status, _ in covered}
        status = (
            "absent"
            if not covered or statuses <= {"failed", "unsupported"}
            else "complete"
            if statuses <= {"complete", "empty"}
            else "partial"
        )
        row = dict(family=family, attribute=family.partition(".")[2], status=status)
        reasons = list(dict.fromkeys(reason for _, _, reason in covered if reason))
        if reasons:
            row["reason"] = "; ".join(reasons)
        rows.append(row)
    return rows


def _native_heads(document: Mapping[str, Any], index: int, population: int) -> dict[str, Any]:
    heads = {}
    for name, family in (
        ("lem", "lemma"),
        ("pos", "pos"),
        ("dep", "dependency"),
        ("con", "constituency"),
        ("srl", "srl"),
    ):
        columns = [v for k, v in document.items() if k.split("/")[0] == name]
        if len(columns) == 1 and isinstance(columns[0], list) and len(columns[0]) == population:
            heads[family] = columns[0][index]
    return heads


def _artifacts(startup: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for group, manifest in startup.get("assets", {}).items():
        rows.extend(
            dict(name=f"{group}/{name}", sha256=pin["sha256"], size=pin["size"])
            for name, pin in manifest["files"].items()
        )
    runtime = startup.get("runtime_identity", {})
    rows.extend(
        dict(name="runtime/" + name, sha256=value)
        for name, value in runtime.items()
        if name.endswith("_sha256")
    )
    return rows
