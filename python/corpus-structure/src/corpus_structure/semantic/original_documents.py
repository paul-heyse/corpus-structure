"""Acquire original document fact pins; native admission independently proves bytes."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Mapping
from typing import Any
from hashlib import sha256

from sqlalchemy import Connection, select

from .data_operation_demands import RootSubject
from .data_operation_support import OriginalDocumentRef, OriginalSourceSelection
from .identity import canonical_bytes
from .metadata import table
from .identifiers import DocumentId
from .refusals import SemanticRefusal
from .types import PreparedRelease


def original_document_subject(document: str) -> str:
    """Canonical whole-document address, distinct from the original document key."""
    if not isinstance(document, str) or not document:
        raise ValueError("original document address requires its nonempty retained key")
    return "original-document:" + sha256(canonical_bytes({"document": document})).hexdigest()


@dataclass(frozen=True)
class OriginalDocumentAcquisition:
    name: str
    reference: OriginalDocumentRef

    @property
    def root(self) -> RootSubject:
        coordinate = {"document": self.reference.document_key}
        return RootSubject(
            original_document_subject(self.reference.document_key),
            self.reference.document_key,
            canonical_bytes({**coordinate, "scope": "whole-document"}),
        )

    def selection(self) -> OriginalSourceSelection:
        return OriginalSourceSelection(
            self.name,
            canonical_bytes(self.reference.model_dump(mode="json")),
            canonical_bytes([{"scope": "whole-document"}]),
        )


def acquire_original_document_selection(
    connection: Connection,
    *,
    project_id: str,
    document_key: str,
    name: str = "original",
) -> OriginalDocumentAcquisition:
    """Read exact immutable metadata; this value does not grant fact admission."""
    if not name:
        raise ValueError("original document selection requires its explicit name")
    document = table("kb.document")
    row = connection.execute(
        select(
            document.c.project_id,
            document.c.key,
            document.c.content_hash,
            document.c.mime,
        ).where(document.c.project_id == project_id, document.c.key == document_key)
    ).one()
    return OriginalDocumentAcquisition(
        name,
        OriginalDocumentRef(
            kind="original-document",
            project_id=row.project_id,
            document_key=row.key,
            content_hash=row.content_hash,
            mime=row.mime,
        ),
    )


class OriginalDocumentConflict(SemanticRefusal):
    """An immutable source identity or its retained bytes differ."""


class OriginalDocumentReadRefused(OriginalDocumentConflict):
    def __init__(self, outcome: str, reason: str):
        self.outcome = outcome
        super().__init__(reason)


def register_original_document(
    connection: Connection,
    *,
    prepared: PreparedRelease,
    project_id: str,
    source_uri: str,
    original_path: str,
    original: bytes,
    mime: str,
    title: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> DocumentId:
    """Register exact source metadata and retain binary bytes through the current facet."""
    from pathlib import Path
    from sqlalchemy.dialects.postgresql import insert
    from corpus_structure.core.evidence import document_key
    from . import _source_admission_calls as calls
    from .identifiers import ProjectId, ReleaseId
    from .original_document_contracts import require_source_database_context

    if Path(original_path).read_bytes() != original:
        raise OriginalDocumentConflict("retained original bytes differ from registered source")
    digest = sha256(original).hexdigest()
    request = calls.prepare_source_document_registration(
        project_id=ProjectId(project_id), key=document_key(project_id, source_uri, digest),
        source_uri=source_uri, content_hash=digest, original_path=original_path,
        mime=mime, title=title, meta=dict(metadata or {}), projection_context=prepared,
    )
    require_source_database_context(connection, prepared)
    document = table("kb.document")
    connection.execute(insert(document).values(**calls.values_source_document_registration_kb_document(request)).on_conflict_do_nothing())
    row = calls.collect_source_document_registration(connection.execute(
        select(*calls.projection_source_document_registration).where(document.c.project_id == request.project_id, document.c.key == request.key)
    ))
    actual = row.decoded_json_fields(operation="data.initialize_source_project")
    if any(actual[name] != value for name, value in calls.expected_source_document_registration_kb_document(request).items()):
        raise OriginalDocumentConflict("source identity denotes another source descriptor")
    retained = calls.retain_original_document(connection, release_id=ReleaseId(prepared.release_id), document_id=row.id, original=original, projection_context=prepared)
    if retained != digest:
        raise OriginalDocumentConflict("retained original digest differs from registered bytes")
    return row.id


def read_original_document_bytes(connection: Connection, reference: OriginalDocumentRef, *, prepared: PreparedRelease) -> bytes:
    """Read one exact retained fact; unavailable custody never falls back to a local file."""
    from . import _source_admission_calls as calls
    from .identifiers import ProjectId
    from .original_document_contracts import require_source_database_context

    request = calls.prepare_original_document_descriptor(project_id=ProjectId(reference.project_id), key=reference.document_key, projection_context=prepared)
    require_source_database_context(connection, prepared)
    document = table("kb.document")
    row = calls.collect_original_document_descriptor(connection.execute(
        select(*calls.projection_original_document_descriptor).where(document.c.project_id == request.project_id, document.c.key == request.key)
    ))
    if row is None:
        raise OriginalDocumentReadRefused("missing", "retained original document is missing")
    if (row.project_id, row.key, row.content_hash, row.mime) != (reference.project_id, reference.document_key, reference.content_hash, reference.mime):
        raise OriginalDocumentReadRefused("invalid", "retained original descriptor differs from the selected fact")
    request = calls.prepare_original_document_artifact(artifact_digest=row.content_hash, projection_context=prepared)
    artifact = table("kb.source_artifact")
    content = calls.collect_original_document_artifact(connection.execute(select(*calls.projection_original_document_artifact).where(artifact.c.artifact_digest == request.artifact_digest)))
    if content is None:
        raise OriginalDocumentReadRefused("missing", "retained original artifact is unavailable")
    if sha256(content).hexdigest() != reference.content_hash:
        raise OriginalDocumentReadRefused("invalid", "retained original artifact is corrupt")
    return content
