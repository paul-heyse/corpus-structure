"""Private PDF producer execution; receipts never imply published source readiness.

The caller supplies an owned producer context so native handles, spool readers and
borrowed buffers settle before claim maintenance ends. Only short adoption
transactions own database connections; no connection enters native computation.
"""

from __future__ import annotations

from collections.abc import Callable, Generator, Iterable, Mapping
from contextlib import ExitStack, closing, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import pyarrow as pa
from sqlalchemy import Connection, Engine

from corpus_structure.core.db.lifetime import BorrowerCancellation
from corpus_structure.semantic.claim_lifetime import OwnedClaim

if TYPE_CHECKING:
    from corpus_structure.core.method import PdfRecordProducerRequest, PdfRecordPublicationDraft
    from corpus_structure.ingest.pdf import PdfRecipe
    from corpus_structure.ingest.pdf_assets import PreparedPdfAssets
    from corpus_structure.ingest.pdf_stream_types import PdfReplayRef
    from corpus_structure.semantic.pdf_publication import (
        FrozenPdfBuildRef,
        PdfBuildState,
        PublishedPdfDocumentRef,
    )
    from corpus_structure.semantic.pdf_staging import PdfBuildRef, PdfStageReceipt


@dataclass(frozen=True)
class PdfStageBatch:
    replay_key: str
    relations: Mapping[str, Iterable[pa.RecordBatch] | pa.RecordBatchReader]


@contextmanager
def _pdf_transaction(engine: Engine, cancellation: BorrowerCancellation) -> Generator[Connection]:
    """Retain this operation's cancellation handle through its owned transaction settlement."""
    with engine.connect() as connection, cancellation.borrow(connection), connection.begin():
        yield connection
        cancellation.check_active()


def adopt_pdf_companions(
    engine: Engine,
    build: PdfBuildRef,
    family: str,
    records: Iterable[Mapping[str, Any]],
    replay_key: str,
    *,
    check_active: Callable[[], None],
    cancellation: BorrowerCancellation,
    start_ordinal: int = 0,
) -> None:
    """Prepare bounded row chunks before acquiring each protected append transaction.

    Arrow IPC batches are transport units, not lease-fence units. A source iterator may
    decode an arbitrarily large replay, but no checkout/task row lock spans that work.
    Absolute offsets keep receipts stable across retry; individual content identities
    remain the native companion/field identities, independently of chunking.
    """
    import json

    from corpus_structure.semantic.pdf_payloads import EncodedPagePayload
    from corpus_structure.semantic.pdf_publication import (
        COMPANION_BATCH_BYTES,
        COMPANION_BATCH_ROWS,
        adopt_pdf_companion_batch,
    )

    pending: list[Mapping[str, Any]] = []
    size = 0
    delivered = start_ordinal

    def flush() -> None:
        nonlocal size, delivered
        if not pending:
            return
        check_active()
        with _pdf_transaction(engine, cancellation) as connection:
            adopt_pdf_companion_batch(
                connection,
                build,
                family,
                pending,
                replay_key=f"{replay_key}:rows:{delivered}",
                start_ordinal=delivered,
                cancellation=cancellation,
            )
        delivered += len(pending)
        pending.clear()
        size = 0
        check_active()

    for row in records:
        check_active()
        row_size = (
            len(row["value"].content) + 256
            if isinstance(row.get("value"), EncodedPagePayload)
            else len(json.dumps(dict(row), ensure_ascii=False, allow_nan=False).encode())
        )
        if pending and (
            len(pending) >= COMPANION_BATCH_ROWS or size + row_size > COMPANION_BATCH_BYTES
        ):
            flush()
        pending.append(row)
        size += row_size
    flush()


