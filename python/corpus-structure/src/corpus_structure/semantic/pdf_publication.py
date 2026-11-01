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
from contextlib import contextmanager
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any

import pyarrow as pa
from sqlalchemy import Connection, Engine, text
from sqlalchemy.engine import RowMapping

from corpus_structure.core.db.lifetime import BorrowerCancellation
from corpus_structure.core.db.store import (
    DatabaseOperationFailure,
    DatabasePhase,
    EffectKnowledge,
    classify_error,
    record_operation_failure,
)

from .pdf_staging import PdfBuildRef, _parameters


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


def _published(row: RowMapping) -> PublishedPdfDocumentRef:
    return PublishedPdfDocumentRef(
        **{key: row[key] for key in PublishedPdfDocumentRef.__dataclass_fields__}
    )


def published_pdf_revision(
    conn: Connection, task_id: int, product_key: str, logical_digest: str
) -> PublishedPdfDocumentRef | None:
    row = (
        conn.execute(
            text("SELECT * FROM ops.read_pdf_published_revision(:task,:key,:digest)"),
            dict(task=task_id, key=product_key, digest=logical_digest),
        )
        .mappings()
        .one_or_none()
    )
    return None if row is None else _published(row)


def freeze_pdf_build(conn: Connection, build: PdfBuildRef, *, kind: str) -> FrozenPdfBuildRef:
    digest = conn.execute(
        text("SELECT ops.freeze_pdf_build(:build,:task,:attempt,:holder,:kind)"),
        {**_parameters(build), "kind": kind},
    ).scalar_one()
    return FrozenPdfBuildRef(build, digest, kind)


def prepare_pdf_build(conn: Connection, frozen: FrozenPdfBuildRef) -> None:
    conn.execute(
        text("SELECT ops.prepare_pdf_build(:build,:task,:attempt,:holder,:frozen)"),
        {**_parameters(frozen.build), "frozen": frozen.frozen_digest},
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
        parameters = [
            {
                **_parameters(build),
                "family": family,
                "local": local,
                "body": json.dumps(body, ensure_ascii=False, allow_nan=False),
                "fields": json.dumps(fields),
                "key": f"{replay_key}:{ordinal}",
                "ordinal": ordinal,
            }
            for ordinal, local, body, fields in pending
        ]
        if cancellation is not None:
            cancellation.check_active()
        conn.execute(
            text(
                "SELECT ops.adopt_pdf_companion(:build,:task,:attempt,:holder,:family,:local,CAST\
(:body AS jsonb),:key,:ordinal,CAST(:fields AS jsonb))"
            ),
            parameters,
        )
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
                from .pdf_payloads import PROFILE, prepare_payload_family

                if codec is None:
                    codec = prepare_payload_family(pdf_context_for_task(conn, build.task_id))
                body.update(
                    page_no=value["page_no"],
                    payload_schema_digest=codec.schema_digest,
                    payload_codec=PROFILE,
                    payload_logical_digest=codec.logical_digest(value),
                )
                payloads.append(("value", codec.encode(value), PROFILE))
            else:
                payloads.append(("value", canonical_bytes(value), "pdf-companion-json-field-v1"))
        if (
            family == "occurrence"
            and isinstance(body.get("text"), str)
            and len(body["text"].encode("utf8")) > 32768
        ):
            payloads.append(("text", body.pop("text").encode("utf8"), "pdf-record-scalar-v1:s"))
        size = sum(len(payload) for _, payload, _ in payloads)
        if pending and (len(pending) >= 64 or byte_count + size > 4 * 1024 * 1024):
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
    "reference",
    "artifact_stream",
    "artifact_part",
    "companion",
    "endpoint",
    "companion_field",
)


