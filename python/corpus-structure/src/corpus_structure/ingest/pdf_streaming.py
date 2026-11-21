"""Pinned page-spool adapter with explicit native global finalization.

Heavy page state is released after atomic spool custody. Native reading-order and heading
algorithms still materialize the document graph. This is not strict end-to-end streaming.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, replace
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from typing import Any, Protocol

from corpus_structure.semantic.pdf_lowering_context import CapturedPdfLowering

from .pdf_stream_types import (
    PdfPageRecovery,
    PdfReplayRef,
    PdfSourceRef,
    PdfStreamReply,
    PdfStreamRequest,
)


def _ref(path: Path, family: str, rows: int = 0) -> PdfReplayRef:
    return PdfReplayRef.from_path(path, family, rows)


def _atomic_bytes(path: Path, value: bytes, family: str) -> PdfReplayRef:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("xb") as sink:
        sink.write(value)
        sink.flush()
        os.fsync(sink.fileno())
    temporary.replace(path)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return _ref(path, family)


@lru_cache(maxsize=1)
def _page_envelope_model():
    """Prepare once; nested Page/BoundingBox serializers remain their native owners."""
    from docling.datamodel.base_models import ErrorItem, Page, PageConfidenceScores
    from docling_core.types.doc import BoundingBox
    from pydantic import ConfigDict, create_model

    return create_model(
        "NativePageReplayEnvelope",
        __config__=ConfigDict(extra="forbid"),
        assembly_types=(dict[str, list[str]], ...),
        confidence=(PageConfidenceScores | None, ...),
        errors=(list[ErrorItem], ...),
        page=(Page, ...),
        shape_lines=(list[BoundingBox], ...),
        shape_boxes=(list[BoundingBox], ...),
        raster=(dict[str, Any], ...),
        scale=(float, ...),
        crop_profile=(str, ...),
        serialization_profile=(str, ...),
    )


class PdfStreamSpool:
    """One caller-owned spool; files survive failures until explicit authenticated cleanup."""

    def __init__(
        self,
        root: Path,
        *,
        on_page: Callable[[PdfReplayRef], None] | None = None,
        check_active: Callable[[], None] | None = None,
        payload_family: Any = None,
        recovery_pages: tuple[PdfPageRecovery, ...] = (),
    ):
        root.mkdir(parents=True, exist_ok=False)
        self.root = root
        self.on_page, self.check_active = on_page, check_active
        self.pages: dict[int, PdfReplayRef] = {}
        self.candidates: dict[int, PdfReplayRef] = {}
        self._payload_family = payload_family
        self.restored_pages: set[int] = set()
        self.preparation_identities = set()
        for recovery in recovery_pages:
            if recovery.page_no in self.restored_pages:
                raise ValueError("PDF recovery repeated a physical page")
            recovery.page.verify()
            recovery.candidate.verify()
            self.pages[recovery.page_no] = recovery.page
            self.candidates[recovery.page_no] = recovery.candidate
            self.restored_pages.add(recovery.page_no)
            self.preparation_identities.add(recovery.preparation_identity)
        if len(self.preparation_identities) > 1:
            raise ValueError("PDF recovery combines different native preparations")

    @property
    def payload_family(self):
        if self._payload_family is None:
            from corpus_structure.semantic.pdf_payloads import prepare_payload_family

            self._payload_family = prepare_payload_family()
        return self._payload_family

    @property
    def candidate_source(self):
        from .pdf_candidate_source import ReplayCandidatePageSource

        return ReplayCandidatePageSource(self.candidates, self.payload_family)

    def active(self) -> None:
        if self.check_active:
            self.check_active()

    def capture_candidates(self, value: Any) -> None:
        self.active()
        if value.page_no in self.candidates:
            raise ValueError("candidate page was spooled twice")
        from dataclasses import replace

        family = self.payload_family
        logical = value.to_wire()
        content = family.encode(logical)
        replay = _atomic_bytes(
            self.root / f"candidate-{value.page_no:06}.arrow", content, "candidate_payload"
        )
        replay = replace(
            replay,
            rows=1,
            schema_digest=family.schema_digest,
            logical_digest=family.logical_digest(logical),
            page_no=value.page_no,
        )
        # The same encoded bytes and source-qualified locator cross the ACK boundary.
        if self.on_page:
            self.on_page(replay)
        self.candidates[value.page_no] = replay

    def capture_page(
        self, page: Any, hierarchy: Any, scale: float, *, confidence: Any, errors: Sequence[Any]
    ) -> None:
        self.active()
        if page.assembled is None:
            return
        if page.page_no in self.pages:
            raise ValueError("page was spooled twice")
        # Detached native raster is an explicit crop recipe, not the PDFium renderer.
        image = page.get_image(scale=scale)
        if image is None:
            raise ValueError("required native replay raster unavailable")
        image_path = self.root / f"raster-{page.page_no:06}.png"
        temporary = image_path.with_suffix(".tmp")
        with temporary.open("xb") as sink:
            image.save(sink, format="PNG")
            sink.flush()
            os.fsync(sink.fileno())
        temporary.replace(image_path)
        raster = _ref(image_path, "native-raster")
        page.parsed_page = hierarchy.retain_parsed_lines(page)
        from .pdf_assembly import assembly_types

        envelope = _page_envelope_model().model_construct(
            assembly_types=assembly_types(page.assembled),
            confidence=confidence,
            errors=list(errors),
            page=page,
            shape_lines=list(page._shape_lines or ()),
            shape_boxes=list(page._shape_bounding_boxes or ()),
            raster={
                "path": str(raster.path),
                "digest": raster.digest,
                "byte_length": raster.byte_length,
            },
            scale=scale,
            crop_profile="docling-native-full-raster-crop-v1",
            serialization_profile="pydantic-native-page-envelope-v2",
        )
        replay = _atomic_bytes(
            self.root / f"page-{page.page_no:06}.json",
            envelope.model_dump_json().encode(),
            "page",
        )
        replay = replace(replay, page_no=page.page_no)
        if self.on_page:
            self.on_page(replay)  # Failure must prevent successful release/admission.
        self.pages[page.page_no] = replay
        # unload() in the pinned threaded backend is a no-op: actually drop references.
        from docling.datamodel.base_models import PagePredictions

        page._backend = None
        page._image_cache = {}
        page.parsed_page = None
        page.assembled = None
        page.predictions = PagePredictions()
        page._shape_lines = None
        page._shape_bounding_boxes = None

    def restore_pages(self, conv_res: Any, expected_pages: Sequence[int] | None = None) -> None:
        from docling.datamodel.base_models import ErrorItem, Page, PageConfidenceScores
        from docling_core.types.doc import BoundingBox
        from PIL import Image
        from pydantic import PrivateAttr

        class ReplayPage(Page):
            _raster: PdfReplayRef | None = PrivateAttr(default=None)
            _scale: float = PrivateAttr(default=1.0)

            def get_image(
                self,
                scale: float = 1.0,
                max_size: int | None = None,
                cropbox: BoundingBox | None = None,
            ) -> Image.Image | None:
                if self._raster is None:
                    return None
                if max_size is not None:
                    assert self.size is not None
                    scale = min(scale, max_size / max(self.size.as_tuple()))
                if scale != self._scale:
                    raise ValueError(
                        f"unrecorded native raster scale requested: page={self.page_no}, "
                        f"requested={scale}, retained={self._scale}"
                    )
                with Image.open(self._raster.path) as original:
                    if cropbox is None:
                        return original.copy()
                    assert self.size is not None
                    return original.crop(
                        cropbox.to_top_left_origin(page_height=self.size.height)
                        .scaled(scale=scale)
                        .as_tuple()
                    )

        restored = []
        current = {page.page_no: page for page in conv_res.pages}
        expected = list(expected_pages) if expected_pages is not None else sorted(current)
        if not self.restored_pages <= set(expected):
            raise ValueError("PDF recovery contains pages outside the native selection")
        for number in expected:
            self.active()
            replay = self.pages.get(number)
            if replay is None:
                if number in current:
                    restored.append(current[number])
                continue
            replay.verify()
            data = json.loads(replay.path.read_bytes())
            from .pdf_assembly import restore_assembly

            raw_page = dict(data["page"])
            raw_page["assembled"] = restore_assembly(raw_page["assembled"], data["assembly_types"])
            page = ReplayPage.model_validate(raw_page)
            page._shape_lines = [BoundingBox.model_validate(box) for box in data["shape_lines"]]
            page._shape_bounding_boxes = [
                BoundingBox.model_validate(box) for box in data["shape_boxes"]
            ]
            raster = data["raster"]
            page._raster = PdfReplayRef(
                Path(raster["path"]), raster["digest"], raster["byte_length"], "native-raster"
            )
            page._raster.verify()
            page._scale = data["scale"]
            if data["confidence"] is not None:
                conv_res.confidence.pages[number] = PageConfidenceScores.model_validate(
                    data["confidence"]
                )
            if number in self.restored_pages:
                conv_res.errors.extend(ErrorItem.model_validate(error) for error in data["errors"])
            if page.size is not None:
                conv_res._page_sizes_by_no[number] = page.size
            restored.append(page)
        conv_res.pages = restored  # Native finalization explicitly consumes global state.

    def iter_candidates(self):
        yield from self.candidate_source.iter_pages()


class _JsonList(list):
    def __init__(self, value: Any, computed: bool = False):
        self.value = value
        self.computed = computed

    def __len__(self):
        return len(self.value)

    def __iter__(self):
        return (_json_view(item, self.computed) for item in self.value)

    def __getitem__(self, index):
        return _json_view(self.value[index], self.computed)


class _JsonDict(dict):
    def __init__(self, value: Mapping, computed: bool = False):
        self.value = value
        self.computed = computed
        self.keys_by_text = {str(key): key for key in value}
        super().__init__((str(key), None) for key in value)

    def __getitem__(self, key):
        original = self.keys_by_text[key]
        return _json_view(self.value[original], self.computed)

    def items(self):
        return {key: self[key] for key in self}.items()

    def values(self):
        return {key: self[key] for key in self}.values()

    def get(self, key, default=None):
        try:
            original = self.keys_by_text[key]
        except KeyError:
            return default
        return _json_view(self.value[original], self.computed)


def _json_view(value: Any, computed: bool = False) -> Any:
    from pydantic import BaseModel

    if isinstance(value, BaseModel):
        all_fields = {
            **type(value).model_fields,
            **(type(value).model_computed_fields if computed else {}),
        }
        all_fields = {
            name: field
            for name, field in all_fields.items()
            if not getattr(field, "exclude", False)
        }
        values = {}
        for name in all_fields:
            if name in value.__dict__:
                values[name] = value.__dict__[name]
            else:
                descriptor = type(value).model_computed_fields[name].wrapped_property
                values[name] = descriptor.__get__(value, type(value))
        nested = tuple(
            name for name, child in values.items() if isinstance(child, (BaseModel, list, dict))
        )
        scalars = value.model_dump(
            mode="json",
            by_alias=True,
            exclude_none=True,
            exclude=set(nested),
            exclude_computed_fields=not computed,
        )
        members: dict[str, Any] = dict(scalars)
        for name in nested:
            field = all_fields[name]
            child = values[name]
            if (
                getattr(field, "exclude", False)
                or child is None
                or (getattr(field, "exclude_if", None) and field.exclude_if(child))
            ):
                continue
            # Docling's wrap serializer omits these two empty native collections.
            if not child and not value.model_dump(
                mode="json", by_alias=True, exclude_none=True, include={name}
            ):
                continue
            members[getattr(field, "serialization_alias", None) or field.alias or name] = child
        return _JsonDict(members, computed)
    if isinstance(value, dict):
        return _JsonDict(value, computed)
    if isinstance(value, list):
        return _JsonList(value, computed)
    return value


@dataclass(frozen=True)
class PreparedPdfCertificationInput:
    """Exact converted values and the preparation acknowledged by the stream owner."""

    document: Any
    spool: PdfStreamSpool
    conversion_status: str
    errors: tuple[str, ...]
    recipe: bytes
    formula_outcomes: tuple[Any, ...]
    effective_options: bytes


@dataclass
class StreamingPdfResult:
    document: Any
    spool: PdfStreamSpool
    conversion_status: str
    errors: tuple[str, ...]
    recipe: bytes
    formula_outcomes: tuple[Any, ...]

    def iter_records(
        self,
        *,
        product_id: str,
        revision_id: str,
        release_id: str,
        source_digest: str,
        write_scalar: Any,
    ) -> Iterator[Any]:
        from corpus_structure.semantic.pdf_records import iter_native_records

        yield from iter_native_records(
            _json_view(self.document),
            product_id=product_id,
            revision_id=revision_id,
            release_id=release_id,
            source_digest=source_digest,
            record_id_for=lambda address, kind: sha256(
                (source_digest + "\0" + address + "\0" + kind).encode()
            ).hexdigest(),
            write_scalar=write_scalar,
        )

    def write_record_batches(
        self,
        root: Path,
        *,
        build_id: str,
        release_id: str,
        source_digest: str,
        on_batch: Callable[[PdfReplayRef], None] | None = None,
        preparation_report: bytes = b"{}",
        lowering: CapturedPdfLowering | None = None,
    ) -> tuple[PdfReplayRef, ...]:
        """Own IPC replay, emit bounded batches synchronously, retain files for retries."""
        import pyarrow as pa

        from corpus_structure.semantic.pdf_record_identity import (
            IdentityFold,
            ScalarDescriptor,
            emit_parts,
        )

        if lowering is None:
            from corpus_structure.semantic.pdf_contracts import trusted_pdf_context
            from corpus_structure.semantic.pdf_lowering_context import capture_pdf_lowering

            lowering = capture_pdf_lowering(trusted_pdf_context())
        max_batch_bytes, max_batch_rows = lowering.max_batch_bytes, lowering.max_batch_rows

        root.mkdir(parents=True, exist_ok=False)
        pending: dict[str, list[dict[str, Any]]] = {}
        sizes: dict[str, int] = {}
        files: list[PdfReplayRef] = []

        def flush(family: str) -> None:
            rows = pending.pop(family, [])
            sizes.pop(family, None)
            if not rows:
                return
            schema = lowering.schema("stage:" + family)
            batch = pa.RecordBatch.from_pylist(rows, schema=schema)
            if batch.nbytes > max_batch_bytes:
                raise ValueError("native replay batch exceeds declared byte limit")
            path = root / f"{len(files):08}-{family}.arrow"
            temporary = path.with_suffix(".tmp")
            with (
                pa.OSFile(str(temporary), "wb") as sink,
                pa.ipc.new_file(sink, schema) as writer,
            ):
                writer.write_batch(batch)
            with temporary.open("rb") as sync:
                os.fsync(sync.fileno())
            temporary.replace(path)
            replay = _ref(path, family, len(rows))
            if on_batch:
                on_batch(replay)
            files.append(replay)

        def append(family: str, row: dict[str, Any]) -> None:
            self.spool.active()
            size = (
                sum(len(value) if isinstance(value, (str, bytes)) else 16 for value in row.values())
                + 256
            )
            if size > max_batch_bytes:
                raise ValueError("native record requires artifact overflow")
            if (
                sizes.get(family, 0) + size > max_batch_bytes // 2
                or len(pending.get(family, ())) >= max_batch_rows
            ):
                flush(family)
            pending.setdefault(family, []).append(row)
            sizes[family] = sizes.get(family, 0) + size

        def scalar(stream_id: str, profile: str, chunks: Any) -> ScalarDescriptor:
            folded = IdentityFold("bytes")
            digest = sha256()
            common = {"product_id": build_id, "revision_id": build_id, "stream_id": stream_id}
            # Complete the descriptor before its first protected transfer. The
            # local complete packet is retained for independent certification.
            from tempfile import TemporaryFile

            with TemporaryFile() as buffered:
                for part in emit_parts(stream_id, chunks):
                    folded.add(part.body)
                    digest.update(part.body)
                    buffered.write(part.body)
                append(
                    "artifact_stream",
                    {
                        **common,
                        "byte_length": folded.byte_length,
                        "serialization_sha256": digest.hexdigest(),
                        "byte_root": folded.digest().hex(),
                        "encoding_profile": profile,
                    },
                )
                flush("artifact_stream")
                buffered.seek(0)

                def prepared_chunks():
                    while chunk := buffered.read(65536):
                        yield chunk

                for part in emit_parts(stream_id, prepared_chunks()):
                    append(
                        "artifact_part",
                        {
                            **common,
                            "ordinal": part.ordinal,
                            "byte_offset": part.offset,
                            "byte_length": part.byte_length,
                            "body": part.body,
                            "sha256_digest": part.sha256_digest,
                        },
                    )
                # One stream per part replay keeps omission and exact retry stable.
                flush("artifact_part")
            return ScalarDescriptor(
                profile[-1:].encode() if profile.startswith("pdf-record-scalar-v1:") else b"y",
                folded.byte_length,
                folded.digest(),
            )

        def file_chunks(path: Path):
            with path.open("rb") as handle:
                while chunk := handle.read(65536):
                    yield chunk

        health = root / "completion.jsonl"
        from dataclasses import asdict

        with health.open("x", encoding="utf8") as output:
            header = {
                "kind": "conversion",
                "status": self.conversion_status,
                "source_digest": source_digest,
                "recipe_sha256": sha256(self.recipe).hexdigest(),
                "basis": "standard-native-before-integration",
            }
            output.write(json.dumps(header, separators=(",", ":")) + "\n")
            for error in self.errors:
                output.write(json.dumps({"kind": "error", "error": error}) + "\n")
            for outcome in self.formula_outcomes:
                output.write(json.dumps({"kind": "formula", **asdict(outcome)}) + "\n")
            output.flush()
            os.fsync(output.fileno())
        scalar("native/completion", lowering.artifact_profile("native_completion"), file_chunks(health))
        scalar("native/recipe", lowering.artifact_profile("native_recipe"), iter((self.recipe,)))
        scalar(
            "native/prepared-runtime",
            lowering.artifact_profile("native_recipe"),
            iter((preparation_report,)),
        )

        for row in self.iter_records(
            product_id=build_id,
            revision_id=build_id,
            release_id=release_id,
            source_digest=source_digest,
            write_scalar=scalar,
        ):
            append("header" if row.kind == "document" else row.kind, dict(row.values))
        for family in list(pending):
            flush(family)
        return tuple(files)

    def certified_reply(
        self,
        request: PdfStreamRequest,
        *,
        on_replay: Callable[[PdfReplayRef], None],
        preparation_report: bytes,
        lowering: CapturedPdfLowering | None = None,
    ) -> PdfStreamReply:
        """Emit the exact certified record and access artifacts for native adoption."""
        from corpus_structure.semantic.pdf_certification import certify_native_stream

        if lowering is None:
            lowering = CapturedPdfLowering.from_document(
                json.loads(request.validation_contract).get("lowering")
            )
        records = self.write_record_batches(
            request.record_root,
            build_id=request.build_id,
            release_id=request.release_id,
            source_digest=request.source.digest,
            on_batch=on_replay,
            preparation_report=preparation_report,
            lowering=lowering,
        )
        on_replay(_ref(request.record_root / "completion.jsonl", "native_completion"))
        prepared = PreparedPdfCertificationInput(
            self.document,
            self.spool,
            self.conversion_status,
            self.errors,
            self.recipe,
            self.formula_outcomes,
            preparation_report,
        )
        companions, certification, access = certify_native_stream(
            prepared, request, records, on_replay=on_replay
        )
        return PdfStreamReply(
            self.conversion_status,
            self.errors,
            self.recipe,
            tuple(self.spool.pages[number] for number in sorted(self.spool.pages)),
            records,
            preparation_report,
            companions,
            certification,
            access,
        )


class PdfStreamProducer(Protocol):
    def prepare(self, source: PdfSourceRef, spool: PdfStreamSpool) -> bytes: ...

    def convert(
        self, source: PdfSourceRef, spool: PdfStreamSpool, *, page_range: tuple[int, int] | None
    ) -> StreamingPdfResult: ...


def run_pdf_stream(
    request: PdfStreamRequest,
    producer: PdfStreamProducer,
    *,
    on_replay: Callable[[PdfReplayRef], None],
    check_active: Callable[[], None] | None = None,
) -> PdfStreamReply:
    """Own native preparation, acknowledgement, conversion and certified emission."""
    from corpus_structure.semantic.pdf_payloads import prepare_payload_schema, schema_load

    from .pdf_build_spool import native_preparation_identity

    request.source.verify()
    lowering = CapturedPdfLowering.from_document(
        json.loads(request.validation_contract).get("lowering")
    )
    spool = PdfStreamSpool(
        request.spool_root,
        on_page=on_replay,
        payload_family=prepare_payload_schema(schema_load(request.payload_schema)),
        recovery_pages=request.recovery_pages,
        check_active=check_active,
    )
    spool.active()
    report = producer.prepare(request.source, spool)
    identity = native_preparation_identity(report)
    prepared = _atomic_bytes(spool.root / "native-preparation.json", report, "native_preparation")
    if spool.preparation_identities and spool.preparation_identities != {identity}:
        raise ValueError("resumed PDF native preparation differs from its verified page spool")
    on_replay(prepared)
    spool.active()
    result = producer.convert(request.source, spool, page_range=request.page_range)
    return result.certified_reply(
        request, on_replay=on_replay, preparation_report=report, lowering=lowering
    )


class StreamingPdfProducer:
    def __init__(self, recipe: Any, *, assets: Any = None):
        if recipe.recipe_id != "docling-standard-pdf-stream-v1":
            raise ValueError("streaming requires the explicit native-raster streaming recipe")
        self.recipe, self.assets = recipe, assets
        self.converter = None

    def prepare(self, source: PdfSourceRef, spool: PdfStreamSpool) -> bytes:
        from .pdf import PdfConverter

        converter = PdfConverter(self.recipe, assets=self.assets, stream_spool=spool)
        converter._prepare()
        self.converter = converter
        return converter.prepared_options_report

    def convert(
        self,
        source: PdfSourceRef,
        spool: PdfStreamSpool,
        *,
        page_range: tuple[int, int] | None = None,
    ) -> StreamingPdfResult:
        converter = self.converter
        if converter is None:
            raise ValueError("native PDF conversion requires prepared options")
        options = {} if page_range is None else {"page_range": page_range}
        result = None
        try:
            result = converter._converter.convert(source.path, raises_on_error=False, **options)
            spool.active()
            if result.status.value == "failure":
                raise RuntimeError("streaming native conversion failed: " + str(result.errors))
            result.document.validate_document()
            assert converter._formula is not None
            return StreamingPdfResult(
                result.document,
                spool,
                result.status.value,
                tuple(str(error) for error in result.errors),
                self.recipe.to_bytes(),
                tuple(converter._formula.outcomes),
            )
        finally:
            if result is not None:
                result.input.release()
            converter._page_lifetime.clear()


def iter_replay_artifact_batches(
    replay: PdfReplayRef, *, build_id: str, stream_id: str, encoding_profile: str
):
    """Parent-side durable uptake, bounded batches before acknowledging a page."""
    import pyarrow as pa

    from corpus_structure.semantic.pdf_record_identity import IdentityFold, emit_parts
    from corpus_structure.semantic.pdf_staging import MAX_BATCH_BYTES, stage_schema

    replay.verify()

    def chunks():
        with replay.path.open("rb") as source:
            while body := source.read(65536):
                yield body

    common = {"product_id": build_id, "revision_id": build_id, "stream_id": stream_id}
    folded = IdentityFold("bytes")
    digest = sha256()
    for part in emit_parts(stream_id, chunks()):
        folded.add(part.body)
        digest.update(part.body)
    yield (
        "artifact_stream",
        pa.RecordBatch.from_pylist(
            [
                {
                    **common,
                    "byte_length": folded.byte_length,
                    "serialization_sha256": digest.hexdigest(),
                    "byte_root": folded.digest().hex(),
                    "encoding_profile": encoding_profile,
                }
            ],
            schema=stage_schema("artifact_stream"),
        ),
    )
    pending, size = [], 0
    for part in emit_parts(stream_id, chunks()):
        pending.append(
            {
                **common,
                "ordinal": part.ordinal,
                "byte_offset": part.offset,
                "byte_length": part.byte_length,
                "body": part.body,
                "sha256_digest": part.sha256_digest,
            }
        )
        size += part.byte_length + 512
        if size >= MAX_BATCH_BYTES // 2:
            yield (
                "artifact_part",
                pa.RecordBatch.from_pylist(pending, schema=stage_schema("artifact_part")),
            )
            pending, size = [], 0
    if pending:
        yield (
            "artifact_part",
            pa.RecordBatch.from_pylist(pending, schema=stage_schema("artifact_part")),
        )
