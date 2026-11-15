"""Current visual declarations compose genuine capture, external result and mapping."""

from pathlib import Path

import pytest

from corpus_structure.ingest.pdf import PdfRecipe
from corpus_structure.ingest.pdf_assets import PreparedPdfAssets
from corpus_structure.semantic import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
    prepare_release,
)
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.native_requests import (
    pdf_region_inputs,
    pdf_region_operation_sources,
)
from corpus_structure.semantic.pdf_capture import pdf_capture_inputs, pdf_capture_operation_sources
from corpus_structure.semantic.primary_operations import combine_primary_sources
from corpus_structure.semantic.visual_requests import (
    visual_external_declaration,
    visual_operation_sources,
)


def test_visual_profile_uses_external_native_receipt_and_mechanical_mapping(tmp_path):
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = pdf_region_inputs(
        pdf_capture_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    )
    recipe = PdfRecipe("0" * 40, "1" * 40, recipe_id="docling-standard-pdf-stream-v1")
    assets = PreparedPdfAssets(tmp_path, b"{}", ())
    sources = combine_primary_sources(
        pdf_region_operation_sources(
            pdf_capture_operation_sources(recipe, assets, directory=tmp_path / "owned")
        ),
        visual_operation_sources(),
    )
    from corpus_structure.semantic.composed import data_operation_dependencies

    declaration = visual_external_declaration()
    dependencies = data_operation_dependencies(
        ResolvedDependencies(), declarations=(declaration,), python_sources=sources
    )
    prepared = prepare_release(bundle, dependencies, PreparationProfile(version="semantic-2"))
    model = compile_data_operations(
        schema=bundle,
        python_sources=sources,
        declarations=(declaration,),
        definitions=prepared.definitions,
        vocabularies=prepared.vocabularies,
    )
    assert prepared.validate_python("DdoVisualSelection", {"page_no": 1}).model_dump(
        mode="python", exclude_unset=True
    ) == {"page_no": 1}
    for invalid in (
        {"page_no": 1, "pointer": "#/texts/0"},
        {"page_no": 1, "region_index": 0},
        {"page_no": 1, "rotation": 90},
    ):
        with pytest.raises(ValueError):
            prepared.validate_python("DdoVisualSelection", invalid)
    recognize = model.operation("source.visual/recognize")
    assert recognize.external is not None
    assert recognize.effects[0].fulfillment == "native-publication-receipt"
    assert recognize.dependencies == ("source.visual_input/render",)
    assert recognize.output_witnesses
    comparisons = recognize.output_witnesses[0].comparisons
    assert {value.output_field for value in comparisons} >= {
        "/image/content_digest",
        "/image/document",
        "/image/transform_json",
        "/image/selection",
    }
    mapping = model.operation("source.visual/map")
    assert mapping.dependencies == ("source.visual/recognize",) and not mapping.effects
    assert model.operation("source.visual_input/render").dependencies == ("source.pdf/capture",)
