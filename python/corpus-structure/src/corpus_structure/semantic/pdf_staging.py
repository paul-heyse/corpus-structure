"""Fenced private PDF record ingestion; receipts are not admitted document products."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, fields
from typing import Any

import pyarrow as pa
from sqlalchemy import Connection, text

from corpus_structure.core.db.lifetime import BorrowerCancellation

from .arrow_transfer import ArrowWriteProfile, copy_arrow_stream
from .pdf_record_model import record_arrow_schema, record_write_profile

STAGE_FAMILIES = {
    "header": "ops.pdf_stage_document",
    "native": "ops.pdf_stage_native",
    "membership": "ops.pdf_stage_membership",
    "reference": "ops.pdf_stage_reference",
    "artifact_stream": "ops.pdf_stage_artifact_stream",
    "artifact_part": "ops.pdf_stage_artifact_part",
}


def stage_upload_profile() -> dict[str, int]:
    import json
    from importlib.resources import files

    import yaml

    source = files("corpus_structure").joinpath("model/semantic/pdf-staging.yaml").read_bytes()
    return json.loads(yaml.safe_load(source)["annotations"]["pds:upload_profile"])


MAX_BATCH_BYTES = stage_upload_profile()["max_bytes"]
MAX_BATCH_ROWS = stage_upload_profile()["max_rows"]


@dataclass(frozen=True, slots=True)
class PdfBuildRef:
    build_id: str
    task_id: int
    attempt: int
    holder: str
    release_id: str
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
                    for target in STAGE_FAMILIES.values()
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
    if name in STAGE_FAMILIES:
        return STAGE_FAMILIES[name]
    if name in STAGE_FAMILIES.values():
        return name
    originals = {
        "ops.pdf_record_document": "header",
        "kb.pdf_record_native": "native",
        "kb.pdf_record_membership": "membership",
        "kb.pdf_record_reference": "reference",
        "ops.pdf_artifact_stream": "artifact_stream",
        "ops.pdf_artifact_part": "artifact_part",
    }
    if name in originals:
        return STAGE_FAMILIES[originals[name]]
    raise ValueError(f"unknown private PDF stage family: {name}")


def stage_schema(name: str) -> pa.Schema:
    return record_arrow_schema(stage_relation(name))


def stage_schemas() -> dict[str, pa.Schema]:
    return {name: stage_schema(name) for name in STAGE_FAMILIES}


def artifact_profile(kind: str) -> str:
    """Resolve fixed producer artifact encodings from their semantic owner.

    Native scalar/opaque encodings retain the PDF record model's separate
    profiles; this lookup describes the finite producer artifacts only.
    """
    import json
    from importlib.resources import files

    import yaml

    source = files("corpus_structure").joinpath("model/semantic/pdf-staging.yaml").read_bytes()
    profiles = json.loads(yaml.safe_load(source)["annotations"]["pds:artifact_profiles"])
    if kind not in profiles:
        raise ValueError(f"unknown private PDF producer artifact: {kind}")
    return profiles[kind]


def _parameters(build: PdfBuildRef) -> dict[str, Any]:
    return dict(
        build=build.build_id, task=build.task_id, attempt=build.attempt, holder=build.holder
    )


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
    row = (
        conn.execute(
            text(
                "SELECT * FROM ops.begin_pdf_build("
                ":task,:attempt,:holder,:source,:recipe,:schema,:key)"
            ),
            dict(
                task=task_id,
                attempt=attempt,
                holder=holder,
                source=source_digest,
                recipe=recipe_digest,
                schema=schema_digest,
                key=replay_key,
            ),
        )
        .mappings()
        .one()
    )
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
    conn.execute(
        text("SELECT ops.prepare_pdf_stage(:build,:task,:attempt,:holder)"), _parameters(build)
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
        copy_arrow_stream(
            conn,
            build._write_profiles[target],
            target=("pg_temp", "ps_" + target.split(".")[1]),
            batches=batches,
            before_encode=check_upload,
            cancellation=cancellation,
        )
    if cancellation is not None:
        cancellation.check_active()
    params = {**_parameters(build), "key": replay_key}
    row = (
        conn.execute(
            text("SELECT * FROM ops.adopt_pdf_batch(:build,:task,:attempt,:holder,:key)"), params
        )
        .mappings()
        .one()
    )
    return PdfStageReceipt(
        row["build_id"], row["replay_key"], row["content_digest"], row["row_count"]
    )


def inspect_pdf_progress(conn: Connection, build: PdfBuildRef) -> tuple[PdfStageReceipt, ...]:
    rows = conn.execute(
        text("SELECT * FROM ops.inspect_pdf_progress(:build,:task,:attempt,:holder)"),
        _parameters(build),
    ).mappings()
    return tuple(
        PdfStageReceipt(row["build_id"], row["replay_key"], row["content_digest"], row["row_count"])
        for row in rows
    )


def resume_pdf_build(
    conn: Connection, build: PdfBuildRef, *, attempt: int, holder: str
) -> PdfBuildRef:
    params = {**_parameters(build), "attempt": attempt, "holder": holder}
    conn.execute(text("SELECT ops.resume_pdf_build(:build,:task,:attempt,:holder)"), params)
    from dataclasses import replace

    return replace(build, attempt=attempt, holder=holder)


def abandon_pdf_build(conn: Connection, build: PdfBuildRef) -> None:
    conn.execute(
        text("SELECT ops.abandon_pdf_build(:build,:task,:attempt,:holder)"), _parameters(build)
    )


def companion_profile(family: str) -> str:
    """Resolve an admitted companion replay encoding from the same semantic owner."""
    import json
    from importlib.resources import files

    import yaml

    source = files("corpus_structure").joinpath("model/semantic/pdf-staging.yaml").read_bytes()
    profile = json.loads(yaml.safe_load(source)["annotations"]["pds:companion_profile"])
    if family not in profile["families"]:
        raise ValueError("unsupported private companion family")
    return profile["prefix"] + family
