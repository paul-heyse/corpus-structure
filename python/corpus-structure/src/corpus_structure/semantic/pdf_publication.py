"""Model-governed frozen PDF preparation, native validation and publication.

SQLAlchemy owns sessions and transactions. A finite DB-free child receives an
owned capture of the actual frozen union; its callback result does not replace
PostgreSQL's independent custody, relational and exact-byte enforcement.
"""

from __future__ import annotations

import json
import multiprocessing
import tempfile
from collections.abc import Callable, Generator, Iterable, Mapping, Sequence
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import contextmanager
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

import pyarrow as pa
from sqlalchemy import Connection, Engine

from corpus_structure.core.db.lifetime import BorrowerCancellation
from corpus_structure.core.db.store import (
    DatabaseOperationFailure,
    DatabasePhase,
    EffectKnowledge,
    classify_error,
    record_operation_failure,
)

from . import _operation_calls as calls
from ._operation_ids import ContentDigest, ProductKey
from .pdf_staging import PdfBuildRef

COMPANION_BATCH_ROWS = 64
COMPANION_BATCH_BYTES = 4 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class FrozenPdfBuildRef:
    build: PdfBuildRef
    frozen_digest: str
    kind: str


@dataclass(frozen=True, slots=True)
class PdfValidationOutcome:
    frozen_digest: str
    logical_digest: str
    contract_digest: str


@dataclass(frozen=True, slots=True)
class PublishedPdfDocumentRef:
    build_id: str
    task_id: int
    product_key: str
    logical_digest: str
    release_id: str
    source_digest: str
    schema_digest: str
    recipe_digest: str
    frozen_digest: str
    kind: str

    @property
    def product_id(self) -> str:
        return self.build_id

    @property
    def revision_id(self) -> str:
        return self.build_id

    @property
    def content_digest(self) -> str:
        """Qualified record identity, never historical canonical-envelope SHA."""
        return self.logical_digest



@dataclass(frozen=True, slots=True)
class PdfExecutionReceipt:
    """Actual sealed publisher, distinct from a later completion's admitting claim."""

    publication: PublishedPdfDocumentRef
    publisher_attempt: int
    publisher_holder: str

    def __post_init__(self) -> None:
        if (type(self.publisher_attempt) is not int or self.publisher_attempt < 1
            or type(self.publisher_holder) is not str or not self.publisher_holder):
            raise ValueError("PDF execution receipt requires its actual sealed publisher fence")



def _published(row: Mapping[str, Any]) -> PublishedPdfDocumentRef:
    return PublishedPdfDocumentRef(
        **{key: row[key] for key in PublishedPdfDocumentRef.__dataclass_fields__}
    )


def published_pdf_revision(
    conn: Connection, task_id: int, product_key: str, logical_digest: str
) -> PublishedPdfDocumentRef | None:
    row = calls.read_pdf_published_revision(
        conn,
        task_id=calls.TaskId(task_id),
        product_key=ProductKey(product_key),
        logical_digest=ContentDigest(logical_digest),
    )
    return None if row is None else _published(row.model_dump(mode="python"))


def freeze_pdf_build(conn: Connection, build: PdfBuildRef, *, kind: str) -> FrozenPdfBuildRef:
    parameters = calls._freeze_pdf_buildRequest.model_validate(
        {
            "build_id": build.build_id,
            "task_id": build.task_id,
            "attempt": build.attempt,
            "holder": build.holder,
            "kind": kind,
        },
        strict=True,
    )
    digest = calls.freeze_pdf_build(
        conn,
        build_id=parameters.build_id,
        task_id=parameters.task_id,
        attempt=parameters.attempt,
        holder=parameters.holder,
        kind=parameters.kind,
    )
    return FrozenPdfBuildRef(build, digest, kind)


def prepare_pdf_build(conn: Connection, frozen: FrozenPdfBuildRef) -> None:
    calls.prepare_pdf_build(
        conn,
        build_id=frozen.build.build_id,
        task_id=calls.TaskId(frozen.build.task_id),
        attempt=calls.TaskAttempt(frozen.build.attempt),
        holder=frozen.build.holder,
        frozen_digest=frozen.frozen_digest,
    )


