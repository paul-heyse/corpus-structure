"""Declared rendering keeps actual PDF dependencies and typed raster value meaning."""

import sys
from hashlib import sha256
from pathlib import Path

import pytest

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


@pytest.mark.parametrize("change_during_encoding", [False, True])
def test_render_profile_has_exact_capture_support_and_no_legacy_publisher(
    tmp_path, change_during_encoding
):
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

    from concurrent.futures import ThreadPoolExecutor
    from types import SimpleNamespace

    from corpus_structure.core.work import drive_prepared_work
    from corpus_structure.orchestrate.data_operations import _PythonWork
    from corpus_structure.semantic.data_operation_ports import PythonRoleValue
    from corpus_structure.semantic.data_operation_values import semantic_value
    from corpus_structure.semantic.file_custody import FileCustodyError, verified_file

    asset = tmp_path / "encoding-premise"
    asset.write_bytes(b"captured")
    port._verification.files = (
        *port._verification.files,
        verified_file(asset, sha256(asset.read_bytes()).hexdigest()),
    )

    def validate_capture(kind, _content):
        assert kind == "DdoPdfPublication"
        return SimpleNamespace(model_dump=lambda **kwargs: {})

    controlled = SimpleNamespace(
        model=model,
        operation=render,
        prepared=SimpleNamespace(
            validate_json=validate_capture,
            validate_python=prepared.validate_python,
        ),
        implementation=lambda *args, **kwargs: SimpleNamespace(run=lambda *args, **kwargs: body),
        verify=port.verify,
    )

    def observe_encoding(frame, event, _argument):
        if event == "call" and frame.f_code is canonical_bytes.__code__:
            value = frame.f_locals["value"]
            if isinstance(value, dict) and value.get("encoding") == "png":
                asset.write_bytes(b"changed while encoding reply")
                sys.setprofile(None)

    incoming = render.roles[0]
    kind = next(
        item.key
        for item in model.identities
        if (item.owner, item.domain) == (incoming.kind, "kind")
    )

    def run():
        with ThreadPoolExecutor(
            max_workers=1,
            initializer=lambda: (
                sys.setprofile(observe_encoding) if change_during_encoding else None
            ),
        ) as pool:
            return drive_prepared_work(
                type(port).plan_python(
                    controlled,
                    (PythonRoleValue(incoming.name, kind, {}),),
                    binding=SimpleNamespace(
                        sufficient=True,
                        operation=render.semantic_id,
                        parameters=canonical_bytes(
                            semantic_value({"pointer": "/texts/7", "region_index": 0, "scale": "2"})
                        ),
                    ),
                    execution_owner=SimpleNamespace(
                        submit_python=lambda work: _PythonWork(pool.submit(work), lambda: None)
                    ),
                ),
                lambda: None,
            )

    if change_during_encoding:
        with pytest.raises(FileCustodyError, match="acquired file changed"):
            run()
    else:
        completion = run()
        assert completion.outputs[0].value() == body
        assert authorized == [identity] * 4
