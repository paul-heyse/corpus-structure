"""Controlled-provider native PDF effects; this is not provider qualification."""

from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
import json
import sys

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.method import MethodSettings
from corpus_structure.ingest.pdf import PdfRecipe
from corpus_structure.ingest.pdf_assets import PreparedPdfAssets
from corpus_structure.ingest.pdf_enrichment import PdfEnrichmentResult
from corpus_structure.ingest.pdf_hierarchy import SectionPolicy
from corpus_structure.ingest.pdf_recognition import NemotronRecipe, RecognitionPage
from corpus_structure.ingest.pdf_streaming import PdfStreamSpool, StreamingPdfResult
from corpus_structure.ingest.pdf_stream_types import PdfStreamReply
from corpus_structure.orchestrate.source_operation import run_source_operation
from corpus_structure.orchestrate.source_request import SourceRunRequest, WholeDocument
from corpus_structure.semantic import PreparationProfile, ResolvedDependencies, SourceArtifact, SourceBundle
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_artifacts import capture_port_generator_sources
from corpus_structure.semantic.data_operation_identity import decode_semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_service import DemandOperationSelection, execute_data_demand, read_data_demand
from corpus_structure.semantic.data_operation_storage import native_operation_declarations, native_protocol_sources
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.pdf_capture import pdf_capture_inputs, pdf_capture_operation_sources
from corpus_structure.semantic.pdf_domain import pdf_domain_dependencies
from corpus_structure.semantic.pdf_effect_contract import PDF_ENRICHMENT_EFFECT, PDF_ENRICHMENT_FACTORY, PDF_INTEGRATION_EFFECT, PDF_INTEGRATION_FACTORY, PDF_ORGANIZATION_EFFECT, PDF_ORGANIZATION_FACTORY
from corpus_structure.semantic.pdf_transforms import PdfEnrichmentOptions, PdfIntegrationOptions, PdfRecognitionResources, pdf_transform_operation_sources
from corpus_structure.semantic.pdf_views import pdf_views_operation_sources
from corpus_structure.semantic.primary_operations import combine_primary_sources
from corpus_structure.semantic.source_discovery import source_discovery_inputs
from semantic.data_operation_kernel_support import CapturedKernelInputs, Kernel, KernelRecipe
from semantic.data_operation_original_support import OriginalSeedRecipe
from semantic.native_record_fixtures import RecordSourceRecipe
from semantic.pdf_integration_support import IMAGE

ROOT = Path(__file__).resolve().parents[4]


def _pdf_recipe(directory):
    native = PdfRecipe("0" * 40, "1" * 40, device="cpu", ocr_device="cpu", recipe_id="docling-standard-pdf-stream-v1")
    assets = PreparedPdfAssets(directory, b"{}", ())
    capture = pdf_capture_operation_sources(native, assets, directory=directory / "owned")
    organization = pdf_transform_operation_sources("organized", options=SectionPolicy("explicit-native-headings"), directory=directory / "owned")
    enriched = pdf_transform_operation_sources("enriched", recipe=native, assets=assets, options=PdfEnrichmentOptions(), directory=directory / "owned", input_operation="source.pdf_sections/organize")
    worker = directory / "explicit-provider.py"
    worker.write_text("raise AssertionError('controlled provider boundary must replace inference')\n")
    integration = pdf_transform_operation_sources("integrated", recognition_recipe=NemotronRecipe("2" * 64, "3" * 64), options=PdfIntegrationOptions(recovery_policy=None, integration_policy={}), resources=PdfRecognitionResources(python=sys.executable, script=str(worker), endpoint="http://127.0.0.1:8123/v1", receipts=str(directory / "receipts"), timeout_seconds=1), directory=directory / "owned", input_operation="source.pdf_sections/organize")
    sources = combine_primary_sources(pdf_views_operation_sources(capture, mode="organized", transformation_sources=organization), pdf_views_operation_sources(capture, mode="enriched", transformation_sources=enriched), pdf_views_operation_sources(capture, mode="integrated", transformation_sources=integration))
    bundle = source_discovery_inputs(pdf_capture_inputs(SourceBundle("toy_semantic", (SourceArtifact("toy_semantic", (ROOT / "domains/toy/semantic.yaml").read_bytes()), SourceArtifact("semantic_core", (ROOT / "python/corpus-structure/src/corpus_structure/model/semantic/core.yaml").read_bytes())))))
    native_sources = native_protocol_sources()
    dependencies = pdf_domain_dependencies(ResolvedDependencies())
    dependencies = data_operation_dependencies(ResolvedDependencies((*dependencies.artifacts, *native_sources, *capture_port_generator_sources())), (native_operation_declarations(native_sources),), sources)
    return KernelRecipe("controlled-pdf-transform-demand", "", None, "", project_id=None, source_stage="private-source", execution_profile="source-native", captured_inputs=CapturedKernelInputs(bundle, dependencies, PreparationProfile(version="semantic-2")))


