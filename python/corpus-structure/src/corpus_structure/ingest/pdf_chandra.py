"""Pinned local Chandra inference and independent replay of its raw HTML."""

from __future__ import annotations

import multiprocessing
import os
from collections.abc import Callable
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from enum import StrEnum
from hashlib import file_digest
from html.parser import HTMLParser
from importlib.metadata import version
from importlib.util import find_spec
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any

from docling.datamodel.base_models import VlmStopReason
from docling.utils.stop_reason import normalize_stop_reason
from docling_core.types.doc import DoclingDocument, Size

if TYPE_CHECKING:
    from multiprocessing.connection import Connection

    from docling.datamodel.base_models import VlmPrediction
    from docling.models.stages.vlm_convert.vlm_convert_model import VlmConvertModel
    from PIL.Image import Image

CHANDRA_REPOSITORY = "datalab-to/chandra-ocr-2"
CHANDRA_REVISION = "af93b47dba1b47b6640c86ccf487ed2260ab9a09"
CHANDRA_PRESET = "chandra_ocr2"
_DOCLING_PACKAGES = {"docling": "2.148.0", "docling-slim": "2.148.0", "docling-core": "2.106.0"}
# The HF revision's LFS SHA-256s and SHA-256s of the verified Git blob contents.
_ARTIFACT_SHA256 = {
    "chat_template.jinja": "0d158f349ca965f7eea9db0eb45cd177b85bb0e4ae05dcdd0f060da8f7d41812",
    "config.json": "e26f17b70463de21fd68f1ef6d8f67f8e33e65d55a7a6895242130a18db60587",
    "generation_config.json": "0c35bb39fbaed1ac0656baabc4f4e9bda20214e12336d0e4e8755aac1f487c2e",
    "model.safetensors": "0804568be9f099d6479fad9ed77a4da4611f3c1e7bc6e009af7dce45e8aa3847",
    "preprocessor_config.json": "957eb01d1ea45341a92d543daec95857a7cbeff5803834bc0603b27ba7b41b3f",
    "processor_config.json": "14932921ca485d458a04dafd8069fbb0a4505622a48208d19ed247115801385b",
    "tokenizer.json": "87a7830d63fcf43bf241c3c5242e96e62dd3fdc29224ca26fed8ea333db72de4",
    "tokenizer_config.json": "316230d6a809701f4db5ea8f8fc862bc3a6f3229c937c174e674ff3ca0a64ac8",
    "video_preprocessor_config.json": (
        "de7ba2c4528aa3c92754dc61ae83f1871369cbf7ab4298dcaa99c2f5a7c80848"
    ),
}


def _verify_artifacts(root: Path) -> Path:
    model = root / CHANDRA_REPOSITORY.replace("/", "--")
    files = {path.name for path in model.iterdir()}
    missing = _ARTIFACT_SHA256.keys() - files
    if missing:
        raise FileNotFoundError(f"missing pinned Chandra artifacts: {', '.join(sorted(missing))}")
    # Transformers discovers local sidecars by name. Refuse unqualified files that could
    # shadow a verified configuration, tokenizer or weights file.
    unexpected = files - _ARTIFACT_SHA256.keys()
    if unexpected:
        raise ValueError(f"unexpected Chandra artifacts: {', '.join(sorted(unexpected))}")
    for name, digest in _ARTIFACT_SHA256.items():
        path = model / name
        if not path.is_file():
            raise FileNotFoundError(f"missing pinned Chandra artifact: {name}")
        with path.open("rb") as source:
            if file_digest(source, "sha256").hexdigest() != digest:
                raise ValueError(f"pinned Chandra artifact integrity mismatch: {name}")
    return model


