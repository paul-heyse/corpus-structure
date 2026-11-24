"""Fenced private PDF record ingestion; receipts are not admitted document products."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, fields

import pyarrow as pa
from sqlalchemy import Connection

from corpus_structure.core.db.lifetime import BorrowerCancellation
from corpus_structure.model.compiled import model_projection, model_source

from . import _pdf_native_calls as calls
from .arrow_transfer import ArrowWriteProfile, copy_arrow_stream
from .identifiers import ReleaseId, TaskAttempt, TaskId
from .pdf_record_model import record_arrow_schema, record_write_profile
from .pdf_replay_transport import PdfReplayBinding, bind_copy_batch

STAGE_FAMILIES = {
    "header": "ops.pdf_stage_document",
    "native": "ops.pdf_stage_native",
    "membership": "ops.pdf_stage_membership",
    "reference": "ops.pdf_stage_reference",
    "artifact_stream": "ops.pdf_stage_artifact_stream",
}


# Fixed incoming part packets have no persistent per-build relation.
UPLOAD_STAGE_FAMILIES = {**STAGE_FAMILIES, "artifact_part": "ops.pdf_stage_artifact_part"}


def stage_upload_profile(*, physical_sources: Mapping[str, bytes] | None = None) -> dict[str, int]:
    import json

    import yaml

    source = (
        model_source("pdf-staging.yaml")
        if physical_sources is None
        else physical_sources["pdf-staging.yaml"]
    )
    return json.loads(yaml.safe_load(source)["annotations"]["pds:upload_profile"])


MAX_BATCH_BYTES = stage_upload_profile()["max_bytes"]
MAX_BATCH_ROWS = stage_upload_profile()["max_rows"]


@dataclass(frozen=True, slots=True)
class PdfBuildRef:
    build_id: str
    task_id: TaskId
    attempt: TaskAttempt
    holder: str
    release_id: ReleaseId
    source_digest: str
    recipe_digest: str
    schema_digest: str
    _write_profiles: Mapping[str, ArrowWriteProfile] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        from types import MappingProxyType

        object.__setattr__(
            self,
            "_write_profiles",
            MappingProxyType(
                {
                    target: record_write_profile(target, release_id=self.release_id)
                    for target in UPLOAD_STAGE_FAMILIES.values()
                }
            ),
        )

    @property
    def product_id(self) -> str:
        return self.build_id

    @property
    def revision_id(self) -> str:
        return self.build_id


@dataclass(frozen=True, slots=True)
class PdfStageReceipt:
    build_id: str
    replay_key: str
    content_digest: str
    row_count: int


def stage_relation(name: str) -> str:
    if name in UPLOAD_STAGE_FAMILIES:
        return UPLOAD_STAGE_FAMILIES[name]
    if name in UPLOAD_STAGE_FAMILIES.values():
        return name
    originals = {
        "ops.pdf_record_document": "header",
        "kb.pdf_record_native": "native",
        "kb.pdf_record_membership": "membership",
        "kb.pdf_record_reference": "reference",
        "ops.pdf_artifact_stream": "artifact_stream",
    }
    if name in originals:
        return UPLOAD_STAGE_FAMILIES[originals[name]]
    raise ValueError(f"unknown private PDF stage family: {name}")


def stage_schema(name: str) -> pa.Schema:
    return record_arrow_schema(stage_relation(name))


def stage_schemas() -> dict[str, pa.Schema]:
    return {name: stage_schema(name) for name in UPLOAD_STAGE_FAMILIES}


@model_projection
def _profile_definitions():
    import json

    import yaml

    annotations = yaml.safe_load(model_source("pdf-staging.yaml"))["annotations"]
    return json.loads(annotations["pds:artifact_profiles"])


def artifact_profile(kind: str) -> str:
    """Resolve fixed producer artifact encodings under process source custody."""
    profiles = _profile_definitions()
    if kind not in profiles:
        raise ValueError(f"unknown private PDF producer artifact: {kind}")
    return profiles[kind]


def begin_pdf_build(
    conn: Connection,
    *,
    task_id: int,
    attempt: int,
    holder: str,
    source_digest: str,
    recipe_digest: str,
    schema_digest: str,
    replay_key: str,
    release_id: str | None = None,
) -> PdfBuildRef:
    row = calls.begin_pdf_build(
        conn,
        task_id=TaskId(task_id),
        attempt=TaskAttempt(attempt),
        holder=holder,
        source_digest=source_digest,
        recipe_digest=recipe_digest,
        schema_digest=schema_digest,
        replay_key=replay_key,
    ).model_dump(mode="python")
    if release_id is not None and row["release_id"] != release_id:
        raise ValueError("PDF build release differs from requested release")
    return PdfBuildRef(**{f.name: row[f.name] for f in fields(PdfBuildRef) if f.init})


def adopt_pdf_batch(
    conn: Connection,
    build: PdfBuildRef,
    replay_key: str,
    relations: Mapping[str, Iterable[pa.RecordBatch] | pa.RecordBatchReader],
    *,
    cancellation: BorrowerCancellation | None = None,
) -> PdfStageReceipt:
    """COPY and adopt in the caller's transaction; never commit or hold a lease here."""
    if cancellation is not None:
        cancellation.check_active()
    names = [stage_relation(name) for name in relations]
    if len(set(names)) != len(names):
        raise ValueError("one input stream per stage relation")
    calls.prepare_pdf_stage(
        conn,
        build_id=build.build_id,
        task_id=TaskId(build.task_id),
        attempt=TaskAttempt(build.attempt),
        holder=build.holder,
    )
    count = size = 0

    def check_upload(batch: pa.RecordBatch) -> None:
        nonlocal count, size
        count += batch.num_rows
        size += batch.nbytes
        if count > MAX_BATCH_ROWS or size > MAX_BATCH_BYTES:
            raise ValueError("private PDF Arrow batch exceeds bounded transfer profile")

    for name, batches in relations.items():
        target = stage_relation(name)
        profile = build._write_profiles[target]
        copy_arrow_stream(
            conn,
            profile,
            target=("pg_temp", "ps_" + target.split(".")[1]),
            batches=(
                bind_copy_batch(
                    batch, profile.schema, PdfReplayBinding(build.build_id, build.release_id)
                )
                for batch in batches
            ),
            before_encode=check_upload,
            cancellation=cancellation,
        )
    if cancellation is not None:
        cancellation.check_active()
    row = calls.adopt_pdf_batch(
        conn,
        build_id=build.build_id,
        task_id=TaskId(build.task_id),
        attempt=TaskAttempt(build.attempt),
        holder=build.holder,
        replay_key=replay_key,
    )
    return PdfStageReceipt(row.build_id, row.replay_key, row.content_digest, row.row_count)


def inspect_pdf_progress(conn: Connection, build: PdfBuildRef) -> tuple[PdfStageReceipt, ...]:
    rows = calls.inspect_pdf_progress(
        conn,
        build_id=build.build_id,
        task_id=TaskId(build.task_id),
        attempt=TaskAttempt(build.attempt),
        holder=build.holder,
    )
    return tuple(
        PdfStageReceipt(row.build_id, row.replay_key, row.content_digest, row.row_count)
        for row in rows
    )


def resume_pdf_build(
    conn: Connection, build: PdfBuildRef, *, attempt: int, holder: str
) -> PdfBuildRef:
    calls.resume_pdf_build(
        conn,
        build_id=build.build_id,
        task_id=TaskId(build.task_id),
        attempt=TaskAttempt(attempt),
        holder=holder,
    )
    from dataclasses import replace

    return replace(build, attempt=TaskAttempt(attempt), holder=holder)


def abandon_pdf_build(conn: Connection, build: PdfBuildRef) -> None:
    calls.abandon_pdf_build(
        conn,
        build_id=build.build_id,
        task_id=TaskId(build.task_id),
        attempt=TaskAttempt(build.attempt),
        holder=build.holder,
    )
