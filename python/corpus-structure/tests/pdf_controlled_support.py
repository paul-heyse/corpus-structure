"""Recipe-owned controlled PDF content through the production stream protocol."""

from __future__ import annotations

import json
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import patch


def _scripted_pipeline_init(pipeline, pipeline_options):
    """External native pipeline control; application preparation remains actual."""
    from docling.models.stages.code_formula.code_formula_vlm_model import CodeFormulaVlmModel

    pipeline.pipeline_options = pipeline_options
    pipeline.heading_hierarchy_model = SimpleNamespace(retain_parsed_lines=lambda page: None)
    formula = object.__new__(CodeFormulaVlmModel)
    formula.elements_batch_size = 1
    formula.engine = None
    pipeline._control_native_images_scale = formula.images_scale
    pipeline.enrichment_pipe = [formula]
    pipeline.assemble_model = SimpleNamespace(options=None)


def _scripted_pipeline_execute(pipeline, source, *, raises_on_error, progress=None):
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
    side = round(10 * pipeline._control_native_images_scale)
    with Image.new("RGB", (side, side), (3, 5, 7)) as image:
        page = Page(
            page_no=1,
            size=Size(width=10, height=10),
            assembled=AssembledUnit(elements=[], headers=[], body=[]),
        )
        page._image_cache = {pipeline._control_native_images_scale: image}
        pipeline._release_page_resources(
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


@contextmanager
def scripted_pdf_pipeline():
    from docling.datamodel import document
    from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline

    def input_document(*args, **kwargs):
        return SimpleNamespace(valid=True, release=lambda: None)

    with (
        patch.object(StandardPdfPipeline, "__init__", _scripted_pipeline_init),
        patch.object(StandardPdfPipeline, "execute", _scripted_pipeline_execute),
        patch.object(document, "InputDocument", input_document),
    ):
        yield


@dataclass(frozen=True)
class ControlledPdfContent:
    document_json: bytes
    formula_outcomes: tuple = ()
    conversion_status: str = "success"
    errors: tuple[str, ...] = ()
    candidate_pages: tuple[bytes, ...] = ()

    @classmethod
    def from_document(
        cls,
        document,
        *,
        formula_outcomes=(),
        conversion_status="success",
        errors=(),
        candidate_pages=(),
    ):
        return cls(
            document.model_dump_json(
                by_alias=True, exclude_none=True, exclude_computed_fields=True
            ).encode(),
            tuple(formula_outcomes),
            conversion_status,
            tuple(errors),
            tuple(json.dumps(page.to_wire(), sort_keys=True).encode() for page in candidate_pages),
        )


_preparation_reports = OrderedDict()


def controlled_preparation_report(recipe, assets, spool):
    from corpus_structure.ingest.pdf import PdfConverter

    key = (recipe.to_bytes(), assets)
    if key in _preparation_reports:
        _preparation_reports.move_to_end(key)
        return _preparation_reports[key]
    with scripted_pdf_pipeline():
        converter = PdfConverter(recipe, assets=assets, stream_spool=spool)
        converter._prepare()
        report = converter.prepared_options_report
    _preparation_reports[key] = report
    if len(_preparation_reports) > 32:
        _preparation_reports.popitem(last=False)
    return report


class _ControlledPdfProducer:
    def __init__(self, worker, content):
        self.worker, self.content = worker, content

    def prepare(self, source, spool):
        return controlled_preparation_report(self.worker.recipe, self.worker.assets, spool)

    def convert(self, source, spool, *, page_range):
        from docling_core.types.doc import DoclingDocument

        from corpus_structure.ingest.pdf_candidates import CandidatePage, InlineCandidate
        from corpus_structure.ingest.pdf_streaming import StreamingPdfResult

        spool.active()
        for raw in self.content.candidate_pages:
            value = json.loads(raw)
            value["candidates"] = tuple(
                InlineCandidate.from_wire(row) for row in value["candidates"]
            )
            value["ocr_regions"] = tuple(value.get("ocr_regions", ()))
            spool.capture_candidates(CandidatePage(**value))
        return StreamingPdfResult(
            DoclingDocument.model_validate_json(self.content.document_json),
            spool,
            self.content.conversion_status,
            self.content.errors,
            self.worker.recipe.to_bytes(),
            self.content.formula_outcomes,
        )


def controlled_pdf_stream(worker, request, content, *, on_replay, check_active=None):
    from corpus_structure.ingest.pdf_streaming import run_pdf_stream

    return run_pdf_stream(
        request,
        _ControlledPdfProducer(worker, content),
        on_replay=on_replay,
        check_active=check_active,
    )


@contextmanager
def controlled_pdf_converter(content):
    from corpus_structure.ingest.pdf_worker import PdfWorker

    def stream(worker, request, *, on_replay, check_active=None):
        return controlled_pdf_stream(
            worker, request, content, on_replay=on_replay, check_active=check_active
        )

    with patch.object(PdfWorker, "stream", stream):
        try:
            yield
        finally:
            _preparation_reports.clear()


def controlled_native_child(connection, recipe, assets, writer_lease=None, **resources):
    """Scripted peer for IPC tests, deliberately outside actual producer custody."""
    from corpus_structure.ingest.pdf_health import error_summary
    from corpus_structure.ingest.pdf_stream_types import PdfReplayReady, PdfStreamRequest
    from corpus_structure.ingest.pdf_streaming import StreamingPdfProducer, run_pdf_stream
    from corpus_structure.ingest.pdf_worker import NativeReply

    def acknowledged(replay):
        connection.send(PdfReplayReady(replay))
        if connection.recv() is not True:
            raise ValueError("controlled replay was not acknowledged")

    try:
        with scripted_pdf_pipeline():
            while (request := connection.recv()) is not None:
                if not isinstance(request, PdfStreamRequest):
                    raise TypeError("scripted peer only supports streaming requests")
                try:
                    result = run_pdf_stream(
                        request, StreamingPdfProducer(recipe, assets=assets), on_replay=acknowledged
                    )
                    connection.send(NativeReply(value=result))
                except Exception as error:
                    connection.send(NativeReply(error=error_summary(error)))
    finally:
        connection.close()
