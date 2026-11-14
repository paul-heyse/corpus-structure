"""PDF capture's declared effect and frozen acquisition; no provider success claim."""

import json
from pathlib import Path

from corpus_structure.ingest.pdf import PdfRecipe
from corpus_structure.ingest.pdf_assets import PreparedPdfAssets
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.pdf_capture import (
    pdf_capture_inputs,
    pdf_capture_operation_sources,
    pdf_publication_value,
)
from corpus_structure.semantic.pdf_publication import PublishedPdfDocumentRef


def test_pdf_capture_declares_exact_effect_and_captured_native_recipe(tmp_path):
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = pdf_capture_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    prepared = prepare_release(bundle)
    recipe = PdfRecipe("0" * 40, "1" * 40, recipe_id="docling-standard-pdf-stream-v1")
    assets = PreparedPdfAssets(tmp_path, b"{}", ())
    sources = pdf_capture_operation_sources(recipe, assets, directory=tmp_path / "owned")
    model = compile_data_operations(
        schema=bundle,
        python_sources=sources,
        definitions=prepared.definitions,
        vocabularies=prepared.vocabularies,
    )
    operation = model.operation("source.pdf/capture")
    assert operation.profile == "command"
    assert operation.capabilities.preparation == "pdf-native"
    assert operation.capabilities.prepared_factory is not None
    assert (
        operation.capabilities.prepared_factory.entrypoint
        == "corpus_structure.ingest.pdf_capture.PdfCaptureOperation.acquire_port"
    )
    assert [
        (effect.name, effect.authorization, effect.idempotency, effect.fulfillment)
        for effect in operation.effects
    ] == [
        (
            "publish_pdf_capture",
            ("original-source", "owned-request-attempt"),
            "request-generation/source-digest/recipe-digest",
            "sealed-native-pdf-receipt",
        )
    ]
    custody = {artifact.name: artifact.content for artifact in sources.boundary_contracts}
    frozen = json.loads(custody["pdf-capture/execution-custody"])
    assert PdfRecipe.from_bytes(bytes.fromhex(frozen["recipe"])) == recipe
    assert frozen["directory"] == str((tmp_path / "owned").resolve())
    assert frozen["assets"]["root"] == str(tmp_path.resolve())


def test_pdf_projection_keeps_whole_native_value_and_separates_actual_publisher_custody():
    publication = PublishedPdfDocumentRef(
        "build:original",
        17,
        "native",
        "0" * 64,
        "release:original",
        "1" * 64,
        "2" * 64,
        "3" * 64,
        "4" * 64,
        "native",
    )
    value = pdf_publication_value(
        "document:original",
        publication,
        {
            "conversion": "success",
            "display_coverage": "complete",
            "inline_coverage": "unknown",
            "cell_coverage": "partial",
            "source_scope": "whole_document",
        },
    )
    assert value == {
        "document": "document:original",
        "source_digest": "1" * 64,
        "logical_digest": "0" * 64,
        "schema_digest": "2" * 64,
        "recipe_digest": "3" * 64,
        "kind": "native",
        "health": {
            "conversion": "success",
            "display_coverage": "complete",
            "inline_coverage": "unknown",
            "cell_coverage": "partial",
        },
    }
