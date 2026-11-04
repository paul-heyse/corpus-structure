"""A genuine compiler14 source-record archive remains readable after M1 projection changes."""

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
from corpus_structure.semantic.types import PreparationProfile, PreparedArtifact

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


def test_genuine_compiler14_archive_reads_without_recompiling(monkeypatch):
    import corpus_structure.semantic.prepare as compiler

    def forbidden(*args, **kwargs):
        raise AssertionError("archived read must not invoke the installed compiler")

    monkeypatch.setattr(compiler, "prepare_release", forbidden)
    old = opened_archive()
    assert (
        old.release_id == "release:8cc0f7922d77b7a3faddbec82e481e4d4448597e42746d58ec387eafcdb34fd9"
    )
    assert old.validate_python("RecordText", {"kind": "text", "text": "retained"}).model_dump() == {
        "kind": "text",
        "text": "retained",
    }
    assert comparison_projection(old).compiler_version == "14"


def test_new_record_projection_gets_a_new_compiler_identity_for_identical_sources():
    _, same_sources, _ = archive()
    old = opened_archive()
    new = prepare_release(same_sources)
    assert json.loads(new.manifest)["profile"]["compiler_version"] == "16"
    assert new.release_id != old.release_id
    assert not any(artifact.kind == ARTIFACT for artifact in old.artifacts)
    assert len([artifact for artifact in new.artifacts if artifact.kind == ARTIFACT]) == 1
    assert comparison_projection(new).compiler_version == "16"
    assert read_record_projection(new)["abi"] == "source-record-projection-1"


def test_old_archive_does_not_acquire_a_projection_from_installed_code():
    with pytest.raises(ValueError, match="projection"):
        read_record_projection(opened_archive())


def test_comparison_artifact_stamp_must_match_its_release():
    old = opened_archive()
    artifacts = []
    for artifact in old.artifacts:
        if artifact.kind == COMPARISON_ARTIFACT:
            data = json.loads(artifact.content)
            data["compiler_version"] = "15"
            artifact = PreparedArtifact(artifact.kind, canonical_bytes(data))
        artifacts.append(artifact)
    with pytest.raises(ValueError, match="compiler differs"):
        comparison_projection(replace(old, artifacts=tuple(artifacts)))