def _recognition_options():
    from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
    from docling.datamodel.pipeline_options import VlmConvertOptions
    from docling.datamodel.pipeline_options_vlm_model import ResponseFormat
    from docling.datamodel.vlm_engine_options import TransformersVlmEngineOptions

    packages = {
        name: version(name)
        for name in (
            *_DOCLING_PACKAGES,
            "torch",
            "torchvision",
            "transformers",
            "accelerate",
            "tokenizers",
            "safetensors",
            "pillow",
        )
    }
    if any(packages[name] != expected for name, expected in _DOCLING_PACKAGES.items()):
        raise ValueError("the Chandra runtime requires the qualified Docling 2.148.0 family")
    if any(find_spec(name) is not None for name in ("causal_conv1d", "fla")):
        raise ValueError("Chandra requires the PyTorch reference linear attention kernels")
    accelerator = AcceleratorOptions(device=AcceleratorDevice.CUDA, cuda_use_flash_attention2=False)
    options = VlmConvertOptions.from_preset(
        CHANDRA_PRESET,
        engine_options=TransformersVlmEngineOptions(
            load_in_8bit=False,
            torch_dtype="bfloat16",
            trust_remote_code=False,
            compile_model=False,
        ),
    )
    spec = options.model_spec
    engine = options.engine_options.engine_type
    if (
        spec.get_repo_id(engine) != CHANDRA_REPOSITORY
        or spec.get_revision(engine) != CHANDRA_REVISION
        or spec.response_format != ResponseFormat.CHANDRA_HTML
    ):
        raise ValueError("Docling's Chandra preset does not match the qualified checkpoint")
    # The verified checkpoint uses built-in Qwen3.5 and Qwen3VL processor classes.
    options.model_spec = spec.model_copy(update={"trust_remote_code": False})
    return packages, accelerator, options


def _recognition_identity(packages, accelerator, options) -> dict[str, Any]:
    spec = options.model_spec
    engine = options.engine_options.engine_type
    return {
        "preset": CHANDRA_PRESET,
        "repository": CHANDRA_REPOSITORY,
        "revision": CHANDRA_REVISION,
        "artifacts_sha256": dict(_ARTIFACT_SHA256),
        "packages": dict(packages),
        "engine": options.engine_options.model_dump(mode="json"),
        "accelerator": accelerator.model_dump(mode="json"),
        "full_attention": "sdpa",
        "linear_attention": "torch_reference",
        "image_boundary": "RGB at Docling engine input",
        "prompt": spec.prompt,
        "response_format": spec.response_format.value,
        "decode": {
            "max_new_tokens": spec.max_new_tokens,
            "temperature": spec.temperature,
            "do_sample": spec.temperature > 0,
            "stop_strings": list(spec.stop_strings),
            "engine_model": spec.get_engine_config(engine).model_dump(mode="json"),
            "generation_config": spec.get_runtime_input_extra_config(engine),
        },
    }


def chandra_recognition_identity() -> dict[str, Any]:
    """Describe the pinned inference inputs without opening model artifacts."""
    return _recognition_identity(*_recognition_options())


