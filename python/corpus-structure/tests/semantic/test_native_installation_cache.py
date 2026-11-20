"""Generation reuse follows captured sources and explicit candidate overrides."""

import pytest
from sqlalchemy import MetaData

from corpus_structure.semantic import target_installation as installation
from corpus_structure.semantic.types import SourceArtifact


@pytest.fixture
def uncached_generation(monkeypatch):
    from corpus_structure.model import compiled
    from corpus_structure.semantic import (
        native_generation,
        native_program_store,
        native_protocol_authoring,
    )
    from corpus_structure.semantic.code_identity import CodeIdentity, CodeUnknown
    from corpus_structure.semantic.types import SourceArtifact

    monkeypatch.setattr(
        native_program_store,
        "capture_generator_code",
        lambda: CodeIdentity(
            entries=("corpus_structure.semantic.target_installation",),
            modules=(),
            distributions=(),
            unknowns=(CodeUnknown("generator", 1, "unresolved input"),),
            meaning=b"incomplete generator identity",
        ),
    )
    monkeypatch.setattr(native_program_store, "capture_generator_sources", lambda identity: ())
    from corpus_structure.semantic.native_objects import NativeIdentity

    trigger_inputs = installation.PhysicalTriggerInputs(
        "controlled_publisher", NativeIdentity("table", "ops", "task"), ()
    )
    monkeypatch.setattr(
        native_generation, "capture_trigger_inputs", lambda selected: trigger_inputs
    )
    monkeypatch.setattr(
        native_protocol_authoring,
        "native_logical_sources",
        lambda **options: {"logical": b"default"},
    )
    monkeypatch.setattr(
        native_protocol_authoring,
        "capture_native_package_resource",
        lambda: SourceArtifact("native/validity-vocabulary.yaml", b"vocabulary"),
    )
    model = compiled.compiled_model({"cache-control.yaml": b"id: urn:cache\nname: cache\n"})
    monkeypatch.setattr(compiled, "running_model", lambda: model)
    calls = []

    def render(inputs):
        calls.append(inputs)
        return object()

    monkeypatch.setattr(native_generation, "_render_captured", render)
    return calls


def metadata(source=b"original"):
    value = MetaData()
    value.info.update(physical_sources={"root": source}, physical_linkml_types=b"types")
    return value


def test_incomplete_identity_bypasses_process_holder_and_renders_fresh(uncached_generation):
    logical = {"logical": b"initial"}
    installation.capture_target_installation(metadata(), logical_sources=logical)
    installation.capture_target_installation(metadata(), logical_sources=dict(logical))
    installation.capture_target_installation(metadata(b"candidate"), logical_sources=logical)
    installation.capture_target_installation(metadata(), logical_sources={"logical": b"changed"})
    pdf = SourceArtifact("pdf/action", b"candidate")
    installation.capture_target_installation(metadata(), logical_sources=logical, pdf_actions=pdf)
    assert len(uncached_generation) == 5
    assert uncached_generation[0].physical_sources != uncached_generation[2].physical_sources


def test_incomplete_identity_does_not_retain_generation_failure(uncached_generation, monkeypatch):
    from corpus_structure.semantic import native_generation

    calls = []

    def fail(*args, **kwargs):
        calls.append(1)
        raise ValueError("invalid candidate declaration")

    monkeypatch.setattr(native_generation, "_render_captured", fail)
    for _ in range(2):
        with pytest.raises(ValueError, match="invalid candidate declaration"):
            installation.capture_target_installation(metadata(), logical_sources={})
    assert len(calls) == 2
