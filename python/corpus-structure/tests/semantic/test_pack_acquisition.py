"""Acquisition and normalized composition do not prepare component packs."""

from pathlib import Path

from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic import regeneration


def test_acquire_and_compose_never_invoke_compiler(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("acquisition/composition must not compile")

    monkeypatch.setattr(regeneration, "prepare_release", forbidden)
    inputs = regeneration.acquire_pack(DOMAINS / "statistics")

    # Local ontology leaves have always used an operation-owned file bridge.
    # Permit only files written from captured ontology bytes during this operation;
    # installed/domain source reads must still fail after acquisition.
    captured = {
        a.content
        for a in inputs.dependencies.artifacts
        if a.name in inputs.dependencies.ontology_sources
    }
    materialized = set()
    observed = set()
    read_bytes, write_bytes = Path.read_bytes, Path.write_bytes

    def captured_write(path, content):
        assert path.parent.name.startswith("corpus-semantic-ontology-")
        assert content in captured
        written = write_bytes(path, content)
        materialized.add(path)
        return written

    def captured_read(path):
        assert path in materialized, f"ambient source read during composition: {path}"
        content = read_bytes(path)
        assert content in captured
        observed.add(path)
        return content

    monkeypatch.setattr(Path, "write_bytes", captured_write)
    monkeypatch.setattr(Path, "read_bytes", captured_read)
    first = regeneration.compose_pack_inputs((inputs,))
    second = regeneration.compose_pack_inputs((inputs,))
    assert first == second
    assert inputs.name == "statistics"
    assert inputs.bundle.sources
    assert observed == materialized and observed


def test_prepare_normalizes_duplicates_and_compiles_only_composed_root(monkeypatch):
    calls = []
    sentinel = object()

    def prepare(bundle, dependencies, profile):
        calls.append((bundle, dependencies, profile))
        return sentinel

    monkeypatch.setattr(regeneration, "prepare_release", prepare)
    result = regeneration.prepare_packs((DOMAINS / "statistics", DOMAINS / "statistics"))
    assert result[-1] is sentinel
    assert calls == [result[:3]]