def adopt_pdf_companion_batch(
    conn: Connection,
    build: PdfBuildRef,
    family: str,
    records: Iterable[Mapping[str, Any]],
    replay_key: str,
    *,
    start_ordinal: int = 0,
    cancellation: BorrowerCancellation | None = None,
) -> None:
    """Typed queryable bodies with fixed value fields in bounded segmented uploads."""
    from hashlib import sha256

    from .identity import canonical_bytes
    from .pdf_record_identity import byte_root, emit_parts
    from .pdf_staging import adopt_pdf_batch, stage_schema

    pending = []
    streams = []
    parts = []
    byte_count = 0
    chunk = 0

    def flush() -> None:
        nonlocal pending, streams, parts, byte_count, chunk
        if cancellation is not None:
            cancellation.check_active()
        if streams:
            adopt_pdf_batch(
                conn,
                build,
                f"{replay_key}:fields:{chunk}",
                {
                    "artifact_stream": (
                        pa.RecordBatch.from_pylist(streams, schema=stage_schema("artifact_stream")),
                    ),
                    "artifact_part": (
                        pa.RecordBatch.from_pylist(parts, schema=stage_schema("artifact_part")),
                    ),
                },
                cancellation=cancellation,
            )
        from .pdf_records import _finite_json

        parameters = []
        for ordinal, local, body, fields in pending:
            _finite_json(body, "#/companion/body")
            parameters.append(
                calls.AdoptPdfCompanionParameters.model_validate(
                    {
                        "build_id": build.build_id,
                        "task_id": build.task_id,
                        "attempt": build.attempt,
                        "holder": build.holder,
                        "family": family,
                        "local_id": local,
                        "body": body,
                        "fields": fields,
                        "replay_key": f"{replay_key}:{ordinal}",
                        "ordinal": ordinal,
                    },
                    strict=True,
                )
            )
        if cancellation is not None:
            cancellation.check_active()
        calls.adopt_pdf_companion_batch(conn, requests=parameters)
        pending = []
        streams = []
        parts = []
        byte_count = 0
        chunk += 1

    codec = None
    for ordinal, record in enumerate(records, start=start_ordinal):
        if cancellation is not None:
            cancellation.check_active()
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
            if body["kind"] == "formula_outcomes" and isinstance(value, Mapping):
                body["outcome"] = value.get("outcome")
                body["has_diagnostic"] = "error" in value
            if body["kind"] == "inline_candidate_pages":
                from .pdf_contracts import pdf_context_for_task
                from .pdf_payloads import PROFILE, EncodedPagePayload, prepare_payload_family

                if codec is None:
                    codec = prepare_payload_family(pdf_context_for_task(conn, build.task_id))
                if isinstance(value, EncodedPagePayload):
                    batch = codec.read_batch(
                        value.content,
                        schema_digest=value.schema_digest,
                        logical_digest=value.logical_digest,
                    )
                    if batch.column("page_no")[0].as_py() != value.page_no:
                        raise ValueError("encoded page locator differs from IPC")
                    encoded = value
                else:
                    encoded = EncodedPagePayload(
                        codec.encode(value),
                        codec.schema_digest,
                        codec.logical_digest(value),
                        value["page_no"],
                    )
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
        if family == "relation" and len(canonical_bytes(body)) > 32768:
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
        size = sum(len(payload) for _, payload, _ in payloads)
        if pending and (
            len(pending) >= COMPANION_BATCH_ROWS or byte_count + size > COMPANION_BATCH_BYTES
        ):
            flush()
        fields = {}
        for field, payload, profile in payloads:
            stream = (
                "companion-field:" + sha256(canonical_bytes([family, local, field])).hexdigest()
            )
            common = dict(product_id=build.build_id, revision_id=build.build_id, stream_id=stream)
            length, root = byte_root((payload,))
            # A single large field still travels through bounded COPY batches.
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
                    adopt_pdf_batch(
                        conn,
                        build,
                        stream + f":parts:{part.ordinal // 64}",
                        {
                            "artifact_part": (
                                pa.RecordBatch.from_pylist(
                                    field_parts, schema=stage_schema("artifact_part")
                                ),
                            )
                        },
                        cancellation=cancellation,
                    )
                    field_parts = []
            parts.extend(field_parts)
            streams.append(
                {
                    **common,
                    "byte_length": length,
                    "byte_root": root.hex(),
                    "serialization_sha256": None,
                    "encoding_profile": profile,
                }
            )
            fields[field] = stream
        pending.append((ordinal, local, body, fields))
        byte_count += size
        if byte_count > 4 * 1024 * 1024:
            flush()
    if pending:
        flush()