class ChandraRuntime:
    """Prepare an offline recipe, then recognize while the caller owns the local GPU."""

    def __init__(self, artifacts: Path):
        self._packages, self._accelerator, self._options = _recognition_options()
        self._artifacts = artifacts.resolve(strict=True)
        _verify_artifacts(self._artifacts)
        self._model: VlmConvertModel | None = None
        self.effective_device: dict[str, Any] | None = None

    def identity(self) -> dict[str, Any]:
        return _recognition_identity(self._packages, self._accelerator, self._options)

    def _load_model(self) -> None:
        import torch
        from docling.models.inference_engines.vlm.transformers_engine import TransformersVlmEngine
        from docling.models.stages.vlm_convert.vlm_convert_model import VlmConvertModel

        if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported(
            including_emulation=False
        ):
            raise RuntimeError("local Chandra requires a CUDA device with native BF16 support")
        model = VlmConvertModel(
            enabled=True,
            enable_remote_services=False,
            artifacts_path=self._artifacts,
            options=self._options,
            accelerator_options=self._accelerator,
        )
        self._model = model
        engine = model.engine
        if (
            not isinstance(engine, TransformersVlmEngine)
            or engine.device != "cuda:0"
            or engine.vlm_model is None
            or engine.processor is None
            or engine.vlm_model.dtype != torch.bfloat16
            or engine.vlm_model.use_kernels
        ):
            self.close()
            raise RuntimeError("local Chandra initialized outside the qualified CUDA BF16 recipe")
        self.effective_device = {
            "device": engine.device,
            "name": torch.cuda.get_device_name(engine.device),
            "compute_capability": list(torch.cuda.get_device_capability(engine.device)),
            "torch": str(torch.__version__),
            "cuda": torch.version.cuda,
            "processor": type(engine.processor).__name__,
            "image_processor": type(engine.processor.image_processor).__name__,
        }

    def recognize(
        self, image: Image, *, before_submit: Callable[[], None] | None = None
    ) -> VlmPrediction:
        """Return the native prediction for exactly the caller's RGB submission."""
        if image.mode != "RGB" or "transparency" in image.info or min(image.size) <= 0:
            raise ValueError("local Chandra requires a nonempty, opaque RGB raster")
        if self._model is None:
            self._load_model()
        assert self._model is not None
        if before_submit is not None:
            before_submit()
        predictions = tuple(self._model.process_images([image], self._options.model_spec.prompt))
        if len(predictions) != 1:
            raise RuntimeError("Chandra prediction count does not match the single submitted image")
        return predictions[0]

    def close(self) -> None:
        """Release GPU allocations before the caller releases its GPU lease."""
        if self._model is not None:
            model, self._model = self._model, None
            model.engine.cleanup()


def _chandra_child(connection: Connection, runtime: ChandraRuntime) -> None:
    from PIL import Image

    os.dup2(2, 1)
    try:

        def submitted() -> None:
            connection.send(("submitted", runtime.effective_device))
            if connection.recv() is not True:
                raise InterruptedError("Chandra submission was not acknowledged")

        while (pixels := connection.recv()) is not None:
            try:
                with Image.open(BytesIO(pixels)) as image:
                    prediction = runtime.recognize(image, before_submit=submitted)
            except Exception as error:
                connection.send(("failed", str(error)[:1800] or type(error).__name__))
            else:
                connection.send(("prediction", prediction))
    except BrokenPipeError, EOFError:
        pass
    finally:
        try:
            runtime.close()
        finally:
            connection.close()


class ChandraWorkerLost(RuntimeError):
    """The child transport failed before it could return a prediction."""


@contextmanager
def supervised_chandra(runtime: ChandraRuntime):
    """Keep one model process for serial requests and drain it before releasing CUDA."""
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe(duplex=True)
    process = context.Process(
        target=_chandra_child, args=(child, runtime), name="chandra-pdf", daemon=True
    )
    idle = True

    def recognize(pixels, *, check_active, before_submit):
        nonlocal idle
        check_active()
        idle = False
        try:
            parent.send(pixels)
        except (OSError, EOFError) as exc:
            raise ChandraWorkerLost("Chandra child stopped accepting frames") from exc
        while True:
            check_active()
            if not parent.poll(0.2):
                if process.is_alive():
                    continue
                raise ChandraWorkerLost(f"Chandra child exited with code {process.exitcode}")
            try:
                state, payload = parent.recv()
            except (OSError, EOFError) as exc:
                raise ChandraWorkerLost("Chandra child closed its response channel") from exc
            if state == "submitted":
                runtime.effective_device = payload
                before_submit()
                try:
                    parent.send(True)
                except (OSError, EOFError) as exc:
                    raise ChandraWorkerLost("Chandra child stopped before submission") from exc
            elif state == "prediction":
                idle = True
                return payload
            elif state == "failed":
                idle = True
                raise RuntimeError(f"Chandra child failed: {payload}")
            else:
                raise ChandraWorkerLost(f"Chandra child returned an unknown message: {state}")

    try:
        process.start()
        child.close()
        yield recognize
    finally:
        try:
            if process.pid is not None:
                if idle and process.is_alive():
                    with suppress(BrokenPipeError, EOFError, OSError):
                        parent.send(None)
                    process.join(timeout=2)
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=2)
                if process.is_alive():
                    process.kill()
                    process.join(timeout=5)
                if process.is_alive():
                    raise RuntimeError(
                        f"Chandra child {process.pid} did not exit after termination"
                    )
                process.close()
        finally:
            parent.close()
            child.close()


