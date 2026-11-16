"""Historical bytes stay inert; exact source regeneration uses the current compiler."""

import gzip
import json
from dataclasses import replace
from functools import cache
from pathlib import Path

import pytest

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.archive_reader import reconstruct_release
from corpus_structure.semantic.comparison_projection import ARTIFACT as COMPARISON_ARTIFACT
from corpus_structure.semantic.comparison_projection import comparison_projection
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.record_projection import ARTIFACT, read_record_projection
from corpus_structure.semantic.types import (
    SEMANTIC_COMPILER_VERSION,
    PreparationError,
    PreparationProfile,
    PreparedArtifact,
)

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = (
    ROOT
    / "docs/design_review/evidence/2026-11-03_m1-public-record-projection"
    / "raw/compiler14-source-record-archive.json.gz"
)


@cache
def archive():
    data = json.loads(gzip.decompress(FIXTURE.read_bytes()))
    bundle = SourceBundle(
        data["bundle"]["root"],
        tuple(
            SourceArtifact(row["name"], bytes.fromhex(row["content_hex"]))
            for row in data["bundle"]["sources"]
        ),
    )
    artifacts = tuple(
        PreparedArtifact(row["kind"], bytes.fromhex(row["content_hex"]))
        for row in data["artifacts"]
    )
    return data, bundle, artifacts


def opened_archive():
    data, bundle, artifacts = archive()
    return reconstruct_release(
        data["products"],
        bytes.fromhex(data["manifest_hex"]),
        bundle,
        PreparationProfile(**data["profile"]),
        artifacts,
    )


def test_genuine_compiler14_archive_refuses_without_recompiling(monkeypatch):
    import corpus_structure.semantic.prepare as compiler

    def forbidden(*args, **kwargs):
        raise AssertionError("archived read must not invoke the installed compiler")

    monkeypatch.setattr(compiler, "prepare_release", forbidden)
    with pytest.raises(ValueError, match="unsupported archived compiler 14"):
        opened_archive()


def test_historical_sources_can_be_regenerated_on_current_basis():
    data, same_sources, _ = archive()
    new = prepare_release(same_sources)
    assert json.loads(new.manifest)["profile"]["compiler_version"] == SEMANTIC_COMPILER_VERSION
    assert new.release_id != data["products"]["release_id"]
    assert len([artifact for artifact in new.artifacts if artifact.kind == ARTIFACT]) == 1
    assert comparison_projection(new).compiler_version == SEMANTIC_COMPILER_VERSION
    assert read_record_projection(new)["abi"] == "source-record-projection-2"


def test_historical_compiler_cannot_produce_current_products():
    data, bundle, _ = archive()
    with pytest.raises(PreparationError, match="unsupported profile"):
        prepare_release(bundle, profile=PreparationProfile(**data["profile"]))


def test_comparison_artifact_rejects_a_retired_compiler_stamp():
    _, bundle, _ = archive()
    current = prepare_release(bundle)
    artifacts = []
    for artifact in current.artifacts:
        if artifact.kind == COMPARISON_ARTIFACT:
            data = json.loads(artifact.content)
            data["compiler_version"] = "15"
            artifact = PreparedArtifact(artifact.kind, canonical_bytes(data))
        artifacts.append(artifact)
    with pytest.raises(ValueError, match="compiler_version"):
        comparison_projection(replace(current, artifacts=tuple(artifacts)))