def ipc_replay_batches(
    replays: Iterable[PdfReplayRef], check_active: Callable[[], None]
) -> Generator[PdfStageBatch]:
    """Borrow each authenticated IPC replay through adoption of its last batch.

    Physical file/batch keys identify exact retries, not logical product identity.
    The caller retains the replay owner until this iterator is closed.
    """
    for replay in replays:
        check_active()
        replay.verify()
        with pa.memory_map(str(replay.path), "r") as source:
            reader = pa.ipc.open_file(source)
            for ordinal in range(reader.num_record_batches):
                check_active()
                yield PdfStageBatch(
                    f"ipc:{replay.family}:{replay.digest}:{ordinal}",
                    {replay.family: (reader.get_batch(ordinal),)},
                )


def run_private_native_pdf_build(
    engine: Engine,
    claim: OwnedClaim,
    holder: str,
    *,
    original: Path,
    recipe: PdfRecipe,
    assets: PreparedPdfAssets | None,
    directory: Path,
    source_digest: str,
    schema_digest: str,
    replay_key: str,
    nemotron_endpoint: str | None = None,
    require_nemotron_handoff: bool = False,
    observation_replay: PdfReplayRef | None = None,
    structural_pin: dict[str, Any] | None = None,
    integration_policy: dict[str, Any] | None = None,
    on_adopted: Callable[[PdfStageReceipt], None] | None = None,
    cancellation: BorrowerCancellation | None = None,
    owned_check: Callable[[], None],
) -> PdfBuildRef:
    """Run the actual finite native worker into protected private record custody.

    Page replay callbacks are flow-control acknowledgements, not document
    publication. Source ownership ends after the child has settled; spools retain
    replay/failure evidence for explicit resume or authenticated cleanup.
    """
    from corpus_structure.ingest.pdf_capacity import (
        native_before_nemotron,
        suspend_resident_nemotron,
    )
    from corpus_structure.ingest.pdf_stream_types import OwnedPdfSource
    from corpus_structure.ingest.pdf_worker import PdfWorker
    from corpus_structure.semantic.pdf_staging import (
        STAGE_FAMILIES,
        adopt_pdf_batch,
        begin_pdf_build,
    )

    cancellation = cancellation or BorrowerCancellation()
    if recipe.recipe_id != "docling-standard-pdf-stream-v1":
        raise ValueError("private streaming requires its explicitly retained stream recipe")
    # Original/recipe custody must precede this entry; begin checks it natively.
    directory.mkdir(parents=True, exist_ok=True)
    owner = OwnedPdfSource.acquire(original, directory, expected_digest=source_digest)
    worker = None
    entered = False
    try:
        worker = PdfWorker(recipe, assets=assets)

        def check_active():
            cancellation.check_active()
            owned_check()

        entered = True
        try:
            with _pdf_transaction(engine, cancellation) as connection:
                build = begin_pdf_build(
                    connection,
                    task_id=claim.task_id,
                    attempt=claim.attempt,
                    holder=holder,
                    source_digest=source_digest,
                    recipe_digest=recipe.digest,
                    schema_digest=schema_digest,
                    replay_key=replay_key,
                )
                from corpus_structure.semantic.pdf_domain import require_pdf_database_action

                require_pdf_database_action(connection, build.release_id, "stage_pdf_producer")
                from corpus_structure.semantic.pdf_contracts import pdf_context_for_task
                from corpus_structure.semantic.pdf_payloads import (
                    prepare_payload_family,
                    schema_dump,
                )

                payload_family = prepare_payload_family(
                    pdf_context_for_task(connection, claim.task_id)
                )
                payload_schema = schema_dump(payload_family.json_schema)
            from corpus_structure.ingest.pdf_build_spool import PdfBuildSpool

            spool = PdfBuildSpool(
                directory,
                build_id=build.build_id,
                task_id=claim.task_id,
                attempt=claim.attempt,
                holder=holder,
                check_active=check_active,
            )
            replay_root = spool.root

            def retain_replay(replay: PdfReplayRef) -> None:
                if replay.family not in {
                    *STAGE_FAMILIES,
                    "page",
                    "candidate_payload",
                    "companion:occurrence",
                }:
                    raise ValueError("unknown private PDF replay family")
                if replay.family == "page":
                    import json

                    from corpus_structure.ingest.pdf_stream_types import PdfReplayRef

                    replay.verify()
                    with replay.path.open() as source:
                        page = json.load(source)
                    raster = page["raster"]
                    spool.append(
                        PdfReplayRef(
                            Path(raster["path"]),
                            raster["digest"],
                            raster["byte_length"],
                            "native-raster",
                            page_no=page["page"]["page_no"],
                        )
                    )
                spool.append(replay)

            def adopt_replay(replay: PdfReplayRef) -> None:
                check_active()
                replay.verify()
                if replay.family == "companion:occurrence":
                    import json

                    from corpus_structure.semantic.pdf_record_model import record_arrow_schema

                    with pa.memory_map(str(replay.path), "r") as source:
                        reader = pa.ipc.open_file(source)
                        if not reader.schema.equals(
                            record_arrow_schema("ops.pdf_stage_companion"), check_metadata=True
                        ):
                            raise ValueError("native occurrence replay schema differs")
                        for ordinal in range(reader.num_record_batches):
                            check_active()
                            batch = reader.get_batch(ordinal)

                            def occurrences(batch=batch):
                                for body in batch.column("body"):
                                    yield json.loads(body.as_py())

                            adopt_pdf_companions(
                                engine,
                                build,
                                "occurrence",
                                occurrences(),
                                replay_key=f"ipc-companion:{replay.digest}:{ordinal}",
                                start_ordinal=batch.column("ordinal")[0].as_py(),
                                check_active=check_active,
                                cancellation=cancellation,
                            )
                    return
                if replay.family not in STAGE_FAMILIES:
                    raise ValueError("unknown private PDF replay family")
                batches = ipc_replay_batches([replay], check_active)
                try:
                    for batch in batches:
                        with _pdf_transaction(engine, cancellation) as connection:
                            receipt = adopt_pdf_batch(
                                connection,
                                build,
                                batch.replay_key,
                                batch.relations,
                                cancellation=cancellation,
                            )
                        if on_adopted is not None:
                            on_adopted(receipt)
                finally:
                    batches.close()

            with ExitStack() as native_lifetime:
                if recipe.device == "cuda" or recipe.ocr_device == "cuda":
                    if require_nemotron_handoff:
                        if nemotron_endpoint is None:
                            raise ValueError("native GPU worker requires a Nemotron endpoint")
                        native_lifetime.enter_context(
                            native_before_nemotron(nemotron_endpoint, check_active=check_active)
                        )
                    else:
                        native_lifetime.enter_context(
                            suspend_resident_nemotron(nemotron_endpoint, check_active=check_active)
                        )
                native_lifetime.enter_context(closing(worker))
                reply = worker.stream(
                    owner.reference,
                    spool_root=replay_root / "pages",
                    record_root=replay_root / "records",
                    build_id=build.build_id,
                    release_id=build.release_id,
                    payload_schema=payload_schema,
                    on_replay=retain_replay,
                    check_active=check_active,
                    observation_replay=observation_replay,
                    structural_pin=structural_pin,
                    integration_policy=integration_policy,
                    reconciliation_root=replay_root / "reconciliation"
                    if observation_replay
                    else None,
                )
            if reply.conversion_status != "success":
                raise RuntimeError(
                    "native streaming conversion did not complete: " + "; ".join(reply.errors)
                )
            # The child and its native borrowers have settled. No page callback
            # above adopts anything; consume the verified journal once now.
            from corpus_structure.ingest.pdf_candidate_source import encoded_replay

            def candidates():
                for replay in spool.entries:
                    if replay.family == "candidate_payload":
                        encoded = encoded_replay(replay, payload_family)
                        yield {
                            "kind": "inline_candidate_pages",
                            "ordinal": encoded.page_no,
                            "value": encoded,
                        }

            adopt_pdf_companions(
                engine,
                build,
                "native_metadata",
                candidates(),
                "native:candidate-metadata",
                check_active=check_active,
                cancellation=cancellation,
            )
            for replay in spool.entries:
                if replay.family not in {"page", "native-raster", "candidate_payload"}:
                    adopt_replay(replay)
            from corpus_structure.semantic.pdf_publication import adopt_pdf_companion_batch

            with _pdf_transaction(engine, cancellation) as connection:
                adopt_pdf_companion_batch(
                    connection,
                    build,
                    "native_metadata",
                    (
                        {
                            "kind": "runtime_report",
                            "ordinal": 0,
                            "value": {
                                "effective_options": reply.effective_options.decode(),
                                "spool": spool.report(),
                            },
                        },
                    ),
                    replay_key="native:runtime-report",
                    cancellation=cancellation,
                )
                adopt_pdf_companion_batch(
                    connection,
                    build,
                    "health",
                    (
                        {
                            "conversion": reply.conversion_status,
                            "display_coverage": "unknown",
                            "inline_coverage": "unknown",
                            "cell_coverage": "unknown",
                            "issues": list(reply.errors),
                            "source_scope": "whole_document",
                        },
                    ),
                    replay_key="native:health",
                    cancellation=cancellation,
                )
            import json

            completion = replay_root / "records" / "completion.jsonl"
            if completion.exists():

                def formula_outcomes():
                    with completion.open() as completion_file:
                        for ordinal, line in enumerate(completion_file):
                            value = json.loads(line)
                            if value.get("kind") != "formula":
                                continue
                            body = {"pointer": value["item_ref"], "outcome": value["outcome"]}
                            if value.get("error"):
                                body["error"] = value["error"]
                            yield {"kind": "formula_outcomes", "ordinal": ordinal, "value": body}

                adopt_pdf_companions(
                    engine,
                    build,
                    "native_metadata",
                    formula_outcomes(),
                    "native:formulas",
                    check_active=check_active,
                    cancellation=cancellation,
                )
            check_active()
        finally:
            # Stop native borrowers before ending claim maintenance or source custody.
            if not worker.closed or worker.pid is not None:
                worker.close()
            owner.close()
    finally:
        if not entered:
            if worker is not None:
                worker.close()
            owner.close()
    return build



