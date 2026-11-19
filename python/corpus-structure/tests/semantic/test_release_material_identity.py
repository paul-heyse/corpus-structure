"""Release identity follows material capture and generated products."""

import json
from dataclasses import replace
from hashlib import sha256

import pytest

from corpus_structure.semantic.determinants import release_library_versions
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.release_identity import material_dependencies, release_manifest
from corpus_structure.semantic.releases import _archive_bytes
from corpus_structure.semantic.types import (
    PreparationProfile,
    PreparedArtifact,
    ResolvedDependencies,
    SourceArtifact,
)
from semantic.releases_support import source_bundle


@pytest.mark.parametrize(("authoring", "transport"), [(True, False), (False, True)])
def test_nonmaterial_capture_change_preserves_release_and_exact_archive(authoring, transport):
    from corpus_structure.semantic.inspection_capsule import make_capsule, open_capsule_inputs

    source = source_bundle()
    old = ResolvedDependencies(
        (
            SourceArtifact(
                "acquisition", b"first", authoring_provenance=authoring, runtime_transport=transport
            ),
        )
    )
    changed = replace(old, artifacts=(replace(old.artifacts[0], content=b"second"),))
    first, second = (prepare_release(source, item) for item in (old, changed))
    assert first.release_id == second.release_id
    assert first.artifacts_sha256 == second.artifacts_sha256
    assert _archive_bytes(source, old, first) == _archive_bytes(source, changed, second)
    capsule = make_capsule(source, old, PreparationProfile(), first)
    assert capsule == make_capsule(source, changed, PreparationProfile(), second)
    _, captured, _, opened = open_capsule_inputs(
        capsule,
        digest=sha256(capsule).hexdigest(),
        release_id=first.release_id,
        manifest_digest=sha256(first.manifest).hexdigest(),
        artifacts_digest=first.artifacts_sha256,
    )
    assert not captured.artifacts
    assert opened.release_id == first.release_id
    assert material_dependencies(old).artifacts == ()
    manifest = json.loads(first.manifest)
    assert manifest["dependencies"] == []
    assert manifest["artifacts"] == sorted([[item.kind, item.digest] for item in first.artifacts])
    assert first.release_id == "release:" + sha256(first.manifest).hexdigest()


def test_material_and_generated_byte_changes_move_identity_independently():
    source = source_bundle()
    dependencies = ResolvedDependencies((SourceArtifact("policy", b"material"),))
    prepared = prepare_release(source, dependencies)
    changed_source = replace(
        dependencies, artifacts=(replace(dependencies.artifacts[0], content=b"changed"),)
    )
    assert prepare_release(source, changed_source).release_id != prepared.release_id
    changed_output = replace(
        prepared, artifacts=(*prepared.artifacts, PreparedArtifact("new-output", b"result"))
    )
    assert (
        release_manifest(
            source,
            dependencies,
            PreparationProfile(),
            changed_output,
            release_library_versions(dependencies),
        )
        != prepared.manifest
    )


def test_pdf_lowering_provenance_does_not_change_installed_pdf_domain_programs():
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.pdf_domain import pdf_domain_sources
    from corpus_structure.semantic.pdf_domain_native import pdf_domain_native_programs
    from corpus_structure.semantic.pdf_lowering import PRODUCER_IDENTITY_INPUTS

    contract, *inputs = pdf_domain_sources(include_producer=False)
    capture = json.loads(contract.content)
    capture["inputs"].extend(
        {"name": name, "sha256": "1" * 64} for name in sorted(PRODUCER_IDENTITY_INPUTS)
    )
    different_producer = (replace(contract, content=canonical_bytes(capture)), *inputs)

    def statements(sources):
        return tuple(
            program.routine.render() for program in pdf_domain_native_programs(sources=sources)
        )

    frozen = statements((contract, *inputs))
    assert statements(different_producer) == frozen
    capture["inputs"][0]["sha256"] = "2" * 64
    different_native_basis = (replace(contract, content=canonical_bytes(capture)), *inputs)
    assert statements(different_native_basis) != frozen


def test_transport_acquisition_is_retained_by_runtime_and_excluded_from_semantics():
    from corpus_structure.semantic.composed import (
        data_operation_dependencies,
        read_data_operation_inputs,
        runtime_transport_inputs,
    )
    from corpus_structure.semantic.data_operation_runtime import RuntimeBinding
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.python_operation_sources import PythonSourceCollection

    transport = SourceArtifact(
        "pdf-capture/execution-custody", b'{"directory":"/first"}', runtime_transport=True
    )
    policy = SourceArtifact("policy", b"{}", reuse_eligible=False)
    capture = data_operation_dependencies(
        ResolvedDependencies(),
        python_sources=PythonSourceCollection((), boundary_contracts=(policy, transport)),
    )
    material = material_dependencies(capture)
    assert any(item.name == "runtime-transport/" + transport.name for item in capture.artifacts)
    assert all(not item.runtime_transport for item in material.artifacts)
    decoded = read_data_operation_inputs(material)
    assert decoded is not None
    _, semantic_sources = decoded
    assert semantic_sources is not None
    assert [(item.name, item.reuse_eligible) for item in semantic_sources.boundary_contracts] == [
        ("policy", False)
    ]
    manifest = json.loads(
        next(
            item.content
            for item in material.artifacts
            if item.name == "data-operations/manifest.json"
        )
    )
    assert transport.name not in manifest["python"]["boundary_contracts"]
    name = "runtime-transport/" + transport.name
    runtime = RuntimeBinding(
        "release:opaque",
        "runtime:opaque",
        canonical_bytes({"implementation_inputs": [{"name": name, "sha256": transport.digest}]}),
        canonical_bytes({"inputs": [{"name": name, "content_hex": transport.content.hex()}]}),
    )
    assert runtime_transport_inputs(runtime) == (transport,)
