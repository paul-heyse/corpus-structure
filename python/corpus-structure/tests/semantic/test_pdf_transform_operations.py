"""Declared PDF modes preserve their actual effect and source-discovery closure."""

import json
import sys
from dataclasses import asdict
from pathlib import Path

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
from corpus_structure.semantic.pdf_effect_contract import (
    PDF_ENRICHMENT_EFFECT,
    PDF_INTEGRATION_EFFECT,
)
from corpus_structure.semantic.pdf_transforms import (
    PdfEnrichmentOptions,
    PdfIntegrationOptions,
    PdfRecognitionOptions,
    PdfRecognitionResources,
    PreparedPdfTransform,
    pdf_transform_operation_sources,
    recognition_page_selection,
)
from corpus_structure.semantic.primary_operations import (
    primary_operation_inputs,
    primary_operation_targets,
)


@pytest.mark.parametrize("mode", ["enriched", "integrated"])
@pytest.mark.parametrize("organized", [False, True])
def test_pdf_mode_captures_only_its_explicit_profile_and_exact_discovery(
    mode, organized, tmp_path, monkeypatch
):
    from corpus_structure.methods import native_profiles

    monkeypatch.setattr(
        native_profiles,
        "spacy_selection",
        lambda config: NativeSelection(
            NativeProfile(
                "spacy",
                {"controlled": "runtime"},
                {},
                config.model_dump(mode="json"),
                "float32",
                "cupy",
                4,
                1,
            ),
            tmp_path,
        ),
    )
    recipe = PdfRecipe("0" * 40, "1" * 40, recipe_id="docling-standard-pdf-stream-v1")
    assets = PreparedPdfAssets(tmp_path, b"{}", ())
    capture = pdf_capture_operation_sources(recipe, assets, directory=tmp_path / "owned")
    from corpus_structure.ingest.pdf_hierarchy import SectionPolicy

    organization = (
        pdf_transform_operation_sources(
            "organized", options=SectionPolicy("explicit-sections"), directory=tmp_path / "owned"
        )
        if organized
        else None
    )
    input_operation = "source.pdf_sections/organize" if organized else "source.pdf/capture"
    if mode == "enriched":
        transformed = pdf_transform_operation_sources(
            mode,
            recipe=recipe,
            assets=assets,
            options=PdfEnrichmentOptions(),
            directory=tmp_path / "owned",
            input_operation=input_operation,
        )
        operation = "source.pdf_math/enrich"
        expected_effect = PDF_ENRICHMENT_EFFECT
    else:
        worker = tmp_path / "explicit-worker.py"
        worker.write_text("raise AssertionError('preparation cannot invoke a provider')\n")
        resources = PdfRecognitionResources(
            python=sys.executable,
            script=str(worker),
            endpoint="http://127.0.0.1:8123/v1",
            receipts=str(tmp_path / "receipts"),
            timeout_seconds=7,
        )
        transformed = pdf_transform_operation_sources(
            mode,
            recognition_recipe=NemotronRecipe("2" * 64, "3" * 64),
            options=PdfIntegrationOptions(integration_policy={}),
            recognition_options=PdfRecognitionOptions(recovery_policy=None),
            resources=resources,
            directory=tmp_path / "owned",
            input_operation=input_operation,
        )
        operation = "source.pdf_integrated/reconcile"
        expected_effect = PDF_INTEGRATION_EFFECT
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    acquired = primary_operation_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)),
        sentence_configuration=SentenceConfig(),
        hanlp_selection=pm2_selection("hanlp", tmp_path, {"controlled": "runtime"}, {}),
        capture_sources=capture,
        pdf_organization_sources=organization,
        pdf_enrichment_sources=transformed if mode == "enriched" else None,
        pdf_integration_sources=transformed if mode == "integrated" else None,
    )
    prepared = prepare_release(acquired.bundle, acquired.dependencies, acquired.profile)
    model = bound_data_operation_model(prepared)
    effect = model.operation(operation)
    assert effect.effects == (expected_effect,)
    assert effect.dependencies == (
        (input_operation,)
        if mode == "enriched"
        else (input_operation, "source.pdf_recognition/observe")
    )
    if mode == "integrated":
        assert model.operation("source.pdf_recognition/observe").dependencies == (
            "source.pdf/capture",
        )
    discovery = "source.pdf_" + mode + "_views/discovery"
    composition = "text.compose_view/" + mode + "-captured-full-native"
    assert model.operation(discovery).dependencies == (operation,)
    assert model.operation(composition).dependencies == (discovery,)
    for target, role, predecessor in (
        (discovery, "capture", operation),
        (composition, "sources", discovery),
    ):
        selection = next(item for item in model.operation(target).roles if item.name == role)
        assert selection.alternatives == (predecessor,) and selection.selected == predecessor
    assert (
        next(item for item in model.operation(composition).roles if item.name == "sources").minimum
        == 0
    )
    assert primary_operation_targets("capture", captured=True, pdf_mode=mode) == (discovery,)
    assert primary_operation_targets("characterize", captured=True, pdf_mode=mode) == (composition,)
    for target in (operation, discovery, composition):
        assert callable(resolve_prepared_factory(model, acquired.sources, target))
    if organized:
        assert model.operation("source.pdf_sections/organize").dependencies == (
            "source.pdf/capture",
        )
        assert model.operation("source.pdf_organized_views/discovery").dependencies == (
            "source.pdf_sections/organize",
        )
        assert primary_operation_targets("capture", captured=True, organized=True) == (
            "source.pdf_organized_views/discovery",
        )
    other = "source.pdf_integrated/reconcile" if mode == "enriched" else "source.pdf_math/enrich"
    assert other not in {item.semantic_id for item in model.operations}
    assert (
        model.operation(composition)
        .callable_surfaces[0]
        .declaration.endswith("ComposeCapturedDocumentFamily.run")
    )


