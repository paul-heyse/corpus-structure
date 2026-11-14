"""Shared controlled inputs and builders for archive reader support."""

from __future__ import annotations

import json
from pathlib import Path

from corpus_structure.semantic.types import PreparedArtifact, SourceArtifact, SourceBundle

_FIXTURE = Path(__file__).parents[1] / "fixtures/semantic/reader-v10.json"


def archived(path: Path = _FIXTURE):
    data = json.loads(path.read_bytes())
    bundle = SourceBundle(
        data["root"],
        tuple(
            SourceArtifact(item["name"], bytes.fromhex(item["content"])) for item in data["sources"]
        ),
    )
    artifacts = tuple(
        PreparedArtifact(item["kind"], bytes.fromhex(item["content"])) for item in data["artifacts"]
    )
    return data, bundle, artifacts
