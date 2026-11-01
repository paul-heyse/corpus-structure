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
from typing import TYPE_CHECKING, Any, Protocol

import pyarrow as pa
from sqlalchemy import Engine

from corpus_structure.semantic.claim_lifetime import maintained_claims
from corpus_structure.semantic.operation_results import ClaimedTask

if TYPE_CHECKING:
    from corpus_structure.ingest.pdf import PdfRecipe
    from corpus_structure.ingest.pdf_assets import PreparedPdfAssets
    from corpus_structure.ingest.pdf_stream_types import PdfReplayRef
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

                worker.stream(
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