def test_native_organization_enrichment_and_integration_keep_real_receipts_and_exact_resume(scenario_seeds, tmp_path, monkeypatch):
    from docling_core.types.doc import BoundingBox, DocItemLabel, DoclingDocument, ProvenanceItem, Size
    from corpus_structure.ingest import pdf_recognition, pdf_worker

    calls = []
    def controlled_stream(self, source, *, spool_root, record_root, build_id, release_id, on_replay, check_active, **options):
        check_active()
        calls.append("capture")
        document = DoclingDocument(name="Controlled native transformation source")
        document.add_page(page_no=1, size=Size(width=200, height=300))
        document.add_heading(text="1 Controlled", level=1)
        document.add_text(label=DocItemLabel.TEXT, text="Selected source value.", prov=ProvenanceItem(page_no=1, bbox=BoundingBox(l=10, t=20, r=150, b=40), charspan=(0, 22)))
        streamed = StreamingPdfResult(document, PdfStreamSpool(spool_root, check_active=check_active), "success", (), self.recipe.to_bytes(), ())
        occurrences = streamed.write_native_occurrence_batches(record_root.with_name(record_root.name + "-occurrences"), build_id=build_id, on_batch=on_replay)
        records = streamed.write_record_batches(record_root, build_id=build_id, release_id=release_id, source_digest=source.digest, on_batch=on_replay)
        return PdfStreamReply("success", (), self.recipe.to_bytes(), (), records + occurrences)
    def controlled_enrichment(self, request, *, check_active):
        check_active()
        calls.append("enrich")
        assert request.selected
        return PdfEnrichmentResult(request.conversion.native, (), (), (), request.conversion.inline_candidates, (), (), b"{}")
    class ControlledRecognition:
        def __init__(self, **resources):
            pass
        def recognize_pages(self, source, recipe, pages, *, check_active, **options):
            calls.append("recognize")
            assert tuple(pages) == (1,)
            directory = tmp_path / "actual-controlled-page"
            directory.mkdir()
            raw = b"<x_0.1><y_0.2>Selected source value.<x_0.8><y_0.3><class_Text>"
            (directory / "submitted.png").write_bytes(IMAGE)
            (directory / "response.txt").write_bytes(raw)
            (directory / "request-000.json").write_text(json.dumps(dict(ordinal=0, stage="fullpage", outcome="succeeded", submitted_image="submitted.png", submitted_digest=sha256(IMAGE).hexdigest(), width=4, height=6, raw_response="response.txt", prompt="Independent controlled recognition", settings={}, finish_reason="stop")))
            check_active()
            yield RecognitionPage(1, directory, {"outcome": "succeeded"}, dict(status="unknown", normalization="unknown", source_space="pdf_points", target_space="submitted_pixels"))
    monkeypatch.setattr(pdf_worker.PdfWorker, "stream", controlled_stream)
    monkeypatch.setattr(pdf_worker.PdfWorker, "enrich", controlled_enrichment)
    monkeypatch.setattr(pdf_recognition, "RecognitionWorker", ControlledRecognition)
    recipe = OriginalSeedRecipe(RecordSourceRecipe(), _pdf_recipe(tmp_path))
    with scenario_seeds.commit_clone(recipe) as clone:
        kernel = Kernel(clone.admin, clone.stage.kernel.preparation, clone.stage.kernel.identities, recipe.target, clone)
        document = table("kb.document")
        with clone.admin.connect() as connection:
            original = connection.execute(select(document.c.key, document.c.content_hash).where(document.c.id == clone.stage.source.document)).one()
        targets = ("source.pdf_organized_views/discovery", "source.pdf_enriched_views/discovery", "source.pdf_integrated_views/discovery")
        source_options = {"sections": ["1 Controlled"], "membership": "descendants"}
        request = SourceRunRequest(project_id=clone.stage.source.project_id, release_id=kernel.prepared.release_id, runtime_id=kernel.runtime, domain="toy", workflow="capture", selection=WholeDocument(), documents=(original.key,), pdf_mode="integrated", recognition_pages=(1,), targets=targets, selections=(DemandOperationSelection(operation="source.pdf_math/enrich", parameters=source_options), DemandOperationSelection(operation=targets[0], parameters=source_options), DemandOperationSelection(operation=targets[1], parameters=source_options)))
        result = run_source_operation(kernel.purpose("write"), request, MethodSettings(data_dir=tmp_path, model_cache=tmp_path), source_root=ROOT, admission_engine=kernel.purpose("admit"))
        with clone.admin.connect() as connection:
            snapshot = read_data_demand(connection, result.demand_id, view="products")
        obligations = {row["obligation_id"]: row for row in snapshot["obligations"]}
        products, derivations = {}, {}
        for use in snapshot["uses"]:
            operation = obligations[use["obligation_id"]]["operation_id"]
            assert use["fate"] == "fulfilled", use
            products[operation] = {product["role"]: decode_semantic_value(product["body"]) for product in use["products"]}
            derivations[operation] = use["derivation_id"]
        assert calls == ["capture", "enrich", "recognize"] or calls == ["capture", "recognize", "enrich"]
        effects = ("source.pdf_sections/organize", "source.pdf_math/enrich", "source.pdf_integrated/reconcile")
        for operation in effects:
            output = products[operation]["result"]
            assert output["source_digest"] == original.content_hash and output["document"] == original.key
            assert output["kind"] == ("integrated" if operation == effects[2] else "native")
            assert not {"run_id", "task_id", "source_view_id"} & output.keys()
        for operation in targets:
            population = products[operation]["result"]
            assert population["members"]
        intents, derivations_table, tasks = (table(name) for name in ("ops.data_completion_intent", "ops.data_derivation", "ops.task"))
        receipts = []
        with clone.admin.connect() as connection:
            for operation in effects:
                retained = connection.execute(select(intents.c.payload, intents.c.producer_task_id, intents.c.producer_attempt, intents.c.producer_holder, tasks.c.run_id).join_from(intents, derivations_table, derivations_table.c.intent_id == intents.c.id).join(tasks, tasks.c.id == intents.c.producer_task_id).where(derivations_table.c.id == derivations[operation])).mappings().one()
                assert retained["run_id"] is None
                (receipt,) = retained["payload"]["execution_evidence"]["pdf_receipts"]
                assert receipt["publication"]["task_id"] == retained["producer_task_id"]
                receipts.append((receipt, retained))
            observations = connection.execute(text("SELECT kind FROM ops.pdf_product WHERE task_id=:task"), {"task": receipts[2][1]["producer_task_id"]}).scalars().all()
            assert "recognition_observation" in observations
            for receipt, retained in receipts:
                forged = deepcopy(receipt)
                forged["publication"]["source_digest"] = "f" * 64
                with pytest.raises(DBAPIError), connection.begin_nested():
                    connection.scalar(text("SELECT ops.pdf_publication_projection(CAST(:receipt AS jsonb),:task,:attempt,:holder)"), {"receipt": json_bytes(forged).decode(), "task": retained["producer_task_id"], "attempt": retained["producer_attempt"], "holder": retained["producer_holder"]})
        before = tuple(calls)
        resumed = execute_data_demand(kernel.purpose("write"), result.demand_id, source_root=ROOT, admission_engine=kernel.purpose("admit"))
        assert resumed.demand_id == result.demand_id and resumed.receipt_count == 0
        assert tuple(calls) == before


