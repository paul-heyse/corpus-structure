"""Owned finite Nemotron triple-pass recognition; publication remains in the task parent."""

from __future__ import annotations

import dataclasses
import json
import math
import os
import re
import select
import signal
import subprocess
import time
from collections.abc import Callable, Generator, Iterator, Mapping, Sequence
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from hashlib import file_digest, sha256
from io import BytesIO
from itertools import groupby
from pathlib import Path
from threading import Event, Lock, get_ident
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.core.work import PhysicalRetirementUncertain
from corpus_structure.core.process_lifetime import _live_group

from ..semantic.identity import canonical_bytes
from .pdf_capacity import pdf_gpu_slot

NEMOTRON_REVISION = "4035ffb1d8f8bafcdb867dfaf6f7514f101464f9"
NEMOTRON_PACKAGES = {
    "nemotron-parse": "3.5.0.post7",
    "vllm": "0.26.0",
    "torch": "2.11.0",
    "transformers": "5.14.1",
    "huggingface-hub": "1.24.0",
    "Pillow": "12.2.0",
}
_BLOCK = re.compile(
    r"<x_([\d.]+)><y_([\d.]+)>(.*?)<x_([\d.]+)><y_([\d.]+)><class_([^>]+)>",
    re.DOTALL,
)
_CLASS = re.compile(r"<class_[^>]+>")
# PDFium forbids overlapping C API calls even on independent document handles. The
# short render/open/close sections serialize; isolated parser/HTTP work can overlap.
_PDFIUM_LOCK = Lock()


