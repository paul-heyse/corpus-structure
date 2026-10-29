"""Composed inputs remain explicit, exact and outside the domain schema namespace."""

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
    composed_dependencies,
    execution_model_from_dependencies,
)
from corpus_structure.semantic.contracts import compile_execution_model, trusted_execution_inputs


def domain():
    return SourceBundle(
        "domain",
        (
            SourceArtifact(
                "domain",
                b"id: https://example.org/domain\nname: domain\n"
                b"prefixes: {ex: 'https://example.org/'}\n"
                b"default_prefix: ex\nclasses: {Thing: {}}\n",
            ),
        ),
    )


def test_composed_inputs_roundtrip_and_domain_namespace():
    trusted = trusted_execution_inputs()
    dependencies = composed_dependencies(ResolvedDependencies(), trusted)
    actual = execution_model_from_dependencies(dependencies)
    assert actual == compile_execution_model(trusted)
    prepared = prepare_release(domain(), dependencies, PreparationProfile(version="semantic-2"))
    assert prepared.execution_model_id == actual.model_id
    assert {d.name for d in prepared.definitions} == {"Thing"}
    assert "execution.lifecycle.v1" in prepared.required_capabilities
    assert (
        next(a.content for a in prepared.artifacts if a.kind == "execution/contracts.json")
        == actual.content
    )


def test_composed_profile_never_implicitly_acquires_installed_inputs():
    with pytest.raises(PreparationError, match="execution"):
        prepare_release(domain(), profile=PreparationProfile(version="semantic-2"))


def test_baseline_does_not_ignore_reserved_execution_inputs():
    with pytest.raises(PreparationError, match="execution"):
        prepare_release(domain(), composed_dependencies(ResolvedDependencies()))


def test_extra_reserved_input_is_not_silently_archived():
    dependencies = composed_dependencies(ResolvedDependencies())
    malformed = replace(
        dependencies,
        artifacts=(*dependencies.artifacts, SourceArtifact("execution/unexpected", b"x")),
    )
    with pytest.raises(ValueError, match="input set"):
        execution_model_from_dependencies(malformed)


def test_duplicate_reserved_input_refused():
    dependencies = composed_dependencies(ResolvedDependencies())
    malformed = replace(
        dependencies, artifacts=(*dependencies.artifacts, dependencies.artifacts[0])
    )
    with pytest.raises(ValueError, match="duplicate"):
        execution_model_from_dependencies(malformed)
