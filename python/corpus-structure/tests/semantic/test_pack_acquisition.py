"""Acquisition and normalized composition do not prepare component packs."""

from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic import regeneration


def test_acquire_and_compose_never_invoke_compiler(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("acquisition/composition must not compile")

    monkeypatch.setattr(regeneration, "prepare_release", forbidden)
    inputs = regeneration.acquire_pack(DOMAINS / "statistics")

    def no_io(*args, **kwargs):
        raise AssertionError("composition must consume acquired bytes only")

    monkeypatch.setattr(__import__("pathlib").Path, "read_bytes", no_io)
    first = regeneration.compose_pack_inputs((inputs,))
    second = regeneration.compose_pack_inputs((inputs,))
    assert first == second
    assert inputs.name == "statistics"
    assert inputs.bundle.sources


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
