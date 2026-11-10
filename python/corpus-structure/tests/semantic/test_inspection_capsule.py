"""Detached custody uses the ordinary authenticated archive boundary."""

import json
from hashlib import sha256

import pytest

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.inspection_capsule import make_capsule, open_capsule
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.releases import ReleaseConflict
from corpus_structure.semantic.types import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)


def test_capsule_roundtrip_and_independent_integrity(monkeypatch):
    bundle = SourceBundle(
        "test",
        (
            SourceArtifact(
                "test",
                b"""id: https://example.org/test
name: test
prefixes: {x: 'https://example.org/', xsd: 'http://www.w3.org/2001/XMLSchema#'}
types:
  integer: {base: int, uri: 'xsd:integer'}
default_prefix: x
classes:
  Record:
    attributes:
      number: {range: integer, required: true, minimum_value: 2}
""",
            ),
        ),
    )
    deps, profile = ResolvedDependencies(), PreparationProfile()
    prepared = prepare_release(bundle, deps, profile)
    content = make_capsule(bundle, deps, profile, prepared)

    def forbidden(*args, **kwargs):
        raise AssertionError("opening must not compile")

    monkeypatch.setattr("corpus_structure.semantic.prepare.prepare_release", forbidden)

    def read(raw):
        return open_capsule(
            raw,
            digest=sha256(raw).hexdigest(),
            release_id=prepared.release_id,
            manifest_digest=sha256(prepared.manifest).hexdigest(),
            artifacts_digest=prepared.artifacts_sha256,
        )

    opened = read(content)
    assert opened.artifacts_sha256 == prepared.artifacts_sha256
    assert opened.validate_json("Record", b'{"number": 2}').model_dump()["number"] == 2
    with pytest.raises(ValueError):
        opened.validate_json("Record", b'{"number": 1}')
    data = json.loads(content)
    data["inputs"][0]["content"] = b"changed".hex()
    with pytest.raises(ReleaseConflict, match="input digest differs"):
        read(canonical_bytes(data))
    with pytest.raises(ReleaseConflict, match="capsule digest differs"):
        open_capsule(
            content,
            digest="bad",
            release_id=prepared.release_id,
            manifest_digest="",
            artifacts_digest="",
        )


def test_managed_candidate_contract_is_frozen(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from corpus_structure.cli.app import app
    from corpus_structure.cli.managed import ResultStore
    from corpus_structure.schema.model_deployment import Candidate

    bundle = SourceBundle(
        "test",
        (
            SourceArtifact(
                "test",
                b"""id: https://example.org/test
name: test
types:
  string: {base: str, uri: 'xsd:string'}
classes:
  Record:
    attributes:
      label: {range: string, required: true}
""",
            ),
        ),
    )
    deps, profile = ResolvedDependencies(), PreparationProfile()
    prepared = prepare_release(bundle, deps, profile)
    content = make_capsule(bundle, deps, profile, prepared)
    monkeypatch.setenv("CORPUS_CI_RESULTS", str(tmp_path / "results"))
    store = ResultStore(tmp_path / "results")

    def publish(capsule):
        binding = Candidate(
            workspace="/historical-checkout",
            model_revision="old",
            generator="old",
            revision=None,
            predecessor=None,
            target="retained",
            release=prepared.release_id,
            release_manifest_sha256=sha256(prepared.manifest).hexdigest(),
            release_artifacts_sha256=prepared.artifacts_sha256,
            packs=("test",),
            files={},
            hashes={},
            inspection_sha256=sha256(content).hexdigest() if capsule else None,
        )
        with store.operation("model.candidate") as result:
            path = result.directory / "deployment.json"
            path.write_text(binding.model_dump_json())
            result.publish("deployment", path)
            if capsule:
                path = result.directory / "inspection.json"
                path.write_bytes(capsule)
                result.publish("inspection", path)
            result.settle(sha256=sha256(binding.model_dump_json().encode()).hexdigest())
        return result.id

    valid, old, tampered = publish(content), publish(None), publish(content + b" ")

    def forbidden(*args, **kwargs):
        raise AssertionError("current checkout preparation forbidden")

    monkeypatch.setattr("corpus_structure.cli.model._prepare_release", forbidden)

    def inspect(identifier):
        return CliRunner().invoke(
            app,
            [
                "model",
                "change",
                "inspect-candidate",
                identifier,
                "--view",
                "contract",
                "--subject-kind",
                "class",
                "--subject",
                "Record",
                "--json",
            ],
        )

    result = inspect(valid)
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)["release_id"] == prepared.release_id
    result = inspect(old)
    assert result.exit_code != 0
    assert "unavailable" in result.output
    result = inspect(tampered)
    assert result.exit_code != 0
    assert "digest differs" in result.output
