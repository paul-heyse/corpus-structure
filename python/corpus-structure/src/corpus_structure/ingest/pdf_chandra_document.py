"""Pinned Docling PDF conversion with lossless, bounded Chandra page capture."""

from __future__ import annotations

import json
from collections.abc import Iterable
from contextlib import closing
from hashlib import sha256
from importlib.metadata import version
from io import BytesIO
from math import isclose
from pathlib import Path
from time import monotonic
from typing import TYPE_CHECKING, Any, Literal

from docling.backend.docling_parse_backend import ThreadedDoclingParseDocumentBackend
from docling.backend.pypdfium2_backend import (
    PyPdfiumDocumentBackend,
    PyPdfiumPageBackend,
    pypdfium2_lock,
)
from docling.datamodel.backend_options import ThreadedDoclingParseBackendOptions
from docling.datamodel.base_models import InputFormat, Page
from docling.datamodel.document import ConversionResult, DocumentStream
from docling.datamodel.pipeline_options import VlmPipelineOptions
from docling.datamodel.settings import settings
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.models.stages.vlm_convert.vlm_convert_model import _prediction_from_engine_output
from docling.pipeline.vlm_pipeline import VlmPipeline

from .pdf_chandra import ChandraRuntime
from .pdf_recognition import render_affine

if TYPE_CHECKING:
    from docling.datamodel.progress import ProgressCallback
    from docling.models.inference_engines.vlm import VlmEngineInput, VlmEngineOutput

_RENDER_SCALE = 2.0


def _retain(path: Path, content: bytes) -> str:
    pending = path.with_name(path.name + ".pending")
    pending.write_bytes(content)
    pending.replace(path)
    return sha256(content).hexdigest()