def recognize_supervised(
    runtime: ChandraRuntime,
    pixels: bytes,
    *,
    check_active: Callable[[], None],
    before_submit: Callable[[], None],
) -> VlmPrediction:
    """Contain native inference and drain the child before the GPU lease can end."""
    check_active()
    with supervised_chandra(runtime) as recognize:
        return recognize(pixels, check_active=check_active, before_submit=before_submit)


class ChandraParseStatus(StrEnum):
    PARSED = "parsed"
    EXPLICIT_BLANK = "explicit_blank"
    MISSING_OUTPUT = "missing_output"
    MALFORMED = "malformed"
    RECOVERED = "recovered"


class ChandraCompletion(StrEnum):
    COMPLETE = "complete"
    UNKNOWN = "unknown"
    LENGTH = "length"
    FILTERED = "filtered"
    ERROR = "error"
    STOPPED = "stopped"


class ChandraParseIssue(StrEnum):
    UNSTRUCTURED_HTML = "unstructured_html"
    MALFORMED_HTML = "malformed_html"
    MISSING_GEOMETRY = "missing_geometry"
    INVALID_GEOMETRY = "invalid_geometry"
    REPETITION_SUSPECTED = "repetition_suspected"
    BLANK_MARKER_CONFLICT = "blank_marker_conflict"
    EMPTY_TABLE = "empty_table"


@dataclass(frozen=True, slots=True)
class ChandraParse:
    document: DoclingDocument | None
    status: ChandraParseStatus
    completion: ChandraCompletion
    issues: tuple[ChandraParseIssue, ...] = ()
    error: str | None = None


def chandra_parser_identity() -> dict[str, Any]:
    return {
        "parser": "docling.utils.chandra_utils.parse_chandra_html",
        "packages": {name: version(name) for name in _DOCLING_PACKAGES},
        "normalize_heading_levels": False,
        "guard": "chandra-html-evidence-v1",
    }


_COMPLETION = {
    VlmStopReason.END_OF_SEQUENCE: ChandraCompletion.COMPLETE,
    VlmStopReason.UNSPECIFIED: ChandraCompletion.UNKNOWN,
    VlmStopReason.LENGTH: ChandraCompletion.LENGTH,
    VlmStopReason.CONTENT_FILTERED: ChandraCompletion.FILTERED,
    VlmStopReason.INFERENCE_ERROR: ChandraCompletion.ERROR,
    VlmStopReason.STOP_SEQUENCE: ChandraCompletion.STOPPED,
}
_VOID_TAGS = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)
_OPTIONAL_END = frozenset({"li", "p", "td", "th", "tr", "thead", "tbody", "tfoot", "colgroup"})