def finish_existing_pdf_product(
    engine: Engine,
    claim: OwnedClaim,
    holder: str,
    *,
    product_key: str,
    kind: Literal["native", "integrated"],
    source_digest: str,
    recipe_bytes: bytes,
    schema_digest: str,
    check_active: Callable[[], None],
    cancellation: BorrowerCancellation | None = None,
) -> PublishedPdfDocumentRef | None:
    """Finish matching immutable progress before invoking any producer computation."""
    from dataclasses import replace
    from hashlib import sha256

    from corpus_structure.semantic.pdf_publication import inspect_pdf_build, retain_pdf_stage_recipe
    from corpus_structure.semantic.pdf_staging import resume_pdf_build

    cancellation = cancellation or BorrowerCancellation()
    check_active()
    frozen = None
    with _pdf_transaction(engine, cancellation) as connection:
        existing = inspect_pdf_build(
            connection, task_id=claim.task_id, attempt=claim.attempt,
            holder=holder, replay_key="product:" + product_key,
        )
        if existing is not None:
            _check_pdf_build_premises(
                existing, claim, source_digest, sha256(recipe_bytes).hexdigest(), schema_digest, kind
            )
            if existing.published is not None:
                return existing.published
            if existing.state not in {"open", "frozen"}:
                raise ValueError("abandoned PDF production requires a successor task")
            resumed = existing.build
            if resumed.attempt != claim.attempt or resumed.holder != holder:
                resumed = resume_pdf_build(connection, resumed, attempt=claim.attempt, holder=holder)
            if existing.frozen is not None:
                frozen = replace(existing.frozen, build=resumed)
        retain_pdf_stage_recipe(
            connection, task_id=claim.task_id, attempt=claim.attempt,
            holder=holder, recipe_bytes=recipe_bytes,
        )
    if frozen is not None:
        return _finish_frozen_pdf(
            engine, frozen, product_key, check_active, cancellation=cancellation
        )
    return None