_CAPTURE_SCHEMA = pa.schema(
    [
        pa.field("family", pa.string(), nullable=False),
        pa.field("body", pa.large_string(), nullable=False),
    ]
)
_FAMILIES = (
    "header",
    "native",
    "membership",
    "artifact_stream",
    "artifact_part",
    "companion",
    "companion_field",
)


def _native_validation_streams(family: str, row: Mapping[str, Any]) -> Iterable[str]:
    """Actual scalar dependencies of the callback's reconstruction and metadata view."""
    if family == "native":
        structure = row["structure_json"]
        for descriptor in structure["fields"].values():
            if descriptor["kind"] == "parts":
                yield descriptor["stream_id"]
        if "extensions" in structure:
            yield structure["extensions"]["stream_id"]
    elif family == "membership":
        if row["value_kind"] == "parts":
            yield row["stream_id"]
        if row.get("member_key_stream_id") is not None:
            yield row["member_key_stream_id"]
    elif family == "companion_field":
        yield row["stream_id"]


def _native_validation_child(capture: str, projection: str, result: Any) -> None:
    """One explicitly materialized native oracle, no database handles or credentials."""
    store = None
    outcome: tuple[bool, str | None] = (True, None)
    try:
        from .pdf_payload_validation import FrozenPayloadStore
        from .pdf_records import reconstruct_native_document, validate_native_callbacks

        store = FrozenPayloadStore(Path(projection).with_suffix(".sqlite"))
        rows: dict[str, list[dict[str, Any]]] = {name: [] for name in _FAMILIES}
        with pa.memory_map(capture, "r") as source:
            reader = pa.ipc.open_file(source)
            for index in range(reader.num_record_batches):
                batch = reader.get_batch(index)
                for family, body in zip(
                    batch.column("family").to_pylist(),
                    batch.column("body").to_pylist(),
                    strict=True,
                ):
                    value = json.loads(body)
                    store.add(family, value)
                    if family in {"header", "native", "membership"}:
                        rows[family].append(value)
        natives = {r["record_id"]: r for r in rows["native"]}
        members: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for row in rows["membership"]:
            members.setdefault((row["parent_id"], row["field_name"]), []).append(row)
        for values in members.values():
            values.sort(key=lambda r: r["ordinal"])

        class Reader:
            def record(self, record_id):
                return natives[record_id]

            def members(self, parent_id, field_name):
                yield from members.get((parent_id, field_name), ())

            def scalar(self, stream_id):
                yield from store.parts(stream_id)

        profiles = {}
        for (raw,) in store.db.execute("SELECT body FROM entry WHERE family='artifact_stream'"):
            descriptor = json.loads(raw)
            profiles[descriptor["stream_id"]] = descriptor["encoding_profile"]
        document = reconstruct_native_document(
            Reader(), rows["header"][0]["root_id"], scalar_profiles=profiles, json_fields="decoded"
        )
        validate_native_callbacks(document)
        # Source access is a derived, per-item projection, never the content authority.
        nodes = {}
        for key in ("body", "furniture"):
            node = document.get(key)
            if node:
                nodes[node["self_ref"]] = node
        for key in ("groups", "texts", "pictures", "tables", "key_value_items", "form_items"):
            for node in document.get(key, []):
                nodes[node["self_ref"]] = node
        order = []
        seen = set()

        def walk(pointer):
            if pointer in seen:
                raise ValueError("native containment repeats an item")
            seen.add(pointer)
            order.append(pointer)
            for child in nodes[pointer].get("children", []):
                walk(child["$ref"])

        walk(document["body"]["self_ref"])
        walk(document["furniture"]["self_ref"])
        order.extend(sorted(set(nodes) - seen))
        sections = {p for p, n in nodes.items() if n.get("label") in ("section", "chapter")}
        owners: dict[str, str | None] = {}

        def section_owner(pointer: str) -> str | None:
            path = []
            visited = set()
            current = pointer
            while current not in owners:
                if current in visited:
                    raise ValueError("cyclic source section ancestry")
                visited.add(current)
                path.append(current)
                if current in sections:
                    owner = current
                    break
                parent = nodes[current].get("parent", {}).get("$ref")
                if parent is None:
                    owner = None
                    break
                current = parent
            else:
                owner = owners[current]
            for node_pointer in path:
                owners[node_pointer] = owner
            return owner

        # Organized section groups use section/chapter labels; keep the native labels.
        with Path(projection).open("w") as out:
            for ordinal, pointer in enumerate(order):
                node = nodes[pointer]
                parent = node.get("parent", {}).get("$ref")
                row = dict(
                    pointer=pointer,
                    ordinal=ordinal,
                    label=node.get("label", "unspecified"),
                    parent_pointer=parent,
                    section_pointer=section_owner(pointer),
                    content_layer=node.get("content_layer", "body"),
                    text=node.get("text"),
                    native_json=node,
                )
                out.write(
                    json.dumps(
                        {"family": "access", "body": row}, ensure_ascii=False, allow_nan=False
                    )
                    + "\n"
                )
                for index, prov in enumerate(node.get("prov", [])):
                    page = document["pages"][str(prov["page_no"])]
                    box = prov["bbox"]
                    region = dict(
                        pointer=pointer,
                        region_index=index,
                        page_no=prov["page_no"],
                        page_width=page["size"]["width"],
                        page_height=page["size"]["height"],
                        left=box["l"],
                        top=box["t"],
                        right=box["r"],
                        bottom=box["b"],
                        origin="top_left" if box["coord_origin"] == "TOPLEFT" else "bottom_left",
                    )
                    out.write(json.dumps({"family": "region", "body": region}) + "\n")
        store.validate(document, Path(projection))
    except BaseException as error:
        outcome = (False, f"{type(error).__name__}: {error}")
    finally:
        try:
            if store is not None:
                store.close()
        except BaseException as cleanup_error:
            cleanup_detail = (
                f"native validation cleanup failed: {type(cleanup_error).__name__}: {cleanup_error}"
            )
            outcome = (False, cleanup_detail if outcome[0] else f"{outcome[1]}; {cleanup_detail}")
        try:
            # Native success acknowledges completed owned store/projection cleanup. The
            # parent also requires terminal process exit, including pipe/interpreter teardown.
            result.send(outcome)
        finally:
            result.close()


