"""Actual current source custody and DDO publication, with a controlled converter only.

The fixture creates no legacy run, method configuration, task alias or source-view row.
Native registration, task claims, publication receipts and semantic products remain real.
It requires the combined current native capture; the controlled converter is not provider evidence.
"""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import pytest

from corpus_structure.semantic.data_operation_artifacts import capture_port_generator_sources
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_storage import native_operation_declarations, native_protocol_sources
from corpus_structure.semantic.pdf_capture import pdf_capture_inputs, pdf_capture_operation_sources
from corpus_structure.semantic.pdf_domain import pdf_domain_dependencies
from corpus_structure.semantic.pdf_views import pdf_views_operation_sources
from corpus_structure.semantic.source_discovery import source_discovery_inputs, source_discovery_operation_sources
from corpus_structure.semantic.source_profiles import source_profile_inputs, source_profile_operation_sources, source_profile_declarations
from corpus_structure.semantic.types import SourceArtifact, SourceBundle, ResolvedDependencies, PreparationProfile
from semantic.data_operation_kernel_support import KernelRecipe, CapturedKernelInputs, Kernel

ROOT = Path(__file__).resolve().parents[4]
PROJECT = "current-source-catalog"


def current_pdf_recipe(directory):
    from corpus_structure.ingest.pdf import PdfRecipe
    from corpus_structure.ingest.pdf_assets import PreparedPdfAssets

    capture = pdf_capture_operation_sources(PdfRecipe("0" * 40, "1" * 40, device="cpu", ocr_device="cpu",
        recipe_id="docling-standard-pdf-stream-v1"), PreparedPdfAssets(directory, b"{}", ()), directory=directory / "owned")
    from corpus_structure.semantic.native_requests import pdf_region_inputs, pdf_region_operation_sources
    from corpus_structure.semantic.visual_requests import visual_operation_sources, visual_external_declaration
    from corpus_structure.semantic.primary_operations import combine_primary_sources
    sources = combine_primary_sources(pdf_views_operation_sources(capture), pdf_region_operation_sources(capture), visual_operation_sources(), source_discovery_operation_sources(), source_profile_operation_sources())
    core = ROOT / "python/corpus-structure/src/corpus_structure/model/semantic/core.yaml"
    bundle = source_profile_inputs(pdf_region_inputs(source_discovery_inputs(pdf_capture_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))))))
    native = native_protocol_sources()
    pdf = pdf_domain_dependencies(ResolvedDependencies())
    dependencies = data_operation_dependencies(ResolvedDependencies((*pdf.artifacts, *native, *capture_port_generator_sources())),
        (native_operation_declarations(native), visual_external_declaration(), source_profile_declarations()), sources)
    return KernelRecipe("current-pdf-source", "", None, "", project_id=None,
        execution_profile="source-native", captured_inputs=CapturedKernelInputs(bundle, dependencies, PreparationProfile(version="semantic-2")))


@dataclass(frozen=True)
class CurrentPdfSource:
    kernel: Kernel
    demand_id: str
    document_key: str
    original: bytes

    def publication(self, connection):
        from corpus_structure.serve.source_catalog import SourceCatalogRequest, read_source_catalog
        from corpus_structure.serve.selected_pdf import SelectedPdfSourceReference

        cursor = None
        for _ in range(100):
            page = read_source_catalog(connection, SourceCatalogRequest(project_id=PROJECT,
                demand_id=self.demand_id, cursor=cursor, limit=10, max_bytes=8 * 1024 * 1024))
            if page.rows:
                assert len(page.rows) == 1
                return SelectedPdfSourceReference.model_validate(page.rows[0]["selection"]), page
            if page.next_cursor is None:
                raise AssertionError("actual capture produced no selected publication")
            cursor = page.next_cursor
        raise AssertionError("bounded current source fixture did not reach its publication")

    def register(self, connection, target, *, selections=()):
        from corpus_structure.semantic.data_operation_service import NativeDemandRequest, DemandRoot, DemandOriginalSelection, create_native_demand
        from corpus_structure.semantic.data_operation_json import json_loads
        from corpus_structure.semantic.original_documents import acquire_original_document_selection
        original = acquire_original_document_selection(connection, project_id=PROJECT, document_key=self.document_key)
        root = original.root
        request = NativeDemandRequest(project_id=PROJECT, release_id=self.kernel.prepared.release_id,
            runtime_id=self.kernel.runtime, roots=(DemandRoot(subject=root.subject, original_source=root.original_source,
                analyzed_scope=json_loads(root.analyzed_scope)),), targets=(target,), selections=selections,
            original_sources={original.name: DemandOriginalSelection(reference=original.reference.model_dump(mode="python"), selectors=[{"scope": "whole-document"}])},
            inference="current-source-journey", execution_profile="source-native")
        return create_native_demand(connection, request)["demand_id"]


