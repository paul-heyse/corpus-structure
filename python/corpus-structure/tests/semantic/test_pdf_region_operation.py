"""Declared rendering keeps actual PDF dependencies and typed raster value meaning."""

from pathlib import Path

from corpus_structure.ingest.pdf import PdfRecipe
from corpus_structure.ingest.pdf_assets import PreparedPdfAssets
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.native_requests import (
    pdf_region_inputs,
    pdf_region_operation_sources,
)
from corpus_structure.semantic.pdf_capture import pdf_capture_inputs, pdf_capture_operation_sources
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.types import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)


def test_render_profile_has_exact_capture_support_and_no_legacy_publisher(tmp_path):
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = pdf_region_inputs(
        pdf_capture_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    )
    recipe = PdfRecipe("0" * 40, "1" * 40, recipe_id="docling-standard-pdf-stream-v1")
    assets = PreparedPdfAssets(tmp_path, b"{}", ())
    sources = pdf_region_operation_sources(
        pdf_capture_operation_sources(recipe, assets, directory=tmp_path / "owned")
    )
    from corpus_structure.semantic.composed import data_operation_dependencies

    dependencies = data_operation_dependencies(ResolvedDependencies(), python_sources=sources)
    prepared = prepare_release(bundle, dependencies, PreparationProfile(version="semantic-2"))
    model = compile_data_operations(
        schema=bundle,
        python_sources=sources,
        definitions=prepared.definitions,
        vocabularies=prepared.vocabularies,
    )
    from corpus_structure.ingest.pdf_region_operation import PdfRegionOperation
    from corpus_structure.semantic.data_operation_ports import python_port_identity

    render = model.operation("source.pdf_region/render")
    authorized = []
    from dataclasses import asdict

    from corpus_structure.semantic.data_operation_admission import PreparedCapabilityIdentity
    from corpus_structure.semantic.identity import canonical_bytes

    base_identity = python_port_identity(
        model, sources, render.semantic_id, schema=bundle, prepared=prepared
    )
    boundaries = (
        *render.assets,
        *(
            boundary
            for implementation in model.implementation_slices
            if implementation.root == render.implementation_root
            for boundary in implementation.boundaries
        ),
    )
    # Pure callable/resource correspondence only; this does not claim native admission.
    identity = PreparedCapabilityIdentity(
        **asdict(base_identity),
        runtime="runtime:correspondence-test",
        assets=canonical_bytes(tuple(asdict(boundary) for boundary in boundaries)),
    )
    port = PdfRegionOperation.acquire_port(
        prepared,
        model,
        render.semantic_id,
        identity=identity,
        authorize=authorized.append,
        custody=sources.boundary_contracts,
        sources=sources,
    )
    assert authorized == [identity]
    port.verify()
    assert authorized == [identity, identity]
    assert render.profile == "derivation" and not render.effects
    assert render.dependencies == ("source.pdf/capture",)
    assert render.roles[0].support is not None
    assert render.roles[0].support.origins == ("computation",)
    assert render.roles[0].support.identity_requirements == ("episode", "alternative")
    assert render.capabilities.prepared_factory is not None
    assert render.capabilities.prepared_factory.entrypoint.endswith("PdfRegionFamily.acquire_port")
    body = dict(
        document="document:original",
        source_digest="0" * 64,
        logical_digest="1" * 64,
        pointer="/texts/7",
        region_index=0,
        scale="2",
        encoding="png",
        content_digest="2" * 64,
        content_hex="89504e47",
    )
    value = prepared.validate_python("DdoPdfRegion", body).model_dump(mode="python")
    assert value == body