def _run_native_validation(
    capture: Path, projection: Path, check_active: Callable[[], None]
) -> None:
    """Settle this DB-free child before returning, including failed/cancelled validation."""
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe(duplex=False)
    process = context.Process(
        target=_native_validation_child, args=(str(capture), str(projection), child)
    )
    primary: BaseException | None = None
    errors: list[BaseException] = []

    def cleanup(action):
        try:
            action()
        except BaseException as error:
            errors.append(error)

    try:
        check_active()
        process.start()
        child.close()
        while not parent.poll(0.2):
            check_active()
            if not process.is_alive():
                raise RuntimeError("native validation child exited without outcome")
        passed, error = parent.recv()
        check_active()
        while process.is_alive():
            process.join(0.2)
            check_active()
        process.join()
        check_active()
        if not passed:
            refusal = ValueError(error)
            if process.exitcode != 0:
                refusal.add_note(f"native validation child exited with status {process.exitcode}")
            raise refusal
        if process.exitcode != 0:
            raise RuntimeError(f"native validation child exited with status {process.exitcode}")
    except BaseException as error:
        primary = error
        raise
    finally:
        # Each independent handle is closed even if another cleanup fails. A live
        # owned process is terminated/killed and reaped, never silently detached.
        cleanup(child.close)
        if process.pid is not None:
            if process.is_alive():
                cleanup(process.terminate)
                cleanup(lambda: process.join(5))
            if process.is_alive():
                cleanup(process.kill)
            cleanup(process.join)
        cleanup(parent.close)
        cleanup(process.close)
        if errors:
            if primary is not None:
                for error in errors:
                    primary.add_note("native validation cleanup failed: " + repr(error))
            else:
                raise BaseExceptionGroup("native validation cleanup failed", errors)


