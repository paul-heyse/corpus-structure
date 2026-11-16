"""Current claimed PDF requests with a finite controlled provider boundary.

Capture, organization, recognition retention, integration and publication use their
production paths. The scripted document/answers establish transport and custody,
not Docling/Nemotron accuracy or verified external provider execution.
"""

import json
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from hashlib import sha256
from pathlib import Path
from typing import Any

from conftest import settings_for_native_clone
from sqlalchemy import select

from corpus_structure.core.method import MethodSettings
from corpus_structure.ingest.pdf_recognition import RecognitionPage
from corpus_structure.ingest.pdf_stream_types import PdfStreamReply
from corpus_structure.ingest.pdf_streaming import PdfStreamSpool, StreamingPdfResult
from corpus_structure.orchestrate.source_operation import run_source_operation
from corpus_structure.orchestrate.source_request import SourceRunRequest, WholeDocument
from corpus_structure.semantic.data_operation_identity import decode_semantic_value
from corpus_structure.semantic.data_operation_service import read_data_demand
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.runtime import open_runtime_engine
from semantic.data_operation_kernel_support import Kernel
from semantic.data_operation_original_support import OriginalSeedRecipe
from semantic.pdf_native_source_support import IMAGE, make_native_source

import sys

from corpus_structure.ingest.pdf import PdfRecipe
from corpus_structure.ingest.pdf_assets import PreparedPdfAssets
from corpus_structure.ingest.pdf_hierarchy import SectionPolicy
from corpus_structure.ingest.pdf_recognition import NemotronRecipe
from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies, SourceArtifact, SourceBundle
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_artifacts import capture_port_generator_sources
from corpus_structure.semantic.data_operation_storage import native_operation_declarations, native_protocol_sources
from corpus_structure.semantic.pdf_capture import pdf_capture_inputs, pdf_capture_operation_sources
from corpus_structure.semantic.pdf_domain import pdf_domain_dependencies
from corpus_structure.semantic.pdf_transforms import PdfEnrichmentOptions, PdfIntegrationOptions, PdfRecognitionResources, pdf_transform_operation_sources
from corpus_structure.semantic.pdf_views import pdf_views_operation_sources
from corpus_structure.semantic.primary_operations import combine_primary_sources
from corpus_structure.semantic.source_discovery import source_discovery_inputs
from semantic.data_operation_kernel_support import CapturedKernelInputs, KernelRecipe

ROOT = Path(__file__).resolve().parents[4]

def current_pdf_recipe(directory):
    native = PdfRecipe(
        "0" * 40,
        "1" * 40,
        device="cpu",
        ocr_device="cpu",
        recipe_id="docling-standard-pdf-stream-v1",
    )
    assets = PreparedPdfAssets(directory, b"{}", ())
    capture = pdf_capture_operation_sources(native, assets, directory=directory / "owned")
    organization = pdf_transform_operation_sources(
        "organized",
        options=SectionPolicy("explicit-native-headings"),
        directory=directory / "owned",
    )
    enriched = pdf_transform_operation_sources(
        "enriched",
        recipe=native,
        assets=assets,
        options=PdfEnrichmentOptions(),
        directory=directory / "owned",
        input_operation="source.pdf_sections/organize",
    )
    worker = directory / "explicit-provider.py"
    worker.write_text(
        "raise AssertionError('controlled provider boundary must replace inference')\n"
    )
    integration = pdf_transform_operation_sources(
        "integrated",
        recognition_recipe=NemotronRecipe("2" * 64, "3" * 64),
        options=PdfIntegrationOptions(recovery_policy=None, integration_policy={}),
        resources=PdfRecognitionResources(
            python=sys.executable,
            script=str(worker),
            endpoint="http://127.0.0.1:8123/v1",
            receipts=str(directory / "receipts"),
            timeout_seconds=1,
        ),
        directory=directory / "owned",
        input_operation="source.pdf_sections/organize",
    )
    sources = combine_primary_sources(
        pdf_views_operation_sources(capture, mode="organized", transformation_sources=organization),
        pdf_views_operation_sources(capture, mode="enriched", transformation_sources=enriched),
        pdf_views_operation_sources(capture, mode="integrated", transformation_sources=integration),
    )
    bundle = source_discovery_inputs(
        pdf_capture_inputs(
            SourceBundle(
                "toy_semantic",
                (
                    SourceArtifact(
                        "toy_semantic", (ROOT / "domains/toy/semantic.yaml").read_bytes()
                    ),
                    SourceArtifact(
                        "semantic_core",
                        (
                            ROOT
                            / "python/corpus-structure/src/corpus_structure/model/semantic/core.yaml"
                        ).read_bytes(),
                    ),
                ),
            )
        )
    )
    native_sources = native_protocol_sources()
    dependencies = pdf_domain_dependencies(ResolvedDependencies())
    dependencies = data_operation_dependencies(
        ResolvedDependencies(
            (*dependencies.artifacts, *native_sources, *capture_port_generator_sources())
        ),
        (native_operation_declarations(native_sources),),
        sources,
    )
    return KernelRecipe(
        "controlled-pdf-transform-demand",
        "",
        None,
        "",
        project_id=None,
        execution_profile="source-native",
        captured_inputs=CapturedKernelInputs(
            bundle, dependencies, PreparationProfile(version="semantic-2")
        ),
    )



