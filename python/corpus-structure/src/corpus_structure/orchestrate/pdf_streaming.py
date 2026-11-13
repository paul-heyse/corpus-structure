"""Private PDF producer execution; receipts never imply published source readiness.

The caller supplies an owned producer context so native handles, spool readers and
borrowed buffers settle before claim maintenance ends. Only short adoption
transactions own database connections; no connection enters native computation.
"""

from __future__ import annotations

from collections.abc import Callable, Generator, Iterable, Iterator, Mapping
from contextlib import AbstractContextManager, ExitStack, closing, contextmanager, nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Protocol

import pyarrow as pa
from sqlalchemy import Connection, Engine

from corpus_structure.core.db.lifetime import BorrowerCancellation
from corpus_structure.semantic.claim_lifetime import OwnedClaim, maintained_claims
from corpus_structure.semantic.product_reference import ProductReference

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


class PrivatePdfProducer(Protocol):
    def __call__(
        self, build: PdfBuildRef, check_active: Callable[[], None], /
    ) -> AbstractContextManager[Iterator[PdfStageBatch]]: ...


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


def run_private_pdf_build(
    engine: Engine,
    claim: OwnedClaim,
    holder: str,
    *,
    source_digest: str,
    recipe_digest: str,
    schema_digest: str,
    replay_key: str,
    producer: PrivatePdfProducer,
    on_adopted: Callable[[PdfStageReceipt], None] | None = None,
    cancellation: BorrowerCancellation | None = None,
    owned_check: Callable[[], None] | None = None,
) -> PdfBuildRef:
    """Adopt bounded producer batches under existing fences, leaving the build private.

    Failure retains already committed progress. Explicit resume/abandon is owned
    by the protected staging API, never implicit conversion or terminal UnitResult.
    A callback failure propagates after commit; retry observes the same receipt.
    """
    from corpus_structure.semantic.pdf_staging import adopt_pdf_batch, begin_pdf_build

    cancellation = cancellation or BorrowerCancellation()
    with (
        maintained_claims(engine, [claim], holder)
        if owned_check is None
        else nullcontext(owned_check)
    ) as check_claim_active:

        def check_active():
            cancellation.check_active()
            check_claim_active()

        check_active()
        with _pdf_transaction(engine, cancellation) as connection:
            build = begin_pdf_build(
                connection,
                task_id=claim.task_id,
                attempt=claim.attempt,
                holder=holder,
                source_digest=source_digest,
                recipe_digest=recipe_digest,
                schema_digest=schema_digest,
                replay_key=replay_key,
            )
            from corpus_structure.semantic.contracts import require_database_operation

            require_database_operation(connection, build.release_id, "stage_pdf_producer")
        with producer(build, check_active) as batches:
            for batch in batches:
                check_active()
                with ExitStack() as readers:
                    for relation in batch.relations.values():
                        if isinstance(relation, pa.RecordBatchReader):
                            readers.callback(relation.close)
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
        check_active()
    return build


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
    owned_check: Callable[[], None] | None = None,
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
        artifact_profile,
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
        with (
            maintained_claims(engine, [claim], holder)
            if owned_check is None
            else nullcontext(owned_check)
        ) as check_claim_active:

            def check_active():
                cancellation.check_active()
                check_claim_active()

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
                    from corpus_structure.semantic.contracts import require_database_operation

                    require_database_operation(connection, build.release_id, "stage_pdf_producer")
                    from corpus_structure.semantic.pdf_contracts import pdf_context_for_task
                    from corpus_structure.semantic.pdf_payloads import (
                        prepare_payload_family,
                        schema_dump,
                    )

                    payload_family = prepare_payload_family(
                        pdf_context_for_task(connection, claim.task_id)
                    )
                    payload_schema = schema_dump(payload_family.json_schema)
                replay_root = directory / build.build_id
                replay_root.mkdir(exist_ok=True)

                def adopt_replay(replay: PdfReplayRef) -> None:
                    check_active()
                    replay.verify()
                    if replay.family == "candidate_payload":
                        from corpus_structure.ingest.pdf_candidate_source import encoded_replay
                        from corpus_structure.semantic.pdf_publication import (
                            adopt_pdf_companion_batch,
                        )

                        if not replay.path.resolve().is_relative_to(
                            (replay_root / "pages").resolve()
                        ):
                            raise ValueError("candidate payload escaped owned replay directory")
                        encoded = encoded_replay(replay, payload_family)
                        with _pdf_transaction(engine, cancellation) as connection:
                            adopt_pdf_companion_batch(
                                connection,
                                build,
                                "native_metadata",
                                (
                                    {
                                        "kind": "inline_candidate_pages",
                                        "ordinal": encoded.page_no,
                                        "value": encoded,
                                    },
                                ),
                                replay_key=f"page:{encoded.page_no}:candidate-metadata",
                                cancellation=cancellation,
                            )
                        return
                    if replay.family == "page":
                        import json

                        from corpus_structure.ingest.pdf_stream_types import PdfReplayRef
                        from corpus_structure.ingest.pdf_streaming import (
                            iter_replay_artifact_batches,
                        )

                        with replay.path.open() as source:
                            page = json.load(source)
                        number = page["page"]["page_no"]
                        raster = page["raster"]
                        raster_path = Path(raster["path"])
                        if not raster_path.resolve().is_relative_to(
                            (replay_root / "pages").resolve()
                        ):
                            raise ValueError("native raster escaped owned replay directory")
                        retained = [
                            ("assembly", replay, artifact_profile("assembly")),
                            (
                                "raster",
                                PdfReplayRef(
                                    raster_path,
                                    raster["digest"],
                                    raster["byte_length"],
                                    "native-raster",
                                ),
                                artifact_profile("raster"),
                            ),
                        ]
                        for suffix, artifact, profile in retained:
                            for index, (family, batch) in enumerate(
                                iter_replay_artifact_batches(
                                    artifact,
                                    build_id=build.build_id,
                                    stream_id=f"page/{number}/{suffix}",
                                    encoding_profile=profile,
                                )
                            ):
                                check_active()
                                with _pdf_transaction(engine, cancellation) as connection:
                                    receipt = adopt_pdf_batch(
                                        connection,
                                        build,
                                        f"page:{number}:{suffix}:{artifact.digest}:{index}",
                                        {family: (batch,)},
                                        cancellation=cancellation,
                                    )
                                if on_adopted is not None:
                                    on_adopted(receipt)
                        return
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
                                suspend_resident_nemotron(
                                    nemotron_endpoint, check_active=check_active
                                )
                            )
                    native_lifetime.enter_context(closing(worker))
                    reply = worker.stream(
                        owner.reference,
                        spool_root=replay_root / "pages",
                        record_root=replay_root / "records",
                        build_id=build.build_id,
                        release_id=build.release_id,
                        payload_schema=payload_schema,
                        on_replay=adopt_replay,
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
                                "value": {"effective_options": reply.effective_options.decode()},
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
                    with completion.open() as completion_file:
                        for ordinal, line in enumerate(completion_file):
                            value = json.loads(line)
                            if value.get("kind") != "formula":
                                continue
                            body = {"pointer": value["item_ref"], "outcome": value["outcome"]}
                            if value.get("error"):
                                body["error"] = value["error"]
                            with _pdf_transaction(engine, cancellation) as connection:
                                adopt_pdf_companion_batch(
                                    connection,
                                    build,
                                    "native_metadata",
                                    (
                                        {
                                            "kind": "formula_outcomes",
                                            "ordinal": ordinal,
                                            "value": body,
                                        },
                                    ),
                                    replay_key=f"native:formula:{ordinal}",
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


def replay_private_pdf_build(
    engine: Engine,
    build: PdfBuildRef,
    claim: OwnedClaim,
    holder: str,
    replays: Iterable[PdfReplayRef],
    *,
    on_adopted: Callable[[PdfStageReceipt], None] | None = None,
    cancellation: BorrowerCancellation | None = None,
    owned_check: Callable[[], None] | None = None,
) -> PdfBuildRef:
    """Explicitly resume exact durable IPC output without invoking recognition again."""
    from corpus_structure.semantic.contracts import require_database_operation
    from corpus_structure.semantic.pdf_staging import adopt_pdf_batch, resume_pdf_build

    cancellation = cancellation or BorrowerCancellation()
    if build.task_id != claim.task_id or build.release_id != claim.release_id:
        raise ValueError("private PDF replay task/release differs from original build")
    with (
        maintained_claims(engine, [claim], holder)
        if owned_check is None
        else nullcontext(owned_check)
    ) as check_claim_active:

        def check_active():
            cancellation.check_active()
            check_claim_active()

        with _pdf_transaction(engine, cancellation) as connection:
            require_database_operation(connection, build.release_id, "stage_pdf_producer")
            resumed = resume_pdf_build(connection, build, attempt=claim.attempt, holder=holder)
        batches = ipc_replay_batches(replays, check_active)
        try:
            for batch in batches:
                check_active()
                with _pdf_transaction(engine, cancellation) as connection:
                    receipt = adopt_pdf_batch(
                        connection,
                        resumed,
                        batch.replay_key,
                        batch.relations,
                        cancellation=cancellation,
                    )
                if on_adopted is not None:
                    on_adopted(receipt)
        finally:
            batches.close()
        check_active()
    return resumed


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
    from uuid import uuid4

    from corpus_structure.ingest.pdf_streaming import PdfStreamSpool, StreamingPdfResult
    from corpus_structure.semantic.pdf_publication import (
        freeze_pdf_build,
        inspect_pdf_build,
        prepare_pdf_build,
        retain_pdf_stage_recipe,
        seal_pdf_build,
        validate_pdf_build,
    )
    from corpus_structure.semantic.pdf_staging import (
        adopt_pdf_batch,
        begin_pdf_build,
        resume_pdf_build,
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
    with _pdf_transaction(engine, cancellation) as connection:
        retain_pdf_stage_recipe(
            connection,
            task_id=claim.task_id,
            attempt=claim.attempt,
            holder=holder,
            recipe_bytes=draft.recipe_bytes,
        )
        existing = inspect_pdf_build(
            connection,
            task_id=claim.task_id,
            attempt=claim.attempt,
            holder=holder,
            replay_key="product:" + draft.product_key,
        )
        if existing is not None:
            _check_pdf_build_premises(
                existing, claim, source_digest, recipe_digest, schema_digest, draft.kind
            )
            if existing.state != "open":
                raise ValueError(
                    "identified PDF draft cannot replace frozen/published content; "
                    "use explicit retained-product reuse or resume_pdf_publication"
                )
            build = existing.build
            if build.attempt != claim.attempt or build.holder != holder:
                build = resume_pdf_build(connection, build, attempt=claim.attempt, holder=holder)
        else:
            build = begin_pdf_build(
                connection,
                task_id=claim.task_id,
                attempt=claim.attempt,
                holder=holder,
                source_digest=source_digest,
                recipe_digest=recipe_digest,
                schema_digest=schema_digest,
                replay_key="product:" + draft.product_key,
            )
    owner = directory / build.build_id / uuid4().hex
    owner.mkdir(parents=True)
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
        on_batch=adopt,
    )
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
    from dataclasses import replace
    from hashlib import sha256
    from uuid import uuid4

    from corpus_structure.semantic.pdf_publication import (
        freeze_pdf_build,
        inspect_pdf_build,
        prepare_pdf_build,
        retain_pdf_stage_recipe,
        seal_pdf_build,
        validate_pdf_build,
    )
    from corpus_structure.semantic.pdf_staging import resume_pdf_build

    cancellation = cancellation or BorrowerCancellation()
    authority_check = check_active

    def check_active():
        cancellation.check_active()
        authority_check()

    source_digest = sha256(request.original).hexdigest()
    recipe_digest = request.recipe.digest
    schema_digest = sha256(request.schema_bytes).hexdigest()
    frozen = None
    check_active()
    with _pdf_transaction(engine, cancellation) as connection:
        existing = inspect_pdf_build(
            connection,
            task_id=claim.task_id,
            attempt=claim.attempt,
            holder=holder,
            replay_key="product:native",
        )
        if existing is not None:
            _check_pdf_build_premises(
                existing, claim, source_digest, recipe_digest, schema_digest, "native"
            )
            if existing.published is not None:
                return existing.published
            if existing.state not in {"open", "frozen"}:
                raise ValueError("abandoned native production requires a successor task")
            resumed = existing.build
            if resumed.attempt != claim.attempt or resumed.holder != holder:
                resumed = resume_pdf_build(
                    connection, resumed, attempt=claim.attempt, holder=holder
                )
            if existing.frozen is not None:
                frozen = replace(existing.frozen, build=resumed)
        retain_pdf_stage_recipe(
            connection,
            task_id=claim.task_id,
            attempt=claim.attempt,
            holder=holder,
            recipe_bytes=request.recipe.to_bytes(),
        )
    if frozen is not None:
        return _finish_frozen_pdf(engine, frozen, "native", check_active, cancellation=cancellation)
    directory = directory / uuid4().hex
    directory.mkdir(parents=True)
    original = directory / "submitted.pdf"
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


def migrate_retained_pdf_envelope(
    engine: Engine,
    claim: OwnedClaim,
    holder: str,
    *,
    path: Path,
    expected_sha256: str,
    original: bytes,
    schema_bytes: bytes,
    recipe_bytes: bytes,
    directory: Path,
    kind: Literal["native", "integrated"],
    product_key: str = "integrated",
    cancellation: BorrowerCancellation | None = None,
    structural_parent: ProductReference | None = None,
) -> PublishedPdfDocumentRef:
    """Explicit qualified storage derivation; never repeats source inference.

    The existing task must already represent this migration/adoption recipe.
    Retained bytes are checked while decoding, before the new build is frozen.
    This writes only private/admitted products for that task, not defaults or a
    completed knowledge result. Original historical products remain unchanged.
    """
    from hashlib import sha256
    from uuid import uuid4

    from corpus_structure.ingest.pdf_retained_stream import retained_pdf_draft
    from corpus_structure.semantic.pdf_contracts import pdf_context_for_task
    from corpus_structure.semantic.pdf_payloads import prepare_payload_family

    cancellation = cancellation or BorrowerCancellation()
    with _pdf_transaction(engine, cancellation) as connection:
        payload_family = prepare_payload_family(pdf_context_for_task(connection, claim.task_id))
    owner = directory / uuid4().hex
    owner.mkdir(parents=True)
    with (
        maintained_claims(engine, [claim], holder) as check_claim_active,
        retained_pdf_draft(
            path,
            expected_sha256=expected_sha256,
            product_key=product_key,
            original=original,
            schema_bytes=schema_bytes,
            recipe_bytes=recipe_bytes,
            directory=owner / "companions",
            kind=kind,
            structural_parent=structural_parent,
            payload_family=payload_family,
        ) as draft,
    ):

        def check_active():
            cancellation.check_active()
            check_claim_active()

        if structural_parent is not None:
            import json

            from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader

            retained_parent = json.loads(draft.recipe_bytes)["retained_parent"]
            expected = ProductReference(
                retained_parent["parent_task_id"],
                retained_parent["parent_product_key"],
                retained_parent["parent_digest"],
            )
            # A same-source pin alone does not prove preservation of the old parent.
            # Resolve the admitted current parent and verify its retained original envelope.
            with _pdf_transaction(engine, cancellation) as connection:
                parent_reader = PublishedPdfReader(
                    connection, structural_parent, cancellation=cancellation
                )
                digest = sha256()
                for block in parent_reader.scalar("retained/envelope"):
                    check_active()
                    digest.update(block)
                if digest.hexdigest() != expected.content_digest:
                    raise ValueError(
                        "current structural parent does not derive from retained parent"
                    )
        return publish_pdf_record_draft(
            engine,
            claim,
            holder,
            draft,
            directory=owner / "publication",
            check_active=check_active,
            cancellation=cancellation,
        )


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


def resume_pdf_publication(
    engine: Engine,
    claim: OwnedClaim,
    holder: str,
    *,
    product_key: str,
    source_digest: str,
    recipe_digest: str,
    schema_digest: str,
    kind: Literal["native", "integrated"],
    check_active: Callable[[], None],
    cancellation: BorrowerCancellation | None = None,
) -> PublishedPdfDocumentRef:
    """Explicit recovery over the same frozen union; accepts no replacement draft."""
    from dataclasses import replace

    from corpus_structure.semantic.pdf_publication import inspect_pdf_build
    from corpus_structure.semantic.pdf_staging import resume_pdf_build

    cancellation = cancellation or BorrowerCancellation()
    authority_check = check_active

    def check_active():
        cancellation.check_active()
        authority_check()

    check_active()
    with _pdf_transaction(engine, cancellation) as connection:
        state = inspect_pdf_build(
            connection,
            task_id=claim.task_id,
            attempt=claim.attempt,
            holder=holder,
            replay_key="product:" + product_key,
        )
        if state is None:
            raise ValueError("no retained PDF build to resume")
        _check_pdf_build_premises(state, claim, source_digest, recipe_digest, schema_digest, kind)
        if state.published is not None:
            return state.published
        if state.frozen is None:
            raise ValueError("PDF build is not frozen; resume its exact upload replay first")
        build = state.build
        if build.attempt != claim.attempt or build.holder != holder:
            build = resume_pdf_build(connection, build, attempt=claim.attempt, holder=holder)
        frozen = replace(state.frozen, build=build)
    return _finish_frozen_pdf(engine, frozen, product_key, check_active, cancellation=cancellation)