@pytest.mark.parametrize("pages", [(1, 1), (2,)])
def test_recognition_refuses_duplicate_or_foreign_physical_pages_before_provider(pages):
    options = PdfRecognitionOptions(recovery_policy=None)
    values = {
        "source_scope": "whole_document",
        "health": {"conversion": "success"},
        "document": {"pages": {"1": {}}},
    }
    with pytest.raises(ValueError, match="physical page inventory"):
        recognition_page_selection(values, pages, options)


def test_recognition_recipe_owns_recovery_and_integration_recipe_owns_selection():
    options = PdfRecognitionOptions(recovery_policy={"max_attempts": 1})
    recipe = NemotronRecipe("2" * 64, "3" * 64)
    profile = PreparedPdfTransform(
        None,
        None,
        {
            "mode": "recognized",
            "options": options.model_dump(mode="json"),
            "recognition_bytes": recipe.to_bytes().hex(),
            "recognition_recipe": asdict(recipe),
        },
    )
    value = json.loads(profile.recipe_bytes((3, 1)))
    assert value["recognition_pages"] == [3, 1]
    assert value["recovery_policy"]["max_attempts"] == 1
    assert "integration_policy" not in value
    assert value["recognition"] == recipe.digest
    with pytest.raises(ValueError):
        PdfRecognitionOptions(recovery_policy={"max_attempts": 2})
    integration = PreparedPdfTransform(
        None,
        None,
        {
            "mode": "integrated",
            "options": PdfIntegrationOptions(integration_policy={}).model_dump(mode="json"),
        },
    )
    selected = json.loads(integration.recipe_bytes())
    assert selected["integration_policy"]["comparison_demand"] == "lexical"
    assert (
        not {"recognition", "recognition_pages", "recovery_policy", "source_recovery"}
        & selected.keys()
    )