def _controlled_stream(self, source, *, spool_root, record_root, build_id, release_id, on_replay, check_active, **options):
    from docling_core.types.doc import BoundingBox, DocItemLabel, DoclingDocument, ProvenanceItem, Size
    from corpus_structure.ingest.pdf_stream_types import PdfStreamReply
    from corpus_structure.ingest.pdf_streaming import PdfStreamSpool, StreamingPdfResult

    check_active()
    document = DoclingDocument(name="Independent current source")
    document.add_page(page_no=1, size=Size(width=200, height=300))
    document.add_heading(text="1 Selected source", level=1)
    document.add_text(label=DocItemLabel.TEXT, text="Alice was running.", prov=ProvenanceItem(page_no=1,
        bbox=BoundingBox(l=10, t=20, r=150, b=40), charspan=(0, 18)))
    result = StreamingPdfResult(document, PdfStreamSpool(spool_root, check_active=check_active),
        "success", (), self.recipe.to_bytes(), ())
    occurrences = result.write_native_occurrence_batches(record_root.with_name(record_root.name + "-occurrences"),
        build_id=build_id, on_batch=on_replay)
    records = result.write_record_batches(record_root, build_id=build_id, release_id=release_id,
        source_digest=source.digest, on_batch=on_replay)
    return PdfStreamReply("success", (), self.recipe.to_bytes(), (), records + occurrences)


@pytest.fixture
def current_pdf_source(scenario_seeds, tmp_path, monkeypatch):
    import pypdfium2 as pdfium
    from corpus_structure.ingest import pdf_worker
    from corpus_structure.semantic.data_operation_demands import DemandPlanner, freeze_demand
    from corpus_structure.semantic.data_operation_service import execute_data_demand
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.identifiers import ProjectId, RealizationId, ReleaseId
    from corpus_structure.semantic.original_documents import register_original_document, acquire_original_document_selection
    from corpus_structure.core.evidence import document_key
    from hashlib import sha256

    monkeypatch.setattr(pdf_worker.PdfWorker, "stream", _controlled_stream)
    document = pdfium.PdfDocument.new()
    page = document.new_page(200, 300)
    page.close()
    output = BytesIO()
    document.save(output)
    document.close()
    original = output.getvalue()
    path = tmp_path / "independent-original.pdf"
    path.write_bytes(original)
    recipe = current_pdf_recipe(tmp_path)
    with scenario_seeds.commit_clone(recipe) as clone:
        stage = clone.stage
        kernel = Kernel(clone.admin, stage.preparation, stage.identities, recipe, clone)
        with kernel.purpose("write").begin() as connection:
            DataOperationStorage(connection).initialize_source_project({"project_id": ProjectId(PROJECT),
                "release_id": ReleaseId(kernel.prepared.release_id), "realization_id": RealizationId("current-source-empty")})
            register_original_document(connection, prepared=kernel.prepared, project_id=PROJECT,
                source_uri="independent-original.pdf", original_path=str(path), original=original, mime="application/pdf")
            key = document_key(PROJECT, "independent-original.pdf", sha256(original).hexdigest())
            selected = acquire_original_document_selection(connection, project_id=PROJECT, document_key=key)
            intent = freeze_demand(kernel.model, roots=(selected.root,), targets=("source.pdf_views/discovery",),
                original_sources=(selected.selection(),), inference="current-source-journey", execution_profile=recipe.execution_profile)
            demand = DemandPlanner(kernel.model, DataOperationStorage(connection)).register(intent,
                project=PROJECT, release=kernel.prepared.release_id, runtime=kernel.runtime)["demand_id"]
        path.unlink()  # The source owner must use retained custody, never a local fallback.
        result = execute_data_demand(kernel.purpose("write"), demand, source_root=ROOT,
            admission_engine=kernel.purpose("admit"), project_id=PROJECT, database_capacity=6)
        assert result.receipt_count == 2
        yield CurrentPdfSource(kernel, demand, key, original)
