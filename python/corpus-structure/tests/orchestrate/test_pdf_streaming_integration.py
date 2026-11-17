"""Real private PostgreSQL/IPC composition with a scripted native provider.

This establishes custody and lifecycle integration, not actual OCR/model execution
or source fidelity. Only the provider is replaced inside the spawned child.
"""

from pathlib import Path
from types import SimpleNamespace

import pytest
from semantic.current_pdf_source_support import _current_pdf_source
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.ingest.pdf_stream_types import PdfStreamReply
from corpus_structure.ingest.pdf_worker import PdfWorker
from corpus_structure.orchestrate import pdf_streaming
from corpus_structure.semantic.pdf_staging import inspect_pdf_progress


class _ScriptedDocumentConverter:
    """External Docling provider control; application preparation/hooks remain actual."""

    def __init__(self, *, allowed_formats, format_options):
        from docling.models.stages.code_formula.code_formula_vlm_model import CodeFormulaVlmModel

        option = format_options[allowed_formats[0]]
        self.pipeline = object.__new__(option.pipeline_cls)
        self.pipeline.pipeline_options = option.pipeline_options
        self.pipeline.heading_hierarchy_model = SimpleNamespace(
            retain_parsed_lines=lambda page: None
        )
        formula = object.__new__(CodeFormulaVlmModel)
        formula.elements_batch_size = 1
        formula.engine = None
        self.native_images_scale = formula.images_scale
        self.pipeline.enrichment_pipe = [formula]
        self.pipeline.assemble_model = SimpleNamespace(options=None)
        self.initialized_pipelines = {"control": self.pipeline}

    def initialize_pipeline(self, input_format):
        pass

    def convert(self, source, *, raises_on_error, **options):
        from docling.datamodel.base_models import AssembledUnit, Page
        from docling_core.types.doc import (
            BoundingBox,
            DocItemLabel,
            DoclingDocument,
            PageItem,
            ProvenanceItem,
            Size,
        )
        from PIL import Image

        # Supply the actual native formula-stage raster capability. The application
        # captures it before release; this provider control has no rendering backend.
        side = round(10 * self.native_images_scale)
        with Image.new("RGB", (side, side), (3, 5, 7)) as image:
            page = Page(
                page_no=1,
                size=Size(width=10, height=10),
                assembled=AssembledUnit(elements=[], headers=[], body=[]),
            )
            page._image_cache = {self.native_images_scale: image}
            self.pipeline._release_page_resources(
                SimpleNamespace(
                    payload=page,
                    page_no=1,
                    is_failed=False,
                    error=None,
                    conv_res=SimpleNamespace(confidence=SimpleNamespace(pages={}), errors=[]),
                )
            )
            assert not page._image_cache and page.assembled is None
        document = DoclingDocument(name="scripted provider control")
        document.pages[1] = PageItem(page_no=1, size=Size(width=10, height=10))
        document.add_text(
            label=DocItemLabel.TEXT,
            text="Private control Ω",
            prov=ProvenanceItem(
                page_no=1,
                bbox=BoundingBox(l=1, t=1, r=9, b=3, coord_origin="TOPLEFT"),
                charspan=(0, 17),
            ),
        )
        return SimpleNamespace(
            document=document,
            status=SimpleNamespace(value="success"),
            errors=(),
            input=SimpleNamespace(release=lambda: None),
        )


def _controlled_native_child(connection, recipe, assets, writer_lease=None):
    # Replace only the external library provider, preserving model-owned application bindings.
    from docling import document_converter

    from corpus_structure.ingest import pdf_worker

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(document_converter, "DocumentConverter", _ScriptedDocumentConverter)
        pdf_worker._native_child(connection, recipe, assets, writer_lease)


