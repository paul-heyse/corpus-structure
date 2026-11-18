"""Generated from authenticated fixed-call assets; do not edit."""

from __future__ import annotations

from typing import (
    Protocol,
    TypedDict,
    cast,
)

from pydantic import JsonValue, TypeAdapter
from sqlalchemy import (
    BigInteger,
    Column,
    Connection,
    Named,
    Result,
    Select,
    Text,
    TypedColumns,
    bindparam,
    column,
    func,
    select,
)
from sqlalchemy.dialects.postgresql import BYTEA, JSONB
from sqlalchemy.sql import ColumnElement

from corpus_structure.semantic.identifiers import DocumentId as DocumentId
from corpus_structure.semantic.identifiers import ProjectId as ProjectId
from corpus_structure.semantic.identifiers import ReleaseId as ReleaseId

from .data_operation_ports import DataOperationNativeRow as NativeRowResult
from .data_operation_ports import DataOperationWireValue as OperationResult
from .metadata import table as _core_table
from .operation_value_types import (
    NativeResultViolation,
    native_result_scope,
)
from .original_document_contracts import require_source_call_context as require_call_context
from .types import PreparedRelease


def _required[T](value: T | None, field: str, result_class: str, operation: str) -> T:
    if value is None:
        raise NativeResultViolation(operation, result_class, field)
    return value


SOURCE_DOCUMENT_REGISTRATION_CONTRACT_DIGEST = (
    "b33045920152889c44da0e4513960c4bb76531a1efd7ce3616aa7c9648620f82"
)


class RegisteredOriginalDocument(NativeRowResult):
    __json_fields__ = ("meta",)
    id: DocumentId
    project_id: ProjectId
    key: str
    source_uri: str
    content_hash: str
    original_path: str
    mime: str
    title: str | None
    meta: str


class _source_document_registrationRequest(OperationResult):
    release_id: ReleaseId
    project_id: ProjectId
    source_uri: str
    content_hash: str
    original_path: str
    mime: str
    title: str | None
    meta: JsonValue
    original: bytes


_source_document_registration_function = func.ops.register_original_document(
    bindparam("release_id", type_=Text()),
    bindparam("project_id", type_=Text()),
    bindparam("source_uri", type_=Text()),
    bindparam("content_hash", type_=Text()),
    bindparam("original_path", type_=Text()),
    bindparam("mime", type_=Text()),
    bindparam("title", type_=Text()),
    bindparam("meta", type_=JSONB(astext_type=Text())),
    bindparam("original", type_=BYTEA()),
).table_valued(
    column("id", BigInteger()),
    column("project_id", Text()),
    column("key", Text()),
    column("source_uri", Text()),
    column("content_hash", Text()),
    column("original_path", Text()),
    column("mime", Text()),
    column("title", Text()),
    column("meta", JSONB(astext_type=Text())),
)


class _source_document_registrationColumns(Protocol):
    id: Column[DocumentId]
    project_id: Column[ProjectId]
    key: Column[str]
    source_uri: Column[str]
    content_hash: Column[str]
    original_path: Column[str]
    mime: Column[str]
    title: Column[str | None]
    meta: Column[JsonValue]


_source_document_registration_columns = cast(
    _source_document_registrationColumns, _source_document_registration_function.c
)
_source_document_registration_statement = select(
    _source_document_registration_columns.id,
    _source_document_registration_columns.project_id,
    _source_document_registration_columns.key,
    _source_document_registration_columns.source_uri,
    _source_document_registration_columns.content_hash,
    _source_document_registration_columns.original_path,
    _source_document_registration_columns.mime,
    _source_document_registration_columns.title,
    _source_document_registration_columns.meta.cast(Text()).label("meta"),
)


def _source_document_registration_result(
    row: tuple[int, str, str, str, str, str, str, str | None, str],
) -> RegisteredOriginalDocument:
    with native_result_scope("data.initialize_source_project", "RegisteredOriginalDocument"):
        return RegisteredOriginalDocument(
            id=DocumentId(row[0]),
            project_id=ProjectId(row[1]),
            key=row[2],
            source_uri=row[3],
            content_hash=row[4],
            original_path=row[5],
            mime=row[6],
            title=row[7],
            meta=row[8],
        )


