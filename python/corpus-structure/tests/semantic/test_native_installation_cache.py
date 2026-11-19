"""Generation reuse follows captured sources and explicit candidate overrides."""

import pytest
from sqlalchemy import MetaData

from corpus_structure.semantic import target_installation as installation
from corpus_structure.semantic.types import SourceArtifact


@pytest.fixture
def held_generation(monkeypatch):
    from corpus_structure.model import compiled
    from corpus_structure.schema import physical

    installation._held_target_installation.cache_clear()
    monkeypatch.setattr(installation, "_generator_custody", lambda: ("generator", ()))
    model = compiled.compiled_model({"cache-control.yaml": b"id: urn:cache\nname: cache\n"})
    monkeypatch.setattr(compiled, "running_model", lambda: model)
    monkeypatch.setattr(physical, "compile_physical", lambda sources, **options: sources)
    calls = []

    def build(selected, **options):
        calls.append((selected, options))
        return object()

    monkeypatch.setattr(installation, "_build_target_installation", build)
    return calls


def metadata(source=b"original"):
    value = MetaData()
    value.info.update(physical_sources={"root": source}, physical_linkml_types=b"types")
    return value


def test_generation_shares_equal_captures_and_distinguishes_candidate_inputs(held_generation):
    logical = {"logical": b"initial"}
    first = installation.capture_target_installation(metadata(), logical_sources=logical)
    assert (
        installation.capture_target_installation(metadata(), logical_sources=dict(logical)) is first
    )
    changed = installation.capture_target_installation(
        metadata(b"candidate"), logical_sources=logical
    )
    assert changed is not first
    assert len(held_generation) == 2
    changed_logical = installation.capture_target_installation(
        metadata(), logical_sources={"logical": b"changed"}
    )
    assert changed_logical is not first
    assert len(held_generation) == 3
    pdf = SourceArtifact("pdf/action", b"candidate")
    assert (
        installation.capture_target_installation(
            metadata(), logical_sources=logical, pdf_actions=pdf
        )
        is not first
    )
    assert len(held_generation) == 4


def test_deterministic_generation_failure_is_held_as_a_value(held_generation, monkeypatch):
    calls = []

    def fail(*args, **kwargs):
        calls.append(1)
        raise ValueError("invalid candidate declaration")

    monkeypatch.setattr(installation, "_build_target_installation", fail)
    for _ in range(2):
        with pytest.raises(ValueError, match="invalid candidate declaration"):
            installation.capture_target_installation(metadata(), logical_sources={})
    assert len(calls) == 1
