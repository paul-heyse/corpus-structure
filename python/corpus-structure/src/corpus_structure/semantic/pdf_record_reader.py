"""Selective published record reads and explicitly streamed native serialization.

The caller owns the Connection and its snapshot. Iterators own only bounded result
pages; no iterator returns a model initialized from a different product pin.
"""

from __future__ import annotations

import codecs
import json
from collections.abc import Callable, Generator, Iterator, Mapping, Sequence
from contextlib import closing, contextmanager, nullcontext
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from typing import Any, BinaryIO

import pyarrow as pa
import pyarrow.compute as pc
from sqlalchemy import Connection, text

from corpus_structure.core.db.lifetime import BorrowerCancellation
from corpus_structure.core.db.store import (
    DatabaseOperationFailure,
    DatabasePhase,
    EffectKnowledge,
    classify_error,
    record_operation_failure,
)

from .product_reference import ProductReference

_METADATA_PROJECTIONS = (
    "pointer",
    "outcome",
    "has_diagnostic",
    "page_no",
    "payload_schema_digest",
    "payload_codec",
    "payload_logical_digest",
)


@dataclass(frozen=True, slots=True)
class PdfExportReceipt:
    byte_length: int
    serialization_sha256: str


def published_native_table(conn: Connection, kind: str = "item"):
    """Use current published projections, retaining the archived deployment route."""
    from sqlalchemy import MetaData

    from .metadata import table

    if kind not in {"item", "region"}:
        raise ValueError("unknown native access projection")
    name = "ops.pdf_published_" + kind
    exists = conn.execute(
        text("SELECT to_regclass(:name) IS NOT NULL"), {"name": name}
    ).scalar_one()
    legacy = table("kb.native_document_" + kind)
    return (
        legacy.to_metadata(MetaData(), name="pdf_published_" + kind, schema="ops")
        if exists
        else legacy
    )


def published_record_reader(
    conn: Connection,
    reference: ProductReference,
    *,
    cancellation: BorrowerCancellation | None = None,
):
    """Return the published port, or None for an explicitly archived PDF product."""
    cancellation = cancellation or BorrowerCancellation()
    with cancellation.borrow(conn):
        available = conn.execute(
            text(
                "SELECT to_regprocedure('ops.read_pdf_published_revision(bigint,te"
                "xt,text)') IS NOT NULL"
            )
        ).scalar_one()
        if not available:
            return None
        row = (
            conn.execute(
                text("SELECT * FROM ops.read_pdf_published_revision(:task,:product,:digest)"),
                dict(
                    task=reference.task_id,
                    product=reference.product_key,
                    digest=reference.content_digest,
                ),
            )
            .mappings()
            .one_or_none()
        )
        return (
            PublishedPdfReader(conn, reference, revision=dict(row), cancellation=cancellation)
            if row
            else None
        )