def publish_pdf_record_draft(
    engine: Engine,
    claim: OwnedClaim,
    holder: str,
    draft: PdfRecordPublicationDraft,
    *,
    directory: Path,
    check_active: Callable[[], None],
    cancellation: BorrowerCancellation | None = None,
) -> PublishedPdfDocumentRef:
    """Publish the actual method result through private rows and frozen validation.

    Called by the existing leased method owner. Conversion/selection has finished;
    no connection is retained while lowering or executing native validation. A
    failure leaves authenticated private progress and original custody available.
    """
    from hashlib import sha256

    from corpus_structure.ingest.pdf_streaming import PdfStreamSpool, StreamingPdfResult
    from corpus_structure.semantic.pdf_publication import (
        freeze_pdf_build,
        prepare_pdf_build,
        seal_pdf_build,
        validate_pdf_build,
    )
    from corpus_structure.semantic.pdf_staging import (
        adopt_pdf_batch,
        begin_pdf_build,
    )

    cancellation = cancellation or BorrowerCancellation()
    authority_check = check_active

    def check_active():
        cancellation.check_active()
        authority_check()

    check_active()
    source_digest = sha256(draft.original).hexdigest()
    recipe_digest = sha256(draft.recipe_bytes).hexdigest()
    schema_digest = sha256(draft.schema_bytes).hexdigest()
    completed = finish_existing_pdf_product(
        engine, claim, holder, product_key=draft.product_key, kind=draft.kind,
        source_digest=source_digest, recipe_bytes=draft.recipe_bytes, schema_digest=schema_digest,
        check_active=check_active, cancellation=cancellation,
    )
    if completed is not None:
        return completed
    with _pdf_transaction(engine, cancellation) as connection:
        build = begin_pdf_build(
            connection, task_id=claim.task_id, attempt=claim.attempt, holder=holder,
            source_digest=source_digest, recipe_digest=recipe_digest, schema_digest=schema_digest,
            replay_key="product:" + draft.product_key,
        )
    from corpus_structure.ingest.pdf_build_spool import PdfBuildSpool

    draft_spool = PdfBuildSpool(
        directory,
        build_id=build.build_id,
        task_id=claim.task_id,
        attempt=claim.attempt,
        holder=holder,
        check_active=check_active,
    )
    owner = draft_spool.root
    spool = PdfStreamSpool(owner / "pages", check_active=check_active)
    streamed = StreamingPdfResult(
        draft.document,
        spool,
        str(draft.health.get("conversion", "success")),
        (),
        draft.recipe_bytes,
        (),
    )

    def adopt(replay: PdfReplayRef) -> None:
        batches = ipc_replay_batches((replay,), check_active)
        try:
            for batch in batches:
                check_active()
                with _pdf_transaction(engine, cancellation) as connection:
                    adopt_pdf_batch(
                        connection,
                        build,
                        batch.replay_key,
                        batch.relations,
                        cancellation=cancellation,
                    )
        finally:
            batches.close()

    streamed.write_record_batches(
        owner / "records",
        build_id=build.build_id,
        release_id=build.release_id,
        source_digest=source_digest,
        on_batch=draft_spool.append,
    )
    for replay in draft_spool.entries:
        adopt(replay)
    if draft.kind == "native" and "occurrence" not in draft.companions:
        from corpus_structure.ingest.pdf_record_product import native_occurrence_rows

        native_occurrences = native_occurrence_rows(draft.document)
    else:
        native_occurrences = None
    companions = dict(draft.companions)
    if native_occurrences is not None:
        companions["occurrence"] = native_occurrences
    native_health = dict(draft.health)
    captured_metadata = dict(draft.metadata)
    if "formula_outcomes" in native_health:
        captured_metadata.setdefault("formula_outcomes", native_health.pop("formula_outcomes"))
    if captured_metadata:

        def metadata_rows():
            for kind, values in captured_metadata.items():
                rows = (values,) if isinstance(values, Mapping) else values
                for ordinal, value in enumerate(rows):
                    yield {"kind": kind, "ordinal": ordinal, "value": value}

        from itertools import chain

        companions["native_metadata"] = chain(
            companions.get("native_metadata", ()), metadata_rows()
        )
    if "health" in companions:
        health_rows = companions["health"]

        def bounded_health_rows():
            for row in health_rows:
                body = dict(row)
                embedded = body.pop("health", None)
                if embedded is not None:
                    body = {**embedded, **body}
                body.pop("formula_outcomes", None)
                yield body

        companions["health"] = bounded_health_rows()
    companions.setdefault(
        "health",
        (
            {
                **native_health,
                "source_scope": draft.source_scope,
            },
        ),
    )
    for family, records in companions.items():
        adopt_pdf_companions(
            engine,
            build,
            family,
            records,
            replay_key=f"companion:{family}",
            check_active=check_active,
            cancellation=cancellation,
        )
    if draft.retained_serialization is not None:
        _adopt_retained_serialization(
            engine, build, draft.retained_serialization, check_active, cancellation=cancellation
        )
    check_active()
    with _pdf_transaction(engine, cancellation) as connection:
        frozen = freeze_pdf_build(connection, build, kind=draft.kind)
    with _pdf_transaction(engine, cancellation) as connection:
        prepare_pdf_build(connection, frozen)
    validate_pdf_build(engine, frozen, check_active=check_active, cancellation=cancellation)
    check_active()
    with _pdf_transaction(engine, cancellation) as connection:
        return seal_pdf_build(connection, frozen, product_key=draft.product_key)


