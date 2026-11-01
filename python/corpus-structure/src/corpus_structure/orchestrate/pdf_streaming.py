"""Private PDF producer execution; receipts never imply published source readiness.

The caller supplies an owned producer context so native handles, spool readers and
borrowed buffers settle before claim maintenance ends. Only short adoption
transactions own database connections; no connection enters native computation.
"""

from __future__ import annotations

from collections.abc import Callable, Generator, Iterable, Iterator, Mapping
from contextlib import AbstractContextManager, ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Protocol

import pyarrow as pa
from sqlalchemy import Engine

from corpus_structure.semantic.claim_lifetime import maintained_claims
from corpus_structure.semantic.operation_results import ClaimedTask

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


def run_private_pdf_build(
    engine: Engine,
    claim: ClaimedTask,
    holder: str,
    *,
    source_digest: str,
    recipe_digest: str,
    schema_digest: str,
    replay_key: str,
    producer: PrivatePdfProducer,
    on_adopted: Callable[[PdfStageReceipt], None] | None = None,
) -> PdfBuildRef:
    """Adopt bounded producer batches under existing fences, leaving the build private.

    Failure retains already committed progress. Explicit resume/abandon is owned
    by the protected staging API, never implicit conversion or terminal UnitResult.
    A callback failure propagates after commit; retry observes the same receipt.
    """
    from corpus_structure.semantic.pdf_staging import adopt_pdf_batch, begin_pdf_build

    with maintained_claims(engine, [claim], holder) as check_active:
        check_active()
        with engine.begin() as connection:
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
                    with engine.begin() as connection:
                        receipt = adopt_pdf_batch(
                            connection, build, batch.replay_key, batch.relations
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
    claim: ClaimedTask,
    holder: str,
    *,
    original: Path,
    recipe: PdfRecipe,
    assets: PreparedPdfAssets | None,
    directory: Path,
    source_digest: str,
    schema_digest: str,
    replay_key: str,
    observation_replay: PdfReplayRef | None = None,
    structural_pin: dict[str, Any] | None = None,
    integration_policy: dict[str, Any] | None = None,
    on_adopted: Callable[[PdfStageReceipt], None] | None = None,
) -> PdfBuildRef:
    """Run the actual finite native worker into protected private record custody.

    Page replay callbacks are flow-control acknowledgements, not document
    publication. Source ownership ends after the child has settled; spools retain
    replay/failure evidence for explicit resume or authenticated cleanup.
    """
    from corpus_structure.ingest.pdf_stream_types import OwnedPdfSource
    from corpus_structure.ingest.pdf_worker import PdfWorker
    from corpus_structure.semantic.pdf_staging import (
        STAGE_FAMILIES,
        adopt_pdf_batch,
        artifact_profile,
        begin_pdf_build,
    )

    if recipe.recipe_id != "docling-standard-pdf-stream-v1":
        raise ValueError("private streaming requires its explicitly retained stream recipe")
    # Original/recipe custody must precede this entry; begin checks it natively.
    directory.mkdir(parents=True, exist_ok=True)
    owner = OwnedPdfSource.acquire(original, directory, expected_digest=source_digest)
    worker = None
    entered = False
    try:
        worker = PdfWorker(recipe, assets=assets)
        with maintained_claims(engine, [claim], holder) as check_active:
            entered = True
            try:
                with engine.begin() as connection:
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
                replay_root = directory / build.build_id
                replay_root.mkdir(exist_ok=True)

                def adopt_replay(replay: PdfReplayRef) -> None:
                    check_active()
                    replay.verify()
                    if replay.family == "page":
                        import json
                        from hashlib import file_digest

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
                        candidates = replay.path.with_name(f"candidate-{number:06}.json")
                        if candidates.exists():
                            with candidates.open("rb") as source:
                                digest = file_digest(source, "sha256").hexdigest()
                            retained.append(
                                (
                                    "candidates",
                                    PdfReplayRef(
                                        candidates, digest, candidates.stat().st_size, "candidates"
                                    ),
                                    artifact_profile("candidates"),
                                )
                            )
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
                                with engine.begin() as connection:
                                    receipt = adopt_pdf_batch(
                                        connection,
                                        build,
                                        f"page:{number}:{suffix}:{artifact.digest}:{index}",
                                        {family: (batch,)},
                                    )
                                if on_adopted is not None:
                                    on_adopted(receipt)
                        if candidates.exists():
                            from corpus_structure.semantic.pdf_publication import (
                                adopt_pdf_companion_batch,
                            )

                            with candidates.open() as candidate_file:
                                candidate_value = json.load(candidate_file)
                            with engine.begin() as connection:
                                adopt_pdf_companion_batch(
                                    connection,
                                    build,
                                    "native_metadata",
                                    (
                                        {
                                            "kind": "inline_candidate_pages",
                                            "ordinal": number,
                                            "value": candidate_value,
                                        },
                                    ),
                                    replay_key=f"page:{number}:candidate-metadata",
                                )
                        return
                    if replay.family == "companion:occurrence":
                        import json

                        from corpus_structure.semantic.pdf_publication import (
                            adopt_pdf_companion_batch,
                        )
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

                                with engine.begin() as connection:
                                    adopt_pdf_companion_batch(
                                        connection,
                                        build,
                                        "occurrence",
                                        occurrences(),
                                        replay_key=f"ipc-companion:{replay.digest}:{ordinal}",
                                        start_ordinal=batch.column("ordinal")[0].as_py(),
                                    )
                        return
                    if replay.family not in STAGE_FAMILIES:
                        raise ValueError("unknown private PDF replay family")
                    batches = ipc_replay_batches([replay], check_active)
                    try:
                        for batch in batches:
                            with engine.begin() as connection:
                                receipt = adopt_pdf_batch(
                                    connection, build, batch.replay_key, batch.relations
                                )
                            if on_adopted is not None:
                                on_adopted(receipt)
                    finally:
                        batches.close()

                reply = worker.stream(
                    owner.reference,
                    spool_root=replay_root / "pages",
                    record_root=replay_root / "records",
                    build_id=build.build_id,
                    release_id=build.release_id,
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

                with engine.begin() as connection:
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
                            with engine.begin() as connection:
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
                                )
                check_active()
            finally:
                # Stop native borrowers before ending claim maintenance or source custody.
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
    claim: ClaimedTask,
    holder: str,
    replays: Iterable[PdfReplayRef],
    *,
    on_adopted: Callable[[PdfStageReceipt], None] | None = None,
) -> PdfBuildRef:
    """Explicitly resume exact durable IPC output without invoking recognition again."""
    from corpus_structure.semantic.contracts import require_database_operation
    from corpus_structure.semantic.pdf_staging import adopt_pdf_batch, resume_pdf_build

    if build.task_id != claim.task_id or build.release_id != claim.release_id:
        raise ValueError("private PDF replay task/release differs from original build")
    with maintained_claims(engine, [claim], holder) as check_active:
        with engine.begin() as connection:
            require_database_operation(connection, build.release_id, "stage_pdf_producer")
            resumed = resume_pdf_build(connection, build, attempt=claim.attempt, holder=holder)
        batches = ipc_replay_batches(replays, check_active)
        try:
            for batch in batches:
                check_active()
                with engine.begin() as connection:
                    receipt = adopt_pdf_batch(
                        connection, resumed, batch.replay_key, batch.relations
                    )
                if on_adopted is not None:
                    on_adopted(receipt)
        finally:
            batches.close()
        check_active()
    return resumed