class PublishedPdfReader:
    def __init__(
        self,
        conn: Connection,
        reference: ProductReference,
        *,
        revision: Mapping[str, Any] | None = None,
        cancellation: BorrowerCancellation | None = None,
    ):
        self.conn, self.reference = conn, reference
        self.cancellation = cancellation or BorrowerCancellation()
        if revision is None:
            with self._read_scope():
                row = (
                    conn.execute(
                        text(
                            "SELECT * FROM ops.read_pdf_published_revision(:task,:product,:digest)"
                        ),
                        dict(
                            task=reference.task_id,
                            product=reference.product_key,
                            digest=reference.content_digest,
                        ),
                    )
                    .mappings()
                    .one()
                )
            revision = dict(row)
        self.revision: dict[str, Any] = dict(revision)
        self._cached_record: Callable[[str], dict[str, Any]] = lru_cache(maxsize=256)(self._record)

    @contextmanager
    def _read_scope(self) -> Generator[None]:
        """Cancel only this live read; the caller retains its connection/snapshot owner."""
        cancellation = getattr(self, "cancellation", None)
        scope = cancellation.borrow(self.conn) if cancellation is not None else nullcontext()
        try:
            with scope:
                yield
                self._check_active()
        except Exception as error:
            record_operation_failure(
                error,
                DatabaseOperationFailure(
                    classify_error(
                        error,
                        phase=DatabasePhase.EXECUTING,
                        effects=EffectKnowledge.NONE,
                        cancellation_requested=cancellation is not None and cancellation.requested,
                    ),
                    f"pdf:{self.reference.task_id}:{self.reference.product_key}",
                    "close_read_snapshot",
                    getattr(self, "revision", {}).get("release_id"),
                ),
            )
            raise

    def _check_active(self) -> None:
        cancellation = getattr(self, "cancellation", None)
        if cancellation is not None:
            cancellation.check_active()

    def iter_rows(
        self,
        family: str,
        filters: Mapping[str, Any] | None = None,
        *,
        after=None,
        batch_size: int = 100,
    ) -> Generator[dict[str, Any]]:
        if not 1 <= batch_size <= 1000:
            raise ValueError("published record batch size must be 1..1000")
        while True:
            # Each bounded function call rechecks the immutable published binding. Close
            # Result before yielding so abandonment cannot leak a server-side cursor.
            with (
                self._read_scope(),
                self.conn.execute(
                    text(
                        "SELECT * FROM ops.read_pdf_record_rows(:task,:product,:digest,:family,"
                        "CAST(:filters AS jsonb),CAST(:after AS jsonb),:limit)"
                    ).execution_options(yield_per=batch_size),
                    dict(
                        task=self.reference.task_id,
                        product=self.reference.product_key,
                        digest=self.reference.content_digest,
                        family=family,
                        filters=json.dumps(dict(filters or {})),
                        after=json.dumps(after) if after is not None else None,
                        limit=batch_size,
                    ),
                ) as result,
            ):
                rows = [dict(r[0]) for r in result]
            if not rows:
                return
            for row in rows:
                self._check_active()
                after = row.pop("_cursor")
                for name in ("scalars_json", "structure_json", "scalar_json"):
                    if name in row and row[name] is not None:
                        row[name] = json.dumps(row[name], ensure_ascii=False, allow_nan=False)
                if family == "artifact_part":
                    row["body"] = bytes.fromhex(row["body"].removeprefix("\\x"))
                yield row
            if len(rows) < batch_size:
                return

    def _one(self, family, filters=None):
        with closing(self.iter_rows(family, filters, batch_size=2)) as rows:
            first = next(rows, None)
            if first is None or next(rows, None) is not None:
                raise ValueError("published native record is absent or ambiguous")
            return first

    def record(self, record_id: str) -> dict[str, Any]:
        self._check_active()
        return self._cached_record(record_id)

    def _record(self, record_id: str) -> dict[str, Any]:
        return self._one("native", {"record_id": record_id})

    def members(self, parent_id: str, field_name: str):
        yield from self.iter_rows("membership", {"parent_id": parent_id, "field_name": field_name})

    def scalar(self, stream_id: str) -> Generator[bytes]:
        from .pdf_record_identity import ArtifactPart, ArtifactPin, replay_artifact

        stream = self._one("artifact_stream", {"stream_id": stream_id})
        pin = ArtifactPin(
            stream_id,
            self.revision["release_id"],
            self.revision["source_digest"],
            stream["byte_length"],
            stream["serialization_sha256"],
            bytes.fromhex(stream["byte_root"]),
        )
        parts = (
            ArtifactPart(
                stream_id,
                row["ordinal"],
                row["byte_offset"],
                row["byte_length"],
                row["body"],
                row["sha256_digest"],
            )
            for row in self.iter_rows("artifact_part", {"stream_id": stream_id})
        )
        with closing(parts) as owned_parts:
            for chunk in replay_artifact(
                owned_parts,
                pin,
                release_id=self.revision["release_id"],
                source_digest=self.revision["source_digest"],
            ):
                self._check_active()
                yield chunk
        self._check_active()

    def _profile(self, stream_id):
        return self._one("artifact_stream", {"stream_id": stream_id})["encoding_profile"]

    def hydrate(self, record_id: str, *, native_type: str) -> dict[str, Any]:
        from .pdf_records import reconstruct_native_document

        class Profiles(dict[str, str]):
            def __missing__(_, stream_id):
                value = self._profile(stream_id)
                _[stream_id] = value
                return value

        self._check_active()
        value = reconstruct_native_document(
            self, record_id, scalar_profiles=Profiles(), native_type=native_type
        )
        self._check_active()
        return value

    def hydrate_document(self):
        """Explicit whole-value demand uses one ordered native cursor, without repairs."""
        with closing(self.iter_native_json()) as chunks:
            value = json.loads(b"".join(chunks))
        self._check_active()
        return value

    def product_kind(self) -> str:
        with self._read_scope():
            return self.conn.execute(
                text(
                    "SELECT kind FROM ops.pdf_product WHERE task_id=:task AND product_key=:product "
                    "AND content_digest=:digest"
                ),
                dict(
                    task=self.reference.task_id,
                    product=self.reference.product_key,
                    digest=self.reference.content_digest,
                ),
            ).scalar_one()

    def native_items(self, pointers):
        result = {}
        for pointer in dict.fromkeys(pointers):
            row = self._one("native", {"native_address": pointer})
            result[pointer] = self.hydrate(row["record_id"], native_type=row["native_type"])
        return result

    def _metadata_rows(self, kind: str, *, pointer=None, page_nos: Sequence[int] | None = None):
        filters: dict[str, Any] = {"family": "native_metadata", "kind": kind}
        if pointer is not None:
            filters["pointer"] = pointer
        if page_nos is not None:
            if any(type(number) is not int or number < 1 for number in page_nos):
                raise ValueError("payload page selectors require positive integer page numbers")
            if not page_nos:
                return
            filters["page_nos"] = sorted(set(page_nos))
        yield from self.iter_rows("companion", filters)

    def _payload_context(self):
        """Prepare once from the producing release, independent of installed current schemas."""
        if not hasattr(self, "_prepared_payload_context"):
            from .pdf_contracts import pdf_context_for_release
            from .releases import open_release

            with self._read_scope():
                self._prepared_payload_context = pdf_context_for_release(
                    self.conn, open_release(self.conn, self.revision["release_id"])
                )
        return self._prepared_payload_context

    def native_metadata(self, kind, *, pointer=None, page_nos: Sequence[int] | None = None):
        """Materialize only selected metadata pages, preserving the logical Python contract."""
        for row in self._metadata_rows(kind, pointer=pointer, page_nos=page_nos):
            yield self.decode_companion_row(row)["value"]

    def iter_payload_batches(
        self,
        kind: str = "inline_candidate_pages",
        *,
        page_nos: Sequence[int] | None = None,
        columns: Sequence[str] | None = None,
        context=None,
    ) -> Iterator[pa.RecordBatch]:
        """Yield owned selected-page batches after closing each artifact result page."""
        from .pdf_payloads import FAMILY, PROFILE, page_payload_batches

        if kind != FAMILY:
            raise ValueError("metadata family has no declared Arrow payload realization")
        for row in self._metadata_rows(kind, page_nos=page_nos):
            body = row["body"]
            fields = row.get("_fields", ())
            if len(fields) != 1 or fields[0]["field_name"] != "value":
                raise ValueError("page payload requires exactly one external value")
            field = fields[0]
            if body.get("payload_codec") != PROFILE or field["encoding_profile"] != PROFILE:
                raise ValueError(
                    "page payload encoding profile differs from envelope: "
                    f"expected={PROFILE!r}, envelope={body.get('payload_codec')!r}, "
                    f"field={field['encoding_profile']!r}; inspect the producing release "
                    "and rebuild from compatible retained evidence"
                )
            payload = b"".join(self.scalar(field["stream_id"]))
            self._check_active()
            for batch in page_payload_batches(
                payload,
                context if context is not None else self._payload_context(),
                schema_digest=body["payload_schema_digest"],
                logical_digest=body["payload_logical_digest"],
                columns=columns,
            ):
                self._check_active()
                yield batch

    def candidate_inventory(self, *, page_nos: Sequence[int] | None = None, context=None):
        """Project page inventory through Arrow kernels without hydrating candidate/OCR objects."""
        for batch in self.iter_payload_batches(
            page_nos=page_nos, columns=("page_no", "candidates", "ocr_regions"), context=context
        ):
            candidates = pc.call_function("list_value_length", [batch.column("candidates")])
            regions = batch.column("ocr_regions")
            region_count = pc.call_function("list_value_length", [regions])
            # Each payload is exactly one page; nested word inventory stays in columnar arrays.
            lines = pc.call_function(
                "list_flatten",
                [
                    pc.call_function(
                        "struct_field",
                        [pc.call_function("list_flatten", [regions])],
                        options=pc.StructFieldOptions("lines"),
                    )
                ],
            )
            words = pc.call_function(
                "list_flatten",
                [pc.call_function("struct_field", [lines], options=pc.StructFieldOptions("words"))],
            )
            yield {
                "page_no": batch.column("page_no")[0].as_py(),
                "candidate_count": candidates[0].as_py() or 0,
                "ocr_region_count": region_count[0].as_py() or 0,
                "ocr_word_count": len(words),
            }

    def iter_candidate_payloads(self, *, context=None):
        """Yield exact source-qualified IPC bytes without reconstructing nested values."""
        from .pdf_payloads import PROFILE, EncodedPagePayload, prepare_payload_family

        family = prepare_payload_family(context if context is not None else self._payload_context())
        for row in self._metadata_rows("inline_candidate_pages"):
            body = row["body"]
            fields = row.get("_fields", ())
            if len(fields) != 1 or fields[0]["field_name"] != "value":
                raise ValueError("page payload requires exactly one external value")
            field = fields[0]
            if body.get("payload_codec") != PROFILE or field["encoding_profile"] != PROFILE:
                raise ValueError("page payload requires its released Arrow realization")
            payload = b"".join(self.scalar(field["stream_id"]))
            batch = family.read_batch(
                payload,
                schema_digest=body["payload_schema_digest"],
                logical_digest=body["payload_logical_digest"],
            )
            page_no = batch.column("page_no")[0].as_py()
            if page_no != body["page_no"]:
                raise ValueError("candidate payload page differs from its envelope")
            self._check_active()
            yield EncodedPagePayload(
                payload, body["payload_schema_digest"], body["payload_logical_digest"], page_no
            )

    def native_product_values(self, *, include_candidate_pages: bool = True):
        """Explicit materialization for native transformations; never a small read."""
        document = self.hydrate_document()
        health_rows = list(self.iter_companions("health"))
        wrappers = [h for h in health_rows if "source_scope" in h]
        if len(wrappers) != 1:
            raise ValueError("native health/source scope is absent or ambiguous")
        wrapper = wrappers[0]
        health = {
            key: value
            for key, value in wrapper.items()
            if key not in {"source_scope", "page_start", "page_end"}
        }
        outcomes = list(self.native_metadata("formula_outcomes"))
        if outcomes:
            health["formula_outcomes"] = outcomes
        value = dict(
            recipe="pdf-native-v1",
            native_schema_version=document["version"],
            derivation_mappings=[],
            product_key=self.reference.product_key,
            artifact_digest=self.revision["source_digest"],
            schema_digest=self.revision["schema_digest"],
            recipe_digest=self.revision["recipe_digest"],
            document=document,
            source_scope=wrapper["source_scope"],
            health=health,
        )
        if wrapper["source_scope"] == "page_range":
            if not all(key in wrapper for key in ("page_start", "page_end")):
                raise ValueError("native page range has no admitted bounds")
            value.update(page_start=wrapper["page_start"], page_end=wrapper["page_end"])
        for kind in (
            "inline_candidate_pages",
            "derivation_mappings",
            "cell_reports",
            "inline_alignment_reports",
            "recognition_coverage",
        ):
            if kind == "inline_candidate_pages" and not include_candidate_pages:
                continue
            values = list(self.native_metadata(kind))
            if values:
                value[kind] = values
        structural = next(
            (r for r in self.iter_companions("input") if r.get("role") == "structural"), None
        )
        if structural is not None:
            value.update(
                parent_task_id=structural["task_id"],
                parent_product_key=structural["product_key"],
                parent_digest=structural["content_digest"],
            )
        runtime = list(self.native_metadata("runtime_report"))
        if runtime:
            if len(runtime) != 1:
                raise ValueError("native runtime metadata is ambiguous")
            value["runtime_report"] = runtime[0]
        return value

    def decode_companion_row(self, row: Mapping[str, Any]) -> dict[str, Any]:
        """Materialize one requested field from exact bytes, retaining JSON float bits."""
        self._check_active()
        body = dict(row["body"])
        if row.get("family") == "native_metadata":
            for projection in _METADATA_PROJECTIONS:
                body.pop(projection, None)
        for field in row.get("_fields", ()):
            name, kind = field["field_name"], field["scalar_kind"]
            if name in body:
                raise ValueError("companion field has both inline and external values")
            payload = b"".join(self.scalar(field["stream_id"]))
            from .pdf_payloads import PROFILE, decode_page_payload

            self._check_active()
            profile = field["encoding_profile"]
            if profile == PROFILE:
                if row["body"].get("payload_codec") != PROFILE:
                    raise ValueError("page payload encoding profile differs from envelope")
                body[name] = decode_page_payload(
                    payload,
                    self._payload_context(),
                    schema_digest=row["body"]["payload_schema_digest"],
                    logical_digest=row["body"]["payload_logical_digest"],
                )
            elif kind == "y":
                body[name] = json.loads(payload)
            elif kind == "s":
                body[name] = payload.decode("utf-8")
            else:
                raise ValueError("unsupported companion scalar kind")
            self._check_active()
        self._check_active()
        return body

    def iter_companions(self, family) -> Iterator[Mapping[str, Any]]:
        for row in self.iter_rows("companion", {"family": family}):
            yield self.decode_companion_row(row)

    def iter_companion_export_events(self, family) -> Generator[dict[str, Any]]:
        with (
            self._read_scope(),
            self.conn.execute(
                text(
                    "SELECT * FROM ops.read_pdf_companion_export_events(:task,:product,:digest,"
                    ":family)"
                ).execution_options(yield_per=32),
                dict(
                    task=self.reference.task_id,
                    product=self.reference.product_key,
                    digest=self.reference.content_digest,
                    family=family,
                ),
            ) as result,
        ):
            for row in result:
                self._check_active()
                yield row[0]

    def iter_companion_json(self, family, events=None) -> Generator[bytes]:
        """One joined cursor streams exact fields without per-field SQL or JSONB coercion."""
        from .pdf_record_identity import ArtifactPart, ArtifactPin, replay_artifact

        def encode(value):
            self._check_active()
            encoded = json.dumps(
                value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
            ).encode()
            self._check_active()
            return encoded

        owns_events = events is None
        events = self.iter_companion_export_events(family) if owns_events else events
        pending = None
        envelope = {}
        first_row = True
        first_field = True
        try:
            while True:
                self._check_active()
                event = pending if pending is not None else next(events, None)
                pending = None
                if event is None:
                    return
                kind = event["kind"]
                if kind == "row":
                    if not first_row:
                        yield b","
                    first_row = False
                    envelope = event["body"]
                    body = dict(envelope)
                    if family == "native_metadata":
                        for projection in _METADATA_PROJECTIONS:
                            body.pop(projection, None)
                    encoded = encode(body)
                    yield b"{" + encoded[1:-1]
                    first_field = not bool(body)
                elif kind == "field":
                    field = event["field"]
                    yield (b"" if first_field else b",") + encode(field["field_name"]) + b":"
                    first_field = False
                    pin = ArtifactPin(
                        field["stream_id"],
                        self.revision["release_id"],
                        self.revision["source_digest"],
                        field["byte_length"],
                        field["serialization_sha256"],
                        bytes.fromhex(field["byte_root"]),
                    )

                    def parts():
                        nonlocal pending
                        for following in events:
                            if following["kind"] != "part":
                                pending = following
                                return
                            part = following["part"]
                            yield ArtifactPart(
                                part["stream_id"],
                                part["ordinal"],
                                part["byte_offset"],
                                part["byte_length"],
                                bytes.fromhex(part["body"].removeprefix("\\x")),
                                part["sha256_digest"],
                            )

                    chunks = replay_artifact(
                        parts(),
                        pin,
                        release_id=self.revision["release_id"],
                        source_digest=self.revision["source_digest"],
                    )
                    from .pdf_payloads import PROFILE, decode_page_payload

                    if field["encoding_profile"] == PROFILE:
                        if envelope.get("payload_codec") != PROFILE:
                            raise ValueError("page payload encoding profile differs from envelope")
                        yield encode(
                            decode_page_payload(
                                b"".join(chunks),
                                self._payload_context(),
                                schema_digest=envelope["payload_schema_digest"],
                                logical_digest=envelope["payload_logical_digest"],
                            )
                        )
                    elif field["scalar_kind"] == "y":
                        yield from chunks
                    elif field["scalar_kind"] == "s":
                        yield b'"'
                        decoder = codecs.getincrementaldecoder("utf-8")()
                        for chunk in chunks:
                            yield encode(decoder.decode(chunk))[1:-1]
                        yield encode(decoder.decode(b"", final=True))[1:-1]
                        yield b'"'
                    else:
                        raise ValueError("unsupported companion scalar kind")
                elif kind == "close":
                    yield b"}"
                else:
                    raise ValueError("unexpected companion export event")
        finally:
            if owns_events:
                events.close()

    def context_rows(self, family, pointers, section_pointer):
        after = ""
        while True:
            with (
                self._read_scope(),
                self.conn.execute(
                    text(
                        "SELECT * FROM ops.read_pdf_record_context_rows(:task,:product,:digest,"
                        "CAST(:pointers AS text[]),:section,:family,:after,:limit)"
                    ),
                    dict(
                        task=self.reference.task_id,
                        product=self.reference.product_key,
                        digest=self.reference.content_digest,
                        pointers=list(pointers),
                        section=section_pointer,
                        family=family,
                        after=after,
                        limit=100,
                    ),
                ) as result,
            ):
                rows = [dict(row[0]) for row in result]
            for row in rows:
                self._check_active()
                after = row["local_id"]
                yield row
            if len(rows) < 100:
                return

    def source_context(
        self,
        pointers,
        section_pointer,
        *,
        row_budget: int | None = None,
        membership: str = "direct",
    ) -> dict[str, Any]:
        """Use the same published relational context constructor as native frame guards."""
        with self._read_scope():
            value = self.conn.execute(
                text(
                    "SELECT ops.record_integrated_source_context(:task,:product,:digest,"
                    "CAST(:pointers AS text[]),:section,:membership,:budget)"
                ),
                dict(
                    task=self.reference.task_id,
                    product=self.reference.product_key,
                    digest=self.reference.content_digest,
                    pointers=list(pointers),
                    section=section_pointer,
                    membership=membership,
                    budget=row_budget,
                ),
            ).scalar_one()
        if value is None:
            raise ValueError("published integrated source context is unavailable")
        return value

    def iter_native_json(self, events=None) -> Generator[bytes]:
        """One ordered containment cursor; scalar parts remain bounded owned reads."""
        from .pdf_records import _decode_scalar, _parse_inline

        def encode(value):
            self._check_active()
            encoded = json.dumps(
                value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
            ).encode()
            self._check_active()
            return encoded

        def scalar(stream_id):
            profile = self._profile(stream_id)
            with closing(self.scalar(stream_id)) as chunks:
                if profile == "pdf-record-native-json-v1":
                    yield from chunks
                elif profile == "pdf-record-scalar-v1:s":
                    yield b'"'
                    decoder = codecs.getincrementaldecoder("utf-8")()
                    for chunk in chunks:
                        yield encode(decoder.decode(chunk))[1:-1]
                    yield encode(decoder.decode(b"", final=True))[1:-1]
                    yield b'"'
                else:
                    yield encode(_decode_scalar(chunks, profile))

        scope = closing(self.iter_native_events()) if events is None else nullcontext(events)
        with scope as owned_events:
            for event in owned_events:
                self._check_active()
                kind, value = event["kind"], event["value"]
                if kind == "literal":
                    yield value.encode("utf-8")
                elif kind == "inline":
                    yield encode(_parse_inline(value))
                elif kind in {"parts", "key_parts"}:
                    if kind == "key_parts":
                        yield event["prefix"].encode()
                    yield from scalar(value)
                    if kind == "key_parts":
                        yield b":"
                elif kind == "extension":
                    pending, opened, separator = b"", False, event["prefix"]
                    with closing(self.scalar(value)) as chunks:
                        for chunk in chunks:
                            if not opened:
                                if not chunk.startswith(b"{"):
                                    raise ValueError("native extension is not an object")
                                chunk, opened = chunk[1:], True
                            pending += chunk
                            if len(pending) > 1:
                                if separator:
                                    yield separator.encode()
                                    separator = ""
                                yield pending[:-1]
                                pending = pending[-1:]
                    if not opened or pending != b"}":
                        raise ValueError("native extension object is incomplete")
                else:
                    raise ValueError("unsupported published export event")

    def iter_native_events(self) -> Generator[dict[str, Any]]:
        with (
            self._read_scope(),
            self.conn.execute(
                text(
                    "SELECT * FROM ops.read_pdf_native_events(:task,:product,:digest)"
                ).execution_options(yield_per=256),
                dict(
                    task=self.reference.task_id,
                    product=self.reference.product_key,
                    digest=self.reference.content_digest,
                ),
            ) as result,
        ):
            for row in result:
                self._check_active()
                yield row[0]

    def write_native_json(self, sink: BinaryIO) -> PdfExportReceipt:
        digest, size = sha256(), 0
        with closing(self.iter_native_json()) as chunks:
            for chunk in chunks:
                self._check_active()
                sink.write(chunk)
                self._check_active()
                digest.update(chunk)
                size += len(chunk)
        self._check_active()
        return PdfExportReceipt(size, digest.hexdigest())

    def write_integrated_json(self, sink: BinaryIO, *, binding=None) -> PdfExportReceipt:
        """Version2 export carries native values, typed companions and immutable bindings.

        Its serialization hash is distinct from the admitted logical digest. It is
        not the historical version1 canonical-envelope replay format.
        """
        if self.product_kind() != "integrated":
            raise ValueError("integrated JSON export requires an integrated product")
        digest, size = sha256(), 0

        def write(chunk):
            nonlocal size
            self._check_active()
            sink.write(chunk)
            self._check_active()
            digest.update(chunk)
            size += len(chunk)

        def encode(value):
            self._check_active()
            encoded = json.dumps(
                value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
            ).encode()
            self._check_active()
            return encoded

        write(
            b'{"export_profile":"pdf-integrated-record-export-v2","binding":'
            + encode(binding or {})
            + b',"product":{"version":2,"kind":"integrated","product_key":'
            + encode(self.reference.product_key)
            + b',"logical_digest":'
            + encode(self.reference.content_digest)
            + b',"revision":'
            + encode(self.revision)
            + b',"content":'
        )
        with closing(self.iter_native_json()) as chunks:
            for chunk in chunks:
                write(chunk)
        for family, name in (
            ("input", "inputs"),
            ("occurrence", "occurrences"),
            ("relation", "relations"),
            ("mapping_report", "mapping_reports"),
            ("coverage", "coverage"),
            ("health", "health"),
            ("request_outcome", "request_outcomes"),
            ("native_metadata", "native_metadata"),
        ):
            write(b"," + encode(name) + b":[")
            with closing(self.iter_companion_json(family)) as chunks:
                for chunk in chunks:
                    write(chunk)
            write(b"]")
        write(b"}}")
        self._check_active()
        return PdfExportReceipt(size, digest.hexdigest())