class _LayoutEvidence(HTMLParser):
    """Observe omissions that Docling's intentionally tolerant mapper can recover."""

    def __init__(self, raw: str):
        super().__init__()
        self.layout_count = 0
        self.blank_count = 0
        self.table_count = 0
        self.unlabelled_text = False
        self.issues: set[ChandraParseIssue] = set()
        self._open: list[tuple[str, bool]] = []
        self.feed(raw)
        if self.rawdata.strip() or any(self._required(entry) for entry in self._open):
            self.issues.add(ChandraParseIssue.MALFORMED_HTML)
        self.close()

    @staticmethod
    def _required(entry: tuple[str, bool]) -> bool:
        tag, layout = entry
        return layout or tag not in _OPTIONAL_END

    def _observe(self, tag: str, attrs: list[tuple[str, str | None]]) -> bool:
        if tag == "table":
            self.table_count += 1
        fields = dict(attrs)
        if "data-label" not in fields and "data-bbox" not in fields:
            return False
        self.layout_count += 1
        if fields.get("data-label") == "Blank-Page":
            self.blank_count += 1
            if tag != "div":
                self.issues.add(ChandraParseIssue.BLANK_MARKER_CONFLICT)
        elif "data-bbox" not in fields:
            self.issues.add(ChandraParseIssue.MISSING_GEOMETRY)
        if "data-bbox" in fields:
            try:
                left, top, right, bottom = map(float, (fields["data-bbox"] or "").split())
                valid = 0 <= left < right <= 1000 and 0 <= top < bottom <= 1000
            except ValueError:
                valid = False
            if not valid:
                self.issues.add(ChandraParseIssue.INVALID_GEOMETRY)
        if (
            sum(name == "data-bbox" for name, _ in attrs) > 1
            or sum(name == "data-label" for name, _ in attrs) > 1
        ):
            self.issues.add(ChandraParseIssue.MALFORMED_HTML)
        return True

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        layout = self._observe(tag, attrs)
        if tag not in _VOID_TAGS:
            self._open.append((tag, layout))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._observe(tag, attrs)

    def handle_data(self, data: str) -> None:
        if data.strip() and not any(layout for _, layout in self._open):
            self.unlabelled_text = True

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self._open) - 1, -1, -1):
            if self._open[index][0] == tag:
                if any(self._required(entry) for entry in self._open[index + 1 :]):
                    self.issues.add(ChandraParseIssue.MALFORMED_HTML)
                del self._open[index:]
                return
        self.issues.add(ChandraParseIssue.MALFORMED_HTML)


def parse_chandra_response(
    raw: str,
    *,
    image_size: tuple[int, int],
    page_no: int,
    stop_reason: str | None = None,
    filename: str = "file",
) -> ChandraParse:
    """Replay already-retained HTML. Provenance is in submitted image pixels."""
    from docling.models.utils.generation_utils import find_repeated_tail
    from docling.utils.chandra_utils import parse_chandra_html

    if min(image_size) <= 0 or page_no < 1:
        raise ValueError("Chandra replay requires a nonempty image and a one-based physical page")
    completion = _COMPLETION[normalize_stop_reason(stop_reason)]
    if not raw.strip():
        return ChandraParse(None, ChandraParseStatus.MISSING_OUTPUT, completion)
    layout = _LayoutEvidence(raw)
    if not layout.layout_count:
        layout.issues.add(ChandraParseIssue.UNSTRUCTURED_HTML)
    try:
        document = parse_chandra_html(
            raw,
            Size(width=image_size[0], height=image_size[1]),
            page_no,
            filename=filename,
            normalize_heading_levels=False,
        )
    except (ValueError, RecursionError) as exc:
        return ChandraParse(
            None, ChandraParseStatus.MALFORMED, completion, tuple(sorted(layout.issues)), str(exc)
        )

    items = [*document.texts, *document.tables, *document.pictures, *document.field_regions]
    if ChandraParseIssue.INVALID_GEOMETRY in layout.issues:
        for item in items:
            # Docling already omits malformed and out-of-range boxes. Its degenerate
            # boxes have zero area and cannot locate evidence in the source frame.
            item.prov = [p for p in item.prov if p.bbox.l < p.bbox.r and p.bbox.t < p.bbox.b]
    if len(document.tables) < layout.table_count or any(
        not table.data.table_cells for table in document.tables
    ):
        layout.issues.add(ChandraParseIssue.EMPTY_TABLE)
    if any(
        find_repeated_tail(text.rstrip(), min_repeats=16, min_span=320, max_unit=64) is not None
        for text in (raw.strip(), *(item.text for item in document.texts))
    ):
        layout.issues.add(ChandraParseIssue.REPETITION_SUSPECTED)
    blank = layout.blank_count == layout.layout_count == 1 and not items
    if layout.blank_count and (not blank or layout.unlabelled_text):
        layout.issues.add(ChandraParseIssue.BLANK_MARKER_CONFLICT)
    if layout.issues:
        status = ChandraParseStatus.RECOVERED
    elif blank:
        status = ChandraParseStatus.EXPLICIT_BLANK
    else:
        status = ChandraParseStatus.PARSED
    return ChandraParse(document, status, completion, tuple(sorted(layout.issues)))