def _json(path: Path, value: Any) -> str:
    return _retain(path, (json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n").encode())


def _source_geometry(original: bytes, page_range: tuple[int, int] | None):
    from pypdfium2 import PdfDocument

    geometry = {}
    with PdfDocument(original) as document:
        first, last = page_range or (1, len(document))
        if not 1 <= first <= last <= len(document):
            raise ValueError("Chandra PDF conversion range is outside the original")
        for page_no in range(first, last + 1):
            with closing(document[page_no - 1]) as page:
                media_box = page.get_mediabox()
                if media_box is None:
                    raise ValueError("Chandra PDF conversion requires a physical media box")
                geometry[page_no] = {
                    "media_box": list(media_box),
                    "crop_box": list(page.get_bbox()),
                    "rotation": page.get_rotation(),
                    "visible_size": list(page.get_size()),
                }
    return (first, last), geometry


class _ReferenceRasterPage(PyPdfiumPageBackend):
    """Use the existing PDFium full-page raster recipe inside Docling conversion."""

    def get_page_image(self, scale=1, cropbox=None):
        if cropbox is not None:
            return super().get_page_image(scale, cropbox)
        with pypdfium2_lock, closing(self._require_page().render(scale=scale)) as bitmap:
            return bitmap.to_pil().convert("RGB")


class _ReferenceRasterPdf(PyPdfiumDocumentBackend):
    def load_page(self, page_no: int) -> PyPdfiumPageBackend:
        with pypdfium2_lock:
            return _ReferenceRasterPage(self._pdoc, self.document_hash, page_no)


class _DocumentCapture:
    def __init__(
        self,
        output: Path,
        geometry: dict[int, dict[str, Any]],
        *,
        original_sha256: str,
        batch_size: int,
    ):
        self.output = output
        self.geometry = geometry
        self.original_sha256 = original_sha256
        self.batch_size = batch_size
        self.raw: dict[int, dict[str, Any]] = {}
        self.mapped: set[int] = set()
        self.batches: list[dict[str, Any]] = []
        self.assembly_seconds = 0.0

    def observe(self, pages, inputs, predict):
        # The installed stage caches full-page renders. Object identity binds the
        # actual engine argument to its physical page, including out-of-order batches.
        by_image = {}
        for page in pages:
            image = page.get_image(scale=_RENDER_SCALE)
            if image is None:
                continue
            if id(image) in by_image:
                raise ValueError("Docling reused the same rendered image for distinct pages")
            by_image[id(image)] = page
        submitted = []
        for item in inputs:
            page = by_image.get(id(item.image))
            if page is None or page.size is None:
                raise ValueError("Chandra engine input has no exact rendered Docling page")
            if item.image.mode != "RGB" or "transparency" in item.image.info:
                raise ValueError("Chandra PDF conversion requires opaque RGB engine inputs")
            width, height = item.image.size
            if not (
                min(width, height) > 0
                and max(width, height) <= 8192
                and width * height <= 24_000_000
            ):
                raise ValueError("Chandra PDF frame exceeds the visual raster limit")
            buffer = BytesIO()
            item.image.save(buffer, format="PNG")
            submitted.append((page, buffer.getvalue(), width, height))
        numbers = [page.page_no for page, _, _, _ in submitted]
        if len(numbers) != len(set(numbers)) or any(number in self.raw for number in numbers):
            raise ValueError("Chandra document inference repeated a physical page")
        if any(number not in self.geometry for number in numbers):
            raise ValueError("Chandra document inference submitted a page outside its scope")
        if self.batch_size > 1:
            next_page = next(iter(self.geometry)) + len(self.raw)
            last_page = min(next_page + self.batch_size - 1, next(reversed(self.geometry)))
            if numbers != list(range(next_page, last_page + 1)):
                raise ValueError("Chandra document batch differs from its ordered page scope")

        started = monotonic()
        outputs = predict(inputs)
        elapsed = monotonic() - started
        if len(outputs) != len(submitted):
            raise ValueError(
                f"Chandra returned {len(outputs)} predictions for {len(submitted)} submitted pages"
            )
        for (page, png, width, height), output in zip(submitted, outputs, strict=True):
            assert page.size is not None
            directory = self.output / "pages" / str(page.page_no)
            directory.mkdir()
            prediction = _prediction_from_engine_output(output)
            files = {
                "submitted.png": _retain(directory / "submitted.png", png),
                "response.html": _retain(directory / "response.html", output.text.encode()),
                "prediction.json": _json(
                    directory / "prediction.json",
                    prediction.model_dump(mode="json", exclude={"text"}),
                ),
            }
            boxes = self.geometry[page.page_no]
            matches = all(
                isclose(points, visible, abs_tol=1e-4) and abs(pixels - points * _RENDER_SCALE) <= 1
                for points, visible, pixels in zip(
                    (page.size.width, page.size.height),
                    boxes["visible_size"],
                    (width, height),
                    strict=True,
                )
            )
            transform = (
                render_affine(
                    media=boxes["media_box"],
                    crop=boxes["crop_box"],
                    rotation=boxes["rotation"],
                    width=width,
                    height=height,
                )
                if matches
                else {"status": "unknown"}
            )
            frame = {
                "width": width,
                "height": height,
                "page_width": page.size.width,
                "page_height": page.size.height,
                "docling_points_to_submitted": [
                    width / page.size.width,
                    0,
                    0,
                    height / page.size.height,
                    0,
                    0,
                ],
                "original_boxes": boxes,
                "transform": transform,
            }
            row = {
                "original_sha256": self.original_sha256,
                "page_no": page.page_no,
                "batch_page_nos": numbers,
                "frame": frame,
                "engine_stop_reason": output.stop_reason,
                "inference_seconds": elapsed,
                "files": files,
            }
            _json(directory / "raw.receipt.json", row)
            self.raw[page.page_no] = row
        self.batches.append({"page_nos": numbers, "inference_seconds": elapsed})
        return outputs

    def save_page(self, page_no, document):
        if page_no not in self.raw:
            return
        directory = self.output / "pages" / str(page_no)
        digest = _json(directory / "document.json", document.export_to_dict())
        row = self.raw[page_no]
        _json(
            directory / "receipt.json",
            {**row, "files": {**row["files"], "document.json": digest}},
        )
        self.mapped.add(page_no)


class ChandraDocumentRuntime:
    """Reuse the verified Chandra model in an isolated, warm Docling PDF worker."""

    def __init__(
        self,
        artifacts: Path,
        *,
        batch_size: int = 1,
        renderer: Literal["docling-parse", "pdfium-reference"] = "docling-parse",
    ):
        if batch_size not in {1, 2}:
            raise ValueError("the Chandra document trial supports batches of one or two")
        started = monotonic()
        self.runtime = ChandraRuntime(artifacts)
        self.prepare_seconds = monotonic() - started
        self.batch_size = batch_size
        self.renderer = renderer
        self._parser_threads = 1 if batch_size == 2 else 2
        self.load_seconds = 0.0
        self._converter: DocumentConverter | None = None
        self._capture: _DocumentCapture | None = None

    def identity(self) -> dict[str, Any]:
        return {
            **self.runtime.identity(),
            "document_recipe": "docling-chandra-pdf-v1",
            "pdf_backend": (
                "ThreadedDoclingParseDocumentBackend"
                if self.renderer == "docling-parse"
                else "PyPdfiumDocumentBackend-reference-raster"
            ),
            "docling_parse": version("docling-parse"),
            "pypdfium2": version("pypdfium2"),
            "render_scale": _RENDER_SCALE,
            "parser_threads": self._parser_threads if self.renderer == "docling-parse" else None,
            "max_concurrent_results": 4 if self.renderer == "docling-parse" else None,
            "batch_size": self.batch_size,
        }

    def __enter__(self):
        worker = self

        class ObservedChandraPipeline(VlmPipeline):
            def _initialize_new_runtime_system(self, pipeline_options):
                # ChandraRuntime owns the single model and validates the effective
                # device. Docling owns batching, parsing and document assembly.
                assert worker.runtime._model is not None
                self.force_backend_text = False
                self.keep_images = False
                self.build_pipe = [worker.runtime._model]

            def _apply_on_pages(
                self, conv_res: ConversionResult, page_batch: Iterable[Page]
            ) -> Iterable[Page]:
                capture = worker._capture
                model = worker.runtime._model
                assert capture is not None and model is not None
                pages = list(page_batch)
                engine = model.engine
                predict = engine.predict_batch

                def observed(input_batch: list[VlmEngineInput]) -> list[VlmEngineOutput]:
                    return capture.observe(pages, input_batch, predict)

                # Only this verified instance in the isolated worker is observed.
                engine.predict_batch = observed
                try:
                    converted = list(super()._apply_on_pages(conv_res, pages))
                finally:
                    delattr(engine, "predict_batch")
                yield from converted

            def _finalize_page_document(self, conv_res, page):
                document = super()._finalize_page_document(conv_res, page)
                assert worker._capture is not None
                worker._capture.save_page(page.page_no, document)
                return document

            def _join_page_documents(self, page_documents):
                started = monotonic()
                document = super()._join_page_documents(page_documents)
                assert worker._capture is not None
                worker._capture.assembly_seconds += monotonic() - started
                return document

        try:
            started = monotonic()
            self.runtime._load_model()
            self.load_seconds = monotonic() - started
            options = VlmPipelineOptions(
                artifacts_path=self.runtime._artifacts,
                accelerator_options=self.runtime._accelerator,
                vlm_options=self.runtime._options,
                enable_remote_services=False,
                generate_page_images=False,
                generate_picture_images=False,
                images_scale=_RENDER_SCALE,
                document_timeout=None,
            )
            backend = ThreadedDoclingParseDocumentBackend
            backend_options = ThreadedDoclingParseBackendOptions(
                render_pages=True,
                render_scale=_RENDER_SCALE,
                parser_threads=self._parser_threads,
                max_concurrent_results=4,
                include_bitmap_images=False,
            )
            self._converter = DocumentConverter(
                allowed_formats=[InputFormat.PDF],
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_cls=ObservedChandraPipeline,
                        pipeline_options=options,
                        backend=backend
                        if self.renderer == "docling-parse"
                        else _ReferenceRasterPdf,
                        backend_options=backend_options
                        if self.renderer == "docling-parse"
                        else None,
                    )
                },
            )
        except BaseException:
            self.runtime.close()
            raise
        return self

    def __exit__(self, *_):
        self._converter = None
        self.runtime.close()

    def convert(
        self,
        pdf: Path,
        output: Path,
        *,
        page_range: tuple[int, int] | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        """Write raw page checkpoints and the native assembled document to a new directory."""
        if self._converter is None or self._capture is not None:
            raise RuntimeError("Chandra PDF conversion requires an open, idle worker")
        started = monotonic()
        original = pdf.read_bytes()
        original_sha256 = sha256(original).hexdigest()
        selected, geometry = _source_geometry(original, page_range)
        (output / "pages").mkdir(parents=True)
        capture = _DocumentCapture(
            output, geometry, original_sha256=original_sha256, batch_size=self.batch_size
        )
        self._capture = capture
        _json(
            output / "input.json",
            {
                "original_sha256": original_sha256,
                "page_range": selected,
                "recipe": self.identity(),
            },
        )
        saved_batch_size = settings.perf.page_batch_size
        saved_profiling = settings.debug.profile_pipeline_timings
        try:
            settings.perf.page_batch_size = self.batch_size
            settings.debug.profile_pipeline_timings = True
            conversion_start = monotonic()
            result = self._converter.convert(
                DocumentStream(name=pdf.name, stream=BytesIO(original)),
                page_range=selected,
                raises_on_error=False,
                progress_callback=progress_callback,
            )
            conversion_seconds = monotonic() - conversion_start
        finally:
            settings.perf.page_batch_size = saved_batch_size
            settings.debug.profile_pipeline_timings = saved_profiling
            self._capture = None
        digest = _json(output / "document.json", result.document.export_to_dict())
        report = {
            "status": result.status.value,
            "original_sha256": original_sha256,
            "page_range": selected,
            "raw_page_nos": sorted(capture.raw),
            "typed_page_nos": sorted(capture.mapped),
            "assembled_page_nos": sorted(result.document.pages),
            "document_sha256": digest,
            "batches": capture.batches,
            "errors": [error.model_dump(mode="json") for error in result.errors],
            "recipe": self.identity(),
            "effective_device": self.runtime.effective_device,
            "prepare_seconds": self.prepare_seconds,
            "load_seconds": self.load_seconds,
            "conversion_seconds": conversion_seconds,
            "assembly_seconds": capture.assembly_seconds,
            "elapsed_seconds": monotonic() - started,
            "docling_timings": {
                name: {"count": timing.count, "seconds": sum(timing.times)}
                for name, timing in result.timings.items()
            },
        }
        _json(output / "report.json", report)
        return report