@contextmanager
def _validation_transaction(
    engine: Engine,
    frozen: FrozenPdfBuildRef,
    cancellation: BorrowerCancellation,
    check_active: Callable[[], None],
) -> Generator[Connection]:
    """Own a validation checkout, settlement and its precise failure context."""
    phase, effects = DatabasePhase.ACQUIRING, EffectKnowledge.NONE
    broken = False
    try:
        check_active()
        with engine.connect() as conn, cancellation.borrow(conn):
            driver = conn.connection.driver_connection
            transaction = conn.begin()
            try:
                phase, effects = DatabasePhase.EXECUTING, EffectKnowledge.UNCERTAIN
                yield conn
                check_active()
                phase = DatabasePhase.COMMITTING
                transaction.commit()
                effects = EffectKnowledge.COMMITTED
            except BaseException as error:
                broken = conn.invalidated or bool(getattr(driver, "broken", False))
                try:
                    transaction.rollback()
                    if not broken and phase != DatabasePhase.COMMITTING:
                        effects = EffectKnowledge.ROLLED_BACK
                except BaseException as cleanup:
                    error.add_note("PDF validation rollback failed: " + repr(cleanup))
                    try:
                        conn.invalidate()
                    except BaseException as invalidation:
                        error.add_note("PDF validation invalidation failed: " + repr(invalidation))
                raise
    except BaseException as error:
        record_operation_failure(
            error,
            DatabaseOperationFailure(
                classify_error(
                    error,
                    phase=phase,
                    effects=effects,
                    broken=broken,
                    cancellation_requested=cancellation.requested,
                ),
                frozen.build.build_id,
                "inspect_frozen_build",
                frozen.build.release_id,
            ),
        )
        raise