def prepare_source_document_registration(
    *,
    release_id: ReleaseId,
    project_id: ProjectId,
    source_uri: str,
    content_hash: str,
    original_path: str,
    mime: str,
    title: str | None,
    meta: JsonValue,
    original: bytes,
    projection_context: PreparedRelease,
) -> Select[DocumentId, ProjectId, str, str, str, str, str, str | None, str]:
    _request = _source_document_registrationRequest(
        release_id=release_id,
        project_id=project_id,
        source_uri=source_uri,
        content_hash=content_hash,
        original_path=original_path,
        mime=mime,
        title=title,
        meta=meta,
        original=original,
    )
    require_call_context(
        projection_context,
        "data.initialize_source_project",
        "source_document_registration",
        SOURCE_DOCUMENT_REGISTRATION_CONTRACT_DIGEST,
    )
    return _source_document_registration_statement.params(
        **{
            "release_id": _request.release_id,
            "project_id": _request.project_id,
            "source_uri": _request.source_uri,
            "content_hash": _request.content_hash,
            "original_path": _request.original_path,
            "mime": _request.mime,
            "title": _request.title,
            "meta": _request.meta,
            "original": _request.original,
        }
    )


materialize_source_document_registration = _source_document_registration_result


def source_document_registration(
    conn: Connection,
    *,
    release_id: ReleaseId,
    project_id: ProjectId,
    source_uri: str,
    content_hash: str,
    original_path: str,
    mime: str,
    title: str | None,
    meta: JsonValue,
    original: bytes,
    projection_context: PreparedRelease,
) -> RegisteredOriginalDocument:
    _statement = prepare_source_document_registration(
        release_id=release_id,
        project_id=project_id,
        source_uri=source_uri,
        content_hash=content_hash,
        original_path=original_path,
        mime=mime,
        title=title,
        meta=meta,
        original=original,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("data.initialize_source_project", "RegisteredOriginalDocument"):
        return _source_document_registration_result(_native_result.one())


ORIGINAL_DOCUMENT_DESCRIPTOR_CONTRACT_DIGEST = (
    "ce00ea9d69b5a2f6e45833f8c313c5884283c0da90265177b32b1853a0bc18ea"
)


class OriginalDocumentDescriptor(NativeRowResult):
    id: DocumentId
    project_id: ProjectId
    key: str
    content_hash: str
    mime: str


class _original_document_descriptorRequest(OperationResult):
    project_id: ProjectId
    key: str


def prepare_original_document_descriptor(
    *,
    project_id: ProjectId,
    key: str,
    projection_context: PreparedRelease,
) -> _original_document_descriptorRequest:
    _request = _original_document_descriptorRequest(
        project_id=project_id,
        key=key,
    )
    require_call_context(
        projection_context,
        "data.initialize_source_project",
        "original_document_descriptor",
        ORIGINAL_DOCUMENT_DESCRIPTOR_CONTRACT_DIGEST,
    )
    return _request


class OriginalDocumentDescriptorKbDocumentValues(TypedDict):
    project_id: ProjectId
    key: str


def values_original_document_descriptor_kb_document(
    request: _original_document_descriptorRequest,
) -> OriginalDocumentDescriptorKbDocumentValues:
    return {
        "project_id": request.project_id,
        "key": request.key,
    }


class OriginalDocumentDescriptorKbDocumentValuesExpected(TypedDict):
    project_id: ProjectId
    key: str


def expected_original_document_descriptor_kb_document(
    request: _original_document_descriptorRequest,
) -> OriginalDocumentDescriptorKbDocumentValuesExpected:
    return {
        "project_id": request.project_id,
        "key": request.key,
    }


class _original_document_descriptor_kb_documentColumns(TypedColumns):
    id: Named[DocumentId]
    project_id: Named[ProjectId]
    key: Named[str]
    content_hash: Named[str]
    mime: Named[str]


class _original_document_descriptor_kb_documentColumnsProtocol(Protocol):
    id: Column[DocumentId]
    project_id: Column[ProjectId]
    key: Column[str]
    content_hash: Column[str]
    mime: Column[str]


_original_document_descriptor_kb_document = _core_table("kb.document").with_cols(
    _original_document_descriptor_kb_documentColumns
)
_original_document_descriptor_kb_document_columns = cast(
    _original_document_descriptor_kb_documentColumnsProtocol,
    _original_document_descriptor_kb_document.c,
)

projection_original_document_descriptor: tuple[
    ColumnElement[DocumentId],
    ColumnElement[ProjectId],
    ColumnElement[str],
    ColumnElement[str],
    ColumnElement[str],
] = (
    _original_document_descriptor_kb_document_columns.id.label("id"),
    _original_document_descriptor_kb_document_columns.project_id.label("project_id"),
    _original_document_descriptor_kb_document_columns.key.label("key"),
    _original_document_descriptor_kb_document_columns.content_hash.label("content_hash"),
    _original_document_descriptor_kb_document_columns.mime.label("mime"),
)


def materialize_original_document_descriptor(
    row: tuple[int, str, str, str, str],
) -> OriginalDocumentDescriptor:
    with native_result_scope("data.initialize_source_project", "OriginalDocumentDescriptor"):
        return OriginalDocumentDescriptor(
            id=DocumentId(row[0]),
            project_id=ProjectId(row[1]),
            key=row[2],
            content_hash=row[3],
            mime=row[4],
        )


def collect_original_document_descriptor(
    result: Result[DocumentId, ProjectId, str, str, str],
) -> OriginalDocumentDescriptor | None:
    with native_result_scope("data.initialize_source_project", "OriginalDocumentDescriptor"):
        row = result.one_or_none()
        return None if row is None else materialize_original_document_descriptor(row)


ORIGINAL_DOCUMENT_ARTIFACT_CONTRACT_DIGEST = (
    "90ca2eb3278ed59058dd27db39b2ff7b376d5d5e1e0a914413b69ddb9ced4eb7"
)


class _original_document_artifactRequest(OperationResult):
    artifact_digest: str


def prepare_original_document_artifact(
    *,
    artifact_digest: str,
    projection_context: PreparedRelease,
) -> _original_document_artifactRequest:
    _request = _original_document_artifactRequest(
        artifact_digest=artifact_digest,
    )
    require_call_context(
        projection_context,
        "data.initialize_source_project",
        "original_document_artifact",
        ORIGINAL_DOCUMENT_ARTIFACT_CONTRACT_DIGEST,
    )
    return _request


class OriginalDocumentArtifactKbSourceArtifactValues(TypedDict):
    artifact_digest: str


def values_original_document_artifact_kb_source_artifact(
    request: _original_document_artifactRequest,
) -> OriginalDocumentArtifactKbSourceArtifactValues:
    return {
        "artifact_digest": request.artifact_digest,
    }


class OriginalDocumentArtifactKbSourceArtifactValuesExpected(TypedDict):
    artifact_digest: str


def expected_original_document_artifact_kb_source_artifact(
    request: _original_document_artifactRequest,
) -> OriginalDocumentArtifactKbSourceArtifactValuesExpected:
    return {
        "artifact_digest": request.artifact_digest,
    }


class _original_document_artifact_kb_source_artifactColumns(TypedColumns):
    content: Named[bytes]


class _original_document_artifact_kb_source_artifactColumnsProtocol(Protocol):
    content: Column[bytes]


_original_document_artifact_kb_source_artifact = _core_table("kb.source_artifact").with_cols(
    _original_document_artifact_kb_source_artifactColumns
)
_original_document_artifact_kb_source_artifact_columns = cast(
    _original_document_artifact_kb_source_artifactColumnsProtocol,
    _original_document_artifact_kb_source_artifact.c,
)

projection_original_document_artifact: tuple[ColumnElement[bytes]] = (
    _original_document_artifact_kb_source_artifact_columns.content.label("content"),
)

_original_document_artifact_adapter = TypeAdapter(bytes)


def materialize_original_document_artifact(row: tuple[bytes]) -> bytes:
    with native_result_scope("data.initialize_source_project", "bytes"):
        return _original_document_artifact_adapter.validate_python(row[0], strict=True)


def collect_original_document_artifact(result: Result[bytes]) -> bytes | None:
    with native_result_scope("data.initialize_source_project", "bytes"):
        row = result.one_or_none()
        return None if row is None else materialize_original_document_artifact(row)


CALL_CONTRACT_DIGEST = "7c3dabcf82751d8710182e70880f38785ae796513975abca2044c912922e0e18"