def produce_published_pdf_records(
    engine: Engine,
    claim: OwnedClaim,
    holder: str,
    request: PdfRecordProducerRequest,
    *,
    directory: Path,
    check_active: Callable[[], None],
    cancellation: BorrowerCancellation | None = None,
) -> PublishedPdfDocumentRef:
    """Actual finite page producer followed by frozen publication, never graph IPC."""
    from hashlib import sha256

    from corpus_structure.semantic.pdf_publication import (
        freeze_pdf_build,
        prepare_pdf_build,
        seal_pdf_build,
        validate_pdf_build,
    )

    cancellation = cancellation or BorrowerCancellation()
    authority_check = check_active

    def check_active():
        cancellation.check_active()
        authority_check()

    source_digest = sha256(request.original).hexdigest()
    schema_digest = sha256(request.schema_bytes).hexdigest()
    completed = finish_existing_pdf_product(
        engine, claim, holder, product_key="native", kind="native", source_digest=source_digest,
        recipe_bytes=request.recipe.to_bytes(), schema_digest=schema_digest,
        check_active=check_active, cancellation=cancellation,
    )
    if completed is not None:
        return completed
    directory.mkdir(parents=True, exist_ok=True)
    original = directory / f"submitted-{claim.task_id}-{claim.attempt}.pdf"
    with original.open("xb") as stream:
        stream.write(request.original)
    build = run_private_native_pdf_build(
        engine,
        claim,
        holder,
        original=original,
        recipe=request.recipe,
        assets=request.assets,
        directory=directory / "producer",
        source_digest=sha256(request.original).hexdigest(),
        schema_digest=sha256(request.schema_bytes).hexdigest(),
        replay_key="product:native",
        nemotron_endpoint=request.nemotron_endpoint,
        require_nemotron_handoff=request.require_nemotron_handoff,
        cancellation=cancellation,
        owned_check=check_active,
    )
    check_active()
    with _pdf_transaction(engine, cancellation) as connection:
        frozen = freeze_pdf_build(connection, build, kind="native")
    with _pdf_transaction(engine, cancellation) as connection:
        prepare_pdf_build(connection, frozen)
    validate_pdf_build(engine, frozen, check_active=check_active, cancellation=cancellation)
    check_active()
    with _pdf_transaction(engine, cancellation) as connection:
        return seal_pdf_build(connection, frozen, product_key="native")


