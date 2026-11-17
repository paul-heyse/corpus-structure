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
from typing import TYPE_CHECKING, Any, Literal, Protocol

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


class PdfProducerClaim(OwnedClaim, Protocol):
    @property
    def runtime_id(self) -> str: ...


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
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.pdf_payloads import EncodedPagePayload
    from corpus_structure.semantic.pdf_publication import (
        COMPANION_BATCH_BYTES,
        COMPANION_BATCH_ROWS,
        PdfCompanionRecord,
    )
    from corpus_structure.semantic.pdf_publication import (
        adopt_pdf_companions as adopt_companion_set,
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
            adopt_companion_set(
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
        if isinstance(row, PdfCompanionRecord):
            row_size = row.encoded_length
        elif isinstance(row.get("value"), EncodedPagePayload):
            row_size = len(row["value"].content) + len(
                canonical_bytes({key: value for key, value in row.items() if key != "value"})
            )
        else:
            row_size = len(canonical_bytes(dict(row)))
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
    claim: PdfProducerClaim,
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
        UPLOAD_STAGE_FAMILIES,
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
    spool = None
    recovered = ()
    entered = False
    try:

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

                context = pdf_context_for_task(connection, claim.task_id)
                payload_family = prepare_payload_family(context)
                payload_schema = schema_dump(payload_family.json_schema)
                from corpus_structure.ingest.pdf_build_spool import PdfSpoolProducerBasis
                from corpus_structure.semantic.pdf_certification import (
                    prepare_pdf_producer_contract,
                )

                producer_contract = prepare_pdf_producer_contract(context, kind="native")
                lowering_identity = producer_contract.lowering_identity
                validation_contract = producer_contract.validation_contract
                payload_schema = producer_contract.payload_schema
                from corpus_structure.semantic import _pdf_native_calls as calls
                from corpus_structure.semantic.identifiers import RuntimeId, TaskAttempt, TaskId

                basis = PdfSpoolProducerBasis(
                    **calls.read_pdf_producer_basis(
                        connection,
                        task_id=TaskId(claim.task_id),
                        attempt=TaskAttempt(claim.attempt),
                        holder=holder,
                        runtime_id=RuntimeId(claim.runtime_id),
                    ).model_dump(mode="python")
                )
            import json

            from corpus_structure.ingest.pdf import pdf_package_versions
            from corpus_structure.ingest.pdf_build_spool import (
                PdfBuildSpool,
                PdfSpoolPremises,
                clone_recovery_entries,
                selected_replay_bytes,
                verify_spool_recovery,
            )
            from corpus_structure.ingest.pdf_stream_types import PdfPageRecovery


            premises = PdfSpoolPremises(
                basis,
                source_digest,
                recipe.digest,
                schema_digest,
                payload_family.schema_digest,
                assets.digest if assets is not None else None,
                pdf_package_versions(),
            )
            recovered = verify_spool_recovery(
                directory,
                build_id=build.build_id,
                task_id=claim.task_id,
                before_attempt=claim.attempt,
                premises=premises,
                check_active=check_active,
            )

            spool = PdfBuildSpool(
                directory,
                build_id=build.build_id,
                task_id=claim.task_id,
                attempt=claim.attempt,
                holder=holder,
                check_active=check_active,
            )
            with _pdf_transaction(engine, cancellation) as connection:
                producer_id = calls.register_pdf_spool_producer(
                    connection,
                    build_id=build.build_id,
                    task_id=TaskId(claim.task_id),
                    attempt=TaskAttempt(claim.attempt),
                    holder=holder,
                    runtime_id=RuntimeId(claim.runtime_id),
                    writer_device=spool.writer_lease.identity["device"],
                    writer_inode=spool.writer_lease.identity["inode"],
                    premises_bytes=premises.to_bytes(),
                )
            spool.declare_premises(premises, producer_id)
            replay_root = spool.root
            copied_paths = set()

            def register_contributor(recovery, selected):
                recovery.check_owned()
                with _pdf_transaction(engine, cancellation) as connection:
                    calls.register_pdf_spool_contributor(
                        connection,
                        build_id=build.build_id,
                        task_id=TaskId(claim.task_id),
                        attempt=TaskAttempt(claim.attempt),
                        holder=holder,
                        runtime_id=RuntimeId(claim.runtime_id),
                        producer_id=recovery.owner.producer_id,
                        manifest_bytes=recovery.manifest,
                        selected_replays=selected_replay_bytes(recovery.root, selected),
                    )

            reply = None
            recovery_pages = []
            # A complete verified record spool precedes any new native setup.
            for recovery in reversed(recovered):
                prior_reply = recovery.complete_reply()
                if prior_reply is not None:
                    ready = recovery.ready_pages(payload_family)
                    if {page.page_no for page in ready} != {
                        page.page_no for page in prior_reply.page_replays
                    }:
                        raise ValueError(
                            "completed PDF spool differs from complete native page custody"
                        )
                    selected = recovery.entries
                    register_contributor(recovery, selected)
                    copied = clone_recovery_entries(
                        recovery, spool, selected, prefix="recovered-complete"
                    )
                    copied_paths.update(clone.path for clone in copied.values())
                    from dataclasses import replace

                    reply = replace(
                        prior_reply,
                        page_replays=tuple(
                            copied[entry.path] for entry in prior_reply.page_replays
                        ),
                        record_replays=tuple(
                            copied[entry.path] for entry in prior_reply.record_replays
                        ),
                        companion_sets=tuple(
                            replace(
                                value, replays=tuple(copied[entry.path] for entry in value.replays)
                            )
                            for value in prior_reply.companion_sets
                        ),
                        certification=copied[prior_reply.certification.path]
                        if prior_reply.certification is not None
                        else None,
                        access_replay=copied[prior_reply.access_replay.path]
                        if prior_reply.access_replay is not None
                        else None,
                    )
                    break
            if reply is None:
                selected_pages = set()
                preparation_identity = None
                for index, recovery in enumerate(reversed(recovered)):
                    pages = []
                    for page in recovery.ready_pages(payload_family):
                        if page.page_no in selected_pages:
                            continue
                        if (
                            preparation_identity is not None
                            and page.preparation_identity != preparation_identity
                        ):
                            raise ValueError(
                                "PDF prior attempts have different determining native preparations"
                            )
                        preparation_identity = page.preparation_identity
                        pages.append(page)
                        selected_pages.add(page.page_no)
                    if not pages:
                        continue
                    numbers = {page.page_no for page in pages}
                    selected = tuple(
                        entry
                        for entry in recovery.entries
                        if (
                            entry.family == "native_preparation"
                            or (
                                entry.page_no in numbers
                                and entry.family in {"page", "candidate_payload", "native-raster"}
                            )
                        )
                    )
                    register_contributor(recovery, selected)
                    # Current preparation is independently observed by the child;
                    # retained preparation remains the contributor's provenance.
                    copied = clone_recovery_entries(
                        recovery,
                        spool,
                        tuple(entry for entry in selected if entry.family != "native_preparation"),
                        prefix=f"recovered-{index}",
                    )
                    copied_paths.update(clone.path for clone in copied.values())
                    recovery_pages.extend(
                        PdfPageRecovery(
                            page.page_no,
                            copied[page.page.path],
                            copied[page.candidate.path],
                            page.preparation_identity,
                        )
                        for page in pages
                    )
            if reply is None:
                worker = PdfWorker(recipe, assets=assets, writer_lease=spool.writer_lease)

            def retain_replay(replay: PdfReplayRef) -> None:
                if replay.family not in {
                    *UPLOAD_STAGE_FAMILIES,
                    "page",
                    "candidate_payload",
                    "native_preparation",
                    "native_completion",
                    "producer_certification",
                    "producer_access",
                    *(
                        "prepared_companion:" + name
                        for name in ("companion", "field", "stream", "part")
                    ),
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

            from corpus_structure.semantic.pdf_shared_streams import PdfSharedStreamTransfer
            shared_transfer = PdfSharedStreamTransfer()

            def adopt_replay(replay: PdfReplayRef) -> None:
                check_active()
                replay.verify()
                if replay.family not in UPLOAD_STAGE_FAMILIES:
                    raise ValueError("unknown private PDF replay family")
                batches = ipc_replay_batches([replay], check_active)
                try:
                    for batch in batches:
                        with _pdf_transaction(engine, cancellation) as connection:
                            if shared_transfer.omit_verified_parts(connection, build, batch.relations):
                                continue
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

            if reply is None:
                if worker is None:
                    raise ValueError("PDF stream requires its active physical worker")
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
                        validation_contract=validation_contract,
                        lowering_identity=lowering_identity,
                        on_replay=retain_replay,
                        check_active=check_active,
                        recovery_pages=tuple(sorted(recovery_pages, key=lambda page: page.page_no)),
                    )
            if reply.conversion_status != "success":
                raise RuntimeError(
                    "native streaming conversion did not complete: " + "; ".join(reply.errors)
                )
            spool.complete(reply)
            fresh_entries = tuple(
                entry for entry in spool.entries if entry.path not in copied_paths
            )
            if fresh_entries:
                with _pdf_transaction(engine, cancellation) as connection:
                    calls.register_pdf_spool_contributor(
                        connection,
                        build_id=build.build_id,
                        task_id=TaskId(claim.task_id),
                        attempt=TaskAttempt(claim.attempt),
                        holder=holder,
                        runtime_id=RuntimeId(claim.runtime_id),
                        producer_id=producer_id,
                        manifest_bytes=spool.path.read_bytes(),
                        selected_replays=selected_replay_bytes(spool.root, fresh_entries),
                    )
            # Certification was computed over the actual complete output and
            # these exact prepared files before any database staging begins.
            if reply.certification is None or reply.access_replay is None:
                raise ValueError("native PDF publication has no producer certification")
            from corpus_structure.semantic.pdf_certification import PdfProducerCertification
            from corpus_structure.semantic.pdf_publication import (
                adopt_prepared_pdf_companion_batches,
                prepared_pdf_companion_batches,
                record_pdf_producer_certification,
                stage_pdf_access_projection,
            )

            reply.certification.verify()
            reply.access_replay.verify()
            certification = PdfProducerCertification(
                **json.loads(reply.certification.path.read_bytes())
            )
            if (
                certification.kind != "native"
                or certification.lowering_identity != lowering_identity
            ):
                raise ValueError("native PDF producer used another captured lowering basis")
            for replay in reply.record_replays:
                adopt_replay(replay)
            for prepared in reply.companion_sets:
                batches = prepared_pdf_companion_batches(prepared)
                try:
                    with _pdf_transaction(engine, cancellation) as connection:
                        adopt_prepared_pdf_companion_batches(
                            connection,
                            build,
                            batches,
                            prepared.replay_key,
                            cancellation=cancellation,
                        )
                finally:
                    batches.close()
            stage_pdf_access_projection(
                engine,
                build,
                reply.access_replay.path,
                cancellation=cancellation,
                check_active=check_active,
            )
            with _pdf_transaction(engine, cancellation) as connection:
                record_pdf_producer_certification(connection, build, certification)
            check_active()
        finally:
            # Stop native borrowers before ending claim maintenance or source custody.
            if worker is not None and (not worker.closed or worker.pid is not None):
                worker.close()
            if spool is not None:
                spool.close()
            for recovery in recovered:
                recovery.close()
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
            connection,
            task_id=claim.task_id,
            attempt=claim.attempt,
            holder=holder,
            replay_key="product:" + product_key,
        )
        if existing is not None:
            _check_pdf_build_premises(
                existing,
                claim,
                source_digest,
                sha256(recipe_bytes).hexdigest(),
                schema_digest,
                kind,
            )
            if existing.published is not None:
                return existing.published
            if existing.state not in {"open", "frozen"}:
                raise ValueError("abandoned PDF production requires a successor task")
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
            recipe_bytes=recipe_bytes,
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
        engine,
        claim,
        holder,
        product_key=draft.product_key,
        kind=draft.kind,
        source_digest=source_digest,
        recipe_bytes=draft.recipe_bytes,
        schema_digest=schema_digest,
        check_active=check_active,
        cancellation=cancellation,
    )
    if completed is not None:
        return completed
    with _pdf_transaction(engine, cancellation) as connection:
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
    from corpus_structure.semantic.pdf_contracts import (
        integrated_metadata_policy,
        pdf_context_for_task,
    )
    from corpus_structure.semantic.pdf_lowering import require_lowering_identity
    from corpus_structure.semantic.pdf_payload_validation import metadata_classes
    from corpus_structure.semantic.pdf_payloads import prepare_payload_family

    with _pdf_transaction(engine, cancellation) as connection:
        context = pdf_context_for_task(connection, claim.task_id)
        payload_family = prepare_payload_family(context)
        lowering_identity = require_lowering_identity(context)
    validation_contract = {
        "schemas": {
            kind: context.boundary.json_schema(cls) for kind, cls in metadata_classes().items()
        },
        "publication_kind": draft.kind,
        "integrated_metadata_policy": integrated_metadata_policy(context)
        if draft.kind == "integrated"
        else None,
    }
    from corpus_structure.ingest.pdf_build_spool import PdfBuildSpool

    with PdfBuildSpool(
        directory,
        build_id=build.build_id,
        task_id=claim.task_id,
        attempt=claim.attempt,
        holder=holder,
        check_active=check_active,
    ) as draft_spool:
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

        from corpus_structure.semantic.pdf_shared_streams import PdfSharedStreamTransfer
        shared_transfer = PdfSharedStreamTransfer()

        def adopt(replay: PdfReplayRef) -> None:
            batches = ipc_replay_batches((replay,), check_active)
            try:
                for batch in batches:
                    check_active()
                    with _pdf_transaction(engine, cancellation) as connection:
                        if shared_transfer.omit_verified_parts(connection, build, batch.relations):
                            continue
                        adopt_pdf_batch(
                            connection,
                            build,
                            batch.replay_key,
                            batch.relations,
                            cancellation=cancellation,
                        )
            finally:
                batches.close()

        native_replays = streamed.write_record_batches(
            owner / "records",
            build_id=build.build_id,
            release_id=build.release_id,
            source_digest=source_digest,
            on_batch=draft_spool.append,
        )
        from corpus_structure.semantic.pdf_certification import write_retained_pdf_replays

        if draft.retained_serialization is not None:
            native_replays += write_retained_pdf_replays(
                owner / "retained",
                build,
                draft.retained_serialization,
                check_active=check_active,
                on_replay=draft_spool.append,
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
        import json

        from corpus_structure.semantic import _pdf_native_calls as calls
        from corpus_structure.semantic.identifiers import TaskAttempt, TaskId
        from corpus_structure.semantic.pdf_certification import (
            PdfProducerPayloads,
            write_pdf_companion_sets,
        )
        from corpus_structure.semantic.pdf_publication import (
            adopt_prepared_pdf_companion_batches,
            prepared_pdf_companion_batches,
            record_pdf_producer_certification,
            stage_pdf_access_projection,
        )

        prepared_sets = write_pdf_companion_sets(
            owner / "prepared-companions",
            build,
            companions,
            payload_family=payload_family,
            check_active=check_active,
            on_replay=draft_spool.append,
        )
        projection = owner / "producer-access.jsonl"
        payloads = PdfProducerPayloads(owner / "producer-payloads.sqlite", validation_contract)
        try:
            payloads.add_replays(native_replays, check_active=check_active)
            payloads.add_companion_replays(prepared_sets, check_active=check_active)
            pins = payloads.target_pins()
            target_meanings = {}
            for start in range(0, len(pins), 64):
                selected = pins[start : start + 64]
                with _pdf_transaction(engine, cancellation) as connection:
                    encoded = calls.read_pdf_certification_targets(
                        connection,
                        build_id=build.build_id,
                        task_id=TaskId(build.task_id),
                        attempt=TaskAttempt(build.attempt),
                        holder=build.holder,
                        targets=[list(pin) for pin in selected],
                    )
                values = json.loads(encoded)
                if {tuple(value["pin"]) for value in values} != set(selected) or len(values) != len(
                    selected
                ):
                    raise ValueError(
                        "PDF producer targets differ from the authenticated input inventory"
                    )
                target_meanings.update((tuple(value["pin"]), value["meaning"]) for value in values)
            certification = payloads.certify(
                draft.document,
                projection,
                release_id=build.release_id,
                source_digest=source_digest,
                recipe_digest=recipe_digest,
                schema_digest=schema_digest,
                kind=draft.kind,
                lowering_identity=lowering_identity,
                target_meanings=target_meanings,
            )
        finally:
            payloads.close()
        import os

        from corpus_structure.ingest.pdf_streaming import _atomic_bytes, _ref

        with projection.open("rb") as source:
            os.fsync(source.fileno())
        draft_spool.append(_ref(projection, "producer_access"))
        draft_spool.append(
            _atomic_bytes(
                owner / "producer-certification.json",
                certification.to_bytes(),
                "producer_certification",
            )
        )
        for replay in native_replays:
            adopt(replay)
        for prepared in prepared_sets:
            batches = prepared_pdf_companion_batches(prepared)
            try:
                with _pdf_transaction(engine, cancellation) as connection:
                    adopt_prepared_pdf_companion_batches(
                        connection, build, batches, prepared.replay_key, cancellation=cancellation
                    )
            finally:
                batches.close()
        stage_pdf_access_projection(
            engine, build, projection, cancellation=cancellation, check_active=check_active
        )
        with _pdf_transaction(engine, cancellation) as connection:
            record_pdf_producer_certification(connection, build, certification)
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
    claim: PdfProducerClaim,
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
        engine,
        claim,
        holder,
        product_key="native",
        kind="native",
        source_digest=source_digest,
        recipe_bytes=request.recipe.to_bytes(),
        schema_digest=schema_digest,
        check_active=check_active,
        cancellation=cancellation,
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
