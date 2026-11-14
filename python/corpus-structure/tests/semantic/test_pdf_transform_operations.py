"""Declared PDF modes preserve their actual effect and source-discovery closure."""

import json
import sys
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest

from corpus_structure.ingest.pdf import PdfRecipe
from corpus_structure.ingest.pdf_assets import PreparedPdfAssets
from corpus_structure.ingest.pdf_recognition import NemotronRecipe
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection, pm2_selection
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.data_operation_consumers import resolve_prepared_factory
from corpus_structure.semantic.pdf_capture import pdf_capture_operation_sources
from corpus_structure.semantic.pdf_effect_contract import PDF_ENRICHMENT_EFFECT, PDF_INTEGRATION_EFFECT
from corpus_structure.semantic.pdf_transforms import (
    PdfEnrichmentOptions,
    PdfIntegrationOptions,
    PdfRecognitionResources,
    PreparedPdfTransform,
    pdf_transform_operation_sources,
)
from corpus_structure.semantic.primary_operations import primary_operation_inputs, primary_operation_targets


@pytest.mark.parametrize("mode", ["enriched", "integrated"])
def test_pdf_mode_captures_only_its_explicit_profile_and_exact_discovery(mode, tmp_path, monkeypatch):
    from corpus_structure.methods import native_profiles

    monkeypatch.setattr(native_profiles, "spacy_selection", lambda config: NativeSelection(NativeProfile("spacy", {"controlled": "runtime"}, {}, config.model_dump(mode="json"), "float32", "cupy", 4, 1), tmp_path))
    recipe = PdfRecipe("0" * 40, "1" * 40, recipe_id="docling-standard-pdf-stream-v1")
    assets = PreparedPdfAssets(tmp_path, b"{}", ())
    capture = pdf_capture_operation_sources(recipe, assets, directory=tmp_path / "owned")
    if mode == "enriched":
        transformed = pdf_transform_operation_sources(mode, recipe=recipe, assets=assets, options=PdfEnrichmentOptions(), directory=tmp_path / "owned")
        operation = "source.pdf_math/enrich"
        expected_effect = PDF_ENRICHMENT_EFFECT
    else:
        worker = tmp_path / "explicit-worker.py"
        worker.write_text("raise AssertionError('preparation cannot invoke a provider')\n")
        resources = PdfRecognitionResources(python=sys.executable, script=str(worker), endpoint="http://127.0.0.1:8123/v1", receipts=str(tmp_path / "receipts"), timeout_seconds=7)
        transformed = pdf_transform_operation_sources(mode, recognition_recipe=NemotronRecipe("2" * 64, "3" * 64), options=PdfIntegrationOptions(recovery_policy=None, integration_policy={}), resources=resources, directory=tmp_path / "owned")
        operation = "source.pdf_integrated/reconcile"
        expected_effect = PDF_INTEGRATION_EFFECT
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    acquired = primary_operation_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)), sentence_configuration=SentenceConfig(), hanlp_selection=pm2_selection("hanlp", tmp_path, {"controlled": "runtime"}, {}), capture_sources=capture, **{"pdf_enrichment_sources" if mode == "enriched" else "pdf_integration_sources": transformed})
    prepared = prepare_release(acquired.bundle, acquired.dependencies, acquired.profile)
    model = bound_data_operation_model(prepared)
    effect = model.operation(operation)
    assert effect.effects == (expected_effect,)
    assert effect.dependencies == ("source.pdf/capture",)
    discovery = "source.pdf_" + mode + "_views/discovery"
    composition = "text.compose_view/" + mode + "-captured-full-native"
    assert model.operation(discovery).dependencies == (operation,)
    assert model.operation(composition).dependencies == (discovery,)
    for target, role, predecessor in ((discovery, "capture", operation), (composition, "sources", discovery)):
        selection = next(item for item in model.operation(target).roles if item.name == role)
        assert selection.alternatives == (predecessor,) and selection.selected == predecessor
    assert next(item for item in model.operation(composition).roles if item.name == "sources").minimum == 0
    assert primary_operation_targets("capture", captured=True, pdf_mode=mode) == (discovery,)
    assert primary_operation_targets("characterize", captured=True, pdf_mode=mode) == (composition,)
    for target in (operation, discovery, composition):
        assert callable(resolve_prepared_factory(model, acquired.sources, target))
    other = "source.pdf_integrated/reconcile" if mode == "enriched" else "source.pdf_math/enrich"
    assert other not in {item.semantic_id for item in model.operations}
    assert model.operation(composition).callable_surfaces[0].declaration.endswith("ComposeCapturedDocumentFamily.run")


@pytest.mark.parametrize("pages", [(1, 1), (2,)])
def test_integration_refuses_duplicate_or_foreign_physical_pages_before_provider(pages):
    options = PdfIntegrationOptions(recovery_policy=None, integration_policy={})
    profile = PreparedPdfTransform(None, None, {"mode": "integrated", "options": options.model_dump(mode="json")})
    selected = SimpleNamespace(product=SimpleNamespace(values=lambda: {"source_scope": "whole_document", "health": {"conversion": "success"}, "document": {"pages": {"1": {}}}}))
    with pytest.raises(ValueError, match="physical page inventory"):
        next(profile._integrate(selected, b"{}", pages, None, None, lambda: None))


def test_integration_recipe_retains_explicit_recovery_and_selection():
    options = PdfIntegrationOptions(recovery_policy={"max_attempts": 1}, integration_policy={})
    recipe = NemotronRecipe("2" * 64, "3" * 64)
    profile = PreparedPdfTransform(None, None, {"mode": "integrated", "options": options.model_dump(mode="json"), "recognition_bytes": recipe.to_bytes().hex(), "recognition_recipe": asdict(recipe)})
    value = json.loads(profile.recipe_bytes((3, 1)))
    assert value["recognition_pages"] == [3, 1]
    assert value["recovery_policy"]["max_attempts"] == 1
    assert value["integration_policy"]["comparison_demand"] == "lexical"
    assert value["recognition"] == recipe.digest
    with pytest.raises(ValueError):
        PdfIntegrationOptions(recovery_policy={"max_attempts": 2}, integration_policy={})
