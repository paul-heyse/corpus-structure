"""Model-governed frozen PDF preparation, native validation and publication.

SQLAlchemy owns sessions and transactions. A finite DB-free child receives an
owned capture of the actual frozen union; its callback result does not replace
PostgreSQL's independent custody, relational and exact-byte enforcement.
"""

from __future__ import annotations

import json
import multiprocessing
import tempfile
from collections.abc import Callable, Generator, Iterable, Mapping
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from contextlib import contextmanager
from dataclasses import dataclass, fields
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, ClassVar, Literal, TypedDict

import pyarrow as pa
from pydantic import ConfigDict, Field
from sqlalchemy import Connection, Engine

from corpus_structure.core.db.lifetime import BorrowerCancellation
from corpus_structure.core.db.store import (
    DatabaseOperationFailure,
    DatabasePhase,
    EffectKnowledge,
    classify_error,
    record_operation_failure,
)

from . import _pdf_native_calls as calls
from .identifiers import ContentDigest, ProductKey, TaskAttempt, TaskId
from .pdf_staging import PdfBuildRef

if TYPE_CHECKING:
    from corpus_structure.ingest.pdf_stream_types import PdfReplayRef

    from .pdf_contracts import PreparedPdfContext
    from .pdf_record_reader import PublishedPdfReader

COMPANION_BATCH_ROWS = 64
COMPANION_BATCH_BYTES = 4 * 1024 * 1024


class _PdfFrozenScope(TypedDict):
    build_id: str
    task_id: TaskId
    attempt: TaskAttempt
    holder: str
    frozen_digest: str


_ReceiptText = Annotated[str, Field(min_length=1)]

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
    __pydantic_config__: ClassVar[ConfigDict] = ConfigDict(extra="forbid", strict=True)

    build_id: _ReceiptText
    task_id: int
    product_key: _ReceiptText
    logical_digest: _ReceiptText
    release_id: _ReceiptText
    source_digest: _ReceiptText
    schema_digest: _ReceiptText
    recipe_digest: _ReceiptText
    frozen_digest: _ReceiptText
    kind: _ReceiptText

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
class PdfSpoolContributorReceipt:
    __pydantic_config__: ClassVar[ConfigDict] = ConfigDict(extra="forbid", strict=True)

    producer_id: _ReceiptText
    task_id: int
    producer_attempt: int
    producer_holder: _ReceiptText
    runtime_id: _ReceiptText
    runtime_manifest_digest: _ReceiptText
    manifest_digest: _ReceiptText
    selection_digest: _ReceiptText
    adopter_attempt: int
    adopter_holder: _ReceiptText


@dataclass(frozen=True, slots=True)
class PdfPublicationCertification:
    __pydantic_config__: ClassVar[ConfigDict] = ConfigDict(extra="forbid", strict=True)

    basis: Literal["producer-certified", "round-trip-verified"]
    lowering_identity: _ReceiptText
    attested_logical_digest: _ReceiptText
    native_document_digest: _ReceiptText
    oracle_receipt_id: _ReceiptText


@dataclass(frozen=True, slots=True)
class PdfExecutionReceipt:
    """Actual sealed publisher, distinct from a later completion's admitting claim."""
    __pydantic_config__: ClassVar[ConfigDict] = ConfigDict(extra="forbid", strict=True)


    publication: PublishedPdfDocumentRef
    publisher_attempt: int
    publisher_holder: _ReceiptText
    contributors: tuple[PdfSpoolContributorReceipt, ...]
    certification: PdfPublicationCertification

    def __post_init__(self) -> None:
        if (
            type(self.publisher_attempt) is not int
            or self.publisher_attempt < 1
            or type(self.publisher_holder) is not str
            or not self.publisher_holder
        ):
            raise ValueError("PDF execution receipt requires its actual sealed publisher fence")
        if self.certification.attested_logical_digest != self.publication.logical_digest:
            raise ValueError("PDF receipt differs from its producer-attested logical digest")


def _published(row: Mapping[str, Any]) -> PublishedPdfDocumentRef:
    return PublishedPdfDocumentRef(
        **{key: row[key] for key in PublishedPdfDocumentRef.__dataclass_fields__}
    )