def validate_pdf_build(
    engine: Engine,
    frozen: FrozenPdfBuildRef,
    check_active: Callable[[], None] | None = None,
    *,
    cancellation: BorrowerCancellation | None = None,
) -> PdfValidationOutcome:
    authority_check = check_active or (lambda: None)
    cancellation = cancellation or BorrowerCancellation()

    def check_active():
        cancellation.check_active()
        authority_check()

    check_active()
    with _validation_transaction(engine, frozen, cancellation, check_active) as conn:
        from .contracts import require_database_operation

        require_database_operation(conn, frozen.build.release_id, "validate_pdf_build")
        existing = calls.lookup_pdf_validation(
            conn,
            build_id=frozen.build.build_id,
            task_id=calls.TaskId(frozen.build.task_id),
            attempt=calls.TaskAttempt(frozen.build.attempt),
            holder=frozen.build.holder,
            frozen_digest=frozen.frozen_digest,
        )
    if existing is not None:
        return PdfValidationOutcome(
            existing.frozen_digest, existing.logical_digest, existing.contract_digest
        )
    with tempfile.TemporaryDirectory(prefix="pdf-native-validation-") as directory:
        capture = Path(directory) / "frozen.arrow"
        projection = Path(directory) / "access.jsonl"
        with (
            pa.OSFile(str(capture), "wb") as sink,
            pa.ipc.new_file(sink, _CAPTURE_SCHEMA) as writer,
        ):
            from .pdf_contracts import integrated_metadata_policy, pdf_context_for_task
            from .pdf_payload_validation import metadata_classes
            from .pdf_payloads import schema_dump

            with _validation_transaction(engine, frozen, cancellation, check_active) as conn:
                context = pdf_context_for_task(conn, frozen.build.task_id)
                schemas = {
                    kind: context.boundary.json_schema(cls)
                    for kind, cls in metadata_classes().items()
                }
            writer.write_batch(
                pa.RecordBatch.from_arrays(
                    [
                        pa.array(["validation_contract"]),
                        pa.array(
                            [
                                schema_dump(
                                    {
                                        "schemas": schemas,
                                        "publication_kind": frozen.kind,
                                        "integrated_metadata_policy": integrated_metadata_policy(
                                            context
                                        )
                                        if frozen.kind == "integrated"
                                        else None,
                                    }
                                ).decode()
                            ],
                            type=pa.large_string(),
                        ),
                    ],
                    schema=_CAPTURE_SCHEMA,
                )
            )
            required_streams: set[str] = set()

            def write_rows(family: str, values: Sequence[Mapping[str, Any]]) -> None:
                for row in values:
                    required_streams.update(_native_validation_streams(family, row))
                writer.write_batch(
                    pa.RecordBatch.from_arrays(
                        [
                            pa.array([family] * len(values)),
                            pa.array([json.dumps(r) for r in values], type=pa.large_string()),
                        ],
                        schema=_CAPTURE_SCHEMA,
                    )
                )

            def capture_rows(family: str, filters: Mapping[str, Any] | None = None) -> None:
                after = None
                while True:
                    check_active()
                    with _validation_transaction(
                        engine, frozen, cancellation, check_active
                    ) as conn:
                        raw_values = calls.read_pdf_frozen_rows(
                            conn,
                            build_id=frozen.build.build_id,
                            task_id=calls.TaskId(frozen.build.task_id),
                            attempt=calls.TaskAttempt(frozen.build.attempt),
                            holder=frozen.build.holder,
                            frozen_digest=frozen.frozen_digest,
                            family=family,
                            after=after,
                            limit=64 if family == "artifact_part" else 1000,
                            filters=dict(filters or {}),
                        )
                        values = []
                        from .operation_value_types import decode_json_text

                        for encoded in raw_values:
                            value = decode_json_text(encoded)
                            if not isinstance(value, dict):
                                raise ValueError("frozen PDF record envelope must be a JSON object")
                            values.append(value)
                    if not values:
                        break
                    after = values[-1]["_cursor"]
                    for row in values:
                        row.pop("_cursor", None)
                    write_rows(family, values)
                    if family == "companion":
                        fields = []
                        for row in values:
                            descriptors = row.get("_fields", [])
                            if not isinstance(descriptors, list):
                                raise ValueError("frozen companion fields must be a JSON array")
                            for descriptor in descriptors:
                                if not isinstance(descriptor, dict):
                                    raise ValueError("frozen companion field must be a JSON object")
                                fields.append(
                                    {
                                        "product_id": row["product_id"],
                                        "revision_id": row["revision_id"],
                                        "family": row["family"],
                                        "local_id": row["local_id"],
                                        **descriptor,
                                    }
                                )
                        if fields:
                            write_rows("companion_field", fields)

            for family in ("header", "native", "membership"):
                capture_rows(family)
            for family in (
                "health",
                "input",
                "native_metadata",
                "occurrence",
                "relation",
                "coverage",
                "mapping_report",
            ):
                capture_rows("companion", {"family": family})
            stream_ids = sorted(required_streams)
            for start in range(0, len(stream_ids), 512):
                filters = {"stream_ids": stream_ids[start : start + 512]}
                capture_rows("artifact_stream", filters)
                capture_rows("artifact_part", filters)
        _run_native_validation(capture, projection, check_active)
        with _validation_transaction(engine, frozen, cancellation, check_active) as conn:
            calls.record_pdf_native_validation(
                conn,
                build_id=frozen.build.build_id,
                task_id=calls.TaskId(frozen.build.task_id),
                attempt=calls.TaskAttempt(frozen.build.attempt),
                holder=frozen.build.holder,
                frozen_digest=frozen.frozen_digest,
                passed=True,
            )
        with projection.open() as source:
            pending = []
            size = 0

            def adopt_projection(rows):
                with _validation_transaction(engine, frozen, cancellation, check_active) as conn:
                    calls.adopt_pdf_access_batch(
                        conn,
                        build_id=frozen.build.build_id,
                        task_id=calls.TaskId(frozen.build.task_id),
                        attempt=calls.TaskAttempt(frozen.build.attempt),
                        holder=frozen.build.holder,
                        frozen_digest=frozen.frozen_digest,
                        rows=rows,
                    )

            for line in source:
                check_active()
                if pending and (size + len(line.encode()) > 8 * 1024**2 or len(pending) >= 128):
                    adopt_projection(pending)
                    pending = []
                    size = 0
                pending.append(json.loads(line))
                size += len(line.encode())
            if pending:
                adopt_projection(pending)
    build = frozen.build
    scope = dict(
        build_id=build.build_id,
        task_id=calls.TaskId(build.task_id),
        attempt=calls.TaskAttempt(build.attempt),
        holder=build.holder,
        frozen_digest=frozen.frozen_digest,
    )

    def run_check(name: str, borrower: BorrowerCancellation) -> None:
        borrower.check_active()
        with _validation_transaction(engine, frozen, borrower, check_active) as conn:
            calls.check_pdf_build(conn, **scope, check_name=name)

    run_check("seal", cancellation)
    checks = ("inventory", "access", "identity", "projection")
    borrowers = [BorrowerCancellation(timeout=cancellation.timeout) for _ in checks]
    store = getattr(engine, "_corpus_store", None)
    workers = min(len(checks), max(1, store.pool.max_size - 1)) if store else len(checks)
    try:
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="pdf-validation") as pool:
            try:
                pending = {
                    pool.submit(run_check, name, borrower)
                    for name, borrower in zip(checks, borrowers, strict=True)
                }
                while pending:
                    check_active()
                    done, pending = wait(pending, timeout=0.2, return_when=FIRST_COMPLETED)
                    for result in done:
                        result.result()
            except BaseException:
                for borrower in borrowers:
                    borrower.request_cancel()
                raise
    except BaseException as error:
        for borrower in borrowers:
            for failure in borrower.cleanup_failures:
                error.add_note("PDF check cancellation cleanup failed: " + repr(failure))
        raise
    with _validation_transaction(engine, frozen, cancellation, check_active) as conn:
        row = calls.validate_pdf_build(conn, **scope)
    return PdfValidationOutcome(row.frozen_digest, row.logical_digest, row.contract_digest)


