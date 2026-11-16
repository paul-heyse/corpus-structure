"""Explicit current operation inputs remain closed and outside the schema namespace."""

import json
from dataclasses import replace

import pytest

from corpus_structure.semantic import (
    PreparationError,
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
    prepare_release,
)
from corpus_structure.semantic.composed import (
    data_operation_dependencies,
    read_data_operation_inputs,
)
from corpus_structure.semantic.data_operation_model import MODEL_VERSION


def domain():
    return SourceBundle(
        "domain",
        (
            SourceArtifact(
                "domain",
                b"""id: https://example.org/domain
name: domain
prefixes: {ex: 'https://example.org/'}
default_prefix: ex
classes: {Thing: {}}
""",
            ),
        ),
    )


def dependencies():
    return data_operation_dependencies(
        ResolvedDependencies(),
        (
            SourceArtifact(
                "operations.yaml",
                json.dumps(dict(version=MODEL_VERSION, operations=[], kinds=[])).encode(),
            ),
        ),
    )


@pytest.mark.parametrize("version", ["semantic-1", "semantic-2"])
def test_explicit_current_inputs_roundtrip_and_domain_namespace(version):
    supplied = dependencies()
    declarations, python = read_data_operation_inputs(supplied)
    assert declarations[0].name == "operations.yaml" and python is None
    prepared = prepare_release(domain(), supplied, PreparationProfile(version=version))
    assert {definition.name for definition in prepared.definitions} == {"Thing"}
    assert json.loads(prepared.manifest)["data_operation_model"]
    assert "data_operations.json" in {artifact.kind for artifact in prepared.artifacts}
    assert not any(item.name.startswith("execution/") for item in supplied.artifacts)


@pytest.mark.parametrize("version", ["semantic-1", "semantic-2"])
def test_schema_profile_does_not_implicitly_supply_execution_authority(version):
    prepared = prepare_release(domain(), profile=PreparationProfile(version=version))
    assert not any(artifact.kind == "data_operations.json" for artifact in prepared.artifacts)
    assert "data_operation_model" not in json.loads(prepared.manifest)


@pytest.mark.parametrize("version", ["semantic-1", "semantic-2"])
def test_reserved_legacy_execution_inputs_refuse(version):
    with pytest.raises(PreparationError, match="execution"):
        prepare_release(
            domain(),
            ResolvedDependencies((SourceArtifact("execution/manifest.json", b"{}"),)),
            PreparationProfile(version=version),
        )


def test_extra_reserved_input_is_not_silently_archived():
    supplied = dependencies()
    with pytest.raises(ValueError, match="input set"):
        read_data_operation_inputs(
            replace(
                supplied,
                artifacts=(*supplied.artifacts, SourceArtifact("data-operations/unexpected", b"x")),
            )
        )


def test_duplicate_reserved_input_refused():
    supplied = dependencies()
    with pytest.raises(ValueError, match="closed manifest"):
        read_data_operation_inputs(
            replace(supplied, artifacts=(*supplied.artifacts, supplied.artifacts[0]))
        )
