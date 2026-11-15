"""Generated from authenticated fixed-call assets; do not edit."""

from __future__ import annotations

from typing import (
    Annotated,
    Protocol,
    TypedDict,
    cast,
)

from pydantic import Field, JsonValue, TypeAdapter
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
    func,
    select,
)
from sqlalchemy.dialects.postgresql import BYTEA
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
    "f45913b4d4faa8e662365758418ece1b435f1bacc7c5d938a0834f08c1bb9eda"
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
    project_id: ProjectId
    key: str
    source_uri: str
    content_hash: str
    original_path: str
    mime: str
    title: str | None
    meta: JsonValue


def prepare_source_document_registration(
    *,
    project_id: ProjectId,
    key: str,
    source_uri: str,
    content_hash: str,
    original_path: str,
    mime: str,
    title: str | None,
    meta: JsonValue,
    projection_context: PreparedRelease,
) -> _source_document_registrationRequest:
    _request = _source_document_registrationRequest(
        project_id=project_id,
        key=key,
        source_uri=source_uri,
        content_hash=content_hash,
        original_path=original_path,
        mime=mime,
        title=title,
        meta=meta,
    )
    require_call_context(
        projection_context,
        "data.initialize_source_project",
        "source_document_registration",
        SOURCE_DOCUMENT_REGISTRATION_CONTRACT_DIGEST,
    )
    return _request


class SourceDocumentRegistrationKbDocumentValues(TypedDict):
    project_id: ProjectId
    key: str
    source_uri: str
    content_hash: str
    original_path: str
    mime: str
    title: str | None
    meta: JsonValue


def values_source_document_registration_kb_document(
    request: _source_document_registrationRequest,
) -> SourceDocumentRegistrationKbDocumentValues:
    return {
        "project_id": request.project_id,
        "key": request.key,
        "source_uri": request.source_uri,
        "content_hash": request.content_hash,
        "original_path": request.original_path,
        "mime": request.mime,
        "title": request.title,
        "meta": request.meta,
    }


class SourceDocumentRegistrationKbDocumentValuesExpected(TypedDict):
    project_id: ProjectId
    key: str
    source_uri: str
    content_hash: str
    original_path: str
    mime: str
    title: str | None
    meta: JsonValue


def expected_source_document_registration_kb_document(
    request: _source_document_registrationRequest,
) -> SourceDocumentRegistrationKbDocumentValuesExpected:
    return {
        "project_id": request.project_id,
        "key": request.key,
        "source_uri": request.source_uri,
        "content_hash": request.content_hash,
        "original_path": request.original_path,
        "mime": request.mime,
        "title": request.title,
        "meta": request.meta,
    }


class _source_document_registration_kb_documentColumns(TypedColumns):
    id: Named[DocumentId]
    project_id: Named[ProjectId]
    key: Named[str]
    source_uri: Named[str]
    content_hash: Named[str]
    original_path: Named[str]
    mime: Named[str]
    title: Named[str | None]
    meta: Named[JsonValue]


class _source_document_registration_kb_documentColumnsProtocol(Protocol):
    id: Column[DocumentId]
    project_id: Column[ProjectId]
    key: Column[str]
    source_uri: Column[str]
    content_hash: Column[str]
    original_path: Column[str]
    mime: Column[str]
    title: Column[str | None]
    meta: Column[JsonValue]


_source_document_registration_kb_document = _core_table("kb.document").with_cols(
    _source_document_registration_kb_documentColumns
)
_source_document_registration_kb_document_columns = cast(
    _source_document_registration_kb_documentColumnsProtocol,
    _source_document_registration_kb_document.c,
)

projection_source_document_registration: tuple[
    ColumnElement[DocumentId],
    ColumnElement[ProjectId],
    ColumnElement[str],
    ColumnElement[str],
    ColumnElement[str],
    ColumnElement[str],
    ColumnElement[str],
    ColumnElement[str | None],
    ColumnElement[str],
] = (
    _source_document_registration_kb_document_columns.id.label("id"),
    _source_document_registration_kb_document_columns.project_id.label("project_id"),
    _source_document_registration_kb_document_columns.key.label("key"),
    _source_document_registration_kb_document_columns.source_uri.label("source_uri"),
    _source_document_registration_kb_document_columns.content_hash.label("content_hash"),
    _source_document_registration_kb_document_columns.original_path.label("original_path"),
    _source_document_registration_kb_document_columns.mime.label("mime"),
    _source_document_registration_kb_document_columns.title.label("title"),
    _source_document_registration_kb_document_columns.meta.cast(Text()).label("meta"),
)


def materialize_source_document_registration(
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


def collect_source_document_registration(
    result: Result[DocumentId, ProjectId, str, str, str, str, str, str | None, str],
) -> RegisteredOriginalDocument:
    with native_result_scope("data.initialize_source_project", "RegisteredOriginalDocument"):
        return materialize_source_document_registration(result.one())


ORIGINAL_DOCUMENT_DESCRIPTOR_CONTRACT_DIGEST = (
    "cc75c4bf1ff3e67657c90cce56a071f38836ac22b399bac99736baae470760e7"
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
    "08cb024ed6511250f348d31450dec96606f07133b1b10c29d35fa30d8eae5d12"
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


RETAIN_ORIGINAL_DOCUMENT_CONTRACT_DIGEST = (
    "5489f5a1920ab662abf628b9f251bb0e17296c64b09e19985f3ddd547bb7e9db"
)


class _retain_original_documentRequest(OperationResult):
    release_id: ReleaseId
    document_id: Annotated[
        DocumentId, Field(ge=DocumentId(-9223372036854775808), le=DocumentId(9223372036854775807))
    ]
    original: bytes


_retain_original_document_function = func.ops.retain_original_document(
    bindparam("release_id", type_=Text()),
    bindparam("document_id", type_=BigInteger()),
    bindparam("original", type_=BYTEA()),
    type_=Text(),
)
_retain_original_document_statement = select(_retain_original_document_function)


def prepare_retain_original_document(
    *,
    release_id: ReleaseId,
    document_id: DocumentId,
    original: bytes,
    projection_context: PreparedRelease,
) -> Select[str]:
    _request = _retain_original_documentRequest(
        release_id=release_id,
        document_id=document_id,
        original=original,
    )
    require_call_context(
        projection_context,
        "data.initialize_source_project",
        "retain_original_document",
        RETAIN_ORIGINAL_DOCUMENT_CONTRACT_DIGEST,
    )
    return _retain_original_document_statement.params(
        **{
            "release_id": _request.release_id,
            "document_id": _request.document_id,
            "original": _request.original,
        }
    )


_retain_original_document_adapter = TypeAdapter(str)


def materialize_retain_original_document(row: tuple[str]) -> str:
    with native_result_scope(
        "data.initialize_source_project", "retain_original_document", "digest"
    ):
        checked = _retain_original_document_adapter.validate_python(row[0], strict=True)
        return checked


def retain_original_document(
    conn: Connection,
    *,
    release_id: ReleaseId,
    document_id: DocumentId,
    original: bytes,
    projection_context: PreparedRelease,
) -> str:
    _statement = prepare_retain_original_document(
        release_id=release_id,
        document_id=document_id,
        original=original,
        projection_context=projection_context,
    )
    _native_result = conn.execute(_statement)
    with native_result_scope("data.initialize_source_project", "retain_original_document"):
        row = _native_result.one()
        return materialize_retain_original_document(row)


CALL_CONTRACT_DIGEST = "89037656e1b852d322c095c184e2acf1d33091bc6967401d3a5648f12b5888a2"
