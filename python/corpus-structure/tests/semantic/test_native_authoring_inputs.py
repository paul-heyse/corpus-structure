"""The current native kernel has an explicit application-independent authority cut."""

from dataclasses import replace
from hashlib import sha256

import pytest

from corpus_structure.semantic.native_products import (
    capture_native_authoring_inputs,
    current_admission_fields,
    current_authoring_provenance,
)


def test_native_authoring_does_not_acquire_legacy_or_application_catalog(monkeypatch):
    from corpus_structure.semantic import composed, contracts

    def forbidden(*args, **kwargs):
        raise AssertionError("native authoring acquired the legacy application catalog")

    monkeypatch.setattr(contracts, "compile_execution_model", forbidden)
    monkeypatch.setattr(contracts, "trusted_execution_inputs", forbidden)
    monkeypatch.setattr(composed, "composed_dependencies", forbidden)
    inputs = capture_native_authoring_inputs()
    assert inputs.model.operations
    assert all(operation.semantic_id.startswith("data.") for operation in inputs.model.operations)
    names = {source.name for source in inputs.sources}
    assert "authoring/native-fixed-calls.json" in names
    assert "native/source-admission-calls.json" in names
    assert "pdf-domain/contract.json" in names
    assert not any(name.startswith(("execution/", "provider/")) for name in names)
    provenance = current_authoring_provenance(inputs)
    assert provenance.model_id == sha256(inputs.model.content).hexdigest()
    assert {name for name, _ in provenance.inputs} == names
    fields = current_admission_fields(inputs)
    assert fields["data_operation_abi"] == "data-operation-model-v8"
    assert (
        not {"execution_abi", "supported_effects", "supported_effect_versions", "parsing_adapters"}
        & fields.keys()
    )


def test_native_capture_rejects_another_physical_model():
    inputs = capture_native_authoring_inputs()
    with pytest.raises(ValueError, match="another physical model"):
        current_admission_fields(replace(inputs, physical_id="another-model"))


def test_current_admission_kernel_has_no_historical_execution_fallback():
    from corpus_structure.semantic.native_products import admission_kernel

    kernel = admission_kernel()
    assert "native execution requires the current declared data operation model" in kernel
    assert "require_execution_operation" not in kernel
    assert "execution_abi" not in kernel
    assert "aclexplode" in kernel
    assert "p.prosecdef" in kernel


def test_explicit_physical_capture_reaches_native_helper_assets_and_guards():
    from corpus_structure.schema.physical import compile_physical
    from corpus_structure.semantic.data_operation_source_native import source_native_sql
    from corpus_structure.semantic.metadata import metadata
    from corpus_structure.semantic.original_document_contracts import ASSET
    from corpus_structure.semantic.pdf_domain import CONTRACT
    from corpus_structure.semantic.pdf_domain_native import pdf_domain_native_sql

    before = capture_native_authoring_inputs()
    sources = dict(metadata.info["physical_sources"])
    sources["physical.yaml"] += b"\n# exact counterfactual authoring input\n"
    changed = compile_physical(sources, linkml_types=metadata.info["physical_linkml_types"])
    after = capture_native_authoring_inputs(target_metadata=changed)
    original = {source.name: source for source in before.sources}
    captured = {source.name: source for source in after.sources}
    assert after.physical_id != before.physical_id
    assert current_authoring_provenance(after) != current_authoring_provenance(before)
    assert captured[ASSET].digest != original[ASSET].digest
    assert captured[CONTRACT].digest != original[CONTRACT].digest
    assert captured[ASSET].digest in source_native_sql(after.sources)
    assert original[ASSET].digest not in source_native_sql(after.sources)
    assert captured[CONTRACT].digest in pdf_domain_native_sql(sources=after.sources)
    assert original[CONTRACT].digest not in pdf_domain_native_sql(sources=after.sources)


def test_native_layout_uses_captured_scientific_schema(monkeypatch):
    from corpus_structure.semantic import scientific_evidence

    inputs = capture_native_authoring_inputs()

    def no_ambient_schema(*args):
        raise AssertionError("native layout reread an uncaptured scientific schema")

    monkeypatch.setattr(scientific_evidence, "files", no_ambient_schema)
    layout = current_admission_fields(inputs)["scientific_report_layout"]
    assert layout["comparison_paths"]
    assert layout["array_rules"]


def test_visual_native_lowering_uses_captured_sql_and_artifact_schema(monkeypatch):
    import json
    from pathlib import Path

    from corpus_structure.semantic.data_operation_source_native import source_native_sql
    from corpus_structure.semantic.data_operation_visual_read import (
        ARTIFACT_SOURCE,
        visual_read_sources,
        visual_read_sql,
    )
    from corpus_structure.semantic.types import SourceArtifact

    inputs = capture_native_authoring_inputs()
    selected = {source.name: source for source in visual_read_sources()}
    schema = json.loads(selected[ARTIFACT_SOURCE].content)
    schema["description"] = "captured visual schema marker"
    changed = tuple(
        SourceArtifact(source.name, json.dumps(schema).encode())
        if source.name == ARTIFACT_SOURCE
        else SourceArtifact(
            source.name,
            source.content.replace(b"ddo_visual_candidate_rows", b"captured_visual_candidate_rows"),
        )
        if source.name == "native/data-operation-visual-read.sql"
        else source
        for source in inputs.sources
    )
    read_text = Path.read_text

    def no_live_read(path, *args, **kwargs):
        # SQL preparation records the installed parser's package version. That
        # library metadata is independent of the captured visual/schema inputs.
        if path.name == "METADATA" and path.parent.name.endswith(".dist-info"):
            return read_text(path, *args, **kwargs)
        raise AssertionError("native lowering read an uncaptured source: " + str(path))

    monkeypatch.setattr(Path, "read_bytes", no_live_read)
    monkeypatch.setattr(Path, "read_text", no_live_read)
    rendered = visual_read_sql(changed)
    assert "captured visual schema marker" in rendered
    assert "captured_visual_candidate_rows" in rendered
    integrated = source_native_sql(changed)
    assert "captured visual schema marker" in integrated
    assert "captured_visual_candidate_rows" in integrated
    assert "ops.ddo_impl_read_selected_visual_evidence" in integrated