RICH_RESPONSE = (
    b"<x_0.05><y_0.03>equal<x_0.30><y_0.07><class_Text>"
    b"<x_0.05><y_0.13>equal<x_0.30><y_0.17><class_Text>"
    b"<x_0.05><y_0.333333>\\begin{tabular}{cc}$x+1$ & 2\\end{tabular}"
    b"<x_0.55><y_0.4><class_Table>"
    b'<x_0.6><y_0.55><chart type="line">\n| Time | Speed (m/s) |\n|---|---|\n|1|2|'
    b"<x_0.95><y_0.9><class_Chart>"
    b"<x_0.6><y_0.2>Value $y+2$ follows<x_0.95><y_0.25><class_Text>"
)


@dataclass
class CurrentPdfIntegration:
    kernel: Any
    clone: Any
    original: Any
    settings: Any
    directory: Path
    calls: list[str] = field(default_factory=list)
    observations: list[tuple[ProductReference, Any]] = field(default_factory=list)
    claims: dict[str, Any] = field(default_factory=dict)
    drafts: dict[str, Any] = field(default_factory=dict)
    publications: dict[str, ProductReference] = field(default_factory=dict)
    values: dict[str, dict] = field(default_factory=dict)
    demand_id: str | None = None
    failure: Any = None

    @property
    def prepared(self):
        return self.kernel.prepared

    def reader(self):
        return self.kernel.purpose("read")


