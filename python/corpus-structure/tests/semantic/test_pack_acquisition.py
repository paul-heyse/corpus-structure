"""Acquisition and normalized composition do not prepare component packs."""

from pathlib import Path

from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic import regeneration


def test_acquire_and_compose_never_invoke_compiler(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("acquisition/composition must not compile")

    monkeypatch.setattr(regeneration, "prepare_release", forbidden)
    inputs = regeneration.acquire_pack(DOMAINS / "statistics")

    def ambient_read(path):
        raise AssertionError(f"ambient source read during composition: {path}")

    monkeypatch.setattr(Path, "read_bytes", ambient_read)
    first = regeneration.compose_pack_inputs((inputs,))
    second = regeneration.compose_pack_inputs((inputs,))
    assert first == second
    assert inputs.name == "statistics"
    assert inputs.bundle.sources
    assert not any(artifact.name.startswith("execution/") for artifact in first[1].artifacts)


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


def test_current_pack_acquisition_has_real_source_contracts_without_old_catalog(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("current pack preparation cannot compile or acquire an old catalog")

    bundle, dependencies, profile, prepared = regeneration.prepare_pack(DOMAINS / "statistics")
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model

    model = bound_data_operation_model(prepared)
    assert model.operation("data.inspect_data_operation_release").profile == "read"
    assert model.operation("rich.consolidate").profile == "derivation"
    admission = model.operation("rich.admit")
    assert admission.profile == "command"
    assert {effect.name for effect in admission.effects} == {"native-rich-knowledge-admission"}
    assert "StatisticsQualification" in prepared.index.definitions
    assert {"data_operation_rich_proposals", "source-readings"} <= {
        source.name for source in bundle.sources
    }
    pin_fields = {prop.name for prop in prepared.index.definitions["RecordSourcePin"].properties}
    assert {"source_product", "kind_contract", "subject_definition"} <= pin_fields
    assert not {"source_view_id", "native_product_task_id"} & pin_fields
    assert not any(artifact.name.startswith("execution/") for artifact in dependencies.artifacts)
    assert profile.version == "semantic-2"
