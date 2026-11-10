"""Independent selected scientific meaning, closed inputs and descriptive metadata custody."""

import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.ontology import (
    OntologyError,
    OntologyPreparation,
    resolve_vocabularies,
)
from corpus_structure.semantic.prepare import _view, prepare_release
from corpus_structure.semantic.terminology import (
    ARTIFACT,
    acquire_terminology,
    decode_vocabulary_metadata,
)
from corpus_structure.semantic.types import (
    PreparedArtifact,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)

ROOT = Path(__file__).parents[4]
PACK = ROOT / "domains/statistics"
SOURCE = PACK / "terminology/sources"


@pytest.fixture(scope="module")
def terminology_release():
    sources, artifacts, names = acquire_terminology(PACK)
    core = (
        Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    ).read_bytes()
    return prepare_release(
        SourceBundle(sources[0].name, (*sources, SourceArtifact("semantic_core", core))),
        ResolvedDependencies(artifacts, (), names),
    )


def test_selected_fields_and_mathematical_moments(terminology_release):
    detail = decode_vocabulary_metadata(terminology_release)
    assert detail["status"] == "available"
    family = detail["enums"]["StatisticalDistributionFamily"]
    assert {(m["value"], m["meaning"]) for m in family["members"]} == {
        ("hypergeometric", "STATO:0000060"),
        ("normal", "STATO:0000227"),
        ("binomial", "STATO:0000276"),
        ("poisson", "STATO:0000051"),
        ("gamma", "STATO:0000268"),
        ("exponential", "STATO:0000160"),
    }
    attributes = detail["enums"]["StatisticalDistributionAttribute"]
    variance = next(m for m in attributes["members"] if m["value"] == "variance")
    assert variance["meaning"] == "STATO:0000693"
    assert variance["label"] == "probability distribution variance"
    assert variance["definitions"] and variance["status"] == "checked"
    assert attributes["fields"] == [
        {"class_name": "StatisticalTerminologyFields", "property": "distribution_attribute"}
    ]
    assert variance["coverage"]["owl_equivalence"] == "unassessed"
    assert all(
        m["predicate"] != "http://www.w3.org/2004/02/skos/core#exactMatch"
        for m in variance["mappings"]
        if m["predicate"].endswith("hasDbXref")
    )
    cls = terminology_release.validate_json(
        "StatisticalTerminologyFields", b'{"distribution_attribute":"variance"}'
    )
    assert cls.model_dump(mode="json")["distribution_attribute"] == "variance"
    with pytest.raises(ValueError):
        terminology_release.validate_json(
            "StatisticalTerminologyFields", b'{"distribution_attribute":"sample_variance"}'
        )


def test_metadata_opens_without_ontology_and_retains_unavailable_old_detail(
    terminology_release, monkeypatch
):
    def forbidden(*args, **kwargs):
        raise AssertionError("ordinary metadata read cannot prepare an ontology")

    monkeypatch.setattr(OntologyPreparation, "__init__", forbidden)
    assert decode_vocabulary_metadata(terminology_release)["status"] == "available"
    old = replace(
        terminology_release,
        artifacts=tuple(a for a in terminology_release.artifacts if a.kind != ARTIFACT),
    )
    assert decode_vocabulary_metadata(old)["status"] == "corrupt"
    manifest = json.loads(old.manifest)
    manifest["profile"]["compiler_version"] = "20"
    assert (
        decode_vocabulary_metadata(replace(old, manifest=canonical_bytes(manifest)))["status"]
        == "unavailable"
    )
    for replacement, status in (
        ({"version": 99}, "unsupported"),
        ({"version": 1}, "corrupt"),
        ({"version": True}, "corrupt"),
    ):
        changed = replace(
            terminology_release,
            artifacts=tuple(
                PreparedArtifact(a.kind, canonical_bytes(replacement)) if a.kind == ARTIFACT else a
                for a in terminology_release.artifacts
            ),
        )
        assert decode_vocabulary_metadata(changed)["status"] == status