def _adopt_retained_serialization(
    engine, build, retained, check_active, *, cancellation: BorrowerCancellation | None = None
):
    import gzip
    from hashlib import sha256

    from corpus_structure.semantic.pdf_record_identity import IdentityFold, emit_parts
    from corpus_structure.semantic.pdf_staging import adopt_pdf_batch, stage_schema

    cancellation = cancellation or BorrowerCancellation()
    authority_check = check_active

    def check_active():
        cancellation.check_active()
        authority_check()

    stream_id = "retained/envelope"
    common = {"product_id": build.build_id, "revision_id": build.build_id, "stream_id": stream_id}
    digest = sha256()
    fold = IdentityFold("bytes")
    opener = gzip.open if retained.compression == "gzip" else open
    with opener(retained.path, "rb") as source:

        def chunks():
            while block := source.read(65536):
                yield block

        pending = []
        index = 0
        for part in emit_parts(stream_id, chunks()):
            digest.update(part.body)
            fold.add(part.body)
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
                check_active()
                with _pdf_transaction(engine, cancellation) as connection:
                    adopt_pdf_batch(
                        connection,
                        build,
                        f"retained:parts:{index}",
                        {
                            "artifact_part": (
                                pa.RecordBatch.from_pylist(
                                    pending, schema=stage_schema("artifact_part")
                                ),
                            ),
                        },
                        cancellation=cancellation,
                    )
                index += 1
                pending.clear()
        if pending:
            with _pdf_transaction(engine, cancellation) as connection:
                adopt_pdf_batch(
                    connection,
                    build,
                    f"retained:parts:{index}",
                    {
                        "artifact_part": (
                            pa.RecordBatch.from_pylist(
                                pending, schema=stage_schema("artifact_part")
                            ),
                        ),
                    },
                    cancellation=cancellation,
                )
    if digest.hexdigest() != retained.serialization_sha256:
        raise ValueError("retained bytes changed during storage adoption")
    check_active()
    row = {
        **common,
        "byte_length": fold.byte_length,
        "byte_root": fold.digest().hex(),
        "serialization_sha256": digest.hexdigest(),
        "encoding_profile": "retained-pdf-envelope-json-v1",
    }
    with _pdf_transaction(engine, cancellation) as connection:
        adopt_pdf_batch(
            connection,
            build,
            "retained:stream",
            {
                "artifact_stream": (
                    pa.RecordBatch.from_pylist([row], schema=stage_schema("artifact_stream")),
                ),
            },
            cancellation=cancellation,
        )