@contextmanager
def current_integration_journey(
    scenario_seeds, tmp_path, monkeypatch, native_settings, *,
    raw_responses=(RICH_RESPONSE, RICH_RESPONSE),
    outcome="succeeded", before_draft=None, before_observation=None,
    expect_unresolved_page=False,
):
    from corpus_structure.ingest import pdf_recognition, pdf_worker
    from corpus_structure.orchestrate import pdf_streaming
    from corpus_structure.semantic import pdf_integrated

    target = OriginalSeedRecipe(current_pdf_recipe(tmp_path))
    with scenario_seeds.commit_clone(target) as clone, monkeypatch.context() as patches:
        kernel = Kernel(clone.admin, clone.stage.kernel.preparation,
                        clone.stage.kernel.identities, target.target, clone)
        original = clone.stage.original.reference
        settings = settings_for_native_clone(native_settings, clone.admin.url.database)
        case = CurrentPdfIntegration(kernel, clone, original, settings, tmp_path)

        def controlled_stream(self, source, *, spool_root, record_root, build_id,
                              release_id, on_replay, check_active, **options):
            from docling_core.types.doc import DoclingDocument

            check_active()
            case.calls.append("capture")
            supplied = make_native_source(source.path.read_bytes())
            document = DoclingDocument.model_validate(supplied.payload["document"])
            document.pages.pop(2)
            document.texts[0].prov = document.texts[0].prov[:1]
            document.add_heading(text="1 Controlled", level=1)
            # The independent fixture retains equal text in distinct native cells.
            assert document.tables[0].data.table_cells[0].text == "equal"
            streamed = StreamingPdfResult(
                document, PdfStreamSpool(spool_root, check_active=check_active),
                "success", (), self.recipe.to_bytes(), (),
            )
            occurrences = streamed.write_native_occurrence_batches(
                record_root.with_name(record_root.name + "-occurrences"),
                build_id=build_id, on_batch=on_replay,
            )
            records = streamed.write_record_batches(
                record_root, build_id=build_id, release_id=release_id,
                source_digest=source.digest, on_batch=on_replay,
            )
            return PdfStreamReply("success", (), self.recipe.to_bytes(), (), records + occurrences)

        def controlled_recognition(self, source, recipe, pages, *, check_active, **options):
            case.calls.append("recognize")
            assert tuple(pages) == (1,)
            directory = tmp_path / "controlled-actual-requests"
            directory.mkdir()
            (directory / "submitted.png").write_bytes(IMAGE)
            for ordinal, raw in enumerate(raw_responses):
                row = dict(
                    ordinal=ordinal, stage="fullpage" if ordinal == 0 else "detection",
                    outcome="succeeded" if raw is not None else "failed",
                    submitted_image="submitted.png", submitted_digest=sha256(IMAGE).hexdigest(),
                    width=4, height=6, prompt="Independent finite controlled recognition",
                    settings={},
                )
                if raw is not None:
                    name = f"response-{ordinal:03d}.txt"
                    (directory / name).write_bytes(raw)
                    row.update(raw_response=name, finish_reason="stop")
                else:
                    row["diagnostic"] = "controlled connection closed before response"
                (directory / f"request-{ordinal:03d}.json").write_text(json.dumps(row))
            check_active()
            yield RecognitionPage(1, directory, {"outcome": outcome}, dict(
                status="coarse", normalization="none", source_space="pdf_points",
                target_space="submitted_pixels", page_width=200.0, page_height=300.0,
                page_rotation=0, crop_left=0.0, crop_top=0.0, crop_right=200.0,
                crop_bottom=300.0, affine=[0.02, 0.0, 0.0, 0.02, 0.0, 0.0],
            ))

        publish_observation = pdf_integrated.store_pdf_observation

        def retain_observation(connection, **arguments):
            if before_observation is not None:
                before_observation(case, connection, arguments)
            digest = publish_observation(connection, **arguments)
            product = arguments["product"]
            case.observations.append((ProductReference(
                arguments["task_id"], product.values()["product_key"], digest
            ), product))
            return digest

        publish_draft = pdf_streaming.publish_pdf_record_draft

        def retained_draft(engine, claim, holder, draft, **arguments):
            # A small finite fixture materializes its actual Arrow journal once.
            # Publication still consumes the same rows through the real writer.
            draft = replace(draft, companions={
                family: tuple(rows) for family, rows in (draft.companions or {}).items()
            })
            case.claims[draft.product_key] = claim
            case.drafts[draft.product_key] = draft
            if before_draft is not None:
                before_draft(case, engine, claim, holder, draft, arguments, publish_draft)
            publication = publish_draft(engine, claim, holder, draft, **arguments)
            case.publications[draft.product_key] = ProductReference(
                publication.task_id, publication.product_key, publication.logical_digest
            )
            return publication

        patches.setattr(pdf_worker.PdfWorker, "stream", controlled_stream)
        patches.setattr(pdf_recognition.RecognitionWorker, "_recognize_pages", controlled_recognition)
        patches.setattr(pdf_integrated, "store_pdf_observation", retain_observation)
        patches.setattr(pdf_streaming, "publish_pdf_record_draft", retained_draft)
        request = SourceRunRequest(
            project_id=original.project_id, release_id=kernel.prepared.release_id,
            runtime_id=kernel.runtime, domain="toy", workflow="capture",
            selection=WholeDocument(), documents=(original.document_key,),
            pdf_mode="integrated", recognition_pages=(1,),
            targets=("source.pdf_integrated_views/discovery",),
        )
        with open_runtime_engine(settings, "current-rich-pdf-integration", purpose="write", max_size=6) as engine:
            from corpus_structure.orchestrate.data_operations import NativeDemandExecutionError

            try:
                result = run_source_operation(
                    engine, request, MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
                    source_root=ROOT, admission_engine=kernel.purpose("admit"),
                )
            except NativeDemandExecutionError as error:
                if not expect_unresolved_page:
                    raise
                assert any(
                    isinstance(failure, RuntimeError)
                    and str(failure) == "unresolved triple-pass physical pages: [1]"
                    for failure in error.failures
                )
                case.failure = error
                result = error.result
            else:
                assert not expect_unresolved_page, "failed page unexpectedly completed integration"
        case.demand_id = result.demand_id
        with clone.admin.connect() as connection:
            snapshot = read_data_demand(connection, result.demand_id, view="products")
        obligations = {row["obligation_id"]: row for row in snapshot["obligations"]}
        for use in snapshot["uses"]:
            if use["fate"] != "fulfilled":
                continue
            operation = obligations[use["obligation_id"]]["operation_id"]
            case.values[operation] = {
                product["role"]: decode_semantic_value(product["body"])
                for product in use["products"]
            }
        yield case