def seal_pdf_build(
    conn: Connection, frozen: FrozenPdfBuildRef, product_key: str = "integrated"
) -> PublishedPdfDocumentRef:
    row = calls.seal_pdf_build(
        conn,
        build_id=frozen.build.build_id,
        task_id=calls.TaskId(frozen.build.task_id),
        attempt=calls.TaskAttempt(frozen.build.attempt),
        holder=frozen.build.holder,
        frozen_digest=frozen.frozen_digest,
        product_key=ProductKey(product_key),
    )
    return _published(row.model_dump(mode="python"))


def retain_pdf_stage_recipe(
    conn: Connection, *, task_id: int, attempt: int, holder: str, recipe_bytes: bytes
) -> str:
    return calls.bind_pdf_stage_recipe(
        conn,
        task_id=calls.TaskId(task_id),
        attempt=calls.TaskAttempt(attempt),
        holder=holder,
        recipe=recipe_bytes,
    )


@dataclass(frozen=True, slots=True)
class PdfBuildState:
    build: PdfBuildRef
    state: str
    frozen: FrozenPdfBuildRef | None
    published: PublishedPdfDocumentRef | None


def inspect_pdf_build(
    conn: Connection, *, task_id: int, attempt: int, holder: str, replay_key: str
) -> PdfBuildState | None:
    value = calls.lookup_pdf_build(
        conn,
        task_id=calls.TaskId(task_id),
        attempt=calls.TaskAttempt(attempt),
        holder=holder,
        replay_key=replay_key,
    )
    if value is None:
        return None
    row = value.model_dump(mode="python")
    build = PdfBuildRef(**{f.name: row[f.name] for f in fields(PdfBuildRef) if f.init})
    digest = calls.lookup_pdf_frozen_digest(
        conn,
        build_id=build.build_id,
        task_id=calls.TaskId(task_id),
        attempt=calls.TaskAttempt(attempt),
        holder=holder,
    )
    kind = calls.lookup_pdf_frozen_kind(
        conn,
        build_id=build.build_id,
        task_id=calls.TaskId(task_id),
        attempt=calls.TaskAttempt(attempt),
        holder=holder,
    )
    published = None
    if row["state"] == "published":
        result = calls.lookup_pdf_published_build(
            conn,
            build_id=build.build_id,
            task_id=calls.TaskId(task_id),
            attempt=calls.TaskAttempt(attempt),
            holder=holder,
        )
        published = _published(result.model_dump(mode="python"))
    if digest is not None and kind is None:
        raise ValueError("frozen PDF digest is missing its publication kind")
    return PdfBuildState(
        build,
        row["state"],
        FrozenPdfBuildRef(build, digest, kind) if digest and kind else None,
        published,
    )


def inspect_pdf_execution_receipt(
    conn: Connection, publication: PublishedPdfDocumentRef, *, attempt: int, holder: str,
    replay_key: str = "product:native",
) -> PdfExecutionReceipt:
    """Authenticate current adoption while retaining the immutable original sealed publisher."""
    state = inspect_pdf_build(
        conn, task_id=publication.task_id, attempt=attempt, holder=holder, replay_key=replay_key,
    )
    if state is None or state.published != publication:
        raise ValueError("PDF execution receipt differs from authenticated sealed build")
    return PdfExecutionReceipt(publication, state.build.attempt, state.build.holder)