def test_real_private_native_pipeline_retains_pages_then_adopts_after_retirement(
    scenario_seeds, tmp_path, monkeypatch
):
    # The current source demand owns original admission, actual capture/discovery
    # requests and their independent physical task/attempt/publication fences.
    # Only the external Docling converter is controlled inside the actual child.
    monkeypatch.setattr(PdfWorker, "_child_target", staticmethod(_controlled_native_child))
    original_stream = PdfWorker.stream
    replies = []
    workers = []

    def inspect_reply(self, *args, **kwargs):
        workers.append(self)
        result = original_stream(self, *args, **kwargs)
        assert isinstance(result, PdfStreamReply)
        assert not hasattr(result, "document") and not hasattr(result, "native")
        assert result.record_replays and result.page_replays
        replies.append(result)
        return result

    # Execute the real adopters while checking the conversion-child boundary.
    # A callback may ACK durable spool custody, but native uptake begins only
    # after every producer process has been physically retired.
    from corpus_structure.semantic import pdf_publication, pdf_staging

    def after_retirement(actual):
        def checked(*args, **kwargs):
            assert workers and all(worker.closed and worker.pid is None for worker in workers)
            return actual(*args, **kwargs)

        return checked

    monkeypatch.setattr(
        pdf_staging, "adopt_pdf_batch", after_retirement(pdf_staging.adopt_pdf_batch)
    )
    monkeypatch.setattr(
        pdf_publication,
        "adopt_pdf_companions",
        after_retirement(pdf_publication.adopt_pdf_companions),
    )
    original_run = pdf_streaming.run_private_native_pdf_build
    adopted, private = [], []

    def inspect_private(engine, *args, **kwargs):
        assert kwargs["owned_check"] is not None
        build = original_run(engine, *args, **kwargs, on_adopted=adopted.append)
        assert not hasattr(build, "content_digest")
        with engine.begin() as connection:
            receipts = inspect_pdf_progress(connection, build)
        private.append((build, receipts, Path(kwargs["directory"])))
        return build

    monkeypatch.setattr(pdf_streaming, "run_private_native_pdf_build", inspect_private)
    with _current_pdf_source(scenario_seeds, tmp_path, monkeypatch, stream=inspect_reply) as source:
        assert len(replies) == len(private) == 1
        assert adopted
        build, receipts, directory = private[0]
        assert not list(directory.glob("pdf-source-*")), "source ends after child settlement"
        callback_receipts = {receipt.replay_key: receipt for receipt in adopted}
        persisted_receipts = {receipt.replay_key: receipt for receipt in receipts}
        assert len(callback_receipts) == len(adopted), "each producer batch acknowledged once"
        assert {key: persisted_receipts[key] for key in callback_receipts} == callback_receipts
        assert persisted_receipts.keys() - callback_receipts.keys() == {
            "native:runtime-report:fields:0"
        }
        assert sum(receipt.row_count for receipt in receipts) > 10
        assert not any(receipt.replay_key.startswith("page:") for receipt in receipts)
        manifests = list(directory.glob("*/attempt-*/manifest.jsonl"))
        assert len(manifests) == 1
        import json

        entries = [json.loads(line) for line in manifests[0].read_text().splitlines()]
        assert entries[0]["attempt"] == build.attempt
        assert {item["replay"]["family"] for item in entries[1:] if "replay" in item} >= {
            "page",
            "native-raster",
        }
        assert any(receipt.replay_key.startswith("ipc:native:") for receipt in receipts)
        assert any(receipt.replay_key.startswith("ipc:artifact_stream:") for receipt in receipts)
        with source.kernel.purpose("read").connect() as connection:
            from corpus_structure.serve.selected_pdf import acquire_selected_pdf_source

            selected, _page = source.publication(connection)
            acquired = acquire_selected_pdf_source(connection, selected)
            assert acquired.receipt.publication.task_id == build.task_id
            for relation in ("ops.pdf_stage_native", "ops.pdf_stage_artifact_part"):
                with pytest.raises(DBAPIError), connection.begin_nested():
                    connection.execute(text(f"SELECT * FROM {relation}"))


@pytest.mark.parametrize("restored", [{1, 3}, {1, 2, 3}])
def test_resumed_pipeline_limits_page_work_and_restores_full_assembly(monkeypatch, restored):
    from docling import document_converter
    from docling.datamodel.base_models import ConversionStatus
    from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline

    from corpus_structure.ingest.pdf import PdfConverter, PdfRecipe

    observations = []

    def restored_pages(result, expected):
        observations.append(("restore", tuple(expected)))
        result.pages = [SimpleNamespace(page_no=number) for number in expected]

    spool = SimpleNamespace(restored_pages=restored, restore_pages=restored_pages)
    monkeypatch.setattr(document_converter, "DocumentConverter", _ScriptedDocumentConverter)
    converter = PdfConverter(
        PdfRecipe(
            "a" * 40,
            "b" * 40,
            device="cpu",
            ocr_device="cpu",
            recipe_id="docling-standard-pdf-stream-v1",
        ),
        stream_spool=spool,
    )
    converter._prepare()
    pipeline = next(iter(converter._converter.initialized_pipelines.values()))
    monkeypatch.setattr(
        StandardPdfPipeline, "_get_expected_page_nos", lambda self, result: [1, 2, 3]
    )

    def build(self, result):
        missing = self._get_expected_page_nos(result)
        assert missing == [2]
        observations.append(("build", tuple(missing)))
        result.pages = [SimpleNamespace(page_no=2)]
        return result

    def assemble(self, result):
        assert [page.page_no for page in result.pages] == [1, 2, 3]
        assert self._get_expected_page_nos(result) == [1, 2, 3]
        observations.append(("assemble", (1, 2, 3)))
        return result

    monkeypatch.setattr(StandardPdfPipeline, "_build_document", build)
    monkeypatch.setattr(StandardPdfPipeline, "_assemble_document", assemble)
    result = SimpleNamespace(
        pages=[],
        status=ConversionStatus.SUCCESS,
        input=SimpleNamespace(_backend=SimpleNamespace(get_document_outline=lambda: [])),
    )
    pipeline._build_document(result)
    pipeline._assemble_document(result)
    expected = [] if len(restored) == 3 else [("build", (2,))]
    assert observations == [*expected, ("restore", (1, 2, 3)), ("assemble", (1, 2, 3))]
    assert pipeline._spool_missing_pages is None and pipeline._spool_expected_pages is None