def publish_pdf_record_draft(
    engine: Engine,
    claim: ClaimedTask,
    holder: str,
    draft: PdfRecordPublicationDraft,
    *,
    directory: Path,
    check_active: Callable[[], None],
) -> PublishedPdfDocumentRef:
    """Publish the actual method result through private rows and frozen validation.

    Called by the existing leased method owner. Conversion/selection has finished;
    no connection is retained while lowering or executing native validation. A
    failure leaves authenticated private progress and original custody available.
    """
    import json
    from hashlib import sha256
    from uuid import uuid4

    from corpus_structure.ingest.pdf_streaming import PdfStreamSpool, StreamingPdfResult
    from corpus_structure.semantic.pdf_publication import (
        adopt_pdf_companion_batch,
        freeze_pdf_build,
        inspect_pdf_build,
        prepare_pdf_build,
        retain_pdf_stage_recipe,
        seal_pdf_build,
        validate_pdf_build,
    )
    from corpus_structure.semantic.pdf_staging import (
        MAX_BATCH_BYTES,
        adopt_pdf_batch,
        begin_pdf_build,
        resume_pdf_build,
    )

    check_active()
    source_digest = sha256(draft.original).hexdigest()
    recipe_digest = sha256(draft.recipe_bytes).hexdigest()
    schema_digest = sha256(draft.schema_bytes).hexdigest()
    with engine.begin() as connection:
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
                with engine.begin() as connection:
                    adopt_pdf_batch(connection, build, batch.replay_key, batch.relations)
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
        pending: list[Mapping[str, Any]] = []
        size = 0
        ordinal = 0
        delivered = 0

        def flush(family=family, pending=pending) -> None:
            nonlocal size, ordinal, delivered
            if not pending:
                return
            check_active()
            with engine.begin() as connection:
                adopt_pdf_companion_batch(
                    connection,
                    build,
                    family,
                    pending,
                    replay_key=f"companion:{family}:{ordinal}",
                    start_ordinal=delivered,
                )
            ordinal += 1
            delivered += len(pending)
            pending.clear()
            size = 0

        for row in records:
            row_size = len(json.dumps(row, ensure_ascii=False, allow_nan=False).encode())
            if pending and size + row_size > MAX_BATCH_BYTES // 2:
                flush()
            pending.append(row)
            size += row_size
        flush()
    if draft.retained_serialization is not None:
        _adopt_retained_serialization(engine, build, draft.retained_serialization, check_active)
    check_active()
    with engine.begin() as connection:
        frozen = freeze_pdf_build(connection, build, kind=draft.kind)
    with engine.begin() as connection:
        prepare_pdf_build(connection, frozen)
    validate_pdf_build(engine, frozen, check_active=check_active)
    check_active()
    with engine.begin() as connection:
        return seal_pdf_build(connection, frozen, product_key=draft.product_key)


