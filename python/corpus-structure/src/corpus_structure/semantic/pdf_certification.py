"""Producer certification over actual output and exact prepared record bytes.

The typed payload validator owns payload interiors and integrated meaning. This
owner reads the producer's actual replay buffers and folds the canonical frames
without reconstructing its native document.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, dataclass
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from typing import Any, Literal

import pyarrow as pa

from .identity import canonical_bytes
from .pdf_lowering_context import CapturedPdfLowering
from .pdf_payload_validation import FrozenPayloadStore
from .pdf_record_identity import (
    ABSENT,
    IdentityFold,
    LogicalIdentity,
    ScalarDescriptor,
    record_frame,
    structured_payload_scalar,
)
from .pdf_replay_transport import PdfReplayBinding, read_replay_batches, replay_schema


@dataclass(frozen=True, slots=True)
class PdfProducerCertification:
    lowering_identity: str
    kind: Literal["native", "integrated"]
    logical_digest: str
    native_document_digest: str
    stream_inventory_digest: str
    source_digest: str
    recipe_digest: str
    schema_digest: str

    def to_bytes(self) -> bytes:
        return canonical_bytes(asdict(self))


@dataclass(frozen=True, slots=True)
class PdfProducerContract:
    validation_contract: bytes
    lowering_identity: str
    payload_schema: bytes


def prepare_pdf_producer_contract(
    context, *, kind: Literal["native", "integrated"]
) -> PdfProducerContract:
    """Explicit captured contract for deployed producers or unadmitted provider probes."""
    from .pdf_contracts import integrated_metadata_policy
    from .pdf_lowering import require_lowering_identity
    from .pdf_lowering_context import capture_pdf_lowering
    from .pdf_payload_validation import metadata_classes
    from .pdf_payloads import prepare_payload_family, schema_dump

    family = prepare_payload_family(context)
    contract = {
        "lowering": capture_pdf_lowering(context).document(),
        "schemas": {
            key: context.boundary.json_schema(cls)
            for key, cls in metadata_classes(context.staging.content).items()
        },
        "publication_kind": kind,
        "schema_digest": context.native_schema_digest,
        "integrated_metadata_policy": integrated_metadata_policy(context)
        if kind == "integrated"
        else None,
    }
    return PdfProducerContract(
        schema_dump(contract), require_lowering_identity(context), schema_dump(family.json_schema)
    )


def jsonb_canonical_text(value: Any) -> str:
    """Match data.canonical_json after JSONB parses the producer's JSON spelling.

    PostgreSQL numeric prints fixed notation and loses a negative zero sign;
    preserve the decimal scale of the exact JSON input, including 1.0.
    """
    value = json.loads(canonical_bytes(value), parse_float=Decimal)

    def encode(item):
        if isinstance(item, dict):
            return (
                "{"
                + ",".join(
                    json.dumps(key, ensure_ascii=False) + ":" + encode(item[key])
                    for key in sorted(item, key=lambda key: key.encode())
                )
                + "}"
            )
        if isinstance(item, list):
            return "[" + ",".join(encode(member) for member in item) + "]"
        if isinstance(item, Decimal):
            return format(abs(item) if item.is_zero() else item, "f")
        return json.dumps(item, ensure_ascii=False, separators=(",", ":"), allow_nan=False)

    return encode(value)


_FRAME_SCHEMA = pa.schema(
    [("family", pa.string()), ("record_key", pa.string()), ("frame", pa.binary())]
)


class PdfProducerPayloads(FrozenPayloadStore):
    """Certify ordered, typed producer rows beneath their captured lowering."""

    def __init__(self, validation_contract: Mapping[str, Any]):
        self.lowering = CapturedPdfLowering.from_document(validation_contract.get("lowering"))
        super().__init__(validation_contract)

    def _verify_stream_inventory(self, schema_digest: str, *, check_active) -> None:
        streams = IdentityFold("pdf-producer-streams-v1")
        for descriptor in self.stream_descriptors():
            check_active()
            self.verify_stream(descriptor, check_active=check_active)
            streams.add(
                record_frame(
                    schema_digest,
                    "producer-stream",
                    descriptor["stream_id"],
                    (
                        ("byte_length", descriptor["byte_length"]),
                        ("byte_root", descriptor["byte_root"]),
                        ("encoding_profile", descriptor["encoding_profile"]),
                        ("serialization_sha256", descriptor.get("serialization_sha256")),
                    ),
                )
            )
        self.stream_inventory_digest = streams.digest().hex()

    def add_replays(
        self,
        replays,
        *,
        check_active=lambda: None,
        legacy_binding: PdfReplayBinding | None = None,
        legacy_lowering: CapturedPdfLowering | None = None,
    ) -> None:
        for replay in replays:
            name = "stage:" + replay.family
            for batch in read_replay_batches(
                replay,
                self.lowering.schema(name),
                check_active=check_active,
                legacy_binding=legacy_binding,
                legacy_schema=None if legacy_lowering is None else legacy_lowering.schema(name),
                map_verified=True,
            ):
                self.add_batch(replay.family, batch)

    def add_companion_replays(
        self,
        sets,
        *,
        check_active=lambda: None,
        legacy_binding: PdfReplayBinding | None = None,
        legacy_lowering: CapturedPdfLowering | None = None,
    ) -> None:
        families = {
            "companion": "companion",
            "field": "companion_field",
            "stream": "artifact_stream",
            "part": "artifact_part",
        }
        for prepared in sets:
            for replay in prepared.replays:
                target = replay.family.removeprefix("prepared_companion:")
                name = "companion:" + target
                for batch in read_replay_batches(
                    replay,
                    self.lowering.schema(name),
                    check_active=check_active,
                    legacy_binding=legacy_binding,
                    legacy_schema=None if legacy_lowering is None else legacy_lowering.schema(name),
                    map_verified=True,
                ):
                    self.add_batch(families[target], batch)

    def _descriptor(self, stream: str) -> ScalarDescriptor:
        descriptor = self.descriptor(stream)
        profile = descriptor["encoding_profile"]
        kind = (
            b"y"
            if profile in {"pdf-record-native-json-v1", "pdf-companion-json-field-v1"}
            else profile[-1:].encode()
        )
        return ScalarDescriptor(
            kind, descriptor["byte_length"], bytes.fromhex(descriptor["byte_root"])
        )

    def _field_scalar(self, row, name):
        field = self.field(row["family"], row["local_id"], name)
        if field is not None:
            if (
                row["family"] == "native_metadata"
                and row["body"]["kind"] == "inline_candidate_pages"
            ):
                return structured_payload_scalar(row["body"]["payload_logical_digest"])
            return self._descriptor(field["stream_id"])
        return row["body"].get(name, ABSENT)

    def target_pins(self) -> tuple[tuple[int, str, str], ...]:
        return tuple(
            sorted(
                {
                    (
                        row["body"]["task_id"],
                        row["body"]["product_key"],
                        row["body"]["content_digest"],
                    )
                    for row in self.companions("input")
                }
            )
        )

    def _identity_fields(self, kind, recipe_digest, target_meanings):
        from .pdf_records import native_record_identity_fields_batch

        for family in ("header", "native", "membership"):
            for batch in self.batches(family):
                yield from native_record_identity_fields_batch(
                    batch,
                    kind="document" if family == "header" else family,
                    scalar_descriptor=self._descriptor,
                )
        inputs = {row["local_id"]: row["body"] for row in self.companions("input")}
        for batch in self.batches("companion"):
            columns = tuple(
                batch.column(name).to_pylist() for name in ("family", "local_id", "ordinal", "body")
            )
            for family, local_id, ordinal, body in zip(*columns, strict=True):
                row = {
                    "family": family,
                    "local_id": local_id,
                    "ordinal": ordinal,
                    "body": json.loads(body),
                }
                yield from self._companion_frames(row, inputs, target_meanings)
        yield "publication", "root", (("kind", kind), ("recipe_digest", recipe_digest))

    def _companion_frames(self, row, inputs, target_meanings):
        family, body = row["family"], dict(row["body"])
        if family == "native_metadata":
            for key in (
                ("value", "payload_codec", "payload_schema_digest")
                if body["kind"] == "inline_candidate_pages"
                else ("value", "item_pointers")
            ):
                body.pop(key, None)
        elif family == "occurrence":
            body.pop("text", None)
        elif family == "relation":
            body = self.companion_value(row)
        elif family == "input":
            pin = (body["task_id"], body["product_key"], body["content_digest"])
            body = {"role": body["role"], "target_meaning": target_meanings[pin]}
        fields = [("body", jsonb_canonical_text(body)), ("ordinal", row["ordinal"])]
        if family in {"native_metadata", "occurrence"}:
            field = "value" if family == "native_metadata" else "text"
            fields.append((field, self._field_scalar(row, field)))
        yield "companion/" + family, row["local_id"], fields
        if family == "relation":
            for ordinal, endpoint in enumerate(body["endpoints"]):
                if "input_index" in endpoint:
                    target = inputs[str(endpoint["input_index"])]
                    meaning = jsonb_canonical_text(
                        target_meanings[
                            (target["task_id"], target["product_key"], target["content_digest"])
                        ]
                    )
                else:
                    meaning = "@self"
                yield (
                    "endpoint",
                    json.dumps([row["local_id"], ordinal], separators=(",", ":")),
                    (
                        ("relation_id", row["local_id"]),
                        ("ordinal", ordinal),
                        ("target_meaning", meaning),
                        ("occurrence_id", endpoint["occurrence_id"]),
                        ("role", endpoint["role"]),
                    ),
                )

    def logical_digest(
        self,
        *,
        release_id: str,
        source_digest: str,
        recipe_digest: str,
        schema_digest: str,
        kind: str,
        target_meanings: Mapping[tuple[int, str, str], Any],
        check_active: Callable[[], None] = lambda: None,
    ) -> str:
        from duckdb import col

        from corpus_structure.analytics import connection

        self._verify_stream_inventory(schema_digest, check_active=check_active)
        logical = LogicalIdentity(schema_digest, release_id, source_digest)

        def batches():
            pending = []
            size = 0
            for family, key, fields in self._identity_fields(kind, recipe_digest, target_meanings):
                check_active()
                encoded = record_frame(schema_digest, family, key, fields)
                size += len(encoded)
                pending.append({"family": family, "record_key": key, "frame": encoded})
                if len(pending) >= 512 or size >= 4 * 1024 * 1024:
                    yield pa.RecordBatch.from_pylist(pending, schema=_FRAME_SCHEMA)
                    pending.clear()
                    size = 0
            if pending:
                yield pa.RecordBatch.from_pylist(pending, schema=_FRAME_SCHEMA)

        with (
            connection() as analytical,
            pa.RecordBatchReader.from_batches(_FRAME_SCHEMA, batches()) as source,
        ):
            self.check_artifact_coordinates(analytical)
            ordered = analytical.from_arrow(source).sort(
                col("family").asc().nulls_last(), col("record_key").asc().nulls_last()
            )
            with ordered.to_arrow_reader(batch_size=512) as output:
                for batch in output:
                    check_active()
                    for family, key, frame in zip(
                        batch.column("family").to_pylist(),
                        batch.column("record_key").to_pylist(),
                        batch.column("frame").to_pylist(),
                        strict=True,
                    ):
                        logical.add_encoded_record(family, key, frame)
        return logical.pin().logical_digest

    def certify(self, document: Any, projection: Path, **options) -> PdfProducerCertification:
        from corpus_structure.ingest.pdf_streaming import SealedPdfNative

        sealed = document if isinstance(document, SealedPdfNative) else SealedPdfNative(document)
        return sealed.certify(self, projection, **options)

    def _certify_native_values(
        self,
        actual: Mapping[str, Any],
        projection: Path,
        *,
        release_id: str,
        source_digest: str,
        recipe_digest: str,
        schema_digest: str,
        kind: Literal["native", "integrated"],
        lowering_identity: str,
        target_meanings: Mapping[tuple[int, str, str], Any],
        check_active: Callable[[], None] = lambda: None,
    ) -> PdfProducerCertification:
        from .pdf_access_projection import project_pdf_access, write_pdf_access_projection

        self._verify_stream_inventory(schema_digest, check_active=check_active)
        items, regions = project_pdf_access(actual)
        self.validate(actual, items=items, regions=regions)
        write_pdf_access_projection(actual, projection, items=items)
        digest = self.logical_digest(
            release_id=release_id,
            source_digest=source_digest,
            recipe_digest=recipe_digest,
            schema_digest=schema_digest,
            kind=kind,
            target_meanings=target_meanings,
            check_active=check_active,
        )
        return PdfProducerCertification(
            lowering_identity,
            kind,
            digest,
            sha256(canonical_bytes(actual)).hexdigest(),
            self.stream_inventory_digest,
            source_digest,
            recipe_digest,
            schema_digest,
        )


def write_pdf_companion_sets(
    root: Path,
    companions: Mapping[str, Iterable[Mapping[str, Any]]],
    *,
    payload_family,
    check_active: Callable[[], None],
    on_replay=None,
    lowering: CapturedPdfLowering | None = None,
):
    """Prepare bounded immutable sets once; certify and later COPY the same files."""
    from corpus_structure.ingest.pdf_stream_types import PdfPreparedCompanionSet
    from corpus_structure.ingest.pdf_streaming import _ref

    from .pdf_companion_encoding import (
        COMPANION_BATCH_BYTES,
        COMPANION_BATCH_ROWS,
        PdfCompanionRecord,
        prepare_pdf_companion_batches,
    )
    from .pdf_payloads import EncodedPagePayload

    root.mkdir(parents=True, exist_ok=False)
    sets = []
    for family, records in companions.items():
        pending, size, start = [], 0, 0

        def flush(family=family, pending=pending):
            nonlocal size, start
            if not pending:
                return
            replays = []

            def write(name, batch):
                path = root / f"{len(sets):08}-{len(replays):08}-{name}.arrow"
                with (
                    pa.OSFile(str(path), "wb") as sink,
                    pa.ipc.new_file(sink, batch.schema) as writer,
                ):
                    writer.write_batch(batch)
                import os

                with path.open("rb") as source:
                    os.fsync(source.fileno())
                replay = _ref(path, "prepared_companion:" + name, batch.num_rows)
                if on_replay is not None:
                    on_replay(replay)
                replays.append(replay)

            prepare_pdf_companion_batches(
                family,
                pending,
                on_batch=write,
                payload_family=payload_family,
                lowering=lowering,
                start_ordinal=start,
                check_active=check_active,
            )
            sets.append(
                PdfPreparedCompanionSet(family, f"companion:{family}:rows:{start}", tuple(replays))
            )
            start += len(pending)
            pending.clear()
            size = 0

        for row in records:
            check_active()
            value = row.get("value")
            length = (
                row.encoded_length
                if isinstance(row, PdfCompanionRecord)
                else (
                    len(value.content)
                    + len(
                        canonical_bytes({key: item for key, item in row.items() if key != "value"})
                    )
                    if isinstance(value, EncodedPagePayload)
                    else len(canonical_bytes(dict(row)))
                )
            )
            if pending and (
                len(pending) >= COMPANION_BATCH_ROWS or size + length > COMPANION_BATCH_BYTES
            ):
                flush()
            pending.append(row)
            size += length
        flush()
    return tuple(sets)


def certify_native_stream(streamed, request, replays, *, on_replay):
    """Certify the native capture while its actual complete document is alive."""
    from corpus_structure.ingest.pdf_record_product import native_occurrence_rows
    from corpus_structure.ingest.pdf_streaming import _atomic_bytes, _ref

    contract = json.loads(request.validation_contract)
    lowering = CapturedPdfLowering.from_document(contract.get("lowering"))
    if contract["publication_kind"] != "native":
        raise ValueError("native capture certification requires the native publication kind")

    def metadata():
        for number in sorted(streamed.spool.candidates):
            yield {
                "kind": "inline_candidate_pages",
                "ordinal": number,
                "value": streamed.spool.candidate_source.encoded(number),
            }
        yield {
            "kind": "runtime_report",
            "ordinal": 0,
            "value": {"effective_options": streamed.effective_options.decode()},
        }
        for ordinal, outcome in enumerate(
            streamed.formula_outcomes, start=1 + len(streamed.errors)
        ):
            value = {"pointer": outcome.item_ref, "outcome": outcome.outcome}
            if outcome.error:
                value["error"] = outcome.error
            yield {"kind": "formula_outcomes", "ordinal": ordinal, "value": value}

    companions = {
        "native_metadata": metadata(),
        "occurrence": native_occurrence_rows(
            streamed.sealed.validate_under(lowering.callback_policy())
        ),
        "health": (
            {
                "conversion": streamed.conversion_status,
                "display_coverage": "unknown",
                "inline_coverage": "unknown",
                "cell_coverage": "unknown",
                "issues": list(streamed.errors),
                "source_scope": "whole_document",
            },
        ),
    }
    sets = write_pdf_companion_sets(
        request.record_root.with_name(request.record_root.name + "-certified-companions"),
        companions,
        payload_family=streamed.spool.payload_family,
        lowering=lowering,
        check_active=streamed.spool.active,
        on_replay=on_replay,
    )
    projection = request.record_root / "producer-access.jsonl"
    payloads = PdfProducerPayloads(contract)
    try:
        payloads.add_replays(replays, check_active=streamed.spool.active)
        payloads.add_companion_replays(sets, check_active=streamed.spool.active)
        certification = payloads.certify(
            streamed.sealed,
            projection,
            release_id=request.release_id,
            source_digest=request.source.digest,
            recipe_digest=sha256(streamed.recipe).hexdigest(),
            schema_digest=contract["schema_digest"],
            kind="native",
            lowering_identity=request.lowering_identity,
            target_meanings={},
        )
    finally:
        payloads.close()
    import os

    with projection.open("rb") as source:
        os.fsync(source.fileno())
    access = _ref(projection, "producer_access")
    on_replay(access)
    certificate = _atomic_bytes(
        request.record_root / "producer-certification.json",
        certification.to_bytes(),
        "producer_certification",
    )
    on_replay(certificate)
    return sets, certificate, access


def write_retained_pdf_replays(root: Path, retained, *, lowering, check_active, on_replay):
    """Own exact retained export bytes before they participate in certification."""
    import gzip
    import os

    from corpus_structure.ingest.pdf_streaming import _ref

    from .pdf_record_identity import IdentityFold, emit_parts

    root.mkdir(parents=True, exist_ok=False)
    common = {"stream_id": "retained/envelope"}
    replays = []

    def write(family, rows):
        batch = pa.RecordBatch.from_pylist(
            rows, schema=replay_schema(lowering.schema("stage:" + family))
        )
        path = root / f"{len(replays):08}-{family}.arrow"
        with pa.OSFile(str(path), "wb") as sink, pa.ipc.new_file(sink, batch.schema) as writer:
            writer.write_batch(batch)
        with path.open("rb") as source:
            os.fsync(source.fileno())
        replay = _ref(path, family, batch.num_rows)
        on_replay(replay)
        replays.append(replay)

    digest, fold = sha256(), IdentityFold("bytes")
    opener = gzip.open if retained.compression == "gzip" else open

    def parts(source):
        def chunks():
            while block := source.read(65536):
                check_active()
                yield block

        yield from emit_parts(common["stream_id"], chunks())

    # The repeatable retained source already owns its backing file. Determine
    # and authenticate the descriptor before any part transfer, without another
    # full uncompressed spool. Certification checks the second pass's bytes.
    with opener(retained.path, "rb") as source:
        for part in parts(source):
            digest.update(part.body)
            fold.add(part.body)
    if digest.hexdigest() != retained.serialization_sha256:
        raise ValueError("retained bytes changed during producer preparation")
    write(
        "artifact_stream",
        [
            {
                **common,
                "byte_length": fold.byte_length,
                "byte_root": fold.digest().hex(),
                "serialization_sha256": digest.hexdigest(),
                "encoding_profile": "retained-pdf-envelope-json-v1",
            }
        ],
    )
    with opener(retained.path, "rb") as source:
        pending = []
        for part in parts(source):
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
            if len(pending) == 64:
                write("artifact_part", pending)
                pending.clear()
        if pending:
            write("artifact_part", pending)
    return tuple(replays)