class PdfRecognitionRecoveryPolicy(BaseModel):
    """One release-bound, narrowly eligible recovery; never an unbounded generic retry."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    policy_id: Literal["length-repetition-recovery-v1"] = "length-repetition-recovery-v1"
    eligible_finish_reason: Literal["length"] = "length"
    min_identical_character_run: int = Field(default=64, ge=64)
    max_attempts: Literal[1] = 1
    permitted_recipe_id: Literal["nemotron-public-triple-union-repetition-recovery-v1"] = (
        "nemotron-public-triple-union-repetition-recovery-v1"
    )


@dataclass(frozen=True, slots=True)
class NemotronRecipe:
    """Recognition identity excludes operational endpoint and includes result-affecting choices."""

    weights_digest: str
    tokenizer_digest: str
    identity_assurance: Literal["trusted_managed_service", "provider_reported"] = (
        "provider_reported"
    )
    source_revision: str = NEMOTRON_REVISION
    model: str = "nemotron-parse"
    render_scale: float = 2.0
    max_regions: int = 80
    max_tokens: int = 8744
    detection_max_tokens: int = 4096
    temperature: float = 0.0
    repetition_penalty: float = 1.1
    top_k: int = 1
    top_p: float = 1.0
    seed: int = 0
    mtp: bool = True
    attention_backend: str = "FLASH_ATTN"
    attention_version: int = 2
    recipe_id: str = "nemotron-public-triple-union-v1"

    def __post_init__(self) -> None:
        if self.source_revision != NEMOTRON_REVISION:
            raise ValueError("unadmitted Nemotron source revision")
        if any(
            re.fullmatch(r"[0-9a-f]{64}", value) is None
            for value in (
                self.weights_digest,
                self.tokenizer_digest,
            )
        ):
            raise ValueError("Nemotron weights/tokenizer require immutable SHA-256 pins")
        if (
            not math.isfinite(self.render_scale)
            or self.render_scale <= 0
            or self.max_regions < 1
            or self.max_tokens < 1
            or self.detection_max_tokens < 1
        ):
            raise ValueError("finite positive render/request capacity is required")

    def settings(self) -> dict[str, dict[str, Any]]:
        common = {
            k: getattr(self, k)
            for k in (
                "temperature",
                "repetition_penalty",
                "top_k",
                "top_p",
                "seed",
                "max_tokens",
            )
        }
        return {
            "fullpage": common,
            "detection": {**common, "max_tokens": self.detection_max_tokens},
            "crop": common,
        }

    def to_bytes(self) -> bytes:
        return canonical_bytes(
            {
                **dataclasses.asdict(self),
                "packages": NEMOTRON_PACKAGES,
                "settings": self.settings(),
                "mode": "triple",
                "triple_regions": "union",
                "merge_policy": "alternatives",
                "crop_margin_ratio": 0.04,
                "crop_margin_px": 12,
                "crop_jpeg_quality": 95,
                "skip_special_tokens": False,
            }
        )

    @property
    def digest(self) -> str:
        return sha256(self.to_bytes()).hexdigest()


def admit_service_generation(endpoint: str, recipe: NemotronRecipe) -> dict[str, Any] | None:
    """Admit the controlled startup manifest; every later request checks this generation."""
    if recipe.identity_assurance == "provider_reported":
        return None
    import httpx

    base = endpoint.rstrip("/").removesuffix("/v1")
    response = httpx.get(base + "/corpus/generation", timeout=10)
    response.raise_for_status()
    record = response.json()
    if (
        record.get("protocol") != "corpus-managed-recognition-1"
        or record.get("assurance") != "trusted_managed_service"
        or not isinstance(record.get("generation"), str)
        or response.headers.get("x-corpus-generation") != record["generation"]
    ):
        raise ValueError("recognition endpoint has no admitted managed generation")
    artifacts = record.get("artifacts", {})
    if (artifacts.get("model.safetensors"), artifacts.get("tokenizer.json")) != (
        recipe.weights_digest,
        recipe.tokenizer_digest,
    ):
        raise ValueError("managed recognition generation differs from configured artifacts")
    return record


@dataclass(frozen=True, slots=True)
class PreparedRecognitionSource:
    """Immutable source custody and one digest computation for all page requests."""

    original: bytes
    digest: str

    @classmethod
    def from_path(cls, path: Path, digest: str) -> PreparedRecognitionFile:
        """Verify an owned seekable original once; page workers borrow its file, not bytes."""
        path = path.resolve(strict=True)
        with path.open("rb") as source:
            if source.read(5) != b"%PDF-":
                raise ValueError("recognition source must be retained PDF bytes")
            source.seek(0)
            if file_digest(source, "sha256").hexdigest() != digest:
                raise ValueError("recognition source digest differs from owned file")
        return PreparedRecognitionFile(path, digest)

    @classmethod
    def prepare(cls, original: bytes) -> PreparedRecognitionSource:
        if not original.startswith(b"%PDF-"):
            raise ValueError("recognition source must be retained PDF bytes")
        return cls(original, sha256(original).hexdigest())


@dataclass(frozen=True, slots=True)
class PreparedRecognitionFile:
    """Verified owned file borrowed for recognition; no full original byte envelope."""

    original: Path
    digest: str


def render_affine(
    *,
    media: Sequence[float],
    crop: Sequence[float],
    rotation: int,
    width: int,
    height: int,
) -> dict[str, Any]:
    """Media-relative PDF TOPLEFT points -> rotated CropBox render pixels.

    PDF boxes use absolute BOTTOMLEFT coordinates. CropBox is intersected with MediaBox
    by the renderer; its visible top-left is expressed relative to the media origin here.
    Affine order is [a,b,c,d,e,f]: x'=a*x+c*y+e, y'=b*x+d*y+f.
    """
    ml, mb, mr, mt = media
    cl, cb, cr, ct = crop
    left, top, right, bottom = cl - ml, mt - ct, cr - ml, mt - cb
    cw, ch = right - left, bottom - top
    if rotation not in {0, 90, 180, 270} or min(cw, ch, width, height) <= 0:
        raise ValueError("invalid render crop/rotation/dimensions")
    if rotation == 0:
        sx, sy = width / cw, height / ch
        affine = [sx, 0.0, 0.0, sy, -left * sx, -top * sy]
    elif rotation == 90:
        sx, sy = width / ch, height / cw
        affine = [0.0, sy, -sx, 0.0, bottom * sx, -left * sy]
    elif rotation == 180:
        sx, sy = width / cw, height / ch
        affine = [-sx, 0.0, 0.0, -sy, right * sx, bottom * sy]
    else:
        sx, sy = width / ch, height / cw
        affine = [0.0, -sy, sx, 0.0, -top * sx, right * sy]
    return dict(
        status="coarse",
        normalization="none",
        source_space="pdf_points",
        target_space="submitted_pixels",
        page_width=mr - ml,
        page_height=mt - mb,
        page_rotation=rotation,
        crop_left=left,
        crop_top=top,
        crop_right=right,
        crop_bottom=bottom,
        affine=affine,
    )


def transform_point(affine: Sequence[float], x: float, y: float) -> tuple[float, float]:
    a, b, c, d, e, f = affine
    return a * x + c * y + e, b * x + d * y + f


def inverse_transform_point(affine: Sequence[float], x: float, y: float) -> tuple[float, float]:
    a, b, c, d, e, f = affine
    determinant = a * d - b * c
    if not determinant:
        raise ValueError("image transform is singular")
    return (d * (x - e) - c * (y - f)) / determinant, (-b * (x - e) + a * (y - f)) / determinant


def crop_transform(transform: Mapping[str, Any], pixels: Sequence[int]) -> dict[str, Any]:
    """Compose clipping in the already rotated rendered frame, preserving PDF frame custody."""
    left, top, right, bottom = pixels
    a, b, c, d, e, f = transform["affine"]
    corners = [
        inverse_transform_point(transform["affine"], x, y)
        for x, y in ((left, top), (right, top), (left, bottom), (right, bottom))
    ]
    return {
        **transform,
        "normalization": "clipped",
        "crop_left": min(p[0] for p in corners),
        "crop_top": min(p[1] for p in corners),
        "crop_right": max(p[0] for p in corners),
        "crop_bottom": max(p[1] for p in corners),
        "affine": [a, b, c, d, e - left, f - top],
    }


def render_recognition_page(
    document: Any, page_no: int, scale: float
) -> tuple[bytes, dict[str, Any]]:
    page = document[page_no - 1]
    try:
        media, crop, rotation = page.get_mediabox(), page.get_bbox(), page.get_rotation()
        bitmap = page.render(scale=scale)
        try:
            image = bitmap.to_pil().convert("RGB")
            try:
                transform = render_affine(
                    media=media,
                    crop=crop,
                    rotation=rotation,
                    width=image.width,
                    height=image.height,
                )
                stream = BytesIO()
                image.save(stream, format="PNG")
                return stream.getvalue(), transform
            finally:
                image.close()
        finally:
            bitmap.close()
    finally:
        page.close()


def terminal_recognition_result(result: Mapping[str, Any]) -> bool:
    """Historical unclassified failures are attempts; completed successes remain readable."""
    return result.get("outcome_class") == "terminal" or (
        result.get("outcome") == "succeeded" and result.get("outcome_class") != "execution"
    )


@dataclass(frozen=True, slots=True)
class RecognitionPage:
    page_no: int
    directory: Path
    result: Mapping[str, Any]
    transform: Mapping[str, Any]
    reused: bool = False

    @property
    def succeeded(self) -> bool:
        return self.result.get("outcome") == "succeeded" and self.result.get("outcome_class") != "execution"

    @property
    def terminal_outcome(self) -> bool:
        return terminal_recognition_result(self.result)

    @property
    def execution_failed(self) -> bool:
        return not self.terminal_outcome

    def requests(
        self, *, verify_retained: bool = False, expected_requests: tuple[bytes, ...] | None = None
    ) -> Iterator[tuple[dict[str, Any], bytes, tuple[bytes, ...]]]:
        """Durable rows survive worker/process loss before result.json is finalized."""
        paths = sorted(
            path
            for path in self.directory.glob("request-*.json")
            if not path.name.endswith(".http.json")
        )
        if expected_requests is not None and len(paths) != len(expected_requests):
            raise ValueError("recognition request inventory changed after report preparation")
        expected = None
        if verify_retained:
            expected = self.result.get("requests")
            if (
                not isinstance(expected, list)
                or len(expected) != len(paths)
                or len(paths) < 2
                or [row.get("ordinal") for row in expected] != list(range(len(paths)))
                or [row.get("stage") for row in expected]
                != ["fullpage", "detection", *(["crop"] * (len(paths) - 2))]
            ):
                raise ValueError("retained recognition request inventory differs from its receipt")
        root = self.directory.resolve()

        def owned(name: str) -> Path:
            path = self.directory / name
            if verify_retained and (path.name != name or path.resolve().parent != root):
                raise ValueError("retained recognition artifact escaped its attempt directory")
            return path

        for ordinal, path in enumerate(paths):
            if verify_retained:
                path = owned(path.name)
            request_content = path.read_bytes()
            if expected_requests is not None and request_content != expected_requests[ordinal]:
                raise ValueError("recognition request changed after report preparation")
            row = json.loads(request_content)
            if expected is not None and (
                row != expected[ordinal]
                or row.get("outcome") != "succeeded"
                or path.name != f"request-{ordinal:03d}.json"
            ):
                raise ValueError("retained recognition request differs from its completed attempt")
            raw = owned(row["raw_response"]).read_bytes() if "raw_response" in row else b""
            artifacts = [owned(row["submitted_image"]).read_bytes()]
            if "raw_response" in row:
                artifacts.append(raw)
            if "http_response" in row:
                artifacts.append(owned(row["http_response"]).read_bytes())
            if row.get("crop", {}).get("jpeg_path") if row.get("crop") else False:
                artifacts.append(owned(row["crop"]["jpeg_path"]).read_bytes())
            if verify_retained:
                if (
                    sha256(raw).hexdigest() != row.get("raw_digest")
                    or sha256(artifacts[0]).hexdigest() != row.get("submitted_digest")
                    or len(artifacts) < 3
                ):
                    raise ValueError("retained recognition raw or submitted bytes differ")
                choice = json.loads(artifacts[2])["choices"][0]
                if choice["message"]["content"].encode() != raw or choice[
                    "finish_reason"
                ] != row.get("finish_reason"):
                    raise ValueError("retained recognition response differs from its raw reading")
                if row["stage"] == "crop":
                    crop = row.get("crop")
                    if (
                        not isinstance(crop, dict)
                        or crop not in self.result["decisions"]
                        or len(artifacts) != 4
                        or sha256(artifacts[3]).hexdigest() != crop["jpeg_digest"]
                    ):
                        raise ValueError(
                            "retained recognition crop differs from its recorded decision"
                        )
                elif artifacts[0] != owned("page.png").read_bytes():
                    raise ValueError(
                        "retained recognition full-page request differs from its frame"
                    )
            # The request metadata contains the upstream crop witness even on later failure.
            # The first observation also protects page selection/omission and final status.
            names = [path.name]
            if row["ordinal"] == 0:
                names.extend(
                    (
                        "input.json",
                        "decisions.json",
                        "result.json",
                        "provider-document.json",
                        "interrupted.json",
                    )
                )
            context = {}
            for name in names:
                retained = owned(name)
                if retained.exists():
                    payload = request_content if name == path.name else retained.read_bytes()
                    context[name] = sha256(payload).hexdigest()
                    artifacts.append(payload)
            row["receipt_digests"] = context
            yield row, raw, tuple(artifacts)


class _RecognitionSlot:
    """One serial pipe borrower; process-group death precedes slot release or restart."""

    def __init__(self, owner: RecognitionWorker) -> None:
        self.owner = owner
        self.process: subprocess.Popen[bytes] | None = None
        self.lock = Lock()

    def _close(self, *, graceful: bool = False) -> None:
        process = self.process
        if process is None:
            return
        if graceful and process.stdin is not None:
            process.stdin.close()
            deadline = time.monotonic() + 2
            while _live_group(process.pid) and time.monotonic() < deadline:
                process.poll()
                time.sleep(0.025)
        for sig, seconds in ((signal.SIGTERM, 2), (signal.SIGKILL, 5)):
            if not _live_group(process.pid):
                break
            try:
                os.killpg(process.pid, sig)
            except ProcessLookupError:
                pass
            deadline = time.monotonic() + seconds
            while _live_group(process.pid) and time.monotonic() < deadline:
                process.poll()
                time.sleep(0.025)
        if _live_group(process.pid):
            raise PhysicalRetirementUncertain(f"recognition process group {process.pid} death remains unproven")
        process.wait(timeout=1)
        for stream in (process.stdin, process.stdout):
            if stream is not None:
                stream.close()
        self.process = None

    def close(self) -> None:
        with self.lock:
            self._close(graceful=True)

    def execute(self, input_path: Path, check_active: Callable[[], None]) -> Mapping[str, Any]:
        with self.lock:
            try:
                check_active()
                if self.process is None:
                    with (input_path.parent / "worker.log").open("ab") as log:
                        self.process = subprocess.Popen(
                            [str(self.owner.python), str(self.owner.script), "--serve"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=log,
                            start_new_session=True, bufsize=0,
                        )
                process = self.process
                assert process.stdin is not None and process.stdout is not None
                process.stdin.write(canonical_bytes({"request": str(input_path.absolute())}) + b"\n")
                process.stdin.flush()
                while True:
                    check_active()
                    readable, _, _ = select.select([process.stdout], [], [], 0.2)
                    if not readable:
                        if process.poll() is not None:
                            raise EOFError(f"recognition worker exited {process.returncode}")
                        continue
                    line = process.stdout.readline(64 * 1024)
                    if not line:
                        raise EOFError(f"recognition worker exited {process.poll()}")
                    reply = json.loads(line)
                    if reply.get("request") != str(input_path.absolute()):
                        raise ValueError("recognition slot replied for another page job")
                    path = input_path.parent / "result.json"
                    if not path.exists():
                        raise ValueError("recognition slot returned without its durable result")
                    result = json.loads(path.read_bytes())
                    if reply.get("fatal"):
                        self._close()
                    return result
            except BaseException as error:
                try:
                    self._close()
                except BaseException as cleanup:
                    raise PhysicalRetirementUncertain("recognition slot retirement failed") from BaseExceptionGroup(
                        "recognition page and retirement failed", [error, cleanup]
                    )
                if not isinstance(error, Exception) or isinstance(error, InterruptedError):
                    raise
                result = {"outcome": "failed", "outcome_class": "execution",
                          "diagnostic": f"{type(error).__name__}: {error}"}
                (input_path.parent / "result.json").write_bytes(canonical_bytes(result))
                return result


@dataclass
class _RecognitionOperation:
    source: PreparedRecognitionSource | PreparedRecognitionFile
    recipe: NemotronRecipe
    document: Any
    page_count: int
    concurrency: int
    owner_thread: int = field(default_factory=get_ident)
    cancelled: Event = field(default_factory=Event)
    binding_lock: Lock = field(default_factory=Lock)
    admitted: bool = False
    service_binding: dict[str, Any] | None = None
    available_slot: _RecognitionSlot | None = None

    def active(self) -> None:
        if self.cancelled.is_set():
            raise InterruptedError("owning recognition operation cancelled")


class RecognitionWorker:
    """An operation opens one PDF and owns bounded reusable page-process slots."""

    def __init__(self, *, python: Path, script: Path, endpoint: str, receipts: Path,
                 timeout_seconds: float = 1800.0) -> None:
        self.python, self.script = python, script
        self.endpoint, self.receipts, self.timeout_seconds = endpoint, receipts, timeout_seconds
        self.last_page: RecognitionPage | None = None
        self._operation: _RecognitionOperation | None = None

    def recognize_pages(
        self, source: PreparedRecognitionSource | PreparedRecognitionFile,
        recipe: NemotronRecipe, page_numbers: Sequence[int], *,
        check_active: Callable[[], None] | None = None,
        reuse: bool = True, concurrency: int = 1,
    ) -> Generator[RecognitionPage]:
        operation = self._operation
        if operation is not None:
            # Bounded repetition recovery borrows the completed slot while the
            # outer iterator is paused. It opens no second PDF or GPU lease.
            if get_ident() != operation.owner_thread or source is not operation.source or concurrency != 1 or len(page_numbers) != 1 or operation.available_slot is None:
                raise ValueError("nested recognition requires the operation's one completed page slot")
            if check_active is not None:
                check_active()
            page = self._execute_page(operation, operation.available_slot, recipe,
                                      page_numbers[0], reuse, check_active or operation.active)
            self._readmit_generation(operation, page)
            self.last_page = page
            yield page
            return
        with pdf_gpu_slot(check_active):
            yield from self._recognize_pages(source, recipe, page_numbers,
                                            check_active=check_active, reuse=reuse,
                                            concurrency=concurrency)

    def _execute_page(
        self, operation: _RecognitionOperation, slot: _RecognitionSlot,
        recipe: NemotronRecipe, page_no: int, reuse: bool, check_active: Callable[[], None],
    ) -> RecognitionPage:
        check_active()
        if type(page_no) is not int or not 1 <= page_no <= operation.page_count:
            raise ValueError("recognition page outside retained source")
        parent = self.receipts / operation.source.digest / recipe.digest / f"page-{page_no:05d}"
        parent.mkdir(parents=True, exist_ok=True)
        if reuse:
            for path in sorted(parent.glob("attempt-*/result.json"), reverse=True):
                result = json.loads(path.read_bytes())
                if terminal_recognition_result(result):
                    submitted = json.loads((path.parent / "input.json").read_bytes())
                    if submitted.get("source_digest") != operation.source.digest or submitted.get("recipe_digest") != recipe.digest:
                        raise ValueError("retained recognition page has different source/recipe premises")
                    return RecognitionPage(page_no, path.parent, result, submitted["transform"], True)
        directory = parent / f"attempt-{len(list(parent.glob('attempt-*'))) + 1:05d}"
        directory.mkdir()
        try:
            with _PDFIUM_LOCK:
                image, transform = render_recognition_page(operation.document, page_no, recipe.render_scale)
            image_path = directory / "page.png"
            image_path.write_bytes(image)
            with operation.binding_lock:
                if (recipe.weights_digest, recipe.tokenizer_digest, recipe.identity_assurance) != (
                    operation.recipe.weights_digest, operation.recipe.tokenizer_digest,
                    operation.recipe.identity_assurance,
                ):
                    raise ValueError("recognition slot recipe changes admitted provider artifacts")
                if not operation.admitted:
                    operation.service_binding = admit_service_generation(self.endpoint, recipe)
                    operation.admitted = True
                service_binding = operation.service_binding
            request = dict(
                image_path=str(image_path.absolute()), endpoint=self.endpoint,
                service_binding=service_binding, identity_assurance=recipe.identity_assurance,
                model=recipe.model, timeout_seconds=self.timeout_seconds, packages=NEMOTRON_PACKAGES,
                settings=recipe.settings(), max_regions=recipe.max_regions, transform=transform,
                recipe_digest=recipe.digest, source_digest=operation.source.digest,
                physical_page_concurrency=operation.concurrency,
            )
            input_path = directory / "input.json"
            input_path.write_bytes(canonical_bytes(request))
            result = slot.execute(input_path, check_active)
            return RecognitionPage(page_no, directory, result, transform)
        except BaseException as error:
            result = {"outcome": "failed", "outcome_class": "execution",
                      "diagnostic": f"{type(error).__name__}: {error}"}
            interrupted = not isinstance(error, Exception) or isinstance(error, (InterruptedError, PhysicalRetirementUncertain))
            (directory / ("interrupted.json" if interrupted else "result.json")).write_bytes(canonical_bytes(result))
            self.last_page = RecognitionPage(page_no, directory, result, locals().get("transform", {}))
            if interrupted:
                raise
            return self.last_page

    def _readmit_generation(self, operation: _RecognitionOperation, page: RecognitionPage) -> None:
        if page.reused:
            return
        with operation.binding_lock:
            binding = operation.service_binding
            if binding is None:
                return
            reported = {
                row.get("response_generation") for row in page.result.get("requests", ())
                if row.get("outcome_class") == "execution"
                and row.get("response_generation") != row.get("service_generation")
            }
            if any(generation is not None and generation != binding["generation"] for generation in reported):
                try:
                    operation.service_binding = admit_service_generation(self.endpoint, operation.recipe)
                except Exception as error:
                    # No response under the new generation becomes terminal
                    # without admission. Keep its physical failure and complete
                    # other pages under the last admitted request fence.
                    (page.directory / "readmission.json").write_bytes(canonical_bytes({
                        "outcome_class": "execution", "diagnostic": f"{type(error).__name__}: {error}",
                    }))

    def _recognize_pages(
        self, source: PreparedRecognitionSource | PreparedRecognitionFile,
        recipe: NemotronRecipe, page_numbers: Sequence[int], *,
        check_active: Callable[[], None] | None, reuse: bool, concurrency: int,
    ) -> Generator[RecognitionPage]:
        import pypdfium2

        if not 1 <= concurrency <= 4 or len(set(page_numbers)) != len(page_numbers):
            raise ValueError("recognition requires distinct pages and concurrency between one and four")
        with _PDFIUM_LOCK:
            document = pypdfium2.PdfDocument(str(source.original) if isinstance(source.original, Path) else source.original)
            try:
                page_count = len(document)
            except BaseException:
                document.close()
                raise
        operation = _RecognitionOperation(source, recipe, document, page_count, concurrency)
        self._operation = operation
        slots = [_RecognitionSlot(self) for _ in range(concurrency)]
        pages = iter(page_numbers)
        pending: dict[Future[RecognitionPage], _RecognitionSlot] = {}
        primary = None
        try:
            with ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="pdf-recognition") as pool:
                def schedule(slot):
                    page_no = next(pages, None)
                    if page_no is not None:
                        pending[pool.submit(self._execute_page, operation, slot, recipe, page_no,
                                            reuse, operation.active)] = slot
                try:
                    for slot in slots:
                        schedule(slot)
                    while pending:
                        if check_active is not None:
                            check_active()
                        ready, _ = wait(pending, timeout=0.2, return_when=FIRST_COMPLETED)
                        if not ready:
                            continue
                        completed = next(iter(ready))
                        slot = pending.pop(completed)
                        page = completed.result()
                        self._readmit_generation(operation, page)
                        self.last_page = page
                        operation.available_slot = slot
                        yield page
                        operation.available_slot = None
                        if check_active is not None:
                            check_active()
                        schedule(slot)
                finally:
                    operation.cancelled.set()
                    for future in pending:
                        future.cancel()
        except BaseException as error:
            primary = error
            raise
        finally:
            errors = []
            for slot in slots:
                try:
                    slot.close()
                except BaseException as error:
                    errors.append(error)
            if errors:
                groups = [slot.process.pid for slot in slots if slot.process is not None]
                raise PhysicalRetirementUncertain(f"recognition operation retains unretired process groups {groups}") from BaseExceptionGroup(
                    "recognition retirement failed", ([primary] if primary is not None else []) + errors
                )
            with _PDFIUM_LOCK:
                document.close()
            self._operation = None

    def replay_completed_pages(
        self,
        source: PreparedRecognitionSource,
        recipe: NemotronRecipe,
        page_numbers: Sequence[int],
        *,
        check_active: Callable[[], None],
    ) -> Generator[RecognitionPage]:
        """Verify exact complete retained frames without contacting the provider or GPU lease."""
        import pypdfium2

        if len(set(page_numbers)) != len(page_numbers):
            raise ValueError("retained recognition pages must have distinct physical identities")
        root = (self.receipts / source.digest / recipe.digest).resolve()
        with _PDFIUM_LOCK:
            document = pypdfium2.PdfDocument(source.original)
        try:
            for page_no in page_numbers:
                check_active()
                with _PDFIUM_LOCK:
                    if not 1 <= page_no <= len(document):
                        raise ValueError("retained recognition page is outside the source")
                    image, transform = render_recognition_page(
                        document, page_no, recipe.render_scale
                    )
                parent = root / f"page-{page_no:05d}"
                for receipt in sorted(parent.glob("attempt-*/result.json"), reverse=True):
                    attempt = receipt.parent
                    if (
                        not re.fullmatch(r"attempt-\d{5,}", attempt.name)
                        or attempt.resolve().parent != parent
                        or receipt.resolve().parent != attempt.resolve()
                    ):
                        raise ValueError("retained recognition attempt escaped its exact scope")
                    result = json.loads(receipt.read_bytes())
                    if result.get("outcome") != "succeeded":
                        continue
                    input_path, frame_path = attempt / "input.json", attempt / "page.png"
                    if any(
                        path.resolve().parent != attempt.resolve()
                        for path in (input_path, frame_path)
                    ):
                        raise ValueError("retained recognition input or frame escaped its attempt")
                    submitted = json.loads(input_path.read_bytes())
                    if (
                        submitted.get("source_digest") != source.digest
                        or submitted.get("recipe_digest") != recipe.digest
                        or submitted.get("transform") != transform
                        or frame_path.read_bytes() != image
                    ):
                        raise ValueError(
                            f"retained recognition page {page_no} frame or binding differs"
                        )
                    yield RecognitionPage(page_no, attempt, result, transform, reused=True)
                    break
                else:
                    raise ValueError(f"retained recognition page {page_no} has no complete attempt")
        finally:
            with _PDFIUM_LOCK:
                document.close()


def repetitive_capped_page(page: RecognitionPage, *, minimum_run: int) -> bool:
    """Observed cap plus a declared repeated-character run, never an inferred success."""
    if page.succeeded or page.execution_failed:
        return False
    for row, raw, _ in page.requests():
        if row.get("finish_reason") != "length":
            continue
        if any(sum(1 for _ in run) >= minimum_run for _, run in groupby(raw.decode("utf-8"))):
            return True
    return False


def repetition_recovery_recipe(recipe: NemotronRecipe) -> NemotronRecipe:
    return dataclasses.replace(
        recipe,
        repetition_penalty=1.3,
        recipe_id="nemotron-public-triple-union-repetition-recovery-v1",
    )


def recognition_observation_values(
    page: RecognitionPage,
    row: Mapping[str, Any],
    raw: bytes,
    *,
    source: PreparedRecognitionSource | PreparedRecognitionFile,
    recipe: NemotronRecipe,
) -> dict[str, Any]:
    """Build PDF-13 primitives; parent admits/publishes with its archived task context."""
    if page.execution_failed:
        raise RuntimeError("recognition execution failure cannot become an operation result")
    stage = row["stage"]
    transform = dict(page.transform)
    if row.get("crop") is not None:
        transform = crop_transform(transform, row["crop"]["pixels"])
    outcome = row.get("outcome", "failed")
    observation: dict[str, Any] = dict(
        pass_role={"fullpage": "A", "detection": "B", "crop": "C"}[stage],
        outcome=outcome,
        usage_availability="available" if row.get("usage") is not None else "unavailable",
        image=dict(
            artifact_digest=row["submitted_digest"],
            page_no=page.page_no,
            width=row["width"],
            height=row["height"],
            encoding="png",
            transform=transform,
            precision="coarse",
        ),
        binding=dict(
            provider="nvidia-public-document-parser",
            package_identity="nemotron-parse==3.5.0.post7;vllm==0.26.0",
            source_identity="nvidia/Nemotron-3.5-Parse@" + recipe.source_revision,
            weights_digest=recipe.weights_digest,
            tokenizer_digest=recipe.tokenizer_digest,
            prompt_digest=sha256(row["prompt"].encode()).hexdigest(),
            decoding_json=canonical_bytes(
                {
                    **row["settings"],
                    "skip_special_tokens": False,
                    "requested_model": recipe.model,
                    "response_model": row.get("response_model"),
                    "identity_assurance": row.get("identity_assurance", "provider_reported"),
                    "service_generation": row.get("service_generation"),
                    "outcome_class": row.get("outcome_class", "terminal" if outcome == "succeeded" else "execution"),
                    "configured_weights_digest": recipe.weights_digest,
                    "configured_tokenizer_digest": recipe.tokenizer_digest,
                    "mtp": recipe.mtp,
                    "attention_backend": recipe.attention_backend,
                    "attention_version": recipe.attention_version,
                    "recipe_id": recipe.recipe_id,
                    "receipt_digests": row.get("receipt_digests", {}),
                }
            ).decode(),
            seed=str(recipe.seed),
            render_policy=f"pdfium-5.14.0-cropbox-media-top-left-rotate-scale-{recipe.render_scale}",
            crop_policy="public-union-margin12px-0.04-jpeg95-then-png-v1",
            merge_policy="alternatives",
        ),
    )
    if "raw_response" in row:
        observation["raw_response_digest"] = sha256(raw).hexdigest()
    if row.get("finish_reason") is not None:
        observation["finish_reason"] = row["finish_reason"]
    if row.get("usage") is not None:
        observation["usage_json"] = canonical_bytes(row["usage"]).decode()
    if outcome != "succeeded":
        observation["diagnostic"] = row.get("diagnostic") or "incomplete or capped generation"
    text = raw.decode("utf-8")
    occurrences = []
    # IDs follow every raw class terminator, including malformed blocks, not deduplicated text.
    matched = {match.end(): match for match in _BLOCK.finditer(text)}
    for ordinal, terminator in enumerate(_CLASS.finditer(text)):
        match = matched.get(terminator.end())
        occurrence: dict[str, Any] = dict(
            occurrence_id=f"block-{ordinal}",
            kind="region",
            address_space="raw_response",
            precision="unknown",
            page_no=page.page_no,
        )
        if match is not None:
            occurrence.update(text=match[3], precision="coarse")
        occurrences.append(occurrence)
    key = (
        f"nemotron:{source.digest}:{recipe.digest}:page:{page.page_no}"
        f":{page.directory.name}:request:{row['ordinal']}"
    )
    return dict(
        version=1,
        kind="recognition_observation",
        product_key=key,
        artifact_digest=source.digest,
        recipe_digest=recipe.digest,
        observation=observation,
        inputs=[],
        occurrences=occurrences,
        relations=[],
        health=dict(
            execution_outcome=outcome,
            mapping_outcome="unknown",
            source_fidelity="unassessed",
            validation_report=(
                "Actual request retained; source fidelity and provider mapping assessed separately."
            ),
        ),
        coverage=[
            dict(
                coverage_id="request-output",
                scope=f"page:{page.page_no}",
                family=f"nemotron-pass-{observation['pass_role']}",
                discovery_policy="public-triple-union-v1",
                outcome=(
                    "unknown"
                    if "raw_response" not in row
                    else "capped"
                    if row.get("finish_reason") == "length"
                    else "partial"
                ),
                detail=("Request output only; completion does not establish source completeness."),
                supports=[],
            )
        ],
    )


def main() -> None:
    """Finite disk-backed recognition entry point; no database or publication authority."""
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--receipts", required=True, type=Path)
    parser.add_argument("--python", required=True, type=Path)
    parser.add_argument("--worker", required=True, type=Path)
    parser.add_argument("--endpoint", default="http://127.0.0.1:8035/v1")
    parser.add_argument("--concurrency", type=int, choices=range(1, 5), default=1)
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="retain failed pages, finish the finite selection, then exit nonzero",
    )
    parser.add_argument("--pages", required=True, help="inclusive range, e.g. 1-1589 or 85")
    args = parser.parse_args()
    bounds = tuple(int(x) for x in args.pages.split("-"))
    if len(bounds) not in {1, 2} or bounds[0] < 1 or bounds[-1] < bounds[0]:
        parser.error("pages must be one positive page or an ascending inclusive range")
    manifest = json.loads(args.manifest.read_bytes())
    recipe = NemotronRecipe(
        manifest["artifacts"]["model.safetensors"], manifest["artifacts"]["tokenizer.json"]
    )
    source = PreparedRecognitionSource.prepare(args.source.read_bytes())
    worker = RecognitionWorker(
        python=args.python, script=args.worker, endpoint=args.endpoint, receipts=args.receipts
    )
    failures = []
    for page in worker.recognize_pages(
        source, recipe, range(bounds[0], bounds[-1] + 1), concurrency=args.concurrency
    ):
        for row, raw, _ in page.requests():
            values = recognition_observation_values(page, row, raw, source=source, recipe=recipe)
            (page.directory / f"observation-{row['ordinal']:03d}.json").write_bytes(
                canonical_bytes(values)
            )
        print(
            json.dumps(
                {
                    "page": page.page_no,
                    "directory": str(page.directory),
                    "outcome": page.result.get("outcome"),
                    "reused": page.reused,
                    "diagnostic": page.result.get("diagnostic"),
                }
            ),
            flush=True,
        )
        if not page.succeeded:
            failures.append(page.page_no)
            if not args.continue_on_error:
                raise RuntimeError(f"page {page.page_no} failed; retained at {page.directory}")
    if failures:
        raise RuntimeError(
            f"recognition selection completed with failed physical pages: {failures}"
        )


if __name__ == "__main__":
    main()
