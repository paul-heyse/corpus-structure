"""Database-free encoding of acquired PDF companion records into bounded Arrow batches."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pyarrow as pa

from .pdf_replay_transport import replay_schema

if TYPE_CHECKING:
    from .pdf_lowering_context import CapturedPdfLowering

COMPANION_BATCH_ROWS = 64
COMPANION_BATCH_BYTES = 4 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class PdfCompanionRecord(Mapping[str, Any]):
    """Decoded producer row with its already encoded UTF-8 byte length."""

    body: Mapping[str, Any]
    encoded_length: int

    def __getitem__(self, key):
        return self.body[key]

    def __iter__(self):
        return iter(self.body)

    def __len__(self):
        return len(self.body)


COMPANION_STAGE_TARGETS = {
    "companion": "ops.pdf_stage_companion",
    "field": "ops.pdf_stage_companion_field",
    "stream": "ops.pdf_stage_artifact_stream",
    "part": "ops.pdf_stage_artifact_part",
}


def prepare_pdf_companion_batches(
    family: str,
    records: Iterable[Mapping[str, Any]],
    *,
    on_batch: Callable[[str, pa.RecordBatch], None],
    payload_family,
    lowering: CapturedPdfLowering | None = None,
    start_ordinal: int = 0,
    check_active: Callable[[], None] = lambda: None,
) -> None:
    """Encode exact bounded companion bytes once, before certification or COPY."""
    from hashlib import sha256

    from .identity import canonical_bytes
    from .pdf_record_identity import byte_root, emit_parts
    from .pdf_records import _finite_json

    if lowering is None:
        from .pdf_contracts import trusted_pdf_context
        from .pdf_lowering_context import capture_pdf_lowering

        lowering = capture_pdf_lowering(trusted_pdf_context())
    max_batch_bytes, max_batch_rows = lowering.max_batch_bytes, lowering.max_batch_rows

    pending, streams, parts, descriptors = [], [], [], []
    byte_count = 0

    def copy(name, rows):
        if rows:
            batch = pa.RecordBatch.from_pylist(
                rows, schema=replay_schema(lowering.schema("companion:" + name))
            )
            if batch.num_rows > max_batch_rows or batch.nbytes > max_batch_bytes:
                raise ValueError("companion COPY transfer exceeds bounded upload profile")
            on_batch(name, batch)
            rows.clear()

    def flush() -> None:
        nonlocal byte_count
        check_active()
        copy("companion", pending)
        copy("field", descriptors)
        copy("stream", streams)
        copy("part", parts)
        byte_count = 0

    codec = payload_family
    for ordinal, record in enumerate(records, start=start_ordinal):
        check_active()
        body = dict(record)
        local = str(
            body.get(
                {
                    "occurrence": "occurrence_id",
                    "relation": "relation_id",
                    "coverage": "coverage_id",
                }.get(family, ""),
                ordinal,
            )
        )
        payloads = []
        if family == "native_metadata":
            local = f"{body['kind']}:{body['ordinal']}"
            value = body.pop("value")
            if isinstance(value, Mapping):
                pointer = next(
                    (
                        value[key]
                        for key in ("pointer", "prose_pointer", "table_pointer")
                        if isinstance(value.get(key), str)
                    ),
                    None,
                )
                if pointer is not None:
                    body["pointer"] = pointer
                if body["kind"] == "inline_alignment_reports":
                    body["item_pointers"] = value["item_pointers"]
            if body["kind"] == "formula_outcomes" and isinstance(value, Mapping):
                body["outcome"] = value.get("outcome")
                body["has_diagnostic"] = "error" in value
            if body["kind"] == "inline_candidate_pages":
                from .pdf_payloads import PROFILE, AdmittedPagePayload, EncodedPagePayload

                if codec is None:
                    raise ValueError(
                        "PDF companion preparation requires the captured payload codec"
                    )
                if isinstance(value, AdmittedPagePayload):
                    if value.schema_digest != codec.schema_digest:
                        raise ValueError("encoded page schema differs from captured codec")
                    encoded = value
                elif isinstance(value, EncodedPagePayload):
                    batch = codec.read_batch(
                        value.content,
                        schema_digest=value.schema_digest,
                        logical_digest=value.logical_digest,
                    )
                    if batch.column("page_no")[0].as_py() != value.page_no:
                        raise ValueError("encoded page locator differs from IPC")
                    encoded = value
                else:
                    encoded = codec.encode_page(value)
                body.update(
                    page_no=encoded.page_no,
                    payload_schema_digest=encoded.schema_digest,
                    payload_codec=PROFILE,
                    payload_logical_digest=encoded.logical_digest,
                )
                payloads.append(("value", encoded.content, PROFILE))
            else:
                payloads.append(("value", canonical_bytes(value), "pdf-companion-json-field-v1"))
        if (
            family == "occurrence"
            and isinstance(body.get("text"), str)
            and len(body["text"].encode("utf8")) > 32768
        ):
            payloads.append(("text", body.pop("text").encode("utf8"), "pdf-record-scalar-v1:s"))
        encoded_body = canonical_bytes(body) if family == "relation" else None
        if family == "relation" and encoded_body is not None and len(encoded_body) > 32768:
            payloads.extend(
                (
                    (
                        "endpoints",
                        canonical_bytes(body.pop("endpoints")),
                        "pdf-companion-json-field-v1",
                    ),
                    ("evidence", body.pop("evidence").encode("utf8"), "pdf-record-scalar-v1:s"),
                )
            )
            encoded_body = None
        _finite_json(body, "#/companion/body")
        if encoded_body is None:
            encoded_body = canonical_bytes(body)
        size = len(encoded_body) + sum(len(payload) for _, payload, _ in payloads)
        if pending and (
            len(pending) >= COMPANION_BATCH_ROWS or byte_count + size > COMPANION_BATCH_BYTES
        ):
            flush()
        for field, payload, profile in payloads:
            stream = (
                "companion-field:" + sha256(canonical_bytes([family, local, field])).hexdigest()
            )
            common = {"stream_id": stream}
            length, root = byte_root((payload,))
            # Descriptor facts precede bounded part packets. The host can omit
            # part COPY when its protected project-scoped probe finds this key.
            streams.append(
                {
                    **common,
                    "byte_length": length,
                    "byte_root": root.hex(),
                    "serialization_sha256": None,
                    "encoding_profile": profile,
                }
            )
            copy("stream", streams)
            field_parts = []
            for part in emit_parts(stream, (payload,)):
                field_parts.append(
                    {
                        **common,
                        "ordinal": part.ordinal,
                        "byte_offset": part.offset,
                        "byte_length": part.byte_length,
                        "body": part.body,
                        "sha256_digest": part.sha256_digest,
                    }
                )
                if len(field_parts) == 64:
                    copy("part", field_parts)
            copy("part", field_parts)
            descriptors.append(
                {
                    "family": family,
                    "local_id": local,
                    "field_name": field,
                    "stream_id": stream,
                    "scalar_kind": "y" if field in {"value", "endpoints"} else "s",
                }
            )
        pending.append(
            {
                "family": family,
                "local_id": local,
                "body": encoded_body.decode("utf8"),
                "ordinal": ordinal,
            }
        )
        byte_count += size
        if byte_count > 4 * 1024 * 1024:
            flush()
    flush()
    check_active()