def test_pinned_conversion_is_deterministic_across_processes():
    code = (
        "from pathlib import Path;from hashlib import sha256;"
        "from corpus_structure.semantic.terminology import convert_stato;"
        f"obo,warnings=convert_stato(Path({str(SOURCE / 'stato-2026-04-20.owl')!r})"
        ".read_bytes());"
        "import json;print(sha256(obo).hexdigest(),"
        "sha256(json.dumps(warnings).encode()).hexdigest())"
    )
    outputs = []
    for seed in ("0", "1"):
        answer = subprocess.run(
            [sys.executable, "-c", code],
            env=dict(os.environ, PYTHONHASHSEED=seed),
            capture_output=True,
            text=True,
            check=True,
        )
        outputs.append(answer.stdout.strip())
        assert (
            outputs[-1].split()[0]
            == "2e4438fb7246e7dc53a90fa04d79eda423b4906910c101608614e4289d9c6581"
        )
    assert outputs[0] == outputs[1]


def test_acquisition_refuses_source_mutation(tmp_path):
    root = tmp_path / "terminology/sources"
    root.mkdir(parents=True)
    (tmp_path / "terminology.yaml").write_text((PACK / "terminology.yaml").read_text())
    (root / "source.json").write_text((SOURCE / "source.json").read_text())
    (root / "stato-2026-04-20.owl").write_bytes(b"changed")
    with pytest.raises(ValueError, match="digest differs"):
        acquire_terminology(tmp_path)


def test_shared_preparation_is_bound_to_exact_source_bytes(tmp_path):
    body = b"format-version: 1.2\nontology: test\n\n[Term]\nid: EX:1\nname: actual\n"
    path = tmp_path / "source.obo"
    path.write_bytes(body)
    schema = SourceBundle(
        "x",
        (
            SourceArtifact(
                "x",
                b"""id: https://example.org/test
name: x
enums:
  Values:
    permissible_values: {actual: {meaning: 'EX:1'}}
""",
            ),
        ),
    )
    operation = OntologyPreparation({"test": body + b"!wrong"})
    with pytest.raises(OntologyError, match="source bytes differ"):
        resolve_vocabularies(_view(schema), {"test": path}, preparation=operation)


def test_checked_metadata_cannot_drop_snapshot_unknowns(terminology_release):
    artifact = next(a for a in terminology_release.artifacts if a.kind == ARTIFACT)
    body = json.loads(artifact.content)
    body["enums"]["StatisticalDistributionAttribute"]["unchecked"] = []
    modified = replace(
        terminology_release,
        artifacts=tuple(
            PreparedArtifact(a.kind, canonical_bytes(body)) if a.kind == ARTIFACT else a
            for a in terminology_release.artifacts
        ),
    )
    assert decode_vocabulary_metadata(modified)["status"] == "corrupt"


def test_conversion_qualification_refuses_changed_selected_meaning():
    from corpus_structure.semantic.terminology import qualify_conversion

    original = (SOURCE / "stato-2026-04-20.owl").read_bytes()
    converted = (
        (SOURCE / "stato-2026-04-20.obo")
        .read_bytes()
        .replace(b"name: normal distribution\n", b"name: wrong meaning\n")
    )
    with pytest.raises(ValueError, match="selected label differs"):
        qualify_conversion(original, converted, ["STATO:0000227"])


def test_mult_pack_composition_retains_terminology_sources():
    from corpus_structure.semantic.regeneration import acquire_pack, compose_pack_inputs
    from corpus_structure.semantic.terminology import CONVERTED, ORIGINAL, PROFILE

    bundle, deps, _profile = compose_pack_inputs(
        (acquire_pack(PACK), acquire_pack(ROOT / "domains/toy"))
    )
    names = {artifact.name for artifact in deps.artifacts}
    assert {ORIGINAL, CONVERTED, PROFILE} <= names
    assert CONVERTED in deps.ontology_sources
    assert not any(name.startswith("pack/statistics/terminology/") for name in names)
    assert any(source.name == "statistics_terminology" for source in bundle.sources)