def _check_pdf_build_premises(
    state: PdfBuildState,
    claim: OwnedClaim,
    source_digest: str,
    recipe_digest: str,
    schema_digest: str,
    kind: Literal["native", "integrated"],
) -> None:
    build = state.build
    if (
        build.task_id,
        build.release_id,
        build.source_digest,
        build.recipe_digest,
        build.schema_digest,
    ) != (
        claim.task_id,
        claim.release_id,
        source_digest,
        recipe_digest,
        schema_digest,
    ):
        raise ValueError("retained PDF operation source/release/recipe/schema differs")
    actual_kind = (
        state.published.kind if state.published else state.frozen.kind if state.frozen else None
    )
    if actual_kind is not None and actual_kind != kind:
        raise ValueError("retained PDF operation semantic kind differs")


def _finish_frozen_pdf(
    engine: Engine,
    frozen: FrozenPdfBuildRef,
    product_key: str,
    check_active: Callable[[], None],
    *,
    cancellation: BorrowerCancellation | None = None,
) -> PublishedPdfDocumentRef:
    from corpus_structure.semantic.pdf_publication import (
        prepare_pdf_build,
        seal_pdf_build,
        validate_pdf_build,
    )

    cancellation = cancellation or BorrowerCancellation()
    authority_check = check_active

    def check_active():
        cancellation.check_active()
        authority_check()

    check_active()
    with _pdf_transaction(engine, cancellation) as connection:
        prepare_pdf_build(connection, frozen)
    validate_pdf_build(engine, frozen, check_active=check_active, cancellation=cancellation)
    check_active()
    with _pdf_transaction(engine, cancellation) as connection:
        return seal_pdf_build(connection, frozen, product_key=product_key)