def produce_published_pdf_records(
    engine: Engine,
    claim: ClaimedTask,
    holder: str,
    request: PdfRecordProducerRequest,
    *,
    directory: Path,
    check_active: Callable[[], None],
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

    source_digest = sha256(request.original).hexdigest()
    recipe_digest = request.recipe.digest
    schema_digest = sha256(request.schema_bytes).hexdigest()
    frozen = None
    check_active()
    with engine.begin() as connection:
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
        return _finish_frozen_pdf(engine, frozen, "native", check_active)
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
    )
    check_active()
    with engine.begin() as connection:
        frozen = freeze_pdf_build(connection, build, kind="native")
    with engine.begin() as connection:
        prepare_pdf_build(connection, frozen)
    validate_pdf_build(engine, frozen, check_active=check_active)
    check_active()
    with engine.begin() as connection:
        return seal_pdf_build(connection, frozen, product_key="native")


def migrate_retained_pdf_envelope(
    engine: Engine,
    claim: ClaimedTask,
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
) -> PublishedPdfDocumentRef:
    """Explicit qualified storage derivation; never repeats source inference.

    The existing task must already represent this migration/adoption recipe.
    Retained bytes are checked while decoding, before the new build is frozen.
    This writes only private/admitted products for that task, not defaults or a
    completed knowledge result. Original historical products remain unchanged.
    """
    from uuid import uuid4

    from corpus_structure.ingest.pdf_retained_stream import retained_pdf_draft

    owner = directory / uuid4().hex
    owner.mkdir(parents=True)
    with (
        maintained_claims(engine, [claim], holder) as check_active,
        retained_pdf_draft(
            path,
            expected_sha256=expected_sha256,
            product_key=product_key,
            original=original,
            schema_bytes=schema_bytes,
            recipe_bytes=recipe_bytes,
            directory=owner / "companions",
            kind=kind,
        ) as draft,
    ):
        return publish_pdf_record_draft(
            engine,
            claim,
            holder,
            draft,
            directory=owner / "publication",
            check_active=check_active,
        )


def _adopt_retained_serialization(engine, build, retained, check_active):
    import gzip
    from hashlib import sha256

    from corpus_structure.semantic.pdf_record_identity import IdentityFold, emit_parts
    from corpus_structure.semantic.pdf_staging import adopt_pdf_batch, stage_schema

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
                with engine.begin() as connection:
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
                    )
                index += 1
                pending.clear()
        if pending:
            with engine.begin() as connection:
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
    with engine.begin() as connection:
        adopt_pdf_batch(
            connection,
            build,
            "retained:stream",
            {
                "artifact_stream": (
                    pa.RecordBatch.from_pylist([row], schema=stage_schema("artifact_stream")),
                ),
            },
        )


def _check_pdf_build_premises(
    state: PdfBuildState,
    claim: ClaimedTask,
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
) -> PublishedPdfDocumentRef:
    from corpus_structure.semantic.pdf_publication import (
        prepare_pdf_build,
        seal_pdf_build,
        validate_pdf_build,
    )

    check_active()
    with engine.begin() as connection:
        prepare_pdf_build(connection, frozen)
    validate_pdf_build(engine, frozen, check_active=check_active)
    check_active()
    with engine.begin() as connection:
        return seal_pdf_build(connection, frozen, product_key=product_key)


def resume_pdf_publication(
    engine: Engine,
    claim: ClaimedTask,
    holder: str,
    *,
    product_key: str,
    source_digest: str,
    recipe_digest: str,
    schema_digest: str,
    kind: Literal["native", "integrated"],
    check_active: Callable[[], None],
) -> PublishedPdfDocumentRef:
    """Explicit recovery over the same frozen union; accepts no replacement draft."""
    from dataclasses import replace

    from corpus_structure.semantic.pdf_publication import inspect_pdf_build
    from corpus_structure.semantic.pdf_staging import resume_pdf_build

    check_active()
    with engine.begin() as connection:
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
    return _finish_frozen_pdf(engine, frozen, product_key, check_active)
