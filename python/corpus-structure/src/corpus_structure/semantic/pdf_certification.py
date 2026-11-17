"""Producer certification over actual output and exact prepared record bytes.

The existing disk-backed payload validator owns payload interiors and integrated
meaning. This owner supplies its producer-side bytes; it never reads staged rows
or reconstructs the producer's native document.
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
from .pdf_payload_validation import FrozenPayloadStore
from .pdf_record_identity import (
    ABSENT,
    IdentityFold,
    LogicalIdentity,
    ScalarDescriptor,
    byte_root,
    record_frame,
    structured_payload_scalar,
)


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
    from .pdf_payload_validation import metadata_classes
    from .pdf_payloads import prepare_payload_family, schema_dump

    family = prepare_payload_family(context)
    contract = {
        "schemas": {
            key: context.boundary.json_schema(cls) for key, cls in metadata_classes().items()
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


class PdfProducerPayloads(FrozenPayloadStore):
    """Exact prepared producer rows, with disk ordering for the existing frame fold."""

    def __init__(self, path: Path, validation_contract: Mapping[str, Any]):
        super().__init__(path)
        self.db.executescript("""
        CREATE TABLE native_entry(family TEXT, key TEXT, body TEXT, PRIMARY KEY(family,key));
        CREATE TABLE identity_frame(family TEXT, key TEXT, frame BLOB, PRIMARY KEY(family,key));
        """)
        self.add("validation_contract", dict(validation_contract))

    def add_batch(self, family: str, batch: pa.RecordBatch) -> None:
        for row in batch.to_pylist():
            if family in {"header", "native", "membership"}:
                key = (
                    row["root_id"]
                    if family == "header"
                    else row["record_id"]
                    if family == "native"
                    else json.dumps([row["parent_id"], row["field_name"], row["ordinal"]])
                )
                self.db.execute(
                    "INSERT INTO native_entry VALUES(?,?,?)", (family, key, json.dumps(row))
                )
            elif family in {"artifact_stream", "artifact_part", "companion", "companion_field"}:
                if family == "artifact_part":
                    row["body"] = "\\x" + row["body"].hex()
                elif family == "companion" and isinstance(row["body"], str):
                    row["body"] = json.loads(row["body"])
                self.add(family, row)

    def add_replays(self, replays, *, check_active=lambda: None) -> None:
        from .pdf_staging import stage_schema

        for replay in replays:
            check_active()
            replay.verify()
            with pa.memory_map(str(replay.path), "r") as source:
                reader = pa.ipc.open_file(source)
                if not reader.schema.equals(stage_schema(replay.family), check_metadata=True):
                    raise ValueError("producer native record replay schema differs")
                for index in range(reader.num_record_batches):
                    self.add_batch(replay.family, reader.get_batch(index))

    def add_companion_replays(self, sets, *, check_active=lambda: None) -> None:
        from .pdf_publication import COMPANION_STAGE_TARGETS
        from .pdf_record_model import record_arrow_schema

        families = {
            "companion": "companion",
            "field": "companion_field",
            "stream": "artifact_stream",
            "part": "artifact_part",
        }
        for prepared in sets:
            for replay in prepared.replays:
                check_active()
                replay.verify()
                target = replay.family.removeprefix("prepared_companion:")
                with pa.memory_map(str(replay.path), "r") as source:
                    reader = pa.ipc.open_file(source)
                    if not reader.schema.equals(
                        record_arrow_schema(COMPANION_STAGE_TARGETS[target]), check_metadata=True
                    ):
                        raise ValueError("producer companion replay schema differs")
                    for index in range(reader.num_record_batches):
                        self.add_batch(families[target], reader.get_batch(index))

    def _descriptor(self, stream: str) -> ScalarDescriptor:
        raw = self.db.execute(
            "SELECT body FROM entry WHERE family='artifact_stream' AND key=?", (stream,)
        ).fetchone()
        if raw is None:
            raise ValueError("producer scalar has no exact stream descriptor")
        descriptor = json.loads(raw[0])
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
        raw = self.db.execute(
            "SELECT body FROM entry WHERE family='companion_field' AND key=?",
            (json.dumps([row["family"], row["local_id"], name]),),
        ).fetchone()
        if raw is not None:
            if (
                row["family"] == "native_metadata"
                and row["body"]["kind"] == "inline_candidate_pages"
            ):
                return structured_payload_scalar(row["body"]["payload_logical_digest"])
            return self._descriptor(json.loads(raw[0])["stream_id"])
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

    def logical_digest(
        self,
        *,
        release_id: str,
        source_digest: str,
        recipe_digest: str,
        schema_digest: str,
        kind: str,
        target_meanings: Mapping[tuple[int, str, str], Any],
    ) -> str:
        from .pdf_records import NativeRow, native_record_identity_fields

        self.db.execute("DELETE FROM identity_frame")

        def add(family, key, fields):
            encoded = record_frame(schema_digest, family, key, fields)
            self.db.execute("INSERT INTO identity_frame VALUES(?,?,?)", (family, key, encoded))

        # Validate every actual stream, including shared and unreferenced streams.
        streams = IdentityFold("pdf-producer-streams-v1")
        for (raw,) in self.db.execute(
            "SELECT body FROM entry WHERE family='artifact_stream' ORDER BY key COLLATE BINARY"
        ):
            descriptor = json.loads(raw)
            digest = sha256()

            def chunks(descriptor=descriptor, digest=digest):
                for body in self.parts(descriptor["stream_id"]):
                    digest.update(body)
                    yield body

            length, root = byte_root(chunks())
            if (length, root.hex()) != (descriptor["byte_length"], descriptor["byte_root"]) or (
                descriptor.get("serialization_sha256") is not None
                and descriptor["serialization_sha256"] != digest.hexdigest()
            ):
                raise ValueError("producer actual bytes differ from their stream descriptor")
            streams.add(
                record_frame(
                    schema_digest,
                    "producer-stream",
                    descriptor["stream_id"],
                    (
                        ("byte_length", length),
                        ("byte_root", root.hex()),
                        ("encoding_profile", descriptor["encoding_profile"]),
                        ("serialization_sha256", descriptor.get("serialization_sha256")),
                    ),
                )
            )
        self.stream_inventory_digest = streams.digest().hex()
        for family, raw in self.db.execute("SELECT family,body FROM native_entry"):
            row = {key: value for key, value in json.loads(raw).items() if value is not None}
            for name in ("scalars_json", "structure_json", "scalar_json"):
                if name in row and not isinstance(row[name], str):
                    row[name] = json.dumps(row[name])
            result = native_record_identity_fields(
                NativeRow("document" if family == "header" else family, row),
                scalar_descriptor=self._descriptor,
            )
            if result is not None:
                add(*result)
        inputs = {row["local_id"]: row["body"] for row in self.companions("input")}
        for (raw,) in self.db.execute("SELECT body FROM entry WHERE family='companion'"):
            row = json.loads(raw)
            family, body = row["family"], dict(row["body"])
            if family == "native_metadata":
                for key in (
                    ("value", "payload_codec", "payload_schema_digest")
                    if body["kind"] == "inline_candidate_pages"
                    else ("value",)
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
            add("companion/" + family, row["local_id"], fields)
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
                    add(
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
        add("publication", "root", (("kind", kind), ("recipe_digest", recipe_digest)))
        logical = LogicalIdentity(schema_digest, release_id, source_digest)
        for family, key, encoded in self.db.execute(
            "SELECT family,key,frame FROM identity_frame ORDER BY family COLLATE BINARY,key COLLATE BINARY"
        ):
            logical.add_encoded_record(family, key, encoded)
        return logical.pin().logical_digest

    def certify(
        self,
        document: Any,
        projection: Path,
        *,
        release_id: str,
        source_digest: str,
        recipe_digest: str,
        schema_digest: str,
        kind: Literal["native", "integrated"],
        lowering_identity: str,
        target_meanings: Mapping[tuple[int, str, str], Any],
    ) -> PdfProducerCertification:
        from corpus_structure.ingest.pdf_streaming import _json_view

        from .pdf_publication import write_pdf_access_projection
        from .pdf_records import validate_native_callbacks

        actual = json.loads(json.dumps(_json_view(document), allow_nan=False, ensure_ascii=False))
        validate_native_callbacks(actual)
        write_pdf_access_projection(actual, projection)
        self.validate(actual, projection)
        digest = self.logical_digest(
            release_id=release_id,
            source_digest=source_digest,
            recipe_digest=recipe_digest,
            schema_digest=schema_digest,
            kind=kind,
            target_meanings=target_meanings,
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
    build,
    companions: Mapping[str, Iterable[Mapping[str, Any]]],
    *,
    payload_family,
    check_active: Callable[[], None],
    on_replay=None,
):
    """Prepare bounded immutable sets once; certify and later COPY the same files."""
    from corpus_structure.ingest.pdf_stream_types import PdfPreparedCompanionSet
    from corpus_structure.ingest.pdf_streaming import _ref

    from .pdf_payloads import EncodedPagePayload
    from .pdf_publication import (
        COMPANION_BATCH_BYTES,
        COMPANION_BATCH_ROWS,
        PdfCompanionRecord,
        prepare_pdf_companion_batches,
    )

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
                build,
                family,
                pending,
                on_batch=write,
                payload_family=payload_family,
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
    from corpus_structure.ingest.pdf_candidate_source import encoded_replay
    from corpus_structure.ingest.pdf_record_product import native_occurrence_rows
    from corpus_structure.ingest.pdf_streaming import _atomic_bytes, _ref

    from .pdf_publication import PdfCompanionEncodingBasis

    contract = json.loads(request.validation_contract)
    if contract["publication_kind"] != "native":
        raise ValueError("native capture certification requires the native publication kind")
    build = PdfCompanionEncodingBasis(request.build_id, request.release_id)

    def metadata():
        for number in sorted(streamed.spool.candidates):
            yield {
                "kind": "inline_candidate_pages",
                "ordinal": number,
                "value": encoded_replay(
                    streamed.spool.candidates[number], streamed.spool.payload_family
                ),
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
        "occurrence": native_occurrence_rows(streamed.document),
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
        build,
        companions,
        payload_family=streamed.spool.payload_family,
        check_active=streamed.spool.active,
        on_replay=on_replay,
    )
    projection = request.record_root / "producer-access.jsonl"
    payloads = PdfProducerPayloads(request.record_root / "producer-payloads.sqlite", contract)
    try:
        payloads.add_replays(replays, check_active=streamed.spool.active)
        payloads.add_companion_replays(sets, check_active=streamed.spool.active)
        certification = payloads.certify(
            streamed.document,
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


def write_retained_pdf_replays(root: Path, build, retained, *, check_active, on_replay):
    """Own exact retained export bytes before they participate in certification."""
    import gzip
    import os

    from corpus_structure.ingest.pdf_streaming import _ref

    from .pdf_record_identity import IdentityFold, emit_parts
    from .pdf_staging import stage_schema

    root.mkdir(parents=True, exist_ok=False)
    common = {
        "product_id": build.build_id,
        "revision_id": build.build_id,
        "stream_id": "retained/envelope",
    }
    replays = []

    def write(family, rows):
        batch = pa.RecordBatch.from_pylist(rows, schema=stage_schema(family))
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