def _native_validation_child(capture: str, projection: str, result: Any) -> None:
    """One explicitly materialized native oracle, no database handles or credentials."""
    store = None
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
                    if family in {"header", "native", "membership", "reference"}:
                        rows[family].append(value)
        natives = {r["record_id"]: r for r in rows["native"]}
        members: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for row in rows["membership"]:
            members.setdefault((row["parent_id"], row["field_name"]), []).append(row)
        for values in members.values():
            values.sort(key=lambda r: r["ordinal"])

        class Reader:
            def record(self, record_id):
                row = dict(natives[record_id])
                for key in ("scalars_json", "structure_json"):
                    row[key] = json.dumps(row[key])
                return row

            def members(self, parent_id, field_name):
                for member in members.get((parent_id, field_name), ()):
                    row = dict(member)
                    if row.get("scalar_json") is not None:
                        row["scalar_json"] = json.dumps(row["scalar_json"])
                    yield {k: v for k, v in row.items() if v is not None}

            def scalar(self, stream_id):
                yield from store.parts(stream_id)

        profiles = {
            json.loads(raw)["stream_id"]: json.loads(raw)["encoding_profile"]
            for (raw,) in store.db.execute("SELECT body FROM entry WHERE family='artifact_stream'")
        }
        document = reconstruct_native_document(
            Reader(), rows["header"][0]["root_id"], scalar_profiles=profiles
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
        # Organized section groups use section/chapter labels; keep the native labels.
        with Path(projection).open("w") as out:
            for ordinal, pointer in enumerate(order):
                node = nodes[pointer]
                parent = node.get("parent", {}).get("$ref")
                owner = pointer
                visited = set()
                while owner not in sections and nodes[owner].get("parent"):
                    if owner in visited:
                        raise ValueError("cyclic source section ancestry")
                    visited.add(owner)
                    owner = nodes[owner]["parent"]["$ref"]
                row = dict(
                    pointer=pointer,
                    ordinal=ordinal,
                    label=node.get("label", "unspecified"),
                    parent_pointer=parent,
                    section_pointer=owner if owner in sections else None,
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
        result.send((True, None))
    except BaseException as error:
        result.send((False, f"{type(error).__name__}: {error}"))
    finally:
        if store is not None:
            store.close()
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
        if not passed:
            raise ValueError(error)
        process.join(5)
        if process.is_alive():
            raise RuntimeError("native validation child did not settle")
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

    params = {**_parameters(frozen.build), "frozen": frozen.frozen_digest}
    check_active()
    with _validation_transaction(engine, frozen, cancellation, check_active) as conn:
        from .contracts import require_database_operation

        require_database_operation(conn, frozen.build.release_id, "validate_pdf_build")
        existing = (
            conn.execute(
                text(
                    "SELECT * FROM ops.lookup_pdf_validation(:build,:task,:attempt,:holder,:frozen)"
                ),
                params,
            )
            .mappings()
            .one_or_none()
        )
    if existing is not None:
        return PdfValidationOutcome(
            existing["frozen_digest"], existing["logical_digest"], existing["contract_digest"]
        )
    with tempfile.TemporaryDirectory(prefix="pdf-native-validation-") as directory:
        capture = Path(directory) / "frozen.arrow"
        projection = Path(directory) / "access.jsonl"
        with (
            pa.OSFile(str(capture), "wb") as sink,
            pa.ipc.new_file(sink, _CAPTURE_SCHEMA) as writer,
        ):
            from .pdf_contracts import pdf_context_for_task
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
                            [schema_dump({"schemas": schemas}).decode()], type=pa.large_string()
                        ),
                    ],
                    schema=_CAPTURE_SCHEMA,
                )
            )
            for family in _FAMILIES:
                after = None
                while True:
                    check_active()
                    with _validation_transaction(
                        engine, frozen, cancellation, check_active
                    ) as conn:
                        values = (
                            conn.execute(
                                text(
                                    "SELECT * FROM \
ops.read_pdf_frozen_rows(:build,:task,:attempt,:holder,:frozen,:family,CAST(:after AS jsonb),256)"
                                ),
                                {
                                    **params,
                                    "family": family,
                                    "after": json.dumps(after) if after is not None else None,
                                },
                            )
                            .scalars()
                            .all()
                        )
                    if not values:
                        break
                    after = values[-1]["_cursor"]
                    for row in values:
                        row.pop("_cursor", None)
                    writer.write_batch(
                        pa.RecordBatch.from_arrays(
                            [
                                pa.array([family] * len(values)),
                                pa.array([json.dumps(r) for r in values], type=pa.large_string()),
                            ],
                            schema=_CAPTURE_SCHEMA,
                        )
                    )
        _run_native_validation(capture, projection, check_active)
        with _validation_transaction(engine, frozen, cancellation, check_active) as conn:
            conn.execute(
                text(
                    "SELECT ops.record_pdf_native_validation(:build,:task,:attempt,:holder,"
                    ":frozen,true)"
                ),
                params,
            )
        with projection.open() as source:
            pending = []
            size = 0

            def adopt_projection(rows):
                with _validation_transaction(engine, frozen, cancellation, check_active) as conn:
                    conn.execute(
                        text(
                            "SELECT ops.adopt_pdf_access_batch(:build,:task,:attempt,:holder,:fro\
zen,CAST(:rows AS jsonb))"
                        ),
                        {**params, "rows": json.dumps(rows)},
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
        check_active()
        with _validation_transaction(engine, frozen, cancellation, check_active) as conn:
            row = (
                conn.execute(
                    text(
                        "SELECT * FROM ops.validate_pdf_build(:build,:task,:attempt,:holder,:froz\
en)"
                    ),
                    params,
                )
                .mappings()
                .one()
            )
        return PdfValidationOutcome(
            row["frozen_digest"], row["logical_digest"], row["contract_digest"]
        )


def seal_pdf_build(
    conn: Connection, frozen: FrozenPdfBuildRef, product_key: str = "integrated"
) -> PublishedPdfDocumentRef:
    row = (
        conn.execute(
            text("SELECT * FROM ops.seal_pdf_build(:build,:task,:attempt,:holder,:frozen,:key)"),
            {**_parameters(frozen.build), "frozen": frozen.frozen_digest, "key": product_key},
        )
        .mappings()
        .one()
    )
    return _published(row)


def retain_pdf_stage_recipe(
    conn: Connection, *, task_id: int, attempt: int, holder: str, recipe_bytes: bytes
) -> str:
    return conn.execute(
        text("SELECT ops.bind_pdf_stage_recipe(:task,:attempt,:holder,:recipe)"),
        dict(task=task_id, attempt=attempt, holder=holder, recipe=recipe_bytes),
    ).scalar_one()


@dataclass(frozen=True, slots=True)
class PdfBuildState:
    build: PdfBuildRef
    state: str
    frozen: FrozenPdfBuildRef | None
    published: PublishedPdfDocumentRef | None


def inspect_pdf_build(
    conn: Connection, *, task_id: int, attempt: int, holder: str, replay_key: str
) -> PdfBuildState | None:
    row = (
        conn.execute(
            text("SELECT * FROM ops.lookup_pdf_build(:task,:attempt,:holder,:key)"),
            dict(task=task_id, attempt=attempt, holder=holder, key=replay_key),
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        return None
    build = PdfBuildRef(**{f.name: row[f.name] for f in fields(PdfBuildRef) if f.init})
    params = dict(build=build.build_id, task=task_id, attempt=attempt, holder=holder)
    digest = conn.execute(
        text("SELECT ops.lookup_pdf_frozen_digest(:build,:task,:attempt,:holder)"), params
    ).scalar_one()
    kind = conn.execute(
        text("SELECT ops.lookup_pdf_frozen_kind(:build,:task,:attempt,:holder)"), params
    ).scalar_one()
    published = None
    if row["state"] == "published":
        value = (
            conn.execute(
                text("SELECT * FROM ops.lookup_pdf_published_build(:build,:task,:attempt,:holder)"),
                params,
            )
            .mappings()
            .one()
        )
        published = _published(value)
    return PdfBuildState(
        build, row["state"], FrozenPdfBuildRef(build, digest, kind) if digest else None, published
    )