def published_pdf_revision(
    conn: Connection, task_id: int, product_key: str, logical_digest: str
) -> PublishedPdfDocumentRef | None:
    row = calls.read_pdf_published_revision(
        conn,
        task_id=TaskId(task_id),
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
        task_id=TaskId(frozen.build.task_id),
        attempt=TaskAttempt(frozen.build.attempt),
        holder=frozen.build.holder,
        frozen_digest=frozen.frozen_digest,
    )


@dataclass(frozen=True, slots=True)
class PdfCompanionEncodingBasis:
    build_id: str
    release_id: str


COMPANION_STAGE_TARGETS = {
    "companion": "ops.pdf_stage_companion",
    "field": "ops.pdf_stage_companion_field",
    "stream": "ops.pdf_stage_artifact_stream",
    "part": "ops.pdf_stage_artifact_part",
}


def prepare_pdf_companion_batches(
    build: PdfCompanionEncodingBasis | PdfBuildRef,
    family: str,
    records: Iterable[Mapping[str, Any]],
    *,
    on_batch: Callable[[str, pa.RecordBatch], None],
    payload_family,
    start_ordinal: int = 0,
    check_active: Callable[[], None] = lambda: None,
) -> None:
    """Encode exact bounded companion bytes once, before certification or COPY."""
    from hashlib import sha256

    from .identity import canonical_bytes
    from .pdf_record_identity import byte_root, emit_parts
    from .pdf_record_model import record_arrow_schema
    from .pdf_records import _finite_json
    from .pdf_staging import MAX_BATCH_BYTES, MAX_BATCH_ROWS

    targets = COMPANION_STAGE_TARGETS
    pending, streams, parts, descriptors = [], [], [], []
    byte_count = 0

    def copy(name, rows):
        if rows:
            batch = pa.RecordBatch.from_pylist(rows, schema=record_arrow_schema(targets[name]))
            if batch.num_rows > MAX_BATCH_ROWS or batch.nbytes > MAX_BATCH_BYTES:
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
            if body["kind"] == "formula_outcomes" and isinstance(value, Mapping):
                body["outcome"] = value.get("outcome")
                body["has_diagnostic"] = "error" in value
            if body["kind"] == "inline_candidate_pages":
                from .pdf_payloads import PROFILE, EncodedPagePayload

                if codec is None:
                    raise ValueError(
                        "PDF companion preparation requires the captured payload codec"
                    )
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
            common = dict(product_id=build.build_id, revision_id=build.build_id, stream_id=stream)
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
                    "product_id": build.build_id,
                    "revision_id": build.build_id,
                    "family": family,
                    "local_id": local,
                    "field_name": field,
                    "stream_id": stream,
                    "scalar_kind": "y" if field in {"value", "endpoints"} else "s",
                }
            )
        pending.append(
            {
                "product_id": build.build_id,
                "revision_id": build.build_id,
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


def adopt_prepared_pdf_companion_batches(
    conn: Connection,
    build: PdfBuildRef,
    batches: Iterable[tuple[str, pa.RecordBatch]],
    replay_key: str,
    *,
    cancellation: BorrowerCancellation | None = None,
) -> None:
    """Adopt already certified fixed-family bytes through the existing set operation."""
    from .arrow_transfer import copy_arrow_stream
    from .pdf_record_model import record_write_profile
    from .pdf_shared_streams import PdfSharedStreamTransfer

    shared_transfer = PdfSharedStreamTransfer()
    calls.prepare_pdf_companions(conn)
    profiles = {
        name: record_write_profile(target, release_id=build.release_id)
        for name, target in COMPANION_STAGE_TARGETS.items()
    }
    for name, batch in batches:
        family = {"stream": "artifact_stream", "part": "artifact_part"}.get(name, name)
        if shared_transfer.omit_verified_parts(conn, build, {family: (batch,)}):
            continue
        target = COMPANION_STAGE_TARGETS[name]
        copy_arrow_stream(
            conn,
            profiles[name],
            target=("pg_temp", "pc_" + target.split(".")[1]),
            batches=(batch,),
            cancellation=cancellation,
        )
    calls.adopt_pdf_companions(
        conn,
        build_id=build.build_id,
        task_id=TaskId(build.task_id),
        attempt=TaskAttempt(build.attempt),
        holder=build.holder,
        replay_key=replay_key,
    )


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


def write_pdf_access_projection(document: Mapping[str, Any], projection: Path) -> None:
    """Derive access and regions from the actual certified native document."""
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
                json.dumps({"family": "access", "body": row}, ensure_ascii=False, allow_nan=False)
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
        for descriptor in store.stream_descriptors():
            profiles[descriptor["stream_id"]] = descriptor["encoding_profile"]
        document = reconstruct_native_document(
            Reader(), rows["header"][0]["root_id"], scalar_profiles=profiles, json_fields="decoded"
        )
        validate_native_callbacks(document)
        write_pdf_access_projection(document, Path(projection))
        store.validate(document, Path(projection))
        from hashlib import sha256

        from corpus_structure.ingest.pdf_streaming import _atomic_bytes

        from .identity import canonical_bytes

        _atomic_bytes(
            Path(projection).with_suffix(".native-sha256"),
            sha256(canonical_bytes(document)).hexdigest().encode(),
            "oracle_native_digest",
        )
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
                process.join()
                # The result may have arrived between the timed poll and exit
                # observation. Recheck the pipe after terminal child custody.
                if parent.poll():
                    break
                raise RuntimeError(
                    f"native validation child exited with status {process.exitcode} without outcome"
                )
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
    force_oracle: bool = False,
) -> PdfValidationOutcome:
    authority_check = check_active or (lambda: None)
    cancellation = cancellation or BorrowerCancellation()

    def check_active():
        cancellation.check_active()
        authority_check()

    check_active()
    with _validation_transaction(engine, frozen, cancellation, check_active) as conn:
        from .pdf_domain import require_pdf_database_action

        require_pdf_database_action(conn, frozen.build.release_id, "validate_pdf_build")
        existing = calls.lookup_pdf_validation(
            conn,
            build_id=frozen.build.build_id,
            task_id=TaskId(frozen.build.task_id),
            attempt=TaskAttempt(frozen.build.attempt),
            holder=frozen.build.holder,
            frozen_digest=frozen.frozen_digest,
        )
    with _validation_transaction(engine, frozen, cancellation, check_active) as conn:
        requirement = calls.read_pdf_certification_requirement(
            conn,
            build_id=frozen.build.build_id,
            task_id=TaskId(frozen.build.task_id),
            attempt=TaskAttempt(frozen.build.attempt),
            holder=frozen.build.holder,
            frozen_digest=frozen.frozen_digest,
        )
    if existing is not None and not force_oracle:
        return PdfValidationOutcome(
            existing.frozen_digest, existing.logical_digest, existing.contract_digest
        )
    if force_oracle or requirement.oracle_receipt_id is None:
        scope: _PdfFrozenScope = dict(
            build_id=frozen.build.build_id,
            task_id=TaskId(frozen.build.task_id),
            attempt=TaskAttempt(frozen.build.attempt),
            holder=frozen.build.holder,
            frozen_digest=frozen.frozen_digest,
        )
        with _validation_transaction(engine, frozen, cancellation, check_active) as conn:
            oracle = calls.begin_pdf_roundtrip_oracle(conn, **scope)
        try:
            with tempfile.TemporaryDirectory(prefix="pdf-native-oracle-") as directory:
                capture = Path(directory) / "frozen.arrow"
                projection = Path(directory) / "access.jsonl"
                from .pdf_contracts import pdf_context_for_task

                with _validation_transaction(engine, frozen, cancellation, check_active) as conn:
                    context = pdf_context_for_task(conn, frozen.build.task_id)

                def rows(family, filters):
                    after = None
                    while True:
                        with _validation_transaction(
                            engine, frozen, cancellation, check_active
                        ) as conn:
                            encoded = calls.read_pdf_frozen_rows(
                                conn,
                                **scope,
                                family=family,
                                after=after,
                                limit=64 if family == "artifact_part" else 1000,
                                filters=filters,
                            )
                            from .operation_value_types import decode_json_text

                            values = [decode_json_text(value) for value in encoded]
                        if not values:
                            return
                        for value in values:
                            if not isinstance(value, dict):
                                raise ValueError("frozen PDF oracle row must be an object")
                            after = value.pop("_cursor")
                            yield value

                write_pdf_oracle_capture(
                    capture,
                    context=context,
                    kind=frozen.kind,
                    rows=rows,
                    json_fields="decoded",
                    check_active=check_active,
                )
                outcome = verify_pdf_oracle_capture(
                    capture,
                    projection,
                    release_id=frozen.build.release_id,
                    lowering_identity=requirement.lowering_identity,
                    kind=frozen.kind,
                    logical_digest=requirement.logical_digest,
                    native_document_digest=requirement.native_document_digest,
                    check_active=check_active,
                )
            with _validation_transaction(engine, frozen, cancellation, check_active) as conn:
                calls.finish_pdf_roundtrip_oracle(
                    conn,
                    **scope,
                    oracle_receipt_id=oracle,
                    state="passed",
                    actual_native_digest=outcome.reconstructed_native_digest,
                    error_message=None,
                )
        except BaseException as error:
            try:
                cleanup = BorrowerCancellation(timeout=cancellation.timeout)
                with _validation_transaction(engine, frozen, cleanup, lambda: None) as conn:
                    calls.finish_pdf_roundtrip_oracle(
                        conn,
                        **scope,
                        oracle_receipt_id=oracle,
                        state="interrupted"
                        if cancellation.requested
                        or isinstance(error, (KeyboardInterrupt, SystemExit))
                        else "failed",
                        actual_native_digest=None,
                        error_message=f"{type(error).__name__}: {error}",
                    )
            except BaseException as settlement:
                error.add_note("PDF oracle outcome settlement also failed: " + repr(settlement))
            raise
    if existing is not None:
        return PdfValidationOutcome(
            existing.frozen_digest, existing.logical_digest, existing.contract_digest
        )
    build = frozen.build
    scope = dict(
        build_id=build.build_id,
        task_id=TaskId(build.task_id),
        attempt=TaskAttempt(build.attempt),
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
        task_id=TaskId(frozen.build.task_id),
        attempt=TaskAttempt(frozen.build.attempt),
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
        task_id=TaskId(task_id),
        attempt=TaskAttempt(attempt),
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
        task_id=TaskId(task_id),
        attempt=TaskAttempt(attempt),
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
        task_id=TaskId(task_id),
        attempt=TaskAttempt(attempt),
        holder=holder,
    )
    kind = calls.lookup_pdf_frozen_kind(
        conn,
        build_id=build.build_id,
        task_id=TaskId(task_id),
        attempt=TaskAttempt(attempt),
        holder=holder,
    )
    published = None
    if row["state"] == "published":
        result = calls.lookup_pdf_published_build(
            conn,
            build_id=build.build_id,
            task_id=TaskId(task_id),
            attempt=TaskAttempt(attempt),
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
    conn: Connection,
    publication: PublishedPdfDocumentRef,
    *,
    attempt: int,
    holder: str,
    replay_key: str = "product:native",
) -> PdfExecutionReceipt:
    """Authenticate current adoption while retaining the immutable original sealed publisher."""
    state = inspect_pdf_build(
        conn,
        task_id=publication.task_id,
        attempt=attempt,
        holder=holder,
        replay_key=replay_key,
    )
    if state is None or state.published != publication:
        raise ValueError("PDF execution receipt differs from authenticated sealed build")
    contributors = tuple(
        PdfSpoolContributorReceipt(**row.model_dump(mode="python"))
        for row in calls.read_pdf_spool_contributors(
            conn,
            build_id=publication.build_id,
            task_id=TaskId(publication.task_id),
            attempt=TaskAttempt(attempt),
            holder=holder,
        )
    )
    validation = calls.read_pdf_published_validation(
        conn,
        task_id=TaskId(publication.task_id),
        product_key=ProductKey(publication.product_key),
        content_digest=ContentDigest(publication.logical_digest),
    )
    if validation is None:
        raise ValueError("PDF execution receipt has no sealed producer certification")
    certification = PdfPublicationCertification(
        validation.certification_basis,
        validation.lowering_identity,
        validation.attested_logical_digest,
        validation.native_document_digest,
        validation.oracle_receipt_id,
    )
    return PdfExecutionReceipt(
        publication, state.build.attempt, state.build.holder, contributors, certification
    )


@dataclass(frozen=True, slots=True)
class PdfRoundtripVerification:
    release_id: str
    lowering_identity: str
    kind: str
    logical_digest: str
    native_document_digest: str
    reconstructed_native_digest: str


def write_pdf_oracle_capture(
    destination: Path,
    *,
    context,
    kind: str,
    rows,
    json_fields: Literal["text", "decoded"],
    check_active: Callable[[], None],
) -> None:
    """Capture exact callback dependencies through one authenticated row owner."""
    from .pdf_contracts import integrated_metadata_policy
    from .pdf_payload_validation import metadata_classes
    from .pdf_payloads import schema_dump

    required_streams = set()
    with (
        pa.OSFile(str(destination), "wb") as sink,
        pa.ipc.new_file(sink, _CAPTURE_SCHEMA) as writer,
    ):

        def write(family, values):
            if not values:
                return
            prepared = []
            for value in values:
                value = dict(value)
                for name in ("scalars_json", "structure_json", "scalar_json"):
                    if json_fields == "text" and isinstance(value.get(name), str):
                        value[name] = json.loads(value[name])
                if family == "artifact_part" and isinstance(value["body"], bytes):
                    value["body"] = "\\x" + value["body"].hex()
                required_streams.update(_native_validation_streams(family, value))
                prepared.append(value)
            writer.write_batch(
                pa.RecordBatch.from_arrays(
                    [
                        pa.array([family] * len(prepared)),
                        pa.array(
                            [json.dumps(value, ensure_ascii=False) for value in prepared],
                            type=pa.large_string(),
                        ),
                    ],
                    schema=_CAPTURE_SCHEMA,
                )
            )

        contract = {
            "schemas": {
                key: context.boundary.json_schema(cls) for key, cls in metadata_classes().items()
            },
            "publication_kind": kind,
            "integrated_metadata_policy": integrated_metadata_policy(context)
            if kind == "integrated"
            else None,
        }
        writer.write_batch(
            pa.RecordBatch.from_arrays(
                [
                    pa.array(["validation_contract"]),
                    pa.array([schema_dump(contract).decode()], type=pa.large_string()),
                ],
                schema=_CAPTURE_SCHEMA,
            )
        )

        def capture(family, filters=None):
            pending = []
            for row in rows(family, dict(filters or {})):
                check_active()
                pending.append(row)
                if len(pending) >= (64 if family == "artifact_part" else 1000):
                    write(family, pending)
                    pending.clear()
            write(family, pending)

        for family in ("header", "native", "membership"):
            capture(family)
        for companion_family in (
            "health",
            "input",
            "native_metadata",
            "occurrence",
            "relation",
            "coverage",
            "mapping_report",
        ):
            pending = []
            fields = []
            for row in rows("companion", {"family": companion_family}):
                check_active()
                row = dict(row)
                descriptors = row.pop("_fields", [])
                fields.extend(
                    {
                        "product_id": row["product_id"],
                        "revision_id": row["revision_id"],
                        "family": row["family"],
                        "local_id": row["local_id"],
                        **descriptor,
                    }
                    for descriptor in descriptors
                )
                pending.append(row)
                if len(pending) >= 1000:
                    write("companion", pending)
                    write("companion_field", fields)
                    pending.clear()
                    fields.clear()
            write("companion", pending)
            write("companion_field", fields)
        streams = sorted(required_streams)
        for offset in range(0, len(streams), 512):
            filters = {"stream_ids": streams[offset : offset + 512]}
            capture("artifact_stream", filters)
            capture("artifact_part", filters)


def verify_pdf_oracle_capture(
    capture: Path,
    projection: Path,
    *,
    release_id: str,
    lowering_identity: str,
    kind: str,
    logical_digest: str,
    native_document_digest: str,
    check_active: Callable[[], None],
) -> PdfRoundtripVerification:
    """Independent reconstruction with equality to the actual producer's native output."""
    _run_native_validation(capture, projection, check_active)
    reconstructed = projection.with_suffix(".native-sha256").read_text()
    if reconstructed != native_document_digest:
        raise ValueError(
            "round-trip PDF reconstruction differs from the certified producer document"
        )
    return PdfRoundtripVerification(
        release_id, lowering_identity, kind, logical_digest, native_document_digest, reconstructed
    )


@dataclass(frozen=True, slots=True)
class PdfPublishedOracleCapture:
    replay: PdfReplayRef
    projection: Path
    release_id: str
    lowering_identity: str
    kind: str
    logical_digest: str
    native_document_digest: str


def capture_published_pdf_oracle(
    reader: PublishedPdfReader,
    *,
    context: PreparedPdfContext,
    directory: Path,
    check_active: Callable[[], None],
) -> PdfPublishedOracleCapture:
    """Capture an authorized exact pin inside its read transaction; no producer fence."""
    from corpus_structure.ingest.pdf_streaming import _ref

    from .pdf_lowering import require_lowering_identity

    reader._check_active()
    receipt = reader.validation_receipt()
    if (
        receipt is None
        or context.release_id is None
        or context.release_id != reader.revision["release_id"]
    ):
        raise ValueError(
            "published PDF oracle requires its admitted release and sealed certification"
        )
    identity = require_lowering_identity(context)
    if (
        receipt.lowering_identity != identity
        or receipt.attested_logical_digest != reader.reference.content_digest
    ):
        raise ValueError("published PDF oracle differs from its released producer certification")
    directory.mkdir(parents=True, exist_ok=True)
    capture, projection = (
        directory / "published-oracle.arrow",
        directory / "published-oracle-access.jsonl",
    )
    if capture.exists() or projection.exists():
        raise FileExistsError("PDF oracle capture requires its own new output files")

    def rows(family, filters):
        yield from reader.iter_rows(
            family, filters, batch_size=64 if family == "artifact_part" else 1000
        )

    write_pdf_oracle_capture(
        capture,
        context=context,
        kind=reader.product_kind(),
        rows=rows,
        json_fields="text",
        check_active=check_active,
    )
    capture.chmod(0o400)
    return PdfPublishedOracleCapture(
        _ref(capture, "pdf_oracle_capture"),
        projection,
        context.release_id,
        identity,
        reader.product_kind(),
        reader.reference.content_digest,
        receipt.native_document_digest,
    )


def verify_published_pdf_oracle(
    capture: PdfPublishedOracleCapture, *, check_active: Callable[[], None]
) -> PdfRoundtripVerification:
    """Run the DB-free oracle after selected read transactions have settled."""
    capture.replay.verify()
    return verify_pdf_oracle_capture(
        capture.replay.path,
        capture.projection,
        release_id=capture.release_id,
        lowering_identity=capture.lowering_identity,
        kind=capture.kind,
        logical_digest=capture.logical_digest,
        native_document_digest=capture.native_document_digest,
        check_active=check_active,
    )


def prepared_pdf_companion_batches(prepared):
    """Borrow certified companion IPC files through their last COPY batch."""
    from .pdf_record_model import record_arrow_schema

    for replay in prepared.replays:
        replay.verify()
        name = replay.family.removeprefix("prepared_companion:")
        with pa.memory_map(str(replay.path), "r") as source:
            reader = pa.ipc.open_file(source)
            if not reader.schema.equals(
                record_arrow_schema(COMPANION_STAGE_TARGETS[name]), check_metadata=True
            ):
                raise ValueError("certified companion IPC schema differs")
            for index in range(reader.num_record_batches):
                yield name, reader.get_batch(index)


def record_pdf_producer_certification(conn: Connection, build: PdfBuildRef, certification) -> None:
    if (certification.source_digest, certification.recipe_digest, certification.schema_digest) != (
        build.source_digest,
        build.recipe_digest,
        build.schema_digest,
    ):
        raise ValueError("PDF producer certification differs from its exact build premises")
    calls.record_pdf_producer_certification(
        conn,
        build_id=build.build_id,
        task_id=TaskId(build.task_id),
        attempt=TaskAttempt(build.attempt),
        holder=build.holder,
        lowering_identity=certification.lowering_identity,
        kind=certification.kind,
        logical_digest=certification.logical_digest,
        native_document_digest=certification.native_document_digest,
        stream_inventory_digest=certification.stream_inventory_digest,
    )


def stage_pdf_access_projection(
    engine: Engine,
    build: PdfBuildRef,
    path: Path,
    *,
    cancellation: BorrowerCancellation,
    check_active: Callable[[], None],
) -> None:
    pending, size = [], 0

    def flush():
        nonlocal size
        if not pending:
            return
        check_active()
        with engine.connect() as conn, cancellation.borrow(conn), conn.begin():
            calls.stage_pdf_access_batch(
                conn,
                build_id=build.build_id,
                task_id=TaskId(build.task_id),
                attempt=TaskAttempt(build.attempt),
                holder=build.holder,
                rows=pending,
            )
            check_active()
        pending.clear()
        size = 0

    with path.open() as source:
        for line in source:
            check_active()
            if pending and (len(pending) >= 128 or size + len(line.encode()) > 8 * 1024**2):
                flush()
            pending.append(json.loads(line))
            size += len(line.encode())
    flush()
