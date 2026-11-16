"""Actual PDF port/resource correspondence only; no native or provider execution claim."""

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from corpus_structure.ingest.pdf import PdfRecipe
from corpus_structure.ingest.pdf_assets import PreparedPdfAssets
from corpus_structure.ingest.pdf_hierarchy import SectionPolicy
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_admission import (
    PreparedCapabilityIdentity,
    bound_data_operation_model,
)
from corpus_structure.semantic.data_operation_consumers import resolve_prepared_factory
from corpus_structure.semantic.data_operation_effects import CapturedEffectPort
from corpus_structure.semantic.data_operation_ports import PortRefusal, python_port_identity
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.pdf_capture import pdf_capture_inputs, pdf_capture_operation_sources
from corpus_structure.semantic.pdf_transforms import (
    pdf_transform_operation_sources,
)
from corpus_structure.semantic.pdf_views import (
    pdf_views_assets,
    pdf_views_operation_sources,
)
from corpus_structure.semantic.source_discovery import source_discovery_inputs
from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies


@pytest.fixture(scope="module")
def captured_pdf_ports(tmp_path_factory):
    directory = tmp_path_factory.mktemp("pdf-resource-correspondence")
    recipe = PdfRecipe("0" * 40, "1" * 40, recipe_id="docling-standard-pdf-stream-v1")
    capture = pdf_capture_operation_sources(
        recipe, PreparedPdfAssets(directory, b"{}", ()), directory=directory / "owned"
    )
    organization = pdf_transform_operation_sources(
        "organized", options=SectionPolicy("explicit-sections"), directory=directory / "owned"
    )
    sources = pdf_views_operation_sources(capture, mode="organized", transformation_sources=organization)
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = source_discovery_inputs(pdf_capture_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))))
    prepared = prepare_release(bundle, data_operation_dependencies(
        ResolvedDependencies(), python_sources=sources), PreparationProfile(version="semantic-2"))
    model = bound_data_operation_model(prepared)
    return bundle, sources, prepared, model


def acquired_port(captured, operation_id):
    bundle, sources, prepared, model = captured
    operation = model.operation(operation_id)
    nominal = python_port_identity(model, sources, operation_id, schema=bundle, prepared=prepared)
    boundaries = (*operation.assets, *(boundary for implementation in model.implementation_slices
        if implementation.root == operation.implementation_root for boundary in implementation.boundaries))
    identity = PreparedCapabilityIdentity(**asdict(nominal), runtime="unadmitted:pdf-resource-correspondence",
        assets=canonical_bytes(tuple(asdict(boundary) for boundary in boundaries)))
    authorized = []
    options = dict(identity=identity, authorize=authorized.append, custody=sources.boundary_contracts, sources=sources)
    factory = resolve_prepared_factory(model, sources, operation_id)
    acquired = factory(prepared, model, operation_id, **options)
    port = acquired.effect_implementation() if isinstance(acquired, CapturedEffectPort) else acquired
    assert authorized == [identity]
    return port, authorized, identity


@pytest.mark.parametrize("operation", ("source.pdf/capture", "source.pdf_views/discovery", "source.pdf_organized_views/discovery", "source.pdf_sections/organize"))
def test_stable_actual_pdf_resource_capture_verifies_without_native_execution(captured_pdf_ports, operation):
    port, authorized, identity = acquired_port(captured_pdf_ports, operation)
    port._verify()
    assert authorized == [identity, identity]


@pytest.mark.parametrize("operation", ("source.pdf/capture", "source.pdf_views/discovery", "source.pdf_organized_views/discovery", "source.pdf_sections/organize"))
@pytest.mark.parametrize("helper", ("pdf_health", "pdf_hierarchy"))
def test_changed_helper_refuses_before_authorization(captured_pdf_ports, operation, helper, monkeypatch):
    port, authorized, identity = acquired_port(captured_pdf_ports, operation)
    from corpus_structure.ingest import pdf_health, pdf_hierarchy

    module = pdf_health if helper == "pdf_health" else pdf_hierarchy
    path = Path(module.__file__).resolve()
    original = Path.read_bytes
    before = original(path)
    changed = (
        before.replace(b'value = dict(health)', b'value = {"display_coverage": "complete"}', 1)
        if helper == "pdf_health"
        else before.replace(b"    return result\n", b"    return {}\n", 1)
    )
    assert changed != before

    def altered(source):
        return changed if source.resolve() == path else original(source)

    monkeypatch.setattr(Path, "read_bytes", altered)
    with pytest.raises((PortRefusal, ValueError), match=r"resources differ|implementation changed"):
        port._verify()
    assert authorized == [identity]


def test_moved_health_bytes_belong_to_both_actual_resource_owners(captured_pdf_ports):
    from corpus_structure.ingest import pdf_health

    files = dict(json.loads(pdf_views_assets().content)["files"])
    assert files["ingest/pdf_health.py"] == Path(pdf_health.__file__).read_bytes().hex()
    _, sources, _, _ = captured_pdf_ports
    capture = next(asset for asset in sources.boundary_contracts if asset.name == "pdf-capture/execution-custody")
    captured = dict(json.loads(capture.content)["files"])
    assert captured["ingest/pdf_health.py"] == Path(pdf_health.__file__).read_bytes().hex()
    from corpus_structure.ingest import pdf_hierarchy
    assert captured["ingest/pdf_hierarchy.py"] == Path(pdf_hierarchy.__file__).read_bytes().hex()
    custody = next(asset for asset in sources.boundary_contracts if asset.name == "pdf-organized/execution-custody")
    files = dict(json.loads(custody.content)["files"])
    assert files["ingest/pdf_health.py"] == Path(pdf_health.__file__).read_bytes().hex()