def test_integration_policy_change_keeps_actual_recognition_recipe_identity(tmp_path):
    from semantic.current_pdf_integration_support import current_pdf_recipe
    from semantic.data_operation_kernel_support import prepare_kernel

    first = prepare_kernel(current_pdf_recipe(tmp_path))
    second = prepare_kernel(
        current_pdf_recipe(
            tmp_path,
            integration_policy={
                "policy_id": "pdf-integration-v1",
                "conflict_action": "keep",
                "unmatched_action": "add",
                "specialized_crop_precedence": True,
                "comparison_demand": "lexical",
            },
        )
    )
    recognition = "source.pdf_recognition/observe"
    integration = "source.pdf_integrated/reconcile"

    def identities(model):
        return {(entry.owner, entry.domain): entry.key for entry in model.identities}

    assert first.model.operation(recognition).recipe == second.model.operation(recognition).recipe
    assert (
        identities(first.model)[recognition, "recipe"]
        == identities(second.model)[recognition, "recipe"]
    )
    assert first.model.operation(integration).recipe != second.model.operation(integration).recipe
    assert (
        identities(first.model)[integration, "recipe"]
        != identities(second.model)[integration, "recipe"]
    )


def test_pdf_reader_materialization_checkpoint_observes_actual_request_cancellation():
    from corpus_structure.core.db.lifetime import BorrowerCancellation
    from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader

    reader = PublishedPdfReader.__new__(PublishedPdfReader)
    reader.cancellation = BorrowerCancellation()
    calls = []

    def active():
        calls.append("request")
        raise InterruptedError("request lease ended")

    reader.external_check_active = active
    with pytest.raises(InterruptedError, match="request lease ended"):
        reader._check_active()
    assert calls == ["request"]


def test_pdf_only_modes_declare_their_actual_source_member_contexts(tmp_path):
    """No downstream language consumer may supply discovery's missing subject meaning."""
    from corpus_structure.semantic.data_operation_ports import PortRefusal, project_product_members
    from corpus_structure.semantic.source_discovery import selected_source_population
    from corpus_structure.semantic.source_products import FrozenNativeSource
    from semantic.current_pdf_integration_support import current_pdf_recipe
    from semantic.data_operation_kernel_support import prepare_kernel

    profile = prepare_kernel(current_pdf_recipe(tmp_path))
    assert not any(
        name.startswith("text.") for name in (op.semantic_id for op in profile.model.operations)
    )
    definition = profile.model.subject_definition("original-source-view")
    assert definition.scope == "original-source"
    assert (
        next(k.name for k in profile.model.kinds if k.semantic_id == definition.identifier_kind)
        == "string"
    )
    value = FrozenNativeSource.from_projection(
        profile.prepared,
        document="independent-original",
        section_pointer="#/texts/0",
        membership="direct",
        text="literal selected source",
        pieces=[
            dict(kind="native_text", start=0, end=23, item_ref="#/texts/0", source_field="text")
        ],
        items=[dict(self_ref="#/texts/0", label="text", text="literal selected source")],
    ).value
    selected_kind = profile.prepared.index.definitions["DdoSelectedNativeSource"].iri
    kind_contract = next(
        identity.key
        for identity in profile.model.identities
        if identity.domain == "kind" and identity.owner == selected_kind
    )
    population = selected_source_population(
        {"document": "independent-original"}, (value,), complete=True, kind_contract=kind_contract
    )
    for operation_id in (
        "source.pdf_organized_views/discovery",
        "source.pdf_enriched_views/discovery",
        "source.pdf_integrated_views/discovery",
    ):
        operation = profile.model.operation(operation_id)
        kind = next(role.kind for role in operation.roles if role.direction == "output")
        (encoded,) = project_product_members(profile.model, kind, population)
        member = json.loads(encoded)
        assert member["context"]["subject_definition"] == "original-source-view"
        assert member["context"]["original_source"] == "independent-original"
        assert member["context"]["subject"] == population["members"][0]["context"]["subject"]
        assert (
            member["context"]["analyzed_scope"]
            == population["members"][0]["context"]["analyzed_scope"]
        )
        invalid = {
            **population,
            "members": [
                {
                    **population["members"][0],
                    "context": {**population["members"][0]["context"], "original_source": None},
                }
            ],
        }
        with pytest.raises(PortRefusal, match="original"):
            project_product_members(profile.model, kind, invalid)