@pytest.mark.parametrize("effect,factory", [(PDF_ORGANIZATION_EFFECT, PDF_ORGANIZATION_FACTORY), (PDF_ENRICHMENT_EFFECT, PDF_ENRICHMENT_FACTORY), (PDF_INTEGRATION_EFFECT, PDF_INTEGRATION_FACTORY)])
def test_native_pdf_transform_eligibility_matches_only_exact_effect_factory_pair(native_rollback, effect, factory):
    definition = {"profile": "command", "implementation_revision": "implementation-slice:captured", "support_contract": {"effects": [asdict(effect)], "capabilities": {"preparation": "pdf-native", "forms": ["scalar"], "prepared_factory": {"entrypoint": factory, "source_digest": "a" * 64}}}}
    query = text("SELECT coalesce(ops.ddo_pdf_command_eligible(jsonb_populate_record(NULL::sem.data_operation_definition,CAST(:value AS jsonb))),false)")
    connection = native_rollback.connection
    assert connection.scalar(query, {"value": json_bytes(definition).decode()}) is True
    invalid = deepcopy(definition)
    invalid["support_contract"]["capabilities"]["prepared_factory"]["entrypoint"] = PDF_INTEGRATION_FACTORY if factory != PDF_INTEGRATION_FACTORY else PDF_ENRICHMENT_FACTORY
    assert connection.scalar(query, {"value": json_bytes(invalid).decode()}) is False
